"""Test 14 of coding plan 16 (§ 8): B's ranking.  z-scoring, weights, ties by employment, ``near_corpus``, missing
features at the mean; one row per stem across groups; the distance to the nearest corpus role on a hash-embedder
role index over a fixture corpus (query form ``role_gloss_w14``); the recovery by string over a fixture corpus with
a ``renamed_from``; the CLI's ``rank`` and ``report``.  No network."""
import json
import math

import pytest

from assistant_axis.gapgen.generators.professions import rank as RK
from assistant_axis.gapgen.generators.professions import report as R
from assistant_axis.tests import professions_fakes as F


def row(stem, zipf=None, emp=None, cos=None, role=None):
    return {"role": role or stem.replace("_", " "), "stem": stem, "group": "g", "zipf": zipf, "employment": emp,
            "log_employment": math.log10(emp) if emp else None, "cosine": cos,
            "distance": None if cos is None else 1 - cos}


class TestZscores:
    def test_zscores(self):
        z = RK.zscores([1.0, 2.0, 3.0, None])
        assert z[3] is None and z[1] == 0.0 and z[0] == pytest.approx(-z[2]) and z[2] == pytest.approx(1.2247449)
        assert RK.zscores([5.0, 5.0]) == [0.0, 0.0] and RK.zscores([None]) == [None]

    def test_weights_and_parse(self):
        assert RK.parse_weights(None) == RK.RANK_WEIGHTS
        assert RK.parse_weights("distance=2,zipf=0") == {"zipf": 0.0, "employment": 1.0, "distance": 2.0}
        with pytest.raises(ValueError):
            RK.parse_weights("fame=1")
        with pytest.raises(ValueError):
            RK.parse_weights("zipf")


class TestRank:
    def test_sum_of_z_scores_highest_first(self):
        rows = [row("a", 5.0, 1_000_000, 0.2), row("b", 3.0, 10_000, 0.9), row("c", 4.0, 100_000, 0.5)]
        out = RK.rank(rows)
        assert [r["stem"] for r in out] == ["a", "c", "b"] and [r["rank"] for r in out] == [1, 2, 3]
        a = out[0]
        assert a["z"]["zipf"] == pytest.approx(1.2247, abs=1e-4) and a["z"]["distance"] > 0
        assert a["score"] == pytest.approx(sum(a["z"].values()), abs=1e-3)

    def test_weights_change_the_order(self):
        rows = [row("famous_near", 5.0, 1_000_000, 0.9), row("obscure_far", 3.0, 10_000, 0.1)]
        assert RK.rank(rows)[0]["stem"] == "famous_near"
        assert RK.rank(rows, weights={"zipf": 0, "employment": 0, "distance": 1})[0]["stem"] == "obscure_far"

    def test_ties_by_employment_then_stem(self):
        rows = [row("x", 3.0, 100, 0.5), row("y", 3.0, 100, 0.5), row("w", 3.0, 100, 0.5)]
        rows[1]["employment"] = 200                         # same score (z-scores from log_employment equal)
        out = RK.rank(rows)
        assert [r["stem"] for r in out] == ["y", "w", "x"]

    def test_near_corpus_flagged_and_still_ranked(self):
        out = RK.rank([row("a", 4.0, 1000, 0.75), row("b", 4.0, 1000, 0.74), row("c", 4.0, 1000, None)])
        flags = {r["stem"]: r["near_corpus"] for r in out}
        assert flags == {"a": True, "b": False, "c": False} and len(out) == 3

    def test_missing_features_count_at_the_mean(self):
        out = {r["stem"]: r for r in RK.rank([row("a", 4.0, None, 0.5), row("b", 2.0, 1000, None)])}
        assert out["a"]["missing"] == ["employment"] and out["a"]["z"]["employment"] is None
        assert out["b"]["missing"] == ["distance"]

    def test_familiarity(self):
        f = RK.familiarity({"role": "bouncer"}, zipf=F.fake_zipf, employment=1_000_000)
        assert f == {"zipf": 3.4, "employment": 1_000_000, "log_employment": 6.0}
        assert RK.familiarity({"role": "bouncer"}, zipf=F.fake_zipf, employment=None)["log_employment"] is None


LAY_ROWS = [
    {"group": "broad:35-3010", "kind": "broad", "code": "35-3010", "source_ref": "soc:35-3010", "employment": 650000,
     "zipf": None, "roles": [
        {"role": "bartender", "stem": "bartender", "gloss": "A bartender is someone who pours drinks behind a bar.",
         "support": 3, "distinct_persona": False, "covers": ["35-3011.00"]},
        {"role": "mixologist", "stem": "mixologist", "gloss": "A mixologist is someone who invents cocktails "
         "behind a bar.", "support": 1, "distinct_persona": True, "covers": ["35-3011.00"]}]},
    {"group": "job_title:33-9032.00:bouncer", "kind": "job_title", "code": "33-9032.00",
     "source_ref": "onet_title:33-9032.00:bouncer", "employment": 1120000, "zipf": 3.4, "roles": [
        {"role": "bouncer", "stem": "bouncer", "gloss": "A bouncer is someone who works the door of a bar, checking "
         "IDs and throwing out drunks.", "support": 3, "distinct_persona": True, "covers": ["33-9032.00"]}]},
    {"group": "job_title:35-3011.00:bouncer", "kind": "job_title", "code": "35-3011.00",
     "source_ref": "onet_title:35-3011.00:bouncer", "employment": 650000, "zipf": 3.4, "roles": [
        {"role": "bouncer", "stem": "bouncer", "gloss": None, "support": 2, "distinct_persona": False,
         "covers": ["35-3011.00"]}]},
    {"group": "broad:29-1210", "kind": "broad", "code": "29-1210", "source_ref": "soc:29-1210", "employment": 782430,
     "roles": [{"role": "doctor", "stem": "doctor", "gloss": "A doctor is someone who examines patients and treats "
                "them.", "support": 3, "distinct_persona": False, "covers": []},
               {"role": "academic", "stem": "academic", "gloss": "An academic is someone who studies texts.",
                "support": 1, "distinct_persona": False, "covers": []}]},
]


class TestRows:
    def test_one_row_per_stem_with_every_source(self):
        rows = {r["stem"]: r for r in RK.ranking_rows(LAY_ROWS)}
        b = rows["bouncer"]
        assert [s["source_ref"] for s in b["sources"]] == ["onet_title:33-9032.00:bouncer",
                                                           "onet_title:35-3011.00:bouncer"]
        assert b["group"] == "job_title:33-9032.00:bouncer" and b["employment"] == 1120000 and b["support"] == 3
        assert b["gloss"].startswith("A bouncer is someone who works the door") and b["distinct_persona"] is True
        assert list(rows) == ["bartender", "mixologist", "bouncer", "doctor", "academic"]


class TestDistance:
    def _index(self, tmp_path):
        F.write_role_corpus(tmp_path / "data")
        embed, _ = F.hash_embed()
        idx, info = RK.build_role_index(tmp_path / "data", cfg=F.FakeMetricConfig(), embed=embed)
        return idx, info, embed

    def test_the_role_index_leaves_default_out(self, tmp_path):
        idx, info, _ = self._index(tmp_path)
        # the settings come through roles_pass.role_settings, the reader M3 and R1 use (review finding 2, 2026-10-23)
        assert info["n_roles"] == 10 and "default" not in idx.stems and info["source"].startswith("M2's trait settings")
        assert info["query_form"] == "role_gloss_w14"
        assert info["representation"] == "w20" and info["variant"] == "raw"

    def test_nearest_corpus_role_through_the_role_gloss_query(self, tmp_path):
        idx, _, embed = self._index(tmp_path)
        r = {"role": "barkeep", "gloss": "A barkeep is someone who pours drinks behind a bar and listens to the "
                                         "regulars all night."}
        d = RK.distance(r, role_index=idx, embed=embed)
        assert d["nearest_role"] == "bartender" and 0 < d["cosine"] <= 1 and d["distance"] == pytest.approx(1 - d["cosine"])
        assert not d["query"].lower().startswith("a barkeep is")                 # the opening taken out
        assert len(d["query"].split()) <= 14
        assert RK.distance({"role": "x", "gloss": None}, role_index=idx, embed=embed)["nearest_role"] is None

    def test_rank_roles_end_to_end(self, tmp_path):
        idx, _, embed = self._index(tmp_path)
        out = RK.rank_roles(LAY_ROWS, zipf=F.fake_zipf, role_index=idx, embed=embed)
        by = {r["stem"]: r for r in out}
        assert by["bartender"]["nearest_role"] == "bartender"
        assert all(r["near_corpus"] == (r["cosine"] is not None and r["cosine"] >= 0.75) for r in out)
        assert by["doctor"]["nearest_role"] == "doctor"
        assert sorted(r["rank"] for r in out) == list(range(1, 6))
        assert all(set(r["z"]) == {"zipf", "employment", "distance"} for r in out)
        lines = RK.top_lines(out, 3)
        assert len(lines) == 3 and "nearest" in lines[0]


class TestRecovery:
    def test_recovery_by_string_with_renamed_from(self, tmp_path):
        F.write_role_corpus(tmp_path / "data")
        occ = R.corpus_occupations(tmp_path / "data")
        assert sorted(occ) == ["bartender", "doctor", "judge", "nurse", "pilot", "scholar"]
        assert occ["scholar"] == ["academic"]
        rec = R.recovery_by_string(["Bartender", {"stem": "doctor"}, {"role": "academic"}, "airline pilot",
                                    "chief nurse executive"], occupation_stems=occ)
        assert rec["n"] == 6 and rec["n_recovered"] == 3 and rec["share"] == 0.5
        assert rec["recovered"] == {"bartender": "bartender", "doctor": "doctor", "scholar": "renamed_from:academic"}
        assert rec["missed"] == ["judge", "nurse", "pilot"]
        assert rec["partial"] == {"nurse": ["chief_nurse_executive"], "pilot": ["airline_pilot"]}

    def test_lay_recovery_at_the_broad_level_and_with_titles(self, tmp_path):
        F.write_role_corpus(tmp_path / "data")
        lr = R.lay_recovery(LAY_ROWS, R.corpus_occupations(tmp_path / "data"))
        assert lr["broad"]["n_recovered"] == 3 and lr["all"]["n_recovered"] == 3
        assert set(lr["broad"]["recovered"]) == {"bartender", "doctor", "scholar"}

    def test_title_strings(self):
        assert R.title_strings("Obstetricians and Gynecologists") >= {"obstetrician", "gynecologist"}
        assert "pathologist" in R.title_strings("Physicians, Pathologists")


class TestCli:
    def test_rank_with_the_hash_embedder_and_the_report(self, tmp_path, monkeypatch, capsys):
        import data_analysis.gap_generation.professions_generator as G
        from assistant_axis.gapgen.generators.professions import rank as RKmod
        monkeypatch.setattr(RKmod, "default_zipf", lambda: F.fake_zipf)
        monkeypatch.setattr(G, "_dirty", lambda args: None)
        data, cand = tmp_path / "data", tmp_path / "cand"
        F.write_role_corpus(data)
        rd = cand / "runs" / "professions" / "r1"
        rd.mkdir(parents=True)
        (rd / "lay.jsonl").write_text("".join(json.dumps(r) + "\n" for r in LAY_ROWS))
        base = ["--candidates-dir", str(cand), "--data-dir", str(data), "--registry", str(tmp_path / "reg.jsonl")]
        # the tracked metric config (M2's settings: w20, centred), with the free hash embedder
        code = G.main(base + ["rank", "--run-id", "r1", "--embedder", "hash"])
        assert code == 0
        out = capsys.readouterr().out
        assert "5 lay roles (one per stem)" in out and "hash: local, free" in out
        ranked = [json.loads(x) for x in (rd / "ranking.jsonl").read_text().splitlines()]
        assert [r["rank"] for r in ranked] == [1, 2, 3, 4, 5] and all("nearest_role" in r for r in ranked)
        st = {r["stem"]: (r["net_new"], r["excluded"]) for r in ranked}
        assert st["bouncer"] == (True, None) and st["bartender"] == (False, "corpus_role")
        assert st["academic"] == (False, "corpus_role")                       # scholar's renamed_from
        assert json.loads((rd / "usage.json").read_text())["n_calls"] >= 1        # the free embedder, charged at $0
        assert G.main(base + ["report", "--run-id", "r1"]) == 0
        rep = (rd / "report.md").read_text()
        assert "## The ranking" in rep and "## Recovery by string" in rep
        assert "[bartender](../../../../data/roles/instructions/bartender.json)" in rep
        assert "[table.jsonl](./table.jsonl) (not there yet)" in rep
