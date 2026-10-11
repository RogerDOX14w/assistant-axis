"""Base-model generator (workstream 3), task 1: the source table, the layout constants, the zero-rate pricing of
the local sampler, and ``setup_external.py --hf-model`` knowing the generator's model.  No network."""
from pathlib import Path

import pytest

from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL, REPO_ROOT
from assistant_axis.judge_pricing import MultiModelUsage, price_for_model


def test_layout_constants():
    from assistant_axis.gapgen.generators import base_model as B
    assert B.GENERATOR == "base_model"
    assert B.BASE_DIR == DATA_CANDIDATES / "base_model"
    assert B.SAMPLES_DIR == DATA_CANDIDATES / "cache" / "base_model"      # gitignored with /data/candidates/cache/
    assert B.WIKIBIO_DIR == DATA_EXTERNAL / "wikibio" and B.ONET_DIR == DATA_EXTERNAL / "onet"
    assert B.MODEL_ID == "Qwen/Qwen3-8B-Base"
    for p in (B.BASE_DIR, B.SAMPLES_DIR, B.WIKIBIO_DIR, B.ONET_DIR, B.table_path(1), B.stats_path(1),
              B.samples_path(1), B.stats_path(0, temperature=0.8)):
        assert Path(p).is_relative_to(REPO_ROOT)
    assert B.table_path(2).name == "candidate_table_round2.jsonl"
    assert B.stats_path(1).name == "stats_round1.json"
    assert B.stats_path(0, temperature=1.2).name == "stats_round0_t1.2.json"
    assert B.samples_path(3) == B.SAMPLES_DIR / "round3" / "samples.jsonl"


def test_sources_table():
    from assistant_axis.gapgen.generators.base_model import sources as S
    assert set(S.SOURCES) == {"wikibio", "onet"}
    wb, on = S.SOURCES["wikibio"], S.SOURCES["onet"]
    assert wb.licence == "CC BY-SA 3.0" and wb.repo_id == "michaelauli/wiki_bio" and wb.revision
    assert wb.size_bytes == 333_998_704 and len(wb.sha256) == 64
    assert on.url.startswith("https://www.onetcenter.org/dl_files/database/db_31_0_csv/")
    # verified 2026-10-10 on onetcenter.org/license_db.html: CC BY 4.0, not public domain (plan 03 said so)
    assert on.licence == "CC BY 4.0" and "USDOL/ETA" in on.attribution
    # Roger, QUESTIONS 60 (2026-10-11): the note says explicitly when the attribution stops being a courtesy
    # and becomes load-bearing - a title surviving as a candidate label in a tracked artefact - rather than
    # leaving that implicit.
    assert "LOAD-BEARING" in on.note and "candidate label" in on.note
    # PersonaHub and SUBTLEX are skipped on purpose, with the reason
    assert {"PersonaHub", "SUBTLEX-US"} <= set(S.SKIPPED)
    # the model: Roger's delete-when-done TODO travels with its entry (2026-10-10, anything over 2 GB)
    m = S.MODEL
    assert m.model_id == "Qwen/Qwen3-8B-Base" and m.licence == "Apache-2.0" and m.size_bytes > 16e9
    assert "delete" in m.todo.lower() and "Roger" in m.todo
    assert "*.safetensors" in S.HF_MODEL_ALLOW_PATTERNS[m.model_id]
    # the optional instruct control is not approved: it has no entry
    assert "Qwen/Qwen3-8B" not in S.HF_MODEL_ALLOW_PATTERNS


def test_zero_rate_pricing_of_the_local_sampler():
    from assistant_axis.gapgen.generators.base_model import MODEL_ID
    assert price_for_model(MODEL_ID) == (0.0, 0.0)
    u = MultiModelUsage()
    u.charge(MODEL_ID, 2_000_000, 160_000)
    d = u.as_dict()
    assert d["total_cost_usd"] == 0.0 and d["total_prompt_tokens"] == 2_000_000 and d["n_calls"] == 1
    # the existing entries are unchanged (no fragment collision)
    assert price_for_model("qwen3-32b") == (0.08, 0.28)


def test_setup_external_knows_the_generator_model(capsys):
    from data_analysis.gap_generation import setup_external
    assert setup_external.main(["--hf-model", "Qwen/Qwen3-8B-Base", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Qwen/Qwen3-8B-Base" in out and "DRY-RUN" in out and "*.safetensors" in out
    # the optional instruct model stays refused until Roger approves it
    assert setup_external.main(["--hf-model", "Qwen/Qwen3-8B", "--dry-run"]) == 2


def test_embedder_allow_patterns_untouched():
    from assistant_axis.gapgen import embed as E
    assert "Qwen/Qwen3-8B-Base" not in E.HF_ALLOW_PATTERNS


# --------------------------------------------------------------------------- download (fakes; no network)

import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from dataclasses import replace  # noqa: E402

from assistant_axis.gapgen.generators.base_model import download as DL  # noqa: E402
from assistant_axis.gapgen.generators.base_model import sources as SRC  # noqa: E402

BODY = {"wikibio": b"PK fake archive bytes", "onet": b"O*NET-SOC Code,Title,Description\n"}


def fake_sources():
    return {k: replace(s, sha256=hashlib.sha256(BODY[k]).hexdigest() if s.sha256 else None)
            for k, s in SRC.SOURCES.items()}


class Net:
    """Records every URL; serves the fake bodies, the published figures and licence pages."""
    def __init__(self, body=None, licence_text=None):
        self.urls, self.body = [], dict(body or BODY)
        self.licence_text = licence_text

    def fetcher(self, url, part):
        self.urls.append(url)
        key = "wikibio" if "wiki_bio" in url else "onet"
        Path(part).parent.mkdir(parents=True, exist_ok=True)
        Path(part).write_bytes(self.body[key])

    def info(self, s):
        return {"size": len(BODY[s.key]), "sha256": hashlib.sha256(BODY[s.key]).hexdigest() if s.repo_id else None}

    def text(self, url):
        if self.licence_text is not None:
            return self.licence_text
        return "license: cc-by-sa-3.0" if "huggingface" in url else "used under the CC BY 4.0 license"


def run_fetch(tmp_path, net, **kw):
    kw.setdefault("approved_by", "Roger, 2026-10-10")
    return DL.fetch(kw.pop("only", ("wikibio", "onet")), external_dir=tmp_path / "ext", sources=fake_sources(),
                    fetcher=net.fetcher, info_fn=net.info, text_fn=net.text,
                    sources_manifest_path=tmp_path / "sources_manifest.json", echo=lambda *a: None, **kw)


def test_fetch_refuses_without_approval(tmp_path):
    with pytest.raises(SystemExit) as e:
        run_fetch(tmp_path, Net(), approved_by=None)
    assert "5a" in str(e.value) and not (tmp_path / "ext").exists()


def test_fetch_dry_run_touches_nothing(tmp_path):
    net = Net()
    res = run_fetch(tmp_path, net, approved_by=None, dry_run=True, only=None)
    assert net.urls == [] and not (tmp_path / "ext").exists() and not (tmp_path / "sources_manifest.json").exists()
    text = "\n".join(res.dry_run_lines)
    assert "wiki_bio" in text and "occupation_data.csv" in text and "setup_external.py" in text
    assert "delete" in text and "PersonaHub" in text


def test_fetch_writes_files_manifests_licences(tmp_path):
    net = Net()
    res = run_fetch(tmp_path, net)
    zp = tmp_path / "ext" / "wikibio" / "data" / "wikipedia-biography-dataset.zip"
    assert zp.read_bytes() == BODY["wikibio"] and res.fetched == ["wikibio", "onet"]
    assert net.urls[0] == (f"https://huggingface.co/datasets/michaelauli/wiki_bio/resolve/{SRC.WIKIBIO_REVISION}/"
                           "data/wikipedia-biography-dataset.zip")
    man = json.loads((tmp_path / "ext" / "wikibio" / "DOWNLOAD_MANIFEST.json").read_text())
    e = man[0]
    assert e["checksum_verified"] and e["licence_verified"] and e["approved_by"] == "Roger, 2026-10-10"
    assert e["licence"] == "CC BY-SA 3.0" and e["size_bytes"] == len(BODY["wikibio"])
    assert "CC BY-SA 3.0" in (tmp_path / "ext" / "wikibio" / "LICENSE.txt").read_text()
    onet = json.loads((tmp_path / "ext" / "onet" / "DOWNLOAD_MANIFEST.json").read_text())[0]
    assert onet["licence"] == "CC BY 4.0" and onet["sha256_published"] is None and not onet["checksum_verified"]
    # QUESTIONS 60: the load-bearing sentence travels into both manifests and the LICENSE.txt beside the file
    assert "LOAD-BEARING" in onet["note"]
    assert "LOAD-BEARING" in (tmp_path / "ext" / "onet" / "LICENSE.txt").read_text()
    tracked = json.loads((tmp_path / "sources_manifest.json").read_text())
    assert [x["key"] for x in tracked] == ["wikibio", "onet"]
    assert "LOAD-BEARING" in next(x for x in tracked if x["key"] == "onet")["note"]
    # a second fetch re-uses the verified archive (O*NET publishes no hash, so it is present-and-kept as well)
    net2 = Net()
    res2 = run_fetch(tmp_path, net2)
    assert net2.urls == [] and res2.skipped == ["wikibio", "onet"]


def test_checksum_mismatch_writes_nothing(tmp_path):
    net = Net(body={"wikibio": b"tampered", "onet": BODY["onet"]})
    with pytest.raises(DL.ChecksumError):
        run_fetch(tmp_path, net, only=("wikibio",))
    d = tmp_path / "ext" / "wikibio" / "data"
    assert not (d.exists() and any(d.iterdir()))


def test_unconfirmed_licence_is_recorded_not_fatal(tmp_path):
    res = run_fetch(tmp_path, Net(licence_text="nothing relevant"), only=("onet",))
    assert res.entries[0]["licence_verified"] is False


def make_snapshot(root, files):
    """A Hub-cache layout: snapshots/<rev>/<name> -> ../../blobs/<sha256>."""
    snap = root / "models--Qwen--Qwen3-8B-Base" / "snapshots" / SRC.MODEL.revision
    blobs = root / "models--Qwen--Qwen3-8B-Base" / "blobs"
    snap.mkdir(parents=True)
    blobs.mkdir(parents=True)
    pub = {}
    for name, body in files.items():
        sha = hashlib.sha256(body).hexdigest()
        (blobs / sha).write_bytes(body)
        os.symlink(os.path.relpath(blobs / sha, snap), snap / name)
        pub[name] = {"size": len(body), "sha256": sha if name.endswith(".safetensors") else None}
    return pub


def test_record_model(tmp_path):
    pub = make_snapshot(tmp_path / "hf", {"config.json": b"{}", "model-00001-of-00001.safetensors": b"\0" * 64})
    info = lambda mid, rev: {"sha": rev, "license": "apache-2.0", "files": pub}  # noqa: E731
    e = DL.record_model(approved_by="Roger, 2026-10-10", hf_dir=tmp_path / "hf", info_fn=info, echo=lambda *a: None)
    assert e["checksum_verified"] and e["licence_verified"] and e["size_bytes"] == 66
    assert e["revision"] == SRC.MODEL.revision and "delete" in e["todo"]
    bad = {**pub, "model-00001-of-00001.safetensors": {"size": 64, "sha256": "0" * 64}}
    e2 = DL.record_model(approved_by="R", hf_dir=tmp_path / "hf", info_fn=lambda m, r: {"license": "mit", "files": bad},
                         echo=lambda *a: None)
    assert not e2["checksum_verified"] and not e2["licence_verified"]
    with pytest.raises(FileNotFoundError, match="setup_external.py --hf-model"):
        DL.record_model(approved_by="R", hf_dir=tmp_path / "nothing", echo=lambda *a: None)
