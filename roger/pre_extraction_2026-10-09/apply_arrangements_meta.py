"""Record the metadata-only arrangements Roger decided on 2026-10-09 (pre-extraction work list W8, W11 (10),
W12 (15-18)).  No regeneration: arrangements do not reach any prompt.

    uv run python roger/pre_extraction_2026-10-09/apply_arrangements_meta.py [--dry-run]

For each member: a `singleton` is dropped, an arrangement of the same kind and members is replaced (so a note
can be updated), anything else is kept, and the new one is appended; the field is written in canonical form.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from assistant_axis.arrangements import field_to_json, parse_arrangement, parse_field  # noqa: E402

D = "2026-10-09 (Roger, pre-extraction work list"
LIFE = ["infant", "toddler", "child", "teenager", "student", "graduate", "newlywed", "parent", "grandparent", "retiree", "elder"]
MIGRATION = sorted(["exile", "expatriate", "immigrant", "naturalized_citizen", "nomad", "pilgrim", "refugee", "wanderer"])
BERRY_OLD = sorted(["assimilated", "exile", "immigrant", "marginalized"])
BERRY_NEW = sorted(["assimilated", "bicultural", "exile", "marginalized"])

JOBS = [
    ("traits", {"kind": "triangle", "members": sorted(["accountable", "blame_shifting", "self_blaming"]),
                "note": f"{D} W8): a triangle, not a kite. Two vices of attribution (blame on others, blame on oneself) with the "
                        "virtue, owning one's part no more and no less, as the reasonable middle. The extraction tests whether "
                        "accountable lies between the vices (a sequence) or off the line."}),
    ("traits", {"kind": "sequence", "members": ["altruistic", "cooperative", "selfish", "competitive"],
                "source": "Social value orientation (Murphy, Ackermann & Handgraaf 2011; the triple-dominance measure)",
                "note": f"{D} W11): the orientations as points on one angle, weight on the other's outcome against one's own: "
                        "altruistic, prosocial (cooperative), individualistic (selfish), competitive. The corpus's individualistic "
                        "is the cultural sense and stays out. The two clean pairs are chords of the arc."}),
    ("traits", {"kind": "sequence", "members": ["young", "middle_aged", "elderly"],
                "note": f"{D} W12): age as a trait. Its role-side counterpart is the life-stage sequence (infant ... elder) "
                        "on the role files; arrangements are same-type only, so the two are recorded separately."}),
    ("roles", {"kind": "sequence", "members": LIFE,
               "note": f"{D} W12): life stages, retiree before elder (the elder is the oldest member of a community). "
                       "Left out: events and off-ramps (widow, divorcee, orphan), intern, pregnant, prodigy, veteran. Its "
                       "trait-side counterpart is the age sequence young, middle_aged, elderly; arrangements are same-type only."}),
    ("roles", {"kind": "map", "members": MIGRATION,
               "note": f"{D} W12): migration and movement, expected roughly two-dimensional on the September role audit's "
                       "axes, rootedness (settled to moving) and agency (chosen to forced). Caveats: the axes are a hypothesis; "
                       "pilgrim and wanderer are as much travel as migration; no member is both forced and still moving."}),
]


def load(kind, stem):
    p = Path(f"data/{kind}/instructions/{stem}.json")
    t = p.read_text(encoding="utf-8"); d = json.loads(t)
    assert json.dumps(d, indent=2, ensure_ascii=False) + "\n" == t, f"format {p}"
    return p, d


def put(p, d, arrs):
    d["arrangement"] = field_to_json(arrs)
    return json.dumps(d, indent=2, ensure_ascii=False) + "\n"


def add(kind, stem, new, out):
    p, d = load(kind, stem) if p_key(kind, stem) not in out else (Path(f"data/{kind}/instructions/{stem}.json"), json.loads(out[p_key(kind, stem)]))
    arrs = [a for a in parse_field(d.get("arrangement")) if a.kind != "singleton"]
    n = parse_arrangement(new)
    arrs = [a for a in arrs if not (a.kind == n.kind and set(a.members) == set(n.members))] + [n]
    out[p_key(kind, stem)] = put(p, d, arrs)


def p_key(kind, stem):
    return f"data/{kind}/instructions/{stem}.json"


def main():
    dry = "--dry-run" in sys.argv
    out = {}
    for kind, arr in JOBS:
        for s in arr["members"]:
            add(kind, s, arr, out)
    # W12 (17): bicultural replaces immigrant as the Berry square's integration corner.
    _, ex = load("roles", "exile")
    old = next(a for a in parse_field(ex["arrangement"]) if a.kind == "square")
    assert sorted(old.members) == BERRY_OLD
    note = (old.note + f" | {D} W12): bicultural replaces immigrant as the integration corner; bicultural was written as "
            "assimilated's mirror (both born to immigrant parents), so that edge differs only in the heritage kept; "
            "immigrant (first generation) keeps the migration map.")
    note = note.replace("immigrant = integration", "integration (immigrant until 2026-10-09, now bicultural)")
    sq = {"kind": "square", "members": BERRY_NEW, "note": note}
    for s in BERRY_NEW:
        add("roles", s, sq, out)
        # drop the old square from the three that stay (same kind, different members)
        k = p_key("roles", s); d = json.loads(out[k])
        arrs = [a for a in parse_field(d["arrangement"]) if not (a.kind == "square" and sorted(a.members) == BERRY_OLD)]
        out[k] = put(Path(k), d, arrs)
    k = p_key("roles", "immigrant"); d = json.loads(out[k]) if k in out else load("roles", "immigrant")[1]
    arrs = [a for a in parse_field(d["arrangement"]) if not (a.kind == "square" and sorted(a.members) == BERRY_OLD)]
    out[k] = put(Path(k), d, arrs)
    for k, text in sorted(out.items()):
        print(("would write " if dry else "write ") + k, json.dumps(json.loads(text)["arrangement"])[:140])
        if not dry:
            Path(k).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
