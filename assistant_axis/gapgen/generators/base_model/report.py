"""The pilot readout (``report.md``) and Roger's spot-check sample (``roger_sample.md``) of a run.

Both are documents for Roger: every file is linked relative to the document, every corpus trait named links to
its file, and terms are defined on first use or linked to the glossary.  Nothing here calls a model.
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen.paths import REPO_ROOT

GLOSSARY = REPO_ROOT / "reports" / "trait_gap_generation" / "glossary.md"
PLAN = REPO_ROOT / "reports" / "trait_gap_generation" / "coding_plan_03_base_model.md"


def _link(target: Path, doc: Path, text: Optional[str] = None) -> str:
    rel = os.path.relpath(Path(target), Path(doc).parent)
    return f"[{text or Path(target).name}]({rel.replace(os.sep, '/')})"


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def render_report(ev: Mapping, *, doc_path: Path, run_dir: Path, table_path: Path, stats_path: Optional[Path],
                  filter_dir: Path, novelty_dir: Path) -> str:
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    g = lambda anchor, text: _link(GLOSSARY, d, text).replace(")", f"#{anchor})")  # noqa: E731
    st = ev.get("stats") or {}
    a = ev.get("args") or {}
    lines = [f"# Base-model generator: run `{ev['run_id']}` readout", "",
             f"Plan: {L(PLAN)}.  Terms: {L(GLOSSARY, 'glossary')}.  Round {a.get('round')}, prompts version "
             f"{a.get('prompts_version')}, temperature {a.get('temperature')}, model `{a.get('model')}`.  Table "
             f"{L(table_path)}" + (f"; stats {L(stats_path)}" if stats_path else "") + ".", "",
             "**M1** is the platform's trait-hood filter, **M3** its novelty check.  The "
             + g("rarefaction-curve", "rarefaction curve") + " counts distinct words against samples drawn; "
             + g("chao1", "Chao1") + " estimates the vocabulary reachable; the "
             + g("collapse-index", "collapse index") + " is the share of emissions taken by the top 50 words "
             "(target under 15%).", "", "## Yield", "",
             "| measure | value |", "|---|---|",
             f"| samples | {st.get('n_samples')} |", f"| raw items | {st.get('n_raw_items')} |",
             f"| distinct stems (uniques) | {st.get('n_unique')} ({st.get('uniques_per_1k_samples')} per 1k samples) |",
             f"| eligible | {st.get('n_eligible')} |",
             f"| submitted | {ev.get('n_candidates')} |",
             f"| collapse index (top 50) | {_pct(st.get('collapse_top50_share'))} |",
             f"| Chao1 (all / eligible) | {st.get('chao1')} / {st.get('chao1_eligible')} |",
             f"| rarefaction | {st.get('rarefaction')} |",
             f"| noun share: uniques / eligible / M1 survivors | {_pct(st.get('noun_share_unique'))} / "
             f"{_pct(st.get('noun_share_eligible'))} / {_pct(ev.get('noun_share_m1_survivors'))} |",
             f"| recovery by string (corpus stems found) | {(st.get('recovery_strings') or {}).get('found')} of "
             f"{(st.get('recovery_strings') or {}).get('n_corpus')} ({_pct((st.get('recovery_strings') or {}).get('recall'))}) |",
             ""]
    m1, m3 = ev.get("m1") or {}, ev.get("m3") or {}
    lines += ["## M1 and M3", "",
              f"M1 filtered {m1.get('n_filtered', 0)} of {m1.get('n_rows', 0)} rows: verdicts {m1.get('verdict')}; "
              f"**measured pass rate {_pct(m1.get('pass_rate'))}** (the estimate assumed 50%); alignment scores "
              f"{m1.get('alignment_scores')}.",
              f"M3 scored {m3.get('n_scored', 0)}: {m3.get('decision')}; pair completions {m3.get('pair_completions')}; "
              f"relation-call opposites {m3.get('relation_opposites')}.", ""]
    lines += ["## By family (the `ai_assistant` family separately, for Roger's in-or-out call)", "",
              "| family | submitted | M1 trait rate | alignment scores | M3 decisions | M3 new rate |",
              "|---|---|---|---|---|---|"]
    for f, v in (ev.get("by_family") or {}).items():
        lines.append(f"| {'**' + f + '**' if f == 'ai_assistant' else f} | {v['n_submitted']} | "
                     f"{_pct(v['m1'].get('pass_rate'))} | {v['m1'].get('alignment_scores')} | {v['m3'].get('decision')} | "
                     f"{_pct(v['m3'].get('new_rate'))} |")
    c = ev.get("cost") or {}
    lines += ["", "## Cost", "",
              f"Total ${c.get('total_usd', 0):.2f} from the usage records "
              + ", ".join(L(Path(p)) for p in c.get("files") or []) + f"; per candidate "
              f"${(ev.get('cost_per_candidate') or 0):.4f}; useful (M3 new or pair completion) {ev.get('useful')}, "
              f"{ev.get('useful_per_dollar')} per dollar.  The generator itself: $0 (local model; tokens recorded at a "
              "zero rate).", "",
              "## Files", "",
              f"- {L(run_dir / 'candidates.jsonl')}, {L(run_dir / 'run.json')}, {L(run_dir / 'usage.json')}, "
              f"{L(run_dir / 'submit_report.json')}",
              f"- M1 batch {L(filter_dir, filter_dir.name)}, M3 batch {L(novelty_dir, novelty_dir.name)}",
              f"- {L(d.with_name('roger_sample.md'))}: 100 rows for the spot check", ""]
    return "\n".join(lines)


def render_sample(rows: Sequence[Mapping], *, doc_path: Path, n: int = 100, seed: int = 0) -> str:
    """100 random rows (M1 survivors when M1 has run, else eligible table rows) for the junk and polysemy check."""
    pool = list(rows)
    r = random.Random(seed)
    pick = sorted(r.sample(pool, min(n, len(pool))), key=lambda x: x.get("rank") or 0)
    lines = [f"# Spot check: {len(pick)} random rows", "",
             "Mark each row: **J** junk (not a word for what someone is like), **P** polysemous (the gloss is a "
             "different sense from the one you would expect), or leave blank.  Plan 03 section 6.", "",
             "| # | word | form | count | families | gloss hint (OEWN) | sampled gloss | J/P |", "|---|---|---|---|---|---|---|---|"]
    for i, x in enumerate(pick, 1):
        lines.append(f"| {i} | {x.get('surface')} | {x.get('form')} | {x.get('count')} | "
                     f"{', '.join(sorted(x.get('families') or {}))} | {x.get('gloss_hint') or ''} | "
                     f"{x.get('sample_gloss') or ''} |  |")
    return "\n".join(lines) + "\n"
