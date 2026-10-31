"""Roger's third sheet (2026-10-31; Roger: "If you have a few more marks you want, give me another sheet: up to half
a dozen if they'd help settle something"): six of the readers' items, chosen to settle the two criteria questions
the readers raised most (readers_questions.md): how far role criterion 5's benefit of the doubt carries a
narrowly voiced professional on a question with no opening (items 12, 34, 80), the trait's subject raised in
order to negate it, the pending T/B rule (92, 142), and the aligned-AI carve-out for a gentle musing with no AI
trace (116).  Each item is copied from its sheet with the readers' question above it and the four "your" lines;
his marks override the readers' as on roger_sheet_2.md (estimate.py reads both).

    uv run python reports/pipeline/combination_rubric_review/reader_check_2/build_roger_3.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WANT = {
    "12": ("role criterion 5", "The chef on a philosophy question with no culinary opening, answered as a generic "
           "survey: does the benefit of the doubt for a helpful professional reach a narrowly voiced profession?  "
           "Reader: T."),
    "34": ("role criterion 5", "The chef on cultural appropriation, where cuisine was an opening, answered as a generic "
           "survey.  Reader: T/B."),
    "80": ("role criterion 5", "The proofreader on a question with no opening and no trace of the role at all: does "
           "criterion 5 alone carry it?  Reader: G/T."),
    "92": ("the trait raised in order to negate it", "Kin raised in the last line only to turn the knife on them "
           "(\"blood... is always the first to bleed\"), clannish.  Reader: T/B by the pending rule."),
    "142": ("the trait raised in order to negate it", "\"No point in passing it around or risking a mistake\", "
            "harmful raised to refuse it.  Reader: T/B by the pending rule."),
    "116": ("the aligned-AI carve-out", "Does \"a helpful AI's voice is in character\" extend to a gentle musing with "
            "nothing marking the AI or its mission?  Reader: T."),
}


def main() -> None:
    key = json.loads((HERE / "key.json").read_text())["items"]
    already = [n for n in WANT if key[n]["on_roger_sheet"]]
    assert not already, f"already on roger_sheet_2.md: {already}"
    blocks = {}
    for s in range(1, 5):
        text = (HERE / f"sheet_{s}.md").read_text()
        for m in re.finditer(r"^### (\d+)\n(.*?)(?=^### \d+\n|\Z)", text, re.S | re.M):
            blocks[m.group(1)] = m.group(2)
    lines = ["# Combination reading, October responses: Roger's third sheet", "",
             "Six of the readers' items (the item numbers are theirs), each chosen for a criteria question the readers "
             "raised; the question is stated above the item.  Put your marks on the `your ...` lines, by "
             "[criteria.md](../reader_check/criteria.md); your marks override the readers', and your note is the "
             "ruling.", "", "---", ""]
    for n, (topic, question) in WANT.items():
        body = blocks[n]
        body = re.sub(r"^role: \ntrait: \nai: \nrelation: \n", "", body, count=1, flags=re.M)
        lines += [f"### {n}", "", f"*{topic}*: {question}", "",
                  "your role: ", "your trait: ", "your ai: ", "your relation: ", "", body.rstrip(), "", ""]
    (HERE / "roger_sheet_3.md").write_text("\n".join(lines))
    print(f"roger_sheet_3.md: {len(WANT)} items: " + ", ".join(f"{n} ({key[n]['stem']})" for n in WANT))


if __name__ == "__main__":
    main()
