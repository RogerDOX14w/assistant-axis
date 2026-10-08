"""The harvest: candidate words from the gap heads of the coverage map (plan § 5, ``roget_harvest.py``).

For each head in the selected gap classes (:data:`coverage.HARVEST_CLASSES` by default), one word
per semicolon group of its adjectives (:func:`harvest_head`): items over ``max_words`` words, items
ending in a function word ("shy of"), proper adjectives WordNet does not know in lower case, words
already in the corpus or the seed queue, and words under the platform's Zipf floor
(``freq.zipf_info``, ``hard_reject``) are dropped and counted; the representative of a group is its
most frequent word; a head gives at most ``per_head_cap`` words, best score first
(``score = zipf + 0.3 if WordNet has it as an adjective - 0.15 x group index``).

Each word becomes one :class:`~assistant_axis.gapgen.Candidate` per head it came from
(``source_ref = "roget:<head id>"``; the registry merges a word harvested from two heads into one
row with two sources, interface resolution 4), with a ``gloss_hint`` built from the head
(:func:`gloss_hint`) and, where the opposed head gives one, a ``partner_hint``: a word of the
opposed head (or, for a pair completion, the trait that covers it) that WordNet lists as an
antonym or that is a negation form of the word (:func:`pair_candidates`; the rank-matched pairs
it adds up to ``pair_top`` per head pair are recorded in ``pair_candidates.jsonl`` without a hint).

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

GENERATOR = "roget"
WN_GENERATOR = "wn_clusters"
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
    zipf_hard: float = HARD_REJECT_BELOW
    include_wn: bool = False
    wn_closure_depth: int = 3

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
                 gap: str = "") -> tuple[list[HarvestItem], Counter]:
    """Representatives of the head's adjective groups (module docstring); ``(items, drop counts)``."""
    known = set(known_stems)
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
            fi = zipf_info(item, zipf_fn=zipf)
            if fi.hard_reject or fi.zipf_min < cfg.zipf_hard:
                drops["zipf_hard"] += 1
                continue
            syns = lex.adj_synsets(item) if lex is not None else []
            cands.append((fi.zipf_min, -len(cands), item, stem, fi.probe_band, bool(syns), len(syns)))
            all_clean.append(item)
        if not cands:
            continue
        cands.sort(reverse=True)
        z, _, item, stem, probe, wn_found, n_senses = cands[0]
        drops["not_representative"] += len(cands) - 1
        seen.add(stem)
        score = round(z + (0.3 if wn_found else 0.0) - 0.15 * gi, 3)
        reps.append(HarvestItem(surface=item, head_id=head.id, partner_id=partner_id, group_index=gi, siblings=[],
                                zipf_min=z, probe_band=probe, wn_found=wn_found, n_senses=n_senses, score=score,
                                class_vi=head.klass == "VI", gap_class=gap))
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


def _sense_word(head: Head, guard: Optional[LabelGuard], *, exclude: Collection[str] = ()) -> Optional[str]:
    """The head's title in lower case (``Seclusion. Exclusion`` -> ``seclusion or exclusion``), or
    its first noun when the title is excluded (the candidate's own word, or a label when a guard is given)."""
    def banned(w: str) -> bool:
        return w.lower() in exclude or (guard is not None and guard.contains(w))
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
    where_clause = f" ({where})" if where and not (guard is not None and guard.contains(where)) else ""
    def ok(w: str) -> bool:
        return (w.islower() and w != me and w != sense and w.split()[-1] not in STOPWORDS
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
            head_scope: Optional[Mapping[str, Optional[int]]] = None) -> HarvestResult:
    """Harvest the selected gap heads; build the gloss hints, the pair candidates and the Candidates.
    ``head_scope`` (head id -> 0, 1, 2 or None): heads rated 0 are skipped and counted."""
    rows = report.by_id()
    selected = select_heads(report, cfg)
    by_head: dict[str, list[HarvestItem]] = {}
    drops: Counter = Counter()
    not_character: list[str] = []
    ratings = dict(head_scope or {})
    for h in selected:
        r = rows[h]
        items, d = harvest_head(index.heads[h], known_stems=known_stems, cfg=cfg, lex=lex, zipf=zipf,
                                partner_id=r.partner, gap=r.gap_class)
        if ratings.get(h) == 0:
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
        # two heads the rules paired (rank-matched pairs stay in pair_candidates.jsonl only)
        if p.pair_source not in ("rule", "rule_weak") or not (p.double_confirmed or p.morph):
            continue
        hints.setdefault((p.a, p.head_a), p.b)
        if not p.partner_existing:
            hints.setdefault((p.b, p.head_b), p.a)
    items = [it for h in selected for it in by_head.get(h, [])]
    cands = to_candidates(items, generator=GENERATOR, run_id=run_id, partner_hints=hints)
    counts = harvest_counts(report, selected, by_head, drops, pc, cands, cfg)
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
         f"- Dropped: {json.dumps(c['drops'])}.",
         f"- Zipf probe band {c['probe_band_frac']:.0%}; Class VI {c['class_vi_frac']:.0%}; WordNet adjective "
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
