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


# ---------------------------------------------------------------------------
# Deferral integration (Phase 6d-1)
# ---------------------------------------------------------------------------

def test_apply_deferrals_reclassifies_stale_direct(tmp_path: Path) -> None:
    from assistant_axis import deferral_registry
    src = tmp_path / "src.json"; src.write_text("v1")
    inputs = [prov.current_file_input("src", src)]
    out = tmp_path / "cache.json"
    _write_envelope(out, {"x": 1}, inputs)
    time.sleep(1.1)
    src.write_text("v1 changed")  # cause drift

    a = audit_caches.audit_cache(out)
    assert a.status == "stale_direct"

    # Inline registry matches this cache by path glob.  We pass
    # ``repo_root=tmp_path`` so paths are normalised relative to the
    # test scratch dir rather than the actual project root.
    reg = [deferral_registry.DeferralEntry(
        path_glob="cache.json",
        dep_key=None,
        reason="explicit defer",
        deferred_at="2026-05-08T00:00:00+00:00",
    )]
    audit_caches.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "deferred"
    assert a.pre_deferred_status == "stale_direct"
    assert a.deferral_matches[0].reason == "explicit defer"


def test_apply_deferrals_skips_current_caches(tmp_path: Path) -> None:
    """A ``current`` cache must NOT be reclassified to ``deferred`` even
    when an entry in the registry happens to match its path -- deferral
    only applies to caches that were actually stale."""
    from assistant_axis import deferral_registry
    src = tmp_path / "src.json"; src.write_text("v1")
    inputs = [prov.current_file_input("src", src)]
    out = tmp_path / "cache.json"
    _write_envelope(out, {"x": 1}, inputs)

    a = audit_caches.audit_cache(out)
    assert a.status == "current"
    reg = [deferral_registry.DeferralEntry(
        path_glob="cache.json", dep_key=None,
        reason="should not apply", deferred_at="2026-05-08",
    )]
    audit_caches.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "current"


def test_apply_deferrals_dep_key_filter(tmp_path: Path) -> None:
    """Registry entry with dep_key restricts to caches drifting on the
    matching dep_key only."""
    from assistant_axis import deferral_registry
    s1 = tmp_path / "s1.json"; s1.write_text("v")
    s2 = tmp_path / "s2.json"; s2.write_text("v")
    out1 = tmp_path / "c1.json"
    out2 = tmp_path / "c2.json"
    _write_envelope(out1, {"x": 1}, [prov.current_file_input("d_target", s1)])
    _write_envelope(out2, {"x": 2}, [prov.current_file_input("d_other", s2)])
    time.sleep(1.1)
    s1.write_text("v changed"); s2.write_text("v changed")

    a1 = audit_caches.audit_cache(out1)
    a2 = audit_caches.audit_cache(out2)
    assert a1.status == "stale_direct" and a2.status == "stale_direct"

    reg = [deferral_registry.DeferralEntry(
        path_glob="c*.json", dep_key="d_target",
        reason="targeted", deferred_at="2026-05-08",
    )]
    audit_caches.apply_deferrals([a1, a2], registry=reg, repo_root=tmp_path)
    assert a1.status == "deferred"
    assert a2.status == "stale_direct"  # dep_key filter excluded it


def test_apply_deferrals_reclassifies_legacy_when_matched(tmp_path: Path) -> None:
    """May 2026 backfill: a bare-JSON legacy cache (no envelope)
    should be reclassified to ``deferred`` when its path matches a
    registry entry, with ``pre_deferred_status="legacy"`` recorded.

    This is the mechanism the judge-cache backfill relies on:
    ``scores_*.json`` files written before Phase 6a have no envelope
    so they read as ``legacy``; an upfront deferral entry says
    "presume current as of mechanism introduction".
    """
    from assistant_axis import deferral_registry
    legacy_cache = tmp_path / "scores_descriptions.json"
    legacy_cache.write_text(json.dumps({"role_a": 1.0, "role_b": 2.0}))

    a = audit_caches.audit_cache(legacy_cache)
    assert a.status == "legacy"

    reg = [deferral_registry.DeferralEntry(
        path_glob="scores_*.json",
        dep_key=None,
        reason="Pre-Phase-6 judge cache; presume current.",
        deferred_at="2026-05-08T00:00:00+00:00",
    )]
    audit_caches.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "deferred"
    assert a.pre_deferred_status == "legacy"
    assert a.deferral_matches[0].path_glob == "scores_*.json"


def test_deferred_upstream_does_not_taint_downstream(
    tmp_path: Path, monkeypatch
) -> None:
    """Finding 1 regression: A → B → C (B is judge step, deferred);
    C's recorded fingerprint of B is current.  After running
    ``apply_deferrals`` THEN ``propagate_transitive_stale`` (the
    fixed order), C must remain ``current`` -- a deferred upstream
    shouldn't taint a downstream that's actually up-to-date with it.
    """
    from assistant_axis import deferral_registry
    monkeypatch.setattr(audit_caches, "_REPO_ROOT", tmp_path)

    src = tmp_path / "src.json"
    src.write_text("hello")
    inputs_b = [prov.current_file_input("src", src)]
    b = tmp_path / "judge_b.json"
    _write_envelope(b, {"name": "B"}, inputs_b)

    inputs_c = [prov.current_file_input("b", b)]
    c = tmp_path / "c.json"
    _write_envelope(c, {"name": "C"}, inputs_c)

    time.sleep(1.1)
    src.write_text("hello world")  # B becomes stale_direct vs src

    audits = [audit_caches.audit_cache(p) for p in (b, c)]
    assert {a.path.name: a.status for a in audits} == {
        "judge_b.json": "stale_direct",
        "c.json": "current",
    }

    reg = [deferral_registry.DeferralEntry(
        path_glob="judge_*.json", dep_key=None,
        reason="judge step deferred", deferred_at="2026-05-09",
    )]
    audit_caches.apply_deferrals(audits, registry=reg, repo_root=tmp_path)
    audit_caches.propagate_transitive_stale(audits)

    statuses = {a.path.name: a.status for a in audits}
    assert statuses == {
        "judge_b.json": "deferred",
        "c.json": "current",  # not stale_transitive — deferred upstream
    }


def test_transitively_stale_cache_can_be_deferred(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression (2026-10-12): A -> B -> C with only C directly stale and
    a registry entry naming B.  ``apply_deferrals`` runs before
    propagation, when B is still ``current``, so it cannot defer B; the
    propagation pass must.  B becomes ``deferred`` (was
    ``stale_transitive``) and, as a barrier, leaves A ``current``."""
    from assistant_axis import deferral_registry
    monkeypatch.setattr(audit_caches, "_REPO_ROOT", tmp_path)

    src = tmp_path / "src.json"
    src.write_text("hello")
    c = tmp_path / "c.json"
    _write_envelope(c, {"name": "C"}, [prov.current_file_input("src", src)])
    b = tmp_path / "b_frozen.json"
    _write_envelope(b, {"name": "B"}, [prov.current_file_input("c", c)])
    a = tmp_path / "a.json"
    _write_envelope(a, {"name": "A"}, [prov.current_file_input("b", b)])
    time.sleep(1.1)
    src.write_text("hello world")

    audits = [audit_caches.audit_cache(p) for p in (a, b, c)]
    reg = [deferral_registry.DeferralEntry(
        path_glob="b_frozen.json", dep_key=None,
        reason="frozen consumer", deferred_at="2026-10-12",
    )]
    audit_caches.apply_deferrals(audits, registry=reg, repo_root=tmp_path)
    assert {x.path.name: x.status for x in audits}["b_frozen.json"] == "current"
    audit_caches.propagate_transitive_stale(
        audits, registry=reg, repo_root=tmp_path)
    statuses = {x.path.name: x.status for x in audits}
    assert statuses == {"a.json": "current", "b_frozen.json": "deferred",
                        "c.json": "stale_direct"}
    b_audit = next(x for x in audits if x.path.name == "b_frozen.json")
    assert b_audit.pre_deferred_status == "stale_transitive"
    assert b_audit.deferral_matches[0].reason == "frozen consumer"

    # Without a registry the old behaviour holds: both consumers tainted.
    audits = [audit_caches.audit_cache(p) for p in (a, b, c)]
    audit_caches.propagate_transitive_stale(audits)
    assert {x.path.name: x.status for x in audits} == {
        "a.json": "stale_transitive", "b_frozen.json": "stale_transitive",
        "c.json": "stale_direct"}


def test_apply_deferrals_legacy_no_match_stays_legacy(tmp_path: Path) -> None:
    """Legacy cache whose path doesn't match any registry entry stays
    ``legacy``; deferrals are opt-in per path."""
    from assistant_axis import deferral_registry
    legacy_cache = tmp_path / "rho_by_layer.json"
    legacy_cache.write_text(json.dumps({"x": 1}))

    a = audit_caches.audit_cache(legacy_cache)
    assert a.status == "legacy"

    reg = [deferral_registry.DeferralEntry(
        path_glob="scores_*.json", dep_key=None,
        reason="judge-only", deferred_at="2026-05-08",
    )]
    audit_caches.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "legacy"  # unchanged


# ---------------------------------------------------------------------------
# 2026-10-12: categories honoured (walk-through E10), every drift covered (E8)
# ---------------------------------------------------------------------------

def _stale_two_inputs(tmp_path: Path) -> Path:
    """An envelope cache whose two inputs (dep_keys d_a, d_b) both drifted."""
    s1 = tmp_path / "s1.json"; s1.write_text("v")
    s2 = tmp_path / "s2.json"; s2.write_text("v")
    out = tmp_path / "scores_x.json"
    _write_envelope(out, {"x": 1}, [prov.current_file_input("d_a", s1),
                                    prov.current_file_input("d_b", s2)])
    time.sleep(1.1)
    s1.write_text("v changed"); s2.write_text("v changed")
    return out


def test_multi_drift_needs_every_dep_key_covered(tmp_path: Path) -> None:
    """Regression (walk-through E8): a cache with two drifted inputs used to
    be matched with dep_key=None, so an entry scoped to one of them deferred
    it.  Now it stays stale_direct until both are covered."""
    from assistant_axis import deferral_registry
    out = _stale_two_inputs(tmp_path)
    only_a = deferral_registry.DeferralEntry(
        path_glob="scores_*.json", dep_key="d_a", reason="a only",
        deferred_at="2026-10-12")
    a = audit_caches.audit_cache(out)
    assert a.status == "stale_direct"
    audit_caches.apply_deferrals([a], registry=[only_a], repo_root=tmp_path)
    assert a.status == "stale_direct"

    only_b = deferral_registry.DeferralEntry(
        path_glob="scores_*.json", dep_key="d_b", reason="b only",
        deferred_at="2026-10-12")
    a = audit_caches.audit_cache(out)
    audit_caches.apply_deferrals([a], registry=[only_a, only_b], repo_root=tmp_path)
    assert a.status == "deferred"
    assert [e.reason for e in a.deferral_matches] == ["a only", "b only"]


def test_legacy_bare_no_longer_defers_an_envelope_cache(tmp_path: Path) -> None:
    """Regression (walk-through E10): the May ``legacy_bare`` globs matched
    envelope-carrying stale_direct judge caches (915 on 2026-10-12).  A
    legacy_bare entry now defers only legacy rows; awaiting_rescore records
    the stale ones."""
    from assistant_axis import deferral_registry
    C = deferral_registry.DeferralCategory
    out = _stale_two_inputs(tmp_path)
    bare = tmp_path / "scores_bare.json"
    bare.write_text(json.dumps({"role_a": 1.0}))
    legacy_bare = deferral_registry.DeferralEntry(
        path_glob="scores_*.json", dep_key=None, reason="bare May cache",
        deferred_at="2026-05-08", category=C.LEGACY_BARE)

    rows = [audit_caches.audit_cache(p) for p in (out, bare)]
    audit_caches.apply_deferrals(rows, registry=[legacy_bare], repo_root=tmp_path)
    assert {r.path.name: r.status for r in rows} == {
        "scores_x.json": "stale_direct", "scores_bare.json": "deferred"}

    awaiting = deferral_registry.DeferralEntry(
        path_glob="scores_*.json", dep_key=None, reason="October re-score",
        deferred_at="2026-10-12", category=C.AWAITING_RESCORE)
    rows = [audit_caches.audit_cache(p) for p in (out, bare)]
    audit_caches.apply_deferrals(rows, registry=[legacy_bare, awaiting], repo_root=tmp_path)
    by = {r.path.name: r for r in rows}
    assert by["scores_x.json"].status == "deferred"
    assert [e.category for e in by["scores_x.json"].deferral_matches] == [C.AWAITING_RESCORE]
    assert by["scores_x.json"].pre_deferred_status == "stale_direct"
    assert [e.category for e in by["scores_bare.json"].deferral_matches] == [C.LEGACY_BARE]


def test_transitive_rows_honour_categories_and_dep_key_scope(
    tmp_path: Path, monkeypatch
) -> None:
    """The transitive pass uses the same matcher: a legacy_bare entry or a
    dep_key-scoped one does not defer a stale_transitive row (it has no
    drifted dep_key of its own); an unscoped awaiting_rescore entry does."""
    from assistant_axis import deferral_registry
    C = deferral_registry.DeferralCategory
    monkeypatch.setattr(audit_caches, "_REPO_ROOT", tmp_path)
    src = tmp_path / "src.json"; src.write_text("hello")
    c = tmp_path / "c.json"
    _write_envelope(c, {"name": "C"}, [prov.current_file_input("src", src)])
    b = tmp_path / "corr_b.json"
    _write_envelope(b, {"name": "B"}, [prov.current_file_input("c", c)])
    time.sleep(1.1)
    src.write_text("hello world")

    def run(entry):
        rows = [audit_caches.audit_cache(p) for p in (b, c)]
        audit_caches.apply_deferrals(rows, registry=[entry], repo_root=tmp_path)
        audit_caches.propagate_transitive_stale(rows, registry=[entry], repo_root=tmp_path)
        return {r.path.name: r.status for r in rows}

    mk = lambda **kw: deferral_registry.DeferralEntry(
        path_glob="corr_*.json", reason="r", deferred_at="2026-10-12", **kw)
    assert run(mk(dep_key=None, category=C.LEGACY_BARE))["corr_b.json"] == "stale_transitive"
    assert run(mk(dep_key="c", category=C.ARCHIVED))["corr_b.json"] == "stale_transitive"
    assert run(mk(dep_key=None, category=C.AWAITING_RESCORE))["corr_b.json"] == "deferred"
