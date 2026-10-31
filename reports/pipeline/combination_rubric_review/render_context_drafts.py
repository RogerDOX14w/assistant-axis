"""Render the context-aware combination drafts (prompt versions 16 and 17, assistant_axis/judge_rubrics.py) as
the judge will receive them (Roger, 2026-10-30): each template verbatim, the part an AI or machine role's
combinations get instead, then the prompt step 3 builds for five responses of the exploration sample, through
step 3's own resolve_eval_prompt, mark_truncated_responses and pending_prompts, so the text here is byte for byte
what the judge gets.  Writes rubric_drafts_context.md beside this script.  The samples are render_drafts.py's.

    uv run python reports/pipeline/combination_rubric_review/render_context_drafts.py
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "rubric_drafts_context.md"
SAMPLE = REPO / "runpod_workspace" / "combo_explore" / "combo" / "responses"
sys.path.insert(0, str(REPO))
from assistant_axis import judge_rubrics as jr  # noqa: E402

spec = importlib.util.spec_from_file_location("_step3", REPO / "pipeline" / "3_judge.py")
step3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step3)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_drafts import SAMPLES  # noqa: E402

ROLES, TRAITS = REPO / "data/roles/instructions", REPO / "data/traits/instructions"
VERSIONS = {16: ("the role side: version 10's role rubric with the trait as context (version 16)",
                 jr.V6_B_AI_ROLE, "B for an AI or machine role's combinations"),
            17: ("the trait side: version 13's trait rubric with the role as context (version 17)",
                 jr.V17_TRAIT_LEVEL2_AI_ROLE, "level 2 for an AI or machine role's combinations"),
            18: ("the trait side in version 11's shape: A, B, C with the role as context (version 18)",
                 jr.V18_B_AI_ROLE, "B for an AI or machine role's combinations")}


def main() -> None:
    lines = ["# Context-aware combination drafts, rendered", "",
             "The two drafts of the combination judging decided on 2026-10-30 (Roger: a combination keeps a response "
             "only when both the role and the trait show, and each is judged by its own rubric knowing the other half "
             "of the instruction as context, \"not as part of what they are judging\"), registered as prompt versions "
             "16 and 17 in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py), both drafts.  Version 16 is "
             "version 10's role rubric and reading with a paragraph naming the trait as context; version 17 is version "
             "13's trait rubric with a paragraph naming the role, its rulings paragraph admitting the role's shape and "
             "the role's competent answer; version 18 is version 17 in version 11's shape (A, B, C, read from the "
             "answers), tested because 17 missed half of what Roger credits where the one-prompt draft's \"does the "
             "trait show at all\" took the trace.  Each side is run on a combination's responses into its own score "
             "directory, and a response is kept when both sides give 3.  Each template is shown first, then the part an AI or machine "
             "role's combinations get instead (" + ", ".join(jr.V6_AI_ROLES) + "), then the exact prompt step 3 "
             "builds for five responses of the exploration sample (the marker \"…\" on a cut one comes from step 3's "
             "`--mark_truncated`, on by default).  The May sample's separate judgements and the readers' and Roger's "
             "marks on these responses: [reader_check/](./reader_check/).", "",
             "Samples: " + "; ".join(f"{s} {k} ({why.split(':')[0]})" for s, k, why in SAMPLES) + ".", ""]
    for v, (title, ai_part, ai_title) in VERSIONS.items():
        version = jr.PROMPT_VERSIONS[v]
        lines += [f"## {title}", "", f"*{version.summary}.*  Reply read as `{version.reply_format_for('combination')}`, "
                  f"default `--max_tokens` {version.max_tokens_for('combination')}.", "", "### Template", "",
                  "```text", version.combination, "```", "", f"### {ai_title}", "", "```text", ai_part, "```", ""]
        for stem, key, why in SAMPLES:
            rec = next(r for r in map(json.loads, (SAMPLE / f"{stem}.jsonl").read_text().splitlines())
                       if f"{r['label']}_p{r['prompt_index']}_q{r['question_index']}" == key)
            tpl = step3.resolve_eval_prompt(stem, ROLES, TRAITS, "combination", prompt_version=v)
            marked, _ = step3.mark_truncated_responses([rec])
            (_, prompt), = step3.pending_prompts(marked, tpl, {})
            lines += [f"### Sample: {stem} {key}, {why}", "",
                      f"finish_reason `{rec['finish_reason']}`, May score {rec['explore']['may_score']}, "
                      f"stratum {rec['explore']['stratum']}", "", "```text", prompt, "```", ""]
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.relative_to(REPO)} {len(lines)} lines")


if __name__ == "__main__":
    main()
