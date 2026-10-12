"""The harvest: candidate words from the gap heads of the coverage map (plan § 5, ``roget_harvest.py``).

For each head in the selected gap classes (:data:`coverage.HARVEST_CLASSES` by default), one word
per semicolon group of its adjectives (:func:`harvest_head`): items over ``max_words`` words, items
ending in a function word ("shy of"), proper adjectives WordNet does not know in lower case, words
already in the corpus or the seed queue, and words the platform's Zipf floor rejects
(``freq.zipf_info``, ``hard_reject``) are dropped and counted; the representative of a group is its
most frequent word; a head gives at most ``per_head_cap`` words, best score first
(``score = zipf + 0.3 if WordNet has it as an adjective - 0.15 x group index``).

The Zipf floor defers to rule 1b (Roger, 2026-10-12, gate audit 2 of
``reports/code_review_2026-10-12/gate_audits/roget_wordnet_selection.md``; :data:`ZIPF_FLOOR_RULE`): a word
below Zipf 1.5 that the negating-prefix rescue or the gloss-hint rescue sends to M1's probe is kept, and only
``hard_reject`` drops.  Every harvested word carries a gloss hint (:func:`gloss_hint`), so the gloss-hint route
applies to every word, as it does in M1 (``filter.py`` passes ``gloss_hint`` for a row with an intended sense).
Before that date a second check (``zipf_min < zipf_hard``, review 5 D4) dropped every word below the line,
rescued or not; those runs record ``zipf_hard`` in their config and a single ``zipf_hard`` drop count.  Now
the drops record ``zipf_hard_reject``, and ``harvest_counts.json`` has a ``zipf_floor`` block: the words below
the line, the ones dropped, the ones rescued by each route (what the second check used to drop), and the
rescued words that became candidates, with the same counts for the heads skipped as not character.

Each word becomes one :class:`~assistant_axis.gapgen.Candidate` per head it came from
(``source_ref = "roget:<head id>"``; the registry merges a word harvested from two heads into one
row with two sources, interface resolution 4), with a ``gloss_hint`` built from the head
(:func:`gloss_hint`) and, where the opposed head gives one, a ``partner_hint``: a word of the
opposed head (or, for a pair completion, the trait that covers it) that WordNet lists as an
antonym or that is a negation form of the word (:func:`pair_candidates`; the rank-matched pairs
it adds up to ``pair_top`` per head pair are recorded in ``pair_candidates.jsonl`` without a hint).
Hints come from pairs the printed synopsis or the rules give (:data:`HINT_SOURCES`), not from a pair by
position alone.

With ``head_scope`` (the head-scope ratings, :mod:`.head_scope`; QUESTIONS 44) a selected head rated 0
(few or none of its adjectives describe a person's character) is skipped: the words it would have given
are counted under the drop reason ``not_character``, and the head under ``n_heads_not_character``.  The
rating of every selected head is recorded in ``harvest_counts.json`` (``head_ratings``), in
``harvest_report.md`` and on each :class:`HarvestItem` (``character``), never in the Candidates.  Without
it the harvest is as before.

``--every-nth K`` (the pilot) keeps every K-th gap head in text order together with its opposed
head when that head is also a gap head.  The run directory gets ``candidates.jsonl`` (exactly
``dataclasses.asdict`` of every Candidate, one per line: the tracked file another checkout
resubmits with ``gap_registry.py submit``), ``pair_candidates.jsonl`` and ``harvest_report.md``.

With ``already_submitted`` (``roget_generate.py harvest --delta-from R``) the run keeps only the candidates an
earlier run did not submit, keyed by (stem, ``source_ref``): a rule change then reaches the registry as a run
of its own, without adding a second source to every row the earlier run made.  The drop counts and the
``zipf_floor`` block describe the whole harvest; the words, the candidates and the ``delta`` block the rest.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Collection, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.freq import HARD_REJECT_BELOW, zipf_info
from assistant_axis.gapgen.normalize import STOPWORDS
from assistant_axis.gapgen.registry import Candidate

from .coverage import HARVEST_CLASSES, CoverageReport
from .pairs import HeadPairing, _negates, _norm
from .parse import Head, RogetIndex
from .wn_clusters import WN_CLOSURE_DEPTH

GENERATOR = "roget"
WN_GENERATOR = "wn_clusters"
#: How the generator-side Zipf floor works, recorded in every run's config (module docstring): ``rule_1b``,
#: only ``freq.zipf_info``'s ``hard_reject`` drops, its rescue routes keep the word for M1's probe.  A run
#: recorded with ``zipf_hard`` instead (before 2026-10-12) dropped every word below that line.
ZIPF_FLOOR_RULE = "rule_1b"
#: Pair sources whose word-level opposites become partner hints: Roget's printed synopsis and the rules.
HINT_SOURCES = ("synopsis", "rule", "rule_weak")
#: Platform rates for the downstream estimate (coding_plan_02 revision item 4): M1 per word, M3
#: per word that passes M1.
M1_USD_PER_WORD = 0.004
M3_USD_PER_PASSING_WORD = 0.018
GLOSS_MIN_WORDS, GLOSS_MAX_WORDS = 18, 43


@dataclass
class HarvestConfig:
    per_head_cap: int = 10
    pair_top: int = 3
    max_words: int = 2
    classes: tuple = HARVEST_CLASSES
    every_nth: Optional[int] = None
    offset: int = 0
    zipf_floor: str = ZIPF_FLOOR_RULE
    include_wn: bool = False
    wn_closure_depth: int = WN_CLOSURE_DEPTH

    def to_json(self) -> dict:
        d = asdict(self)
        d["classes"] = list(self.classes)
        return d


@dataclass
class HarvestItem:
    surface: str
    head_id: str
    partner_id: Optional[str]
    group_index: int
    siblings: list
    zipf_min: float
    probe_band: bool
    wn_found: bool
    n_senses: int
    score: float
    class_vi: bool
    gap_class: str = ""
    gloss_hint: str = ""
    character: Optional[int] = None     # the head-scope rating of the head (1 or 2), None if unrated
    rescue: Optional[str] = None        # below Zipf 1.5, kept by rule 1b: negating_prefix | gloss_hint


@dataclass
class PairCandidate:
    a: str
    b: str
    head_a: str
    head_b: str
    double_confirmed: bool
    morph: bool = False
    partner_existing: list = field(default_factory=list)
    pair_source: str = "rule"
    gap_class: str = ""


@dataclass
class HarvestResult:
    items: list
    pairs: list
    candidates: list
    counts: dict
    config: dict
    selected_heads: list
    wn_items: list = field(default_factory=list)
    wn_candidates: list = field(default_factory=list)
    head_gap_class: dict = field(default_factory=dict)    # selected head -> its gap class


# --------------------------------------------------------------------------- label hygiene

class LabelGuard:
    """``contains(text)``: does the text use any corpus or queue label (a word equal to a one-word
    stem, a hyphenated word or one of its parts equal to one, or a multiword label as a phrase)?"""

    def __init__(self, known_stems: Collection[str]):
        self.single = {s for s in known_stems if "_" not in s}
        self.phrases = [s.replace("_", " ") for s in known_stems if "_" in s]

    def contains(self, text: str) -> bool:
        low = text.lower()
        for tok in re.findall(r"[a-z]+(?:[-'][a-z]+)*", low):
            if normalize_to_file_name(tok) in self.single or tok in self.single:
                return True
            if "-" in tok and any(p in self.single for p in tok.split("-")):
                return True
        norm = " " + re.sub(r"[^a-z]+", " ", low) + " "
        return any(f" {p} " in norm for p in self.phrases)


# --------------------------------------------------------------------------- one head

def harvest_head(head: Head, *, known_stems: Collection[str], cfg: HarvestConfig, lex=None,
                 zipf: Optional[Callable[[str], float]] = None, partner_id: Optional[str] = None,
                 gap: str = "", gloss_hint: bool = True,
                 zipf_stats: Optional[Counter] = None) -> tuple[list[HarvestItem], Counter]:
    """Representatives of the head's adjective groups (module docstring); ``(items, drop counts)``.

    ``gloss_hint``: the words will be submitted with a gloss hint, as :func:`harvest` submits every word, so
    rule 1b's gloss-hint route keeps a word below the Zipf floor; ``False`` for a caller that submits words
    without one, where only the negating-prefix route rescues and ``hard_reject`` drops the rest.
    ``zipf_stats``, when given, is updated with ``below_line`` (words under the floor that reached the
    check), ``hard_reject`` (dropped) and ``rescued_<route>`` (kept by that route)."""
    known = set(known_stems)
    zs = zipf_stats if zipf_stats is not None else Counter()
    drops: Counter = Counter()
    reps: list[HarvestItem] = []
    seen: set[str] = set()
    all_clean: list[str] = []
    for gi, group in enumerate(head.pos.get("Adj", [])):
        cands = []
        for raw in group:
            item = raw.strip()
            words = item.split()
            if len(words) > cfg.max_words:
                drops["too_many_words"] += 1
                continue
            if words[-1].lower() in STOPWORDS or words[0].lower() in STOPWORDS:
                drops["function_word"] += 1
                continue
            if item[:1].isupper():
                low = item.lower()
                if lex is not None and lex.is_adjective(low):
                    item = low
                else:
                    drops["proper"] += 1
                    continue
            stem = normalize_to_file_name(item)
            if not stem:
                drops["empty"] += 1
                continue
            if stem in known:
                drops["known_label"] += 1
                continue
            if stem in seen:
                drops["repeat"] += 1
                continue
            # rule 1b (Roger, 2026-10-12): only hard_reject drops; the rescue routes send the word to M1's probe
            fi = zipf_info(item, zipf_fn=zipf, gloss_hint=gloss_hint)
            if fi.zipf_min < HARD_REJECT_BELOW:
                zs["below_line"] += 1
            if fi.hard_reject:
                zs["hard_reject"] += 1
                drops["zipf_hard_reject"] += 1
                continue
            if fi.rescue:
                zs[f"rescued_{fi.rescue}"] += 1
            syns = lex.adj_synsets(item) if lex is not None else []
            cands.append((fi.zipf_min, -len(cands), item, stem, fi.probe_band, bool(syns), len(syns), fi.rescue))
            all_clean.append(item)
        if not cands:
            continue
        cands.sort(reverse=True)
        z, _, item, stem, probe, wn_found, n_senses, rescue = cands[0]
        drops["not_representative"] += len(cands) - 1
        seen.add(stem)
        score = round(z + (0.3 if wn_found else 0.0) - 0.15 * gi, 3)
        reps.append(HarvestItem(surface=item, head_id=head.id, partner_id=partner_id, group_index=gi, siblings=[],
                                zipf_min=z, probe_band=probe, wn_found=wn_found, n_senses=n_senses, score=score,
                                class_vi=head.klass == "VI", gap_class=gap, rescue=rescue))
    reps.sort(key=lambda it: (-it.score, it.group_index, it.surface))
    if len(reps) > cfg.per_head_cap:
        drops["cap"] += len(reps) - cfg.per_head_cap
        reps = reps[: cfg.per_head_cap]
    for it in reps:
        it.siblings = [s for s in all_clean if s != it.surface]
    return reps, drops


# --------------------------------------------------------------------------- gloss hints

def _join(words: Sequence[str]) -> str:
    words = list(words)
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


def uses_word(text: str, word: str) -> bool:
    """``text`` contains ``word`` as a word or as a part of a hyphenated word ("scot-free" uses "free",
    "freedom" and "carefree" do not)."""
    w = word.strip().lower()
    return bool(w) and re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", text.lower()) is not None


def _sense_word(head: Head, guard: Optional[LabelGuard], *, exclude: Collection[str] = ()) -> Optional[str]:
    """The head's title in lower case (``Seclusion. Exclusion`` -> ``seclusion or exclusion``), or
    its first noun when the title is excluded (it uses the candidate's own word, :func:`uses_word`, or a label
    when a guard is given)."""
    def banned(w: str) -> bool:
        return any(uses_word(w, e) for e in exclude) or (guard is not None and guard.contains(w))
    t = re.sub(r"\.\s+", " or ", head.title.strip()).strip(" .").lower()
    if t and not banned(t):
        return t
    for n in head.items("N"):
        if " " not in n and not banned(n):
            return n.lower()
    return None


#: Class VI sections whose heads are feelings (affections in general, personal and sympathetic
#: affections); the moral and religious sections (IV, V) are dispositions like Classes IV-V.
FEELING_SECTIONS = ("I", "II", "III")


def is_feeling_head(head: Head) -> bool:
    return head.klass == "VI" and head.section.split(".", 1)[0].strip() in FEELING_SECTIONS


def gloss_hint(item: HarvestItem, head: Head, partner_head: Optional[Head], *,
               guard: Optional[LabelGuard] = None) -> str:
    """The intended sense, 18-43 words, never using the word itself (and, only when a ``guard`` is
    given, no corpus or queue label either; the harvest passes none, Roger 2026-10-08, QUESTIONS 41):

    "This means a disposition toward resolution (volition in general), of a piece with unflinching,
    determined and indomitable, shown in determination, backbone and grit; the opposite pole is
    irresolution."  The feeling heads of Class VI (:func:`is_feeling_head`) read "a general tendency
    to feel <sense> and act from it" (an emotional state taken as an inclination, plan § 1).  A head
    too sparse for 18 words gives a shorter hint."""
    me = item.surface.lower()
    sense = _sense_word(head, guard, exclude={me}) or "this temper"
    if is_feeling_head(head):
        core = f"This means a general tendency to feel {sense} and act from it"
    else:
        core = f"This means a disposition toward {sense}"
    where = (head.section.split(". ", 1)[-1] if head.section else "").lower()
    where_clause = (f" ({where})" if where and not uses_word(where, me)
                    and not (guard is not None and guard.contains(where)) else "")

    # the word itself is kept out of every part, inside a hyphenated sibling too ("scot-free" for "free",
    # review 2026-10-12; QUESTIONS 41: the hint never uses the candidate's own word)
    def ok(w: str) -> bool:
        return (w.islower() and not uses_word(w, me) and w != sense and w.split()[-1] not in STOPWORDS
                and not (guard is not None and guard.contains(w)))

    # one-word siblings and nouns first; multiword ones only to reach the minimum length
    sibs = [s for s in item.siblings if len(s.split()) == 1 and ok(s.lower())]
    sibs += [s for s in item.siblings if len(s.split()) == 2 and ok(s.lower())]
    sibs = list(dict.fromkeys(sibs))[:6]
    nouns = [n for n in head.items("N") if len(n.split()) == 1 and len(n) >= 4 and ok(n)]
    nouns += [n for n in head.items("N") if 2 <= len(n.split()) <= 3 and ok(n)]
    nouns = list(dict.fromkeys(nouns))[:8]
    opposite = None
    if partner_head is not None:
        opposite = _sense_word(partner_head, guard, exclude={me})

    def build(n_sib: int, n_noun: int) -> str:
        s = core + where_clause
        if n_sib:
            s += f", of a piece with {_join(sibs[:n_sib])}"
        if n_noun:
            s += f", shown in {_join(nouns[:n_noun])}"
        if opposite:
            s += f"; the opposite pole is {opposite}"
        return s + "."

    n_sib, n_noun = min(3, len(sibs)), min(3, len(nouns))
    text = build(n_sib, n_noun)
    while len(text.split()) < GLOSS_MIN_WORDS and (n_noun < len(nouns) or n_sib < len(sibs)):
        if n_noun < len(nouns):
            n_noun += 1
        else:
            n_sib += 1
        text = build(n_sib, n_noun)
    while len(text.split()) > GLOSS_MAX_WORDS and (n_noun or n_sib):
        if n_noun:
            n_noun -= 1
        else:
            n_sib -= 1
        text = build(n_sib, n_noun)
    return text


# --------------------------------------------------------------------------- pairs

def pair_candidates(items_a: Sequence[HarvestItem], items_b: Sequence[HarvestItem], lex=None, *,
                    existing_b: Sequence[str] = (), existing_b_labels: Optional[Mapping[str, str]] = None,
                    top: int = 3, pair_source: str = "rule", gap_class: str = "") -> list[PairCandidate]:
    """Word pairs across two opposed heads.  A WordNet antonym (``double_confirmed``: the heads are
    opposed and WordNet opposes the words) or a negation form (``morph``) first, then the best
    remaining words of each side in score order, up to ``top`` pairs.  With ``existing_b`` (the
    opposed head is covered: a pair completion), the ``b`` side is the covering trait."""
    out: list[PairCandidate] = []
    used_a: set[str] = set()
    used_b: set[str] = set()
    labels = dict(existing_b_labels or {})
    if existing_b:
        b_words = {labels.get(s, s.replace("_", " ")).lower(): s for s in existing_b}
        for it in items_a:
            ants = {a.lower() for a, _ in lex.antonyms(it.surface)} if lex is not None else set()
            hit = next((w for w in b_words if w in ants), None)
            if hit is not None:
                out.append(PairCandidate(it.surface, labels.get(b_words[hit], hit), it.head_id, "", True, False,
                                         list(existing_b), pair_source, gap_class))
                used_a.add(it.surface)
        for it in items_a:
            if len(out) >= top:
                break
            if it.surface in used_a:
                continue
            first = existing_b[0]
            out.append(PairCandidate(it.surface, labels.get(first, first.replace("_", " ")), it.head_id, "", False,
                                     False, list(existing_b), pair_source, gap_class))
            used_a.add(it.surface)
        return out
    b_by = {it.surface.lower(): it for it in items_b}
    for it in items_a:
        ants = {a.lower() for a, _ in lex.antonyms(it.surface)} if lex is not None else set()
        for w, jt in b_by.items():
            if jt.surface in used_b or it.surface in used_a:
                continue
            wn_hit = w in ants
            morph = _negates(_norm(it.surface), _norm(w)) or _negates(_norm(w), _norm(it.surface))
            if wn_hit or morph:
                out.append(PairCandidate(it.surface, jt.surface, it.head_id, jt.head_id, wn_hit, morph, [],
                                         pair_source, gap_class))
                used_a.add(it.surface)
                used_b.add(jt.surface)
    rest_a = [it for it in items_a if it.surface not in used_a]
    rest_b = [it for it in items_b if it.surface not in used_b]
    for x, y in zip(rest_a, rest_b):
        if len(out) >= top:
            break
        out.append(PairCandidate(x.surface, y.surface, x.head_id, y.head_id, False, False, [], pair_source, gap_class))
    return out


# --------------------------------------------------------------------------- selection and the run

def gap_heads(report: CoverageReport, cfg: HarvestConfig) -> list[str]:
    return [r.id for r in report.rows if r.gap_class in cfg.classes]


def select_heads(report: CoverageReport, cfg: HarvestConfig) -> list[str]:
    """The gap heads to harvest: all, or every ``every_nth``-th from ``offset`` in text order with
    its opposed head when that is a gap head too (kept in text order)."""
    gaps = gap_heads(report, cfg)
    if not cfg.every_nth:
        return gaps
    rows = report.by_id()
    gset = set(gaps)
    keep = {h for i, h in enumerate(gaps) if i % cfg.every_nth == cfg.offset % cfg.every_nth}
    for h in list(keep):
        p = rows[h].partner
        if p and p in gset:
            keep.add(p)
    return [h for h in gaps if h in keep]


def to_candidates(items: Sequence[HarvestItem], *, generator: str, run_id: str,
                  partner_hints: Optional[Mapping[tuple[str, str], str]] = None) -> list[Candidate]:
    """One Candidate per (word, head), ranked by score (then head order as given, then word)."""
    hints = dict(partner_hints or {})
    order = sorted(range(len(items)), key=lambda i: (-items[i].score, i))
    out = []
    for rank, i in enumerate(order, 1):
        it = items[i]
        out.append(Candidate(surface=it.surface, generator=generator, run_id=run_id, rank=rank, score=it.score,
                             gloss_hint=it.gloss_hint or None, sense_id=1, source_ref=f"roget:{it.head_id}",
                             partner_hint=hints.get((it.surface, it.head_id))))
    return out


def harvest(report: CoverageReport, index: RogetIndex, pairs: Mapping[str, HeadPairing], *, cfg: HarvestConfig,
            known_stems: Collection[str], run_id: str, lex=None, zipf: Optional[Callable[[str], float]] = None,
            label_of: Optional[Mapping[str, str]] = None,
            head_scope: Optional[Mapping[str, Optional[int]]] = None,
            already_submitted: Optional[Collection[tuple[str, str]]] = None,
            delta_from: Optional[str] = None) -> HarvestResult:
    """Harvest the selected gap heads; build the gloss hints, the pair candidates and the Candidates.
    ``head_scope`` (head id -> 0, 1, 2 or None): heads rated 0 are skipped and counted.
    ``already_submitted``: ``(stem, source_ref)`` keys an earlier run (``delta_from``) submitted; those
    candidates are left out (module docstring)."""
    rows = report.by_id()
    selected = select_heads(report, cfg)
    by_head: dict[str, list[HarvestItem]] = {}
    drops: Counter = Counter()
    zstats: Counter = Counter()
    zstats_skipped: Counter = Counter()
    not_character: list[str] = []
    ratings = dict(head_scope or {})
    for h in selected:
        r = rows[h]
        skip = ratings.get(h) == 0
        # every word gets a gloss hint below, so rule 1b's gloss-hint route applies (Roger, 2026-10-12)
        items, d = harvest_head(index.heads[h], known_stems=known_stems, cfg=cfg, lex=lex, zipf=zipf,
                                partner_id=r.partner, gap=r.gap_class, gloss_hint=True,
                                zipf_stats=zstats_skipped if skip else zstats)
        if skip:
            # not character: the words it would have given are dropped and counted, its other drops are not
            not_character.append(h)
            if items:
                drops["not_character"] += len(items)
            continue
        for it in items:
            it.character = ratings.get(h)
        drops.update(d)
        partner_head = index.heads[r.partner] if r.partner and r.partner in index.heads else None
        for it in items:
            it.gloss_hint = gloss_hint(it, index.heads[h], partner_head)   # no label guard (QUESTIONS 41)
        by_head[h] = items
    # pair candidates and partner hints (evidence-backed pairs only)
    pc: list[PairCandidate] = []
    done: set[frozenset] = set()
    for h in selected:
        r = rows[h]
        if h not in by_head or not r.partner or r.pair_kind != "pair" or frozenset((h, r.partner)) in done:
            continue
        done.add(frozenset((h, r.partner)))
        src = r.pair_source
        if r.partner in by_head:
            got = pair_candidates(by_head[h], by_head[r.partner], lex, top=cfg.pair_top, pair_source=src,
                                  gap_class=r.gap_class)
        elif r.partner_existing:
            got = pair_candidates(by_head[h], [], lex, existing_b=r.partner_existing, existing_b_labels=label_of,
                                  top=cfg.pair_top, pair_source=src, gap_class=r.gap_class)
            for p in got:
                p.head_b = r.partner
        else:
            got = []
        pc.extend(got)
    hints: dict[tuple[str, str], str] = {}
    for p in pc:
        # a partner hint names a word-level opposite: a WordNet antonym or a negation form across
        # two heads Roget's synopsis or the rules paired (rank-matched pairs stay in pair_candidates.jsonl
        # only; a pair by position alone gives none)
        if p.pair_source not in HINT_SOURCES or not (p.double_confirmed or p.morph):
            continue
        hints.setdefault((p.a, p.head_a), p.b)
        if not p.partner_existing:
            hints.setdefault((p.b, p.head_b), p.a)
    items = [it for h in selected for it in by_head.get(h, [])]
    zipf_block = zipf_floor_counts(zstats, zstats_skipped, items)
    delta = None
    if already_submitted is not None:
        prev = set(already_submitted)
        new_items = [it for it in items if (normalize_to_file_name(it.surface), f"roget:{it.head_id}") not in prev]
        new_ids = {id(it) for it in new_items}
        new_words = {it.surface for it in new_items}
        delta = {"from": delta_from, "n_harvested": len(items), "n_already_submitted": len(items) - len(new_items),
                 "n_new": len(new_items),
                 "new_below_line": sorted({it.surface for it in new_items if it.rescue}),
                 "new_other": sorted({it.surface for it in new_items if not it.rescue})}
        by_head = {h: [it for it in its if id(it) in new_ids] for h, its in by_head.items()}
        items = new_items
        pc = [p for p in pc if p.a in new_words or p.b in new_words]
    cands = to_candidates(items, generator=GENERATOR, run_id=run_id, partner_hints=hints)
    counts = harvest_counts(report, selected, by_head, drops, pc, cands, cfg)
    counts["zipf_floor"] = zipf_block
    counts["delta"] = delta
    counts["n_heads_not_character"] = len(not_character)
    counts["heads_not_character"] = not_character
    counts["head_ratings"] = {h: ratings.get(h) for h in selected} if head_scope is not None else {}
    counts["items_by_character"] = (dict(Counter(str(it.character) for it in items)) if head_scope is not None
                                    else {})
    return HarvestResult(items=items, pairs=pc, candidates=cands, counts=counts, config=cfg.to_json(),
                         selected_heads=selected, head_gap_class={h: rows[h].gap_class for h in selected})


def harvest_counts(report: CoverageReport, selected: Sequence[str], by_head: Mapping[str, list], drops: Counter,
                   pc: Sequence[PairCandidate], cands: Sequence[Candidate], cfg: HarvestConfig) -> dict:
    rows = report.by_id()
    items = [it for h in selected for it in by_head.get(h, [])]
    n_gap = len(gap_heads(report, cfg))
    by_class = Counter(rows[h].gap_class for h in selected)
    items_by_class = Counter(it.gap_class for it in items)
    n = len(items)
    return {
        "n_gap_heads": n_gap, "n_heads_selected": len(selected),
        "n_heads_harvested": sum(1 for h in selected if by_head.get(h)),
        "heads_by_gap_class": dict(by_class), "items_by_gap_class": dict(items_by_class),
        "n_items": n, "n_unique_words": len({normalize_to_file_name(it.surface) for it in items}),
        "n_candidates": len(cands), "drops": dict(drops.most_common()),
        "probe_band_frac": round(sum(it.probe_band for it in items) / n, 3) if n else 0.0,
        "class_vi_frac": round(sum(it.class_vi for it in items) / n, 3) if n else 0.0,
        "wn_found_frac": round(sum(it.wn_found for it in items) / n, 3) if n else 0.0,
        "n_pair_candidates": len(pc), "n_double_confirmed": sum(p.double_confirmed for p in pc),
        "n_morph": sum(p.morph for p in pc),
        "n_partner_hints": sum(1 for c in cands if c.partner_hint),
        "per_head": {h: len(by_head.get(h, [])) for h in selected},
        "downstream_estimate_usd": {"m1": round(n * M1_USD_PER_WORD, 2),
                                    "m3_if_half_pass": round(n * 0.5 * M3_USD_PER_PASSING_WORD, 2)},
    }


def _zipf_part(stats: Counter) -> dict:
    rescued = {k[len("rescued_"):]: v for k, v in sorted(stats.items()) if k.startswith("rescued_")}
    return {"below_line": stats.get("below_line", 0), "hard_reject": stats.get("hard_reject", 0),
            "rescued": rescued, "rescued_total": sum(rescued.values())}


def zipf_floor_counts(stats: Counter, skipped: Counter, items: Sequence[HarvestItem]) -> dict:
    """The ``zipf_floor`` block of ``harvest_counts.json`` (gate audit 2, proposal 3).

    ``below_line``: words under Zipf 1.5 that reached the check (after the length, function-word, proper-name
    and known-label checks); ``hard_reject``: those dropped (no rescue route); ``rescued``: those kept by each
    route, which the second check dropped before 2026-10-12 (``rescued_total``); ``submitted``: the rescued
    words that became candidates (their group's most frequent clean word, within the cap), the words the
    rule change adds; ``in_skipped_heads``: the same counts for the heads rated not character (none of their
    words is submitted)."""
    sub = [it for it in items if it.rescue]
    return {"rule": ZIPF_FLOOR_RULE, "line": HARD_REJECT_BELOW, **_zipf_part(stats),
            "submitted": len(sub), "submitted_by_rescue": dict(Counter(it.rescue for it in sub)),
            "submitted_words": sorted({it.surface for it in sub}),
            "in_skipped_heads": _zipf_part(skipped)}


def would_be_words(index: RogetIndex, head_ids: Iterable[str], *, known_stems: Collection[str],
                   cfg: Optional[HarvestConfig] = None, lex=None,
                   zipf: Optional[Callable[[str], float]] = None) -> dict[str, list[str]]:
    """``{head id: words}``: what :func:`harvest_head` gives each head under the harvest's per-head rules (one
    word per semicolon group, the cap), whatever the head's gap class or head-scope rating.  The "would-be
    words" of gate audit 2 § 4, behind the coverage report's word-level column."""
    cfg = cfg or HarvestConfig()
    out: dict[str, list[str]] = {}
    for h in head_ids:
        if h in index.heads:
            items, _ = harvest_head(index.heads[h], known_stems=known_stems, cfg=cfg, lex=lex, zipf=zipf)
            out[h] = [it.surface for it in items]
    return out


# --------------------------------------------------------------------------- the WordNet stream

def wn_candidates(items: Sequence, *, run_id: str, every_nth: Optional[int] = None, offset: int = 0) -> list[Candidate]:
    """Candidates of the ``wn_clusters`` stream (one per word), every ``every_nth``-th of the list
    (sorted by route, then score) when given."""
    items = sorted(items, key=lambda it: (it.route, -it.score, it.surface))
    if every_nth:
        items = [it for i, it in enumerate(items) if i % every_nth == offset % every_nth]
    return [Candidate(surface=it.surface, generator=WN_GENERATOR, run_id=run_id, rank=i, score=it.score,
                      gloss_hint=it.gloss_hint or None, sense_id=1, source_ref=f"oewn:{it.synset_id}",
                      partner_hint=it.partner_hint)
            for i, it in enumerate(items, 1)]


# --------------------------------------------------------------------------- writing

def candidate_lines(cands: Iterable[Candidate]) -> str:
    """``candidates.jsonl``: ``json.dumps(dataclasses.asdict(c), ensure_ascii=False)`` per line, the
    form ``RunContext.record_candidates`` keeps, so a later submit leaves the file unchanged."""
    return "".join(json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in cands)


def write_candidates(cands: Sequence[Candidate], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(candidate_lines(cands), path)
    return path


def read_candidates(path: Path) -> list[Candidate]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Candidate(**json.loads(line)))
    return out


def report_markdown(result: HarvestResult, index: RogetIndex, *, run_id: str, title: str = "Roget harvest") -> str:
    c = result.counts
    L = [f"# {title}: run {run_id}", "",
         f"Config: `{json.dumps(result.config)}`.", "",
         f"- Gap heads: {c['n_gap_heads']}; selected {c['n_heads_selected']}; harvested (one word or more) "
         f"{c['n_heads_harvested']}.",
         f"- Words: {c['n_items']} ({c['n_unique_words']} distinct), candidates {c['n_candidates']}; by gap class "
         f"{json.dumps(c['items_by_gap_class'])}.",
         f"- Dropped: {json.dumps(c['drops'])}."]
    zf = c.get("zipf_floor")
    if zf:
        sk = zf["in_skipped_heads"]
        L.append(f"- Zipf floor ({zf['rule']}: only `hard_reject` drops; the negating-prefix and gloss-hint rescues "
                 f"go to M1's probe): {zf['below_line']} words below {zf['line']}, {zf['hard_reject']} dropped, "
                 f"{zf['rescued_total']} rescued {json.dumps(zf['rescued'])} (dropped by the second check before "
                 f"2026-10-12); {zf['submitted']} of them candidates"
                 + (f" ({', '.join(zf['submitted_words'])})" if zf["submitted_words"] else "")
                 + f".  In the heads skipped as not character: {sk['below_line']} below the line, "
                   f"{sk['hard_reject']} dropped, {sk['rescued_total']} rescued.")
    dl = c.get("delta")
    if dl:
        L.append(f"- Delta against run {dl['from']}: {dl['n_harvested']} words harvested, {dl['n_already_submitted']} "
                 f"already submitted there and left out, {dl['n_new']} new (below the Zipf line: "
                 f"{', '.join(dl['new_below_line']) or '-'}; other: {', '.join(dl['new_other']) or '-'}).")
    L += [f"- Zipf probe band {c['probe_band_frac']:.0%}; Class VI {c['class_vi_frac']:.0%}; WordNet adjective "
          f"{c['wn_found_frac']:.0%}.",
          f"- Pair candidates {c['n_pair_candidates']} (WordNet-confirmed {c['n_double_confirmed']}, negation forms "
          f"{c['n_morph']}); candidates with a partner hint {c['n_partner_hints']}.",
          f"- Downstream estimate: M1 about ${c['downstream_estimate_usd']['m1']:.2f}; M3 about "
          f"${c['downstream_estimate_usd']['m3_if_half_pass']:.2f} if half the words pass M1."]
    ratings = c.get("head_ratings") or {}
    if ratings:
        L.append(f"- Head scope ({c.get('head_scope', {}).get('path', 'head-scope ratings')}): "
                 f"{c.get('n_heads_not_character', 0)} selected heads rated 0 (not character) skipped, "
                 f"{c['drops'].get('not_character', 0)} words with them; words by the rating of their head "
                 f"{json.dumps(c.get('items_by_character', {}))}.")
    L += ["", "| head | gap class | character | words |", "|---|---|---|---|"]
    by_head: dict[str, list] = {}
    for it in result.items:
        by_head.setdefault(it.head_id, []).append(it.surface)
    skipped = set(c.get("heads_not_character") or [])
    for h in result.selected_heads:
        gc = result.head_gap_class.get(h) or next((it.gap_class for it in result.items if it.head_id == h), "")
        rt = ratings.get(h)
        words = "skipped (not character)" if h in skipped else (", ".join(by_head.get(h, [])) or "-")
        L.append(f"| {h} {index.heads[h].title} | {gc or '-'} | {'-' if rt is None else rt} | {words} |")
    L.append("")
    return "\n".join(L)


def write_harvest(result: HarvestResult, run_dir: Path, index: RogetIndex, *, run_id: str) -> dict[str, Path]:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    out = {"candidates": write_candidates(result.candidates, run_dir / "candidates.jsonl")}
    pc = run_dir / "pair_candidates.jsonl"
    atomic_write_text("".join(json.dumps(asdict(p), ensure_ascii=False) + "\n" for p in result.pairs), pc)
    out["pair_candidates"] = pc
    rep = run_dir / "harvest_report.md"
    atomic_write_text(report_markdown(result, index, run_id=run_id), rep)
    out["report"] = rep
    hc = run_dir / "harvest_counts.json"
    atomic_write_text(json.dumps({"config": result.config, "counts": result.counts,
                                  "selected_heads": result.selected_heads}, indent=1) + "\n", hc)
    out["counts"] = hc
    return out
