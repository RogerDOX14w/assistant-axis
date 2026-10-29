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


def _write_scores(path, share3: float):
    """100 scores, the first ``round(100 * share3)`` of them 3."""
    k3 = round(100 * share3)
    path.write_text(json.dumps({f"pos_p0_q{i}": 3 if i < k3 else 2 for i in range(100)}))


def _trees(tmp_path, *, noise: dict, share3: dict, trunc: dict, broken=(), scale=None):
    """Vectors: a common direction (dominant, as in real activation means) +
    an entity's own direction (times ``scale[cap]``, default 1) + noise of
    size ``noise[cap]``; scores with the score-3 share ``share3[cap]`` (a
    number, or a dict by entity); ``trunc[cap]`` of responses cut."""
    g = torch.Generator().manual_seed(0)
    common = torch.randn(SHAPE, generator=g) * 100
    own = {n: torch.randn(SHAPE, generator=g) for n in NAMES}
    trees = {}
    for cap in cmp.CAPS:
        t = tmp_path / f"cap{cap}"
        for sub in ("responses", "scores", "vectors"):
            (t / sub).mkdir(parents=True)
        for n in NAMES:
            v = common + (scale or {}).get(cap, 1.0) * own[n] + noise[cap] * torch.randn(
                SHAPE, generator=g)
            torch.save({"vector": v.float(), "type": "pos_3"}, t / "vectors" / f"{n}.pt")
            sh = share3[cap][n] if isinstance(share3[cap], dict) else share3[cap]
            _write_scores(t / "scores" / f"{n}.json", sh)
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
    assert s["256"]["cos0_centred"] < cmp.COSINE_MIN < s["512"]["cos0_centred"]
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


# ---------------------------------------------------------------------------
# The 2026-10-28 additions: the norm rule, the floor and σ, the 4σ flags,
# --extra_scores, --vectors_all and --prefix_means
# ---------------------------------------------------------------------------

QUIET = {256: 0.5, 512: 0.0, 768: 0.0, 1024: 0.0}      # 512 and 768 pass the cosine rule


def _load_json(out):
    return json.loads(out.with_suffix(".json").read_text())


@pytest.mark.parametrize("scale, decision", [(1.15, 768), (1.05, 512)])
def test_the_norm_rule_decides(tmp_path, scale, decision):
    # 512 is the 1024 vector with its own direction 15% (or 5%) longer: the
    # centred cosine is 1 and the share unmoved, so only the norm rule can
    # refuse it.
    trees = _trees(tmp_path, noise=QUIET, share3={c: 0.8 for c in cmp.CAPS},
                   trunc={c: 0.1 for c in cmp.CAPS}, scale={512: scale})
    rc, out = _run(tmp_path, trees)
    data = _load_json(out)
    s = data["summaries"]["traits"]["512"]
    assert s["cos0_centred"] == pytest.approx(1.0, abs=1e-9) and s["d_share3"] == 0
    assert s["norm_shift"] == pytest.approx(scale - 1, abs=1e-5)
    assert abs(s["norm_shift_raw"]) < 0.01                 # the common direction hides it raw
    assert data["decision"] == decision and data["verdicts"]["512"] is (decision == 512)
    assert "| traits | 512 |" in out.read_text() and f"{100 * (scale - 1):+.1f}%" in out.read_text()


def _repeat_tree(tmp_path, trees, shares: dict, *, noise=0.0):
    """A second 512 tree: 512's vectors (plus ``noise``), scores with
    ``shares[name]`` (default 0.8), 512's responses."""
    g = torch.Generator().manual_seed(1)
    t = tmp_path / "cap512b"
    for sub in ("responses", "scores", "vectors"):
        (t / sub).mkdir(parents=True)
    for n in NAMES:
        v = torch.load(trees[512] / "vectors" / f"{n}.pt", weights_only=False)
        v["vector"] = v["vector"] + noise * torch.randn(SHAPE, generator=g)
        torch.save(v, t / "vectors" / f"{n}.pt")
        _write_scores(t / "scores" / f"{n}.json", shares.get(n, 0.8))
        (t / "responses" / f"{n}.jsonl").write_bytes(
            (trees[512] / "responses" / f"{n}.jsonl").read_bytes())
    return t


# repeat minus 512, by entity: σ roles 0.02, traits 0.01, combinations 0.03;
# the outliers' large moves stay out of σ.
FLOOR_OFFSETS = {"r1": 0.02, "r2": -0.02, "r3": 0.0, "t1": 0.01, "t2": -0.01, "t3": 0.0,
                 "c1": 0.03, "c2": 0.0, "c3": -0.03, "verbose": 0.2, "concise": -0.2}


def test_the_floor_and_sigma_from_a_repeat_tree(tmp_path):
    trees = _trees(tmp_path, noise=QUIET, share3={c: 0.8 for c in cmp.CAPS},
                   trunc={c: 0.1 for c in cmp.CAPS})
    rep = _repeat_tree(tmp_path, trees, {n: 0.8 + d for n, d in FLOOR_OFFSETS.items()},
                       noise=0.02)
    rc, out = _run(tmp_path, trees, "--repeat", f"512={rep}")
    assert rc == 0
    fl = _load_json(out)["floor"]
    assert fl["sigma"]["roles"] == pytest.approx(0.02)
    assert fl["sigma"]["traits"] == pytest.approx(0.01)
    assert fl["sigma"]["combinations"] == pytest.approx(0.03)
    assert fl["per_entity"]["verbose"]["d_share3"] == pytest.approx(0.2)
    # every measure of the floor, per stratum: share, cosines, norm
    s = fl["summaries"]["traits"]
    assert s["d_share3"] == pytest.approx(0.0, abs=1e-12)
    assert 0.9 < s["cos0_centred"] < 1.0 and s["cos0_raw"] > 0.9999
    assert s["cos_header_centred"] < 1.0 and s["norm_shift"] is not None
    text = out.read_text()
    assert "| traits | floor 512′ vs 512 |" in text
    assert "| traits | 1.00 | 4.0 |" in text                 # σ and 4σ in points
    # The run sanity stays on raw cosines, which the common direction keeps
    # above 0.999 under this noise; the centred floor above shows it.
    assert "## Run sanity" in text and "(ok)" in text


def test_four_sigma_flags_one_entity_and_not_another(tmp_path):
    # At 768, t1 moves by 5σ of the traits (σ = 1 point) and t2 by 2σ.
    shares = {c: 0.8 for c in cmp.CAPS}
    shares[768] = {n: 0.8 for n in NAMES}
    shares[768].update({"t1": 0.85, "t2": 0.82})
    trees = _trees(tmp_path, noise=QUIET, share3=shares, trunc={c: 0.1 for c in cmp.CAPS})
    rep = _repeat_tree(tmp_path, trees, {n: 0.8 + d for n, d in FLOOR_OFFSETS.items()})
    extra = tmp_path / "cap768_rejudge"
    extra.mkdir()
    _write_scores(extra / "t1.json", 0.85)             # t1 judged twice at 768
    rc, out = _run(tmp_path, trees, "--repeat", f"512={rep}", "--extra_scores", f"768={extra}")
    flags = _load_json(out)["flags"]
    assert [(f["entity"], f["cap"]) for f in flags] == [("t1", 768)]
    f = flags[0]
    assert f["type"] == "traits" and f["sigma"] == pytest.approx(0.01)
    assert f["z"] == pytest.approx(5.0) and f["judgings_cap"] == 2 and f["averaged"] is True
    text = out.read_text()
    assert "| t1 | traits | 768 | +5.0 | 1.00 | +5.0 | 2 / 1 | yes |" in text
    # Without --repeat there is no σ, so no flags, and the readout says why.
    rc, out = _run(tmp_path, trees)
    assert _load_json(out)["flags"] is None
    assert "without `--repeat` there is no σ" in out.read_text()


def test_the_share_table_lists_each_type_lowest_first(tmp_path):
    shares = {c: {n: 0.8 for n in NAMES} for c in cmp.CAPS}
    shares[1024].update({"t1": 0.9, "t2": 0.3, "t3": 0.6, "verbose": 0.5})
    shares[512].update({"t2": 0.25})
    trees = _trees(tmp_path, noise=QUIET, share3=shares, trunc={c: 0.1 for c in cmp.CAPS})
    rc, out = _run(tmp_path, trees)
    text = out.read_text()
    section = text.split("## Score-3 share per entity, lowest first")[1].split("\n## ")[0]
    traits = section.split("**Traits**")[1].split("**Combinations**")[0]
    rows = [line.split(" | ")[0].lstrip("| ") for line in traits.splitlines() if line.startswith("| ")][1:]
    assert rows == ["t2", "verbose *(outlier)*", "t3", "concise *(outlier)*", "t1"]
    assert "| t2 | 80.0% | 25.0% | 80.0% | 30.0% | +50.0 | -5.0 | +50.0 |" in traits
    assert "**Roles**" in section and "| r1 |" in section


def test_entity_links_are_relative_to_the_readout():
    out = cmp.REPO / "reports" / "pipeline" / "readout.md"      # not written
    assert cmp.linked_entity("bold", out) == "[bold](../../data/traits/instructions/bold.json)"
    assert cmp.linked_entity("actor", out) == "[actor](../../data/roles/instructions/actor.json)"
    assert cmp.linked_entity("r_angel__verbose", out) == (
        "r_[angel](../../data/roles/instructions/angel.json)__"
        "[verbose](../../data/traits/instructions/verbose.json)")
    assert cmp.linked_entity("no_such_entity", out) == "no_such_entity"
    assert cmp.linked_entity("bold", Path("/elsewhere/readout.md")) == "bold"


def test_extra_scores_average_the_judgings_and_give_the_judge_only_floor(tmp_path):
    trees = _trees(tmp_path, noise=QUIET, share3={c: 0.8 for c in cmp.CAPS},
                   trunc={c: 0.1 for c in cmp.CAPS})
    rejudge = tmp_path / "scores_rejudge"
    rejudge.mkdir()
    for n, sh in {"t1": 0.70, "t2": 0.80, "t3": 0.90}.items():
        _write_scores(rejudge / f"{n}.json", sh)
    rc, out = _run(tmp_path, trees, "--extra_scores", f"512={rejudge}")
    data = _load_json(out)
    t1, t2 = data["per_entity"]["t1"]["512"], data["per_entity"]["r1"]["512"]
    assert t1["scores"]["share3"] == pytest.approx(0.75) and t1["scores"]["n_judgings"] == 2
    assert t1["scores"]["share3_judgings"] == [0.8, 0.7]
    assert t1["d_share3"] == pytest.approx(-0.05)
    assert t2["scores"]["n_judgings"] == 1                    # no extra file: one judging
    assert data["summaries"]["traits"]["512"]["d_share3"] == pytest.approx(0.0, abs=1e-12)
    jf = data["judge_floor"]
    assert jf["sd"]["traits"] == pytest.approx(0.1) and jf["n"]["traits"] == 3
    assert jf["sd"]["roles"] is None and jf["n"]["roles"] == 0
    text = out.read_text()
    assert "| t1 | traits | 1 / 2 / 1 / 1 |" in text        # judgings per cap, per entity
    assert "Judge-only SD" in text and "traits 10.00" in text


def test_a_missing_input_directory_is_an_error(tmp_path):
    trees = _trees(tmp_path, noise=QUIET, share3={c: 0.8 for c in cmp.CAPS},
                   trunc={c: 0.1 for c in cmp.CAPS})
    assert _run(tmp_path, trees, "--extra_scores", f"512={tmp_path / 'nope'}")[0] == 1
    assert _run(tmp_path, trees, "--vectors_all", f"300={trees[512] / 'vectors'}")[0] == 1


def _vec(tree, n):
    return torch.load(tree / "vectors" / f"{n}.pt", weights_only=False)["vector"]


def test_vectors_all_gives_selection_alone(tmp_path):
    trees = _trees(tmp_path, noise=QUIET, share3={c: 0.8 for c in cmp.CAPS},
                   trunc={c: 0.1 for c in cmp.CAPS})
    deciding = [n for k in cmp.DECIDING_STRATA for n in
                (STRATA["roles_narrative"] + STRATA["roles"] if k == "roles" else STRATA[k])]
    # 512: the all-response vector is the selected one (selection changed
    # nothing); 768: the all-response vectors are the selected ones spread
    # 1.25 times as far from their mean (selected/all = 0.8: a -20% norm).
    a512, a768 = tmp_path / "all512", tmp_path / "all768"
    a512.mkdir()
    a768.mkdir()
    m768 = torch.stack([_vec(trees[768], n) for n in deciding]).double().mean(0)
    for n in NAMES:
        marker = {"all_responses": True, "n_responses": 100}
        torch.save({"vector": _vec(trees[512], n), "type": "all_responses", "metadata": marker},
                   a512 / f"{n}.pt")
        v = _vec(trees[768], n).double()
        torch.save({"vector": (m768 + 1.25 * (v - m768)).float(), "type": "all_responses",
                    "inputs": marker}, a768 / f"{n}.pt")
    rc, out = _run(tmp_path, trees, "--vectors_all", f"512={a512}", "--vectors_all", f"768={a768}")
    sel = _load_json(out)["selection"]
    s512, s768 = sel["512"]["summaries"]["traits"], sel["768"]["summaries"]["traits"]
    assert s512["cos0_centred"] == pytest.approx(1.0) and s512["cos0_raw"] == pytest.approx(1.0)
    assert s512["norm_shift"] == pytest.approx(0.0, abs=1e-9)
    assert s512["cos_header_centred"] == pytest.approx(1.0)
    assert s768["cos0_centred"] == pytest.approx(1.0, abs=1e-6)
    assert s768["norm_shift"] == pytest.approx(0.8 - 1, abs=1e-5)
    assert sel["512"]["not_marked_all_responses"] == [] == sel["768"]["not_marked_all_responses"]
    text = out.read_text()
    assert "**Selection alone**" in text and "| traits | 768 |" in text and "-20.0%" in text


def test_prefix_means_give_content_alone(tmp_path):
    trees = _trees(tmp_path, noise=QUIET, share3={c: 0.8 for c in cmp.CAPS},
                   trunc={c: 0.1 for c in cmp.CAPS})
    layer = cmp.DEFAULT_LAYER
    deciding = [n for n in NAMES if n not in STRATA["traits_outliers"]
                + STRATA["combinations_outliers"]]
    full = {n: _vec(trees[1024], n)[0, layer].double() for n in NAMES}
    m = torch.stack([full[n] for n in deciding]).mean(0)
    pdir = tmp_path / "prefix_means"
    pdir.mkdir()
    g = torch.Generator().manual_seed(2)
    for n in NAMES:
        scores = json.loads((trees[1024] / "scores" / f"{n}.json").read_text())
        data, short = {}, {}
        for i, (k, s) in enumerate(scores.items()):
            if s == 3:
                # N = 256: the full mean itself; N = 512: 0.9 of the way from
                # the pilot mean (cos 1, norm -10%); half of them short of 512.
                rows = torch.stack([full[n], m + 0.9 * (full[n] - m)])
            else:                       # not selected by the judge: must not count
                rows = 1000 * torch.randn(2, SHAPE[2], generator=g, dtype=torch.float64)
            data[k] = rows.unsqueeze(1).float()          # (N, 1 layer, hidden)
            short[k] = [False, i < 40]
        data["metadata"] = {"prefix_tokens": [256, 512], "layers": [layer], "short": short}
        torch.save(data, pdir / f"{n}.pt")
    rc, out = _run(tmp_path, trees, "--prefix_means", f"1024={pdir}")
    ct = _load_json(out)["content"]
    assert ct["prefix_tokens"] == [256, 512]
    s256, s512 = ct["summaries"]["256"]["traits"], ct["summaries"]["512"]["traits"]
    assert s256["cos0_centred"] == pytest.approx(1.0, abs=1e-6)
    assert s256["cos0_raw"] == pytest.approx(1.0, abs=1e-6)
    assert s256["norm_shift"] == pytest.approx(0.0, abs=1e-5)
    assert s512["cos0_centred"] == pytest.approx(1.0, abs=1e-6)
    assert s512["norm_shift"] == pytest.approx(-0.1, abs=1e-5)
    assert s256["short_share"] == 0 and s512["short_share"] == pytest.approx(0.5)
    assert ct["per_entity"]["512"]["t1"]["n_selected"] == 80
    text = out.read_text()
    assert "**Content alone**" in text and "| traits | 512 |" in text and "-10.0%" in text


def test_prefix_means_note_a_file_without_the_layer(tmp_path):
    trees = _trees(tmp_path, noise=QUIET, share3={c: 0.8 for c in cmp.CAPS},
                   trunc={c: 0.1 for c in cmp.CAPS})
    pdir = tmp_path / "prefix_means"
    pdir.mkdir()
    torch.save({"pos_p0_q0": torch.zeros(1, 1, SHAPE[2]),
                "metadata": {"prefix_tokens": [256], "layers": [3]}}, pdir / "t1.pt")
    rc, out = _run(tmp_path, trees, "--prefix_means", f"1024={pdir}")
    assert rc == 0 and "t1: layer 25 is not in its prefix file" in out.read_text()
