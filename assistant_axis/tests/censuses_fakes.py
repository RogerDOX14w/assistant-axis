"""Shared fakes for the census generator tests: lookups standing in for ``wordfreq`` and OEWN,
a fake ``wn`` word index, the fixture files and a fake corpus.  No network, no model."""
from __future__ import annotations

import json
from pathlib import Path

from assistant_axis.gapgen.generators.censuses import ingest as I
from assistant_axis.gapgen.generators.censuses.glosshint import Sense

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "censuses"

#: Per-word Zipf, as ``gapgen.freq.zipf_info`` looks words up (unlisted words: 0).
WORD_ZIPF = {"kind": 5.0, "abandoned": 4.0, "accommodating": 3.0, "well": 6.0, "bred": 3.0, "risk": 5.0,
             "averse": 3.0, "flustered": 2.6, "agitated": 3.0, "gloomy": 3.0, "la": 4.0, "mode": 4.5, "a": 7.0,
             "sunny": 3.5, "sprightly": 2.0, "quaintish": 1.0, "rarish": 2.0}
#: Whole-surface Zipf (the unknown-word test).
SURFACE_ZIPF = {**WORD_ZIPF, "well-bred": 3.0, "risk-averse": 2.8, "a la mode": 3.0}
IN_WORDNET = {"kind", "abandoned", "accommodating", "well-bred", "flustered", "agitated", "gloomy", "a la mode",
              "sunny", "risk-averse", "quaintish", "rarish"}
SENSES = {
    "kind": [Sense("a category of things distinguished by some common characteristic", "n"),
             Sense("having or showing a tender and considerate and helpful nature", "a")],
    "flustered": [Sense("thrown into a state of agitated confusion", "s")],
    "agitated": [Sense("troubled emotionally and usually deeply", "a")],
    "a la mode": [Sense("in the current fashion or style", "s")],
    "sunny": [Sense("bright and pleasant", "a")],
    "gloomy": [Sense("depressingly dark", "s"), Sense("marked by melancholy and despondency", "s")],
}
LEMMAS = frozenset({"accommodating", "kind", "gloomy", "sunny", "agitated", "flustered"})


def fake_lookups(**over) -> I.Lookups:
    kw = dict(zipf=lambda s: SURFACE_ZIPF.get(s, 0.0), in_wordnet=lambda s: s in IN_WORDNET,
              senses=lambda s: list(SENSES.get(s, [])), adjective_lemmas=LEMMAS,
              zipf_word=lambda w: WORD_ZIPF.get(w, 0.0))
    kw.update(over)
    return I.Lookups(**kw)


def fixture_inputs():
    allport = []
    for col in ("I", "II", "III", "IV"):
        allport += I.parse_allport_txt(FIXTURES / f"allport_{col}.txt", col)
    merged = I.parse_allport_txt(FIXTURES / "allport_merged.txt", None)
    tda = I.parse_tda_properties(FIXTURES / "tda_properties_small.csv")
    return allport, merged, tda


def make_corpus(root: Path, traits=("risk_averse", "kind_to_animals", "kind", "gloomy"), queue=("flustered",)) -> Path:
    """A fake data dir: trait files and a seed queue."""
    d = root / "data"
    inst = d / "traits" / "instructions"
    inst.mkdir(parents=True, exist_ok=True)
    for t in traits:
        (inst / f"{t}.json").write_text(json.dumps({"positive_label": t.replace("_", " ")}))
    (d / "seed_queue.json").write_text(json.dumps({"entries": [
        *({"stem": q, "label": q, "entity_type": "trait", "status": "candidate"} for q in queue),
        {"stem": "dropped", "label": "dropped", "entity_type": "trait", "status": "not_adopted"}]}))
    return d


def fixture_table(tmp_path: Path, **kw):
    from assistant_axis.gapgen.generators.censuses.corpus import corpus_trait_stems, queue_trait_stems
    data = make_corpus(tmp_path)
    allport, merged, tda = fixture_inputs()
    rows, extra = I.build_table(allport, tda, lookups=fake_lookups(**kw), corpus_stems=corpus_trait_stems(data),
                                queue_stems=queue_trait_stems(data_dir=data), merged=merged)
    return rows, extra, data


class FakeSynset:
    def __init__(self, definition, pos):
        self._d, self.pos = definition, pos

    def definition(self):
        return self._d


class FakeSense:
    def __init__(self, definition, pos):
        self._s = FakeSynset(definition, pos)

    def synset(self):
        return self._s


class FakeWord:
    def __init__(self, pos, senses):
        self.pos = pos
        self._senses = [FakeSense(d, p) for d, p in senses]

    def senses(self):
        return self._senses


class FakeWordnet:
    """``words(form)`` over ``{form: [(word_pos, [(definition, synset_pos), ...]), ...]}``."""

    def __init__(self, index):
        self.index = index

    def words(self, form):
        return [FakeWord(pos, senses) for pos, senses in self.index.get(form, [])]
