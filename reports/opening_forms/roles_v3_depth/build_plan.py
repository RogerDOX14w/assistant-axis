"""Plan for the depth check of role rubric V3's own output (W1, 2026-10-09).

The earlier depth runs read the old corpus's instructions:
roles_depth (89 roles: its "Act as" instruction and one other drawn at random)
and roles_openings_depth (99 roles: the "Act as" text with the openings act_as,
from_now_on and be).  This plan reads the current (V3) instructions of the same
99 roles on the same 10 questions per role (the old corpus's own questions,
fixed in both earlier plans), so that the instruction is the only thing that
differs and every comparison is paired within role.

Variants of a role:
  v3_<class>  design "rotation": one of the role's five V3 instructions; the
              opening class rotates over the roles within each kind (good, bad,
              indifferent), so each class is read in about a fifth of them.
              This is the V3 sample; the V3 figures use these only.
  old_other   design "anchor": the old corpus instruction that roles_depth read
              as "other", asked again, so the old corpus can be compared with
              V3 in the same run and the drift since 2026-10-02 measured.
  v3_<class>  design "observer_extra" / "observer_control": for a role whose V3
              file has instructions the role audit flagged for observer register
              (the quote found in the instruction itself), every flagged
              instruction, and one unflagged one when the rotation drew a
              flagged instruction; for part 2, not in the V3 figures.

Run from the repo root:
    uv run python reports/opening_forms/roles_v3_depth/build_plan.py
"""
import json
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import audit_role_instructions as A  # noqa: E402

SEED = 20261009
OUT = Path(__file__).resolve().parent
OLD_DEPTH = Path("reports/opening_forms/roles_depth/plan.json")
OLD_OPENINGS = Path("reports/opening_forms/roles_openings_depth/plan.json")
KINDS = Path("reports/role_rubric_v3_pilot/sample100_kinds.json")
JUDGED = Path("reports/role_rubric_v3_pilot/judged/final")
ROLES = Path("data/roles/instructions")
CLASSES = ("from_now_on", "be", "youre", "become", "you_are")


def opening_class(text: str) -> str:
    f = A.role_opening_form(text)
    return {A.ROLE_FORM_FROM_NOW_ON: "from_now_on", A.ROLE_FORM_BE: "be", A.ROLE_FORM_YOURE: "youre",
            A.ROLE_FORM_BECOME: "become", A.ROLE_FORM_YOU_ARE_WHO: "you_are", A.ROLE_FORM_YOU_ARE: "you_are"}[f]


def norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def observer_flags(stem: str, doc: dict) -> dict[int, str]:
    """slot -> quote, for the instructions the audit flagged for observer register with a quote
    that is in the instruction (a quote from the description is the judge's mistake)."""
    j = json.loads((JUDGED / f"{stem}.json").read_text(encoding="utf-8"))
    out = {}
    for k, item in enumerate(j["instruction_judge"]["items"]):
        q = item["quotes"].get("observer_register")
        if q and norm(q) in norm(doc["instruction"][k]["pos"]):
            out[k] = q
    return out


def main() -> None:
    old_depth = json.loads(OLD_DEPTH.read_text(encoding="utf-8"))["traits"]
    old_open = json.loads(OLD_OPENINGS.read_text(encoding="utf-8"))["traits"]
    kinds = json.loads(KINDS.read_text(encoding="utf-8"))["kinds"]
    rng = random.Random(SEED)
    order = list(CLASSES)
    rng.shuffle(order)
    by_kind = {}
    for stem in old_open:
        by_kind.setdefault(kinds[stem], []).append(stem)
    drawn, i = {}, 0
    for kind in ("good", "bad", "indifferent"):
        stems = sorted(by_kind[kind])
        rng.shuffle(stems)
        for stem in stems:
            drawn[stem] = order[i % len(order)]
            i += 1
    plan = {"purpose": "depth of role rubric V3's own output (W1, 2026-10-09): one V3 instruction per role "
                       "(opening classes rotated within kind), the old corpus's 'other' instruction again as an "
                       "anchor, and the observer-flagged V3 instructions with a control, on the 10 questions of "
                       "the earlier depth runs",
            "entity": "role", "seed": SEED, "class_order": order,
            "sources": {"old_depth_plan": str(OLD_DEPTH), "old_openings_plan": str(OLD_OPENINGS),
                        "kinds": str(KINDS), "observer_judgements": str(JUDGED), "v3_files": str(ROLES)},
            "traits": {}}
    for stem, t in old_open.items():
        doc = json.loads((ROLES / f"{stem}.json").read_text(encoding="utf-8"))
        if " ".join(doc["description"].split()) != t["description"] or doc["eval_prompt"] != t["judge_prompt"]:
            raise SystemExit(f"{stem}: description or eval_prompt changed since the earlier runs")
        texts = [" ".join(x["pos"].split()) for x in doc["instruction"]]
        cls = [opening_class(x) for x in texts]
        if sorted(cls) != sorted(CLASSES):
            raise SystemExit(f"{stem}: V3 openings are {cls}")
        flags = observer_flags(stem, doc)

        def variant(k: int, design: str) -> dict:
            return {"name": f"v3_{cls[k]}", "text": doc["instruction"][k]["pos"], "slot": k,
                    "form": A.role_opening_form(texts[k]), "arm": "v3", "design": design,
                    "observer": k in flags, "observer_quote": flags.get(k)}

        k0 = cls.index(drawn[stem])
        variants = [variant(k0, "rotation")]
        if flags:
            variants += [variant(k, "observer_extra") for k in sorted(flags) if k != k0]
            if k0 in flags:
                unflagged = [k for k in range(5) if k not in flags]
                variants.append(variant(rng.choice(unflagged), "observer_control"))
        if stem in old_depth:
            o = next(v for v in old_depth[stem]["variants"] if v["name"] == "other")
            variants.append({"name": "old_other", "text": o["text"], "slot": o["slot"], "form": o["form"],
                             "arm": "anchor", "design": "anchor"})
        plan["traits"][stem] = {"label": t["label"], "description": t["description"], "entity": "role",
                                "judge_prompt": t["judge_prompt"], "kind": kinds[stem], "variants": variants,
                                "questions": t["questions"]}
    (OUT / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    from collections import Counter
    vs = [v for t in plan["traits"].values() for v in t["variants"]]
    n = sum(len(t["variants"]) * len(t["questions"]) for t in plan["traits"].values())
    print(f"{len(plan['traits'])} roles, {len(vs)} instructions, {n} answers")
    print("by design:", dict(Counter(v["design"] for v in vs)))
    print("rotation by class:", dict(Counter(v["name"] for v in vs if v["design"] == "rotation")))
    print("rotation by class and kind:", dict(Counter((v["name"], plan["traits"][s]["kind"]) for s, t in plan["traits"].items()
                                                      for v in t["variants"] if v["design"] == "rotation")))
    print("observer roles:", sorted(s for s, t in plan["traits"].items() if any(v.get("observer") for v in t["variants"])))


if __name__ == "__main__":
    main()
