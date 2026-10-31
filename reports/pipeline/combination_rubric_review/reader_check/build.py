"""Blind reading sheets for the combination rubric review (Roger, 2026-10-30): for each response, does the role
show, does the trait show, is there an AI lapse, and how do the two personas interact.  Items come from the
exploration sample (../explore/rows_arms.json: every response with the April-text combination score, the
dedicated role and trait scores, and the drafts 14 and 15's A/B/R/T answers), chosen where the approaches
differ: a draft's R or T against the dedicated judge's verdict, in both directions, plus items every judge
agrees on as a check on the readers.  No judge's verdict is shown; the goal entity (r_ or t_) is hidden.

Writes sheet_1.md and sheet_2.md (the holistic sheets: role, trait, question, response; four return lines),
role_sheet.md and trait_sheet.md (a subset shown one persona at a time, for the separate-reader check),
roger_sheet.md (his blind sheet, the same four lines prefixed "your"), and key.json.

    uv run python reports/pipeline/combination_rubric_review/reader_check/build.py
"""
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name

HERE = Path("reports/pipeline/combination_rubric_review/reader_check")
ROWS = Path("reports/pipeline/combination_rubric_review/explore/rows_arms.json")
ROLES, TRAITS = Path("data/roles/instructions"), Path("data/traits/instructions")
RENAMED_ROLE = {"aligned_artificial_intelligence": "instrumentally_aligned_ai"}
AI_ROLES = ("cyborg", "instrumentally_aligned_ai", "paperclip_maximizer", "robot", "virtue_aligned_ai")
SEED = 20261030
#: pool -> how many; a pool is (question, arms' answer, dedicated judge's verdict)
WANT = {("R", True, False): 20, ("R", False, True): 10, ("T", True, False): 20, ("T", False, True): 10}
N_AGREED = {(True, True): 8, (True, False): 4, (False, True): 4, (False, False): 4}
PER_STEM_CAP = 4
N_SINGLE = 30          # items read again one persona at a time
N_ROGER = 40
#: Items the readers' reports flagged as criteria questions (2026-10-30) that the draw above left off Roger's
#: sheet; they go on it in a second section, for his ruling.
ROGER_EXTRA = (4, 8, 12, 33, 37, 43, 48, 58, 61, 65, 67, 70, 72)
PER_SHEET = 40
LINK = "../../../../data"


def description(kind: str, stem: str) -> str:
    return json.loads((Path("data") / kind / "instructions" / f"{stem}.json").read_text())["description"]


def quoted(text: str) -> str:
    return "\n".join(("> " + l) if l.strip() else ">" for l in text.splitlines())


def main() -> None:
    rng = random.Random(SEED)
    rows = json.load(open(ROWS))
    for r in rows:
        r["trait_show"] = r["T"] >= 2
        r["role_stem"] = RENAMED_ROLE.get(r["role"], r["role"])
    pools = defaultdict(list)
    for r in rows:
        arms_R, arms_T = (r["a14"]["R"], r["a15"]["R"]), (r["a14"]["T"], r["a15"]["T"])
        judge_R, judge_T = r["role_abc"]["C"], r["trait_show"]
        if all(x == judge_R for x in arms_R) and all(x == judge_T for x in arms_T):
            pools[("agree", judge_R, judge_T)].append(r)
            continue
        if all(x != judge_R for x in arms_R):
            pools[("R", arms_R[0], judge_R)].append(r)
        if all(x != judge_T for x in arms_T):
            pools[("T", arms_T[0], judge_T)].append(r)
    print("pools:", {k: len(v) for k, v in sorted(pools.items(), key=str)})

    chosen, used, per_stem = [], set(), Counter()

    def take(pool, n, tag):
        cands = [r for r in pools[pool] if (r["stem"], r["key"]) not in used]
        rng.shuffle(cands)
        got = 0
        for r in cands:
            if got == n:
                break
            if per_stem[r["stem"]] >= PER_STEM_CAP:
                continue
            used.add((r["stem"], r["key"])); per_stem[r["stem"]] += 1; got += 1
            chosen.append({**r, "pool": tag})
        if got < n:
            print(f"  pool {pool}: only {got} of {n}")

    for (q, arm, judge), n in WANT.items():
        take((q, arm, judge), n, f"{q}: arms {'yes' if arm else 'no'}, judge {'yes' if judge else 'no'}")
    for (jr_, jt), n in N_AGREED.items():
        take(("agree", jr_, jt), n, f"agreed: role {'yes' if jr_ else 'no'}, trait {'yes' if jt else 'no'}")
    rng.shuffle(chosen)
    for n, it in enumerate(chosen, 1):
        it["n"] = n
    single = set(rng.sample(range(1, len(chosen) + 1), N_SINGLE))
    disagree = [it["n"] for it in chosen if not it["pool"].startswith("agreed")]
    agreed = [it["n"] for it in chosen if it["pool"].startswith("agreed")]
    roger = set(rng.sample(disagree, N_ROGER - 10) + rng.sample(agreed, 10))

    def head(it, show_role: bool, show_trait: bool) -> list:
        lines = []
        if show_role:
            stem = it["role_stem"]
            ai = " *(an AI or machine role)*" if stem in AI_ROLES else ""
            lines.append(f"**Role**: [{corpus_display_name(stem, 'roles')}]({LINK}/roles/instructions/{stem}.json){ai}: "
                         f"{description('roles', stem)}")
            lines.append("")
        if show_trait:
            stem = it["trait"]
            lines.append(f"**Trait**: [{corpus_display_name(stem, 'traits')}]({LINK}/traits/instructions/{stem}.json): "
                         f"{description('traits', stem)}")
            lines.append("")
        lines += [f"**Question**: {it['question']}", "", "**Response**:", "",
                  quoted(it["answer"] + ("…" if it["cut"] else "")), "", "---", ""]
        return lines

    def item(it, lines_before: list, show_role=True, show_trait=True) -> list:
        return [f"### {it['n']}", ""] + lines_before + [""] + head(it, show_role, show_trait)

    header = ("Mark each response by the criteria in [criteria.md](./criteria.md).  Four lines under each number: "
              "`role:` and `trait:` take **G** (shows, enough for a 3), **B** (does not), **T** (both defensible) or "
              "**?**, with a note (\"C:\" and the decisive words for a close call, the criterion's number where one "
              "decides it); `ai:` takes **y**, **t** or **n**; `relation:` takes a tag from the criteria and a note.  "
              "Several judges have scored every response; none of their scores is shown.")
    sheets = [chosen[i:i + PER_SHEET] for i in range(0, len(chosen), PER_SHEET)]
    for s, items in enumerate(sheets, 1):
        lines = [f"# Combination reading: does the role show, does the trait show?  Sheet {s} of {len(sheets)}", "",
                 header, "", "---", ""]
        for it in items:
            lines += item(it, ["role: ", "trait: ", "ai: ", "relation: "])
        (HERE / f"sheet_{s}.md").write_text("\n".join(lines))
    single_header = ("The same responses as on the holistic sheets, shown with one persona only, for a check of the "
                     "holistic reading.  Mark by [criteria.md](./criteria.md): the `{what}:` line takes **G**, **B**, "
                     "**T** or **?** with a note; the `ai:` line **y**, **t** or **n**.  No judge's score is shown.")
    for what, show in (("role", (True, False)), ("trait", (False, True))):
        lines = [f"# Combination reading, {what} only: does the {what} show?", "",
                 single_header.format(what=what), "", "---", ""]
        for it in sorted((it for it in chosen if it["n"] in single), key=lambda it: it["n"]):
            lines += item(it, [f"{what}: ", "ai: "], *show)
        (HERE / f"{what}_sheet.md").write_text("\n".join(lines))
    lines = ["# Combination reading: Roger's sheet", "",
             "Forty of the readers' items, in the same form (the item numbers are theirs).  Put your marks on the "
             "`your ...` lines, by [criteria.md](./criteria.md); your marks override the readers'.", "", "---", ""]
    for it in sorted((it for it in chosen if it["n"] in roger), key=lambda it: it["n"]):
        lines += item(it, ["your role: ", "your trait: ", "your ai: ", "your relation: "])
    extra = [it for it in chosen if it["n"] in ROGER_EXTRA and it["n"] not in roger]
    if extra:
        lines += ["## Readers' questions", "",
                  "Items the readers flagged as unclear under the criteria (their reports of 2026-10-30), not drawn "
                  "above; the same four lines.  Your mark on these settles the criteria question as much as the item.",
                  "", "---", ""]
        for it in sorted(extra, key=lambda it: it["n"]):
            lines += item(it, ["your role: ", "your trait: ", "your ai: ", "your relation: "])
    (HERE / "roger_sheet.md").write_text("\n".join(lines))

    key = {"seed": SEED, "pools": {str(k): len(v) for k, v in pools.items()}, "items": {}}
    for it in chosen:
        key["items"][str(it["n"])] = {
            "stem": it["stem"], "key": it["key"], "stratum": it["stratum"], "pool": it["pool"],
            "role": it["role_stem"], "trait": it["trait"], "goal": "trait" if it["stem"].startswith("t_") else "role",
            "cut": it["cut"], "may": it["may"], "april_text_luna": it["C"],
            "role_judge": {"score": it["Rs"], **it["role_abc"]}, "trait_judge": {"score": it["T"], "shows": it["trait_show"]},
            "v14": {**it["a14"], "score": it["s14"]}, "v15": {**it["a15"], "score": it["s15"]},
            "on_single_sheets": it["n"] in single, "on_roger_sheet": it["n"] in roger,
            "sheet": next(s for s, items in enumerate(sheets, 1) if it in items)}
    (HERE / "key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(chosen)} items on {len(sheets)} sheets; {len(single)} on the single-persona sheets; {len(roger)} on Roger's")
    print("by pool:", Counter(it["pool"] for it in chosen))
    print("by stratum:", Counter(it["stratum"] for it in chosen))
    print("by stem:", Counter(it["stem"] for it in chosen).most_common(6))


if __name__ == "__main__":
    main()
