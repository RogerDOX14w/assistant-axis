#!/usr/bin/env python3
"""Workstream 13's CLI: the generator dashboard and its parts, from what the platform recorded.

    uv run python data_analysis/gap_generation/generator_dashboard.py <command> [...]

The plan is ``reports/trait_gap_generation/coding_plan_13_generator_testing.md`` (§ 7); the library is
``assistant_axis/gapgen/testing/``.  Every command but ``paraphrase-set run`` costs nothing (no API call).  Outputs
go to ``data/candidates/testing/`` (``--out``): enveloped JSON (``json_metadata``, with the inputs), rewritten whole,
the previous file kept as ``<name>.bak.<UTC>`` when its result changes; ``--dry-run`` prints what would be written
and writes nothing.

Common flags: ``--registry`` (default the tracked snapshot ``registry.snapshot.jsonl.gz``; ``--live`` for the
checkout's log ``registry.jsonl``), ``--data-dir``, ``--regions``, ``--graph`` (default: the review graph built over
the most trait batches, today ``review_traits_all_2``), ``--review-root``, ``--out``, ``--dry-run``.

* ``independence [--check]``: ``independence.json``, each generator stream's class, mechanism and exclusion rule
  with its row counts; ``--check`` exits 1 when a registry generator has no rule.
* ``review-rate [--batch B ...] [--idle-s 300]``: ``review_rates.json``, the review rate per batch with a
  ``decisions.jsonl``, the pooled rate and the promote shares (per group, decision 3; per term beside it).
* ``repetition [--level 3 4]``: ``repetition.json``, pre-handled terms and attachment to the reviewed batches.
* ``concepts [--unit components_4 grown_3] [--tau 0.67]``: ``concepts.json``, the concept units, their agreement
  with the review, and the pilot's reading lists (20 strict components and 20 grown units, seeded).
* ``estimate [--unit ...] [--by-region]``: ``estimates.json`` (Chapman, Chao2, coverage, accumulation, the
  alignment sweep's two occasions, the corpus as an occasion); prints the assumptions every time.
* ``simulate [--n 2000 --occasions 4 --sigma 1.0 --rho 0.3 --replicates 200 --seed 0]``: ``simulation.json``.
* ``recovery-extras --batch B [--c 4]``: ``data/candidates/recovery/<B>/extras.json`` (the strict column, pair
  recovery, recall at N, the ``needs_opus`` list).  No call: a pair the record cannot decide at 4 is listed.
* ``roger-sample --batch B [--n 20 --seed 0]``: ``data/candidates/recovery/<B>/roger_sample.md``, the manual check
  of plan 13 § 8 (twenty recovered and twenty novel verdicts of a harness batch, seeded, for Roger to mark).
* ``dashboard [--harness B ...]``: every record above rebuilt and folded into ``dashboard.json`` and
  ``dashboard.md``; costs from every ``usage.json``.  Re-run after every M3 batch, every review ``apply`` and every
  harness run.
* ``paraphrase-set build [--n-single 40 --n-pairs 40 --seed 0]`` ($0: ``set.jsonl`` and ``hidden.json``);
  ``paraphrase-set run --budget-usd 0.5 [--resume]`` (Haiku 5.5, one call per item, about $0.01; prints the
  estimate first; refuses an estimate over the budget and uncommitted platform code without ``--allow-dirty``;
  writes ``responses.jsonl``, ``answers.jsonl``, ``usage.json``, ``run.json`` and the scratch ``registry.jsonl``,
  then prints the harness command); ``paraphrase-set report --batch rec_testing_paraphrase_set`` (``report.md``).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import novelty as NV  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import recovery as RC  # noqa: E402
from assistant_axis.gapgen.registry import read_snapshot, snapshot_file, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.testing import TESTING_DIR  # noqa: E402
from assistant_axis.gapgen.testing import concepts as C  # noqa: E402
from assistant_axis.gapgen.testing import dashboard as D  # noqa: E402
from assistant_axis.gapgen.testing import estimators as E  # noqa: E402
from assistant_axis.gapgen.testing import independence as IND  # noqa: E402
from assistant_axis.gapgen.testing import recovery_extras as RX  # noqa: E402
from assistant_axis.gapgen.testing import repetition as RP  # noqa: E402
from assistant_axis.gapgen.testing import review_minutes as RM  # noqa: E402

REVIEW_ROOT = paths.DATA_CANDIDATES / "review"
RECOVERY_ROOT = paths.DATA_CANDIDATES / "recovery"
UNIT_LABELS = {("components_4", None): "strict components (4)", ("grown_3", 0.67): "grown across 3-links, density >= 0.67",
               ("grown_3", 0.5): "the same, density >= 0.5", ("grown_3", 0.8): "the same, density >= 0.8",
               ("components_3", None): "components at 3 (chains unbroken)"}
OCC3 = ("lexicon", "ipip", "base_model", "masked_lm")
OCC4 = OCC3 + ("alignment",)


# --------------------------------------------------------------------------- inputs and outputs

def registry_path(args) -> Path:
    if args.registry is not None:
        return Path(args.registry)
    return paths.REGISTRY_PATH if args.live else snapshot_file(paths.DATA_CANDIDATES)


def load_rows(args) -> dict:
    p = registry_path(args)
    if not p.exists():
        raise SystemExit(f"REFUSED: no registry at {p}")
    return read_snapshot(p)


def default_graph(review_root: Path) -> Optional[Path]:
    """The review graph built over the most trait batches (not a physical or states pass); ties by the newest."""
    best = None
    for d in sorted(Path(review_root).glob("review_*")):
        if not (d / "graph.json").exists() or d.name.startswith(("review_physical", "review_states")):
            continue
        run = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else {}
        n = len(run.get("from_batches") or [])
        key = (n, (d / "graph.json").stat().st_mtime)
        if best is None or key > best[0]:
            best = (key, d / "graph.json")
    return best[1] if best else None


def graph_path(args) -> Path:
    p = Path(args.graph) if args.graph else default_graph(args.review_root)
    if p is None or not Path(p).exists():
        raise SystemExit(f"REFUSED: no review graph (--graph, or a review_*/graph.json under {args.review_root})")
    return Path(p)


def rel(p) -> str:
    """A path as recorded: relative to the repository when it is inside it."""
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def file_input(dep_key: str, p: Path):
    from assistant_axis.provenance import current_file_input
    return current_file_input(dep_key=dep_key, path=Path(p))


def write_output(path: Path, payload, *, title: str, inputs: list, dry_run: bool) -> Path:
    """The envelope, written whole; the previous file kept as ``<name>.bak.<UTC>`` when its result changed."""
    from assistant_axis.plot_metadata import json_metadata
    path = Path(path)
    env = json_metadata(payload, title=title, inputs=inputs or None)
    text = json.dumps(env, indent=1, ensure_ascii=False, default=str) + "\n"
    if len(text) > 500_000:                       # concepts.json: one line per top-level key keeps it diffable
        text = "{\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False, default=str)}"
                                  for k, v in env.items()) + "\n}\n"
    if dry_run:
        print(f"DRY-RUN: would write {path} ({len(text):,} bytes)")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8")).get("result")
        except (OSError, json.JSONDecodeError):
            old = None
        if old != json.loads(json.dumps(payload, default=str)):
            shutil.copyfile(path, path.with_name(f"{path.name}.bak.{utc_stamp()}"))
    atomic_write_text(text, path)
    print(f"wrote {path}")
    return path


def queue_of(args) -> dict:
    p = Path(args.data_dir) / "seed_queue.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"entries": []}


def review_dirs(args, batches=None) -> list[Path]:
    dirs = RM.review_batch_dirs(args.review_root)
    if batches:
        dirs = [d for d in dirs if d.name in set(batches)]
    return dirs


# --------------------------------------------------------------------------- the parts

def build_independence(args, rows) -> list[dict]:
    return IND.independence_table(rows, IND.trait_sources(args.data_dir), queue_of(args))


def build_review_rates(args, rows, batches=None) -> dict:
    dirs = review_dirs(args, batches)
    recs = [RM.review_record(d, idle_s=args.idle_s) for d in dirs]
    pooled = RM.pooled_review_rate(dirs, idle_s=args.idle_s)
    res = RM.load_resolutions(dirs)
    pshare = RM.pooled_promote_share(rows, res)
    shares = {g: RM.promote_share(rows, generator=g, resolutions=res, pooled=pshare).as_dict()
              for g in D.generator_names(rows) if g not in IND.POOL_GENERATORS + IND.ATTRIBUTED_GENERATORS}
    by_batch = {}
    for d in dirs:                       # the groups each batch resolved (its terms' per-term share is not separable)
        b = RM.pooled_promote_share(rows, RM.load_resolutions([d]))
        by_batch[d.name] = {"per_group": b.per_group, "n_groups": b.n_groups, "n_promoted_groups": b.n_promoted_groups,
                            "by_shape": b.by_shape}
    as_of = max((e.at for d in dirs for e in RM.load_events(d, drop_undone=False)), default=None)
    return {"batches": recs, "pooled": pooled.as_dict(), "promote_share_pooled": pshare.as_dict(),
            "promote_share_by_batch": by_batch, "promote_share_by_generator": shares, "idle_s": args.idle_s,
            "review_as_of": as_of.isoformat() if as_of else None}


def build_repetition(graph, rows, levels=(3, 4)) -> list[dict]:
    return RP.repetition_records(graph, levels=levels, rows=rows)


def build_concepts(args, graph, rows, *, units=("components_4", "grown_3"), tau=C.DEFAULT_TAU) -> dict:
    dirs = review_dirs(args)
    cache: dict = {}
    nodes = RP.kept_nodes(graph)
    out = {"graph": graph.get("batch_id"), "n_kept": len(nodes), "tau": tau, "units": {}, "sensitivity": {},
           "chain_diagnostic": None, "samples": {}}
    for unit in units:
        us = C.build_units(graph, unit, tau=tau, cache=cache)
        t = C.concept_table(graph, unit=unit, units=us, tau=tau if unit == "grown_3" else None, rows=rows,
                            occasions=OCC4)
        ag = C.review_agreement(us, dirs, graph, rows=rows)
        out["units"][unit] = t.as_dict() | {"agreement": ag.as_dict()}
        out["samples"][unit] = C.unit_sample(us, nodes, n=20, seed=0)
    for t2 in C.SENSITIVITY_TAUS:
        us = C.build_units(graph, "grown_3", tau=t2, cache=cache)
        t = C.concept_table(graph, unit="grown_3", units=us, tau=t2, rows=rows, occasions=OCC4)
        full = t.as_dict()
        out["sensitivity"][f"grown_3@{t2}"] = t.as_dict(with_concepts=False) | \
            {"agreement": C.review_agreement(us, dirs, graph, rows=rows).as_dict(),
             "chao2_three": D.estimates_from_table(full, occasions=OCC3).get("chao2"),
             "chao2_four": D.estimates_from_table(full, occasions=OCC4).get("chao2")}
    us = C.build_units(graph, "components_3", cache=cache)
    t = C.concept_table(graph, unit="components_3", units=us, rows=rows, occasions=OCC4)
    full = t.as_dict()
    out["chain_diagnostic"] = t.as_dict(with_concepts=False) | \
        {"agreement": C.review_agreement(us, dirs, graph, rows=rows).as_dict(),
         "chao2_three": D.estimates_from_table(full, occasions=OCC3).get("chao2"),
         "chao2_four": D.estimates_from_table(full, occasions=OCC4).get("chao2")}
    return out


def build_estimates(args, concepts: dict, rows, traits, *, by_region=True) -> dict:
    out = {"assumptions": list(E.ASSUMPTIONS), "units": {}}
    tables = dict(concepts["units"])
    for unit, t in tables.items():
        rec = {"three_occasions": D.estimates_from_table(t, occasions=OCC3),
               "four_occasions_with_alignment": D.estimates_from_table(t, occasions=OCC4),
               "accumulation": D.accumulation_by_mechanism(t, rows, runs_root=Path(args.candidates_dir) / "runs",
                                                           mechanisms=("lexicon", "ipip", "base_model", "alignment")),
               "alignment_population": D.alignment_occasions(rows, t),
               "corpus_as_occasion": D.corpus_occasion(rows, t, traits, occasions=OCC3)}
        if by_region:
            rec["by_region"] = D.estimates_by_region(t, occasions=OCC3)
        out["units"][unit] = rec
    return out


def print_assumptions() -> None:
    print("Assumptions of every estimate:")
    for a in E.ASSUMPTIONS:
        print(f"  - {a}")


def harness_records(args, rows, batches=None) -> list[dict]:
    """The recorded harness batches (``--harness``, default every one with a report): report, extras (read, or
    computed when absent), and for a pooled batch the strict column and pair recovery per generator."""
    out = []
    for d in sorted(Path(args.recovery_root).glob("*")):
        if batches and d.name not in set(batches):
            continue
        rp = d / "recovery_report.json"
        if not rp.exists():
            continue
        rep = json.loads(rp.read_text(encoding="utf-8")).get("result", {})
        ex_p = d / "extras.json"
        ex = json.loads(ex_p.read_text(encoding="utf-8")).get("result") if ex_p.exists() else RX.extras_json(d)
        rec = {"batch_id": d.name, "report": rep, "extras": ex}
        if rep.get("generator") == "pooled":
            att = {k: RC.attribution(rows[k], rows) for k in rows if rows[k].get("sources")}
            by_g: dict = {}
            for k, pairs in att.items():
                for g, _ in pairs:
                    by_g.setdefault(g, set()).add(k)
            strict, pair = {}, {}
            for g, keys in by_g.items():
                sv, pv = [], []
                for sd in RX.seed_dirs(d):
                    if (sd / "matches.jsonl").exists():
                        sv.append(RX.strict_column(sd, keys=keys).recall)
                        pv.append(RX.pair_recovery(sd, keys=keys).share)
                strict[g] = sum(x for x in sv if x is not None) / len(sv) if sv else None
                pair[g] = sum(x for x in pv if x is not None) / len(pv) if pv else None
            rec["strict_by_generator"], rec["pair_by_generator"] = strict, pair
        out.append(rec)
    return out


# --------------------------------------------------------------------------- commands

def cmd_independence(args) -> int:
    rows = load_rows(args)
    if args.check:
        miss = IND.missing_rules(rows)
        for g, s in miss:
            print(f"MISSING: no stream rule for {g}/{s}", file=sys.stderr)
        print("independence --check: " + ("OK" if not miss else f"{len(miss)} stream(s) without a rule"))
        return 1 if miss else 0
    table = build_independence(args, rows)
    print(IND.table_markdown(table))
    write_output(Path(args.out) / "independence.json", {"rows": table, "registry": rel(registry_path(args))},
                 title="generator_dashboard independence",
                 inputs=[file_input("registry", registry_path(args)), file_input("seed_queue",
                                                                                 Path(args.data_dir) / "seed_queue.json")],
                 dry_run=args.dry_run)
    return 0


def cmd_review_rate(args) -> int:
    rows = load_rows(args)
    rec = build_review_rates(args, rows, args.batch)
    for r in rec["batches"]:
        print(json.dumps(r))
    print(f"pooled: {json.dumps(rec['pooled'])}")
    print(f"promote share, pooled: {json.dumps(rec['promote_share_pooled'])}")
    logs = [d / RM.LOG_NAME for d in review_dirs(args, args.batch)]
    write_output(Path(args.out) / "review_rates.json", rec, title="generator_dashboard review-rate",
                 inputs=[file_input(f"log_{p.parent.name}", p) for p in logs] + [file_input("registry", registry_path(args))],
                 dry_run=args.dry_run)
    return 0


def cmd_repetition(args) -> int:
    rows = load_rows(args)
    gp = graph_path(args)
    graph = RP.load_graph(gp)
    recs = build_repetition(graph, rows, tuple(args.level))
    print(RP.repetition_markdown(recs))
    write_output(Path(args.out) / "repetition.json", {"graph": str(gp), "rows": recs},
                 title="generator_dashboard repetition",
                 inputs=[file_input("graph", gp), file_input("registry", registry_path(args))], dry_run=args.dry_run)
    return 0


def cmd_concepts(args) -> int:
    rows = load_rows(args)
    gp = graph_path(args)
    graph = RP.load_graph(gp)
    rec = build_concepts(args, graph, rows, units=tuple(args.unit), tau=args.tau)
    for u, t in rec["units"].items():
        ag = t["agreement"]
        print(f"{u}: {t['n_concepts']} units, {t['n_singletons']} singletons, largest {t['largest']}; kept together "
              f"{ag['kept_together']}, one concept {ag['one_concept']}, hard negatives joined "
              f"{ag['hard_negatives_joined']} of {ag['n_negatives']}")
    for k, t in rec["sensitivity"].items():
        print(f"{k}: {t['n_concepts']} units, largest {t['largest']}")
    cd = rec["chain_diagnostic"]
    print(f"components_3: {cd['n_concepts']} units, largest {cd['largest']}")
    write_output(Path(args.out) / "concepts.json", rec | {"graph_path": str(gp)}, title="generator_dashboard concepts",
                 inputs=[file_input("graph", gp), file_input("registry", registry_path(args))], dry_run=args.dry_run)
    return 0


def cmd_estimate(args) -> int:
    print_assumptions()
    rows = load_rows(args)
    gp = graph_path(args)
    graph = RP.load_graph(gp)
    traits = NV.load_trait_corpus(args.data_dir)
    conc = build_concepts(args, graph, rows, units=tuple(args.unit), tau=args.tau)
    rec = build_estimates(args, conc, rows, traits, by_region=args.by_region)
    for u, r in rec["units"].items():
        c3 = r["three_occasions"].get("chao2") or {}
        print(f"{u}: Chao2 over {r['three_occasions']['occasions']} N {c3.get('N')} ({c3.get('lo')}-{c3.get('hi')}), "
              f"coverage {r['three_occasions'].get('coverage')}")
    write_output(Path(args.out) / "estimates.json", rec | {"graph": str(gp)}, title="generator_dashboard estimate",
                 inputs=[file_input("graph", gp), file_input("registry", registry_path(args))], dry_run=args.dry_run)
    return 0


def cmd_simulate(args) -> int:
    from assistant_axis.gapgen.testing import simulate as S
    res = S.run_scenarios(N=args.n, m_occ=args.occasions, sigma=args.sigma, rho=args.rho, replicates=args.replicates,
                          seed=args.seed)
    print(S.bias_table_markdown(res))
    write_output(Path(args.out) / "simulation.json", res, title="generator_dashboard simulate", inputs=[],
                 dry_run=args.dry_run)
    return 0


def cmd_recovery_extras(args) -> int:
    d = Path(args.recovery_root) / args.batch
    if not (d / "run.json").exists():
        print(f"REFUSED: no harness batch at {d}", file=sys.stderr)
        return 2
    ex = RX.extras_json(d, c=args.c)
    print(RX.extras_markdown(ex))
    if ex["needs_opus"]:
        print(f"{ex['n_needs_opus']} pair(s) need an Opus reading the record lacks; they are listed in extras.json and "
              "left out of the strict column.  Sending them (--send-opus) is not built: no recorded batch needed it.")
        if args.send_opus:
            print("REFUSED: --send-opus is not built (see above)", file=sys.stderr)
            return 2
    inputs = [file_input(f"matches_s{sd.name[4:]}", sd / "matches.jsonl") for sd in RX.seed_dirs(d)
              if (sd / "matches.jsonl").exists()]
    write_output(d / "extras.json", ex, title=f"generator_dashboard recovery-extras {args.batch}", inputs=inputs,
                 dry_run=args.dry_run)
    return 0


def cmd_roger_sample(args) -> int:
    d = Path(args.recovery_root) / args.batch
    if not (d / "run.json").exists():
        print(f"REFUSED: no harness batch at {d}", file=sys.stderr)
        return 2
    md = RX.roger_sample(d, traits=NV.load_trait_corpus(args.data_dir), n=args.n, seed=args.seed)
    if args.dry_run:
        print(md)
        return 0
    atomic_write_text(md, d / "roger_sample.md")
    print(f"wrote {d / 'roger_sample.md'}")
    return 0


def cmd_dashboard(args) -> int:
    print_assumptions()
    rows = load_rows(args)
    rp = registry_path(args)
    gp = graph_path(args)
    graph = RP.load_graph(gp)
    traits = NV.load_trait_corpus(args.data_dir)
    queue = queue_of(args)
    out = Path(args.out)
    ind = build_independence(args, rows)
    rr = build_review_rates(args, rows)
    rep = build_repetition(graph, rows)
    conc = build_concepts(args, graph, rows)
    est = build_estimates(args, conc, rows, traits)
    harness = harness_records(args, rows, args.harness)
    costs = D.cost_by_run(rows, candidates_dir=Path(args.candidates_dir))
    shares = {g: RM.PromoteShare(**v) for g, v in rr["promote_share_by_generator"].items()}
    pooled_rate = RM.PooledRate(**{k: tuple(v) if isinstance(v, list) else v for k, v in rr["pooled"].items()})
    rep_map = {(r["generator"], r["level"]): r for r in rep}
    grows = D.build_rows(rows, traits=traits, queue=queue, graph=graph, independence=ind, repetition=rep_map,
                         shares=shares, rate=pooled_rate, costs=costs, harness=harness)
    sim_p = out / "simulation.json"
    sim = json.loads(sim_p.read_text(encoding="utf-8")).get("result") if sim_p.exists() else None
    from assistant_axis.gapgen.testing import simulate as S
    csum = []
    for (unit, tau), label in UNIT_LABELS.items():
        if unit == "components_3":
            t = conc["chain_diagnostic"]
        elif unit == "grown_3" and tau != conc["tau"]:
            t = conc["sensitivity"].get(f"grown_3@{tau}")
        else:
            t = conc["units"].get(unit)
        if not t:
            continue
        e = est["units"].get(unit) if (unit, tau) in (("components_4", None), ("grown_3", conc["tau"])) else None
        csum.append({"unit": unit, "tau": tau, "label": label, "n_concepts": t["n_concepts"],
                     "n_singletons": t["n_singletons"], "largest": t["largest"], "agreement": t.get("agreement"),
                     "chao2_3": (e or {}).get("three_occasions", {}).get("chao2") or t.get("chao2_three"),
                     "chao2_4": (e or {}).get("four_occasions_with_alignment", {}).get("chao2") or t.get("chao2_four")})
    esum = []
    for unit, label in (("components_4", "the strict unit (components_4)"),
                        ("grown_3", f"the grown unit (grown_3, density >= {conc['tau']})")):
        e = est["units"].get(unit)
        if e:
            esum.append({"unit": unit, "label": label, "three": e["three_occasions"],
                         "four": e["four_occasions_with_alignment"], "corpus": e["corpus_as_occasion"],
                         "accumulation": {m: {k: v for k, v in a.items() if k != "curve"}
                                          for m, a in e["accumulation"].items()},
                         "alignment": e["alignment_population"]})
    dash = {"schema_version": D.SCHEMA_VERSION, "produced_at": utc_now(),
            "inputs": {"registry": rel(rp), "registry_keys": len(rows), "registry_sha256": RC.file_sha256(rp),
                       "graph": rel(gp),
                       "graph_batch": graph.get("batch_id"), "review_batches": [r["batch_id"] for r in rr["batches"]],
                       "review_as_of": rr.get("review_as_of"), "harness_batches": [h["batch_id"] for h in harness]},
            "rows": [r.as_dict() for r in grows], "review_rate": rr["pooled"],
            "promote_share_pooled": rr["promote_share_pooled"],
            "string_recall_any": {k: v for k, v in D.any_generator_string_recall(rows, traits).items() if k != "stems"},
            "concepts_summary": csum, "estimates_summary": esum,
            "unit_samples": {u: conc["samples"][u] for u in conc["samples"]},
            "costs": {"n_files": len(costs.files), "total_read": round(costs.total_read, 4),
                      "attributed": round(costs.attributed_total(), 4),
                      "unattributed": round(sum(costs.unattributed.values()), 4),
                      "unattributed_files": costs.unattributed,
                      "by_run": {f"{g}/{r}": c.as_dict() for (g, r), c in sorted(costs.by_run.items())}},
            "simulation_table": S.bias_table_markdown(sim) if sim else None}
    inputs = [file_input("registry", rp), file_input("graph", gp)] + \
        [file_input(f"log_{d.name}", d / RM.LOG_NAME) for d in review_dirs(args)]
    write_output(out / "independence.json", {"rows": ind, "registry": rel(rp)}, title="generator_dashboard independence",
                 inputs=inputs[:1], dry_run=args.dry_run)
    write_output(out / "review_rates.json", rr, title="generator_dashboard review-rate", inputs=inputs,
                 dry_run=args.dry_run)
    write_output(out / "repetition.json", {"graph": rel(gp), "rows": rep}, title="generator_dashboard repetition",
                 inputs=inputs[:2], dry_run=args.dry_run)
    write_output(out / "concepts.json", conc | {"graph_path": rel(gp)}, title="generator_dashboard concepts",
                 inputs=inputs, dry_run=args.dry_run)
    write_output(out / "estimates.json", est | {"graph": rel(gp)}, title="generator_dashboard estimate",
                 inputs=inputs[:2], dry_run=args.dry_run)
    write_output(out / "dashboard.json", dash, title="generator_dashboard dashboard", inputs=inputs,
                 dry_run=args.dry_run)
    md = D.render_markdown(dash)
    if args.dry_run:
        print(f"DRY-RUN: would write {out / 'dashboard.md'} ({len(md):,} characters)")
    else:
        atomic_write_text(md, out / "dashboard.md")
        print(f"wrote {out / 'dashboard.md'}")
    print(f"costs: read ${costs.total_read:.2f} in {len(costs.files)} records; attributed ${costs.attributed_total():.2f}, "
          f"not attributed ${sum(costs.unattributed.values()):.2f}")
    return 0


# --------------------------------------------------------------------------- paraphrase set

def cmd_paraphrase(args) -> int:
    from assistant_axis.gapgen.testing import paraphrase_set as PS
    sd = Path(args.set_dir)
    data_dir = Path(args.data_dir)
    traits = NV.load_trait_corpus(data_dir)
    regions = RC.load_regions(args.regions)
    if args.pcmd == "build":
        paraphrases, sources = PS.load_paraphrases()
        items, stats = PS.build_set_with_stats(traits, paraphrases, regions, n_single=args.n_single,
                                               n_pairs=args.n_pairs, seed=args.seed, sources=sources,
                                               alignment=PS.load_alignment(args.regions))
        kinds = RC.arrangement_kinds(data_dir, traits)
        hidden = PS.hidden_file(items, traits, regions, kinds)
        print(f"{len(items)} items ({Counter(i.kind for i in items)}); {hidden['n_hidden']} traits hidden in "
              f"{hidden['n_groups']} groups; refused while drawing: {json.dumps(stats.get('refused'))}")
        print(PS.estimate(items).format())
        if args.dry_run:
            print(f"DRY-RUN: would write {sd / PS.SET_NAME} and {sd / PS.HIDDEN_NAME}")
            return 0
        sd.mkdir(parents=True, exist_ok=True)
        for p in (sd / PS.SET_NAME, sd / PS.HIDDEN_NAME):
            if p.exists():
                shutil.copyfile(p, p.with_name(f"{p.name}.bak.{utc_stamp()}"))
        PS.write_set(items, sd / PS.SET_NAME)
        atomic_write_text(json.dumps(hidden | {"drawn_at": utc_now(), "build": {"seed": args.seed, "stats": stats}},
                                     indent=2, ensure_ascii=False, default=str) + "\n", sd / PS.HIDDEN_NAME)
        print(f"wrote {sd / PS.SET_NAME} and {sd / PS.HIDDEN_NAME}")
        return 0
    if args.pcmd == "run":
        from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort
        from assistant_axis.gapgen.runs import git_sha, platform_dirty_files
        from assistant_axis.judge_pricing import BudgetExceededError
        if not (sd / PS.SET_NAME).exists():
            print(f"REFUSED: no {sd / PS.SET_NAME}; run paraphrase-set build first", file=sys.stderr)
            return 2
        items = PS.read_set(sd / PS.SET_NAME)
        est = PS.estimate(items)
        print(f"{len(items)} items, Haiku 5.5, one call each:\n{est.format()}")
        try:
            cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                                   confirmed_by=args.confirmed_by)
        except CostRefused:
            return 2
        dirty = platform_dirty_files()
        if dirty and not args.allow_dirty:
            print(f"REFUSED: uncommitted changes to the platform's own code or prompt paths ({len(dirty)}); commit "
                  "first, or pass --allow-dirty", file=sys.stderr)
            return 2
        if args.dry_run:
            sys_text = PS.system_prompt()
            print(f"DRY-RUN: hard cap ${cap:.2f}; the first request:\n[system]\n{sys_text}\n\n[user]\n"
                  f"{PS.render_user(items[0])}")
            return 0
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        client = anthropic.AsyncAnthropic(max_retries=0)
        usage = GuardedUsage(budget_usd=cap, usage_path=sd / PS.USAGE_NAME)
        run_meta = {"batch_id": PS.BATCH_ID, "git_sha": git_sha(), "argv": sys.argv[1:], "model": PS.MODEL,
                    "rubric": {k: v for k, v in PS.load_rubric().items() if k != "text"}, "n_items": len(items),
                    "estimate_usd": round(est.usd, 4), "budget_usd": args.budget_usd, "cap_usd": cap,
                    "confirmed_by": args.confirmed_by, "allow_dirty": bool(args.allow_dirty), "dirty": dirty,
                    "resumed": bool(args.resume), "started_at": utc_now()}
        status = 0
        try:
            answers = PS.run(items, client=client, usage=usage, out_dir=sd, resume=args.resume, traits=traits)
        except BudgetExceededError as exc:
            print(f"STOPPED: {exc}", file=sys.stderr)
            answers, status = PS.read_answers(sd / PS.ANSWERS_NAME), 2
        n = PS.to_scratch_registry(items, answers, regions, sd / PS.REGISTRY_NAME)
        run_meta.update(finished_at=utc_now(), status=status, cost_usd=round(usage.total_cost_usd, 6), n_rows=n,
                        n_answered=sum(1 for a in answers if a.get("answered")),
                        n_reasked=sum(1 for a in answers if a.get("reasked")),
                        n_label_path=sum(1 for a in answers if a.get("label_path")))
        atomic_write_text(json.dumps(run_meta, indent=2) + "\n", sd / "run.json")
        print(usage.log_line())
        print(f"scratch registry: {n} rows at {sd / PS.REGISTRY_NAME}\nnext, the harness (about $1.5, cap $4):\n"
              f"  {PS.harness_command(sd)}")
        return status
    if args.pcmd == "report":
        bd = Path(args.recovery_root) / args.batch
        if not bd.exists():
            print(f"REFUSED: no harness batch {bd}", file=sys.stderr)
            return 2
        md = PS.report(bd, set_path=sd / PS.SET_NAME, answers_path=sd / PS.ANSWERS_NAME,
                       registry_path=sd / PS.REGISTRY_NAME, candidates_dir=Path(args.candidates_dir), data_dir=data_dir,
                       report_dir=sd)
        if args.dry_run:
            print(md)
            return 0
        atomic_write_text(md, sd / PS.REPORT_NAME)
        print(f"wrote {sd / PS.REPORT_NAME}")
        return 0
    return 2


# --------------------------------------------------------------------------- the parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    def common(p):
        p.add_argument("--registry", type=Path, default=None,
                       help="a registry log or snapshot (default the tracked snapshot; --live for the checkout's log)")
        p.add_argument("--live", action="store_true", help="read the checkout's live registry log")
        p.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
        p.add_argument("--regions", type=Path, default=paths.CORPUS_REGIONS_PATH)
        p.add_argument("--graph", type=Path, default=None)
        p.add_argument("--review-root", type=Path, default=REVIEW_ROOT)
        p.add_argument("--recovery-root", type=Path, default=RECOVERY_ROOT)
        p.add_argument("--candidates-dir", type=Path, default=paths.DATA_CANDIDATES)
        p.add_argument("--out", type=Path, default=TESTING_DIR)
        p.add_argument("--idle-s", type=float, default=RM.IDLE_S)
        p.add_argument("--dry-run", action="store_true")

    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("independence")
    common(p)
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_independence)
    p = sub.add_parser("review-rate")
    common(p)
    p.add_argument("--batch", nargs="+", default=None)
    p.set_defaults(func=cmd_review_rate)
    p = sub.add_parser("repetition")
    common(p)
    p.add_argument("--level", type=int, nargs="+", choices=(3, 4), default=[3, 4])
    p.set_defaults(func=cmd_repetition)
    for name, fn in (("concepts", cmd_concepts), ("estimate", cmd_estimate)):
        p = sub.add_parser(name)
        common(p)
        p.add_argument("--unit", nargs="+", choices=("components_4", "grown_3"), default=["components_4", "grown_3"])
        p.add_argument("--tau", type=float, default=C.DEFAULT_TAU)
        if name == "estimate":
            p.add_argument("--by-region", action="store_true")
        p.set_defaults(func=fn)
    p = sub.add_parser("simulate")
    common(p)
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--occasions", type=int, default=4)
    p.add_argument("--sigma", type=float, default=1.0)
    p.add_argument("--rho", type=float, default=0.3)
    p.add_argument("--replicates", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_simulate)
    p = sub.add_parser("recovery-extras")
    common(p)
    p.add_argument("--batch", required=True)
    p.add_argument("--c", type=int, default=RX.STRICT_C)
    p.add_argument("--send-opus", action="store_true", help="not built (no recorded batch has needed it)")
    p.add_argument("--budget-usd", type=float, default=1.0)
    p.set_defaults(func=cmd_recovery_extras)
    p = sub.add_parser("roger-sample")
    common(p)
    p.add_argument("--batch", required=True)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_roger_sample)
    p = sub.add_parser("dashboard")
    common(p)
    p.add_argument("--harness", nargs="+", default=None, help="the harness batches to read (default: every one)")
    p.set_defaults(func=cmd_dashboard)
    p = sub.add_parser("paraphrase-set")
    psub = p.add_subparsers(dest="pcmd", required=True)
    from assistant_axis.gapgen.testing import PARAPHRASE_SET_DIR
    for name in ("build", "run", "report"):
        q = psub.add_parser(name)
        common(q)
        q.add_argument("--set-dir", type=Path, default=PARAPHRASE_SET_DIR)
        if name == "build":
            q.add_argument("--n-single", type=int, default=40)
            q.add_argument("--n-pairs", type=int, default=40)
            q.add_argument("--seed", type=int, default=0)
        if name == "run":
            q.add_argument("--budget-usd", type=float, required=True)
            q.add_argument("--resume", action="store_true")
            q.add_argument("--allow-dirty", action="store_true")
            q.add_argument("--confirm-expensive", action="store_true")
            q.add_argument("--confirmed-by", default=None)
        if name == "report":
            q.add_argument("--batch", default="rec_testing_paraphrase_set")
        q.set_defaults(func=cmd_paraphrase)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
