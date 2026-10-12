"""The additive response-record fields of walk-through P6 (2026-10-12):
``question_id``, ``finish_reason``, ``thinking_stripped``,
``thinking_suspected``.  vLLM is faked: ``llm.generate`` returns objects
shaped like vLLM's RequestOutput (``.outputs[0].text`` / ``.finish_reason``).
Steps 2 and 3 reading such records is tested in
pipeline/tests/test_response_fields_readers.py."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from assistant_axis import generation as g


class FakeTokenizer:
    def apply_chat_template(self, conv, tokenize=False, add_generation_prompt=True, **kw):
        return "|".join(m["content"] for m in conv) + ("<gen>" if add_generation_prompt else "")


class FakeLLM:
    """Answers each prompt from ``replies`` (by the user question it
    contains), with a finish reason."""

    def __init__(self, replies):
        self.replies = replies

    def get_tokenizer(self):
        return FakeTokenizer()

    def generate(self, prompts, sampling_params):
        out = []
        for p in prompts:
            q = p.split("|")[-1].replace("<gen>", "")
            text, reason = self.replies[q]
            out.append(SimpleNamespace(outputs=[SimpleNamespace(text=text, finish_reason=reason)]))
        return out


def _generator(replies, model="Qwen/Qwen3-32B"):
    gen = g.VLLMGenerator(model)
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
    gen = _generator({"q": ("x </think> y", "stop")}, model="google/gemma-2-27b-it")
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
