"""Structural generators, A: the hand-typed classical tables (coding_plan_09 section 8, ``classical``; tasks 1-2)."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from assistant_axis.gapgen.generators.structural import classical as C


@pytest.fixture(scope="module")
def rows():
    return C.load_all()


def test_every_scheme_loads(rows):
    assert {r.scheme for r in rows} == set(C.SCHEMES)
    for s in C.SCHEMES:
        assert C.load_classical(s), s


def test_tables_are_valid(rows):
    assert C.validate(rows) == []


def test_counts(rows):
    """12-14 Aristotle triples, 30 Theophrastus, 7 + 7 + 7 sins and virtues, 24 x 3 VIA, 20 Murray x 2."""
    c = C.counts(rows)
    assert 12 <= c["aristotle"]["groups"] <= 14 and c["aristotle"]["rows"] == 3 * c["aristotle"]["groups"]
    assert c["aristotle"]["roles"] == {"deficiency": c["aristotle"]["groups"], "mean": c["aristotle"]["groups"],
                                      "excess": c["aristotle"]["groups"]}
    assert c["theophrastus"] == {"rows": 30, "groups": 30, "roles": {"vice": 30}}
    assert c["sins_virtues"]["rows"] == 21 and c["sins_virtues"]["roles"] == {"sin": 7, "virtue": 14}
    assert c["via"]["rows"] == 72 and c["via"]["groups"] == 24
    assert c["via"]["roles"] == {"strength": 24, "underuse": 24, "overuse": 24}
    assert c["murray"]["rows"] == 40 and c["murray"]["roles"] == {"need_high": 20, "need_low": 20}
    for s, (lo, hi) in C.EXPECTED_COUNTS.items():
        assert lo <= c[s]["rows"] <= hi, s


def test_roles_legal_per_scheme(rows):
    for r in rows:
        assert r.role in C.ROLES_BY_SCHEME[r.scheme], r.id
    bad = replace(rows[0], role="virtue")
    assert any("role" in p for p in C.validate([bad, *rows[1:]]))


def test_aristotelian_triples_have_one_mean_and_two_vices(rows):
    ari = [r for r in rows if r.scheme == "aristotle"]
    groups = {}
    for r in ari:
        groups.setdefault(r.group, []).append(r.role)
    for g, roles in groups.items():
        assert sorted(roles) == ["deficiency", "excess", "mean"], g
    # two means in one triple is refused
    mean = next(r for r in ari if r.role == "mean")
    exc = next(r for r in ari if r.role == "excess" and r.group == mean.group)
    broken = [replace(exc, role="mean") if r.id == exc.id else r for r in ari]
    assert any("one mean and two vices" in p for p in C.validate(broken))


def test_every_sibling_resolves_and_is_mutual(rows):
    by = {r.id: r for r in rows}
    for r in rows:
        for s in r.sibling_ids:
            assert s in by and r.id in by[s].sibling_ids, (r.id, s)
    first = next(r for r in rows if r.sibling_ids)
    dangling = replace(first, sibling_ids=(*first.sibling_ids, "aristotle:nowhere:mean"))
    probs = C.validate([dangling if r.id == first.id else r for r in rows])
    assert any("does not resolve" in p for p in probs)


def test_via_is_refused_while_unverified_and_accepted_when_verified(rows, tmp_path):
    via = [r for r in rows if r.scheme == "via"]
    # the file's rows were checked against the source on 2026-10-13, so the shipped table passes the gate
    assert C.verification_state(rows)["via"] == {"n": 72, "verified": 72, "unverified": 0, "gated": True}
    assert all(r.verified_by and "source check" in r.verified_by for r in via)
    C.require_verified(rows)
    unverified = [replace(r, verified_by=None) for r in via]               # the state the table was typed in
    assert C.verification_state(unverified)["via"]["unverified"] == 72
    with pytest.raises(C.SchemeUnverified):
        C.require_verified([*unverified, *(r for r in rows if r.scheme != "via")])
    with pytest.raises(C.SchemeUnverified):
        C.require_verified(unverified, ["via"])
    C.require_verified([r for r in rows if r.scheme != "via"])             # the other schemes are not gated
    verified = [replace(r, verified_by="Roger, 2026-10-14") for r in unverified]
    C.require_verified(verified)
    one_left = [replace(r, verified_by=None) if i == 5 else r for i, r in enumerate(verified)]
    with pytest.raises(C.SchemeUnverified):
        C.require_verified(one_left)
    # through the files as well
    d = tmp_path / "classical"
    d.mkdir()
    (d / "via.json").write_text(json.dumps([r.as_dict() for r in verified]), encoding="utf-8")
    C.require_verified(C.load_classical("via", classical_dir=d))


def test_sins_pair_with_their_contrary_virtues(rows):
    by = {r.id: r for r in rows}
    sins = [r for r in rows if r.role == "sin"]
    assert len(sins) == 7
    for s in sins:
        assert len(s.sibling_ids) == 1 and by[s.sibling_ids[0]].role == "virtue"


def test_row_schema_round_trips(rows):
    for r in rows[:20]:
        d = r.as_dict()
        assert d["schema_version"] == 1 and isinstance(d["sibling_ids"], list)
        assert C._row(d) == r
