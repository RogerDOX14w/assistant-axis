"""Blind reading sheets for the v6 judge decision (Roger, 2026-10-27).  The reference is gpt-4.1-mini under role
rubric v5, the current best though known to be flawed; the two candidates are gpt-4.1-mini and gpt-5.6-luna under
v6 (first runs; keep = 3 throughout).  Responses come from the 30 October sample roles and the 11 May roles.

Each response falls in one cell of three keep (1) / drop (0) decisions, written reference, gpt-4.1-mini v6,
gpt-5.6-luna v6:
  011  both candidates add it        001  only gpt-5.6-luna adds it     010  only gpt-4.1-mini v6 adds it
  100  both candidates remove it     110  only gpt-5.6-luna removes it  101  only gpt-4.1-mini v6 removes it
  111  all keep (control)            000  all drop (control)
A candidate's changes against the reference are its adds and removes, so the marks in each cell, weighted by the
cell's population, say for each candidate whether it improves on v5; cells 010, 110, 001 and 101 decide between
the two.  The large cells are split by role group (October: perfectionist, altruist, the five AI roles; May: the AI
roles and the harmful roles), "*" holding the rest of the cell, so that each group is represented.  Sampled at
random within each stratum; key.json records every stratum's population, and each item's v5, v6 and v6-rerun
scores from both judges.  The readers' criteria are in criteria.md beside the sheets.
Writes sheet_1..5.md and key.json.

    uv run python reports/pipeline/judge_comparison/reader_check_v6/build.py
"""
import json
import random
from collections import Counter
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name
from assistant_axis.judge_rubrics import V6_AI_ROLES

R = Path("runpod_workspace/rubric_exp")
OUT = Path("reports/pipeline/judge_comparison/reader_check_v6")
ROLES = Path("data/roles/instructions")   # step 3 rendered the v6 prompts from these files, for both sets
SEED = 20261028
RESPONSES = {"oct": R / "responses", "may": R / "may_target/responses"}
LABEL = {"oct": "October sample", "may": "May roles"}
SCORES = {("mini", "v5"): {"oct": R / "versions/v5/scores", "may": R / "may_target/scores_v5"},
          ("mini", "v6"): {s: R / f"judges/gpt-4.1-mini/{s}/v6" for s in RESPONSES},
          ("mini", "v6_rerun"): {s: R / f"judges/gpt-4.1-mini/{s}/v6_rerun" for s in RESPONSES},
          ("luna", "v5"): {s: R / f"judges/gpt-5.6-luna/{s}/v5" for s in RESPONSES},
          ("luna", "v6"): {s: R / f"judges/gpt-5.6-luna/{s}/v6" for s in RESPONSES},
          ("luna", "v6_rerun"): {s: R / f"judges/gpt-5.6-luna/{s}/v6_rerun" for s in RESPONSES}}
HARMFUL = tuple(json.loads(Path("reports/pipeline/role_rubric_experiment/v5_check/key.json").read_text())
                ["categories"]["E harmful roles"])
# (set, cell) -> {group: sample size}; "*" is the rest of the cell.
WANT = {("oct", "011"): {"perfectionist": 6, "altruist": 5, "ai": 7, "*": 12},
        ("oct", "010"): {"perfectionist": 7, "altruist": 4, "ai": 8, "*": 11},
        ("oct", "110"): {"ai": 12, "*": 13},
        ("oct", "100"): {"*": 15}, ("oct", "001"): {"*": 8}, ("oct", "101"): {"*": 4},
        ("oct", "111"): {"*": 8}, ("oct", "000"): {"*": 8},
        ("may", "011"): {"ai": 6, "harmful": 7, "*": 12},
        ("may", "010"): {"ai": 6, "harmful": 7, "*": 12},
        ("may", "110"): {"ai": 7, "*": 8},
        ("may", "100"): {"*": 12}, ("may", "001"): {"*": 10}, ("may", "101"): {"*": 4},
        ("may", "111"): {"*": 6}, ("may", "000"): {"*": 8}}
N_SHEETS = 5


def scores(d: Path) -> dict:
    out = {}
    for p in sorted(d.glob("*.json")):
        if p.stem.startswith("_") or p.stem in ("usage", "judge_rubric", "batch_state"):
            continue
        s = {k: v for k, v in json.loads(p.read_text()).items() if isinstance(v, int)}
        if s:
            out[p.stem] = s
    return out


def responses(d: Path, entity: str) -> dict:
    out = {}
    for line in (d / f"{entity}.jsonl").read_text().splitlines():
        if line.strip():
            x = json.loads(line)
            out[f"{x['label']}_p{x['prompt_index']}_q{x['question_index']}"] = x
    return out


def answer(rec: dict) -> str:
    return next(m["content"] for m in reversed(rec["conversation"]) if m["role"] == "assistant")


def group(set_: str, entity: str) -> str:
    if entity in V6_AI_ROLES:
        return "ai"
    if set_ == "oct" and entity in ("perfectionist", "altruist"):
        return entity
    if set_ == "may" and entity in HARMFUL:
        return "harmful"
    return "other"


def main() -> None:
    rng = random.Random(SEED)
    sc = {(j, v, s): scores(d) for (j, v), ds in SCORES.items() for s, d in ds.items()}
    pools: dict = {}
    for s in RESPONSES:
        m5, m6, l6 = sc[("mini", "v5", s)], sc[("mini", "v6", s)], sc[("luna", "v6", s)]
        for e in sorted(set(m5) & set(m6) & set(l6)):
            for k in sorted(set(m5[e]) & set(m6[e]) & set(l6[e])):
                cell = "".join(str(int(x[e][k] == 3)) for x in (m5, m6, l6))
                g = group(s, e)
                pools.setdefault(f"{s}|{cell}|{g if g in WANT[(s, cell)] else '*'}", []).append((s, e, k))
    items = []
    for (s, cell), want in WANT.items():
        for g, n in want.items():
            st = f"{s}|{cell}|{g}"
            for set_, e, k in rng.sample(pools.get(st, []), min(n, len(pools.get(st, [])))):
                items.append({"stratum": st, "set": set_, "entity": e, "key": k,
                              "scores": {f"{j}_{v}": sc[(j, v, set_)].get(e, {}).get(k) for (j, v) in SCORES}})
    rng.shuffle(items)

    key = {"built": "2026-10-28", "seed": SEED,
           "cell": "keep (1) / drop (0) by: reference gpt-4.1-mini v5, candidate gpt-4.1-mini v6, "
                   "candidate gpt-5.6-luna v6 (first runs; keep = 3)",
           "population": {st: len(v) for st, v in sorted(pools.items())},
           "sampled": dict(sorted(Counter(i["stratum"] for i in items).items())),
           "note": "G = should be in the vector.  Marks in a cell judge the judges that keep it there: G in 011 "
                   "says both candidates were right to add it, G in 110 that gpt-5.6-luna was wrong to remove it, "
                   "G in 010 that gpt-4.1-mini v6 was right to add it, and so on.", "items": {}}
    cache: dict = {}

    def block(n: int, it: dict) -> list:
        doc = json.loads((ROLES / f"{it['entity']}.json").read_text())
        if (it["set"], it["entity"]) not in cache:
            cache[(it["set"], it["entity"])] = responses(RESPONSES[it["set"]], it["entity"])
        rec = cache[(it["set"], it["entity"])][it["key"]]
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in answer(rec).splitlines())
        link = "../../../../" + str(ROLES / f"{it['entity']}.json")
        ai = " *(an AI or machine role)*" if it["entity"] in V6_AI_ROLES else ""
        return [f"### {n}", "", "mark: ", "",
                f"**Role**: [{corpus_display_name(it['entity'], 'roles')}]({link}){ai} ({LABEL[it['set']]}): "
                f"{doc['description']}",
                "", f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "", "---", ""]

    header = ("Each response below was scored by three judges; none of their scores is shown.  Mark whether it "
              "**should** be in its role's vector, by the criteria in [criteria.md](./criteria.md): **G** good "
              "data, it deserves a 3; **B** bad, below 3; **T** both defensible; **?** cannot tell.  A note after "
              "the letter is welcome (\"C:\" for a close call, quoting the decisive words).")
    per = -(-len(items) // N_SHEETS)
    for s in range(N_SHEETS):
        lines = [f"# Judge decision under rubric v6: is each response good data for its role's vector? "
                 f"Sheet {s + 1} of {N_SHEETS}", "", header, "", "---", ""]
        for it in items[s * per:(s + 1) * per]:
            n = len(key["items"]) + 1
            lines += block(n, it)
            key["items"][str(n)] = {**it, "sheet": s + 1}
        (OUT / f"sheet_{s + 1}.md").write_text("\n".join(lines))
    (OUT / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(len(items), "items;", key["sampled"])
    print("population:", key["population"])


if __name__ == "__main__":
    main()
