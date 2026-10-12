"""Tests for tools/audit_pngs.py.

Smoke coverage for the audit pipeline plus the deferral integration
that mirrors ``audit_caches``: ``stale -> deferred`` (Phase 6d-1) and
``legacy -> deferred`` (May 2026 judge-cache backfill).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless; do not require a display server.
import matplotlib.pyplot as plt  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis import provenance as prov  # noqa: E402
from assistant_axis.plot_metadata import png_metadata  # noqa: E402
from tools import audit_pngs  # noqa: E402


def _save_legacy_png(path: Path) -> None:
    """Write a PNG with no provenance ``Inputs`` chunk."""
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    fig.savefig(path)
    plt.close(fig)


def _save_envelope_png(path: Path, inputs) -> None:
    """Write a PNG carrying an ``Inputs`` chunk for ``inputs``."""
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    fig.savefig(path, metadata=png_metadata(
        title="test", inputs=inputs,
    ))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Per-PNG classification
# ---------------------------------------------------------------------------

def test_audit_png_legacy_no_inputs_chunk(tmp_path: Path) -> None:
    p = tmp_path / "plot.png"
    _save_legacy_png(p)
    a = audit_pngs.audit_png(p)
    assert a.status == "legacy"


def test_audit_png_current_envelope_validates(tmp_path: Path) -> None:
    src = tmp_path / "src.json"; src.write_text("v1")
    inputs = [prov.current_file_input("src", src)]
    p = tmp_path / "plot.png"
    _save_envelope_png(p, inputs)
    a = audit_pngs.audit_png(p)
    assert a.status == "current"


def test_audit_png_stale_when_input_drifts(tmp_path: Path) -> None:
    src = tmp_path / "src.json"; src.write_text("v1")
    inputs = [prov.current_file_input("src", src)]
    p = tmp_path / "plot.png"
    _save_envelope_png(p, inputs)
    time.sleep(1.1)
    src.write_text("v1 changed")  # cause drift
    a = audit_pngs.audit_png(p)
    assert a.status == "stale"


# ---------------------------------------------------------------------------
# Deferral integration
# ---------------------------------------------------------------------------

def test_apply_deferrals_reclassifies_stale(tmp_path: Path) -> None:
    from assistant_axis import deferral_registry
    src = tmp_path / "src.json"; src.write_text("v1")
    inputs = [prov.current_file_input("src", src)]
    p = tmp_path / "plot.png"
    _save_envelope_png(p, inputs)
    time.sleep(1.1)
    src.write_text("v1 changed")

    a = audit_pngs.audit_png(p)
    assert a.status == "stale"

    reg = [deferral_registry.DeferralEntry(
        path_glob="plot.png",
        dep_key=None,
        reason="explicit defer",
        deferred_at="2026-05-08T00:00:00+00:00",
    )]
    audit_pngs.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "deferred"
    assert a.pre_deferred_status == "stale"
    assert a.deferral_matches[0].reason == "explicit defer"


def test_categories_and_dep_key_coverage_are_honoured(tmp_path: Path) -> None:
    """2026-10-12 (walk-through E8, E10), as in audit_caches: legacy_bare
    defers only a legacy PNG, awaiting_rescore only a stale one, and a stale
    PNG with two drifted inputs needs both covered."""
    from assistant_axis import deferral_registry
    C = deferral_registry.DeferralCategory
    s1 = tmp_path / "s1.json"; s1.write_text("v")
    s2 = tmp_path / "s2.json"; s2.write_text("v")
    stale = tmp_path / "correlation_plot.png"
    _save_envelope_png(stale, [prov.current_file_input("d_a", s1),
                               prov.current_file_input("d_b", s2)])
    sub = tmp_path / "old"; sub.mkdir()
    legacy = sub / "correlation_plot.png"
    _save_legacy_png(legacy)
    time.sleep(1.1)
    s1.write_text("v changed"); s2.write_text("v changed")

    def run(*entries):
        rows = [audit_pngs.audit_png(p) for p in (stale, legacy)]
        audit_pngs.apply_deferrals(rows, registry=list(entries), repo_root=tmp_path)
        return [r.status for r in rows]

    mk = lambda **kw: deferral_registry.DeferralEntry(
        path_glob="*correlation_plot.png", reason="r", deferred_at="2026-10-12", **kw)
    assert run(mk(dep_key=None, category=C.LEGACY_BARE)) == ["stale", "deferred"]
    assert run(mk(dep_key=None, category=C.AWAITING_RESCORE)) == ["deferred", "legacy"]
    assert run(mk(dep_key="d_a", category=C.ARCHIVED)) == ["stale", "legacy"]
    assert run(mk(dep_key="d_a", category=C.ARCHIVED),
               mk(dep_key="d_b", category=C.ARCHIVED)) == ["deferred", "legacy"]


def test_apply_deferrals_reclassifies_legacy_when_matched(
    tmp_path: Path,
) -> None:
    """May 2026 backfill: a legacy PNG (no Inputs chunk) should
    reclassify to ``deferred`` when its path matches a registry
    entry, with ``pre_deferred_status="legacy"`` recorded.
    """
    from assistant_axis import deferral_registry
    p = tmp_path / "correlation_plot.png"
    _save_legacy_png(p)

    a = audit_pngs.audit_png(p)
    assert a.status == "legacy"

    reg = [deferral_registry.DeferralEntry(
        path_glob="correlation_*.png",
        dep_key=None,
        reason="Pre-Phase-6 judge plot; presume current.",
        deferred_at="2026-05-08T00:00:00+00:00",
    )]
    audit_pngs.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "deferred"
    assert a.pre_deferred_status == "legacy"


def test_apply_deferrals_legacy_no_match_stays_legacy(tmp_path: Path) -> None:
    from assistant_axis import deferral_registry
    p = tmp_path / "rho_by_layer.png"
    _save_legacy_png(p)
    a = audit_pngs.audit_png(p)
    assert a.status == "legacy"

    reg = [deferral_registry.DeferralEntry(
        path_glob="correlation_*.png", dep_key=None,
        reason="judge-only", deferred_at="2026-05-08",
    )]
    audit_pngs.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "legacy"


def test_apply_deferrals_skips_current_pngs(tmp_path: Path) -> None:
    """A ``current`` PNG must not be reclassified to ``deferred``
    even when the path-glob happens to match -- deferral is opt-in
    for stale/legacy only."""
    from assistant_axis import deferral_registry
    src = tmp_path / "src.json"; src.write_text("v")
    inputs = [prov.current_file_input("src", src)]
    p = tmp_path / "plot.png"
    _save_envelope_png(p, inputs)

    a = audit_pngs.audit_png(p)
    assert a.status == "current"

    reg = [deferral_registry.DeferralEntry(
        path_glob="plot.png", dep_key=None,
        reason="should not apply", deferred_at="2026-05-08",
    )]
    audit_pngs.apply_deferrals([a], registry=reg, repo_root=tmp_path)
    assert a.status == "current"
