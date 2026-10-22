"""Test 12 of coding plan 16 (§ 8): SOC codes, the OEWS table, the broad groups and the job-title cut.
``broad_code`` on O*NET and SOC codes (with SOC 2018's Physicians spill-over); ``read_oews_national`` on a fixture
workbook (needs openpyxl: skipped without it) and its clear error naming ``uv add openpyxl``; the CSV and JSON
reader; ``broad_groups`` (a group per broad code with its detailed occupations and employment; 459 on the real
O*NET file when it is on disk, skipped otherwise); ``lay_title_candidates`` applies the cut; ``build`` writes the
table.  No network."""
import io
import json
import sys
import zipfile

import pytest

from assistant_axis.gapgen.generators.professions import onet as O
from assistant_axis.gapgen.generators.professions import soc as SOC
from assistant_axis.gapgen.paths import DATA_EXTERNAL
from assistant_axis.tests import professions_fakes as F


class TestCodes:
    def test_broad_code(self):
        assert SOC.broad_code("29-1212.00") == "29-1210"
        assert SOC.broad_code("29-1212") == "29-1210"
        assert SOC.broad_code("29-1210") == "29-1210"
        assert SOC.broad_code("33-9032.00") == "33-9030"
        assert SOC.broad_code("11-1011.03") == "11-1010"
        # SOC 2018's Physicians run on into 29-122x: there is no broad group 29-1220
        assert SOC.broad_code("29-1221.00") == "29-1210" and SOC.broad_code("29-1229.06") == "29-1210"
        assert SOC.broad_code("29-1241.00") == "29-1240"
        with pytest.raises(ValueError):
            SOC.broad_code("2912")

    def test_detailed_code_and_tiers(self):
        assert SOC.detailed_code("29-1212.00") == "29-1212"
        assert SOC.soc_tiers("29-1212.00") == {"major": "29-0000", "minor": "29-1000", "broad": "29-1210",
                                               "detailed": "29-1212"}
        assert SOC.soc_tiers("29-1210")["detailed"] is None
        assert SOC.soc_tiers("15-1252.00")["minor"] == "15-1200"
        assert SOC.soc_tiers("19-1011", oews={"19-1000": {"o_group": "minor"}})["minor"] == "19-1000"


class TestOews:
    def test_csv_reader(self, tmp_path):
        t = SOC.read_oews_table(F.write_oews_csv(tmp_path / "oews.csv"))
        assert t["29-1210"] == {"title": "Physicians", "o_group": "broad", "tot_emp": 782430}
        assert t["29-1212"]["tot_emp"] is None                      # "**": suppressed
        assert SOC.read_oews(tmp_path / "oews.csv") == t

    def test_json_reader_both_shapes(self, tmp_path):
        p = tmp_path / "o.json"
        p.write_text(json.dumps([{"OCC_CODE": "35-3011", "OCC_TITLE": "Bartenders", "O_GROUP": "detailed",
                                  "TOT_EMP": "650,000"}]))
        assert SOC.read_oews_table(p)["35-3011"]["tot_emp"] == 650000
        p.write_text(json.dumps({"35-3011": {"title": "Bartenders", "o_group": "Detailed", "tot_emp": 5}}))
        assert SOC.read_oews_table(p)["35-3011"] == {"title": "Bartenders", "o_group": "detailed", "tot_emp": 5}

    def test_missing_columns_refused(self, tmp_path):
        p = tmp_path / "bad.csv"
        p.write_text("OCC_CODE,OCC_TITLE\n11-1011,Chief Executives\n")
        with pytest.raises(ValueError, match="o_group"):
            SOC.read_oews_table(p)

    def test_workbook_without_openpyxl_names_uv_add(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "openpyxl", None)       # import openpyxl -> ImportError
        p = tmp_path / "oesm25nat.zip"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("oesm25nat/national_M2025_dl.xlsx", b"not really")
        with pytest.raises(SOC.MissingDependency, match="uv add openpyxl"):
            SOC.read_oews_national(p)

    def test_read_oews_national_on_a_fixture_workbook(self, tmp_path):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["AREA", "AREA_TITLE", "OCC_CODE", "OCC_TITLE", "O_GROUP", "TOT_EMP", "H_MEAN"])
        for code, (t, g, e) in F.OEWS.items():
            ws.append(["99", "U.S.", code, t, g, e, 30.5])
        buf = io.BytesIO()
        wb.save(buf)
        p = tmp_path / "oesm25nat.zip"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("oesm25nat/field_descriptions.xlsx", b"")
            zf.writestr("oesm25nat/national_M2025_dl.xlsx", buf.getvalue())
        t = SOC.read_oews_national(p)
        assert t["29-1210"] == {"title": "Physicians", "o_group": "broad", "tot_emp": 782430}
        assert t["29-1212"]["tot_emp"] is None and len(t) == len(F.OEWS)
        x = tmp_path / "national.xlsx"
        x.write_bytes(buf.getvalue())
        assert SOC.read_oews(x) == t


class TestBroadGroups:
    def _occ(self):
        return [O.Occupation(c, t, d) for c, (t, d) in F.OCCUPATIONS.items()]

    def test_a_group_per_broad_code_with_its_occupations_and_employment(self, tmp_path):
        oews = SOC.read_oews_table(F.write_oews_csv(tmp_path / "o.csv"))
        gs = {g.code: g for g in SOC.broad_groups(self._occ(), oews)}
        assert sorted(gs) == ["11-1010", "29-1210", "33-9030", "35-3010", "53-2010"]
        phys = gs["29-1210"]
        assert [o.code for o in phys.detailed] == ["29-1211.00", "29-1212.00", "29-1221.00"]
        assert (phys.title, phys.title_source, phys.employment, phys.employment_source) == \
            ("Physicians", "oews", 782430, "oews_broad")
        assert [o.code for o in gs["11-1010"].detailed] == ["11-1011.00", "11-1011.03"]
        pil = gs["53-2010"]                          # no broad row: the single detailed occupation's title, summed
        assert (pil.title, pil.title_source, pil.employment, pil.employment_source) == \
            ("Airline Pilots, Copilots, and Flight Engineers", "onet_detailed", 110000, "oews_detailed_sum")
        row = phys.as_table_row()
        assert row["kind"] == "broad" and row["detailed"][1] == {"code": "29-1212.00", "title": "Cardiologists",
                                                                 "description": F.OCCUPATIONS["29-1212.00"][1]}

    def test_without_oews(self):
        gs = {g.code: g for g in SOC.broad_groups(self._occ(), None, soc_titles={"29-1210": "Physicians"})}
        assert gs["29-1210"].title == "Physicians" and gs["29-1210"].title_source == "soc_structure"
        assert gs["29-1210"].employment is None
        # one detailed code (11-1011, with its .03 specialty): its own title; several and no title: the O*NET titles
        assert (gs["11-1010"].title, gs["11-1010"].title_source) == ("Chief Executives", "onet_detailed")
        bare = {g.code: g for g in SOC.broad_groups(self._occ(), None)}["29-1210"]
        assert (bare.title, bare.title_source) == ("Anesthesiologists; Cardiologists; Pediatricians, General",
                                                   "onet_titles")

    def test_detailed_employment(self, tmp_path):
        oews = SOC.read_oews_table(F.write_oews_csv(tmp_path / "o.csv"))
        by = {g.code: g for g in SOC.broad_groups(self._occ(), oews)}
        assert SOC.detailed_employment("33-9032.00", oews, by) == (1120000, "oews_detailed")
        assert SOC.detailed_employment("29-1212.00", oews, by) == (782430, "broad_group")     # suppressed: the group's

    def test_459_on_the_real_onet_file(self):
        p = DATA_EXTERNAL / "onet" / "occupation_data.csv"
        if not p.exists():
            pytest.skip(f"{p} is not on disk (git-ignored; fetched by base_model_generator.py fetch)")
        occ = O.read_occupation_data(p)
        gs = SOC.broad_groups(occ)
        assert len(occ) == 1016 and len(gs) == 459
        assert len(next(g for g in gs if g.code == "29-1210").detailed) == 19


class TestCut:
    def _titles(self, rows):
        return [O.JobTitle(code=c, title=t) for c, t in rows]

    def test_singular_and_label(self):
        assert [O.singular(w) for w in ("bouncers", "nannies", "watchmen", "boxes", "boss", "bus", "chorus",
                                        "analysis", "guard")] == \
            ["bouncer", "nanny", "watchman", "box", "boss", "bus", "chorus", "analysis", "guard"]
        assert O.lay_label("Night  Watchmen") == ("night watchman", True)
        assert O.lay_label("Bouncer") == ("bouncer", False)
        assert O.title_stem("nurse's aide") == "nurses_aide"

    def test_abbreviations(self):
        assert O.is_abbreviation("RN") and O.is_abbreviation("Asst.") and O.is_abbreviation("Mgr")
        assert O.is_abbreviation("2nd") and O.is_abbreviation("A/V") and not O.is_abbreviation("Bouncer")

    def test_the_cut(self):
        titles = self._titles([
            ("33-9032.00", "Bouncer"), ("33-9032.00", "Security Guard"),          # its occupation's own name
            ("33-9032.00", "Security Officer"), ("33-9032.00", "Guard (Armed)"),  # parentheses
            ("33-9032.00", "RN"), ("33-9032.00", "Asst. Guard"),                  # abbreviations
            ("33-9032.00", "Night Shift Security Guard"),                         # three words
            ("33-9032.00", "Bellhop"),                                            # Zipf 2.6 < 3
            ("35-3011.00", "Bartender"), ("35-3011.00", "Barkeep"),               # bartender: a corpus role
            ("35-3011.00", "Bouncers"), ("33-9032.00", "Night Watchmen"),         # duplicate after singular
            ("35-3011.00", "Mixologist"), ("53-2011.00", "Lifeguard"),
        ])
        occ = {c: O.Occupation(c, t, d) for c, (t, d) in F.OCCUPATIONS.items()}
        emp = {"33-9032.00": 1120000, "35-3011.00": 650000}
        kept, rep = O.cut_job_titles(titles, zipf=F.fake_zipf, corpus_stems={"bartender", "doctor"},
                                     occupations=occ, employment=emp, n=3)
        d = rep.as_dict()["dropped"]
        assert d == {"parentheses": 1, "abbreviation": 2, "words": 1, "zipf": 1, "corpus_role": 1,
                     "occupation_title": 1, "duplicate": 1}
        assert rep.n_titles == 14 and rep.n_passed == 6 and rep.n_kept == 3
        # the top three by Zipf (ties by label): bouncer 3.4, security officer 3.3, lifeguard 3.2
        assert [c.label for c in kept] == ["bouncer", "security officer", "lifeguard"]
        b = kept[0]
        assert b.code == "33-9032.00" and b.also_under == ["35-3011.00"]          # kept under the larger employment
        assert O.lay_title_candidates(titles, zipf=F.fake_zipf, corpus_stems={"bartender"}, occupations=occ, n=10)[-1].label \
            in {"barkeep", "mixologist", "night watchman"}

    def test_a_duplicate_under_a_larger_occupation_replaces_the_first(self):
        titles = self._titles([("35-3011.00", "Bouncer"), ("33-9032.00", "Bouncer")])
        kept, _ = O.cut_job_titles(titles, zipf=F.fake_zipf, corpus_stems=(),
                                   employment={"33-9032.00": 1120000, "35-3011.00": 650000})
        assert kept[0].code == "33-9032.00" and kept[0].also_under == ["35-3011.00"]

    def test_job_titles_reader_accepts_the_known_headers(self, tmp_path):
        p = F.write_job_titles(tmp_path, [("33-9032.00", "Bouncer")])
        (jt,) = O.read_job_titles(p)
        assert jt == O.JobTitle(code="33-9032.00", title="Bouncer", short_title=None, sources="08")
        p.write_text("O*NET-SOC Code,Job Title\n33-9032.00,Bouncer\n")
        assert O.read_job_titles(p)[0].title == "Bouncer"
        p.write_text("Code X,Whatever\n1,2\n")
        with pytest.raises(ValueError, match="no code or title column"):
            O.read_job_titles(p)


class TestBuildCli:
    @pytest.fixture
    def env(self, tmp_path, monkeypatch):
        import data_analysis.gap_generation.professions_generator as G
        from assistant_axis.gapgen.generators.professions import onet as Omod
        monkeypatch.setattr(Omod, "default_zipf", lambda: F.fake_zipf)
        ext, data, cand = tmp_path / "ext", tmp_path / "data", tmp_path / "cand"
        F.write_onet(ext)
        F.write_job_titles(ext, [("33-9032.00", "Bouncer"), ("33-9032.00", "Security Guard"),
                                 ("35-3011.00", "Bartender"), ("35-3011.00", "Mixologist")])
        F.write_role_corpus(data)
        oews = F.write_oews_csv(tmp_path / "oews.csv")
        base = ["--external-dir", str(ext), "--data-dir", str(data), "--candidates-dir", str(cand)]
        return G, base, oews, cand

    def test_build_writes_the_table(self, env, capsys):
        G, base, oews, cand = env
        assert G.main(base + ["build", "--run-id", "r1", "--oews", str(oews)]) == 0
        out = capsys.readouterr().out
        assert "5 SOC broad groups (459 expected)" in out and "*** not 459 ***" in out
        rd = cand / "runs" / "professions" / "r1"
        rows = [json.loads(x) for x in (rd / "table.jsonl").read_text().splitlines()]
        assert [r["kind"] for r in rows].count("broad") == 5
        jt = [r for r in rows if r["kind"] == "job_title"]
        assert [r["title"] for r in jt] == ["Bouncer", "Mixologist"]
        assert jt[0] == {"kind": "job_title", "code": "33-9032.00", "occupation": "Security Guards", "title": "Bouncer",
                         "label": "bouncer", "stem": "bouncer", "zipf": 3.4, "employment": 1120000,
                         "employment_source": "oews_detailed", "description": F.OCCUPATIONS["33-9032.00"][1],
                         "also_under": [], "short_title": None}
        build = json.loads((rd / "build.json").read_text())
        assert build["cut"]["dropped"]["corpus_role"] == 1 and build["cut"]["dropped"]["occupation_title"] == 1
        assert build["source_keys"] == ["onet_occupations", "bls_oews_national", "onet_job_titles"]
        assert build["recovery_source_titles"]["n"] == 6            # the fixture's six occupation roles
        assert (rd / "ATTRIBUTION.md").exists() and (rd / "run.json").exists() and (rd / "usage.json").exists()
        assert json.loads((rd / "usage.json").read_text())["n_calls"] == 0

    def test_build_refuses_without_oews_unless_told(self, env, capsys):
        G, base, _, cand = env
        assert G.main(base + ["build", "--run-id", "r2"]) == 2
        assert "no OEWS table" in capsys.readouterr().err
        assert G.main(base + ["build", "--run-id", "r2", "--no-oews", "--dry-run"]) == 0
        assert "--no-oews" in capsys.readouterr().out
        assert not (cand / "runs" / "professions" / "r2" / "table.jsonl").exists()

    def test_build_with_esco_adds_its_groups(self, env, capsys):
        G, base, oews, cand = env
        ext = cand.parent / "ext"
        (ext / "esco").mkdir(parents=True)
        rows = [{"uri": "u:1", "code": "5414.2", "isco_group": "5414", "isco_group_title": "Security guards",
                 "preferred_label": "bouncer", "alt_labels": ["doorman"], "description": "Keeps order at the door."},
                {"uri": "u:2", "code": "5414.1", "isco_group": "5414", "isco_group_title": "Security guards",
                 "preferred_label": "security guard", "alt_labels": [], "description": "Guards premises."}]
        (ext / "esco" / "occupations_en.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        assert G.main(base + ["build", "--run-id", "e1", "--oews", str(oews), "--source", "onet", "esco"]) == 0
        rd = cand / "runs" / "professions" / "e1"
        table = [json.loads(x) for x in (rd / "table.jsonl").read_text().splitlines()]
        (g,) = [r for r in table if r["kind"] == "esco_group"]
        assert g["code"] == "5414" and g["title"] == "Security guards" and len(g["detailed"]) == 2
        from assistant_axis.gapgen.generators.professions import lay as LAY
        lg = LAY.group_from_row(g)
        assert lg.id == "esco:5414" and lg.source_ref == "esco:5414" and lg.occupations[0]["title"] == "bouncer"
        assert "ESCO" in (rd / "ATTRIBUTION.md").read_text()
        assert G.main(base + ["build", "--run-id", "e2", "--oews", str(oews), "--source", "esco",
                              "--no-job-titles"]) == 0
