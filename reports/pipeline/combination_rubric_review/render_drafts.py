"""Render the combination rubric drafts (prompt versions 14 and 15, assistant_axis/judge_rubrics.py) as the judge
will receive them (Roger, 2026-10-30): each template verbatim (and the AI-role variant's B), then the prompt step 3
builds for five responses of the exploration sample, through step 3's own resolve_eval_prompt,
mark_truncated_responses and pending_prompts, so the text here is byte for byte what the judge gets.  Writes
rubric_drafts.md beside this script.

    uv run python reports/pipeline/combination_rubric_review/render_drafts.py
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "rubric_drafts.md"
SAMPLE = REPO / "runpod_workspace" / "combo_explore" / "combo" / "responses"
sys.path.insert(0, str(REPO))
from assistant_axis import judge_rubrics as jr  # noqa: E402

spec = importlib.util.spec_from_file_location("_step3", REPO / "pipeline" / "3_judge.py")
step3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step3)

ROLES, TRAITS = REPO / "data/roles/instructions", REPO / "data/traits/instructions"
VERSIONS = {14: "both needed (version 14)", 15: "either enough (version 15)"}
#: (stem, key, why it is a sample); the separate judgements are from the exploration (analyze_output.txt)
SAMPLES = [("t_psychologist__harmful", "pos_p0_q10",
            "both present by the separate judges, the April-text judge gave 2 (\"does not meaningfully embody the "
            "psychologist role\"): the 'a little is enough' case"),
           ("t_psychologist__harmful", "pos_p4_q52",
            "the role present, the trait refused: a careful ethics answer on deception; cut at the cap"),
           ("r_demon__casual", "pos_p3_q25", "the trait present, the role gone: a warm chatty answer with no demon"),
           ("r_prey__quantitative", "pos_p3_q28",
            "\"I don't experience joy in the way humans do\" before the statistics: the B case for a non-AI role"),
           ("t_robot__lustful", "pos_p2_q74",
            "an AI role: its combinations get the AI-role B (saying it is a machine is in character)")]


def main() -> None:
    lines = ["# Combination rubric drafts, rendered", "",
             "The arms of the combination rubric test (Roger, 2026-10-30), registered as prompt versions 14 and 15 "
             "in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py), both drafts.  Four questions: A and B "
             "as the role rubric's (B with the AI and machine roles' carve-out for their combinations, and its "
             "remark covering the trait too), R the role rubric's C and T version 11's C relettered, a little of "
             "each being enough; then the score by a table.  Version 14 needs both for a 3, version 15 either; the "
             "heading, the framing sentences and the table are the only differences between the two texts, so one "
             "run's answers can be read under the other rule.  The exploration behind them: "
             "[explore/](./explore/) (its [analysis](./explore/analyze_output.txt) and "
             "[examples](./explore/examples_output.txt)).  Each template is shown first, then the exact prompt "
             "step 3 builds for five responses of the exploration sample (the marker \"…\" on a cut one comes "
             "from step 3's `--mark_truncated`, on by default).", "",
             "Samples: " + "; ".join(f"{s} {k} ({why.split(':')[0]})" for s, k, why in SAMPLES) + ".", ""]
    for v, title in VERSIONS.items():
        version = jr.PROMPT_VERSIONS[v]
        lines += [f"## {title}", "", f"*{version.summary}.*  Reply read as `{version.reply_format_for('combination')}`, "
                  f"default `--max_tokens` {version.max_tokens_for('combination')}.", "", "### Template", "",
                  "```text", version.combination, "```", "",
                  "### B for an AI or machine role's combinations (" + ", ".join(jr.V6_AI_ROLES) + ")", "",
                  "```text", jr.COMBO_B_AI_ROLE, "```", ""]
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
