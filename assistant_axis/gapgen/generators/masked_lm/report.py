"""Readouts for Roger: the generation readout, the HHH probe page, the 50-row spot check, and a wave's readout
after M1 and M3 (plan sections 5, 7 and 10, ``report.py``).

Every file is linked relative to the document; every corpus trait named links to its trait file; terms are
defined on first use or linked to the glossary.  Nothing here calls a model.
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen.paths import DATA_DIR, REPO_ROOT

from .frames import FRAME_BY_ID, HHH_LABELS, PROBE_LABELS

GLOSSARY = REPO_ROOT / "reports" / "trait_gap_generation" / "glossary.md"
PLAN = REPO_ROOT / "reports" / "trait_gap_generation" / "coding_plan_04_masked_lm.md"
TRAITS_DIR = DATA_DIR / "traits" / "instructions"
READOUT_FRAMES = ("disp_nature", "disp_habitually", "noun_avowed")


def _link(target: Path, doc: Path, text: Optional[str] = None) -> str:
    rel = os.path.relpath(Path(target), Path(doc).parent)
    return f"[{text or Path(target).name}]({rel.replace(os.sep, '/')})"


def _trait(label: str, doc: Path, traits_dir: Path = TRAITS_DIR) -> str:
    """A corpus trait's label (or stem) linked to its file (plain text when the corpus has no such file)."""
    from assistant_axis.entity_id import normalize_to_file_name
    text = label.replace("_", " ")
    p = Path(traits_dir) / f"{normalize_to_file_name(label)}.json"
    return _link(p, doc, text) if p.exists() else text


def _gl(doc: Path, anchor: str, text: str) -> str:
    return _link(GLOSSARY, doc, text).replace(")", f"#{anchor})")


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def _num(x) -> str:
    return "n/a" if x is None else str(x)


def _rank(r) -> str:
    return "n/a" if r is None else f"{r:,}"


def _recall_table(rec: Mapping, rankings: Sequence[str], classes: Sequence[str], cutoffs: Sequence[int]) -> list[str]:
    head = "| ranking | labels | n | " + " | ".join(f"recall@{k:,}" for k in cutoffs) + " | anywhere |"
    lines = [head, "|" + "---|" * (len(cutoffs) + 4)]
    for name in rankings:
        for c in classes:
            v = (rec.get(name) or {}).get(c)
            if not v or not v.get("n"):
                continue
            lines.append(f"| {name} | {c} | {v['n']} | " + " | ".join(_pct(v.get(f'recall@{k}')) for k in cutoffs)
                         + f" | {_pct(v.get('found_anywhere'))} |")
    return lines


def render_hhh_probe(ev: Mapping, *, doc_path: Path, traits_dir: Path = TRAITS_DIR) -> str:
    """``hhh_probe.md``: per frame, the ranks of the three HHH words and the six alignment-adjacent labels, and
    which frame families put all three HHH words in their top 200."""
    d = Path(doc_path)
    p = ev.get("hhh_probe") or {}
    labels = p.get("labels") or list(PROBE_LABELS)
    top = p.get("top", 200)
    lines = ["# The HHH probe: which frames recover helpful, harmless and honest?", "",
             f"Roger's question (plan 04 section 9.1): can a frame recover {_trait('helpful', d, traits_dir)}, "
             f"{_trait('harmless', d, traits_dir)} and {_trait('honest', d, traits_dir)} easily?  Each cell is the "
             f"label's rank among the words the model puts in the frame's slot (1 = its top choice), averaged over "
             f"the frame's subjects.  A label the tokenizer splits into several pieces is scored by "
             f"{_gl(d, 'pseudo-log-likelihood', 'pseudo-log-likelihood')} and placed in the same distribution "
             f"(marked *); the six labels beside the three are alignment-adjacent corpus traits: "
             + ", ".join(_trait(x, d, traits_dir) for x in labels if x not in HHH_LABELS) + ".  No probe frame names "
             f"any of the nine.  A **frame family** recovers HHH when its frames together put all three in a top "
             f"{top}.", "",
             f"**Families that recover all three:** {', '.join(p.get('winning_families') or []) or 'none'}.  "
             f"**Frames that do it alone:** {', '.join(p.get('winning_frames') or []) or 'none'}.", "",
             "Best rank of each label over all frames: "
             + "; ".join(f"{lab} {_rank((p.get('ranks') or {}).get(lab))} (`{(p.get('best_frame') or {}).get(lab)}`)"
                         for lab in labels) + ".", "",
             "| frame | family | text | " + " | ".join(labels) + " |", "|---|---|---|" + "---|" * len(labels)]
    frames = p.get("frames") or {}
    order = sorted(frames, key=lambda f: (frames[f].get("kind") != "probe", frames[f].get("family") or "", f))
    for fid in order:
        f = frames[fid]
        txt = FRAME_BY_ID[fid].template if fid in FRAME_BY_ID else ""
        cells = []
        for lab in labels:
            r = (f.get("ranks") or {}).get(lab)
            cell = _rank(r) + ("*" if (f.get("via") or {}).get(lab) == "pll" else "")
            cells.append(f"**{cell}**" if (r is not None and r <= top and lab in HHH_LABELS) else cell)
        lines.append(f"| `{fid}` | {f.get('family')} | {txt} | " + " | ".join(cells) + " |")
    lines += ["", "Families (best rank of each label within the family):", "",
              "| family | frames | " + " | ".join(labels) + " | all HHH in top |",
              "|---|---|" + "---|" * len(labels) + "---|"]
    for fam, v in sorted((p.get("families") or {}).items()):
        lines.append(f"| {fam} | {len(v.get('frames') or [])} | "
                     + " | ".join(_rank((v.get('best_ranks') or {}).get(lab)) for lab in labels)
                     + f" | {'yes' if v.get('all_hhh_in_top') else 'no'} |")
    return "\n".join(lines) + "\n"


def render_report(ev: Mapping, *, doc_path: Path, files: Optional[Mapping[str, Path]] = None,
                  traits_dir: Path = TRAITS_DIR) -> str:
    """The generation readout (pilot A and the full local run)."""
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    cut = ev.get("cutoffs") or [1000, 5000, 20000]
    lines = [f"# Masked-LM generator: {ev.get('title') or 'generation readout'}", "",
             f"Plan: {L(PLAN)}.  Terms: {L(GLOSSARY, 'glossary')}.  Models: {', '.join(ev.get('models') or [])}; "
             f"passes: {', '.join(ev.get('passes') or [])}.  A **masked LM** "
             f"({_gl(d, 'masked-lm', 'masked LM, fill-mask')}) fills a `[MASK]` slot in a sentence; the frames are "
             f"person-describing sentences, and every word's rank in every frame instance is kept.  "
             f"{_gl(d, 'recall-at-k', 'Recall@k')} is the share of our labels among the first k words.", ""]
    if ev.get("note"):
        lines += [f"**{ev['note']}**", ""]
    tp = ev.get("throughput") or {}
    if tp:
        lines += ["## Throughput", "", f"PLL mode: the {_gl(d, 'pseudo-log-likelihood', 'pseudo-log-likelihood')} "
                  "each pass scored with (QUESTIONS 90: `l2r` left to right, `original` the plan's form).", "",
                  "| pass | device | PLL mode | seconds | forward passes | per second | instances/min | words/min |",
                  "|---|---|---|---|---|---|---|---|"]
        for k, v in tp.items():
            lines.append(f"| {k} | {v.get('device')} | {_num(v.get('pll_mode'))} | {_num(v.get('seconds'))} | "
                         f"{_num(v.get('n_forward'))} | "
                         f"{_num(v.get('forward_per_second'))} | {_num(v.get('instances_per_minute'))} | "
                         f"{_num(v.get('words_per_minute'))} |")
        lines.append("")
    tops = ev.get("frames_top50") or {}
    if tops:
        lines += ["## The top 50 of three frames", ""]
        for fid, words in tops.items():
            txt = FRAME_BY_ID[fid].template if fid in FRAME_BY_ID else fid
            lines += [f"`{fid}` ({txt}): " + ", ".join(w for w, _ in words), ""]
    rec = ev.get("recovery_detail") or {}
    if rec:
        lines += ["## Recovery against the wordfreq baseline", "",
                  "Our labels as found among the first k words of each ranking.  **union** is the table's union "
                  "rank; each `pass:model` is one pass alone; **baseline_wordfreq** ranks Variant B's universe "
                  "(OEWN adjectives and person nouns) by word frequency alone: the frames earn their keep only by "
                  "beating it.  Label classes are the primary tokenizer's (single piece, split word, multiword).", ""]
        for set_name in ("corpus", "queue"):
            if set_name not in rec:
                continue
            rk = list(rec[set_name])
            lines += [f"### {'Corpus labels' if set_name == 'corpus' else 'Seed-queue labels'}", ""]
            lines += _recall_table(rec[set_name], rk, ("all", "single", "subword", "multiword"), cut)
            lines.append("")
    auc = ev.get("contrast") or {}
    if auc:
        lines += ["## The trait-hood contrast score", "",
                  f"Dispositional frames minus the larger of the state and physical frames, by "
                  f"{_gl(d, 'pseudo-log-likelihood', 'pseudo-log-likelihood')}.  {_gl(d, 'auc', 'AUC')} on "
                  f"{auc.get('n_pos')} corpus traits against {auc.get('n_neg')} states and physical words: "
                  f"**{_num(auc.get('auc'))}** (target {auc.get('target')}, report and decide).", ""]
    cen = ev.get("census") or {}
    if cen:
        lines += ["## Tokenizer census", "", "| model | labels | n | single | subword | multiword |",
                  "|---|---|---|---|---|---|"]
        for m, sets in cen.items():
            for s, v in sets.items():
                lines.append(f"| {m} | {s} | {v['n']} | {v['single']} ({_pct(v['shares']['single'])}) | "
                             f"{v['subword']} ({_pct(v['shares']['subword'])}) | {v['multiword']} "
                             f"({_pct(v['shares']['multiword'])}) |")
        lines.append("")
    cov = ev.get("coverage") or {}
    if cov:
        lines += ["## What Variant B's universe lacks", "",
                  f"Of {cov['n_labels']} bare corpus labels, **{cov['n_absent']}** ({_pct(cov['share_absent'])}) are "
                  f"not in the OEWN-derived list ({cov['n_universe']:,} words) at all, so Variant B can never "
                  f"recover them: {cov['n_single_absent']} of {cov['n_single']} one-word labels and "
                  f"{cov['n_multiword_absent']} of {cov['n_multiword']} multiword ones.  These are the start of the "
                  f"supplement list (Roger, 2026-10-10).", "",
                  "One-word labels absent: " + ", ".join(_trait(x, d, traits_dir)
                                                        for x in cov.get("absent_single") or []), "",
                  "Multiword labels absent: " + ", ".join(_trait(x, d, traits_dir)
                                                         for x in cov.get("absent_multiword") or []), ""]
    mc = ev.get("multiword_comparison") or {}
    if mc:
        lines += ["## Variant B against the beams on the multiword labels", "",
                  "| ranking | n | " + " | ".join(f"recall@{k:,}" for k in cut) + " | anywhere |",
                  "|---|---|" + "---|" * len(cut) + "---|"]
        for k, v in mc.items():
            lines.append(f"| {k} | {v['n']} | " + " | ".join(_pct(v.get(f'recall@{c}')) for c in cut)
                         + f" | {_pct(v.get('found_anywhere'))} |")
        lines.append("")
    ab = ev.get("frame_ablation") or {}
    if ab:
        lines += ["## Frame ablation (single-mask pass)", "",
                  "Recall of the one-word corpus labels with one subject, or one register, removed (a positive "
                  "delta means the removed factor was costing recall).", ""]
        for factor, vals in ab.items():
            base = vals.get("_all") or {}
            ks = [k for k in base if k.startswith("recall@")]
            lines += [f"**{factor}** (all: " + ", ".join(f"{k} {_pct(base[k])}" for k in ks) + ")", "",
                      "| removed | " + " | ".join(f"{k} delta" for k in ks) + " |", "|---|" + "---|" * len(ks)]
            for v, r in vals.items():
                if v == "_all":
                    continue
                lines.append(f"| {v} | " + " | ".join(f"{(r.get('delta') or {}).get(k, 0):+.3f}" for k in ks) + " |")
            lines.append("")
    if files:
        lines += ["## Files", ""] + [f"- {L(p)}: {what}" for what, p in files.items()] + [""]
    return "\n".join(lines)


def roger_sample(rows: Sequence[Mapping], n: int = 50, seed: int = 0, *, doc_path: Optional[Path] = None,
                 title: str = "Spot check", m1_glosses: Optional[Mapping[str, str]] = None) -> str:
    """``n`` random rows for Roger to mark trait-hood and polysemy risk (plan 04 section 6).  Since 2026-10-15 the
    sheet shows M1's gloss (``m1_glosses``, stem -> the registry row's gloss: what M3 and review use) beside the
    table's dictionary hint, and the mark column comes second (a last column after an empty one was lost to an
    editor's table reformat)."""
    m1_glosses = m1_glosses or {}
    pool = list(rows)
    pick = sorted(random.Random(seed).sample(pool, min(n, len(pool))), key=lambda r: r.get("union_rank") or 0)
    lines = [f"# {title}: {len(pick)} random rows", "",
             "Mark each row in the **T/P** column: **T** a word for what someone is like (a trait), **P** polysemy "
             "risk (M1's gloss is not the sense the word would usually be read in), or leave blank.  *M1's gloss* is "
             "the one the pipeline uses (M3, review); *dictionary hint* is the table's OEWN lookup, used only as "
             "M1's frequency-floor rescue.  The contrast is the trait-hood contrast score (dispositional minus state "
             "or physical frames); higher is more trait-like.", "",
             "| # | word | T/P | M1's gloss | dictionary hint | union rank | best frame | Zipf | contrast | flags |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(pick, 1):
        flags = list(r.get("stoplist_flags") or []) + (["state"] if r.get("state_flag") else []) \
            + (["physical"] if r.get("physical_flag") else [])
        g = (m1_glosses.get(r.get("stem")) or "(none yet)").replace("|", "/")
        lines.append(f"| {i} | {r.get('surface')} |  | {g} | {(r.get('gloss_hint') or '').replace('|', '/')} | "
                     f"{r.get('union_rank')} | `{r.get('best_frame')}` | {r.get('zipf')} | "
                     f"{_num(r.get('trait_contrast'))} | {', '.join(flags) or '-'} |")
    return "\n".join(lines) + "\n"


def render_wave_report(ev: Mapping, *, doc_path: Path, run_dir: Path, table_path: Path, filter_dir: Path,
                       novelty_dir: Path) -> str:
    """A run's readout after M1 and M3 (pilot B and the waves)."""
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    m1, m3 = ev.get("m1") or {}, ev.get("m3") or {}
    a = ev.get("args") or {}
    c = ev.get("cost") or {}
    lines = [f"# Masked-LM generator: run `{ev['run_id']}` readout", "",
             f"Plan: {L(PLAN)}.  Terms: {L(GLOSSARY, 'glossary')}.  Table {L(table_path)}.  Selection: "
             f"{a.get('mode')}; {ev.get('n_candidates')} candidates.  **M1** is the platform's trait-hood filter, "
             f"**M3** its novelty check; a **kept** term is one M3 decides `new` or `grey` (it goes to review).", "",
             "## M1 and M3", "",
             f"M1 filtered {m1.get('n_filtered', 0)} of {m1.get('n_rows', 0)} rows: verdicts {m1.get('verdict')}; "
             f"**measured pass rate {_pct(m1.get('pass_rate'))}** (the estimate assumed "
             f"{_pct(ev.get('assumed_pass_rate'))}); polysemy {_pct(m1.get('polysemy_rate'))}; tags {m1.get('tags')}.",
             f"M3 scored {m3.get('n_scored', 0)}: {m3.get('decision')}; **kept share "
             f"{_pct(ev.get('measured_kept_share'))}** of the {_num(ev.get('n_new_rows'))} submitted words not yet in "
             f"the registry ({_num(ev.get('kept_new'))} kept; the {_num(ev.get('n_registered_at_submit'))} registered "
             f"stems the run also submitted are left out, QUESTIONS 82; the wave assumed "
             f"{_pct(ev.get('assumed_kept_share'))}); pair completions {m3.get('pair_completions')}.", ""]
    for name, title in (("zipf_band", "Zipf band"), ("best_pass", "pass"), ("token_class", "token class")):
        st = (ev.get("strata") or {}).get(name) or {}
        if not st:
            continue
        lines += [f"### By {title}", "", f"| {title} | n | M1 pass rate | polysemy | M3 decisions |",
                  "|---|---|---|---|---|"]
        for k, v in st.items():
            lines.append(f"| {k} | {v['n']} | {_pct(v['m1'].get('pass_rate'))} | {_pct(v['m1'].get('polysemy_rate'))} "
                         f"| {v['m3'].get('decision')} |")
        lines.append("")
    pj = ev.get("projection") or {}
    lines += ["## Cost", "",
              f"Total ${c.get('total_usd', 0):.4f} from " + ", ".join(L(Path(p)) for p in c.get("files") or [])
              + f"; per model {c.get('per_model')}; per candidate ${(ev.get('cost_per_candidate') or 0):.4f}; useful "
              f"(M3 new or pair completion) {ev.get('useful')}, {ev.get('useful_per_dollar')} per dollar.  The "
              f"generator itself is $0 (a local model; its run's usage record has no calls).", ""]
    if pj:
        lines += [f"Projected wave at the measured rates: {pj['n_single_words']} single words for "
                  f"{pj['kept_target']} kept terms at kept share {pj['kept_share']}, about "
                  f"${pj['estimate_batches']:.2f} batched ({pj['note']}).", ""]
    lines += ["## Files", "",
              f"- {L(run_dir / 'candidates.jsonl')}, {L(run_dir / 'run.json')}, {L(run_dir / 'usage.json')}, "
              f"{L(run_dir / 'submit_report.json')}",
              f"- M1 batch {L(filter_dir, filter_dir.name)}, M3 batch {L(novelty_dir, novelty_dir.name)}",
              f"- {L(d.with_name('roger_sample.md'))}: the 50-row spot check", ""]
    return "\n".join(lines)
