"""Test 11 of coding plan 16 (§ 8): B's sources.  Every ``Source`` has a licence, a URL and attribution text;
``fetch`` on a fake HTTP layer (200 for O*NET, 403 for BLS) writes manifest rows and says "download by hand" for BLS;
a file downloaded by hand is recorded as such; ``fetch`` is refused without ``--approved-by``; ``ATTRIBUTION.md``
holds the O*NET paragraph verbatim; the ESCO adapter pages a fake API.  No network."""
import json

import pytest

from assistant_axis.gapgen.generators.base_model.sources import SOURCES as BM_SOURCES
from assistant_axis.gapgen.generators.professions import sources as S
from assistant_axis.gapgen.generators.professions.sources import HttpResponse
from assistant_axis.tests import professions_fakes as F


class TestSources:
    def test_every_source_has_a_licence_a_url_and_attribution(self):
        for k, s in S.SOURCES.items():
            assert s.licence and s.licence_url.startswith("https://"), k
            assert s.url and s.url.startswith("https://"), k
            assert s.attribution and len(s.attribution) > 40, k
            assert S.ATTRIBUTION[k], k
            assert k in S.LICENCE_CHECK, k

    def test_the_onet_paragraph_is_the_base_model_generators_verbatim(self):
        assert S.ONET_ATTRIBUTION == BM_SOURCES["onet"].attribution
        assert S.SOURCES["onet_occupations"].attribution == S.ONET_ATTRIBUTION
        assert S.SOURCES["onet_job_titles"].attribution == S.ONET_ATTRIBUTION
        assert "LOAD-BEARING" in S.SOURCES["onet_job_titles"].note

    def test_the_plan_s_sizes_destinations_and_waves(self):
        assert S.SOURCES["onet_job_titles"].size_bytes == 4_504_432
        assert S.SOURCES["onet_job_titles"].dest == "onet/job_titles.csv"
        assert S.SOURCES["bls_oews_national"].dest == "bls/oesm25nat.zip"
        assert S.SOURCES["onet_occupations"].on_disk and S.SOURCES["onet_occupations"].row_key == "onet"
        assert S.SOURCES["esco_occupations"].wave == 2 and S.SOURCES["esco_occupations"].via == "esco_api"
        assert S.SOURCES["bls_soc_structure"].optional
        assert set(S.DEFAULT_FETCH) == {"onet_job_titles", "bls_oews_national"}
        assert "ISCO-08" in S.SKIPPED

    def test_attribution_md_holds_the_onet_paragraph_verbatim_once(self, tmp_path):
        p = S.write_attribution(tmp_path, ["onet_occupations", "onet_job_titles", "bls_oews_national"],
                                run_label="run professions/r1")
        text = p.read_text()
        assert p.name == "ATTRIBUTION.md"
        assert BM_SOURCES["onet"].attribution in text
        assert text.count(BM_SOURCES["onet"].attribution) == 1
        assert S.ONET_CHANGES in text and "Bureau of Labor Statistics" in text
        assert "ESCO" not in text.split("|")[0]          # ESCO only when used
        rec = S.attribution_record(["onet_job_titles"])
        assert rec["onet_job_titles"] == S.ONET_ATTRIBUTION and rec["onet_changes"] == S.ONET_CHANGES

    def test_licence_check_reads_the_page(self):
        http = F.onet_http()
        assert S.licence_check("onet_job_titles", text_fn=lambda u: S.page_text(http, u))
        # bls.gov's 403 page: not the licence page, although its body says "public domain"
        assert not S.licence_check("bls_oews_national", text_fn=lambda u: S.page_text(http, u))
        assert not S.licence_check("onet_job_titles", text_fn=lambda u: (_ for _ in ()).throw(OSError("down")))


class TestFetch:
    def test_refused_without_approved_by(self, tmp_path):
        with pytest.raises(S.NotApproved) as e:
            S.fetch(["onet_job_titles"], dest_root=tmp_path, approved_by=None, http=F.onet_http())
        assert "approved-by" in str(e.value)
        with pytest.raises(S.NotApproved):
            S.fetch(["onet_job_titles"], dest_root=tmp_path, approved_by="  ", http=F.onet_http())
        assert not (tmp_path / "onet").exists()

    def test_dry_run_needs_no_approval_and_requests_nothing(self, tmp_path):
        http = F.onet_http()
        res = S.fetch(None, dest_root=tmp_path, approved_by=None, http=http, dry_run=True)
        assert any("job_titles.csv" in x for x in res.dry_run_lines) and http.calls == []
        assert any(x.startswith("not fetched: ISCO-08") for x in res.dry_run_lines)

    def test_onet_200_writes_the_file_and_a_manifest_row_bls_403_says_download_by_hand(self, tmp_path):
        onet = tmp_path / "onet"
        onet.mkdir()
        # the base-model generator's row for occupation_data.csv is kept, the new row appended
        (onet / "DOWNLOAD_MANIFEST.json").write_text(json.dumps([{"key": "onet", "file": "x"}]))
        (onet / "LICENSE.txt").write_text("Licence: CC BY 4.0\nSource: https://www.onetcenter.org/dl_files/database/"
                                          "db_31_0_csv/occupation_data.csv\n")
        lines = []
        res = S.fetch(None, dest_root=tmp_path, approved_by="Roger, 2026-10-23", http=F.onet_http(),
                      echo=lines.append)
        assert res.fetched == ["onet_job_titles"]
        assert (onet / "job_titles.csv").read_text() == F.JOB_TITLES_CSV
        rows = json.loads((onet / "DOWNLOAD_MANIFEST.json").read_text())
        assert [r["key"] for r in rows] == ["onet", "onet_job_titles"]
        r = rows[1]
        assert r["licence"] == "CC BY 4.0" and r["licence_verified"] is True
        assert r["approved_by"] == "Roger, 2026-10-23" and r["downloaded_by"] == "fetch"
        assert r["size_bytes"] == r["size_bytes_published"] == len(F.JOB_TITLES_CSV.encode())
        assert r["sha256"] and r["file"].endswith("onet/job_titles.csv") and r["attribution"] == S.ONET_ATTRIBUTION
        lic = (onet / "LICENSE.txt").read_text()
        assert "occupation_data.csv" in lic and "job_titles.csv" in lic        # extended, not replaced
        # BLS refused: no file, no row, a message with the URL and the destination
        assert res.hand == [{"key": "bls_oews_national", "url": F.BLS_OEWS_URL, "dest": str(tmp_path / "bls/oesm25nat.zip")}]
        assert not (tmp_path / "bls" / "oesm25nat.zip").exists()
        assert not (tmp_path / "bls" / "DOWNLOAD_MANIFEST.json").exists()
        msg = "\n".join(lines)
        assert "download by hand" in msg and F.BLS_OEWS_URL in msg and "--hand" in msg

    def test_a_file_downloaded_by_hand_is_recorded_as_such(self, tmp_path):
        bls = tmp_path / "bls"
        bls.mkdir()
        (bls / "oesm25nat.zip").write_bytes(b"PK-by-hand")
        res = S.fetch(["bls_oews_national"], dest_root=tmp_path, approved_by="Roger, 2026-10-23",
                      http=F.onet_http(), hand=True, echo=lambda *_: None)
        assert res.fetched == ["bls_oews_national"]
        (row,) = json.loads((bls / "DOWNLOAD_MANIFEST.json").read_text())
        assert row["downloaded_by"] == "hand" and row["size_bytes"] == len(b"PK-by-hand")
        assert row["licence_verified"] is False        # the licence page refused us too: recorded, not fatal
        assert row["licence"] == "public domain"
        with pytest.raises(FileNotFoundError):
            S.fetch(["bls_soc_structure"], dest_root=tmp_path, approved_by="Roger", http=F.onet_http(), hand=True,
                    echo=lambda *_: None)

    def test_bls_200_is_fetched(self, tmp_path):
        res = S.fetch(["bls_oews_national"], dest_root=tmp_path, approved_by="Roger", http=F.onet_http(bls_status=200),
                      echo=lambda *_: None)
        assert res.fetched == ["bls_oews_national"] and (tmp_path / "bls" / "oesm25nat.zip").exists()

    def test_present_files_are_not_fetched_again_and_the_on_disk_occupations_row_is_kept(self, tmp_path):
        S.fetch(["onet_job_titles"], dest_root=tmp_path, approved_by="Roger", http=F.onet_http(), echo=lambda *_: None)
        (tmp_path / "onet" / "occupation_data.csv").write_text("O*NET-SOC Code,Title,Description\n")
        S.merge_manifest([{"key": "onet", "tool": "base_model_generator.py fetch", "downloaded_at": "2026-10-10"}],
                         tmp_path / "onet" / "DOWNLOAD_MANIFEST.json")
        http = F.onet_http()
        res = S.fetch(["onet_job_titles", "onet_occupations"], dest_root=tmp_path, approved_by="Roger", http=http,
                      echo=lambda *_: None)
        assert res.skipped == ["onet_job_titles", "onet_occupations"] and res.fetched == []
        assert ("GET", F.ONET_TITLES_URL) not in http.calls and ("GET", F.ONET_OCC_URL) not in http.calls
        rows = {r["key"]: r for r in json.loads((tmp_path / "onet" / "DOWNLOAD_MANIFEST.json").read_text())}
        assert rows["onet"] == {"key": "onet", "tool": "base_model_generator.py fetch", "downloaded_at": "2026-10-10"}

    def test_unknown_key_refused(self, tmp_path):
        with pytest.raises(KeyError):
            S.fetch(["isco08"], dest_root=tmp_path, approved_by="Roger", http=F.onet_http())


class TestEsco:
    API = S.ESCO_API

    def _http(self):
        p1 = F.esco_page([F.esco_occupation("u:1", "nurse responsible for general care", code="2221.1",
                                            alts=["general nurse"], group_title="Nursing professionals"),
                          F.esco_occupation("u:2", "bouncer", code="5414.2", full=False)],
                         total=3, next_href=f"{self.API}/search?page=2")
        p2 = F.esco_page([F.esco_occupation("u:3", "lifeguard", code="5419.4")], total=3)
        detail = HttpResponse(200, json.dumps(F.esco_occupation("u:2", "bouncer", code="5414.2", alts=["doorman"],
                                                                desc="Bouncers keep order at the door.")).encode())
        http = F.onet_http()
        http.table.update({f"{self.API}/search?type=*": p1, f"{self.API}/search?page=2": p2,
                           f"{self.API}/resource/occupation?*": detail})
        return http

    def test_pages_the_search_api_and_fetches_a_result_without_details(self, tmp_path):
        http = self._http()
        info = S.fetch_esco_occupations(http, tmp_path / "esco" / "occupations_en.jsonl", echo=lambda *_: None)
        assert info == {"n_rows": 3, "n_pages": 2, "n_detail_fetches": 1, "total": 3}
        rows = [json.loads(x) for x in (tmp_path / "esco" / "occupations_en.jsonl").read_text().splitlines()]
        assert [r["preferred_label"] for r in rows] == ["nurse responsible for general care", "bouncer", "lifeguard"]
        assert rows[0]["alt_labels"] == ["general nurse"] and rows[0]["isco_group"] == "2221"
        assert rows[0]["isco_group_title"] == "Nursing professionals"
        assert rows[1]["alt_labels"] == ["doorman"] and rows[1]["description"] == "Bouncers keep order at the door."
        first = http.calls[0][1]
        assert "type=occupation" in first and "language=en" in first and "full=true" in first

    def test_a_smoke_run_writes_a_sample_beside_the_file_and_no_manifest_row(self, tmp_path):
        """Review minor 8 (2026-10-23): ``esco_max_pages`` pages only that far, prints one parsed row before writing,
        and writes a sample, never the source's file or its manifest row."""
        lines = []
        res = S.fetch(["esco_occupations"], dest_root=tmp_path, approved_by="Roger, 2026-10-23", http=self._http(),
                      esco_max_pages=1, echo=lines.append)
        sample = tmp_path / "esco" / "occupations_en.sample.jsonl"
        assert res.samples == [sample] and res.fetched == [] and res.entries == []
        assert len(sample.read_text().splitlines()) == 2                                   # page 1 only
        assert not (tmp_path / "esco" / "occupations_en.jsonl").exists()
        assert not (tmp_path / "esco" / "DOWNLOAD_MANIFEST.json").exists()
        assert any(x.startswith("esco_occupations: first row parsed: {") for x in lines)
        assert any("smoke run, 1 page(s), 2 rows of the API's 3" in x for x in lines)

    def test_fetch_records_esco_behind_its_key(self, tmp_path):
        res = S.fetch(["esco_occupations"], dest_root=tmp_path, approved_by="Roger, 2026-10-23", http=self._http(),
                      echo=lambda *_: None)
        assert res.fetched == ["esco_occupations"]
        (row,) = json.loads((tmp_path / "esco" / "DOWNLOAD_MANIFEST.json").read_text())
        assert row["downloaded_by"] == "esco_api" and row["n_rows"] == 3 and row["licence_verified"] is True
        assert row["unverified"] == list(S.ESCO_UNVERIFIED)

    def test_a_failed_page_raises(self, tmp_path):
        http = F.FakeHttp({f"{self.API}/search?type=*": HttpResponse(500, b"")})
        with pytest.raises(RuntimeError, match="HTTP 500"):
            S.fetch_esco_occupations(http, tmp_path / "x.jsonl")


class TestCli:
    @pytest.fixture
    def cli(self, monkeypatch, tmp_path):
        import data_analysis.gap_generation.professions_generator as G
        http = F.onet_http()
        monkeypatch.setattr(G, "_http", lambda ua: http)
        return G, tmp_path, http

    def test_fetch_refused_without_approved_by(self, cli, capsys):
        G, tmp, http = cli
        assert G.main(["--external-dir", str(tmp), "fetch"]) == 2
        assert "approved-by" in capsys.readouterr().err and http.calls == []

    def test_fetch_waits_for_a_download_by_hand(self, cli, capsys):
        G, tmp, _ = cli
        code = G.main(["--external-dir", str(tmp), "fetch", "--approved-by", "Roger, 2026-10-23"])
        out = capsys.readouterr()
        assert code == 3 and "download by hand" in out.out and "WAITING" in out.err
        assert (tmp / "onet" / "job_titles.csv").exists()

    def test_fetch_dry_run(self, cli, capsys):
        G, tmp, http = cli
        assert G.main(["--external-dir", str(tmp), "fetch", "--source", "onet", "esco", "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert "esco_occupations" in out and "wave 2" in out and http.calls == []
