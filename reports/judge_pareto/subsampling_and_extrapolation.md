# Subsampling in the response-judging pilots, and the extrapolation above them

Written 2026-11-07 (Roger: "We should write up an explanation"), after the question-cut penalty was understood and the
extrapolation redone in two parts.  For whoever reads the response-Pareto figures in
[`roger/axis_judge_experiments/response_pareto/`](../../roger/axis_judge_experiments/response_pareto/) — Roger, Konstantinos,
the next agent — and for whoever changes [`scripts/judge_response_pareto.py`](../../scripts/judge_response_pareto.py).
The decisions those figures carried are in [`response_judging_plan.md`](./response_judging_plan.md) § 4e; this note is about
how to read the figures, not what was decided.

## 1. Two ways of taking a fraction of the responses

Every entity (1,273 personas: traits and roles) has 425 kept responses in the May data, to 40 questions under 5
instructions, a couple of samples each.  Judging a fraction of them can be done two ways.

**Cut by question.**  Keep whole questions: for coverage 1/9, every entity is judged on the same ninth of the questions
(4–5 of the 40, all their instructions and samples; rotated by entity rank, so the questions differ between entities but
each entity's judged mean rests on 4–5 questions).  This is how the pilots were judged: the tool cut by question until
2026-11-04, the batches of 20 answers to one question made it the natural unit, and every later cell had to match the
earlier ones to be comparable and extendable.  The ninth (parts 0, 9 and 18 of a split in 27) and the third (parts 0, 3
and 6 of a split in 9) that every judge was run on are cuts of this kind.

**Golden.**  Keep the responses whose *golden point* — the fractional part of (5Q + p) / φ, from the response's absolute
question number Q and instruction p (`judge_tier_cost_eval.golden_point`) — falls in the first fraction of the unit
circle.  A low-discrepancy rule: the kept responses of each entity spread evenly over questions and instructions, as
close to a random subsample as a deterministic rule gets, with no clustering.  The same rule assigns shares between judges
when several split the responses (judge i of J takes the points in [i/J, (i+1)/J)), which is where "golden split" comes
from; for one judge it only says which responses are kept.  This is how the tool has cut since 2026-11-04 and how
production will subsample.

In the figures, every measured base — the ninth, the third — is cut by question.  The smaller measured points below a
base (1/27, 2/27, and the finer 1/81, 2/81) are golden subsamples *of that cut share*, so they inherit its cut and add a
within-share loss of their own.  The only golden subsamples of everything are the six-axis anchor's
([`judge_response_anchor6_quality.png`](../../roger/axis_judge_experiments/response_pareto/judge_response_anchor6_quality.png)),
which judged every response on six axes.

## 2. The question-cut penalty

A share cut by question scores below a golden subsample of the same size, because the judge mean of each entity rests on
4–5 whole questions where the golden one spreads over most of the 40, and the per-entity mean is correlated with an
activation projection taken over all 425 responses.  Measured on the 61 pilot axes × 12 projection variants, as a golden
ninth of the third against the cut ninth, both read from each judge's settled third (the cut ninth is the third's part 0
of the split in 9, (question + entity rank) % 9 = 0: the same cells the ninth figures measure; `two_part_calibration` in
[`judge_response_pareto.py`](../../scripts/judge_response_pareto.py), from the settled third dumps):

| judge | cut ninth | golden ninth of the third | penalty at a ninth | cut third |
|---|---|---|---|---|
| Luna (k=4, worst 20% one axis a call) | 0.7242 | 0.7324 | **+0.0082** | 0.7402 |
| Haiku 5.5 (k=2, worst 10%, its third's design; see below) | 0.7330 | 0.7366 | **+0.0036** | 0.7434 |
| Gemini 3.1 Flash-Lite (k=6, worst 25%) | 0.7314 | 0.7399 | **+0.0086** | 0.7446 |
| Jev 1.14 (yes/no, 20 × 30–31) | 0.7381 | 0.7482 | **+0.0101** | 0.7520 |

Until 2026-11-07 10:00 UTC the cut ninth was read from each judge's *ninth* dump instead (Luna +0.0074, Haiku +0.0039
then; Gemini, whose third was not yet judged, took the mean of the others).  The ninth dump holds the same cells, but
its worst-X% composition is chosen on the ninth's own folds where the third's is chosen on the third's, and the two
differ on 5–8% of the items (0 for Jev, which composes nothing), worth 0.0008 on Luna and 0.0003 on Haiku: composition
noise, not question-cut penalty.  Reading both terms from the third keeps the penalty a pure question-cut effect at one
design, which matters for Haiku: its ninth has been settled at k=4, worst 25% since 2026-11-07 while its third exists at
k=2, 10%, and pairing the two dumps would have passed the designs' difference (about 0.0015 at a ninth) off as penalty.
Haiku's ninth is lifted by the penalty measured at its third's design, the nearest measured.  The gap is
judge-dependent — Jev's binary answers lose most from resting on few questions — and axis-dependent: on the six anchor
axes Haiku's gap is 0.0097 where its 61-axis mean is 0.0039, so the calibration keeps the penalty per axis and a figure on
a subset of axes uses its own axes' values.  The "golden ninth of the third" is itself inside a cut third, whose own
penalty against a golden third is about 0.002 on the anchor's six axes (Luna +0.002 / −0.001, Haiku +0.003 / +0.002 for
its two designs), so the true penalty of a cut ninth against golden-everything is these numbers plus about 0.002.

The penalty shrinks with coverage: a cut share at coverage c rests on 40c questions, and its loss against a golden
subsample goes roughly as 1/c − 1 (8 units at a ninth, 2 at a third, 0 at everything), which the anchor's thirds agree
with within their noise.  The model uses that law anchored at the measured ninth and zero at the third:
`penalty(delta9, c) = delta9 × (1/c − 3) / 6`.

The plainest picture of it is the Jev shapes figure
([`judge_response_pareto_61_jev_shapes.png`](../../roger/axis_judge_experiments/response_pareto/judge_response_pareto_61_jev_shapes.png)):
the teal circles are the cut ninth and golden subsamples of it, the teal diamonds golden subsamples of the cut third — the
same design — and at the same coverage and cost (1/9, $41) the diamond is 0.7482 against the circle's 0.7381.

## 3. What the figures do and do not say

- **Rankings between designs within a figure stand.**  Every arm sits on the same cut share, so the depression is common to
  them (nearly: the penalty differs a little by design).  Every decision in the plan — k, the percentage left out,
  20 against 40 answers, the formats, the judges' order, the splits — was made on measured points at equal coverage.
- **Absolute levels and the slope do not.**  The measured ninth-to-third-to-all curve is steeper than the real one; a
  golden subsample at the same coverage scores 0.004–0.010 higher at a ninth and about 0.002 higher at a third.  A
  subset(N) production mode subsamples the golden way, so its quality must be read off the golden curve — the lifted
  base, the Jev diamonds, the anchor — not off the cut pilots.  On that reading a golden third gives up about
  0.002–0.003 against everything, not the 0.005 the cut figures suggested.
- **The cost axis is unaffected**: the cut and golden subsamples of one coverage cost the same.

## 4. The extrapolation above a base, in two parts

Coverages above a base (the third and everything from a ninth; everything from a third) are extrapolated.  Since
2026-11-07 the extrapolated points are drawn in two parts (`arm_points`):

1. **The lift.**  The base is raised by its question-cut penalty on the figure's axes at its coverage (§ 2), and drawn as a
   hollow point at the base's cost, above the measured one.  The vertical step is the penalty made visible.
2. **Spearman-Brown by question from the lifted base.**  Each arm's split-half reliability R is measured on its own share
   (the per-entity means of alternate questions, correlated across entities, Spearman-Brown to the whole), raised to the
   judge's golden-over-cut ratio at a ninth (Luna 0.974/0.960, Haiku 0.978/0.970, Gemini 0.982/0.970, Jev 0.984/0.966;
   nothing above a third).  Coverage M times the base's has reliability R_M = M R / (1 + (M − 1) R), and ρ grows by
   s × (√(R_M / R) − 1), where s is measured per judge on golden steps within the third (1/9 → 1/3: **Luna 1.19,
   Haiku 1.25, Gemini 1.04, Jev 0.94**; on 1/9 → 2/9 the same to 0.02, so the law fits the golden curve's shape).

Both ingredients come from each judge's settled third dump on the 61 axes
([`_tier_eval_scratch/settled61/`](../../roger/axis_judge_experiments/_tier_eval_scratch/settled61/), git-ignored), whose
part 0 of the split in 9 is the cut ninth (§ 2), are
cached as [`extrapolation_calibration.json`](../../roger/axis_judge_experiments/response_pareto/extrapolation_calibration.json)
beside the figures (remade when a third dump changes), and are named in every figure's subtitle.  A judge without a
third dump took the mean of the others (Gemini until 2026-11-07); a mix arm takes the mean of its judges.  Known
residuals: the cut third's own penalty (about 0.002) is not lifted, so extrapolated
points may run that much low; and the calibration is per judge and axis, not per projection variant (below).  The anchor
script ([`judge_response_anchor.py`](../../scripts/judge_response_anchor.py)) draws the model's predictions from the ninth
and from the third against the anchor's measured golden curve, and prints the s each measurement implies beside the
calibrated one.

**Checked against the anchor (2026-11-07; after a fix, since the anchor script had applied the golden-over-cut ratio
twice, once in the figure JSON's reliability and once itself).**  From the cut ninth, the prediction at every response is
within 0.003 of the six-axis measurement on every row
([`judge_response_anchor6_quality.png`](../../roger/axis_judge_experiments/response_pareto/judge_response_anchor6_quality.png)):

| judge, design | ninth | predicted at all | measured at all | implied s (calibrated) |
|---|---|---|---|---|
| Luna, one axis a call | 0.7039 | 0.7237 | 0.7237 | 1.20 (1.19) |
| Luna, settled (k=4, worst 20%) | 0.7163 | 0.7386 | 0.7369 | 1.00 (1.19) |
| Haiku, one axis a call | 0.7200 | 0.7362 | 0.7379 | 1.50 (1.25) |
| Haiku, settled (k=2, worst 10%) | 0.7218 | 0.7381 | 0.7409 | 1.63 (1.25) |
| Jev, 20 answers × 5–6 axes | 0.7375 | 0.7520 | 0.7517 | 0.89 (0.94) |

From the third the same (Luna 0.7236 and 0.7397 predicted against 0.7237 and 0.7369; Haiku 0.7363 and 0.7395 against
0.7379 and 0.7409).  Haiku's settled row is the anchor's measured design, k=2, worst 10% (the settled design until
2026-11-07; its third's parts exist at k=2 only).  The anchor script takes the calibration each figure JSON carries, so
the rows above are under the ninth-dump calibration (Luna +0.0074, Haiku +0.0039 at a ninth on the 61 axes; on the six
axes +0.0119, +0.0073, Jev +0.0092); the rows under the third-only calibration of § 2 follow the next redraw of the
figures.  Gemini has no anchor cells, so its rows are predictions only.  On the 61 axes, the ninth's extrapolation to a third set against the measured cut third is within
±0.003 on 11 of the 12 projection variants for every judge, with mean 0.000 for the settled designs and +0.001 to +0.002
for one axis a call (the ideal is about +0.002, the cut third's own penalty, so the settled designs run a little low);
the twelfth, `s0_l25_raw`, overshoots by +0.004 to +0.006 for every judge (Luna +0.006, Haiku +0.004, Jev +0.004), so the
penalty and s, which are means over the variants, misfit that one variant.  A per-variant calibration would fix it; not
done (2026-11-07).

### What it replaced, and why the old curves kinked

Until 2026-11-07 the raw Spearman-Brown gain was multiplied by one ratio: 1.86 (the score-alone rubric's third and full
cells, eight cases), then 1.62 (Luna's cut third against its cut ninth, 6 designs × 12 variants, Roger 2026-11-06: "redo
the extrapolation updated on that data").  That ratio folded two things together — the gain from coverage, which
Spearman-Brown models, and the recovery of the question-cut penalty, which it does not — so it was only right for steps
like the one it was fitted on: from a golden base it overshot (the anchor's golden curves rise about 0.85 × the raw
gain), and from the cut bases of other judges it wandered (Haiku's implied ratio 1.43, Jev's 1.22).  The kink in the old
figures, where the first extrapolated step rose faster than the measured curve, was the penalty's recovery being added on
top of the coverage gain; the diamonds measured the level it reached (0.7520 at the third against 0.7519 extrapolated),
so the kink was right in level and wrong in shape.

## 5. Pinning it down further

Judging the four settled designs on every response of the 61 axes would replace the lift with measurement, at roughly
61/321 of a production run each — about Luna $190, Haiku $160, Gemini $235, Jev $115, $700 in all — for charts, not
decisions.  Two cheaper routes: a golden ninth per judge at its settled design (about $15–25 each, $70 for the four),
which would make the lifted base a measured point and pin the 0.002 residual; or the first production run, which is golden
at whatever coverage it uses and becomes the measured point for every judge in it.  Recommendation (2026-11-07):
neither now.

## 6. Error bars on the mixes

Roger (2026-11-07): "do you have a way to put error bars on those rho and quality numbers? I'd suggest estimating as if
we were redrawing the set of questions used from a larger set", then "add the variance for redrawing axes, and for
rejudging", and "I'm interested in the variance of the relative answers, not the variance in the absolute score: some
axes are just easier or harder for all judges."  [`judge_response_error_bars.py`](../../scripts/judge_response_error_bars.py)
(tests: [`test_judge_response_error_bars.py`](../../results_analysis/tests/test_judge_response_error_bars.py)) reads the
settled dumps that `--judge mix` reads and takes the same arms, each judge alone and the golden splits of three and of
four, and applies every draw identically to every arm, axis and variant, reporting each arm's **paired difference from
the best golden split** under the draw, so that an axis or a question that is hard for every judge cancels.  Three
components, reported separately and in quadrature:

1. **Redrawing the questions**: a bootstrap over the third's 100 question positions (every arm keeps its items with their
   judge assignment; the positions are resampled with replacement and the entity means recomputed with the
   multiplicities; 200 draws).
2. **Redrawing the axes**: a bootstrap over the 61 axes of each arm's per-axis ρ (mean of the 12 variants), the same axis
   resample for every arm (2,000 draws).
3. **Rejudging**: Gaussian noise with each judge's per-item rejudge sd added to every item, one draw per (judge, axis,
   item) shared by every arm that holds the item (100 draws).  The sd is read off pairs of cells that judged the same
   responses under near-identical designs (the ninth's stacked plain cells at k = 2, 4 and 6 for the LLM judges;
   Jev's yes/no at 12, 24 and 31 axes a request): the sd of the centred pair difference over √2, written to
   [judge_response_rejudge_noise.json](../../roger/axis_judge_experiments/response_pareto/judge_response_rejudge_noise.json).

| judge | per-item rejudge sd | item score sd | noise share of item variance |
|---|---|---|---|
| Luna | 10.9 | 27.8 | 0.15 |
| Haiku | 13.6 | 25.8 | 0.28 |
| Gemini | 8.7 | 26.5 | 0.11 |
| Jev | 2.1 | 31.9 | 0.00 |

Jev is deterministic given a request, so its sd is the effect of packaging the request differently; the LLM judges'
pairs differ a little in design (the axes a call), so their sd overstates pure rejudging slightly.

**The result on the third dumps** (Haiku at k=2, worst 10%, its third's design at the time; Luna k=4, 20%; Gemini k=6,
25%; Jev 20 answers × 30–31 axes a request; [judge_response_error_bars_third.json](../../roger/axis_judge_experiments/response_pareto/judge_response_error_bars_third.json)):

| arm | ρ at the third | Δ vs HGJ | SE questions | SE axes | SE rejudging | SE all | Δ/SE |
|---|---|---|---|---|---|---|---|
| Haiku + Gemini + Jev | 0.7591 | 0 | | | | | |
| all four | 0.7574 | −0.0017 | 0.0003 | 0.0012 | 0.0001 | 0.0012 | −1.4 |
| Luna + Gemini + Jev | 0.7570 | −0.0021 | 0.0005 | 0.0015 | 0.0001 | 0.0016 | −1.3 |
| Luna + Haiku + Jev | 0.7566 | −0.0025 | 0.0005 | 0.0018 | 0.0001 | 0.0019 | −1.4 |
| Jev alone | 0.7520 | −0.0071 | 0.0012 | 0.0040 | 0.0002 | 0.0042 | −1.7 |
| Luna + Haiku + Gemini | 0.7517 | −0.0074 | 0.0004 | 0.0020 | 0.0001 | 0.0021 | −3.6 |
| Gemini alone | 0.7446 | −0.0145 | 0.0006 | 0.0027 | 0.0002 | 0.0028 | −5.2 |
| Haiku alone | 0.7434 | −0.0156 | 0.0007 | 0.0028 | 0.0002 | 0.0029 | −5.4 |
| Luna alone | 0.7402 | −0.0189 | 0.0011 | 0.0038 | 0.0003 | 0.0040 | −4.7 |

What it says.  The axis redraw is the component that matters.  Rejudging is negligible: at a third each entity mean
averages about 150 items, so even Haiku's 13.6 points of per-item noise moves a split's ρ by 0.0001.  The question
redraw is three to five times smaller than the axis redraw.  With the axes in, the three Jev-containing 3-way splits and
the 4-way lie within 1.3–1.4 standard errors of one another, so the 61 axes cannot say which judge to leave out; leaving
Jev out costs 0.0074 at 3.6 standard errors, and any split beats any judge alone by about 5.  The cruder check agrees: on
each of the third's three ninths alone (parts 0, 3 and 6 of the split in 9), Haiku + Gemini + Jev leads all four by
0.0031, Luna + Gemini + Jev by 0.0048 and Luna + Haiku + Jev by 0.0053, with a spread of 0.0002–0.0003 across the three.
The absolute standard errors (not reported above) are about 0.002 for the questions and 0.009 for the axes on every
arm: that is the error bar on a single number, and most of it is common to every arm.  If the differences held at their
point values, the 321 production axes would shrink the axis SE by a factor of about 2.3 and separate the splits.

**Instructions per entity** (Roger: "Increasing the number of instructions per entity is currently untested: could you
test that (by faking dropping one)"; `--drop_instructions`).  The data has 5 instructions per entity and 100 questions
each.  Dropping one instruction from the judged items (the vectors keep all five) costs 0.0023–0.0026 on every arm, with
a spread of 0.001 over which one is dropped; dropping two costs 0.0055–0.0069.  That is the "fewer judged items" effect
of the question cut again, so on the judging side a sixth instruction would be worth about +0.002, like 20% more
questions.  What it cannot test is the vector side, whether a sixth instruction's responses make a better activation
mean: the cached slices are averaged over responses, so that needs the per-response activations (for May on the G-Drive
archive, for October on the pods' volumes), a recompute of the entity vectors and the axes leaving one instruction
out, hours of reading and no judging.

**To redo on the October data**: make each judge's settled dump on that tree
(`judge_response_pareto.py --stack_group g61 --judge <luna|haiku|gemini|jev>` for the ninths, `--judge <luna3|...>` for
the thirds, with that tree's `--experiments_dir`, `--data_dir` and `--cache_dir`), then
`judge_response_error_bars.py --dumps third --drop_instructions` with the same flags.  The rejudge noise is re-estimated
from that tree's repeat cells (`REPEAT_CELLS` in the script) when its `judge_response_rejudge_noise.json` is absent or
`--recompute_noise` is given.
