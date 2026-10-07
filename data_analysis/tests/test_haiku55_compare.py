"""``haiku55_compare.py`` (coding_plan_haiku55.md): the comparison helpers on small synthetic runs, and the filter
comparison on two recorded Haiku 4.5 runs of the 99 test words (read only; no API call)."""
import json

import pytest

from data_analysis.gap_generation import haiku55_compare as H


def frow(label, outcome, reading=None, *, gloss=None, membership=None, gloss_model="m", alignment=None, notes=()):
    f = {"outcome": outcome, "judged_sense": reading, "membership_kind": membership, "gloss_model": gloss_model,
         "alignment": alignment, "notes": list(notes), "verdict": "trait" if outcome == "trait" else "reject"}
    return {"label": label, "stage": "classified", "filter": f, "gloss": gloss}


def frun(batch, rows, records=()):
    return {"batch": batch, "dir": None, "run": {}, "rows": rows, "by_label": {r["label"]: r for r in rows},
            "records": list(records)}


class TestFilterHelpers:
    def test_against_reference_and_word_by_word(self):
        exp = {"a": {"outcome": "trait", "accepted": "x"}, "b": {"outcome": "states"}, "c": {"outcome": "turned_away"}}
        r1 = frun("one", [frow("a", "trait", "x"), frow("b", "trait", "y"), frow("c", "turned_away")])
        r2 = frun("two", [frow("a", "trait", "X"), frow("b", "states", "z")])
        a = H.against_reference(r1, exp, ["a", "b", "c"])
        assert a["n"] == 3 and a["same"] == 2 and a["differ"][0]["label"] == "b" and a["outcomes"] == {"trait": 2, "turned_away": 1}
        a2 = H.against_reference(r2, exp, ["a", "b", "c"])
        assert a2["n"] == 2 and a2["same"] == 2 and a2["missing"] == ["c"]
        w = H.word_by_word(r1, r2, ["a", "b", "c"])
        assert w["n_both"] == 2 and w["same_outcome"] == 1 and w["same_reading_wording"] == 1     # case-blind
        assert w["differ"] == [{"label": "b", "one": "trait", "two": "states", "one_reading": "y", "two_reading": "z"}]

    def test_gloss_checks_band_and_the_fact_wins(self):
        long = "This means " + "being " * 18 + "kind."
        rows = [frow("a", "trait", gloss=long), frow("b", "trait", gloss="This means being from Denmark.", membership="nationality"),
                frow("c", "trait", gloss="Means nothing much at all.", gloss_model="s"),
                frow("d", "trait", gloss="This means being from Denmark, " + "with " * 16 + "pride.", membership="nationality"),
                frow("e", "states", gloss=None)]
        g = H.gloss_checks(frun("r", rows))
        assert g["n_traits"] == 4 and g["with_gloss"] == 4 and g["form_ok"] == 3
        assert g["non_membership"]["n"] == 2 and g["non_membership"]["in_band"] == 1 and g["non_membership"]["below"] == 1
        assert g["membership"]["n"] == 2 and [x["label"] for x in g["membership"]["possibly_padded"]] == ["d"]
        assert g["by_gloss_model"] == {"m": 3, "s": 1}

    def test_inputs_and_parse_rates_from_records(self):
        rec = lambda lab, ok=True, model="m", step="sense": {"step": step, "role": "first", "model": model,  # noqa: E731
                                                             "keys": [f"{lab}#1"], "index": None, "prompt_sha256": "p",
                                                             "user": json.dumps({"id": 1, "label": lab}), "text": "t",
                                                             "parse_errors": {} if ok else {"k": "bad"},
                                                             "usage_raw": {"input_tokens": 10, "output_tokens": 5},
                                                             "stop_reason": "end_turn", "charged_as": model}
        a = frun("a", [], [rec("x"), rec("y")])
        b = frun("b", [], [rec("x"), rec("y", ok=False), rec("y")])
        s = H.same_inputs(a, b, ["x", "y", "z"])
        assert s["n_both"] == 2 and s["step1_user_identical"] == 2 and s["system_prompts_identical"] == {"sense": True}
        p = H.parse_rates(b["records"])
        assert p == {"sense|first|m": {"n": 2, "ok_first": 1, "ok": 2}}


class TestRelationHelpers:
    @pytest.mark.parametrize("should,answer,want", [
        ("opposed", "opposed", True), ("opposed", "unrelated", False), ("similar", "similar", True),
        ("unrelated", "unrelated", True), ("unrelated", "similar", False), ("not opposed", "unrelated", True),
        ("not opposed", "unsure", True), ("not opposed", "opposed", False), ("opposed or 1", "unrelated", True),
        ("opposed or 1", "opposed", True), ("opposed or 1", "similar", False), ("opposed", None, None),
        ("something else", "opposed", None)])
    def test_correction_right(self, should, answer, want):
        assert H.correction_right(should, answer) is want

    def test_relation_agreement(self):
        a = {"k1": {"s": "similar", "t": "opposed", "u": "unrelated"}, "k2": {"s": "unrelated"}}
        b = {"k1": {"s": "similar", "t": "unrelated", "u": "unrelated"}, "k2": {"s": "unrelated"}, "k3": {"s": "similar"}}
        g = H.relation_agreement(a, b, ["k1", "k2", "k3"])
        assert g["n"] == 4 and g["same"] == 3 and g["agreement"] == 0.75
        assert g["confusion"] == {"similar -> similar": 1, "opposed -> unrelated": 1, "unrelated -> unrelated": 2}
        assert g["kappa"] is not None and 0 < g["kappa"] < 1


def test_filter_words_on_two_recorded_haiku_45_runs():
    """The comparison as the CLI makes it, on the two recorded live runs of 2026-09-29 and 30 (read only)."""
    exp = {e["word"]: e for e in H.read_jsonl(H.REFERENCE_JOIN)}
    runs = [H.load_filter_run(b) for b in ("r7_split_test_words", "split_pilot_live")]
    if not all(r["rows"] for r in runs):
        pytest.skip("recorded runs not present")
    c = H.compare_filter_words(runs, exp, list(exp))
    assert c["against_reference"]["split_pilot_live"]["same"] == 92                  # acceptance_split.md, run A
    assert c["against_reference"]["r7_split_test_words"]["n"] == 99
    assert c["inputs"]["r7_split_test_words vs split_pilot_live"]["step1_user_identical"] == 99
    md = H.filter_words_markdown(c)
    assert "## Outcomes against the reference join" in md and "| split_pilot_live | 99 | 92 |" in md
