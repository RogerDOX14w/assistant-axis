"""The text corpora (Roger, 2026-10-14, open decision 2: "Why not now? This sounds like a good source, we might need
less of a frame for this"): curated character descriptions, read with looser regex frames than the Books bank.

Two sources (:data:`TEXT_SOURCES`), both written by people and selected by their users, which is what Roger's answer
3 admits ("if other people have generated such personas and then applied any curation or selection"):

* **PIPPA** (``PygmalionAI/PIPPA``, Apache-2.0, not gated, tagged not-for-all-audiences, which answer 2 accepts):
  the ``bot_description`` of ``pippa_deduped.jsonl`` (*measured* 257 MB), one per conversation, deduplicated here by
  text (many conversations share a bot);
* **the character cards** (``hieunguyenminh/roleplay``, CC BY 4.0, 5,755 cards, 2.2 MB): the ``description`` field.
  The file name is read from the Hub's file listing at fetch time (:func:`resolve_filename`).

Character descriptions list traits directly ("Personality: shy, stubborn, kind"; "She is kind, caring and a bit
shy"), so the bank (:data:`TEXT_FRAMES`) has **list frames** besides the fixed ones: ``trait_list`` (a "Personality:"
or "Traits:" label, and the W++ form ``Personality("shy" + "kind")``), ``copular_list`` (the adjectives after "she
is", "he seems": the list is read item by item and stops at the first item that is not one word, a hyphenated word,
a word before a preposition, or an "-ly" adverb before a word), ``attributive`` ("a shy, quiet girl"), the
possessive ``known_for`` and ``poss_nature`` ("her stubborn streak"), the **filler-first** frames Books cannot
locate (``to_a_fault``, ``by_nature``, ``at_heart``), ``tendency`` and ``always``.  Degree adverbs and hedges ("very",
"a bit", "kind of") are stripped from an item (:data:`INTENSIFIERS`).  Regex only, no spaCy, no POS tagger: a noun
in an adjective slot is M1's to turn away.  A filler with a capital in the running text is a name and is skipped;
list items are lower-cased (cards often capitalise them).

A frame's key in the table is ``<source>.<frame id>`` (``pippa.copular_list``), its ``source_ref``
``frames:<source>:<frame id>``.  **Document frequency** is the number of distinct descriptions with the filler in
the frame (the table's ``volumes``), ``match`` the number of occurrences, and the floor is
:data:`TEXT_FRAME_FLOOR` occurrences (the Books floor of 40 is for a corpus five orders of magnitude larger).  Each
(frame, filler) keeps its first example sentence, which the Books n-grams cannot give.

Downloads: :func:`fetch_text` writes each file to ``data/external/corpus_frames/<source>/`` (git-ignored) and records
URL, bytes, sha256, licence and Roger's go in ``DOWNLOAD_MANIFEST.json`` there; a source with no recorded approval is
refused (:class:`NotApproved`) unless ``approved_by`` names it.  ``extract-text --delete-raw`` removes the downloads
once the extracts are written (decision 2: "PIPPA ... is deleted after extraction if disk is short"); the manifest
keeps their hashes.  No paid API is involved.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import BinaryIO, Callable, Iterable, Iterator, Mapping, Optional, Protocol, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.normalize import STOPWORDS
from assistant_axis.gapgen.registry import utc_now

from ..ipip.download import NotApproved
from . import DOWNLOAD_MANIFEST_NAME, TEXT_EXTERNAL_DIR
from .books import Hit, aggregate
from .frames import PERSON_NOUNS, TOKEN_RE

TEXT_TYPES: tuple[str, ...] = ("list", "postposed")
#: The text frames' floor: occurrences in the frame over the whole source (see the module docstring).
TEXT_FRAME_FLOOR = 3
TOOL = "corpus_frames_generator.py fetch-text"
EXTRACTS_DIRNAME = "extracts"
EXTRACT_STATS_NAME = "extract_stats.json"
MAX_EXAMPLE_CHARS = 240
USER_AGENT = "assistant-axis corpus-frames generator (research; contact via the repository owner)"
HF_API = "https://huggingface.co/api/datasets/"
HF_RESOLVE = "https://huggingface.co/datasets/{repo}/resolve/main/{filename}"

#: Degree adverbs and hedges stripped from the front of an item (longest first when matched).
INTENSIFIERS: tuple[str, ...] = tuple(sorted({
    "very", "quite", "rather", "extremely", "incredibly", "really", "so", "too", "somewhat", "fairly", "pretty",
    "super", "highly", "deeply", "overly", "slightly", "mostly", "often", "always", "usually", "generally", "also",
    "sometimes", "a bit", "a little", "a little bit", "kind of", "sort of", "truly", "exceptionally", "remarkably",
    "terribly", "awfully", "fiercely", "insanely", "extra", "naturally", "secretly", "surprisingly", "genuinely",
    "a tad", "a bit of a", "very very", "most", "more", "less", "quite a bit", "occasionally", "frequently",
    "totally", "completely", "utterly", "absolutely", "hopelessly", "painfully", "almost", "nearly", "just",
}, key=lambda s: (-len(s), s)))
#: Words that open a copular clause but are not a description of the person ("she is born in ...").
EXCLUDED: frozenset = frozenset("""
born known called named used made seen found located based set currently now here there still just even like
actually going trying getting being having doing able unable not never only who that which what when where how
years year old ready supposed about sure
""".split()) | STOPWORDS
#: Person nouns the attributive frame closes on: the Books set and a few the descriptions use.
TEXT_PERSON_NOUNS: frozenset = PERSON_NOUNS | frozenset("kid teen teenager dude gal type personality".split())
PREPOSITIONS: frozenset = frozenset("of to with about toward towards at in around for by on".split())
DETERMINERS: frozenset = frozenset("a an the his her their my your our its this that these those some any".split())
_TOKEN = re.compile(rf"^{TOKEN_RE}$")
_INTENS_RE = re.compile(r"^(?:" + "|".join(re.escape(x) for x in INTENSIFIERS) + r")\s+", re.IGNORECASE)
_INTENS_ALT = "|".join(re.escape(x) for x in INTENSIFIERS)


# --------------------------------------------------------------------------- the frames

@dataclass(frozen=True)
class TextFrameSpec:
    """One text frame, before it is bound to a source."""
    id: str
    type: str
    kind: str                    # "list" (an item list), "single" (one filler, ``pattern`` group ``filler``)
    pattern: str
    note: str
    filler_kind: str = "adj"


@dataclass(frozen=True)
class TextFrame:
    """A text frame bound to a source: ``id`` is the table's frame key ``<source>.<frame id>``."""
    id: str
    base: str
    source: str
    type: str
    kind: str
    pattern: str
    note: str
    filler_kind: str = "adj"
    tier: int = 1
    floor: int = TEXT_FRAME_FLOOR

    @property
    def template(self) -> str:
        return self.note

    def as_dict(self) -> dict:
        return asdict(self)


_COP = (r"(?:is|was|are|were|seems|seemed|appears|appeared|remains|remained|can be|tends to be|has always been|"
        r"has been|is often|is always|is usually)")
_NOUNS = "|".join(sorted(TEXT_PERSON_NOUNS, key=lambda w: (-len(w), w)))
#: A clause's subject: a pronoun, a person noun, or a capitalised word (a name; ``{{char}}`` is read as "Char").
_SUBJ = rf"(?:he|she|they|char|i|you|{_NOUNS}|[A-Z][a-z]+)"
TEXT_FRAME_SPECS: tuple[TextFrameSpec, ...] = (
    TextFrameSpec("trait_list", "list", "list",
                  r"\b(?:personality(?:\s+traits?)?|traits?|character(?:istics|\s+traits?)|temperament|"
                  r"demeanou?r|attitude|disposition|mind)\s*(?:\([^)\n]{0,40}\))?\s*(?:[:=]|\s-\s)\s*"
                  r"(?P<items>[^\n]{1,400})",
                  "a labelled trait list (\"Personality: shy, stubborn, kind\")"),
    TextFrameSpec("copular_list", "copular", "list",
                  rf"\b{_SUBJ}\s+{_COP}\s+(?P<items>[^.;:!?\n]{{1,200}})",
                  "the adjectives after she is / he seems (\"She is kind, caring and a bit shy\")"),
    TextFrameSpec("attributive", "copular", "list",
                  rf"\b(?:a|an)\s+(?P<items>(?:{TOKEN_RE})(?:(?:,\s*|\s+and\s+|\s+)(?:{TOKEN_RE})){{0,3}})\s+"
                  rf"(?P<noun>{_NOUNS})\b",
                  "a X <person noun> (\"a shy, quiet girl\")"),
    TextFrameSpec("known_for", "possessive", "single",
                  rf"\bknown (?:for|as) (?:his|her|their|its) (?:(?:{_INTENS_ALT})\s+)?(?P<filler>{TOKEN_RE})\b",
                  "known for her X", filler_kind="quality_noun"),
    TextFrameSpec("poss_nature", "possessive", "single",
                  rf"\b(?:his|her|their) (?:(?:{_INTENS_ALT})\s+)?(?P<filler>{TOKEN_RE}) "
                  r"(?P<noun>nature|personality|streak|side|demeanou?r|attitude|temperament|disposition|heart)\b",
                  "her X nature / streak / side"),
    TextFrameSpec("to_a_fault", "postposed", "single", rf"\b(?P<filler>{TOKEN_RE}) to a fault\b", "X to a fault"),
    TextFrameSpec("by_nature", "postposed", "single", rf"\b(?P<filler>{TOKEN_RE}) by nature\b", "X by nature"),
    TextFrameSpec("at_heart", "postposed", "single", rf"\b(?P<filler>{TOKEN_RE}) at heart\b", "X at heart"),
    TextFrameSpec("tendency", "tendency", "single",
                  rf"\b(?:tendency|tends|tend|inclined|apt|prone) to be (?:(?:{_INTENS_ALT})\s+)?"
                  rf"(?P<filler>{TOKEN_RE})\b", "tends to be X"),
    TextFrameSpec("always", "habitual", "single",
                  rf"\b{_SUBJ} (?:is|was|are|were) (?:always|often|usually|constantly|forever) "
                  rf"(?P<filler>{TOKEN_RE})\b", "she is always X"),
)


# --------------------------------------------------------------------------- the sources

@dataclass(frozen=True)
class TextSource:
    key: str
    repo: str
    filename: Optional[str]          # None: resolved from the Hub's listing (``filename_pattern``)
    field: str
    licence: str
    licence_url: str
    what: str
    filename_pattern: str = r"\.(parquet|jsonl|json|csv)$"
    approval: Optional[str] = None   # None: refused unless the caller names Roger's go
    size_note: str = ""

    def url(self, filename: Optional[str] = None) -> str:
        fn = filename or self.filename
        if not fn:
            raise ValueError(f"{self.key}: no file name (resolve it from the Hub's listing first)")
        return HF_RESOLVE.format(repo=self.repo, filename=fn)


TEXT_SOURCES: dict[str, TextSource] = {s.key: s for s in (
    TextSource(key="pippa", repo="PygmalionAI/PIPPA", filename="pippa_deduped.jsonl", field="bot_description",
               licence="Apache-2.0", licence_url="https://www.apache.org/licenses/LICENSE-2.0",
               what="PIPPA: Character.AI conversations with their bots' human-written descriptions (bot_description)",
               size_note="about 257 MB (measured 2026-10-13 on the dataset card)"),
    TextSource(key="cards", repo="hieunguyenminh/roleplay", filename=None, field="description",
               licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/",
               what="5,755 role-play character cards (name, description, text); credited as CC BY 4.0 requires",
               size_note="about 2.2 MB (measured 2026-10-13 on the dataset card)"),
)}


def text_frames(sources: Iterable[str] = tuple(TEXT_SOURCES), specs: Sequence[TextFrameSpec] = TEXT_FRAME_SPECS
                ) -> list[TextFrame]:
    """Every text frame of every source (frame key ``<source>.<frame id>``)."""
    return [TextFrame(id=f"{s}.{sp.id}", base=sp.id, source=s, type=sp.type, kind=sp.kind, pattern=sp.pattern,
                      note=sp.note, filler_kind=sp.filler_kind) for s in sources for sp in specs]


def text_bank_sha256(specs: Sequence[TextFrameSpec] = TEXT_FRAME_SPECS) -> str:
    doc = {"specs": [asdict(s) for s in specs], "intensifiers": list(INTENSIFIERS), "excluded": sorted(EXCLUDED),
           "nouns": sorted(TEXT_PERSON_NOUNS), "floor": TEXT_FRAME_FLOOR, "token_re": TOKEN_RE}
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- reading the descriptions

def clean_text(text: str) -> str:
    """NFKC, straight quotes, ``{{char}}`` / ``{{user}}`` as names, markup tags dropped."""
    t = unicodedata.normalize("NFKC", str(text or ""))
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\{\{\s*char\s*\}\}", "Char", t, flags=re.IGNORECASE)
    t = re.sub(r"\{\{\s*user\s*\}\}", "User", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>\n]{0,80}>", " ", t)
    return t


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
    return [" ".join(p.split()) for p in parts if p and p.strip()]


def _strip_intensifiers(item: str) -> str:
    s = item.strip()
    while True:
        t = _INTENS_RE.sub("", s, count=1)
        if t == s:
            return s
        s = t.strip()


def item_filler(item: str, *, lower: bool) -> Optional[str]:
    """The filler an item of a list gives, or None (see the module docstring): one word, a hyphenated word, a word
    before a preposition (its first word), an "-ly" adverb before a word (both), or a word before a person noun."""
    s = item.strip().strip("\"'()[]{}*_~`").strip()
    s = re.sub(r"\s+(?:etc|and so on)\.?$", "", s, flags=re.IGNORECASE).rstrip(".!?").strip()
    if lower:
        s = s.lower()
    s = _strip_intensifiers(s)
    words = s.split()
    if not words or words[0].lower() in DETERMINERS:
        return None
    if any(w != w.lower() for w in words):
        return None
    if len(words) >= 2 and words[1] in PREPOSITIONS:
        words = words[:1]
    elif len(words) == 2 and words[1] in TEXT_PERSON_NOUNS:
        words = words[:1]
    elif len(words) == 2 and words[0].endswith("ly") and len(words[0]) > 4:
        pass
    elif len(words) != 1:
        return None
    if not all(_TOKEN.match(w) for w in words) or words[-1] in EXCLUDED or words[0] in EXCLUDED:
        return None
    if len(words) == 1 and (len(words[0]) < 3 or words[0] in TEXT_PERSON_NOUNS):
        return None
    return " ".join(words)


def _split_items(text: str, *, labelled: bool) -> list[str]:
    if labelled:
        text = re.split(r"\.\s|\.$", text)[0]
        quoted = re.findall(r'"([^"\n]{1,40})"', text)
        if quoted and "+" in text:                       # W++: Personality("shy" + "kind")
            return quoted
        return [x for x in re.split(r"[,;/|+•]|\s+and\s+|\s+or\s+|\s-\s", text) if x.strip()]
    return [x for x in re.split(r",\s*(?:and\s+|or\s+|but\s+)?|\s+(?:and|or|but|yet)\s+", text) if x.strip()]


_WPP_RE = re.compile(r"\b(?:personality|mind|traits?)\s*\(\s*(?P<items>[^)]{1,600})\)", re.IGNORECASE)


def frame_fillers(frame: TextFrame, sentence: str) -> list[tuple[str, Optional[str]]]:
    """``[(filler, noun)]`` the frame finds in one sentence."""
    out: list[tuple[str, Optional[str]]] = []
    if frame.base == "trait_list":
        found = [m.group("items") for m in re.finditer(frame.pattern, sentence, flags=re.IGNORECASE)]
        found += [m.group("items") for m in _WPP_RE.finditer(sentence)]
        for items in found:
            for it in _split_items(items, labelled=True):
                f = item_filler(it, lower=True)
                if f:
                    out.append((f, None))
        return out
    if frame.base == "copular_list":
        for m in re.finditer(frame.pattern, sentence):
            for it in _split_items(m.group("items"), labelled=False):
                f = item_filler(it, lower=False)
                if not f:
                    break                 # the list stops at its first item that is not a description
                out.append((f, None))
        return out
    if frame.base == "attributive":
        for m in re.finditer(frame.pattern, sentence):
            noun = m.group("noun")
            for w in re.split(r",\s*|\s+and\s+|\s+", m.group("items")):
                w = w.strip()
                if not w or w in DETERMINERS or w in INTENSIFIERS:
                    continue
                f = item_filler(w, lower=False)
                if f:
                    out.append((f, noun))
        return out
    for m in re.finditer(frame.pattern, sentence, flags=re.IGNORECASE):
        f = m.group("filler")
        if f != f.lower() or f in EXCLUDED or f in TEXT_PERSON_NOUNS or len(f) < 3:
            continue
        out.append((f, m.groupdict().get("noun").lower() if m.groupdict().get("noun") else None))
    return out


@dataclass
class TextExtract:
    hits: dict                   # frame key -> [Hit] (match = occurrences, volumes = documents)
    n_documents: int
    n_unique: int


def extract_frames(documents: Iterable[str], frames: Sequence[TextFrame]) -> TextExtract:
    """Run every frame over every distinct document (deduplicated by cleaned text)."""
    acc: dict[str, dict[tuple, list]] = {f.id: {} for f in frames}
    seen: set[str] = set()
    n_docs = 0
    for doc in documents:
        n_docs += 1
        t = clean_text(doc)
        h = hashlib.sha1(" ".join(t.split()).encode("utf-8")).hexdigest()
        if not t.strip() or h in seen:
            continue
        seen.add(h)
        doc_i = len(seen)
        for sent in sentences(t):
            for f in frames:
                for filler, noun in frame_fillers(f, sent):
                    a = acc[f.id].setdefault((filler, noun), [0, 0, -1, None])
                    a[0] += 1
                    if a[2] != doc_i:
                        a[1] += 1
                        a[2] = doc_i
                    if a[3] is None:
                        a[3] = sent[:MAX_EXAMPLE_CHARS].replace("\t", " ")
    hits = {k: [Hit(filler=f, noun=n, match=m, volumes=v, example=e) for (f, n), (m, v, _, e) in
                sorted(d.items(), key=lambda kv: (kv[0][0], kv[0][1] or ""))] for k, d in acc.items()}
    return TextExtract(hits=hits, n_documents=n_docs, n_unique=len(seen))


def read_documents(path: Path, field_name: str) -> Iterator[str]:
    """The ``field_name`` texts of a downloaded file: JSON lines, a JSON array, CSV, or parquet (``pyarrow``)."""
    p = Path(path)
    suf = p.suffix.lower()
    if suf == ".parquet":
        import pyarrow.parquet as pq
        names = pq.read_schema(p).names
        if field_name not in names:
            raise KeyError(f"{p.name}: no column {field_name!r} (columns: {', '.join(names)})")
        for v in pq.read_table(p, columns=[field_name]).column(field_name).to_pylist():
            if v:
                yield str(v)
        return
    if suf == ".csv":
        with open(p, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get(field_name):
                    yield row[field_name]
        return
    with open(p, encoding="utf-8") as fh:
        head = fh.read(1)
        fh.seek(0)
        if head == "[":
            for obj in json.load(fh):
                if isinstance(obj, dict) and obj.get(field_name):
                    yield str(obj[field_name])
            return
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get(field_name):
                yield str(obj[field_name])


# --------------------------------------------------------------------------- extracts on disk

def extract_dir(text_dir: Path = TEXT_EXTERNAL_DIR) -> Path:
    return Path(text_dir) / EXTRACTS_DIRNAME


def write_text_extract(hits: Sequence[Hit], path: Path) -> str:
    """``filler TAB noun TAB match TAB documents TAB example`` per line; returns the file's sha256."""
    body = "".join(f"{h.filler}\t{h.noun or ''}\t{h.match}\t{h.volumes}\t{(h.example or '').replace(chr(9), ' ')}\n"
                   for h in hits)
    atomic_write_text(body, Path(path))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def read_text_extract(path: Path) -> list[Hit]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = (line.split("\t") + ["", "", "", "", ""])[:5]
        try:
            m, v = int(parts[2]), int(parts[3])
        except ValueError:
            continue
        out.append(Hit(filler=parts[0], noun=parts[1] or None, match=m, volumes=v, example=parts[4] or None))
    return aggregate(out)


def run_extract(*, text_dir: Path = TEXT_EXTERNAL_DIR, sources: Iterable[str] = tuple(TEXT_SOURCES),
                manifest: Optional[Mapping] = None, delete_raw: bool = False, dry_run: bool = False,
                echo=print) -> dict:
    """Extract every source's frames from its downloaded file (named in ``DOWNLOAD_MANIFEST.json``), write
    ``extracts/<frame key>.tsv`` and ``extracts/extract_stats.json``; with ``delete_raw`` remove the downloads after."""
    root = Path(text_dir)
    man = dict(manifest) if manifest is not None else load_text_manifest(root)
    entries = {e["key"]: e for e in man.get("entries") or []}
    stats: dict = {"text_bank_sha256": text_bank_sha256(), "sources": {}, "frames": {}, "at": utc_now()}
    out_dir = extract_dir(root)
    deleted = []
    for key in sources:
        e = entries.get(key)
        if not e:
            echo(f"{key}: not downloaded (no manifest entry): run fetch-text first")
            continue
        path = root / e["file"]
        if not path.exists():
            echo(f"{key}: {path} is gone (deleted after an earlier extraction?): fetch it again to re-extract")
            continue
        frames = text_frames([key])
        ex = extract_frames(read_documents(path, TEXT_SOURCES[key].field), frames)
        stats["sources"][key] = {"file": e["file"], "sha256": e.get("sha256"), "n_documents": ex.n_documents,
                                 "n_unique": ex.n_unique}
        for f in frames:
            hs = ex.hits[f.id]
            stats["frames"][f.id] = {"hits": sum(h.match for h in hs), "fillers": len(hs),
                                     "above_floor": sum(1 for h in hs if h.match >= f.floor)}
            if not dry_run:
                stats["frames"][f.id]["sha256"] = write_text_extract(hs, out_dir / f"{f.id}.tsv")
        echo(f"{key}: {ex.n_unique:,} distinct descriptions of {ex.n_documents:,}; "
             + ", ".join(f"{f.base} {stats['frames'][f.id]['fillers']}" for f in frames))
        if delete_raw and not dry_run:
            path.unlink()
            deleted.append(str(path))
    stats["deleted_raw"] = deleted
    if not dry_run and stats["sources"]:
        prev = {}
        sp = out_dir / EXTRACT_STATS_NAME
        if sp.exists():
            prev = json.loads(sp.read_text(encoding="utf-8"))
        merged = {**prev, **stats, "sources": {**(prev.get("sources") or {}), **stats["sources"]},
                  "frames": {**(prev.get("frames") or {}), **stats["frames"]}}
        atomic_write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", sp)
    return stats


def text_extract_paths(text_dir: Path = TEXT_EXTERNAL_DIR) -> dict[str, Path]:
    """Every text extract present: ``{frame key: path}``."""
    d = extract_dir(text_dir)
    return {p.stem: p for p in sorted(d.glob("*.tsv"))} if d.exists() else {}


# --------------------------------------------------------------------------- the download

class TextFetcher(Protocol):
    def stream(self, url: str) -> BinaryIO: ...
    def json(self, url: str) -> object: ...


class HttpTextFetcher:  # pragma: no cover - the network
    def __init__(self, *, timeout: float = 120.0):
        self.timeout = timeout

    def stream(self, url: str) -> BinaryIO:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        return urllib.request.urlopen(req, timeout=self.timeout)  # noqa: S310 - fixed https URLs

    def json(self, url: str) -> object:
        with self.stream(url) as fh:
            return json.loads(fh.read().decode("utf-8"))


def resolve_filename(src: TextSource, *, fetch: TextFetcher) -> str:
    """The source's file: its fixed name, else the first file of the Hub's listing matching its pattern (largest
    parquet first: the Hub stores a dataset's table as ``data/train-*.parquet``)."""
    if src.filename:
        return src.filename
    info = fetch.json(HF_API + src.repo)
    files = [s.get("rfilename") for s in (info or {}).get("siblings") or [] if s.get("rfilename")]
    pat = re.compile(src.filename_pattern, re.IGNORECASE)
    cand = [f for f in files if pat.search(f)]
    if not cand:
        raise RuntimeError(f"{src.repo}: no file matching {src.filename_pattern!r} in the Hub's listing ({files})")
    order = {".parquet": 0, ".jsonl": 1, ".json": 2, ".csv": 3}
    return sorted(cand, key=lambda f: (order.get(Path(f).suffix.lower(), 9), f))[0]


def load_text_manifest(text_dir: Path = TEXT_EXTERNAL_DIR) -> dict:
    p = Path(text_dir) / DOWNLOAD_MANIFEST_NAME
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@dataclass
class TextFetchReport:
    fetched: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    entries: list = field(default_factory=list)
    manifest: dict = field(default_factory=dict)
    dry_run_lines: list = field(default_factory=list)


def _download(url: str, dest: Path, *, fetch: TextFetcher) -> tuple[int, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    h = hashlib.sha256()
    n = 0
    with fetch.stream(url) as resp, open(part, "wb") as out:
        for chunk in iter(lambda: resp.read(1 << 20), b""):
            out.write(chunk)
            h.update(chunk)
            n += len(chunk)
    part.replace(dest)
    return n, h.hexdigest()


def fetch_text(keys: Iterable[str] = tuple(TEXT_SOURCES), *, approved_by: Optional[str], fetch: TextFetcher,
               text_dir: Path = TEXT_EXTERNAL_DIR, force: bool = False, dry_run: bool = False,
               now_fn: Callable[[], str] = utc_now, git_sha: Optional[str] = None,
               sources: Optional[Mapping[str, TextSource]] = None,
               sources_manifest_path: Optional[Path] = None) -> TextFetchReport:
    """Download the text corpora (see the module docstring).  Refused before any request (:class:`NotApproved`) for a
    source with no recorded approval unless ``approved_by`` names Roger's go (a dry run makes no request and prints
    what it would fetch without it)."""
    S = dict(sources or TEXT_SOURCES)  # noqa: N806
    keys = list(keys)
    unknown = [k for k in keys if k not in S]
    if unknown:
        raise KeyError(f"unknown text source(s): {', '.join(unknown)} (known: {', '.join(S)})")
    unapproved = [k for k in keys if S[k].approval is None and not (approved_by or "").strip()]
    if unapproved and not dry_run:              # a dry run makes no request
        raise NotApproved(f"{', '.join(unapproved)}: no approval on record for this download (about 260 MB in all); "
                          f"fetch it only after Roger's go, naming it with --approved-by '<Roger, date>' (plan 05 "
                          f"open decision 2)")
    root = Path(text_dir)
    rep = TextFetchReport()
    if dry_run:
        for k in keys:
            s = S[k]
            rep.dry_run_lines.append(f"{k}: {s.repo} ({s.filename or 'file from the Hub listing'}; {s.size_note}; "
                                     f"{s.licence}) -> {root / k}/")
        return rep
    prev = load_text_manifest(root)
    entries = {e["key"]: e for e in prev.get("entries") or []}
    for k in keys:
        s = S[k]
        fn = resolve_filename(s, fetch=fetch)
        dest = root / k / Path(fn).name
        old = entries.get(k)
        if dest.exists() and not force and old and old.get("sha256") and old.get("file") == f"{k}/{dest.name}":
            rep.skipped.append(k)
            continue
        url = s.url(fn)
        n, sha = _download(url, dest, fetch=fetch)
        entries[k] = {"key": k, "repo": s.repo, "file": f"{k}/{dest.name}", "url": url, "size_bytes": n,
                      "sha256": sha, "hash_source": "received bytes", "field": s.field, "licence": s.licence,
                      "licence_url": s.licence_url, "what": s.what, "approval": s.approval or approved_by,
                      "downloaded_at": now_fn(), "tool": TOOL, "git_sha": git_sha}
        rep.fetched.append(k)
    rep.entries = [entries[k] for k in sorted(entries)]
    doc = {"tool": TOOL, "entries": rep.entries, "total_bytes": sum(int(e.get("size_bytes") or 0)
                                                                     for e in rep.entries),
           "note": "decision 2 (Roger, 2026-10-14): the text corpora in the first build; deletable after "
                   "extraction (extract-text --delete-raw), the hashes kept here"}
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", root / DOWNLOAD_MANIFEST_NAME)
    rep.manifest = doc
    if sources_manifest_path is not None:
        from .books import update_sources_manifest
        update_sources_manifest(sources_manifest_path, "text", doc)
    return rep


__all__ = ["TEXT_TYPES", "TEXT_FRAME_FLOOR", "INTENSIFIERS", "EXCLUDED", "TEXT_PERSON_NOUNS", "TextFrameSpec",
           "TextFrame", "TEXT_FRAME_SPECS", "TextSource", "TEXT_SOURCES", "text_frames", "text_bank_sha256",
           "clean_text", "sentences", "item_filler", "frame_fillers", "TextExtract", "extract_frames",
           "read_documents", "extract_dir", "write_text_extract", "read_text_extract", "run_extract",
           "text_extract_paths", "TextFetcher", "HttpTextFetcher", "resolve_filename", "load_text_manifest",
           "fetch_text", "TextFetchReport", "NotApproved"]
