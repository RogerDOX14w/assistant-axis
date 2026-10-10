"""Shared fakes for the base-model generator tests: a small census table, a WikiBio archive built in the test's
tmp dir (same layout as the real ``wikipedia-biography-dataset.zip``), an O*NET occupation file, a fake
lexicon / OEWN, a fake sampling backend.  No network, no model."""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from assistant_axis.gapgen.generators.censuses.glosshint import Sense
from assistant_axis.gapgen.generators.censuses.ingest import TableRow

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "base_model"
CENSUS_TABLE_SMALL = FIXTURES / "census_table_small.jsonl"
ONET_SMALL = FIXTURES / "onet_small.csv"
SAMPLES_SMALL = FIXTURES / "samples_small.jsonl"

#: (surface, prop, definition): TDA rows of the small census table, in rank order.
TDA_WORDS = [
    ("brave", 0.98, "possessing or displaying courage"),
    ("lazy", 0.98, "moving slowly and gently"),
    ("stubborn", 0.88, "tenaciously unwilling or marked by tenacious unwillingness to yield"),
    ("blunt", 0.86, "characterized by directness in manner or speech"),
    ("gentle", 0.84, "soft and mild; not harsh or stern or severe"),
    ("brash", 0.62, "offensively bold"),
    ("bumptious", 0.52, "offensively self-assertive"),
    ("brusque", 0.51, "rudely abrupt or blunt in speech or manner"),
    ("fey", 0.31, "slightly insane"),
    ("hidebound", 0.22, "stubbornly conservative and narrow-minded"),
]


def census_rows() -> list[TableRow]:
    rows = []
    for i, (w, prop, defn) in enumerate(TDA_WORDS, 1):
        rows.append(TableRow(
            schema_version=1, surface=w, stem=w, label=w, allport=None, in_merged=None,
            tda={"row": 100 + i, "prop": prop, "n": 80, "gbooks_freq": -0.1, "gn1710": True, "sg435": False,
                 "bffm100": False, "n_rows": 1},
            zipf=3.0, freq_hard_reject=False, freq_probe_band=False, freq_rescue=None, freq_platform=None,
            wordnet={"found": True, "n_adj_senses": 1, "person_sense_rank": 1, "definition": defn, "pos": "a"},
            gloss_hint=defn, repaired_from=None, unknown_word=False, eligible=True, ineligible_reason=None,
            stage="tda", rank=i, score=prop, corpus_stem_match=False, queue_stem_match=False))
    # an Allport-only row (never a seed) and a malformed row
    rows.append(TableRow(
        schema_version=1, surface="agitated", stem="agitated", label="agitated",
        allport={"columns": ["II"], "raw": {"II": "agitated"}, "line": {"II": 2}}, in_merged=True, tda=None,
        zipf=3.0, freq_hard_reject=False, freq_probe_band=False, freq_rescue=None, freq_platform=None,
        wordnet=None, gloss_hint=None, repaired_from=None, unknown_word=False, eligible=True,
        ineligible_reason=None, stage="allport_hi", rank=len(TDA_WORDS) + 1, score=None,
        corpus_stem_match=False, queue_stem_match=False))
    rows.append(TableRow(
        schema_version=1, surface=None, stem=None, label="F.F.V", allport=None, in_merged=None,
        tda={"row": 1}, zipf=None, freq_hard_reject=None, freq_probe_band=None, freq_rescue=None,
        freq_platform=None, wordnet=None, gloss_hint=None, repaired_from=None, unknown_word=False, eligible=False,
        ineligible_reason="malformed", stage=None, rank=len(TDA_WORDS) + 2, score=None, corpus_stem_match=False,
        queue_stem_match=False))
    return rows


def census_table_text() -> str:
    return "".join(json.dumps(r.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n" for r in census_rows())


ONET_TEXT = (
    'O*NET-SOC Code,Title,Description\n'
    '11-1011.00,Chief Executives,"Determine and formulate policies and provide overall direction."\n'
    '15-1252.00,Software Developers,"Research, design, and develop computer and network software."\n'
    '29-1141.00,Registered Nurses,"Assess patient health problems and needs."\n'
    '35-2014.00,"Cooks, Restaurant","Prepare, season, and cook dishes."\n'
    '47-2111.00,Electricians,"Install, maintain, and repair electrical wiring."\n'
)

#: (title, infobox, sentences) of the fake WikiBio articles: tokenized and lowercased as the real ones are.
WIKIBIO_ARTICLES = [
    ("walter extra", "name_1:walter\tname_2:extra\tnationality_1:german",
     ["walter extra is a german award-winning aerobatic pilot , chief aircraft designer and founder of extra "
      "flugzeugbau -lrb- extra aircraft construction -rrb- , a manufacturer of aerobatic aircraft .",
      "extra was trained as a mechanical engineer ."]),
    ("aurelio lópez", "name_1:aurelio\tname_2:lópez",
     ["aurelio lópez rodríguez -lrb- 1948 -- 1992 -rrb- was a mexican professional baseball pitcher ."]),
    ("ada short", "article_title_1:ada\tarticle_title_2:short",
     ["ada short was a fictional test entry whose paragraph is long enough to keep , with several more words "
      "here to pass the floor ."]),
    ("tiny", "name_1:tiny", ["too short ."]),
]


def make_wikibio_zip(path: Path, articles: Sequence = WIKIBIO_ARTICLES, split: str = "train") -> Path:
    """A zip with the real archive's layout: ``wikipedia-biography-dataset/<split>/<split>.{id,box,nb,sent,title}``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    base = f"wikipedia-biography-dataset/{split if split != 'val' else 'valid'}/"
    stem = split if split != "val" else "valid"
    ids, boxes, nbs, sents, titles = [], [], [], [], []
    for i, (title, box, sentences) in enumerate(articles, 1):
        ids.append(str(i))
        boxes.append(box)
        nbs.append(str(len(sentences)))
        sents.extend(sentences)
        titles.append(title)
    with zipfile.ZipFile(path, "w") as z:
        for ext, lines in (("id", ids), ("box", boxes), ("nb", nbs), ("sent", sents), ("title", titles)):
            z.writestr(base + f"{stem}.{ext}", "".join(x + "\n" for x in lines))
    return path


#: The fake lexicon: adjectives and nouns as an OEWN-backed lookup would give them.
ADJECTIVES = frozenset({"stubborn", "kind", "generous", "curious", "sincere", "stupid", "hostile", "able",
                        "happy", "careless", "brave", "gentle", "blunt", "patient", "loyal", "quick-tempered",
                        "unflappable", "warm", "calm", "humble", "meticulous", "cold"})
NOUNS = frozenset({"stubbornness", "kindness", "generosity", "humility", "temper", "patience", "loyalty",
                   "cold", "pilot", "warmth", "ability"})
SENSES = {
    "stubborn": [Sense("tenaciously unwilling or marked by tenacious unwillingness to yield", "a")],
    "generous": [Sense("willing to give and share unstintingly", "a")],
    "unflappable": [Sense("not easily perturbed or excited or upset; marked by extreme calm and composure", "s")],
    "cold": [Sense("having a low or inadequate temperature", "a"),
             Sense("lacking the warmth of normal human feeling", "a")],
    "humility": [Sense("a disposition to be humble; a lack of false pride", "n")],
}
#: Per-word Zipf (unlisted: 0, i.e. unknown to wordfreq).
ZIPF = {"stubborn": 3.8, "kind": 5.0, "generous": 4.0, "curious": 4.1, "patient": 4.3, "loyal": 4.0, "quick": 4.9,
        "tempered": 2.6, "unflappable": 2.1, "warm": 4.6, "calm": 4.5, "humility": 3.3, "meticulous": 3.0,
        "cold": 4.9, "fiercely": 3.2, "careless": 3.5, "brave": 4.3, "gentle": 4.1, "blunt": 3.6,
        "rare": 4.0, "zorbish": 0.0, "listens": 3.4, "willing": 4.6, "listen": 4.9, "hidebound": 1.4,
        "humble": 3.9, "kindness": 3.9, "stubbornness": 2.6, "generosity": 3.3}


def fake_zipf(word: str) -> float:
    return ZIPF.get(word, 0.0)


@dataclass
class FakeGeneration:
    text: str
    n_prompt_tokens: int
    n_new_tokens: int
    stop_reason: str


@dataclass
class FakeBackend:
    """A ``SampleBackend``: returns scripted continuations (cycled), counts calls, can fail on a given call."""
    replies: Sequence[str] = ("stubborn, kind, generous, and fiercely loyal.\n\nNext paragraph",)
    model_id: str = "Qwen/Qwen3-8B-Base"
    batch_size: int = 4
    fail_on_call: Optional[int] = None
    calls: list = field(default_factory=list)

    def generate(self, prompts, *, temperature, top_p, min_p, max_new_tokens):
        self.calls.append({"n": len(prompts), "temperature": temperature, "top_p": top_p, "min_p": min_p,
                           "max_new_tokens": max_new_tokens})
        if self.fail_on_call is not None and len(self.calls) == self.fail_on_call:
            raise KeyboardInterrupt("simulated interruption")
        out = []
        for i, p in enumerate(prompts):
            r = self.replies[(len(self.calls) + i) % len(self.replies)]
            out.append(FakeGeneration(text=r, n_prompt_tokens=len(p.split()), n_new_tokens=len(r.split()),
                                      stop_reason="max_tokens"))
        return out


def write_text_fixtures() -> None:  # pragma: no cover - run by hand to regenerate the tracked fixtures
    FIXTURES.mkdir(parents=True, exist_ok=True)
    CENSUS_TABLE_SMALL.write_text(census_table_text(), encoding="utf-8")
    ONET_SMALL.write_text(ONET_TEXT, encoding="utf-8")


def zip_bytes(path: Path) -> bytes:
    return io.BytesIO(Path(path).read_bytes()).getvalue()
