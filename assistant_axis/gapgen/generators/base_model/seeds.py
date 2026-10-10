"""The seed bundle: the external material every prompt is drawn from (plan section 5, ``seeds.py``).

* **adjectives** (seed list A): the TDA rows of the census table (the censuses generator's frozen interface,
  ``load_census_table``), kept when the TDA familiarity ``prop`` (the share of raters who knew the word) is at
  least ``familiarity_floor`` (0.5: the "too rare for the model" filter), each with its OEWN definition from
  the table as a gloss (the ``list_gloss`` family shows it).
* **bios** (seed list B): openings of Wikipedia biographies from ``wiki_bio`` (``wikipedia-biography-dataset.zip``,
  CoreNLP-tokenized and lower-cased; detokenized here), at most ``max_bio_words`` words, at least
  ``min_bio_words``.  A seeded reservoir of ``bio_pool_size`` articles of one split is drawn once and cached
  beside the archive (gitignored, like the archive: biography text never enters a tracked file).
* **occupations** (seed list C): O*NET occupation titles (``occupation_data.csv``), un-inverted and lower-cased.
* **nouns**: common OEWN nouns (Zipf >= 3.5, one lower-case word, concrete lexicographer files, no sense
  that is a person), the context words of the contrast and AI families.
* **constraints**: the prompt families' constraint phrases live in :mod:`.prompts` (wording is prompt data,
  pinned by ``PROMPTS_VERSION``); the bundle carries no corpus material of any kind.

Nothing here reads ``data/traits`` or ``data/roles`` (a test watches the open calls).  Draws take a
``random.Random`` so that a fixed seed gives fixed prompts.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text

from . import ONET_DIR, WIKIBIO_DIR

WIKIBIO_ZIP = "data/wikipedia-biography-dataset.zip"
ONET_FILE = "occupation_data.csv"
#: Bumped whenever the opening text a pool entry holds changes (2: single quotes detokenized).
POOL_VERSION = 2
#: OEWN lexicographer files whose nouns make neutral context words (things, places, events, food ...).
CONCRETE_LEXFILES = frozenset({"noun.artifact", "noun.object", "noun.location", "noun.food", "noun.plant",
                               "noun.animal", "noun.substance", "noun.body", "noun.phenomenon", "noun.time",
                               "noun.event", "noun.quantity", "noun.shape"})
COMMON_NOUN_MIN_ZIPF = 3.5

_DETOK = (("-lrb-", "("), ("-rrb-", ")"), ("-lsb-", "["), ("-rsb-", "]"), ("-lcb-", "{"), ("-rcb-", "}"),
          ("``", '"'), ("''", '"'), (" -- ", " – "))
_SPACE_BEFORE = re.compile(r" ([,.;:!?%)\]}]|'s\b|n't\b|'re\b|'ve\b|'ll\b|'d\b|'m\b)")
_SPACE_AFTER = re.compile(r"([(\[{]) ")
_QUOTED = re.compile(r'" ([^"]*?) "')
_SQUOTED = re.compile(r"` ([^`']*?) '")
_LEADING_NOTE = re.compile(r"^\s*\([^)]*\)\s*")


@dataclass(frozen=True)
class SeedWord:
    word: str
    gloss: Optional[str]
    prop: Optional[float]


@dataclass(frozen=True)
class Bio:
    ref: str       # wikibio:<split>:<0-based index in the split>
    name: str
    text: str


@dataclass
class SeedBundle:
    adjectives: tuple[SeedWord, ...]
    bios: tuple[Bio, ...]
    occupations: tuple[str, ...]
    nouns: tuple[str, ...]
    manifest: dict = field(default_factory=dict)

    def draw_adjectives(self, rng: random.Random, k: int, *, letter: Optional[str] = None,
                        with_gloss: bool = False) -> list[SeedWord]:
        """``k`` distinct adjectives; with ``letter``, all starting with it when at least ``k`` do; with
        ``with_gloss``, only adjectives that have a definition."""
        pool = self.adjectives
        if with_gloss:
            pool = tuple(a for a in pool if a.gloss) or pool
        if letter:
            sub = tuple(a for a in pool if a.word.startswith(letter))
            if len(sub) >= k:
                pool = sub
        return rng.sample(pool, min(k, len(pool)))

    def draw_bio(self, rng: random.Random) -> Bio:
        return rng.choice(self.bios)

    def draw_occupation(self, rng: random.Random) -> str:
        return rng.choice(self.occupations)

    def draw_nouns(self, rng: random.Random, k: int) -> list[str]:
        return rng.sample(self.nouns, min(k, len(self.nouns)))


# ---------------------------------------------------------------------------- adjectives

def tda_adjectives(census_table: Path, *, familiarity_floor: float = 0.5) -> list[SeedWord]:
    """The census table's TDA rows with ``prop >= familiarity_floor``, in rank order."""
    from assistant_axis.gapgen.generators.censuses import load_census_table
    out = []
    for r in load_census_table(census_table):
        if not (r.tda and r.stem and r.surface):
            continue
        prop = r.tda.get("prop")
        if prop is None or prop < familiarity_floor:
            continue
        gloss = (r.wordnet or {}).get("definition") or r.gloss_hint
        if gloss:
            gloss = _LEADING_NOTE.sub("", gloss) or None     # OEWN usage notes: "(followed by 'of') not having ..."
        out.append(SeedWord(word=r.surface, gloss=gloss, prop=prop))
    return out


# ---------------------------------------------------------------------------- wiki_bio

def detokenize(text: str) -> str:
    """Undo the CoreNLP tokenization of a WikiBio sentence (brackets, quotes, spacing)."""
    s = " " + " ".join(text.split()) + " "
    for a, b in _DETOK:
        s = s.replace(f" {a} " if a.startswith("-") else a, f" {b} " if a.startswith("-") else b)
    s = " ".join(s.split())
    s = _QUOTED.sub(r'"\1"', s)
    s = _SQUOTED.sub(r"'\1'", s)
    s = _SPACE_BEFORE.sub(r"\1", s)
    s = _SPACE_AFTER.sub(r"\1", s)
    return s.strip()


def _capitalize_sentences(text: str) -> str:
    parts = re.split(r"(?<=[.!?]) ", text)
    return " ".join(p[:1].upper() + p[1:] for p in parts if p)


def _box_name(box: str) -> Optional[str]:
    """``name_1:walter name_2:extra`` -> ``walter extra``; else the ``article_title_*`` fields."""
    for field_name in ("name", "article_title"):
        parts: dict[int, str] = {}
        for cell in box.rstrip("\n").split("\t"):
            key, _, val = cell.partition(":")
            m = re.fullmatch(rf"{field_name}_(\d+)", key)
            if m and val and val != "<none>":
                parts[int(m.group(1))] = val
        if parts:
            return " ".join(parts[i] for i in sorted(parts))
    return None


def _title_case(name: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in detokenize(name).split())


def first_words(text: str, limit: int) -> str:
    """Whole sentences up to ``limit`` words; a first sentence longer than that is cut at ``limit`` and
    marked with an ellipsis."""
    out: list[str] = []
    n = 0
    for sent in re.split(r"(?<=[.!?]) ", text):
        w = sent.split()
        if n + len(w) > limit:
            if not out:
                return " ".join(w[:limit]) + " ..."
            break
        out.append(sent)
        n += len(w)
    return " ".join(out)


def iter_wikibio(zip_path: Path, *, split: str = "train", max_words: int = 200) -> Iterator[Bio]:
    """Every article of a split of the WikiBio archive: ``Bio(ref, name, opening)``."""
    stem = "valid" if split in ("val", "valid") else split
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()

        def member(ext: str) -> str:
            want = f"/{stem}/{stem}.{ext}"
            hit = [n for n in names if n.endswith(want)]
            if len(hit) != 1:
                raise FileNotFoundError(f"{zip_path}: no single member ending {want}")
            return hit[0]

        opened = [io.TextIOWrapper(z.open(member(e)), encoding="utf-8") for e in ("title", "box", "nb", "sent")]
        titles, boxes, nbs, sents = opened
        try:
            for i, (title, box, nb) in enumerate(zip(titles, boxes, nbs)):
                lines = [sents.readline() for _ in range(int(nb))]
                raw_name = _box_name(box) or title.strip()
                name = _title_case(raw_name)
                text = detokenize(" ".join(x.strip() for x in lines))
                lc = detokenize(raw_name)
                if lc:
                    text = re.sub(rf"\b{re.escape(lc)}\b", name, text)
                text = _capitalize_sentences(text)
                yield Bio(ref=f"wikibio:{split}:{i}", name=name, text=first_words(text, max_words))
        finally:
            for f in opened:
                f.close()


def bio_pool(zip_path: Path, *, split: str = "train", size: int = 20_000, seed: int = 0, min_words: int = 15,
             max_words: int = 200, cache_dir: Optional[Path] = None) -> list[Bio]:
    """A seeded reservoir sample of ``size`` usable openings (at least ``min_words`` words), in index order.
    Cached as ``bio_pool_<split>_k<size>_s<seed>.jsonl`` in ``cache_dir`` (the archive's directory's parent by
    default, which is gitignored), keyed on the archive's size and the parameters."""
    zip_path = Path(zip_path)
    cache_dir = Path(cache_dir) if cache_dir else zip_path.parent.parent
    cache = cache_dir / f"bio_pool_{split}_k{size}_s{seed}.jsonl"
    meta = {"pool_version": POOL_VERSION, "zip_size": zip_path.stat().st_size, "split": split, "size": size,
            "seed": seed, "min_words": min_words, "max_words": max_words}
    if cache.exists():
        lines = cache.read_text(encoding="utf-8").splitlines()
        if lines and json.loads(lines[0]) == meta:
            return [Bio(**json.loads(x)) for x in lines[1:] if x.strip()]
    rng = random.Random(seed)
    res: list[tuple[int, Bio]] = []
    n = 0
    for i, b in enumerate(iter_wikibio(zip_path, split=split, max_words=max_words)):
        if len(b.text.split()) < min_words:
            continue
        n += 1
        if len(res) < size:
            res.append((i, b))
        else:
            j = rng.randrange(n)
            if j < size:
                res[j] = (i, b)
    pool = [b for _, b in sorted(res, key=lambda t: t[0])]
    body = json.dumps(meta) + "\n" + "".join(json.dumps(b.__dict__, ensure_ascii=False) + "\n" for b in pool)
    cache_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, cache)
    return pool


# ---------------------------------------------------------------------------- O*NET

def parse_onet(path: Path) -> list[str]:
    """Occupation titles from ``occupation_data.csv``: one comma inverts (``Cooks, Restaurant`` -> ``restaurant
    cooks``); with more commas the part before the first is kept; lower-cased except all-capital words."""
    out: list[str] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            t = (row.get("Title") or "").strip()
            if not t:
                continue
            parts = [p.strip() for p in t.split(",")]
            t = f"{parts[1]} {parts[0]}" if len(parts) == 2 else parts[0]
            t = " ".join(w if (w.isupper() and len(w) > 1) else w.lower() for w in t.split())
            if t not in out:
                out.append(t)
    return out


# ---------------------------------------------------------------------------- nouns

def oewn_common_nouns(*, wordnet=None, zipf_fn: Optional[Callable[[str], float]] = None,
                      min_zipf: float = COMMON_NOUN_MIN_ZIPF) -> list[str]:  # pragma: no cover - needs OEWN
    """Common, concrete, non-person OEWN nouns (sorted): a one-word lower-case lemma of four letters or more,
    Zipf >= ``min_zipf``, whose first sense is in :data:`CONCRETE_LEXFILES` and no sense is ``noun.person``;
    not also a verb (``wash``, ``join``), and not the plural of another noun lemma (``parts``)."""
    if wordnet is None:
        from assistant_axis.gapgen.wordnet import oewn
        wordnet = oewn()
    if zipf_fn is None:
        from wordfreq import zipf_frequency
        zipf_fn = lambda w: zipf_frequency(w, "en")  # noqa: E731
    verbs = {w.lemma() for w in wordnet.words(pos="v")}
    nouns_all = {w.lemma() for w in wordnet.words(pos="n")}
    out = set()
    for w in wordnet.words(pos="n"):
        lemma = w.lemma()
        if len(lemma) < 4 or not lemma.isalpha() or not lemma.islower():
            continue
        if lemma in verbs or (lemma.endswith("s") and lemma[:-1] in nouns_all):
            continue
        senses = w.senses()
        if not senses:
            continue
        lex = [s.synset().lexfile() for s in senses]
        if lex[0] not in CONCRETE_LEXFILES or "noun.person" in lex:
            continue
        if zipf_fn(lemma) < min_zipf:
            continue
        out.add(lemma)
    return sorted(out)


# ---------------------------------------------------------------------------- the bundle

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_seed_bundle(*, census_table: Optional[Path] = None, wikibio_dir: Path = WIKIBIO_DIR,
                     onet_dir: Path = ONET_DIR, familiarity_floor: float = 0.5, bio_pool_size: int = 20_000,
                     pool_seed: int = 0, bio_split: str = "train", min_bio_words: int = 15, max_bio_words: int = 200,
                     nouns: Optional[Sequence[str]] = None) -> SeedBundle:
    """Load every seed list (see the module docstring).  ``nouns`` replaces the OEWN noun list (tests)."""
    if census_table is None:
        from assistant_axis.gapgen.generators.censuses import CENSUS_TABLE_PATH
        census_table = CENSUS_TABLE_PATH
    census_table, wikibio_dir, onet_dir = Path(census_table), Path(wikibio_dir), Path(onet_dir)
    zip_path = wikibio_dir / WIKIBIO_ZIP
    onet_path = onet_dir / ONET_FILE
    for p, how in ((zip_path, "base_model_generator.py fetch --only wikibio"),
                   (onet_path, "base_model_generator.py fetch --only onet"), (census_table, "census_generator.py ingest")):
        if not p.exists():
            raise FileNotFoundError(f"missing {p}: run `{how}` first")
    adjectives = tda_adjectives(census_table, familiarity_floor=familiarity_floor)
    bios = bio_pool(zip_path, split=bio_split, size=bio_pool_size, seed=pool_seed, min_words=min_bio_words,
                    max_words=max_bio_words, cache_dir=wikibio_dir)
    occupations = parse_onet(onet_path)
    noun_list = list(nouns) if nouns is not None else oewn_common_nouns()
    manifest = {"census_table_sha256": _sha256(census_table), "familiarity_floor": familiarity_floor,
                "n_adjectives": len(adjectives), "wikibio_zip_size": zip_path.stat().st_size,
                "bio_split": bio_split, "bio_pool_size": bio_pool_size, "pool_seed": pool_seed,
                "min_bio_words": min_bio_words, "max_bio_words": max_bio_words, "n_bios": len(bios),
                "onet_sha256": _sha256(onet_path), "n_occupations": len(occupations), "n_nouns": len(noun_list),
                "nouns_source": "given" if nouns is not None else f"OEWN, Zipf >= {COMMON_NOUN_MIN_ZIPF}, concrete"}
    return SeedBundle(adjectives=tuple(adjectives), bios=tuple(bios), occupations=tuple(occupations),
                      nouns=tuple(noun_list), manifest=manifest)
