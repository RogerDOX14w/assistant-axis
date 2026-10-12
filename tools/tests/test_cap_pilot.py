"""The cap pilot's tooling (walk-through P6, 2026-10-12): the entity-list
builder and the four-tree comparison, on fake corpora and fake trees.  No
model, no API; the pilot itself is not run."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import cap_pilot_compare as cmp  # noqa: E402
from tools import cap_pilot_entities as ent  # noqa: E402


# ---------------------------------------------------------------------------
# The entity list
# ---------------------------------------------------------------------------

@pytest.fixture
def corpus(tmp_path):
    roles, traits, lengths = tmp_path / "roles", tmp_path / "traits", tmp_path / "lengths"
    for d in (roles, traits, lengths):
        d.mkdir()
    role_names = [f"role{i:02d}" for i in range(30)] + ["angel", "patient", "default"]
    trait_names = [f"trait{i:02d}" for i in range(30)] + ["verbose", "concise", "patient"]
    for n in role_names:
        (roles / f"{n}.json").write_text("{}")
    for n in trait_names:
        (traits / f"{n}.json").write_text("{}")
    for i, n in enumerate(role_names):          # role29 longest, role00 shortest
        text = "x" * (100 + 10 * i if n.startswith("role") else 50)
        (lengths / f"{n}.jsonl").write_text(
            json.dumps({"conversation": [{"role": "assistant", "content": text}]}) + "\n")
    goal = tmp_path / "goal.json"
    goal.write_text(json.dumps({
        "roles": {"goal": ["angel"] + role_names[:6], "non_goal": role_names[6:12]},
        "traits": {"goal": trait_names[:6], "non_goal": ["concise"] + trait_names[6:12] + ["verbose"]}}))
    return {"roles_dir": roles, "traits_dir": traits, "goal_file": goal, "lengths_tree": lengths}


def test_the_list_has_the_plans_strata(corpus):
    out = ent.build(seed=1, **corpus)
    st = out["strata"]
    assert len(out["all"]) == len(set(out["all"])) == 64
    # the 8 narrative roles are the longest by recorded median length
    assert st["roles_narrative"] == [f"role{i:02d}" for i in range(29, 21, -1)]
    assert len(st["roles"]) == 12 and not set(st["roles"]) & set(st["roles_narrative"])
    assert len(st["traits"]) == 20 and st["traits_outliers"] == ["verbose", "concise"]
    assert st["combinations_outliers"] == ["r_angel__verbose", "r_angel__concise"]
    combos = st["combinations"]
    assert len(combos) == 20 and sum(c.startswith("r_") for c in combos) == 10
    assert not any(c.endswith(("__verbose", "__concise")) for c in combos)
    # a name of both kinds, and default, are never drawn
    assert "patient" not in out["all"] and "default" not in out["all"]
    assert out["excluded_collision_names"] == ["patient"]
    assert out["by_type"]["role"] == st["roles_narrative"] + st["roles"]


def test_the_list_is_reproducible_from_its_seed(corpus):
    a, b, c = ent.build(seed=7, **corpus), ent.build(seed=7, **corpus), ent.build(seed=8, **corpus)
    assert a["all"] == b["all"] and a["all"] != c["all"]


def test_the_cli_refuses_to_overwrite(corpus, tmp_path):
    args = ["--output", str(tmp_path / "list.json")] + [
        x for k, v in corpus.items() for x in (f"--{k}", str(v))]
    assert ent.main(args) == 0
    assert ent.main(args) == 1
    assert ent.main(args + ["--force"]) == 0


def test_the_committed_list_matches_the_plan():
    out = json.loads((REPO / "reports" / "pipeline" / "cap_pilot_entities.json").read_text())
    assert out["seed"] == ent.DEFAULT_SEED and len(out["all"]) == 64
    assert out["strata"]["traits_outliers"] == ["verbose", "concise"]
    assert out["strata"]["combinations_outliers"] == ["r_angel__verbose", "r_angel__concise"]


# ---------------------------------------------------------------------------
# The comparison, on fake trees
# ---------------------------------------------------------------------------

STRATA = {"roles_narrative": ["r1"], "roles": ["r2", "r3"], "traits": ["t1", "t2", "t3"],
          "traits_outliers": ["verbose", "concise"], "combinations": ["c1", "c2", "c3"],
          "combinations_outliers": ["r_angel__verbose", "r_angel__concise"]}
NAMES = [n for v in STRATA.values() for n in v]
SHAPE = (8, 30, 16)


def _entities(tmp_path):
    e = {"seed": 1, "strata": STRATA, "all": NAMES}
    p = tmp_path / "entities.json"
    p.write_text(json.dumps(e))
    return p, e


def _trees(tmp_path, *, noise: dict, share3: dict, trunc: dict, broken=()):
    """Vectors: a common direction (dominant, as in real activation means) +
    an entity's own direction + noise of size ``noise[cap]``; scores with
    the score-3 share ``share3[cap]``; ``trunc[cap]`` of responses cut."""
    g = torch.Generator().manual_seed(0)
    common = torch.randn(SHAPE, generator=g) * 100
    own = {n: torch.randn(SHAPE, generator=g) for n in NAMES}
    trees = {}
    for cap in cmp.CAPS:
        t = tmp_path / f"cap{cap}"
        for sub in ("responses", "scores", "vectors"):
            (t / sub).mkdir(parents=True)
        for n in NAMES:
            v = common + own[n] + noise[cap] * torch.randn(SHAPE, generator=g)
            torch.save({"vector": v.float(), "type": "pos_3"}, t / "vectors" / f"{n}.pt")
            k3 = round(100 * share3[cap])
            (t / "scores" / f"{n}.json").write_text(
                json.dumps({f"pos_p0_q{i}": 3 if i < k3 else 2 for i in range(100)}))
            kl = round(10 * trunc[cap])
            (t / "responses" / f"{n}.jsonl").write_text("".join(
                json.dumps({"finish_reason": "length" if i < kl else "stop"}) + "\n"
                for i in range(10)))
        trees[cap] = t
    return trees


def _run(tmp_path, trees, *extra):
    ent_file, _ = _entities(tmp_path)
    out = tmp_path / "readout.md"
    rc = cmp.main(["--trees", *[f"{c}={p}" for c, p in trees.items()], "--entities", str(ent_file),
                   "--output", str(out), "--traits_dir", str(tmp_path / "no_traits"), *extra])
    return rc, out


def test_keep_512_when_it_meets_the_rule(tmp_path):
    trees = _trees(tmp_path, noise={256: 0.5, 512: 0.02, 768: 0.01, 1024: 0.0},
                   share3={256: 0.70, 512: 0.80, 768: 0.80, 1024: 0.81},
                   trunc={256: 0.9, 512: 0.7, 768: 0.3, 1024: 0.1})
    rc, out = _run(tmp_path, trees)
    assert rc == 0
    data = json.loads(out.with_suffix(".json").read_text())
    assert data["decision"] == 512
    text = out.read_text()
    assert "**Cap: 512.**" in text and "512: meets the rule" in text
    s = data["summaries"]["traits"]
    assert s["512"]["truncation"] == pytest.approx(0.7) and s["512"]["d_share3"] == pytest.approx(-0.01)
    assert s["256"]["cos0_centred"] < 0.99 < s["512"]["cos0_centred"]
    # raw cosines are near 1 at every cap (the shared direction): why the rule uses centred ones
    assert s["256"]["cos0_raw"] > 0.999
    assert "| verbose / concise |" in text                     # the pair axis
    assert "| verbose | 256 |" in text and "| r_angel__concise | 1024 |" in text


def test_take_768_when_512_moves_the_score3_share(tmp_path):
    trees = _trees(tmp_path, noise={256: 0.5, 512: 0.02, 768: 0.01, 1024: 0.0},
                   share3={256: 0.60, 512: 0.75, 768: 0.80, 1024: 0.80},
                   trunc={256: 0.9, 512: 0.7, 768: 0.3, 1024: 0.1})
    rc, out = _run(tmp_path, trees)
    data = json.loads(out.with_suffix(".json").read_text())
    assert data["decision"] == 768 and data["verdicts"]["512"] is False


def test_take_1024_when_768_misses_the_cosine(tmp_path):
    trees = _trees(tmp_path, noise={256: 0.6, 512: 0.5, 768: 0.4, 1024: 0.0},
                   share3={c: 0.8 for c in cmp.CAPS}, trunc={c: 0.1 for c in cmp.CAPS})
    rc, out = _run(tmp_path, trees)
    assert json.loads(out.with_suffix(".json").read_text())["decision"] == 1024


def test_outliers_do_not_decide(tmp_path):
    trees = _trees(tmp_path, noise={256: 0.5, 512: 0.02, 768: 0.01, 1024: 0.0},
                   share3={c: 0.8 for c in cmp.CAPS}, trunc={c: 0.1 for c in cmp.CAPS})
    # verbose at 512 far from its 1024 vector, and its score-3 share moved
    v = torch.load(trees[512] / "vectors" / "verbose.pt", weights_only=False)
    v["vector"] = torch.randn(SHAPE) * 100
    torch.save(v, trees[512] / "vectors" / "verbose.pt")
    (trees[512] / "scores" / "verbose.json").write_text(json.dumps({f"k{i}": 0 for i in range(10)}))
    rc, out = _run(tmp_path, trees)
    assert json.loads(out.with_suffix(".json").read_text())["decision"] == 512


def test_run_sanity_with_a_repeat(tmp_path):
    trees = _trees(tmp_path, noise={256: 0.5, 512: 0.02, 768: 0.01, 1024: 0.0},
                   share3={c: 0.8 for c in cmp.CAPS}, trunc={c: 0.1 for c in cmp.CAPS})
    rc, out = _run(tmp_path, trees, "--repeat", f"512={trees[512]}")
    assert "min 1.00000" in out.read_text() and "(ok)" in out.read_text()


def test_missing_scores_leave_the_decision_open(tmp_path):
    trees = _trees(tmp_path, noise={c: 0.0 for c in cmp.CAPS},
                   share3={c: 0.8 for c in cmp.CAPS}, trunc={c: 0.1 for c in cmp.CAPS})
    for n in STRATA["traits"]:
        (trees[512] / "scores" / f"{n}.json").unlink()
    rc, out = _run(tmp_path, trees)
    assert json.loads(out.with_suffix(".json").read_text())["decision"] is None
    assert "**Undecided**" in out.read_text()


def test_a_missing_tree_is_an_error(tmp_path):
    trees = _trees(tmp_path, noise={c: 0.0 for c in cmp.CAPS},
                   share3={c: 0.8 for c in cmp.CAPS}, trunc={c: 0.1 for c in cmp.CAPS})
    del trees[768]
    rc, _ = _run(tmp_path, trees)
    assert rc == 1


def test_records_without_finish_reason_give_no_truncation_share(tmp_path):
    f = tmp_path / "r.jsonl"
    f.write_text(json.dumps({"label": "pos"}) + "\n")
    assert cmp.truncation_share(f) is None
