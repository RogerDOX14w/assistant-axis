"""Near-duplicates inside the trait corpus: M3's same-concept call on each trait's nearest non-partner neighbours.

W3 on Roger's work list (the pre-extraction drop-or-merge review), the second pass after the embedding-only one
(``data/candidates/calibration_916/drop_or_merge.md``, an upper fence on nearest-neighbour cosines, which flags 15
pairs and misses paraphrases).  The CLI is ``data_analysis/gap_generation/corpus_near_duplicates.py``; outputs under
``data/candidates/near_duplicates_916/``.

* **Pairs** (:func:`nearest_pairs`): every corpus trait in M3's covered space (the index
  ``novelty_score.load_index`` builds from ``metric_config.json``: ``label: description`` in the covered
  representation, projected into the space fitted on the corpus), and its ``k`` (3) nearest other traits by cosine,
  leaving out itself and every member of every arrangement it belongs to (whatever kind ``arrangements.py`` records:
  pair, simplex, sequence, set, map, ring, tree, square, cube, orthoplex), and a clean pair by reciprocal
  ``negative_label`` that no arrangement records yet; then the pairs under the cosine floor (0.35, decision 11 of
  ``coding_plan_review.md``: below it 0.1% of M3's recorded readings were 4) are dropped, and unordered pairs
  deduplicated.  The neighbours the arrangement rule kept out (those nearer than a trait's k-th kept neighbour) are
  recorded, unread, for the report.
* **Readings**: rubric A (``overlap_concept.md`` as pinned), one pair per call, through
  :meth:`NoveltyRunner.run_pairs` unchanged: Sonnet 5.5 first, Opus 5.5 under M3's rule at cut-off 3
  (:func:`novelty.sonnet_action`: Opus reads Sonnet's 3s, 2s and ``unsure``; a Sonnet 4 stands, a Sonnet 1 or 0
  stands).  The **final** reading of a direction is Opus's where the rule asked Opus, else Sonnet's; "3 or above"
  is exactly M3's rule set 2 covering at cut-off 3 (:func:`novelty.verdict_cuts`), Sonnet 2 raised by Opus
  included.
* **Two directions**, as R1 reads them (``review_graph``): the first with the stem that sorts first as the target;
  the second only where the first's final reading is 3 or above, so every pair read 3 or above both ways is found.
  A pair named with ``also`` (asked about by hand) is read both ways whatever the first says.
* **Sections** (:func:`classify`): ``same_4`` (4 both ways), ``same_3`` (3 or above both ways, not 4 and 4),
  ``one_way`` (3 or above in one direction only).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.judge_pricing import BATCH_SUFFIX

from . import novelty as NV
from . import novelty_runner as NR
from .cost import Estimate

#: M3's cut-off far from alignment: rubric A's 3 ("the same concept, differing only in scope, degree or
#: emphasis") covers.  Opus re-reads Sonnet's 3s, 2s and unsure answers.
CUT_OFF = 3
DEFAULT_K = 3
#: Decision 11 of coding_plan_review.md (R1's overlap floor): below 0.35, 0.1% of M3's recorded readings were 4
#: and 3.9% were 3 or above.
DEFAULT_COSINE_FLOOR = 0.35
#: M3's rule set 2: a Sonnet 2 that Opus reads 3 or above counts (decision 12 of the M3 section).
RULES = NV.RULES[2]
FIRST_WAVE, SECOND_WAVE = "d1", "d2"
SECTIONS: tuple[str, ...] = ("same_4", "same_3", "one_way")
SECTION_TITLES = {
    "same_4": "Same concept both ways (4 and 4)",
    "same_3": "Same concept, scope or degree differs (3 or more both ways)",
    "one_way": "One way only (3 or more in one direction)",
}
#: The arrangement kinds whose members are mutually opposed (a pair, the corners of a simplex): neighbours left out
#: for these are expected antonyms; any other kind (sequence, set, map, ring, tree, square, cube, orthoplex) holds
#: neighbours, which can be near-duplicates.
LABEL_PAIR = "label_pair"
#: Cosine bins (lower edges) of the estimate's measured shares, and the observations a bin needs.
SHARE_BINS = (0.35, 0.45, 0.55, 0.65)
MIN_SHARE_OBS = 10


def is_opposing(kind: str) -> bool:
    """A pair, a triangle, a tetrahedron, an N-simplex, or a clean pair by label alone."""
    return kind == LABEL_PAIR or NV.is_expanding(kind)


# --------------------------------------------------------------------------- the corpus as candidates

class CorpusCandidate(NR.M3Candidate):
    """A corpus trait as the target of the overlap call: cut-off 3 whatever its region."""

    @property
    def cut_off(self) -> int:
        return CUT_OFF


def corpus_candidate(t: NV.CorpusTrait) -> CorpusCandidate:
    """The trait as M3's target: key and stem its file stem, label its ``positive_label``, gloss its description
    (exactly what the overlap call shows of an "other" corpus trait)."""
    return CorpusCandidate(key=t.stem, stem=t.stem, label=t.label, gloss=t.description, alignment_score=None,
                           region=None, generators=[])


# --------------------------------------------------------------------------- arrangements and pairs

def arrangement_partners(data_dir: Path) -> dict[str, dict[str, list[str]]]:
    """``{stem: {other: [kinds]}}``: every member of every arrangement each trait file records (kinds sorted), and a
    clean pair by reciprocal ``negative_label`` that no arrangement of the trait records (kind :data:`LABEL_PAIR`)."""
    from assistant_axis.arrangements import load_corpus_arrangements, reciprocal_pairs
    recs = load_corpus_arrangements(Path(data_dir), "traits")
    out: dict[str, dict[str, set]] = {s: defaultdict(set) for s in recs}
    for s, r in recs.items():
        for a in r.arrangements:
            for m in a.members:
                if m != s:
                    out[s][m].add(a.kind)
    for a, b in reciprocal_pairs(recs):
        for x, y in ((a, b), (b, a)):
            if y not in out[x]:
                out[x][y].add(LABEL_PAIR)
    return {s: {o: sorted(k) for o, k in sorted(d.items())} for s, d in out.items()}


@dataclass
class PairPlan:
    """The scan's pairs.  ``pairs``: ``{(a, b): {"cosine", "listed_by": [{"stem", "rank"}]}}`` with ``a < b``, at the
    floor or above; ``below_floor``: the same for the nearest pairs under it (not read); ``kept_out``: ``{(a, b):
    {"cosine", "kinds", "kept_out_for": [stem]}}``, arrangement members nearer to a trait than its k-th kept
    neighbour; ``stats``: the counts."""
    pairs: dict
    below_floor: dict
    kept_out: dict
    stats: dict
    k: int = DEFAULT_K
    floor: float = DEFAULT_COSINE_FLOOR


def nearest_pairs(stems: Sequence[str], Z: np.ndarray, partners: Mapping[str, Mapping[str, Sequence[str]]], *,
                  k: int = DEFAULT_K, floor: float = DEFAULT_COSINE_FLOOR) -> PairPlan:
    """Each trait's ``k`` nearest other traits by cosine (rows of ``Z`` are unit vectors, in ``stems`` order; ties by
    stem), leaving out every stem ``partners[trait]`` names; the pairs under ``floor`` dropped; unordered pairs
    deduplicated (``listed_by`` says which trait listed it, at which rank)."""
    stems = list(stems)
    Z = np.asarray(Z, dtype=np.float64)
    if Z.shape[0] != len(stems):
        raise ValueError(f"{Z.shape[0]} rows for {len(stems)} stems")
    S = Z @ Z.T
    rank = np.argsort(np.argsort(np.array(stems)))        # ties broken by stem
    found: dict[tuple, dict] = {}
    kept_out: dict[tuple, dict] = {}
    directed = 0
    kept_out_by_kind: Counter = Counter()
    for i, s in enumerate(stems):
        excl = partners.get(s) or {}
        got = 0
        for j in np.lexsort((rank, -S[i])):
            if j == i:
                continue
            t, c = stems[j], round(float(S[i, j]), 6)
            if t in excl:
                key = tuple(sorted((s, t)))
                ko = kept_out.setdefault(key, {"cosine": c, "kinds": list(excl[t]), "kept_out_for": []})
                ko["kept_out_for"].append(s)
                for kind in excl[t]:
                    kept_out_by_kind[kind] += 1
                continue
            got += 1
            directed += 1
            key = tuple(sorted((s, t)))
            found.setdefault(key, {"cosine": c, "listed_by": []})["listed_by"].append({"stem": s, "rank": got})
            if got >= k:
                break
    pairs = {p: v for p, v in sorted(found.items()) if v["cosine"] >= floor}
    below = {p: v for p, v in sorted(found.items()) if v["cosine"] < floor}
    stats = {"n_traits": len(stems), "k": k, "cosine_floor": floor, "n_directed": directed,
             "n_unique_before_floor": len(found), "n_below_floor": len(below), "n_pairs": len(pairs),
             "n_kept_out_neighbours": sum(len(v["kept_out_for"]) for v in kept_out.values()),
             "n_kept_out_pairs": len(kept_out),
             "kept_out_by_kind": dict(sorted(kept_out_by_kind.items(), key=lambda kv: (-kv[1], kv[0]))),
             "n_kept_out_pairs_non_opposing_at_floor": sum(
                 1 for v in kept_out.values()
                 if v["cosine"] >= floor and not any(is_opposing(x) for x in v["kinds"])),
             "cosine_quantiles": _quantiles([v["cosine"] for v in found.values()]),
             "cosine_bins_of_pairs": _bins([v["cosine"] for v in pairs.values()])}
    return PairPlan(pairs=pairs, below_floor=below, kept_out=dict(sorted(kept_out.items())), stats=stats, k=k,
                    floor=floor)


def _quantiles(xs: Sequence[float]) -> Optional[dict]:
    if not xs:
        return None
    q = np.quantile(np.asarray(xs), [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])
    return dict(zip(("min", "p10", "p25", "median", "p75", "p90", "max"), (round(float(x), 4) for x in q)))


def _bins(xs: Sequence[float], bins: Sequence[float] = SHARE_BINS) -> dict:
    out = Counter()
    for c in xs:
        i = max([j for j, lo in enumerate(bins) if c >= lo] or [-1])
        out["below " + str(bins[0]) if i < 0 else (f"{bins[i]}-{bins[i + 1]}" if i + 1 < len(bins) else f"{bins[i]}+")] += 1
    return dict(out)


def parse_pair(text: str) -> tuple[str, str, Optional[str]]:
    """``A/B`` or ``A/B:note`` (``--also``): two stems and an optional note."""
    head, _, note = text.partition(":")
    a, sep, b = head.partition("/")
    if not sep or not a.strip() or not b.strip() or a.strip() == b.strip():
        raise ValueError(f"a pair is A/B or A/B:note with two different stems, not {text!r}")
    return a.strip(), b.strip(), (note.strip() or None)


# --------------------------------------------------------------------------- readings

def _int(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def direction_reading(r: Optional[Mapping], *, target: str, other: str) -> Optional[dict]:
    """One direction (a :meth:`NoveltyRunner.read_pairs` result) under M3's rule at cut-off 3: ``{"target", "other",
    "sonnet", "opus", "opus_role", "final", "at_3", "four", "reason", "unparsed"}``; ``{"target", "other",
    "stalled", "phase"}`` for a pair left without an answer; ``None`` for a direction not read.

    ``final``: Opus's value where the rule asked Opus (Sonnet at 3 or 2, or ``unsure``), else Sonnet's (an int,
    ``"opposite"``, ``"unsure"``, or ``None`` when the answer never parsed).  ``at_3``: the final reading is 3 or
    above (rule set 2 covering at cut-off 3); ``four``: it is 4.  ``reason``: Opus's where asked, else Sonnet's."""
    if r is None:
        return None
    if "stalled" in r:
        return {"target": target, "other": other, "stalled": r["stalled"], "phase": r.get("phase")}
    s = dict(r.get("sonnet") or {})
    o = dict(r["opus"]) if r.get("opus") else None
    sv = s.get("value")
    role = NV.OPUS_ROLES.get(NV.sonnet_action(sv, CUT_OFF))
    final = (o or {}).get("value") if role else sv
    fi = _int(final)
    reason = ((o or {}).get("reason") if role else None) or s.get("reason")
    return {"target": target, "other": other, "sonnet": s, "opus": o, "opus_role": role, "final": final,
            "at_3": fi is not None and fi >= CUT_OFF, "four": fi == 4, "reason": reason,
            "unparsed": final is None}


def needs_second(r: Optional[Mapping]) -> bool:
    """Whether a first-direction result sends the second direction: its final reading is 3 or above."""
    d = direction_reading(r, target="", other="") if r is not None else None
    return bool(d and d.get("at_3"))


def classify(ab: Optional[Mapping], ba: Optional[Mapping]) -> Optional[str]:
    """``same_4``, ``same_3``, ``one_way``, ``incomplete`` (a direction left without an answer, or the second not
    yet read after a first at 3 or above) or ``None`` (below 3 in every direction read)."""
    if ab is None or "stalled" in ab or (ba is not None and "stalled" in ba):
        return "incomplete"
    if ab["at_3"] and ba is None:
        return "incomplete"
    reads = [d for d in (ab, ba) if d is not None]
    n3 = sum(1 for d in reads if d["at_3"])
    if len(reads) == 2 and ab["four"] and ba["four"]:
        return "same_4"
    if len(reads) == 2 and n3 == 2:
        return "same_3"
    if n3 == 1:
        return "one_way"
    return None


def pair_row(a: str, b: str, *, traits: Mapping[str, NV.CorpusTrait], cosine: Optional[float], sources: Sequence[str],
             listed_by: Sequence[Mapping] = (), notes: Sequence[str] = (), first: Optional[Mapping] = None,
             second: Optional[Mapping] = None, second_because: Optional[str] = None,
             kinds: Sequence[str] = ()) -> dict:
    """One line of ``pairs.jsonl``: the two traits (stems, labels, descriptions), the cosine, why it was read
    (``sources``: ``scan`` and/or ``asked``), both directions' readings and finals, and the section."""
    ab = direction_reading(first, target=a, other=b)
    ba = direction_reading(second, target=b, other=a)
    return {"a": a, "b": b, "label_a": traits[a].label, "label_b": traits[b].label,
            "description_a": traits[a].description, "description_b": traits[b].description,
            "cosine": cosine, "sources": list(sources), "listed_by": [dict(x) for x in listed_by],
            "notes": list(notes), "arrangement_kinds": list(kinds), "ab": ab, "ba": ba,
            "second_because": second_because if ba is not None else None,
            "final_ab": (ab or {}).get("final"), "final_ba": (ba or {}).get("final"), "section": classify(ab, ba)}


# --------------------------------------------------------------------------- the scan

@dataclass
class ScanPlan:
    """What the scan reads: ``pairs`` ``{(a, b): {"cosine", "sources", "listed_by", "notes", "kinds"}}`` (``a < b``),
    the scan's nearest pairs and the asked ones; ``both_ways``: the pairs read in both directions whatever the first
    says (the asked ones)."""
    pairs: dict
    both_ways: set = field(default_factory=set)

    def first_items(self) -> list[tuple[str, str, int]]:
        return [(a, b, 1) for a, b in self.pairs]


def scan_plan(plan: PairPlan, *, also: Sequence[tuple[str, str, Optional[str]]] = (), stems: Iterable[str],
              Z: Optional[np.ndarray] = None, partners: Optional[Mapping[str, Mapping]] = None) -> ScanPlan:
    """The scan's pairs plus the ``also`` pairs (``(a, b, note)``; read both ways); each asked pair takes its cosine
    from ``Z`` (rows in ``stems`` order) and its arrangement kinds from ``partners``.  ``ValueError`` for a stem not
    in ``stems``."""
    stems = list(stems)
    row = {s: i for i, s in enumerate(stems)}
    out = {p: {"cosine": v["cosine"], "sources": ["scan"], "listed_by": list(v["listed_by"]), "notes": [],
               "kinds": []} for p, v in plan.pairs.items()}
    both = set()
    for a, b, note in also:
        missing = [s for s in (a, b) if s not in row]
        if missing:
            raise ValueError(f"not a trait in the corpus: {', '.join(missing)}")
        p = tuple(sorted((a, b)))
        cos = round(float(Z[row[a]] @ Z[row[b]]), 6) if Z is not None else None
        d = out.setdefault(p, {"cosine": cos, "sources": [], "listed_by": [], "notes": [], "kinds": []})
        if "asked" not in d["sources"]:
            d["sources"].append("asked")
        if note:
            d["notes"].append(note)
        d["kinds"] = sorted(set(d["kinds"]) | set(((partners or {}).get(a) or {}).get(b) or []))
        both.add(p)
    return ScanPlan(pairs=dict(sorted(out.items())), both_ways=both)


def second_items(sp: ScanPlan, first: Mapping[tuple[str, str], Mapping]) -> list[tuple[str, str, int, str]]:
    """``(b, a, 2, because)`` for every pair whose second direction is read: the first read 3 or above
    (``first_at_3``), or the pair was asked about (``asked``).  A pair whose first direction stalled waits."""
    out = []
    for a, b in sp.pairs:
        r = first.get((a, b))
        if r is None or "stalled" in r:
            continue
        if needs_second(r):
            out.append((b, a, 2, "first_at_3"))
        elif (a, b) in sp.both_ways:
            out.append((b, a, 2, "asked"))
    return out


def run_scan(runner: NR.NoveltyRunner, sp: ScanPlan, cands: Mapping[str, CorpusCandidate], *,
             gate: Optional[Callable[[list], None]] = None) -> tuple[dict, dict, list]:
    """The first direction of every pair (wave ``d1``), ``gate(second items)`` (the CLI's cost check; it raises to
    stop), then the second directions (wave ``d2``).  ``(first, second, second items)``; a stop is raised after every
    answer received is recorded (the runner's)."""
    items = sp.first_items()
    first: dict = {}
    if items:
        targets = [cands[a] for a in dict.fromkeys(a for a, _, _ in items)]
        first = runner.run_pairs(targets, items, wave=FIRST_WAVE)
    back = second_items(sp, first)
    if gate is not None:
        gate(back)
    second: dict = {}
    if back:
        targets = [cands[b] for b in dict.fromkeys(b for b, _, _, _ in back)]
        second = runner.run_pairs(targets, [(b, a, pos) for b, a, pos, _ in back], wave=SECOND_WAVE)
    return first, second, back


def assemble_rows(sp: ScanPlan, *, traits: Mapping[str, NV.CorpusTrait], first: Mapping, second: Mapping,
                  back: Sequence[tuple]) -> list[dict]:
    """The ``pairs.jsonl`` rows, in pair order."""
    because = {(a, b): why for b, a, _, why in back}
    rows = []
    for (a, b), d in sp.pairs.items():
        rows.append(pair_row(a, b, traits=traits, cosine=d["cosine"], sources=d["sources"], listed_by=d["listed_by"],
                             notes=d["notes"], kinds=d["kinds"], first=first.get((a, b)), second=second.get((b, a)),
                             second_because=because.get((a, b))))
    return rows


# --------------------------------------------------------------------------- distributions

def _value_key(v: Any) -> str:
    return "unparsed" if v is None else str(v)


def readings_distribution(rows: Sequence[Mapping]) -> dict:
    """The final readings by direction, Sonnet's first readings, the Opus re-reads by role and how often Opus moved
    Sonnet's value, the sections, and the incomplete pairs."""
    first = Counter(_value_key(r["ab"].get("final")) for r in rows if r.get("ab") and "stalled" not in r["ab"])
    second = Counter(_value_key(r["ba"].get("final")) for r in rows if r.get("ba") and "stalled" not in r["ba"])
    sonnet = Counter()
    roles = Counter()
    moved = Counter()
    for r in rows:
        for d in (r.get("ab"), r.get("ba")):
            if not d or "stalled" in d:
                continue
            sonnet[_value_key((d.get("sonnet") or {}).get("value"))] += 1
            if d.get("opus_role"):
                roles[d["opus_role"]] += 1
                sv, ov = (d.get("sonnet") or {}).get("value"), (d.get("opus") or {}).get("value")
                moved["same" if sv == ov else ("up" if _int(sv) is not None and _int(ov) is not None and ov > sv
                                               else ("down" if _int(sv) is not None and _int(ov) is not None
                                                     else "other"))] += 1
    order = ["0", "1", "2", "3", "4", "opposite", "unsure", "unparsed"]

    def ordered(c: Counter) -> dict:
        return {k: c[k] for k in order if c.get(k)} | {k: v for k, v in sorted(c.items()) if k not in order}
    sections = Counter(r.get("section") or "below_3" for r in rows)
    return {"first_direction_final": ordered(first), "second_direction_final": ordered(second),
            "sonnet_first_readings": ordered(sonnet), "opus_rereads_by_role": dict(roles),
            "opus_vs_sonnet": dict(moved), "sections": dict(sections),
            "n_second_read": sum(1 for r in rows if r.get("ba") is not None),
            "second_read_because": dict(Counter(r.get("second_because") for r in rows if r.get("ba") is not None))}


# --------------------------------------------------------------------------- the estimate

@dataclass
class Shares:
    """Per cosine bin (lower edges ``bins``), measured on M3's recorded readings (candidate against corpus trait):
    ``opus``, the share of Sonnet readings the rule at cut-off 3 sends to Opus (2, 3 or unsure); ``second``, the share
    whose final reading is 3 or above; ``n``, the readings behind them.  A bin with fewer than
    :data:`MIN_SHARE_OBS` readings takes 1.0, so that the estimate errs high."""
    bins: tuple
    opus: tuple
    second: tuple
    n: tuple

    def at(self, cosine: float) -> tuple[float, float]:
        i = max([j for j, lo in enumerate(self.bins) if cosine >= lo] or [0])
        return self.opus[i], self.second[i]

    def as_dict(self) -> dict:
        return {"bins": list(self.bins), "opus": [round(x, 4) for x in self.opus],
                "second": [round(x, 4) for x in self.second], "n": list(self.n)}


def measured_shares(readings: Iterable[Mapping], *, bins: Sequence[float] = SHARE_BINS,
                    min_obs: int = MIN_SHARE_OBS) -> Shares:
    """:class:`Shares` from M3 ``readings.jsonl`` rows (``cosine``, ``sonnet``, ``opus``).  The final reading is
    Opus's where Opus read the pair, else Sonnet's (a cut-off-4 row's Sonnet 2 was never re-read, so the second
    share errs slightly low there; the gate re-estimates on the real first readings)."""
    bins = tuple(bins)
    n, no, n3 = ([0] * len(bins) for _ in range(3))
    for r in readings:
        c = r.get("cosine")
        if c is None or c < bins[0] or r.get("sonnet") is None:
            continue
        i = max(j for j, lo in enumerate(bins) if c >= lo)
        sv = (r.get("sonnet") or {}).get("value")
        ov = (r.get("opus") or {}).get("value") if r.get("opus") else None
        fin = ov if ov is not None else sv
        n[i] += 1
        no[i] += sv in (2, 3, "unsure")
        n3[i] += _int(fin) is not None and fin >= CUT_OFF

    def share(k):
        return tuple((k[i] / n[i]) if n[i] >= min_obs else 1.0 for i in range(len(bins)))
    return Shares(bins=bins, opus=share(no), second=share(n3), n=tuple(n))


def estimate_scan(sp: ScanPlan, shares: Shares, *, overlap_tokens: Optional[Mapping[str, tuple[int, int]]] = None,
                  transport: str = "live") -> Estimate:
    """The scan's estimate before any call: Sonnet on every first direction; Opus on the bin's Opus share; the second
    direction on the bin's second share (every asked pair in full), Sonnet then Opus on all of it (errs high: a
    Sonnet 4 is not re-read)."""
    tok = dict(NR.OVERLAP_TOKENS) | dict(overlap_tokens or {})
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    est = Estimate()
    n = len(sp.pairs)
    o1 = s2 = 0.0
    for p, d in sp.pairs.items():
        op, sec = shares.at(d["cosine"] if d["cosine"] is not None else shares.bins[0])
        o1 += op
        s2 += 1.0 if p in sp.both_ways else sec
    est.add(f"first direction, Sonnet ({n} pairs)", NR.FIRST_MODEL + suffix, n, *tok["sonnet"])
    est.add("first direction, Opus (Sonnet's 3s, 2s and unsure; M3's share by cosine bin)", NR.SECOND_MODEL + suffix,
            int(round(o1)), *tok["opus"])
    est.add("second direction, Sonnet (first final 3 or above, M3's share by bin; the asked pairs in full)",
            NR.FIRST_MODEL + suffix, int(round(s2)), *tok["sonnet"])
    est.add("second direction, Opus (all of the second-direction Sonnet readings)", NR.SECOND_MODEL + suffix,
            int(round(s2)), *tok["opus"])
    return est


def estimate_second(back: Sequence, *, overlap_tokens: Optional[Mapping[str, tuple[int, int]]] = None,
                    transport: str = "live") -> Estimate:
    """The gate's estimate of the second direction on the real items: Sonnet on each, Opus on each (errs high)."""
    tok = dict(NR.OVERLAP_TOKENS) | dict(overlap_tokens or {})
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    est = Estimate()
    est.add(f"second direction, Sonnet ({len(back)} pairs)", NR.FIRST_MODEL + suffix, len(back), *tok["sonnet"])
    est.add("second direction, Opus (all of them; errs high)", NR.SECOND_MODEL + suffix, len(back), *tok["opus"])
    return est


# --------------------------------------------------------------------------- deliberate near-duplicates

_PLAIN = re.compile(r"plain trait ([A-Za-z][A-Za-z_ -]*?)(?=\s*(?:[,;(]|$| in ))")


def trait_sources(data_dir: Path) -> dict[str, str]:
    """``{stem: source}`` of the trait files that carry a ``source`` field (a standard's provenance, and where a
    near-duplicate is deliberate, a clause saying so: the naming rule asks for it there, never in the description)."""
    import json
    out = {}
    for p in sorted((Path(data_dir) / "traits" / "instructions").glob("*.json")):
        s = json.loads(p.read_text(encoding="utf-8")).get("source")
        if isinstance(s, str) and s.strip():
            out[p.stem] = s.strip()
    return out


def _names(text: str, stem: str, traits: Mapping[str, NV.CorpusTrait]) -> bool:
    t = traits.get(stem)
    for c in {stem, stem.replace("_", " "), t.label if t else None} - {None, ""}:
        if re.search(rf"(?<![\w-]){re.escape(c)}(?![\w-])", text, re.I):
            return True
    return False


def deliberate_note(a: str, b: str, *, sources: Mapping[str, str], traits: Mapping[str, NV.CorpusTrait]
                    ) -> Optional[str]:
    """The ``source`` clause that records ``a`` and ``b`` as a deliberate near-duplicate, or ``None``: a clause of
    either file's ``source`` that speaks of deliberate duplication and names the other trait (stem or label), or two
    clauses naming the same plain trait (two standards' versions of one trait)."""
    def clauses(stem):
        return [c.strip() for c in (sources.get(stem) or "").split(";") if "deliberat" in c.lower()]
    for x, y in ((a, b), (b, a)):
        for c in clauses(x):
            if _names(c, y, traits):
                return f"{traits[x].label if x in traits else x}: {c}"
    plain = {}
    for x in (a, b):
        for c in clauses(x):
            m = _PLAIN.search(c)
            if m:
                plain[x] = m.group(1).strip().lower()
    if len(plain) == 2 and plain[a] == plain[b]:
        return f"both: deliberate near-duplicates of the plain trait {plain[a]}"
    return None


def mark_deliberate(rows: Sequence[dict], *, sources: Mapping[str, str], traits: Mapping[str, NV.CorpusTrait]) -> int:
    """Set each row's ``deliberate`` (:func:`deliberate_note`); the number marked."""
    n = 0
    for r in rows:
        r["deliberate"] = deliberate_note(r["a"], r["b"], sources=sources, traits=traits)
        n += r["deliberate"] is not None
    return n


# --------------------------------------------------------------------------- the cosine table

_LINK =re.compile(r"\(\.\./\.\./traits/instructions/([A-Za-z0-9_]+)\.json\)")


def parse_drop_or_merge(text: str, *, section: str = "## Partners excluded") -> list[dict]:
    """The rows of ``drop_or_merge.md``'s partners-excluded table: ``[{"a", "b", "flagged_by", "raw"}]`` in table
    order (``a``, ``b`` as the table gives them: the trait and its nearest)."""
    start = text.find(section)
    if start < 0:
        return []
    body = text[start + len(section):]
    end = body.find("\n## ")
    body = body if end < 0 else body[:end]
    out = []
    for line in body.splitlines():
        if not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        stems = [m.group(1) for c in cells[:2] for m in [_LINK.search(c)] if m]
        if len(stems) != 2:
            continue
        try:
            raw = float(cells[3])
        except (IndexError, ValueError):
            raw = None
        out.append({"a": stems[0], "b": stems[1], "flagged_by": cells[2] if len(cells) > 2 else None, "raw": raw})
    return out


# --------------------------------------------------------------------------- the report

TRAIT_REL = "../../traits/instructions/"
GLOSSARY = "../../../reports/trait_gap_generation/glossary.md"
RUBRIC_REL = "../../../reports/trait_gap_generation/rubrics/overlap_concept.md"
REVIEW_PLAN_REL = "../../../reports/trait_gap_generation/coding_plan_review.md"


def _md(s: Any) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def trait_link(stem: str, label: Optional[str] = None, *, exists: bool = True) -> str:
    """``[label](../../traits/instructions/<stem>.json)``; a stem with no file in the scanned corpus is linked at its
    path all the same, its label in italics (its file is not in the corpus this scan read)."""
    text = _md(label or stem.replace("_", " "))
    return f"[{text}]({TRAIT_REL}{stem}.json)" if exists else f"[*{text}*]({TRAIT_REL}{stem}.json)"


def _v(v: Any) -> str:
    return "?" if v is None else str(v)


def reading_text(d: Optional[Mapping]) -> str:
    """``S4``, ``S3 O4``, ``S2 O1``, ``S opposite``; ``not read``; ``stalled``."""
    if d is None:
        return "not read"
    if "stalled" in d:
        return "stalled"
    s = f"S{_v((d.get('sonnet') or {}).get('value'))}"
    if d.get("opus_role"):
        s += f" O{_v((d.get('opus') or {}).get('value'))}"
    return s.replace("Sopposite", "S opposite").replace("Ounsure", "O unsure").replace("Sunsure", "S unsure") \
        .replace("Oopposite", "O opposite")


def _final_num(d: Optional[Mapping]) -> int:
    v = _int((d or {}).get("final"))
    return -1 if v is None else v


def row_reason(r: Mapping) -> str:
    """The reason of the direction with the higher final reading (the first on a tie): Opus's where asked."""
    ab, ba = r.get("ab"), r.get("ba")
    d = ba if (ba and "stalled" not in ba and _final_num(ba) > _final_num(ab)) else ab
    return (d or {}).get("reason") or ""


def _section_rows(rows: Sequence[Mapping], section: str) -> list[Mapping]:
    xs = [r for r in rows if r.get("section") == section]
    return sorted(xs, key=lambda r: (-(_final_num(r.get("ab")) + _final_num(r.get("ba"))), -(r.get("cosine") or 0),
                                     r["a"], r["b"]))


def _table(rows: Sequence[Mapping], *, with_notes: bool = False) -> list[str]:
    head = "| # | traits | cosine | first → second | second → first | description (first) | description (second) | reason |"
    sep = "|---|---|---|---|---|---|---|---|"
    if with_notes:
        head = head[:-1] + " note |"
        sep += "---|"
    out = [head, sep]
    for i, r in enumerate(rows, 1):
        pair = f"{trait_link(r['a'], r['label_a'])} and {trait_link(r['b'], r['label_b'])}"
        if "scan" not in r.get("sources", []):
            pair += " (read on request)"
        if r.get("deliberate"):
            pair += f"<br>*deliberate, by the `source` field ({_md(r['deliberate'])})*"
        cos = "" if r.get("cosine") is None else f"{r['cosine']:.3f}"
        line = (f"| {i} | {pair} | {cos} | {reading_text(r.get('ab'))} | {reading_text(r.get('ba'))} | "
                f"{_md(r['description_a'])} | {_md(r['description_b'])} | {_md(row_reason(r))} |")
        if with_notes:
            line += f" {_md('; '.join(r.get('notes') or []))} |"
        out.append(line)
    return out


def _section_name(s: Optional[str]) -> str:
    return {"same_4": "4 and 4", "same_3": "3 or more both ways", "one_way": "3 or more one way",
            "incomplete": "incomplete", None: "below 3"}.get(s, str(s))


def comparison(rows: Sequence[Mapping], cosine_rows: Sequence[Mapping], *, corpus: Iterable[str],
               plan: Optional[PairPlan] = None) -> dict:
    """This scan against the cosine table: for each of its rows, the pair's readings and section here (or why it was
    not read); and the pairs this scan puts at 3 or more both ways that the table does not name."""
    corpus = set(corpus)
    by = {(r["a"], r["b"]): r for r in rows}
    table = []
    named = set()
    for x in cosine_rows:
        p = tuple(sorted((x["a"], x["b"])))
        named.add(p)
        r = by.get(p)
        if r is not None:
            why = None
        elif not (x["a"] in corpus and x["b"] in corpus):
            why = "not in the corpus this scan read"
        elif plan is not None and p in plan.below_floor:
            why = "below the cosine floor"
        elif plan is not None and p in plan.kept_out:
            why = "arrangement partners"
        else:
            why = "not among either trait's nearest neighbours here"
        table.append({**x, "pair": list(p), "section": r.get("section") if r else None, "row": r, "why_not_read": why})
    missed = [r for r in rows if r.get("section") in ("same_4", "same_3") and (r["a"], r["b"]) not in named]
    one_way_missed = [r for r in rows if r.get("section") == "one_way" and (r["a"], r["b"]) not in named]
    return {"table": table, "missed_both": missed, "missed_one_way": one_way_missed,
            "n_rated": Counter(t["section"] or ("not read" if t["why_not_read"] else "below 3") for t in table)}


def report_markdown(rows: Sequence[Mapping], *, plan: PairPlan, traits: Mapping[str, NV.CorpusTrait],
                    cmp: Optional[dict], run: Mapping, dist: Mapping, cosine_table_rel: str,
                    per_kind: int = 5) -> str:
    """``near_duplicates.md``, for Roger (links relative to ``data/candidates/near_duplicates_916/``)."""
    st = plan.stats
    corpus = set(traits)
    rub = run.get("rubric") or {}
    n_asked = sum(1 for r in rows if "asked" in r.get("sources", []))
    sec_counts = Counter(r.get("section") for r in rows)
    L: list[str] = []
    L.append("# Near-duplicates in the trait corpus: the same-concept call on each trait's nearest neighbours")
    L.append("")
    L.append(
        f"W3, the pre-extraction drop-or-merge review, second pass.  Every trait file in the corpus ({st['n_traits']} "
        f"at commit `{run.get('git_sha')}`) was compared with its {plan.k} nearest other traits by "
        f"[cosine similarity]({GLOSSARY}#cosine-similarity) (1: the same direction, 0: unrelated) in M3's "
        f"[covered space]({GLOSSARY}#covered-and-directional-settings) (the OpenAI embedding of `label: description`, "
        f"[centred]({GLOSSARY}#centred-space) on the corpus mean, as M3, the novelty check, retrieves), leaving out "
        "its **arrangement partners**: every member of any arrangement its file records (a clean pair, a triangle, a "
        "sequence, a set, a map, a ring, a square, the MBTI 4-cube, an orthoplex) and a clean pair by label alone.  "
        f"Pairs under cosine {plan.floor} were dropped (decision 11 of [coding_plan_review.md]({REVIEW_PLAN_REL}): "
        "below it 0.1% of M3's recorded readings were 4).  Each remaining pair was read by M3's same-concept call "
        f"([rubric A]({GLOSSARY}#rubric-a-concept-similarity-rubric-b-co-occurrence), [overlap_concept.md]({RUBRIC_REL}) "
        f"version {rub.get('version')}), one pair per call, which answers 0 to 4 or \"opposite\" or \"unsure\": **4** "
        "\"the same concept: either label could replace the other in any description of a persona\"; **3** \"the same "
        "concept, differing only in scope, degree or emphasis\"; **2** overlapping concepts, each adding something; "
        "**1** related but distinct; **0** different.")
    L.append("")
    L.append(
        "**How a pair was read.**  Sonnet 5.5 reads first; Opus 5.5 re-reads Sonnet's 3s, 2s and \"unsure\" answers "
        "(M3's rule at **cut-off** 3, the reading at which M3 counts a candidate as covered far from alignment), and "
        "its reading is the final one where it was asked; a Sonnet 4, 1 or 0 stands.  The **first direction** has the "
        "trait whose file name sorts first as the target; the **second direction** (the other way round) was read only "
        "where the first's final reading was 3 or above, as R1, the candidate-grouping step, does: so every pair "
        "reading 3 or above both ways is found, but a pair reading 3 or above only in its second direction is not.  "
        "Readings are shown as `S3 O4` (Sonnet 3, then Opus 4: final 4) or `S4` (Sonnet alone); the reason is from "
        "the direction with the higher final reading, Opus's where Opus read it.")
    L.append("")
    L.append(
        f"**Counts.**  {st['n_directed']} nearest-neighbour entries, {st['n_unique_before_floor']} distinct pairs, "
        f"{st['n_below_floor']} under the floor, **{st['n_pairs']} read**"
        + (f" (plus {n_asked - sum(1 for r in rows if 'asked' in r['sources'] and 'scan' in r['sources'])} read on "
           "request)" if n_asked else "")
        + f"; {dist.get('n_second_read', 0)} read the other way too.  "
        f"**{sec_counts.get('same_4', 0)}** pairs are 4 both ways, **{sec_counts.get('same_3', 0)}** 3 or more both "
        f"ways, **{sec_counts.get('one_way', 0)}** 3 or more one way only"
        + (f"; {sec_counts['incomplete']} incomplete (resume the run)" if sec_counts.get("incomplete") else "")
        + f".  Spend ${run.get('cost_usd', 0):.2f}, live.")
    n_del = {s: sum(1 for r in rows if r.get("section") == s and r.get("deliberate")) for s in SECTIONS}
    if any(n_del.values()):
        L.append("")
        L.append(
            f"**Deliberate near-duplicates** are marked in the tables ({n_del['same_4']} of the 4-and-4 pairs, "
            f"{n_del['same_3']} of the 3-or-more pairs, {n_del['one_way']} of the one-way ones): pairs whose files' "
            "`source` field records the duplication as deliberate (a standard's version beside the plain trait, as "
            "the naming rule asks it to be recorded), so they are expected here and need no decision unless the "
            "standard's version is to go.")
    L.append("")
    for s in SECTIONS:
        xs = _section_rows(rows, s)
        L.append(f"## {SECTION_TITLES[s]}")
        L.append("")
        if s == "same_4":
            L.append("Final reading 4 in both directions: either label could replace the other.  The strongest "
                     "candidates to drop one or merge.")
            L.append("")
        elif s == "same_3":
            L.append("Final reading 3 or above in both directions, not 4 and 4: the same concept with a different "
                     "scope, degree or emphasis (or 4 one way and 3 the other).  Candidates to merge, or to sharpen "
                     "one description so the two separate.")
            L.append("")
        elif s == "one_way":
            L.append("The first direction read 3 or above and the second did not (or, for a pair read on request, "
                     "either way round).  Usually one trait is a narrower or stronger case of the other.")
            L.append("")
        if not xs:
            L.append("None.")
        else:
            L += _table(xs)
        L.append("")
    asked = [r for r in rows if "asked" in r.get("sources", [])]
    L.append("## Pairs Roger asked about")
    L.append("")
    if not asked:
        L.append("None were named.")
    else:
        L.append("Read both ways, whatever the first direction said, and listed here whether or not they reached 3.  "
                 "\"In the scan\" means the pair was also among the nearest neighbours read above.")
        L.append("")
        L.append("| traits | cosine | in the scan | first → second | second → first | here | description (first) | "
                 "description (second) | reason | note |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in asked:
            cos = "" if r.get("cosine") is None else f"{r['cosine']:.3f}"
            inscan = "yes" if "scan" in r["sources"] else (
                "no: arrangement partners (" + ", ".join(r.get("arrangement_kinds") or []) + ")"
                if r.get("arrangement_kinds") else "no")
            L.append(f"| {trait_link(r['a'], r['label_a'])} and {trait_link(r['b'], r['label_b'])} | {cos} | {inscan} | "
                     f"{reading_text(r.get('ab'))} | {reading_text(r.get('ba'))} | {_section_name(r.get('section'))} | "
                     f"{_md(r['description_a'])} | {_md(r['description_b'])} | {_md(row_reason(r))} | "
                     f"{_md('; '.join(r.get('notes') or []))} |")
    L.append("")
    if cmp is not None:
        L.append("## Against the cosine table")
        L.append("")
        n_all = len(cmp["table"])
        rated = Counter(t["section"] for t in cmp["table"])
        L.append(
            f"[drop_or_merge.md]({cosine_table_rel}) flags {n_all} pairs by an [upper fence]({GLOSSARY}#t_hi-t_lo-upper-fence) "
            "on nearest-neighbour cosines (partners excluded), with two embedding models.  Here "
            f"{rated.get('same_4', 0)} of them read 4 both ways, {rated.get('same_3', 0)} 3 or more both ways, "
            f"{rated.get('one_way', 0)} 3 or more one way, "
            f"{sum(1 for t in cmp['table'] if t['row'] is not None and t['section'] is None)} below 3, and "
            f"{_n_not_read(cmp)} not read.")
        L.append("")
        L.append("| traits | flagged by | cosine there (raw) | cosine here | first → second | second → first | here |")
        L.append("|---|---|---|---|---|---|---|")
        for t in cmp["table"]:
            r = t["row"]
            a, b = t["a"], t["b"]
            la = traits[a].label if a in corpus else None
            lb = traits[b].label if b in corpus else None
            here = _section_name(t["section"]) if r is not None else f"not read: {t['why_not_read']}"
            cos = "" if r is None or r.get("cosine") is None else f"{r['cosine']:.3f}"
            raw = "" if t.get("raw") is None else f"{t['raw']:.3f}"
            L.append(f"| {trait_link(a, la, exists=a in corpus)} and {trait_link(b, lb, exists=b in corpus)} | "
                     f"{_md(t.get('flagged_by') or '')} | {raw} | {cos} | {reading_text((r or {}).get('ab'))} | "
                     f"{reading_text((r or {}).get('ba'))} | {here} |")
        L.append("")
        mb = sorted(cmp["missed_both"], key=lambda r: (r["section"] != "same_4", -(r.get("cosine") or 0)))
        L.append(f"**Found here, not in the cosine table: {len(mb)} pairs at 3 or more both ways** "
                 f"({sum(1 for r in mb if r['section'] == 'same_4')} of them 4 and 4; "
                 f"{sum(1 for r in mb if r.get('deliberate'))} deliberate by their `source` field), and "
                 f"{len(cmp['missed_one_way'])} at 3 or more one way.  The pairs at 3 or more both ways, 4 and 4 first, "
                 "then by cosine:")
        L.append("")
        if mb:
            L.append(", ".join(f"{trait_link(r['a'], r['label_a'])} and {trait_link(r['b'], r['label_b'])} "
                               f"({r['cosine']:.2f}, {'4/4' if r['section'] == 'same_4' else '3+/3+'}"
                               f"{', deliberate' if r.get('deliberate') else ''})" for r in mb) + ".")
        else:
            L.append("None.")
        L.append("")
    L.append("## What this scan does not see")
    L.append("")
    nb = st["n_below_floor"]
    L.append(f"- **The floor.**  {nb} nearest pairs under cosine {plan.floor} were not read.  At decision 11's rates "
             f"(0.1% read 4, 3.9% read 3 or above, measured on candidate-against-corpus readings) that is about "
             f"{nb * 0.001:.1f} pairs at 4 and {nb * 0.039:.0f} at 3 or above left unseen.")
    ko = plan.kept_out
    non_opp = sorted(((p, v) for p, v in ko.items() if not any(is_opposing(k) for k in v["kinds"])),
                     key=lambda kv: (-kv[1]["cosine"], kv[0]))
    by_kind = ", ".join(f"{k} {n}" for k, n in st["kept_out_by_kind"].items())
    L.append(f"- **Arrangement partners.**  {st['n_kept_out_neighbours']} neighbours nearer to a trait than the last "
             f"of its {plan.k} read neighbours were left out as arrangement partners ({by_kind}).  For a clean pair or "
             "a simplex that is the point (its members are opposites), but the members of a sequence, set, map, ring, "
             "square, cube or orthoplex are neighbours, not opposites, and can be near-duplicates: "
             f"{len(non_opp)} such pairs ({st['n_kept_out_pairs_non_opposing_at_floor']} at the floor or above) were "
             f"not read.  The nearest of each kind, unread unless marked (up to {per_kind} a kind):")
    by: dict[str, list] = defaultdict(list)
    for p, v in non_opp:
        by[" + ".join(v["kinds"])].append((p, v))
    for kind in sorted(by, key=lambda k: (-len(by[k]), k)):
        items = by[kind]
        shown = ", ".join(
            f"{trait_link(a, traits[a].label)} and {trait_link(b, traits[b].label)} ({v['cosine']:.2f}"
            + (f"; read on request: {_section_name(rd.get('section'))}" if rd else "") + ")"
            for (a, b), v in items[:per_kind]
            for rd in [next((r for r in rows if (r["a"], r["b"]) == (a, b)), None)])
        L.append(f"  - {kind} ({len(items)} pairs): {shown}{', ...' if len(items) > per_kind else ''}")
    missing = sorted({s for t in (cmp or {}).get("table", []) for s in (t["a"], t["b"]) if s not in corpus})
    if missing:
        L.append(f"- **Not in the corpus read.**  {', '.join(trait_link(s, exists=False) for s in missing)}: "
                 "flagged by the cosine table, which was run on the main checkout with these files present, but not "
                 "committed at the commit this scan read, so not read here.")
    L.append("- **Second direction only.**  A pair whose first direction read below 3 was not read the other way, so "
             "a pair at 3 or more only with the second trait as the target is not in \"One way only\".")
    L.append("")
    L.append("## The run")
    L.append("")
    roles, moved = dist["opus_rereads_by_role"], dist["opus_vs_sonnet"]
    L.append(f"- Final readings, first direction: {_dist_text(dist['first_direction_final'])}; second direction: "
             f"{_dist_text(dist['second_direction_final'])}.  Opus re-read {sum(roles.values())} Sonnet readings "
             f"({roles.get('at_cut_off', 0)} Sonnet 3s, {roles.get('below_cut_off', 0)} Sonnet 2s, "
             f"{roles.get('sonnet_unsure', 0)} unsure): it agreed {moved.get('same', 0)} times, read higher "
             f"{moved.get('up', 0)}, lower {moved.get('down', 0)}"
             + (f", other {moved['other']}" if moved.get("other") else "") + ".")
    L.append(f"- Models: {run.get('models', {}).get('overlap_first')} then {run.get('models', {}).get('overlap_second')}; "
             f"rubric `{rub.get('name')}` version {rub.get('version')} (sha256 `{str(rub.get('sha256'))[:12]}`); "
             f"embedding `{run.get('embedding', {}).get('model')}`, space `{run.get('embedding', {}).get('variant')}`, "
             f"representation `{run.get('embedding', {}).get('representation')}`.")
    L.append(f"- Spend ${run.get('cost_usd', 0):.2f} (estimate ${run.get('estimate_usd', 0):.2f}, cap "
             f"${run.get('cap_usd') or 0:.2f}), {run.get('n_calls', 0)} calls, live; "
             f"{run.get('wall_time_s', 0) / 60:.0f} minutes.")
    L.append("- Files: [pairs.jsonl](./pairs.jsonl) (every pair, both directions' readings and reasons), "
             "[responses.jsonl](./responses.jsonl) (every response), [usage.json](./usage.json), "
             "[run.json](./run.json) (settings, counts, provenance).")
    L.append("")
    return "\n".join(L)


def _n_not_read(cmp: Mapping) -> int:
    return sum(1 for t in cmp["table"] if t["row"] is None)


def _dist_text(d: Mapping) -> str:
    return ", ".join(f"{k}: {v}" for k, v in d.items()) or "none"
