"""The review graph's sibling groups (plan 09 section 12 item 3; Roger, 2026-10-13: "Sounds good"): the structural
generator's answers for one trait (its opposite, excess, deficiency and principal-target items) shown as one group,
read from the generator's operator table when it exists, never merged and touching no other edge or group.  On the
toy graph of test_gapgen_review_graph.py (no API call: the fake client)."""
import json

from assistant_axis.gapgen import review_graph as RG
from assistant_axis.tests.test_gapgen_review_graph import build


def src(trait, op, *, target=None, kind=None):
    s = {"generator_part": "operators", "source_stem": trait, "operator": op,
         "kind": kind or ("degree_filler" if op in ("excess", "deficiency") else op)}
    if target:
        s["target"] = target
    return s


def table_row(stem, *sources):
    return {"stem": stem, "label": stem.replace("_", " "), "sources": list(sources)}


TABLE = [
    # three answers for the trait "worldly": the opposite, the excess and a principal-target retarget
    table_row("godless", src("worldly", "opposite")),
    table_row("irreligious", src("worldly", "excess")),
    table_row("pious", src("worldly", "retarget", target="the_user", kind="principal_retarget"),
              src("devoted", "deficiency")),
    # an ordinary retarget is no sibling; one answer alone makes no group
    table_row("skeptic", src("worldly", "retarget", target="self", kind="retarget"), src("doubting", "opposite")),
    # a classical source is no operator answer; a row whose stem is no kept candidate is skipped
    table_row("devout", {"generator_part": "classical", "source_id": "aristotle:x:mean", "role": "mean"}),
    table_row("not_in_graph", src("worldly", "deficiency")),
]


def test_sibling_groups_from_the_operator_table():
    keys = ["godless#1", "irreligious#1", "pious#1", "skeptic#1", "devout#1"]
    groups = RG.sibling_groups(keys, TABLE)
    assert groups == [{"trait": "trait:worldly", "members": ["godless#1", "irreligious#1", "pious#1"],
                       "roles": {"godless#1": ["opposite"], "irreligious#1": ["excess"],
                                 "pious#1": ["retarget:the_user"]}}]
    assert RG.sibling_groups(keys, []) == []


def test_a_toy_graph_carries_them_and_changes_nothing_else(tmp_path, monkeypatch):
    monkeypatch.setattr(RG, "structural_operator_table", lambda: [])
    plain, _, _ = build(tmp_path, name="plain")
    monkeypatch.setattr(RG, "structural_operator_table", lambda: TABLE)
    g, _, _ = build(tmp_path, name="with")
    assert [x["members"] for x in g.sibling_groups] == [["godless#1", "irreligious#1", "pious#1"]]
    # the edges, the merged and proposed groups and the stats are those of the graph without the table
    a, b = plain.to_json(), g.to_json()
    assert "sibling_groups" not in a and b.pop("sibling_groups") == g.sibling_groups
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    # graph.json round trip
    back = RG.Graph.from_json(json.loads(json.dumps(g.to_json())))
    assert back.sibling_groups == g.sibling_groups and RG.Graph.from_json(a).sibling_groups == []


def test_no_operator_table_no_groups(tmp_path, monkeypatch):
    """Behind the table's presence: with no operator table on disk the graph is written as before."""
    from assistant_axis.gapgen.generators import structural as S
    monkeypatch.setattr(S, "OPERATOR_TABLE_PATH", tmp_path / "absent" / "operator_table.jsonl")
    assert RG.structural_operator_table() == []
    g, _, _ = build(tmp_path)
    assert g.sibling_groups == [] and "sibling_groups" not in g.to_json()
