"""SpanMapper - Map token spans to activations and compute per-turn aggregates."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING
import torch

if TYPE_CHECKING:
    from .conversation import ConversationEncoder

logger = logging.getLogger(__name__)

# Search slack beyond the header's length when a SpanMapper is given header
# ids but no search distance (chat_layout.SEARCH_SLACK; 7 + 7 = 14 for Qwen3,
# the value the hand-written table had for "qwen").
_DEFAULT_SEARCH_SLACK = 7

# A header of at least this many tokens is accepted with one wrong token; a
# shorter one must match exactly (Roger, 2026-10-13: Gemma 2's three-token
# and OLMo 2's two-token headers, where one wrong token of two or three is
# no match).  The 8slot run's seven tokens keep the one-token tolerance.
EXACT_MATCH_BELOW = 4


def allowed_header_mismatches(n_header: int) -> int:
    """How many of an ``n_header``-token header may differ for
    ``_find_header`` to accept it: 1 from :data:`EXACT_MATCH_BELOW` tokens on,
    0 below."""
    return 1 if n_header >= EXACT_MATCH_BELOW else 0


class SpanMapper:
    """
    Maps token span indices to activations and computes per-turn aggregations.

    Handles:
    - Mapping spans to activation tensors
    - Excluding code blocks from aggregation
    - Computing mean activations per turn
    - Extracting per-token header activations for assistant turns

    The assistant-header token ids are injected (since the multi-model plan,
    reports/pipeline/coding_plan_multi_model_extraction.md § 5.4): step 2
    passes those :func:`assistant_axis.internals.chat_layout.derive_chat_layout`
    read off the model's chat template.  Until then they came from a table
    per family matched by a substring of the model name (``_HEADER_TOKENS``,
    ``_MAX_HEADER_SEARCH_DIST``, ``expected_assistant_header_ids``, gone).
    ``header_ids=None`` means body means only (``--no-headers``).
    """

    def __init__(self, tokenizer, *, header_ids: Optional[Sequence[int]] = None,
                 search_distance: Optional[int] = None):
        """
        Args:
            tokenizer: HuggingFace tokenizer (code-block detection, log lines)
            header_ids: the assistant header's token ids, in order; None for
                body means only
            search_distance: how far before a span's start ``_find_header``
                looks for the header's first token (default: the header's
                length + 7; ``ChatLayout.search_distance``)
        """
        self.tokenizer = tokenizer
        self.header_ids: Optional[List[int]] = (
            [int(i) for i in header_ids] if header_ids is not None else None)
        if self.header_ids is not None and not self.header_ids:
            raise ValueError("header_ids is empty; pass None for body means only")
        self.search_distance = search_distance

    def _max_dist(self, n_header: int) -> int:
        if self.search_distance is not None:
            return int(self.search_distance)
        return n_header + _DEFAULT_SEARCH_SLACK

    def _find_header(
        self,
        full_ids: List[int],
        span_start: int,
        expected_header: List[int],
    ) -> Tuple[Optional[int], List[Tuple[int, int, int]]]:
        """Search backwards from *span_start* for the assistant header.

        The nearest occurrence of the header's first token within the search
        distance is taken, and accepted when at most
        :func:`allowed_header_mismatches` of the N header tokens differ: one
        for N >= 4 (what the 8slot run used for N = 7, so Qwen3 is
        unchanged), none for a shorter header (Gemma 2's three tokens, OLMo
        2's two; built 2026-10-13, the multi-model plan § 5.4, on Roger's
        word: one wrong token of two or three is no match).

        Returns:
            (header_start_index, mismatches) where mismatches is a list of
            (position_in_header, expected_id, actual_id) tuples.
            *header_start_index* is None when no acceptable alignment was found.
        """
        N = len(expected_header)
        open_tag = expected_header[0]
        max_dist = self._max_dist(N)

        search_start = max(0, span_start - max_dist)
        candidate = None
        for i in range(span_start - 1, search_start - 1, -1):
            if full_ids[i] == open_tag:
                candidate = i
                break

        if candidate is None:
            return None, [(0, open_tag, -1)]

        mismatches = []
        matched = 0
        for k in range(N):
            idx = candidate + k
            if idx < 0 or idx >= len(full_ids):
                mismatches.append((k, expected_header[k], -1))
                continue
            if full_ids[idx] == expected_header[k]:
                matched += 1
            else:
                mismatches.append((k, expected_header[k], full_ids[idx]))

        if matched >= N - allowed_header_mismatches(N):
            return candidate, mismatches
        return None, mismatches

    def map_spans(
        self,
        batch_activations: torch.Tensor,
        batch_spans: List[Dict[str, Any]],
        batch_metadata: Dict[str, Any],
        batch_full_ids: Optional[List[List[int]]] = None,
        extract_headers: bool = True,
    ) -> Tuple[List[torch.Tensor], List[Dict[str, Any]], List[List[str]]]:
        """
        Map span indices to activations and compute per-turn mean activations.
        Optionally extracts individual header-token activations for assistant turns.
        Optimized for GPU computation with bf16 consistency.

        Args:
            batch_activations: (num_layers, batch_size, max_seq_len, hidden_size)
            batch_spans: span dicts with conversation_id and local indices
            batch_metadata: dict with batching information
            batch_full_ids: per-conversation token ID lists (needed for header extraction)
            extract_headers: if True, this mapper has ``header_ids`` and
                batch_full_ids is provided, extract header activations; slot 0 =
                body mean, slots 1..N = individual header tokens.

        Returns:
            (conversation_activations, mismatches, turn_roles) where each conv
            tensor is (1+N, num_turns, num_layers, hidden_size) when headers are
            extracted or (num_turns, num_layers, hidden_size) otherwise;
            mismatches is a list of dicts recording any header-token alignment
            issues; turn_roles[i] lists the role of each turn stacked for
            conversation i, in order (a span past the truncation length is
            dropped, so it can be shorter than the conversation's spans).
        """
        num_layers, batch_size, max_seq_len, hidden_size = batch_activations.shape
        device = batch_activations.device
        dtype = batch_activations.dtype  # Preserve bf16

        do_headers = (
            extract_headers
            and batch_full_ids is not None
            and self.header_ids is not None
        )
        header_ids: Optional[List[int]] = self.header_ids if do_headers else None
        N = len(header_ids) if header_ids is not None else 0

        all_mismatches: List[Dict[str, Any]] = []

        conversation_activations: List[Any] = [None] * batch_metadata['total_conversations']
        turn_roles: List[List[str]] = [[] for _ in range(batch_metadata['total_conversations'])]

        # Group spans by conversation
        spans_by_conversation: Dict[int, List[Dict[str, Any]]] = {}
        for span in batch_spans:
            conv_id = span['conversation_id']
            if conv_id not in spans_by_conversation:
                spans_by_conversation[conv_id] = []
            spans_by_conversation[conv_id].append(span)

        # Sort spans by turn within each conversation
        for conv_id in spans_by_conversation:
            spans_by_conversation[conv_id].sort(key=lambda x: x['turn'])

        # Extract per-turn activations for each conversation
        for conv_id in range(batch_metadata['total_conversations']):
            if conv_id not in spans_by_conversation:
                # Empty conversation - maintain dtype and device consistency
                if do_headers:
                    conversation_activations[conv_id] = torch.empty(
                        1 + N, 0, num_layers, hidden_size, dtype=dtype, device=device
                    )
                else:
                    conversation_activations[conv_id] = torch.empty(
                        0, num_layers, hidden_size, dtype=dtype, device=device
                    )
                continue

            spans = spans_by_conversation[conv_id]
            full_ids = batch_full_ids[conv_id] if batch_full_ids else None
            turn_activations = []

            for span in spans:
                # Use local indices since batch_activations[conv_id] corresponds to this conversation
                start_idx = span['start']  # Local start within the conversation
                end_idx = span['end']      # Local end within the conversation

                # Check bounds to handle truncation
                actual_length = batch_metadata['truncated_lengths'][conv_id]
                if start_idx >= actual_length:
                    # Span is beyond truncated length, skip
                    continue

                # Adjust end index if it exceeds actual length
                end_idx = min(end_idx, actual_length)

                if start_idx >= end_idx:
                    # Invalid span, skip
                    continue

                # Extract activations for this span from the conversation
                # batch_activations[:, conv_id, start_idx:end_idx, :] has shape (num_layers, span_length, hidden_size)
                span_activations = batch_activations[:, conv_id, start_idx:end_idx, :]

                # Compute mean across tokens in this span (optimized for GPU)
                span_length = span_activations.size(1)
                if span_length == 0:
                    continue
                if span_length == 1:
                    # Single token - avoid mean computation
                    mean_activation = span_activations.squeeze(1)  # (num_layers, hidden_size)
                else:
                    # Multi-token span - compute mean on GPU
                    mean_activation = span_activations.mean(dim=1)  # (num_layers, hidden_size)

                if do_headers:
                    slots = [mean_activation]

                    if span.get('role') == 'assistant' and full_ids is not None:
                        hdr_start, mm = self._find_header(
                            full_ids, start_idx, header_ids  # type: ignore[arg-type]
                        )
                        for pos_idx, exp_id, act_id in mm:
                            all_mismatches.append({
                                "conversation_id": conv_id,
                                "turn": span.get("turn"),
                                "position": pos_idx,
                                "expected": exp_id,
                                "actual": act_id,
                            })

                        if hdr_start is None and mm:
                            max_dist = self._max_dist(N)
                            w_start = max(0, start_idx - max_dist - 5)
                            w_end = min(len(full_ids), start_idx + 5)
                            window_ids = full_ids[w_start:w_end]
                            try:
                                window_toks = [
                                    self.tokenizer.convert_ids_to_tokens(t)
                                    for t in window_ids
                                ]
                            except Exception:
                                window_toks = ["?"] * len(window_ids)
                            marker = start_idx - w_start
                            logger.warning(
                                "HEADER NOT FOUND: conv=%d turn=%s "
                                "span_start=%d full_ids_len=%d "
                                "actual_length=%d search=[%d..%d)",
                                conv_id, span.get("turn"), start_idx,
                                len(full_ids), actual_length,
                                max(0, start_idx - max_dist), start_idx,
                            )
                            logger.warning(
                                "  ids[%d:%d]: %s  (^ = span_start at offset %d)",
                                w_start, w_end, window_ids, marker,
                            )
                            logger.warning(
                                "  tok[%d:%d]: %s",
                                w_start, w_end, window_toks,
                            )
                            logger.warning(
                                "  expected header ids: %s  span: %s",
                                header_ids, {k: span[k] for k in
                                             ('role', 'turn', 'start', 'end',
                                              'n_tokens', 'conversation_id')
                                             if k in span},
                            )

                        if hdr_start is not None:
                            for k in range(N):
                                tok_idx = hdr_start + k
                                if tok_idx < actual_length:
                                    tok_act = batch_activations[:, conv_id, tok_idx, :]
                                else:
                                    tok_act = torch.full(
                                        (num_layers, hidden_size),
                                        float("nan"), dtype=dtype, device=device,
                                    )
                                slots.append(tok_act)
                        else:
                            nan_slot = torch.full(
                                (num_layers, hidden_size),
                                float("nan"), dtype=dtype, device=device,
                            )
                            for _ in range(N):
                                slots.append(nan_slot)
                    else:
                        # Non-assistant turn: fill header slots with NaN
                        nan_slot = torch.full(
                            (num_layers, hidden_size),
                            float("nan"), dtype=dtype, device=device,
                        )
                        for _ in range(N):
                            slots.append(nan_slot)

                    turn_activations.append(torch.stack(slots))  # (1+N, layers, hidden)
                else:
                    turn_activations.append(mean_activation)
                turn_roles[conv_id].append(span.get('role'))

            if turn_activations:
                stacked = torch.stack(turn_activations)
                if do_headers:
                    # (turns, 1+N, layers, hidden) → (1+N, turns, layers, hidden)
                    stacked = stacked.permute(1, 0, 2, 3)
                conversation_activations[conv_id] = stacked
            else:
                # No valid activations - maintain dtype and device consistency
                if do_headers:
                    conversation_activations[conv_id] = torch.empty(
                        1 + N, 0, num_layers, hidden_size, dtype=dtype, device=device
                    )
                else:
                    conversation_activations[conv_id] = torch.empty(
                        0, num_layers, hidden_size, dtype=dtype, device=device
                    )

        return conversation_activations, all_mismatches, turn_roles

    def map_spans_no_code(
        self,
        batch_activations: torch.Tensor,
        batch_spans: List[Dict[str, Any]],
        batch_metadata: Dict[str, Any],
    ) -> Tuple[List[torch.Tensor], List[Dict[str, Any]]]:
        """
        Map span indices to activations, excluding code blocks. No header extraction.
        Optimized for GPU computation with bf16 consistency.

        Returns:
            (conversation_activations, []) -- mismatches list is always empty.
        """
        num_layers, batch_size, max_seq_len, hidden_size = batch_activations.shape
        device = batch_activations.device
        dtype = batch_activations.dtype  # Preserve bf16

        conversation_activations = [[] for _ in range(batch_metadata['total_conversations'])]

        # Group spans by conversation
        spans_by_conversation = {}
        for span in batch_spans:
            conv_id = span['conversation_id']
            if conv_id not in spans_by_conversation:
                spans_by_conversation[conv_id] = []
            spans_by_conversation[conv_id].append(span)

        # Sort spans by turn within each conversation
        for conv_id in spans_by_conversation:
            spans_by_conversation[conv_id].sort(key=lambda x: x['turn'])

        # Import ConversationEncoder here to avoid circular import
        from .conversation import ConversationEncoder
        encoder = ConversationEncoder(self.tokenizer)

        # Extract per-turn activations for each conversation
        for conv_id in range(batch_metadata['total_conversations']):
            if conv_id not in spans_by_conversation:
                # Empty conversation - maintain dtype and device consistency
                conversation_activations[conv_id] = torch.empty(0, num_layers, hidden_size, dtype=dtype, device=device)
                continue

            spans = spans_by_conversation[conv_id]
            turn_activations = []

            for span in spans:
                # Use local indices since batch_activations[conv_id] corresponds to this conversation
                start_idx = span['start']  # Local start within the conversation
                end_idx = span['end']      # Local end within the conversation

                # Check bounds to handle truncation
                actual_length = batch_metadata['truncated_lengths'][conv_id]
                if start_idx >= actual_length:
                    # Span is beyond truncated length, skip
                    continue

                # Adjust end index if it exceeds actual length
                end_idx = min(end_idx, actual_length)

                if start_idx >= end_idx:
                    # Invalid span, skip
                    continue

                # Extract activations for this span from the conversation
                # batch_activations[:, conv_id, start_idx:end_idx, :] has shape (num_layers, span_length, hidden_size)
                span_activations = batch_activations[:, conv_id, start_idx:end_idx, :]

                # Identify code block tokens to exclude from the mean
                text = span['text']
                exclude_mask = encoder.code_block_token_mask(text)

                # Handle case where the exclude mask might not match span length due to tokenization differences
                span_length = span_activations.size(1)
                if len(exclude_mask) != span_length:
                    # Resize exclude_mask to match actual span length
                    if len(exclude_mask) > span_length:
                        exclude_mask = exclude_mask[:span_length]
                    else:
                        # Pad with False if exclude_mask is shorter
                        padding = torch.zeros(span_length - len(exclude_mask), dtype=torch.bool)
                        exclude_mask = torch.cat([exclude_mask, padding])

                # Create include mask (invert of exclude mask)
                include_mask = ~exclude_mask

                # Compute mean across non-code tokens only
                if include_mask.any():
                    # Select only non-code tokens
                    included_activations = span_activations[:, include_mask, :]  # (num_layers, included_tokens, hidden_size)

                    if included_activations.size(1) == 1:
                        # Single token - avoid mean computation
                        mean_activation = included_activations.squeeze(1)  # (num_layers, hidden_size)
                    else:
                        # Multi-token span - compute mean on GPU for non-code tokens only
                        mean_activation = included_activations.mean(dim=1)  # (num_layers, hidden_size)
                    turn_activations.append(mean_activation)
                else:
                    # All tokens are code blocks - skip this turn
                    continue

            if turn_activations:
                # Stack to get (num_turns, num_layers, hidden_size)
                conversation_activations[conv_id] = torch.stack(turn_activations)
            else:
                # No valid activations for this conversation - maintain dtype and device consistency
                conversation_activations[conv_id] = torch.empty(0, num_layers, hidden_size, dtype=dtype, device=device)

        return conversation_activations, []

    def mean_all_turn_activations(
        self,
        probing_model,
        encoder: 'ConversationEncoder',
        conversation: List[Dict[str, str]],
        layer: int = 15,
        chat_format: bool = True,
        **chat_kwargs,
    ) -> torch.Tensor:
        """
        Get mean activations for all turns in a conversation using build_turn_spans and extract_full_activations.

        Args:
            probing_model: ProbingModel instance
            encoder: ConversationEncoder instance
            conversation: List of dict with 'role' and 'content' keys
            layer: Layer index to extract activations from (default 15)
            **chat_kwargs: additional arguments for apply_chat_template

        Returns:
            torch.Tensor: Mean activations of shape (num_turns, hidden_size) for all turns in chronological order
        """
        # Get turn spans for the conversation
        full_ids, spans = encoder.build_turn_spans(conversation, **chat_kwargs)

        # Import ActivationExtractor here to avoid circular import
        from .activations import ActivationExtractor
        extractor = ActivationExtractor(probing_model, encoder)

        # Extract full activations for the conversation
        activations = extractor.full_conversation(
            conversation, layer=layer, chat_format=chat_format, **chat_kwargs
        )

        # Handle the case where extract_full_activations returns multi-layer format
        if activations.ndim == 3:  # (num_layers, num_tokens, hidden_size)
            activations = activations[0]  # Take the first (and only) layer

        # Compute mean activation for each turn
        turn_mean_activations = []

        for span in spans:
            start_idx = span['start']
            end_idx = span['end']

            # Extract activations for this turn's tokens
            if start_idx < end_idx and end_idx <= activations.shape[0]:
                turn_activations = activations[start_idx:end_idx, :]  # (turn_tokens, hidden_size)
                mean_activation = turn_activations.mean(dim=0)  # (hidden_size,)
                turn_mean_activations.append(mean_activation)

        if not turn_mean_activations:
            # Return empty tensor with correct shape if no valid turns
            return torch.empty(0, activations.shape[1] if activations.ndim > 1 else 0)

        # Stack to get (num_turns, hidden_size)
        return torch.stack(turn_mean_activations)
