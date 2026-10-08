"""Opposed-head reconstruction: which Roget heads are the two poles of one opposition.

Roget printed most heads in two columns of correlatives (604 Resolution beside 605
Irresolution); the Gutenberg text is linear, so the pairs are reconstructed by rules over
neighbouring heads in a subsection (plan § 5, ``roget_pairs.py``).  Under the plan's 2026-10-08
revision there is no LLM pass: what the rules leave open stays open.

Evidence for a candidate pair (two heads adjacent in their subsection, or one apart with a
lettered head between them, or named by an editorial ``{ant. N}`` note):

* ``annotation``: the text's own ``{ant. N}`` / ``{opp. N}`` note;
* ``title_negation``: one title negates the other (Willingness / Unwillingness; "Absence of ...");
* ``negation``: items of one head that are prefix or suffix negations of items of the other
  (resolute / irresolute; -ful / -less), over the adjectives and nouns, :func:`negation_overlap`;
* ``wn_links``: items of one head that WordNet lists as antonyms of items of the other.

Since 2026-10-09 the rules are second: Roget's own pairing, read from the Tabular Synopsis of Categories of
the printed 1911 edition (:mod:`.synopsis`), is the strongest evidence, and :func:`merge_synopsis` lets it
decide every head it prints (``source: "synopsis"``), keeping the rule result in each record for
comparison; the rules decide only the heads it does not print.

A candidate is confirmed when the annotation or title negation is present, or the negation count
and fraction reach :data:`CONFIRM` ``n_min`` / ``frac_min``, or the WordNet links reach ``wn_min``.
Confirmed candidates are matched greedily, strongest first (:func:`rule_pairs`).  A **weak** pass
then pairs two still-unpaired adjacent heads with any evidence at all (one negation or one WordNet
link), recorded with ``source: "rule_weak"``.  A lettered head next to a matched pair becomes a
``triad`` member (604 / 604a / 605); a head left with an unpaired neighbour is ``unresolved``; a
head with none is a ``singleton``.  Partners are reciprocal by construction.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Collection, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text

from .parse import Head, RogetIndex

NEG_PREFIXES = ("un", "in", "im", "ir", "il", "dis", "non", "a", "mis")
SUFFIX_SWAPS = (("ful", "less"),)
#: Confirmation thresholds (task 5: the sweep printed by ``pair`` checks them on the known pairs).
CONFIRM = dict(n_min=2, frac_min=0.08, wn_min=2)
PAIRING_RULES_VERSION = 1
KINDS = ("pair", "triad", "singleton", "unresolved")


@dataclass
class NegationScore:
    n: int
    frac: float
    examples: list = field(default_factory=list)


def _norm(w: str) -> str:
    return w.lower().replace("-", "").replace(" ", "")


def _negates(a: str, b: str) -> bool:
    """``b`` is a prefix negation of ``a`` (or the -ful / -less swap of it)."""
    if len(a) < 4 or len(b) < 4:
        return False
    for p in NEG_PREFIXES:
        if b == p + a and (p != "a" or len(a) >= 5):
            return True
    for x, y in SUFFIX_SWAPS:
        if a.endswith(x) and b == a[: -len(x)] + y:
            return True
        if a.endswith(y) and b == a[: -len(y)] + x:
            return True
    return False


def negation_overlap(items_a: Sequence[str], items_b: Sequence[str]) -> NegationScore:
    """Items of one list that negate an item of the other, either direction (symmetric).
    ``n`` counts distinct matched pairs; ``frac = n / min(len(a), len(b))``."""
    na = {_norm(x): x for x in items_a if " " not in x.strip()}
    nb = {_norm(x): x for x in items_b if " " not in x.strip()}
    pairs = []
    for ka, a in na.items():
        for kb, b in nb.items():
            if _negates(ka, kb) or _negates(kb, ka):
                pairs.append((a, b))
    denom = max(1, min(len(set(items_a)), len(set(items_b))))
    pairs = sorted(set(pairs))
    return NegationScore(n=len(pairs), frac=round(len(pairs) / denom, 4), examples=[list(p) for p in pairs[:5]])


def wn_antonym_links(items_a: Sequence[str], items_b: Sequence[str], lex, *, limit: int = 40) -> int:
    """Pairs ``(x in a, y in b)`` (first ``limit`` items of each) where WordNet lists ``y`` as a
    sense antonym of ``x`` or the reverse (adjectives and nouns), counted once."""
    if lex is None:
        return 0
    la = [x.lower() for x in list(dict.fromkeys(items_a))[:limit]]
    lb = [y.lower() for y in list(dict.fromkeys(items_b))[:limit]]
    sa, sb = set(la), set(lb)
    links = set()
    for x in la:
        for ant, _ in lex.antonyms(x, pos=("a", "s", "n")):
            if ant.lower() in sb:
                links.add((x, ant.lower()))
    for y in lb:
        for ant, _ in lex.antonyms(y, pos=("a", "s", "n")):
            if ant.lower() in sa:
                links.add((ant.lower(), y))
    return len(links)


def wn_cluster_coverage(adj_a: Sequence[str], adj_b: Sequence[str], lex, *, limit: int = 40) -> float:
    """Share of the two heads' single-word adjectives that WordNet's adjective clusters oppose to
    some adjective of the other head (indirect antonymy: a satellite is opposed to the satellites
    of its head's antonym, jubilant / dejected through elated / dejected).  ``(linked items of a +
    linked items of b) / (items of a + items of b)``; 0 without a lexicon."""
    if lex is None or not hasattr(lex, "antonym_heads"):
        return 0.0
    la = [x.lower() for x in list(dict.fromkeys(adj_a))[:limit] if " " not in x.strip()]
    lb = [y.lower() for y in list(dict.fromkeys(adj_b))[:limit] if " " not in y.strip()]
    if not la or not lb:
        return 0.0
    ha = {x: lex.head_synsets(x) for x in la}
    hb = {y: lex.head_synsets(y) for y in lb}
    aa = {x: lex.antonym_heads(x) for x in la}
    ab = {y: lex.antonym_heads(y) for y in lb}
    linked_a = {x for x in la if any(aa[x] & hb[y] for y in lb)}
    linked_b = {y for y in lb if any(ab[y] & ha[x] for x in la)}
    return round((len(linked_a) + len(linked_b)) / (len(la) + len(lb)), 4)


_TITLE_NEG = ("un", "in", "im", "ir", "il", "dis", "non", "mis")


def title_negation(t1: str, t2: str) -> bool:
    """One title negates the other: a negating prefix (Willingness / Unwillingness), "Absence of
    X" / "Want of X" / "Lack of X", or the -ful / -less swap."""
    a, b = t1.lower().strip(), t2.lower().strip()
    for x, y in ((a, b), (b, a)):
        xs = x.replace("-", "")
        ys = y.replace("-", "")
        if any(ys == p + xs for p in _TITLE_NEG) and len(xs) >= 4:
            return True
        for lead in ("absence of ", "want of ", "lack of ", "absence or want of "):
            if y.startswith(lead) and y[len(lead):].strip() and (y[len(lead):].strip() in x or x in y[len(lead):]):
                return True
    return False


@dataclass
class HeadPairing:
    head: str
    partner: Optional[str]
    kind: str                    # pair | triad | singleton | unresolved
    members: list
    evidence: dict
    source: str                  # rule | rule_weak | unresolved

    def to_json(self) -> dict:
        d = asdict(self)
        d.pop("head")
        return d


def _profile_items(h: Head) -> list[str]:
    return h.items("Adj") + h.items("N") + [h.title]


def pair_evidence(a: Head, b: Head, lex, *, adjacent: bool = True) -> dict:
    neg = negation_overlap(_profile_items(a), _profile_items(b))
    return {"adjacent": adjacent,
            "annotation": (b.id in a.antonym_refs) or (a.id in b.antonym_refs),
            "title_negation": title_negation(a.title, b.title),
            "negation": asdict(neg),
            "wn_links": wn_antonym_links(a.items("Adj") + a.items("N"), b.items("Adj") + b.items("N"), lex),
            "wn_cluster": wn_cluster_coverage(a.items("Adj"), b.items("Adj"), lex)}


def confirmed(ev: Mapping, confirm: Mapping = CONFIRM) -> bool:
    """The strict rule: annotation, title negation, enough negation pairs, or enough direct
    WordNet antonym pairs (cluster-level opposition alone is not enough)."""
    neg = ev["negation"]
    return bool(ev["annotation"] or ev["title_negation"]
                or (neg["n"] >= confirm["n_min"] and neg["frac"] >= confirm["frac_min"])
                or ev["wn_links"] >= confirm["wn_min"])


#: The weak pass's floor on cluster-level opposition (share of the two heads' adjectives).
WEAK_CLUSTER_MIN = 0.35


def weak(ev: Mapping) -> bool:
    """Any word-level evidence: one negation pair, one direct antonym pair, or cluster-level
    opposition over at least :data:`WEAK_CLUSTER_MIN` of the adjectives."""
    return (ev["negation"]["n"] >= 1 or ev["wn_links"] >= 1
            or ev.get("wn_cluster", 0.0) >= WEAK_CLUSTER_MIN)


def strength(ev: Mapping) -> float:
    return (10.0 * ev["annotation"] + 5.0 * ev["title_negation"] + ev["negation"]["n"]
            + 3.0 * ev["negation"]["frac"] + ev["wn_links"] + 4.0 * ev.get("wn_cluster", 0.0))


def candidate_pairs(index: RogetIndex, *, heads: Optional[Collection[str]] = None) -> list[tuple[str, str, bool]]:
    """``(a, b, adjacent)``: neighbours in each subsection (one apart when a lettered head sits
    between them) and the pairs the ``{ant. N}`` notes name."""
    scope = set(heads) if heads is not None else set(index.order)
    out: dict[tuple[str, str], bool] = {}
    for ids in index.by_subsection.values():
        ids = [h for h in ids if h in scope]
        for i, a in enumerate(ids):
            if i + 1 < len(ids):
                out.setdefault(tuple(sorted((a, ids[i + 1]), key=index.position)), True)
            # over a run of lettered heads to the next unlettered one (737 / 737a / 737b / 738)
            j = i + 1
            while j < len(ids) and index.heads[ids[j]].letter:
                j += 1
            if j > i + 1 and j < len(ids):
                out.setdefault(tuple(sorted((a, ids[j]), key=index.position)), True)
    for a in scope:
        for t in index.heads[a].antonym_refs:
            if t in index.heads and t != a:
                key = tuple(sorted((a, t), key=index.position))
                out.setdefault(key, False)
    return [(a, b, adj) for (a, b), adj in out.items()]


#: Weights of the tiling (:func:`rule_pairs`): a confirmed pair scores ``CONFIRMED_BONUS`` plus its
#: strength, a weak one ``WEAK_BONUS`` plus its strength, a pair with no evidence ``POSITION_PRIOR``
#: (Roget printed the heads as correlative pairs; ``position_pass=False`` turns the prior off).
CONFIRMED_BONUS = 5.0
WEAK_BONUS = 1.0
POSITION_PRIOR = 0.5


def _tile(ids: Sequence[str], weight, is_lettered) -> list[tuple[str, str]]:
    """Best tiling of a subsection's heads into consecutive pairs and singles (dynamic
    programming): a head pairs with the next one, or across a run of lettered heads with the next
    unlettered one; singles score 0; ``weight(a, b)`` is a pair's score or ``None``."""
    n = len(ids)
    f = [0.0] * (n + 2)
    choice: list = [None] * (n + 1)
    for i in range(n - 1, -1, -1):
        best, pick = f[i + 1], None
        options = [i + 1] if i + 1 < n else []
        j = i + 1
        while j < n and is_lettered(ids[j]):
            j += 1
        if j > i + 1 and j < n:
            options.append(j)
        for j in options:
            w = weight(ids[i], ids[j])
            if w is None:
                continue
            if w + f[j + 1] > best + 1e-9:
                best, pick = w + f[j + 1], j
        f[i], choice[i] = best, pick
    out, i = [], 0
    while i < n:
        j = choice[i]
        if j is None:
            i += 1
        else:
            out.append((ids[i], ids[j]))
            i = j + 1
    return out


def rule_pairs(index: RogetIndex, lex, *, heads: Optional[Collection[str]] = None,
               confirm: Mapping = CONFIRM, weak_pass: bool = True, position_pass: bool = False) -> dict[str, HeadPairing]:
    """Pair the heads in scope (default: every head); one :class:`HeadPairing` per head.

    1. Non-adjacent pairs named by an ``{ant. N}`` note are taken first.
    2. Each subsection is tiled into consecutive pairs and singles (:func:`_tile`): confirmed
       pairs (``source: rule``) weigh most, then weak ones (``rule_weak``), then evidence-free
       neighbours (``position``, only with ``position_pass``).
    3. A head of a ``position`` pair that is strictly opposed to a neighbour in an evidence pair is
       that pair's third pole (``triad``) and its position partner is freed (850 Taste beside 851
       Vulgarity / 852 Fashion).
    4. A lettered head beside a pair is a ``triad`` member; a head left over is ``unresolved`` when
       a neighbour is also unpaired, else a ``singleton``."""
    scope_set = set(index.order) if heads is None else set(heads)
    scope = [h for h in index.order if h in scope_set]
    cands = candidate_pairs(index, heads=scope)
    evid = {(a, b): pair_evidence(index.heads[a], index.heads[b], lex, adjacent=adj) for a, b, adj in cands}

    def ev_of(a, b):
        return evid.get((a, b)) or evid.get((b, a))

    partner: dict[str, str] = {}
    source: dict[str, str] = {}
    # 1. annotated non-adjacent pairs
    for (a, b), ev in sorted(evid.items(), key=lambda kv: -strength(kv[1])):
        if not ev["adjacent"] and ev["annotation"] and a not in partner and b not in partner:
            partner[a], partner[b] = b, a
            source[a] = source[b] = "rule"

    def classify(ev) -> Optional[str]:
        if ev is None:
            return None
        if confirmed(ev, confirm):
            return "rule"
        if weak_pass and weak(ev):
            return "rule_weak"
        if position_pass and ev["adjacent"]:
            return "position"
        return None

    def weight(a, b):
        if a in partner or b in partner:
            return None
        ev = ev_of(a, b)
        src = classify(ev)
        if src == "rule":
            return CONFIRMED_BONUS + strength(ev)
        if src == "rule_weak":
            return WEAK_BONUS + strength(ev)
        if src == "position":
            return POSITION_PRIOR + strength(ev)
        return None

    # 2. tile each subsection
    for ids in index.by_subsection.values():
        ids = [h for h in ids if h in scope_set and h not in partner]
        for a, b in _tile(ids, weight, lambda h: bool(index.heads[h].letter)):
            partner[a], partner[b] = b, a
            source[a] = source[b] = classify(ev_of(a, b))
    # 3. third poles taken out of position pairs
    third: dict[str, list[str]] = {}
    for (a, b), ev in sorted(evid.items(), key=lambda kv: -strength(kv[1])):
        if not (ev["adjacent"] and confirmed(ev, confirm)):
            continue
        for x, y in ((a, b), (b, a)):
            if x in third or y not in partner or partner.get(y) == x or source.get(y) == "position":
                continue
            if x not in partner or source.get(x) == "position":
                if x in partner:
                    freed = partner.pop(x)
                    partner.pop(freed, None)
                    source.pop(x, None)
                    source.pop(freed, None)
                third[x] = sorted({x, y, partner[y]}, key=index.position)
    out: dict[str, HeadPairing] = {}
    for h in scope:
        if h in partner:
            p = partner[h]
            out[h] = HeadPairing(head=h, partner=p, kind="pair", members=sorted([h, p], key=index.position),
                                 evidence=dict(ev_of(h, p) or {}, llm=None), source=source[h])
    # 4. lettered heads beside a pair, then the rest
    for ids in index.by_subsection.values():
        ids = [h for h in ids if h in scope_set]
        for i, h in enumerate(ids):
            if h in out:
                continue
            if h in third:
                others = [m for m in third[h] if m != h]
                out[h] = HeadPairing(head=h, partner=None, kind="triad", members=third[h],
                                     evidence={"adjacent": True, "pair": others,
                                               "strict_with": [m for m in others if ev_of(h, m) is not None
                                                               and confirmed(ev_of(h, m), confirm)],
                                               "llm": None},
                                     source="rule")
                continue
            neighbours = [ids[j] for j in (i - 1, i + 1) if 0 <= j < len(ids)]
            pair_nb = [nb for nb in neighbours if nb in partner]
            if index.heads[h].letter and pair_nb:
                nb = pair_nb[0]
                members = sorted({h, nb, partner[nb]}, key=index.position)
                out[h] = HeadPairing(head=h, partner=None, kind="triad", members=members,
                                     evidence={"adjacent": True, "pair": [nb, partner[nb]], "llm": None},
                                     source="rule")
                continue
            free = [nb for nb in neighbours if nb not in partner]
            ev = {nb: ev_of(h, nb) for nb in free if ev_of(h, nb) is not None}
            kind = "unresolved" if free else "singleton"
            out[h] = HeadPairing(head=h, partner=None, kind=kind, members=[h],
                                 evidence={"neighbours": ev, "llm": None}, source="unresolved" if free else "rule")
    return {h: out[h] for h in scope}


# --------------------------------------------------------------------------- the printed synopsis

def merge_synopsis(index: RogetIndex, rules: Mapping[str, HeadPairing], synopsis: Mapping[str, Mapping], *,
                   lex=None) -> dict[str, HeadPairing]:
    """The pairing with Roget's printed synopsis (:mod:`.synopsis`, ``synopsis_pairs.json``) as the
    strongest evidence (``source: "synopsis"``); every record keeps the rule result under
    ``evidence["rule"]`` for comparison.

    * A head the synopsis prints in a pair or a triad takes that pairing (a pair also carries the rules'
      word-level evidence for it, as a rule pair does).
    * A head the synopsis prints alone is a singleton, unless the rules paired it with a head the 1911
      synopsis does not print (a lettered head added later, such as 464a Incomparability): that rule pair
      is kept, with the synopsis record beside it.
    * A head the synopsis does not print keeps its rule result, except a pair whose partner the synopsis
      pairs elsewhere (then a singleton, ``partner_taken_by_synopsis``) and a third pole whose pair the
      merge broke (``triad_broken_by_synopsis``)."""
    def rule_summary(h):
        r = rules.get(h)
        return {"kind": r.kind, "partner": r.partner, "source": r.source} if r else None

    def syn_summary(h):
        s = synopsis[h]
        return {k: s[k] for k in ("kind", "partner", "members", "block", "how", "page", "row") if k in s}

    out: dict[str, HeadPairing] = {}
    for h in index.order:
        s = synopsis.get(h)
        if s is None or s["kind"] not in ("pair", "triad"):
            continue
        ev = {"synopsis": syn_summary(h), "rule": rule_summary(h)}
        if s["kind"] == "pair":
            ev = {**pair_evidence(index.heads[h], index.heads[s["partner"]], lex), "llm": None, **ev}
        out[h] = HeadPairing(head=h, partner=s["partner"], kind=s["kind"], members=list(s["members"]), evidence=ev,
                             source="synopsis")
    for h in index.order:
        s = synopsis.get(h)
        if s is None or s["kind"] != "singleton":
            continue
        r = rules.get(h)
        p = r.partner if r is not None and r.kind == "pair" else None
        if p and p not in synopsis and rules.get(p) is not None and rules[p].partner == h:
            out[h] = HeadPairing(head=h, partner=p, kind="pair", members=list(r.members),
                                 evidence={**r.evidence, "synopsis": syn_summary(h), "rule": rule_summary(h)},
                                 source=r.source)
        else:
            out[h] = HeadPairing(head=h, partner=None, kind="singleton", members=[h],
                                 evidence={"synopsis": syn_summary(h), "rule": rule_summary(h)}, source="synopsis")
    rest = [h for h in index.order if h not in out and h in rules]
    for h in rest:                                   # pairs and lone heads first, third poles after
        r = rules[h]
        if r.kind == "triad":
            continue
        if r.kind == "pair" and r.partner in synopsis and not (r.partner in out and out[r.partner].partner == h):
            out[h] = HeadPairing(head=h, partner=None, kind="singleton", members=[h],
                                 evidence={"rule": rule_summary(h), "partner_taken_by_synopsis": r.partner},
                                 source=r.source)
        else:
            out[h] = HeadPairing(head=h, partner=r.partner, kind=r.kind, members=list(r.members),
                                 evidence={**r.evidence, "synopsis": None}, source=r.source)
    for h in rest:
        r = rules[h]
        if r.kind != "triad":
            continue
        pair = [m for m in r.members if m != h]
        if len(pair) == 2 and all(m in out for m in pair) and out[pair[0]].partner == pair[1]:
            out[h] = HeadPairing(head=h, partner=None, kind="triad", members=list(r.members),
                                 evidence={**r.evidence, "synopsis": None}, source=r.source)
        else:
            out[h] = HeadPairing(head=h, partner=None, kind="singleton", members=[h],
                                 evidence={"rule": rule_summary(h), "triad_broken_by_synopsis": pair},
                                 source=r.source)
    return {h: out[h] for h in index.order if h in out}


def residue(index: RogetIndex, pairing: Mapping[str, HeadPairing]) -> list[tuple[str, list[str]]]:
    """``(subsection key, head ids still unresolved)`` in text order."""
    out = []
    for key, ids in index.by_subsection.items():
        left = [h for h in ids if h in pairing and pairing[h].kind == "unresolved"]
        if left:
            out.append((key, left))
    return out


# --------------------------------------------------------------------------- known pairs

def load_known_pairs(path: Path) -> list[dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d.get("pairs", d) if isinstance(d, dict) else d


def check_known_pairs(index: RogetIndex, pairing: Mapping[str, HeadPairing], known: Iterable[Mapping]) -> dict:
    """``{"checked", "hit", "miss", "wrong", "dropped"}``: a known pair whose titles do not match
    the parse is dropped (listed, not failed); a hit pairs the two as listed; a miss leaves one
    unpaired; a wrong pairs one of them elsewhere."""
    res = {"checked": 0, "hit": [], "miss": [], "wrong": [], "dropped": []}
    for k in known:
        a, b = str(k["a"]), str(k["b"])
        ta, tb = k.get("title_a"), k.get("title_b")
        if a not in index.heads or b not in index.heads or \
                (ta and index.heads[a].title.lower() != ta.lower()) or (tb and index.heads[b].title.lower() != tb.lower()):
            res["dropped"].append({"a": a, "b": b, "title_a": ta, "title_b": tb,
                                   "parsed": [index.heads[a].title if a in index.heads else None,
                                              index.heads[b].title if b in index.heads else None]})
            continue
        res["checked"] += 1
        pa = pairing.get(a)
        pb = pairing.get(b)
        if pa and pa.partner == b:
            res["hit"].append([a, b])
        elif (pa and pa.partner) or (pb and pb.partner):
            res["wrong"].append({"pair": [a, b], "a_partner": pa.partner if pa else None,
                                 "b_partner": pb.partner if pb else None})
        else:
            res["miss"].append({"pair": [a, b], "a_kind": pa.kind if pa else None, "b_kind": pb.kind if pb else None})
    res["recall"] = round(len(res["hit"]) / res["checked"], 4) if res["checked"] else None
    return res


def threshold_sweep(index: RogetIndex, lex, known: Sequence[Mapping], *, heads=None,
                    grid: Sequence[tuple[int, float, int]] = ((1, 0.0, 1), (2, 0.05, 2), (2, 0.08, 2), (3, 0.08, 2),
                                                              (2, 0.08, 3), (3, 0.1, 3))) -> list[dict]:
    """Known-pairs recall and wrong count for each ``(n_min, frac_min, wn_min)`` (strict pass only
    and with the weak pass)."""
    out = []
    for n_min, frac_min, wn_min in grid:
        conf = dict(n_min=n_min, frac_min=frac_min, wn_min=wn_min)
        for wp in (False, True):
            p = rule_pairs(index, lex, heads=heads, confirm=conf, weak_pass=wp, position_pass=False)
            r = check_known_pairs(index, p, known)
            out.append({"confirm": conf, "weak_pass": wp, "recall": r["recall"], "hit": len(r["hit"]),
                        "wrong": len(r["wrong"]), "miss": len(r["miss"]), "checked": r["checked"],
                        "n_pairs": sum(1 for x in p.values() if x.kind == "pair") // 2,
                        "n_unresolved": sum(1 for x in p.values() if x.kind == "unresolved")})
    return out


# --------------------------------------------------------------------------- persistence

def save_pairs(pairing: Mapping[str, HeadPairing], path: Path, *, inputs: Sequence = (), meta: Optional[dict] = None) -> Path:
    from assistant_axis.plot_metadata import json_metadata

    payload = {"rules_version": PAIRING_RULES_VERSION, "confirm": dict(CONFIRM), **(meta or {}),
               "pairs": {h: p.to_json() for h, p in pairing.items()}}
    title = ("Roget opposed heads (printed synopsis, then rules; workstream 2)" if (meta or {}).get("synopsis")
             else "Roget opposed heads (rules, workstream 2)")
    env = json_metadata(payload, inputs=list(inputs), title=title)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    from .parse import dumps_one_per_line
    atomic_write_text(dumps_one_per_line(env, "pairs"), path)
    return path


def load_pairs(path: Path) -> dict[str, HeadPairing]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d)
    pairs = d.get("pairs", d)
    return {h: HeadPairing(head=h, **v) for h, v in pairs.items()}


def partner_of(pairing: Mapping[str, HeadPairing], hid: str) -> Optional[str]:
    p = pairing.get(hid)
    return p.partner if p else None
