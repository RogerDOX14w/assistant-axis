"""Fakes for the masked-LM generator's tests: a tokenizer with the Hugging Face call surface the adapter uses,
and a fill-mask model whose logits a test plants.  No network, no model load.

``FakeHFTokenizer`` (BPE flavour, like roberta): a leading-space word is the piece ``Ġword`` when the vocabulary
has it, else a greedy split into ``Ġ<prefix>`` and continuation pieces; a word with no leading space (the first
word, the word after a hyphen or a mask) uses pieces without ``Ġ``; ``<mask>`` absorbs the space before it
(roberta's ``lstrip``); offsets exclude the leading space.  The WordPiece flavour (like BERT) uses ``##``
continuation pieces and drops spaces.

``FakeMaskedLM.logprobs_at`` asks the test's ``scorer(pieces, position)`` for ``{piece: logit}`` (every other piece
gets ``base``) and returns the log-softmax.
"""
from __future__ import annotations

import re
from typing import Callable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.gapgen.generators.masked_lm.models import TokenizerAdapter

_BPE_RE = re.compile(r" ?<mask>|'[a-z]+| ?[A-Za-z]+| ?[^\sA-Za-z]")
_WP_RE = re.compile(r"\[MASK\]|'[a-z]+|[A-Za-z]+|[^\sA-Za-z]")


class FakeHFTokenizer:
    def __init__(self, vocab: Sequence[str], scheme: str = "bpe"):
        self.scheme = scheme
        if scheme == "bpe":
            specials = ["<s>", "<pad>", "</s>", "<unk>", "<mask>"]
            self.bos, self.eos, self.mask_token, unk = "<s>", "</s>", "<mask>", "<unk>"
        else:
            specials = ["[CLS]", "[PAD]", "[SEP]", "[UNK]", "[MASK]"]
            self.bos, self.eos, self.mask_token, unk = "[CLS]", "[SEP]", "[MASK]", "[UNK]"
        self.tokens = list(specials) + [v for v in vocab if v not in specials]
        self.ids = {t: i for i, t in enumerate(self.tokens)}
        self.mask_token_id = self.ids[self.mask_token]
        self.pad_token_id = self.ids[specials[1]]
        self.unk_id = self.ids[unk]
        self.all_special_ids = [self.ids[s] for s in specials]

    def __len__(self) -> int:
        return len(self.tokens)

    def convert_ids_to_tokens(self, ids):
        return [self.tokens[i] for i in ids]

    def _split(self, word: str, *, space: bool) -> list[str]:
        if self.scheme == "bpe":
            first = "Ġ" if space else ""
            if first + word in self.ids:
                return [first + word]
            out, rest, lead = [], word, first
            while rest:
                for j in range(len(rest), 0, -1):
                    cand = lead + rest[:j]
                    if cand in self.ids:
                        out.append(cand)
                        rest, lead = rest[j:], ""
                        break
                else:
                    return out + ["<unk>"]
            return out
        if word in self.ids:
            return [word]
        out, rest, lead = [], word, ""
        while rest:
            for j in range(len(rest), 0, -1):
                if lead + rest[:j] in self.ids:
                    out.append(lead + rest[:j])
                    rest, lead = rest[j:], "##"
                    break
            else:
                return out + ["[UNK]"]
        return out

    def _encode(self, text: str):
        pieces, offsets = [], []
        rx = _BPE_RE if self.scheme == "bpe" else _WP_RE
        for m in rx.finditer(text):
            chunk = m.group(0)
            a, b = m.start(), m.end()
            space = chunk.startswith(" ")
            body = chunk[1:] if space else chunk
            a2 = a + (1 if space else 0)
            if body in ("<mask>", "[MASK]"):
                pieces.append(self.mask_token)
                offsets.append((a2, b))
            elif body.isalpha():
                parts = self._split(body, space=space)
                pos = a2
                for p in parts:
                    n = len(p.replace("Ġ", "").replace("##", "")) if p not in ("<unk>", "[UNK]") else len(body)
                    pieces.append(p)
                    offsets.append((pos, min(b, pos + n)))
                    pos += n
            else:
                p = ("Ġ" + body) if (space and self.scheme == "bpe" and "Ġ" + body in self.ids) else body
                pieces.append(p if p in self.ids else (self.tokens[self.unk_id]))
                offsets.append((a2, b))
        return pieces, offsets

    def __call__(self, text: str, add_special_tokens: bool = True, return_offsets_mapping: bool = False):
        pieces, offsets = self._encode(text)
        ids = [self.ids.get(p, self.unk_id) for p in pieces]
        if add_special_tokens:
            ids = [self.ids[self.bos]] + ids + [self.ids[self.eos]]
            offsets = [(0, 0)] + offsets + [(0, 0)]
        out = {"input_ids": ids}
        if return_offsets_mapping:
            out["offset_mapping"] = offsets
        return out

    def decode(self, ids, clean_up_tokenization_spaces: bool = False) -> str:
        out = ""
        for i in ids:
            t = self.tokens[i]
            if i in self.all_special_ids:
                continue
            if self.scheme == "bpe":
                out += t.replace("Ġ", " ")
            else:
                out += t[2:] if t.startswith("##") else (" " + t)
        return out


def make_tokenizer(vocab: Sequence[str], scheme: str = "bpe", key: str = "roberta") -> TokenizerAdapter:
    return TokenizerAdapter(FakeHFTokenizer(vocab, scheme), scheme=scheme, key=key, revision="fake-rev")


Scorer = Callable[[list, int], Mapping[str, float]]


class FakeMaskedLM:
    """A fill-mask model with planted logits (see the module docstring)."""

    def __init__(self, tok: TokenizerAdapter, scorer: Scorer, *, key: str = "roberta", base: float = -8.0):
        self.tok, self.scorer, self.key, self.base = tok, scorer, key, base
        self.model_id, self.revision, self.device, self.batch_size = "fake-mlm", "fake-rev", "cpu", 8
        self.n_forward = 0
        self.calls: list[tuple[tuple[str, ...], int]] = []

    def _row(self, seq: Sequence[int], pos: int) -> np.ndarray:
        pieces = [self.tok.pieces[i] for i in seq]
        self.calls.append((tuple(pieces), pos))
        logits = np.full(self.tok.vocab_size, self.base, dtype=np.float64)
        for p, v in (self.scorer(pieces, pos) or {}).items():
            if p in self.tok.tok.ids:
                logits[self.tok.tok.ids[p]] = v
        logits -= logits.max()
        return (logits - np.log(np.exp(logits).sum())).astype(np.float32)

    def logprobs_at(self, seqs, positions) -> np.ndarray:
        self.n_forward += len(seqs)
        return np.stack([self._row(s, p) for s, p in zip(seqs, positions)]) if len(seqs) else \
            np.zeros((0, self.tok.vocab_size), dtype=np.float32)

    def target_logprobs(self, seqs, positions, targets) -> np.ndarray:
        lp = self.logprobs_at(seqs, positions)
        return np.asarray([lp[i, t] for i, t in enumerate(targets)], dtype=np.float32)


def identity_lemmatizer(lemmas: Optional[Mapping[str, str]] = None) -> Callable[[str], str]:
    m = dict(lemmas or {})
    return lambda w: m.get(w.lower(), w.lower())


# ---------------------------------------------------------------------------- a fake WordNet

class FakeSyn:
    def __init__(self, sid: str, lemmas: Sequence[str], definition: str, pos: str, hyponyms=()):
        self.id, self._lemmas, self._def, self.pos, self._hypo = sid, list(lemmas), definition, pos, list(hyponyms)

    def lemmas(self):
        return list(self._lemmas)

    def definition(self):
        return self._def

    def hyponyms(self):
        return list(self._hypo)


class FakeWord:
    def __init__(self, lemma: str, pos: str):
        self._l, self.pos = lemma, pos

    def lemma(self):
        return self._l


class FakeWordNet:
    """``words(pos=)`` and ``synsets(lemma, pos=)``: enough for ``wordlist.oewn_candidates``."""

    def __init__(self, adjectives: Sequence[str], synsets: Sequence[FakeSyn]):
        self.adj = list(adjectives)
        self.syns = list(synsets)

    def words(self, form=None, pos=None):
        if pos in ("a", "s"):
            return [FakeWord(a, "a") for a in self.adj] if pos == "a" else []
        return []

    def synsets(self, lemma, pos=None):
        return [s for s in self.syns if lemma in s.lemmas() and (pos is None or s.pos == pos)]


def fake_person_wordnet() -> FakeWordNet:
    leader = FakeSyn("n3", ["leader"], "a person who rules or guides or inspires others", "n")
    optimist = FakeSyn("n4", ["optimist"], "a person disposed to take a favorable view of things", "n")
    king = FakeSyn("n5", ["Henry IV"], "king of England", "n")
    person = FakeSyn("n1", ["person", "individual"], "a human being", "n", [king])
    actor = FakeSyn("n2", ["actor", "doer"], "a person who acts and gets things done", "n", [leader, optimist])
    other_person = FakeSyn("n9", ["person"], "a grammatical category", "n")
    return FakeWordNet(["kind", "Kantian", "risk-averse", "kind", "absent-minded", "a b c d e", "x2"],
                       [person, actor, other_person, leader, optimist, king])
