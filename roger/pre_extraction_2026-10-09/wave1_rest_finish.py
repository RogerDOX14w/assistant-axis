"""Wave 1 remainder, after the checks of wave1_rest_edits.json (2026-10-10; log wave1_rest_run.log): the pairs the
checks support, the triangles and sequences Roger decided on 2026-10-09, and the MLQ source move.

    uv run python roger/pre_extraction_2026-10-09/wave1_rest_finish.py [--dry-run]

- E7: mystical -> rationalist | empirical | skeptical (4); rationalist -> mystic | intuitionist (3): each names the
  other ('mystic' for mystical, as provincial's 'cosmopolite' counted for cosmopolitan): pair.
- W10 (6): data-driven -> anecdotal | intuitive (3); anecdotal (non-X, staged 2026-10-09) -> statistical | data-driven
  | empirical (4), and 2026-09-16 statistical | empirical | data-driven.  Strictly two known words; read as nearly
  clean: 'statistical' is the rewritten data-driven's own sense, and empirical (observation against guessing) is
  paired with speculative.  Pair, flagged to Roger as a judgement call.
- W7: the will triangle benevolent / malevolent / uncaring, every corner non-X (benevolent and uncaring relabelled in
  the run); the moral-standing triangle good / evil / amoral beside their pairs (labels stay the pairs').
- W9: micromanaging / absentee paired by decision; the sequence micromanaging, hands-on, hands-off, absentee; the
  MLQ source moves from hands-off to absentee.
- W14: the moral-circle sequence in Roger's 13-member order; philanthropic, patriotic, cosmopolitan leave it.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from assistant_axis.arrangements import field_to_json, parse_arrangement, parse_field  # noqa: E402

T = Path("data/traits/instructions")
D = "2026-10-10 (Roger 2026-10-09, pre-extraction work list"
W14 = json.load(open("roger/pre_extraction_2026-10-09/w14_edits.json", encoding="utf-8"))
OLD_CIRCLE = {"selfish", "clannish", "cliqueish", "insular", "parochial", "regionalist", "sectarian", "nationalist",
              "patriotic", "ethnocentric", "civilizationist", "cosmopolitan", "philanthropic", "humanitarian",
              "kind_to_animals", "ecocentric"}

WILL = {"kind": "triangle", "members": ["benevolent", "malevolent", "uncaring"],
        "note": f"{D} W7 (1)): the will copy of the help / harm / don't-care triangle, wanting people well, wanting them"
                " harmed, wanting nothing for them; every corner non-X (the 2026-10-09 convention). Checks 2026-10-10:"
                " benevolent -> malevolent | selfish | callous, uncaring -> caring | compassionate, and malicious (feeling"
                " triangle) -> benevolent."}
MORAL = {"kind": "triangle", "members": ["amoral", "evil", "good"],
         "note": f"{D} W7 (1)): the moral-standing copy, beside the pairs good / evil and amoral / moral, whose labels"
                 " it leaves as they are (a pair's labels are the prompt-facing antonyms)."}
DELEGATION = {"kind": "sequence", "members": ["micromanaging", "hands_on", "hands_off", "absentee"],
              "note": f"{D} W9 (1)): involvement in work one has handed over, most to least: steps in unasked and redoes"
                      " it, steps in unasked when needed, only when asked, not even then. The neutral pair hands-on /"
                      " hands-off sits inside the two vices, which are paired by decision."}


def arrs_of(d):
    return parse_field(d.get("arrangement"))


def load(stem, out):
    if stem in out:
        return out[stem]
    p = T / f"{stem}.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == t, p
    out[stem] = d
    return d


def put(stem, d, arrs, out):
    d["arrangement"] = field_to_json(arrs); out[stem] = d


def add(arr, out, drop=lambda a: False):
    n = parse_arrangement(arr)
    for s in arr["members"]:
        d = load(s, out)
        keep = [a for a in arrs_of(d) if a.kind != "singleton" and not drop(a)
                and not (a.kind == n.kind and set(a.members) == set(n.members))]
        put(s, d, keep + [n], out)


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(["uv", "run", "python", *cmd], check=True)


def main():
    dry = "--dry-run" in sys.argv
    out = {}
    add(WILL, out)
    add(MORAL, out)
    add(DELEGATION, out)
    hands_off, absentee = load("hands_off", out), load("absentee", out)
    assert hands_off.get("source") == "MLQ (leadership style)" and "source" not in absentee
    absentee["source"] = hands_off.pop("source")
    # W14: the new order replaces the old 16-member sequence; the three that leave become singletons
    old = next(a for a in arrs_of(load("nationalist", out)) if a.kind == "sequence" and set(a.members) == OLD_CIRCLE)
    circle = {"kind": "sequence", "members": W14["sequence"],
              "note": old.note + f" | {D} W14): descriptions rewritten in terms of circle size, from family to town or"
                      " parish, city or home state, region of the country, faith, nation and racial group; order set by"
                      " Roger; philanthropic, patriotic and cosmopolitan removed (their texts are not a circle size)"}
    add(circle, out, drop=lambda a: a.kind == "sequence" and set(a.members) == OLD_CIRCLE)
    for s in W14["removed_from_sequence"]:
        d = load(s, out)
        rest = [a for a in arrs_of(d) if not (a.kind == "sequence" and set(a.members) == OLD_CIRCLE)]
        assert not rest and d["negative_label"] == f"non-{d['positive_label']}", s
        d["arrangement"] = {"kind": "singleton", "note": f"{D} W14): removed from the moral-circle sequence"}
        out[s] = d
    for s, d in sorted(out.items()):
        print(("would write " if dry else "write ") + s, json.dumps(d["arrangement"])[:150])
        if not dry:
            (T / f"{s}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if dry:
        return
    run(["data_analysis/seed_entities.py", "pair", "--a", "mystical", "--b", "rationalist", "--regenerate", "both",
         "--note", "2026-10-10 (pre-extraction W3 E7): written to matched scopes, known beyond reason against only what"
         " reason and proof show; mystical -> rationalist | empirical | skeptical (4), rationalist -> mystic |"
         " intuitionist (3)."])
    run(["data_analysis/seed_entities.py", "pair", "--a", "anecdotal", "--b", "data_driven", "--regenerate", "b",
         "--note", "2026-10-10 (pre-extraction W10 (6)): data-driven rewritten to anecdotal's scope; data-driven ->"
         " anecdotal | intuitive (3); anecdotal (non-X) -> statistical | data-driven | empirical (4) twice, read as"
         " nearly clean ('statistical' is data-driven's own sense; empirical is paired with speculative). Judgement"
         " call, flagged to Roger."])
    run(["data_analysis/seed_entities.py", "pair", "--a", "absentee", "--b", "micromanaging", "--regenerate", "both",
         "--note", f"{D} W9): paired by decision, the two vices at the ends of the delegation sequence; each one's"
         " check names the far end of the neutral pair (micromanaging -> hands-off | delegating, absentee ->"
         " hands-on | engaged), the sensible contrary rather than the opposite vice."])
    run(["tools/sync_entity_lists.py"])
    run(["data_analysis/check_arrangements.py"])


if __name__ == "__main__":
    main()
