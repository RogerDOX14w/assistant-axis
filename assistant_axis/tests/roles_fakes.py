"""Fakes for the roles pass's tests (coding plan 16, § 8): registry rows of the three role shapes, a fake Anthropic
responder for the stage (role gloss, role kind) and for M3's role calls (relation over ``roles``, overlap
``target``/``other``), and a ten-role fixture corpus.  No network, no key."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.registry import new_record
from assistant_axis.tests.fake_anthropic import make_response, system_text, user_text

#: A ten-role fixture corpus: stem -> (description, arrangement).  ``predator`` / ``prey`` and ``guardian`` /
#: ``destroyer`` are recorded pairs (they expand); ``doctor`` is the parent of the sub-role ``cardiologist``;
#: ``devils_advocate`` shows its display override.  ``default`` is in the directory and must be left out.
ROLE_CORPUS: dict[str, tuple[str, Optional[dict]]] = {
    "doctor": ("A doctor is a physician who examines patients, works out what is wrong with them, and treats it.", None),
    "nurse": ("A nurse is someone who cares for patients on a ward, giving medicines and watching their condition.", None),
    "pilot": ("A pilot is someone who flies aircraft, from the preflight checks to the landing.", None),
    "predator": ("A predator is an animal that hunts and kills other animals for food.",
                 {"kind": "pair", "members": ["predator", "prey"]}),
    "prey": ("A prey is an animal that is hunted and eaten by other animals.", {"kind": "pair", "members": ["predator", "prey"]}),
    "guardian": ("A guardian is someone who protects others from harm, standing between them and danger.",
                 {"kind": "pair", "members": ["destroyer", "guardian"]}),
    "destroyer": ("A destroyer is someone who tears things down, wrecking what others have built.",
                  {"kind": "pair", "members": ["destroyer", "guardian"]}),
    "judge": ("A judge is someone who weighs evidence in court and hands down impartial rulings.", None),
    "devils_advocate": ("A devil's advocate is someone who argues the side nobody else will take, to test an idea.", None),
    "optimist": ("An optimist is someone who expects things to turn out well whatever happens.", None),
}
#: Their kinds, as role_kinds.json would record them.
ROLE_KINDS: dict[str, str] = {"doctor": "occupation", "nurse": "occupation", "pilot": "occupation",
                              "predator": "non_human", "prey": "non_human", "guardian": "stance",
                              "destroyer": "stance", "judge": "occupation", "devils_advocate": "stance",
                              "optimist": "temperament"}


def write_role_corpus(data_dir: Path, *, with_default: bool = True, kinds: bool = True,
                      renamed: Optional[Mapping[str, str]] = None) -> Path:
    """The fixture corpus under ``<data_dir>/roles/instructions`` (and ``role_kinds.json`` beside it)."""
    d = Path(data_dir) / "roles" / "instructions"
    d.mkdir(parents=True, exist_ok=True)
    for stem, (desc, arr) in ROLE_CORPUS.items():
        doc = {"description": desc, "arrangement": arr or {"kind": "singleton"}}
        if renamed and stem in renamed:
            doc["renamed_from"] = {"stem": renamed[stem], "date": "2026-10-01", "reason": "test"}
        (d / f"{stem}.json").write_text(json.dumps(doc), encoding="utf-8")
    if with_default:
        (d / "default.json").write_text(json.dumps({"description": "You are an AI assistant.",
                                                    "arrangement": {"kind": "singleton"}}), encoding="utf-8")
    if kinds:
        (Path(data_dir) / "roles" / "role_kinds.json").write_text(json.dumps(
            {"prompt_sha256": "11b559f0cff50189", "roles": {s: {"kind": k} for s, k in ROLE_KINDS.items()}}),
            encoding="utf-8")
    return Path(data_dir)


def held_row(surface: str, reading: Optional[str], *, gen: str = "censuses", tags=("role_person",)) -> dict:
    """A row M1 put on the roles list (plain key, ``entity_type: "role"``, ``holding: "roles"``)."""
    r = new_record(surface, sources=[{"generator": gen, "run_id": "2026-10-08-pilot", "rank": 1, "score": None,
                                      "source_ref": None, "gloss_hint": None, "partner_hint": None,
                                      "surface": surface}])
    r["filter"] = {"pipeline": "split", "verdict": "tagged", "outcome": "roles", "tags": list(tags),
                   "judged_sense": reading, "accepted_reading": 1 if reading else None,
                   "sense": {"readings": [{"reading": reading, "rank": "primary"}]} if reading else None}
    r["gloss"], r["holding"], r["entity_type"] = None, "roles", "role"
    return r


def aimed_row(surface: str, reading: Optional[str], *, route: str = "role", kind_guess: str = "occupation",
              gen: str = "professions") -> dict:
    """A role-aimed row a generator submitted in role mode (``stem|R#1``) after M1 routed it."""
    r = new_record(surface, entity_type="role",
                   sources=[{"generator": gen, "run_id": "w1", "rank": 1, "score": None, "source_ref": f"soc:{surface}",
                             "gloss_hint": None, "partner_hint": None, "surface": surface, "kind_guess": kind_guess,
                             "human": kind_guess != "non_human"}])
    r["filter"] = {"pipeline": "split", "verdict": "tagged" if route == "role" else "trait",
                   "outcome": "roles" if route == "role" else "trait", "tags": ["role_person"] if route == "role" else [],
                   "judged_sense": reading, "accepted_reading": 1, "role_route": route, "routes_version": 1,
                   "sense": {"readings": [{"reading": reading, "rank": "primary"}]}}
    r["gloss"], r["holding"] = None, None
    return r


def trait_row(surface: str = "plucky") -> dict:
    r = new_record(surface)
    r["filter"] = {"verdict": "trait", "outcome": "trait", "tags": [], "alignment": 1, "region": "moral_stance"}
    r["gloss"] = f"This means being {surface}."
    return r


def gloss_for(label: str, reading: Optional[str]) -> str:
    art = "An" if label[:1].lower() in "aeiou" else "A"
    return f"{art} {label} is someone who {reading or 'does what a ' + label + ' does'}."


def stage_responder(*, kinds: Optional[Mapping[str, list]] = None, bad_gloss=(), bad_gloss_once=(), bad_kind=(),
                    seen: Optional[dict] = None, fallback=None):
    """Answers the role gloss call with :func:`gloss_for` (``bad_gloss``: never parses; ``bad_gloss_once``: the
    first call does not) and the role kind call with ``kinds[label]`` in turn (one kind per reading, cycling;
    default ``occupation``; ``bad_kind``: never parses).  ``seen`` counts calls by (step, label).  Any other call
    goes to ``fallback``."""
    kinds = dict(kinds or {})
    seen = seen if seen is not None else {}
    gloss_sys, kind_sys = sr.load_prompt("role_gloss"), sr.load_prompt("role_kind")

    def answer(kw):
        s = system_text(kw)
        if s == gloss_sys:
            obj = json.loads(user_text(kw))
            label = obj["label"]
            n = seen[("role_gloss", label)] = seen.get(("role_gloss", label), 0) + 1
            if label in bad_gloss or (label in bad_gloss_once and n == 1):
                return make_response("I would rather not.", input_tokens=650, output_tokens=5)
            return make_response(json.dumps({"results": [{"id": 1, "gloss": gloss_for(label, obj["reading"])}]}),
                                 input_tokens=650, output_tokens=90)
        if s == kind_sys:
            u = user_text(kw)
            label = u.split("\n", 1)[0][len("Role: "):]
            n = seen[("role_kind", label)] = seen.get(("role_kind", label), 0) + 1
            if label in bad_kind:
                return make_response("hmm", input_tokens=900, output_tokens=5)
            ks = kinds.get(label) or ["occupation"]
            k = ks[(n - 1) % len(ks)]
            return make_response(json.dumps({"reason": f"{label} is a {k}.", "kind": k}), input_tokens=900,
                                 output_tokens=120)
        if fallback is not None:
            return fallback(kw)
        raise AssertionError(f"unexpected call: {s[:80]!r}")
    return answer


def role_m3_responder(relations: Optional[Mapping] = None, overlap: Optional[Mapping] = None, *,
                      default_rel: str = "unrelated", default_overlap=1):
    """M3's role calls: the relation call (``{"candidate", "roles": [...]}``) from ``relations[(candidate, role)]``;
    the overlap call (``{"target", "other"}``) from ``overlap[(target, other, "sonnet"|"opus")]`` or
    ``overlap[(target, other)]``."""
    relations, overlap = dict(relations or {}), dict(overlap or {})

    def responder(kw):
        obj = json.loads(user_text(kw))
        model = kw["model"]
        fam = "opus" if "opus" in model else ("sonnet" if "sonnet" in model else "haiku")
        if "candidate" in obj:
            listed = obj.get("roles") if "roles" in obj else obj["traits"]
            c = obj["candidate"]["label"]
            rows = [{"id": t["id"], "reason": "r", "relation": relations.get((c, t["label"]), default_rel)}
                    for t in listed]
            return make_response(json.dumps({"results": rows}), input_tokens=1200, output_tokens=400)
        c, o = obj["target"]["label"], obj["other"]["label"]
        v = overlap.get((c, o, fam), overlap.get((c, o), default_overlap))
        return make_response(json.dumps({"reason": f"{fam} on {o}", "similarity": v}), input_tokens=150,
                             output_tokens=80, cache_read=600)
    return responder
