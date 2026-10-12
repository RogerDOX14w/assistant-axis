"""The beam passes: words the tokenizer splits, and multiword phrases (plan section 5, ``beam.py``; plan 04
sections 3.4 and 3.5).

Both passes fill a run of masks left to right (:func:`beam_fill`).  The first mask is filled from the model's
distribution with every mask still in place: the top ``k_first`` pieces that begin a word.  Each later mask is
filled conditioned on the pieces before it, from the model's own top ``beam_width`` pieces at that position (the
model chooses; a branch whose top pieces all break the slot's constraint dies), and a sequence's score is the sum
of its pieces' log-probabilities (a left-to-right chain, the scale of :mod:`.pll`'s ``l2r`` mode).  Each mask
carries a constraint (:data:`.frames.MULTIWORD_PATTERNS`):

* ``first`` / ``new_word``: a piece that begins a word (a leading-space piece in BPE; not ``##`` in WordPiece);
* ``cont``: a continuation piece, no leading space: **the same word goes on**.  The subword pass uses only
  these after the first mask (Roger's bare ``[MASK][MASK]`` and its longer runs in every generation frame,
  "He's habitually [MASK][MASK]" among them; two to four blanks, six under bert-wwm:
  :data:`.frames.SUBWORD_WIDTHS`, QUESTIONS 79 and 89), so it rebuilds whole words such as sycophantic, never
  phrases;
* ``free``: either (a continuation piece makes one word, a leading-space piece a two-word phrase).  No pattern of
  the multiword pass uses it since QUESTIONS 79 (Roger, 2026-10-12) took the bare two-slot form out: it was meant
  for split words, not phrases;
* ``after_hyphen``: the piece after a hyphen (no leading space in BPE; a word-initial piece in WordPiece).

**Rescoring** (:func:`_rescore`, on by default): an accepted surface's ``best_logprob`` is its pseudo-log-likelihood
spliced whole into the single slot of the instance that found it, so it sits on the union's scale (the chain's
own score, which leaves a pattern's literal text unscored, is kept as ``beam_score``).  The pass's PLL mode
(QUESTIONS 90): ``l2r`` for the subword pass, the plan's ``original`` for the multiword pass, unless
``pll_mode`` (the CLI's ``--pll-mode``) sets both.

The surface is rebuilt from the pattern and the pieces' text (tokenizer-independent), lower-cased; a one-word
surface is lemmatised like the single-mask pass's; the multiword pass drops a phrase that opens or closes on a
function word (:func:`function_word_edge`: "a fighter", "very shy", "lied to us", which the real model returned in
numbers from the bare two-slot form before QUESTIONS 79, and still does from "[MASK] to [MASK]").  Per surface:
the best score with its frame and subject, the
number of instances that produced it (``n_top``: every accepted sequence counts as surfaced, so a beam word is
always in the union; this is not the single-mask pass's top-2,000 test, and a run of ``w`` blanks can accept up to
``k_first x beam_width^(w-1)`` sequences an instance, over 2,000 at four blanks and ``k_first`` 100), its mean rank
among its instance's accepted sequences, its form (``word``, ``hyphenated``, ``phrase``) and pattern.  Roger's decision of 2026-10-10 keeps both beams at reduced K as the off-list
complement of Variant B, their yields reported apart (the CLI's defaults; the plan's 300 / 100 stay the
functions' own).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

import numpy as np

from .frames import (
    FRAME_BY_ID, MULTIWORD_HOSTS, MULTIWORD_PATTERNS, SLOT, SUBJECT_BY_KEY, Frame, alternating_subjects,
    instantiate_span, subword_widths,
)

CONSTRAINTS = ("first", "new_word", "cont", "free", "after_hyphen")
#: Pronouns the platform's fixed stoplist leaves out (it is the frequency floor's, and stays as it is), and the
#: colloquial intensifiers the real model puts before an adjective ("much fun", "damn cute", "freaking cute" in the
#: smoke run).  Degree adverbs that change the sense ("fiercely independent", "socially awkward") stay.
EDGE_EXTRA = frozenset("""us himself herself themselves myself yourself yourselves itself ourselves much damn darn
freaking fucking really super pretty totally kinda sorta real way""".split())


@dataclass(frozen=True)
class BeamHit:
    surface: str
    form: str                 # word | hyphenated | phrase
    score: float
    tokens: tuple


def allowed(tok, constraint: str) -> np.ndarray:
    """A boolean mask over the vocabulary: the pieces a slot with ``constraint`` accepts."""
    alpha = np.array([tok.is_alpha_piece(i) for i in range(tok.vocab_size)], dtype=bool)
    ws = np.asarray(tok.word_start, dtype=bool)
    if constraint in ("first", "new_word"):
        return alpha & ws
    if constraint == "cont":
        return alpha & ~ws
    if constraint == "free":
        return alpha
    if constraint == "after_hyphen":
        return alpha & (~ws if tok.scheme == "bpe" else ws)
    raise ValueError(f"unknown constraint {constraint!r} (one of {CONSTRAINTS})")


def function_word_edge(surface: str) -> bool:
    """A phrase that opens or closes on a function word (``gapgen.normalize.STOPWORDS``): "a fighter", "very shy",
    "in denial", "lied to us".  "[MASK] to [MASK]" produces many (the bare two-slot form did, before QUESTIONS 79);
    none is a label."""
    from assistant_axis.gapgen.normalize import STOPWORDS
    words = surface.split()
    edge = STOPWORDS | EDGE_EXTRA
    return len(words) > 1 and (words[0] in edge or words[-1] in edge)


def form_of(surface: str) -> str:
    return "phrase" if " " in surface else ("hyphenated" if "-" in surface else "word")


def assemble(pattern: str, constraints: Sequence[str], pieces: Sequence[str], word_start: Sequence[bool]) -> str:
    """The surface: the pattern with each mask replaced by its piece's text; a ``free`` slot filled with a
    word-start piece opens a new word (a space)."""
    parts = pattern.split(SLOT)
    out = parts[0]
    for j, (c, p, ws) in enumerate(zip(constraints, pieces, word_start)):
        out += (" " + p) if (c == "free" and ws) else p
        out += parts[j + 1]
    return " ".join(out.split()).lower()


class _Allowed:
    """Cached constraint masks per tokenizer."""

    def __init__(self, tok):
        self.tok = tok
        self._m: dict[str, np.ndarray] = {}

    def __call__(self, c: str) -> np.ndarray:
        if c not in self._m:
            self._m[c] = allowed(self.tok, c)
        return self._m[c]


def beam_fill(mlm, text: str, start: int, end: int, constraints: Sequence[str], *, pattern: str, k_first: int,
              beam_width: int = 3, masks_cache: Optional[_Allowed] = None) -> list[BeamHit]:
    """Fill the masks inside ``text[start:end]`` (see the module docstring); hits sorted by score."""
    tok = mlm.tok
    ok = masks_cache or _Allowed(tok)
    ids, span = tok.encode_with_span(text, start, end)
    masks = [p for p in span if ids[p] == tok.mask_id]
    if len(masks) != len(constraints):
        raise ValueError(f"{text!r}: {len(masks)} masks in the slot, {len(constraints)} constraints")
    lp0 = mlm.logprobs_at([ids], [masks[0]])[0]
    a0 = np.where(ok(constraints[0]), lp0, -np.inf)
    k = min(int(k_first), int(np.isfinite(a0).sum()))
    first = np.argpartition(-a0, k - 1)[:k] if k else np.array([], dtype=int)
    beams = []
    for t in first:
        seq = list(ids)
        seq[masks[0]] = int(t)
        beams.append((seq, float(lp0[t]), (int(t),)))
    special = np.zeros(tok.vocab_size, dtype=bool)
    special[list(tok.special_ids)] = True
    for j in range(1, len(masks)):
        if not beams:
            break
        lps = mlm.logprobs_at([b[0] for b in beams], [masks[j]] * len(beams))
        lps[:, special] = -np.inf
        cmask = ok(constraints[j])
        nxt = []
        for (seq, score, toks), lp in zip(beams, lps):
            top = np.argpartition(-lp, beam_width - 1)[:beam_width]
            for t in sorted(top, key=lambda x: -lp[x]):
                if cmask[t]:
                    s2 = list(seq)
                    s2[masks[j]] = int(t)
                    nxt.append((s2, score + float(lp[t]), toks + (int(t),)))
        beams = nxt
    hits = []
    for seq, score, toks in beams:
        pieces = [tok.piece_text[t] for t in toks]
        surface = assemble(pattern, constraints, pieces, [bool(tok.word_start[t]) for t in toks])
        hits.append(BeamHit(surface=surface, form=form_of(surface), score=score, tokens=toks))
    hits.sort(key=lambda h: (-h.score, h.surface))
    return hits


def _run(mlm, jobs: Sequence[tuple[Frame, str, str, tuple]], *, k_first: int, beam_width: int, pass_name: str,
         lemmatize: Optional[Callable[[str], str]], accept: Callable[[BeamHit, tuple], bool], settings: Mapping,
         rescore: bool = True, pll_mode: Optional[str] = None, echo=print):
    from .pll import pass_mode
    from .singlemask import PassResult, WordAgg, base_meta
    pll_mode = pass_mode(pass_name, pll_mode)
    t0 = time.time()
    n_fwd0 = getattr(mlm, "n_forward", 0)
    ok = _Allowed(mlm.tok)
    best: dict[str, dict] = {}
    yields: dict[str, dict] = {}
    for frame, subj, pattern, constraints in jobs:
        text, a, b = instantiate_span(frame, SUBJECT_BY_KEY.get(subj), mlm.tok.mask_token, pattern=pattern)
        hits = [h for h in beam_fill(mlm, text, a, b, constraints, pattern=pattern, k_first=k_first,
                                     beam_width=beam_width, masks_cache=ok) if accept(h, constraints)]
        y = yields.setdefault(pattern, {"instances": 0, "hits": 0, "word": 0, "hyphenated": 0, "phrase": 0})
        y["instances"] += 1
        seen = set()
        for rank, h in enumerate(hits, 1):
            w = lemmatize(h.surface) if (lemmatize and h.form == "word") else h.surface
            if w in seen:
                continue
            seen.add(w)
            y["hits"] += 1
            y[h.form] += 1
            cur = best.setdefault(w, {"best": None, "ranks": [], "frames": set()})
            cur["ranks"].append(rank)
            cur["frames"].add((frame.id, subj))
            if cur["best"] is None or h.score > cur["best"][0]:
                cur["best"] = (h.score, frame.id, subj, h.form, pattern)
    rescored = _rescore(mlm, {w: cur["best"] for w, cur in best.items()}, mode=pll_mode) if rescore else {}
    aggs = {}
    for w, cur in best.items():
        score, fid, subj, form, pattern = cur["best"]
        aggs[w] = WordAgg(word=w, surface=w, best_logprob=rescored.get(w, score), best_frame=fid,
                          best_subject=subj or None, mean_rank=float(np.mean(cur["ranks"])), n_top=len(cur["frames"]),
                          n_instances=len(jobs), form=form, pattern=pattern, beam_score=score)
    seconds = time.time() - t0
    n_fwd = getattr(mlm, "n_forward", 0) - n_fwd0
    meta = base_meta(mlm, pass_name, k_first=k_first, beam_width=beam_width, rescored=bool(rescore),
                     pll_mode=pll_mode, **settings)
    meta.update({"n_jobs": len(jobs), "yields": yields, "n_words": len(aggs),
                 "forms": {f: sum(1 for a in aggs.values() if a.form == f) for f in ("word", "hyphenated", "phrase")},
                 "seconds": round(seconds, 2), "n_forward": int(n_fwd),
                 "forward_per_second": round(n_fwd / seconds, 1) if seconds > 0 else None,
                 "jobs": [{"frame": f.id, "subject": s, "pattern": p} for f, s, p, _ in jobs]})
    echo(f"{pass_name}:{getattr(mlm, 'key', '?')}: {len(jobs)} instances, {len(aggs)} distinct surfaces "
         f"{meta['forms']}; {n_fwd} forward passes in {seconds:.1f} s")
    return PassResult(pass_name=pass_name, model_key=getattr(mlm, "key", "?"), aggs=aggs, meta=meta)


def _rescore(mlm, best: Mapping[str, tuple], *, mode: Optional[str] = None) -> dict[str, float]:
    """Each surface's pseudo-log-likelihood (:mod:`.pll`) spliced whole into its best instance's single slot: the
    probability of the word or phrase in the frame, its literal text included, on the scale of the single-mask
    and Variant-B scores (a pattern's own chain leaves the literal out: "[MASK]-seeking" scores only the first
    piece, so "attention-seeking" reached -0.07 and beam rows took 120 of the union's first 200 in the smoke run)."""
    from .frames import instantiate
    from .pll import PLL_MODE, pll_matrix
    out: dict[str, float] = {}
    by_inst: dict[tuple, list[str]] = {}
    for w, (_, fid, subj, _, _) in best.items():
        by_inst.setdefault((fid, subj), []).append(w)
    for (fid, subj), words in sorted(by_inst.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        text = instantiate(FRAME_BY_ID[fid], SUBJECT_BY_KEY.get(subj), mlm.tok.mask_token)
        for w, v in zip(words, pll_matrix(mlm, words, [text], mode=mode or PLL_MODE)[:, 0]):
            out[w] = float(v)
    return out


def subword_pass(mlm, frames: Sequence[Frame], *, k_first: int = 300, widths: Optional[Sequence[int]] = None,
                 beam_width: int = 3, subjects: Sequence[str] = ("she", "he"),
                 lemmatize: Optional[Callable[[str], str]] = None, rescore: bool = True,
                 pll_mode: Optional[str] = None, echo=print):
    """Words the tokenizer splits: each frame (one subject, she and he alternating) with runs of adjacent masks,
    ``widths`` long (default the model's, :data:`.frames.SUBWORD_WIDTHS`: 2-4, 2-6 under bert-wwm); every mask
    after the first must be a continuation piece."""
    widths = tuple(int(w) for w in widths) if widths is not None else subword_widths(getattr(mlm, "key", "?"))
    jobs = []
    for fid, subj in alternating_subjects(list(frames), subjects):
        for w in widths:
            jobs.append((FRAME_BY_ID[fid], subj, SLOT * int(w), ("first",) + ("cont",) * (int(w) - 1)))
    return _run(mlm, jobs, k_first=k_first, beam_width=beam_width, pass_name="subword", lemmatize=lemmatize,
                accept=lambda h, c: h.form == "word", settings={"widths": list(widths), "subjects": list(subjects)},
                rescore=rescore, pll_mode=pll_mode, echo=echo)


def multiword_pass(mlm, frames: Optional[Sequence[Frame]] = None, *, k_first: int = 100,
                   patterns: Mapping[str, tuple] = MULTIWORD_PATTERNS, beam_width: int = 3,
                   subjects: Sequence[str] = ("she", "he"), lemmatize: Optional[Callable[[str], str]] = None,
                   rescore: bool = True, pll_mode: Optional[str] = None, echo=print):
    """Phrases and compounds: each pattern of :data:`.frames.MULTIWORD_PATTERNS` in the slot of each host frame
    (:data:`.frames.MULTIWORD_HOSTS`, one subject each), each keeping what its constraints build (the bare
    ``[MASK][MASK]`` is the subword pass's since QUESTIONS 79).  Rescored in the plan's ``original`` PLL unless
    ``pll_mode`` says otherwise (QUESTIONS 90)."""
    hosts = list(frames) if frames is not None else [FRAME_BY_ID[f] for f in MULTIWORD_HOSTS]
    jobs = []
    for fid, subj in alternating_subjects(hosts, subjects):
        for pat, cons in patterns.items():
            jobs.append((FRAME_BY_ID[fid], subj, pat, tuple(cons)))
    return _run(mlm, jobs, k_first=k_first, beam_width=beam_width, pass_name="multiword", lemmatize=lemmatize,
                accept=lambda h, c: not function_word_edge(h.surface),
                settings={"patterns": dict(patterns), "subjects": list(subjects)}, rescore=rescore,
                pll_mode=pll_mode, echo=echo)
