"""Fixtures for the structural generators' tests (coding_plan_09 section 8): a toy corpus with pairs, a triangle, a
sequence, a ``non-X`` singleton, a renamed trait and a standard-labelled pair; a seed queue with every status; a
corpus-regions file with principal-target traits; a registry with decided and undecided rows of other generators;
a fake OEWN lexicon; reply builders; and a scripted Anthropic client keyed by the rendered prompt's hash, so that a
changed prompt fails loudly."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional

from assistant_axis.gapgen.generators.base_model.parse import Lexicon
from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

#: stem -> (positive_label, negative_label, arrangement, description)
TRAITS: dict[str, tuple] = {
    "brave": ("brave", "timid", {"kind": "pair", "members": ["brave", "timid"]},
              "This means facing danger and pain without backing away."),
    "timid": ("timid", "brave", {"kind": "pair", "members": ["brave", "timid"]},
              "This means shrinking from risk, strangers and anything new."),
    "honest": ("honest", "dishonest", {"kind": "pair", "members": ["dishonest", "honest"]},
               "This means saying what is true and leaving no false impression."),
    "dishonest": ("dishonest", "honest", {"kind": "pair", "members": ["dishonest", "honest"]},
                  "This means lying and misleading whenever it pays."),
    "gloomy": ("gloomy", "non-gloomy", {"kind": "singleton"}, "This means expecting the worst and seeing little joy."),
    "zealous": ("zealous", "apathetic", None, "This means throwing oneself into a cause with fervor."),
    "callous": ("callous", "non-callous", {"kind": "triangle", "members": ["callous", "compassionate", "malicious"]},
                "This means being unmoved by others' pain."),
    "compassionate": ("compassionate", "non-compassionate",
                      {"kind": "triangle", "members": ["callous", "compassionate", "malicious"]},
                      "This means feeling others' pain and wanting to ease it."),
    "malicious": ("malicious", "non-malicious",
                  {"kind": "triangle", "members": ["callous", "compassionate", "malicious"]},
                  "This means wanting others to suffer and acting to make it happen."),
    "selfish": ("selfish", "non-selfish", {"kind": "sequence", "members": ["selfish", "clannish", "humanitarian"]},
                "This means caring only for oneself."),
    "clannish": ("clannish", "non-clannish", {"kind": "sequence", "members": ["selfish", "clannish", "humanitarian"]},
                 "This means caring only for one's own group."),
    "humanitarian": ("humanitarian", "non-humanitarian",
                     {"kind": "sequence", "members": ["selfish", "clannish", "humanitarian"]},
                     "This means caring for all people alike."),
    "dependable": ("dependable", "non-dependable", {"kind": "singleton"},
                   "This means doing what one said one would, every time."),
    "careful_hexaco": ("careful (HEXACO)", "careless (HEXACO)",
                       {"kind": "pair", "members": ["careful_hexaco", "careless_hexaco"]},
                       "This means planning ahead and checking one's work."),
    "careless_hexaco": ("careless (HEXACO)", "careful (HEXACO)",
                        {"kind": "pair", "members": ["careful_hexaco", "careless_hexaco"]},
                        "This means acting on impulse and leaving mistakes in."),
    "obedient": ("obedient", "rebellious", {"kind": "pair", "members": ["obedient", "rebellious"]},
                 "This means doing what one is told by those in charge."),
    "rebellious": ("rebellious", "obedient", {"kind": "pair", "members": ["obedient", "rebellious"]},
                   "This means resisting whoever is in charge."),
}
RENAMED = {"dependable": {"stem": "trusty_old", "date": "2026-09-01", "reason": "test"}}
#: stem -> (region, alignment_score)
REGIONS = {"obedient": ("alignment_ai_agent", 3), "rebellious": ("alignment_ai_agent", 3),
           "honest": ("moral_stance", 3), "dishonest": ("moral_stance", 2), "callous": ("moral_stance", 1)}
QUEUE = [
    {"stem": "plucky", "label": "plucky", "entity_type": "trait", "status": "backlog"},
    {"stem": "mettlesome", "label": "mettlesome", "entity_type": "trait", "status": "paired"},
    {"stem": "brave", "label": "brave", "entity_type": "trait", "status": "paired"},
    {"stem": "rash", "label": "rash", "entity_type": "trait", "status": "not_adopted"},
    {"stem": "callous", "label": "callous", "entity_type": "trait", "status": "not_adopted"},
    {"stem": "spunky", "label": "spunky", "entity_type": "trait", "status": "candidate"},
    {"stem": "doughty", "label": "doughty", "entity_type": "trait", "status": "done"},
    {"stem": "valiant", "label": "Valiant", "entity_type": "trait", "status": "superseded"},
    {"stem": "warrior", "label": "warrior", "entity_type": "role", "status": "backlog"},
]
LEXICON = Lexicon(adjectives=frozenset({"brave", "timid", "stubborn", "rash", "harsh", "generous", "careful",
                                        "careless", "lax", "reckless", "craven", "dauntless", "organized"}),
                  nouns=frozenset({"bravery", "stubbornness", "rashness"}))


def write_corpus(root: Path, traits: Optional[Mapping] = None) -> Path:
    """``root/data`` with the toy trait files, the regions file and the queue; returns the data dir."""
    data = Path(root) / "data"
    tdir = data / "traits" / "instructions"
    tdir.mkdir(parents=True, exist_ok=True)
    for stem, (label, neg, arr, desc) in (traits or TRAITS).items():
        doc = {"positive_label": label, "negative_label": neg, "description": desc, "instruction": []}
        if arr is not None:
            doc["arrangement"] = arr
        if stem in RENAMED:
            doc["renamed_from"] = RENAMED[stem]
        (tdir / f"{stem}.json").write_text(json.dumps(doc), encoding="utf-8")
    (data / "seed_queue.json").write_text(json.dumps({"_meta": {}, "entries": QUEUE}), encoding="utf-8")
    cdir = data / "candidates"
    cdir.mkdir(parents=True, exist_ok=True)
    regions = {s: {"label": s, "region": REGIONS.get(s, ("cognitive_epistemic", 0))[0],
                   "alignment_score": REGIONS.get(s, ("cognitive_epistemic", 0))[1]} for s in (traits or TRAITS)}
    (cdir / "corpus_regions.json").write_text(json.dumps({"result": regions, "_provenance": {}}), encoding="utf-8")
    return data


def registry_row(stem: str, generator: str, *, verdict: Optional[str] = None, decision: Optional[str] = None,
                 review: str = "unreviewed", run_id: str = "r1") -> dict:
    row = {"schema_version": 1, "key": f"{stem}#1", "stem": stem, "sense_id": 1, "surface": stem, "label": stem,
           "sources": [{"generator": generator, "run_id": run_id, "surface": stem, "source_ref": None}],
           "filter": {"verdict": verdict} if verdict else None,
           "novelty": {"decision": decision} if decision else None,
           "review": {"status": review}, "rev": 1}
    return row


def write_registry(path: Path, rows) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def item(label: str, gloss: Optional[str] = None, *, common: bool = True, polysemy: bool = False) -> dict:
    return {"label": label, "gloss": gloss or f"This means acting {label.lower()} in daily life.",
            "has_common_word": common, "polysemy": polysemy}


def reply(position: str = "mean", *, opposite=None, excess=None, deficiency=None, retarget=None, remode=None,
          principal: bool = False, reasoning: str = "Reasoned first.") -> str:
    targets = O.TARGETS + (O.PRINCIPAL_TARGETS if principal else ())
    rt = {t: None for t in targets}
    rt.update(retarget or {})
    rm = {m: None for m in O.MODES}
    rm.update(remode or {})
    return json.dumps({"reasoning": reasoning, "position": position, "opposite": opposite, "excess": excess,
                       "deficiency": deficiency, "retarget": rt, "remode": rm})


class ScriptedClient(FakeAsyncAnthropic):
    """Answers by the rendered prompt's hash (system and user turn); an unscripted prompt raises, loudly.  A list
    of texts is answered in turn (a retry gets the next one)."""

    def __init__(self, scripts: Mapping[str, object], *, input_tokens: int = 1500, output_tokens: int = 600):
        self.scripts = {k: (list(v) if isinstance(v, list) else [v]) for k, v in scripts.items()}
        self.seen: list[str] = []

        def responder(kw):
            key = O.prompt_sha256(system_text(kw), user_text(kw))
            self.seen.append(key)
            if key not in self.scripts:
                raise AssertionError(f"unscripted prompt (a changed prompt?): {user_text(kw)[:200]}")
            q = self.scripts[key]
            text = q.pop(0) if len(q) > 1 else q[0]
            if isinstance(text, BaseException):
                return text
            return make_response(text, input_tokens=input_tokens, output_tokens=output_tokens)
        super().__init__(responder)


def script_for(inputs, system: str, answers: Mapping[str, object]) -> dict:
    """``{prompt sha: answer}`` for the inputs whose stem has an answer."""
    by = {ti.stem: ti for ti in inputs}
    return {O.prompt_sha256(system, O.render_operator_user(by[s])): a for s, a in answers.items() if s in by}
