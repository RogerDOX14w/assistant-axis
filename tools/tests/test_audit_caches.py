"""Tests for tools/audit_caches.py.

Focused on the transitive-stale propagation algorithm; the per-cache
audit logic is already covered by ``test_provenance.test_load_validated_json*``
(both share ``validate_recorded`` under the hood).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Make ``tools.audit_caches`` importable without requiring an editable
# install of the tools dir.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis import provenance as prov  # noqa: E402
from tools import audit_caches  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _envelope(payload, inputs):
    """Build a provenance envelope mimicking what ``json_metadata`` writes."""
    return {
        "result": payload,
        "_provenance": {
            "schema_version": prov.PROVENANCE_SCHEMA_VERSION,
            "produced_by": {"cmd": "uv run python test.py"},
            "produced_at": "2026-05-08T00:00:00+00:00",
            "inputs": prov.inputs_to_jsonable(inputs),
        },
    }


def _write_envelope(path: Path, payload, inputs) -> None:
    path.write_text(json.dumps(_envelope(payload, inputs)))


# ---------------------------------------------------------------------------
# Per-cache classification
# ---------------------------------------------------------------------------

def test_audit_cache_legacy_no_envelope(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"hello": 1}))
    a = audit_caches.audit_cache(p)
    assert a.status == "legacy"


def test_audit_cache_current(tmp_path: Path) -> None:
    src = tmp_path / "src.json"
    src.write_text("hello")
    inputs = [prov.current_file_input("src", src)]
    out = tmp_path / "cache.json"
    _write_envelope(out, {"x": 1}, inputs)
    a = audit_caches.audit_cache(out)
    assert a.status == "current"
    assert a.cmd == "uv run python test.py"


def test_audit_cache_stale_direct(tmp_path: Path) -> None:
    src = tmp_path / "src.json"
    src.write_text("hello")
    inputs = [prov.current_file_input("src", src)]
    out = tmp_path / "cache.json"
    _write_envelope(out, {"x": 1}, inputs)
    time.sleep(1.1)
    src.write_text("hello world")  # cause drift
    a = audit_caches.audit_cache(out)
    assert a.status == "stale_direct"
    reasons = a.stale_reasons()
    assert len(reasons) == 1
    assert "src" in reasons[0]


def test_audit_cache_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    a = audit_caches.audit_cache(p)
    assert a.status == "legacy"
    assert a.notes
    assert "not valid JSON" in a.notes[0]


# ---------------------------------------------------------------------------
# Transitive stale propagation
# ---------------------------------------------------------------------------

def test_transitive_stale_one_hop(tmp_path: Path, monkeypatch) -> None:
    """A → B; B is stale; A's own deps validate clean (file-fp on B
    still matches because B's mtime hasn't changed).  After
    propagation, A should be ``stale_transitive``."""
    monkeypatch.setattr(audit_caches, "_REPO_ROOT", tmp_path)

    # Source file feeds B.
    src = tmp_path / "src.json"
    src.write_text("hello")
    inputs_b = [prov.current_file_input("src", src)]
    b = tmp_path / "b.json"
    _write_envelope(b, {"name": "B"}, inputs_b)

    # A depends on B.
    inputs_a = [prov.current_file_input("b", b)]
    a = tmp_path / "a.json"
    _write_envelope(a, {"name": "A"}, inputs_a)

    # Mutate src so B becomes stale (but B itself is not regenerated).
    time.sleep(1.1)
    src.write_text("hello world")

    audits = [audit_caches.audit_cache(a), audit_caches.audit_cache(b)]
    # Pre-propagation: A is current (B's mtime/size unchanged), B stale_direct.
    statuses_pre = {x.path.name: x.status for x in audits}
    assert statuses_pre == {"a.json": "current", "b.json": "stale_direct"}

    audit_caches.propagate_transitive_stale(audits)
    statuses_post = {x.path.name: x.status for x in audits}
    assert statuses_post == {"a.json": "stale_transitive",
                             "b.json": "stale_direct"}
    a_audit = next(x for x in audits if x.path.name == "a.json")
    assert b in a_audit.transitive_stale_via


def test_transitive_stale_two_hops(tmp_path: Path, monkeypatch) -> None:
    """A → B → C; only C is directly stale.  Both A and B should be
    ``stale_transitive`` after propagation."""
    monkeypatch.setattr(audit_caches, "_REPO_ROOT", tmp_path)

    src = tmp_path / "src.json"
    src.write_text("hello")

    inputs_c = [prov.current_file_input("src", src)]
    c = tmp_path / "c.json"
    _write_envelope(c, {"name": "C"}, inputs_c)

    inputs_b = [prov.current_file_input("c", c)]
    b = tmp_path / "b.json"
    _write_envelope(b, {"name": "B"}, inputs_b)

    inputs_a = [prov.current_file_input("b", b)]
    a = tmp_path / "a.json"
    _write_envelope(a, {"name": "A"}, inputs_a)

    # Drift only at C's source.
    time.sleep(1.1)
    src.write_text("hello world")

    audits = [audit_caches.audit_cache(p) for p in (a, b, c)]
    audit_caches.propagate_transitive_stale(audits)
    statuses = {x.path.name: x.status for x in audits}
    assert statuses == {"a.json": "stale_transitive",
                        "b.json": "stale_transitive",
                        "c.json": "stale_direct"}


def test_transitive_stale_diamond(tmp_path: Path, monkeypatch) -> None:
    """Diamond: A depends on B and C; both B and C depend on D; D is
    stale.  A picks up *both* B and C as transitive_stale_via."""
    monkeypatch.setattr(audit_caches, "_REPO_ROOT", tmp_path)

    src = tmp_path / "src.json"
    src.write_text("hello")
    inputs_d = [prov.current_file_input("src", src)]
    d = tmp_path / "d.json"
    _write_envelope(d, {"name": "D"}, inputs_d)

    inputs_b = [prov.current_file_input("d", d)]
    b = tmp_path / "b.json"
    _write_envelope(b, {"name": "B"}, inputs_b)

    inputs_c = [prov.current_file_input("d", d)]
    c = tmp_path / "c.json"
    _write_envelope(c, {"name": "C"}, inputs_c)

    inputs_a = [prov.current_file_input("b", b),
                prov.current_file_input("c", c)]
    a = tmp_path / "a.json"
    _write_envelope(a, {"name": "A"}, inputs_a)

    time.sleep(1.1)
    src.write_text("hello world")

    audits = [audit_caches.audit_cache(p) for p in (a, b, c, d)]
    audit_caches.propagate_transitive_stale(audits)
    statuses = {x.path.name: x.status for x in audits}
    assert statuses == {
        "a.json": "stale_transitive",
        "b.json": "stale_transitive",
        "c.json": "stale_transitive",
        "d.json": "stale_direct",
    }
    a_audit = next(x for x in audits if x.path.name == "a.json")
    via = {p.name for p in a_audit.transitive_stale_via}
    assert via == {"b.json", "c.json"}


def test_no_propagation_when_all_clean(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(audit_caches, "_REPO_ROOT", tmp_path)
    src = tmp_path / "src.json"
    src.write_text("hello")
    inputs_b = [prov.current_file_input("src", src)]
    b = tmp_path / "b.json"
    _write_envelope(b, {"name": "B"}, inputs_b)
    inputs_a = [prov.current_file_input("b", b)]
    a = tmp_path / "a.json"
    _write_envelope(a, {"name": "A"}, inputs_a)
    audits = [audit_caches.audit_cache(p) for p in (a, b)]
    audit_caches.propagate_transitive_stale(audits)
    assert {x.status for x in audits} == {"current"}
