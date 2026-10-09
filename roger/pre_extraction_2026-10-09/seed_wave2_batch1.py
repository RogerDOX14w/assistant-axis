"""Queue entries for the first reviewed wave-2 batch (W6 five, W23 four, W25 Dark Tetrad four), status `ready`.
Final texts from wave2_review_1.md; notes, neighbours, tags and sources from the writers' drafts.  Then run
`seed_entities.py write / generate / check` on the 13 stems.

    uv run python roger/pre_extraction_2026-10-09/seed_wave2_batch1.py [--dry-run]
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import seed_entities as SE  # noqa: E402

W = Path("roger/pre_extraction_2026-10-09")
DEC = "Roger 2026-10-09, pre-extraction work list"


def block(name):
    t = (W / name).read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", t, re.S)[-1])


def near_text(v):
    if isinstance(v, str):
        return v
    return "; ".join(f"{x.get('stem')}: {x.get('separator') or x.get('why') or x.get('note') or ''}".strip() if isinstance(x, dict) else str(x) for x in v)


final = {x["stem"]: x for x in block("wave2_review_1.md")}
w6 = {x["stem"]: x for x in block("w6_drafts.md")}
w23 = {x["stem"]: x for x in block("w23_drafts.md")}
w25 = {x["stem"]: x for x in block("w25_dark_tetrad_drafts.md")}
EXTRA_NEAR = {"fickle": "unreliable: fails commitments, not enthusiasm that cools",
              "just": "transactional: keeps score of exchanges, not of desert",
              "narcissistic_dark_tetrad": "self_aggrandizing: inflates one's own part in a story, the plain everyday trait"}
EXTRA_NOTES = {
    "southeast_asian": "The four countries named are the region's four most populous (reviewer, 2026-10-09).",
    "pacific_islander": "Maori are left unnamed: in New Zealand usage 'Pacific peoples' excludes them (reviewer, decided 2026-10-09).",
    "sadistic_dark_tetrad": "Markedly milder in harm done than the plain cruelty traits, by the SD4's design (it minimizes physical sadism items); rule 9: mirror the source's strength.",
}
OLD_DT = {"machiavellian_dark_tetrad": "machiavellianism_dark_tetrad", "narcissistic_dark_tetrad": "narcissism_dark_tetrad",
          "psychopathic_dark_tetrad": "psychopathy_dark_tetrad", "sadistic_dark_tetrad": "everyday_sadism_dark_tetrad"}


def main():
    dry = "--dry-run" in sys.argv
    Q = Path("data/seed_queue.json"); q = SE.load_queue(Q); by = {e["stem"]: e for e in q["entries"]}
    done = []
    for stem, f in final.items():
        src = w6.get(stem) or w23.get(stem) or w25.get(stem)
        group = "W6" if stem in w6 else "W23" if stem in w23 else "W25"
        notes = (src.get("description_notes") or "") + ((" " + EXTRA_NOTES[stem]) if stem in EXTRA_NOTES else "")
        near = near_text(src.get("nearest_existing") or "") + (("; " + EXTRA_NEAR[stem]) if stem in EXTRA_NEAR else "")
        tags = [t for t in (src.get("tags") or []) if t not in ("optional", "not_imported")]
        fields = {"label": f["label"], "description": f["description"], "description_draft": f["description"],
                  "description_notes": notes.strip(), "nearest_existing": near, "tags": tags, "status": "ready",
                  "pairing": "singleton", "review_verdict": f["verdict"]}
        for k in ("source", "source_url", "source_text", "source_retrieved"):
            if src.get(k):
                fields[k] = src[k]
        dec = f"[{DEC} {group}: seed; reviewed in wave2_review_1.md ({f['verdict']}).]"
        e = by.get(stem) or (by.get(OLD_DT[stem]) if stem in OLD_DT else None)
        if e is None:
            e = {"stem": stem, "entity_type": "trait", "chunk": "pre-extraction",
                 "sub_chunk": {"W6": "W6: occupational instruments", "W23": "W23: September deferrals", "W25": "W25: Dark Tetrad"}[group],
                 "section": "pre-extraction work list " + group, "lines": None, "partner": None, "arrangement_members": None}
            q["entries"].append(e)
        elif e["stem"] != stem:
            fields["notes"] = ((e.get("notes") or "") + f" Queue stem was {e['stem']} until 2026-10-09 (the construct adjective is the label).").strip()
            e["stem"] = stem
        e.update(fields)
        e["decision"] = ((e.get("decision") or "") + " " + dec).strip()
        if stem == "fickle":
            e["notes"] = ((e.get("notes") or "") + " Also the trait-gap candidate fickle#1 (M3 new, from loyal's antonym check); seeded through this path, so the registry row is marked seeded by that session.").strip()
        done.append((stem, e["label"]))
    print("\n".join(f"{s}: {l}" for s, l in done))
    if not dry:
        SE.save_queue(q, Q)


if __name__ == "__main__":
    main()
