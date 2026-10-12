"""The single-mask pass, the word groups it ranks, and the pass records every module shares (plan section 5,
``singlemask.py``; plan 04 section 3.3).

**Word groups** (:func:`build_word_groups`): every vocabulary piece that begins a word and is ASCII-alphabetic
(two letters or more) is detokenised, lower-cased and lemmatised (:func:`make_lemmatizer`: a form OEWN lists is
kept as it is; otherwise ``wn``'s morphy, adjective first, then noun; never a verb, so a participle the
dictionary lists as an adjective survives), and the pieces of one lemma form a group.  A lemma's probability in
an instance is the sum over its pieces ("Kind", "kind", "kinder" are one word).  Non-alphabetic pieces and
continuation pieces never form a word here.

**The pass** (:func:`run_single_pass`): one forward pass per frame instance, the full softmax at the slot, folded
into the groups.  Per word: ``best_logprob`` (max over instances) with its frame and subject, ``mean_rank`` (rank
among the groups, mean over instances), ``n_top`` (instances where it is in the top ``top_rank``, 2,000 by
default), the mean and the best log-probability per subject and the best per register (what the frame ablation
removes), and ``gender_log_odds``: the mean over frames of (she instance minus he instance), recorded and
never a gate (Roger, plan 04 section 9.2).  Only words in some instance's top ``top_rank`` are kept.

Per frame, the pass also keeps what the HHH probe reads: the frame's 200 best words (by the mean over its
instances) and the rank of each probe label (:data:`.frames.PROBE_LABELS`): a label that is one word piece is
ranked among the groups; one the tokenizer splits is scored by pseudo-log-likelihood in each instance
(:mod:`.pll`) and ranked against the same distribution (``via: "pll"``).

:class:`PassResult` is the record every pass returns and :func:`write_pass` / :func:`load_pass` store it under
``data/candidates/cache/masked_lm/agg/<model>/<pass>.jsonl`` (one word per line, sorted) plus a ``.meta.json``
(instances, timings, model revision, versions, the frame-bank hash, settings).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.atomic_io import atomic_write_text

from .frames import PROBE_LABELS, Instance, bank_sha256

TOP_RANK = 2000
FRAME_TOP = 200
LOG_FLOOR = -100.0


# ---------------------------------------------------------------------------- lemmas and word groups

def make_lemmatizer(is_lemma: Callable[[str], bool], morphy: Callable[[str, str], Iterable[str]]
                    ) -> Callable[[str], str]:
    """``word -> lemma`` (lower case in, lower case out); see the module docstring.  Cached."""
    cache: dict[str, str] = {}

    def lemma(word: str) -> str:
        w = word.lower()
        if w in cache:
            return cache[w]
        out = w
        if not is_lemma(w):
            for pos in ("a", "n"):
                cands = sorted(c.lower() for c in (morphy(w, pos) or ()) if c and c.lower() != w)
                hit = next((c for c in cands if is_lemma(c)), None)
                if hit:
                    out = hit
                    break
        cache[w] = out
        return out
    return lemma


def default_lemmatizer() -> Callable[[str], str]:  # pragma: no cover - needs the OEWN database
    """The OEWN lemmatizer: ``wn``'s morphy over the in-tree OEWN 2024 (``gapgen.wordnet``)."""
    import wn.morphy

    from assistant_axis.gapgen import wordnet as gw
    if not gw.ensure_oewn(download=False):
        raise SystemExit("OEWN is not installed in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn` first")
    w = gw.oewn()
    forms = {x.lemma().lower() for x in w.words()}
    m = wn.morphy.Morphy(w)

    def morphy(word: str, pos: str):
        return (m(word, pos) or {}).get(pos, ())
    return make_lemmatizer(forms.__contains__, morphy)


@dataclass
class WordGroups:
    """Vocabulary pieces grouped by lemma: ``token_ids`` ordered by group, ``starts`` the group offsets (for
    ``np.add.reduceat``), ``lemmas`` the group names (sorted)."""
    lemmas: list[str]
    token_ids: np.ndarray
    starts: np.ndarray

    def __post_init__(self):
        self.index = {w: i for i, w in enumerate(self.lemmas)}

    def __len__(self) -> int:
        return len(self.lemmas)

    def fold(self, lp_tokens: np.ndarray) -> np.ndarray:
        """``(n, vocab)`` token log-probabilities -> ``(n, groups)`` group log-probabilities (log of the summed
        probability), floored at :data:`LOG_FLOOR`."""
        lp = np.atleast_2d(lp_tokens)[:, self.token_ids].astype(np.float64)
        p = np.add.reduceat(np.exp(lp), self.starts, axis=1)
        with np.errstate(divide="ignore"):
            out = np.log(p)
        return np.maximum(out, LOG_FLOOR).astype(np.float32)


def build_word_groups(tok, lemmatize: Callable[[str], str], *, min_len: int = 2) -> WordGroups:
    by_lemma: dict[str, list[int]] = {}
    for i in range(tok.vocab_size):
        if not tok.word_start[i] or not tok.is_alpha_piece(i):
            continue
        text = tok.piece_text[i]
        if len(text) < min_len:
            continue
        by_lemma.setdefault(lemmatize(text.lower()), []).append(i)
    lemmas = sorted(by_lemma)
    ids, starts = [], []
    for w in lemmas:
        starts.append(len(ids))
        ids.extend(sorted(by_lemma[w]))
    return WordGroups(lemmas=lemmas, token_ids=np.asarray(ids, dtype=np.int64),
                      starts=np.asarray(starts, dtype=np.int64))


def ranks_of(lp: np.ndarray) -> np.ndarray:
    """1-based ranks along the last axis (best = 1; ties broken by index)."""
    order = np.argsort(-lp, axis=-1, kind="stable")
    ranks = np.empty_like(order)
    rows = np.arange(lp.shape[0])[:, None]
    ranks[rows, order] = np.arange(1, lp.shape[1] + 1)[None, :]
    return ranks


def estimate_rank(sorted_desc: np.ndarray, value: float) -> int:
    """Rank a score would take in a distribution sorted in descending order: 1 + the number of entries above it."""
    return int(np.searchsorted(-sorted_desc, -float(value), side="left")) + 1


# ---------------------------------------------------------------------------- records

@dataclass
class WordAgg:
    word: str
    surface: str
    best_logprob: float
    best_frame: str
    best_subject: Optional[str]
    mean_rank: Optional[float]
    n_top: int
    n_instances: int = 0
    by_subject_logprob: dict = field(default_factory=dict)
    by_subject_best: dict = field(default_factory=dict)
    by_register_best: dict = field(default_factory=dict)
    gender_log_odds: Optional[float] = None
    form: Optional[str] = None            # word | hyphenated | phrase (the beam passes)
    pattern: Optional[str] = None         # the multiword pattern or the subword width
    beam_score: Optional[float] = None    # a beam pass's chain score, before rescoring

    def as_dict(self) -> dict:
        d = asdict(self)
        for k in ("best_logprob", "mean_rank", "gender_log_odds", "beam_score"):
            if d[k] is not None:
                d[k] = round(float(d[k]), 4)
        for k in ("by_subject_logprob", "by_subject_best", "by_register_best"):
            d[k] = {a: round(float(b), 4) for a, b in sorted(d[k].items())}
        return d


@dataclass
class PassResult:
    pass_name: str            # single | probe | subword | multiword | variant_b | contrast
    model_key: str
    aggs: dict                # word -> WordAgg (or a plain dict when loaded)
    meta: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.pass_name}:{self.model_key}"


def agg_paths(agg_dir: Path, model_key: str, pass_name: str) -> tuple[Path, Path]:
    d = Path(agg_dir) / model_key
    return d / f"{pass_name}.jsonl", d / f"{pass_name}.meta.json"


def write_pass(res: PassResult, agg_dir: Path) -> tuple[Path, Path]:
    data, meta = agg_paths(agg_dir, res.model_key, res.pass_name)
    data.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for w in sorted(res.aggs):
        a = res.aggs[w]
        rows.append(json.dumps(a.as_dict() if hasattr(a, "as_dict") else a, ensure_ascii=False, sort_keys=True))
    atomic_write_text("".join(r + "\n" for r in rows), data)
    atomic_write_text(json.dumps(res.meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n", meta)
    return data, meta


def load_pass(agg_dir: Path, model_key: str, pass_name: str) -> Optional[PassResult]:
    data, meta = agg_paths(agg_dir, model_key, pass_name)
    if not data.exists():
        return None
    aggs = {}
    for line in data.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            aggs[d["word"]] = d
    m = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
    return PassResult(pass_name=pass_name, model_key=model_key, aggs=aggs, meta=m)


def load_all_passes(agg_dir: Path, *, models: Optional[Sequence[str]] = None,
                    passes: Sequence[str] = ("single", "probe", "subword", "multiword", "variant_b")
                    ) -> dict[str, PassResult]:
    """Every stored pass as ``{"<pass>:<model>": PassResult}`` (contrast excluded)."""
    out = {}
    root = Path(agg_dir)
    keys = models if models is not None else sorted(p.name for p in root.iterdir() if p.is_dir()) \
        if root.exists() else []
    for m in keys:
        for p in passes:
            r = load_pass(root, m, p)
            if r is not None:
                out[r.key] = r
    return out


def base_meta(mlm, pass_name: str, **settings) -> dict:
    from assistant_axis.gapgen.registry import utc_now
    meta = {"pass": pass_name, "model_key": getattr(mlm, "key", None), "model": getattr(mlm, "model_id", None),
            "revision": getattr(mlm, "revision", None), "device": getattr(mlm, "device", None),
            "frame_bank_sha256": bank_sha256(), "at": utc_now(), "settings": settings}
    try:
        from .models import runtime_versions
        meta["versions"] = runtime_versions()
    except Exception:  # noqa: BLE001 - versions are a record, never a reason to fail
        meta["versions"] = None
    return meta


# ---------------------------------------------------------------------------- the pass

def encode_instances(tok, instances: Sequence[Instance]) -> tuple[list[list[int]], list[int]]:
    seqs, pos = [], []
    for inst in instances:
        ids = tok.encode(inst.text)
        masks = [i for i, t in enumerate(ids) if t == tok.mask_id]
        if len(masks) != 1:
            raise ValueError(f"instance {inst.frame_id}/{inst.subject} has {len(masks)} masks, expected 1")
        seqs.append(ids)
        pos.append(masks[0])
    return seqs, pos


def instance_group_logprobs(mlm, instances: Sequence[Instance], groups: WordGroups, *, chunk: int = 64
                            ) -> np.ndarray:
    """``(n_instances, n_groups)`` group log-probabilities at each instance's slot."""
    seqs, pos = encode_instances(mlm.tok, instances)
    out = np.empty((len(instances), len(groups)), dtype=np.float32)
    for i in range(0, len(seqs), chunk):
        out[i:i + chunk] = groups.fold(mlm.logprobs_at(seqs[i:i + chunk], pos[i:i + chunk]))
    return out


def _frame_means(instances: Sequence[Instance], lp: np.ndarray) -> tuple[list[str], np.ndarray]:
    fids = list(dict.fromkeys(inst.frame_id for inst in instances))
    idx = {f: [i for i, inst in enumerate(instances) if inst.frame_id == f] for f in fids}
    return fids, np.stack([lp[idx[f]].mean(axis=0) for f in fids]) if fids else np.zeros((0, lp.shape[1]))


def track_label_scores(mlm, instances: Sequence[Instance], lp: np.ndarray, groups: WordGroups,
                       labels: Sequence[str], *, lemmatize: Callable[[str], str], pll_mode: str
                       ) -> dict[str, np.ndarray]:
    """Per label, its log-probability in each instance: the group's when the label is one word piece, else its
    pseudo-log-likelihood spliced into the instance."""
    from .pll import pll_matrix
    out: dict[str, np.ndarray] = {}
    pll_labels = []
    for lab in labels:
        ids = mlm.tok.word_ids(lab)
        g = groups.index.get(lemmatize(lab.lower())) if len(ids) == 1 else None
        if g is not None:
            out[lab] = lp[:, g]
        else:
            pll_labels.append(lab)
    if pll_labels:
        mat = pll_matrix(mlm, pll_labels, [inst.text for inst in instances], mode=pll_mode)
        for i, lab in enumerate(pll_labels):
            out[lab] = mat[i]
    return out


def run_single_pass(mlm, instances: Sequence[Instance], *, top_rank: int = TOP_RANK, batch: Optional[int] = None,
                    lemmatize: Optional[Callable[[str], str]] = None, groups: Optional[WordGroups] = None,
                    track: Sequence[str] = PROBE_LABELS, pass_name: str = "single", pll_mode: Optional[str] = None,
                    echo=print) -> PassResult:
    """The single-mask pass over ``instances`` (see the module docstring)."""
    from .pll import PLL_MODE
    pll_mode = pll_mode or PLL_MODE
    t0 = time.time()
    n_fwd0 = getattr(mlm, "n_forward", 0)
    if lemmatize is None:
        lemmatize = default_lemmatizer()
    groups = groups or build_word_groups(mlm.tok, lemmatize)
    lp = instance_group_logprobs(mlm, instances, groups, chunk=batch or 64)
    ranks = ranks_of(lp)
    n = len(instances)
    top = ranks <= top_rank
    n_top = top.sum(axis=0)
    keep = np.nonzero(n_top > 0)[0]
    best_i = lp.argmax(axis=0)
    mean_rank = ranks.mean(axis=0)
    subj = [inst.subject for inst in instances]
    regs = [inst.register for inst in instances]
    subj_idx = {s: [i for i, x in enumerate(subj) if x == s] for s in dict.fromkeys(subj) if s is not None}
    reg_idx = {r: [i for i, x in enumerate(regs) if x == r] for r in dict.fromkeys(regs)}
    subj_mean = {s: lp[ix].mean(axis=0) for s, ix in subj_idx.items()}
    subj_best = {s: lp[ix].max(axis=0) for s, ix in subj_idx.items()}
    reg_best = {r: lp[ix].max(axis=0) for r, ix in reg_idx.items()}
    # she minus he, paired by frame
    pos_of = {(inst.frame_id, inst.subject): i for i, inst in enumerate(instances)}
    pairs = [(pos_of[(f, "she")], pos_of[(f, "he")]) for f in dict.fromkeys(i.frame_id for i in instances)
             if (f, "she") in pos_of and (f, "he") in pos_of]
    gender = (lp[[a for a, _ in pairs]] - lp[[b for _, b in pairs]]).mean(axis=0) if pairs else None
    aggs: dict[str, WordAgg] = {}
    for g in keep:
        w = groups.lemmas[g]
        bi = int(best_i[g])
        aggs[w] = WordAgg(
            word=w, surface=w, best_logprob=float(lp[bi, g]), best_frame=instances[bi].frame_id,
            best_subject=instances[bi].subject, mean_rank=float(mean_rank[g]), n_top=int(n_top[g]), n_instances=n,
            by_subject_logprob={s: float(v[g]) for s, v in subj_mean.items()},
            by_subject_best={s: float(v[g]) for s, v in subj_best.items()},
            by_register_best={r: float(v[g]) for r, v in reg_best.items()},
            gender_log_odds=float(gender[g]) if gender is not None else None)
    # per frame: the top words and the probe labels' ranks
    fids, fmean = _frame_means(instances, lp)
    tracked = track_label_scores(mlm, instances, lp, groups, track, lemmatize=lemmatize, pll_mode=pll_mode) \
        if track else {}
    frames_out = {}
    for fi, f in enumerate(fids):
        row = fmean[fi]
        order = np.argsort(-row, kind="stable")
        srt = row[order]
        ix = [i for i, inst in enumerate(instances) if inst.frame_id == f]
        labels = {}
        for lab, vec in tracked.items():
            v = float(np.mean(vec[ix]))
            g = groups.index.get(lemmatize(lab.lower()))
            via = "vocab" if (g is not None and len(mlm.tok.word_ids(lab)) == 1) else "pll"
            rank = int((row > row[g]).sum()) + 1 if via == "vocab" else estimate_rank(srt, v)
            labels[lab] = {"rank": rank, "logprob": round(v, 4), "via": via}
        inst0 = instances[ix[0]]
        frames_out[f] = {"register": inst0.register, "family": inst0.family, "kind": inst0.kind, "slot": inst0.slot,
                         "n_instances": len(ix),
                         "top": [[groups.lemmas[int(g)], round(float(row[g]), 4)] for g in order[:FRAME_TOP]],
                         "labels": labels}
    thresholds = [float(np.sort(lp[i])[::-1][min(top_rank, lp.shape[1]) - 1]) for i in range(n)]
    seconds = time.time() - t0
    n_fwd = getattr(mlm, "n_forward", 0) - n_fwd0
    meta = base_meta(mlm, pass_name, top_rank=top_rank, pll_mode=pll_mode, track=list(track))
    meta.update({"n_instances": n, "n_groups": len(groups), "n_words_kept": len(aggs),
                 "instances": [inst.as_dict() for inst in instances], "thresholds": thresholds,
                 "frames": frames_out, "seconds": round(seconds, 2), "n_forward": int(n_fwd),
                 "instances_per_minute": round(60.0 * n / seconds, 1) if seconds > 0 else None,
                 "forward_per_second": round(n_fwd / seconds, 1) if seconds > 0 else None})
    echo(f"{pass_name}:{getattr(mlm, 'key', '?')}: {n} instances, {len(groups)} word groups, {len(aggs)} words in "
         f"some top {top_rank}; {seconds:.1f} s ({meta['instances_per_minute']} instances/min)")
    return PassResult(pass_name=pass_name, model_key=getattr(mlm, "key", "?"), aggs=aggs, meta=meta)


def frame_top(res_meta: Mapping, frame_id: str, n: int = 50) -> list:
    """A frame's top ``n`` words from a pass's meta."""
    return list((res_meta.get("frames") or {}).get(frame_id, {}).get("top", [])[:n])
