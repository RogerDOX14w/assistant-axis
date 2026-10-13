"""Workstream 11's retroactive sweep: the overlap call on every lexical-only pair of the recorded kept rows.

The plan is ``reports/trait_gap_generation/coding_plan_11_novelty_ensemble.md`` (§ 5-7, § 10); the lexicon side is
:mod:`assistant_axis.gapgen.lexical`; the CLI ``data_analysis/gap_generation/lexical_recall.py``.

* :func:`sweep_plan`: for every kept row (an M3 ``novelty`` block decided ``new`` or ``grey``, every pass: the trait
  track, the physical and the states passes), its lexical neighbours that the block never listed, read or covered by
  (the *lexical-only pairs*), each with its cosine from the cached embeddings and the row's own cut-off rule (the rule
  set the block records, :func:`novelty.rules_of`; the graded rule's band when the block records it).  A name-only link
  (a queue entry with no text), and a Moby-only pair under :data:`lexical.MOBY_COSINE_FLOOR` (or with no cosine), are
  ``judged: false``.
* :func:`run_sweep`: Sonnet then Opus on every judgeable pair, each under its row's cut-off rule
  (:meth:`novelty_runner.NoveltyRunner.read_pairs`, as the recovery harness reads a candidate against a hidden trait),
  and :func:`recovery.pair_outcome` under the row's rule set: ``at_cut_off`` is "M3 would have covered the row on this
  pair had it been listed".  The sweep never flips an M3 decision.
* :func:`lexical_block`: the row's ``lexical`` registry block (§ 6), written beside the untouched ``novelty`` block.
* :func:`sweep_report` / :func:`sweep_markdown`: the readout, the stop-rule line first; :func:`dry_readout` /
  :func:`dry_markdown`: the free gate-1 readout; :func:`marks_sheet`, :func:`parse_marks_markdown`,
  :func:`fold_marks`: Roger's blind marks on up to 40 covers (open decision 2), in the cover audit's form.

No API call is made here except through the runner the caller hands to :func:`run_sweep`.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from . import lexical as LX
from . import novelty as NV
from .lexical import labelled_measurement  # noqa: F401 - re-exported (plan § 5 lists it here)
from .novelty_runner import M3Candidate

# --------------------------------------------------------------------------- constants

PASSES: tuple[str, ...] = ("trait", "physical", "states")
KEPT_DECISIONS: tuple[str, ...] = ("new", "grey")
#: Why a pair is not judged.
NOT_JUDGED: tuple[str, ...] = ("listed_by_m3", "name_only", "moby_below_floor", "moby_no_cosine", "moby_over_cap",
                               "no_description", "not_sampled")
#: The block's flags (§ 6).
FLAGS: tuple[str, ...] = ("lexical_cover", "lexical_below_cut", "lexical_name_only", "lexical_unparsed",
                          "lexical_antonym")
#: The gate audit's five retrieval misses (``reports/code_review_2026-10-12/gate_audits/m3_novelty.md`` § 7.2): the
#: candidate and the trait the audit found it should have been covered by.
AUDIT_RETRIEVAL_MISSES: dict[str, str] = {"delightful#1": "agreeable", "pleasant#1": "agreeable", "nice#1": "agreeable",
                                          "annoying#1": "disagreeable", "unsteadfast#1": "submissive"}
#: The share of pairs Opus reads, before the sweep measures it: 0.40 in M3's full scan, 0.62 on its shortlists
#: (``novelty_runner.OPUS_SHARE_FULL_SCAN`` / ``OPUS_SHARE_SHORTLIST``); lexical-only pairs are far pairs, so the
#: lower is the likelier, and the estimate prices the higher.
OPUS_SHARE_ASSUMED: tuple[float, float] = (0.40, 0.62)
DEFAULT_BUDGET_USD = 10.0
#: The stop rule (plan § 8): fewer than about this many real covers stops the plan before the integration.
STOP_LINE_COVERS = 5
#: The build line on Roger's marks (open decision 2): about 36 of 40 marked covers confirmed, read as 90% of those
#: marked when there are fewer than 40, with at least the stop line confirmed (QUESTIONS 132).
BUILD_LINE_SHARE = 0.9
MARKS_MAX = 40
MARK_CODES: dict[str, str] = {"C": "covered: the existing trait already does this job (a real miss of M3's retrieval)",
                              "N": "new: the candidate is a different trait (the lexical link is a coincidence)",
                              "?": "unsure, or the gloss misreads the word"}


# --------------------------------------------------------------------------- rows

def row_pass(row: Mapping) -> str:
    """A row's pass: the ``novelty`` block's ``pass`` (``physical``, ``states``) or ``trait``."""
    return (row.get("novelty") or {}).get("pass") or "trait"


def kept_rows(rows: Mapping[str, Mapping], passes: Optional[Iterable[str]] = None) -> dict[str, dict]:
    """The rows whose ``novelty`` block is decided ``new`` or ``grey`` (the kept rows), of ``passes`` (default all)."""
    want = set(passes or PASSES)
    return {k: dict(r) for k, r in sorted(rows.items())
            if (r.get("novelty") or {}).get("decision") in KEPT_DECISIONS and row_pass(r) in want}


def m3_seen(block: Mapping) -> set[str]:
    """The stems M3 listed, read or covered by for a row (the pairs some model has read or could have)."""
    out = {x["stem"] for x in block.get("listed") or [] if x.get("stem")}
    out |= {x["stem"] for x in block.get("readings") or [] if x.get("stem")}
    if block.get("covered_by"):
        out.add(block["covered_by"])
    return out


def row_rules(block: Mapping) -> tuple[NV.CutOff, NV.Rules]:
    """The cut-off rule and rule set a row was decided under: :func:`novelty.rules_of`, and the block's recorded
    ``cut_off_rule`` (rule set 3's graded rule) or the rule set's rule at its alignment score.  A recorded ``cut_off``
    that disagrees with the rebuilt one wins (as a fixed cut-off), so the sweep never reads a row at a cut-off other than
    its own."""
    rules = NV.rules_of(block)
    rec = block.get("cut_off_rule")
    if isinstance(rec, Mapping) and "c" in rec:
        spec = NV.CutOff(**{k: rec[k] for k in NV.CutOff.__dataclass_fields__ if k in rec})
    else:
        spec = NV.cut_off_spec(block.get("alignment_score"), rules)
    c = block.get("cut_off")
    if isinstance(c, int) and not isinstance(c, bool) and c != spec.c:
        spec = NV.as_cut_off(c)
    return spec, rules


def candidate_for(row: Mapping) -> Optional[M3Candidate]:
    """The row as M3 judged it (label, and the gloss its pass used: the physical pass's gloss stage, the states pass's
    block, else the row's own gloss), or ``None`` when no gloss is found."""
    from . import physical_pass as PP
    from . import states_pass as SP
    p = row_pass(row)
    gloss = None
    if p == PP.PASS_NAME:
        gloss = PP.gloss_of(row)
    elif p == SP.PASS_NAME:
        gloss = SP.gloss_of(row)
    gloss = gloss or row.get("gloss")
    if not (isinstance(gloss, str) and gloss.strip()):
        return None
    nv = row.get("novelty") or {}
    gens = list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))
    return M3Candidate(key=row["key"], stem=row["stem"], label=row["label"], gloss=gloss.strip(),
                       alignment_score=nv.get("alignment_score"), region=nv.get("region"), generators=gens)


@dataclass
class SweepCandidate(M3Candidate):
    """An :class:`M3Candidate` judged at its row's own recorded cut-off rule, whatever the runner's rules."""
    spec: Optional[NV.CutOff] = None

    def cut_off_spec(self, rules: Optional[NV.Rules] = None) -> NV.CutOff:
        return self.spec if self.spec is not None else super().cut_off_spec(rules)


def block_sha256(block: Optional[Mapping]) -> Optional[str]:
    """A hash of a registry block as JSON (sorted keys): the acceptance check that the sweep left it alone."""
    if block is None:
        return None
    return hashlib.sha256(json.dumps(block, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- the plan

@dataclass
class PairItem:
    key: str
    label: str
    gloss: Optional[str]
    pass_: str
    stem: str
    kind: str
    link: str
    lexicon: str
    name_only: bool
    word: Optional[str]
    via: Optional[str]
    also_found: list
    cosine: Optional[float]
    cut_off: dict
    rules: str
    alignment_score: Any
    position: int
    judged: bool = True
    not_judged: Optional[str] = None
    listed_by_m3: bool = False
    moby_only: bool = False

    def as_dict(self) -> dict:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        return d

    @classmethod
    def from_dict(cls, d: Mapping) -> "PairItem":
        d = dict(d)
        d["pass_"] = d.pop("pass", d.get("pass_", "trait"))
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


def cosine_fn(index, vectors: Mapping[str, Any]) -> Callable[[str, str], Optional[float]]:
    """``cosine(key, stem)`` from the cached candidate embeddings (``vectors``: key -> raw vector) projected into the
    index's covered space; ``None`` when the key has no vector or the stem is not in the index."""
    proj: dict[str, Any] = {}

    def cos(key: str, stem: str) -> Optional[float]:
        if index is None or key not in vectors:
            return None
        if key not in proj:
            proj[key] = index.project(np.asarray(vectors[key]))
        c = index.cosine_to(proj[key], stem)
        return None if c is None else round(float(c), 6)
    return cos


@dataclass
class RowPlan:
    key: str
    pass_: str
    links: list            # PairItem, lexical-only first then the listed-by-M3 ones
    antonyms: list         # lexical.Antonym
    family: list           # dicts
    spec: NV.CutOff
    rules: NV.Rules
    candidate: Optional[M3Candidate]


def sweep_plan(rows: Mapping[str, Mapping], lookup: LX.Lookup, index=None, vectors: Optional[Mapping] = None, *,
               hidden: Iterable[str] = (), descriptions: Optional[Mapping[str, str]] = None,
               candidates_for_family: Optional[Mapping[str, str]] = None,
               moby_floor: float = LX.MOBY_COSINE_FLOOR) -> tuple[list[PairItem], dict[str, RowPlan]]:
    """``(items, plans)``: every kept row's lexical neighbours (``rows``: kept rows by key, :func:`kept_rows`).
    ``items``: the lexical-only pairs (the block's ``listed``, ``readings`` and ``covered_by`` excluded, and ``hidden``),
    each with its cosine (``index`` and ``vectors``: the cached embeddings; ``None`` without), the row's cut-off rule,
    and ``judged`` / ``not_judged``: a name-only link (``name_only``), a target with no description to show
    (``no_description``), a Moby-only pair under ``moby_floor`` (``moby_below_floor``) or without a cosine
    (``moby_no_cosine``) are not judged.  ``plans``: per row, every link (the listed-by-M3 ones too, ``judged: false``),
    its antonym evidence and its stem family (members among the corpus, the queue and ``candidates_for_family``:
    ``{stem: label}``).  ``descriptions``: stem -> the text the overlap call shows (default: every target with a text
    counts as having one)."""
    cos = cosine_fn(index, vectors or {})
    hid = set(hidden)
    items: list[PairItem] = []
    plans: dict[str, RowPlan] = {}
    for key in sorted(rows):
        row = rows[key]
        nv = row.get("novelty") or {}
        spec, rules = row_rules(nv)
        cand = candidate_for(row)
        seen = m3_seen(nv)
        links = lookup.neighbours(row["label"], row["stem"], exclude=hid)
        row_items: list[PairItem] = []
        pos = 0
        for ln in links:
            listed = ln.stem in seen
            pos += 1
            c = cos(key, ln.stem)
            it = PairItem(key=key, label=row["label"], gloss=cand.gloss if cand else None, pass_=row_pass(row),
                          stem=ln.stem, kind=ln.kind, link=ln.link, lexicon=ln.lexicon, name_only=ln.name_only,
                          word=ln.word, via=ln.via, also_found=list(ln.also_found), cosine=c, cut_off=spec.as_dict(),
                          rules=rules.name, alignment_score=nv.get("alignment_score"), position=pos,
                          listed_by_m3=listed, moby_only=ln.moby_only)
            why = None
            if listed:
                why = "listed_by_m3"
            elif ln.name_only:
                why = "name_only"
            elif cand is None or (descriptions is not None and ln.stem not in descriptions):
                why = "no_description"
            elif ln.moby_only and c is None:
                why = "moby_no_cosine"
            elif ln.moby_only and c < moby_floor:
                why = "moby_below_floor"
            if why:
                it.judged, it.not_judged = False, why
            row_items.append(it)
            if not listed:
                items.append(it)
        fam = lookup.family_links(row["label"], row["stem"], candidates=candidates_for_family)
        plans[key] = RowPlan(key=key, pass_=row_pass(row), links=row_items,
                             antonyms=lookup.antonym_evidence(row["label"], row["stem"]), family=fam, spec=spec,
                             rules=rules, candidate=cand)
    return items, plans


# --------------------------------------------------------------------------- estimate and cap

def pair_prices(transport: str = "live") -> tuple[float, float]:
    """``(Sonnet, Opus)`` dollars a pair, from M3's measured tokens (``novelty_runner.OVERLAP_TOKENS``)."""
    from assistant_axis.judge_pricing import BATCH_SUFFIX, cost_for_usage

    from .novelty_runner import FIRST_MODEL, OVERLAP_TOKENS, SECOND_MODEL
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    return (cost_for_usage(FIRST_MODEL + suffix, *OVERLAP_TOKENS["sonnet"]),
            cost_for_usage(SECOND_MODEL + suffix, *OVERLAP_TOKENS["opus"]))


def sweep_estimate(n_pairs: int, *, opus_share: float = OPUS_SHARE_ASSUMED[1], transport: str = "live",
                   label: str = "lexical-only pair"):
    """The sweep's :class:`cost.Estimate`: Sonnet on ``n_pairs``, Opus on ``opus_share`` of them, at M3's measured
    tokens a pair."""
    from assistant_axis.judge_pricing import BATCH_SUFFIX

    from .cost import Estimate
    from .novelty_runner import FIRST_MODEL, OVERLAP_TOKENS, SECOND_MODEL
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    est = Estimate()
    est.add(f"overlap, Sonnet on every {label}", FIRST_MODEL + suffix, n_pairs, *OVERLAP_TOKENS["sonnet"])
    est.add(f"overlap, Opus on {opus_share:.0%} of them (ASSUMED until measured)", SECOND_MODEL + suffix,
            int(round(n_pairs * opus_share)), *OVERLAP_TOKENS["opus"])
    return est


def cap_items(items: Sequence[PairItem], budget_usd: float, *, opus_share: float = OPUS_SHARE_ASSUMED[1],
              transport: str = "live") -> dict:
    """Fit the judged pairs under ``budget_usd`` (gate 1, plan § 10): every OEWN pair is kept; if the total is over
    the budget, Moby's pairs are kept by cosine, highest first, down to the budget, and the rest are marked
    ``moby_over_cap``.  Returns ``{"n_cut", "n_kept_moby", "cut_cosine"}`` (the items are changed in place)."""
    s, o = pair_prices(transport)
    per = s + opus_share * o
    judged = [it for it in items if it.judged]
    if len(judged) * per <= budget_usd:
        return {"n_cut": 0, "n_kept_moby": sum(1 for it in judged if it.lexicon == "moby"), "cut_cosine": None}
    oewn = [it for it in judged if it.lexicon != "moby"]
    moby = sorted((it for it in judged if it.lexicon == "moby"), key=lambda it: (-(it.cosine or -1.0), it.key, it.stem))
    room = int(max(0.0, budget_usd - len(oewn) * per) // per) if per > 0 else len(moby)
    cut = moby[room:]
    for it in cut:
        it.judged, it.not_judged = False, "moby_over_cap"
    return {"n_cut": len(cut), "n_kept_moby": len(moby) - len(cut),
            "cut_cosine": cut[0].cosine if cut else None}


# --------------------------------------------------------------------------- the paid reading

def run_sweep(runner, items: Sequence[PairItem], *, rows: Optional[Mapping[str, Mapping]] = None, wave: str = "lex"
              ) -> tuple[list[dict], Optional[BaseException]]:
    """Sonnet then Opus on every judged pair (``runner``: a :class:`novelty_runner.NoveltyRunner` on the corpus and the
    queue entries with a text, its records, transport and usage the sweep's), each pair under its row's own cut-off
    rule (:class:`SweepCandidate`) and rule set (``items``' ``rules`` name, a block's rules from ``rows`` when given).
    Returns ``(results, stop)``: one row per judged pair with ``sonnet``, ``opus``, ``verdict``, ``at_or_above`` and
    ``at_cut_off`` (:func:`recovery.pair_outcome` under the row's rule set), or ``stalled`` for a pair left without an
    answer; ``stop`` is a stop the runner met (a budget stop), returned after every answer is recorded, for the caller to
    raise once it has written what it has."""
    from .recovery import pair_outcome
    todo = [it for it in items if it.judged]
    if not todo:
        return [], None
    cands: dict[str, SweepCandidate] = {}
    for it in todo:
        if it.key not in cands:
            spec = NV.CutOff(**it.cut_off)
            cands[it.key] = SweepCandidate(key=it.key, stem=(rows or {}).get(it.key, {}).get("stem") or it.key.split("#")[0],
                                           label=it.label, gloss=it.gloss or "", alignment_score=it.alignment_score,
                                           region=None, spec=spec)
    rules_by_key: dict[str, NV.Rules] = {}
    for it in todo:
        if it.key not in rules_by_key:
            blk = ((rows or {}).get(it.key) or {}).get("novelty")
            rules_by_key[it.key] = NV.rules_of(blk) if blk else _rules_by_name(it.rules)

    async def go():
        runner._stop = None   # noqa: SLF001 - the runner's own stop slot, read below
        for c in cands.values():
            runner.states.setdefault(c.key, _state(c))
        return await runner.read_pairs([(runner.states[it.key], it.stem, it.position) for it in todo], wave=wave)

    readings = asyncio.run(go())
    stop = runner._stop      # noqa: SLF001
    out = []
    for it in todo:
        r = readings.get((it.key, it.stem))
        base = it.as_dict()
        if r is None or "stalled" in r:
            out.append(base | {"stalled": (r or {}).get("stalled", "not read")})
            continue
        spec = cands[it.key].spec
        po = pair_outcome(r, spec, rules_by_key[it.key])
        out.append(base | {"sonnet": r["sonnet"], "opus": r.get("opus"), "verdict": po["verdict"],
                           "at_or_above": po["at_or_above"], "at_cut_off": po["recovers"]})
    return out, stop


def _state(c: M3Candidate):
    from .novelty_runner import CandState
    return CandState(cand=c)


def _rules_by_name(name: str) -> NV.Rules:
    for r in NV.RULES.values():
        if r.name == name:
            return r
    return NV.DEFAULT_RULES


# --------------------------------------------------------------------------- the block

def best_value(res: Mapping) -> Optional[int]:
    vals = [v for v in ((res.get("sonnet") or {}).get("value"), (res.get("opus") or {}).get("value"))
            if isinstance(v, int) and not isinstance(v, bool)]
    return max(vals) if vals else None


def _link_entry(it: PairItem, res: Optional[Mapping]) -> dict:
    d = {"stem": it.stem, "kind": it.kind, "link": it.link, "lexicon": it.lexicon, "cosine": it.cosine,
         "name_only": it.name_only, "listed_by_m3": it.listed_by_m3, "judged": bool(it.judged and res is not None
                                                                                    and "stalled" not in res)}
    if it.word:
        d["word"] = it.word
    if it.via:
        d["via"] = it.via
    if it.also_found:
        d["also_found"] = list(it.also_found)
    if not it.judged:
        d["not_judged"] = it.not_judged
    elif res is None or "stalled" in res:
        d["not_judged"] = "stalled" if res is not None else "not_read"
        if res is not None:
            d["stalled"] = res.get("stalled")
    else:
        d["sonnet"] = res.get("sonnet")
        d["opus"] = res.get("opus")
        d["verdict"] = res.get("verdict")
        d["at_cut_off"] = bool(res.get("at_cut_off"))
    return d


def block_flags(links: Sequence[Mapping], antonyms: Sequence[Mapping]) -> list[str]:
    """The flags of § 6: ``lexical_cover`` (a judged link at the cut-off), ``lexical_below_cut`` (judged links, every
    one that parsed under the cut-off), ``lexical_name_only`` (a link to a text-less queue entry),
    ``lexical_unparsed`` (a judged link whose reading never parsed), ``lexical_antonym`` (an antonym link to a trait
    with no pair partner)."""
    flags = []
    judged = [x for x in links if x.get("judged")]
    parsed = [x for x in judged if x.get("verdict") not in (None, "unparsed")]
    if any(x.get("at_cut_off") for x in judged):
        flags.append("lexical_cover")
    elif parsed:
        flags.append("lexical_below_cut")
    if any(x.get("name_only") for x in links):
        flags.append("lexical_name_only")
    if any(x.get("verdict") == "unparsed" for x in judged):
        flags.append("lexical_unparsed")
    if any(not a.get("partner_has_file") for a in antonyms):
        flags.append("lexical_antonym")
    return flags


def lexical_block(row: Mapping, links: Sequence[PairItem], antonyms: Sequence, family: Sequence[Mapping],
                  readings: Mapping[tuple[str, str], Mapping], *, run_id: str, lookup: LX.Lookup,
                  spec: NV.CutOff, rules: NV.Rules, usage: Optional[Mapping] = None, at: str) -> dict:
    """The row's ``lexical`` block (plan § 6): every link (the lexical-only pairs with their readings and verdicts; the
    links M3 already listed, ``listed_by_m3: true``, unjudged), the antonym evidence, the stem family, the row's
    cut-off rule and rule set, the flags, the pairs judged, the row's spend.  ``readings``: ``(key, stem)`` ->
    :func:`run_sweep`'s result row."""
    key = row["key"]
    entries = [_link_entry(it, readings.get((key, it.stem))) for it in links]
    ants = [a.as_dict() if hasattr(a, "as_dict") else dict(a) for a in antonyms]
    return {"run_id": run_id, "lookup_sha256": lookup.content_sha256, "lexicons": lookup.lexicon_versions,
            "links": entries, "antonyms": ants, "family": [dict(f) for f in family],
            "cut_off_rule": spec.as_dict(), "rules": rules.name, "flags": block_flags(entries, ants),
            "n_pairs_judged": sum(1 for e in entries if e.get("judged")),
            "usage": dict(usage) if usage else NV.usage_dict({}), "at": at}


def needs_block(plan: RowPlan) -> bool:
    """A row gets a ``lexical`` block when it has a lexical-only link, antonym evidence or a stem family (a row with
    none is listed in the sweep's ``plan.json`` and gets no block)."""
    return any(not it.listed_by_m3 for it in plan.links) or bool(plan.antonyms) or bool(plan.family)


# --------------------------------------------------------------------------- readouts

def _band(it: Mapping) -> str:
    c = it.get("cut_off") or {}
    return f"c{c.get('c')} {c.get('band') or c.get('rule') or ''}".strip()


def _counter(xs: Iterable) -> dict:
    return dict(sorted(Counter(xs).items(), key=lambda kv: str(kv[0])))


def merges(rows: Mapping[str, Mapping]) -> dict[str, str]:
    """``{key: corpus stem}`` for the rows Roger merged into a corpus trait in review (``review.into = "trait:<stem>"``)."""
    out = {}
    for k, r in rows.items():
        rv = r.get("review") or {}
        into = rv.get("into")
        if rv.get("status") == "merged_into" and isinstance(into, str) and into.startswith("trait:"):
            out[k] = into.split(":", 1)[1]
    return out


def _quantiles(xs: Sequence[float]) -> Optional[dict]:
    if not xs:
        return None
    a = np.asarray(xs, dtype=float)
    return {"n": len(xs), "min": round(float(a.min()), 4), "p10": round(float(np.quantile(a, 0.1)), 4),
            "median": round(float(np.median(a)), 4), "p90": round(float(np.quantile(a, 0.9)), 4),
            "max": round(float(a.max()), 4)}


def family_groups(plans: Mapping[str, RowPlan], key_of_stem: Mapping[str, str]) -> list[list[str]]:
    """Connected groups of kept rows tied by a family link to another kept row (union-find), largest first."""
    parent = {k: k for k in plans}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for k, p in plans.items():
        for f in p.family:
            if f.get("kind") == "candidate":
                o = key_of_stem.get(f["stem"])
                if o and o in parent:
                    ra, rb = find(k), find(o)
                    if ra != rb:
                        parent[ra] = rb
    groups: dict[str, list[str]] = defaultdict(list)
    for k in plans:
        groups[find(k)].append(k)
    return sorted((sorted(g) for g in groups.values() if len(g) > 1), key=lambda g: (-len(g), g))


def dry_readout(*, kept: Mapping[str, Mapping], items: Sequence[PairItem], plans: Mapping[str, RowPlan],
                lookup: LX.Lookup, estimate=None, corpus_labels: Optional[Mapping[str, str]] = None,
                cap: Optional[Mapping] = None) -> dict:
    """Gate 1's readout (plan § 10), $0: coverage; the kept rows; the lexical-only pairs by link type, lexicon, target
    kind, cut-off band and pass, Moby's share and floor; name-only links; antonym evidence beside M3's
    ``pair_completion_for``; families among the kept rows; the free labels (Roger's merges, the audit's five)."""
    corpus_labels = corpus_labels or {}
    lexs = list(lookup.lexicons)
    found = {n: sum(1 for r in kept.values() if LX.first_form(r["label"], lookup.lexicons[n])[0]) for n in lexs}
    lo = list(items)
    hit_rows = sorted({it.key for it in lo})
    judged = [it for it in lo if it.judged]
    listed = sum(1 for p in plans.values() for it in p.links if it.listed_by_m3)
    std = sum(1 for it in lo if "(" in (corpus_labels.get(it.stem) or lookup.rows.get(it.stem, {}).get("label") or ""))
    ren = sum(1 for it in lo if it.word and it.word not in
              {LX.norm(f) for f in LX.label_forms(lookup.rows[it.stem]["label"])})
    mg = merges(kept)
    hit_merged = {k: mg[k] for k in hit_rows if k in mg}
    lex_target = {k: s for k, s in hit_merged.items() if any(it.key == k and it.stem == s for it in lo)}
    audit = {}
    for k, t in AUDIT_RETRIEVAL_MISSES.items():
        p = plans.get(k)
        audit[k] = {"trait": t, "in_sweep": p is not None,
                    "reached": bool(p and any(it.stem == t and not it.listed_by_m3 for it in p.links)),
                    "links": [f"{it.stem} ({it.lexicon} {it.link})" for it in (p.links if p else [])
                              if not it.listed_by_m3]}
    ant_rows = {k: p for k, p in plans.items() if p.antonyms}
    oewn_ant = {k: p for k, p in ant_rows.items() if any(a.link == "antonym" and a.kind == "corpus" for a in p.antonyms)}
    single = {k for k, p in oewn_ant.items() if any(a.link == "antonym" and a.kind == "corpus" and not a.partner_has_file
                                                     for a in p.antonyms)}
    pcf_same = sum(1 for k, p in ant_rows.items()
                   if set((kept[k].get("novelty") or {}).get("pair_completion_for") or []) & {a.stem for a in p.antonyms})
    pcf_any = sum(1 for k in ant_rows if (kept[k].get("novelty") or {}).get("pair_completion_for"))
    key_of_stem = {kept[k]["stem"]: k for k in kept}
    groups = family_groups(plans, key_of_stem)
    fam_rows = [k for k, p in plans.items() if p.family]
    fam_kinds = Counter(f["kind"] for p in plans.values() for f in p.family)
    fam_via = Counter(f["via"] for p in plans.values() for f in p.family)
    cos = [it.cosine for it in lo if it.cosine is not None]
    moby = [it for it in lo if it.lexicon == "moby"]
    out = {
        "lexicons": lookup.header.get("lexicons"), "lookup_sha256": lookup.content_sha256,
        "coverage": lookup.header.get("coverage"),
        "kept_rows": {"n": len(kept), "by_pass": _counter(row_pass(r) for r in kept.values()),
                      "single_word": sum(1 for r in kept.values() if "_" not in r["stem"]),
                      "phrases": sum(1 for r in kept.values() if "_" in r["stem"]),
                      "found_in_lexicon": found,
                      "by_cut_off": _counter(row_rules(r["novelty"])[0].c for r in kept.values()),
                      "by_rules": _counter((r["novelty"].get("rules") or {}).get("name") for r in kept.values())},
        "pairs": {"n_rows_with_links": len(hit_rows),
                  "n_rows_with_links_single_word": sum(1 for k in hit_rows if "_" not in kept[k]["stem"]),
                  "n_pairs": len(lo), "n_judgeable": len(judged), "n_listed_by_m3": listed,
                  "not_judged": _counter(it.not_judged for it in lo if not it.judged),
                  "by_link": _counter(it.link for it in lo), "by_lexicon": _counter(it.lexicon for it in lo),
                  "by_kind": _counter(it.kind for it in lo), "by_cut_off_band": _counter(_band(it.as_dict()) for it in lo),
                  "by_pass": _counter(it.pass_ for it in lo),
                  "rows_by_cut_off": _counter(row_rules(kept[k]["novelty"])[0].c for k in hit_rows),
                  "rows_by_alignment": _counter(kept[k]["novelty"].get("alignment_score") for k in hit_rows),
                  "to_standards_derived_traits": std, "via_renamed_from": ren,
                  "name_only_links": sum(1 for it in lo if it.name_only),
                  "moby": {"n": len(moby), "moby_only": sum(1 for it in moby if it.moby_only),
                           "moby_only_below_floor": sum(1 for it in moby if it.not_judged == "moby_below_floor"),
                           "moby_only_no_cosine": sum(1 for it in moby if it.not_judged == "moby_no_cosine")},
                  "cosine": _quantiles(cos), "no_cosine": sum(1 for it in lo if it.cosine is None)},
        "antonym_evidence": {"rows": len(ant_rows), "rows_oewn_antonym_to_corpus": len(oewn_ant),
                             "of_which_trait_has_no_partner": len(single),
                             "by_link": _counter(a.link for p in ant_rows.values() for a in p.antonyms),
                             "rows_with_pair_completion_for": pcf_any,
                             "rows_whose_pair_completion_for_is_an_antonym": pcf_same},
        "families": {"rows_with_family": len(fam_rows), "by_kind": dict(fam_kinds), "by_via": dict(fam_via),
                     "groups_among_kept_rows": len(groups), "largest_groups": groups[:10]},
        "free_labels": {"roger_merges_into_corpus": len(mg), "hit_rows_merged_into_corpus": len(hit_merged),
                        "hit_rows_merged_into_their_lexical_target": len(lex_target),
                        "lexical_target_merges": dict(sorted(lex_target.items())),
                        "hit_rows_reviewed": _counter((kept[k].get("review") or {}).get("status") for k in hit_rows)},
        "audit_retrieval_misses": audit,
    }
    if estimate is not None:
        out["estimate"] = {"usd": round(estimate.usd, 4), "lines": [str(x) for x in estimate.lines],
                           "opus_share_assumed": list(OPUS_SHARE_ASSUMED)}
    if cap is not None:
        out["cap"] = dict(cap)
    return out


def _pct(n: int, d: int) -> str:
    return f"{n / d:.1%}" if d else "n/a"


def _tbl(d: Mapping, head: tuple[str, str] = ("", "n")) -> str:
    lines = [f"| {head[0]} | {head[1]} |", "|---|---|"]
    for k, v in d.items():
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def dry_markdown(r: Mapping, *, labelled: Optional[Mapping] = None, rel: str = "../../") -> str:
    """``dry_readout.md``: the gate-1 readout for Roger (links relative to ``data/candidates/lexical/``)."""
    p, k = r["pairs"], r["kept_rows"]
    lines = ["# Lexical recall: the dry readout (gate 1, $0)", "",
             f"Lookup [lookup.json](./lookup.json) (content sha256 `{r['lookup_sha256'][:12]}`); lexicons "
             + ", ".join(f"{n} `{(v or {}).get('id') or (v or {}).get('sha256', '')[:12]}`"
                         for n, v in (r.get('lexicons') or {}).items()) + ".  Terms: [glossary](../../../reports/trait_gap_generation/glossary.md)"
             " (lexical link, lexical neighbour, lexical-only pair).", "",
             "## Coverage of the lookup table", ""]
    for n, cov in (r.get("coverage") or {}).items():
        lines.append(f"- **{n}**: " + "; ".join(f"{kind} {v['found']} of {v['of']}" for kind, v in cov.items()))
    lines += ["", "## The kept rows", "",
              f"{k['n']} kept rows (M3 `new` or `grey`), {k['single_word']} single words and {k['phrases']} phrases; by "
              f"pass {k['by_pass']}; by cut-off {k['by_cut_off']}; rule sets {k['by_rules']}.  Found in the lexicon: "
              + ", ".join(f"{n} {v}" for n, v in k["found_in_lexicon"].items()) + ".", "",
              "## The lexical-only pairs", "",
              f"**{p['n_rows_with_links']} kept rows ({p['n_rows_with_links_single_word']} single words) have "
              f"{p['n_pairs']} lexical-only pairs**; {p['n_judgeable']} are judgeable; {p['n_listed_by_m3']} further "
              f"links were already listed by M3.  Not judged: {p['not_judged'] or 'none'}.  "
              f"{p['to_standards_derived_traits']} pairs go to a standards-derived trait (a bare lemma such as `agreeable` "
              f"reaches [agreeable (Big Five)]({rel}traits/instructions/agreeable_big_five.json) too) and "
              f"{p['via_renamed_from']} reach a trait through its `renamed_from`.", "",
              "| by | counts |", "|---|---|",
              f"| link type | {p['by_link']} |", f"| lexicon | {p['by_lexicon']} |", f"| target kind | {p['by_kind']} |",
              f"| cut-off band | {p['by_cut_off_band']} |", f"| pass | {p['by_pass']} |",
              f"| hit rows by cut-off | {p['rows_by_cut_off']} |", f"| hit rows by alignment score | {p['rows_by_alignment']} |",
              f"| name-only links | {p['name_only_links']} |", f"| Moby | {p['moby']} |",
              f"| cosine of the pairs | {p['cosine']} (no cosine: {p['no_cosine']}) |", ""]
    a = r["antonym_evidence"]
    lines += ["## Antonym evidence", "",
              f"{a['rows']} kept rows carry antonym evidence ({a['by_link']}); {a['rows_oewn_antonym_to_corpus']} have an OEWN "
              f"antonym that is a corpus trait, {a['of_which_trait_has_no_partner']} of them a trait with no pair partner.  "
              f"{a['rows_with_pair_completion_for']} of the rows with evidence also carry M3's `pair_completion_for`, "
              f"{a['rows_whose_pair_completion_for_is_an_antonym']} naming one of the same traits.", ""]
    f = r["families"]
    lines += ["## Stem families", "",
              f"{f['rows_with_family']} kept rows have a family member ({f['by_kind']}; {f['by_via']}); "
              f"{f['groups_among_kept_rows']} groups of kept rows tie each other.  Largest: "
              + "; ".join(", ".join(g) for g in f["largest_groups"][:5]) + ".", ""]
    fl = r["free_labels"]
    lines += ["## Free labels", "",
              f"Roger merged {fl['roger_merges_into_corpus']} kept rows into a corpus trait in review.  Of the rows with "
              f"lexical-only pairs, {fl['hit_rows_reviewed'].get('merged_into', 0)} were merged in review (into a trait "
              f"or another candidate), {fl['hit_rows_merged_into_corpus']} into a corpus trait, and "
              f"**{fl['hit_rows_merged_into_their_lexical_target']} were merged into the lexically linked trait**: "
              + ", ".join(f"`{kk}` → [{v}]({rel}traits/instructions/{v}.json)" for kk, v in fl["lexical_target_merges"].items())
              + ".", "", "The gate audit's five retrieval misses:", "",
              "| candidate | the audit's trait | reached | lexical-only links |", "|---|---|---|---|"]
    for kk, v in r["audit_retrieval_misses"].items():
        lines.append(f"| `{kk}` | [{v['trait']}]({rel}traits/instructions/{v['trait']}.json) | "
                     f"{'**yes**' if v['reached'] else ('no' if v['in_sweep'] else 'not a kept row')} | "
                     f"{', '.join(v['links']) or '-'} |")
    if r.get("estimate"):
        e = r["estimate"]
        lines += ["", "## The sweep's estimate", "", f"**${e['usd']:.2f}** live (Opus share ASSUMED "
                  f"{e['opus_share_assumed'][0]:.2f}-{e['opus_share_assumed'][1]:.2f}, priced at the higher):", ""]
        lines += [f"- {x}" for x in e["lines"]]
    if r.get("cap"):
        lines += ["", f"Cap: {r['cap']}"]
    if labelled:
        lines += ["", "## The labelled pairs", "", labelled_markdown(labelled)]
    return "\n".join(lines) + "\n"


def labelled_markdown(m: Mapping) -> str:
    """The labelled-pairs measurement as a table per lexicon."""
    out = []
    for lname, rel in (m.get("by_lexicon") or {}).items():
        out += [f"**{lname}** ([labelled_pairs.json](../calibration/labelled_pairs.json), {m.get('n_pairs')} pairs): "
                "both sides found; abstain; synonym-like links (synonym / similar / also); antonym links "
                "(antonym / affix); recall or false-flag rate over the pairs with both sides found.", "",
                "| relation | n | both found | abstain | synonym-like | by link | antonym | by antonym | rate |",
                "|---|---|---|---|---|---|---|---|---|"]
        for r, d in rel.items():
            rate = d.get("recall", d.get("false_flag"))
            what = "recall" if "recall" in d else ("false flags" if "false_flag" in d else "")
            out.append(f"| {r} | {d['n']} | {d['both_found']} | {d['abstain']} | {d['linked']} | "
                       f"{'/'.join(str(d['by_link'][t]) for t in LX.LINK_TYPES)} | {d['antonym_linked']} | "
                       f"{'/'.join(str(d['by_antonym'][t]) for t in LX.ANTONYM_TYPES)} | "
                       f"{(f'{what} {rate:.1%}') if rate is not None else '-'} |")
        out.append("")
    return "\n".join(out)


def sweep_report(results: Sequence[Mapping], *, items: Sequence[PairItem], kept: Mapping[str, Mapping],
                 plans: Mapping[str, RowPlan], usage: Optional[Mapping] = None, parse_rates: Optional[Mapping] = None,
                 marks: Optional[Mapping] = None, n_written: Optional[int] = None) -> dict:
    """The sweep's readout (plan § 6, § 10 gate 2), the stop-rule figure first: covers at the cut-off (a lexical-only
    pair read at its row's own cut-off under its rule set), by link type, lexicon, cut-off band, pass and target kind;
    the below-cut readings; precision proxies (covers on rows Roger merged into that trait, into another, accepted; the
    audit's list); Opus's measured share; parse rates; spend; Roger's marks when given (:func:`fold_marks`)."""
    res = [r for r in results if "stalled" not in r]
    covers = [r for r in res if r.get("at_cut_off")]
    below = [r for r in res if not r.get("at_cut_off") and r.get("verdict") != "unparsed"]
    n_opus = sum(1 for r in res if r.get("opus"))

    def by(field_: str) -> dict:
        d: dict = {}
        for r in res:
            k = r.get(field_) if field_ != "band" else _band(r)
            e = d.setdefault(str(k), {"judged": 0, "covers": 0})
            e["judged"] += 1
            e["covers"] += int(bool(r.get("at_cut_off")))
        return dict(sorted(d.items()))
    mg = merges(kept)
    cover_rows = sorted({r["key"] for r in covers})
    prec = {"cover_rows": len(cover_rows),
            "merged_into_that_trait": sorted(k for k in cover_rows if any(c["key"] == k and mg.get(k) == c["stem"]
                                                                         for c in covers)),
            "merged_into_another_trait": sorted(k for k in cover_rows if k in mg and not any(
                c["key"] == k and mg.get(k) == c["stem"] for c in covers)),
            "accepted_as_new": sorted(k for k in cover_rows if (kept.get(k, {}).get("review") or {}).get("status") == "accepted"),
            "audit_list": sorted(k for k in cover_rows if k in AUDIT_RETRIEVAL_MISSES)}
    hist = Counter()
    three_under_four = 0
    for r in below:
        b = best_value(r)
        hist[b if b is not None else "none"] += 1
        if b == 3 and (r.get("cut_off") or {}).get("c") == 4:
            three_under_four += 1
    hit_rows = sorted({it.key for it in items})
    hit_merged = {k: mg[k] for k in hit_rows if k in mg}
    lex_target = {k: s for k, s in hit_merged.items() if any(it.key == k and it.stem == s for it in items)}
    lex_target_cut = {k: s for k, s in lex_target.items() if any(c["key"] == k and c["stem"] == s for c in covers)}
    ant_rows = {k: p for k, p in plans.items() if p.antonyms}
    spend = (usage or {}).get("total_cost_usd")
    out = {
        "stop_rule": {"covers_at_cut_off": len(covers), "cover_rows": len(cover_rows), "stop_line": STOP_LINE_COVERS,
                      "below_stop_line": len(covers) < STOP_LINE_COVERS,
                      "line": (f"covers at the cut-off: {len(covers)} pairs on {len(cover_rows)} rows "
                               f"({'under' if len(covers) < STOP_LINE_COVERS else 'at or over'} the stop line of about "
                               f"{STOP_LINE_COVERS}); Roger's marks decide the build (about {BUILD_LINE_SHARE:.0%} "
                               f"confirmed, 36 of 40)")},
        "n_rows_swept": len(kept), "n_rows_with_links": len(hit_rows), "n_pairs": len(items),
        "n_judged": len(res), "n_stalled": len(results) - len(res),
        "not_judged": _counter(it.not_judged for it in items if not it.judged),
        "covers_at_cut_off": len(covers), "below_cut": len(below),
        "unparsed": sum(1 for r in res if r.get("verdict") == "unparsed"),
        "by_link": by("link"), "by_lexicon": by("lexicon"), "by_cut_off_band": by("band"), "by_pass": by("pass"),
        "by_kind": by("kind"),
        "below_cut_best_reading": {str(k): v for k, v in sorted(hist.items(), key=lambda kv: str(kv[0]))},
        "below_cut_three_at_cut_off_four": three_under_four,
        "precision_proxies": prec,
        "roger_merges": {"rows": len(hit_merged), "into_corpus": len(hit_merged), "lexical_target": len(lex_target),
                         "lexical_target_read_at_cut_off": len(lex_target_cut),
                         "lexical_target_rows": dict(sorted(lex_target.items()))},
        "audit_retrieval_misses_reached": sorted(k for k, t in AUDIT_RETRIEVAL_MISSES.items()
                                                 if any(it.key == k and it.stem == t for it in items)),
        "audit_retrieval_misses_covered": sorted(k for k, t in AUDIT_RETRIEVAL_MISSES.items()
                                                 if any(c["key"] == k and c["stem"] == t for c in covers)),
        "antonym_evidence": {"rows": len(ant_rows),
                             "singleton_partner": sum(1 for p in ant_rows.values()
                                                      if any(not a.partner_has_file for a in p.antonyms)),
                             "beside_pair_completion_for": sum(1 for k in ant_rows
                                                               if (kept[k].get("novelty") or {}).get("pair_completion_for"))},
        "opus_share_measured": round(n_opus / len(res), 4) if res else None,
        "n_opus_readings": n_opus,
        "parse_rate": dict(parse_rates or {}),
        "spend_usd": round(float(spend), 4) if spend is not None else None,
        "spend_by_model": {m: round(float(v.get("cost_usd", 0.0)), 4)
                           for m, v in ((usage or {}).get("per_model") or {}).items()},
        "yield_per_dollar": (round(len(covers) / float(spend), 3) if spend else None),
        "covers": [{k: c.get(k) for k in ("key", "label", "stem", "kind", "link", "lexicon", "cosine", "pass", "cut_off",
                                          "verdict")} | {"sonnet": (c.get("sonnet") or {}).get("value"),
                                                         "opus": (c.get("opus") or {}).get("value")} for c in covers],
    }
    if n_written is not None:
        out["n_blocks_written"] = n_written
    if marks:
        out["marks"] = dict(marks)
    return out


def sweep_markdown(rep: Mapping, results: Sequence[Mapping], *, kept: Mapping[str, Mapping], batch_id: str,
                   rel: str = "../../../../") -> str:
    """``sweep_report.md``: the stop-rule line first, the counts, then one row per judged pair (covers first)."""
    s = rep["stop_rule"]
    lines = [f"# Lexical sweep `{batch_id}`", "", f"**{s['line']}**", ""]
    if rep.get("marks"):
        m = rep["marks"]
        lines += [f"**Roger's marks: {m.get('line')}**", ""]
    lines += [f"Rows swept {rep['n_rows_swept']}; rows with lexical-only pairs {rep['n_rows_with_links']}; pairs "
              f"{rep['n_pairs']}, judged {rep['n_judged']} (stalled {rep['n_stalled']}; not judged {rep['not_judged']}); "
              f"covers {rep['covers_at_cut_off']}, below the cut-off {rep['below_cut']}, unparsed {rep['unparsed']}.  "
              f"Opus read {rep['n_opus_readings']} of the judged pairs (share {rep['opus_share_measured']}); spend "
              f"${rep['spend_usd']} ({rep['spend_by_model']}); covers per dollar {rep['yield_per_dollar']}.", "",
              "| by | judged / covers |", "|---|---|"]
    for f in ("by_link", "by_lexicon", "by_cut_off_band", "by_pass", "by_kind"):
        lines.append(f"| {f[3:]} | " + "; ".join(f"{k} {v['judged']}/{v['covers']}" for k, v in rep[f].items()) + " |")
    lines += ["", f"Below the cut-off, best reading: {rep['below_cut_best_reading']}; a 3 at cut-off 4: "
              f"{rep['below_cut_three_at_cut_off_four']} (Roger's TODO 4: worth a review flag?).", "",
              f"Precision proxies: {rep['precision_proxies']}.  Roger's merges among the rows with pairs: "
              f"{rep['roger_merges']}.  The audit's retrieval misses reached: {rep['audit_retrieval_misses_reached']}, "
              f"covered: {rep['audit_retrieval_misses_covered']}.  Antonym evidence: {rep['antonym_evidence']}.  "
              f"Parse rates: {rep['parse_rate']}.", "",
              "| key | label | gloss | the trait | link | cosine | Sonnet | Opus | verdict | review |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted((r for r in results if "stalled" not in r),
                   key=lambda r: (not r.get("at_cut_off"), -(best_value(r) or -1), r["key"], r["stem"]))
    for r in order:
        rv = (kept.get(r["key"], {}).get("review") or {})
        st = rv.get("status") or ""
        if rv.get("into"):
            st += f" → {rv['into']}"
        tgt = (f"[{r['stem']}]({rel}traits/instructions/{r['stem']}.json)" if r["kind"] == "corpus"
               else f"{r['stem']} (queue)")
        g = (r.get("gloss") or "").replace("|", "/")
        lines.append(f"| `{r['key']}` | {r['label']} | {g} | {tgt} | {r['lexicon']} {r['link']} | {r.get('cosine')} | "
                     f"{(r.get('sonnet') or {}).get('value')} | {(r.get('opus') or {}).get('value')} | "
                     f"{'**cut**' if r.get('at_cut_off') else r.get('verdict')} | {st} |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- Roger's blind marks

def marks_sheet(results: Sequence[Mapping], *, descriptions: Mapping[str, str], target_labels: Mapping[str, str],
                n: int = MARKS_MAX, seed: int = 20261014, batch_id: str, rel: str = "../../") -> tuple[str, dict]:
    """``(markdown, key)``: up to ``n`` covers (every one when there are no more; else a seeded sample, stratified by
    lexicon and link type in proportion), shuffled, each with the candidate's gloss and the trait's description and
    nothing about the readings, for Roger to mark C, N or ? (the cover audit's form,
    ``m3_cover_audit_for_marks.md``).  The key (``key.json``) holds each row's readings and where it came from."""
    covers = [r for r in results if r.get("at_cut_off") and "stalled" not in r]
    rng = random.Random(seed)
    if len(covers) > n:
        strata: dict[str, list] = defaultdict(list)
        for r in sorted(covers, key=lambda r: (r["key"], r["stem"])):
            strata[f"{r['lexicon']}:{r['link']}"].append(r)
        quota = {s: max(1, round(n * len(v) / len(covers))) for s, v in strata.items()}
        while sum(quota.values()) > n:
            big = max(quota, key=lambda s: quota[s])
            quota[big] -= 1
        pick = []
        for s in sorted(strata):
            pick += rng.sample(strata[s], min(quota[s], len(strata[s])))
        covers = pick
    covers = sorted(covers, key=lambda r: (r["key"], r["stem"]))
    rng.shuffle(covers)
    rows = []
    lines = ["# Lexical covers: does the existing trait really cover the word? For Roger's marks", "",
             f"Written for Roger by `lexical_recall.py marks --batch-id {batch_id}`.  Each row below is a kept candidate "
             "(M3 decided it new) and a corpus trait that a dictionary links it to, which M3 never read; the overlap "
             "call, run on the pair afterwards, read it at the candidate's own cut-off.  Your marks decide whether the "
             "integration (plan 11 tasks 6-8) is built: about 90% confirmed builds it.", "",
             "**How to mark.**  Read the candidate's gloss and the trait's description, and put one of these in the "
             "last column:", ""]
    lines += [f"- **{c}**: {t}." for c, t in MARK_CODES.items()]
    lines += ["", f"The rows are shuffled and show no readings; the key is in [key.json]({rel}data/candidates/lexical/sweep/"
              f"{batch_id}/marks/key.json), read after marking.", "",
              "| # | candidate | its gloss | linked trait | that trait's description | mark |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(covers, 1):
        lab = target_labels.get(r["stem"]) or r["stem"].replace("_", " ")
        tgt = (f"[{lab}]({rel}data/traits/instructions/{r['stem']}.json)" if r["kind"] == "corpus"
               else f"{lab} (seed queue)")
        desc = (descriptions.get(r["stem"]) or "").replace("|", "/")
        g = (r.get("gloss") or "").replace("|", "/")
        lines.append(f"| {i} | {r['label']} | {g} | {tgt} | {desc} |  |")
        rows.append({"n": i, "key": r["key"], "label": r["label"], "stem": r["stem"], "kind": r["kind"],
                     "link": r["link"], "lexicon": r["lexicon"], "cosine": r.get("cosine"), "pass": r.get("pass"),
                     "cut_off": (r.get("cut_off") or {}).get("c"), "verdict": r.get("verdict"),
                     "sonnet": (r.get("sonnet") or {}).get("value"), "opus": (r.get("opus") or {}).get("value"),
                     "sonnet_reason": (r.get("sonnet") or {}).get("reason"),
                     "opus_reason": (r.get("opus") or {}).get("reason")})
    md = "\n".join(lines) + "\n"
    key = {"batch_id": batch_id, "seed": seed, "n_covers": sum(1 for r in results if r.get("at_cut_off")),
           "n_marked": len(rows), "mark_codes": MARK_CODES,
           "marks_file_sha256": hashlib.sha256(md.encode("utf-8")).hexdigest(), "rows": rows}
    return md, key


_MARK_RE = re.compile(r"^\|\s*(\d+)\s*\|")


def parse_marks_markdown(text: str) -> dict[int, dict]:
    """Roger's marks read from the marked sheet: ``{n: {"mark": "C"|"N"|"?"|None, "note": ...}}``.  The last column
    is the mark: a cell starting with C, N or ? (any case; "covered", "new" read as C and N); anything after it is a
    note; an empty cell is ``None``."""
    out: dict[int, dict] = {}
    for line in text.splitlines():
        m = _MARK_RE.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        cell = cells[-1] if len(cells) >= 6 else ""
        mark, note = None, None
        if cell:
            head = cell.split()[0].rstrip(".,:;").lower()
            mark = {"c": "C", "covered": "C", "n": "N", "new": "N", "?": "?", "unsure": "?"}.get(head)
            if mark is None and cell[0] in "CcNn?":
                mark = cell[0].upper() if cell[0] != "?" else "?"
            note = cell[len(cell.split()[0]):].strip(" -:;,.") or None
            if mark is None:
                note = cell
        out[int(m.group(1))] = {"mark": mark, "note": note}
    return out


def fold_marks(key: Mapping, marks: Mapping[int, Mapping] | Sequence[Mapping]) -> dict:
    """Roger's marks against the key: per row the mark, and the counts: ``confirmed`` (C: a real miss of M3's
    retrieval), ``rejected`` (N), ``unsure`` (?), ``unmarked``; ``precision`` (confirmed over C + N), and the build
    line (about 90% of the marked confirmed, 36 of 40; open decision 2) with the stop line (fewer than about 5
    confirmed real misses stops the plan)."""
    if not isinstance(marks, Mapping):
        marks = {int(m["n"]): m for m in marks}
    rows = []
    for r in key.get("rows") or []:
        m = marks.get(int(r["n"])) or marks.get(str(r["n"])) or {}
        rows.append(dict(r) | {"mark": m.get("mark"), "roger_note": m.get("note") or m.get("roger_note")})
    c = Counter(r["mark"] for r in rows)
    conf, rej, uns, none = c.get("C", 0), c.get("N", 0), c.get("?", 0), c.get(None, 0)
    decided = conf + rej
    prec = round(conf / decided, 4) if decided else None
    build = prec is not None and prec >= BUILD_LINE_SHARE and conf >= STOP_LINE_COVERS
    line = (f"{conf} confirmed real misses, {rej} rejected, {uns} unsure, {none} unmarked of {len(rows)} marked "
            f"(precision {prec if prec is not None else 'n/a'}); "
            + ("build the integration (tasks 6-8)" if build else
               ("stop: fewer than about 5 confirmed" if conf < STOP_LINE_COVERS else
                f"under the build line of about {BUILD_LINE_SHARE:.0%}: Roger decides")))
    return {"n_marked": len(rows), "confirmed": conf, "rejected": rej, "unsure": uns, "unmarked": none,
            "precision": prec, "build": build, "line": line, "rows": rows,
            "by_link": _marks_by(rows)}


def _marks_by(rows: Sequence[Mapping]) -> dict:
    out: dict = {}
    for r in rows:
        d = out.setdefault(f"{r['lexicon']}:{r['link']}", {"C": 0, "N": 0, "?": 0, "unmarked": 0})
        d[r["mark"] if r["mark"] in ("C", "N", "?") else "unmarked"] += 1
    return dict(sorted(out.items()))
