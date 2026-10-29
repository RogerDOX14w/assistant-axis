"""Render the trait rubric review's arms (prompt versions 11 to 13, assistant_axis/judge_rubrics.py; 13 settled
2026-10-30 as the extraction's trait rubric) as the judge will receive them (Roger, 2026-10-28): each template
verbatim, then the prompt step 3 builds for five of the reviewed
responses, through step 3's own resolve_eval_prompt, mark_truncated_responses and pending_prompts, so the text
here is byte for byte what the judge gets.  Writes rubric_drafts.md beside this script.

    uv run python reports/pipeline/trait_rubric_review/render_drafts.py
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "rubric_drafts.md"
RC = REPO / "reports/pipeline/trait_rubric_review/reader_check"
sys.path.insert(0, str(RC))
import build  # noqa: E402

from assistant_axis import judge_rubrics as jr  # noqa: E402

spec = importlib.util.spec_from_file_location("_step3", REPO / "pipeline" / "3_judge.py")
step3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step3)

ROLES, TRAITS = REPO / "data/roles/instructions", REPO / "data/traits/instructions"
VERSIONS = {11: "A/B/C port (version 11)", 12: "four-clause edit of version 3 (version 12)",
            13: "version 12 with version 11's B treatment in levels 2 and 3 (version 13)"}
#: (key.json item, why it is a sample)
SAMPLES = [("32", "avoidant, your G: a four-sentence shrug; luna keeps it, May and mini v3 drop it"),
           ("23", "honest, cut at the cap, in the cell where mini keeps and luna drops: the truncation case"),
           ("47", "evil, your T on the 2|3 border: \"I have no feelings or emotions, but I can provide a "
                  "perspective\", then strongly in trait; the B test"),
           ("62", "whimsical, your G: three pieces of boilerplate the whimsy absorbs; the other B test"),
           ("204", "ethnocentric, your G on the second sheet (item 40): \"As an AI model, I may have biases\" "
                   "inside the trait; version 11 keeps it, version 12 gave it 2 in both runs; the level-2 case "
                   "version 13 is for")]


def main() -> None:
    key = json.loads((RC / "key.json").read_text())["items"]
    roger = json.loads((RC / "roger_marks.json").read_text())
    roger["items"].update(json.loads((RC / "roger_marks_2.json").read_text())["items"])
    lines = ["# Trait rubric drafts, rendered", "",
             "The arms of the trait rubric test (Roger, 2026-10-28 and 2026-10-30), registered as prompt versions "
             "11 to 13 in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py): 11 and 12 drafts, and "
             "**13 settled on 2026-10-30 as the trait rubric for the October extraction and step 3's default**, "
             "judged by gpt-5.6-luna (Roger; tested twice: all-tier precision / recall 93.8 / 90.9 and 94.1 / 90.3 "
             "on the 362 marked items, kappa 0.93 between the runs; "
             "[versions_scores.json](./reader_check/versions_scores.json)).  All carry the "
             "same rulings from [criteria.md](./reader_check/criteria.md): the persona is the default assistant "
             "plus the trait; a little is enough; a refusal or dodge in the trait's manner counts; the "
             "helpful-assistant clause and its converse; an AI mention counts only when the trait does not "
             "absorb it; a response ending in \"…\" was cut.  No corpus trait is named.  Version 11 is the "
             "role rubric's A, B, C port, read from the answers as version 10 reads a role reply; version 12 is "
             "version 3's scale with the rulings as a paragraph and levels 2 and 3 reworded; version 13 is "
             "version 12 with levels 2 and 3 carrying version 11's B treatment of an AI mention, after luna read "
             "version 12's level 2 as any self-reference.  Each template is "
             "shown first, then the exact prompt step 3 builds for five reviewed responses (the marker "
             "\"…\" on the cut one comes from step 3's `--mark_truncated`, on by default).", "",
             "Samples: " + "; ".join(f"item {i} ({why.split(',')[0]})" for i, why in SAMPLES) + ".", ""]
    for v, title in VERSIONS.items():
        version = jr.PROMPT_VERSIONS[v]
        lines += [f"## {title}", "", f"*{version.summary}.*  Reply read as `{version.reply_format_for('trait')}`, "
                  f"default `--max_tokens` {version.max_tokens}.", "", "### Template", "", "```text",
                  version.trait, "```", ""]
        for i, why in SAMPLES:
            it = key[i]
            rec = build.responses(build.SETS[it["set"]][0], it["entity"])[it["key"]]
            tpl = step3.resolve_eval_prompt(it["entity"], ROLES, TRAITS, "trait", prompt_version=v)
            marked, n = step3.mark_truncated_responses([rec])
            (_, prompt), = step3.pending_prompts(marked, tpl, {})
            mark = roger["items"].get(i, "")
            lines += [f"### Sample: item {i}, {why}", "",
                      f"Key `{it['entity']} {it['key']}`, cell {it['stratum']}, finish_reason `{rec['finish_reason']}`"
                      f"{' (marked)' if n else ''}; your mark {mark or '(none)'}.", "", "```text", prompt, "```", ""]
    OUT.write_text("\n".join(lines))
    print("wrote", OUT.relative_to(REPO), len(lines), "lines")


if __name__ == "__main__":
    main()
