"""The three fill-mask models, their tokenizers, the device, and the tokenizer census (plan section 5, ``models.py``).

:data:`MODELS` pins each model (Hub id, revision, published size and weights sha256, licence; checked against the
Hub API on 2026-10-11).  Each download is Roger's approval, recorded in the model's ``approved_by``:
**roberta-large** on 2026-10-11 (~1.4 GB, MIT, into the gitignored ``data/external/hf/``), and
``bert-large-cased-whole-word-masking`` and ``ModernBERT-large`` on 2026-10-12 with the fill-mask plan (plan
section 1).  Downloads go only through
``setup_external.py --hf-model <id>`` with :data:`HF_MODEL_ALLOW_PATTERNS` (the approved models alone); every load
here is ``local_files_only`` from the in-tree cache (``gapgen.paths.hf_cache_dir``) and **never passes
``trust_remote_code``** (:func:`loader_kwargs`, asserted by the tests).

:class:`TokenizerAdapter` gives the passes one view of a tokenizer whatever its scheme: ``bpe`` (roberta,
ModernBERT: a piece that begins with the leading-space marker ``Ġ`` begins a word, any other piece continues one)
or ``wordpiece`` (BERT: a piece that begins with ``##`` continues a word).  :class:`HFMaskedLM` adds the model:
batched log-softmax at chosen positions (:meth:`HFMaskedLM.logprobs_at`) and the log-probability of chosen
targets (:meth:`HFMaskedLM.target_logprobs`), on MPS or CPU in float32.

:func:`token_census` classes a label ``single`` (one token in sentence position), ``subword`` (one word the
tokenizer splits) or ``multiword`` (a space or a hyphen): it bounds what the single-mask pass can ever return.
It needs the tokenizer files only.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

import numpy as np

from assistant_axis.gapgen.paths import REPO_ROOT, hf_cache_dir, pin_hf_cache


@dataclass(frozen=True)
class ModelSpec:
    key: str                     # roberta | bert_wwm | modernbert (the CLI's --models names)
    hf_id: str
    short: str                   # the table's ``models[]`` name
    revision: str                # pinned; the revision actually loaded is recorded beside it
    approx_gb: float
    weights_bytes: int           # model.safetensors, as published
    weights_sha256: str          # its published LFS sha256
    licence: str
    licence_url: str
    scheme: str                  # bpe | wordpiece
    approved_by: Optional[str] = None   # Roger's approval of the download; None = a fresh ask


MODELS: dict[str, ModelSpec] = {m.key: m for m in (
    ModelSpec(key="roberta", hf_id="FacebookAI/roberta-large", short="roberta-large",
              revision="722cf37b1afa9454edce342e7895e588b6ff1d59", approx_gb=1.4, weights_bytes=1_421_700_479,
              weights_sha256="047c85f0b96269cd62e6f732644f067004eebd95af5b5d35965ae2528f13bf38", licence="MIT",
              licence_url="https://huggingface.co/FacebookAI/roberta-large", scheme="bpe",
              approved_by="Roger, 2026-10-11 (roberta-large only, ~1.4 GB, into data/external/hf)"),
    ModelSpec(key="bert_wwm", hf_id="google-bert/bert-large-cased-whole-word-masking",
              short="bert-large-cased-whole-word-masking", revision="4110364c3591c4609a3401e86f6c03a0495536fa",
              approx_gb=1.3, weights_bytes=1_338_695_480,
              weights_sha256="3a903a597c11052feb1dbd6d41e2c38e2795c809e55bd0b8e384c662f59a64ee", licence="Apache-2.0",
              licence_url="https://huggingface.co/google-bert/bert-large-cased-whole-word-masking", scheme="wordpiece",
              approved_by="Roger, 2026-10-12 (approved with the fill-mask plan; ~1.3 GB, into data/external/hf)"),
    ModelSpec(key="modernbert", hf_id="answerdotai/ModernBERT-large", short="ModernBERT-large",
              revision="45bb4654a4d5aaff24dd11d4781fa46d39bf8c13", approx_gb=1.6, weights_bytes=1_583_544_840,
              weights_sha256="44510fec5d3a81a1877f225637b869495f18e55f6f23a09abb9be0acc030295f",
              licence="Apache-2.0", licence_url="https://huggingface.co/answerdotai/ModernBERT-large", scheme="bpe",
              approved_by="Roger, 2026-10-12 (approved with the fill-mask plan; ~1.6 GB, into data/external/hf)"),
)}
PRIMARY_MODEL = "roberta"

#: What a load needs: config, tokenizer files, the safetensors weights (no .bin, .h5, msgpack or ONNX duplicates),
#: and the model card (its licence line).
_ALLOW = ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.json",
          "merges.txt", "vocab.txt", "model.safetensors", "README.md"]
#: ``setup_external.py --hf-model`` may fetch the **approved** models only: a model enters this map when its
#: ``approved_by`` is filled in (the record of Roger's word).
HF_MODEL_ALLOW_PATTERNS: dict[str, list[str]] = {m.hf_id: list(_ALLOW) for m in MODELS.values() if m.approved_by}

MPS_REFUSAL = ("MPS is not available in this process (inside the Claude Code Bash sandbox Metal sees no device); "
               "run outside the sandbox, or pass --device cpu")


def spec(key: str) -> ModelSpec:
    if key not in MODELS:
        raise KeyError(f"unknown model {key!r} (one of {', '.join(MODELS)})")
    return MODELS[key]


def parse_models(arg: str) -> list[str]:
    """``--models roberta,bert_wwm`` -> keys, validated."""
    keys = [k.strip() for k in str(arg).split(",") if k.strip()]
    for k in keys:
        spec(k)
    return keys


def model_missing(key: str) -> str:
    s = spec(key)
    who = f"approved: {s.approved_by}" if s.approved_by else "NOT approved yet: Roger's word first (plan section 1)"
    return (f"{s.hf_id} is not downloaded into data/external/hf: run `uv run python data_analysis/gap_generation/"
            f"setup_external.py --hf-model {s.hf_id}` first (~{s.approx_gb} GB, {who}); this command never downloads")


def model_present(key: str, cache_dir: Optional[Path] = None) -> bool:
    from assistant_axis.gapgen.embed import hf_snapshot_present
    return hf_snapshot_present(spec(key).hf_id, cache_dir)


def snapshot_path(key: str, cache_dir: Optional[Path] = None) -> Optional[Path]:
    """The newest snapshot directory of a model in the in-tree cache (None when absent)."""
    from assistant_axis.gapgen.embed import hf_snapshot_dir
    snaps = hf_snapshot_dir(spec(key).hf_id, cache_dir) / "snapshots"
    revs = sorted(p for p in snaps.iterdir() if p.is_dir()) if snaps.is_dir() else []
    return revs[-1] if revs else None


def resolve_device(device: str) -> str:
    """``mps`` (refused when Metal sees no device, as inside the sandbox), ``cpu``, or ``auto`` (MPS if there)."""
    import torch
    if device == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    if device == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError(MPS_REFUSAL)
    if device not in ("mps", "cpu"):
        raise ValueError(f"--device must be mps, cpu or auto, got {device!r}")
    return device


def loader_kwargs(key: str, cache_dir: Optional[Path] = None) -> dict:
    """The keyword arguments of every ``from_pretrained`` here: the in-tree cache, local files only, and no
    ``trust_remote_code`` (plan section 1: never)."""
    return {"cache_dir": str(cache_dir or hf_cache_dir()), "local_files_only": True}


# ---------------------------------------------------------------------------- tokenizers

_ASCII_ALPHA = re.compile(r"^[A-Za-z]+$")


class TokenizerAdapter:
    """One view of a Hugging Face tokenizer (see the module docstring).  Attributes the passes read:
    ``mask_token`` (the string a frame's slot becomes), ``mask_id``, ``pad_id``, ``vocab_size``, ``special_ids``,
    ``word_start`` (bool per id), ``piece_text`` (the piece without its marker), ``scheme``, ``key``, ``revision``."""

    def __init__(self, hf_tok, *, scheme: str, key: str, revision: Optional[str] = None,
                 vocab_size: Optional[int] = None):
        if scheme not in ("bpe", "wordpiece"):
            raise ValueError(f"unknown tokenizer scheme {scheme!r}")
        self.tok, self.scheme, self.key, self.revision = hf_tok, scheme, key, revision
        self.mask_token = hf_tok.mask_token
        self.mask_id = int(hf_tok.mask_token_id)
        self.pad_id = int(hf_tok.pad_token_id if hf_tok.pad_token_id is not None else 0)
        n = len(hf_tok)
        self.vocab_size = max(n, int(vocab_size or 0))
        pieces = hf_tok.convert_ids_to_tokens(list(range(n))) + [""] * (self.vocab_size - n)
        self.special_ids = set(int(i) for i in hf_tok.all_special_ids)
        self.pieces = pieces
        self.word_start = np.zeros(self.vocab_size, dtype=bool)
        self.piece_text: list[str] = []
        for i, p in enumerate(pieces):
            p = p or ""
            if scheme == "bpe":
                start = p.startswith("Ġ")
                text = p[1:] if start else p
            else:
                start = not p.startswith("##")
                text = p if start else p[2:]
            self.word_start[i] = start and i not in self.special_ids and bool(text)
            self.piece_text.append(text)

    # -- encoding ------------------------------------------------------------------------
    def encode(self, text: str) -> list[int]:
        """Token ids of a frame instance (special tokens added).  A bare leading-space piece the tokenizer leaves
        before a mask (a mask token without ``lstrip``) is dropped, so the slot predicts a word-start piece."""
        ids = list(self.tok(text, add_special_tokens=True)["input_ids"])
        return self._drop_space_before_mask(ids)

    def _drop_space_before_mask(self, ids: list[int]) -> list[int]:
        if self.scheme != "bpe":
            return ids
        out: list[int] = []
        for i, t in enumerate(ids):
            if i + 1 < len(ids) and ids[i + 1] == self.mask_id and self.pieces[t] == "Ġ":
                continue
            out.append(t)
        return out

    def encode_with_span(self, text: str, start: int, end: int) -> tuple[list[int], list[int]]:
        """Token ids of ``text`` and the positions of the tokens covering characters ``[start, end)``."""
        enc = self.tok(text, add_special_tokens=True, return_offsets_mapping=True)
        ids = list(enc["input_ids"])
        pos = [i for i, (a, b) in enumerate(enc["offset_mapping"])
               if b > a and a < end and b > start and (ids[i] not in self.special_ids or ids[i] == self.mask_id)]
        return ids, pos

    def word_ids(self, word: str) -> list[int]:
        """The word's tokens in sentence position (after a space; no special tokens)."""
        text = (" " + word) if self.scheme == "bpe" else word
        return list(self.tok(text, add_special_tokens=False)["input_ids"])

    def decode(self, ids: Sequence[int]) -> str:
        return self.tok.decode(list(ids), clean_up_tokenization_spaces=False)

    # -- pieces ------------------------------------------------------------------------
    def is_alpha_piece(self, i: int) -> bool:
        return i not in self.special_ids and bool(_ASCII_ALPHA.match(self.piece_text[i] or ""))

    def sha256(self) -> str:
        """A fingerprint of the vocabulary (what the cached word groups are keyed by)."""
        h = hashlib.sha256()
        h.update(self.scheme.encode())
        for p in self.pieces:
            h.update((p or "").encode("utf-8", "surrogatepass") + b"\0")
        return h.hexdigest()


def load_tokenizer(key: str, *, cache_dir: Optional[Path] = None) -> TokenizerAdapter:
    """The model's tokenizer from the in-tree cache (tokenizer files suffice).  Never downloads."""
    s = spec(key)
    pin_hf_cache()
    if not model_present(key, cache_dir):
        raise FileNotFoundError(model_missing(key))
    from transformers import AutoTokenizer
    hf_tok = AutoTokenizer.from_pretrained(s.hf_id, **loader_kwargs(key, cache_dir))
    snap = snapshot_path(key, cache_dir)
    return TokenizerAdapter(hf_tok, scheme=s.scheme, key=key, revision=snap.name if snap else None)


class HFMaskedLM:  # pragma: no cover - loads the real model; exercised by the GAPGEN_RUN_LOCAL smoke test
    """A fill-mask model on MPS or CPU, float32, loaded from the in-tree cache only."""

    def __init__(self, key: str = PRIMARY_MODEL, *, device: str = "mps", cache_dir: Optional[Path] = None,
                 batch_size: int = 64):
        import torch
        import transformers
        from transformers import AutoModelForMaskedLM
        transformers.logging.set_verbosity_error()        # the load report and the weight-loading progress bar
        try:
            transformers.utils.logging.disable_progress_bar()
        except AttributeError:
            pass
        s = spec(key)
        self.device = resolve_device(device)
        self.tok = load_tokenizer(key, cache_dir=cache_dir)
        self.model = AutoModelForMaskedLM.from_pretrained(s.hf_id, dtype=torch.float32,
                                                          **loader_kwargs(key, cache_dir)).to(self.device).eval()
        vocab = int(self.model.get_output_embeddings().weight.shape[0])
        if vocab != self.tok.vocab_size:
            self.tok = TokenizerAdapter(self.tok.tok, scheme=s.scheme, key=key, revision=self.tok.revision,
                                        vocab_size=vocab)
        self.key, self.model_id, self.batch_size = key, s.short, int(batch_size)
        self.revision = self.tok.revision
        self.n_forward = 0
        self._torch = torch

    def _batches(self, n: int):
        order = list(range(n))
        for i in range(0, n, self.batch_size):
            yield order[i:i + self.batch_size]

    def _logits_at(self, seqs: Sequence[Sequence[int]], positions: Sequence[int], idx: Sequence[int]):
        torch = self._torch
        width = max(len(seqs[i]) for i in idx)
        ids = torch.full((len(idx), width), self.tok.pad_id, dtype=torch.long)
        att = torch.zeros((len(idx), width), dtype=torch.long)
        for r, i in enumerate(idx):
            ids[r, :len(seqs[i])] = torch.tensor(list(seqs[i]), dtype=torch.long)
            att[r, :len(seqs[i])] = 1
        with torch.inference_mode():
            logits = self.model(input_ids=ids.to(self.device), attention_mask=att.to(self.device)).logits
            rows = logits[torch.arange(len(idx), device=self.device),
                          torch.tensor([positions[i] for i in idx], device=self.device)]
            lp = torch.log_softmax(rows.float(), dim=-1)
        self.n_forward += len(idx)
        return lp

    def logprobs_at(self, seqs: Sequence[Sequence[int]], positions: Sequence[int]) -> np.ndarray:
        """``(n, vocab)`` log-softmax at ``positions[i]`` of ``seqs[i]`` (float32)."""
        out = np.empty((len(seqs), self.tok.vocab_size), dtype=np.float32)
        for idx in self._batches(len(seqs)):
            out[idx] = self._logits_at(seqs, positions, idx).cpu().numpy()
        return out

    def target_logprobs(self, seqs: Sequence[Sequence[int]], positions: Sequence[int],
                        targets: Sequence[int]) -> np.ndarray:
        """``(n,)`` log-probability of ``targets[i]`` at ``positions[i]`` of ``seqs[i]``."""
        torch = self._torch
        out = np.empty(len(seqs), dtype=np.float32)
        for idx in self._batches(len(seqs)):
            lp = self._logits_at(seqs, positions, idx)
            t = torch.tensor([targets[i] for i in idx], device=self.device)
            out[idx] = lp[torch.arange(len(idx), device=self.device), t].cpu().numpy()
        return out


def load_mlm(key: str = PRIMARY_MODEL, device: str = "mps", *, cache_dir: Optional[Path] = None,
             batch_size: int = 64) -> HFMaskedLM:
    """The model, from the in-tree cache only (``FileNotFoundError`` naming the setup command when absent)."""
    if not model_present(key, cache_dir):
        raise FileNotFoundError(model_missing(key))
    return HFMaskedLM(key, device=device, cache_dir=cache_dir, batch_size=batch_size)


def runtime_versions() -> dict:
    import platform

    import torch
    import transformers
    return {"torch": torch.__version__, "transformers": transformers.__version__, "python": platform.python_version(),
            "machine": platform.machine()}


# ---------------------------------------------------------------------------- the census

CENSUS_CLASSES = ("single", "subword", "multiword")
_MULTI_RE = re.compile(r"[\s\-]")


@dataclass(frozen=True)
class CensusRow:
    label: str
    n_tokens: int
    klass: str                   # single | subword | multiword

    def as_dict(self) -> dict:
        return asdict(self)


def token_class(label: str, tokenizer) -> tuple[int, str]:
    """``(n_tokens, class)`` of a label in sentence position."""
    n = len(tokenizer.word_ids(label))
    if _MULTI_RE.search(label.strip()):
        return n, "multiword"
    return n, ("single" if n == 1 else "subword")


def token_census(labels: Iterable[str], tokenizer) -> list[CensusRow]:
    out = []
    for lab in labels:
        n, k = token_class(lab, tokenizer)
        out.append(CensusRow(label=lab, n_tokens=n, klass=k))
    return out


def census_summary(rows: Sequence[CensusRow]) -> dict:
    c = Counter(r.klass for r in rows)
    n = len(rows)
    return {"n": n, **{k: c.get(k, 0) for k in CENSUS_CLASSES},
            "shares": {k: round(c.get(k, 0) / n, 4) if n else None for k in CENSUS_CLASSES},
            "subword_examples": sorted(r.label for r in rows if r.klass == "subword")[:40]}


# ---------------------------------------------------------------------------- the download record

def _rel(path: Path) -> str:
    for p, root in ((Path(path), REPO_ROOT), (Path(path).resolve(), REPO_ROOT.resolve())):
        try:
            return str(p.relative_to(root))
        except ValueError:
            continue
    return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_model(key: str, *, approved_by: Optional[str] = None, cache_dir: Optional[Path] = None,
                 info_fn: Optional[Callable[[str, Optional[str]], dict]] = None, now: Optional[str] = None,
                 echo=print) -> dict:
    """Verify a downloaded snapshot against the Hub's published hashes and return its manifest entry.

    Each LFS file (the weights) is hashed here and compared with the published sha256 and with the pinned
    :attr:`ModelSpec.weights_sha256`; the other files carry their size and sha256.  The licence is read from the
    Hub's model card (``cardData.license``) and compared with the pinned one.  ``info_fn(model_id, revision)``
    returns ``{"sha", "license", "files": {name: {"size", "sha256"}}}`` (the base-model generator's
    ``hub_model_info``; a fake in tests)."""
    from assistant_axis.gapgen.registry import utc_now
    s = spec(key)
    snap = snapshot_path(key, cache_dir)
    if snap is None:
        raise FileNotFoundError(model_missing(key))
    if info_fn is None:  # pragma: no cover - network
        from ..base_model.download import hub_model_info as info_fn
    info = info_fn(s.hf_id, snap.name)
    files, bad, total = [], [], 0
    for p in sorted(snap.iterdir()):
        if not p.is_file():
            continue
        size = p.stat().st_size
        total += size
        sha = sha256_file(p)
        pub = (info.get("files") or {}).get(p.name) or {}
        rec = {"file": p.name, "size_bytes": size, "sha256": sha}
        if pub.get("sha256"):
            rec["sha256_published"] = pub["sha256"]
            rec["sha256_verified"] = sha == pub["sha256"]
            if not rec["sha256_verified"]:
                bad.append(p.name)
        if pub.get("size") is not None and pub["size"] != size:
            bad.append(p.name)
        files.append(rec)
    weights = next((f for f in files if f["file"] == "model.safetensors"), None)
    pinned_ok = bool(weights and weights["sha256"] == s.weights_sha256 and weights["size_bytes"] == s.weights_bytes)
    lic = str(info.get("license") or "")
    lic_ok = lic.lower() == s.licence.lower()
    entry = {"key": key, "model_id": s.hf_id, "revision": snap.name, "revision_pinned": s.revision,
             "revision_matches_pin": snap.name == s.revision, "dir": _rel(snap), "size_bytes": total,
             "weights_size_bytes": weights["size_bytes"] if weights else None,
             "weights_sha256": weights["sha256"] if weights else None,
             "weights_sha256_pinned": s.weights_sha256, "weights_match_pin": pinned_ok, "files": files,
             "checksum_verified": not bad and pinned_ok, "licence": s.licence, "licence_card": lic,
             "licence_url": s.licence_url, "licence_verified": lic_ok,
             "approved_by": approved_by or s.approved_by, "recorded_at": now or utc_now(),
             "tool": "setup_external.py --hf-model (download); masked_lm_generator.py record-model (record)",
             "todo": None if s.approx_gb < 2 else "TODO once the workstream is done: ask Roger whether to delete the "
                                                   "weights (his rule, 2026-10-10: anything over 2 GB gets this note)"}
    verdict = "verified (published and pinned)" if entry["checksum_verified"] else \
        "MISMATCHED: " + ", ".join(bad or ["pin"])
    echo(f"model {s.hf_id} @ {snap.name[:8]}: {len(files)} files, {total:,} bytes; weights "
         f"{entry['weights_size_bytes']:,} bytes sha256 {entry['weights_sha256']} {verdict}; "
         f"licence {lic or '?'} ({'confirmed' if lic_ok else '*** NOT CONFIRMED ***'})")
    return entry
