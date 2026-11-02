"""The additive response-record fields of walk-through P6 (2026-10-12):
``question_id``, ``finish_reason``, ``thinking_stripped``,
``thinking_suspected``.  vLLM is faked: ``llm.generate`` returns objects
shaped like vLLM's RequestOutput (``.outputs[0].text`` / ``.finish_reason``).
Steps 2 and 3 reading such records is tested in
pipeline/tests/test_response_fields_readers.py.

Since the multi-model plan (2026-10-13) step 1 hands vLLM token ids
(``{"prompt_token_ids": [...]}``) and the family row decides the clean-up:
the fakes tokenize to character codes and the generator is given its row
(harness only; no assertion changed).

Since the response-token-ids plan (2026-11-02,
reports/pipeline/response_token_ids/plan.md § 4.5) the fake vLLM's outputs
carry ``token_ids`` too, and the fake tokenizer decodes them: an id below
0x110000 is that character, :data:`THINK_END` is ``</think>`` (one id, not
special, as in Qwen3), :data:`STOP` and :data:`SPECIAL` are special tokens
(dropped by ``skip_special_tokens``), and ``BYTE + b`` is the raw byte ``b``,
so that a character can be split across ids (the cap landing inside it).  The
existing tests' replies get the ids of their text plus the stop token
(harness only; no assertion changed)."""
from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import pytest

from assistant_axis import generation as g
from assistant_axis.model_families import FAMILIES

THINK_END = 0x110000      # "</think>": one id, an added token that is not special
STOP = 0x110001           # "<|im_end|>", special: the stop token
SPECIAL = 0x110002        # "<|box_start|>", special: one the model might sample mid-response
BYTE = 0x120000           # BYTE + b: the raw byte b
_NAMES = {THINK_END: "</think>", STOP: "<|im_end|>", SPECIAL: "<|box_start|>"}


def ids_of(text: str):
    """The fake's ids for ``text``: one per character, ``</think>`` as one id."""
    out = []
    for i, part in enumerate(text.split("</think>")):
        if i:
            out.append(THINK_END)
        out.extend(ord(c) for c in part)
    return out


def bytes_of(char: str):
    """``char`` as one id per UTF-8 byte (a character the cap can cut)."""
    return [BYTE + b for b in char.encode("utf-8")]


class FakeTokenizer:
    all_special_ids = [STOP, SPECIAL]

    def apply_chat_template(self, conv, tokenize=False, add_generation_prompt=True, **kw):
        text = "|".join(m["content"] for m in conv) + ("<gen>" if add_generation_prompt else "")
        return [ord(c) for c in text] if tokenize else text

    def convert_tokens_to_ids(self, token):
        return {v: k for k, v in _NAMES.items()}.get(token, 0)

    def decode(self, ids, skip_special_tokens=False, **kw):
        out = bytearray()
        for i in ids:
            if i in self.all_special_ids and skip_special_tokens:
                continue
            if i in _NAMES:
                out += _NAMES[i].encode("utf-8")
            elif i >= BYTE:
                out.append(i - BYTE)
            else:
                out += chr(i).encode("utf-8")
        return out.decode("utf-8", errors="replace")


class FakeLLM:
    """Answers each prompt from ``replies`` (by the user question it
    contains), with a finish reason, and the ids: given as a third element
    (a tuple, as vLLM may hand them), or else the text's ids plus the stop
    token when the reason is ``"stop"``."""

    def __init__(self, replies):
        self.replies = replies

    def get_tokenizer(self):
        return FakeTokenizer()

    def generate(self, prompts, sampling_params):
        out = []
        for p in prompts:
            text = "".join(chr(i) for i in p["prompt_token_ids"])
            q = text.split("|")[-1].replace("<gen>", "")
            text, reason, *ids = self.replies[q]
            ids = tuple(ids[0]) if ids else tuple(ids_of(text) + ([STOP] if reason == "stop" else []))
            out.append(SimpleNamespace(outputs=[SimpleNamespace(text=text, finish_reason=reason,
                                                                token_ids=ids)]))
        return out


def _generator(replies, model="Qwen/Qwen3-32B", family="qwen3"):
    gen = g.VLLMGenerator(model, family=FAMILIES[family])
    gen.llm = FakeLLM(replies)
    gen.sampling_params = object()
    return gen


def test_records_carry_the_four_new_fields(monkeypatch):
    monkeypatch.setattr(g, "supports_system_prompt", lambda tok: True)
    replies = {
        "q0": ("A plain answer.", "stop"),
        "q3": ("Okay, so the user is asking about tides. Let me break this down.\n"
               "</think>\nTides come from the moon.", "stop"),
        "q6": ("Okay, so the user is asking about stars. I should explain fusion and " * 3, "length"),
    }
    gen = _generator(replies)
    res = gen.generate_for_role(["You are a sailor."], ["q0", "q3", "q6"],
                                question_ids=[0, 3, 6])
    by_q = {r["question"]: r for r in res}
    assert [r["question_index"] for r in res] == [0, 1, 2]        # positions, as before
    assert [r["question_id"] for r in res] == [0, 3, 6]           # the file's ids
    assert by_q["q0"]["finish_reason"] == "stop" and by_q["q6"]["finish_reason"] == "length"
    assert by_q["q3"]["thinking_stripped"] is True
    assert by_q["q3"]["conversation"][-1]["content"] == "Tides come from the moon."
    assert by_q["q3"]["thinking_suspected"] is False              # the strip removed it
    assert by_q["q6"]["thinking_suspected"] is True and by_q["q6"]["thinking_stripped"] is False
    assert by_q["q0"]["thinking_suspected"] is False
    # the keys written before 2026-10-12 are unchanged and come first
    assert list(res[0])[:5] == ["system_prompt", "prompt_index", "question_index", "question",
                                "conversation"]


def test_generate_batch_still_returns_texts():
    gen = _generator({"q": ("Answer.", "stop")})
    assert gen.generate_batch([[{"role": "user", "content": "q"}]]) == ["Answer."]


def test_no_strip_and_no_cleanup_for_other_families():
    gen = _generator({"q": ("x </think> y", "stop")}, model="google/gemma-2-27b-it",
                     family="gemma2")
    [d] = gen.generate_batch_detailed([[{"role": "user", "content": "q"}]])
    assert d["text"] == "x </think> y" and d["thinking_stripped"] is False


def test_question_ids_must_match_the_questions():
    gen = _generator({"q": ("a", "stop")})
    with pytest.raises(ValueError):
        gen.generate_for_role(["i"], ["q"], question_ids=[1, 2])


def test_question_ids_come_from_the_file_after_the_reduction(tmp_path):
    (tmp_path / "q.jsonl").write_text(
        "".join(json.dumps({"id": 100 + i, "question": f"q{i}"}) + "\n" for i in range(10)))
    rg = g.RoleResponseGenerator(model_name="fake/model", roles_dir=str(tmp_path),
                                 output_dir=str(tmp_path / "out"),
                                 questions_file=str(tmp_path / "q.jsonl"), short_name="F",
                                 question_count=7, reduce_questions=3)
    assert rg.load_questions() == ["q0", "q3", "q6"]
    assert rg.question_ids == [100, 103, 106]


@pytest.mark.parametrize("text, expected", [
    ("Okay, so the user is asking how to give feedback. Hmm.", True),
    ("Alright, the user's question is about tides.", True),
    ("To evaluate the user's question on energy efficiency, we must consider", True),
    ("Hmm... let me think. As a wanderer I have seen a lot.", False),    # in character
    ("Okay, so you're asking how to respond to your pet sitter.", False),
    ("The user interface of the app is simple.", False),               # not the conversation
    ("x" * 700 + " the user is asking", False),                         # beyond the window
])
def test_the_leaked_thinking_heuristic(text, expected):
    assert g.looks_like_leaked_thinking(text) is expected


# ---------------------------------------------------------------------------
# The generated ids (the response-token-ids plan, 2026-11-02, § 4.1 and § 4.5)
# ---------------------------------------------------------------------------

def _old_record(content, *, finish_reason="stop", thinking_stripped=False, question="q0"):
    """What the code before 2026-11-02 wrote for the one response of
    :func:`_one`, key by key, in order."""
    return {"system_prompt": "You are a sailor.", "prompt_index": 0, "question_index": 0,
            "question": question,
            "conversation": [{"role": "system", "content": "You are a sailor."},
                             {"role": "user", "content": question},
                             {"role": "assistant", "content": content}],
            "question_id": 7, "finish_reason": finish_reason,
            "thinking_stripped": thinking_stripped, "thinking_suspected": False}


def _one(monkeypatch, reply, family="qwen3"):
    monkeypatch.setattr(g, "supports_system_prompt", lambda tok: True)
    gen = _generator({"q0": reply}, family=family)
    [rec] = gen.generate_for_role(["You are a sailor."], ["q0"], question_ids=[7])
    return rec


def test_the_ids_are_stored_verbatim_after_the_existing_keys(monkeypatch):
    ids = ids_of("Tides come from the moon.") + [STOP]
    rec = _one(monkeypatch, ("Tides come from the moon.", "stop", ids))
    old = _old_record("Tides come from the moon.")
    assert list(rec)[:len(old)] == list(old)                 # the old keys first, in order
    assert {k: rec[k] for k in old} == old                   # with the values they had
    assert list(rec)[len(old):] == ["response_token_ids"]
    assert rec["response_token_ids"] == ids                  # the stop token included
    assert type(rec["response_token_ids"]) is list           # vLLM's tuple, as a list of ints
    assert all(type(i) is int for i in rec["response_token_ids"])
    json.dumps(rec)


def test_a_stripped_response_keeps_the_text_before_the_strip(monkeypatch):
    raw = "Okay, so the user is asking about tides.\n</think>\n\nTides come from the moon."
    rec = _one(monkeypatch, (raw, "stop"))
    old = _old_record("Tides come from the moon.", thinking_stripped=True)
    assert {k: rec[k] for k in old} == old                   # content stripped as before
    assert rec["raw_text"] == raw
    assert rec["response_token_ids"] == ids_of(raw) + [STOP] # the plan is in the ids
    assert list(rec)[len(old):] == ["response_token_ids", "raw_text"]


def test_no_raw_text_when_nothing_was_stripped(monkeypatch):
    rec = _one(monkeypatch, ("x </think> y", "stop"), family="gemma2")
    assert rec["conversation"][-1]["content"] == "x </think> y"
    assert "raw_text" not in rec and rec["thinking_stripped"] is False
