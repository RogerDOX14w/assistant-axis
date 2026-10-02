# M2 pilot readout: metric calibration on the existing corpus

2026-10-01, the M2 agent (Opus), for Roger's pilot decision; updated the same day for round 2 and on 2026-10-02 for rounds 3 and 4 (newest first).  Plan: [15_metric_calibration.md](./15_metric_calibration.md) and [coding_plan_platform.md](./coding_plan_platform.md) §9 tasks 11-18; task 19 (`--write-config`, the final run, the README) waits for the decisions at the end.  Terms of art link to [glossary.md](./glossary.md) on first use in each section.

## Round 4 (2026-10-02)

Why this round: round 3 showed that for the [covered setting](./glossary.md#two-settings) (is a candidate already in the corpus?) the [embedding](./glossary.md#embedding) retrieves well but cannot decide.  A 14-word [paraphrase](./glossary.md#paraphrase-recall) finds its own trait among its 5 [nearest neighbours](./glossary.md#nearest-neighbour) about 99.7% of the time, while a similarity line that catches 95% of paraphrases also catches 37-49% of the recorded antonym pairs ([labelled pairs](./glossary.md#labelled-pairs)).  Roger has agreed in outline an M3 design in which the embedding only retrieves each candidate's nearest existing traits and LLM calls judge them, so [recall@k](./glossary.md#recall-at-k) is now the primary measure for the covered setting.  Round 3 had picked `w14` (a [representation](./glossary.md#representations): descriptions cut to 14 words) with `pw16` ([partial whitening](./glossary.md#partial-whitening) of the top 16 components) on a margin of one or two queries out of 659, without a test; Roger asked for a significantly larger test with real statistics.  Decided before this round (Roger): bge is dropped; [K](./glossary.md#k95) = 10 for the directional setting, provisionally; the contrast clauses stay; [task (b)](./glossary.md#tasks-abc) is left to the LLM.

What was done (code: [calibrate_metric.py](../../data_analysis/gap_generation/calibrate_metric.py) `--round4` and [retrieval.py](../../assistant_axis/gapgen/retrieval.py); results in [retrieval_round4.json](../../data/candidates/calibration/retrieval_round4.json), every table in [retrieval_round4.md](../../data/candidates/calibration/retrieval_round4.md)):

- **Five query sources: 3,098 queries about all 659 traits.**

  | source | queries | what it is |
  |---|---|---|
  | paraphrase (round 3) | 659 | [paraphrases.json](../../data/candidates/calibration/paraphrases.json): Haiku rewords each description, keeping the meaning and sharing as few words as it can (prompt version 2) |
  | plain paraphrase | 659 | [paraphrases_plain.json](../../data/candidates/calibration/paraphrases_plain.json), new: the same disposition in everyday words, "a friend explaining it over coffee" (prompt `plain` version 1) |
  | terse paraphrase | 659 | [paraphrases_terse.json](../../data/candidates/calibration/paraphrases_terse.json), new: the core sense as a dictionary gives it, at most 12 words after "This means" (prompt `terse` version 1; median 13 words in all) |
  | M1 gloss, run 1 | 554 | the [M1 filter's glosses](./glossary.md#m1-gloss) of existing labels, written by Haiku from the bare label ([m1_validation](../../data/candidates/filter/m1_validation/results.jsonl)): 614 labels have one, of which the 554 whose [plain reading](./glossary.md#plain-reading) is the corpus sense ([corpus_comparison_1](../../data/candidates/plain_reading/corpus_comparison_1/results.jsonl), 591 labels `same`) |
  | M1 gloss, run 2 | 567 | the same from the rerun ([m1_validation_r2](../../data/candidates/filter/m1_validation_r2/results.jsonl)): 630 with a gloss, 567 kept |

  The M1 glosses are the realistic M3 query: a definition written by someone else from the word alone, not a rewording of the corpus description.  Both new Haiku sets parsed 659 of 659; in each, 2.4-2.9% of the rewrites reuse a word of the label, mostly one word of a multi-word label ("loss" for [loss-averse](../../data/traits/instructions/loss_averse.json)), as round 3's did.
- **Query and corpus form**: the query is the text alone, without a label, cut to 14 words (round 3's M3 case); the corpus is `label: description` cut to 14 or 20 words ([representations](./glossary.md#representations) `w14`, `w20`).  Two models, OpenAI `text-embedding-3-large` and EmbeddingGemma (a [local model](./glossary.md#local-model)); six spaces, [centred](./glossary.md#centred) and the [partial whitenings](./glossary.md#partial-whitening) `pw8`, `pw12`, `pw16`, `pw24`, `pw32`; [cosine](./glossary.md#cosine).
- **Statistics**: each setting against centred `w14`, scored on the same queries, at recall@1 and recall@5, per model, pooled over the sources: [McNemar's exact test](./glossary.md#mcnemar) (with the discordant counts) and a [paired bootstrap](./glossary.md#paired-bootstrap) 95% interval (2,000 resamples, seed 0) that resamples whole traits, since one trait has up to five queries and McNemar's test treats them as independent.  **A difference is called real when both agree**: McNemar's p after [Holm's adjustment](./glossary.md#holm) over the 24 comparisons is below 0.05, and the bootstrap interval excludes zero.  After the first run I added a second family (each `pwN` inside `w20` against centred `w20`, with its own Holm adjustment), recall@20 and the two models' merged top 10, and reran from the cache.
- **Cost**: $0.526 this round: Haiku $0.522 (66 calls, 90,791 input and 86,167 output tokens), OpenAI $0.005 (the new query texts), EmbeddingGemma free; the estimate was $0.716 against a $10 cap.  $0.895 in all after round 4 ([usage.json](../../data/candidates/calibration/usage.json)).  Run records with the pinned prompt versions and hashes: [run_round4a.json](../../data/candidates/calibration/run_round4a.json) (the paid run; log [run_round4a.log](../../data/candidates/calibration/run_round4a.log)) and [run_round4.json](../../data/candidates/calibration/run_round4.json) (the rerun from the cache, $0; log [run_round4b.log](../../data/candidates/calibration/run_round4b.log)).  Round 3's [run.json](../../data/candidates/calibration/run.json) is left as it was, since the other outputs belong to it.

### Headline

1. **Partial whitening makes no real difference.**  No `pwN` differs from centring at recall@1 or recall@5, for either model, inside `w14` or inside `w20`.  The largest gains (+0.003 to +0.004 at recall@5 for OpenAI) are three or four queries in a thousand and do not survive the adjustment.  Round 3's `pw16` was noise.
2. **`w20` beats `w14`.**  Real for EmbeddingGemma at both k (recall@1 +0.026, recall@5 +0.012).  For OpenAI the direction is the same (+0.008, +0.006), and recall@5 passes before adjustment (p = 0.005; 28 queries against 10; interval +0.001 to +0.011) but not after (Holm p = 0.11): probably real but small, and not confirmed.  This reverses round 3's `w14`, which rested on round 3's paraphrases alone, the one source on which `w14` is ahead (OpenAI recall@1 0.947 against 0.939); on the plain and terse paraphrases and on both M1 sets, `w20` is level or ahead.
3. **The M1 glosses are much harder than the paraphrases**, and they are the numbers to plan with: OpenAI `w20` recall@5 is 0.93-0.94 and recall@10 0.97-0.98 on them, against 0.991-1.000 on the three paraphrase sets.  Most of their misses retrieve a near-synonym first.
4. **One model's longer list beats two models' short lists merged**: OpenAI's own top 10 (recall 0.990 pooled, 0.972-0.978 on the M1 glosses) beats both models' top 5 merged (7.0 traits on average; 0.980 and 0.942-0.951), and both top 10s merged (14.2 traits; 0.993) is no better than OpenAI's own top 20 (0.994).
5. **Recommendation for the covered setting**: OpenAI, `w20`, centred, cosine, k = 10, lists not merged (the last subsection).

### Pooled recall@k, every model × representation × space

All 3,098 queries (two thirds of them paraphrases, so this table flatters the realistic case; per source below):

| model | representation | space | recall@1 | recall@3 | recall@5 | recall@10 | recall@20 |
|---|---|---|---|---|---|---|---|
| OpenAI | `w14` | `centred` | 0.827 | 0.946 | 0.969 | 0.987 | 0.993 |
| OpenAI | `w14` | `pw8` | 0.829 | 0.947 | 0.972 | 0.989 | 0.994 |
| OpenAI | `w14` | `pw12` | 0.827 | 0.949 | 0.973 | 0.989 | 0.995 |
| OpenAI | `w14` | `pw16` | 0.829 | 0.949 | 0.972 | 0.989 | 0.995 |
| OpenAI | `w14` | `pw24` | 0.825 | 0.948 | 0.971 | 0.988 | 0.994 |
| OpenAI | `w14` | `pw32` | 0.825 | 0.947 | 0.970 | 0.988 | 0.993 |
| OpenAI | `w20` | `centred` | 0.835 | 0.957 | 0.975 | 0.990 | 0.994 |
| OpenAI | `w20` | `pw8` | 0.837 | 0.957 | 0.977 | 0.990 | 0.995 |
| OpenAI | `w20` | `pw12` | 0.835 | 0.959 | 0.978 | 0.992 | 0.996 |
| OpenAI | `w20` | `pw16` | 0.836 | 0.960 | 0.978 | 0.991 | 0.996 |
| OpenAI | `w20` | `pw24` | 0.834 | 0.960 | 0.978 | 0.991 | 0.996 |
| OpenAI | `w20` | `pw32` | 0.832 | 0.958 | 0.978 | 0.991 | 0.996 |
| EmbeddingGemma | `w14` | `centred` | 0.779 | 0.900 | 0.934 | 0.959 | 0.978 |
| EmbeddingGemma | `w14` | `pw8` | 0.784 | 0.906 | 0.936 | 0.962 | 0.979 |
| EmbeddingGemma | `w14` | `pw12` | 0.786 | 0.905 | 0.937 | 0.962 | 0.980 |
| EmbeddingGemma | `w14` | `pw16` | 0.783 | 0.906 | 0.936 | 0.961 | 0.979 |
| EmbeddingGemma | `w14` | `pw24` | 0.782 | 0.906 | 0.934 | 0.958 | 0.978 |
| EmbeddingGemma | `w14` | `pw32` | 0.779 | 0.902 | 0.932 | 0.956 | 0.976 |
| EmbeddingGemma | `w20` | `centred` | 0.804 | 0.919 | 0.946 | 0.969 | 0.987 |
| EmbeddingGemma | `w20` | `pw8` | 0.806 | 0.919 | 0.947 | 0.974 | 0.987 |
| EmbeddingGemma | `w20` | `pw12` | 0.808 | 0.917 | 0.948 | 0.975 | 0.986 |
| EmbeddingGemma | `w20` | `pw16` | 0.805 | 0.916 | 0.948 | 0.975 | 0.987 |
| EmbeddingGemma | `w20` | `pw24` | 0.802 | 0.912 | 0.946 | 0.973 | 0.986 |
| EmbeddingGemma | `w20` | `pw32` | 0.799 | 0.912 | 0.942 | 0.971 | 0.984 |

### The paired comparisons against centred `w14`

Pooled over the five sources (3,098 queries); "found only by" are McNemar's discordant counts:

| model | k | setting | its recall | centred `w14` | difference | found only by the setting / only by centred `w14` | McNemar p | Holm p | bootstrap 95% | real |
|---|---|---|---|---|---|---|---|---|---|---|
| OpenAI | 1 | `w14` `pw8` | 0.829 | 0.827 | +0.002 | 23 / 17 | 0.4296 | 1.0000 | -0.002 to +0.006 | no |
| OpenAI | 1 | `w14` `pw12` | 0.827 | 0.827 | +0.001 | 29 / 27 | 0.8939 | 1.0000 | -0.004 to +0.005 | no |
| OpenAI | 1 | `w14` `pw16` | 0.829 | 0.827 | +0.002 | 35 / 29 | 0.5323 | 1.0000 | -0.003 to +0.007 | no |
| OpenAI | 1 | `w14` `pw24` | 0.825 | 0.827 | -0.002 | 42 / 48 | 0.5984 | 1.0000 | -0.009 to +0.005 | no |
| OpenAI | 1 | `w14` `pw32` | 0.825 | 0.827 | -0.001 | 52 / 56 | 0.7730 | 1.0000 | -0.009 to +0.006 | no |
| OpenAI | 1 | `w20` `centred` | 0.835 | 0.827 | +0.008 | 101 / 76 | 0.0709 | 1.0000 | -0.002 to +0.017 | no |
| OpenAI | 5 | `w14` `pw8` | 0.972 | 0.969 | +0.004 | 15 / 4 | 0.0192 | 0.3842 | +0.001 to +0.006 | no |
| OpenAI | 5 | `w14` `pw12` | 0.973 | 0.969 | +0.004 | 19 / 6 | 0.0146 | 0.3073 | +0.001 to +0.008 | no |
| OpenAI | 5 | `w14` `pw16` | 0.972 | 0.969 | +0.003 | 20 / 10 | 0.0987 | 1.0000 | -0.000 to +0.007 | no |
| OpenAI | 5 | `w14` `pw24` | 0.971 | 0.969 | +0.003 | 21 / 13 | 0.2295 | 1.0000 | -0.001 to +0.007 | no |
| OpenAI | 5 | `w14` `pw32` | 0.970 | 0.969 | +0.002 | 21 / 16 | 0.5114 | 1.0000 | -0.002 to +0.006 | no |
| OpenAI | 5 | `w20` `centred` | 0.975 | 0.969 | +0.006 | 28 / 10 | 0.0051 | 0.1121 | +0.001 to +0.011 | no |
| EmbeddingGemma | 1 | `w14` `pw8` | 0.784 | 0.779 | +0.006 | 60 / 42 | 0.0918 | 1.0000 | -0.001 to +0.012 | no |
| EmbeddingGemma | 1 | `w14` `pw12` | 0.786 | 0.779 | +0.007 | 70 / 47 | 0.0415 | 0.7885 | +0.000 to +0.014 | no |
| EmbeddingGemma | 1 | `w14` `pw16` | 0.783 | 0.779 | +0.005 | 84 / 69 | 0.2576 | 1.0000 | -0.003 to +0.012 | no |
| EmbeddingGemma | 1 | `w14` `pw24` | 0.782 | 0.779 | +0.004 | 92 / 81 | 0.4472 | 1.0000 | -0.005 to +0.012 | no |
| EmbeddingGemma | 1 | `w14` `pw32` | 0.779 | 0.779 | +0.000 | 101 / 101 | 1.0000 | 1.0000 | -0.011 to +0.010 | no |
| EmbeddingGemma | 1 | `w20` `centred` | 0.804 | 0.779 | +0.026 | 179 / 99 | <0.0001 | <0.0001 | +0.014 to +0.037 | **yes** |
| EmbeddingGemma | 5 | `w14` `pw8` | 0.936 | 0.934 | +0.002 | 22 / 16 | 0.4177 | 1.0000 | -0.003 to +0.006 | no |
| EmbeddingGemma | 5 | `w14` `pw12` | 0.937 | 0.934 | +0.003 | 28 / 20 | 0.3123 | 1.0000 | -0.003 to +0.008 | no |
| EmbeddingGemma | 5 | `w14` `pw16` | 0.936 | 0.934 | +0.002 | 31 / 25 | 0.5044 | 1.0000 | -0.003 to +0.007 | no |
| EmbeddingGemma | 5 | `w14` `pw24` | 0.934 | 0.934 | +0.000 | 36 / 36 | 1.0000 | 1.0000 | -0.006 to +0.006 | no |
| EmbeddingGemma | 5 | `w14` `pw32` | 0.932 | 0.934 | -0.002 | 35 / 42 | 0.4944 | 1.0000 | -0.009 to +0.004 | no |
| EmbeddingGemma | 5 | `w20` `centred` | 0.946 | 0.934 | +0.012 | 73 / 37 | 0.0008 | 0.0177 | +0.004 to +0.020 | **yes** |

Plainly: **real at p < 0.05: EmbeddingGemma `w20` against `w14`, at recall@1 and at recall@5.  Not real: every partial whitening, for both models, at both k; and OpenAI `w20` against `w14`, at both k.**  Before the adjustment four more pass p < 0.05 (OpenAI `pw8` and `pw12` at recall@5, OpenAI `w20` at recall@5, EmbeddingGemma `pw12` at recall@1), each a gain of 0.4 to 0.7 points; with 24 tests about one such pass is expected by chance alone, and none survives Holm.  Inside `w20` (the second family; table in [retrieval_round4.md](../../data/candidates/calibration/retrieval_round4.md)) no space differs from centred `w20` either: OpenAI's `pw12` to `pw32` at recall@5 have p 0.01-0.04 before adjustment (+0.003 to +0.004; 12 queries against 2 for `pw12`) and 0.26-0.70 after.  If partial whitening helps OpenAI at all, it is by about three queries in a thousand at k = 5, and by nothing that matters at k = 10 (0.992 against 0.990).

### Per source: do the M1 glosses behave like the paraphrases?

Recall per source, centred, `w20` (with `w14` beside it):

| source | queries | OpenAI `w20`: recall@1 / @5 / @10 / @20 | OpenAI `w14`: @1 / @5 / @10 | EmbeddingGemma `w20`: @1 / @5 / @10 / @20 | EmbeddingGemma `w14`: @1 / @5 / @10 |
|---|---|---|---|---|---|
| paraphrase (round 3) | 659 | 0.939 / 0.999 / 1.000 / 1.000 | 0.947 / 0.997 / 1.000 | 0.956 / 0.995 / 0.995 / 1.000 | 0.945 / 0.995 / 0.999 |
| plain paraphrase | 659 | 0.871 / 0.991 / 0.997 / 0.997 | 0.870 / 0.980 / 0.994 | 0.871 / 0.983 / 0.989 / 0.995 | 0.850 / 0.962 / 0.980 |
| terse paraphrase | 659 | 0.936 / 1.000 / 1.000 / 1.000 | 0.906 / 0.991 / 1.000 | 0.932 / 0.991 / 0.995 / 0.999 | 0.880 / 0.977 / 0.986 |
| M1 gloss, run 1 | 554 | 0.691 / 0.931 / 0.978 / 0.987 | 0.680 / 0.930 / 0.969 | 0.607 / 0.870 / 0.915 / 0.971 | 0.583 / 0.857 / 0.906 |
| M1 gloss, run 2 | 567 | 0.693 / 0.940 / 0.972 / 0.984 | 0.688 / 0.935 / 0.967 | 0.596 / 0.868 / 0.935 / 0.967 | 0.575 / 0.857 / 0.908 |
| pooled | 3098 | 0.835 / 0.975 / 0.990 / 0.994 | 0.827 / 0.969 / 0.987 | 0.804 / 0.946 / 0.969 / 0.987 | 0.779 / 0.934 / 0.959 |

No.  A paraphrase is the corpus description reworded and keeps its specifics; an M1 gloss is a definition written from the word alone and lands on the word's general sense.  OpenAI's recall@1 falls from 0.94 on round 3's paraphrases to 0.69 on the glosses, and recall@5 from 0.999 to 0.93-0.94; the plain paraphrases sit between (0.87 at recall@1).  Under OpenAI the two M1 runs are within 0.01 of each other at every k (EmbeddingGemma within 0.02), so the estimate is stable.  Round 3's [paraphrase recall](./glossary.md#paraphrase-recall) (0.944 at k = 1) is therefore an upper bound; for a re-proposed existing trait in M3, expect about 0.69 at k = 1, 0.93-0.94 at k = 5 and 0.97-0.98 at k = 10 (OpenAI, `w20`).

What the misses are (OpenAI, `w20`, centred: 79 queries miss at k = 5, 72 of them M1 glosses, and 30 at k = 10; every miss is listed under `misses` in [retrieval_round4.json](../../data/candidates/calibration/retrieval_round4.json)).  Most put a near-synonym first, which an adjudicator shown the list would take as covering the candidate anyway: [calm](../../data/traits/instructions/calm.json) retrieves [unflappable](../../data/traits/instructions/unflappable.json) and [composed](../../data/traits/instructions/composed.json) first, [thorough](../../data/traits/instructions/thorough.json) [meticulous](../../data/traits/instructions/meticulous.json), [responsible](../../data/traits/instructions/responsible.json) [accountable](../../data/traits/instructions/accountable.json), [humble](../../data/traits/instructions/humble.json) [modest](../../data/traits/instructions/modest.json), [agreeable](../../data/traits/instructions/agreeable.json) [easygoing](../../data/traits/instructions/easygoing.json).  The farthest misses are glosses of another sense, despite the plain-reading filter: the gloss for [straight](../../data/traits/instructions/straight.json) is "saying what one thinks in plain words" (the corpus trait is sexual orientation; first retrieved [forthright](../../data/traits/instructions/forthright.json) and [blunt](../../data/traits/instructions/blunt.json)), for [critical](../../data/traits/instructions/critical.json) "finding fault readily" (the corpus trait questions power structures; first [judgmental](../../data/traits/instructions/judgmental.json) and [harsh](../../data/traits/instructions/harsh.json)), and run 1's [engaged](../../data/traits/instructions/engaged.json) "having made a formal promise to marry" (first [married](../../data/traits/instructions/married.json)).  Those candidates are a different concept from the corpus trait, and treating them as not covered is the right outcome, so recall understates how well the covered decision will go.

### Merging both models' lists

Centred `w20`; the merged list is the union of the two models' top k, so its length varies:

| list | mean length | pooled | M1 gloss, run 1 | M1 gloss, run 2 | paraphrases (three sets) |
|---|---|---|---|---|---|
| OpenAI top 5 | 5 | 0.975 | 0.931 | 0.940 | 0.996 |
| OpenAI top 10 | 10 | 0.990 | 0.978 | 0.972 | 0.999 |
| OpenAI top 20 | 20 | 0.994 | 0.987 | 0.984 | 0.999 |
| EmbeddingGemma top 5 | 5 | 0.946 | 0.870 | 0.868 | 0.990 |
| EmbeddingGemma top 10 | 10 | 0.969 | 0.915 | 0.935 | 0.993 |
| EmbeddingGemma top 20 | 20 | 0.987 | 0.971 | 0.967 | 0.998 |
| both models' top 3 merged | 4.1 | 0.968 | 0.913 | 0.921 | 0.996 |
| both models' top 5 merged | 7.0 | 0.980 | 0.942 | 0.951 | 0.999 |
| both models' top 10 merged | 14.2 | 0.993 | 0.984 | 0.979 | 1.000 |

Paired, pooled: both top 5s merged against OpenAI's top 10, 4 queries found only by the merge and 37 only by OpenAI's ten (p < 0.0001); both top 10s merged against OpenAI's top 10, 8 against 0 (p = 0.008); both top 10s merged against OpenAI's top 20, 3 against 7 (p = 0.34, no difference).  Adding EmbeddingGemma's list buys what lengthening OpenAI's own list buys, at a somewhat shorter list (14 against 20 traits) but with a second model in the path.  EmbeddingGemma alone is clearly the weaker retriever on the realistic query (recall@10 0.915-0.935 against 0.972-0.978).

### The old threshold design on the same queries

On all 3,098 queries, [`t_hi`](./glossary.md#thresholds) at 95% recall (OpenAI `w20` centred: 0.326) has 61% of the recorded antonym pairs above it, and 81% of the queries have some other trait above it (EmbeddingGemma 49% and 93%), against round 3's 37-49% and 44-72% on its paraphrases alone: the harder queries pull `t_hi` down, and a threshold would send nearly every candidate to adjudication anyway.  The retrieval design loses nothing by dropping it.

### Recommendation for the covered setting (retrieval design)

- **Representation `w20`** (descriptions cut to 20 words, the query to 14).  It is level with or ahead of `w14` for both models on every source, except round 3's paraphrases under OpenAI at k = 1 (0.939 against 0.947), and really ahead for EmbeddingGemma.  It is also the directional setting's representation, so M3 embeds the corpus once.
- **Space: centred** on the fixed corpus mean, as in the directional setting.  No partial whitening has a detectable effect at this sample size; centring is the simpler of equals.
- **Model: OpenAI `text-embedding-3-large`**: ahead of EmbeddingGemma by 4-6 points at k = 10 on the M1 glosses.
- **k = 10**: the adjudicator sees the ten nearest existing traits.  Recall 0.990 pooled and 0.972-0.978 on the M1 glosses, and most of what remains is a near-synonym or another sense.  k = 20 lifts the M1 figure to 0.984-0.987; worth it only if the adjudication prompt judges twenty definitions as well as ten.
- **Do not merge the two models' lists**: merging both top 10s matches OpenAI's own top 20 and no more, for a second model in the path.
- Under this design the covered block's `t_hi` and `t_lo` stop being the decision; the block would carry k instead.  That belongs to the M3 design, which is still open, and to task 19's config, which waits.

## Round 3 (2026-10-02)

Roger's decision on round 2: [tasks (a) and (c)](./glossary.md#tasks-abc) serve two different uses of the embedding in M3 and are tuned separately; task (b), telling a near-duplicate from an antonym, is left to the LLM adjudicator ("trivially easy by LLM inspection") and is reported, not used to choose.  What was done, with no blinded judge:

- **[Criterion (g)](./glossary.md#contrast-criteria) ran**: Haiku paraphrased all 659 descriptions ([paraphrases.json](../../data/candidates/calibration/paraphrases.json); prompt version 2, a short reason before each rewrite, 659 of 659 parsed; $0.321).  The calibration was rerun with them ([paraphrase_metrics.json](../../data/candidates/calibration/paraphrase_metrics.json)), which fills (g), [held-out recovery](./glossary.md#heldout-recovery) (i), [paraphrase recall](./glossary.md#paraphrase-recall) and a covered threshold from paraphrase-level duplicates, which the duplicate rulings could not supply ([QUESTIONS.md](./QUESTIONS.md) 26).
- **Criterion (e) will not run**: Roger marked the 30 comparisons himself (below), and that settled the contrast question.
- **Two settings, chosen separately** (the "covered" and "directional" blocks of the config, [metric_config.py](../../assistant_axis/gapgen/metric_config.py)); the proposed config is in [summary.json](../../data/candidates/calibration/summary.json) under `proposed_metric_config`.  [metric_config.json](../../data/candidates/metric_config.json) is not written yet (task 19).
- **Cost**: $0.350 this round ($0.321 Haiku, $0.029 OpenAI for embedding the paraphrases); **$0.368 in all** ([usage.json](../../data/candidates/calibration/usage.json)).

### The paraphrases, and how a candidate will look in M3

Three query forms were tried against the corpus: the whole paraphrase with the trait's own label (trivial: the label alone finds the trait, recall 0.99-1.00 everywhere), the whole paraphrase without a label, and the paraphrase cut to 14 words without a label.  The last is the M3 case: a candidate arrives as a 14-word [M1 gloss](./glossary.md#m1-gloss) under its own, different label.  [Paraphrase recall@1](./glossary.md#paraphrase-recall) (the trait is the nearest corpus entry to its own paraphrase), cosine, partial whitening `pw16` (the covered setting's space; `centred` differs by at most 0.013):

| model | corpus representation | whole paraphrase, with the trait's label | whole paraphrase, no label | paraphrase cut to 14 words, no label (the M3 case) |
|---|---|---|---|---|
| openai | full | 1.000 | 0.967 | 0.929 |
| openai | noprefix | 1.000 | 0.980 | 0.932 |
| openai | w20 | 1.000 | 0.962 | 0.939 |
| openai | w14 | 1.000 | 0.944 | 0.944 |
| openai | dup | 1.000 | 0.967 | 0.929 |
| openai | strip | 1.000 | 0.968 | 0.930 |
| bge | full | 1.000 | 0.933 | 0.829 |
| bge | noprefix | 1.000 | 0.936 | 0.818 |
| bge | w20 | 0.999 | 0.921 | 0.873 |
| bge | w14 | 0.997 | 0.889 | 0.889 |
| bge | dup | 0.999 | 0.927 | 0.829 |
| bge | strip | 1.000 | 0.933 | 0.824 |
| gemma | full | 1.000 | 0.992 | 0.941 |
| gemma | noprefix | 1.000 | 0.995 | 0.936 |
| gemma | w20 | 1.000 | 0.985 | 0.955 |
| gemma | w14 | 0.997 | 0.950 | 0.950 |
| gemma | dup | 1.000 | 0.994 | 0.941 |
| gemma | strip | 1.000 | 0.989 | 0.942 |

(In the `w14` rows the paraphrase is cut to 14 words in every column, so the last two columns coincide.)  With the label, every representation is perfect and says nothing.  Without it, the whole paraphrase is found best against whole descriptions (`noprefix`, `full`), but a 14-word query is found best against descriptions cut to the same scope (`w14`, `w20`): OpenAI 0.944 against 0.929, bge 0.889 against 0.829, EmbeddingGemma 0.950 against 0.941.  That confirms round 2's gloss-length result on paraphrases rather than on Roger's weak duplicate labels: scope-match the corpus to the gloss.  No representation reaches the plan's 0.95 target for the M3 query form on all three models; OpenAI and EmbeddingGemma come within 0.01, bge does not.

### The covered threshold, from paraphrases

[`t_hi`](./glossary.md#thresholds) is now set at 95% recall of (trait, own 14-word paraphrase) pairs, in the covered setting (`w14`, `pw16`, cosine), and it clears `t_lo` for every model:

| model | t_hi | t_lo | recall at t_hi (held out by fold) | antonyms above t_hi | near-distinct above t_hi | random pairs above t_hi | hidden original, paraphrase still covered | corpus traits whose nearest neighbour is above t_hi |
|---|---|---|---|---|---|---|---|---|
| openai | 0.354 | 0.181 | 0.951 (0.950) | 0.49 | 0.18 | 0.0010 | 0.50 | 488 |
| bge | 0.315 | 0.223 | 0.951 (0.951) | 0.49 | 0.24 | 0.0015 | 0.72 | 583 |
| gemma | 0.409 | 0.241 | 0.951 (0.953) | 0.37 | 0.09 | 0.0010 | 0.44 | 416 |

The held-out column sets `t_hi` on four of the five folds of the [labelled pairs](./glossary.md#labelled-pairs) (groups that never split a pair) and measures recall on the fifth: it holds.  The price of 95% recall is in the last three columns.  Between 37% and 49% of recorded antonym pairs sit above `t_hi` (the antonym confusion the adjudicator must absorb; this is task (b) in operational form), and when a trait is hidden from the corpus its paraphrase is still above `t_hi` against some other trait 44% (EmbeddingGemma) to 72% (bge) of the time: a genuinely new candidate near an existing one will usually be sent for adjudication rather than passed as new.  Random pairs almost never cross it (0.1%).  So the covered line, as calibrated, is a "send to the adjudicator" line, not a verdict; the "new" side below `t_lo` is the only decision the embedding makes alone.

### Criteria (g) and (i) for the contrast clauses

| criterion | openai | bge | gemma |
|---|---|---|---|
| (g) mean distance full → paraphrase / full → stripped (110 traits) | 0.166 / 0.033 | 0.222 / 0.057 | 0.183 / 0.050 |
| (g) share where stripping moves the vector more than paraphrasing | 0.00 | 0.00 | 0.01 |
| (i) paraphrase recall@1, clauses kept → stripped | 1.000 → 1.000 | 1.000 → 0.999 | 1.000 → 1.000 |

(`centred`, representation `full`.)  Rewording a description moves its vector about four to five times as far as removing its clause does, and in 99-100% of the 110 traits stripping moves it less than paraphrasing: the clause effect is within paraphrase noise.  (i) with the trait's own label is saturated (1.000) and decides nothing.

**Roger's marks (the human half of criterion e).**  Decoded against the key ([contrast_marks_roger.json](../../data/candidates/calibration/contrast_marks_roger.json); sheet [contrast_comparisons_for_marks.md](./contrast_comparisons_for_marks.md)): clause kept preferred 13, clause stripped 16, same 1.  By [class](./glossary.md#contrast-classes): N 3 kept / 2 stripped, P 10 / 14, S 1 same.  Sixteen of 29 decided comparisons is a coin flip (a sign test, the chance of a split at least this uneven if he had no preference, gives p = 0.71).  With (g), the ablation of round 1 and this, the clause has no dramatic effect either way, and **the clauses stay in the embedded text** (plan 15's rule: keep when the criteria are no worse with them).  The Sonnet judge (e) is not run: $0.59 to confirm a coin flip is not worth it.  Under the covered setting's `w14` representation the question mostly disappears anyway: the clause sits at the end of a description, and in 93 of the 110 descriptions that have one it falls after the first 14 words, outside the embedded text.

### The two settings

| | covered: is the candidate already here? | directional: does it add a direction? |
|---|---|---|
| chosen on | task (a) and [paraphrase recall](./glossary.md#paraphrase-recall) for the M3 query form (target 0.95); task (b) reported, not used | task (c), a proxy |
| representation | `w14` (descriptions cut to a gloss's 14 words) | `w20` |
| space | [partial whitening](./glossary.md#partial-whitening) `pw16` on the fixed corpus mean | [centred](./glossary.md#centred) on the fixed corpus mean |
| measure | cosine to the nearest existing trait | [residual fraction](./glossary.md#residual) outside the top K = 10 directions |
| numbers | recall@1 0.944 / 0.889 / 0.950 (OpenAI / bge / EmbeddingGemma); task (a) 0.64 / 0.57 / 0.64; task (b) 0.43 / 0.40 / 0.48 | task (c) Spearman 0.30 / 0.27 / 0.29; K = 10 / 20 / 40 / K_95 mean 0.29 / 0.24 / 0.23 / 0.14 |
| thresholds | `t_hi` 0.354 / 0.315 / 0.409, `t_lo` 0.181 / 0.223 / 0.241 | none (a ranking score) |
| contrast clauses | kept (mostly outside the 14 words) | kept |

How each was chosen ([calibrate.py](../../assistant_axis/gapgen/calibrate.py) `choose_settings`; the `strip` representation is excluded because the clauses stay):

- **Covered**: no candidate meets 0.95 mean recall for the M3 query form, so those within 0.01 of the best mean recall (0.928) qualify; among them, those within 0.03 of the best task (a) (differences under that are noise with 82 against 34 labelled pairs); of those, the best recall.  That gives `w14` `pw16` (mean recall 0.928, task (a) 0.618).  `w14` with `centred` or `raw` is within noise of it on every number (recall 0.923-0.925, task (a) 0.61-0.64), so the choice of space inside `w14` matters little; what matters is `w14`.  Whole-description representations lose 0.06-0.07 of recall for bge and about 0.01-0.015 for the others.
- **Directional**: the best mean task (c) over (representation, space, K) is `w20` `centred` at K = 10 (0.286).  The K sensitivity, and criterion (i) as the stability of the residual under rewording with the original hidden ([Spearman](./glossary.md#spearman) between a paraphrase's held-out residual and the original's [leave-one-out](./glossary.md#loo) residual), per model, task (c) / (i):

| model | K=10 | K=20 | K=40 | K_95 (K) |
|---|---|---|---|---|
| openai | 0.30 / 0.64 | 0.26 / 0.63 | 0.27 / 0.63 | 0.21 / 0.32 (376) |
| bge | 0.27 / 0.53 | 0.27 / 0.60 | 0.20 / 0.58 | 0.08 / 0.41 (240) |
| gemma | 0.29 / 0.72 | 0.19 / 0.71 | 0.21 / 0.68 | 0.15 / 0.54 (250) |

  Small K beats [K_95](./glossary.md#k95) on both counts: the residual at K_95 tracks persona space less (0.08-0.21) and survives rewording less (0.32-0.54).  Among 10, 20 and 40, K = 10 is best or tied on task (c) for every model (by up to 0.10 for EmbeddingGemma), while (i) is level across them (within 0.07 per model); K = 10 is the provisional choice, not a settled one.  The caveat stands: task (c) is a proxy (the correlation with the persona-space residual of existing traits), and (i) here measures whether the score is about the concept rather than the wording, not whether it finds missing traits; nothing yet tests the latter directly.


## Round 2 (2026-10-01)

What was added, at Roger's request, with no LLM calls:

- **[Partial whitening](./glossary.md#partial-whitening)** `pw1`, `pw2`, `pw4`, `pw8`, `pw16`, `pw32`, `pw64`: after [centring](./glossary.md#centred), each of the top N [principal components](./glossary.md#pcs) is shrunk to the standard deviation of the (N+1)th and the rest are left alone.  Every task was run on them as on the other five space variants (216 views in all: 3 models, 6 [representations](./glossary.md#representations), 12 variants).
- **The doubled gloss** (`dup`, Roger's note on the first readout: "experiment with doubling the gloss rather than truncating the description"): the short side, an [M1 filter gloss](./glossary.md#m1-gloss), is embedded as "label: gloss gloss"; the corpus descriptions are embedded as written, unchanged, because the question is whether the short side can be brought up to the descriptions' length rather than the descriptions cut down.
- **The [blinded comparisons](./glossary.md#blinded-comparisons) were redrawn** (criterion (e) below): the first draw counted any difference in the five neighbours as a difference, so many of Roger's 30 were the same five traits reordered.
- **The K question is stated plainly** (decision 2).

What changed in the results and recommendations:

- **Partial whitening does not help.**  `pw1` and `pw2` behave like plain centring; from `pw8` up they move toward [ZCA](./glossary.md#zca): duplicate-vs-distinct [AUC](./glossary.md#auc) (task a) rises a little, while duplicate-vs-antonym (task b), the [persona-space](./glossary.md#persona-space) correlation (task c) and the pairwise agreement with persona space ([criterion h](./glossary.md#contrast-criteria), 0.52 → 0.39 at `pw16` for OpenAI) fall.  No `pw` variant improves on centring overall.
- **Doubling the gloss does not help either**: tasks (a) and (b) are unchanged or slightly worse than `full`, while cutting the descriptions to 14 words (`w14`) still helps.  So what helps is matching the *content scope* of the two sides, not their length.
- **Provisional variant**: with 24 variant-and-metric candidates the composite ranking now puts `centred` cosine first (mean rank 7.7; `raw` cosine and CSLS 8.0); it was `raw` cosine in round 1, within noise of `centred`.  The drop-or-merge table below is now drawn in the `centred` space (16 pairs instead of 12).  The recommendation (`centred`, cosine) is unchanged.
- **Cost**: $0.0036 more (the doubled glosses; estimated, see [usage_notes.md](../../data/candidates/calibration/usage_notes.md)); $0.0189 in all.

Roger's answers so far are recorded under the decisions at the end.

## Headline

- **Run**: [calibrate_metric.py](../../data_analysis/gap_generation/calibrate_metric.py) `--skip-llm`, three models (OpenAI `text-embedding-3-large`; [local](./glossary.md#local-model) `BAAI/bge-large-en-v1.5` with [CLS pooling](./glossary.md#cls-pooling); local `google/embeddinggemma-300m` through sentence-transformers with its "sentence similarity" prompt on both sides), six representations (`full`, `noprefix`, `w20`, `w14`, `strip`, `dup`), twelve space variants (`raw`, `centred` on the fixed corpus mean, `centred_pc1`, `centred_pc3`, regularised `zca`, `pw1`-`pw64`), 659 trait files (the corpus directory's 661 entries include two `.md` files).
- **Cost**: $0.368 in all after round 3, $0.895 after round 4 ([usage.json](../../data/candidates/calibration/usage.json), cumulative over runs; round 4's share is in its section).  After round 3: Claude Haiku 4.5 $0.321 (46,896 input and 54,802 output tokens in 34 calls, the paraphrases); OpenAI $0.048 (365,914 tokens in 48 calls, of which 27,512 tokens in 3 calls are an estimate for a stopped round-2 run, [usage_notes.md](../../data/candidates/calibration/usage_notes.md)); the local models at zero cost.  Rounds 1 and 2 alone came to $0.0189.  The first run's spend line is in [run1.log](../../data/candidates/calibration/run1.log).
- **Compute**: embeddings 30-40 s per model on [MPS](./glossary.md#mps); the round-2 run took 39 minutes, almost all of it the [leave-one-out](./glossary.md#loo) [residual](./glossary.md#residual) (one 658x658 eigendecomposition per trait per centred or partially whitened view) ([run.json](../../data/candidates/calibration/run.json)).
- **Inputs built for this**: [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json) (284 antonym, 79 duplicate, 3 deliberate duplicate, 34 near-distinct, 5 polysemy rejects, 2,000 random; hand-checked in [labelled_pairs_curation.json](../../data/candidates/calibration/labelled_pairs_curation.json), 126 mechanical rows excluded with reasons; see [labelled pairs](./glossary.md#labelled-pairs)), [contrast_cuts.json](../../data/candidates/calibration/contrast_cuts.json) (106 of the census's 107 still in the corpus, 7 hand overrides in [contrast_cut_overrides.json](../../data/candidates/calibration/contrast_cut_overrides.json)), persona yields recomputed (below).
- **The three findings that matter for M3**:
  1. **[Cosine](./glossary.md#cosine) cannot draw the covered line by itself.**  Roger's recorded duplicate rulings (seed-queue decisions, the pairing review) sit no closer than distinct neighbours ([task a](./glossary.md#tasks-abc), AUC 0.42-0.74) and *farther* than the recorded antonyms (task b, AUC 0.28-0.56 in the `full` representation, below 0.5 in all but a few cells).  At 95% recall of those duplicates, [`t_hi`](./glossary.md#thresholds) falls below `t_lo`, the 99th percentile of random pairs, for every model and variant, partial whitening included.  The rulings are "area covered by" judgements, not paraphrases; the covered decision in M3 needs the adjudicator and a paraphrase-level calibration set ([criterion g](./glossary.md#contrast-criteria)).
  2. **Gloss length**: cutting the corpus side to the glosses' 14 words (`w14`) helps duplicate detection (tasks a and b rise for every model, most for bge: 0.44 → 0.57 and 0.41 → 0.52, raw) and costs a little self-recovery ([gloss recall@1](./glossary.md#gloss-recall) 0.979 → 0.971 OpenAI, 0.924 → 0.892 bge).  Doubling the gloss instead (`dup`, round 2) does not help.
  3. **Persona agreement is real but moderate**: pairwise text cosine against pairwise persona cosine (293 traits with vectors, 42,778 pairs) [Spearman](./glossary.md#spearman) 0.50-0.55 in `raw`/`centred` for all three models, 0.16-0.18 in `zca`, 0.37-0.41 at `pw16`; local novelty (1 - [nearest-neighbour](./glossary.md#nearest-neighbour) cosine) against the persona yield 0.24-0.35.

## Persona yields (task c's target)

The May 2026 per-trait [residual fractions](./glossary.md#residual) survive only as the 24 bracketed values in [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) § "Strategy 1", computed against the top 20 [principal components](./glossary.md#pcs) of the 60 clean-pair axis directions, a basis that was not saved.  So the yield was **recomputed** as plan 12 step 1 describes: the 8-slot set ([qwen-3-32b Roger 8slot](<../../runpod_workspace/qwen/qwen-3-32b Roger 8slot/MANIFEST.json>)), slot 6, layer 25, 302 traits and 280 roles, centred on the traits+roles mean, [soft shear](./glossary.md#soft-shear) L=3 (the goal / no-goal subspaces built on this data), and each trait's [leave-one-out](./glossary.md#loo) residual outside the top-K PCs of the other 581 entities.  293 of the 302 trait vectors match a current trait file (the other nine have no current file: renamed or deleted stems).  The pool's [K_95](./glossary.md#k95) is 170, not plan 12's 37.  Cross-check: Spearman between the 24 bracketed values and the recomputed yield is 0.53 / 0.40 / 0.52 / 0.54 at K = 10 / 20 / 37 / 40.  Task (c) uses K = 37.

## Leave-one-out table: representation `full`, every model x variant

(a) [AUC](./glossary.md#auc), labelled duplicates over near-distinct neighbours (82 against 34); (b) AUC, duplicates over recorded antonyms (82 against 284; 0.5 = conflated, below 0.5 = antonyms closer); (c) [Spearman](./glossary.md#spearman) of the novelty score with the persona yield (n = 293): local `cos` = 1 - NN cosine, [`CSLS`](./glossary.md#csls) = minus NN CSLS, `resid` = [leave-one-out](./glossary.md#loo) [residual](./glossary.md#residual) outside the top-K PCs of the other traits (centred and partially whitened variants only; [K_95](./glossary.md#k95) in brackets); gloss r@1: [gloss recall@1](./glossary.md#gloss-recall) (630 traits).  Every representation (216 rows) is in [loo_table.md](../../data/candidates/calibration/loo_table.md); all rows with sample sizes, p values and the K = 10/40 sensitivities in [loo_metrics.json](../../data/candidates/calibration/loo_metrics.json).


**openai**

| representation | variant | (a) cos | (a) CSLS | (b) cos | (b) CSLS | (c) cos | (c) CSLS | (c) resid K=20 | (c) resid K95 (K) | gloss r@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| full | raw | 0.60 | 0.62 | 0.41 | 0.39 | 0.24 | 0.16 | – | – (–) | 0.979 |
| full | centred | 0.57 | 0.61 | 0.40 | 0.39 | 0.24 | 0.14 | 0.26 | 0.20 (366) | 0.979 |
| full | centred_pc1 | 0.59 | 0.63 | 0.40 | 0.39 | 0.24 | 0.15 | 0.24 | 0.19 (370) | 0.979 |
| full | centred_pc3 | 0.66 | 0.65 | 0.40 | 0.40 | 0.20 | 0.15 | 0.13 | 0.13 (376) | 0.984 |
| full | zca | 0.74 | 0.68 | 0.37 | 0.32 | 0.11 | 0.09 | – | – (–) | 0.994 |
| full | pw1 | 0.58 | 0.62 | 0.40 | 0.39 | 0.24 | 0.14 | 0.25 | 0.20 (367) | 0.979 |
| full | pw2 | 0.58 | 0.62 | 0.40 | 0.39 | 0.24 | 0.14 | 0.25 | 0.20 (368) | 0.979 |
| full | pw4 | 0.59 | 0.62 | 0.40 | 0.39 | 0.24 | 0.15 | 0.24 | 0.19 (369) | 0.983 |
| full | pw8 | 0.62 | 0.64 | 0.39 | 0.38 | 0.22 | 0.14 | 0.21 | 0.17 (375) | 0.983 |
| full | pw16 | 0.64 | 0.65 | 0.37 | 0.36 | 0.20 | 0.13 | 0.18 | 0.15 (385) | 0.984 |
| full | pw32 | 0.66 | 0.65 | 0.35 | 0.34 | 0.17 | 0.12 | 0.17 | 0.15 (400) | 0.986 |
| full | pw64 | 0.68 | 0.66 | 0.34 | 0.32 | 0.14 | 0.10 | 0.15 | 0.13 (425) | 0.989 |

**bge**

| representation | variant | (a) cos | (a) CSLS | (b) cos | (b) CSLS | (c) cos | (c) CSLS | (c) resid K=20 | (c) resid K95 (K) | gloss r@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| full | raw | 0.44 | 0.53 | 0.41 | 0.41 | 0.26 | 0.22 | – | – (–) | 0.924 |
| full | centred | 0.46 | 0.54 | 0.41 | 0.41 | 0.29 | 0.22 | 0.22 | 0.07 (238) | 0.922 |
| full | centred_pc1 | 0.43 | 0.52 | 0.37 | 0.37 | 0.28 | 0.20 | 0.20 | 0.05 (242) | 0.929 |
| full | centred_pc3 | 0.42 | 0.50 | 0.34 | 0.34 | 0.24 | 0.20 | 0.10 | -0.01 (248) | 0.936 |
| full | zca | 0.56 | 0.53 | 0.31 | 0.28 | 0.09 | 0.08 | – | – (–) | 0.965 |
| full | pw1 | 0.45 | 0.53 | 0.41 | 0.40 | 0.30 | 0.22 | 0.22 | 0.06 (239) | 0.924 |
| full | pw2 | 0.45 | 0.53 | 0.40 | 0.40 | 0.30 | 0.22 | 0.22 | 0.06 (240) | 0.927 |
| full | pw4 | 0.44 | 0.53 | 0.39 | 0.39 | 0.29 | 0.22 | 0.21 | 0.05 (242) | 0.930 |
| full | pw8 | 0.47 | 0.54 | 0.35 | 0.36 | 0.27 | 0.21 | 0.17 | 0.02 (248) | 0.940 |
| full | pw16 | 0.50 | 0.54 | 0.32 | 0.33 | 0.24 | 0.20 | 0.16 | -0.01 (257) | 0.952 |
| full | pw32 | 0.52 | 0.54 | 0.30 | 0.30 | 0.20 | 0.17 | 0.22 | -0.03 (271) | 0.959 |
| full | pw64 | 0.54 | 0.53 | 0.29 | 0.28 | 0.16 | 0.13 | 0.20 | -0.05 (296) | 0.959 |

**gemma**

| representation | variant | (a) cos | (a) CSLS | (b) cos | (b) CSLS | (c) cos | (c) CSLS | (c) resid K=20 | (c) resid K95 (K) | gloss r@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| full | raw | 0.69 | 0.68 | 0.56 | 0.52 | 0.26 | 0.21 | – | – (–) | 0.890 |
| full | centred | 0.63 | 0.66 | 0.55 | 0.52 | 0.28 | 0.20 | 0.16 | 0.10 (249) | 0.889 |
| full | centred_pc1 | 0.61 | 0.64 | 0.47 | 0.45 | 0.25 | 0.19 | 0.14 | 0.07 (252) | 0.890 |
| full | centred_pc3 | 0.61 | 0.64 | 0.39 | 0.38 | 0.21 | 0.17 | 0.09 | 0.04 (258) | 0.902 |
| full | zca | 0.67 | 0.64 | 0.37 | 0.34 | 0.10 | 0.09 | – | – (–) | 0.938 |
| full | pw1 | 0.63 | 0.66 | 0.54 | 0.51 | 0.28 | 0.19 | 0.15 | 0.10 (249) | 0.892 |
| full | pw2 | 0.63 | 0.66 | 0.53 | 0.50 | 0.27 | 0.19 | 0.15 | 0.09 (250) | 0.894 |
| full | pw4 | 0.62 | 0.66 | 0.50 | 0.48 | 0.26 | 0.19 | 0.13 | 0.08 (252) | 0.897 |
| full | pw8 | 0.62 | 0.66 | 0.45 | 0.44 | 0.24 | 0.18 | 0.09 | 0.05 (259) | 0.905 |
| full | pw16 | 0.63 | 0.66 | 0.41 | 0.40 | 0.22 | 0.17 | 0.07 | 0.03 (268) | 0.908 |
| full | pw32 | 0.64 | 0.65 | 0.38 | 0.37 | 0.19 | 0.14 | 0.13 | 0.01 (284) | 0.908 |
| full | pw64 | 0.64 | 0.64 | 0.36 | 0.34 | 0.13 | 0.10 | 0.15 | 0.00 (308) | 0.917 |


Reading the table: no cell reaches the plan's target `auc_dup_vs_distinct >= 0.85` (a target, not a gate: review amendment 2); the best are OpenAI [`zca`](./glossary.md#zca) (0.74) and EmbeddingGemma `raw` (0.69; 0.71-0.72 with `w20`/`w14`, in [loo_table.md](../../data/candidates/calibration/loo_table.md)).  `zca` buys (a) and gloss recall at the price of (b), and halves (c).  [Partial whitening](./glossary.md#partial-whitening) traces the path between the two: `pw1` and `pw2` are centring to within 0.02 on every task, by `pw4` (b) starts to fall (EmbeddingGemma 0.55 → 0.50), and from `pw8` up, (a) and gloss recall rise toward `zca` while (b) and (c) fall toward it.  [CSLS](./glossary.md#csls) lifts (a) for bge (whose raw space has [hubs](./glossary.md#hubness)) and does little elsewhere; it lowers (c) everywhere.  Ranked by mean rank over tasks (a), (b), (c) of the cross-model means, the top is `centred` cosine 7.7, `raw` CSLS 8.0, `raw` cosine 8.0, `pw1` cosine 9.0, `pw2` cosine 9.3; `zca` and `pw64` come 17th-24th ([summary.json](../../data/candidates/calibration/summary.json) `provisional.ranking`).

## Nearest-neighbour distributions and thresholds

[nn_hist_openai.png](../../data/candidates/calibration/nn_hist_openai.png), [nn_hist_bge.png](../../data/candidates/calibration/nn_hist_bge.png), [nn_hist_gemma.png](../../data/candidates/calibration/nn_hist_gemma.png): one panel per variant (now twelve, four to a row), the [leave-one-out](./glossary.md#loo) [nearest-neighbour](./glossary.md#nearest-neighbour) cosine (filled), the same with recorded arrangement partners excluded (outline), the [labelled pairs](./glossary.md#labelled-pairs) as rugs under the axis, and three lines: [`t_hi`](./glossary.md#thresholds) (95% duplicate recall), `t_lo` (99% of random pairs) and the [upper fence](./glossary.md#thresholds) of the partner-excluded bulk.  The bulk is unimodal in every panel; the right shoulder of the plain histogram is mostly recorded clean pairs, whose descriptions mirror each other, and shrinks once partners are excluded.

Threshold placement in the provisional variant (`centred`, cosine; all variants in [thresholds.json](../../data/candidates/calibration/thresholds.json); [quartiles and IQR](./glossary.md#iqr)):

| model | representation | NN median (Q1-Q3) | upper fence | t_hi (all dup) | t_hi (certain) | t_lo | t_hi > t_lo | NN >= dup median | above fence |
|---|---|---|---|---|---|---|---|---|---|
| openai | full | 0.478 (0.400-0.561) | 0.802 | 0.165 | 0.214 | 0.249 | False | 615 | 0 |
| openai | w14 | 0.452 (0.393-0.529) | 0.733 | 0.143 | 0.190 | 0.232 | False | 620 | 8 |
| bge | full | 0.481 (0.418-0.561) | 0.777 | 0.116 | 0.155 | 0.295 | False | 648 | 8 |
| bge | w14 | 0.460 (0.400-0.531) | 0.727 | 0.085 | 0.085 | 0.273 | False | 654 | 14 |
| gemma | full | 0.496 (0.436-0.578) | 0.790 | 0.145 | 0.212 | 0.310 | False | 617 | 2 |
| gemma | w14 | 0.478 (0.421-0.556) | 0.759 | 0.105 | 0.129 | 0.317 | False | 583 | 0 |


[`t_hi`](./glossary.md#thresholds) lies below `t_lo` everywhere (every model, representation and variant, the twelve included), so the duplicate rulings cannot set the covered threshold (finding 1; [QUESTIONS.md](./QUESTIONS.md) 26): 583-654 of the 659 traits have a nearest neighbour closer than the *median* labelled duplicate.  The low tail is therefore taken as plan 15 step 7 describes it, where a tail separates from the bulk: traits beyond the [upper fence](./glossary.md#thresholds) of the NN distribution.  With partners included the fence catches 0-14 traits per model, all recorded pairs or sets; with partners excluded, 16 (OpenAI), 21 (bge) and 9 (EmbeddingGemma) traits, 16 distinct pairs in all.

## Hubness census

k = 10 occurrence ([hubness.json](../../data/candidates/calibration/hubness.json), every representation): [hubs](./glossary.md#hubness) are traits in 30 or more others' 10-NN lists.  Only the raw bge and EmbeddingGemma spaces have any (3 each); [centring](./glossary.md#centred) removes them and [CSLS](./glossary.md#csls) removes them too.  Skew of the 10-occurrence counts falls from 0.73-0.89 (raw) to 0.41-0.65 (centred), and further with [partial whitening](./glossary.md#partial-whitening) (0.20-0.31 at `pw16`-`pw32`).  Hubness is not a problem in any centred space; CSLS is not needed for it.

| model | variant | cos: skew N10 / max N10 / hubs (N10>=30) | top hubs (cos) | CSLS: skew / max / hubs | top hubs (CSLS) |
|---|---|---|---|---|---|
| openai | raw | 0.73 / 29 / 0 | [temperate](../../data/traits/instructions/temperate.json) 29, [aggressive](../../data/traits/instructions/aggressive.json) 28, [philosophical](../../data/traits/instructions/philosophical.json) 27, [benevolent](../../data/traits/instructions/benevolent.json) 26 | 0.40 / 22 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 22, [philosophical](../../data/traits/instructions/philosophical.json) 21, [homebody](../../data/traits/instructions/homebody.json) 20, [educational](../../data/traits/instructions/educational.json) 20 |
| openai | centred | 0.41 / 23 / 0 | [homebody](../../data/traits/instructions/homebody.json) 23, [honest](../../data/traits/instructions/honest.json) 22, [benevolent](../../data/traits/instructions/benevolent.json) 22, [contrarian](../../data/traits/instructions/contrarian.json) 21 | 0.39 / 21 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 21, [homebody](../../data/traits/instructions/homebody.json) 20, [educational](../../data/traits/instructions/educational.json) 19, [self-pitying](../../data/traits/instructions/self_pitying.json) 18 |
| openai | centred_pc1 | 0.41 / 22 / 0 | [plain-spoken](../../data/traits/instructions/plain_spoken.json) 22, [honest](../../data/traits/instructions/honest.json) 21, [flat](../../data/traits/instructions/flat.json) 21, [competitive](../../data/traits/instructions/competitive.json) 20 | 0.36 / 21 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 21, [homebody](../../data/traits/instructions/homebody.json) 18, [elderly](../../data/traits/instructions/elderly.json) 17, [exclusivist](../../data/traits/instructions/exclusivist.json) 17 |
| openai | centred_pc3 | 0.60 / 25 / 0 | [honest](../../data/traits/instructions/honest.json) 25, [staid](../../data/traits/instructions/staid.json) 25, [uncaring](../../data/traits/instructions/uncaring.json) 23, [malicious](../../data/traits/instructions/malicious.json) 22 | 0.33 / 19 / 0 | [avoidant](../../data/traits/instructions/avoidant.json) 19, [materialist](../../data/traits/instructions/materialist.json) 19, [open-minded](../../data/traits/instructions/open_minded.json) 19, [obsessive](../../data/traits/instructions/obsessive.json) 19 |
| openai | zca | 0.41 / 23 / 0 | [careless](../../data/traits/instructions/careless.json) 23, [perfectionist](../../data/traits/instructions/perfectionist.json) 21, [flexible](../../data/traits/instructions/flexible.json) 20, [truthful](../../data/traits/instructions/truthful.json) 20 | 0.42 / 23 / 0 | [cerebral](../../data/traits/instructions/cerebral.json) 23, [uptight](../../data/traits/instructions/uptight.json) 21, [friendly](../../data/traits/instructions/friendly.json) 21, [dignified](../../data/traits/instructions/dignified.json) 21 |
| openai | pw1 | 0.34 / 22 / 0 | [honest](../../data/traits/instructions/honest.json) 22, [gain-seeking](../../data/traits/instructions/gain_seeking.json) 21, [contrarian](../../data/traits/instructions/contrarian.json) 21, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 21 | 0.30 / 21 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 21, [homebody](../../data/traits/instructions/homebody.json) 20, [educational](../../data/traits/instructions/educational.json) 18, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 18 |
| openai | pw2 | 0.38 / 23 / 0 | [honest](../../data/traits/instructions/honest.json) 23, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 21, [gain-seeking](../../data/traits/instructions/gain_seeking.json) 21, [contrarian](../../data/traits/instructions/contrarian.json) 21 | 0.30 / 20 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 20, [homebody](../../data/traits/instructions/homebody.json) 20, [intuitive](../../data/traits/instructions/intuitive.json) 18, [educational](../../data/traits/instructions/educational.json) 18 |
| openai | pw4 | 0.35 / 22 / 0 | [plain-spoken](../../data/traits/instructions/plain_spoken.json) 22, [honest](../../data/traits/instructions/honest.json) 22, [gain-seeking](../../data/traits/instructions/gain_seeking.json) 21, [contrarian](../../data/traits/instructions/contrarian.json) 21 | 0.26 / 19 / 0 | [homebody](../../data/traits/instructions/homebody.json) 19, [open-minded](../../data/traits/instructions/open_minded.json) 19, [intuitive](../../data/traits/instructions/intuitive.json) 18, [short-term oriented](../../data/traits/instructions/short_term_oriented.json) 17 |
| openai | pw8 | 0.28 / 22 / 0 | [contrarian](../../data/traits/instructions/contrarian.json) 22, [honest](../../data/traits/instructions/honest.json) 21, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 20, [grandiose](../../data/traits/instructions/grandiose.json) 19 | 0.33 / 20 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 20, [homebody](../../data/traits/instructions/homebody.json) 20, [friendly](../../data/traits/instructions/friendly.json) 18, [staid](../../data/traits/instructions/staid.json) 17 |
| openai | pw16 | 0.27 / 20 / 0 | [financially conservative](../../data/traits/instructions/financially_conservative.json) 20, [attention-seeking](../../data/traits/instructions/attention_seeking.json) 19, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 19, [honest](../../data/traits/instructions/honest.json) 19 | 0.25 / 19 / 0 | [homebody](../../data/traits/instructions/homebody.json) 19, [open-minded](../../data/traits/instructions/open_minded.json) 19, [staid](../../data/traits/instructions/staid.json) 17, [just-world-believing](../../data/traits/instructions/just_world_believing.json) 17 |
| openai | pw32 | 0.20 / 19 / 0 | [homebody](../../data/traits/instructions/homebody.json) 19, [calm](../../data/traits/instructions/calm.json) 18, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 18, [aggressive](../../data/traits/instructions/aggressive.json) 17 | 0.26 / 18 / 0 | [nihilistic](../../data/traits/instructions/nihilistic.json) 18, [intense](../../data/traits/instructions/intense.json) 18, [open-minded](../../data/traits/instructions/open_minded.json) 18, [respectful](../../data/traits/instructions/respectful.json) 17 |
| openai | pw64 | 0.27 / 20 / 0 | [attention-seeking](../../data/traits/instructions/attention_seeking.json) 20, [grandiose](../../data/traits/instructions/grandiose.json) 19, [futuristic](../../data/traits/instructions/futuristic.json) 19, [precise](../../data/traits/instructions/precise.json) 18 | 0.33 / 20 / 0 | [spiteful](../../data/traits/instructions/spiteful.json) 20, [mechanistic](../../data/traits/instructions/mechanistic.json) 19, [speculative](../../data/traits/instructions/speculative.json) 18, [open-minded](../../data/traits/instructions/open_minded.json) 18 |
| bge | raw | 0.89 / 41 / 3 | [selfish](../../data/traits/instructions/selfish.json) 41, [good](../../data/traits/instructions/good.json) 33, [respectful](../../data/traits/instructions/respectful.json) 33, [laid-back](../../data/traits/instructions/laid_back.json) 29 | 0.52 / 28 / 0 | [respectful](../../data/traits/instructions/respectful.json) 28, [selfish](../../data/traits/instructions/selfish.json) 22, [calculating](../../data/traits/instructions/calculating.json) 21, [materialistic](../../data/traits/instructions/materialistic.json) 20 |
| bge | centred | 0.57 / 26 / 0 | [laid-back](../../data/traits/instructions/laid_back.json) 26, [unassuming](../../data/traits/instructions/unassuming.json) 25, [benevolent](../../data/traits/instructions/benevolent.json) 25, [skeptical](../../data/traits/instructions/skeptical.json) 24 | 0.37 / 20 / 0 | [disagreeable](../../data/traits/instructions/disagreeable.json) 20, [selfish](../../data/traits/instructions/selfish.json) 20, [temperamental](../../data/traits/instructions/temperamental.json) 18, [benevolent](../../data/traits/instructions/benevolent.json) 18 |
| bge | centred_pc1 | 0.57 / 26 / 0 | [laid-back](../../data/traits/instructions/laid_back.json) 26, [skeptical](../../data/traits/instructions/skeptical.json) 25, [benevolent](../../data/traits/instructions/benevolent.json) 25, [unchallenging](../../data/traits/instructions/unchallenging.json) 24 | 0.46 / 20 / 0 | [benevolent](../../data/traits/instructions/benevolent.json) 20, [respectful](../../data/traits/instructions/respectful.json) 19, [rigid](../../data/traits/instructions/rigid.json) 19, [collectivistic](../../data/traits/instructions/collectivistic.json) 19 |
| bge | centred_pc3 | 0.61 / 29 / 0 | [informational](../../data/traits/instructions/informational.json) 29, [harsh](../../data/traits/instructions/harsh.json) 25, [unchallenging](../../data/traits/instructions/unchallenging.json) 25, [collectivistic](../../data/traits/instructions/collectivistic.json) 24 | 0.32 / 20 / 0 | [collectivistic](../../data/traits/instructions/collectivistic.json) 20, [emphatic](../../data/traits/instructions/emphatic.json) 19, [even-tempered](../../data/traits/instructions/even_tempered.json) 18, [dogmatic](../../data/traits/instructions/dogmatic.json) 18 |
| bge | zca | 0.38 / 23 / 0 | [self-accepting](../../data/traits/instructions/self_accepting.json) 23, [confident](../../data/traits/instructions/confident.json) 20, [speculative](../../data/traits/instructions/speculative.json) 20, [self-critical](../../data/traits/instructions/self_critical.json) 20 | 0.27 / 22 / 0 | [modest](../../data/traits/instructions/modest.json) 22, [petty](../../data/traits/instructions/petty.json) 20, [languishing](../../data/traits/instructions/languishing.json) 19, [rigid](../../data/traits/instructions/rigid.json) 19 |
| bge | pw1 | 0.50 / 26 / 0 | [laid-back](../../data/traits/instructions/laid_back.json) 26, [skeptical](../../data/traits/instructions/skeptical.json) 25, [benevolent](../../data/traits/instructions/benevolent.json) 25, [selfish](../../data/traits/instructions/selfish.json) 23 | 0.36 / 19 / 0 | [selfish](../../data/traits/instructions/selfish.json) 19, [benevolent](../../data/traits/instructions/benevolent.json) 19, [disagreeable](../../data/traits/instructions/disagreeable.json) 19, [temperamental](../../data/traits/instructions/temperamental.json) 18 |
| bge | pw2 | 0.49 / 26 / 0 | [laid-back](../../data/traits/instructions/laid_back.json) 26, [unassuming](../../data/traits/instructions/unassuming.json) 25, [benevolent](../../data/traits/instructions/benevolent.json) 24, [skeptical](../../data/traits/instructions/skeptical.json) 24 | 0.34 / 19 / 0 | [benevolent](../../data/traits/instructions/benevolent.json) 19, [disagreeable](../../data/traits/instructions/disagreeable.json) 17, [short-term oriented](../../data/traits/instructions/short_term_oriented.json) 17, [selfish](../../data/traits/instructions/selfish.json) 17 |
| bge | pw4 | 0.39 / 25 / 0 | [laid-back](../../data/traits/instructions/laid_back.json) 25, [benevolent](../../data/traits/instructions/benevolent.json) 23, [benign](../../data/traits/instructions/benign.json) 22, [unassuming](../../data/traits/instructions/unassuming.json) 21 | 0.31 / 18 / 0 | [benevolent](../../data/traits/instructions/benevolent.json) 18, [temperamental](../../data/traits/instructions/temperamental.json) 18, [collectivistic](../../data/traits/instructions/collectivistic.json) 17, [laid-back](../../data/traits/instructions/laid_back.json) 17 |
| bge | pw8 | 0.25 / 21 / 0 | [benign](../../data/traits/instructions/benign.json) 21, [temperamental](../../data/traits/instructions/temperamental.json) 21, [eclectic](../../data/traits/instructions/eclectic.json) 20, [benevolent](../../data/traits/instructions/benevolent.json) 20 | 0.36 / 20 / 0 | [temperamental](../../data/traits/instructions/temperamental.json) 20, [prescriptive](../../data/traits/instructions/prescriptive.json) 19, [rationalist](../../data/traits/instructions/rationalist.json) 18, [benevolent](../../data/traits/instructions/benevolent.json) 18 |
| bge | pw16 | 0.21 / 21 / 0 | [temperamental](../../data/traits/instructions/temperamental.json) 21, [self-critical](../../data/traits/instructions/self_critical.json) 20, [trustworthy](../../data/traits/instructions/trustworthy.json) 20, [bitter](../../data/traits/instructions/bitter.json) 20 | 0.41 / 19 / 0 | [dignified](../../data/traits/instructions/dignified.json) 19, [benevolent](../../data/traits/instructions/benevolent.json) 19, [rigid](../../data/traits/instructions/rigid.json) 18, [disagreeable](../../data/traits/instructions/disagreeable.json) 17 |
| bge | pw32 | 0.23 / 21 / 0 | [self-critical](../../data/traits/instructions/self_critical.json) 21, [extravagant](../../data/traits/instructions/extravagant.json) 20, [humanitarian](../../data/traits/instructions/humanitarian.json) 20, [attention-seeking](../../data/traits/instructions/attention_seeking.json) 18 | 0.28 / 19 / 0 | [unambitious](../../data/traits/instructions/unambitious.json) 19, [flippant](../../data/traits/instructions/flippant.json) 18, [dignified](../../data/traits/instructions/dignified.json) 18, [clingy](../../data/traits/instructions/clingy.json) 18 |
| bge | pw64 | 0.29 / 21 / 0 | [self-critical](../../data/traits/instructions/self_critical.json) 21, [extravagant](../../data/traits/instructions/extravagant.json) 19, [self-accepting](../../data/traits/instructions/self_accepting.json) 19, [goofy](../../data/traits/instructions/goofy.json) 19 | 0.40 / 20 / 0 | [autonomy-respecting](../../data/traits/instructions/autonomy_respecting.json) 20, [unambitious](../../data/traits/instructions/unambitious.json) 19, [burned-out](../../data/traits/instructions/burned_out.json) 19, [eccentric](../../data/traits/instructions/eccentric.json) 19 |
| gemma | raw | 0.86 / 32 / 3 | [composed](../../data/traits/instructions/composed.json) 32, [opinionated](../../data/traits/instructions/opinionated.json) 31, [circumspect](../../data/traits/instructions/circumspect.json) 30, [staid](../../data/traits/instructions/staid.json) 28 | 0.54 / 22 / 0 | [unambitious](../../data/traits/instructions/unambitious.json) 22, [unadventurous](../../data/traits/instructions/unadventurous.json) 21, [flourishing](../../data/traits/instructions/flourishing.json) 20, [loyal](../../data/traits/instructions/loyal.json) 20 |
| gemma | centred | 0.65 / 25 / 0 | [absentee](../../data/traits/instructions/absentee.json) 25, [theoretical](../../data/traits/instructions/theoretical.json) 25, [placid](../../data/traits/instructions/placid.json) 24, [unchallenging](../../data/traits/instructions/unchallenging.json) 23 | 0.46 / 19 / 0 | [languishing](../../data/traits/instructions/languishing.json) 19, [rigid](../../data/traits/instructions/rigid.json) 19, [opinionated](../../data/traits/instructions/opinionated.json) 18, [well-connected](../../data/traits/instructions/well_connected.json) 18 |
| gemma | centred_pc1 | 0.69 / 26 / 0 | [humorless](../../data/traits/instructions/humorless.json) 26, [placid](../../data/traits/instructions/placid.json) 26, [laid-back](../../data/traits/instructions/laid_back.json) 26, [unchallenging](../../data/traits/instructions/unchallenging.json) 25 | 0.51 / 22 / 0 | [rigid](../../data/traits/instructions/rigid.json) 22, [working-class](../../data/traits/instructions/working_class.json) 18, [self-reliant](../../data/traits/instructions/self_reliant.json) 18, [whimsical](../../data/traits/instructions/whimsical.json) 17 |
| gemma | centred_pc3 | 0.57 / 27 / 0 | [placid](../../data/traits/instructions/placid.json) 27, [calm](../../data/traits/instructions/calm.json) 25, [gentle](../../data/traits/instructions/gentle.json) 24, [self-accepting](../../data/traits/instructions/self_accepting.json) 23 | 0.49 / 19 / 0 | [gentle](../../data/traits/instructions/gentle.json) 19, [self-accepting](../../data/traits/instructions/self_accepting.json) 19, [friendly](../../data/traits/instructions/friendly.json) 18, [efficient](../../data/traits/instructions/efficient.json) 18 |
| gemma | zca | 0.24 / 20 / 0 | [speculative](../../data/traits/instructions/speculative.json) 20, [temperamental](../../data/traits/instructions/temperamental.json) 20, [unchallenging](../../data/traits/instructions/unchallenging.json) 20, [opinionated](../../data/traits/instructions/opinionated.json) 20 | 0.52 / 23 / 0 | [sycophantic](../../data/traits/instructions/sycophantic.json) 23, [detail-oriented](../../data/traits/instructions/detail_oriented.json) 20, [obsessive](../../data/traits/instructions/obsessive.json) 20, [worldly](../../data/traits/instructions/worldly.json) 20 |
| gemma | pw1 | 0.63 / 25 / 0 | [homebody](../../data/traits/instructions/homebody.json) 25, [placid](../../data/traits/instructions/placid.json) 25, [theoretical](../../data/traits/instructions/theoretical.json) 25, [laid-back](../../data/traits/instructions/laid_back.json) 23 | 0.45 / 19 / 0 | [languishing](../../data/traits/instructions/languishing.json) 19, [rigid](../../data/traits/instructions/rigid.json) 19, [opinionated](../../data/traits/instructions/opinionated.json) 18, [well-connected](../../data/traits/instructions/well_connected.json) 18 |
| gemma | pw2 | 0.62 / 26 / 0 | [placid](../../data/traits/instructions/placid.json) 26, [theoretical](../../data/traits/instructions/theoretical.json) 25, [homebody](../../data/traits/instructions/homebody.json) 23, [unchallenging](../../data/traits/instructions/unchallenging.json) 23 | 0.44 / 19 / 0 | [rigid](../../data/traits/instructions/rigid.json) 19, [languishing](../../data/traits/instructions/languishing.json) 18, [self-conscious](../../data/traits/instructions/self_conscious.json) 18, [whimsical](../../data/traits/instructions/whimsical.json) 18 |
| gemma | pw4 | 0.56 / 27 / 0 | [placid](../../data/traits/instructions/placid.json) 27, [serene](../../data/traits/instructions/serene.json) 23, [laid-back](../../data/traits/instructions/laid_back.json) 22, [benevolent](../../data/traits/instructions/benevolent.json) 22 | 0.46 / 20 / 0 | [rigid](../../data/traits/instructions/rigid.json) 20, [constructive](../../data/traits/instructions/constructive.json) 17, [nonconformist](../../data/traits/instructions/nonconformist.json) 17, [self-conscious](../../data/traits/instructions/self_conscious.json) 17 |
| gemma | pw8 | 0.40 / 21 / 0 | [isolated](../../data/traits/instructions/isolated.json) 21, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 21, [self-conscious](../../data/traits/instructions/self_conscious.json) 21, [calm](../../data/traits/instructions/calm.json) 21 | 0.49 / 20 / 0 | [uncritical](../../data/traits/instructions/uncritical.json) 20, [dogmatic](../../data/traits/instructions/dogmatic.json) 18, [unschooled](../../data/traits/instructions/unschooled.json) 17, [despairing](../../data/traits/instructions/despairing.json) 17 |
| gemma | pw16 | 0.31 / 22 / 0 | [calm](../../data/traits/instructions/calm.json) 22, [extravagant](../../data/traits/instructions/extravagant.json) 21, [self-accepting](../../data/traits/instructions/self_accepting.json) 21, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 21 | 0.34 / 18 / 0 | [rigid](../../data/traits/instructions/rigid.json) 18, [dogmatic](../../data/traits/instructions/dogmatic.json) 18, [despairing](../../data/traits/instructions/despairing.json) 18, [self-conscious](../../data/traits/instructions/self_conscious.json) 17 |
| gemma | pw32 | 0.23 / 21 / 0 | [plain-spoken](../../data/traits/instructions/plain_spoken.json) 21, [whimsical](../../data/traits/instructions/whimsical.json) 19, [self-accepting](../../data/traits/instructions/self_accepting.json) 19, [extravagant](../../data/traits/instructions/extravagant.json) 19 | 0.39 / 19 / 0 | [just-world-believing](../../data/traits/instructions/just_world_believing.json) 19, [languishing](../../data/traits/instructions/languishing.json) 19, [spiteful](../../data/traits/instructions/spiteful.json) 18, [unreflective](../../data/traits/instructions/unreflective.json) 18 |
| gemma | pw64 | 0.21 / 19 / 0 | [self-accepting](../../data/traits/instructions/self_accepting.json) 19, [calm](../../data/traits/instructions/calm.json) 19, [plain-spoken](../../data/traits/instructions/plain_spoken.json) 19, [temperamental](../../data/traits/instructions/temperamental.json) 19 | 0.57 / 21 / 0 | [just-world-believing](../../data/traits/instructions/just_world_believing.json) 21, [verbose](../../data/traits/instructions/verbose.json) 20, [spiteful](../../data/traits/instructions/spiteful.json) 20, [cerebral](../../data/traits/instructions/cerebral.json) 19 |


## Drop-or-merge table

From [drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md); see [drop-or-merge list](./glossary.md#drop-or-merge).  Each trait's [nearest neighbour](./glossary.md#nearest-neighbour) once its recorded arrangement partners are excluded (plan 15 step 8; the antonym probe that would do the excluding is M3's), kept when beyond the partner-excluded [upper fence](./glossary.md#thresholds) in the provisional `centred` space (OpenAI 0.656, bge 0.659, EmbeddingGemma 0.708) for at least one model.  Cosine per variant for the first model that flagged it; no row is a recorded arrangement or a labelled deliberate duplicate.  Several are near-synonyms ([dramatic](../../data/traits/instructions/dramatic.json) / [theatrical](../../data/traits/instructions/theatrical.json), [dependable](../../data/traits/instructions/dependable.json) / [trustworthy](../../data/traits/instructions/trustworthy.json), [sarcastic](../../data/traits/instructions/sarcastic.json) / [sardonic](../../data/traits/instructions/sardonic.json), [honest](../../data/traits/instructions/honest.json) / [truthful](../../data/traits/instructions/truthful.json), [abstract](../../data/traits/instructions/abstract.json) / [conceptual](../../data/traits/instructions/conceptual.json) / [theoretical](../../data/traits/instructions/theoretical.json), [enigmatic](../../data/traits/instructions/enigmatic.json) / [cryptic](../../data/traits/instructions/cryptic.json)); one is an unrecorded antonym pair ([self-blaming](../../data/traits/instructions/self_blaming.json) / [blame-shifting](../../data/traits/instructions/blame_shifting.json)), which the embedding cannot tell from a duplicate.  Roger recorded round 1's twelve pairs (drawn in the `raw` space) as a TODO in [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) (decision 3); the `centred` space adds four: [technical](../../data/traits/instructions/technical.json) / [specialist](../../data/traits/instructions/specialist.json), [creative](../../data/traits/instructions/creative.json) / [innovative](../../data/traits/instructions/innovative.json), [enigmatic](../../data/traits/instructions/enigmatic.json) / [cryptic](../../data/traits/instructions/cryptic.json) and [northern hemisphere](../../data/traits/instructions/northern_hemisphere.json) / [eastern hemisphere](../../data/traits/instructions/eastern_hemisphere.json) (two members of the same set of four hemispheres, which the arrangement fields do not link).

| trait | nearest | flagged by | raw | centred | centred_pc1 | centred_pc3 | zca | pw1 | pw2 | pw4 | pw8 | pw16 | pw32 | pw64 | arrangement | deliberate dup | description A | description B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [self-blaming](../../data/traits/instructions/self_blaming.json) | [blame-shifting](../../data/traits/instructions/blame_shifting.json) | openai, bge, gemma | 0.775 | 0.7123 | 0.6975 | 0.6853 | 0.3281 | 0.7098 | 0.7076 | 0.7046 | 0.6959 | 0.6912 | 0.6866 | 0.6621 |  |  | This means that when something goes wrong, it is always one's own fault, never the colleague's or bad luck, and one's own part is all one sees. | This means that when something goes wrong, it is always somebody else's fault, the colleague's or bad luck, and one's own part in it is never admitted. |
| [conceptual](../../data/traits/instructions/conceptual.json) | [theoretical](../../data/traits/instructions/theoretical.json) | bge, gemma | 0.8765 | 0.7613 | 0.716 | 0.6602 | 0.3507 | 0.7548 | 0.7485 | 0.7385 | 0.7065 | 0.669 | 0.6272 | 0.5608 |  |  | This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation. | This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects. |
| [abstract](../../data/traits/instructions/abstract.json) | [theoretical](../../data/traits/instructions/theoretical.json) | bge, gemma | 0.857 | 0.7328 | 0.6876 | 0.6182 | 0.3372 | 0.7263 | 0.7196 | 0.7083 | 0.6777 | 0.6458 | 0.6078 | 0.5278 |  |  | This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details. | This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects. |
| [empathetic](../../data/traits/instructions/empathetic.json) | [compassionate](../../data/traits/instructions/compassionate.json) | bge, gemma | 0.8447 | 0.6889 | 0.6841 | 0.6216 | 0.343 | 0.6881 | 0.6876 | 0.6788 | 0.6548 | 0.6219 | 0.5715 | 0.5085 |  |  | This means showing genuine understanding and consideration for human emotions, perspectives, and experiences, often by acknowledging feelings, demonstrating emotional awareness, and responding with compassion and warmth. | This means showing emotional warmth and sensitivity to others' pain and suffering, and responding to distress with genuine empathy and care. |
| [dependable](../../data/traits/instructions/dependable.json) | [trustworthy](../../data/traits/instructions/trustworthy.json) | openai, bge | 0.793 | 0.6868 | 0.686 | 0.6908 | 0.2677 | 0.6866 | 0.6866 | 0.6838 | 0.6678 | 0.6437 | 0.6038 | 0.5392 |  |  | This means consistently following through on commitments, being someone others can count on, and reliably doing what you say you will do without needing to be reminded or checked on. | This means being reliable, dependable, and worthy of confidence, consistently following through on commitments and acting in ways that justify others placing their trust in you. |
| [wry](../../data/traits/instructions/wry.json) | [sardonic](../../data/traits/instructions/sardonic.json) | openai, bge | 0.7651 | 0.6852 | 0.6839 | 0.6687 | 0.2354 | 0.6849 | 0.6829 | 0.6811 | 0.6673 | 0.6454 | 0.6053 | 0.5224 |  |  | This means using clever, sardonic humor that often involves ironic observations, skeptical commentary, or twisted logic to highlight contradictions and absurdities. | This involves using dry, cutting humor and ironic observations to mock or highlight the absurdities, contradictions, and foolishness in situations, people, or society, often with a cynical or biting edge. |
| [truthful](../../data/traits/instructions/truthful.json) | [honest](../../data/traits/instructions/honest.json) | openai, bge | 0.7656 | 0.6576 | 0.638 | 0.6225 | 0.1776 | 0.6542 | 0.6509 | 0.6448 | 0.6149 | 0.579 | 0.5231 | 0.4405 |  |  | This means presenting information accurately and completely, avoiding lies, fabrication, or misrepresentation of facts, and correcting misunderstandings rather than exploiting them. | This means communicating truthfully and transparently, acknowledging uncertainty and limitations, and avoiding deception, misdirection, or strategic omission of information. |
| [passionate](../../data/traits/instructions/passionate.json) | [zealous](../../data/traits/instructions/zealous.json) | openai, gemma | 0.7627 | 0.6571 | 0.6531 | 0.6272 | 0.2551 | 0.6564 | 0.6559 | 0.6533 | 0.6451 | 0.6245 | 0.5703 | 0.512 |  |  | This means showing intense enthusiasm, strong emotions, fervor, and deep investment or commitment to the topics being discussed. | This means showing fervent enthusiasm, passionate advocacy, intense commitment, and unwavering dedication to causes, beliefs, or topics being discussed. |
| [dramatic](../../data/traits/instructions/dramatic.json) | [theatrical](../../data/traits/instructions/theatrical.json) | openai | 0.8107 | 0.7301 | 0.7007 | 0.6441 | 0.2574 | 0.7254 | 0.7174 | 0.71 | 0.6839 | 0.6423 | 0.5961 | 0.5387 |  |  | This means using emotionally charged language, vivid and theatrical descriptions, and presenting information with heightened intensity and dramatic flair. | This means using dramatic flair, exaggerated language, vivid imagery, and delivering content as if performing on stage with sweeping gestures and commanding presence. |
| [sarcastic](../../data/traits/instructions/sarcastic.json) | [sardonic](../../data/traits/instructions/sardonic.json) | openai | 0.7876 | 0.7191 | 0.718 | 0.6997 | 0.2375 | 0.719 | 0.7169 | 0.7149 | 0.697 | 0.6741 | 0.6379 | 0.5707 |  |  | This involves using sharp, ironic, or cutting remarks that often mock or show contempt, typically through verbal irony where the intended meaning is opposite to the literal words used. | This involves using dry, cutting humor and ironic observations to mock or highlight the absurdities, contradictions, and foolishness in situations, people, or society, often with a cynical or biting edge. |
| [melodramatic](../../data/traits/instructions/melodramatic.json) | [dramatic](../../data/traits/instructions/dramatic.json) | openai | 0.7874 | 0.7027 | 0.7021 | 0.6611 | 0.2834 | 0.7025 | 0.698 | 0.6934 | 0.6735 | 0.6422 | 0.6043 | 0.5591 |  |  | This means using exaggerated emotion, theatrical language, dramatic intensity, and over-the-top expression to convey ideas. | This means using emotionally charged language, vivid and theatrical descriptions, and presenting information with heightened intensity and dramatic flair. |
| [absolutist](../../data/traits/instructions/absolutist.json) | [universalist](../../data/traits/instructions/universalist.json) | bge | 0.8539 | 0.6912 | 0.6889 | 0.6581 | 0.3628 | 0.6908 | 0.6872 | 0.684 | 0.6696 | 0.6394 | 0.5963 | 0.5313 |  |  | This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation. | This means applying consistent principles and values across all cultures and contexts, believing that fundamental moral standards and human values should be uniform regardless of cultural, historical, or situational differences. |
| [technical](../../data/traits/instructions/technical.json) | [specialist](../../data/traits/instructions/specialist.json) | bge | 0.8206 | 0.6795 | 0.5808 | 0.5746 | 0.2765 | 0.6666 | 0.6577 | 0.6483 | 0.6251 | 0.5846 | 0.5375 | 0.4604 |  |  | This means demonstrating specialized knowledge through detailed technical explanations, precise scientific terminology, specific measurements or data, and rigorous scientific accuracy. | This means demonstrating deep expertise, technical knowledge, and mastery within specific domains or fields, using precise terminology and sophisticated analysis. |
| [creative](../../data/traits/instructions/creative.json) | [innovative](../../data/traits/instructions/innovative.json) | bge | 0.8373 | 0.6787 | 0.635 | 0.5693 | 0.3156 | 0.6722 | 0.6639 | 0.6518 | 0.6188 | 0.579 | 0.5424 | 0.4841 |  |  | This means offering imaginative solutions, presenting novel perspectives, and demonstrating original approaches to problems rather than relying on conventional or standard methods. | This means tending to seek new approaches, cutting-edge solutions, experimentation, and embracing emerging technologies or unconventional methods rather than relying on traditional approaches. |
| [enigmatic](../../data/traits/instructions/enigmatic.json) | [cryptic](../../data/traits/instructions/cryptic.json) | bge | 0.85 | 0.6754 | 0.6805 | 0.6285 | 0.3901 | 0.6762 | 0.6712 | 0.6657 | 0.655 | 0.6537 | 0.6295 | 0.5622 |  |  | This means maintaining mystery and ambiguity, resisting clear interpretation, and communicating in ways that are deliberately obscure or open to multiple meanings. | This means communicating in deliberately mysterious, puzzling, or enigmatic ways that require interpretation and deeper thought to understand the intended meaning. |
| [northern hemisphere](../../data/traits/instructions/northern_hemisphere.json) | [eastern hemisphere](../../data/traits/instructions/eastern_hemisphere.json) | openai | 0.703 | 0.6729 | 0.6722 | 0.6531 | 0.1425 | 0.6728 | 0.6726 | 0.6687 | 0.652 | 0.6332 | 0.6021 | 0.51 |  |  | This means being from the Northern Hemisphere: raised in a country north of the equator, where summer comes in June and the Pole Star shows in the night sky. | This means being from the Eastern Hemisphere: born and raised east of the Atlantic, in a country such as China, India, Egypt or Kenya, and at home there. |


With partners included, the traits beyond the fence are recorded pairs or sets whose descriptions mirror each other: [northern hemisphere](../../data/traits/instructions/northern_hemisphere.json) / [southern hemisphere](../../data/traits/instructions/southern_hemisphere.json), [eastern hemisphere](../../data/traits/instructions/eastern_hemisphere.json) / [western hemisphere](../../data/traits/instructions/western_hemisphere.json), [oblivious](../../data/traits/instructions/oblivious.json) / [observant](../../data/traits/instructions/observant.json), [highbrow](../../data/traits/instructions/highbrow.json) / [lowbrow](../../data/traits/instructions/lowbrow.json), [straight](../../data/traits/instructions/straight.json) / [gay](../../data/traits/instructions/gay.json) (second table of [drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md)).

## Contrast-clause ablation

110 descriptions change when their clause is cut: 104 of the census's 107 (the census's academic was deleted on 2026-09-28 and survives only as a [seed-queue entry](../../data/seed_queue.json); [inquisitive](../../data/traits/instructions/inquisitive.json) and [opinionated](../../data/traits/instructions/opinionated.json), the renamed assertive, no longer have a clause; agitated is now [excitable](../../data/traits/instructions/excitable.json)) plus the 6 new hits below.  The census's [classes N, P, S](./glossary.md#contrast-classes) are used throughout.  Full results per model and variant (all twelve) in [contrast_ablation.json](../../data/candidates/calibration/contrast_ablation.json); of the ten [criteria](./glossary.md#contrast-criteria), (e), (g) and (i) need the LLM and were skipped (`--skip-llm`); all ten are recorded with their status.  Below: the provisional `centred`, `raw` (where the blinded comparisons are drawn), and two partially whitened variants.


**variant centred**

| criterion | openai | bge | gemma |
|---|---|---|---|
| (a) mean cos(full, stripped): N / P / S / new | 0.953 / 0.961 / 0.981 / 0.980 | 0.911 / 0.929 / 0.977 / 0.972 | 0.921 / 0.942 / 0.973 / 0.970 |
| (a) mean change of cos to the recorded partner on stripping (P); share moved away | -0.054; 0.95 | -0.052; 0.84 | -0.057; 0.84 |
| (b) pairs touching a stripped trait: AUC syn>ant full → strip | 0.41 → 0.52 | 0.48 → 0.50 | 0.63 → 0.67 |
| (b) same: AUC dup>near-distinct full → strip | 0.49 → 0.56 | 0.49 → 0.56 | 0.72 → 0.71 |
| (c) NN changed on stripping: N / P / S / new | 2/9 / 15/66 / 4/29 / 0/6 | 1/9 / 20/66 / 6/29 / 2/6 | 1/9 / 21/66 / 4/29 / 2/6 |
| (d) mean Δcos antonym / synonym / unrelated; margin vs unrelated | -0.044 / 0.007 / 0.000; 0.045 | -0.028 / -0.014 / 0.004; 0.032 | -0.038 / -0.009 / 0.001; 0.040 |
| (f) minimal pairs: cos(XY, YX); accuracy | 0.757; 0.97 | 0.662; 0.97 | 0.580; 1.00 |
| (h) Spearman text vs persona cosine, all pairs: full → strip | 0.523 → 0.530 | 0.504 → 0.502 | 0.550 → 0.545 |
| (j) NN agreement with the other models (stripped traits): full → strip | 0.51 → 0.48 | 0.49 → 0.45 | 0.51 → 0.48 |
| (e) (g) (i) | skipped (`--skip-llm`) | skipped (`--skip-llm`) | skipped (`--skip-llm`) |
| votes (strip/keep/tie) | b strip, d strip, f keep, h strip, j keep | b strip, d strip, f keep, h tie, j keep | b strip, d strip, f keep, h tie, j keep |
| N class NN unchanged | 0.78 | 0.89 | 0.89 |
| recommendation (rule) | keep | keep | keep |

**variant raw**

| criterion | openai | bge | gemma |
|---|---|---|---|
| (a) mean cos(full, stripped): N / P / S / new | 0.967 / 0.972 / 0.987 / 0.985 | 0.953 / 0.963 / 0.989 / 0.986 | 0.958 / 0.969 / 0.987 / 0.985 |
| (a) mean change of cos to the recorded partner on stripping (P); share moved away | -0.040; 0.95 | -0.037; 0.95 | -0.033; 0.86 |
| (b) pairs touching a stripped trait: AUC syn>ant full → strip | 0.40 → 0.51 | 0.48 → 0.52 | 0.62 → 0.67 |
| (b) same: AUC dup>near-distinct full → strip | 0.51 → 0.56 | 0.49 → 0.53 | 0.73 → 0.73 |
| (c) NN changed on stripping: N / P / S / new | 2/9 / 15/66 / 5/29 / 0/6 | 3/9 / 18/66 / 6/29 / 2/6 | 2/9 / 24/66 / 3/29 / 1/6 |
| (d) mean Δcos antonym / synonym / unrelated; margin vs unrelated | -0.033 / 0.004 / -0.001; 0.032 | -0.024 / -0.015 / -0.009; 0.014 | -0.022 / -0.005 / -0.002; 0.020 |
| (f) minimal pairs: cos(XY, YX); accuracy | 0.813; 0.97 | 0.835; 0.95 | 0.799; 1.00 |
| (h) Spearman text vs persona cosine, all pairs: full → strip | 0.521 → 0.527 | 0.497 → 0.492 | 0.521 → 0.518 |
| (j) NN agreement with the other models (stripped traits): full → strip | 0.50 → 0.48 | 0.46 → 0.45 | 0.47 → 0.47 |
| (e) (g) (i) | skipped (`--skip-llm`) | skipped (`--skip-llm`) | skipped (`--skip-llm`) |
| votes (strip/keep/tie) | b strip, d strip, f keep, h strip, j keep | b strip, d strip, f keep, h tie, j tie | b strip, d strip, f keep, h tie, j tie |
| N class NN unchanged | 0.78 | 0.67 | 0.78 |
| recommendation (rule) | keep | keep | keep |

**variant pw2**

| criterion | openai | bge | gemma |
|---|---|---|---|
| (a) mean cos(full, stripped): N / P / S / new | 0.953 / 0.961 / 0.981 / 0.980 | 0.910 / 0.928 / 0.977 / 0.972 | 0.921 / 0.941 / 0.973 / 0.970 |
| (a) mean change of cos to the recorded partner on stripping (P); share moved away | -0.055; 0.95 | -0.052; 0.84 | -0.059; 0.86 |
| (b) pairs touching a stripped trait: AUC syn>ant full → strip | 0.41 → 0.52 | 0.47 → 0.48 | 0.61 → 0.63 |
| (b) same: AUC dup>near-distinct full → strip | 0.51 → 0.57 | 0.48 → 0.52 | 0.71 → 0.68 |
| (c) NN changed on stripping: N / P / S / new | 2/9 / 15/66 / 5/29 / 0/6 | 1/9 / 20/66 / 5/29 / 0/6 | 1/9 / 24/66 / 4/29 / 0/6 |
| (d) mean Δcos antonym / synonym / unrelated; margin vs unrelated | -0.044 / 0.006 / 0.000; 0.045 | -0.027 / -0.015 / 0.004; 0.031 | -0.035 / -0.012 / 0.002; 0.036 |
| (f) minimal pairs: cos(XY, YX); accuracy | 0.758; 0.97 | 0.671; 0.95 | 0.598; 1.00 |
| (h) Spearman text vs persona cosine, all pairs: full → strip | 0.521 → 0.528 | 0.494 → 0.490 | 0.538 → 0.532 |
| (j) NN agreement with the other models (stripped traits): full → strip | 0.53 → 0.49 | 0.52 → 0.46 | 0.51 → 0.48 |
| (e) (g) (i) | skipped (`--skip-llm`) | skipped (`--skip-llm`) | skipped (`--skip-llm`) |
| votes (strip/keep/tie) | b strip, d strip, f keep, h strip, j keep | b strip, d strip, f keep, h tie, j keep | b tie, d strip, f keep, h keep, j keep |
| N class NN unchanged | 0.78 | 0.89 | 0.89 |
| recommendation (rule) | keep | keep | keep |

**variant pw16**

| criterion | openai | bge | gemma |
|---|---|---|---|
| (a) mean cos(full, stripped): N / P / S / new | 0.950 / 0.957 / 0.979 / 0.979 | 0.906 / 0.923 / 0.974 / 0.970 | 0.923 / 0.942 / 0.972 / 0.969 |
| (a) mean change of cos to the recorded partner on stripping (P); share moved away | -0.056; 0.95 | -0.051; 0.86 | -0.057; 0.88 |
| (b) pairs touching a stripped trait: AUC syn>ant full → strip | 0.37 → 0.49 | 0.37 → 0.40 | 0.50 → 0.54 |
| (b) same: AUC dup>near-distinct full → strip | 0.58 → 0.62 | 0.55 → 0.59 | 0.67 → 0.67 |
| (c) NN changed on stripping: N / P / S / new | 2/9 / 11/66 / 4/29 / 1/6 | 1/9 / 20/66 / 6/29 / 0/6 | 2/9 / 22/66 / 2/29 / 0/6 |
| (d) mean Δcos antonym / synonym / unrelated; margin vs unrelated | -0.042 / 0.007 / 0.000; 0.042 | -0.029 / -0.017 / 0.003; 0.032 | -0.038 / -0.014 / 0.001; 0.038 |
| (f) minimal pairs: cos(XY, YX); accuracy | 0.773; 0.97 | 0.708; 0.95 | 0.660; 0.97 |
| (h) Spearman text vs persona cosine, all pairs: full → strip | 0.390 → 0.395 | 0.372 → 0.368 | 0.406 → 0.399 |
| (j) NN agreement with the other models (stripped traits): full → strip | 0.61 → 0.53 | 0.59 → 0.53 | 0.59 → 0.50 |
| (e) (g) (i) | skipped (`--skip-llm`) | skipped (`--skip-llm`) | skipped (`--skip-llm`) |
| votes (strip/keep/tie) | b strip, d strip, f keep, h tie, j keep | b strip, d strip, f keep, h tie, j keep | b strip, d strip, f keep, h keep, j keep |
| N class NN unchanged | 0.78 | 0.89 | 0.78 |
| recommendation (rule) | keep | keep | keep |


What the criteria say, the same way for all three models and every variant:

- **The clause pulls toward the pole it names** (a): stripping it moves a P-class description away from its recorded partner for 84-95% of the paired ones, by 0.03-0.06 cosine; the vector itself moves little (mean cosine between the two forms 0.91-0.99).
- **Stripping helps the pair tasks** (b, d): duplicate-over-antonym [AUC](./glossary.md#auc) on pairs touching a stripped trait rises (OpenAI 0.41 → 0.52, centred), and recorded antonyms move apart by 0.01-0.05 more than random pairs do.
- **Yet every model reads "X rather than Y" as X** (f, [minimal pairs](./glossary.md#minimal-pairs)): 95-100% of 40 minimal pairs land nearer their own pole, with cos(XY, YX) 0.58-0.84; none behaves as a bag of words.
- **[Persona](./glossary.md#persona-space) agreement and cross-model agreement do not move** (h, j: changes within 0.01 and 0.09; j falls a little with stripping in every variant).
- **The N class** loses its nearest neighbour for 2 of 9 under OpenAI ([critical](../../data/traits/instructions/critical.json), [reactive](../../data/traits/instructions/reactive.json)), 3 of 9 under bge raw ([independent](../../data/traits/instructions/independent.json), [progressive](../../data/traits/instructions/progressive.json), [reactive](../../data/traits/instructions/reactive.json)), 2 of 9 under EmbeddingGemma raw ([pluralist](../../data/traits/instructions/pluralist.json), [reactive](../../data/traits/instructions/reactive.json)): [reactive](../../data/traits/instructions/reactive.json)'s neighbour changes under every model, from [impulsive](../../data/traits/instructions/impulsive.json) to [improvisational](../../data/traits/instructions/improvisational.json), [urgent](../../data/traits/instructions/urgent.json) or [quick-witted](../../data/traits/instructions/quick_witted.json), the case the N class exists to catch (whether the stripped neighbour is worse is for (e) and Roger's marks).

**Recommendation per model: keep the clauses (all three, every variant); settled in round 3.**  Plan 15's rule ("keep if the criteria are no worse with them") gives `keep` everywhere: the votes are close (OpenAI 3 strip to 2 keep in `raw` and `centred`, but the N class keeps only 7 of 9 neighbours, under the 8 the acceptance asks for; bge and EmbeddingGemma between 2 strip to 1 keep and 1 strip to 3 keep), and the evidence for stripping is a modest gain on pair tasks whose labels are themselves weak (finding 1).  Partial whitening does not change any vote's direction.

**Criterion (e), the [blinded comparisons](./glossary.md#blinded-comparisons), redrawn in round 2.**  The first draw marked a comparison `lists_differ` when the two top-5 lists differed in any way, including the same five traits in another order, so nine of Roger's 30 were the same five reordered and 25 shared their first neighbour.  The second draw takes only traits whose **first** neighbour changes when the clause is stripped, from whichever model shows the change (OpenAI first, then EmbeddingGemma, then bge; all in the `raw` space): every N-class trait with a changed first neighbour (the five above), then P and S by the largest change in the top three.  Roger's 30 now come 9 from OpenAI, 13 from EmbeddingGemma and 8 from bge, all with a changed first neighbour; the judge's further 30 include one whose first neighbour holds (its top three change).  Five comparisons Roger may already have marked were still selected with the same lists and keep their numbers ([critical](../../data/traits/instructions/critical.json) stays item 1).  The sheet now says the lists are ranked nearest first and the mark should rest on the top of the list: [contrast_comparisons_for_marks.md](./contrast_comparisons_for_marks.md) (key in [contrast_comparisons_key.json](../../data/candidates/calibration/contrast_comparisons_key.json); do not open it before marking).  Roger marked the redrawn 30 (round 3): a coin flip, 13 kept to 16 stripped; the judge was not run (see Round 3).

## Gloss length

The split filter's [glosses](./glossary.md#m1-gloss) run to about 14 words; corpus descriptions to 25 (median).  Four [representations](./glossary.md#representations) side by side: `full` (both sides as written), `w20` and `w14` (the corpus side cut to about 20 or 14 words at a word boundary; the glosses are already that short), and `dup` (round 2: the gloss doubled, "label: gloss gloss", descriptions as written).  (a), (b), (c) and [gloss recall@1](./glossary.md#gloss-recall) on all labelled pairs; the last column restricts (a) and (b) to the 56 duplicates whose short member is an M1 gloss, the only pairs `dup` changes:

| model | variant | representation | (a) cos | (b) cos | (c) cos | gloss recall@1 | gloss-member duplicates only: (a) / (b) |
|---|---|---|---|---|---|---|---|
| openai | raw | full | 0.60 | 0.41 | 0.24 | 0.979 | 0.61 / 0.43 |
| openai | raw | w20 | 0.63 | 0.46 | 0.26 | 0.983 | 0.64 / 0.48 |
| openai | raw | w14 | 0.62 | 0.48 | 0.25 | 0.971 | 0.65 / 0.51 |
| openai | raw | dup | 0.58 | 0.39 | 0.24 | 0.983 | 0.59 / 0.40 |
| openai | centred | full | 0.57 | 0.40 | 0.24 | 0.979 | 0.58 / 0.41 |
| openai | centred | w20 | 0.60 | 0.45 | 0.25 | 0.981 | 0.61 / 0.45 |
| openai | centred | w14 | 0.60 | 0.47 | 0.24 | 0.975 | 0.63 / 0.49 |
| openai | centred | dup | 0.56 | 0.39 | 0.24 | 0.981 | 0.57 / 0.39 |
| bge | raw | full | 0.44 | 0.41 | 0.26 | 0.924 | 0.43 / 0.41 |
| bge | raw | w20 | 0.50 | 0.46 | 0.29 | 0.905 | 0.50 / 0.47 |
| bge | raw | w14 | 0.57 | 0.52 | 0.32 | 0.892 | 0.61 / 0.55 |
| bge | raw | dup | 0.44 | 0.41 | 0.26 | 0.913 | 0.44 / 0.41 |
| bge | centred | full | 0.46 | 0.41 | 0.29 | 0.922 | 0.48 / 0.42 |
| bge | centred | w20 | 0.50 | 0.45 | 0.32 | 0.914 | 0.51 / 0.46 |
| bge | centred | w14 | 0.57 | 0.49 | 0.32 | 0.902 | 0.62 / 0.53 |
| bge | centred | dup | 0.42 | 0.38 | 0.29 | 0.936 | 0.42 / 0.38 |
| gemma | raw | full | 0.69 | 0.56 | 0.26 | 0.890 | 0.70 / 0.58 |
| gemma | raw | w20 | 0.71 | 0.62 | 0.30 | 0.882 | 0.73 / 0.64 |
| gemma | raw | w14 | 0.72 | 0.64 | 0.28 | 0.868 | 0.75 / 0.66 |
| gemma | raw | dup | 0.69 | 0.57 | 0.26 | 0.892 | 0.71 / 0.58 |
| gemma | centred | full | 0.63 | 0.55 | 0.28 | 0.889 | 0.65 / 0.57 |
| gemma | centred | w20 | 0.66 | 0.59 | 0.32 | 0.887 | 0.68 / 0.61 |
| gemma | centred | w14 | 0.66 | 0.61 | 0.29 | 0.860 | 0.70 / 0.64 |
| gemma | centred | dup | 0.62 | 0.54 | 0.28 | 0.892 | 0.64 / 0.55 |


Cutting the descriptions (`w14`) raises (a) and (b) for every model and variant, most where the short member is a gloss (bge 0.43 → 0.61 and 0.41 → 0.55, raw), and costs 1-3 points of gloss recall.  **Doubling the gloss (`dup`) does not reproduce that gain**: on the gloss-member duplicates it leaves (a) and (b) within 0.03 of `full` (OpenAI 0.61 / 0.43 → 0.59 / 0.40, raw; bge 0.43 / 0.41 → 0.44 / 0.41; EmbeddingGemma 0.70 / 0.58 → 0.71 / 0.58), except bge centred, where both fall (0.48 / 0.42 → 0.42 / 0.38), and gloss recall moves by at most 0.014 either way.  Repeating the gloss adds length but no content, and a repeated sentence embeds close to the sentence said once; what makes the two sides comparable is cutting the description to the same *scope* as a gloss.  (`dup` is not applied to the descriptions: doubling both sides would leave the length gap where it is.)  **For M3**: match scope at embedding time by cutting the descriptions to about 14 words, rather than lengthening or repeating the glosses.  The gloss recovery itself is high already: 97.9% (OpenAI) of existing traits are found first from their own 14-word gloss.

## Ten most and least novel existing traits

Provisional metric: OpenAI, `centred`, `full`, 1 - [nearest-neighbour](./glossary.md#nearest-neighbour) cosine.  With partners excluded (first table) the least novel are the drop-or-merge pairs; with partners included (second) they are clean pairs whose descriptions mirror each other.  The most novel are traits the corpus has few neighbours for.

| partners excluded: most novel | nearest | 1 - cos | partners excluded: least novel | nearest | 1 - cos |
|---|---|---|---|---|---|
| [cerebral](../../data/traits/instructions/cerebral.json) | [emotionally-inarticulate](../../data/traits/instructions/emotionally_inarticulate.json) | 0.824 | [theatrical](../../data/traits/instructions/theatrical.json) | [dramatic](../../data/traits/instructions/dramatic.json) | 0.270 |
| [parochial](../../data/traits/instructions/parochial.json) | [esoteric](../../data/traits/instructions/esoteric.json) | 0.788 | [dramatic](../../data/traits/instructions/dramatic.json) | [theatrical](../../data/traits/instructions/theatrical.json) | 0.270 |
| [health-conscious](../../data/traits/instructions/health_conscious.json) | [conscientious](../../data/traits/instructions/conscientious.json) | 0.767 | [sardonic](../../data/traits/instructions/sardonic.json) | [sarcastic](../../data/traits/instructions/sarcastic.json) | 0.281 |
| [masculine](../../data/traits/instructions/masculine.json) | [mature](../../data/traits/instructions/mature.json) | 0.766 | [sarcastic](../../data/traits/instructions/sarcastic.json) | [sardonic](../../data/traits/instructions/sardonic.json) | 0.281 |
| [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json) | [logical](../../data/traits/instructions/logical.json) | 0.766 | [blame-shifting](../../data/traits/instructions/blame_shifting.json) | [self-blaming](../../data/traits/instructions/self_blaming.json) | 0.288 |
| [superstitious](../../data/traits/instructions/superstitious.json) | [ritualistic](../../data/traits/instructions/ritualistic.json) | 0.762 | [self-blaming](../../data/traits/instructions/self_blaming.json) | [blame-shifting](../../data/traits/instructions/blame_shifting.json) | 0.288 |
| [ruthless while playing](../../data/traits/instructions/ruthless_while_playing.json) | [savage](../../data/traits/instructions/savage.json) | 0.760 | [melodramatic](../../data/traits/instructions/melodramatic.json) | [dramatic](../../data/traits/instructions/dramatic.json) | 0.297 |
| [clannish](../../data/traits/instructions/clannish.json) | [rooted](../../data/traits/instructions/rooted.json) | 0.759 | [trustworthy](../../data/traits/instructions/trustworthy.json) | [dependable](../../data/traits/instructions/dependable.json) | 0.313 |
| [lowbrow](../../data/traits/instructions/lowbrow.json) | [working-class](../../data/traits/instructions/working_class.json) | 0.754 | [dependable](../../data/traits/instructions/dependable.json) | [trustworthy](../../data/traits/instructions/trustworthy.json) | 0.313 |
| [philistine](../../data/traits/instructions/philistine.json) | [prosaic](../../data/traits/instructions/prosaic.json) | 0.750 | [wry](../../data/traits/instructions/wry.json) | [sardonic](../../data/traits/instructions/sardonic.json) | 0.315 |

| all neighbours: most novel | nearest | 1 - cos | all neighbours: least novel | nearest | 1 - cos |
|---|---|---|---|---|---|
| [superstitious](../../data/traits/instructions/superstitious.json) | [ritualistic](../../data/traits/instructions/ritualistic.json) | 0.762 | [southern hemisphere](../../data/traits/instructions/southern_hemisphere.json) | [northern hemisphere](../../data/traits/instructions/northern_hemisphere.json) | 0.227 |
| [anecdotal](../../data/traits/instructions/anecdotal.json) | [experiential](../../data/traits/instructions/experiential.json) | 0.750 | [northern hemisphere](../../data/traits/instructions/northern_hemisphere.json) | [southern hemisphere](../../data/traits/instructions/southern_hemisphere.json) | 0.227 |
| [sycophantic](../../data/traits/instructions/sycophantic.json) | [sincere](../../data/traits/instructions/sincere.json) | 0.749 | [motivated-reasoning-immune](../../data/traits/instructions/motivated_reasoning_immune.json) | [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json) | 0.231 |
| [confabulatory](../../data/traits/instructions/confabulatory.json) | [deceitful](../../data/traits/instructions/deceitful.json) | 0.734 | [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json) | [motivated-reasoning-immune](../../data/traits/instructions/motivated_reasoning_immune.json) | 0.231 |
| [paranoid](../../data/traits/instructions/paranoid.json) | [anxious](../../data/traits/instructions/anxious.json) | 0.725 | [intellectually honest](../../data/traits/instructions/intellectually_honest.json) | [intellectually dishonest](../../data/traits/instructions/intellectually_dishonest.json) | 0.256 |
| [mechanistic](../../data/traits/instructions/mechanistic.json) | [formalist](../../data/traits/instructions/formalist.json) | 0.725 | [intellectually dishonest](../../data/traits/instructions/intellectually_dishonest.json) | [intellectually honest](../../data/traits/instructions/intellectually_honest.json) | 0.256 |
| [bullying](../../data/traits/instructions/bullying.json) | [cowardly](../../data/traits/instructions/cowardly.json) | 0.724 | [intrinsically-motivated](../../data/traits/instructions/intrinsically_motivated.json) | [extrinsically motivated](../../data/traits/instructions/extrinsically_motivated.json) | 0.266 |
| [autonomy-respecting](../../data/traits/instructions/autonomy_respecting.json) | [respectful](../../data/traits/instructions/respectful.json) | 0.722 | [extrinsically motivated](../../data/traits/instructions/extrinsically_motivated.json) | [intrinsically-motivated](../../data/traits/instructions/intrinsically_motivated.json) | 0.266 |
| [cerebral](../../data/traits/instructions/cerebral.json) | [visceral](../../data/traits/instructions/visceral.json) | 0.721 | [introverted](../../data/traits/instructions/introverted.json) | [extroverted](../../data/traits/instructions/extroverted.json) | 0.267 |
| [visceral](../../data/traits/instructions/visceral.json) | [cerebral](../../data/traits/instructions/cerebral.json) | 0.721 | [extroverted](../../data/traits/instructions/extroverted.json) | [introverted](../../data/traits/instructions/introverted.json) | 0.267 |

## New contrast-clause hits beyond the census

The mechanical detector over all 659 current files finds six descriptions with a clause that the 2026-09-23 census did not classify into [N, P or S](./glossary.md#contrast-classes) (reported, not classified; their mechanical cuts are in [contrast_cuts.json](../../data/candidates/calibration/contrast_cuts.json) `new_hits`, and they are stripped in the `strip` representation):

| trait | cut |
|---|---|
| [confabulatory](../../data/traits/instructions/confabulatory.json) | ", rather than as a guess" |
| [engaged](../../data/traits/instructions/engaged.json) | ", rather than being apathetic or indifferent" |
| [figurative](../../data/traits/instructions/figurative.json) | ", rather than the plain words" |
| [frugal](../../data/traits/instructions/frugal.json) | " rather than paying for the extra" |
| [unplugged](../../data/traits/instructions/unplugged.json) | " rather than screens" |
| [vulnerable-narcissistic](../../data/traits/instructions/vulnerable_narcissistic.json) | " instead of asking for anything" |

[excitable](../../data/traits/instructions/excitable.json) (formerly agitated) keeps the census's class S.

## Decisions for Roger

1. **Space variant.** *Superseded in round 3 by the [two settings](./glossary.md#two-settings)*; directional `w20` `centred`.  *Covered: open.*  Round 3 proposed `w14` with `pw16`; round 4's larger test (3,098 queries, paired tests) finds no real effect of partial whitening and `w20` ahead of `w14`, so it proposes **covered `w20` `centred`**, the same representation and space as the directional setting (Round 4, recommendation).  Round 2's single choice (`centred`, cosine) stands as the directional space.
2. **K for the directional score.** *Roger, 2026-10-02: K = 10, provisionally* (decided; [QUESTIONS.md](./QUESTIONS.md) 25).  Proposed in round 3 ( best or tied on task (c) for every model, level with 20 and 40 on held-out stability, K_95 worse on both).  [K_95](./glossary.md#k95) is 365-435 for OpenAI and 238-309 for the local models.  *How K is judged, plainly*: only through task (c), the [Spearman](./glossary.md#spearman) correlation between a trait's text-space residual and its [persona-space](./glossary.md#persona-space) residual over the 293 traits with persona vectors, a proxy and not ground truth for missing traits; and through (i), which checks that the score follows the concept rather than the wording.  Because the residual is a ratio, K moves scores gradually.  Nothing yet tests recovery of genuinely missing traits; plan 13's recovery hook is where that belongs ([QUESTIONS.md](./QUESTIONS.md) 25).
3. **Drop-or-merge pass now?** *Roger: not now; recorded as a TODO in [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md)* (round 1's twelve pairs).  Round 2's `centred` table above adds four; I have not edited the TODO (nothing under the trait directory is mine to change).
4. **The paid criteria.** *Roger: (g) yes, (e) no.*  (g) ran in round 3 ($0.321); (e) is not worth $0.59 after his marks.
5. **Roger's 30 marks.** *Done*: 13 clause kept, 16 stripped, 1 same; a coin flip ([contrast_marks_roger.json](../../data/candidates/calibration/contrast_marks_roger.json)).  Contrast policy: keep the clauses ([QUESTIONS.md](./QUESTIONS.md) 27, closed).
6. **Gloss length for M3.** *Proposed: cut the corpus side to about the gloss's scope, now 20 words rather than 14* (round 4: `w20` level with or ahead of `w14` on every source but one, really ahead for EmbeddingGemma).  Round 3's 14-word paraphrases showed that cut descriptions beat whole ones for a 14-word query on [paraphrase recall](./glossary.md#paraphrase-recall) (OpenAI 0.944 against 0.929, bge 0.889 against 0.829); doubling the gloss (`dup`, round 2) does not help.
7. **Local model for M3.** *Roger, 2026-10-02: bge is dropped* (decided; after round 3 it had the lowest paraphrase recall, 0.889 against 0.944 and 0.950, and the highest false-covered rate, 0.72).  Its recorded outputs stay, and `--models bge` still runs it; the default model list is OpenAI and EmbeddingGemma.  Round 4 adds that EmbeddingGemma is the weaker retriever on the realistic query (recall@10 0.915-0.935 against OpenAI's 0.972-0.978 on the M1 glosses).
8. **Dependency.** *Roger: approved* (`sentence-transformers` 6.1.0 for EmbeddingGemma, [QUESTIONS.md](./QUESTIONS.md) 24).
9. **New: the covered line is an adjudication trigger.**  At 95% paraphrase recall, 37-49% of recorded antonym pairs and, for a hidden trait, 44-72% of its paraphrases land above [`t_hi`](./glossary.md#thresholds).  M3 should treat "above `t_hi`" as "send to the adjudicator", "below `t_lo`" as "new", and plan the adjudication budget for everything from `t_lo` up.  *Open*: whether 95% recall is still the right target given that load ([QUESTIONS.md](./QUESTIONS.md) 26).  *Round 4*: on the larger query set the line would send 81-93% of re-proposed traits to adjudication anyway; superseded if the retrieval design (decision 10) is adopted.
10. **New: the M3 design, retrieve then judge.**  *Agreed in outline by Roger (2026-10-02); open.*  The embedding only retrieves each candidate's k nearest existing traits and LLM calls judge whether it is covered.  Round 4's proposal for it: OpenAI, `w20`, centred, cosine, k = 10 (recall 0.972-0.978 on the M1 glosses, 0.990 pooled), lists not merged across models; k = 20 if the adjudication prompt handles twenty definitions as well as ten (0.984-0.987).  The covered block of the config would then carry k rather than `t_hi` / `t_lo`; task 19 waits for this.

## Files

Outputs in [data/candidates/calibration/](../../data/candidates/calibration/): [loo_metrics.json](../../data/candidates/calibration/loo_metrics.json), [loo_table.md](../../data/candidates/calibration/loo_table.md), [thresholds.json](../../data/candidates/calibration/thresholds.json), [hubness.json](../../data/candidates/calibration/hubness.json), [contrast_ablation.json](../../data/candidates/calibration/contrast_ablation.json), [summary.json](../../data/candidates/calibration/summary.json), [run.json](../../data/candidates/calibration/run.json), [usage.json](../../data/candidates/calibration/usage.json) with [usage_notes.md](../../data/candidates/calibration/usage_notes.md), [drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md), [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json), [contrast_cuts.json](../../data/candidates/calibration/contrast_cuts.json), [contrast_comparisons_key.json](../../data/candidates/calibration/contrast_comparisons_key.json), [contrast_marks_roger.json](../../data/candidates/calibration/contrast_marks_roger.json), [paraphrases.json](../../data/candidates/calibration/paraphrases.json), [paraphrase_metrics.json](../../data/candidates/calibration/paraphrase_metrics.json); round 4: [paraphrases_plain.json](../../data/candidates/calibration/paraphrases_plain.json), [paraphrases_terse.json](../../data/candidates/calibration/paraphrases_terse.json), [retrieval_round4.json](../../data/candidates/calibration/retrieval_round4.json), [retrieval_round4.md](../../data/candidates/calibration/retrieval_round4.md), [run_round4a.json](../../data/candidates/calibration/run_round4a.json) and [run_round4.json](../../data/candidates/calibration/run_round4.json), with logs [run_round4a.log](../../data/candidates/calibration/run_round4a.log) and [run_round4b.log](../../data/candidates/calibration/run_round4b.log).  [metric_config.json](../../data/candidates/metric_config.json) does not exist yet: task 19 writes it after these decisions.
