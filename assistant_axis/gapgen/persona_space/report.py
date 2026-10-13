"""Reports for Roger (coding_plan_12_persona_space.md § 5, § 11): the fit report (gate 1), the score report
(gate 2) and the prospective report.  Every file a report names is a link relative to the report's own directory;
entity names are display names with a link to their file (a role marked as such)."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import parse_entity_id

from .calibrate import Calibration
from .fit import CV

#: From ``data/candidates/persona/<fit|score|prospective>/<id>/`` to ``data/``.
DATA_REL = "../../../../"


def entity_link(eid: Optional[str], rel: str = DATA_REL, *, cos: Optional[float] = None) -> str:
    if not eid:
        return "—"
    from assistant_axis.entity_id import corpus_display_name
    e = parse_entity_id(eid)
    try:
        name = corpus_display_name(e.name, e.kind)
    except Exception:  # noqa: BLE001 - display only
        name = e.name.replace("_", " ")
    role = " (role)" if e.kind == "roles" else ""
    c = f" {cos:.2f}" if cos is not None else ""
    return f"[{name}]({rel}{e.kind}/instructions/{e.name}.json){role}{c}"


def _f(x, nd: int = 3) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def _mean(xs) -> Optional[float]:
    xs = list(xs)
    return float(np.mean(xs)) if xs else None


def fit_png(cv: CV, cal: Calibration, path: Path, *, title: str, inputs=None) -> Path:
    """Two panels: the per-PC R² of the held-out predictions (PCs 1-64 of the pool) at the chosen alpha, and the
    residual Spearman against N for every alpha, the chosen alpha bold and the chosen N marked."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from assistant_axis.plot_metadata import png_metadata
    s = cv.summary[cv.alpha]
    r2 = np.array(s["per_pc_r2"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.6), constrained_layout=True,
                                 gridspec_kw={"width_ratios": [1.6, 1]})
    a1.bar(np.arange(1, len(r2) + 1), r2, color="#4a7ab5", width=0.8)
    a1.axhline(0, color="#444444", lw=0.8)
    a1.set_xlabel("principal component of the pool (1 = most variance)")
    a1.set_ylabel("held-out R²")
    a1.set_xlim(0.3, len(r2) + 0.7)
    a1.set_ylim(min(-0.05, float(r2.min()) - 0.05), 1.0)
    a1.set_title(f"Per-PC R² of the held-out predictions (alpha {cv.alpha:g})", fontsize=11)
    for x0, x1, label in ((9, 24, "9-24"), (25, 48, "25-48"), (49, 64, "49-64")):
        if len(r2) >= x1:
            m = float(r2[x0 - 1:x1].mean())
            a1.hlines(m, x0 - 0.4, x1 + 0.4, color="#c0392b", lw=1.6)
            a1.text((x0 + x1) / 2, m + 0.03, f"mean {m:.2f}", ha="center", fontsize=8, color="#c0392b",
                    bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 1.5})
    Ns = sorted(int(n) for n in s["rho_by_N"])
    alphas = sorted(cv.summary)
    cmap = plt.get_cmap("viridis")
    for j, alpha in enumerate(alphas):
        rho = [cv.summary[alpha]["rho_by_N"][str(n)] for n in Ns]
        chosen = alpha == cv.alpha
        a2.plot(Ns, rho, marker="o", ms=6 if chosen else 3.5, lw=2.6 if chosen else 1.0,
                color=cmap(0.1 + 0.8 * j / max(1, len(alphas) - 1)), alpha=1.0 if chosen else 0.75,
                label=f"alpha {alpha:g}" + (" (chosen)" if chosen else ""), zorder=4 if chosen else 2)
    best = cv.summary[cv.alpha]["rho_by_N"][str(cv.N)]
    a2.scatter([cv.N], [best], s=140, facecolors="none", edgecolors="#c0392b", lw=2, zorder=5,
               label=f"chosen N = {cv.N}")
    a2.set_xticks(Ns)
    a2.set_xlabel("N (top principal directions the residual is taken outside)")
    a2.set_ylabel("Spearman, predicted vs actual residual")
    a2.set_title("Residual rank agreement on held-out rows", fontsize=11)
    a2.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)
    return path


def fit_report(cv: CV, cal: Calibration, *, fit_id: str, pool_counts: Mapping, png_name: str = "fit_report.png",
               rel: str = DATA_REL) -> str:
    """``fit_report.md`` (gate 1): the pool, the per-PC table, the alpha table, the N curve and the chosen N, the
    kNN comparison, recovery by kind, the shrinkage and the two thresholds."""
    s = cv.summary[cv.alpha]
    r2 = s["per_pc_r2"]
    L = [f"# Persona-space fit `{fit_id}`", "",
         f"The ridge map from a `label: description` embedding (OpenAI text-embedding-3-large, cut to 20 words) to the "
         f"entity's persona vector (Qwen3-32B, slot 6, layer 25, centred on the corpus mean, soft shear L=3), fitted on "
         f"{cv.n_rows} entities ({pool_counts['n_train_traits']} traits, {pool_counts['n_train_roles']} roles) with a "
         f"role column, evaluated on {cv.cfg.n_folds} arrangement-grouped folds ({cv.n_groups} groups: a pair, "
         f"triangle or tetrahedron of traits, or an arrangement of roles, is held out whole).  Chosen: **alpha "
         f"{cv.alpha:g}, N = {cv.N}**.  The plot: [{png_name}](./{png_name}).  Terms: "
         f"[glossary](../../../../../reports/trait_gap_generation/glossary.md#persona-space-novelty).", "",
         "## The pool", "",
         f"{pool_counts['n']} vectors ({pool_counts['n_traits']} traits, {pool_counts['n_roles']} roles); "
         f"{pool_counts['n_with_file']} with a current file ({pool_counts['n_with_file_traits']} + "
         f"{pool_counts['n_with_file_roles']}; {pool_counts['n_renamed_traits']} + {pool_counts['n_renamed_roles']} "
         f"through `renamed_from`); {pool_counts['n_train']} train.  Orphans (no file; in the pool for the geometry, "
         f"never trained on or listed): {', '.join(f'`{x}`' for x in pool_counts['orphans']) or 'none'}.  "
         f"Sense-changed renames (the May vector is the old sense): "
         f"{', '.join(f'`{x}`' for x in pool_counts['sense_changed']) or 'none'}.", "",
         "Spectrum: K for 50 / 80 / 90 / 95 / 99% of the variance = "
         f"{cv.spectrum['k50']} / {cv.spectrum['k80']} / {cv.spectrum['k90']} / {cv.spectrum['k95']} / "
         f"{cv.spectrum['k99']}; top 12 carry {cv.spectrum['top12_share']:.1%}; log-log slope over 1-64 "
         f"{cv.spectrum['loglog_slope_1_64']}; λ1/λ12 = {cv.spectrum['lambda1_over_12']}, λ1/λ32 = "
         f"{cv.spectrum['lambda1_over_32']}.", "",
         "## Alpha", "",
         "| alpha | median cos | traits | roles | top-1 | top-5 | best residual Spearman | pred / actual residual_24 |",
         "|---|---|---|---|---|---|---|---|"]
    for a in sorted(cv.summary):
        x = cv.summary[a]
        best = max(v for v in x["rho_by_N"].values() if v is not None)
        mark = " **(chosen)**" if a == cv.alpha else ""
        L.append(f"| {a:g}{mark} | {x['median_cos']:.3f} | {x['median_cos_traits']:.3f} | {_f(x['median_cos_roles'])} | "
                 f"{x['top1']:.3f} | {x['top5']:.3f} | {best:.3f} | {x['residual_pred_median_by_N'].get('24', 0):.3f} / "
                 f"{x['residual_true_median_by_N'].get('24', 0):.3f} |")
    L += ["", f"Rule: {cv.cfg.alpha_tie_window} tie window on the median cosine, the smaller alpha wins.", "",
          "## Recovery by kind (chosen alpha)", "",
          "| kind | median cos | top-1 | top-5 |", "|---|---|---|---|",
          f"| traits | {s['median_cos_traits']:.3f} | {s['top1_traits']:.3f} | {s['top5_traits']:.3f} |",
          f"| roles | {_f(s['median_cos_roles'])} | {_f(s['top1_roles'])} | {_f(s['top5_roles'])} |",
          f"| all | {s['median_cos']:.3f} | {s['top1']:.3f} | {s['top5']:.3f} |", "",
          f"Recovery: the held-out prediction's nearest among the {cv.n_rows} actual vectors is its own (top-1) or "
          f"among the five nearest (top-5).  For held-out traits, the nearest other entity is a role "
          f"{s['nn_is_role_share_traits']:.1%} of the time.", "",
          "## Per-PC R² (chosen alpha; the pool's principal components)", "",
          "| PC | " + " | ".join(str(i) for i in range(1, 13)) + " |", "|---|" + "---|" * 12,
          "| R² | " + " | ".join(f"{x:.2f}" for x in r2[:12]) + " |", "",
          "| PC | " + " | ".join(str(i) for i in range(13, 25)) + " |", "|---|" + "---|" * 12,
          "| R² | " + " | ".join(f"{x:.2f}" for x in r2[12:24]) + " |", "",
          f"Means: PCs 9-24 {_f(_mean(r2[8:24]), 2)}, 25-48 {_f(_mean(r2[24:48]), 2)}, 49-64 {_f(_mean(r2[48:64]), 2)}.  "
          "A direction the text predicts badly is one this text-only scorer cannot see.", "",
          "## The N sweep (chosen alpha)", "",
          "| N | Spearman, all | traits | predicted median | actual median |", "|---|---|---|---|---|"]
    for n in sorted(int(k) for k in s["rho_by_N"]):
        mark = " **(chosen)**" if n == cv.N else ""
        L.append(f"| {n}{mark} | {s['rho_by_N'][str(n)]:.3f} | {_f(s['rho_by_N_traits'][str(n)])} | "
                 f"{s['residual_pred_median_by_N'][str(n)]:.3f} | {s['residual_true_median_by_N'][str(n)]:.3f} |")
    L += ["", f"Rule: the largest Spearman; Ns within {cv.cfg.n_tie_window} of it tie, and the one nearest "
              f"{cv.cfg.prefer_N} wins.", "",
          "## kNN baseline", "",
          "The cosine-weighted mean of the k nearest training vectors by embedding cosine, against the ridge's "
          f"{s['median_cos']:.3f}:", "", "| k | " + " | ".join(cv.knn_cos_by_k) + " |",
          "|---|" + "---|" * len(cv.knn_cos_by_k),
          "| median cos | " + " | ".join(f"{v:.3f}" for v in cv.knn_cos_by_k.values()) + " |", ""]
    if cv.alt:
        a = cv.alt.get(cv.alpha)
        if a:
            L += ["## The gloss side", "",
                  f"{a['n']} trained traits also have an M1 gloss of their label ({a['name']}).  Predicted from "
                  f"`label: M1 gloss` with the fold model that held them out, their median cosine to the actual vector "
                  f"is {a['median_cos_alt']:.3f}, against {a['median_cos_desc_same_rows']:.3f} from their "
                  f"descriptions: a candidate (gloss-only) lands about as well as a trait described by a gloss.", ""]
    L += ["## Calibration and the thresholds (gate 1)", "",
          f"Shrinkage: the held-out predicted `residual_{cal.N}` has median {cal.residual_pred_quantiles[10]:.3f} against "
          f"the actual {cal.residual_true_quantiles[10]:.3f}, so a candidate's residual is read as its percentile "
          f"among the held-out predictions (`residual_pct`).", "",
          f"- `dup_threshold` = **{cal.dup_threshold:.3f}** (the median held-out cosine between a prediction and its "
          f"own vector).  The flag's base rate: a held-out existing entity's prediction is at or above it to "
          f"*another* entity {_f(cal.dup_base_rate and cal.dup_base_rate * 100, 1)}% of the time (the median "
          f"nearest-other cosine is {cal.nn_cos_pred_quantiles[10]:.3f}, p90 {cal.nn_cos_pred_quantiles[18]:.3f}); "
          f"a candidate that is a genuinely new trait can expect about that rate of duplicate-like flags.",
          f"- `novel_pct` = **{cal.novel_pct:.2f}**.",
          f"- `cover_questioned` cosine: {cal.cover_questioned_cos:.3f} (the 10th percentile of held-out "
          f"self-cosines); `novel_vs_covered` percentile {cal.novel_vs_covered_pct:.2f}.",
          f"- Set by: {cal.thresholds_set_by}.", "",
          "| percentile | " + " | ".join(f"{int(x * 100)}" for x in cal.levels[::2]) + " |",
          "|---|" + "---|" * len(cal.levels[::2]),
          "| predicted residual | " + " | ".join(f"{x:.3f}" for x in cal.residual_pred_quantiles[::2]) + " |",
          "| actual residual | " + " | ".join(f"{x:.3f}" for x in cal.residual_true_quantiles[::2]) + " |",
          "| self cosine | " + " | ".join(f"{x:.3f}" for x in cal.self_cos_quantiles[::2]) + " |", ""]
    return "\n".join(L)


def _row_line(r: Mapping, rel: str) -> str:
    near = ", ".join(entity_link(a, rel, cos=c) for a, c in r["nearest"])
    m3 = r.get("m3_decision") or "undecided"
    if r.get("m3_covered_by"):
        m3 += f" by {entity_link(r['m3_covered_by'] + '|T', rel)}"
    return (f"| {r['label']} (`{r['key']}`) | {', '.join(r.get('generators') or [])} | {r['residual_pct']:.2f} | "
            f"{r['residual']:.3f} | {r['flag']} | {near} | {m3} |")


def score_report(rows: Sequence[Mapping], agreement: Mapping, counts: Mapping, cal: Calibration, *, batch_id: str,
                 n_top: int = 30, readings: Optional[Mapping] = None, rel: str = DATA_REL) -> str:
    """``score_report.md`` (gate 2): the top and bottom ``n_top`` by ``residual_pct`` with their nearest names, the
    agreement table, the flags and disagreements by generator."""
    by = sorted(rows, key=lambda r: (-r["residual_pct"], r["key"]))
    head = ["| candidate | generators | residual pct | residual | flag | nearest (cos) | M3 |", "|---|---|---|---|---|---|---|"]
    a = agreement
    L = [f"# Persona-space scores, batch `{batch_id}`", "",
         f"{len(rows)} candidates scored with fit `{cal.fit_id}` (N = {cal.N}, alpha {cal.alpha:g}).  Flags: "
         f"{a['flags']}.  The disagreements: [disagreements.md](./disagreements.md); the rows: "
         f"[scores.jsonl](./scores.jsonl).  Terms: "
         f"[glossary](../../../../../reports/trait_gap_generation/glossary.md#persona-space-novelty).", "",
         "## Agreement with M3", "",
         "| figure | value |", "|---|---|",
         f"| AUC of the nearest-trait cosine, M3 covered against new | {_f(a['auc_nn_cos_covered_vs_new'])} |",
         f"| Spearman, nearest-trait cosine against M3's first text cosine | {_f(a['spearman_nn_cos_vs_m3_cosine'])} |",
         f"| M3's covering trait is the persona-nearest trait | {_f(a['covered_by_is_nearest'])} "
         f"(of {a['n_covered_by_with_vector']}) |",
         f"| ... among the three nearest traits | {_f(a['covered_by_in_top3'])} |",
         f"| M3 decisions | {a['m3']} |", "",
         "## Disagreements", "",
         "| kind | met the rule | listed |", "|---|---|---|"]
    for k in ("dup_vs_new", "cover_questioned", "novel_vs_covered"):
        c = counts.get(k, {})
        L.append(f"| `{k}` | {c.get('met_rule', 0)} | {c.get('listed', 0)} |")
    if readings:
        at = sum(1 for r in readings.values() if r.get("at_cut_off"))
        L += ["", f"Overlap readings (decision 2b): {len(readings)} pairs read, {at} at or above the candidate's "
                  f"cut-off (M3's decision unchanged)."]
    L += ["", "## By generator", "", "| generator | n | duplicate-like | novel-like | AUC | mean residual pct | "
                                      "disagreements |", "|---|---|---|---|---|---|---|"]
    for g, v in sorted(a["by_generator"].items()):
        L.append(f"| {g} | {v['n']} | {v['flags'].get('duplicate_like', 0)} | {v['flags'].get('novel_like', 0)} | "
                 f"{_f(v['auc'])} | {_f(v['mean_residual_pct'], 2)} | {v.get('disagreements') or {}} |")
    L += ["", f"## Top {n_top} by residual percentile (persona space's most novel directions)", ""] + head
    L += [_row_line(r, rel) for r in by[:n_top]]
    L += ["", f"## Bottom {n_top} by residual percentile", ""] + head
    L += [_row_line(r, rel) for r in by[::-1][:n_top]]
    return "\n".join(L) + "\n"


def prospective_report(rows: Sequence[Mapping], *, fit_id: str, compare_cmd: str,
                       comparison: Optional[Mapping] = None, rel: str = DATA_REL) -> str:
    """The prospective set's report: counts, flags, the most and least novel predictions, and the comparison once
    run (with the command to run it)."""
    from collections import Counter
    k = Counter(r["kind"] for r in rows)
    f = Counter(r["flag"] for r in rows)
    L = [f"# Prospective predictions, fit `{fit_id}`", "",
         f"{len(rows)} entities with a file and no training vector ({k.get('traits', 0)} traits, {k.get('roles', 0)} "
         f"roles), scored with the May fit: flags {dict(f)}.  Rows: [predicted.jsonl](./predicted.jsonl).", "",
         "After the next extraction, compare them with their actual vectors:", "", "```", compare_cmd, "```", ""]
    if comparison:
        c = comparison
        L += ["## Comparison", "", "| figure | value |", "|---|---|",
              f"| entities with a new vector | {c['n_with_vector']} of {c['n']} |",
              f"| rank Spearman, predicted against actual residual (N = {c['N']}) | {_f(c['rho_residual_rank'])} |",
              f"| mean Jaccard of the three nearest | {_f(c['nearest3_jaccard_mean'])} |",
              f"| top-1 / top-3 name hit | {_f(c['top1_name_hit'])} / {_f(c['top3_name_hit'])} |",
              f"| AUC, predicted nearest cosine for actual >= 0.7 | {_f(c['auc_dup'])} ({c['n_dup_actual']} such) |", ""]
        for name, v in c["named_pairs"].items():
            L.append(f"- {name}: actual {_f(v['actual_cos'])}, predicted {_f(v['predicted_cos'])}")
        L.append("")
    by = sorted(rows, key=lambda r: (-r["residual_pct"], r["id"]))
    head = ["| entity | residual pct | flag | nearest (cos) |", "|---|---|---|---|"]
    line = (lambda r: f"| {entity_link(r['id'], rel)} | {r['residual_pct']:.2f} | {r['flag']} | "
            f"{', '.join(entity_link(a, rel, cos=c) for a, c in r['nearest'])} |")
    L += ["## Top 20 by residual percentile", ""] + head + [line(r) for r in by[:20]]
    L += ["", "## Bottom 20", ""] + head + [line(r) for r in by[::-1][:20]]
    return "\n".join(L) + "\n"
