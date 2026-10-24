"""Blind reading sheets for the v5 check (Roger, 2026-10-24): v5's boundary flips against v4, by role
category, up-flips (v4 < 3, v5 = 3) and some down-flips mixed; readers mark whether each response is
good data for its role's vector.  Writes sheet_1..4.md and key.json."""
import json, random
from pathlib import Path
R = Path("runpod_workspace/rubric_exp"); OUT = Path("reports/pipeline/role_rubric_experiment/v5_check")
ROLES = Path("data/roles/instructions"); SEED = 20261024
SOURCES = {  # name: (v4 scores dir, v5 scores dir, responses dir)
    "oct": (R / "versions/v4/scores", R / "versions/v5/scores", R / "responses"),
    "may": (R / "may_target/scores_v4", R / "may_target/scores_v5", R / "may_target/responses"),
}
CATEGORIES = {
    "A helpful professionals": ["secretary", "scheduler", "screener", "translator", "proofreader", "debugger",
                                "moderator", "emissary", "organizer", "interpreter", "validator", "psychologist",
                                "biologist", "historian"],
    "B other occupations and characters": ["soldier", "merchant", "pirate"],
    "C stances and dispositions": ["altruist", "contrarian", "minimalist", "pacifist", "peacekeeper",
                                   "perfectionist", "realist", "visionary"],
    "D AI and machine roles": ["assistant", "instrumentally_aligned_ai", "robot", "cyborg", "paperclip_maximizer"],
    "E harmful roles": ["hacker", "virus"],
    "F non-human and mythic": ["alien", "ghost", "spirit", "oracle", "familiar", "tree", "guru"],
}
N_UP, N_DOWN = 30, 10
def scores(d, r):
    p = d / f"{r}.json"
    return {k: v for k, v in json.loads(p.read_text()).items() if isinstance(v, int)} if p.exists() else {}
def responses(d, r):
    p = d / f"{r}.jsonl"
    out = {}
    for l in p.read_text().splitlines():
        if l.strip():
            x = json.loads(l); out[f"{x['label']}_p{x['prompt_index']}_q{x['question_index']}"] = x
    return out
rng = random.Random(SEED)
items, counts = [], {}
for cat, roles in CATEGORIES.items():
    pools = {"up": {}, "down": {}}
    for src, (d4, d5, _) in SOURCES.items():
        for r in roles:
            a, b = scores(d4, r), scores(d5, r)
            if not a or not b:
                continue
            ks = sorted(set(a) & set(b))
            pools["up"][(src, r)] = [k for k in ks if a[k] < 3 and b[k] == 3]
            pools["down"][(src, r)] = [k for k in ks if a[k] == 3 and b[k] < 3]
    counts[cat] = {d: {f"{s}/{r}": len(v) for (s, r), v in pools[d].items() if v} for d in pools}
    for direction, n in (("up", N_UP), ("down", N_DOWN)):
        for lst in pools[direction].values():
            rng.shuffle(lst)
        taken = 0
        while taken < n and any(pools[direction].values()):
            for key in sorted(pools[direction]):
                if taken >= n:
                    break
                if pools[direction][key]:
                    src, r = key
                    items.append({"category": cat, "direction": direction, "source": src, "role": r,
                                  "key": pools[direction][key].pop()})
                    taken += 1
rng.shuffle(items)
n_sheets = 4
key = {"built": "2026-10-24", "seed": SEED, "n_up": N_UP, "n_down": N_DOWN, "categories": CATEGORIES,
       "flip_counts": counts,
       "note": "G = good data (deserves 3). Up-flip (v4 < 3, v5 = 3) marked G: v5 right; down-flip marked G: v4 right.",
       "items": {}}
per = -(-len(items) // n_sheets)
for s in range(n_sheets):
    chunk = items[s * per:(s + 1) * per]
    lines = [f"# v5 check: is each response good data for its role's vector? Sheet {s + 1} of {n_sheets}", "",
             "Each response below is one that two judge rubrics disagree on: one scored it 3 (it enters the role's vector), the other below 3.  Which is which is not shown.  Mark whether it **should** be in the vector, by Roger's criteria: **G** good data, it deserves a 3; **B** bad, below 3; **T** both defensible; **?** cannot tell.  A note after the letter is welcome (\"C:\" for a close call).", "", "---", ""]
    for it in chunk:
        n = len(key["items"]) + 1
        doc = json.loads((ROLES / f"{it['role']}.json").read_text())
        resp = responses(SOURCES[it["source"]][2], it["role"])[it["key"]]
        answer = next(m["content"] for m in resp["conversation"] if m["role"] == "assistant")
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in answer.splitlines())
        lines += [f"### {n}", "", "mark: ", "",
                  f"**Role**: [{it['role'].replace('_', ' ')}](../../../../data/roles/instructions/{it['role']}.json): {doc['description']}", "",
                  f"**Question**: {resp['question']}", "", "**Response**:", "", quoted, "", "---", ""]
        key["items"][str(n)] = {**it, "sheet": s + 1}
    (OUT / f"sheet_{s + 1}.md").write_text("\n".join(lines))
(OUT / "key.json").write_text(json.dumps(key, indent=1) + "\n")
from collections import Counter
print(len(items), "items")
print(Counter((i["category"][:1], i["direction"]) for i in items))
for cat, c in counts.items():
    print(cat, "| up flips:", sum(c["up"].values()), "| down flips:", sum(c["down"].values()))
