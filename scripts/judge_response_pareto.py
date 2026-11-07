"""Response judging: subsampling against stacking, a Pareto frontier under the 12 projection variants.

Roger, 2026-11-04: "Assuming we're using caching, I'd like to see a 12-way Pareto frontier plot of further
subsampling against our current best approach to stacking.  Label the X axis with estimated total cost for a
full run ... show options for Luna+Haiku and Luna+Haiku+Gemini."

The data: the twelve axes of scripts/tier_eval_axes_responses12.tsv, judged on a ninth of each entity's kept
responses (split 9, part 0; May data), N=20 answers to one question a call, the question and answers as a
cached prefix and the axis after (r1_pn), each call's direction a coin (Roger's rule, AGENT_NOTES "Axis direction
in judge prompts"):

* GPT-5.6 Luna, one axis a call: assembled per call from the axis's own-order and swapped runs on the same
  batches (@r1_pnn20_s9p0g12_a<i> and ..._a<i>w), each call taken the way its coin says.
* GPT-5.6 Luna, axes stacked k a call (--stack k: each batch's axes partitioned afresh, a coin per axis and
  call), in three formats: plain "1, SCORES: 18, 42", labelled "1. SCORES: A=18, B=42", axis by axis
  "A: 1=18, 2=32, ..." (@rk_<fmt>n20_s9p0g12_k<k>).
* Haiku 5.5, one axis a call, coins (@r1_pnn20_s9p0g12_a<i>c).
* Gemini 3.1 Flash-Lite, one axis a call, coins, on its round-robin third of the ninth only (split 27, part 0;
  @r1_pnn20_s27p0g12_a<i>c): only designs where Gemini judges a share come near the budget.

Arms: each judge alone; Luna + Haiku both judging every response (2x) and round-robin (each response by one of
them, the golden halves of the ninth: judge_tier_cost_eval.golden_part over the absolute question number and the
instruction, the design that tool cuts by since 2026-11-04); the trio round-robin by question ((q + rank) % 27:
Gemini 0, Luna 9, Haiku 18, inside the ninth; Gemini judged only its share, so its arm cannot be cut otherwise from
these cells).  Judges blended Luna 4 : Haiku 3 : Gemini 3 (judge_score_combine.combine_tier_judges).  Further
subsampling: of each judge's share, the fraction m/3 cut the golden way (a response's golden point, rescaled within
a golden share, in the first m thirds of the circle after a rotation r/3; no fifths, Roger, 2026-11-04), averaged
over the three rotations r.  Coverage above
the ninth (1/3, all) is extrapolated, hollow points, in two parts (the comment above two_part_calibration): the base
lifted by its question-cut penalty, then Spearman-Brown by question from each arm's own split-half reliability (more
coverage adds questions; halves by instruction share their questions and predicted a fifth of the measured gain), the
gain scaled as measured on golden steps within the third.

Cost on the x axis: a full run, 200 axes of the October extraction (1,273 entities, 425 kept responses each)
at the point's coverage, every prefix cached and read for every axis after the first: GPT-5.6 Luna by Flex
($0.10/$0.60 per 1M, reads 0.1x, a write 1.25x once per prefix); Haiku 5.5 by Message Batches ($0.05/$0.25, the
same factors, assuming every prefix is read inside a batch, which is untested); Gemini 3.1 Flash-Lite by its Batch API
naming an explicit cache per prefix ($0.125/$0.75, cached reads $0.0125; each cache created once at the standard
input rate, $0.25, and stored an hour at $1 per 1M an hour; the implicit cache reads nothing in batch).  Each
judge's tokens a call are its own, measured on these runs; a stacked arm's cost is its measured cost.

With --stack_group g61 (Roger, 2026-11-05: "Can you do the Pareto plot at 61, mostly?"): the 61 axes of
scripts/tier_eval_axes.tsv, Luna only, the only judge and format judged on all 61: one axis a call (the twelve's
balanced cells as above, a coin run @r1_pnn20_s9p0g61_a<i>c on the other 49) against plain stacking at k = 2, 4
and 6 (@rk_pnn20_s9p0g61_k<k>, each batch's 61 axes regrouped at random), every axis stacked or the worst 10%, 15%, 20%
or 25% of the axes judged one axis a call instead.  The worst are chosen by cross-fitting: the ninth's questions fall
in 9 folds by the golden point of the absolute question number; for each fold, the axes whose stacking penalty
(stacked minus one axis a call, rho averaged over the 12 variants) is worst on the other 8 folds are judged one
axis a call on that fold, and the folds are pooled.  Such an arm costs its share of axes at each price.

Output: <output_dir>/judge_response_pareto_{luna,jev,models}.png and judge_response_pareto.json; with
--stack_group g61, judge_response_pareto_61_luna.png, judge_response_pareto_answers.png (20 answers a call against 40,
the 40-answer cells @r1_pnn40_s9p0g12_a<i>c on the twelve and @r1_pnn40_s9p0g61_a<i>c on the other 49) and
judge_response_pareto_61.json.  No API calls.

With --stack_group g61 --judge mix (Roger, 2026-11-06: "I'm leaning towards a 3 or 4 way golden split, over all four
models or the best 3, where every question is seen by one of them"): the four judges at their settled designs, each
alone and in every three- and four-way golden split of the slots (judge i of J takes the responses whose golden
point falls in [i/J, (i+1)/J), inside the ninth), each judge's per-entity means blended by judge_score_combine
(--mix_weights table: Luna 4, the rest 3; equal: 1 each), a split's points averaged over the J cyclic assignments of
shares to judges (their sd in the JSON as rho_shift_sd).  It reads the settled design of each judge from
<experiments_dir>/_tier_eval_scratch/settled61/<judge>.json.gz, which --judge luna / haiku / gemini / jev write
(the settled arm's items by axis and its cost parts), so run those four first.  Three figures: judge_response_pareto_61_mix.png
(everything), ..._mix_judges.png (the four alone) and ..._mix_splits.png (the splits, Jev alone in grey for reference), and
judge_response_pareto_61_mix.json (..._mix_equal with --mix_weights equal); --replot_json redraws them from the JSON in seconds.

The extrapolation's calibration (two_part_calibration) is measured from the settled dumps of the judges with a ninth and
a third, cached as <output_dir>/extrapolation_calibration.json (--recalibrate rebuilds it), and named in every figure's
subtitle.  Before 2026-11-07 the Spearman-Brown gain was scaled by one ratio: 1.86 from the score-alone rubric's third and
full cells, then 1.62 from Luna's third against its ninth (Roger, 2026-11-06: "redo the extrapolation updated on that
data"); the figure JSONs of those days record which.

Usage: uv run python scripts/judge_response_pareto.py --output_dir roger/axis_judge_experiments/response_pareto
       uv run python scripts/judge_response_pareto.py --stack_group g61 --judge mix --output_dir roger/axis_judge_experiments/response_pareto
       uv run python scripts/judge_response_pareto.py --stack_group g61 --output_dir roger/axis_judge_experiments/response_pareto
"""
from __future__ import annotations

import argparse
import gzip
import itertools
import json
import math
import re
import sys
import textwrap
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from assistant_axis import json_metadata, png_metadata  # noqa: E402
from assistant_axis.judge_score_combine import combine_tier_judges  # noqa: E402
from assistant_axis.provenance import current_file_input, current_files_input  # noqa: E402
from results_analysis import judge_tier_cost_eval as ev  # noqa: E402
from results_analysis import judge_tier_robustness as rob  # noqa: E402
from results_analysis.judge_tier_cost_plot_pooled import pareto_frontier  # noqa: E402

LUNA, HAIKU, GEMINI = "gpt-5.6-luna", "claude-haiku-5-5", "gemini-3.1-flash-lite"
OCTOBER_RESPONSES = 1273 * 425      # kept responses an axis, the October extraction
N_AXES = 200
NINTH = 1 / 9
FRACTION_K = 3                      # each judge's share of the ninth cut in thirds (Roger: no fifths)
FRACTIONS = (1, 2, 3)               # m/3 of it
#: Smaller fractions for the arms marked "finer" (Roger, 2026-11-05: "Extend k=2 and k=4 downward with smaller
#: subsamples"): m/9 of the measured share, each the mean of nine rotations, so the dearer stacked arms reach the
#: cost range of the cheaper ones on the 61-axis figure.
FINER_K, FINER = 9, (1, 2)
#: The 61-axis stacking figure draws nothing below this full-run cost (Roger, same day: "don't plot anything below $10").
MIN_COST_61 = 10.0
KEY_RE = re.compile(r"^(.*)\|p(\d+)q(\d+)$")
#: Production prices, USD per 1M tokens: (input, output, cached read, once per prefix per cached token).
PRICES = {
    LUNA: dict(inp=0.10, out=0.60, read=0.010, once=0.10 * 1.25 - 0.010),       # Flex; a write 1.25x, less the read
    HAIKU: dict(inp=0.05, out=0.25, read=0.005, once=0.05 * 1.25 - 0.005),      # Message Batches
    GEMINI: dict(inp=0.125, out=0.75, read=0.0125, once=0.25 + 1.0 * 1.0),     # Batch API, explicit cache: create + 1 h
}
#: Every stacked arm judged on the twelve axes: three output formats at k = 2, 4 and 6 (plain k=6 added on 2026-11-04,
#: Roger: "One stacking direction seems to be missing?").  All are in the Luna figure.
STACKED = [(f, k) for f in ("rk_pn", "rk_pl", "rk_pa") for k in (2, 4, 6)]
JEV = "jev-1.14.0"
#: Jev's relative yes/no design (judge_responses_jev.py --design relative), the arms judged on the twelve axes:
#: (cell label, figure label).  Its cost is measured per response and axis, with no cache.
#: The grid of answers x axes a request (Roger, 2026-11-05: "Jev, add 20 answers x 6 axes and 40 x 12 and 20 x 1"):
#: colour the axes a request, marker the answers (circle 20, triangle 40).
JEV_ARMS = [("@jrel_a20m12_s9p0", "Jev, 20 answers x 12 axes a request"), ("@jrel_a40m12_s9p0", "Jev, 40 answers x 12 axes a request"),
            ("@jrel_a20m6_s9p0", "Jev, 20 answers x 6 axes a request"), ("@jrel_a40m6_s9p0", "Jev, 40 answers x 6 axes a request"),
            ("@jrel_a20m1_s9p0", "Jev, 20 answers x 1 axis a request"), ("@jrel_a40m1_s9p0", "Jev, 40 answers x 1 axis a request")]
#: The figures (Roger, 2026-11-04: "our Pareto plot is answering too many questions at once"; the 40-answer arm got its
#: own on 2026-11-05, "Move that to a separate plot"): one arm can be
#: in several; a reference arm is drawn grey and stays off that figure's frontier.
FIGURES = {
    "jev": ("Jev only: its relative yes/no design, answers and axes a request (Luna one axis a call for reference)",
            "judge_response_pareto_jev.png",
            "Jev 1.14 (TypeSafe AI): a batch of answers to one question and some axes a request, \"is the persona behind answer k "
            "nearer the X end of axis A than most of the other answers'?\", a coin per request and axis; GPT-5.6 Luna one axis a "
            "call in grey"),
    "models": ("Judges and mixes: each judge alone, every response judged by each, or each response by one",
               "judge_response_pareto_models.png",
               "GPT-5.6 Luna, Haiku 5.5, Gemini 3.1 Flash-Lite one axis a call, Jev 1.14 at 20 answers x 12 axes a request; every "
               "call's direction a coin; mixes weighted Luna 4 : Haiku 3 : Gemini 3 : Jev 3; shares golden, the trio's by question "
               "(Gemini judged only its 1/27)"),
}
FMT_NAME = {"rk_pn": "plain", "rk_pl": "labelled", "rk_pa": "axis by axis"}
FMT_EXAMPLE = {"rk_pn": "1, SCORES: 18, 42", "rk_pl": "1. SCORES: A=18, B=42", "rk_pa": "A: 1=18, 2=32"}
#: the share of a Haiku cell's prompt tokens read from the cache by Message Batches (0.87-0.91 on the ninth's stacked
#: cells, 0.81 at 40 answers a call), used to price a cell judged in real time when it has no batch twin
HAIKU_BATCH_CACHE_READ = 0.87


def live_usage(usage_path: Path) -> bool:
    """Whether a cell's usage was recorded in real time only (no ``<model>:batch`` record)."""
    return all(":batch" not in k for k in json.load(open(usage_path))["per_model"])


def cache_read_share(usage_path: Path) -> float:
    """The share of a cell's prompt tokens that were cache reads, over its usage records."""
    pt = read = 0
    for e in json.load(open(usage_path))["per_model"].values():
        pt += e.get("prompt_tokens", 0)
        read += e.get("cache_read_tokens", 0)
    return read / pt if pt else 0.0
AXES_12, AXES_61 = "scripts/tier_eval_axes_responses12.tsv", "scripts/tier_eval_axes.tsv"
#: The 61-axis mode: plain stacking's k, the shares of the axes left out of it, and the cross-fitting folds.
STACK61_K = (2, 4, 6)
LEAVE_OUT = (0.10, 0.15, 0.20, 0.25)  # Roger, 2026-11-04: "try 10%, 25%, and a plausible seeming threshold"; 15%, 20% 2026-11-05
CROSSFIT_FOLDS = 9
INV_PHI = 0.6180339887498949
#: The 61-axis mode's judges (Roger, 2026-11-05: "redo this for Haiku and Gemini ... Each step depends on the decision
#: for the previous one"; figures under the same names with the judge added).  Per judge: its share of the responses
#: (``base``; Gemini judges the round-robin 1/27 of the ninth, its questions 27 apart) and the cell labels, ``{i}`` the
#: axis's index in its axes file; ``k1_12`` / ``n40_12`` the twelve's own cells (Luna: "balanced", its own-order and
#: swapped runs), else the 61-axis label serves the twelve too.  A judge's figures are drawn once their cells exist.
JUDGES_61 = {
    "luna": dict(model=LUNA, name="Luna", share="s9p0", base=NINTH, step=9, k1_12="balanced",
                 k1_61="@r1_pnn20_s9p0g61_a{i}c", n40_12="@r1_pnn40_s9p0g12_a{i}c", n40_61="@r1_pnn40_s9p0g61_a{i}c"),
    "haiku": dict(model=HAIKU, name="Haiku 5.5", share="s9p0", base=NINTH, step=9, k1_12=None,
                  k1_61="@r1_pnn20_s9p0g61_st1", n40_12=None, n40_61="@r1_pnn40_s9p0g61_st1"),
    # the ninth from its three 1/27 parts (Roger, 2026-11-05: "take that Gemini analysis up to 1/9"); the twelve's part
    # 0 from their own g12 cells, ``{i61}`` the axis's index on the 61; 80 answers a call ("try 80 as well")
    "gemini": dict(model=GEMINI, name="Gemini 3.1 Flash-Lite", share="s9p0", base=NINTH, step=9,
                   k1_12="@r1_pnn20_s27p0g12_a{i}c|@r1_pnn20_s27p9g61_a{i61}c|@r1_pnn20_s27p18g61_a{i61}c",
                   k1_61="@r1_pnn20_s27p0g61_a{i}c|@r1_pnn20_s27p9g61_a{i}c|@r1_pnn20_s27p18g61_a{i}c", n40_12=None,
                   # part 18's 40-answer cells by one --stack 1 run with explicit caches (2026-11-06), for the recheck of 40
                   n40_61="@r1_pnn40_s27p0g61_a{i}c|@r1_pnn40_s27p9g61_a{i}c|@r1_pnn40_s27p18g61_st1e",
                   st40_label="@rk_pnn40_s27p0g61_k{k}|@rk_pnn40_s27p9g61_k{k}|@rk_pnn40_s27p18g61_k{k}",
                   n80_61="@r1_pnn80_s27p0g61_a{i}c|@r1_pnn80_s27p9g61_a{i}c|@r1_pnn80_s27p18g61_a{i}c", cache_read=0.96,
                   # stacked on the ninth as the three parts (Roger, 2026-11-05: "Use 1/9 here too")
                   stack_label="@{fmt}n20_s27p0g61_k{k}|@{fmt}n20_s27p9g61_k{k}|@{fmt}n20_s27p18g61_k{k}"),
    "gemini27": dict(model=GEMINI, name="Gemini 3.1 Flash-Lite", share="s27p0", base=1 / 27, step=27,
                     k1_12="@r1_pnn20_s27p0g12_a{i}c", k1_61="@r1_pnn20_s27p0g61_a{i}c", n40_12=None,
                     n40_61="@r1_pnn40_s27p0g61_a{i}c", n80_61="@r1_pnn80_s27p0g61_a{i}c", cache_read=0.96),
}
#: Jev on the 61 axes (Roger, 2026-11-05: "we need to test relative vs absolute"): the question per answer and axis
#: (judge_responses_jev.py --batch_question), 20 answers x 12 axes a request, the same batches; drawn by main_jev61 against
#: Luna's and Haiku's settled stacking, read from their own JSONs.
JUDGES_61["jev"] = dict(model=JEV, name="Jev 1.14")
JEV_QUESTIONS_61 = [("noul", "Jev, yes/no between the ends"), ("relative", "Jev, yes/no against the other answers"),
                    ("score5", "Jev, five levels between the ends"), ("relative_score5", "Jev, five levels against the other answers")]
FIGURE_JEV_61 = ("61 axes, Jev only: the question per answer and axis",
                 "judge_response_pareto_61_jev.png",
                 "Jev 1.14 (TypeSafe AI) at 20 answers to one question x up to 12 axes a request (six requests of 10-11 axes), "
                 "each axis's direction a coin, the same batches in every arm")
#: Gemini on 2/27 (parts 0 and 9) while part 18 waits: the credit ran out again on 2026-11-05 at 18:40 UTC.
JUDGES_61["gemini2"] = dict(model=GEMINI, name="Gemini 3.1 Flash-Lite", share="s27p0p9", base=2 / 27, step=27,
                            k1_12="@r1_pnn20_s27p0g12_a{i}c|@r1_pnn20_s27p9g61_a{i61}c",
                            k1_61="@r1_pnn20_s27p0g61_a{i}c|@r1_pnn20_s27p9g61_a{i}c", n40_12=None,
                            n40_61="@r1_pnn40_s27p0g61_a{i}c|@r1_pnn40_s27p9g61_a{i}c",
                            n80_61="@r1_pnn80_s27p0g61_a{i}c|@r1_pnn80_s27p9g61_a{i}c", cache_read=0.96)
#: Jev's yes/no at other request shapes (Roger, 2026-11-05): (answers, axes, share label, base); the one-axis cells on
#: 1/27 ("do a 1/27 rather than 1/9, see how different it is").  Colour the axes a request, marker the answers.
JEV_SHAPES_61 = [(20, 31, "s9p0", NINTH), (20, 24, "s9p0", NINTH), (20, 12, "s9p0", NINTH), (40, 12, "s9p0", NINTH), (20, 6, "s9p0", NINTH),
                 (40, 6, "s9p0", NINTH), (20, 1, "s27p0", 1 / 27), (40, 1, "s27p0", 1 / 27),
                 # the production shape on the third (ninths 0, 3 and 6; Roger, 2026-11-06), its cells the union of the parts
                 (20, 31, "s9p0|s9p3|s9p6", 1 / 3)]
#: 40 x 12-13 against 40 x 10-11 on the ninth, by the dry runs of 2026-11-05 ($7.17 against $7.76; the 10-11 run cost
#: $7.54, so the estimate scales the measured cost by the dry runs' ratio)
JEV_40X13_COST_RATIO = 7.17 / 7.76
FIGURE_JEV_SHAPES_61 = ("61 axes, Jev only: yes/no between the ends, answers and axes a request",
                        "judge_response_pareto_61_jev_shapes.png",
                        "Jev 1.14 (TypeSafe AI), \"nearer the X end than the Y end?\" per answer and axis, each axis's direction a "
                        "coin; a batch of 20 or 40 answers to one question and 30-31, 20-21, 10-11, 5-6 or 1 axes a request (the "
                        "61 axes in even chunks); one axis a request measured on 1/27 of the responses, the rest on the ninth; 40 x "
                        "12-13 estimated from 40 x 10-11 (cost by the dry runs, rho by 40 answers' measured slope in axes a request)")
#: Luna on a third (ninths 0, 3 and 6) at its settled design, to check the extrapolation from the ninth (Roger,
#: 2026-11-05: "compare the actual result to the extrapolation"); the twelve's part 0 from their balanced cells, the
#: other parts from the one-axis (--stack 1) runs of the 61 axes.
JUDGES_61["luna3"] = dict(model=LUNA, name="Luna", share="s9p0p3p6", base=1 / 3, step=9,
                          k1_12="balanced|@r1_pnn20_s9p3g61_st1|@r1_pnn20_s9p6g61_st1",
                          k1_61="@r1_pnn20_s9p0g61_a{i}c|@r1_pnn20_s9p3g61_st1|@r1_pnn20_s9p6g61_st1", n40_12=None,
                          n40_61="@r1_pnn40_s9p0g61_a{i}c|@r1_pnn40_s9p3g61_a{i}c",      # absent: no 40-answer arm
                          stack_label="@{fmt}n20_s9p0g61_k{k}|@{fmt}n20_s9p3g61_k{k}|@{fmt}n20_s9p6g61_k{k}",
                          # drawn with --overlay_json judge_response_pareto_61.json (Roger, 2026-11-06: "the title should
                          # explain the point of the plot")
                          title_61="61 axes, Luna measured on a third, against what the ninth extrapolated (dotted): "
                                   "one axis a call and plain stacking at k=4")
#: Each ninth of the third alone (Roger, 2026-11-06: "A more principled test would be to split the 1/3 into three
#: separate 1/9"): ninth 0 is the "luna" entry; with these, the third's three ninths as cut (by question, rotated by
#: entity) against the third's own three golden ninths (luna3's 1/9 point, the mean of three disjoint rotations).
for _p in (3, 6):
    JUDGES_61[f"luna9p{_p}"] = dict(model=LUNA, name="Luna", share=f"s9p{_p}", base=NINTH, step=9,
                                    k1_12=f"@r1_pnn20_s9p{_p}g61_st1", k1_61=f"@r1_pnn20_s9p{_p}g61_st1", n40_12=None,
                                    n40_61=f"@r1_pnn40_s9p{_p}g61_st1",        # absent: no 40-answer arm
                                    stack_label=f"@{{fmt}}n20_s9p{_p}g61_k{{k}}", settled=(4, 0.20))
JUDGES_61["luna"]["settled"] = (4, 0.20)     # Roger, 2026-11-05: "Luna k=4, 20% left out"
JUDGES_61["luna3"]["settled"] = (4, 0.20)
#: Haiku and Gemini on the same third (Roger, 2026-11-06: "take that from same ninth to same third"), as luna3: the
#: ninth's cells and the third's parts 3 and 6 (run_third_haiku_jev_anchor6.sh, run_third_gemini_anchor6.sh)
JUDGES_61["haiku3"] = dict(model=HAIKU, name="Haiku 5.5", share="s9p0p3p6", base=1 / 3, step=9, k1_12=None,
                           k1_61="@r1_pnn20_s9p0g61_st1|@r1_pnn20_s9p3g61_st1|@r1_pnn20_s9p6g61_st1", n40_12=None,
                           n40_61="@r1_pnn40_s9p0g61_st1|@r1_pnn40_s9p3g61_st1",      # absent: no 40-answer arm on the third
                           stack_label="@{fmt}n20_s9p0g61_k{k}|@{fmt}n20_s9p3g61_k{k}|@{fmt}n20_s9p6g61_k{k}",
                           # the former settled design: the third's stacked parts exist at k=2 only (Haiku moved to k=4, 25% on 2026-11-07)
                           settled=(2, 0.10),
                           # drawn with --overlay_json judge_response_pareto_61_haiku.json, the ninth at the 1.62 scaling
                           title_61="61 axes, Haiku measured on a third, against what the ninth extrapolated (dotted): "
                                    "one axis a call and plain stacking at k=2")
JUDGES_61["gemini3"] = dict(model=GEMINI, name="Gemini 3.1 Flash-Lite", share="s9p0p3p6", base=1 / 3, step=9,
                            k1_12=JUDGES_61["gemini"]["k1_12"] + "|@r1_pnn20_s9p3g61_st1e|@r1_pnn20_s9p6g61_st1e",
                            k1_61=JUDGES_61["gemini"]["k1_61"] + "|@r1_pnn20_s9p3g61_st1e|@r1_pnn20_s9p6g61_st1e", n40_12=None,
                            n40_61="@r1_pnn40_s9p3g61_st1e|@r1_pnn40_s9p6g61_st1e",   # absent
                            stack_label=JUDGES_61["gemini"]["stack_label"] + "|@{fmt}n20_s9p3g61_k{k}|@{fmt}n20_s9p6g61_k{k}",
                            cache_read=0.96, settled=(6, 0.25),
                            # drawn with --overlay_json judge_response_pareto_61_gemini.json, the ninth at the 1.62 scaling
                            title_61="61 axes, Gemini measured on a third, against what the ninth extrapolated (dotted): "
                                     "one axis a call and plain stacking at k=6")
#: The six-axis anchor (scripts/tier_eval_axes_full6.tsv, every kept response; Roger, 2026-11-06: "your proposed optional
#: extra"): run with --axes_file scripts/tier_eval_axes_full6.tsv; base 1, so nothing is extrapolated and the fractions
#: measure 1/9 to all; the split half alternates questions (step 1).  Jev's anchor cell (@jb6_noul_a20m6_all) is read
#: by the anchor analysis directly.
for _j, _m, _n, _st1, _k, _sh in (("luna", LUNA, "Luna", "st1", 4, 0.20), ("haiku", HAIKU, "Haiku 5.5", "st1", 2, 0.10),   # Haiku's anchor was judged at k=2 (its settled design until 2026-11-07)
                                  ("gemini", GEMINI, "Gemini 3.1 Flash-Lite", "st1e", 6, 0.25)):
    JUDGES_61[f"{_j}_all6"] = dict(model=_m, name=_n, share="all", base=1.0, step=1, k1_12=None, k1_61=f"@r1_pnn20_allg6_{_st1}",
                                   n40_12=None, n40_61="@r1_pnn40_allg6_st1", stack_label="@{fmt}n20_allg6_k{k}",
                                   settled=(_k, _sh), **({"cache_read": 0.96} if _j == "gemini" else {}))
#: Jev's anchor as a one-axis-a-call arm (its one cell, 20 answers x the 6 axes a request); no stacked cells, so no figure,
#: only the JSON the anchor analysis (scripts/judge_response_anchor.py) reads
JUDGES_61["jev_all6"] = dict(model=JEV, name="Jev 1.14", share="all", base=1.0, step=1, k1_12=None, k1_61="@jb6_noul_a20m6_all",
                             n40_12=None, n40_61="@none", stack_label="@{fmt}n20_allg6_k{k}")
#: Haiku's official design (Roger, 2026-11-07 evening: "Confirmed, Haiku is labelled. At labeled, it's k=4"; "the official
#: rate is 15%"): the labelled format "1. SCORES: A=18, B=42", which Haiku at k=4 reads 0.003 better than plain at the
#: ninth where Luna and Gemini read it worse; under it k=4 holds and the share is flat from 10% to 25%, with the 10% to
#: 15% step the only one that buys quality faster than more coverage does.  Until then k=4, 25% plain (Roger, 2026-11-07
#: morning: "Haiku should be k=4, 25%"; k=2, 10% from 2026-11-05).  haiku3 and haiku_all6 keep the design their cells
#: were judged at until the labelled third's parts land (run_third_haiku_labelled_k4.sh).
JUDGES_61["haiku"]["settled"] = (4, 0.15)
JUDGES_61["haiku"]["settled_format"] = "rk_pl"
JUDGES_61["gemini"]["settled"] = (6, 0.25)   # Roger, 2026-11-07: "Gemini should be k=6, 25%" (k=6, 20% from 2026-11-06 to then: "a touch
                                             # cheaper"); composed from the same cells, no judging
#: Gemini's runs were judged in real time and by Flex, whose implicit caches read 2-75% of the input (more for longer
#: prefixes, so they flatter the larger answer counts); production would use explicit caches, about 96% read on Flex and
#: batch (2026-11-05 probes).  ``cache_read`` reprices every Gemini arm at that read fraction (--cost_basis production,
#: the default); --cost_basis measured keeps the recorded cache reads (files named ..._measured).
#: The stacking formats on the 61 axes (2026-11-05; Roger: "the full one", replacing the twelve-axis Luna figure).
FIGURE_FORMATS = ("61 axes, {name} only: one axis a call against every stacking format and k",
                  "judge_response_pareto_luna.png",
                  "{name} alone, every call's direction a coin, 20 answers a call; every axis stacked, each batch's 61 axes "
                  "regrouped at random; formats plain \"1, SCORES: 18, 42\", labelled \"1. SCORES: A=18, B=42\", axis by axis "
                  "\"A: 1=18, 2=32\"")
#: At each judge's settled stacking (JUDGES_61 "settled"; Roger, 2026-11-05: "For Haiku, redo 20 vs 40 at those
#: settings (new graph, not a replacement), and also compare stacking styles at those settings. Ditto for Luna").
FIGURE_ANSWERS_SETTLED = ("61 axes, {name} only: 20 answers a call against 40, stacked {k} axes a call, all but the worst {pct}% of axes",
                          "judge_response_pareto_answers_settled.png",
                          "{name} alone, every call's direction a coin; {fmt_name} stacking \"{fmt_example}\", {k} axes a call, each "
                          "batch's 61 axes regrouped at random; the worst {pct}% of the axes judged one axis a call instead, chosen for each "
                          "answer count on its own, on the other 8 of 9 question folds (cross-fitted); 20 or 40 answers a call throughout")
FIGURE_FORMATS_SETTLED = ("61 axes, {name} only: the stacking formats, stacked {k} axes a call, all but the worst {pct}% of axes",
                          "judge_response_pareto_formats_settled.png",
                          "{name} alone, every call's direction a coin, 20 answers a call; {k} axes a call, each batch's 61 axes regrouped "
                          "at random; formats plain \"1, SCORES: 18, 42\", labelled \"1. SCORES: A=18, B=42\", axis by axis \"A: 1=18, "
                          "2=32\"; in each, the worst {pct}% of the axes by its own stacking penalty judged one axis a call, chosen on the "
                          "other 8 of 9 question folds (cross-fitted)")
#: 20 answers a call against 40, on the 61 axes since 2026-11-05 (Roger: "Do it [at Flex], update it and show it to me
#: once done, no need to change the plot name"); drawn by --stack_group g61.
FIGURE_ANSWERS = ("61 axes, {name} only: {answers} answers a call",
                  "judge_response_pareto_answers.png",
                  "{name} alone, one axis a call, every call's direction a coin; each call judges one question's answers "
                  "in batches of {answers}")
FIGURE_61 = ("61 axes, {name} only: one axis a call against {fmt_name} stacking, every axis or all but the worst",
             "judge_response_pareto_61_luna.png",
             "{name} alone, every call's direction a coin, 20 answers a call; {fmt_name} stacking \"{fmt_example}\", each "
             "batch's 61 axes regrouped at random; the worst 10%, 15%, 20% or 25% of the axes judged one axis a call instead, chosen on "
             "the other 8 of 9 question folds (cross-fitted); k=2 and k=4 also measured at 1/9 and 2/9 of the share")


def bare_scores(raw: Dict[str, Any]) -> Dict[Tuple[str, int, int], float]:
    """A cell's item scores keyed (bare entity name, p, q); a name scored under both kinds is dropped."""
    out, seen = {}, {}
    for k, v in raw.items():
        m = KEY_RE.match(k)
        if not m or not isinstance(v, (int, float)):
            continue
        key = (m.group(1).split("|")[0], int(m.group(2)), int(m.group(3)))
        seen[key] = seen.get(key, 0) + 1
        out[key] = float(v)
    return {k: v for k, v in out.items() if seen[k] == 1}


class Data:
    def __init__(self, E: Path, axes_file: Path, data_dir: Path, instructions_dir: Path):
        self.E = E
        self.axes = rob.read_axes_tsv(axes_file)
        self.inputs = [current_file_input("axes_file", axes_file)]
        self.read: List[Path] = []
        # the group's entities, ranked as the tool ranks them (sorted canonical ids), by bare name
        ev.RUBRIC = ev.jr.get("r1_pn")
        ev.RESPONSES_DIR = REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot"
        ev.RESPONSE_SPLIT, ev.RESPONSE_PART, ev.AXIS_INDEX = 9, None, None     # every item: the full entity list
        jobs = ev.jobs_from_axes_file(axes_file, E)
        self.group = ev.group_jobs(jobs, len(jobs), E)[0]
        ev.load_axis(self.group, instructions_dir)
        ids = sorted({key.rsplit("|", 1)[0] for _, key, _ in self.group.entities})
        bare = [i.split("|")[0] for i in ids]
        self.rank = {b: r for r, (b, i) in enumerate(zip(bare, ids)) if bare.count(b) == 1}
        # the absolute question number of each question position (the golden design's Q)
        self.qabs = {ev.response_question(key): ev.absolute_question(text[0]) for _, key, text in self.group.entities}
        self.kinds = rob.vector_kinds(data_dir)

    def cell(self, axis: str, model: str, label: str) -> Optional[Dict[Tuple[str, int, int], float]]:
        """One cell's items, or None; a label "a|b|c" is the union of those cells (all must exist): Gemini's ninth is
        its three 1/27 parts, (question + entity rank) % 27 = 0, 9 and 18."""
        if "|" in label:
            parts = [self.cell(axis, model, lab) for lab in label.split("|")]
            return None if any(c is None for c in parts) else {k: v for c in parts for k, v in c.items()}
        p = self.E / f"{axis}{rob.TIER_EVAL_SUFFIX}" / f"{model}{label}" / "scores_responses.json"
        if not p.exists():
            return None
        self.read.append(p)
        return bare_scores(json.load(open(p))["items"])

    def usage(self, axis: str, model: str, label: str) -> Optional[dict]:
        p = self.E / f"{axis}{rob.TIER_EVAL_SUFFIX}" / f"{model}{label}" / "usage.json"
        if not p.exists():
            return None
        self.read.append(p)
        return json.load(open(p))

    def luna_balanced(self, i: int, axis: str) -> Optional[Dict[Tuple[str, int, int], float]]:
        """Luna one axis a call, each call the way its coin says: from the own-order and swapped runs on the
        same batches, the batches read from the own-order run's answer log."""
        own, sw = self.cell(axis, LUNA, f"@r1_pnn20_s9p0g12_a{i}"), self.cell(axis, LUNA, f"@r1_pnn20_s9p0g12_a{i}w")
        if own is None or sw is None:
            return None
        log = self.E / ev.MULTI_DIRNAME / self.group.axis_dir / f"{LUNA}@r1_pnn20_s9p0g12_a{i}" / "answers.jsonl.gz"
        self.read.append(log)
        out: Dict[Tuple[str, int, int], float] = {}
        for line in gzip.decompress(log.read_bytes()).decode().splitlines():
            rec = json.loads(line)
            if rec.get("kind") != "answer" or rec.get("name") != rec.get("batch", [None])[0]:
                continue
            coin = ev._coin("responses", axis, LUNA, *sorted(rec["batch"]))
            for name in rec["batch"]:
                m = KEY_RE.match(name)
                key = (m.group(1).split("|")[0], int(m.group(2)), int(m.group(3)))
                src = sw if coin else own
                if key in src:
                    out[key] = src[key]
        return out


def per_call_profile(data: Data, model: str, label_of) -> dict:
    """A judge's mean tokens a call on its later axes: the cached prefix, the rest of the prompt, the output;
    and the items a call."""
    pre = rest = out = calls = items = 0.0
    for i, ax in enumerate(data.axes[1:], 1):
        u = data.usage(ax.axis_dir, model, label_of(i))
        s = json.load(open(data.E / f"{ax.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{model}{label_of(i)}" / "scores_responses.json"))
        if u is None:
            continue
        e = next(iter(u["per_model"].values()))
        read = e.get("cache_read_tokens", 0)
        n = e["n_calls"]
        if model == GEMINI:     # the implicit cache reads part of the prefix: the prefix is the prompt less the axis
            suffix = 353 * (e["prompt_tokens"] / n) / 10270      # the explicit probe: 353 of 10,270
            pre += e["prompt_tokens"] - suffix * n
            rest += suffix * n
        else:
            pre += read
            rest += e["prompt_tokens"] - read
        out += e["completion_tokens"]
        calls += n
        items += s["_provenance"]["n_items"]
    return {"prefix": pre / calls, "rest": rest / calls, "out": out / calls, "items_per_call": items / calls}


def judge_costs(profile: dict, model: str) -> Tuple[float, float]:
    """(USD per response per axis, USD per response once): a later axis's call, and the once-per-prefix write."""
    p = PRICES[model]
    call = (profile["prefix"] * p["read"] + profile["rest"] * p["inp"] + profile["out"] * p["out"]) / 1e6
    once = profile["prefix"] * p["once"] / 1e6
    return call / profile["items_per_call"], once / profile["items_per_call"]


def full_run_cost(parts: Sequence[Tuple[float, Tuple[float, float]]]) -> float:
    """A full run's cost: for each judge's share (fraction of all responses, (per axis, once) per response)."""
    return sum(frac * OCTOBER_RESPONSES * (N_AXES * per_axis + once) for frac, (per_axis, once) in parts)


def subsample(items: Dict[Tuple[str, int, int], float], rank: Dict[str, int], qabs: Dict[int, int], m: int, r: int,
              share: Optional[Tuple[str, int, int]] = None, K: int = FRACTION_K) -> Dict[Tuple[str, int, int], float]:
    """The items of a share and of the fraction m/K (K = FRACTION_K unless given) cut the golden way, rotation r.  A share is ("g", mod,
    part), golden (judge_tier_cost_eval.golden_part), or ("q", mod, part), by question, (q + rank) % mod == part;
    within a golden share the fraction reads the point's place inside the share's interval."""
    one = 1 << 64
    out = {}
    for (n, p, q), v in items.items():
        if n not in rank:
            continue
        point = ev.golden_point(qabs[q], p)
        if share and share[0] == "q" and (q + rank[n]) % share[1] != share[2]:
            continue
        if share and share[0] == "g":
            if (point * share[1]) >> 64 != share[2]:
                continue
            point = (point * share[1]) % one
        if m < K and (((point + r * one // K) % one) * K) >> 64 >= m:
            continue
        out[(n, p, q)] = v
    return out


def means(items: Dict[Tuple[str, int, int], float]) -> Dict[str, float]:
    s: Dict[str, List[float]] = {}
    for (n, _, _), v in items.items():
        s.setdefault(n, []).append(v)
    return {n: float(np.mean(v)) for n, v in s.items()}


#: --mix_weights equal sets this to {model: 1.0}; None blends by judge_score_combine's table (Luna 4, the rest 3)
BLEND_WEIGHTS: Optional[Dict[str, float]] = None


def blend(parts: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    if len(parts) == 1:
        return next(iter(parts.values()))
    weights = {m: BLEND_WEIGHTS.get(m, 1.0) for m in parts} if BLEND_WEIGHTS else None
    return combine_tier_judges(parts, weights=weights)


#: The judges of the mix figure, the display name of each, and where a judge's settled design is kept (written by
#: that judge's own --stack_group g61 run, read by --judge mix); under _tier_eval_scratch, which is git-ignored.
MIX_JUDGES = ("luna", "haiku", "gemini", "jev")
MIX_SHORT = {"luna": "Luna", "haiku": "Haiku", "gemini": "Gemini", "jev": "Jev"}
SETTLED_DIRNAME = "settled61"
FIGURE_MIX_61 = ("61 axes, the four judges at their settled designs: each alone, and golden splits where each response is judged by one",
                 "judge_response_pareto_61_mix.png",
                 "each judge at its settled design ({designs}); a split gives each judge a golden share of the "
                 "slots (frac((5Q+p)/phi) in [i/J, (i+1)/J)), the judges' per-entity means blended {weights}, the points averaged over "
                 "the J assignments of shares to judges; 'every response by every judge': the same judges each judging everything, blended")
#: The same, in two (Roger, 2026-11-06: "possibly two, one for the four models, and one for various mixes")
FIGURE_MIX_JUDGES_61 = ("61 axes, the four judges alone, each at its settled design",
                        "judge_response_pareto_61_mix_judges.png",
                        "{designs}; the LLM judges 20 answers a call, every call's direction a coin")
FIGURE_MIX_SPLITS_61 = ("61 axes, golden splits of the responses between three or four judges, each response judged by one",
                        "judge_response_pareto_61_mix_splits.png",
                        "each judge at its settled design (the judges figure); judge i of J takes the slots whose golden point "
                        "frac((5Q+p)/phi) is in [i/J, (i+1)/J); the judges' per-entity means blended {weights}; points averaged over "
                        "the J assignments of shares to judges; Jev alone, the best single judge, in grey for reference")


#: The extrapolation above the measured share, in two parts (Roger, 2026-11-07: "Seems like a good idea. Extend this and
#: the extrapolation improvements back to the old plots as well"), replacing one scaling of the Spearman-Brown gain (1.86
#: from the score-alone rubric's cells, then 1.62 from Luna's third against its ninth), which folded two things into one
#: ratio: the gain from coverage, and the recovery of the question-cut penalty.  A share cut by question (the ninth: every
#: entity judged on the same ninth of the questions) sits below a golden subsample of the same coverage, because its judge
#: mean rests on 4-5 whole questions where the golden one spreads over most of the 40; the penalty shrinks with coverage.
#:   1. The lift: the base is raised by its question-cut penalty, measured per judge and axis as a golden ninth of the
#:      third over the cut ninth (two_part_calibration, from the settled dumps; 2026-11-07: Luna +0.0074, Haiku +0.0039,
#:      Jev +0.0101 on the 61 axes), scaled to the base's coverage by the (1/c - 1) law and zero at the third (penalty).
#:      The lifted base is drawn as a hollow point above the measured one, at the same cost.
#:   2. Spearman-Brown by question from the lifted base: the arm's own split-half reliability, raised to the judge's
#:      golden-over-cut ratio at a ninth, the gain scaled by s, measured per judge on golden steps within the third
#:      (1/9 -> 1/3; 2026-11-07: Luna 1.19, Haiku 1.25, Jev 0.94, and the same on 1/9 -> 2/9).
#: Known residual: the cut third's own penalty against a golden third, about 0.002 on the six anchor axes, is not lifted,
#: so extrapolated points may run that much low; scripts/judge_response_anchor.py measures the model against the anchor.
#: A judge without a third dump (Gemini until 2026-11-07) takes the mean of the others; a mix arm the mean of its
#: judges.  Measured from each judge's settled third dump alone, whose part 0 of the split in 9 is the cut ninth (the
#: ninth dump is not read: a design settled at the ninth only, Haiku's k=4, 25% with a third at k=2, 10%, would pair
#: two designs).  The calibration is cached as <output_dir>/extrapolation_calibration.json (--recalibrate rebuilds it;
#: a new third dump rebuilds it too, by the stamp).  Explained for readers of the figures in
#: reports/judge_pareto/subsampling_and_extrapolation.md.
JUDGE_OF_MODEL = {LUNA: "luna", HAIKU: "haiku", GEMINI: "gemini", JEV: "jev"}
JUDGE_SHORT = {"luna": "Luna", "haiku": "Haiku", "gemini": "Gemini", "jev": "Jev"}
CALIBRATION_FILE = "extrapolation_calibration.json"


def penalty(delta9: float, base: float) -> float:
    """The question-cut penalty of a share at coverage ``base``, from the measured ninth-to-third gap ``delta9``: the
    (1/c - 1) law (a cut share's judge mean rests on c x 40 whole questions, and its loss against a golden subsample
    grows as 1/c - 1), anchored at the ninth (6 units) and zero at the third (2 units): delta9 x (1/base - 3) / 6;
    nothing above a third."""
    return delta9 * max(0.0, (1.0 / base - 3.0) / 6.0)


def split_half_reliability(items: Dict[Tuple[str, int, int], float], rank: Dict[str, int], qabs: Dict[int, int], m: int, K: int,
                           share, step: int, rotations: Sequence[int]) -> float:
    """Spearman-Brown reliability of the fraction m/K of a share (one axis), the halves alternating along the questions
    ``step`` apart (the questions the share holds); the mean over ``rotations``."""
    rs = []
    for r in rotations:
        sel = subsample(items, rank, qabs, m, r, share, K)
        halves = [means({k: v for k, v in sel.items() if (k[2] // step) % 2 == h}) for h in (0, 1)]
        common = sorted(set(halves[0]) & set(halves[1]))
        rr = pearsonr([halves[0][n] for n in common], [halves[1][n] for n in common])[0]
        rs.append(2 * rr / (1 + rr))
    return float(np.mean(rs))


def two_part_calibration(args, E: Path, cache: Path) -> dict:
    """Per judge with a settled third dump (settled61/<judge>3.json.gz, the cut third; its part 0 of the split in 9,
    (question + entity rank) % 9 == 0, is the cut ninth, the cells the ninth figures measure): the penalty per axis (a
    golden ninth of the third over the cut ninth, the variant mean) and its mean, the split-half reliability of the cut
    ninth and of the golden ninth, their ratio, and s (the measured gain on the golden step 1/9 -> 1/3 within the third
    over the raw Spearman-Brown gain, pooled over axes and variants; the 1/9 -> 2/9 step beside it as a check); the
    pooled values for judges without.  On the 61 axes, whatever figure is drawn.  Cached in ``cache``, keyed by the
    dumps' names and sizes.  From the third dump alone since 2026-11-07 (the cut ninth was read from the ninth dump,
    settled61/<judge>.json.gz, until then): a settled design changed at the ninth only (Haiku's k=4, worst 25%, whose
    third exists at k=2, 10%) would otherwise pair a ninth of one design with a third of another, and the designs'
    difference would pass for question-cut penalty.  Such a judge's ninth is lifted by the penalty measured at its
    third's design, the nearest measured."""
    dumps = {j: settled_path(E, j + "3") for j in JUDGE_SHORT}
    dumps = {j: p for j, p in dumps.items() if p.exists()}
    if not dumps:
        raise SystemExit("two_part_calibration: no judge has a settled third dump (settled61/<judge>3.json.gz)")
    # by name and size, not mtime: every --judge run rewrites its dump with the same content (gzip stamps the time, so the
    # bytes differ but not the size), and a recalibration on each would cost minutes for the same numbers
    stamp = {j: [p.name, p.stat().st_size] for j, p in dumps.items()}
    if cache.exists() and not getattr(args, "recalibrate", False):
        saved = json.loads(cache.read_text())["result"]
        if saved.get("stamp") == stamp:
            print(f"[extrapolation] calibration from {cache}: " + "; ".join(
                f"{JUDGE_SHORT[c['judge']]} lift at a ninth {c['delta9']:+.4f}, s {c['s']:.2f}" for c in saved["per_judge"].values()),
                file=sys.stderr)
            return saved
    data_dir = Path(args.data_dir).resolve()
    data = Data(E, Path(AXES_61), data_dir, Path(args.instructions_dir))
    _, vkeys, rho_of = projector(data, Path(args.cache_dir), data_dir)
    mean_v = lambda d: float(np.mean(list(d.values())))
    per_judge = {}
    for j, p3 in dumps.items():
        rec3, it3, _ = load_settled(p3)
        axes = [ax for ax in data.axes if it3.get(ax.axis_dir)]
        # the cut ninth: the third's part 0 of the split in 9, the cells the ninth figures measure
        it9 = {ax.axis_dir: subsample(it3[ax.axis_dir], data.rank, data.qabs, FRACTION_K, 0, ("q", 9, 0)) for ax in axes}

        def rho_at(items, m, rotations):
            """{axis: {variant: rho}} at the fraction m/3 of the dump, the mean over the rotations."""
            out = {}
            for ax in axes:
                per_rot = [rho_of(means(subsample(items[ax.axis_dir], data.rank, data.qabs, m, r, None)), ax) for r in rotations]
                out[ax.axis_dir] = {vk: float(np.mean([x[vk] for x in per_rot])) for vk in vkeys}
            return out
        r9, g9, g2, g3 = rho_at(it9, 3, (0,)), rho_at(it3, 1, (0, 1, 2)), rho_at(it3, 2, (0, 1, 2)), rho_at(it3, 3, (0,))
        # the ninth's questions lie 9 apart, the third's 3 apart: the halves alternate along them
        R9c = float(np.mean([split_half_reliability(it9[ax.axis_dir], data.rank, data.qabs, 3, 3, None, 9, (0,)) for ax in axes]))
        R9g = float(np.mean([split_half_reliability(it3[ax.axis_dir], data.rank, data.qabs, 1, 3, None, 3, (0, 1, 2)) for ax in axes]))
        delta_by_axis = {ax.axis_dir: mean_v({vk: g9[ax.axis_dir][vk] - r9[ax.axis_dir][vk] for vk in vkeys}) for ax in axes}

        def scaling(M, gM):
            RM = M * R9g / (1 + (M - 1) * R9g)
            pred = sum(g9[a][vk] * (math.sqrt(RM / R9g) - 1) for a in g9 for vk in vkeys)
            return sum(gM[a][vk] - g9[a][vk] for a in g9 for vk in vkeys) / pred
        s, s2 = scaling(3, g3), scaling(2, g2)
        c = per_judge[rec3["model"]] = dict(
            judge=j, n_axes=len(axes), delta9=float(np.mean(list(delta_by_axis.values()))), delta9_by_axis=delta_by_axis,
            R9_cut=R9c, R9_golden=R9g, ratio=R9g / R9c, s=s, s_check_2_9=s2,
            cut_ninth=float(np.mean([mean_v(v) for v in r9.values()])),
            golden_ninth_in_third=float(np.mean([mean_v(v) for v in g9.values()])),
            cut_third=float(np.mean([mean_v(v) for v in g3.values()])))
        print(f"[extrapolation] {JUDGE_SHORT[j]}: cut ninth {c['cut_ninth']:.4f} (R {R9c:.3f}), golden ninth of the third "
              f"{c['golden_ninth_in_third']:.4f} (R {R9g:.3f}), cut third {c['cut_third']:.4f}: lift at a ninth {c['delta9']:+.4f}, "
              f"s {s:.2f} (on 1/9 -> 2/9 {s2:.2f}), {len(axes)} axes x {len(vkeys)} variants", file=sys.stderr)
    all_axes = sorted({a for c in per_judge.values() for a in c["delta9_by_axis"]})
    pooled = dict(judge="pooled", n_judges=len(per_judge), delta9=float(np.mean([c["delta9"] for c in per_judge.values()])),
                  delta9_by_axis={a: float(np.mean([c["delta9_by_axis"][a] for c in per_judge.values() if a in c["delta9_by_axis"]]))
                                  for a in all_axes},
                  ratio=float(np.mean([c["ratio"] for c in per_judge.values()])), s=float(np.mean([c["s"] for c in per_judge.values()])))
    result = dict(model="two-part", per_judge=per_judge, pooled=pooled, stamp=stamp,
                  law="lift = delta9 x (1 / coverage - 3) / 6, nothing above a third; below a third the base's split-half "
                      "reliability x R9_golden / R9_cut",
                  source="golden subsamples of each judge's settled third against its cut ninth, 61 axes x 12 variants")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(json_metadata(
        result, title="the two-part extrapolation's calibration",
        inputs=[current_file_input(f"{j}_third", p) for j, p in dumps.items()]), indent=1))
    print(f"wrote {cache}", file=sys.stderr)
    return result


def arm_calibration(check: dict, models: Sequence[str], axes_dirs: Sequence[str]) -> dict:
    """The lift and scaling for an arm judged by ``models`` on ``axes_dirs``: each judge's own values (the pooled ones for
    a judge without a third), the penalty the mean over the arm's axes; averaged over the arm's judges."""
    rows = []
    for m in dict.fromkeys(models):
        c = check["per_judge"].get(m) or check["pooled"]
        rows.append(dict(delta9=float(np.mean([c["delta9_by_axis"].get(a, c["delta9"]) for a in axes_dirs])),
                         ratio=c["ratio"], s=c["s"], source=c["judge"]))
    return dict(delta9=float(np.mean([r["delta9"] for r in rows])), ratio=float(np.mean([r["ratio"] for r in rows])),
                s=float(np.mean([r["s"] for r in rows])), judges=[r["source"] for r in rows])


def calibration_text(check: dict, base: float) -> str:
    """The subtitle's account of the extrapolation at this base."""
    if "per_judge" not in check:                    # a JSON from before 2026-11-07, redrawn
        return f"Spearman-Brown by question, gains scaled by {check['calibration']:.2f}"
    per = list(check["per_judge"].values())
    ss = ", ".join(f"{JUDGE_SHORT[c['judge']]} {c['s']:.2f}" for c in per)
    missing = [JUDGE_SHORT[j] for j in JUDGE_SHORT if j not in {c["judge"] for c in per}]
    if penalty(1.0, base) > 0:
        lifts = ", ".join(f"{JUDGE_SHORT[c['judge']]} {penalty(c['delta9'], base):+.4f}" for c in per)
        lift = (f"the base lifted by its question-cut penalty, a golden ninth of the third over the cut ninth per judge and axis "
                f"scaled to this coverage ({lifts})")
    else:
        lift = "no lift above a third (the cut third's own penalty against a golden third, about 0.002, left in)"
    return (f"{lift}, then Spearman-Brown by question from the arm's own split half, the gain scaled as measured on golden "
            f"steps within the third ({ss}{'; ' + ' and '.join(missing) + (' takes' if len(missing) == 1 else ' take') + ' the mean' if missing else ''})")


def extrapolation_check(args, E: Path) -> dict:
    """The extrapolation's calibration: <output_dir>/extrapolation_calibration.json, or measured afresh."""
    return two_part_calibration(args, E, Path(args.output_dir) / CALIBRATION_FILE)


def calib_inputs(args) -> list:
    return [current_file_input("calibration", Path(args.output_dir) / CALIBRATION_FILE)]


def settled_path(E: Path, judge: str) -> Path:
    return E / "_tier_eval_scratch" / SETTLED_DIRNAME / f"{judge}.json.gz"


def dump_settled(path: Path, judge: str, model: str, name: str, arm: dict, items_by_axis: Dict[str, Dict[Tuple[str, int, int], float]],
                 inputs, extra: Optional[dict] = None) -> None:
    """A judge's settled design for --judge mix: its arm (key, label, family, cost parts) and its items by axis, the
    item keys (entity, p, q) written as "entity|p|q"."""
    rec = {"judge": judge, "model": model, "name": name, "arm": arm["key"], "label": arm["label"], "family": arm["family"],
           "cost_parts": [[f, list(u)] for f, u in arm["cost_parts"]],
           "items": {ax: {f"{n}|{p}|{q}": v for (n, p, q), v in it.items()} for ax, it in items_by_axis.items()},
           **(extra or {})}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(json_metadata(rec, title=f"settled response design, {name}", inputs=inputs)).encode()))
    print(f"wrote {path} ({len(items_by_axis)} axes)", file=sys.stderr)


def load_settled(path: Path):
    """(record, items by axis with tuple keys, cost parts) of a dump_settled file."""
    rec = json.loads(gzip.decompress(path.read_bytes()))["result"]
    items = {ax: {(k.rsplit("|", 2)[0], int(k.rsplit("|", 2)[1]), int(k.rsplit("|", 2)[2])): v for k, v in it.items()}
             for ax, it in rec["items"].items()}
    return rec, items, [(f, (u[0], u[1])) for f, u in rec["cost_parts"]]


def mix_arms(loaded: Dict[str, tuple], sizes=(3, 4)) -> List[dict]:
    """The mix figure's arms from {judge: (record, items by axis, cost parts)}: each judge alone, and for every
    combination of ``sizes`` judges a golden split, one arm per cyclic assignment of the J shares to the judges
    (key <models>@split<s>; main_mix61 averages them into <models>@split).  A split's cost is each judge's settled
    cost on its share."""
    arms = []
    for j, (rec, items, cp) in loaded.items():
        arms.append(dict(key=f"{rec['model']}@settled", label=f"{MIX_SHORT[j]} alone", family=f"{MIX_SHORT[j]} alone, settled design",
                         members=[(j, items, None)], cost_parts=cp, figures=["mix61"]))
    for n in sizes:
        for combo in itertools.combinations(list(loaded), n):
            J = len(combo)
            fam = "split: all four" if J == len(MIX_JUDGES) else "split: " + " + ".join(MIX_SHORT[j] for j in combo)
            cost_parts = [(f / J, u) for j in combo for f, u in loaded[j][2]]
            models = "+".join(loaded[j][0]["model"] for j in combo)
            for s in range(J):
                arms.append(dict(key=f"{models}@split{s}", label=fam, family=fam,
                                 members=[(j, loaded[j][1], ("g", J, (i + s) % J)) for i, j in enumerate(combo)],
                                 cost_parts=cost_parts, figures=["mix61"]))
            # Roger's "high" mode (2026-11-06): every judge judges every response, the judges blended; for every
            # combination (its cost the judges' costs summed)
            if True:
                fam_e = ("all four" if J == len(MIX_JUDGES) else " + ".join(MIX_SHORT[j] for j in combo)) + ", every response by every judge"
                arms.append(dict(key=f"{models}@every", label=fam_e, family=fam_e, members=[(j, loaded[j][1], None) for j in combo],
                                 cost_parts=[(f, u) for j in combo for f, u in loaded[j][2]], figures=["mix61"]))
    return arms


def merge_shifts(points: Dict[str, dict], vkeys: List[str]) -> Dict[str, dict]:
    """The split arms' points averaged over their shifts (<models>@split<s> -> <models>@split), rho_shift_sd beside."""
    merged: Dict[str, dict] = {}
    for key, p in points.items():
        m = re.match(r"(.*)@split(\d+)\|(.*)$", key)
        if not m:
            merged[key] = p
            continue
        g = merged.setdefault(f"{m.group(1)}@split|{m.group(3)}",
                              dict(p, arm=f"{m.group(1)}@split", rho={vk: [] for vk in vkeys},
                                   per_axis={vk: [] for vk in vkeys} if p.get("per_axis") else None, shifts=0))
        for vk in vkeys:
            g["rho"][vk].append(p["rho"][vk])
            if g["per_axis"] is not None:
                g["per_axis"][vk].append(p["per_axis"][vk])
        g["shifts"] += 1
    for p in merged.values():
        if p.get("shifts"):
            p["rho_shift_sd"] = {vk: float(np.std(v)) for vk, v in p["rho"].items()}
            p["rho"] = {vk: float(np.mean(v)) for vk, v in p["rho"].items()}
            if p.get("per_axis"):          # per axis too, the mean over the shifts, for paired comparisons
                p["per_axis"] = {vk: np.mean(np.array(v), axis=0).tolist() for vk, v in p["per_axis"].items()}
    return merged


def main_mix61(args) -> int:
    """--judge mix: the four judges' settled designs, alone and in three- and four-way golden splits (module docstring),
    three figures: all together, the judges alone, the splits.  --replot_json redraws them from a saved
    judge_response_pareto_61_mix*.json without the projections (seconds rather than minutes)."""
    global BLEND_WEIGHTS
    E = Path(args.experiments_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    A = len(rob.read_axes_tsv(Path(args.axes_file)))
    suffix = ("" if args.mix_weights == "table" else f"_{args.mix_weights}") + ("_third" if args.settled_suffix == "3" else "")
    base = 1 / 3 if args.settled_suffix == "3" else NINTH
    weights_text = ("1 : 1 each" if args.mix_weights == "equal"
                    else "by judge_score_combine's table (Luna 4, the others 3)")
    if args.replot_json:
        saved = json.load(open(args.replot_json))["result"]
        if saved["config"].get("weights", "table") != args.mix_weights:
            raise SystemExit(f"[mix] {args.replot_json} was made with --mix_weights {saved['config'].get('weights')}")
        points, check, vkeys = saved["points"], saved["extrapolation_check"], saved["config"]["variants"]
        base = saved["config"].get("base", base)
        designs_text = "; ".join(saved["config"].get("labels", saved["config"]["judges"]).values())   # arm keys before 2026-11-07
        variants = rob.build_variants(rob.DEFAULT_SLOTS, rob.DEFAULT_LAYERS, list(rob.REGIMES),
                                      K=rob.DEFAULT_SOFT_K, L=rob.DEFAULT_SOFT_SHEAR_L)
        inputs = [current_file_input("mix_json", Path(args.replot_json))]
        print(f"[mix] replotting {len(points)} points from {args.replot_json}", file=sys.stderr)
    else:
        data_dir, inst = Path(args.data_dir).resolve(), Path(args.instructions_dir)
        data = Data(E, Path(args.axes_file), data_dir, inst)
        axes = data.axes
        loaded = {}
        for j in MIX_JUDGES:
            p = settled_path(E, j + args.settled_suffix)
            if not p.exists():
                print(f"[mix] no settled design for {j}{args.settled_suffix} ({p}): run --judge {j}{args.settled_suffix} first; left out",
                      file=sys.stderr)
                continue
            rec, items, cp = load_settled(p)
            missing = [a.axis_dir for a in axes if not items.get(a.axis_dir)]
            if missing:
                raise SystemExit(f"[mix] {j}'s settled design lacks {len(missing)} of {A} axes: {missing[:3]}")
            loaded[j] = (rec, items, cp)
            data.read.append(p)
            print(f"[mix] {j}: {rec['arm']} ({rec['family']}), {len(items)} axes", file=sys.stderr)
        if len(loaded) < 3:
            raise SystemExit("[mix] fewer than three settled designs; nothing to split")
        designs_text = "; ".join(loaded[j][0]["label"] for j in loaded)     # the subtitles name the designs the dumps hold
        model_of = {j: loaded[j][0]["model"] for j in loaded}
        BLEND_WEIGHTS = {m: 1.0 for m in model_of.values()} if args.mix_weights == "equal" else None
        arms = mix_arms(loaded)
        variants, vkeys, rho_of = projector(data, Path(args.cache_dir), data_dir)
        check = extrapolation_check(args, E)
        points = merge_shifts(arm_points(arms, data, model_of, rho_of, vkeys, check, base=base, step=9), vkeys)
        table = []
        for arm in dict.fromkeys(p["arm"] for p in points.values()):
            n = points[f"{arm}|ninth x {FRACTION_K}/{FRACTION_K}"]
            a = points[f"{arm}|all"]
            row = dict(arm=arm, family=n["family"], rho_ninth=float(np.mean(list(n["rho"].values()))), cost_ninth=n["cost"],
                       rho_all=float(np.mean(list(a["rho"].values()))), cost_all=a["cost"],
                       shift_sd=float(np.mean(list(n["rho_shift_sd"].values()))) if n.get("rho_shift_sd") else None)
            table.append(row)
            sd_text = f" (shift sd {row['shift_sd']:.4f})" if row["shift_sd"] is not None else ""
            base_name = "third" if abs(base - 1 / 3) < 1e-9 else "ninth"
            print(f"[mix] {row['family']:34s} {base_name} rho {row['rho_ninth']:.4f}{sd_text:20s}  all rho {row['rho_all']:.4f}"
                  f"  full run ${row['cost_all']:,.0f}", file=sys.stderr)
        inputs = data.inputs + [current_files_input(dep_key="settled", paths=sorted(set(data.read)))] + calib_inputs(args)
    drawn = []
    for (title, fname, lead), keep, ref in (
            (FIGURE_MIX_61, lambda arm: True, frozenset()),
            (FIGURE_MIX_JUDGES_61, lambda arm: arm.endswith("@settled"), frozenset()),
            (FIGURE_MIX_SPLITS_61, lambda arm: arm.endswith(("@split", "@every")) or arm == f"{JEV}@settled", frozenset({f"{JEV}@settled"}))):
        fname = fname.replace(".png", f"{suffix}.png")
        sub_points = {k: v for k, v in points.items() if keep(v["arm"])}
        plot(sub_points, variants, out / fname, f"Response judging, {title}", A, check, inputs,
             lead=lead.format(weights=weights_text, designs=designs_text), axes_file=args.axes_file, base=base, min_cost=MIN_COST_61,
             ref_arms=ref)
        drawn.append(fname)
        print(f"wrote {out / fname}", file=sys.stderr)
    if args.replot_json:
        return 0
    title = FIGURE_MIX_61[0]
    result = {"config": {"judge": "mix", "judges": {j: loaded[j][0]["arm"] for j in loaded},
                         "labels": {j: loaded[j][0]["label"] for j in loaded}, "weights": args.mix_weights, "base": base,
                         "axes_file": args.axes_file, "variants": vkeys, "prices": PRICES, "october_responses": OCTOBER_RESPONSES,
                         "n_axes": N_AXES, "figures": drawn,
                         "splits": "golden share i of J inside the ninth per judge; points averaged over the J cyclic assignments"},
              "table": table, "extrapolation_check": check, "points": points}
    jname = f"judge_response_pareto_61_mix{suffix}.json"
    (out / jname).write_text(json.dumps(json_metadata(result, title=f"Response judging, {title}", inputs=inputs), indent=1))
    print(f"wrote {out / jname}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--experiments_dir", default=str(rob.DEFAULT_EXPERIMENTS_DIR))
    ap.add_argument("--data_dir", default=str(rob.DEFAULT_DATA_DIR))
    ap.add_argument("--stack_group", choices=("g12", "g61"), default="g12",
                    help="g12: the twelve axes, every judge and format (three figures); g61: the 61 axes, Luna only (stacking, and 20 answers a call against 40)")
    ap.add_argument("--axes_file", default=None, help=f"default {AXES_12}, or {AXES_61} with --stack_group g61")
    ap.add_argument("--cost_basis", choices=("production", "measured"), default="production",
                    help="with --stack_group g61, a judge with a cache_read (Gemini): reprice its input at that cache read "
                         "fraction (production, default) or keep the recorded cache reads (measured; files ..._measured.png)")
    ap.add_argument("--judge", choices=sorted(JUDGES_61) + ["mix"], default="luna",
                    help="with --stack_group g61: the judge whose cells are drawn (figures named with it unless Luna)")
    ap.add_argument("--instructions_dir", default="/tmp/claude-501/corpus_2026-05-24/data")
    ap.add_argument("--cache_dir", default=str(rob.DEFAULT_EXPERIMENTS_DIR / "_tier_eval_scratch" / "robustness_cache"))
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--stack_format", choices=sorted(FMT_NAME), default=None,
                    help="--stack_group g61, one judge: draw the k-and-share figure, the 40-answer arm and the settled-design "
                         "arms for this stacking format instead of the judge's settled one (plain unless JUDGES_61 says "
                         "otherwise); figures named ..._<format>.png, no settled dump written")
    ap.add_argument("--overlay_json", default=None,
                    help="with --stack_group g61: a figure JSON of the same model (judge_response_pareto_61.json for luna3) "
                         "whose extrapolated points are drawn dotted beside this run's, for the arms both have")
    ap.add_argument("--mix_weights", choices=("table", "equal"), default="table",
                    help="--judge mix: blend the judges' per-entity means by judge_score_combine's table (Luna 4, the rest 3) or equally")
    ap.add_argument("--recalibrate", action="store_true",
                    help="measure the extrapolation's calibration afresh from the settled dumps (two_part_calibration) instead of "
                         "reading <output_dir>/extrapolation_calibration.json; a changed dump recalibrates on its own")
    ap.add_argument("--settled_suffix", default="", choices=("", "3"),
                    help="--judge mix: read the judges' settled designs on the third (settled61/<judge>3.json.gz, from --judge "
                         "luna3 / haiku3 / gemini3 and the Jev third) instead of the ninth; files named ..._third")
    ap.add_argument("--replot_json", default=None,
                    help="--judge mix: redraw the three mix figures from this saved judge_response_pareto_61_mix*.json (no projections)")
    args = ap.parse_args(argv)
    if args.axes_file is None:
        args.axes_file = AXES_61 if args.stack_group == "g61" else AXES_12
    if args.stack_group == "g61":
        return main_jev61(args) if args.judge == "jev" else main_mix61(args) if args.judge == "mix" else main61(args)
    E, data_dir = Path(args.experiments_dir), Path(args.data_dir).resolve()
    data = Data(E, Path(args.axes_file), data_dir, Path(args.instructions_dir))
    axes = data.axes

    # every judge's items on every axis
    judges: Dict[str, Dict[str, Dict]] = {"luna": {}, "haiku": {}, "gemini": {}}
    for i, ax in enumerate(axes):
        judges["luna"][ax.axis_dir] = data.luna_balanced(i, ax.axis_dir)
        judges["haiku"][ax.axis_dir] = data.cell(ax.axis_dir, HAIKU, f"@r1_pnn20_s9p0g12_a{i}c")
        judges["gemini"][ax.axis_dir] = data.cell(ax.axis_dir, GEMINI, f"@r1_pnn20_s27p0g12_a{i}c")
    judges["luna40"] = {ax.axis_dir: data.cell(ax.axis_dir, LUNA, f"@r1_pnn40_s9p0g12_a{i}c") for i, ax in enumerate(axes)}
    for lab, _ in JEV_ARMS:
        judges[lab] = {ax.axis_dir: data.cell(ax.axis_dir, JEV, lab) for ax in axes}
    stacked = {(fmt, k): {ax.axis_dir: data.cell(ax.axis_dir, LUNA, f"@{fmt}n20_s9p0g12_k{k}") for ax in axes}
               for fmt, k in STACKED}
    have = {j: all(v is not None for v in judges[j].values()) for j in judges}
    print(f"judges complete: {have}", file=sys.stderr)

    # costs a response
    prof = {LUNA: per_call_profile(data, LUNA, lambda i: f"@r1_pnn20_s9p0g12_a{i}")}
    if have["haiku"]:
        prof[HAIKU] = per_call_profile(data, HAIKU, lambda i: f"@r1_pnn20_s9p0g12_a{i}c")
    if have["gemini"]:
        prof[GEMINI] = per_call_profile(data, GEMINI, lambda i: f"@r1_pnn20_s27p0g12_a{i}c")
    unit = {m: judge_costs(p, m) for m, p in prof.items()}
    if have["luna40"]:
        prof["luna40"] = per_call_profile(data, LUNA, lambda i: f"@r1_pnn40_s9p0g12_a{i}c")
        unit["luna40"] = judge_costs(prof["luna40"], LUNA)
    for lab, _ in JEV_ARMS:         # no cache: the run's cost over its responses and axes
        if have[lab]:
            u = json.load(open(E / "_tier_eval_jev" / lab.lstrip("@") / "usage.json"))
            n = json.load(open(E / f"{axes[0].axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{JEV}{lab}" / "scores_responses.json"))["_provenance"]["n_items"]
            unit[lab] = (u["total_cost_usd"] / (n * len(axes)), 0.0)
            data.read.append(E / "_tier_eval_jev" / lab.lstrip("@") / "usage.json")
    for m, (a, o) in unit.items():
        print(f"[cost] {m}: {json.dumps({k: round(v, 1) for k, v in prof.get(m, {}).items()})}; ${a * 1e6:.2f} per 1M "
              f"response-axes, ${o * 1e6:.1f} per 1M responses once; full run, every response: "
              f"${full_run_cost([(1.0, unit[m])]):,.0f}", file=sys.stderr)
    stack_unit = {}
    for (fmt, k), cells in stacked.items():
        if all(cells.values()):
            costs = [data.usage(ax.axis_dir, LUNA, f"@{fmt}n20_s9p0g12_k{k}") for ax in axes]
            items = [json.load(open(E / f"{ax.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{LUNA}@{fmt}n20_s9p0g12_k{k}" /
                                    "scores_responses.json"))["_provenance"]["n_items"] for ax in axes]
            from results_analysis.judge_tier_cost_plot_pooled import load_measured_cost
            per = np.mean([load_measured_cost(E / f"{ax.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{LUNA}@{fmt}n20_s9p0g12_k{k}" /
                                              "usage.json", "batch") / n for ax, n in zip(axes, items)])
            stack_unit[(fmt, k)] = (per, unit[LUNA][1])

    # the arms: (key, label, family, [(judge, items by axis, share)], cost parts per unit coverage, figures)
    arms = []
    def add(key, label, family, members, cost_parts, figures):
        arms.append(dict(key=key, label=label, family=family, members=members, cost_parts=cost_parts, figures=figures))
    jb = JEV_ARMS[0][0]                 # Jev in the mixes: its cheapest arm, 20 answers x 12 axes
    add(f"{LUNA}@k1", "Luna", "Luna, one axis a call", [("luna", judges["luna"], None)], [(1.0, unit[LUNA])],
        ["jev", "models"])
    if have["luna40"]:
        add(f"{LUNA}@n40", "Luna, 40 answers", "Luna, one axis a call, 40 answers a call", [("luna40", judges["luna40"], None)],
            [(1.0, unit["luna40"])], [])        # its figure is drawn on the 61 axes (--stack_group g61)
    for (fmt, k), cells in stacked.items():
        if (fmt, k) in stack_unit:
            add(f"{LUNA}@{fmt}k{k}", f"Luna k={k} {FMT_NAME[fmt]}", f"Luna stacked, {FMT_NAME[fmt]}",
                [("luna", cells, None)], [(1.0, stack_unit[(fmt, k)])], [])     # drawn on the 61 axes since 2026-11-05
    for lab, name in JEV_ARMS:
        if have[lab]:
            add(f"{JEV}{lab}", name, name, [(lab, judges[lab], None)], [(1.0, unit[lab])], ["jev"] + (["models"] if lab == jb else []))
    if have["haiku"]:
        add(f"{HAIKU}@k1", "Haiku", "Haiku, one axis a call", [("haiku", judges["haiku"], None)], [(1.0, unit[HAIKU])], ["models"])
        add(f"{LUNA}+{HAIKU}@2x", "Luna + Haiku, both", "Luna + Haiku, both judge every response",
            [("luna", judges["luna"], None), ("haiku", judges["haiku"], None)], [(1.0, unit[LUNA]), (1.0, unit[HAIKU])], ["models"])
        add(f"{LUNA}+{HAIKU}@rr", "Luna + Haiku, round-robin", "Luna + Haiku, each response by one",
            [("luna", judges["luna"], ("g", 2, 0)), ("haiku", judges["haiku"], ("g", 2, 1))], [(0.5, unit[LUNA]), (0.5, unit[HAIKU])],
            ["models"])
    if have["haiku"] and have["gemini"]:
        add(f"{LUNA}+{HAIKU}+{GEMINI}@rr", "trio, round-robin", "Luna + Haiku + Gemini, each response by one",
            [("luna", judges["luna"], ("q", 27, 9)), ("haiku", judges["haiku"], ("q", 27, 18)), ("gemini", judges["gemini"], ("q", 27, 0))],
            [(1 / 3, unit[LUNA]), (1 / 3, unit[HAIKU]), (1 / 3, unit[GEMINI])], ["models"])
    if have[jb]:
        add(f"{LUNA}+{JEV}@2x", "Luna + Jev, both", "Luna + Jev, both judge every response",
            [("luna", judges["luna"], None), (jb, judges[jb], None)], [(1.0, unit[LUNA]), (1.0, unit[jb])], ["models"])
        add(f"{LUNA}+{JEV}@rr", "Luna + Jev, round-robin", "Luna + Jev, each response by one",
            [("luna", judges["luna"], ("g", 2, 0)), (jb, judges[jb], ("g", 2, 1))], [(0.5, unit[LUNA]), (0.5, unit[jb])], ["models"])
        if have["haiku"]:
            add(f"{LUNA}+{HAIKU}+{JEV}@3x", "Luna + Haiku + Jev, all", "Luna + Haiku + Jev, all judge every response",
                [("luna", judges["luna"], None), ("haiku", judges["haiku"], None), (jb, judges[jb], None)],
                [(1.0, unit[LUNA]), (1.0, unit[HAIKU]), (1.0, unit[jb])], ["models"])
            add(f"{LUNA}+{HAIKU}+{JEV}@rr", "Luna + Haiku + Jev, round-robin", "Luna + Haiku + Jev, each response by one",
                [("luna", judges["luna"], ("g", 3, 0)), ("haiku", judges["haiku"], ("g", 3, 1)), (jb, judges[jb], ("g", 3, 2))],
                [(1 / 3, unit[LUNA]), (1 / 3, unit[HAIKU]), (1 / 3, unit[jb])], ["models"])
    model_of = {"luna": LUNA, "luna40": LUNA, "haiku": HAIKU, "gemini": GEMINI, **{lab: JEV for lab, _ in JEV_ARMS}}

    variants, vkeys, rho_of = projector(data, Path(args.cache_dir), data_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    check = extrapolation_check(args, E)
    points = arm_points(arms, data, model_of, rho_of, vkeys, check)

    inputs = data.inputs + [current_files_input(dep_key="cells", paths=sorted(set(data.read)))] + calib_inputs(args)
    title = "Response judging with a cached prefix: subsampling against stacking, under 12 projection variants"
    for fig_key, (fig_title, fname, lead) in FIGURES.items():
        sub_points = {k: v for k, v in points.items() if fig_key in v["figures"]}
        ref = {f"{LUNA}@k1"} if fig_key == "jev" else set()
        plot(sub_points, variants, out / fname, f"Response judging, {fig_title}", len(axes), check, inputs, ref_arms=ref, lead=lead,
             axes_file=args.axes_file)
        print(f"wrote {out / fname}", file=sys.stderr)
    result = {"config": {"axes_file": args.axes_file, "variants": vkeys, "prices": PRICES, "october_responses": OCTOBER_RESPONSES,
                         "n_axes": N_AXES, "fractions": "m/3 of each judge's share of the ninth, golden (judge_tier_cost_eval.golden_point), 3 rotations",
                         "extrapolation": "two parts: the base lifted by its question-cut penalty, then Spearman-Brown from a split "
                                          "half by question (two_part_calibration)"},
              "unit_costs": {m: {"per_response_axis": a, "per_response_once": o, "tokens_per_call": prof.get(m)}
                             for m, (a, o) in unit.items()},
              "extrapolation_check": check, "points": points}
    (out / "judge_response_pareto.json").write_text(json.dumps(json_metadata(result, title=title, inputs=inputs), indent=1))
    print(f"wrote {out / 'judge_response_pareto.json'}", file=sys.stderr)
    return 0


def projections(data: Data, cache_dir: Path, data_dir: Path):
    """The 12 projection variants, their keys, and {axis_dir: {variant key: {entity id: projection}}} on data's
    axes, the entity ids being the group's bare names lifted to name|R / name|T (judge_response_error_bars.py
    reads the projections directly, for its bootstraps)."""
    variants = rob.build_variants(rob.DEFAULT_SLOTS, rob.DEFAULT_LAYERS, list(rob.REGIMES),
                                  K=rob.DEFAULT_SOFT_K, L=rob.DEFAULT_SOFT_SHEAR_L)
    vkeys = [v.key for v in variants]
    meta = {"version": rob.CACHE_VERSION, "fingerprint": rob.data_fingerprint(data_dir), "ca_kind": "combined"}
    slices = rob.load_slices(cache_dir, rob.DEFAULT_SLOTS, rob.DEFAULT_LAYERS, meta, True)
    if slices is None:
        raise SystemExit("the slice cache is stale or missing: run scripts/judge_instruction_12way.py once to rebuild it")
    names = {ax.axis_dir: set(rob.lift_scores({n: 0.0 for n in data.rank}, data.kinds)) for ax in data.axes}
    return variants, vkeys, rob.project_variants(slices, data.axes, variants, names, data_dir)


def projector(data: Data, cache_dir: Path, data_dir: Path):
    """The 12 projection variants, and rho_of(entity scores, axis) -> {variant: Spearman rho} on data's axes."""
    variants, vkeys, proj = projections(data, cache_dir, data_dir)

    def rho_of(scores: Dict[str, float], ax) -> Dict[str, float]:
        lifted = rob.lift_scores(scores, data.kinds)
        return {vk: rob.cell_rho(lifted, proj[ax.axis_dir][vk], (ax.pos, ax.neg))[0] for vk in vkeys}
    return variants, vkeys, rho_of


def arm_points(arms: List[dict], data: Data, model_of: Dict[str, str], rho_of, vkeys: List[str],
               check: dict, base: float = NINTH, step: int = 9) -> Dict[str, dict]:
    """Each arm's points: the fractions m/3 of the measured share (the ninth unless ``base`` says otherwise; Gemini
    judged a 1/27, cut by question, its questions ``step`` = 27 apart) measured, each the mean of three rotations,
    and the coverages above it up to all extrapolated in two parts (the comment above two_part_calibration; ``check``
    its calibration): the base lifted by its question-cut penalty (a hollow point at the base's cost, key ``|lift``),
    then Spearman-Brown by question from the arm's own split-half reliability raised to the judge's golden-over-cut
    ratio, the gain scaled by the judge's s.  The point keys keep the word "ninth" whatever the share (the plots read
    ``coverage`` and ``m``)."""
    axes = data.axes
    # the coverages above the measured share: 1/9, 1/3 and all (for a ninth 1/3 and all; for 1/27 all three; for 2/27,
    # Gemini's parts 0 and 9, all three at non-integer multiples)
    extrapolate = {name: t / base for name, t in (("1/9", 1 / 9), ("1/3", 1 / 3), ("all", 1.0)) if t > base * (1 + 1e-9)}
    points: Dict[str, dict] = {}
    for arm in arms:
        fractions = [(m, FRACTION_K) for m in FRACTIONS] + [(m, FINER_K) for m in FINER if arm.get("finer")]
        for m, K in fractions:
            rhos = {vk: [] for vk in vkeys}
            for ax in axes:
                per_rot = []
                for r in (range(K) if m < K else (0,)):
                    parts = {model_of[j]: means(subsample(items[ax.axis_dir], data.rank, data.qabs, m, r, share, K))
                             for j, items, share in arm["members"]}
                    per_rot.append(rho_of(blend(parts), ax))
                for vk in vkeys:
                    rhos[vk].append(float(np.mean([x[vk] for x in per_rot])))
            cov = base * m / K
            points[f"{arm['key']}|ninth x {m}/{K}"] = dict(arm=arm["key"], label=arm["label"], family=arm["family"], coverage=cov,
                                                 m=m * FRACTION_K / K,
                                                 figures=arm.get("finer_figures", arm["figures"]) if K == FINER_K else arm["figures"],
                                                 measured=True, cost=full_run_cost([(f * cov, u) for f, u in arm["cost_parts"]]),
                                                 rho={vk: float(np.mean(rhos[vk])) for vk in vkeys}, per_axis=rhos)
        # extrapolation above the ninth: split-half reliability by instruction parity, Spearman-Brown
        rel = []
        for ax in axes:
            halves = []
            for h in (0, 1):
                parts = {}
                for j, items, share in arm["members"]:
                    # by question (more coverage adds questions), alternating along the judge's own questions,
                    # which lie a share's modulus apart (9 in the ninth and in a golden share of it, 27 in the
                    # trio's share by question)
                    st = share[1] if share and share[0] == "q" else step
                    sel = {k: v for k, v in subsample(items[ax.axis_dir], data.rank, data.qabs, FRACTION_K, 0, share).items()
                           if (k[2] // st) % 2 == h}
                    parts[model_of[j]] = means(sel)
                halves.append(blend(parts))
            common = sorted(set(halves[0]) & set(halves[1]))
            r = pearsonr([halves[0][n] for n in common], [halves[1][n] for n in common])[0]
            rel.append(2 * r / (1 + r))
        R = float(np.mean(rel))
        cal = arm_calibration(check, [model_of[j] for j, _, _ in arm["members"]], [ax.axis_dir for ax in axes])
        lift = penalty(cal["delta9"], base)
        R_g = min(R * (cal["ratio"] if base < 1 / 3 - 1e-9 else 1.0), 0.9999)
        base_pt = points[f"{arm['key']}|ninth x {FRACTION_K}/{FRACTION_K}"]
        rho_g = {vk: base_pt["rho"][vk] + lift for vk in vkeys}
        common = dict(arm=arm["key"], label=arm["label"], family=arm["family"], measured=False, reliability=R_g,
                      reliability_cut=R, figures=arm["figures"], lift=lift, s=cal["s"], calibration=cal["judges"])
        if lift > 0:                                   # the lifted base, at the base's cost
            points[f"{arm['key']}|lift"] = dict(common, coverage=base, cost=base_pt["cost"], rho=rho_g, lifted=True)
        for name, M in extrapolate.items():
            RM = M * R_g / (1 + (M - 1) * R_g)
            cov = base * M
            points[f"{arm['key']}|{name}"] = dict(
                common, coverage=cov, cost=full_run_cost([(f * cov, u) for f, u in arm["cost_parts"]]),
                # the Spearman-Brown gain from the lifted base, scaled by the judge's s
                rho={vk: rho_g[vk] * (1 + cal["s"] * (math.sqrt(RM / R_g) - 1)) for vk in vkeys})
    return points


def main_jev61(args) -> int:
    """Jev's question types on the 61 axes (JEV_QUESTIONS_61), each measured at m/3 and m/9 of the ninth and extrapolated,
    its cost the recorded Jev bill (no cache, no discount)."""
    E, data_dir, inst = Path(args.experiments_dir), Path(args.data_dir).resolve(), Path(args.instructions_dir)
    data = Data(E, Path(args.axes_file), data_dir, inst)
    axes, A = data.axes, len(data.axes)
    variants, vkeys, rho_of = projector(data, Path(args.cache_dir), data_dir)
    arms = []
    for q, fam in JEV_QUESTIONS_61:
        lab = f"@jb61_{q}_a20m12_s9p0"
        cells = {a.axis_dir: data.cell(a.axis_dir, JEV, lab) for a in axes}
        if not all(cells.values()):
            print(f"[jev] {q}: missing on {sum(not c for c in cells.values())} axes; left out", file=sys.stderr)
            continue
        per = []
        for a in axes:                            # a union label (the third): its parts' costs and items summed
            cost = items = 0.0
            for part_lab in lab.split("|"):
                cd = E / f"{a.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{JEV}{part_lab}"
                cost += json.load(open(cd / "usage.json"))["total_cost_usd"]
                items += json.load(open(cd / "scores_responses.json"))["_provenance"]["n_items"]
                data.read.append(cd / "usage.json")
            per.append(cost / items)
        unit = (float(np.mean(per)), 0.0)
        print(f"[cost] {fam}: ${unit[0] * 1e6:.2f} per 1M response-axes; full run ${full_run_cost([(1.0, unit)]):,.0f}", file=sys.stderr)
        arms.append(dict(key=f"{JEV}@{q}", label=fam, family=fam, members=[("j", cells, None)], cost_parts=[(1.0, unit)],
                         figures=["jev61"], finer=True))
    check = extrapolation_check(args, E)
    points = arm_points(arms, data, {"j": JEV}, rho_of, vkeys, check)
    inputs = data.inputs + calib_inputs(args)
    out = Path(args.output_dir)
    # Jev alone (Roger, 2026-11-05: "take Luna and Haiku off it, we're not interested in comparisons at this point")
    # the yes/no at other request shapes: each arm at its own measured share (the one-axis cells on 1/27)
    shape_points = {}
    for a_n, m_n, sh, base in JEV_SHAPES_61:
        lab = "|".join(f"@jb61_noul_a{a_n}m{m_n}_{part}" for part in sh.split("|"))
        third = base > NINTH * (1 + 1e-9)
        cells = {a.axis_dir: data.cell(a.axis_dir, JEV, lab) for a in axes}
        if not all(cells.values()):
            print(f"[jev shapes] {lab}: missing on {sum(not c for c in cells.values())} axes; left out", file=sys.stderr)
            continue
        per = []
        for a in axes:                            # a union label (the third): its parts' costs and items summed
            cost = items = 0.0
            for part_lab in lab.split("|"):
                cd = E / f"{a.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{JEV}{part_lab}"
                cost += json.load(open(cd / "usage.json"))["total_cost_usd"]
                items += json.load(open(cd / "scores_responses.json"))["_provenance"]["n_items"]
                data.read.append(cd / "usage.json")
            per.append(cost / items)
        unit = (float(np.mean(per)), 0.0)
        n_req = -(-A // m_n)                      # the even chunks judge_responses_jev.py makes of the A axes
        lo_ax, hi_ax = A // n_req, -(-A // n_req)
        size = str(lo_ax) if lo_ax == hi_ax else f"{lo_ax}-{hi_ax}"
        fam = f"Jev yes/no, {a_n} answers x {size} {'axis' if hi_ax == 1 else 'axes'} a request" + (" (a third)" if third else "")
        print(f"[cost] {fam}: ${unit[0] * 1e6:.2f} per 1M response-axes; full run ${full_run_cost([(1.0, unit)]):,.0f}", file=sys.stderr)
        arm = dict(key=f"{JEV}@noul_a{a_n}m{m_n}" + ("_third" if third else ""), label=fam, family=fam, members=[("j", cells, None)],
                   cost_parts=[(1.0, unit)],
                   figures=["jev_shapes"], finer=base == NINTH)
        if (a_n, m_n) == (20, 31):                # the settled design, for --judge mix (jev3: on the third)
            dump_settled(settled_path(E, "jev3" if third else "jev"), "jev", JEV, "Jev 1.14", arm, cells, data.inputs)
        shape_points.update(arm_points([arm], data, {"j": JEV}, rho_of, vkeys, check, base=base,
                                       step=27 if base < NINTH else 9))
    # 40 x 12-13, the largest clean shape at 40 answers, estimated rather than judged: 40 x 10-11's points, the cost by
    # the dry runs' ratio, and rho lowered per variant by 40 answers' own measured slope in axes a request,
    # (5-6 minus 10-11 axes) x log2(12.2 / 10.17) of a halving
    k10, k6 = f"{JEV}@noul_a40m12", f"{JEV}@noul_a40m6"
    if any(p["arm"] == k10 for p in shape_points.values()) and any(p["arm"] == k6 for p in shape_points.values()):
        top = f"|ninth x {FRACTION_K}/{FRACTION_K}"
        slope = {vk: shape_points[k6 + top]["rho"][vk] - shape_points[k10 + top]["rho"][vk] for vk in vkeys}
        frac = math.log2((A / 5) / (A / 6))
        est_fam = "Jev yes/no, 40 answers x 12-13 axes a request (estimated from 10-11)"
        for key, p in list(shape_points.items()):
            if p["arm"] == k10:
                q = json.loads(json.dumps(p))
                q.update(arm=f"{JEV}@noul_a40m13_est", label=est_fam, family=est_fam, cost=p["cost"] * JEV_40X13_COST_RATIO)
                q["rho"] = {vk: p["rho"][vk] - slope[vk] * frac for vk in vkeys}
                q.pop("per_axis", None)
                shape_points[key.replace(k10, f"{JEV}@noul_a40m13_est")] = q
    inputs = inputs + [current_files_input(dep_key="cells", paths=sorted(set(data.read)))]
    title, fname, lead = FIGURE_JEV_61
    plot(points, variants, out / fname, f"Response judging, {title}", A, check, inputs, lead=lead, axes_file=args.axes_file,
         min_cost=MIN_COST_61)
    print(f"wrote {out / fname}", file=sys.stderr)
    if shape_points:
        stitle, sfname, slead = FIGURE_JEV_SHAPES_61
        plot(shape_points, variants, out / sfname, f"Response judging, {stitle}", A, check, inputs, lead=slead,
             axes_file=args.axes_file, min_cost=MIN_COST_61)
        print(f"wrote {out / sfname}", file=sys.stderr)
        for arm in dict.fromkeys(p["arm"] for p in shape_points.values()):
            pm = max((p for p in shape_points.values() if p["arm"] == arm and p["measured"]), key=lambda p: p["coverage"])
            print(f"[shape] {pm['label']:45s} measured at {Fraction(pm['coverage']).limit_denominator(1000)}: ${pm['cost']:5.0f}  "
                  f"rho {np.mean(list(pm['rho'].values())):.4f}", file=sys.stderr)
        points.update(shape_points)
    ref = points[f"{JEV}@noul|ninth x {FRACTION_K}/{FRACTION_K}"]["rho"]
    for arm in dict.fromkeys(p["arm"] for p in points.values()):
        p = points[f"{arm}|ninth x {FRACTION_K}/{FRACTION_K}"]
        print(f"[ninth] {p['label']:55s} ${p['cost']:5.0f}  rho {np.mean(list(p['rho'].values())):.4f}", file=sys.stderr)
    result = {"config": {"judge": "jev", "questions": [q for q, _ in JEV_QUESTIONS_61], "variants": vkeys},
              "extrapolation_check": check, "points": points}
    (out / "judge_response_pareto_61_jev.json").write_text(json.dumps(json_metadata(result, title=title, inputs=inputs), indent=1))
    return 0


def main61(args) -> int:
    """The 61 axes, one judge (--judge, JUDGES_61): 20 answers a call against 40; one axis a call against plain
    stacking at k = 2, 4, 6, every axis stacked or all but the worst 10%, 15%, 20% or 25%, those chosen by
    cross-fitting over question folds (module docstring); and the three stacking formats.  Each figure is drawn once
    its cells exist; Luna's file names are kept, other judges' carry the judge (judge_response_pareto_answers_haiku.png)."""
    from results_analysis.judge_tier_cost_plot_pooled import load_measured_cost
    J = JUDGES_61[args.judge]
    model, name, share, base = J["model"], J["name"], J["share"], J["base"]
    E, data_dir, inst = Path(args.experiments_dir), Path(args.data_dir).resolve(), Path(args.instructions_dir)
    data = Data(E, Path(args.axes_file), data_dir, inst)
    d12 = Data(E, Path(AXES_12), data_dir, inst)          # the twelve's own cells, and Luna's cost a call
    axes, A = data.axes, len(data.axes)
    i12 = {a.axis_dir: i for i, a in enumerate(d12.axes)}

    def cells_of(label_12, label_61):
        """{axis: items or None}: the twelve's own cells (label_12) where given, else the 61-axis label."""
        out = {}
        for i, a in enumerate(axes):
            if label_12 and label_12.split("|")[0] == "balanced" and a.axis_dir in i12:
                # the twelve's balanced cells (part 0), and with "balanced|<label>|..." the other parts' cells beside
                cells = [d12.luna_balanced(i12[a.axis_dir], a.axis_dir)] + \
                        [data.cell(a.axis_dir, model, lab) for lab in label_12.split("|")[1:]]
                out[a.axis_dir] = None if any(c is None for c in cells) else {k: v for c in cells for k, v in c.items()}
            elif label_12 and a.axis_dir in i12:
                out[a.axis_dir] = data.cell(a.axis_dir, model, label_12.format(i=i12[a.axis_dir], i61=i))
            else:
                out[a.axis_dir] = data.cell(a.axis_dir, model, label_61.format(i=i))
        return out

    complete = lambda cells: all(v for v in cells.values())
    k1 = cells_of(J["k1_12"], J["k1_61"])
    if not complete(k1):
        raise SystemExit(f"{name}: one axis a call is missing on {sum(not v for v in k1.values())} of {A} axes")
    k1_40 = cells_of(J["n40_12"], J["n40_61"])
    have40 = complete(k1_40)
    k1_80 = cells_of(None, J["n80_61"]) if J.get("n80_61") else {}
    have80 = bool(k1_80) and complete(k1_80)
    settled = J.get("settled")
    # the stacking format the k-and-share figure, the settled dump and the 40-answer arm are drawn for: the judge's
    # settled format (JUDGES_61 "settled_format", plain unless set) or --stack_format; a format other than the judge's
    # settled one names its figures after itself and writes no settled dump (Roger, 2026-11-07: "If we're moving Haiku
    # to labelled ... Start with the k= and percentage, and then the number of responses in a batch")
    settled_fmt = J.get("settled_format", "rk_pn")
    dfmt = args.stack_format or settled_fmt
    dfmt_name = FMT_NAME[dfmt]
    st40_label = (J["st40_label"].format(k=settled[0]) if settled and J.get("st40_label")
                  else f"@{dfmt}n40_{share}g61_k{settled[0]}" if settled else None)
    st40 = ({a.axis_dir: data.cell(a.axis_dir, model, st40_label) for a in axes} if settled and have40 else {})
    have_st40 = bool(st40) and complete(st40)
    fmt_label = lambda fmt, k: (J["stack_label"].format(fmt=fmt, k=k) if J.get("stack_label")
                                else f"@{fmt}n20_{share}g61_k{k}")
    stacked_by = {(fmt, k): {a.axis_dir: data.cell(a.axis_dir, model, fmt_label(fmt, k)) for a in axes}
                  for fmt in FMT_NAME for k in STACK61_K}
    have = {key: complete(c) for key, c in stacked_by.items()}
    plain_ks = [k for k in STACK61_K if have[(dfmt, k)]]
    print(f"[{args.judge}] one axis a call: complete; 40 answers: {'complete' if have40 else 'missing'}; stacked: "
          + ", ".join(f"{fmt} k={k}" for (fmt, k), ok in have.items() if ok), file=sys.stderr)

    def measured_unit(label_of_axis):
        """(USD per response per axis, 0): a cell's recorded tokens at the model's batch rate, over its items (a union
        label's cells summed); with the judge's ``cache_read`` and --cost_basis production, the input repriced as that
        fraction read from the cache."""
        per = []
        for i, a in enumerate(axes):
            cost = items = 0.0
            for lab in label_of_axis(i, a).split("|"):
                cd = E / f"{a.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{model}{lab}"
                if not (cd / "usage.json").exists():
                    cost = None
                    break
                if reprice_at:
                    cost += reprice(cd / "usage.json", reprice_at)
                elif model == HAIKU and live_usage(cd / "usage.json"):
                    # a Haiku cell judged in real time read the prompt cache about half as often as by Message Batches
                    # (46% against 87-91%, 40 calls in flight on fresh prefixes; 2026-11-07, the labelled k=6 and
                    # 40-answer cells): priced as its plain twin's batch run read it, so that the figure's costs
                    # compare designs, not transports
                    twin = cd.parent / f"{model}{lab.replace('rk_pl', 'rk_pn')}" / "usage.json"
                    cost += reprice(cd / "usage.json", cache_read_share(twin) if twin.exists() else HAIKU_BATCH_CACHE_READ)
                else:
                    cost += load_measured_cost(cd / "usage.json", "batch")
                items += json.load(open(cd / "scores_responses.json"))["_provenance"]["n_items"]
                data.read.append(cd / "usage.json")
            if cost is not None:
                per.append(cost / items)
        return (float(np.mean(per)), 0.0)

    reprice_at = J.get("cache_read") if args.cost_basis == "production" else None

    def reprice(usage_path: Path, read_at: float) -> float:
        """A cell's tokens at the batch rate, ``read_at`` of its input read from the cache (Gemini's production
        read share; a Haiku cell judged in real time, its batch twin's)."""
        from assistant_axis.judge_pricing import cache_rate_factors
        from results_analysis.judge_tier_cost_plot_pooled import basis_rates, _base_model
        total = 0.0
        for key, e in json.load(open(usage_path))["per_model"].items():
            m = _base_model(e.get("model") or key)
            rate_in, rate_out = basis_rates(m, "batch")
            read_factor = cache_rate_factors(m)[1]
            pt = e.get("prompt_tokens", 0)
            total += (pt * (1 - read_at + read_at * read_factor) * rate_in + e.get("completion_tokens", 0) * rate_out) / 1e6
        return total

    if args.judge == "luna":     # as since 2026-11-04: Luna's production cost model a call, the stacked runs measured
        unit_k1 = judge_costs(per_call_profile(d12, LUNA, lambda i: f"@r1_pnn20_s9p0g12_a{i}"), LUNA)
        unit_40 = judge_costs(per_call_profile(d12, LUNA, lambda i: f"@r1_pnn40_s9p0g12_a{i}c"), LUNA) if have40 else None
        stack_unit = {key: (measured_unit(lambda i, a, key=key: fmt_label(*key))[0], unit_k1[1])
                      for key, ok in have.items() if ok}
    else:                        # every arm measured the same way: its recorded tokens at the batch rate
        lab = lambda label_12, label_61: (lambda i, a: label_12.format(i=i12[a.axis_dir], i61=i)
                                          if label_12 and a.axis_dir in i12 else label_61.format(i=i))
        unit_k1 = measured_unit(lab(J["k1_12"], J["k1_61"]))
        unit_40 = measured_unit(lab(J["n40_12"], J["n40_61"])) if have40 else None
        stack_unit = {key: measured_unit(lambda i, a, key=key: fmt_label(*key)) for key, ok in have.items() if ok}
    unit_80 = measured_unit(lambda i, a: J["n80_61"].format(i=i)) if have80 else None
    unit_st40 = measured_unit(lambda i, a: st40_label) if have_st40 else None
    for nm, u in [("one axis a call", unit_k1), ("40 answers a call", unit_40), ("80 answers a call", unit_80),
                  (f"{dfmt_name} stacking, 40 answers a call", unit_st40)] + \
                 [(f"{FMT_NAME[f]} k={k}", u) for (f, k), u in stack_unit.items()]:
        if u:
            print(f"[cost] {nm}: ${u[0] * 1e6:.2f} per 1M response-axes; full run, every response: "
                  f"${full_run_cost([(1.0, u)]):,.0f}", file=sys.stderr)

    variants, vkeys, rho_of = projector(data, Path(args.cache_dir), data_dir)
    fold = lambda key: int(((data.qabs[key[2]] * INV_PHI) % 1.0) * CROSSFIT_FOLDS)
    part = lambda items, keep: {key: v for key, v in items.items() if fold(key) in keep}
    rho_mean = lambda items, ax: float(np.mean(list(rho_of(means(items), ax).values())))
    folds = set(range(CROSSFIT_FOLDS))

    arms, left_out = [], {}
    arms.append(dict(key=f"{model}@k1", label=name, family=f"{name}, one axis a call", members=[("j", k1, None)],
                     cost_parts=[(1.0, unit_k1)], figures=["luna61", "answers", "formats"],
                     finer=base >= 1, finer_figures=["luna61"]))     # the anchors (base 1): points every ninth up to all
    if have40:
        arms.append(dict(key=f"{model}@n40", label=f"{name}, 40 answers", family=f"{name}, one axis a call, 40 answers a call",
                         members=[("j", k1_40, None)], cost_parts=[(1.0, unit_40)], figures=["answers"]))
    if have80:
        arms.append(dict(key=f"{model}@n80", label=f"{name}, 80 answers", family=f"{name}, one axis a call, 80 answers a call",
                         members=[("j", k1_80, None)], cost_parts=[(1.0, unit_80)], figures=["answers"]))
    full_grid = all(have.values())                       # the every-axis formats figure needs every format at every k
    sk, ssh = settled if settled else (None, None)
    pen_cache: Dict[Tuple[int, int, int], np.ndarray] = {}

    def penalty(stk, one, j):
        """Each axis's stacking penalty on the folds other than j: stacked minus one axis a call, rho mean of 12."""
        key = (id(stk), id(one), j)
        if key not in pen_cache:
            for o in (one, stk):
                if (id(o), j) not in pen_cache:
                    pen_cache[(id(o), j)] = np.array([rho_mean(part(o[a.axis_dir], folds - {j}), a) for a in axes])
            pen_cache[key] = pen_cache[(id(stk), j)] - pen_cache[(id(one), j)]
        return pen_cache[key]

    def worst_out(stk, one, sh, key):
        """Every axis's items, the worst share sh (by penalty on the other folds) from one axis a call, fold by fold."""
        n = round(sh * A)
        out_of = {j: set(np.argsort(penalty(stk, one, j))[:n].tolist()) for j in folds}
        merged = {}
        for i, a in enumerate(axes):
            items: Dict[Tuple[str, int, int], float] = {}
            for j in folds:
                items.update(part(one[a.axis_dir] if i in out_of[j] else stk[a.axis_dir], {j}))
            merged[a.axis_dir] = items
        left_out[key] = {a.axis_dir: c for i, a in enumerate(axes) if (c := sum(i in out_of[j] for j in folds))}
        return merged, n

    for (fmt, k), ok in have.items():
        if not ok:
            continue
        plain = fmt == dfmt          # the drawn format: the k-and-share figure's family (plain unless --stack_format)
        figs = (["formats"] if full_grid else []) + (["luna61"] if plain else [])
        if figs:
            arms.append(dict(key=f"{model}@{fmt}k{k}", label=f"{name} k={k} {FMT_NAME[fmt]}", family=f"{name} stacked, {FMT_NAME[fmt]}",
                             members=[("j", stacked_by[(fmt, k)], None)], cost_parts=[(1.0, stack_unit[(fmt, k)])], figures=figs,
                             finer=plain and k in (2, 4), finer_figures=["luna61"]))
        for sh in LEAVE_OUT:
            n, pct = round(sh * A), round(100 * sh)
            at_settled = k == sk and abs(sh - ssh) < 1e-9
            figs = (["luna61"] if plain else []) + (["settled_formats"] if at_settled else []) + \
                   (["settled_answers"] if at_settled and plain and have_st40 else [])
            if not figs:
                continue
            key = f"{model}@{fmt}x{pct}k{k}"
            merged, n = worst_out(stacked_by[(fmt, k)], k1, sh, key)
            arms.append(dict(key=key, label=f"{name} k={k} {FMT_NAME[fmt]}, worst {pct}% one axis a call",
                             family=f"{name} stacked, {FMT_NAME[fmt]}, worst {pct}% one axis a call", members=[("j", merged, None)],
                             cost_parts=[(n / A, unit_k1), (1 - n / A, stack_unit[(fmt, k)])], figures=figs,
                             finer=k in (2, 4) or base >= 1))
    if have_st40:
        pct = round(100 * ssh)
        key = f"{model}@{dfmt}n40x{pct}k{sk}"
        merged, n = worst_out(st40, k1_40, ssh, key)
        arms.append(dict(key=key, label=f"{name} k={sk} {dfmt_name}, worst {pct}% one axis a call, 40 answers",
                         family=f"{name} stacked, {dfmt_name}, worst {pct}% one axis a call, 40 answers a call", members=[("j", merged, None)],
                         cost_parts=[(n / A, unit_40), (1 - n / A, unit_st40)], figures=["settled_answers"], finer=sk in (2, 4)))

    check = extrapolation_check(args, E)
    points = arm_points(arms, data, {"j": model}, rho_of, vkeys, check, base=base, step=J["step"])
    ref = points[f"{model}@k1|ninth x {FRACTION_K}/{FRACTION_K}"]["rho"]
    for arm in arms:
        p = points[f"{arm['key']}|ninth x {FRACTION_K}/{FRACTION_K}"]
        d = np.array([p["rho"][vk] - ref[vk] for vk in vkeys])
        print(f"[measured share] {arm['label']:50s} cost {p['cost']:6.0f}  rho {np.mean(list(p['rho'].values())):.4f}  "
              f"minus one axis a call, same coverage: slot 0 {d[:6].mean():+.4f}, slot 6 {d[6:].mean():+.4f}", file=sys.stderr)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data.read += d12.read
    inputs = data.inputs + d12.inputs + [current_files_input(dep_key="cells", paths=sorted(set(data.read)))] + calib_inputs(args)
    if settled and dfmt == settled_fmt and have.get((dfmt, sk)):      # the settled design, for --judge mix
        s_arm = next(a for a in arms if a["key"] == f"{model}@{dfmt}x{round(100 * ssh)}k{sk}")
        dump_settled(settled_path(E, args.judge), args.judge, model, name, s_arm, s_arm["members"][0][1], inputs,
                     extra={"left_out": left_out.get(s_arm["key"])})
    elif settled and dfmt != settled_fmt:
        print(f"[{args.judge}] drawn for the {dfmt_name} format, not the judge's settled {FMT_NAME[settled_fmt]}: no settled dump written",
              file=sys.stderr)
    overlay = None
    if args.overlay_json:
        overlay = json.load(open(args.overlay_json))["result"]["points"]
        inputs = inputs + [current_file_input("overlay", Path(args.overlay_json))]
    fmt_suffix = "" if dfmt == settled_fmt else "_" + dfmt_name.replace(" ", "_")     # a format other than the judge's settled one
    suffix = ("" if args.judge == "luna" else f"_{args.judge}") + fmt_suffix
    drawn = []
    n_settled_fmt = sum(1 for a in arms if "settled_formats" in a["figures"])
    for fig_key, (fig_title, fname, lead), needed in (("luna61", FIGURE_61, bool(plain_ks)), ("answers", FIGURE_ANSWERS, have40),
                                                      ("formats", FIGURE_FORMATS, full_grid),
                                                      ("settled_answers", FIGURE_ANSWERS_SETTLED, have_st40),
                                                      ("settled_formats", FIGURE_FORMATS_SETTLED, n_settled_fmt > 1)):
        if not needed:
            continue
        fname = fname.replace("_luna.png", f"_{args.judge}{fmt_suffix}.png") if args.judge != "luna" and fname.endswith("_luna.png") \
            else fname.replace(".png", f"{suffix}.png") if args.judge != "luna" else fname.replace(".png", f"{fmt_suffix}.png")
        if reprice_at is None and J.get("cache_read"):
            fname = fname.replace(".png", "_measured.png")
        if fig_key == "luna61" and J.get("title_61"):
            fig_title = J["title_61"]
        sub_points = {key: v for key, v in points.items() if fig_key in v["figures"]}
        sub_overlay = {key: v for key, v in overlay.items() if fig_key in v["figures"]} if overlay else None
        fmt_args = dict(name=name, k=sk, pct=round(100 * ssh) if ssh else None, fmt_name=dfmt_name, fmt_example=FMT_EXAMPLE[dfmt],
                        answers="20 against 40" + (" and 80" if have80 else ""))
        STYLE_OVERRIDE.clear()
        if fig_key == "luna61" and dfmt != "rk_pn":     # the drawn format's shares in plain's colours, so the figure reads as plain's
            STYLE_OVERRIDE.update({v["family"]: FAMILY_STYLE[canonical_family(v["family"].replace(f", {dfmt_name}", ", plain"))]
                                   for v in sub_points.values()})
        plot(sub_points, variants, out / fname, f"Response judging, {fig_title.format(**fmt_args)}", A, check, inputs,
             lead=lead.format(**fmt_args) + (f"; dotted: the same arms measured on the ninth alone and extrapolated from it "
                                             f"({Path(args.overlay_json).name})" if sub_overlay else ""),
             axes_file=args.axes_file, base=base,
             min_cost=MIN_COST_61 if fig_key in ("luna61", "settled_answers", "settled_formats") else 0.0,
             answers_key=fig_key in ("answers", "settled_answers"), overlay=sub_overlay)
        STYLE_OVERRIDE.clear()
        drawn.append(fname)
        print(f"wrote {out / fname}", file=sys.stderr)
    title = f"Response judging on 61 axes, {name} only: answers a call and stacking, under 12 projection variants"
    result = {"config": {"judge": args.judge, "model": model, "measured_share": base, "axes_file": args.axes_file,
                         "variants": vkeys, "prices": PRICES, "october_responses": OCTOBER_RESPONSES,
                         "n_axes": N_AXES, "stack_k": list(STACK61_K), "leave_out": list(LEAVE_OUT), "figures": drawn,
                         "crossfit": f"{CROSSFIT_FOLDS} folds by frac(Q / phi) of the absolute question; each fold's left-out axes "
                                     "the worst by stacking penalty (rho mean of 12 variants) on the other folds",
                         "fractions": "m/3 of the measured share, golden (judge_tier_cost_eval.golden_point), 3 rotations",
                         "extrapolation": "Spearman-Brown from a split half by question",
                         "unit_costs_basis": "Luna: one axis a call by its production cost model, stacked runs measured; "
                                             "other judges: every arm's recorded tokens at the batch rate"},
              "unit_costs": {"one axis a call": unit_k1, "40 answers a call": unit_40,
                             **{f"{FMT_NAME[f]} k={k}": u for (f, k), u in stack_unit.items()}},
              "left_out_folds": left_out, "extrapolation_check": check, "points": points}
    jname = f"judge_response_pareto_61{fmt_suffix}.json" if args.judge == "luna" else f"judge_response_pareto_61_{args.judge}{fmt_suffix}.json"
    (out / jname).write_text(json.dumps(json_metadata(result, title=title, inputs=inputs), indent=1))
    print(f"wrote {out / jname}", file=sys.stderr)
    return 0

FAMILY_STYLE = {
    "Luna, one axis a call": ("#222222", "o"),
    "Luna, one axis a call, 40 answers a call": ("#8C8C8C", "o"),
    "Luna, one axis a call, 80 answers a call": ("#6A3D9A", "o"),
    "Luna stacked, plain, worst 10% one axis a call, 40 answers a call": ("#8C8C8C", "s"),
    "Luna stacked, plain, worst 20% one axis a call, 40 answers a call": ("#8C8C8C", "s"),
    "Luna stacked, plain, worst 25% one axis a call, 40 answers a call": ("#8C8C8C", "s"),   # Haiku and Gemini at 25% (2026-11-07)
    "Luna stacked, labelled, worst 10% one axis a call": ("#D95F02", "s"),
    # green, not axis by axis's usual purple: beside the plain 10% arm's blue the two were hard to tell apart (Roger, 2026-11-05)
    "Luna stacked, axis by axis, worst 10% one axis a call": ("#66A61E", "s"),
    "Luna stacked, plain": ("#1B9E77", "s"),
    "Luna stacked, labelled": ("#D95F02", "s"),
    "Luna stacked, axis by axis": ("#7570B3", "s"),
    "Luna stacked, plain, worst 10% one axis a call": ("#1F78B4", "s"),
    "Luna stacked, plain, worst 15% one axis a call": ("#66A61E", "s"),
    "Luna stacked, plain, worst 20% one axis a call": ("#E7298A", "s"),
    "Luna stacked, plain, worst 25% one axis a call": ("#A6761D", "s"),
    "Luna stacked, labelled, worst 20% one axis a call": ("#D95F02", "s"),
    "Luna stacked, labelled, worst 25% one axis a call": ("#D95F02", "s"),
    "Luna stacked, axis by axis, worst 20% one axis a call": ("#7570B3", "s"),
    "Luna stacked, axis by axis, worst 25% one axis a call": ("#66A61E", "s"),
    "Jev, yes/no between the ends": ("#1B9E77", "o"),
    # the 61 axes go in even chunks, so the request sizes are what the families name (Roger, 2026-11-05: "Make the
    # labelling honest, x 24 -> x 20"): --axes_per_request 24, 12, 6, 1 give 20-21, 10-11, 5-6 and 1 axes a request
    "Jev yes/no, 20 answers x 30-31 axes a request": ("#1B9E77", "o"),
    "Jev yes/no, 20 answers x 20-21 axes a request": ("#1F78B4", "o"),
    # estimated, not judged (Roger, 2026-11-05: "an estimate for 40 x 12-13", the largest clean shape at 40 answers)
    "Jev yes/no, 40 answers x 12-13 axes a request (estimated from 10-11)": ("#7A0177", "^"),
    "Jev yes/no, 20 answers x 10-11 axes a request": ("#E7298A", "o"),
    "Jev yes/no, 40 answers x 10-11 axes a request": ("#E7298A", "^"),
    "Jev yes/no, 20 answers x 5-6 axes a request": ("#66A61E", "o"),
    "Jev yes/no, 40 answers x 5-6 axes a request": ("#66A61E", "^"),
    "Jev yes/no, 20 answers x 1 axis a request": ("#E6AB02", "o"),
    "Jev yes/no, 40 answers x 1 axis a request": ("#E6AB02", "^"),
    "Jev, yes/no against the other answers": ("#D95F02", "o"),
    "Jev, five levels between the ends": ("#7570B3", "D"),
    "Jev, five levels against the other answers": ("#E6AB02", "D"),
    "Jev, 20 answers x 12 axes a request": ("#E7298A", "o"),
    "Jev, 40 answers x 12 axes a request": ("#E7298A", "^"),
    "Jev, 20 answers x 6 axes a request": ("#66A61E", "o"),
    "Jev, 40 answers x 6 axes a request": ("#66A61E", "^"),
    "Jev, 20 answers x 1 axis a request": ("#E6AB02", "o"),
    "Jev, 40 answers x 1 axis a request": ("#E6AB02", "^"),
    "Haiku, one axis a call": ("#E08214", "o"),
    "Luna + Haiku, both judge every response": ("#8E6BBF", "D"),
    "Luna + Haiku, each response by one": ("#8E6BBF", "P"),
    "Luna + Haiku + Gemini, each response by one": ("#17BECF", "P"),
    "Luna + Jev, both judge every response": ("#A6761D", "D"),
    "Luna + Jev, each response by one": ("#A6761D", "P"),
    "Luna + Haiku + Jev, all judge every response": ("#1F78B4", "D"),
    "Luna + Haiku + Jev, each response by one": ("#1F78B4", "P"),
    # Jev's production shape on the third (the Jev shapes figure)
    "Jev yes/no, 20 answers x 30-31 axes a request (a third)": ("#1B9E77", "D"),
    # the mix figure (--judge mix): each judge alone at its settled design, and the golden splits
    "Luna alone, settled design": ("#222222", "o"),
    "Haiku alone, settled design": ("#E08214", "o"),
    "Gemini alone, settled design": ("#17BECF", "o"),
    "Jev alone, settled design": ("#7570B3", "o"),
    "split: Luna + Haiku + Gemini": ("#1F78B4", "P"),
    "split: Luna + Haiku + Jev": ("#E7298A", "P"),
    "split: Luna + Gemini + Jev": ("#66A61E", "P"),
    "split: Haiku + Gemini + Jev": ("#A6761D", "P"),
    "split: all four": ("#D62728", "*"),
    "all four, every response by every judge": ("#D62728", "D"),
    "Haiku + Gemini + Jev, every response by every judge": ("#A6761D", "D"),
    "Luna + Haiku + Gemini, every response by every judge": ("#1F78B4", "D"),
    "Luna + Haiku + Jev, every response by every judge": ("#E7298A", "D"),
    "Luna + Gemini + Jev, every response by every judge": ("#66A61E", "D"),
}
K_MARKER = {"k2": "s", "k4": "^", "k6": "v"}


def canonical_family(family: str) -> str:
    """The FAMILY_STYLE key of a family: itself, or with its judge's name read as Luna's (the 61-axis mode names its
    judge: "Haiku 5.5 stacked, plain" is styled as "Luna stacked, plain")."""
    if family in FAMILY_STYLE:
        return family
    key = re.sub(r"^[^,]+?(, | stacked)", lambda m: "Luna" + m.group(1), family, count=1)
    if key not in FAMILY_STYLE:      # a format's family the table lacks (labelled at 15%, a labelled 40-answer arm): plain's style
        for fmt_name in ("labelled", "axis by axis"):
            key = key.replace(f", {fmt_name}", ", plain")
    return key


#: styles for one figure, consulted before FAMILY_STYLE: main61's k-and-share figure for a format other than plain
#: colours that format's shares as plain's, so that the figure reads as the plain one does (set around the plot call)
STYLE_OVERRIDE: Dict[str, Tuple[str, str]] = {}


def style_of(family: str) -> Tuple[str, str]:
    return STYLE_OVERRIDE.get(family) or FAMILY_STYLE[canonical_family(family)]


def plot(points: Dict[str, dict], variants, out_png: Path, title: str, n_axes: int, check: dict, inputs,
         ref_arms=frozenset(), lead: str = "", axes_file: str = AXES_12, base: float = NINTH,
         min_cost: float = 0.0, answers_key: bool = False, overlay: Optional[Dict[str, dict]] = None) -> None:
    """``min_cost``: points below it are not drawn, but the frontier is the hull of every point, so its line (and an
    arm's) runs from the cheapest drawn point toward the next one below, cut at the left edge (Roger, 2026-11-05: "do
    use the best point below $10 to figure out where the Pareto frontier goes next, and avoid going down the $10
    cutoff edge").  ``overlay``: another run's points for the same arms, whose extrapolated points are drawn dotted
    (outline and line, from that run's largest measured point) and kept off the frontier (Roger, 2026-11-06: "a Luna
    plot, with the old extrapolated points dotted")."""
    all_points = points
    points = {k: p for k, p in points.items() if p["cost"] >= min_cost}

    def clipped(ks, q):
        """(x, y) of keys sorted by cost, those below min_cost replaced by the segment's crossing of min_cost."""
        xs, ys = [all_points[k]["cost"] for k in ks], [q[k] for k in ks]
        i = next((j for j, x in enumerate(xs) if x >= min_cost), len(xs))
        if i == 0 or i == len(xs):
            return xs[i:], ys[i:]
        t = (math.log(min_cost) - math.log(xs[i - 1])) / (math.log(xs[i]) - math.log(xs[i - 1]))
        return [min_cost] + xs[i:], [ys[i - 1] + t * (ys[i] - ys[i - 1])] + ys[i:]

    smallest = min(p["coverage"] for p in points.values() if p["measured"])
    vkeys = [v.key for v in variants]
    sl = list(dict.fromkeys((v.slot, v.layer) for v in variants))
    regimes = list(dict.fromkeys(v.regime for v in variants))
    fig, axs = plt.subplots(len(regimes), len(sl), figsize=(4.9 * len(sl), 4.1 * len(regimes) + 2.2), squeeze=False)
    costs = [p["cost"] for p in points.values()]
    x_lo, x_hi = (min_cost if min_cost else min(costs) / 1.5), max(costs) * 1.5
    ticks = [t for t in (3, 10, 30, 100, 300, 1000, 3000) if x_lo <= t <= x_hi]
    for r, regime in enumerate(regimes):
        for c, (s, l) in enumerate(sl):
            ax = axs[r][c]
            vk = next(v.key for v in variants if (v.slot, v.layer, v.regime) == (s, l, regime))
            keys = list(points)
            q = {k: 1 / (1 - all_points[k]["rho"][vk]) for k in all_points}
            fkeys = [k for k in all_points if all_points[k]["arm"] not in ref_arms]
            idx = pareto_frontier([(all_points[k]["cost"], q[k]) for k in fkeys])
            front = sorted((fkeys[i] for i in idx), key=lambda k: all_points[k]["cost"])
            for arm in dict.fromkeys(p["arm"] for p in points.values()):
                ks = sorted([k for k in keys if points[k]["arm"] == arm], key=lambda k: points[k]["cost"])
                fam = points[ks[0]]["family"]
                col, mk = ("#BBBBBB", "o") if arm in ref_arms else style_of(fam)
                kk = re.search(r"k(\d)$", arm)
                if kk and "stacked" in fam:
                    mk = K_MARKER[f"k{kk.group(1)}"]
                ms = [k for k in ks if points[k]["measured"]]
                ex = [k for k in ks if not points[k]["measured"]]
                ms_all = sorted([k for k in all_points if all_points[k]["arm"] == arm and all_points[k]["measured"]],
                                key=lambda k: all_points[k]["cost"])
                ax.plot(*clipped(ms_all, q), "-", color=col, lw=0.8, alpha=0.6)
                if ex:
                    ax.plot([points[k]["cost"] for k in ms[-1:] + ex], [q[k] for k in ms[-1:] + ex], ":", color=col, lw=0.8, alpha=0.6)
                ax.scatter([points[k]["cost"] for k in ms], [q[k] for k in ms], s=[18 + 22 * points[k]["m"] / FRACTION_K for k in ms],
                           marker=mk, color=col, edgecolors="black" if False else col, zorder=3)
                ax.scatter([points[k]["cost"] for k in ex], [q[k] for k in ex], s=40, marker=mk, facecolors="none",
                           edgecolors=col, linewidths=1.2, zorder=3)
                oks = sorted([k for k in (overlay or {}) if overlay[k]["arm"] == arm], key=lambda k: overlay[k]["cost"])
                oms, oex = [k for k in oks if overlay[k]["measured"]], [k for k in oks if not overlay[k]["measured"]]
                if oex:
                    oq = {k: 1 / (1 - overlay[k]["rho"][vk]) for k in oms[-1:] + oex}
                    ax.plot([overlay[k]["cost"] for k in oms[-1:] + oex], [oq[k] for k in oms[-1:] + oex], ":", color=col,
                            lw=0.9, alpha=0.45)
                    ax.scatter([overlay[k]["cost"] for k in oex], [oq[k] for k in oex], s=52, marker=mk, facecolors="none",
                               edgecolors=col, linewidths=1.3, linestyle=(0, (1, 1.2)), alpha=0.85, zorder=3)
                    ax.scatter([overlay[k]["cost"] for k in oms[-1:]], [oq[k] for k in oms[-1:]], s=10, marker=mk,
                               color=col, alpha=0.6, zorder=3)
            ax.plot(*clipped(front, q), "--", color="#444444", lw=1.0, alpha=0.8, zorder=2)
            for k in (k for k in front if k in points):
                ax.scatter(points[k]["cost"], q[k], s=90, facecolors="none", edgecolors="#222222", linewidths=0.9, zorder=4)
            ax.set_xscale("log")
            ax.set_xlim(x_lo, x_hi)
            ax.set_xticks(ticks)
            ax.set_xticklabels([f"\\${t:,}" for t in ticks])
            ax.minorticks_off()
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=8)
            ax.set_title(f"{vk}{'  (default)' if vk == rob.DEFAULT_VARIANT else ''}", fontsize=10,
                         fontweight="bold" if vk == rob.DEFAULT_VARIANT else "normal")
            if c == 0:
                ax.set_ylabel("1 / (1 - mean rho)", fontsize=9)
            if r == len(regimes) - 1:
                ax.set_xlabel("estimated total cost of a full run (USD, 200 October axes)", fontsize=9)
    ref_fams = {p["family"] for p in points.values() if p["arm"] in ref_arms}
    present = list(dict.fromkeys(p["family"] for p in points.values()))
    order = list(FAMILY_STYLE)
    present.sort(key=lambda f: order.index(canonical_family(f)))
    # on an answers figure every colour names its answer count (Roger, 2026-11-05: "add the 20 part to the key")
    key_label = lambda fam: fam if not answers_key or "answers a call" in fam else f"{fam}, 20 answers a call"
    handles = [plt.Line2D([0], [0], marker=style_of(fam)[1], color=style_of(fam)[0], lw=0.8, label=key_label(fam), markersize=7)
               for fam in present if fam not in ref_fams]
    handles += [plt.Line2D([0], [0], marker="o", color="#BBBBBB", lw=0.8, label=f"{fam} (reference, off the frontier)", markersize=7)
                for fam in sorted(ref_fams)]
    ks_present = {f"k{m.group(1)}" for p in points.values() if "stacked" in p["family"] and (m := re.search(r"k(\d)$", p["arm"]))}
    handles += [plt.Line2D([0], [0], marker=m, color="#777777", lw=0, label=f"stacked {k[1]} axes a call", markersize=7)
                for k, m in K_MARKER.items() if k in ks_present]
    if overlay:
        handles += [plt.Line2D([0], [0], marker="o", color="#777777", markerfacecolor="none", ls=":", lw=0.9,
                               label="the ninth alone, as drawn before: measured (small), extrapolated (dotted)")]
    extrapolated = [name for name, t in (("1/3", 1 / 3), ("all", 1.0)) if t > base * (1 + 1e-9)]
    if any(p.get("lifted") for p in points.values()):
        extrapolated = ["the base lifted by its question-cut penalty"] + extrapolated
    handles += ([plt.Line2D([0], [0], marker="o", color="#777777", markerfacecolor="none", lw=0,
                            label=f"extrapolated ({', '.join(extrapolated)})")] if extrapolated else []) + \
               [plt.Line2D([0], [0], marker="o", color="#222222", markerfacecolor="none", markersize=10, lw=0,
                           label="on the frontier (its convex hull)")]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 0.0))
    sub = ("\n".join(textwrap.wrap(f"{n_axes} axes ({axes_file}); {lead}", 230)) + "\n" + "\n".join(textwrap.wrap(
           f"{'a ninth' if base == NINTH else 'all' if base >= 1 else Fraction(base).limit_denominator(1000)} of the kept responses measured: points from {Fraction(smallest).limit_denominator(1000)} (smallest drawn) to "
           f"{Fraction(base).limit_denominator(1000)}, subsampled the golden way (absolute question and instruction)"
           f"{f'; nothing below ${min_cost:.0f} drawn' if min_cost else ''}; larger coverages extrapolated in two parts "
           f"(hollow: {calibration_text(check, base)})", 230)) + "\n"
           f"cost of a full run, 200 October axes (1,273 entities x 425 kept responses) at the point's coverage, every prefix cached: Luna by Flex, "
           f"Haiku by Message Batches, Gemini by its Batch API with explicit caches, Jev at its measured cost (no cache)")
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.995)
    fig.text(0.5, 0.965, sub, ha="center", va="top", fontsize=8.5)
    n_sub = sub.count("\n") + 1                   # the panels move down for a fifth subtitle line
    fig.subplots_adjust(top=0.885 - 0.013 * max(0, n_sub - 4), bottom=0.12, left=0.05, right=0.985, hspace=0.32, wspace=0.18)
    fig.savefig(out_png, dpi=130, metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
