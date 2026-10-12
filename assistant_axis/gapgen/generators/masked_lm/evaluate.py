"""The generator's free measures and a wave's paid-step readout (plan sections 5, 6 and 10, ``evaluate.py``).

Free (no call; ``evaluate``):

* :func:`recovery_curves`: recall@k of the corpus's labels and the seed queue's (the generator never sees our
  list, so nothing is hidden) against the union cutoff, per ranking (the union, each pass of each model, the
  wordfreq baseline) and per label class (``single`` / ``subword`` / ``multiword`` under the primary tokenizer).
  A label is recovered when its stem is among the ranking's first k stems.
* :func:`frequency_ranking` / :func:`frequency_baseline`: the same universe Variant B scores (OEWN adjectives and
  person nouns) ranked by Zipf alone.  The frames earn their keep only by beating it (plan 04 section 6).
* :func:`frame_ablation`: the single-mask pass's recall with each subject, or each register, removed.
* :func:`hhh_probe`: per frame, the ranks of the nine probe labels; the frame families whose frames put all three
  HHH words (helpful, harmless, honest) in their top 200 (Roger's question, plan 04 section 9.1).
* :func:`contrast_auc`: the contrast score's AUC on 100 corpus traits against 100 states and physical words
  (target 0.85: report and decide, not a gate).
* :func:`census_payload` and :func:`.wordlist.universe_coverage`: the tokenizer census; the corpus labels OEWN's
  universe lacks (what bounds Variant B).

After M1 and M3 (``report --run-id``): :func:`evaluate_run` reads the registry rows of a run and the M1 / M3
batch directories: verdicts and tags by Zipf band, pass and token class; the measured M1 pass rate (replacing
the assumed 0.88) and kept share (M3 ``new`` or ``grey`` over submitted, replacing the assumed 0.5 the wave is
sized by); polysemy; covered / new / grey; cost from the ``usage.json`` files, per model, the generator's own at
zero; useful candidates per dollar; the projected full-wave cost.
"""
from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name

from .frames import HHH_LABELS, PROBE_LABELS

CUTOFFS = (1000, 2000, 5000, 10000, 20000)
PROBE_TOP = 200
AUC_TARGET = 0.85
_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")
_MULTI_RE = re.compile(r"[\s\-]")

#: The contrast check's negatives (plan 04 section 6): 50 transient states and 50 physical descriptions,
#: hand-picked; none is a corpus or seed-queue label (checked 2026-10-12: the corpus's physical track holds tall,
#: short, muscular, young, athletic and others, so those are not negatives; ``test_gapgen_mlm_evaluate.py``).
CONTRAST_STATES = tuple("""
tired hungry thirsty sleepy busy sick ill exhausted bored drunk sober late early awake asleep injured sweaty
nauseous dizzy feverish hungover jetlagged sunburned soaked cold warm hot sore stuffy pregnant unemployed
absent present lost stranded relieved startled surprised shocked overwhelmed distracted preoccupied rushed delayed
famished parched drowsy groggy bloated winded
""".split())
CONTRAST_PHYSICAL = tuple("""
blonde brunette bald freckled slender skinny plump overweight petite lanky stocky bearded tanned pale curly
wrinkled handsome pretty beautiful gorgeous right-handed toothless pimply chubby broad-shouldered long-legged
red-haired grey-haired hairy tattooed pierced wiry gangly svelte potbellied bowlegged knock-kneed hunchbacked
dimpled rosy-cheeked square-jawed doe-eyed flat-footed big-boned pockmarked swarthy gaunt rotund clean-shaven
gap-toothed
""".split())
CONTRAST_NEGATIVES = CONTRAST_STATES + CONTRAST_PHYSICAL


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


def bare_label(label: str) -> str:
    """A label with a standard's suffix stripped ("openness (Big Five)" -> "openness")."""
    return _SUFFIX_RE.sub("", str(label)).strip()


def corpus_labels(data_dir: Path) -> list[str]:
    """Bare labels of every trait file (``positive_label``, else the stem with spaces), in stem order."""
    d = Path(data_dir) / "traits" / "instructions"
    out = []
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append(bare_label(doc.get("positive_label") or p.stem.replace("_", " ")))
    return list(dict.fromkeys(out))


def queue_labels(queue_path: Path) -> list[str]:
    """Bare labels of the seed queue's trait entries (dropped ones left out, as the censuses do)."""
    from ..censuses.corpus import DROPPED_QUEUE_STATUSES
    p = Path(queue_path)
    if not p.exists():
        return []
    out = []
    for e in json.loads(p.read_text(encoding="utf-8")).get("entries", []):
        if e.get("status") in DROPPED_QUEUE_STATUSES or e.get("entity_type") not in (None, "trait"):
            continue
        lab = e.get("label") or (e.get("stem") or "").replace("_", " ")
        if lab:
            out.append(bare_label(lab))
    return list(dict.fromkeys(out))


def classify(labels: Iterable[str], tokenizer=None) -> dict[str, str]:
    """``{label: single | subword | multiword}``; without a tokenizer a one-word label counts as ``single``."""
    from .models import token_class
    out = {}
    for lab in labels:
        if tokenizer is not None:
            out[lab] = token_class(lab, tokenizer)[1]
        else:
            out[lab] = "multiword" if _MULTI_RE.search(lab) else "single"
    return out


def _stem(s: str) -> str:
    return normalize_to_file_name(s)


def ranking_from_table(table: Sequence[Mapping]) -> list[str]:
    return [r["stem"] for r in sorted(table, key=lambda r: r["union_rank"]) if r.get("stem")]


def ranking_from_pass(aggs: Mapping) -> list[str]:
    """A pass's own ranking: every word it scored, best log-probability first (Variant B: its whole universe)."""
    items = []
    for w, a in aggs.items():
        a = a.as_dict() if hasattr(a, "as_dict") else a
        items.append((-float(a["best_logprob"]), a.get("surface") or w))
    out, seen = [], set()
    for _, s in sorted(items):
        st = _stem(s)
        if st and st not in seen:
            seen.add(st)
            out.append(st)
    return out


def frequency_ranking(universe: Sequence[str], zipf: Callable[[str], float]) -> list[str]:
    """The universe by Zipf descending (ties by word): the wordfreq baseline."""
    scored = sorted(((-float(zipf(w)), w.lower(), w) for w in universe))
    out, seen = [], set()
    for _, _, w in scored:
        st = _stem(w)
        if st and st not in seen:
            seen.add(st)
            out.append(st)
    return out


def recall_at(ranking: Sequence[str], labels: Sequence[str], cutoffs: Sequence[int]) -> dict:
    pos = {}
    for i, st in enumerate(ranking):
        pos.setdefault(st, i)
    stems = [_stem(lab) for lab in labels]
    out = {"n": len(stems), "n_ranked": len(ranking)}
    for k in cutoffs:
        out[f"recall@{k}"] = _frac(sum(1 for s in stems if pos.get(s, 1 << 60) < k), len(stems))
    out["found_anywhere"] = _frac(sum(1 for s in stems if s in pos), len(stems))
    return out


def recovery_curves(table: Sequence[Mapping], label_sets: Mapping[str, Sequence[str]],
                    cutoffs: Sequence[int] = CUTOFFS, *, rankings: Optional[Mapping[str, Sequence[str]]] = None,
                    classes: Optional[Mapping[str, str]] = None) -> dict:
    """``{label set: {ranking: {class: {recall@k ...}}}}``; ``class`` is ``all``, ``single``, ``subword``,
    ``multiword``.  The table's union order is the ranking ``union``; ``rankings`` adds others (passes, the
    baseline)."""
    ranks = {"union": ranking_from_table(table)}
    ranks.update(dict(rankings or {}))
    out: dict = {}
    for set_name, labels in label_sets.items():
        cls = {lab: (classes or {}).get(lab) or ("multiword" if _MULTI_RE.search(lab) else "single") for lab in labels}
        groups = {"all": list(labels)}
        for k in ("single", "subword", "multiword"):
            groups[k] = [lab for lab in labels if cls[lab] == k]
        out[set_name] = {name: {g: recall_at(r, labs, cutoffs) for g, labs in groups.items()}
                         for name, r in ranks.items()}
    return out


def frequency_baseline(label_sets: Mapping[str, Sequence[str]], cutoffs: Sequence[int] = CUTOFFS, *,
                       universe: Sequence[str], zipf: Callable[[str], float],
                       classes: Optional[Mapping[str, str]] = None) -> dict:
    """Recall of the label sets from the universe ranked by Zipf alone."""
    r = frequency_ranking(universe, zipf)
    return recovery_curves([], label_sets, cutoffs, rankings={"baseline_wordfreq": r}, classes=classes)


def frame_ablation(aggs: Mapping, factor: str, *, labels: Sequence[str], cutoffs: Sequence[int] = (1000, 5000)
                   ) -> dict:
    """The single-mask pass's recall of ``labels`` with each value of ``factor`` (``subject`` or ``register``)
    removed: each word's best log-probability recomputed over the other values."""
    field = {"subject": "by_subject_best", "register": "by_register_best"}[factor]
    rows = [(a.as_dict() if hasattr(a, "as_dict") else a) for a in aggs.values()]
    values = sorted({v for r in rows for v in (r.get(field) or {})})

    def ranking(drop: Optional[str]) -> list[str]:
        scored = []
        for r in rows:
            vals = [x for k, x in (r.get(field) or {}).items() if k != drop]
            if vals:
                scored.append((-max(vals), r.get("surface") or r["word"]))
        return [_stem(s) for _, s in sorted(scored)]
    base = recall_at(ranking(None), labels, cutoffs)
    out = {"_all": base}
    for v in values:
        rec = recall_at(ranking(v), labels, cutoffs)
        rec["delta"] = {f"recall@{k}": round((rec[f"recall@{k}"] or 0) - (base[f"recall@{k}"] or 0), 4)
                        for k in cutoffs}
        out[v] = rec
    return out


def hhh_probe(pass_metas: Iterable[Mapping], *, top: int = PROBE_TOP, hhh: Sequence[str] = HHH_LABELS,
              labels: Sequence[str] = PROBE_LABELS) -> dict:
    """Per frame, the probe labels' ranks; the families (probe families and, for the generation frames, the
    registers) whose frames put every HHH word in a top ``top``; the frames that do it alone."""
    frames: dict[str, dict] = {}
    for meta in pass_metas:
        for fid, f in (meta.get("frames") or {}).items():
            frames[fid] = {"family": f.get("family"), "kind": f.get("kind"), "register": f.get("register"),
                           "pass": meta.get("pass"),
                           "ranks": {lab: (f.get("labels") or {}).get(lab, {}).get("rank") for lab in labels},
                           "via": {lab: (f.get("labels") or {}).get(lab, {}).get("via") for lab in labels}}
    fams: dict[str, dict] = {}
    for fid, f in sorted(frames.items()):
        fam = fams.setdefault(f["family"] or "?", {"frames": [], "best_ranks": {}})
        fam["frames"].append(fid)
        for lab, r in f["ranks"].items():
            if r is not None:
                cur = fam["best_ranks"].get(lab)
                fam["best_ranks"][lab] = r if cur is None else min(cur, r)
    for fam in fams.values():
        fam["all_hhh_in_top"] = all((fam["best_ranks"].get(h) or 1 << 30) <= top for h in hhh)
    winning_frames = sorted(fid for fid, f in frames.items()
                            if all((f["ranks"].get(h) or 1 << 30) <= top for h in hhh))
    best = {}
    for lab in labels:
        rs = [(f["ranks"][lab], fid) for fid, f in frames.items() if f["ranks"].get(lab) is not None]
        best[lab] = min(rs)[0] if rs else None
    best_frame = {lab: (min((f["ranks"][lab], fid) for fid, f in frames.items() if f["ranks"].get(lab) is not None)[1]
                        if best[lab] is not None else None) for lab in labels}
    return {"top": top, "hhh": list(hhh), "labels": list(labels), "frames": frames, "families": fams,
            "winning_families": sorted(k for k, v in fams.items() if v["all_hhh_in_top"]),
            "winning_frames": winning_frames, "ranks": best, "best_frame": best_frame}


def contrast_auc(contrasts: Mapping[str, object], pos_labels: Sequence[str], neg_labels: Sequence[str]) -> dict:
    """AUC of ``trait_contrast`` separating ``pos_labels`` (traits) from ``neg_labels`` (states, physical): the
    probability that a random trait scores above a random negative (ties count half)."""
    def val(w):
        c = contrasts.get(w)
        if c is None:
            return None
        return float(c.trait_contrast if hasattr(c, "trait_contrast") else c["trait_contrast"])
    pos = [v for v in (val(w) for w in pos_labels) if v is not None]
    neg = [v for v in (val(w) for w in neg_labels) if v is not None]
    if not pos or not neg:
        return {"auc": None, "n_pos": len(pos), "n_neg": len(neg), "target": AUC_TARGET}
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    auc = wins / (len(pos) * len(neg))
    return {"auc": round(auc, 4), "n_pos": len(pos), "n_neg": len(neg), "target": AUC_TARGET,
            "meets_target": auc >= AUC_TARGET,
            "missing": sorted(w for w in list(pos_labels) + list(neg_labels) if val(w) is None)}


def contrast_positives(labels: Sequence[str], n: int = 100, seed: int = 0, *, exclude: Iterable[str] = ()
                       ) -> list[str]:
    """``n`` one-word corpus labels drawn with a fixed seed (the contrast check's positives), leaving out
    ``exclude`` (the corpus's physical and demographic track: :func:`demographic_labels`), since the score is meant
    to separate dispositions from states and physical descriptions."""
    ex = set(exclude) | set(CONTRAST_NEGATIVES)
    pool = sorted(lab for lab in labels if not _MULTI_RE.search(lab) and lab not in ex)
    return sorted(random.Random(seed).sample(pool, min(n, len(pool))))


def demographic_labels(labels: Sequence[str], regions_path: Optional[Path] = None) -> list[str]:
    """The labels whose corpus trait is in the ``identity_demographic`` region (``corpus_regions.json``: the
    physical track and memberships), left out of the contrast check's positives."""
    from assistant_axis.gapgen.paths import CORPUS_REGIONS_PATH
    p = Path(regions_path or CORPUS_REGIONS_PATH)
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    d = d.get("result", d) if isinstance(d, dict) else d
    rows = d.get("regions", d) if isinstance(d, dict) else {}
    demo = {k for k, v in rows.items() if isinstance(v, dict) and v.get("region") == "identity_demographic"}
    return [lab for lab in labels if _stem(lab) in demo]


def census_payload(rows_by_set: Mapping[str, Sequence]) -> dict:
    from .models import census_summary
    return {name: census_summary(rows) for name, rows in rows_by_set.items()}


def throughput(pass_metas: Iterable[Mapping]) -> dict:
    out = {}
    for m in pass_metas:
        out[f"{m.get('pass')}:{m.get('model_key')}"] = {
            "device": m.get("device"), "seconds": m.get("seconds"), "n_forward": m.get("n_forward"),
            "forward_per_second": m.get("forward_per_second"),
            "instances_per_minute": m.get("instances_per_minute"), "n_instances": m.get("n_instances"),
            "words_per_minute": round(60.0 * m["n_words"] / m["seconds"], 1)
            if m.get("n_words") and m.get("seconds") else None}
    return out


# ---------------------------------------------------------------------------- after M1 / M3

def cost_summary(usage_paths: Iterable[Path]) -> dict:
    """Sum ``usage.json`` files per model (cost and tokens)."""
    per_model: dict[str, dict] = {}
    files = []
    for p in usage_paths:
        p = Path(p)
        if not p.exists():
            continue
        files.append(str(p))
        d = json.loads(p.read_text(encoding="utf-8"))
        for m, u in (d.get("per_model") or {}).items():
            cur = per_model.setdefault(m, {"cost_usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "n_calls": 0})
            cur["cost_usd"] = round(cur["cost_usd"] + float(u.get("cost_usd") or 0.0), 6)
            for k in ("prompt_tokens", "completion_tokens", "n_calls"):
                cur[k] += int(u.get(k) or 0)
    return {"files": files, "per_model": dict(sorted(per_model.items())),
            "total_usd": round(sum(v["cost_usd"] for v in per_model.values()), 6)}


def run_rows(registry_rows: Mapping[str, Mapping], run_id: str, generator: str = "masked_lm") -> list[Mapping]:
    return [r for _, r in sorted(registry_rows.items())
            if any(s.get("generator") == generator and s.get("run_id") == run_id for s in r.get("sources") or [])]


def _source(row: Mapping, run_id: str) -> Mapping:
    for s in row.get("sources") or []:
        if s.get("generator") == "masked_lm" and s.get("run_id") == run_id:
            return s
    return {}


def _m1(rows: Sequence[Mapping]) -> dict:
    filt = [r for r in rows if r.get("filter")]
    traits = [r for r in filt if r["filter"].get("verdict") == "trait"]
    return {"n_rows": len(rows), "n_filtered": len(filt), "n_trait": len(traits),
            "pass_rate": _frac(len(traits), len(filt)),
            "verdict": dict(sorted(Counter(str(r["filter"].get("verdict")) for r in filt).items())),
            "outcome": dict(sorted(Counter(str(r["filter"].get("outcome")) for r in filt).items())),
            "tags": dict(sorted(Counter(t for r in filt for t in (r["filter"].get("tags") or [])).items())),
            "polysemy_rate": _frac(sum(1 for r in filt if r["filter"].get("polysemy")), len(filt))}


def _m3(rows: Sequence[Mapping]) -> dict:
    nov = [r for r in rows if r.get("novelty")]
    dec = Counter(str(r["novelty"].get("decision")) for r in nov)
    return {"n_scored": len(nov), "decision": dict(sorted(dec.items())),
            "new_rate": _frac(dec.get("new", 0), len(nov)),
            "kept": dec.get("new", 0) + dec.get("grey", 0),
            "pair_completions": sum(1 for r in nov if r["novelty"].get("pair_completion_for")),
            "new_stems": sorted(r["stem"] for r in nov if r["novelty"].get("decision") == "new"),
            "grey_stems": sorted(r["stem"] for r in nov if r["novelty"].get("decision") == "grey")}


def evaluate_run(run_id: str, *, run_dir: Path, table: Sequence[Mapping], registry_rows: Mapping[str, Mapping],
                 filter_dir: Path, novelty_dir: Path) -> dict:
    """A submitted run's numbers once M1 and M3 have run (see the module docstring)."""
    from ..censuses.ingest import zipf_band
    from .submit import KEPT_SHARE_ASSUMED, KEPT_TARGET_DEFAULT, M1_PASS_RATE_ASSUMED, estimate_downstream_usd
    cands = [json.loads(x) for x in (run_dir / "candidates.jsonl").read_text(encoding="utf-8").splitlines()
             if x.strip()] if (run_dir / "candidates.jsonl").exists() else []
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8")) if (run_dir / "run.json").exists() else {}
    rows = run_rows(registry_rows, run_id)
    by_stem = {r["stem"]: r for r in table if r.get("stem")}
    strata: dict[str, dict] = {}
    for name, keyf in (("zipf_band", lambda r: zipf_band((by_stem.get(r["stem"]) or {}).get("zipf"))),
                       ("best_pass", lambda r: str((by_stem.get(r["stem"]) or {}).get("best_pass"))),
                       ("token_class", lambda r: str((by_stem.get(r["stem"]) or {}).get("token_class")))):
        groups: dict[str, list] = {}
        for r in rows:
            groups.setdefault(keyf(r), []).append(r)
        strata[name] = {k: {"n": len(v), "m1": _m1(v), "m3": _m3(v)} for k, v in sorted(groups.items())}
    m1, m3 = _m1(rows), _m3(rows)
    cost = cost_summary([run_dir / "usage.json", Path(filter_dir) / "usage.json", Path(novelty_dir) / "usage.json"])
    useful = m3["decision"].get("new", 0) + m3["pair_completions"]
    kept_share = _frac(m3["kept"], len(rows)) if m3["n_scored"] else None
    pass_rate = m1["pass_rate"]
    projection = None
    if kept_share:
        n_single = math.ceil(KEPT_TARGET_DEFAULT / kept_share)
        projection = {"kept_target": KEPT_TARGET_DEFAULT, "kept_share": kept_share, "n_single_words": n_single,
                      "estimate_batches": estimate_downstream_usd(n_single, transport="batches",
                                                                  pass_rate=pass_rate or M1_PASS_RATE_ASSUMED
                                                                  ).total_usd,
                      "note": "single words only; the wave adds its multiword and subword rows at the same rates"}
    return {"run_id": run_id, "generator": "masked_lm", "args": run.get("args"), "n_candidates": len(cands),
            "n_registry_rows": len(rows), "m1": m1, "m3": m3, "strata": strata,
            "measured_pass_rate": pass_rate, "assumed_pass_rate": M1_PASS_RATE_ASSUMED,
            "measured_kept_share": kept_share, "assumed_kept_share": KEPT_SHARE_ASSUMED,
            "cost": cost, "cost_per_candidate": _frac(cost["total_usd"], len(cands)), "useful": useful,
            "useful_per_dollar": round(useful / cost["total_usd"], 1) if cost["total_usd"] else None,
            "projection": projection,
            "generator_usage": cost_summary([run_dir / "usage.json"])}


# ---------------------------------------------------------------------------- the evaluation payload

def build_evaluation(*, table: Sequence[Mapping], passes: Mapping[str, object], label_sets: Mapping[str, Sequence[str]],
                     classes: Optional[Mapping[str, str]] = None, cutoffs: Sequence[int] = CUTOFFS,
                     universe: Optional[Sequence[str]] = None, zipf: Optional[Callable[[str], float]] = None,
                     contrasts: Optional[Mapping[str, object]] = None, corpus_for_auc: Sequence[str] = (),
                     auc_exclude: Sequence[str] = (),
                     census: Optional[Mapping] = None, readout_frames: Sequence[str] = ("disp_nature",
                                                                                       "disp_habitually",
                                                                                       "noun_avowed"),
                     title: Optional[str] = None, note: Optional[str] = None) -> dict:
    """``evaluation.json``'s payload (plan section 6; the plan's flat ``recovery`` names, the per-ranking,
    per-class detail in ``recovery_detail``)."""
    from .table import table_counts
    from .wordlist import universe_coverage
    rankings = {k: ranking_from_pass(p.aggs) for k, p in sorted(passes.items())}
    if universe is not None and zipf is not None:
        rankings["baseline_wordfreq"] = frequency_ranking(universe, zipf)
    detail = recovery_curves(table, label_sets, cutoffs, rankings=rankings, classes=classes)
    corp = detail.get("corpus") or {}

    def merged(rec_by_class: Mapping, kinds: Sequence[str]) -> dict:
        n = sum((rec_by_class.get(k) or {}).get("n", 0) for k in kinds)
        out = {"n": n}
        for c in list(cutoffs) + ["anywhere"]:
            key = "found_anywhere" if c == "anywhere" else f"recall@{c}"
            hits = sum(((rec_by_class.get(k) or {}).get(key) or 0) * (rec_by_class.get(k) or {}).get("n", 0)
                       for k in kinds)
            out[key] = _frac(round(hits), n)
        return out
    summary = {}
    if corp:
        summary["corpus_single"] = merged(corp["union"], ("single", "subword"))
        summary["corpus_multi"] = merged(corp["union"], ("multiword",))
    if "queue" in detail:
        summary["queue"] = detail["queue"]["union"]["all"]
    if "baseline_wordfreq" in rankings:
        b = {}
        if corp:
            b["corpus_single"] = merged(corp["baseline_wordfreq"], ("single", "subword"))
            b["corpus_multi"] = merged(corp["baseline_wordfreq"], ("multiword",))
        if "queue" in detail:
            b["queue"] = detail["queue"]["baseline_wordfreq"]["all"]
        summary["baseline_wordfreq"] = b
    multi_labels = [lab for lab in label_sets.get("corpus", []) if _MULTI_RE.search(lab)]
    mc = {k: recall_at(r, multi_labels, cutoffs) for k, r in rankings.items()
          if k.split(":")[0] in ("variant_b", "multiword", "subword", "baseline_wordfreq")} if multi_labels else {}
    single = next((p for k, p in sorted(passes.items()) if k.startswith("single:")), None)
    one_word = [lab for lab in label_sets.get("corpus", []) if not _MULTI_RE.search(lab)]
    ablation = {f: frame_ablation(single.aggs, f, labels=one_word) for f in ("subject", "register")} \
        if single is not None and one_word else {}
    metas = [p.meta for p in passes.values()]
    probe = hhh_probe([m for m in metas if m.get("frames")])
    con = None
    if contrasts:
        con = contrast_auc(contrasts, contrast_positives(corpus_for_auc, exclude=auc_exclude), CONTRAST_NEGATIVES)
    tops = {}
    for fid in readout_frames:
        for m in metas:
            f = (m.get("frames") or {}).get(fid)
            if f:
                tops[fid] = f["top"][:50]
                break
    tc = table_counts(table)
    return {"title": title, "note": note, "cutoffs": list(cutoffs),
            "models": sorted({k.split(":", 1)[1] for k in passes}), "passes": sorted(passes),
            "n_union": tc["n_union"], "n_eligible": tc["n_eligible"], "table_counts": tc,
            "recovery": summary, "recovery_detail": detail, "multiword_comparison": mc,
            "frame_ablation": ablation, "hhh_probe": probe,
            "contrast_auc": (con or {}).get("auc"), "contrast": con,
            "census": dict(census or {}),
            "coverage": universe_coverage(label_sets.get("corpus", []), universe) if universe is not None else None,
            "throughput": throughput(metas), "frames_top50": tops}


def plot_recovery_curves(ev: Mapping, path: Path, *, inputs: Optional[list] = None,
                         label_set: str = "corpus") -> Path:
    """``recovery_curves.png``: recall against the cutoff, one panel per label class, a line per ranking (the
    union, each pass, the wordfreq baseline dashed)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from assistant_axis import png_metadata
    from assistant_axis.plot_metadata import suptitle_with_specs
    rec = (ev.get("recovery_detail") or {}).get(label_set) or {}
    cut = list(ev.get("cutoffs") or CUTOFFS)
    classes = ("single", "subword", "multiword")
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.4), sharey=True)
    others = [k for k in sorted(rec) if k not in ("union", "baseline_wordfreq")]
    palette = ["tab:blue", "tab:orange", "tab:green", "tab:purple", "tab:brown", "tab:pink", "tab:olive", "tab:cyan",
               "tab:gray"]     # red is the union's alone, black the baseline's
    color = {k: palette[i % len(palette)] for i, k in enumerate(others)}
    for ax, c in zip(axes, classes):
        n = None
        for name in sorted(rec, key=lambda k: (k == "baseline_wordfreq", k != "union", k)):
            v = (rec[name] or {}).get(c) or {}
            if not v.get("n"):
                continue
            n = v["n"]
            ys = [v.get(f"recall@{k}") or 0.0 for k in cut]
            style = dict(ls="--", color="black") if name == "baseline_wordfreq" else \
                dict(lw=2.6, color="tab:red") if name == "union" else dict(lw=1.3, color=color[name])
            ax.plot(cut, ys, marker="o", ms=3, label=name, **style)
        ax.set_xscale("log")
        ax.set_xticks(cut)
        ax.set_xticklabels([f"{k // 1000}k" for k in cut])
        ax.set_title(f"{c} labels (n = {n if n is not None else 0})")
        ax.set_xlabel("cutoff N (first N words of the ranking)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(f"recall of the {label_set}'s labels")
    axes[0].set_ylim(0, 1)
    handles, labels = axes[0].get_legend_handles_labels()
    for ax in axes[1:]:
        h, lab = ax.get_legend_handles_labels()
        for hh, ll in zip(h, lab):
            if ll not in labels:
                handles.append(hh)
                labels.append(ll)
    fig.legend(handles, labels, loc="lower center", ncol=min(5, max(1, len(labels))), frameon=False)
    title = "Masked-LM generator: recovery of our labels against the wordfreq baseline"
    spec = (f"{ev.get('title') or ''}; models {', '.join(ev.get('models') or [])}; "
            f"label classes by the primary tokenizer")
    _, top_rect = suptitle_with_specs(fig, title, spec)
    n_rows = math.ceil(len(labels) / 5) if labels else 1
    fig.subplots_adjust(top=top_rect - 0.04, bottom=0.14 + 0.04 * n_rows, left=0.06, right=0.98, wspace=0.08)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, bbox_inches="tight", metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)
    return Path(path)
