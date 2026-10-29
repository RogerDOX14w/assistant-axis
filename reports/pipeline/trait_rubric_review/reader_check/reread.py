"""Re-read sheets (Roger's option 1, 2026-10-28): the items whose first mark rested on the rules Roger's rulings
changed, to be read again under the revised criteria.md.  An item qualifies when the readers marked it T or ?, or
when their note cites the old rules 1 to 3 (boilerplate, AI mentions, lapses) or rule 5 (an opening passed by),
and Roger did not mark it himself (roger_marks.json).  Items keep their original numbers, so a mark on a re-read
sheet replaces the first mark in tally.py.  Writes reread_1.md, reread_2.md and reread_items.json.

    uv run python reports/pipeline/trait_rubric_review/reader_check/reread.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name

D = Path("reports/pipeline/trait_rubric_review/reader_check")
sys.path.insert(0, str(D))
import build  # noqa: E402
import tally  # noqa: E402

RULE_WORDS = re.compile(r"lapse|boilerplate|rule ?[1235]|\bAI\b|cheap phrase|opening|no feelings|as an AI|Qwen"
                        r"|training|real-time|emotions", re.I)
N_SHEETS = 2
HEADER = ("Each response below was scored by three judges; none of their scores is shown.  Mark whether it "
          "**should** be in its trait's vector, by the criteria in [criteria.md](./criteria.md): **G** good data, "
          "it deserves a 3; **B** bad, below 3; **T** both defensible; **?** cannot tell.  A note after the letter "
          "is welcome (\"C:\" for a close call, quoting the decisive words).  Item numbers are not consecutive.")


def main() -> None:
    key = json.loads((D / "key.json").read_text())["items"]
    roger = json.loads((D / "roger_marks.json").read_text())["items"]
    first = tally.marks(first_only=True)
    chosen = sorted((i for i, (m, n) in first.items()
                     if (m in ("T", "?") or RULE_WORDS.search(n)) and i not in roger), key=int)
    per = -(-len(chosen) // N_SHEETS)
    cache: dict = {}
    record = {}
    for s in range(N_SHEETS):
        lines = [f"# Trait judge decision, second reading: is each response good data for its trait's vector? "
                 f"Sheet {s + 1} of {N_SHEETS}", "", HEADER, "", "---", ""]
        for i in chosen[s * per:(s + 1) * per]:
            it = key[i]
            doc = json.loads((build.TRAITS / f"{it['entity']}.json").read_text())
            if (it["set"], it["entity"]) not in cache:
                cache[(it["set"], it["entity"])] = build.responses(build.SETS[it["set"]][0], it["entity"])
            rec = cache[(it["set"], it["entity"])][it["key"]]
            quoted = "\n".join(("> " + l) if l.strip() else ">" for l in build.answer(rec).splitlines())
            link = "../../../../" + str(build.TRAITS / f"{it['entity']}.json")
            lines += [f"### {i}", "", "mark: ", "",
                      f"**Trait**: [{corpus_display_name(it['entity'], 'traits')}]({link}): {doc['description']}",
                      "", f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "", "---", ""]
            record[i] = {"sheet": s + 1, "first_mark": first[i][0], "first_note": first[i][1],
                         "why": "T or ?" if first[i][0] in ("T", "?") else "note cites an old rule"}
        (D / f"reread_{s + 1}.md").write_text("\n".join(lines))
    (D / "reread_items.json").write_text(json.dumps({"built": "2026-10-28", "items": record}, indent=1) + "\n")
    print(len(chosen), "items in", N_SHEETS, "sheets;", dict(Counter(r["first_mark"] for r in record.values())),
          "by first mark;", dict(Counter(key[i]["tier"] for i in chosen)), "by tier")


if __name__ == "__main__":
    main()
