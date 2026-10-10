"""The granularity readings: how alike are two items of one pole, by M3's own overlap call?

Roger's criterion (plan 07 § 9.4): choose the granularity whose clusters are "about the same size as our '3-4'
relationship level for covered judgements".  Operationalised (plan § 7 ``granularity``): for every consensus
cluster, :func:`sample_pairs` draws ``per_cluster`` item pairs uniformly from the pairs inside its poles, and
``cross_pole`` pairs across the two poles of a bipolar cluster (expected "opposite", a check on the split); each
item is shown to the pinned rubric A (``overlap_concept.md``, one pair per call) as a trait
(:func:`item_entry`), through ``overlap_test.OverlapRunner`` on Sonnet 5.5, unchanged.  :func:`readout` gives each
granularity's distribution over 0-4, "opposite" and "unsure", and the share at 3 or 4.

Read comparatively (QUESTIONS 50): single items are narrower than traits, so absolute levels may sit low; the
decision statistic is the comparison between the granularities, with Roger's read of sampled clusters.
"""
from __future__ import annotations

import itertools
import random
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen import overlap_test as OT
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM
from assistant_axis.judge_pricing import MultiModelUsage

from .cluster import item_embed_text
from .ingest import ItemRow, code_order

MODEL = OT.SONNET
RUBRIC = "A"
SHARE_KEYS: tuple[str, ...] = ("0", "1", "2", "3", "4", "opposite", "unsure")


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
        for k, (kind, (x, y)) in enumerate(picks):
            if rng.random() < 0.5:
                x, y = y, x
            calls.append(OT.PairCall(call_id=f"{origin}:{kind[0]}{k}", set=kind, target=x, listed=[y],
                                     origin_call_id=origin))
            used.update((x, y))
    corpus = {i: item_entry(items[i]) for i in sorted(used, key=code_order)}
    return calls, corpus


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
                       concurrency: int = OT.DEFAULT_CONCURRENCY) -> OT.StageResult:
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


def readout(records: Sequence[Mapping], *, granularity: int, n_clusters: int, label_form: str, cost_usd: float,
            model: str = MODEL, rubric_version: Optional[int] = None) -> dict:
    """The distribution of one granularity's readings (the latest answer per call): within-pole shares over
    0-4, "opposite" and "unsure" (they sum to 1 over the parsed answers), the share at 3 or 4, and the cross-pole
    share read "opposite"."""
    latest = OT.latest_records(records)
    by_set: dict[str, list] = {"within": [], "cross": []}
    for r in latest.values():
        by_set.setdefault(r.get("set") or "within", []).append(_value(r))

    def dist(vals):
        ok = [v for v in vals if v is not None]
        n = len(ok)
        out = {k: (round(sum(1 for v in ok if v == k) / n, 4) if n else None) for k in SHARE_KEYS}
        out["share_3_4"] = round(sum(1 for v in ok if v in ("3", "4")) / n, 4) if n else None
        out["n"] = n
        out["n_unparsed"] = len(vals) - n
        return out
    cross = [v for v in by_set.get("cross", [])]
    cross_ok = [v for v in cross if v is not None]
    within = dist(by_set.get("within", []))
    return {"granularity": int(granularity), "n_clusters": int(n_clusters), "n_pairs_read": within["n"] + len(cross_ok),
            "n_pairs_sent": len(latest), "within": within,
            "cross_pole": {"n": len(cross_ok),
                           "opposite": round(sum(1 for v in cross_ok if v == "opposite") / len(cross_ok), 4)
                           if cross_ok else None, "n_unparsed": len(cross) - len(cross_ok)},
            "model": model, "rubric": RUBRIC, "rubric_version": rubric_version, "label_form": label_form,
            "cost_usd": round(float(cost_usd), 4)}


def readout_markdown(readouts: Sequence[Mapping], *, samples: Mapping[int, Sequence[Mapping]],
                     items: Mapping[str, ItemRow], answers: Mapping[str, Sequence[Mapping]], doc_path: Path,
                     files: Sequence[Path] = ()) -> str:
    """``granularity_readout.md``: the distributions side by side, then for each granularity the sampled clusters
    (their items by pole, their names when named, the readings of their pairs).  ``answers`` maps a cluster's
    origin id (``g350:c017``) to its readings (``{"set", "target", "other", "value", "reason"}``)."""
    import os
    d = Path(doc_path)

    def link(p: Path) -> str:
        return f"[{Path(p).name}]({os.path.relpath(Path(p), d.parent).replace(os.sep, '/')})"
    gs = [r["granularity"] for r in readouts]
    lines = ["# IPIP clusters: the granularity readout", "",
             "Each consensus cluster's item pairs (inside a pole) read by M3's overlap call (rubric A, one pair per "
             "call, Sonnet 5.5), each item shown as a trait (\"I <statement>\", described as a lasting tendency).  "
             "Roger's criterion: the granularity whose pairs centre on 3-4, the level at which M3 calls a candidate "
             "covered.  Read comparatively (QUESTIONS 50): single items are narrower than traits.", "",
             "| | " + " | ".join(f"~{g} clusters" for g in gs) + " |", "|---|" + "---|" * len(gs)]
    for k in SHARE_KEYS + ("share_3_4", "n", "n_unparsed"):
        lines.append(f"| within: {k} | " + " | ".join(
            "" if r["within"].get(k) is None else (f"{r['within'][k]:.1%}" if isinstance(r['within'][k], float)
                                                   else str(r["within"][k])) for r in readouts) + " |")
    lines.append("| cross-pole pairs read \"opposite\" | " + " | ".join(
        "" if r["cross_pole"]["opposite"] is None else f"{r['cross_pole']['opposite']:.1%} of {r['cross_pole']['n']}"
        for r in readouts) + " |")
    for k in ("n_clusters", "n_pairs_read", "cost_usd"):
        lines.append(f"| {k} | " + " | ".join(str(r[k]) for r in readouts) + " |")
    lines.append("")
    for g in gs:
        lines += [f"## ~{g} clusters: {len(samples.get(g, []))} sampled clusters", ""]
        for r in samples.get(g, []):
            origin = f"g{r['granularity']}:c{int(r['cluster_id']):03d}"
            lines.append(f"### Cluster {r['cluster_id']} ({len(r['items'])} items"
                         + (", bipolar" if r.get("bipolar") else "") + ")")
            for p in r["poles"]:
                names = []
                for form in ("blind", "hinted"):
                    if p.get(form):
                        names.append(f"{form} **{p[form]['label']}**")
                lines.append(f"- pole {p['pole']}" + (f" ({'; '.join(names)})" if names else "") + ": "
                             + "; ".join(item_embed_text(items[i].text) for i in p["items"]))
            for a in answers.get(origin, []):
                lines.append(f"  - {a['set']}: \"{a['target']}\" / \"{a['other']}\" -> **{a['value']}** ({a['reason']})")
            lines.append("")
    if files:
        lines += ["## Files", ""] + [f"- {link(p)}" for p in files] + [""]
    return "\n".join(lines)
