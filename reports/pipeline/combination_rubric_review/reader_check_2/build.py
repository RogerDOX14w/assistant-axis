"""Second blind reading sheet for the combination rubric review (Roger, 2026-10-31): a stratified random draw
from the judged October samples (runpod_workspace/combo_recheck, 27 r_ combinations, and
runpod_workspace/tcomb_recheck, 44 t_; the pods' step 1 output at the 1024 cap under the October instructions,
every response scored by the three candidate "both" rules: draft 14, the context sides 16 with 17, 16 with 18),
so that precision and recall against the readers can be estimated for that data and its slices rather than for
contested cases, as the first sheet (../reader_check/) measured them on May responses.

Strata: kind (r_, t_) x keep level (terciles of the combination's mean keep under the three candidates) x the
candidates' pattern on the response (all keep, mixed, all drop).  Per kind x level: 10 all-keep, 12 mixed and 5
all-drop items at random, at most PER_STEM_CAP per combination, 162 in all; Roger's sheet takes 2, 2 and 1 of
them per kind x level, 30.  Each item carries its cell's frame count in key.json, so estimate.py weights the
marks back to the frame.  No judge's or candidate's answer is shown; the goal entity (r_ or t_) is hidden.

Writes sheet_1.md ... sheet_4.md (role, trait, question, response; four return lines), roger_sheet_2.md (the
same, "your" lines) and key.json.

    uv run python reports/pipeline/combination_rubric_review/reader_check_2/build.py
"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from assistant_axis.entity_id import corpus_display_name

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "context_arms"))
sys.path.insert(0, str(HERE.parent / "reader_check"))
import compare  # noqa: E402
import tally  # noqa: E402

REPO = compare.REPO
TCOMB = REPO / "runpod_workspace" / "tcomb_recheck"
SEED = 20261031
PATTERNS = ("all keep", "mixed", "all drop")
WANT = {"all keep": 10, "mixed": 12, "all drop": 5}      # per kind x level
ROGER = {"all keep": 2, "mixed": 2, "all drop": 1}       # per kind x level, from the items drawn
PER_STEM_CAP = 4
N_SHEETS = 4
LINK = "../../../../data"
CANDIDATES = ("draft 14", "16 and 17", "16 and 18")


def keeps(r: dict) -> dict:
    return {"draft 14": r["V14"] == 3, "16 and 17": r["V16"] == 3 and r["V17"] == 3,
            "16 and 18": r["V16"] == 3 and r["V18"] == 3}


def pattern(k: dict) -> str:
    return "all keep" if all(k.values()) else "all drop" if not any(k.values()) else "mixed"


def description(kind: str, stem: str) -> str:
    return json.loads((REPO / "data" / kind / "instructions" / f"{stem}.json").read_text())["description"]


def quoted(text: str) -> str:
    return "\n".join(("> " + l) if l.strip() else ">" for l in text.splitlines())


def head(it: dict) -> list:
    role, trait = it["role"], it["trait"]
    ai = " *(an AI or machine role)*" if role in tally.AI_ROLES else ""
    return [f"**Role**: [{corpus_display_name(role, 'roles')}]({LINK}/roles/instructions/{role}.json){ai}: "
            f"{description('roles', role)}", "",
            f"**Trait**: [{corpus_display_name(trait, 'traits')}]({LINK}/traits/instructions/{trait}.json): "
            f"{description('traits', trait)}", "",
            f"**Question**: {it['question']}", "", "**Response**:", "",
            quoted(it["answer"] + ("…" if it["cut"] else "")), "", "---", ""]


def item(it: dict, lines_before: list) -> list:
    return [f"### {it['n']}", ""] + lines_before + [""] + head(it)


def main() -> None:
    rng = random.Random(SEED)
    rows = compare.load_sample(compare.RECHECK) + compare.load_sample(TCOMB)
    rows = [r for r in rows if all(r[k] is not None for k in ("V14", "V16", "V17", "V18", "Rs", "T", "C"))]
    for r in rows:
        r["keep"] = keeps(r)
        r["pattern"] = pattern(r["keep"])
    per_stem = defaultdict(list)
    for r in rows:
        per_stem[r["stem"]].append(mean(r["keep"].values()))
    stem_keep = {s: mean(v) for s, v in per_stem.items()}
    ks = sorted(stem_keep.values())
    cut_lo, cut_hi = ks[len(ks) // 3], ks[2 * len(ks) // 3]
    level = {s: ("low" if k < cut_lo else "medium" if k < cut_hi else "high") for s, k in stem_keep.items()}
    for r in rows:
        r["level"] = level[r["stem"]]
        r["cell"] = (r["kind"], r["level"], r["pattern"])
    frame = Counter(r["cell"] for r in rows)
    print(f"{len(rows)} responses in {len(stem_keep)} combinations; level cutpoints {cut_lo:.3f} {cut_hi:.3f}; "
          f"combinations by level {Counter(level.values())}")

    chosen, used, taken = [], set(), Counter()
    cells = [(k, lv, p) for k in "rt" for lv in ("low", "medium", "high") for p in PATTERNS]
    for cell in cells:
        pool = [r for r in rows if r["cell"] == cell and (r["stem"], r["key"]) not in used]
        rng.shuffle(pool)
        got = 0
        for r in pool:
            if got == WANT[cell[2]]:
                break
            if taken[r["stem"]] >= PER_STEM_CAP:
                continue
            used.add((r["stem"], r["key"])); taken[r["stem"]] += 1; got += 1
            chosen.append(r)
        if got < WANT[cell[2]]:
            print(f"  cell {cell}: only {got} of {WANT[cell[2]]} (frame {frame[cell]})")
    rng.shuffle(chosen)
    for n, it in enumerate(chosen, 1):
        it["n"] = n
    roger = set()
    for k in "rt":
        for lv in ("low", "medium", "high"):
            for p, n in ROGER.items():
                roger.update(it["n"] for it in rng.sample([it for it in chosen if it["cell"] == (k, lv, p)], n))

    note = ("Each response below was generated in October 2026 by Qwen-3-32B at the 1024-token cap under the current "
            "instructions (the criteria file describes the May sheet's responses; the criteria themselves are "
            "unchanged).  The sample is a stratified random draw, so there is no expected share of any mark.")
    header = ("Mark each response by the criteria in [criteria.md](../reader_check/criteria.md).  Four lines under each "
              "number: `role:` and `trait:` take **G** (shows, enough for a 3), **B** (does not), **T** (both "
              "defensible) or **?**, with a note (\"C:\" and the decisive words for a close call, the criterion's number "
              "where one decides it); `ai:` takes **y**, **t** or **n**; `relation:` takes a tag from the criteria and a "
              "note.  Several judges have scored every response; none of their scores is shown.  " + note)
    per_sheet = -(-len(chosen) // N_SHEETS)
    sheets = [chosen[i:i + per_sheet] for i in range(0, len(chosen), per_sheet)]
    for s, items in enumerate(sheets, 1):
        lines = [f"# Combination reading, October responses: does the role show, does the trait show?  Sheet {s} of "
                 f"{len(sheets)}", "", header, "", "---", ""]
        for it in items:
            lines += item(it, ["role: ", "trait: ", "ai: ", "relation: "])
        (HERE / f"sheet_{s}.md").write_text("\n".join(lines))
    lines = ["# Combination reading, October responses: Roger's sheet", "",
             "Thirty of the readers' items (the item numbers are theirs), drawn at random within the strata.  Put your "
             "marks on the `your ...` lines, by [criteria.md](../reader_check/criteria.md); your marks override the "
             "readers'.  " + note, "", "---", ""]
    for it in sorted((it for it in chosen if it["n"] in roger), key=lambda it: it["n"]):
        lines += item(it, ["your role: ", "your trait: ", "your ai: ", "your relation: "])
    (HERE / "roger_sheet_2.md").write_text("\n".join(lines))

    key = {"seed": SEED, "frame": {" | ".join(c): n for c, n in sorted(frame.items())},
           "level_cutpoints": [cut_lo, cut_hi], "stem_keep": stem_keep, "stem_level": level,
           "drawn": {" | ".join(c): sum(it["cell"] == c for it in chosen) for c in cells}, "items": {}}
    for it in chosen:
        key["items"][str(it["n"])] = {
            "stem": it["stem"], "key": it["key"], "kind": it["kind"], "level": it["level"], "pattern": it["pattern"],
            "role": it["role"], "trait": it["trait"], "goal": "trait" if it["kind"] == "t" else "role", "cut": it["cut"],
            "april_text_luna": it["C"], "role_judge": it["Rs"], "trait_judge": it["T"],
            "v14": it["V14"], "v16": it["V16"], "v17": it["V17"], "v18": it["V18"], "keep": it["keep"],
            "on_roger_sheet": it["n"] in roger,
            "sheet": next(s for s, items in enumerate(sheets, 1) if it in items)}
    (HERE / "key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(chosen)} items on {len(sheets)} sheets; {len(roger)} on Roger's")
    print("by cell:", {" | ".join(c): sum(it["cell"] == c for it in chosen) for c in cells})
    print("by stem:", Counter(it["stem"] for it in chosen).most_common(8))
    print("roles:", Counter(it["role"] for it in chosen))


if __name__ == "__main__":
    main()
