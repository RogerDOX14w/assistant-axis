"""The assistant-header layout, derived from the model's own chat template.

Step 2 stores, per response, slot 0 (the mean over the response's content
tokens) and one slot per *header* token: the tokens the template puts between
the end of the user turn (or of the stored reasoning) and the first token of
the assistant's content.  Until the multi-model plan
(reports/pipeline/coding_plan_multi_model_extraction.md § 5.1) the header was
a hand-written list per family, matched by a substring of the model name; it
is now read off the template at startup, so a new family costs a table row in
:mod:`assistant_axis.model_families` and Qwen3 derives exactly the seven
tokens of the 8slot tree.

:func:`derive_chat_layout` renders a probe conversation three ways with the
family's template kwargs and ``return_dict=False`` (transformers 5 returns a
``BatchEncoding`` otherwise):

1. ``base``: the probe (``[system, user]`` when the family takes a system
   prompt, ``[user]`` otherwise) without an assistant turn;
2. ``gen``: the same with ``add_generation_prompt=True``; the *generation
   prompt* is ``gen[len(base):]``;
3. ``full``: the probe plus an assistant turn with a sentinel content (and,
   for a family whose reasoning is stored, a sentinel ``thinking``).

The header is the slice of ``full`` from ``len(base)`` (or the end of the
stored reasoning's tokens) to the first content token.  It is read from the
stored rendering, not from the generation prompt, because step 2 computes on
the stored conversation; for gpt-oss the two differ (§ 5.1).  The
generation-prompt difference is the cross-check.  Every failed check raises
:class:`LayoutError` naming both sequences as decoded strings.

Imports nothing heavy (no torch); the package ``__init__`` of
``assistant_axis.internals`` does.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROBE_SYSTEM = "You are a pirate"
PROBE_USER = "What is law"
PROBE_CONTENT = "Arr matey"
PROBE_THINKING = "Law rules"

# _find_header searches this many tokens beyond the header's own length
# before the content (the 14 that spans._MAX_HEADER_SEARCH_DIST["qwen"] had for
# Qwen3's seven tokens; § 5.1).
SEARCH_SLACK = 7


class LayoutError(ValueError):
    """The chat template does not give a usable assistant-header layout."""


@dataclass(frozen=True)
class ChatLayout:
    """What step 2 needs to know about where the assistant's content starts.

    ``header_tokens`` are ``tokenizer.decode([id])`` per id (``"\\n"`` for
    198, ``"<|im_start|>"`` for 151644: the strings the 8slot metadata has;
    ``convert_ids_to_tokens`` would give ``"Ċ"``)."""

    header_ids: Tuple[int, ...]
    header_tokens: Tuple[str, ...]
    generation_prompt_ids: Tuple[int, ...]
    model_type: str
    template_kwargs: Dict[str, Any]
    probe: Tuple[Dict[str, str], ...]
    search_distance: int

    def metadata(self) -> Dict[str, Any]:
        """The layout keys step 2 writes into every activation file's
        metadata (lists, as the 8slot files have them)."""
        return {
            "header_tokens": list(self.header_tokens),
            "header_ids": list(self.header_ids),
            "model_type": self.model_type,
            "template_kwargs": dict(self.template_kwargs),
            "generation_prompt_ids": list(self.generation_prompt_ids),
        }


def chat_ids(tokenizer, messages: Sequence[Dict[str, Any]], *, add_generation_prompt: bool,
             template_kwargs: Optional[Dict[str, Any]] = None) -> List[int]:
    """Token ids of ``messages`` under the tokenizer's chat template, a flat
    list of ints (``return_dict=False``; a mapping is unwrapped)."""
    ids = tokenizer.apply_chat_template(
        list(messages), tokenize=True, add_generation_prompt=add_generation_prompt,
        return_dict=False, **dict(template_kwargs or {}))
    if hasattr(ids, "keys"):
        ids = ids["input_ids"]
    return [int(i) for i in ids]


def _plain_ids(tokenizer, text: str) -> List[int]:
    enc = tokenizer(text, add_special_tokens=False)
    ids = enc["input_ids"] if hasattr(enc, "keys") else enc.input_ids
    return [int(i) for i in ids]


def _occurrences(hay: Sequence[int], needle: Sequence[int], start: int = 0) -> List[int]:
    n = len(needle)
    if not n:
        return []
    return [i for i in range(start, len(hay) - n + 1) if list(hay[i:i + n]) == list(needle)]


def _decode(tokenizer, ids: Sequence[int]) -> str:
    return tokenizer.decode(list(ids))


def _derive_once(tokenizer, family, probe: List[Dict[str, Any]], content: str,
                 thinking: str) -> Tuple[List[int], List[int], List[int]]:
    """(header_ids, generation_prompt_ids, full_ids) for one probe."""
    kwargs = dict(family.template_kwargs)
    base = chat_ids(tokenizer, probe, add_generation_prompt=False, template_kwargs=kwargs)
    gen = chat_ids(tokenizer, probe, add_generation_prompt=True, template_kwargs=kwargs)
    if gen[:len(base)] != base:
        raise LayoutError(
            f"{family.model_type}: the generation-prompt rendering does not start with the "
            f"rendering without it: {_decode(tokenizer, gen)!r} vs {_decode(tokenizer, base)!r}")
    gen_prompt = gen[len(base):]
    if not gen_prompt:
        raise LayoutError(f"{family.model_type}: add_generation_prompt=True adds nothing to "
                          f"{_decode(tokenizer, base)!r}")

    turn: Dict[str, Any] = {"role": "assistant", "content": content}
    if family.reasoning_stored:
        turn["thinking"] = thinking
    full = chat_ids(tokenizer, probe + [turn], add_generation_prompt=False,
                    template_kwargs=kwargs)
    if full[:len(base)] != base:
        raise LayoutError(
            f"{family.model_type}: the rendering with the assistant turn does not start with "
            f"the rendering without it: {_decode(tokenizer, full)!r} vs "
            f"{_decode(tokenizer, base)!r}")
    stored = full[len(base):]
    if stored[:len(gen_prompt)] != gen_prompt:
        raise LayoutError(
            f"{family.model_type}: the generation prompt {_decode(tokenizer, gen_prompt)!r} is "
            f"not a prefix of the stored assistant turn {_decode(tokenizer, stored)!r}: step 2 "
            f"would compute on a context step 1 never sent")

    start = len(base)
    if family.reasoning_stored:
        t_ids = _plain_ids(tokenizer, thinking)
        hits = _occurrences(full, t_ids, start)
        if len(hits) != 1:
            raise LayoutError(
                f"{family.model_type}: the probe's thinking {thinking!r} "
                f"({len(hits)} times) is not found exactly once in the stored turn "
                f"{_decode(tokenizer, stored)!r}")
        start = hits[0] + len(t_ids)
    c_ids = _plain_ids(tokenizer, content)
    hits = _occurrences(full, c_ids, start)
    if len(hits) != 1:
        raise LayoutError(
            f"{family.model_type}: the probe's content {content!r} ({len(hits)} times) is not "
            f"found exactly once in the stored turn {_decode(tokenizer, stored)!r} (its tokens "
            f"alone: {c_ids}); a template that merges the content with the header token "
            f"before it")
    header = full[start:hits[0]]
    if not header:
        raise LayoutError(f"{family.model_type}: no header tokens before the content in "
                          f"{_decode(tokenizer, stored)!r}")
    if set(header) & set(c_ids):
        raise LayoutError(f"{family.model_type}: the header {_decode(tokenizer, header)!r} "
                          f"contains a content token")
    return header, gen_prompt, full


def derive_chat_layout(tokenizer, family, *, probe_system: str = PROBE_SYSTEM,
                       probe_user: str = PROBE_USER, probe_content: str = PROBE_CONTENT,
                       probe_thinking: str = PROBE_THINKING) -> ChatLayout:
    """The header layout of ``tokenizer``'s chat template under ``family``'s
    row (an :class:`assistant_axis.model_families.FamilySpec`).

    Raises :class:`LayoutError` when the generation prompt is not a prefix of
    the stored assistant turn, when the header is empty or holds a content
    token, when the header differs with and without a system message, or when
    the row's ``expected_header_tokens`` are set and differ from the derived
    tokens.  The probe texts start and end with a letter, so that no
    whitespace merges across a boundary."""
    user = {"role": "user", "content": probe_user}
    with_system = family.system_prompt == "native"
    probe = ([{"role": "system", "content": probe_system}] if with_system else []) + [user]
    header, gen_prompt, _ = _derive_once(tokenizer, family, probe, probe_content, probe_thinking)
    if with_system:
        header_u, _, _ = _derive_once(tokenizer, family, [user], probe_content, probe_thinking)
        if header_u != header:
            raise LayoutError(
                f"{family.model_type}: the assistant header differs with a system message "
                f"({_decode(tokenizer, header)!r}) and without ({_decode(tokenizer, header_u)!r})")

    tokens = tuple(tokenizer.decode([i]) for i in header)
    expected = family.expected_header_tokens
    if expected is not None and tuple(expected) != tokens:
        raise LayoutError(
            f"{family.model_type}: the template derives the header {list(tokens)!r} "
            f"({len(tokens)} tokens), but the family row expects {list(expected)!r} "
            f"({len(expected)}); a different template (another row) or a changed tokenizer")
    return ChatLayout(
        header_ids=tuple(header),
        header_tokens=tokens,
        generation_prompt_ids=tuple(gen_prompt),
        model_type=family.model_type,
        template_kwargs=dict(family.template_kwargs),
        probe=tuple(dict(m) for m in probe),
        search_distance=len(header) + SEARCH_SLACK,
    )
