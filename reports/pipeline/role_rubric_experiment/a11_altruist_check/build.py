"""Blind reading sheet for A11 on altruist (Roger, 2026-10-26): v4 judges altruist with the level-2
example "philanthropic AI for the role philanthropist" (arm A11) instead of A1's "altruistic AI for
the role altruist", on counts alone (229 -> 276 kept, 37 down / 84 up).  This samples those flips,
up-flips (A1 < 3, A11 = 3) and down-flips mixed, for a reader to mark whether each response is good
data for altruist's vector.  Writes sheet_1.md and key.json."""
import json, random
from pathlib import Path
R = Path("runpod_workspace/rubric_exp"); OUT = Path(__file__).parent
ROLE = "altruist"; SEED = 20261026; N_UP, N_DOWN = 28, 12
def scores(arm):
    p = R / "judged" / arm / f"{ROLE}.json"
    return {k: v for k, v in json.loads(p.read_text()).items() if isinstance(v, int)}
responses = {}
for l in (R / "responses" / f"{ROLE}.jsonl").read_text().splitlines():
    if l.strip():
        x = json.loads(l); responses[f"{x['label']}_p{x['prompt_index']}_q{x['question_index']}"] = x
a1, a11 = scores("A1"), scores("A11")
ks = sorted(set(a1) & set(a11))
pools = {"up": [k for k in ks if a1[k] < 3 and a11[k] == 3], "down": [k for k in ks if a1[k] == 3 and a11[k] < 3]}
rng = random.Random(SEED)
items = []
for direction, n in (("up", N_UP), ("down", N_DOWN)):
    items += [{"direction": direction, "key": k, "a1": a1[k], "a11": a11[k]}
              for k in rng.sample(pools[direction], n)]
rng.shuffle(items)
doc = json.loads((Path("data/roles/instructions") / f"{ROLE}.json").read_text())
key = {"built": "2026-10-26", "seed": SEED, "role": ROLE, "n_up": N_UP, "n_down": N_DOWN,
       "flip_counts": {d: len(v) for d, v in pools.items()},
       "kept": {"A1": sum(v == 3 for v in a1.values()), "A11": sum(v == 3 for v in a11.values())},
       "note": "G = good data (deserves 3). Up-flip (A1 < 3, A11 = 3) marked G: A11 right; down-flip marked G: A1 right.",
       "items": {}}
lines = ["# A11 check: is each response good data for altruist's vector?", "",
         "Each response below is one that two judge rubrics disagree on: one scored it 3 (it enters the role's vector), the other below 3.  Which is which is not shown.  Mark whether it **should** be in the vector, by Roger's criteria: **G** good data, it deserves a 3; **B** bad, below 3; **T** both defensible; **?** cannot tell.  A note after the letter is welcome (\"C:\" for a close call).", "", "---", ""]
for it in items:
    n = len(key["items"]) + 1
    resp = responses[it["key"]]
    answer = next(m["content"] for m in resp["conversation"] if m["role"] == "assistant")
    quoted = "\n".join(("> " + l) if l.strip() else ">" for l in answer.splitlines())
    lines += [f"### {n}", "", "mark: ", "",
              f"**Role**: [{ROLE}](../../../../data/roles/instructions/{ROLE}.json): {doc['description']}", "",
              f"**Question**: {resp['question']}", "", "**Response**:", "", quoted, "", "---", ""]
    key["items"][str(n)] = it
(OUT / "sheet_1.md").write_text("\n".join(lines))
(OUT / "key.json").write_text(json.dumps(key, indent=1) + "\n")
print(len(items), "items;", key["flip_counts"], key["kept"])
