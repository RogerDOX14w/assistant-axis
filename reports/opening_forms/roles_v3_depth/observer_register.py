"""Observer register in the role rubric V3's output (W1 part 2, 2026-10-09): no API calls.

Reads the role audit's existing judgements (Sonnet 4.6 fault judge, blind) and
the files they judged, and breaks the "observer_register" fault down by the
opening of the flagged instruction (``audit_role_instructions.role_opening_form``)
and by whether the instruction carries a relative clause on the role noun
("a ... who ...", "whose").  Arms: the development sample's corpus and V3 draft,
the held-out set's corpus and regeneration, and the whole current corpus
(``judged/final``, every role file, checked to be the judged content).  Run from
the repo root:

    uv run python reports/opening_forms/roles_v3_depth/observer_register.py

Writes observer_register.json beside this file.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import audit_role_instructions as A  # noqa: E402
from data_analysis import audit_trait_instructions as T  # noqa: E402

P = Path("reports/role_rubric_v3_pilot")
ARMS = {   # arm -> (judged dir, the files it judged)
    "dev_corpus": (P / "judged/corpus", P / "stage/dev/corpus"),
    "dev_v3": (P / "judged/v3", P / "stage/dev/v3"),
    "held_corpus": (P / "judged/held_corpus", P / "stage/held_out/held_corpus"),
    "held_final": (P / "judged/held_final", P / "stage/held_out/held_final"),
    "final_all": (P / "judged/final", Path("data/roles/instructions")),
}
OUT = Path(__file__).resolve().parent / "observer_register.json"
# a relative clause in the opening sentence: "a pilgrim who ...", "a virtuoso whose ..."
RELATIVE = re.compile(r"^[^.;:]*?\b(?:who|whose)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def instructions(arm: str):
    judged_dir, src = ARMS[arm]
    for p in sorted(judged_dir.glob("*.json")):
        doc = json.loads((src / p.name).read_text(encoding="utf-8"))
        j = json.loads(p.read_text(encoding="utf-8"))
        if j["content_sha256"] != T.content_sha256(doc):
            raise SystemExit(f"{arm}/{p.stem}: judgement is not of the file on disk")
        for item, pair in zip(j["instruction_judge"]["items"], doc["instruction"]):
            text = " ".join(pair["pos"].split())
            quote = item["quotes"].get("observer_register")
            yield {"stem": p.stem, "id": item["id"], "text": text, "form": A.role_opening_form(text),
                   "relative": bool(RELATIVE.match(text)), "words": len(text.split()),
                   "observer": "observer_register" in item["faults"], "quote": quote,
                   # the judge sometimes quotes the description instead of the instruction
                   "quote_in_text": bool(quote) and norm(quote) in norm(text),
                   "quote_in_description": bool(quote) and norm(quote) in norm(doc.get("description", "")),
                   "position": item["id"],
                   "other_faults": [f for f in item["faults"] if f != "observer_register"]}


def tally(rows: list[dict], key, flag) -> dict:
    d = defaultdict(lambda: [0, 0])
    for r in rows:
        d[str(key(r))][0] += flag(r)
        d[str(key(r))][1] += 1
    return {k: {"flagged": v[0], "of": v[1], "rate": round(100 * v[0] / v[1], 1)}
            for k, v in sorted(d.items(), key=lambda kv: (-kv[1][1], kv[0]))}


def real(r: dict) -> bool:
    """A flag whose quote is in the instruction itself (not one quoting the description)."""
    return r["observer"] and r["quote_in_text"]


def summary(rows: list[dict]) -> dict:
    by_form = defaultdict(lambda: [0, 0])
    by_rel = defaultdict(lambda: [0, 0])
    by_form_rel = defaultdict(lambda: [0, 0])
    for r in rows:
        for d, k in ((by_form, r["form"]), (by_rel, r["relative"]), (by_form_rel, f"{r['form']} | relative={r['relative']}")):
            d[k][0] += r["observer"]
            d[k][1] += 1
    per_file = Counter(r["stem"] for r in rows if r["observer"])
    flagged = [r for r in rows if r["observer"]]
    return {
        "instructions": len(rows), "flagged": len(flagged), "rate": round(100 * len(flagged) / len(rows), 2),
        "files": len({r["stem"] for r in rows}), "files_with_one_or_more": len(per_file),
        "files_with_two_or_more": sorted(s for s, n in per_file.items() if n >= 2),
        "flag_quote_not_in_instruction": sum(not r["quote_in_text"] for r in flagged),
        "flag_quote_from_description": sum(r["quote_in_description"] and not r["quote_in_text"] for r in flagged),
        "by_form": {k: {"flagged": v[0], "of": v[1], "rate": round(100 * v[0] / v[1], 1)}
                    for k, v in sorted(by_form.items(), key=lambda kv: -kv[1][1])},
        "by_relative_clause": {str(k): {"flagged": v[0], "of": v[1], "rate": round(100 * v[0] / v[1], 1)}
                               for k, v in by_rel.items()},
        "by_form_and_relative": {k: {"flagged": v[0], "of": v[1], "rate": round(100 * v[0] / v[1], 1)}
                                 for k, v in sorted(by_form_rel.items())},
        "real_flags": sum(real(r) for r in rows),
        "real_rate": round(100 * sum(real(r) for r in rows) / len(rows), 2),
        "files_with_two_or_more_real": sorted(s for s, n in Counter(r["stem"] for r in rows if real(r)).items() if n >= 2),
        "real_by_form": tally(rows, lambda r: r["form"], real),
        "real_by_relative_clause": tally(rows, lambda r: r["relative"], real),
        "all_flags_by_position": tally(rows, lambda r: r["position"], lambda r: r["observer"]),
        "description_quotes_by_position": tally(rows, lambda r: r["position"],
                                                lambda r: r["observer"] and not r["quote_in_text"]),
        "form_by_position": {pos: dict(Counter(r["form"] for r in rows if r["position"] == pos))
                             for pos in sorted({r["position"] for r in rows})},
        "mean_words": {"flagged": round(sum(r["words"] for r in flagged) / max(1, len(flagged)), 1),
                       "all": round(sum(r["words"] for r in rows) / len(rows), 1)},
    }


def main() -> None:
    out = {"note": "observer_register flags of the role audit's fault judge (Sonnet 4.6, blind), by opening form "
                   "and relative clause; rates in percent of instructions", "arms": {}}
    rows_by_arm = {arm: list(instructions(arm)) for arm in ARMS}
    for arm, rows in rows_by_arm.items():
        out["arms"][arm] = summary(rows)
    final = rows_by_arm["final_all"]
    out["final_all_flagged"] = [{k: r[k] for k in ("stem", "id", "form", "relative", "quote", "quote_in_text", "quote_in_description", "text")}
                                for r in final if r["observer"]]
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for arm, s in out["arms"].items():
        print(f"\n== {arm}: {s['flagged']} of {s['instructions']} ({s['rate']}%), files {s['files_with_one_or_more']} of "
              f"{s['files']}, two or more: {len(s['files_with_two_or_more'])} {s['files_with_two_or_more']}; quote not in "
              f"the instruction {s['flag_quote_not_in_instruction']} (from the description {s['flag_quote_from_description']}); "
              f"words flagged {s['mean_words']['flagged']} vs {s['mean_words']['all']}")
        for k, v in s["by_form"].items():
            print(f"   {k:28s} {v['flagged']:3d} / {v['of']:4d}  {v['rate']:5.1f}%")
        print("   relative clause:", s["by_relative_clause"])
        print(f"   REAL (quote in the instruction): {s['real_flags']} ({s['real_rate']}%), files two or more: "
              f"{s['files_with_two_or_more_real']}")
        for k, v in s["real_by_form"].items():
            print(f"      {k:28s} {v['flagged']:3d} / {v['of']:4d}  {v['rate']:5.1f}%")
        print("      who/whose clause:", {k: (v["flagged"], v["of"], v["rate"]) for k, v in s["real_by_relative_clause"].items()})
        print("   all flags by position:", {k: v["flagged"] for k, v in s["all_flags_by_position"].items()},
              " description quotes by position:", {k: v["flagged"] for k, v in s["description_quotes_by_position"].items()})
        print("   form by position:", {k: max(v, key=v.get) + f" {max(v.values())}/{sum(v.values())}" for k, v in s["form_by_position"].items()})
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
