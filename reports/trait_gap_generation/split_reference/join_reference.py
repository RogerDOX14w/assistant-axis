"""Reference join for the split filter: the rules of coding_plan_split.md section 6, applied to the
recorded answers of steps 1 to 3 (probe_rerun_wording/results.jsonl, 99 test words) and of the
same-sense check (probe_same_sense/results.jsonl, the 30 words with two trait readings).  No API
call.  Writes expected_outcomes.jsonl beside this file and prints the table by group.

    uv run python reports/trait_gap_generation/split_reference/join_reference.py
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "probe_rerun_wording" / "results.jsonl"
SAME = HERE.parent / "probe_same_sense" / "results.jsonl"
ON = {"trait", "membership"}
QUEUE = {"state": "states", "physical": "physical", "role": "roles"}


def join(sense: dict, same_sense: str | None = None) -> dict:
    """``sense`` is step 1's answer, each primary reading carrying ``check_established``,
    ``kind_call`` and (when it was asked) ``check_vague``.  ``same_sense`` is the same-sense
    check's answer for the word's two trait readings: "same", "shade", "different" or None."""
    primaries = [x for x in (sense.get("readings") or []) if x.get("rank") == "primary"]
    if not primaries:
        return {"outcome": "turned_away", "cause": "no_reading", "accepted": None, "notes": []}
    est = lambda x: (x.get("check_established") or {}).get("established")  # noqa: E731
    kind = lambda x: (x.get("kind_call") or {}).get("kind")  # noqa: E731
    survivors = [x for x in primaries if est(x) != "stretched"]
    if not survivors:
        return {"outcome": "turned_away", "cause": "stretched", "accepted": None, "notes": []}
    notes = []
    if survivors[0] is not primaries[0]:
        notes.append("most_likely_reading_stretched")
    first = survivors[0]
    on = [x for x in survivors if kind(x) in ON]
    if kind(first) in ON:
        accepted, outcome, cause = first, "trait", None
    elif on:
        accepted, outcome, cause = on[0], "trait", None
        notes.append("obvious_sense_not_trait")
    elif kind(first) in QUEUE:
        accepted, outcome, cause = first, QUEUE[kind(first)], None
    else:
        return {"outcome": "turned_away", "cause": kind(first), "accepted": None, "notes": notes}
    if outcome == "trait":
        if len(on) > 1 and same_sense == "different":
            notes.append("two_trait_senses")
        if any(kind(x) in QUEUE for x in survivors if x is not accepted) and "obvious_sense_not_trait" not in notes:
            notes.append("nontrait_person_sense")
    if (accepted.get("check_established") or {}).get("first_thought_in_the_way"):
        notes.append("first_thought_in_the_way")
    vague = accepted.get("check_vague") or {}
    for k in ("leaves_something_out", "fits_many_in_different_ways"):
        if vague.get(k):
            notes.append(k)
    return {"outcome": outcome, "cause": cause, "accepted": accepted["reading"], "kind": kind(accepted),
            "same_sense": same_sense if len(on) > 1 else None,
            "membership_kind": (accepted.get("kind_call") or {}).get("membership_kind"),
            "established": est(accepted), "vague_asked": bool(vague), "notes": notes}


def main() -> None:
    rows = [json.loads(line) for line in open(SRC, encoding="utf-8")]
    same = {d["word"]: d["relation"] for d in (json.loads(line) for line in open(SAME, encoding="utf-8"))}
    out, table = [], {}
    for r in rows:
        j = join(r["sense"], same.get(r["word"]))
        out.append({"word": r["word"], "group": r["group"], **j})
        table.setdefault(r["group"], Counter())[j["outcome"]] += 1
    with open(HERE / "expected_outcomes.jsonl", "w", encoding="utf-8") as fh:
        for o in out:
            fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    cols = ("trait", "states", "physical", "roles", "turned_away")
    print("| group | words | " + " | ".join(cols) + " |\n|---|---|" + "---|" * len(cols))
    for g, c in table.items():
        print(f"| {g} | {sum(c.values())} | " + " | ".join(str(c.get(k, 0)) for k in cols) + " |")
    tot = Counter(o["outcome"] for o in out)
    print(f"| all | {len(out)} | " + " | ".join(str(tot.get(k, 0)) for k in cols) + " |")
    print("causes of turning away:", dict(Counter(o["cause"] for o in out if o["outcome"] == "turned_away")))
    print("notes:", dict(Counter(n for o in out for n in o["notes"])))
    print("accepted reading had no vague check on record:",
          [o["word"] for o in out if o["accepted"] and not o["vague_asked"]])
    print("usable false but a primary reading given:",
          [r["word"] for r in rows if r["sense"].get("usable") is False
           and any(x.get("rank") == "primary" for x in r["sense"].get("readings") or [])])


if __name__ == "__main__":
    main()
