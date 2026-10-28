"""Blind reading sheets for the choice between role rubrics v6 and v7 (Roger, 2026-10-28).  The v6 sheets
(../reader_check_v6/) were drawn around v6's disagreements and cover few of the responses v7 changes; these sheets
sample those changes.  Each October and May response is placed by its first-run scores (keep = 3):

  luna adds      gpt-5.6-luna drops it under v6 and keeps it under v7
  luna removes   gpt-5.6-luna keeps it under v6 and drops it under v7
  mini adds      gpt-4.1-mini drops it under v6 and keeps it under v7, and gpt-5.6-luna drops it under both
  all keep       both judges keep it under both versions (control)
  all drop       both judges drop it under both versions (control)

split by role group (emissary; the AI roles; May: harmful roles and professionals; October: stances and the rest),
"*" holding the rest of a part.  Responses already on the v6 sheets are left out, except for ten of them (not
marked by Roger) drawn again as unannounced re-marks, to show whether these readers mark as the third round did.
The tally pools these marks with the v6 sheets' within each joint keep cell.  key.json records each stratum's
population, how many of its responses the v6 sheets already mark, and each item's scores from both judges under
v5, v6, the v6 rerun and v7.  The readers' criteria are ../reader_check_v6/criteria.md, unchanged.
Writes sheet_1..4.md and key.json.

    uv run python reports/pipeline/judge_comparison/reader_check_v7/build.py
"""
import importlib.util
import json
import random
import re
from collections import Counter
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name
from assistant_axis.judge_rubrics import V6_AI_ROLES

V6_DIR = Path("reports/pipeline/judge_comparison/reader_check_v6")
_spec = importlib.util.spec_from_file_location("v6_build", V6_DIR / "build.py")
v6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v6)

OUT = Path("reports/pipeline/judge_comparison/reader_check_v7")
SEED = 20261029
SCORES = {**v6.SCORES,
          ("mini", "v7"): {s: v6.R / f"judges/gpt-4.1-mini/{s}/v7" for s in v6.RESPONSES},
          ("luna", "v7"): {s: v6.R / f"judges/gpt-5.6-luna/{s}/v7" for s in v6.RESPONSES}}
STANCES = ("perfectionist", "altruist", "minimalist", "pacifist", "contrarian", "visionary")
# (set, part) -> {group: sample size}; "*" is the rest of the part.
WANT = {("may", "luna adds"): {"emissary": 12, "professional": 30, "ai": 6, "harmful": 12},
        ("may", "luna removes"): {"*": 10},
        ("oct", "luna adds"): {"emissary": 6, "stance": 10, "ai": 5, "*": 9},
        ("oct", "luna removes"): {"*": 8},
        ("may", "mini adds"): {"*": 15}, ("oct", "mini adds"): {"*": 7},
        ("may", "all keep"): {"*": 5}, ("oct", "all keep"): {"*": 5},
        ("may", "all drop"): {"*": 5}, ("oct", "all drop"): {"*": 5}}
N_REMARK = 10
N_SHEETS = 4


def group(set_: str, entity: str) -> str:
    if entity in V6_AI_ROLES:
        return "ai"
    if entity == "emissary":
        return "emissary"
    if set_ == "may":
        return "harmful" if entity in v6.HARMFUL else "professional"
    return "stance" if entity in STANCES else "other"


def part(m6: bool, m7: bool, l6: bool, l7: bool) -> str | None:
    if l7 and not l6:
        return "luna adds"
    if l6 and not l7:
        return "luna removes"
    if m7 and not m6 and not l6:
        return "mini adds"
    if m6 and m7 and l6:
        return "all keep"
    if not (m6 or m7 or l6):
        return "all drop"
    return None   # mini removes or mini keeps alone: not sampled


def v6_marks() -> dict:
    """The third round's reader marks on the v6 sheets, ``{item number: letter}``."""
    out = {}
    for p in sorted(V6_DIR.glob("sheet_*.md")):
        cur = None
        for line in p.read_text().splitlines():
            m = re.match(r"^### (\d+)\s*$", line)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r"^mark:\s*(\S)", line)
            if m and cur:
                out[cur] = m.group(1).upper()
                cur = None
    return out


def main() -> None:
    rng = random.Random(SEED)
    sc = {(j, v, s): v6.scores(d) for (j, v), ds in SCORES.items() for s, d in ds.items()}
    key6 = json.loads((V6_DIR / "key.json").read_text())["items"]
    on_v6 = {(it["set"], it["entity"], it["key"]) for it in key6.values()}
    pools: dict = {}
    already: Counter = Counter()
    for s in v6.RESPONSES:
        m6, m7, l6, l7 = (sc[(j, v, s)] for j, v in (("mini", "v6"), ("mini", "v7"), ("luna", "v6"), ("luna", "v7")))
        for e in sorted(set(m6) & set(m7) & set(l6) & set(l7)):
            for k in sorted(set(m6[e]) & set(m7[e]) & set(l6[e]) & set(l7[e])):
                p = part(*(x[e][k] == 3 for x in (m6, m7, l6, l7)))
                if p is None:
                    continue
                g = group(s, e)
                st = f"{s}|{p}|{g if g in WANT[(s, p)] else '*'}"
                if (s, e, k) in on_v6:
                    already[st] += 1
                pools.setdefault(st, []).append((s, e, k))
    items = []

    def item(st: str, s: str, e: str, k: str, **extra) -> dict:
        return {"stratum": st, "set": s, "entity": e, "key": k, **extra,
                "scores": {f"{j}_{v}": sc[(j, v, s)].get(e, {}).get(k) for (j, v) in SCORES}}
    for (s, p), want in WANT.items():
        for g, n in want.items():
            st = f"{s}|{p}|{g}"
            pool = [x for x in pools.get(st, []) if x not in on_v6]
            items += [item(st, *x) for x in rng.sample(pool, min(n, len(pool)))]
    roger = json.loads((V6_DIR / "roger_marks.json").read_text())["v6_items"]
    r3 = v6_marks()
    for n6 in rng.sample(sorted(i for i in key6 if i not in roger and i in r3), N_REMARK):
        it = key6[n6]
        items.append(item("remark", it["set"], it["entity"], it["key"], v6_item=n6, v6_mark=r3[n6]))
    rng.shuffle(items)

    key = {"built": "2026-10-28", "seed": SEED,
           "parts": "first runs, keep = 3: luna adds (luna v6 drops, v7 keeps), luna removes (v6 keeps, v7 drops), "
                    "mini adds (mini v6 drops, v7 keeps; luna drops under both), all keep and all drop (controls: "
                    "both judges, both versions); remark = an item of the v6 sheets drawn again",
           "population": {st: len(v) for st, v in sorted(pools.items())},
           "marked_on_v6_sheets": dict(sorted(already.items())),
           "sampled": dict(sorted(Counter(i["stratum"] for i in items).items())),
           "criteria": "../reader_check_v6/criteria.md", "items": {}}
    cache: dict = {}

    def block(n: int, it: dict) -> list:
        doc = json.loads((v6.ROLES / f"{it['entity']}.json").read_text())
        if (it["set"], it["entity"]) not in cache:
            cache[(it["set"], it["entity"])] = v6.responses(v6.RESPONSES[it["set"]], it["entity"])
        rec = cache[(it["set"], it["entity"])][it["key"]]
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in v6.answer(rec).splitlines())
        link = "../../../../" + str(v6.ROLES / f"{it['entity']}.json")
        ai = " *(an AI or machine role)*" if it["entity"] in V6_AI_ROLES else ""
        return [f"### {n}", "", "mark: ", "",
                f"**Role**: [{corpus_display_name(it['entity'], 'roles')}]({link}){ai} ({v6.LABEL[it['set']]}): "
                f"{doc['description']}",
                "", f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "", "---", ""]

    header = ("Each response below was scored by several judges; none of their scores is shown.  Mark whether it "
              "**should** be in its role's vector, by the criteria in [criteria.md](../reader_check_v6/criteria.md): "
              "**G** good data, it deserves a 3; **B** bad, below 3; **T** both defensible; **?** cannot tell.  A "
              "note after the letter is welcome (\"C:\" for a close call, quoting the decisive words).")
    per = -(-len(items) // N_SHEETS)
    for s in range(N_SHEETS):
        lines = [f"# Judge decision: is each response good data for its role's vector? Sheet {s + 1} of {N_SHEETS}",
                 "", header, "", "---", ""]
        for it in items[s * per:(s + 1) * per]:
            n = len(key["items"]) + 1
            lines += block(n, it)
            key["items"][str(n)] = {**it, "sheet": s + 1}
        (OUT / f"sheet_{s + 1}.md").write_text("\n".join(lines))
    (OUT / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(len(items), "items;", key["sampled"])
    print("population:", key["population"])
    print("already marked on the v6 sheets:", key["marked_on_v6_sheets"])


if __name__ == "__main__":
    main()
