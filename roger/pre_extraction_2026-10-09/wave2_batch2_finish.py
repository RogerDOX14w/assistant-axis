"""Wave 2, batch 2, after the checks (2026-10-10): pair efficient / wasteful, record the ZTPI set, drop cruel and
merciful (W7), give sadistic cruel's goal-list slot, close the queue entries.

    uv run python roger/pre_extraction_2026-10-09/wave2_batch2_finish.py [--dry-run]

Check answers (two samples each, in data/traits/antonym_check_history.jsonl):
  efficient -> inefficient|wasteful (4), twice;  wasteful -> efficient|economical (4), three times: a clean pair.
  sadistic -> compassionate|empathetic (3): not merciful, so merciful's deletion (W7 (4)) is no longer held.
  future_oriented -> present-oriented|spontaneous (4), twice: a spoke at spontaneous (paired with formulaic).
  win_win_seeking -> zero-sum|adversarial|competitive (3, 4): no file named but competitive (paired); non-X.
  violent -> nonviolent|peaceful(|gentle) (4), twice: both paired elsewhere; non-X.
"""
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.getcwd())
from assistant_axis.arrangements import field_to_json, parse_arrangement, parse_field  # noqa: E402
from data_analysis import seed_entities as SE  # noqa: E402

TRAITS = Path("data/traits/instructions")
TODAY = date.today().isoformat()
ZTPI = {
    "kind": "set",
    "members": sorted(["bitter", "nostalgic", "hedonistic", "fatalistic", "future_oriented"]),
    "source": "Zimbardo Time Perspective Inventory (ZTPI; Zimbardo & Boyd 1999), its five factors",
    "note": "2026-10-10 (Roger 2026-10-09, pre-extraction work list W11 (11)): the corpus traits nearest the five time"
            " perspectives, plain traits, not the instrument's poles. Fit: bitter, past-negative (fair: resentment"
            " rather than rumination); nostalgic, past-positive (good); hedonistic, present-hedonistic (good);"
            " fatalistic, present-fatalistic (good; external locus of control is its wider neighbour);"
            " future-oriented, future (written for the factor on 2026-10-10, planning and goals without the"
            " delay-of-gratification clause, which is self-disciplined's; it takes the place proposed for"
            " self-disciplined because the factor is an orientation in time and self-disciplined is will against"
            " appetite). A set, not a sequence: past and present each have two factors.",
}
DROP = {
    "cruel": "W7 (Roger 2026-10-09): replaced by sadistic, which takes its traits.goal slot (index 25); its text mixed"
             " indifference to suffering (callous) with pleasure in it (sadistic).",
    "merciful": "W7 (4) (Roger 2026-10-09): dropped as a copy of the help / harm / don't-care triangle in the mercy"
                " register; held until sadistic's check, which named compassionate | empathetic, not merciful.",
}


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(["uv", "run", "python", *cmd], check=True)


def main():
    dry = "--dry-run" in sys.argv
    # 1. the ZTPI set: drop a singleton, keep anything else (hedonistic keeps its pair with ascetic)
    for s in ZTPI["members"]:
        p = TRAITS / f"{s}.json"; d = json.loads(p.read_text(encoding="utf-8"))
        arrs = [a for a in parse_field(d.get("arrangement")) if a.kind != "singleton"
                and not (a.kind == "set" and set(a.members) == set(ZTPI["members"]))]
        d["arrangement"] = field_to_json(arrs + [parse_arrangement(ZTPI)])
        print(f"{s}: arrangement -> {json.dumps(d['arrangement'])[:120]}")
        if not dry:
            p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # 2. drops and the goal-list slot
    G = Path("data/goal_roles_and_traits.json"); g = json.loads(G.read_text(encoding="utf-8"))
    i = g["traits"]["goal"].index("cruel"); assert i == 25, i
    g["traits"]["goal"][i] = "sadistic"
    for k1 in ("traits",):
        for k2 in ("goal", "non_goal"):
            assert "merciful" not in g[k1][k2] and "cruel" not in g[k1][k2]
    Q = Path("data/seed_queue.json"); q = SE.load_queue(Q)
    for e in q["entries"]:
        if e["stem"] == "merciful" and e["entity_type"] == "trait":
            e["status"] = "not_adopted"; e["dropped_at"] = TODAY
            e["decision"] = ((e.get("decision") or "") + f" [Dropped {TODAY}: {DROP['merciful']}]").strip()
        if e["stem"] in ("sadistic", "future_oriented", "win_win_seeking") and e["status"] == "checked":
            e["status"] = "done"
    if dry:
        print("would drop", list(DROP), "and put sadistic at traits.goal[25]")
        return
    G.write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SE.save_queue(q, Q)
    subprocess.run(["git", "rm", "-q", *(str(TRAITS / f"{s}.json") for s in DROP)], check=True)
    # 3. the clean pair, both sides regenerated --instructions-only so each neg clause names the other
    run(["data_analysis/seed_entities.py", "pair", "--a", "efficient", "--b", "wasteful", "--regenerate", "both", "--note",
         f"{TODAY} (pre-extraction W10 (7)): written together; efficient -> inefficient|wasteful (4) twice, wasteful ->"
         " efficient|economical (4) three times. Label wasteful vs inefficient open (Roger), the blind name of"
         " wasteful's instructions being inefficient twice."])
    run(["tools/sync_entity_lists.py"])
    run(["data_analysis/check_arrangements.py"])


if __name__ == "__main__":
    main()
