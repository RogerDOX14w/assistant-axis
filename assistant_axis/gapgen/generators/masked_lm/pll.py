"""Pseudo-log-likelihood scoring: Variant B and the trait-hood contrast score (plan section 5, ``pll.py``; the
Variant-B decision of open question 1, Roger 2026-10-10: "build both, and experiment from there").

**PLL** (:func:`pll_items`): a word is spliced into a frame with its *actual* tokens; each of its tokens is
masked in turn and the log-probabilities the model assigns them back are summed.  Two modes:

* ``l2r`` (the default): when token *j* is scored, the word's later tokens are masked too, so the word is
  scored left to right like a chain of conditionals (Kauf & Ivanova 2023, "PLL-word-l2r").  Plain PLL lets the
  later pieces of a split word predict the earlier ones ("syc" is easy once "oph", "antic" are visible), which
  inflates every split word against a one-piece word; ``l2r`` keeps a split word's score on the scale of the
  single-mask log-probabilities it is ranked beside in the union, and matches the beam passes' chain.
* ``original``: only token *j* is masked (Salazar et al. 2020), the plan's form.

For a one-piece word both are the single-mask log-probability.  **The mode is set per pass** (QUESTIONS 90, Roger
2026-10-12: "left-to-right for single and split words, the plan's original form for multiword phrases";
:data:`PASS_PLL_MODES`): ``l2r`` for the single-mask, probe and subword passes, Variant B and the contrast score,
``original`` for the multiword pass, whose phrases pilot A ranked far better that way (18.0% of the multiword
labels in the top 5,000 against 4.5%).  The global ``--pll-mode`` overrides every pass.

**Variant B** (:func:`variant_b`): OEWN's adjectives and person nouns (:mod:`.wordlist`) scored by PLL in twelve
fixed instances (:data:`.frames.VARIANT_B_INSTANCES`) and ranked by the best of them.  Each instance's own
single-mask distribution over the word groups is computed too, so a word's PLL can be placed in it: ``mean_rank``
and ``n_top`` (instances where it would be in the top 2,000) mean what they mean for the single-mask pass.  Its
universe is WordNet's: it cannot surface a word OEWN lacks (the coverage count in :mod:`.evaluate` says how many
corpus labels that is), but it handles any listed word exactly, however it tokenizes, with no beam noise.

**The contrast score** (:func:`score_words`, frozen interface): the mean PLL in the dispositional contrast frames
minus the larger of the means in the state and the physical frames (:data:`.frames.CONTRAST_SET`, subjects she and
he); ``state_flag`` / ``physical_flag`` when that mean beats the dispositional one.  Local, $0, any word list:
other generators' candidates can be run through it.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

import numpy as np

from .frames import (
    CONTRAST_SET, CONTRAST_SUBJECTS, FRAME_BY_ID, SUBJECT_BY_KEY, VARIANT_B_INSTANCES, Instance, instantiate,
    pairs_to_instances,
)

PLL_MODES = ("l2r", "original")
PLL_MODE = "l2r"
#: Each pass's mode when ``--pll-mode`` is not given (see the module docstring).  Variant B is not named in
#: QUESTIONS 90 (pilot A did not run it): it keeps ``l2r``, the scale of its single and split words.
PASS_PLL_MODES: dict[str, str] = {"single": "l2r", "probe": "l2r", "subword": "l2r", "multiword": "original",
                                  "variant_b": "l2r", "contrast": "l2r"}
#: The score of a word the tokenizer cannot represent (its pieces are all unknown or special): far below any real
#: log-probability, and finite so the records stay JSON.
UNSCORABLE = -1000.0
#: Words per checkpoint chunk of the long scoring runs.
CHUNK_WORDS = 1000


def pass_mode(pass_name: str, override: Optional[str] = None) -> str:
    """The PLL mode a pass runs in: ``override`` (the global ``--pll-mode``) when given, else the pass's own
    (:data:`PASS_PLL_MODES`)."""
    mode = override or PASS_PLL_MODES.get(pass_name)
    if mode not in PLL_MODES:
        raise ValueError(f"pll mode must be one of {PLL_MODES}, got {mode!r} (pass {pass_name!r})")
    return mode


def splice(text: str, mask_token: str, word: str) -> tuple[str, int, int]:
    """``text`` with its (single) mask token replaced by ``word``; the word's character span."""
    i = text.find(mask_token)
    if i < 0 or text.find(mask_token, i + 1) >= 0:
        raise ValueError(f"expected exactly one {mask_token!r} in {text!r}")
    out = text[:i] + word + text[i + len(mask_token):]
    return out, i, i + len(word)


def masked_items(ids: Sequence[int], positions: Sequence[int], mask_id: int, mode: str = PLL_MODE
                 ) -> list[tuple[list[int], int, int]]:
    """``(masked sequence, position, target)`` for each token of the word."""
    if mode not in PLL_MODES:
        raise ValueError(f"pll mode must be one of {PLL_MODES}, got {mode!r}")
    out = []
    for j, p in enumerate(positions):
        seq = list(ids)
        for q in (positions[j:] if mode == "l2r" else [p]):
            seq[q] = mask_id
        out.append((seq, p, int(ids[p])))
    return out


def pll_items(mlm, items: Sequence[tuple[Sequence[int], Sequence[int]]], *, mode: str = PLL_MODE) -> np.ndarray:
    """PLL of each ``(ids, word positions)`` item: one masked sequence per word token, batched together."""
    seqs, pos, tgt, owner = [], [], [], []
    out = np.zeros(len(items), dtype=np.float64)
    for k, (ids, positions) in enumerate(items):
        if not positions:
            out[k] = UNSCORABLE
            continue
        for seq, p, t in masked_items(ids, positions, mlm.tok.mask_id, mode):
            seqs.append(seq)
            pos.append(p)
            tgt.append(t)
            owner.append(k)
    if not seqs:
        return out
    order = sorted(range(len(seqs)), key=lambda i: len(seqs[i]))   # less padding
    lps = mlm.target_logprobs([seqs[i] for i in order], [pos[i] for i in order], [tgt[i] for i in order])
    np.add.at(out, np.asarray([owner[i] for i in order]), np.asarray(lps, dtype=np.float64))
    return out


def pll_score(mlm, instance_text: str, word: str, *, mode: str = PLL_MODE) -> float:
    """PLL of ``word`` spliced into one instance's text (which holds the model's mask token once)."""
    text, a, b = splice(instance_text, mlm.tok.mask_token, word)
    ids, positions = mlm.tok.encode_with_span(text, a, b)
    return float(pll_items(mlm, [(ids, positions)], mode=mode)[0])


def pll_matrix(mlm, words: Sequence[str], instance_texts: Sequence[str], *, mode: str = PLL_MODE) -> np.ndarray:
    """``(n_words, n_instances)`` PLLs."""
    items = []
    for w in words:
        for t in instance_texts:
            text, a, b = splice(t, mlm.tok.mask_token, w)
            items.append(mlm.tok.encode_with_span(text, a, b))
    flat = pll_items(mlm, items, mode=mode)
    return flat.reshape(len(words), len(instance_texts)).astype(np.float32)


def checkpoint_key(texts: Sequence[str], mode: str, model_key: str, revision: Optional[str] = None) -> str:
    """A short fingerprint of what a checkpoint's scores depend on (instance texts, mode, model, revision), for
    its file name: a checkpoint is resumed only by the same scoring."""
    import hashlib
    doc = json.dumps({"texts": list(texts), "mode": mode, "model": model_key, "revision": revision})
    return hashlib.sha256(doc.encode()).hexdigest()[:12]


def _checkpointed(words: Sequence[str], texts: Sequence[str], mlm, *, mode: str, checkpoint: Optional[Path],
                  chunk: int, echo) -> dict[str, list[float]]:
    """PLLs of every word in every text, ``chunk`` words at a time, appended to ``checkpoint`` (JSON lines
    ``{"word", "pll"}``) after each chunk so an interrupted run resumes where it stopped."""
    done: dict[str, list[float]] = {}
    if checkpoint is not None and Path(checkpoint).exists():
        for line in Path(checkpoint).read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue                    # a torn last line: that chunk is redone
            if len(d.get("pll") or []) == len(texts):
                done[d["word"]] = d["pll"]
    todo = [w for w in words if w not in done]
    t0 = time.time()
    for i in range(0, len(todo), chunk):
        part = todo[i:i + chunk]
        mat = pll_matrix(mlm, part, texts, mode=mode)
        lines = []
        for w, row in zip(part, mat):
            done[w] = [round(float(x), 4) for x in row]
            lines.append(json.dumps({"word": w, "pll": done[w]}, ensure_ascii=False))
        if checkpoint is not None:
            Path(checkpoint).parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint, "a", encoding="utf-8") as fh:
                fh.write("".join(x + "\n" for x in lines))
        n = min(i + chunk, len(todo))
        dt = time.time() - t0
        echo(f"  scored {n}/{len(todo)} words x {len(texts)} instances ({len(words) - len(todo)} resumed); "
             f"{dt:.0f} s, about {dt / n * (len(todo) - n) / 60:.1f} min to go")
    return done


# ---------------------------------------------------------------------------- Variant B

def variant_b(mlm, wordlist: Sequence[str], frames: Sequence[tuple[str, str]] = VARIANT_B_INSTANCES, *,
              top_rank: int = 2000, groups=None, lemmatize: Optional[Callable[[str], str]] = None,
              mode: str = PLL_MODE, checkpoint: Optional[Path] = None, chunk: int = CHUNK_WORDS, echo=print):
    """Variant B over ``wordlist`` (see the module docstring).  Returns a ``PassResult`` (pass ``variant_b``);
    every word of the list is kept (the full ranking feeds the recovery curves; the table takes the surfaced)."""
    from .singlemask import (
        WordAgg, PassResult, base_meta, build_word_groups, default_lemmatizer, estimate_rank,
        instance_group_logprobs,
    )
    t0 = time.time()
    n_fwd0 = getattr(mlm, "n_forward", 0)
    insts = pairs_to_instances(frames, mlm.tok.mask_token)
    if groups is None:
        groups = build_word_groups(mlm.tok, lemmatize or default_lemmatizer())
    dist = instance_group_logprobs(mlm, insts, groups)
    srt = -np.sort(-dist, axis=1)
    thresholds = srt[:, min(top_rank, srt.shape[1]) - 1]
    words = list(dict.fromkeys(wordlist))
    scores = _checkpointed(words, [i.text for i in insts], mlm, mode=mode, checkpoint=checkpoint, chunk=chunk,
                           echo=echo)
    aggs = {}
    for w in words:
        row = np.asarray(scores[w], dtype=np.float32)
        bi = int(row.argmax())
        ranks = [estimate_rank(srt[i], row[i]) for i in range(len(insts))]
        aggs[w] = WordAgg(word=w, surface=w, best_logprob=float(row[bi]), best_frame=insts[bi].frame_id,
                          best_subject=insts[bi].subject, mean_rank=float(np.mean(ranks)),
                          n_top=int(sum(1 for r in ranks if r <= top_rank)), n_instances=len(insts),
                          by_subject_logprob={s: float(np.mean([row[i] for i, x in enumerate(insts)
                                                                if x.subject == s]))
                                              for s in dict.fromkeys(x.subject for x in insts)})
    seconds = time.time() - t0
    n_fwd = getattr(mlm, "n_forward", 0) - n_fwd0
    meta = base_meta(mlm, "variant_b", top_rank=top_rank, pll_mode=mode, n_words=len(words))
    meta.update({"instances": [i.as_dict() for i in insts], "thresholds": [float(x) for x in thresholds],
                 "n_words": len(words), "n_surfaced": sum(1 for a in aggs.values() if a.n_top > 0),
                 "seconds": round(seconds, 2), "n_forward": int(n_fwd),
                 "forward_per_second": round(n_fwd / seconds, 1) if seconds > 0 else None})
    echo(f"variant_b:{getattr(mlm, 'key', '?')}: {len(words)} words x {len(insts)} instances, "
         f"{meta['n_surfaced']} in some top {top_rank}; {seconds:.1f} s")
    return PassResult(pass_name="variant_b", model_key=getattr(mlm, "key", "?"), aggs=aggs, meta=meta)


# ---------------------------------------------------------------------------- the contrast score

@dataclass(frozen=True)
class Contrast:
    trait_contrast: float          # dispositional minus max(state, physical); the Candidate.score of the wave
    state_flag: bool               # the state frames' mean beats the dispositional one
    physical_flag: bool            # the physical frames' mean beats the dispositional one
    dispositional: float
    state: float
    physical: float

    def as_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in asdict(self).items()}


def contrast_instances(mask_token: str, frames: Sequence[str] = CONTRAST_SET,
                       subjects: Sequence[str] = CONTRAST_SUBJECTS) -> list[Instance]:
    out = []
    for fid in frames:
        f = FRAME_BY_ID[fid]
        for s in subjects:
            out.append(Instance(f.id, s, instantiate(f, SUBJECT_BY_KEY[s], mask_token), f.register, f.kind, f.family,
                                f.slot))
    return out


def contrast_from_scores(row: Sequence[float], kinds: Sequence[str]) -> Contrast:
    def mean(k):
        v = [float(x) for x, kk in zip(row, kinds) if kk == k]
        if not v:
            raise ValueError(f"no {k} frames in the contrast set")
        return float(np.mean(v))
    d, s, p = mean("dispositional"), mean("state"), mean("physical")
    return Contrast(trait_contrast=d - max(s, p), state_flag=s > d, physical_flag=p > d, dispositional=d, state=s,
                    physical=p)


def score_words(words: Iterable[str], *, model_key: str = "roberta", frames: Sequence[str] = CONTRAST_SET,
                subjects: Sequence[str] = CONTRAST_SUBJECTS, mlm=None, device: str = "auto",
                mode: str = PLL_MODE, checkpoint: Optional[Path] = None, chunk: int = CHUNK_WORDS,
                echo=print) -> dict[str, Contrast]:
    """The trait-hood contrast score of each word (frozen interface; see the module docstring).  ``mlm``
    defaults to ``model_key`` loaded from the in-tree cache on ``device`` (``auto``: MPS when there)."""
    if mlm is None:  # pragma: no cover - loads the real model
        from .models import load_mlm
        mlm = load_mlm(model_key, device)
    insts = contrast_instances(mlm.tok.mask_token, frames, subjects)
    kinds = [i.kind for i in insts]
    ws = list(dict.fromkeys(words))
    scores = _checkpointed(ws, [i.text for i in insts], mlm, mode=mode, checkpoint=checkpoint, chunk=chunk,
                           echo=echo)
    return {w: contrast_from_scores(scores[w], kinds) for w in ws}
