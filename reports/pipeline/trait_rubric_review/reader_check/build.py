"""Blind reading sheets for the trait judge decision (Roger, 2026-10-28): is a response good data for its trait's
vector?  The reference is gpt-4.1-mini's May 2026 production scores (the number-only rubric; what the vectors on
disk were built from); the two candidates are gpt-4.1-mini and gpt-5.6-luna under trait rubric v3 (first runs;
keep = 3 throughout).  Responses come from 24 May traits in three tiers of May keep rate (selection.json): the 8
low-keep traits of the held sample, 8 medium and 8 high.

Each response falls in one cell of three keep (1) / drop (0) decisions, written reference, gpt-4.1-mini v3,
gpt-5.6-luna v3:
  011  both candidates add it        001  only gpt-5.6-luna adds it     010  only gpt-4.1-mini v3 adds it
  100  both candidates remove it     110  only gpt-5.6-luna removes it  101  only gpt-4.1-mini v3 removes it
  111  all keep (precision)          000  all drop (recall)
Strata are tier x cell, sampled at random within each; key.json records every stratum's population and each
item's reference, v3 and v3-rerun scores from both judges.  The readers' criteria are in criteria.md beside the
sheets.  Writes sheet_1..N.md and key.json.

    uv run python reports/pipeline/trait_rubric_review/reader_check/build.py
"""
import json
import random
from collections import Counter
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name

R = Path("runpod_workspace/rubric_exp")
OUT = Path("reports/pipeline/trait_rubric_review/reader_check")
TRAITS = Path("data/traits/instructions")   # step 3 rendered the v3 prompts from these files
MAY = Path("runpod_workspace/qwen/qwen-3-32b Roger 8slot/traits/scores")
SELECTION = json.loads(Path("reports/pipeline/trait_rubric_review/selection.json").read_text())
SEED = 20261028
#: set -> (responses directory, the judges' set directory under runpod_workspace/rubric_exp/judges/<judge>/)
SETS = {"low": (R / "held_traits/responses", "traits"), "new": (R / "held_traits_tiers/responses", "tiers")}
SCORES = {(j, v): {s: R / f"judges/{j}/{d}/{v}" for s, (_, d) in SETS.items()}
          for j in ("gpt-4.1-mini", "gpt-5.6-luna") for v in ("v3", "v3_rerun")}
SHORT = {"gpt-4.1-mini": "mini", "gpt-5.6-luna": "luna"}
# cell -> sample size per tier ("111" is where precision lives, "000" where recall does).
WANT = {"011": 14, "010": 14, "001": 14, "100": 14, "110": 14, "101": 14, "111": 20, "000": 14}
PER_SHEET = 50


def tier_of(trait: str):
    """The trait's tier, or None for a judged trait the selection no longer holds (selection.json "replaced")."""
    for tier, v in SELECTION["tiers"].items():
        names = v if isinstance(v, list) else v["semantic"] + v["random"]
        if trait in names:
            return tier
    return None


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


#: What step 3's --mark_truncated appends to the judge's copy of a response cut at step 1's --max_tokens
#: (finish_reason "length"); the readers see the same (Roger, 2026-10-28: "we should do this for the reader too").
#: No space since 2026-10-29 (3_judge.TRUNCATION_MARKER; a mid-word cut reads as cut).  The May copies carry the
#: field since the backfill of 2026-10-28 (../backfill_finish_reason.py); sheets built before it (sheet_1 to 7,
#: reread_1 and 2, roger_sheet.md) show cut responses unmarked.
TRUNCATION_MARKER = "…"


def answer(rec: dict, marked: bool = True) -> str:
    text = next(m["content"] for m in reversed(rec["conversation"]) if m["role"] == "assistant")
    if marked and rec.get("finish_reason") == "length":
        text += TRUNCATION_MARKER
    return text


def main() -> None:
    rng = random.Random(SEED)
    sc = {(SHORT[j], v, s): scores(d) for (j, v), ds in SCORES.items() for s, d in ds.items()}
    may = scores(MAY)
    pools: dict = {}
    for s in SETS:
        m3, l3 = sc[("mini", "v3", s)], sc[("luna", "v3", s)]
        for e in sorted(set(m3) & set(l3)):
            tier = tier_of(e)
            if tier is None:
                continue
            for k in sorted(set(may[e]) & set(m3[e]) & set(l3[e])):
                cell = "".join(str(int(x[k] == 3)) for x in (may[e], m3[e], l3[e]))
                pools.setdefault(f"{tier}|{cell}", []).append((s, e, k))
    items = []
    for tier in SELECTION["tiers"]:
        for cell, n in WANT.items():
            st = f"{tier}|{cell}"
            for set_, e, k in rng.sample(pools.get(st, []), min(n, len(pools.get(st, [])))):
                items.append({"stratum": st, "set": set_, "entity": e, "key": k, "tier": tier,
                              "scores": {"may": may[e][k],
                                         **{f"{SHORT[j]}_{v}": sc[(SHORT[j], v, set_)].get(e, {}).get(k)
                                            for (j, v) in SCORES}}})
    rng.shuffle(items)

    key = {"built": "2026-10-28", "seed": SEED,
           "cell": "keep (1) / drop (0) by: reference gpt-4.1-mini May production scores, candidate gpt-4.1-mini "
                   "v3, candidate gpt-5.6-luna v3 (first runs; keep = 3)",
           "population": {st: len(v) for st, v in sorted(pools.items())},
           "sampled": dict(sorted(Counter(i["stratum"] for i in items).items())),
           "note": "G = should be in the vector.  Marks in a cell judge the judges that keep it there.",
           "items": {}}
    cache: dict = {}

    def block(n: int, it: dict) -> list:
        doc = json.loads((TRAITS / f"{it['entity']}.json").read_text())
        if (it["set"], it["entity"]) not in cache:
            cache[(it["set"], it["entity"])] = responses(SETS[it["set"]][0], it["entity"])
        rec = cache[(it["set"], it["entity"])][it["key"]]
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in answer(rec).splitlines())
        link = "../../../../" + str(TRAITS / f"{it['entity']}.json")
        return [f"### {n}", "", "mark: ", "",
                f"**Trait**: [{corpus_display_name(it['entity'], 'traits')}]({link}): {doc['description']}",
                "", f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "", "---", ""]

    header = ("Each response below was scored by three judges; none of their scores is shown.  Mark whether it "
              "**should** be in its trait's vector, by the criteria in [criteria.md](./criteria.md): **G** good "
              "data, it deserves a 3; **B** bad, below 3; **T** both defensible; **?** cannot tell.  A note after "
              "the letter is welcome (\"C:\" for a close call, quoting the decisive words).")
    n_sheets = -(-len(items) // PER_SHEET)
    for s in range(n_sheets):
        lines = [f"# Trait judge decision: is each response good data for its trait's vector? "
                 f"Sheet {s + 1} of {n_sheets}", "", header, "", "---", ""]
        for it in items[s * PER_SHEET:(s + 1) * PER_SHEET]:
            n = len(key["items"]) + 1
            lines += block(n, it)
            key["items"][str(n)] = {**it, "sheet": s + 1}
        (OUT / f"sheet_{s + 1}.md").write_text("\n".join(lines))
    (OUT / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(len(items), "items in", n_sheets, "sheets;", key["sampled"])
    print("population:", key["population"])


if __name__ == "__main__":
    main()
