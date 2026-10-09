"""Wave 2, batch 2 (pre-extraction work list W3 E3, W7, W10 (7), W11 (11, 12)): sadistic, savage -> violent,
efficient / wasteful, future-oriented, win-win-seeking.  Final texts from wave2_review_2.md; notes, nearest
neighbours and tags from wave2_plain_drafts.md, with the reviewer's fixes applied.

    uv run python roger/pre_extraction_2026-10-09/wave2_batch2.py prep [--dry-run]
        queue entries (status ready) and seed files for the four new traits; savage rewritten under non-violent
        and renamed violent (seed_entities.py rename, which regenerates it); efficient rewritten under
        non-efficient and regenerated; the four new ones generated.
    uv run python roger/pre_extraction_2026-10-09/wave2_batch2.py check
        seed_entities.py check on the four new ones, then generate_antonyms.py --name-pos on all six (a second
        antonym sample for each new one, the first for violent and efficient) and a plain second sample for
        violent and efficient; every answer goes to the check history (keep every sample), the blind names to
        the queue entries' name_answers where there is an entry.

Pairing, the ZTPI set, cruel's drop and the goal-list slot are done after the answers are read, not here.
"""
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import seed_entities as SE  # noqa: E402

W = Path("roger/pre_extraction_2026-10-09")
TRAITS = Path("data/traits/instructions")
DEC = "Roger 2026-10-09, pre-extraction work list"
NEW = ["sadistic", "wasteful", "future_oriented", "win_win_seeking"]
ALL = NEW + ["violent", "efficient"]


def block(name):
    t = (W / name).read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)\n```", t, re.S)[-1])


def near_text(v):
    return "; ".join(f"{x['stem']}: {x['separator']}" for x in v)


final = {x["stem"]: x for x in block("wave2_review_2.md")}
drafts = {x["stem"]: x for x in block("wave2_plain_drafts.md")}
drafts["win_win_seeking"] = drafts.pop("win_win")

EXTRA_NEAR = {
    "sadistic": [],
    "violent": [("warrior", "role: combat as a trade with a code"), ("quarrelsome_hexaco", "fights a disagreement with words")],
    "efficient": [("competent", "getting it right, work that holds up; efficient's own content is economy"),
                  ("apathetic", "the least effort that makes it go away, no care for the result"),
                  ("monochronic_hall", "one thing at a time on a schedule; time as a resource, not economy of effort")],
    "wasteful": [("polychronic_hall", "'seldom feeling that time is wasted'; the separator is many things at once, against schedules"),
                 ("apathetic", "least effort, no care for the result")],
    "future_oriented": [("career_oriented", "work before family, the next project or deadline; this is all of life"),
                        ("reactive", "this draft negated; reactive is paired with proactive"),
                        ("restless", "always reaching for the next thing, as agitation now, not planning"),
                        ("conscientious_big_five", "goal-striving as order and duty, not an orientation in time"),
                        ("conscientious_hexaco", "thinking before acting, as order and duty"),
                        ("self_starting", "starts without being told; not about time")],
    "win_win_seeking": [("fair", "the same rules for all, not both sides' full needs"),
                        ("unyielding", "gives no ground, but for its own side only"),
                        ("strategic", "the long game in a contest"),
                        ("mediator", "role: seeks mutually acceptable solutions as a neutral third party")],
}
NOTE_FIX = {
    "sadistic": lambda n: n.replace("goal-list slot (#25)", "goal-list slot (traits.goal index 25, the 26th entry)")
    + " Evil's 'glad when others suffer' carries the same pleasure clause as malicious's 'satisfaction in others'"
      " misfortune or suffering': when W7's parked item on malicious's clause goes to Roger, evil's goes with it"
      " (reviewer, wave2_review_2).",
    "future_oriented": lambda n: n + " Pairing (reviewer): a check that names reactive lands on the proactive /"
      " reactive pair, so future-oriented would be a spoke; 'present-oriented' (long-term oriented's check) has no"
      " file; the queue's present_focused (backlog) is the materialistic / spiritual common-mode sense, so a check"
      " naming it is a word match only.",
    "win_win_seeking": lambda n: n.replace("Seed non-X; label provisional", "Seed non-X; label provisional"
      " (reviewer: 'win-win' describes a deal, not a person, so win-win-seeking on the corpus pattern of"
      " closure-seeking, gain-seeking, status-seeking)") + " Compromising: not seeded (reviewer confirmed:"
      " covered in pieces by agreeable (HEXACO), peaceful and moderate, and the label reads as 'compromised').",
}
GROUP = {"sadistic": "W7", "wasteful": "W10", "future_oriented": "W11", "win_win_seeking": "W11"}
SUB = {"W7": "W7: help / harm / don't-care triangles", "W10": "W10: unclassified traits", "W11": "W11: sets of existing traits"}


def entry_fields(stem):
    f, d = final[stem], drafts[stem]
    near = d["nearest_existing"] + [{"stem": s, "separator": t} for s, t in EXTRA_NEAR[stem]]
    notes = NOTE_FIX.get(stem, lambda n: n)(d["description_notes"])
    return {"label": f["label"], "description": f["description"], "description_draft": f["description"],
            "description_notes": notes, "nearest_existing": near_text(near), "tags": d["tags"],
            "status": "ready", "pairing": "singleton", "review_verdict": f["verdict"]}


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(["uv", "run", "python", *cmd], check=True)


def load(stem):
    return json.load(open(TRAITS / f"{stem}.json", encoding="utf-8"))


def save(stem, d):
    (TRAITS / f"{stem}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prep(dry):
    Q = Path("data/seed_queue.json"); q = SE.load_queue(Q); by = {e["stem"]: e for e in q["entries"]}
    for stem in NEW:
        g = GROUP[stem]
        e = by.get(stem)
        if e is None:
            e = {"stem": stem, "entity_type": "trait", "chunk": "pre-extraction", "sub_chunk": SUB[g],
                 "section": "pre-extraction work list " + g, "lines": None, "partner": None, "arrangement_members": None}
            q["entries"].append(e)
        e.update(entry_fields(stem))
        e["decision"] = ((e.get("decision") or "") + f" [{DEC} {g}: seed; reviewed in wave2_review_2.md.]").strip()
        print(f"queue {stem}: {e['label']!r} ready")
    if dry:
        return
    SE.save_queue(q, Q)
    run(["data_analysis/seed_entities.py", "write", "--stems", *NEW])
    # savage: the person sense (W3 E3), renamed violent provisionally (Roger's call after --name-pos)
    d = load("savage")
    d["description"] = final["savage"]["description"]
    d["negative_label"] = "non-violent"
    d["arrangement"] = {"kind": "singleton", "note": "2026-10-10 (pre-extraction W3 E3): rewritten from cutting comebacks"
                        " (harsh's sense) to physical violence and renamed from savage; the 2026-09-23 note on gentle"
                        " concerned the old sense."}
    save("savage", d)
    run(["data_analysis/seed_entities.py", "rename", "--old", "savage", "--new", "violent", "--no-check", "--reason",
         "W3 E3 (Roger 2026-10-09): sense changed with the rename, was cutting comebacks, now physical violence; do not"
         " join savage's May vectors to this text. Label provisional, Roger's call between violent and savage after the"
         " label-blind naming check."])
    # efficient: economy of time and effort (W10 decision 7), non-X until its check against wasteful
    d = load("efficient")
    d["description"] = final["efficient"]["description"]
    d["negative_label"] = "non-efficient"
    d["arrangement"] = {"kind": "singleton", "note": "2026-10-10 (pre-extraction W10 (7)): rewritten as economy of time"
                        " and effort, written together with wasteful; was a one-way pointer at thorough."}
    save("efficient", d)
    run(["data_analysis/regenerate_trait_instructions.py", "--traits", "efficient", "--force"])
    run(["data_analysis/seed_entities.py", "generate", "--stems", *NEW])
    run(["tools/sync_entity_lists.py"])
    run(["data_analysis/check_arrangements.py", "--quiet"])


def antonyms(stems, name_pos):
    cmd = ["uv", "run", "python", "data_analysis/generate_antonyms.py", "--traits", *stems] + (["--name-pos"] if name_pos else [])
    res = subprocess.run(cmd, text=True, capture_output=True)
    if res.returncode != 0:
        print(res.stderr[-2000:]); raise SystemExit(1)
    print(res.stderr[-400:])
    return json.loads(res.stdout)


def record(results, phase):
    Q = Path("data/seed_queue.json"); q = SE.load_queue(Q); by = {e["stem"]: e for e in q["entries"]}
    reg = SE.build_registry(q, Path("data")); hist = []
    for stem, r in results.items():
        v = SE.classify_check(r.get("negative_label", ""), None, reg)
        rec = SE.check_history_record(stem, SE._trait_doc(Path("data"), stem), r, v, None, phase)
        if "positive_name" in r:
            rec["positive_name"] = r.get("positive_name"); rec["positive_name_reasoning"] = r.get("positive_name_reasoning")
        hist.append(rec)
        e = by.get(stem)
        if e is not None:
            SE.note_check_answer(e, r.get("negative_label"), phase)
            if "positive_name" in r:
                e.setdefault("name_answers", []).append({
                    "date": date.today().isoformat(), "phase": phase, "label": load(stem)["positive_label"],
                    "positive_name": r.get("positive_name"), "negative_label": r.get("negative_label"),
                    "antonym_score": r.get("antonym_score")})
        line = f"{stem:16s} -> {r.get('negative_label')} ({r.get('antonym_score')}) [{v['category']}; known {v.get('known')}]"
        if "positive_name" in r:
            line += f"   blind name: {r.get('positive_name')}"
        print(line)
        print(f"    antonym: {(r.get('reasoning') or '')[:300]}")
        if r.get("positive_name_reasoning"):
            print(f"    name:    {r['positive_name_reasoning'][:300]}")
    SE.save_queue(q, Q); SE.append_check_history(Path("data"), hist)


def check():
    run(["data_analysis/seed_entities.py", "check", "--stems", *NEW])
    record(antonyms(ALL, True), "pre-extraction wave 2 batch 2, --name-pos")
    record(antonyms(["violent", "efficient"], False), "pre-extraction wave 2 batch 2, second sample")


def names():
    """A second label-blind sample on the stems named after `names` (the labels still open)."""
    record(antonyms(sys.argv[2:], True), "pre-extraction wave 2 batch 2, --name-pos second sample")


if __name__ == "__main__":
    {"prep": lambda: prep("--dry-run" in sys.argv), "check": check, "names": names}[sys.argv[1]]()
