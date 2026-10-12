"""The granularity readings: which of the cuts (``GRANULARITIES``: ~600, ~350, ~150 clusters) is the right one?

**Roger replaced the plan's single measure with two signals, read together** (QUESTIONS 50, 2026-10-11:
"we need to look at both to make a judgement"), both reported **by cluster-size band** and against each other,
never against an absolute bar -- one agglomerative threshold can over-split a dense region and under-split a
sparse one at the same time.  On a tie the **finer** cut wins: a too-small pair is recoverable (R1's
end-of-waves grouping merges duplicates) while a too-big cluster yields one name and hides the other traits
inside it.

1. **Too small shows between clusters.**  :func:`nearest_pair_calls` reads each pole against the nearest pole of
   *another* cluster (``cluster.nearest_other_poles``, written on the pole row by ``cluster``), **by name and
   gloss**, with the same pinned overlap call.  A reading of **3** ("the same concept, differing only in scope,
   degree or emphasis") rather than 2 ("overlapping, neither implies the other") often means one trait was split
   across two clusters, so :func:`nearest_readout` reports the share at 3 and at 3-or-4 per size band.
2. **Too big shows on inspection.**  :func:`spanning_clusters` picks clusters across the whole size range (the
   big ones are where several traits hide) and :func:`readout_markdown` prints them **in full**: every item
   statement, with both the blind and the hinted name of each pole.

The within-pole item pairs of plan § 7 stay as the third, cheaper view: :func:`sample_pairs` draws
``per_cluster`` pairs from inside each pole and ``cross_pole`` pairs across the poles of a bipolar cluster
(expected "opposite", a check on the split), each item shown as a trait (:func:`item_entry`).  Every reading goes
through the pinned rubric A (``overlap_concept.md``, one pair per call) and ``overlap_test.OverlapRunner`` on
Sonnet 5.5, unchanged.  Single items are narrower than traits, so those absolute levels may sit low; that is the
reason signal 1 reads names and glosses rather than item texts.

**The nearest-*corpus*-trait column is a different thing** and is kept clearly apart (QUESTIONS 50): it is
novelty, not size.  A correctly-sized cluster may well duplicate a corpus trait.
"""
from __future__ import annotations

import itertools
import random
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM
from assistant_axis.judge_pricing import MultiModelUsage

from .cluster import item_embed_text
from .ingest import ItemRow, code_order

#: Sonnet 5.5, ``overlap_test.SONNET`` (tested equal).  ``overlap_test`` is imported on first use: it pulls in the
#: OpenAI SDK through ``assistant_axis.judge``, and this package imports no SDK at import time (plan § 8).
MODEL = "claude-sonnet-5-5"
RUBRIC = "A"
CONCURRENCY = 8
SHARE_KEYS: tuple[str, ...] = ("0", "1", "2", "3", "4", "opposite", "unsure")
#: The two signals of QUESTIONS 50, plus the within-pole item pairs of plan § 7.  ``SIGNALS`` is what the CLI's
#: ``--signals`` takes; the inspection signal costs nothing and is always rendered.
SIGNALS: tuple[str, ...] = ("within", "nearest")
#: Cluster-size bands: every share is reported inside a band as well as overall (QUESTIONS 50), because one
#: threshold can over-split a dense region and under-split a sparse one at once.  ``(low, high inclusive or
#: None)``.
SIZE_BANDS: tuple[tuple[int, Optional[int]], ...] = ((2, 3), (4, 7), (8, 15), (16, None))


def band_label(lo: int, hi: Optional[int]) -> str:
    return f"{lo}-{hi}" if hi is not None else f"{lo}+"


BAND_LABELS: tuple[str, ...] = tuple(band_label(lo, hi) for lo, hi in SIZE_BANDS)


def band_of(n: int) -> str:
    """The band label for a cluster of ``n`` items (a size below the first band falls in it)."""
    n = int(n)
    for lo, hi in SIZE_BANDS:
        if hi is None or n <= hi:
            return band_label(lo, hi)
    return BAND_LABELS[-1]


class _LazyOT:
    """``overlap_test``, imported when an attribute is first read."""

    def __getattr__(self, name):
        from assistant_axis.gapgen import overlap_test
        return getattr(overlap_test, name)


OT = _LazyOT()


def item_entry(item: ItemRow) -> dict:
    """An item shown as a trait to the overlap rubric (plan § 5)."""
    s = item_embed_text(item.text)
    return {"label": s, "description": f'This means being someone of whom "{s}" is generally true, as a tendency '
                                       f'rather than an episode.'}


def _pairs(a: Sequence[str], b: Optional[Sequence[str]] = None) -> list[tuple[str, str]]:
    if b is None:
        return [tuple(sorted(p, key=code_order)) for p in itertools.combinations(sorted(a, key=code_order), 2)]
    return [(x, y) for x in sorted(a, key=code_order) for y in sorted(b, key=code_order)]


def sample_pairs(rows: Sequence[Mapping], items: Mapping[str, ItemRow], *, per_cluster: int = 3, cross_pole: int = 1,
                 seed: int = 0, consensus: str = "kept") -> tuple[list[OT.PairCall], dict]:
    """``(calls, corpus)``: for each cluster row with ``consensus`` (default the kept ones), ``per_cluster`` pairs
    drawn uniformly without replacement from the pairs inside its poles (all of them when fewer), and
    ``cross_pole`` pairs across the poles of a bipolar cluster; each pair's order (which item is the target) is a
    seeded coin.  ``corpus`` maps every item used to :func:`item_entry`."""
    calls: list[OT.PairCall] = []
    used: set[str] = set()
    for r in rows:
        if consensus and r.get("consensus") != consensus:
            continue
        g, cid = int(r["granularity"]), int(r["cluster_id"])
        rng = random.Random(f"{seed}:{g}:{cid}")
        origin = f"g{g}:c{cid:03d}"
        within = [p for pole in r["poles"] for p in _pairs(pole["items"])]
        picks = [("within", p) for p in rng.sample(within, min(per_cluster, len(within)))]
        if len(r["poles"]) == 2 and cross_pole:
            cross = _pairs(r["poles"][0]["items"], r["poles"][1]["items"])
            picks += [("cross", p) for p in rng.sample(cross, min(cross_pole, len(cross)))]
        for kind, (x, y) in picks:
            if rng.random() < 0.5:
                x, y = y, x
            # the id names the pair: the runner skips answers on record by id, so a cluster split differently later
            # (new poles, new pairs) never reuses an answer given for another pair
            calls.append(OT.PairCall(call_id=f"{origin}:{kind}:{x}>{y}", set=kind, target=x, listed=[y],
                                     origin_call_id=origin))
            used.update((x, y))
    corpus = {i: item_entry(items[i]) for i in sorted(used, key=code_order)}
    return calls, corpus


def origin_id(granularity: int, cluster_id: int) -> str:
    """The id a cluster's calls share, whichever signal they belong to: ``g350:c017``."""
    return f"g{int(granularity)}:c{int(cluster_id):03d}"


def pole_key_str(cluster_id: int, pole: str) -> str:
    return f"c{int(cluster_id):03d}{pole}"


def pole_entry(pole: Mapping, *, form: str = "blind", label_form: str = DEFAULT_LABEL_FORM) -> Optional[dict]:
    """A named pole as the overlap rubric sees a trait: its label and its gloss (QUESTIONS 50, signal 1 -- the
    nearest-other reading is "by name and gloss", not by item text).  ``None`` for an unnamed pole."""
    from assistant_axis.gapgen.prompt_labels import prompt_label
    nm = pole.get(form)
    if not nm or not nm.get("label") or not nm.get("gloss"):
        return None
    return {"label": prompt_label(nm["label"], label_form), "description": nm["gloss"]}


def nearest_pair_calls(rows: Sequence[Mapping], *, form: str = "blind", consensus: str = "kept",
                       label_form: str = DEFAULT_LABEL_FORM) -> tuple[list[OT.PairCall], dict, dict]:
    """``(calls, corpus, counts)`` for signal 1: one call per named pole of a kept cluster against the nearest
    pole of **another** cluster (``nearest_other`` on the pole row, written by ``cluster``), read by name and
    gloss.  An unordered pair is asked once, in the order of the pole ids, so two poles that are each other's
    nearest are not read twice.  A pole with no name, or whose nearest has no name, is counted and skipped.

    Since 2026-10-12 ``cluster`` chooses the nearest among the **kept** poles only (``"among": "kept"``), which are
    all named by ``name --all``, so a reading is no longer dropped for a neighbour on the loose pile (review 5 D3:
    67 of 238 poles read at ~600 before).  A table written earlier chose it among every pole; ``counts`` says which
    (``nearest_among``), and ``n_nearest_in_other_consensus`` counts what such a table leaves out."""
    entries: dict[str, dict] = {}
    poles: dict[tuple, Mapping] = {}
    by_cluster: dict[int, Mapping] = {}
    status = {int(r["cluster_id"]): r.get("consensus") for r in rows}
    for r in rows:
        if consensus and r.get("consensus") != consensus:
            continue
        by_cluster[int(r["cluster_id"])] = r
        for p in r["poles"]:
            poles[(int(r["cluster_id"]), p["pole"])] = p
            e = pole_entry(p, form=form, label_form=label_form)
            if e is not None:
                entries[pole_key_str(int(r["cluster_id"]), p["pole"])] = e
    calls: list[OT.PairCall] = []
    seen: set = set()
    n_unnamed = n_no_nearest = n_other_unnamed = n_other_outside = 0
    among: set = set()
    for key in sorted(poles):
        p = poles[key]
        a = pole_key_str(*key)
        if a not in entries:
            n_unnamed += 1
            continue
        nn = p.get("nearest_other")
        if not nn:
            n_no_nearest += 1
            continue
        among.add(nn.get("among", "all"))
        other = (int(nn["cluster_id"]), nn["pole"])
        b = pole_key_str(*other)
        if b not in entries:
            n_other_unnamed += 1
            # of those, the nearest pole sits in a cluster outside ``consensus`` (a loose one, never named): counted
            # apart so the readout shows how much of signal 1 that leaves out (review 2026-10-12)
            n_other_outside += int(bool(consensus) and status.get(other[0]) != consensus)
            continue
        pair = tuple(sorted((a, b)))
        if pair in seen:
            continue
        seen.add(pair)
        g = int(by_cluster[key[0]]["granularity"])
        calls.append(OT.PairCall(call_id=f"{origin_id(g, key[0])}:nearest:{a}>{b}", set="nearest", target=a,
                                 listed=[b], origin_call_id=origin_id(g, key[0])))
    corpus = {k: entries[k] for k in sorted({x for c in calls for x in (c.target, c.listed[0])})}
    counts = {"n_calls": len(calls), "n_poles": len(poles), "n_named": len(entries), "n_unnamed": n_unnamed,
              "n_without_nearest": n_no_nearest, "n_nearest_unnamed": n_other_unnamed,
              "n_nearest_in_other_consensus": n_other_outside, "nearest_among": sorted(among), "form": form,
              "label_form": label_form}
    return calls, corpus, counts


def call_bands(rows: Sequence[Mapping], calls: Sequence[OT.Call]) -> dict[str, str]:
    """``{call_id: size band}``, the band of the cluster a call came from (its ``origin_call_id``).  Every signal
    uses the same origin id, so one rule bands them all (QUESTIONS 50: every share is reported by band)."""
    size = {origin_id(int(r["granularity"]), int(r["cluster_id"])): len(r["items"]) for r in rows}
    out = {}
    for c in calls:
        n = size.get(getattr(c, "origin_call_id", "") or "")
        if n is not None:
            out[c.call_id] = band_of(n)
    return out


def spanning_clusters(rows: Sequence[Mapping], n: int = 10, *, seed: int = 0, consensus: str = "kept",
                      named_only: bool = True) -> list[dict]:
    """``n`` kept clusters chosen to **span the size range** (QUESTIONS 50, signal 2: a cluster holding more than
    one trait hides in the big ones, so a uniform sample of a long-tailed size distribution would mostly show
    small ones).  The clusters are sorted by size and cut into ``n`` equal buckets; one is drawn from each, seeded;
    the largest cluster is always included."""
    kept = [r for r in rows if not consensus or r.get("consensus") == consensus]
    if named_only:
        named = [r for r in kept if any(p.get("blind") for p in r["poles"])]
        kept = named or kept
    if not kept or n <= 0:
        return []
    kept = sorted(kept, key=lambda r: (len(r["items"]), int(r["cluster_id"])))
    if len(kept) <= n:
        return sorted(kept, key=lambda r: int(r["cluster_id"]))
    rng = random.Random(f"span:{seed}")
    picks, used = [kept[-1]], {int(kept[-1]["cluster_id"])}
    for b in range(n - 1):
        lo = round(b * len(kept) / (n - 1)) if n > 1 else 0
        hi = max(lo + 1, round((b + 1) * len(kept) / (n - 1)))
        bucket = [r for r in kept[lo:hi] if int(r["cluster_id"]) not in used]
        if bucket:
            got = rng.choice(bucket)
            picks.append(got)
            used.add(int(got["cluster_id"]))
    return sorted(picks, key=lambda r: int(r["cluster_id"]))


def estimate_usd(calls: Sequence[OT.Call], corpus: Mapping, rubrics: Mapping[str, Mapping], *, model: str = MODEL
                 ) -> dict:
    """The overlap test's own estimate: every token at the uncached rate (an upper bound) and with the rubric read
    from the prompt cache."""
    est = OT.estimate(calls, corpus, rubrics, [model], [RUBRIC])
    return {"n_calls": len(calls), "uncached_usd": round(est.usd, 4),
            "cached_usd": round(OT.cached_estimate_usd(calls, corpus, rubrics, [model], [RUBRIC]), 4),
            "lines": [str(x) for x in est.lines]}


async def run_readings(calls: Sequence[OT.PairCall], corpus: Mapping, *, client, usage: MultiModelUsage, out_dir: Path,
                       rubrics: Optional[Mapping] = None, model: str = MODEL, label_form: str = DEFAULT_LABEL_FORM,
                       concurrency: int = CONCURRENCY) -> "OT.StageResult":
    """One stage of rubric A on ``model`` over ``calls`` (resumable: answers already on record are not sent again),
    ``responses.jsonl`` and ``usage.json`` in ``out_dir``."""
    rubrics = rubrics or OT.load_rubrics(keys=[RUBRIC])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runner = OT.OverlapRunner(client, rubrics, corpus, usage=usage, responses_path=out_dir / "responses.jsonl",
                              usage_path=out_dir / "usage.json", concurrency=concurrency, label_form=label_form)
    return await runner.run_stage(RUBRIC, model, list(calls))


def _value(rec: Mapping):
    rows, _errors, _meta = OT.reparse(rec)
    v = (rows.get(1) or {}).get("value")
    return None if v is None else str(v)


def _dist(vals: Sequence) -> dict:
    """The distribution over 0-4, "opposite" and "unsure" (summing to 1 over the parsed answers), the share at 3
    or 4 and the share at exactly 3 (QUESTIONS 50: a 3 between two clusters is the split-trait signal)."""
    ok = [v for v in vals if v is not None]
    n = len(ok)
    out = {k: (round(sum(1 for v in ok if v == k) / n, 4) if n else None) for k in SHARE_KEYS}
    out["share_3_4"] = round(sum(1 for v in ok if v in ("3", "4")) / n, 4) if n else None
    out["share_3"] = round(sum(1 for v in ok if v == "3") / n, 4) if n else None
    out["n"] = n
    out["n_unparsed"] = len(vals) - n
    return out


def _by_band(rows: Sequence[tuple]) -> dict:
    """``{band: distribution}`` over ``[(band, value)]``, every band present even when empty."""
    out = {}
    for b in BAND_LABELS:
        out[b] = _dist([v for bb, v in rows if bb == b])
    return out


def readout(records: Sequence[Mapping], *, granularity: int, n_clusters: int, label_form: str, cost_usd: float,
            model: str = MODEL, rubric_version: Optional[int] = None, bands: Optional[Mapping[str, str]] = None,
            sizes: Optional[Mapping] = None, nearest_counts: Optional[Mapping] = None) -> dict:
    """One granularity's readings (the latest answer per call), split by signal and **by cluster-size band**
    (QUESTIONS 50): ``within`` the item pairs inside a pole, ``cross_pole`` the check on a bipolar split, and
    ``nearest`` signal 1, each pole against the nearest pole of another cluster read by name and gloss.
    ``bands`` maps a call id to its band (:func:`call_bands`); without it only the overall shares are given."""
    latest = OT.latest_records(records)
    by_set: dict[str, list] = {"within": [], "cross": [], "nearest": []}
    banded: dict[str, list] = {"within": [], "cross": [], "nearest": []}
    for cid, r in latest.items():
        s = r.get("set") or "within"
        v = _value(r)
        by_set.setdefault(s, []).append(v)
        banded.setdefault(s, []).append(((bands or {}).get(r.get("call_id") or cid, "unbanded"), v))
    cross = list(by_set.get("cross", []))
    cross_ok = [v for v in cross if v is not None]
    within = _dist(by_set.get("within", []))
    nearest = _dist(by_set.get("nearest", []))
    return {"granularity": int(granularity), "n_clusters": int(n_clusters),
            "n_pairs_read": within["n"] + len(cross_ok) + nearest["n"], "n_pairs_sent": len(latest),
            "within": within, "within_by_band": _by_band(banded.get("within", [])),
            "nearest": nearest, "nearest_by_band": _by_band(banded.get("nearest", [])),
            "nearest_counts": dict(nearest_counts or {}),
            "cross_pole": {"n": len(cross_ok),
                           "opposite": round(sum(1 for v in cross_ok if v == "opposite") / len(cross_ok), 4)
                           if cross_ok else None, "n_unparsed": len(cross) - len(cross_ok)},
            "sizes": dict(sizes or {}), "bands": list(BAND_LABELS),
            "model": model, "rubric": RUBRIC, "rubric_version": rubric_version, "label_form": label_form,
            "cost_usd": round(float(cost_usd), 4)}


def band_sizes(rows: Sequence[Mapping], *, consensus: str = "kept") -> dict:
    """``{band: n kept clusters}`` plus ``n_clusters`` and the size quartiles, for the readout's header."""
    kept = [r for r in rows if not consensus or r.get("consensus") == consensus]
    sizes = sorted(len(r["items"]) for r in kept)
    counts = {b: 0 for b in BAND_LABELS}
    for n in sizes:
        counts[band_of(n)] += 1
    mid = (sizes[len(sizes) // 2] if sizes else None)
    return {"n_clusters": len(kept), "per_band": counts, "min": sizes[0] if sizes else None, "median": mid,
            "max": sizes[-1] if sizes else None}


def _fmt(v) -> str:
    if v is None:
        return ""
    return f"{v:.1%}" if isinstance(v, float) else str(v)


def readout_markdown(readouts: Sequence[Mapping], *, samples: Mapping[int, Sequence[Mapping]],
                     items: Mapping[str, ItemRow], answers: Mapping[str, Sequence[Mapping]], doc_path: Path,
                     files: Sequence[Path] = ()) -> str:
    """``granularity_readout.md``, the document Roger reads (QUESTIONS 50): the two signals side by side and by
    cluster-size band, then, for each granularity, the sampled clusters **in full** -- every item statement, both
    names of each pole, its nearest other cluster, and the readings of its pairs.  ``answers`` maps a cluster's
    origin id (``g350:c017``) to its readings (``{"set", "target", "other", "value", "reason"}``)."""
    import os
    d = Path(doc_path)

    def link(p: Path) -> str:
        return f"[{Path(p).name}]({os.path.relpath(Path(p), d.parent).replace(os.sep, '/')})"
    gs = [r["granularity"] for r in readouts]
    head = "| | " + " | ".join(f"~{g} clusters" for g in gs) + " |"
    rule = "|---|" + "---|" * len(gs)
    lines = ["# IPIP clusters: the granularity readout", "",
             "Two signals, read together and against each other, never against an absolute bar (QUESTIONS 50, "
             "Roger 2026-10-11).  **Signal 1, too small**: each pole read against the nearest pole of *another* "
             "cluster, by name and gloss, with M3's pinned overlap call (rubric A, one pair per call, Sonnet 5.5); "
             "a reading of **3** (\"the same concept, differing only in scope, degree or emphasis\") rather than 2 "
             "often means one trait was split across two clusters.  **Signal 2, too big**: the clusters printed in "
             "full below, chosen to span the size range, for reading.  Both are reported by cluster-size band, "
             "because one threshold can over-split a dense region and under-split a sparse one at the same time; "
             "on a tie the **finer** cut is preferred, since a too-small pair is recoverable at the end-of-waves "
             "grouping while a too-big cluster hides the traits inside it.", "",
             "The within-pole item pairs are the third, cheaper view (each item shown as a trait, \"I "
             "<statement>\"); single items are narrower than traits, so those absolute levels may sit low.  The "
             "nearest-**corpus**-trait column of each cluster row is a different thing and is not a size signal: "
             "it is novelty.", "",
             "## Signal 1: each pole against the nearest pole of another cluster", "", head, rule]
    for k in ("share_3", "share_3_4", "4", "3", "2", "1", "0", "opposite", "unsure", "n", "n_unparsed"):
        lines.append(f"| {k} | " + " | ".join(_fmt(r.get("nearest", {}).get(k)) for r in readouts) + " |")
    lines += ["", "By cluster-size band (share at 3, share at 3-4, pairs read):", "",
              "| band | " + " | ".join(f"~{g}" for g in gs) + " |", rule]
    for b in BAND_LABELS:
        cells = []
        for r in readouts:
            x = (r.get("nearest_by_band") or {}).get(b) or {}
            cells.append(f"{_fmt(x.get('share_3'))} / {_fmt(x.get('share_3_4'))} / {x.get('n', 0)}")
        lines.append(f"| {b} items | " + " | ".join(cells) + " |")
    lines += ["", "## The within-pole item pairs, and the bipolar check", "", head, rule]
    for k in SHARE_KEYS + ("share_3_4", "n", "n_unparsed"):
        lines.append(f"| within: {k} | " + " | ".join(_fmt(r["within"].get(k)) for r in readouts) + " |")
    lines.append("| cross-pole pairs read \"opposite\" | " + " | ".join(
        "" if r["cross_pole"]["opposite"] is None else f"{r['cross_pole']['opposite']:.1%} of {r['cross_pole']['n']}"
        for r in readouts) + " |")
    for k in ("n_clusters", "n_pairs_read", "cost_usd"):
        lines.append(f"| {k} | " + " | ".join(str(r.get(k)) for r in readouts) + " |")
    lines += ["", "Kept clusters per size band:", "", "| band | " + " | ".join(f"~{g}" for g in gs) + " |", rule]
    for b in BAND_LABELS:
        lines.append(f"| {b} items | " + " | ".join(str(((r.get("sizes") or {}).get("per_band") or {}).get(b, ""))
                                                    for r in readouts) + " |")
    lines.append("")
    for g in gs:
        lines += [f"## Signal 2: ~{g} clusters, {len(samples.get(g, []))} clusters in full (spanning the size "
                  f"range)", ""]
        for r in samples.get(g, []):
            origin = origin_id(int(r["granularity"]), int(r["cluster_id"]))
            lines.append(f"### Cluster {r['cluster_id']} ({len(r['items'])} items, band {band_of(len(r['items']))}"
                         + (", bipolar" if r.get("bipolar") else "") + ")")
            nc = r.get("nearest_corpus")
            if nc:
                lines.append(f"- nearest corpus trait (novelty, not size): {nc.get('stem')} at "
                             f"{nc.get('mean_cos')}")
            for p in r["poles"]:
                names = [f"{form} **{p[form]['label']}**" + (f" ({p[form]['kind']})"
                                                             if p[form].get("kind") else "")
                         for form in ("blind", "hinted") if p.get(form)]
                lines.append(f"- **pole {p['pole']}**" + (f" -- {'; '.join(names)}" if names else " -- not named"))
                for form in ("blind", "hinted"):
                    if p.get(form) and p[form].get("gloss"):
                        lines.append(f"  - {form} gloss: {p[form]['gloss']}")
                nn = p.get("nearest_other")
                if nn:
                    lines.append(f"  - nearest other cluster: c{int(nn['cluster_id']):03d}{nn['pole']} at "
                                 f"{nn.get('cos')}")
                for i in p["items"]:
                    lines.append(f"  - {item_embed_text(items[i].text)}")
            for a in answers.get(origin, []):
                lines.append(f"- reading ({a['set']}): \"{a['target']}\" / \"{a['other']}\" -> **{a['value']}** "
                             f"({a['reason']})")
            lines.append("")
    if files:
        lines += ["## Files", ""] + [f"- {link(p)}" for p in files] + [""]
    return "\n".join(lines)
