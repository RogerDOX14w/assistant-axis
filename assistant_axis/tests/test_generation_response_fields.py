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
(harness only; no assertion changed).

Since the surgical strip (Roger, 2026-11-03) ``"\\n\\n"`` is one id too,
:data:`NL2`, as in Qwen3's vocabulary, because step 1's cut is "the token
after ``</think>`` decodes to exactly ``\\n\\n``"; :func:`ids_of` writes every
``"\\n\\n"`` that way, left to right.  :data:`NL3` (``"\\n\\n\\n"`` as one
token) is only ever given explicitly."""
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
NL2 = 0x110003            # "\n\n": one id, as in Qwen3's vocabulary
NL3 = 0x110004            # "\n\n\n": one id (given explicitly only)
BYTE = 0x120000           # BYTE + b: the raw byte b
_NAMES = {THINK_END: "</think>", STOP: "<|im_end|>", SPECIAL: "<|box_start|>",
          NL2: "\n\n", NL3: "\n\n\n"}


def ids_of(text: str):
    """The fake's ids for ``text``: one per character, ``</think>`` and each
    ``"\\n\\n"`` (left to right) as one id."""
    out = []
    for i, part in enumerate(text.split("</think>")):
        if i:
            out.append(THINK_END)
        j = 0
        while j < len(part):
            if part.startswith("\n\n", j):
                out.append(NL2)
                j += 2
            else:
                out.append(ord(part[j]))
                j += 1
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
            if not ids:
                ids = [ids_of(text) + ([STOP] if reason == "stop" else [])]
            ids = tuple(ids[0])
            out.append(SimpleNamespace(outputs=[SimpleNamespace(text=text, finish_reason=reason,
                                                                token_ids=ids)]))
        return out


def _generator(replies, model="Qwen/Qwen3-32B", family="qwen3", **kw):
    gen = g.VLLMGenerator(model, family=FAMILIES[family], **kw)
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
    # Flagged expectation change (Roger, 2026-11-03, the surgical strip): the
    # one "\n" after this reply's </think> is not the "\n\n" the strip cuts,
    # so it stays; the old .strip() removed it ("Tides come from the moon.").
    assert by_q["q3"]["conversation"][-1]["content"] == "\nTides come from the moon."
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


def _one(monkeypatch, reply, family="qwen3", **gen_kw):
    monkeypatch.setattr(g, "supports_system_prompt", lambda tok: True)
    gen = _generator({"q0": reply}, family=family, **gen_kw)
    [rec] = gen.generate_for_role(["You are a sailor."], ["q0"], question_ids=[7])
    return rec


def test_the_ids_are_stored_verbatim_after_the_existing_keys(monkeypatch):
    ids = ids_of("Tides come from the moon.") + [STOP]
    rec = _one(monkeypatch, ("Tides come from the moon.", "stop", ids))
    old = _old_record("Tides come from the moon.")
    assert list(rec)[:len(old)] == list(old)                 # the old keys first, in order
    assert {k: rec[k] for k in old} == old                   # with the values they had
    assert list(rec)[len(old):] == ["response_token_ids", "content_token_range",
                                    "thinking_token_range"]
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
    assert list(rec)[len(old):] == ["response_token_ids", "content_token_range",
                                    "thinking_token_range", "raw_text"]


def test_no_raw_text_when_nothing_was_stripped(monkeypatch):
    rec = _one(monkeypatch, ("x </think> y", "stop"), family="gemma2")
    assert rec["conversation"][-1]["content"] == "x </think> y"
    assert "raw_text" not in rec and rec["thinking_stripped"] is False
    # Another family's rule detects nothing: no plan range, the content from 0.
    assert rec["thinking_token_range"] is None
    assert rec["content_token_range"] == [0, len(ids_of("x </think> y"))]


# ---------------------------------------------------------------------------
# The two ranges (§ 4.2), through generate_for_role (§ 4.5 items 2 to 6)
# ---------------------------------------------------------------------------

def _decoded(ids, r):
    return FakeTokenizer().decode(ids[r[0]:r[1]], skip_special_tokens=True)


def test_a_clean_response_points_at_everything_but_the_stop_token(monkeypatch, caplog):
    text = "Tides come from the moon."
    with caplog.at_level(logging.INFO):
        rec = _one(monkeypatch, (text, "stop"))
    ids = rec["response_token_ids"]
    assert ids[-1] == STOP
    assert rec["content_token_range"] == [0, len(ids) - 1]
    assert _decoded(ids, rec["content_token_range"]) == rec["conversation"][-1]["content"]
    assert rec["thinking_token_range"] is None
    assert "1 of 1 responses: the stored ids decode to the stored text" in caplog.text


def test_a_stripped_response_points_past_the_plan(monkeypatch, caplog):
    # Flagged expectation change (Roger, 2026-11-03, the surgical strip): the
    # strip cuts the plan, its last </think> and the "\n\n" after it, and
    # keeps the model's own whitespace at the ends (the old .strip() made the
    # content "Tides come from the moon."); the thinking range ends after the
    # "\n\n" and the content range starts there, so the two partition the
    # ids, and the check is plain equality.
    raw = "Plan: be brief. </think> Not yet. </think>\n\n Tides come from the moon. \n"
    with caplog.at_level(logging.WARNING):
        rec = _one(monkeypatch, (raw, "stop"))
    ids = rec["response_token_ids"]
    k = len(ids) - ids[::-1].index(THINK_END)                # the index after the last </think>
    assert ids[k] == NL2
    assert rec["thinking_stripped"] is True and rec["raw_text"] == raw
    assert rec["thinking_token_range"] == [0, k + 1]
    start, end = rec["content_token_range"]
    assert start == k + 1 and end == len(ids) - 1             # nothing between the two ranges
    content = rec["conversation"][-1]["content"]
    assert content == " Tides come from the moon. \n"
    assert _decoded(ids, [start, end]) == content
    assert ("Stripped orphaned thinking content from 1/1 responses (vLLM/Qwen thinking leak); "
            "1 of them still begin or end with whitespace, which is kept") in caplog.text


def test_the_strip_takes_one_double_newline_and_nothing_else():
    # The rule on its own (Roger, 2026-11-03).
    assert g.strip_leaked_plan("plan</think>\n\nAnswer.") == "Answer."
    assert g.strip_leaked_plan("plan</think>\n\n\nAnswer.") == "\nAnswer."   # the third stays
    assert g.strip_leaked_plan("plan</think>\nAnswer.") == "\nAnswer."       # one newline stays
    assert g.strip_leaked_plan("plan</think> Answer. \n") == " Answer. \n"
    assert g.strip_leaked_plan("a</think>b</think>\n\nAnswer.") == "Answer."  # the last </think>
    assert g.strip_leaked_plan("plan</think>") == ""
    assert g.strip_leaked_plan("plan</think>\n\n") == ""


def test_a_third_newline_after_the_plan_is_kept_and_pointed_at(monkeypatch, caplog):
    # "</think>\n\n\n" written as the "\n\n" token and a "\n": the strip takes
    # the first two, the range starts at the third.
    raw = "Plan.</think>\n\n\nTides."
    with caplog.at_level(logging.WARNING):
        rec = _one(monkeypatch, (raw, "stop"))
    ids = rec["response_token_ids"]
    assert ids[6:8] == [NL2, ord("\n")]
    assert rec["conversation"][-1]["content"] == "\nTides."
    assert rec["thinking_token_range"] == [0, 7]
    assert rec["content_token_range"] == [7, len(ids) - 1]
    assert _decoded(ids, rec["content_token_range"]) == "\nTides."
    assert "1 of them still begin or end with whitespace" in caplog.text


def test_three_newlines_as_one_token_after_the_plan_get_a_null_range(monkeypatch, caplog):
    # Accepted by Roger (2026-11-03): the text rule takes two characters of a
    # three-character token, so no token boundary is behind the stored text;
    # the range is null and counted, and step 2 takes the text path.
    raw = "Plan.</think>\n\n\nTides."
    ids = ids_of("Plan.") + [THINK_END, NL3] + ids_of("Tides.") + [STOP]
    with caplog.at_level(logging.WARNING):
        rec = _one(monkeypatch, (raw, "stop", ids))
    assert rec["thinking_stripped"] is True and rec["conversation"][-1]["content"] == "\nTides."
    assert rec["thinking_token_range"] == [0, 6]               # NL3 is not "\n\n": the cut is k
    assert rec["content_token_range"] is None
    assert "1 of 1 responses: the stored ids do not decode to the stored text" in caplog.text


def test_a_plan_whose_end_tag_is_not_one_id_gets_null_ranges(monkeypatch, caplog):
    raw = "Plan: be brief.</think>Tides."
    ids = [ord(c) for c in raw] + [STOP]                     # "</think>" spelled in pieces
    with caplog.at_level(logging.WARNING):
        rec = _one(monkeypatch, (raw, "stop", ids))
    assert rec["thinking_stripped"] is True and rec["raw_text"] == raw
    assert rec["conversation"][-1]["content"] == "Tides."     # stripped as before
    assert rec["thinking_token_range"] is None and rec["content_token_range"] is None
    assert rec["response_token_ids"] == ids                   # still written, verbatim
    assert ("1 of 1 responses: the stored ids do not decode to the stored text (1 of them a "
            "stripped plan whose </think> is not one id)") in caplog.text


@pytest.mark.parametrize("char, kept", [("é", 1), ("€", 2), ("😀", 3)])
def test_a_cap_inside_a_character_steps_back_over_its_ids(monkeypatch, char, kept):
    # vLLM's text holds no partial character (the smoke run checks that it
    # does not end in U+FFFD; if it does, the check fails: the next test).
    ids = ids_of("Tides") + bytes_of(char)[:kept]
    rec = _one(monkeypatch, ("Tides", "length", ids))
    assert rec["finish_reason"] == "length"
    assert rec["content_token_range"] == [0, 5]


def test_a_text_that_keeps_the_partial_character_fails_the_check(monkeypatch):
    ids = ids_of("Tides") + bytes_of("é")[:1]
    rec = _one(monkeypatch, ("Tides" + chr(0xFFFD), "length", ids))
    assert rec["content_token_range"] is None


def test_a_sampled_special_token_is_kept_in_the_ids_and_the_range(monkeypatch):
    ids = ids_of("Arr ") + [SPECIAL] + ids_of("matey.") + [STOP]
    rec = _one(monkeypatch, ("Arr matey.", "stop", ids))
    assert rec["response_token_ids"] == ids
    assert rec["content_token_range"] == [0, len(ids) - 1]   # the special token inside it
    assert SPECIAL in ids[slice(*rec["content_token_range"])]


def test_keep_leaves_the_plan_in_the_text_and_records_where_it_is(monkeypatch, caplog):
    # --response_cleanup keep (§ 4.3, § 4.5 item 7)
    raw = "Okay, so the user is asking about tides.\n</think>\n\nTides come from the moon."
    stripped = _one(monkeypatch, (raw, "stop"))
    with caplog.at_level(logging.WARNING):
        kept = _one(monkeypatch, (raw, "stop"), response_cleanup_override="keep")
    assert kept["conversation"][-1]["content"] == raw              # vLLM's text, plan and all
    assert kept["thinking_stripped"] is False and "raw_text" not in kept
    assert kept["thinking_token_range"] == stripped["thinking_token_range"] is not None
    ids = kept["response_token_ids"]
    assert ids == stripped["response_token_ids"]
    assert kept["content_token_range"] == [0, len(ids) - 1]
    assert _decoded(ids, kept["content_token_range"]) == raw
    assert kept["thinking_suspected"] is True                       # the heuristic sees the plan
    assert "Kept orphaned thinking content in 1/1 responses" in caplog.text
    # "family" is the row's rule, as no override.
    assert _one(monkeypatch, (raw, "stop"), response_cleanup_override="family") == stripped


def test_the_override_is_checked_and_the_side_car_rule_is_what_was_done():
    # The side-car records the clean-up applied, not the flag (Roger,
    # 2026-11-03): keep is "none", so on a row whose rule is none it is the
    # same run as the default, and only keep against a strip is a difference.
    assert g.response_cleanup_for(FAMILIES["qwen3"], override="keep") == "none"
    assert g.response_cleanup_for(FAMILIES["qwen3"], override="family") == "strip_leaked_think"
    assert g.response_cleanup_for(FAMILIES["llama"], override=None) == "none"
    assert (g.response_cleanup_for(FAMILIES["llama"], override="keep")
            == g.response_cleanup_for(FAMILIES["llama"], override="family") == "none")
    with pytest.raises(ValueError):
        g.response_cleanup_for(FAMILIES["qwen3"], override="strip")
    with pytest.raises(ValueError):
        g.VLLMGenerator("Qwen/Qwen3-32B", family=FAMILIES["qwen3"],
                        response_cleanup_override="none")


def test_the_override_reaches_the_generator(tmp_path):
    rg = g.RoleResponseGenerator(model_name="fake/model", roles_dir=str(tmp_path),
                                 output_dir=str(tmp_path / "out"),
                                 questions_file=str(tmp_path / "q.jsonl"), short_name="F",
                                 response_cleanup_override="keep")
    assert rg.generator.response_cleanup_override == "keep"


def test_ids_that_are_not_the_text_get_a_null_range(monkeypatch, caplog):
    with caplog.at_level(logging.WARNING):
        rec = _one(monkeypatch, ("Tides.", "stop", ids_of("Tides!") + [STOP]))
    assert rec["content_token_range"] is None
    assert rec["conversation"][-1]["content"] == "Tides."     # the text is what vLLM gave
    assert "step 2 will take the text path for them" in caplog.text


# ---------------------------------------------------------------------------
# token_ranges as a pure function (§ 4.5 item 8)
# ---------------------------------------------------------------------------

def _ranges(ids, text, *, leaked=False, stripped=False, think_end_id=THINK_END):
    return g.token_ranges(FakeTokenizer(), ids, text, leaked=leaked, stripped=stripped,
                          think_end_id=think_end_id, special_ids=[STOP, SPECIAL])


def test_token_ranges_clean_and_empty():
    ids = ids_of("Arr.")
    assert _ranges(ids + [STOP], "Arr.") == (None, (0, 4))
    assert _ranges(ids, "Arr.") == (None, (0, 4))                       # no stop token
    assert _ranges(ids + [STOP, STOP], "Arr.") == (None, (0, 4))        # trailing specials
    assert _ranges([], "") == (None, (0, 0))                            # an empty response
    assert _ranges([STOP], "") == (None, (0, 0))
    assert _ranges(ids + [STOP], "Arr!") == (None, None)                # not the text


def test_token_ranges_stripped():
    # Flagged expectation change (Roger, 2026-11-03): the cut is after the
    # "\n\n" token that follows </think> (it was at </think>, and the check
    # compared after .strip()); the stored text keeps the model's trailing
    # newline, and the check is plain equality.
    plan = ids_of("Plan.") + [THINK_END]
    ids = plan + ids_of("\n\nArr.\n") + [STOP]
    assert ids[6] == NL2
    assert _ranges(ids, "Arr.\n", leaked=True, stripped=True) == ((0, 7), (7, len(ids) - 1))
    assert _ranges(ids, "Arr.", leaked=True, stripped=True) == ((0, 7), None)  # no .strip()
    # No "\n\n" after </think>: the cut is at </think>.
    other = plan + ids_of(" Arr.") + [STOP]
    assert _ranges(other, " Arr.", leaked=True, stripped=True) == ((0, 6), (6, len(other) - 1))
    # Only a plan: the thinking range is everything, the content range empty.
    assert _ranges(plan + [STOP], "", leaked=True, stripped=True) == ((0, 6), (6, 6))
    assert _ranges(plan + [NL2, STOP], "", leaked=True, stripped=True) == ((0, 7), (7, 7))
    assert _ranges(plan + [NL2], "", leaked=True, stripped=True) == ((0, 7), (7, 7))
    # </think> in pieces: both null when stripped.
    pieces = ids_of("Plan.") + [ord(c) for c in "</think>"] + ids_of("Arr.") + [STOP]
    assert _ranges(pieces, "Arr.", leaked=True, stripped=True) == (None, None)
    # No </think> id at all in the tokenizer: the same.
    assert _ranges(ids, "Arr.", leaked=True, stripped=True, think_end_id=None) == (None, None)


def test_token_ranges_leaked_but_kept():
    # --response_cleanup keep: the text is vLLM's, plan and all.  Flagged
    # expectation change (Roger, 2026-11-03): the thinking range ends where
    # the strip would cut, after the "\n\n" (it ended at </think>, (0, 6)).
    ids = ids_of("Plan.") + [THINK_END] + ids_of("\n\nArr.") + [STOP]
    raw = "Plan.</think>\n\nArr."
    assert _ranges(ids, raw, leaked=True) == ((0, 7), (0, len(ids) - 1))
    assert (_ranges(ids, raw, leaked=True)[0]
            == _ranges(ids, "Arr.", leaked=True, stripped=True)[0])   # the same in both modes
    # </think> in pieces: no thinking range, the content range still from 0.
    pieces = [ord(c) for c in raw] + [STOP]
    assert _ranges(pieces, raw, leaked=True) == (None, (0, len(pieces) - 1))


def test_token_ranges_partial_characters():
    for char, n in (("é", 2), ("€", 3), ("😀", 4)):
        ids = ids_of("Hi") + bytes_of(char)
        assert _ranges(ids, "Hi" + char) == (None, (0, 2 + n))          # the whole character
        for kept in range(1, n):
            assert _ranges(ids_of("Hi") + bytes_of(char)[:kept], "Hi") == (None, (0, 2))
    # At most three ids are dropped: four lone continuation bytes are not a
    # partial character at the cap (the check then fails).
    stray = ids_of("Hi") + [BYTE + 0x80] * 4
    assert _ranges(stray, "Hi") == (None, None)


def test_token_ranges_a_strip_without_detection_is_a_bug():
    with pytest.raises(ValueError):
        _ranges(ids_of("Arr."), "Arr.", stripped=True)


def test_the_end_tag_id_is_accepted_only_when_it_decodes_to_the_tag():
    assert g.think_end_token_id(FakeTokenizer()) == THINK_END

    class NoTag(FakeTokenizer):
        def convert_tokens_to_ids(self, token):
            return 0                                          # the unknown token's id

    assert g.think_end_token_id(NoTag()) is None
