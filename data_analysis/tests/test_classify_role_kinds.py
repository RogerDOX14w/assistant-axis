"""classify_role_kinds: parsing and the majority rule (no API calls)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import classify_role_kinds as C  # noqa: E402


def test_parse_kind_accepts_prose_before_the_object_and_normalises_the_key():
    assert C.parse_kind('Sure.\n{"reason": "a creature", "kind": "Non-Human"}') == {"kind": "non_human", "reason": "a creature"}
    assert C.parse_kind('{"reason": "x", "kind": "wizardry"}') is None
    assert C.parse_kind(None) is None


def test_combine_majority_split_and_empty():
    r = lambda k: {"kind": k, "reason": ""}
    assert C.combine([r("pastime"), r("stance"), r("pastime")]) | {} == {"kind": "pastime", "split": False, "n_parsed": 3, "unanimous": False}
    three_way = C.combine([r("status"), r("stance"), r("other")])
    assert three_way["kind"] == "status" and three_way["split"]
    assert C.combine([None, r("other"), None])["kind"] == "other"
    assert C.combine([None, None])["kind"] is None


def test_every_kind_key_is_unique_and_nine():
    assert len(C.KIND_KEYS) == len(set(C.KIND_KEYS)) == 9
