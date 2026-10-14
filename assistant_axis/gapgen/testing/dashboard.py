"""The generator dashboard: one row per generator, from what the platform recorded (plan 13 § 6, "Dashboard row";
§ 10, the pilot).  Nothing is generated or judged here.

Per generator: its class and mechanism (:mod:`.independence`), cost by stage (:func:`cost_by_run`), the funnel
(candidates, M1's verdicts, M3's decisions), the regions of its kept terms, repetition (:mod:`.repetition`), the
review's figures and the promote share (:mod:`.review_minutes`), **string recall** (the corpus stems its rows name,
separator-blind, stem or ``renamed_from``, of the corpus), **negatives** (the words Roger turned down in the seed
queue that it proposed again), the harness's recall where a batch covers it (``n/a`` otherwise, never 0), and the
**stop rule** (:func:`stop_rule`): expected accepted terms per minute of Roger's review.

Cost attribution (:func:`cost_by_run`).  Every ``usage.json`` (and the generators' ``*_usage*.json``) under
``data/candidates/`` is read once.  A generator run's own file goes to its run; an M1 or M3 batch to the run its
``run.json`` argv names with ``--run G/R`` (several: pro rata by the batch's rows), a ``--keys`` or states-pass
batch pro rata by its rows' generators (a states-pass row for its source row's), a re-decided or replayed run as its
source batch; an R1 build pro rata by its kept rows; a recovery batch to the harness line of its run (a pooled batch
pro rata by its rows); a reduced-corpus M3 run is part of its recovery batch's file and is not read again.  What
names no generator (calibration, development probes, the corpus-region runs, the states pass's own calls) is
listed as unattributed.  The attributed lines and the unattributed ones sum to everything read.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from .. import novelty as NV
from . import independence as IND
from .repetition import adjacency, kept_nodes, node_generators, pair_levels

SCHEMA_VERSION = 1
KEPT = ("new", "grey")
STAGES = ("generator", "m1", "m3", "r1", "harness")


# --------------------------------------------------------------------------- string recall and negatives

def corpus_names(traits: Mapping[str, NV.CorpusTrait]) -> dict[str, str]:
    """``{blind name: corpus stem}`` for every corpus stem and ``renamed_from``."""
    out = {}
    for s, t in traits.items():
        out.setdefault(NV.blind(s), s)
        for o in t.renamed_from:
            out.setdefault(NV.blind(o), s)
    return out


def string_recall(rows: Iterable[Mapping], names: Mapping[str, str], n_corpus: int) -> dict:
    """The corpus stems the rows name, separator-blind (``names``: :func:`corpus_names`)."""
    got = {names[NV.blind(r["stem"])] for r in rows if r.get("stem") and NV.blind(r["stem"]) in names}
    return {"n": len(got), "of": n_corpus, "share": round(len(got) / n_corpus, 4) if n_corpus else None,
            "stems": sorted(got)}


def negative_names(queue: Mapping, corpus_stems: Iterable[str]) -> set[str]:
    """The words Roger turned down: every seed-queue entry of a trait with status ``not_adopted`` or
    ``superseded``, its stem and its normalised label, less any that is a corpus stem now (separator-blind)."""
    from assistant_axis.entity_id import normalize_to_file_name
    corpus = {NV.blind(s) for s in corpus_stems}
    out = set()
    for e in (queue or {}).get("entries") or []:
        if e.get("status") not in ("not_adopted", "superseded") or (e.get("entity_type") or "trait") != "trait":
            continue
        for n in (e.get("stem"), normalize_to_file_name(e["label"]) if e.get("label") else None):
            if n and NV.blind(n) not in corpus:
                out.add(n)
    return out


def negative_hits(rows: Iterable[Mapping], names: set[str]) -> dict:
    blind = {NV.blind(n): n for n in names}
    hit = {blind[NV.blind(r["stem"])] for r in rows if r.get("stem") and NV.blind(r["stem"]) in blind}
    return {"hit": len(hit), "of": len(names), "names": sorted(hit)}


# --------------------------------------------------------------------------- costs

def _read_json(p: Path) -> Optional[dict]:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _usage_cost(p: Path) -> float:
    d = _read_json(p) or {}
    return float(d.get("total_cost_usd") or 0.0)


def _argv_runs(argv: Sequence[str]) -> list[tuple[str, str]]:
    out = []
    for i, a in enumerate(argv):
        if a == "--run" and i + 1 < len(argv) and "/" in argv[i + 1]:
            g, r = argv[i + 1].split("/", 1)
            out.append((g, r))
    return out


def _argv_value(argv: Sequence[str], flag: str) -> Optional[str]:
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _keys_of(d: Path) -> list[str]:
    p = d / "results.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line)["key"])
            except (json.JSONDecodeError, KeyError):
                continue
    return out


def weights_from_keys(keys: Iterable[str], rows: Mapping[str, Mapping]) -> dict[tuple[str, str], float]:
    """Pro rata weights over (generator, run) for a set of rows: each row's weight split equally over the sources it
    counts for (a states-pass source replaced by its source row's; the pools kept, so nothing is lost)."""
    w: dict[tuple[str, str], float] = defaultdict(float)
    n = 0
    for k in keys:
        r = rows.get(k)
        if not r:
            continue
        srcs = IND.attributed_sources(r, rows) or [{"generator": s.get("generator"), "run_id": s.get("run_id")}
                                                    for s in r.get("sources") or []]
        if not srcs:
            continue
        n += 1
        for s in srcs:
            w[(s["generator"], s["run_id"])] += 1.0 / len(srcs)
    return {k: v / n for k, v in w.items()} if n else {}


@dataclass
class CostLines:
    generator: float = 0.0
    m1: float = 0.0
    m3: float = 0.0
    r1: float = 0.0
    harness: float = 0.0

    @property
    def total(self) -> float:
        return self.generator + self.m1 + self.m3 + self.r1 + self.harness

    def add(self, stage: str, usd: float) -> None:
        setattr(self, stage, getattr(self, stage) + usd)

    def as_dict(self) -> dict:
        return {k: round(getattr(self, k), 4) for k in STAGES} | {"total": round(self.total, 4)}


@dataclass
class CostReport:
    by_run: dict = field(default_factory=dict)          # (generator, run_id) -> CostLines
    unattributed: dict = field(default_factory=dict)    # file -> usd
    files: list = field(default_factory=list)            # every file read, with its stage and usd
    total_read: float = 0.0

    def by_generator(self) -> dict[str, CostLines]:
        out: dict[str, CostLines] = defaultdict(CostLines)
        for (g, _), c in self.by_run.items():
            for s in STAGES:
                out[g].add(s, getattr(c, s))
        return dict(out)

    def attributed_total(self) -> float:
        return sum(c.total for c in self.by_run.values())


GENERATOR_SIDE_FILES: dict[str, str] = {"base_model": "base_model/gloss_sense_usage_round*.json",
                                        "ipip": "ipip/**/*usage*.json", "roget": "roget/*usage*.json"}


def cost_by_run(rows: Mapping[str, Mapping], *, candidates_dir: Path) -> CostReport:
    """Every cost record under ``candidates_dir`` attributed (module docstring)."""
    cd = Path(candidates_dir)
    rep = CostReport()
    seen: set[Path] = set()

    def charge(path: Path, stage: str, weights: Mapping[tuple[str, str], float], usd: Optional[float] = None):
        usd = _usage_cost(path) if usd is None else usd
        seen.add(path.resolve())
        rep.total_read += usd
        rep.files.append({"path": str(path.relative_to(cd)), "stage": stage, "usd": round(usd, 6),
                          "to": sorted(f"{g}/{r}" for g, r in weights) if weights else None})
        if not weights:
            rep.unattributed[str(path.relative_to(cd))] = round(usd, 6)
            return
        for k, w in weights.items():
            rep.by_run.setdefault(k, CostLines()).add(stage, usd * w)

    # generator runs
    for p in sorted((cd / "runs").glob("*/*/usage.json")):
        g, r = p.parent.parent.name, p.parent.name
        charge(p, "generator", {(g, r): 1.0})
    for g, pattern in GENERATOR_SIDE_FILES.items():
        runs = sorted(p.name for p in (cd / "runs" / g).glob("*") if p.is_dir())
        w = {(g, r): 1.0 / len(runs) for r in runs} if runs else {}
        for p in sorted(cd.glob(pattern)):
            if p.resolve() not in seen:
                charge(p, "generator", w)

    # M1 and M3 batches (a --from-batch run is charged as its source)
    weights_of: dict[str, dict] = {}

    def batch_weights(kind: str, d: Path, run: Mapping) -> dict:
        argv = list(run.get("argv") or [])
        runs = _argv_runs(argv)
        if runs:
            if len(runs) == 1:
                return {runs[0]: 1.0}
            ks = _keys_of(d)
            w = {k: v for k, v in weights_from_keys(ks, rows).items() if k in set(runs)}
            tot = sum(w.values())
            return {k: v / tot for k, v in w.items()} if tot else {r: 1.0 / len(runs) for r in runs}
        src = _argv_value(argv, "--from-batch")
        if src:
            sd = d.parent / src
            if src not in weights_of and (sd / "run.json").exists():
                weights_of[src] = batch_weights(kind, sd, _read_json(sd / "run.json") or {})
            return weights_of.get(src, {})
        if "--keys" in argv or "--keys-file" in argv or "--unscored" in argv or run.get("pass") or \
                _argv_value(argv, "--holding"):
            return weights_from_keys(_keys_of(d), rows)
        return {}

    for kind, stage in (("filter", "m1"), ("novelty", "m3")):
        for d in sorted(p for p in (cd / kind).glob("*") if p.is_dir()):
            u = d / "usage.json"
            if not u.exists():
                continue
            run = _read_json(d / "run.json") or {}
            if kind == "novelty" and "hide" in run:
                seen.add(u.resolve())            # a reduced-corpus run: its recovery batch's usage.json has it
                continue
            w = batch_weights(kind, d, run)
            weights_of[d.name] = w
            charge(u, stage, w)

    # R1 builds: pro rata by kept rows
    for d in sorted(p for p in (cd / "review").glob("*") if p.is_dir()):
        u = d / "usage.json"
        if not u.exists():
            continue
        g = _read_json(d / "graph.json") or {}
        g = g.get("result", g)
        keys = [n["key"] for n in g.get("nodes") or [] if n.get("kind") == "candidate" and n.get("decision") in KEPT]
        charge(u, "r1", weights_from_keys(keys, rows))

    # recovery batches
    for d in sorted(p for p in (cd / "recovery").glob("*") if p.is_dir()):
        u = d / "usage.json"
        if not u.exists():
            continue
        run = _read_json(d / "run.json") or {}
        if run.get("pooled"):
            kf = d / "pooled_keys.txt"
            keys = [x.strip() for x in kf.read_text().splitlines() if x.strip()] if kf.exists() else []
            w = weights_from_keys(keys, rows)
        elif run.get("generator") and run.get("run_id"):
            w = {(run["generator"], run["run_id"]): 1.0}
        else:
            w = {}
        charge(u, "harness", w)

    # everything else: read and listed as unattributed
    for p in sorted(cd.rglob("*usage*.json")):
        if "cache" in p.relative_to(cd).parts or p.resolve() in seen or ".bak." in p.name:
            continue
        if p.parent.name.startswith("seed") and (p.parent.parent.parent.name == "recovery"):
            continue                             # a harness seed's own file: in the batch's usage.json
        charge(p, "other", {})
    return rep


# --------------------------------------------------------------------------- the stop rule

@dataclass
class StopRule:
    undecided_kept: int
    pre_handled: int
    terms: int
    groups: int
    singleton_terms: int
    grouped_terms: int
    expected_minutes: Optional[float]
    expected_accepted: Optional[float]
    novel_per_review_minute: Optional[float]
    novel_per_usd: Optional[float]
    share_used: Optional[float] = None
    share_borrowed: bool = False
    #: The same terms at the review's blended measured rate (terms and accepted terms per active minute over every
    #: shape, the pooled review rate; 2.43 and 0.42 on the TDA batch): the other end of the range the per-shape
    #: projection above sits in (plan 13 review, S2).
    blended_minutes: Optional[float] = None
    blended_accepted: Optional[float] = None
    blended_per_review_minute: Optional[float] = None
    blended_per_usd: Optional[float] = None

    def as_dict(self) -> dict:
        return asdict(self)


def term_groups(terms: Iterable[str], proposed_groups: Sequence[Sequence[str]]) -> list[list[str]]:
    """``terms`` grouped as the review would meet them: by the graph's proposed groups (a term in several, in its
    first; a proposed group counts once however many of ``terms`` it holds), a term in none alone."""
    left = set(terms)
    out = []
    for g in proposed_groups:
        mine = [k for k in g if k in left]
        if mine:
            out.append(sorted(mine))
            left -= set(mine)
    return out + [[k] for k in sorted(left)]


def in_proposed_groups(terms: Iterable[str], proposed_groups: Sequence[Sequence[str]]) -> set[str]:
    """The ``terms`` that sit in some proposed group of the graph (plan 13 § 6: "grouped by the graph's proposed
    groups"), whoever proposed the group's other members."""
    grouped = {k for g in proposed_groups for k in g}
    return {k for k in terms if k in grouped}


def stop_rule(*, undecided: set, pre_handled: set, proposed_groups: Sequence[Sequence[str]],
              singleton_mean_s: Optional[float], per_member_s: Optional[float], per_group_share: Optional[float],
              cost_usd: Optional[float], borrowed: bool = False, terms_per_minute: Optional[float] = None,
              accepted_per_minute: Optional[float] = None) -> StopRule:
    """Plan 13 § 6: over the undecided, not pre-handled kept terms, ``expected_minutes`` = (singleton terms x
    singleton_mean_s + grouped terms x per_member_s) / 60, a term being grouped when it sits in any proposed group of
    the graph (:func:`in_proposed_groups`; before the review of 2026-10-13 only when the group held another of the
    same generator's terms); ``expected_accepted`` = the groups those terms form (each proposed group one, each
    singleton one) x the per-group promote share (decision 3); their ratio, and accepted per dollar of the
    generator's cost.  Beside it, with ``terms_per_minute`` and ``accepted_per_minute`` (the review's blended
    measured rates), the same terms at the blended rate: minutes = terms / terms_per_minute, accepted = minutes x
    accepted_per_minute.  The two bracket the expectation: the per-shape figure leans on the share singletons were
    promoted at, the blended one on the TDA batch's mix of shapes."""
    terms = set(undecided) - set(pre_handled)
    groups = term_groups(terms, proposed_groups)
    grouped = len(in_proposed_groups(terms, proposed_groups))
    single = len(terms) - grouped
    mins = None
    if singleton_mean_s is not None and per_member_s is not None:
        mins = (single * singleton_mean_s + grouped * per_member_s) / 60.0
    acc = len(groups) * per_group_share if per_group_share is not None else None
    b_mins = len(terms) / terms_per_minute if terms_per_minute else None
    b_acc = b_mins * accepted_per_minute if b_mins is not None and accepted_per_minute is not None else None
    return StopRule(undecided_kept=len(undecided), pre_handled=len(set(undecided) & set(pre_handled)), terms=len(terms),
                    groups=len(groups), singleton_terms=single, grouped_terms=grouped,
                    expected_minutes=round(mins, 1) if mins is not None else None,
                    expected_accepted=round(acc, 1) if acc is not None else None,
                    novel_per_review_minute=round(acc / mins, 3) if acc is not None and mins else None,
                    novel_per_usd=round(acc / cost_usd, 2) if acc is not None and cost_usd else None,
                    share_used=per_group_share, share_borrowed=borrowed,
                    blended_minutes=round(b_mins, 1) if b_mins is not None else None,
                    blended_accepted=round(b_acc, 1) if b_acc is not None else None,
                    blended_per_review_minute=round(b_acc / b_mins, 3) if b_acc is not None and b_mins else None,
                    blended_per_usd=round(b_acc / cost_usd, 2) if b_acc is not None and cost_usd else None)


# --------------------------------------------------------------------------- the generator rows

@dataclass
class GeneratorRow:
    """One row of ``dashboard.json`` (plan 13 § 6; ``schema_version`` 1; fields are added, never renamed)."""
    generator: str
    cls: str
    mechanism: Optional[str]
    runs: list
    cost_usd: dict
    candidates: int
    m1: dict
    m3: dict
    regions_of_kept: dict
    repetition: dict
    review: dict
    string_recall: dict
    negatives: dict
    recall: dict
    stop_rule: dict
    streams: list = field(default_factory=list)
    attributed_via_states_pass: int = 0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["class"] = d.pop("cls")
        d["string_recall"] = {k: v for k, v in d["string_recall"].items() if k != "stems"}
        d["negatives"] = {k: v for k, v in d["negatives"].items() if k != "names"}
        return d


def blended_accepted_rate(rate: Any) -> Optional[float]:
    """Accepted terms per active minute of a pooled review rate (promoted over active minutes; 0.42 on the TDA
    batch), unrounded."""
    mins = getattr(rate, "active_minutes", None)
    promoted = getattr(rate, "promoted", None)
    return promoted / mins if mins and promoted is not None else None


def _pct(x: Optional[float], nd: int = 0) -> str:
    return "n/a" if x is None else f"{100 * x:.{nd}f}%"


def generator_names(rows: Mapping[str, Mapping]) -> list[str]:
    """Every generator with a source in the registry, in the order of :data:`independence.STREAMS`, the rest after."""
    have = {s.get("generator") for r in rows.values() for s in r.get("sources") or [] if s.get("generator")}
    order = list(dict.fromkeys(g for g, _ in IND.STREAMS))
    return [g for g in order if g in have] + sorted(have - set(order))


def harness_entries(generator: str, harness: Sequence[Mapping]) -> list[dict]:
    """A generator's figures from the harness batches given: a pooled batch's per-generator mean, or a single-run
    batch of one of its runs (``n/a`` stays ``None``)."""
    out = []
    for h in harness:
        rep = h.get("report") or {}
        ex = h.get("extras") or {}
        if rep.get("generator") == "pooled":
            m = ((rep.get("breakdown_mean") or {}).get("by_generator") or {}).get(generator)
            if not m:
                continue
            strict = (h.get("strict_by_generator") or {}).get(generator)
            pair = (h.get("pair_by_generator") or {}).get(generator)
            out.append({"batch": h["batch_id"], "scope": "pooled", "recall": m.get("recall"),
                        "precision": m.get("precision"), "false_cover_candidates": m.get("false_cover_candidates"),
                        "n_kept": m.get("n_kept"), "strict": strict, "pair": pair, "seeds": m.get("seeds")})
        elif rep.get("generator") == generator:
            mean = rep.get("mean") or {}
            seeds = ex.get("seeds") or []
            strict = [s["strict"]["recall"] for s in seeds if s.get("strict")]
            pair = [s["pair_recovery"]["share"] for s in seeds if s.get("pair_recovery")]
            out.append({"batch": h["batch_id"], "scope": f"run {rep.get('run_id')}", "recall": mean.get("recall_kept"),
                        "precision": mean.get("precision_kept"),
                        "false_cover_candidates": mean.get("false_cover_candidates"),
                        "n_kept": None, "strict": sum(strict) / len(strict) if strict else None,
                        "pair": sum(pair) / len(pair) if pair else None, "seeds": rep.get("n_seeds"),
                        "by_region": mean.get("kept_by_region"),
                        "recall_at_n": [x for s in seeds for x in (s.get("recall_at_n") or [])][-5:] or None})
    return out


def build_rows(rows: Mapping[str, Mapping], *, traits: Mapping[str, NV.CorpusTrait], queue: Mapping,
               graph: Mapping, independence: Sequence[Mapping], repetition: Mapping[tuple[str, int], Mapping],
               shares: Mapping[str, Any], rate: Any, costs: CostReport, harness: Sequence[Mapping] = (),
               ) -> list[GeneratorRow]:
    """The dashboard's rows (one per registry generator, the pools included and marked)."""
    names = corpus_names(traits)
    neg = negative_names(queue, traits)
    nodes = kept_nodes(graph)
    levels = pair_levels(graph, set(nodes))
    adj3 = adjacency(graph, 3, levels=levels)
    decided = {k for k, n in nodes.items() if (rows.get(k, {}).get("review") or {}).get("status")
               in ("accepted", "merged_into", "rejected")}
    proposed = [list(g) for g in graph.get("proposed_groups") or []]
    by_g_cost = costs.by_generator()
    ind_by = defaultdict(list)
    for r in independence:
        ind_by[r["generator"]].append(r)
    out = []
    for g in generator_names(rows):
        mine = [r for r in rows.values() if any(s.get("generator") == g for s in r.get("sources") or [])]
        via_sp = [r for r in rows.values() if g in IND.generators_of(r, rows)
                  and not any(s.get("generator") == g for s in r.get("sources") or [])]
        runs = sorted({s.get("run_id") for r in mine for s in r.get("sources") or [] if s.get("generator") == g})
        streams = ind_by.get(g, [])
        rule = IND.generator_streams(g)
        classes = sorted({s.cls for s in rule}) or ["not_a_generator"]
        mechs = sorted({s.mechanism for s in rule if s.mechanism})
        verdicts = Counter((r.get("filter") or {}).get("verdict") or "unfiltered" for r in mine)
        trait_rows = [r for r in mine if (r.get("filter") or {}).get("verdict") == "trait"]
        decs = Counter((r.get("novelty") or {}).get("decision") or "undecided" for r in trait_rows)
        exact = sum(1 for r in trait_rows if (r.get("novelty") or {}).get("reason") == "exact_label")
        kept_keys = {r["key"] for r in trait_rows if (r.get("novelty") or {}).get("decision") in KEPT}
        regions = Counter(((r.get("filter") or {}).get("region") or "none") for r in trait_rows
                          if r["key"] in kept_keys)
        # decided among its review terms (kept rows), as the promote share counts them; a covered row pulled into a
        # group by hand is decided too and counted apart
        rev = Counter((r.get("review") or {}).get("status") for r in mine if r["key"] in kept_keys
                      and (r.get("review") or {}).get("status") in ("accepted", "merged_into", "rejected"))
        rev_other = sum(1 for r in mine if r["key"] not in kept_keys
                        and (r.get("review") or {}).get("status") in ("accepted", "merged_into", "rejected"))
        share = shares.get(g)
        rep3, rep4 = repetition.get((g, 3)), repetition.get((g, 4))
        att = next(iter((rep3 or {}).get("attached_to_batch", {}).values()), None) if rep3 else None
        cost = by_g_cost.get(g, CostLines())
        # the stop rule over the generator's terms in the review graph
        gterms = {k for k, n in nodes.items() if g in node_generators(n)}
        undecided = gterms - decided
        pre = {k for k in undecided if adj3.get(k, set()) & decided}
        sr = stop_rule(undecided=undecided, pre_handled=pre, proposed_groups=proposed,
                       singleton_mean_s=getattr(rate, "singleton_mean_s", None),
                       per_member_s=getattr(rate, "per_member_s", None),
                       per_group_share=getattr(share, "per_group", None) if share else None,
                       cost_usd=cost.total or None, borrowed=bool(getattr(share, "borrowed", False)),
                       terms_per_minute=getattr(rate, "terms_per_active_minute", None),
                       accepted_per_minute=blended_accepted_rate(rate))
        h = harness_entries(g, harness)
        pooled_h = next((x for x in h if x["scope"] == "pooled"), None)
        side = any(s.harness_side_only for s in rule)
        out.append(GeneratorRow(
            generator=g, cls="/".join(classes), mechanism="/".join(mechs) or None, runs=runs,
            cost_usd={"generator": round(cost.generator, 4), "m1": round(cost.m1, 4), "m3": round(cost.m3, 4),
                      "r1_share": round(cost.r1, 4), "harness": round(cost.harness, 4) if cost.harness else None,
                      "total": round(cost.total, 4)},
            candidates=len(mine), m1={k: verdicts[k] for k in sorted(verdicts)},
            m3={"kept": len(kept_keys), "covered": decs.get("covered", 0), "exact_label": exact,
                "undecided": decs.get("undecided", 0)},
            regions_of_kept=dict(sorted(regions.items(), key=lambda kv: -kv[1])),
            repetition={"pre_handled_3": (rep3 or {}).get("share"), "pre_handled_4": (rep4 or {}).get("share"),
                        "attached_to_first_batch": (att or {}).get("share"),
                        "n_undecided": (rep3 or {}).get("n_undecided")},
            review={"decided": sum(rev.values()), "accepted": rev.get("accepted", 0), "merged": rev.get("merged_into", 0),
                    "rejected": rev.get("rejected", 0), "decided_not_kept": rev_other,
                    "promote_share_term": getattr(share, "per_term", None) if share else None,
                    "promote_share_group": getattr(share, "per_group", None) if share else None,
                    "borrowed": bool(getattr(share, "borrowed", False)) if share else None,
                    "groups_resolved": getattr(share, "n_groups", None) if share else None,
                    "by_shape": getattr(share, "by_shape", None) if share else None},
            string_recall=string_recall(mine, names, len(traits)),
            negatives=negative_hits(mine, neg),
            recall={"headline": (pooled_h or {}).get("recall"), "strict": (pooled_h or {}).get("strict"),
                    "pair": (pooled_h or {}).get("pair"), "precision": (pooled_h or {}).get("precision"),
                    "false_cover_candidates": (pooled_h or {}).get("false_cover_candidates"),
                    "harness_batch": (pooled_h or {}).get("batch"), "harness_side": side,
                    "batches": h},
            stop_rule=sr.as_dict(), streams=streams, attributed_via_states_pass=len(via_sp)))
    return out


def any_generator_string_recall(rows: Mapping[str, Mapping], traits: Mapping[str, NV.CorpusTrait]) -> dict:
    """The corpus stems any generator names (the pools left out)."""
    gen_rows = [r for r in rows.values() if any(s.get("generator") not in IND.POOL_GENERATORS
                                                for s in r.get("sources") or [])]
    return string_recall(gen_rows, corpus_names(traits), len(traits))


# --------------------------------------------------------------------------- estimates (from a concept table)

def _q_of(incidence: Mapping) -> dict[int, int]:
    return {int(k): v for k, v in (incidence.get("by_k") or {}).items()}


def estimates_from_table(table: Mapping, *, occasions: Sequence[str]) -> dict:
    """Chapman per occasion pair and Chao2 over ``occasions`` from a concept table's concepts (``mechanisms``)."""
    import itertools

    from . import estimators as E
    occ = [o for o in occasions if any(o in c["mechanisms"] for c in table["concepts"])]
    caught = {o: {c["id"] for c in table["concepts"] if o in c["mechanisms"]} for o in occ}
    pairs = []
    for a, b in itertools.combinations(occ, 2):
        n1, n2, m = len(caught[a]), len(caught[b]), len(caught[a] & caught[b])
        est = E.chapman(n1, n2, m)
        pairs.append({"a": a, "b": b, "n1": n1, "n2": n2, "m": m} | est.as_dict())
    q = Counter(len(set(c["mechanisms"]) & set(occ)) for c in table["concepts"])
    q.pop(0, None)
    out = {"occasions": occ, "chapman": pairs, "Q": {str(k): v for k, v in sorted(q.items())}}
    if len(occ) >= 2 and q:
        c2 = E.chao2(dict(q), len(occ))
        out["chao2"] = c2.as_dict() | {"Q1": q.get(1, 0), "Q2": q.get(2, 0), "S_obs": sum(q.values()),
                                       "classic": round(E.chao2_classic(dict(q), len(occ)), 1)}
        out["coverage"] = round(E.coverage_from_Q(dict(q)), 4)
    return out


def estimates_by_region(table: Mapping, *, occasions: Sequence[str]) -> dict:
    regions = sorted({c.get("region") or "none" for c in table["concepts"]})
    out = {}
    for reg in regions:
        sub = {"concepts": [c for c in table["concepts"] if (c.get("region") or "none") == reg]}
        out[reg] = {"n_concepts": len(sub["concepts"])} | estimates_from_table(sub, occasions=occasions)
    return out


def accumulation_by_mechanism(table: Mapping, rows: Mapping[str, Mapping], *, runs_root: Path,
                              mechanisms: Sequence[str]) -> dict:
    """Per mechanism: unique new concepts against candidates emitted, the mechanism's runs in date order and each run
    in its ``candidates.jsonl`` order (n counts every emitted candidate; a candidate that is not a kept term adds no
    concept), with the Chao extrapolation to twice the observed n and the end slope (over the last tenth)."""
    from ..normalize import make_key, normalize_candidate
    from . import estimators as E
    concept_of = {k: c["id"] for c in table["concepts"] for k in c["keys"]}
    gen_mech = {}
    for (g, _), s in IND.STREAMS.items():
        gen_mech.setdefault(g, s.mechanism)
    out = {}
    for mech in mechanisms:
        gens = sorted(g for g, m in gen_mech.items() if m == mech)
        order: list[str] = []
        runs_used = []
        for g in gens:
            for rd in sorted(p for p in (Path(runs_root) / g).glob("*") if (p / "candidates.jsonl").exists()):
                runs_used.append(f"{g}/{rd.name}")
                for line in (rd / "candidates.jsonl").read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    c = json.loads(line)
                    try:
                        n = normalize_candidate(c["surface"])
                    except Exception:  # noqa: BLE001 - a surface the registry refused
                        continue
                    order.append(make_key(n.stem, int(c.get("sense_id") or 1)))
        if not order:
            continue
        # n counts every emitted candidate; unique counts concepts among the kept ones
        cmap = {k: concept_of.get(k) for k in order}
        curve, seen, n = [], set(), 0
        step = max(1, len(order) // 200)
        for i, k in enumerate(order, 1):
            if cmap.get(k) is not None:
                seen.add(cmap[k])
            if i % step == 0 or i == len(order):
                curve.append((i, len(seen)))
        ab = E.abundance_counts(order, {k: v for k, v in cmap.items() if v is not None})
        ext = E.chao_extrapolate(curve, Q1=ab.get(1, 0), Q2=ab.get(2, 0), to_n=2 * len(order))
        out[mech] = {"runs": runs_used, "n_emitted": len(order), "unique": len(seen), "curve": curve,
                     "extrapolation": [(int(a), round(float(b), 1)) for a, b in ext],
                     "end_slope": round(E.end_slope(curve, max(1, len(order) // 10)), 4),
                     "Q1": ab.get(1, 0), "Q2": ab.get(2, 0)}
    return out


def alignment_occasions(rows: Mapping[str, Mapping], table: Mapping, *, runs=("2026-10-11-papers", "2026-10-11-b")
                        ) -> dict:
    """The alignment sweep as its own population (pre-registered question 7): its two runs as the occasions, overlap
    by registry row (the same normalised label) and by concept unit (kept rows only), Chapman on each."""
    from . import estimators as E
    a_run, b_run = runs
    keys = {r: {k for k, row in rows.items() if any(s.get("generator") == "alignment_sweep" and s.get("run_id") == r
                                                    for s in row.get("sources") or [])} for r in runs}
    concept_of = {k: c["id"] for c in table["concepts"] for k in c["keys"]}
    cs = {r: {concept_of[k] for k in keys[r] if k in concept_of} for r in runs}
    out = {"runs": list(runs)}
    for name, (s1, s2) in (("rows", (keys[a_run], keys[b_run])), ("kept_concepts", (cs[a_run], cs[b_run]))):
        n1, n2, m = len(s1), len(s2), len(s1 & s2)
        out[name] = {"n1": n1, "n2": n2, "m": m} | E.chapman(n1, n2, m).as_dict() if n1 and n2 else \
            {"n1": n1, "n2": n2, "m": m}
    return out


def corpus_occasion(rows: Mapping[str, Mapping], table: Mapping, traits: Mapping[str, NV.CorpusTrait], *,
                    occasions: Sequence[str]) -> dict:
    """The corpus as an occasion (Roger, 2026-10-12: occasions are the mechanisms and the corpus).  The population is
    every trait concept: the corpus's traits and the new concepts (the unit's kept concepts).  A mechanism catches a
    corpus trait when one of its rows was covered by it, by an overlap reading or the exact label (``covered_by``),
    and a new concept when one of its kept rows is in it.  Chapman of the corpus against each mechanism, and Chao2
    over the corpus and the mechanisms; ``left`` = N minus the corpus."""
    from . import estimators as E
    caught: dict[str, set] = defaultdict(set)
    for k, r in rows.items():
        nv = r.get("novelty") or {}
        cov = nv.get("covered_by")
        if nv.get("decision") != "covered" or not isinstance(cov, str) or cov not in traits:
            continue
        for m in IND.mechanisms_of(r, rows):
            caught[m].add(("corpus", cov))
    for c in table["concepts"]:
        for m in c["mechanisms"]:
            caught[m].add(("new", c["id"]))
    corpus = {("corpus", s) for s in traits}
    occ = [o for o in occasions if caught.get(o)]
    out = {"occasions": ["corpus"] + occ, "n_corpus": len(corpus), "chapman_with_corpus": []}
    for o in occ:
        n2 = len(caught[o])
        m = len(caught[o] & corpus)
        est = E.chapman(len(corpus), n2, m)
        out["chapman_with_corpus"].append({"mechanism": o, "n_corpus": len(corpus), "n_mechanism": n2, "m": m}
                                          | est.as_dict() | {"left": round(est.N - len(corpus), 1)})
    allc = corpus | set().union(*[caught[o] for o in occ]) if occ else corpus
    q = Counter()
    for x in allc:
        q[(x in corpus) + sum(1 for o in occ if x in caught[o])] += 1
    q.pop(0, None)
    if q and occ:
        c2 = E.chao2(dict(q), 1 + len(occ))
        out["chao2"] = c2.as_dict() | {"Q": {str(k): v for k, v in sorted(q.items())},
                                       "left": round(c2.N - len(corpus), 1)}
    return out


# --------------------------------------------------------------------------- the Markdown

def _num(x, fmt="{:,.0f}") -> str:
    return "n/a" if x is None else fmt.format(x)


def _blended(sr: Mapping, what: str) -> str:
    """The blended-rate figure beside a per-shape one in the table (empty when it is not known)."""
    if sr.get("blended_minutes") is None or sr.get("expected_accepted") is None:
        return ""
    if what == "accepted":
        return f" (blended: {_num(sr['blended_accepted'], '{:,.0f}')} in {_num(sr['blended_minutes'], '{:,.0f}')})"
    if what == "rate":
        return f" ({_num(sr['blended_per_review_minute'], '{:.2f}')} blended)"
    return f" ({_num(sr['blended_per_usd'], '{:.1f}')} blended)" if sr.get("blended_per_usd") is not None else ""


def render_markdown(dash: Mapping, *, rel: str = "../../../") -> str:
    """``dashboard.md`` (beside ``dashboard.json`` in ``data/candidates/testing/``; links relative to it)."""
    from .estimators import ASSUMPTIONS
    rows = dash["rows"]
    rr = dash.get("review_rate") or {}
    L = [f"# Generator dashboard ({dash['produced_at'][:10]})", "",
         "Plan 13's one table per generator ([coding_plan_13_generator_testing.md]"
         f"({rel}reports/trait_gap_generation/coding_plan_13_generator_testing.md)), built by "
         f"[generator_dashboard.py]({rel}data_analysis/gap_generation/generator_dashboard.py) from what the platform "
         "recorded; nothing here was generated or judged.  Terms are defined in the "
         f"[glossary]({rel}reports/trait_gap_generation/glossary.md).  Every figure is in "
         "[dashboard.json](./dashboard.json); the parts are [independence.json](./independence.json), "
         "[review_rates.json](./review_rates.json), [repetition.json](./repetition.json), "
         "[concepts.json](./concepts.json), [estimates.json](./estimates.json) and "
         "[simulation.json](./simulation.json).", "",
         f"Inputs: the registry {dash['inputs']['registry']}, the review graph "
         f"[{dash['inputs']['graph_batch']}]({rel}data/candidates/review/{dash['inputs']['graph_batch']}/graph.json), "
         f"the review logs of {', '.join(dash['inputs']['review_batches'])} (figures that lag review are as of "
         f"{dash['inputs'].get('review_as_of') or 'n/a'}), and the harness batches "
         f"{', '.join(dash['inputs']['harness_batches']) or 'none'}.", ""]
    L += ["## The table", "",
          "| generator | class | mechanism | candidates | M1 trait | M3 kept / covered (exact label) | cost $ | "
          "pre-handled (3 / 4) | review decided (accepted) | promote share, group (term) | string recall | "
          "negatives | recall (strict, pair) | expected accepted in minutes | accepted per review-minute | "
          "accepted per $ |", "|" + "---|" * 16]
    for r in rows:
        rec = r["recall"]
        if rec.get("headline") is None:
            recall = "n/a"
        else:
            recall = (f"{_pct(rec['headline'], 1)} ({_pct(rec.get('strict'), 1)}, {_pct(rec.get('pair'), 1)})"
                      + (" harness side" if rec.get("harness_side") else ""))
        sr = r["stop_rule"]
        rv = r["review"]
        share = (f"{_pct(rv['promote_share_group'])} ({_pct(rv['promote_share_term'])})"
                 + (", borrowed" if rv.get("borrowed") else "")) if rv.get("promote_share_group") is not None else "n/a"
        L.append(f"| {r['generator']} | {r['class']} | {r['mechanism'] or ''} | {r['candidates']:,} | "
                 f"{r['m1'].get('trait', 0):,} | {r['m3']['kept']:,} / {r['m3']['covered']:,} ({r['m3']['exact_label']}) | "
                 f"{r['cost_usd']['total']:.2f} | {_pct(r['repetition']['pre_handled_3'])} / "
                 f"{_pct(r['repetition']['pre_handled_4'])} | {rv['decided']} ({rv['accepted']}) | {share} | "
                 f"{r['string_recall']['n']} ({_pct(r['string_recall']['share'], 1)}) | {r['negatives']['hit']} | "
                 f"{recall} | {_num(sr['expected_accepted'], '{:,.1f}')} in {_num(sr['expected_minutes'], '{:,.0f}')}"
                 f"{_blended(sr, 'accepted')} | {_num(sr['novel_per_review_minute'], '{:.2f}')}"
                 f"{_blended(sr, 'rate')} | {_num(sr['novel_per_usd'], '{:.1f}')}{_blended(sr, 'usd')} |")
        for st in r.get("streams") or []:
            if len(r.get("streams") or []) > 1 and len({x["class"] for x in r["streams"]}) > 1:
                L.append(f"| &nbsp;&nbsp;{r['generator']}/{st['stream']} | {st['class']} | {st['mechanism'] or ''} | "
                         f"{st['n_rows']:,} | {st['n_trait']:,} | {st['n_kept']:,} kept | | | | | | | | | | |")
    ar = dash.get("string_recall_any") or {}
    L += ["", f"Any generator names {ar.get('n')} of {ar.get('of')} corpus stems by string ({_pct(ar.get('share'), 1)}).",
          "",
          "**Reading the columns.**  *Pre-handled*: undecided kept terms with a 3-edge (4-edge) to a term review has "
          "decided; they cost no review-minute.  *Promote share*: promote resolutions over resolved groups (decision 3), "
          "per term in brackets; *borrowed*: under 50 decided terms, the pooled share.  *String recall*: corpus stems "
          "the generator's rows name, separator-blind, of the corpus.  *Negatives*: words Roger turned down in the seed "
          "queue that the generator proposed again.  *Recall*: the harness's mean recall over its kept candidates "
          "(n/a: no harness batch covers it yet), the strict column at cut-off 4 and pair recovery beside it; *harness "
          "side*: a seeded generator, no generator-side hiding.  *Expected accepted*: the groups its undecided, not "
          "pre-handled kept terms form times the per-group promote share; the minutes from the measured times per "
          "shape (a term in any proposed group is priced as a group member, the rest as singletons).  *Blended*, in "
          "brackets: the same terms at the review's measured overall rates (terms and accepted terms per active "
          "minute), the other end of the range.  The per-shape figure leans on the share at which singletons were "
          "promoted, measured on about forty resolved singletons (a 95% interval of roughly 0.37-0.66) that the app "
          "surfaced first in the TDA batch; the generators' remaining singletons need not resemble them.", ""]
    # recorded harness batches
    hb = [(r["generator"], h) for r in rows for h in r["recall"].get("batches") or []]
    if hb:
        L += ["## Recall from the recorded harness batches", "",
              "Each batch tested one pilot run, at seed 0 only, under the rule sets before rule set 3 (2026-10-08); "
              "the decision-1 pooled batch, when it is run, fills the table's recall column for every generator.", "",
              "| generator | batch | scope | recall (mean over seeds) | strict, at 4 | pair recovery | precision | "
              "false-cover candidates |", "|---|---|---|---|---|---|---|---|"]
        for g, h in hb:
            L.append(f"| {g} | [{h['batch']}]({rel}data/candidates/recovery/{h['batch']}/recovery_report.md) | "
                     f"{h['scope']} | {_pct(h.get('recall'), 1)} | {_pct(h.get('strict'), 1)} | {_pct(h.get('pair'), 1)} | "
                     f"{_pct(h.get('precision'), 1)} | {_num(h.get('false_cover_candidates'), '{:g}')} |")
        L.append("")
    # costs
    L += ["## Cost by stage (USD)", "", "| generator | generator | M1 | M3 | R1 share | harness | total |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        c = r["cost_usd"]
        L.append(f"| {r['generator']} | {c['generator']:.2f} | {c['m1']:.2f} | {c['m3']:.2f} | {c['r1_share']:.2f} | "
                 f"{_num(c['harness'], '{:.2f}')} | {c['total']:.2f} |")
    co = dash.get("costs") or {}
    L += ["", f"Read {co.get('n_files')} cost records, ${co.get('total_read', 0):.2f} in all: "
          f"${co.get('attributed', 0):.2f} attributed to generator runs, ${co.get('unattributed', 0):.2f} not "
          "attributed (calibration, development probes, corpus regions, the passes' own calls).", ""]
    # review rate
    if rr:
        L += ["## Review rate", "",
              f"Pooled over {', '.join(rr.get('batches') or [])}: {rr.get('terms')} terms in {rr.get('active_minutes')} "
              f"active minutes, {rr.get('terms_per_active_minute')} terms a minute; a singleton {rr.get('singleton_mean_s')} s,"
              f" a grouped term {rr.get('per_member_s')} s.  Left out as too small: "
              f"{', '.join(rr.get('left_out') or []) or 'none'}.  Pooled promote share: per group "
              f"{_pct((dash.get('promote_share_pooled') or {}).get('per_group'), 1)}, per term "
              f"{_pct((dash.get('promote_share_pooled') or {}).get('per_term'), 1)}; by shape "
              f"{json.dumps((dash.get('promote_share_pooled') or {}).get('by_shape'))}; holding-list passes left out of "
              f"the share: {', '.join(dash.get('promote_share_left_out') or []) or 'none'}.", ""]
    # concepts and estimates
    ce = dash.get("concepts_summary") or []
    if ce:
        L += ["## Concept units (decision 2: Roger names the headline)", "",
              "| unit | units | singletons | largest | kept together | one concept | hard negatives joined | "
              "Chao2 (three occasions) | Chao2 (four, with the alignment sweep) |", "|---|---|---|---|---|---|---|---|---|"]
        for c in ce:
            ag = c.get("agreement") or {}
            L.append(f"| {c['label']} | {c['n_concepts']:,} | {c['n_singletons']:,} | {c['largest']} | "
                     f"{_pct(ag.get('kept_together'))} | {_pct(ag.get('one_concept'))} | "
                     f"{ag.get('hard_negatives_joined')} of {ag.get('n_negatives')} | "
                     f"{_num((c.get('chao2_3') or {}).get('N'))} ({_num((c.get('chao2_3') or {}).get('lo'))}-"
                     f"{_num((c.get('chao2_3') or {}).get('hi'))}) | {_num((c.get('chao2_4') or {}).get('N'))} |")
        L += ["", "*Kept together*: of the pairs of decided candidates Roger made one concept, the share one unit holds; "
              "*one concept*: of the decided pairs sharing a unit, the share Roger made one concept; *hard negatives*: "
              "pairs he marked distinct or dropped from a group the graph had proposed.  Chao2 over the three "
              "occasions of the main population (the lexicon walks, IPIP, the base model; the masked LM has no run "
              "yet); the alignment sweep is a separate population and is printed apart.", ""]
        L += ["Assumptions of every estimate (printed each time):", ""] + [f"- {a}" for a in ASSUMPTIONS] + [""]
    for e in dash.get("estimates_summary") or []:
        L += [f"### Estimates at {e['label']}", "",
              "| occasions | concepts seen | N̂ (95% interval) | coverage | left (N̂ minus seen) |", "|---|---|---|---|---|"]
        for name, x in (("lexicon, IPIP, base model", e.get("three")), ("the same and the alignment sweep", e.get("four"))):
            c = (x or {}).get("chao2") or {}
            L.append(f"| {name} | {_num(c.get('S_obs'))} | {_num(c.get('N'))} ({_num(c.get('lo'))}-{_num(c.get('hi'))}) | "
                     f"{_pct((x or {}).get('coverage'))} | {_num((c.get('N') or 0) - (c.get('S_obs') or 0) if c else None)} |")
        co = e.get("corpus") or {}
        cc = co.get("chao2") or {}
        L += ["", f"With the corpus as an occasion (its {co.get('n_corpus')} traits a sample of all trait concepts; a "
              f"generator catches a corpus trait when one of its rows was covered by it): Chao2 N̂ {_num(cc.get('N'))} "
              f"({_num(cc.get('lo'))}-{_num(cc.get('hi'))}), so about **{_num(cc.get('left'))} concepts not in the "
              "corpus**.  Chapman of the corpus with each mechanism:", "",
              "| mechanism | concepts it caught | of them corpus traits | N̂ (95% interval) | left |", "|---|---|---|---|---|"]
        for c in co.get("chapman_with_corpus") or []:
            L.append(f"| {c['mechanism']} | {c['n_mechanism']:,} | {c['m']:,} | {_num(c['N'])} ({_num(c['lo'])}-"
                     f"{_num(c['hi'])}) | {_num(c['left'])} |")
        L += ["", "Chapman between mechanisms (new concepts only):", "",
              "| pair | n1 | n2 | shared | N̂ (95% interval) |", "|---|---|---|---|---|"]
        for c in (e.get("three") or {}).get("chapman") or []:
            L.append(f"| {c['a']} x {c['b']} | {c['n1']:,} | {c['n2']:,} | {c['m']} | {_num(c['N'])} ({_num(c['lo'])}-"
                     f"{_num(c['hi'])}) |")
        L += ["", "Accumulation per mechanism (every candidate it emitted, in its runs' order; a candidate that is not "
              "a kept term adds no concept):", "",
              "| mechanism | candidates emitted | new concepts | end slope (concepts per candidate, last tenth) | "
              "projected at twice the output |", "|---|---|---|---|---|"]
        for m, a in (e.get("accumulation") or {}).items():
            L.append(f"| {m} | {a['n_emitted']:,} | {a['unique']:,} | {a['end_slope']:.3f} | "
                     f"{_num(a['extrapolation'][-1][1] if a.get('extrapolation') else None)} |")
        al = e.get("alignment") or {}
        if al:
            kc = al.get("kept_concepts") or {}
            L += ["", f"The alignment sweep as its own population (its papers run and variant B as the occasions, "
                  f"overlap by concept unit): {kc.get('n1')} and {kc.get('n2')} concepts, {kc.get('m')} shared, Chapman "
                  f"N̂ {_num(kc.get('N'))} ({_num(kc.get('lo'))}-{_num(kc.get('hi'))}).", ""]
    samples = dash.get("unit_samples") or {}
    if samples:
        L += ["## Reading lists for decision 2 (twenty units of each kind, seeded, two or more members)", ""]
        for unit, xs in samples.items():
            L += [f"**{unit}**", ""] + [f"{i}. ({x['size']}) " + ", ".join(x["labels"]) for i, x in enumerate(xs, 1)] + [""]
    sim = dash.get("simulation_table")
    if sim:
        L += ["## The estimators on simulated data", "", sim, ""]
    return "\n".join(L) + "\n"


def load_dashboard(path: Optional[Path] = None) -> dict:
    """The dashboard as last written (the frozen interface): ``dashboard.json``'s payload (its envelope removed)."""
    from . import DASHBOARD_JSON_PATH
    d = json.loads(Path(path or DASHBOARD_JSON_PATH).read_text(encoding="utf-8"))
    return d.get("result", d)


__all__ = ["SCHEMA_VERSION", "corpus_names", "string_recall", "negative_names", "negative_hits", "weights_from_keys",
           "CostLines", "CostReport", "cost_by_run", "StopRule", "term_groups", "in_proposed_groups", "stop_rule",
           "blended_accepted_rate", "GeneratorRow",
           "generator_names", "harness_entries", "build_rows", "any_generator_string_recall", "estimates_from_table",
           "estimates_by_region", "accumulation_by_mechanism", "alignment_occasions", "corpus_occasion",
           "render_markdown", "load_dashboard"]
