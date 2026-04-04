"""Tests for SpanMapper header extraction."""

import pytest
import torch

from assistant_axis.internals.spans import SpanMapper, _HEADER_TOKENS


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

class FakeTokenizer:
    """Minimal tokenizer stub sufficient for SpanMapper tests."""

    def __init__(self, vocab: dict[str, int], unk_id: int = 0):
        self._vocab = vocab
        self.unk_token_id = unk_id

    def convert_tokens_to_ids(self, token: str) -> int:
        return self._vocab.get(token, self.unk_token_id)

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        if text in self._vocab:
            return [self._vocab[text]]
        return [self.unk_token_id]


QWEN_VOCAB = {
    "<|im_start|>": 151644,
    "assistant": 77091,
    "\n": 198,
}
QWEN_HEADER = [151644, 77091, 198]

GEMMA_VOCAB = {
    "<start_of_turn>": 106,
    "model": 2516,
    "\n": 108,
}
GEMMA_HEADER = [106, 2516, 108]

LLAMA_VOCAB = {
    "<|start_header_id|>": 128006,
    "assistant": 78191,
    "<|end_header_id|>": 128007,
    "\n\n": 271,
}
LLAMA_HEADER = [128006, 78191, 128007, 271]


@pytest.fixture(params=[
    ("qwen3-0.6b", QWEN_VOCAB, QWEN_HEADER),
    ("gemma-2-27b", GEMMA_VOCAB, GEMMA_HEADER),
    ("llama-3.3-70b", LLAMA_VOCAB, LLAMA_HEADER),
], ids=["qwen", "gemma", "llama"])
def family_fixture(request):
    model_name, vocab, expected = request.param
    tok = FakeTokenizer(vocab)
    return model_name, tok, expected


# ---------------------------------------------------------------------------
# expected_assistant_header_ids
# ---------------------------------------------------------------------------

class TestExpectedAssistantHeaderIds:

    def test_returns_correct_ids(self, family_fixture):
        model_name, tok, expected = family_fixture
        sm = SpanMapper(tok, model_name=model_name)
        assert sm.expected_assistant_header_ids() == expected

    def test_raises_for_unknown_family(self):
        tok = FakeTokenizer({})
        sm = SpanMapper(tok, model_name="totally-unknown-model")
        with pytest.raises(ValueError, match="Unrecognized model family"):
            sm.expected_assistant_header_ids()


# ---------------------------------------------------------------------------
# _find_header
# ---------------------------------------------------------------------------

class TestFindHeader:

    def test_exact_match(self):
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        full_ids = [999, 151644, 77091, 198, 42, 43, 44]
        hdr_start, mm = sm._find_header(full_ids, span_start=4, expected_header=QWEN_HEADER)
        assert hdr_start == 1
        assert mm == []

    def test_total_mismatch_returns_none(self):
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        full_ids = [10, 20, 30, 40, 50, 60]
        hdr_start, mm = sm._find_header(full_ids, span_start=4, expected_header=QWEN_HEADER)
        assert hdr_start is None

    def test_qwen_thinking_gap(self):
        """Qwen with thinking disabled can have several tokens between the header
        and the content span start; the backward search should still find it."""
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        full_ids = [
            999,
            151644, 77091, 198,  # header at positions 1-3
            888, 889, 890,       # thinking tags / whitespace
            42, 43, 44,          # actual content starts at 7
        ]
        hdr_start, mm = sm._find_header(full_ids, span_start=7, expected_header=QWEN_HEADER)
        assert hdr_start == 1
        assert mm == []


# ---------------------------------------------------------------------------
# map_spans -- output shapes
# ---------------------------------------------------------------------------

def _make_batch(num_layers=2, hidden=4, seq_len=20, n_convs=1):
    """Create minimal batch_activations and metadata for testing."""
    acts = torch.randn(num_layers, n_convs, seq_len, hidden)
    metadata = {
        "total_conversations": n_convs,
        "truncated_lengths": [seq_len] * n_convs,
    }
    return acts, metadata


class TestMapSpansShape:

    def test_no_headers_3d(self):
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        acts, meta = _make_batch()
        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user",      "start": 0, "end": 5},
            {"conversation_id": 0, "turn": 1, "role": "assistant", "start": 8, "end": 15},
        ]
        full_ids = list(range(20))

        result, mm = sm.map_spans(acts, spans, meta, extract_headers=False)
        assert result[0].ndim == 3  # (num_turns, num_layers, hidden)
        assert result[0].shape == (2, 2, 4)
        assert mm == []

    def test_headers_4d(self):
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        acts, meta = _make_batch()
        header = QWEN_HEADER
        N = len(header)
        full_ids = [0] * 20
        full_ids[5] = header[0]
        full_ids[6] = header[1]
        full_ids[7] = header[2]

        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user",      "start": 0, "end": 5},
            {"conversation_id": 0, "turn": 1, "role": "assistant", "start": 8, "end": 15},
        ]
        result, mm = sm.map_spans(
            acts, spans, meta,
            batch_full_ids=[full_ids],
            extract_headers=True,
        )
        assert result[0].ndim == 4  # (1+N, turns, layers, hidden)
        assert result[0].shape == (1 + N, 2, 2, 4)

    def test_body_mean_recovery(self):
        """conv_acts[0] should equal the body-mean from no-header mode."""
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        acts, meta = _make_batch()

        header = QWEN_HEADER
        full_ids = [0] * 20
        full_ids[5] = header[0]
        full_ids[6] = header[1]
        full_ids[7] = header[2]

        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user",      "start": 0, "end": 5},
            {"conversation_id": 0, "turn": 1, "role": "assistant", "start": 8, "end": 15},
        ]

        with_hdr, _ = sm.map_spans(acts, spans, meta, batch_full_ids=[full_ids], extract_headers=True)
        without_hdr, _ = sm.map_spans(acts, spans, meta, extract_headers=False)

        body_from_4d = with_hdr[0][0]
        body_from_3d = without_hdr[0]
        assert torch.allclose(body_from_4d, body_from_3d)

    def test_user_turn_headers_are_nan(self):
        """Non-assistant turns should have NaN in header slots."""
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        acts, meta = _make_batch()
        full_ids = [0] * 20

        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user", "start": 0, "end": 5},
        ]
        result, _ = sm.map_spans(acts, spans, meta, batch_full_ids=[full_ids], extract_headers=True)
        header_slots = result[0][1:, 0, :, :]
        assert torch.isnan(header_slots).all()

    def test_failed_header_fills_nan(self):
        """When _find_header fails, header slots should be NaN."""
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        acts, meta = _make_batch()
        full_ids = [999] * 20  # no open tag anywhere

        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user",      "start": 0, "end": 5},
            {"conversation_id": 0, "turn": 1, "role": "assistant", "start": 8, "end": 15},
        ]
        result, mm = sm.map_spans(acts, spans, meta, batch_full_ids=[full_ids], extract_headers=True)
        header_slots = result[0][1:, 1, :, :]
        assert torch.isnan(header_slots).all()
        assert len(mm) > 0

    def test_empty_conversation(self):
        tok = FakeTokenizer(QWEN_VOCAB)
        sm = SpanMapper(tok, model_name="qwen3-0.6b")
        acts, meta = _make_batch(n_convs=2)
        full_ids_0 = [0] * 20
        full_ids_1 = [0] * 20

        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user", "start": 0, "end": 5},
        ]
        result, _ = sm.map_spans(
            acts, spans, meta,
            batch_full_ids=[full_ids_0, full_ids_1],
            extract_headers=True,
        )
        assert result[1].ndim == 4
        assert result[1].shape[1] == 0  # zero turns

    def test_gemma_header_length(self):
        tok = FakeTokenizer(GEMMA_VOCAB)
        sm = SpanMapper(tok, model_name="gemma-2-27b")
        acts, meta = _make_batch()
        header = GEMMA_HEADER
        N = len(header)
        full_ids = [0] * 20
        for i, h in enumerate(header):
            full_ids[5 + i] = h

        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user",      "start": 0, "end": 5},
            {"conversation_id": 0, "turn": 1, "role": "assistant", "start": 8, "end": 15},
        ]
        result, _ = sm.map_spans(acts, spans, meta, batch_full_ids=[full_ids], extract_headers=True)
        assert result[0].shape[0] == 1 + N

    def test_llama_header_length(self):
        tok = FakeTokenizer(LLAMA_VOCAB)
        sm = SpanMapper(tok, model_name="llama-3.3-70b")
        acts, meta = _make_batch()
        header = LLAMA_HEADER
        N = len(header)
        full_ids = [0] * 20
        for i, h in enumerate(header):
            full_ids[4 + i] = h

        spans = [
            {"conversation_id": 0, "turn": 0, "role": "user",      "start": 0, "end": 4},
            {"conversation_id": 0, "turn": 1, "role": "assistant", "start": 8, "end": 15},
        ]
        result, _ = sm.map_spans(acts, spans, meta, batch_full_ids=[full_ids], extract_headers=True)
        assert result[0].shape[0] == 1 + N
