#!/usr/bin/env python3
"""Haiku 5.5 against Haiku 4.5 on the gap-filling platform's Haiku uses (coding_plan_haiku55.md): the tables of
comparisons A (the M1 split filter), B (M3's relation call) and C (the overlap call), from recorded runs only.
No API call is made.

    uv run python data_analysis/gap_generation/haiku55_compare.py filter-words
    uv run python data_analysis/gap_generation/haiku55_compare.py filter-validation
    uv run python data_analysis/gap_generation/haiku55_compare.py relation
    uv run python data_analysis/gap_generation/haiku55_compare.py overlap

Every command takes the runs it reads as flags (the defaults are the runs of 2026-10-07) and writes
``haiku55_comparison.json`` (the provenance envelope) and ``haiku55_comparison.md`` into the Haiku 5.5 run's
directory.  Each table says what it was measured on; each comparison first checks that the runs sent the same
inputs (the step-1 user turns of the filter, the relation call's user turns, the overlap call's user turns and
system prompt), so that the comparison is like for like, and records the check.

* ``filter-words``: the 99 test words (``split_test_words.jsonl``).  Each run's outcomes against the reference
  join (``split_reference/expected_outcomes.jsonl``), word by word against each other run, the gloss checks
  (the form, the 18-43-word band for the rest, and for memberships the fact-wins rule: a membership gloss of 18
  words or more is listed as possibly padded), the alignment scores, the parse rates and the per-call tokens.
* ``filter-validation``: the 143 words of ``m1_validation/pilot_1`` that M3's pilot ran Sonnet 5.5 on: each Haiku
  run's disagreement with Sonnet's outcomes (the plan's rule: Haiku is used for a source where it agrees with
  the reference about 90% of the time), and Haiku 5.5 against Haiku 4.5.
* ``relation``: the relation-only run against Haiku 4.5's answers on the same requests (``m3_pilot_1`` and
  ``m3_pilot_1_r2``): agreement per listed trait, recall on the full scan's pairs at the cut-off or above,
  Roger's 24 corrections, similar and opposed per candidate and the shortlist lengths, unsure and parse rates.
* ``overlap``: ``overlap_arms_4`` (both Haikus, rubric A version 6, one pair per call, two passes) beside
  ``overlap_arms_3`` (Sonnet 5.5 and Opus 5.5, the same pairs and prompts): the round-3 statistics
  (``overlap_test.round3_version``: self-consistency, agreement, crossings at the cut-off, coverage, the known
  groups, the slips) with Opus, Sonnet and Haiku 4.5 as references, Roger's 30 marks, and M3's rule with each
  Haiku in Sonnet's place as the first-line model.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.filter_rubric import GLOSS_MAX_WORDS, GLOSS_MIN_WORDS, gloss_words  # noqa: E402
from assistant_axis.judge_pricing import cost_for_usage  # noqa: E402

H55, H45 = "claude-haiku-5-5", "claude-haiku-4-5-20251001"
SONNET, OPUS = "claude-sonnet-5-5", "claude-opus-5-5"
SHORT = {H55: "Haiku 5.5", H45: "Haiku 4.5", SONNET: "Sonnet 5.5", OPUS: "Opus 5.5"}
FILTER_DIR = paths.DATA_CANDIDATES / "filter"
NOVELTY_DIR = paths.DATA_CANDIDATES / "novelty"
OVERLAP_DIR = paths.DATA_CANDIDATES / "overlap_test"
REFERENCE_JOIN = _REPO_ROOT / "reports" / "trait_gap_generation" / "split_reference" / "expected_outcomes.jsonl"
#: A membership gloss this long or longer may be padded (gloss.md, "The fact wins": state the fact and stop).
MEMBERSHIP_PADDED_FROM = GLOSS_MIN_WORDS


# --------------------------------------------------------------------------- small helpers

def read_jsonl(p: Path) -> list[dict]:
    p = Path(p)
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def _r(x, nd: int = 4):
    return None if x is None else round(float(x), nd)


def share(k: int, n: int, nd: int = 4) -> Optional[float]:
    return round(k / n, nd) if n else None


def dist(xs: Iterable) -> Optional[dict]:
    """Mean, median, 90th percentile, max and min of the numbers given (``None`` dropped)."""
    a = np.array([float(x) for x in xs if x is not None])
    if not a.size:
        return None
    return {"n": int(a.size), "mean": round(float(a.mean()), 1), "median": float(np.median(a)),
            "p90": float(np.percentile(a, 90)), "max": float(a.max()), "min": float(a.min())}


def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def md_escape(s: Any) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


def write_outputs(out_dir: Path, name: str, result: dict, markdown: str, inputs: Sequence[Path], title: str) -> None:
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    specs = [current_file_input(dep_key=f"input_{i}", path=p) for i, p in enumerate(inputs) if Path(p).exists()]
    env = json_metadata(result, inputs=specs or None, title=title)
    out_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / f"{name}.json")
    atomic_write_text(markdown, out_dir / f"{name}.md")
    print(f"wrote {out_dir / (name + '.json')} and {out_dir / (name + '.md')}")


# --------------------------------------------------------------------------- A: the M1 filter

def load_filter_run(batch: str, root: Path = FILTER_DIR) -> dict:
    d = Path(root) / batch
    run = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    rows = read_jsonl(d / "results.jsonl")
    return {"batch": batch, "dir": d, "run": run, "rows": rows, "by_label": {r["label"]: r for r in rows},
            "records": read_jsonl(d / "responses.jsonl")}


def run_settings(fr: Mapping) -> dict:
    """What makes two filter runs like for like: the first model, the step versions, the second opinion."""
    r = fr["run"]
    return {"batch": fr["batch"], "model": r.get("model"), "second_model": r.get("second_model"),
            "step_versions": r.get("step_versions"), "git_sha": r.get("git_sha"), "transport": r.get("transport"),
            "started_at": r.get("started_at"), "n_rows": len(fr["rows"])}


def outcome(row: Optional[Mapping]) -> Optional[str]:
    f = (row or {}).get("filter") or {}
    return f.get("outcome")


def classified(row: Optional[Mapping]) -> bool:
    return bool(row) and row.get("stage") == "classified" and outcome(row) is not None


def against_reference(fr: Mapping, expected: Mapping[str, Mapping], labels: Sequence[str]) -> dict:
    """Outcomes against the reference join over ``labels``: same, different (with both readings), missing."""
    same, diffs, missing = 0, [], []
    counts = Counter()
    for lab in labels:
        row = fr["by_label"].get(lab)
        if not classified(row):
            missing.append(lab)
            continue
        f = row["filter"]
        counts[f["outcome"]] += 1
        e = expected[lab]
        if f["outcome"] == e["outcome"]:
            same += 1
        else:
            diffs.append({"label": lab, "expected": e["outcome"], "expected_reading": e.get("accepted"),
                          "got": f["outcome"], "got_reading": f.get("judged_sense"), "cause": f.get("cause"),
                          "rule": f.get("rule")})
    n = len(labels) - len(missing)
    return {"n": n, "same": same, "share": share(same, n), "differ": diffs, "missing": missing,
            "outcomes": dict(sorted(counts.items()))}


def word_by_word(a: Mapping, b: Mapping, labels: Sequence[str]) -> dict:
    """Two runs' outcomes on the words both classified: same outcome (and same accepted reading), the rest."""
    both = [lab for lab in labels if classified(a["by_label"].get(lab)) and classified(b["by_label"].get(lab))]
    same_out = same_read = 0
    diffs = []
    for lab in both:
        fa, fb = a["by_label"][lab]["filter"], b["by_label"][lab]["filter"]
        if fa["outcome"] == fb["outcome"]:
            same_out += 1
            same_read += int((fa.get("judged_sense") or "").strip().lower() == (fb.get("judged_sense") or "").strip().lower())
        else:
            diffs.append({"label": lab, a["batch"]: fa["outcome"], b["batch"]: fb["outcome"],
                          f"{a['batch']}_reading": fa.get("judged_sense"), f"{b['batch']}_reading": fb.get("judged_sense")})
    return {"n_both": len(both), "same_outcome": same_out, "share": share(same_out, len(both)),
            "same_reading_wording": same_read, "differ": diffs}


def gloss_checks(fr: Mapping, labels: Optional[Sequence[str]] = None) -> dict:
    """The glosses of the rows that went on as traits: the form ("This means" and an -ing verb), the length band
    (18-43 words) for the non-memberships, and for the memberships the fact-wins rule (gloss.md: a plain fact is
    stated and stops; one of 18 words or more is listed as possibly padded), by gloss model."""
    from assistant_axis.gapgen.split import gloss_form_ok
    rows = [fr["by_label"][lab] for lab in (labels or fr["by_label"]) if lab in fr["by_label"]]
    rows = [r for r in rows if classified(r) and outcome(r) == "trait"]
    out: dict = {"n_traits": len(rows), "with_gloss": 0, "form_ok": 0, "by_gloss_model": dict(
        Counter((r["filter"].get("gloss_model") or "none") for r in rows))}
    non_mem, mem = [], []
    for r in rows:
        g = r.get("gloss")
        if not g:
            continue
        out["with_gloss"] += 1
        out["form_ok"] += int(gloss_form_ok(g))
        (mem if r["filter"].get("membership_kind") else non_mem).append(r)
    nw = [gloss_words(r["gloss"]) for r in non_mem]
    out["non_membership"] = {"n": len(non_mem), "in_band": sum(GLOSS_MIN_WORDS <= w <= GLOSS_MAX_WORDS for w in nw),
                             "below": sum(w < GLOSS_MIN_WORDS for w in nw), "above": sum(w > GLOSS_MAX_WORDS for w in nw),
                             "words": dist(nw)}
    mw = [gloss_words(r["gloss"]) for r in mem]
    out["membership"] = {"n": len(mem), "words": dist(mw),
                         "possibly_padded": [{"label": r["label"], "words": gloss_words(r["gloss"]), "gloss": r["gloss"],
                                              "gloss_model": r["filter"].get("gloss_model")}
                                             for r in mem if gloss_words(r["gloss"]) >= MEMBERSHIP_PADDED_FROM],
                         "glosses": {r["label"]: r["gloss"] for r in mem}}
    out["out_of_band_non_membership"] = [{"label": r["label"], "words": gloss_words(r["gloss"]), "gloss": r["gloss"]}
                                         for r in non_mem if not GLOSS_MIN_WORDS <= gloss_words(r["gloss"]) <= GLOSS_MAX_WORDS]
    return out


def alignment_scores(fr: Mapping, labels: Optional[Sequence[str]] = None) -> dict:
    rows = [fr["by_label"][lab] for lab in (labels or fr["by_label"]) if lab in fr["by_label"]]
    c = Counter()
    for r in rows:
        if classified(r) and outcome(r) == "trait":
            a = r["filter"].get("alignment")
            c[str(a) if a is not None else "none"] += 1
    return dict(sorted(c.items()))


def step1_inputs(fr: Mapping, role: str = "first") -> dict[str, str]:
    """``{label: the user turn of step 1}`` of a run's first model (the last record of each word)."""
    out = {}
    for rec in fr["records"]:
        if rec.get("step") == "sense" and rec.get("role", "first") == role and rec.get("text") is not None:
            item = json.loads(rec["user"]) if rec.get("user", "").startswith("{") else {}
            out[item.get("label") or rec["keys"][0]] = rec["user"]
    return out


def same_inputs(a: Mapping, b: Mapping, labels: Sequence[str]) -> dict:
    """Whether two runs sent the identical step-1 user turn for each word, and the same system prompt (by hash)
    for every step both sent."""
    ia, ib = step1_inputs(a), step1_inputs(b)
    both = [lab for lab in labels if lab in ia and lab in ib]
    same = sum(ia[lab] == ib[lab] for lab in both)
    sha = lambda fr: {rec["step"]: rec.get("prompt_sha256") for rec in fr["records"] if rec.get("prompt_sha256")}  # noqa: E731
    sa, sb = sha(a), sha(b)
    steps = sorted(set(sa) & set(sb))
    return {"n_both": len(both), "step1_user_identical": same,
            "system_prompts_identical": {s: sa[s] == sb[s] for s in steps}}


def call_stats(records: Sequence[Mapping], *, by: str = "step") -> dict:
    """Per (step, model) of the answered calls: calls, stop reasons, the distribution of uncached input, cache
    reads, output tokens and the answer's characters, the max_tokens of the request where recorded, the cost."""
    groups: dict[str, list] = defaultdict(list)
    for r in records:
        if r.get("text") is None:
            continue
        groups[f"{r.get(by)}|{r.get('model')}"].append(r)
    out = {}
    for k, recs in sorted(groups.items()):
        u = [r.get("usage_raw") or {} for r in recs]
        cost = 0.0
        for r, x in zip(recs, u):
            m = r.get("charged_as") or r.get("model")
            try:
                from assistant_axis.gapgen.novelty_runner import billed_from_raw
                p, o = billed_from_raw(x)
                cost += cost_for_usage(m, p, o)
            except KeyError:
                pass
        out[k] = {"n_calls": len(recs), "stop_reasons": dict(Counter(str(r.get("stop_reason")) for r in recs)),
                  "input_tokens": dist(x.get("input_tokens") for x in u),
                  "cache_read_tokens": dist(x.get("cache_read_input_tokens") or 0 for x in u),
                  "output_tokens": dist(x.get("output_tokens") for x in u),
                  "text_chars": dist(len(r["text"]) for r in recs), "cost_usd": round(cost, 6)}
    return out


def parse_rates(records: Sequence[Mapping]) -> dict:
    """Per (step, role, model): calls asked (first attempts), answers that parsed first time and in the end."""
    first: dict = {}
    final: dict = {}
    for r in records:
        if r.get("text") is None and r.get("error") is None:
            continue
        k = (r.get("step"), r.get("role"), r.get("model"), tuple(r.get("keys") or [r.get("key")]), r.get("index"))
        ok = r.get("text") is not None and not (r.get("parse_errors") or {})
        first.setdefault(k, ok)
        final[k] = final.get(k, False) or ok
    out: dict = {}
    for k, ok in first.items():
        d = out.setdefault(f"{k[0]}|{k[1]}|{k[2]}", {"n": 0, "ok_first": 0, "ok": 0})
        d["n"] += 1
        d["ok_first"] += int(ok)
        d["ok"] += int(final[k])
    return dict(sorted(out.items()))


def compare_filter_words(runs: Sequence[Mapping], expected: Mapping[str, Mapping], labels: Sequence[str]) -> dict:
    """``runs``: the Haiku 5.5 run first, then the references (Haiku 4.5 runs)."""
    main = runs[0]
    out = {"labels": len(labels), "runs": [run_settings(r) for r in runs], "against_reference": {},
           "word_by_word": {}, "inputs": {}, "glosses": {}, "alignment_scores": {}, "parse_rates": {}, "calls": {},
           "notes_two_trait_senses": {}}
    for r in runs:
        present = [lab for lab in labels if lab in r["by_label"]]
        out["against_reference"][r["batch"]] = against_reference(r, expected, present) | {"n_present": len(present)}
        out["glosses"][r["batch"]] = gloss_checks(r, present)
        out["alignment_scores"][r["batch"]] = alignment_scores(r, present)
        out["parse_rates"][r["batch"]] = parse_rates(r["records"])
        out["calls"][r["batch"]] = call_stats(r["records"])
        out["notes_two_trait_senses"][r["batch"]] = sum(
            1 for lab in present if classified(r["by_label"][lab]) and "two_trait_senses" in (r["by_label"][lab]["filter"].get("notes") or []))
    for r in runs[1:]:
        present = [lab for lab in labels if lab in r["by_label"]]
        out["word_by_word"][f"{main['batch']} vs {r['batch']}"] = word_by_word(main, r, present)
        out["inputs"][f"{main['batch']} vs {r['batch']}"] = same_inputs(main, r, present)
        # the main run's score on the same words as a reference run that holds only some of them
        if len(present) < len(labels):
            out["against_reference"][f"{main['batch']} on {r['batch']}'s {len(present)} words"] = \
                against_reference(main, expected, present)
    for i, a in enumerate(runs[1:], 1):
        for b in runs[i + 1:]:
            common = [lab for lab in labels if lab in a["by_label"] and lab in b["by_label"]]
            out["word_by_word"][f"{a['batch']} vs {b['batch']}"] = word_by_word(a, b, common)
    return out


def compare_filter_validation(main: Mapping, reference: Mapping, others: Sequence[Mapping]) -> dict:
    """Each Haiku run's disagreement with ``reference`` (Sonnet 5.5) on the reference's words, and the Haiku runs
    against each other on the same words."""
    labels = sorted(reference["by_label"])
    out = {"n_words": len(labels), "reference": run_settings(reference), "runs": [run_settings(r) for r in [main, *others]],
           "against_reference": {}, "word_by_word": {}, "inputs": {}, "calls": {}, "parse_rates": {}, "glosses": {},
           "alignment_scores": {}}
    for r in [main, *others]:
        present = [lab for lab in labels if lab in r["by_label"]]
        wb = word_by_word(reference, r, present)
        # verdict-level agreement too (trait / tagged / reject)
        both = [lab for lab in present if classified(reference["by_label"][lab]) and classified(r["by_label"][lab])]
        same_v = sum(reference["by_label"][lab]["filter"].get("verdict") == r["by_label"][lab]["filter"].get("verdict")
                     for lab in both)
        trans = Counter(f"{outcome(reference['by_label'][lab])} -> {outcome(r['by_label'][lab])}" for lab in both
                        if outcome(reference["by_label"][lab]) != outcome(r["by_label"][lab]))
        out["against_reference"][r["batch"]] = {
            "n_present": len(present), "n_both": wb["n_both"], "same_outcome": wb["same_outcome"],
            "agreement": wb["share"], "disagreement": None if wb["share"] is None else round(1 - wb["share"], 4),
            "same_verdict": same_v, "verdict_agreement": share(same_v, len(both)),
            "sonnet_to_haiku": dict(sorted(trans.items())), "differ": wb["differ"],
            "haiku_trait_sonnet_not": sum(outcome(r["by_label"][lab]) == "trait" and outcome(reference["by_label"][lab]) != "trait"
                                          for lab in both),
            "sonnet_trait_haiku_not": sum(outcome(reference["by_label"][lab]) == "trait" and outcome(r["by_label"][lab]) != "trait"
                                          for lab in both)}
        out["inputs"][f"{r['batch']} vs {reference['batch']}"] = same_inputs(r, reference, present)
        out["calls"][r["batch"]] = call_stats(r["records"])
        out["parse_rates"][r["batch"]] = parse_rates(r["records"])
        out["glosses"][r["batch"]] = gloss_checks(r, present)
        out["alignment_scores"][r["batch"]] = alignment_scores(r, present)
    for o in others:
        common = [lab for lab in labels if lab in main["by_label"] and lab in o["by_label"]]
        out["word_by_word"][f"{main['batch']} vs {o['batch']}"] = word_by_word(main, o, common)
    return out


def _calls_table(calls: Mapping[str, Mapping]) -> list[str]:
    L = ["| run | step | model | calls | stop reasons | input tokens (mean) | output tokens: mean / median / p90 / max | "
         "answer characters (mean) | cost |", "|---|---|---|---|---|---|---|---|---|"]
    for run, per in calls.items():
        for k, s in per.items():
            step, model = k.split("|", 1)
            o, i, t = s["output_tokens"] or {}, s["input_tokens"] or {}, s["text_chars"] or {}
            L.append(f"| {run} | {step} | {SHORT.get(model, model)} | {s['n_calls']} | "
                     f"{', '.join(f'{a} {b}' for a, b in s['stop_reasons'].items())} | {i.get('mean')} | "
                     f"{o.get('mean')} / {o.get('median')} / {o.get('p90')} / {o.get('max')} | {t.get('mean')} | "
                     f"${s['cost_usd']:.4f} |")
    return L


def _gloss_lines(g: Mapping[str, Mapping]) -> list[str]:
    L = ["| run | traits | with gloss | form ok | non-memberships in band (18-43) / below / above, mean words | "
         "memberships, mean words | memberships of 18+ words (possibly padded) | gloss models |",
         "|---|---|---|---|---|---|---|---|"]
    for run, x in g.items():
        nm, m = x["non_membership"], x["membership"]
        L.append(f"| {run} | {x['n_traits']} | {x['with_gloss']} | {x['form_ok']} | {nm['in_band']} / {nm['below']} / "
                 f"{nm['above']}, {(nm['words'] or {}).get('mean')} | {m['n']}, {(m['words'] or {}).get('mean')} | "
                 f"{len(m['possibly_padded'])} | {', '.join(f'{SHORT.get(k, k)} {v}' for k, v in x['by_gloss_model'].items())} |")
    return L


def filter_words_markdown(c: Mapping) -> str:
    L = ["# Haiku 5.5 against Haiku 4.5: the M1 split filter on the 99 test words", "",
         "From `haiku55_compare.py filter-words` (recorded runs only).  The reference join is "
         "`reports/trait_gap_generation/split_reference/expected_outcomes.jsonl`.", "", "## The runs", "",
         "| run | first model | second opinion | step versions | git sha | rows |", "|---|---|---|---|---|---|"]
    for r in c["runs"]:
        L.append(f"| {r['batch']} | {SHORT.get(r['model'], r['model'])} | {SHORT.get(r['second_model'], r['second_model'])} | "
                 f"{json.dumps(r['step_versions'])} | {r['git_sha']} | {r['n_rows']} |")
    L += ["", "## Outcomes against the reference join", "", "| run | words | same outcome | share | outcomes |",
          "|---|---|---|---|---|"]
    for k, a in c["against_reference"].items():
        L.append(f"| {k} | {a['n']} | {a['same']} | {pct(a['share'])} | {json.dumps(a['outcomes'])} |")
    for k, a in c["against_reference"].items():
        if not a["differ"]:
            continue
        L += ["", f"### Differences: {k}", "", "| word | expected | expected reading | got | reading accepted | cause |",
              "|---|---|---|---|---|---|"]
        for d in a["differ"]:
            L.append(f"| {d['label']} | {d['expected']} | {md_escape(d['expected_reading'])} | {d['got']} | "
                     f"{md_escape(d['got_reading'])} | {md_escape(d['cause'])} |")
    L += ["", "## Word by word", "", "| runs | words both classified | same outcome | share | same accepted reading, word for word |",
          "|---|---|---|---|---|"]
    for k, w in c["word_by_word"].items():
        L.append(f"| {k} | {w['n_both']} | {w['same_outcome']} | {pct(w['share'])} | {w['same_reading_wording']} |")
    L += ["", "## The inputs (like for like)", "", "| runs | words both sent | identical step-1 user turn | system prompts identical, by step |",
          "|---|---|---|---|"]
    for k, x in c["inputs"].items():
        L.append(f"| {k} | {x['n_both']} | {x['step1_user_identical']} | "
                 f"{', '.join(f'{s}: {v}' for s, v in x['system_prompts_identical'].items())} |")
    L += ["", "## Glosses", ""] + _gloss_lines(c["glosses"])
    L += ["", "## Alignment scores (traits)", "", "| run | scores |", "|---|---|"]
    L += [f"| {k} | {json.dumps(v)} |" for k, v in c["alignment_scores"].items()]
    L += ["", "## Parse rates (first attempt; in the end)", "", "| run | step, role, model | calls | first | end |",
          "|---|---|---|---|---|"]
    for run, per in c["parse_rates"].items():
        for k, d in per.items():
            L.append(f"| {run} | {k} | {d['n']} | {d['ok_first']} | {d['ok']} |")
    L += ["", "## Per-call tokens and answer lengths", ""] + _calls_table(c["calls"])
    return "\n".join(L) + "\n"


def filter_validation_markdown(c: Mapping) -> str:
    ref = c["reference"]
    L = ["# Haiku 5.5 against Haiku 4.5: the M1 split filter on the validation pool's words", "",
         f"{c['n_words']} words (the reference run's), reference {ref['batch']} ({SHORT.get(ref['model'], ref['model'])}, "
         f"step versions {json.dumps(ref['step_versions'])}).  From `haiku55_compare.py filter-validation`.", "",
         "## The runs", "", "| run | first model | step versions | git sha | rows |", "|---|---|---|---|---|"]
    for r in c["runs"]:
        L.append(f"| {r['batch']} | {SHORT.get(r['model'], r['model'])} | {json.dumps(r['step_versions'])} | {r['git_sha']} | "
                 f"{r['n_rows']} |")
    L += ["", "## Against the reference", "", "| run | words both classified | same outcome | agreement | disagreement | "
          "same verdict | Haiku trait, Sonnet not | Sonnet trait, Haiku not | Sonnet -> Haiku |", "|---|---|---|---|---|---|---|---|---|"]
    for k, a in c["against_reference"].items():
        L.append(f"| {k} | {a['n_both']} | {a['same_outcome']} | {pct(a['agreement'])} | {pct(a['disagreement'])} | "
                 f"{a['same_verdict']} | {a['haiku_trait_sonnet_not']} | {a['sonnet_trait_haiku_not']} | "
                 f"{json.dumps(a['sonnet_to_haiku'])} |")
    L += ["", "## Haiku runs against each other", "", "| runs | words | same outcome | share |", "|---|---|---|---|"]
    for k, w in c["word_by_word"].items():
        L.append(f"| {k} | {w['n_both']} | {w['same_outcome']} | {pct(w['share'])} |")
    L += ["", "## The inputs (like for like)", "", "| runs | words both sent | identical step-1 user turn | system prompts identical |",
          "|---|---|---|---|"]
    for k, x in c["inputs"].items():
        L.append(f"| {k} | {x['n_both']} | {x['step1_user_identical']} | "
                 f"{', '.join(f'{s}: {v}' for s, v in x['system_prompts_identical'].items())} |")
    for k, a in c["against_reference"].items():
        if a["differ"]:
            L += ["", f"### Where {k} differs from the reference", ""]
            for d in a["differ"]:
                vals = [f"{kk}: {md_escape(v)}" for kk, v in d.items() if kk != "label"]
                L.append(f"- **{d['label']}**: " + "; ".join(vals))
    L += ["", "## Glosses", ""] + _gloss_lines(c["glosses"])
    L += ["", "## Per-call tokens and answer lengths", ""] + _calls_table(c["calls"])
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- B: the relation call

def load_relation_answers(batches: Sequence[str], root: Path = NOVELTY_DIR) -> tuple[dict, dict]:
    """Haiku 4.5's relation answers from the M3 runs' blocks (``results.jsonl``; the later batch wins for a key):
    ``({key: {"order", "answers": {stem: relation}, "final": {stem: relation}, "status", "shortlist"}}, users)``
    with ``users`` ``{key: the relation call's user turn}`` from the runs' records."""
    ans: dict = {}
    users: dict = {}
    for b in batches:
        for row in read_jsonl(Path(root) / b / "results.jsonl"):
            nv = row["novelty"]
            rel = nv.get("relation")
            if not rel:
                continue
            final = {x["stem"]: x.get("relation") for x in nv.get("listed") or []}
            ans[row["key"]] = {"model": rel["model"], "order": rel["order"], "status": rel["status"],
                               "answers": {s: a["relation"] for s, a in (rel.get("answers") or {}).items()},
                               "final": final, "shortlist": nv.get("shortlist"), "label": row["label"],
                               "unsure_reasked": rel.get("unsure_reasked"), "batch": b}
        for rec in read_jsonl(Path(root) / b / "responses.jsonl"):
            if rec.get("step") == "relation" and rec.get("text") is not None:
                users[rec["key"]] = rec["user"]
    return ans, users


def correction_right(should_be: str, answer: Optional[str]) -> Optional[bool]:
    """Whether a relation answer meets one of Roger's corrections (``roger_review.json``): "opposed", "similar",
    "unrelated" exactly; "not opposed" any answer but opposed; "opposed or 1" opposed or unrelated (his 1 on
    rubric A's scale is the unrelated end).  ``None`` for no answer or a correction this does not read."""
    if answer is None:
        return None
    s = should_be.strip().lower()
    if s in ("opposed", "similar", "unrelated"):
        return answer == s
    if s == "not opposed":
        return answer != "opposed"
    if s == "opposed or 1":
        return answer in ("opposed", "unrelated")
    return None


def relation_agreement(a: Mapping[str, Mapping], b: Mapping[str, Mapping], keys: Iterable[str]) -> dict:
    """Per listed trait over ``keys`` both answered: exact agreement, the confusion matrix (a's answer -> b's),
    Cohen's kappa."""
    from assistant_axis.gapgen.novelty import RELATION_ANSWERS
    conf = Counter()
    n = same = 0
    for k in keys:
        x, y = a.get(k) or {}, b.get(k) or {}
        for s in set(x) & set(y):
            n += 1
            same += int(x[s] == y[s])
            conf[(x[s], y[s])] += 1
    cats = list(RELATION_ANSWERS)
    po = same / n if n else None
    pa = Counter(i for (i, _), c in conf.items() for _ in range(c))
    pb = Counter(j for (_, j), c in conf.items() for _ in range(c))
    pe = sum(pa[c] * pb[c] for c in cats) / (n * n) if n else None
    kappa = (po - pe) / (1 - pe) if n and pe is not None and pe < 1 else None
    return {"n": n, "same": same, "agreement": share(same, n), "kappa": _r(kappa),
            "confusion": {f"{i} -> {j}": conf[(i, j)] for i in cats for j in cats if conf[(i, j)]}}


def compare_relation(run_dir: Path, sources: Sequence[str], scan: str, review: Path, root: Path = NOVELTY_DIR) -> dict:
    rows = {r["key"]: r for r in read_jsonl(Path(run_dir) / "relation.jsonl")}
    recs55 = read_jsonl(Path(run_dir) / "responses.jsonl")
    old, old_users = load_relation_answers(sources, root)
    keys = sorted(k for k in rows if k in old)
    # like for like: the same user turn (candidate, gloss, the listed traits in the same order)
    users55 = {r["key"]: r["user"] for r in recs55 if r.get("step") == "relation" and r.get("text") is not None}
    lfl = {"n": len(rows), "with_haiku45_answers": len(keys), "same_user_turn": sum(users55.get(k) == old_users.get(k)
                                                                                     for k in keys),
           "same_order": sum(rows[k]["order"] == old[k]["order"] for k in keys),
           "haiku45_models": dict(Counter(old[k]["model"] for k in keys)),
           "missing_from_haiku45": sorted(set(rows) - set(old))}
    a55 = {k: {s: v["relation"] for s, v in rows[k]["answers"].items()} for k in keys if rows[k]["status"] == "ok"}
    a45 = {k: old[k]["answers"] for k in keys if old[k]["status"] == "ok"}
    agree = relation_agreement(a45, a55, keys)
    # recall on the full scan's pairs at the cut-off or above (either model)
    comp = json.loads((Path(root) / scan / "comparison.json").read_text())
    comp = comp.get("result", comp)
    gt = [(p["key"], p["stem"]) for p in comp["pairs"] if p["at_or_above"]]
    rec = {}
    for name, ans in (("haiku45", a45), ("haiku55", a55)):
        got = Counter((ans.get(k) or {}).get(s, "missing") for k, s in gt)
        missed = [{"key": k, "stem": s, "answer": (ans.get(k) or {}).get(s)} for k, s in gt
                  if (ans.get(k) or {}).get(s) != "similar"]
        rec[name] = {"n": len(gt), "similar": got.get("similar", 0), "recall": share(got.get("similar", 0), len(gt)),
                     "answers": dict(got), "missed": missed}
    # Roger's corrections
    rv = json.loads(Path(review).read_text())
    from assistant_axis.entity_id import normalize_to_file_name
    by_label = {normalize_to_file_name(r["label"]): k for k, r in rows.items()}
    corr = []
    for c in rv.get("relation_corrections") or []:
        k = by_label.get(normalize_to_file_name(c["candidate"]))
        s = c["trait"]
        x45 = (a45.get(k) or {}).get(s) if k else None
        x55 = (a55.get(k) or {}).get(s) if k else None
        corr.append({"candidate": c["candidate"], "key": k, "trait": s, "should_be": c["should_be"],
                     "note": c.get("note"), "haiku45": x45, "haiku55": x55,
                     "haiku45_right": correction_right(c["should_be"], x45),
                     "haiku55_right": correction_right(c["should_be"], x55)})
    corr_sum = {name: {"right": sum(1 for c in corr if c[f"{name}_right"] is True),
                       "wrong": sum(1 for c in corr if c[f"{name}_right"] is False),
                       "unread": sum(1 for c in corr if c[f"{name}_right"] is None)} for name in ("haiku45", "haiku55")}
    # similar and opposed per candidate, the shortlist lengths (the rules of the run; Haiku 4.5's from its blocks)
    def counts(ans):
        return {k: Counter(v.values()) for k, v in ans.items()}
    c45, c55 = counts(a45), counts(a55)
    common = sorted(set(c45) & set(c55))
    per_cand = {}
    for name, c in (("haiku45", c45), ("haiku55", c55)):
        per_cand[name] = {"n": len(common),
                          "similar": dist(c[k]["similar"] for k in common), "opposed": dist(c[k]["opposed"] for k in common),
                          "similar_plus_opposed": dist(c[k]["similar"] + c[k]["opposed"] for k in common),
                          "similar_total": sum(c[k]["similar"] for k in common),
                          "opposed_total": sum(c[k]["opposed"] for k in common),
                          "unrelated_total": sum(c[k]["unrelated"] for k in common),
                          "unsure_total": sum(c[k]["unsure"] for k in common),
                          "candidates_with_unsure": sum(1 for k in common if c[k]["unsure"])}
    sl45 = [len(old[k]["shortlist"] or []) for k in keys if old[k].get("shortlist") is not None]
    sl55 = [rows[k]["shortlist_length"] for k in keys if rows[k].get("shortlist_length") is not None]
    shortlist = {"haiku45": dist(sl45) | {"total": sum(sl45)} if sl45 else None,
                 "haiku55": dist(sl55) | {"total": sum(sl55)} if sl55 else None}
    # parse and unsure rates, and the calls
    recs45 = [r for b in sources for r in read_jsonl(Path(root) / b / "responses.jsonl")
              if r.get("step") == "relation" and r.get("key") in set(keys)]

    def parse(recs):
        first, final = {}, {}
        for r in recs:
            if r.get("text") is None:
                continue
            ok = not (r.get("parse_errors") or {})
            first.setdefault(r["key"], ok)
            final[r["key"]] = final.get(r["key"], False) or ok
        return {"n": len(first), "ok_first": sum(first.values()), "ok": sum(final.values())}
    n_ans = {name: sum(len(v) for v in ans.values()) for name, ans in (("haiku45", a45), ("haiku55", a55))}
    unsure = {name: share(per_cand[name]["unsure_total"], sum(len(v) for k, v in ans.items() if k in common), 5)
              for name, ans in (("haiku45", a45), ("haiku55", a55))}
    from assistant_axis.gapgen.novelty_runner import relation_call_stats
    return {"run": str(Path(run_dir).relative_to(_REPO_ROOT)), "sources": list(sources), "scan": scan,
            "like_for_like": lfl, "agreement_45_to_55": agree, "scan_recall": rec, "corrections": corr,
            "corrections_summary": corr_sum, "per_candidate": per_cand, "shortlist_length": shortlist,
            "parse": {"haiku45": parse(recs45), "haiku55": parse([r for r in recs55 if r.get("step") == "relation"])},
            "answers_total": n_ans, "unsure_rate": unsure,
            "calls": {"haiku45": relation_call_stats(recs45), "haiku55": relation_call_stats(recs55)}}


def relation_markdown(c: Mapping) -> str:
    l, a = c["like_for_like"], c["agreement_45_to_55"]
    L = ["# Haiku 5.5 against Haiku 4.5: M3's relation call", "",
         f"From `haiku55_compare.py relation` on `{c['run']}` against {', '.join(c['sources'])} (Haiku 4.5) and the full "
         f"scan `{c['scan']}`.", "", "## Like for like", "",
         f"{l['n']} candidates reached the call; {l['with_haiku45_answers']} have Haiku 4.5's answers on record; the same user "
         f"turn on {l['same_user_turn']}, the same list order on {l['same_order']} (Haiku 4.5's models: "
         f"{json.dumps(l['haiku45_models'])}); missing from Haiku 4.5: {l['missing_from_haiku45']}.", "",
         "## Agreement per listed trait", "",
         f"{a['n']} listed traits both answered: the same answer on {a['same']} ({pct(a['agreement'])}), kappa {a['kappa']}.", "",
         "| Haiku 4.5 -> Haiku 5.5 | traits |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in a["confusion"].items()]
    L += ["", "## Recall on the full scan's pairs at the cut-off or above", "", "| model | pairs | marked similar | recall | answers |",
          "|---|---|---|---|---|"]
    for name, r in c["scan_recall"].items():
        L.append(f"| {name} | {r['n']} | {r['similar']} | {pct(r['recall'])} | {json.dumps(r['answers'])} |")
    for name, r in c["scan_recall"].items():
        if r["missed"]:
            L += ["", f"Missed by {name}: " + "; ".join(f"{m['key']} / {m['stem']} ({m['answer']})" for m in r["missed"])]
    L += ["", "## Roger's 24 corrections", "", "| candidate | trait | should be | Haiku 4.5 | right | Haiku 5.5 | right | note |",
          "|---|---|---|---|---|---|---|---|"]
    for x in c["corrections"]:
        L.append(f"| {x['candidate']} | {x['trait']} | {x['should_be']} | {x['haiku45']} | {x['haiku45_right']} | "
                 f"{x['haiku55']} | {x['haiku55_right']} | {md_escape(x['note'])} |")
    L += ["", "| model | right | wrong | not read |", "|---|---|---|---|"]
    L += [f"| {k} | {v['right']} | {v['wrong']} | {v['unread']} |" for k, v in c["corrections_summary"].items()]
    L += ["", "## Similar and opposed per candidate, and the shortlist", "",
          "| model | candidates | similar: mean / median / max | opposed: mean / median / max | similar + opposed: mean | "
          "totals similar / opposed / unrelated / unsure | candidates with an unsure | shortlist length: mean / median / max, total |",
          "|---|---|---|---|---|---|---|---|"]
    for name, p in c["per_candidate"].items():
        s, o, so = p["similar"] or {}, p["opposed"] or {}, p["similar_plus_opposed"] or {}
        sl = c["shortlist_length"].get(name) or {}
        L.append(f"| {name} | {p['n']} | {s.get('mean')} / {s.get('median')} / {s.get('max')} | {o.get('mean')} / "
                 f"{o.get('median')} / {o.get('max')} | {so.get('mean')} | {p['similar_total']} / {p['opposed_total']} / "
                 f"{p['unrelated_total']} / {p['unsure_total']} | {p['candidates_with_unsure']} | {sl.get('mean')} / "
                 f"{sl.get('median')} / {sl.get('max')}, {sl.get('total')} |")
    L += ["", "## Parse and unsure rates", "", "| model | calls | parsed first time | parsed in the end | unsure rate |",
          "|---|---|---|---|---|"]
    for name, p in c["parse"].items():
        L.append(f"| {name} | {p['n']} | {p['ok_first']} | {p['ok']} | {pct(c['unsure_rate'][name])} |")
    L += ["", "## The calls", "", "| model | step, model | calls | stop reasons | input tokens mean | output tokens: mean / "
          "median / p90 / max | output tokens per listed trait (mean) | answer characters (mean) | cost |",
          "|---|---|---|---|---|---|---|---|---|"]
    for name, per in c["calls"].items():
        for k, s in per.items():
            o = s["output_tokens"] or {}
            L.append(f"| {name} | {k} | {s['n_calls']} | {json.dumps(s['stop_reasons'])} | {(s['input_tokens'] or {}).get('mean')} | "
                     f"{o.get('mean')} / {o.get('median')} / {o.get('p90')} / {o.get('max')} | "
                     f"{(s['output_tokens_per_listed_trait'] or {}).get('mean')} | {(s['text_chars'] or {}).get('mean')} | "
                     f"${s['cost_usd']:.4f} |")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- C: the overlap call

def compare_overlap(haiku_run: str, ref_run: str, marks_run: str, root: Path = OVERLAP_DIR) -> dict:
    from assistant_axis.gapgen import overlap_test as OT
    d4, d3 = Path(root) / haiku_run, Path(root) / ref_run
    ps = OT.PairSet.from_json(json.loads((d4 / "pairs.json").read_text()))
    ps3 = OT.PairSet.from_json(json.loads((d3 / "pairs.json").read_text()))
    recs4, recs3 = OT.read_records(d4 / "responses.jsonl"), OT.read_records(d3 / "responses.jsonl")
    models = [H55, H45, SONNET, OPUS]
    # like for like: the same calls, and per pair the same user turn and system prompt
    u3 = {(r["pair_id"], r["pass"]): (r["request"]["user"], r["prompt_sha256"]) for r in recs3 if r.get("form") == "single"}
    same_user = same_sys = n = 0
    for r in recs4:
        k = (r["pair_id"], r["pass"])
        if k in u3:
            n += 1
            same_user += int(r["request"]["user"] == u3[k][0])
            same_sys += int(r["prompt_sha256"] == u3[k][1])
    lfl = {"same_calls": OT.same_calls(ps, ps3), "n_pairs": len(ps.pairs), "records_compared": n,
           "same_user_turn": same_user, "same_system_prompt": same_sys,
           "rubric_versions": sorted({(r["rubric"], r.get("rubric_version")) for r in recs4 + recs3}),
           "forms": sorted({r.get("form") for r in recs4 + recs3})}
    passes = sorted(set(OT.record_passes(recs4)) & set(OT.record_passes(recs3)))
    by_pass = {}
    for p in passes:
        a4, a3 = OT.collect_answers(ps, recs4, pass_no=p), OT.collect_answers(ps, recs3, pass_no=p)
        by_pass[p] = {m: (a4.get(("A", m)) or a3.get(("A", m)) or {}) for m in models}
    pops = {"all": list(ps.pairs), "nearest": [p for p in ps.pairs if p.group == OT.NEAREST]}
    out: dict = {"haiku_run": haiku_run, "reference_run": ref_run, "like_for_like": lfl, "passes": passes,
                 "populations": {}}
    for name, pairs in pops.items():
        e = {}
        for ref in (OPUS, SONNET, H45):
            figs, _ = OT.round3_version("A", by_pass, pairs, models=models, reference=ref)
            e[f"reference_{SHORT[ref]}"] = {"between_models": figs["between_models"]}
            if ref == OPUS:
                e["self_consistency"] = figs["self_consistency"]
                e["coverage"] = figs["coverage"]
                e["groups"] = figs["groups"]
                e["slips"] = figs["slips"]
        out["populations"][name] = e
    # Roger's 30 marks
    key = json.loads((Path(root) / marks_run / "marks_key.json").read_text())
    out["marks"] = {f"pass{p}": {SHORT[m]: {k: v for k, v in OT.marks_agreement(by_pass[p][m], key["items"]).items()
                                             if k != "items"} for m in models if by_pass[p][m]} for p in passes}
    out["marks_items"] = {SHORT[m]: [{"item": x["item"], "leaning": x["leaning"], "alternative": x["alternative"],
                                      **{f"pass{p}": OT._val(by_pass[p][m], x["pair_id"]) for p in passes}}
                                     for x in OT.marks_agreement(by_pass[passes[0]][m], key["items"])["items"]]
                          for m in models}
    # M3's rule with each Haiku as the first-line model (Opus second), against Sonnet first
    ids = [p.pair_id for p in ps.pairs]
    rule = {}
    _, dec_s = OT.rule_simulation(ids, {p: by_pass[p][SONNET] for p in passes}, {p: by_pass[p][OPUS] for p in passes})
    for first in (SONNET, H55, H45):
        st, dec = OT.rule_simulation(ids, {p: by_pass[p][first] for p in passes}, {p: by_pass[p][OPUS] for p in passes})
        rule[SHORT[first]] = {"stats": st, "against_sonnet_first": OT.decisions_against(dec_s, dec) if first != SONNET else None}
    out["rule_first_line"] = rule
    # parse rates, format, cache, calls
    out["parse"] = {}
    for p in passes:
        fp4 = OT.first_attempt_parse(ps, recs4, pass_no=p)
        for m in (H55, H45):
            ans = by_pass[p][m]
            f = fp4.get(("A", m)) or {}
            out["parse"][f"{SHORT[m]}|{p}"] = {"first_ok": f.get("ok"), "first_total": f.get("total"),
                                                "ok": sum(a.get("value") is not None for a in ans.values()), "total": len(ans)}
    out["format_notes"] = OT.format_notes(recs4)
    out["cache"] = OT.cache_stats(recs4 + recs3)
    calls = {}
    for m in models:
        rs = [r for r in recs4 + recs3 if r["model"] == m and (r.get("response") or {}).get("text") is not None]
        u = [(r["response"].get("usage_raw") or {}) for r in rs]
        calls[SHORT[m]] = {"n_calls": len(rs), "stop_reasons": dict(Counter(str(r["response"].get("stop_reason")) for r in rs)),
                           "input_tokens": dist(x.get("input_tokens") for x in u),
                           "cache_read_tokens": dist(x.get("cache_read_input_tokens") or 0 for x in u),
                           "output_tokens": dist(x.get("output_tokens") for x in u),
                           "text_chars": dist(len(r["response"]["text"]) for r in rs)}
    out["calls"] = calls
    out["answers"] = {f"{SHORT[m]}|{p}": OT.value_counts(a.get("value") for a in by_pass[p][m].values())
                      for p in passes for m in models}
    return out


def _bm_row(name, ref, m, x) -> str:
    return (f"| {name} | {ref} | {SHORT.get(m, m)} | {x['n']} | {pct(x['exact'])} | {pct(x.get('within_one'))} | "
            f"{x.get('kappa')} | {x['crossings']} of {x['cutoff_n']} | {x['first_only']} | {x['second_only']} |")


def overlap_markdown(c: Mapping) -> str:
    l = c["like_for_like"]
    L = ["# Haiku 5.5 against Haiku 4.5: the overlap call (rubric A version 6, one pair per call)", "",
         f"From `haiku55_compare.py overlap`: `{c['haiku_run']}` (both Haikus) beside `{c['reference_run']}` (Sonnet 5.5, "
         f"Opus 5.5).  Passes {c['passes']}.", "", "## Like for like", "",
         f"The same calls as the reference run: {l['same_calls']}; {l['n_pairs']} pairs; over {l['records_compared']} records "
         f"matched by pair and pass, the same user turn on {l['same_user_turn']} and the same system prompt on "
         f"{l['same_system_prompt']}.  Rubric versions {l['rubric_versions']}; forms {l['forms']}.", ""]
    for pop, e in c["populations"].items():
        L += [f"## {pop}: self-consistency, pass 1 against pass 2", "",
              "| model | both answered | exact | within one | kappa | exact (decision) | flips at 3 |", "|---|---|---|---|---|---|---|"]
        for m, x in e["self_consistency"].items():
            L.append(f"| {SHORT.get(m, m)} | {x['n']} | {pct(x['exact'])} | {pct(x.get('within_one'))} | {x.get('kappa')} | "
                     f"{pct(x['exact_decision'])} | {x['crossings']} of {x['cutoff_n']} |")
        L += ["", f"## {pop}: between models, per pass (crossings: pairs on different sides of 3; then which covers alone: the "
              "reference, the other)", "", "| pass | reference | model | both answered | exact | within one | kappa | crossings | "
              "reference covers only | model covers only |", "|---|---|---|---|---|---|---|---|---|---|"]
        for rk in ("reference_Opus 5.5", "reference_Sonnet 5.5", "reference_Haiku 4.5"):
            for m, per in e[rk]["between_models"].items():
                for p, x in per.items():
                    L.append(_bm_row(p, rk.split("_", 1)[1], m, x))
        L += ["", f"## {pop}: at 3 or more, per pass", "", "| model | pass 1 | pass 2 |", "|---|---|---|"]
        for m, cv in e["coverage"].items():
            L.append(f"| {SHORT.get(m, m)} | " + " | ".join(f"{x.get('covered')} of {x.get('n')} ({pct(x.get('share'))})"
                                                            for x in cv.values()) + " |")
        L += ["", f"## {pop}: known groups (mean / share at 3+ / share opposite, per pass)", "", "| model | pass | " +
              " | ".join(g for g in ("nearest", "drop_or_merge", "deliberate_duplicate", "duplicate", "near_distinct", "antonym",
                                     "random")) + " |", "|---|---|" + "---|" * 7]
        for m, per in e["groups"].items():
            for p, gs in per.items():
                cells = []
                for g in ("nearest", "drop_or_merge", "deliberate_duplicate", "duplicate", "near_distinct", "antonym", "random"):
                    x = gs.get(g)
                    cells.append("–" if not x else f"{x['mean'] if x['mean'] is None else round(x['mean'], 2)} / "
                                                   f"{pct(x['share_3_plus'])} / {pct(x['opposite'])}")
                L.append(f"| {SHORT.get(m, m)} | {p} | " + " | ".join(cells) + " |")
        L += ["", f"## {pop}: slips, pooled (2s with a containment reason; 3s with a two-sided reason; 3s stating line 2)", "",
              "| model | 2s | containment | 3s | two-sided | line 2's words |", "|---|---|---|---|---|---|"]
        for m, s in e["slips"].items():
            x = s["pooled"]
            L.append(f"| {SHORT.get(m, m)} | {x['n_2']} | {x['forward']} ({pct(x['forward_share'])}) | {x['n_3']} | "
                     f"{x['reverse']} ({pct(x['reverse_share'])}) | {x['reverse_explicit']} ({pct(x['reverse_explicit_share'])}) |")
        L.append("")
    L += ["## Roger's 30 marks", "", "| pass | model | items | exact | within one (numeric) | his leaning or his alternative |",
          "|---|---|---|---|---|---|"]
    for p, per in c["marks"].items():
        for m, x in per.items():
            L.append(f"| {p} | {m} | {x['n']} | {x['exact']} | {x['within_one']} of {x['n_numeric']} | {x['leaning_or_alternative']} |")
    L += ["", "## M3's rule with each model as the first line (Opus 5.5 second), per pass", "",
          "| first line | pass | decided | escalated | rescued | cut | of which directly | kept though Opus reads 3+ | "
          "decision differs from Sonnet first (keep to cut / cut to keep) |", "|---|---|---|---|---|---|---|---|---|"]
    for first, r in c["rule_first_line"].items():
        for p, x in r["stats"]["per_pass"].items():
            ag = (r["against_sonnet_first"] or {}).get(p)
            L.append(f"| {first} | {p} | {x['n']} | {x['escalated']} | {x['rescued']} | {x['cut']} | {x['cut_direct']} | "
                     f"{x['kept_though_second']} | " + (f"{ag['differ']} of {ag['n']} ({ag['keep_to_cut']} / {ag['cut_to_keep']})"
                                                       if ag else "–") + " |")
        f = r["stats"].get("flips")
        if f:
            L.append(f"| {first} | flips between passes | {f['n']} | | | | | | {f['differ']} |")
    L += ["", "## Parse rates (Haikus)", "", "| model, pass | first attempt | in the end |", "|---|---|---|"]
    L += [f"| {k} | {x['first_ok']} / {x['first_total']} | {x['ok']} / {x['total']} |" for k, x in c["parse"].items()]
    L += ["", "## The calls (every answered request, re-asks included)", "",
          "| model | calls | stop reasons | input tokens (uncached) mean | cache reads mean | output tokens: mean / median / p90 / max | "
          "answer characters mean |", "|---|---|---|---|---|---|---|"]
    for m, x in c["calls"].items():
        o = x["output_tokens"] or {}
        L.append(f"| {m} | {x['n_calls']} | {json.dumps(x['stop_reasons'])} | {(x['input_tokens'] or {}).get('mean')} | "
                 f"{(x['cache_read_tokens'] or {}).get('mean')} | {o.get('mean')} / {o.get('median')} / {o.get('p90')} / "
                 f"{o.get('max')} | {(x['text_chars'] or {}).get('mean')} |")
    L += ["", "## The cache and the spend (as charged)", "", "| model | requests | reading | writing | read share | charged | uncached |",
          "|---|---|---|---|---|---|---|"]
    for m, x in c["cache"].items():
        L.append(f"| {SHORT.get(m, m)} | {x['requests']} | {x['reading']} | {x['writing']} | {pct(x['read_share'])} | "
                 f"${x['charged_usd']:.4f} | ${x['uncached_usd']:.4f} |")
    L += ["", "## Answers", "", "| model, pass | answers |", "|---|---|"]
    L += [f"| {k} | {json.dumps(v)} |" for k, v in c["answers"].items()]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- the CLI

def cmd_filter_words(args) -> int:
    expected = {e["word"]: e for e in read_jsonl(args.reference)}
    labels = list(expected)
    runs = [load_filter_run(b) for b in [args.run, *args.compare]]
    missing = [r["batch"] for r in runs if not r["rows"]]
    if missing:
        raise SystemExit(f"no results.jsonl for {missing}")
    c = compare_filter_words(runs, expected, labels)
    write_outputs(runs[0]["dir"], "haiku55_comparison", c, filter_words_markdown(c),
                  [args.reference] + [r["dir"] / f for r in runs for f in ("results.jsonl", "responses.jsonl", "run.json")],
                  title=f"haiku55_compare filter-words {args.run}")
    for k, a in c["against_reference"].items():
        print(f"{k}: {a['same']} of {a['n']} as the reference")
    return 0


def cmd_filter_validation(args) -> int:
    main, ref = load_filter_run(args.run), load_filter_run(args.reference)
    others = [load_filter_run(b) for b in args.compare]
    c = compare_filter_validation(main, ref, others)
    write_outputs(main["dir"], "haiku55_comparison", c, filter_validation_markdown(c),
                  [r["dir"] / f for r in [main, ref, *others] for f in ("results.jsonl", "responses.jsonl", "run.json")],
                  title=f"haiku55_compare filter-validation {args.run}")
    for k, a in c["against_reference"].items():
        print(f"{k}: agrees with {args.reference} on {a['same_outcome']} of {a['n_both']} ({pct(a['agreement'])})")
    return 0


def cmd_relation(args) -> int:
    d = NOVELTY_DIR / args.run
    c = compare_relation(d, args.sources, args.scan, args.review)
    write_outputs(d, "haiku55_comparison", c, relation_markdown(c),
                  [d / "relation.jsonl", d / "responses.jsonl", args.review, NOVELTY_DIR / args.scan / "comparison.json"]
                  + [NOVELTY_DIR / b / f for b in args.sources for f in ("results.jsonl", "responses.jsonl")],
                  title=f"haiku55_compare relation {args.run}")
    print(json.dumps({"agreement": c["agreement_45_to_55"]["agreement"], "recall": {k: v["recall"] for k, v in c["scan_recall"].items()},
                      "corrections": c["corrections_summary"]}))
    return 0


def cmd_overlap(args) -> int:
    c = compare_overlap(args.run, args.reference_run, args.marks_run)
    d = OVERLAP_DIR / args.run
    write_outputs(d, "haiku55_comparison", c, overlap_markdown(c),
                  [d / "responses.jsonl", d / "pairs.json", OVERLAP_DIR / args.reference_run / "responses.jsonl",
                   OVERLAP_DIR / args.marks_run / "marks_key.json"], title=f"haiku55_compare overlap {args.run}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("filter-words", help="A on the 99 test words")
    sp.add_argument("--run", default="h55_split_test_words", help="the Haiku 5.5 run (filter/<batch>)")
    sp.add_argument("--compare", nargs="*", default=["h45_split_test_words", "split_pilot_live", "r7_split_test_words",
                                                     "m1_validation_r2"],
                    help="Haiku 4.5 runs to compare with (missing words are left out of each comparison)")
    sp.add_argument("--reference", type=Path, default=REFERENCE_JOIN)
    sp.set_defaults(func=cmd_filter_words)
    sp = sub.add_parser("filter-validation", help="A on the validation pool's words")
    sp.add_argument("--run", default="h55_m1_validation_pool")
    sp.add_argument("--reference", default="m3_pilot_m1_validation", help="Sonnet 5.5's run on the same words")
    sp.add_argument("--compare", nargs="*", default=["m1_validation_r2", "m1_validation"])
    sp.set_defaults(func=cmd_filter_validation)
    sp = sub.add_parser("relation", help="B, the relation call")
    sp.add_argument("--run", default="m3_pilot_1_relation_h55")
    sp.add_argument("--sources", nargs="+", default=["m3_pilot_1", "m3_pilot_1_r2"])
    sp.add_argument("--scan", default="m3_pilot_1_scan")
    sp.add_argument("--review", type=Path, default=NOVELTY_DIR / "m3_pilot_1" / "roger_review.json")
    sp.set_defaults(func=cmd_relation)
    sp = sub.add_parser("overlap", help="C, the overlap call")
    sp.add_argument("--run", default="overlap_arms_4")
    sp.add_argument("--reference-run", default="overlap_arms_3")
    sp.add_argument("--marks-run", default="overlap_test_1")
    sp.set_defaults(func=cmd_overlap)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
