"""Census generator, downloads: verification, Dataverse fallback, idempotency, manifest, licences.

A fake fetcher stands in for the network."""
import hashlib
import json

import pytest

from assistant_axis.gapgen.generators.censuses import download as D
from assistant_axis.gapgen.generators.censuses.sources import OSF_NODE_API, TDA_CITATION_API, Source

OSF_BYTES = b"Abandoned\r\nAbject\r\n"
ORIG_BYTES = b"adjective,N,prop\nkind,80,0.98\n"
TAB_BYTES = b'adjective\tN\tprop\n"kind"\t80\t0.98\n'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def md5(b):
    return hashlib.md5(b).hexdigest()


def make_sources(*, dv_md5=None):
    osf = Source(key="allport_I", filename="Personal Traits.txt", url="https://osf.io/download/aaaaa/",
                 dest="osf_dir/Personal Traits.txt", size_bytes=len(OSF_BYTES), sha256=sha(OSF_BYTES),
                 md5=md5(OSF_BYTES), licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/",
                 citation="x", column="I", provider="osf")
    dv = Source(key="tda_properties", filename="TDA_properties.csv",
                url="https://dataverse.example/api/access/datafile/1?format=original",
                alt_url="https://dataverse.example/api/access/datafile/1", dest="tda_dir/TDA_properties.csv",
                size_bytes=len(ORIG_BYTES), md5=dv_md5 or md5(ORIG_BYTES), licence="CC0 1.0",
                licence_url="http://creativecommons.org/publicdomain/zero/1.0", citation="y", doi="10.0/x",
                version=4, provider="dataverse")
    return {"allport_I": osf, "tda_properties": dv}


NODE = {"data": {"attributes": {"title": "Allport's Trait-Word List Digitized"}}}
CONTRIB = {"data": [
    {"attributes": {"index": 1, "bibliographic": True}, "embeds": {"users": {"data": {"attributes": {"full_name": "B Two"}}}}},
    {"attributes": {"index": 0, "bibliographic": True}, "embeds": {"users": {"data": {"attributes": {"full_name": "A One"}}}}},
    {"attributes": {"index": 2, "bibliographic": False}, "embeds": {"users": {"data": {"attributes": {"full_name": "Hidden"}}}}},
]}
CITE = {"status": "OK", "data": {"message": 'Condon, David, 2021, "TDA", <a href="https://doi.org/x">https://doi.org/x</a>, V4'}}


class FakeFetcher:
    def __init__(self, files):
        self.files = dict(files)
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url == OSF_NODE_API:
            return json.dumps(NODE).encode()
        if url == OSF_NODE_API + "contributors/?embed=users":
            return json.dumps(CONTRIB).encode()
        if url == TDA_CITATION_API:
            return json.dumps(CITE).encode()
        if "api.osf.io/v2/licenses" in url:
            return json.dumps({"data": {"attributes": {"text": "CC BY TEXT"}}}).encode()
        if "legalcode" in url:
            return b"CC0 TEXT"
        if url in self.files:
            return self.files[url]
        raise AssertionError(f"unexpected fetch {url}")


def files(osf=OSF_BYTES, orig=ORIG_BYTES, tab=TAB_BYTES):
    s = make_sources()
    return {s["allport_I"].url: osf, s["tda_properties"].url: orig, s["tda_properties"].alt_url: tab}


def run(tmp_path, fetcher, **kw):
    kw.setdefault("sources", make_sources())
    return D.fetch_all(dest_root=tmp_path / "wl", fetcher=fetcher, now="2026-10-08T00:00:00+00:00", git_sha="abc",
                       sources_manifest_path=tmp_path / "sources_manifest.json", **kw)


def test_verified_download_and_manifest(tmp_path):
    f = FakeFetcher(files())
    man = run(tmp_path, f)
    e = {x["key"]: x for x in man.entries}
    assert (tmp_path / "wl/osf_dir/Personal Traits.txt").read_bytes() == OSF_BYTES
    assert e["allport_I"]["checksum_verified"] and e["allport_I"]["checksum_source"] == "osf:extra.hashes"
    assert e["allport_I"]["sha256"] == sha(OSF_BYTES) == e["allport_I"]["sha256_published"]
    assert e["allport_I"]["file"].endswith("wl/osf_dir/Personal Traits.txt")
    assert e["allport_I"]["attribution"] == ("Allport's Trait-Word List Digitized (A One, B Two), https://osf.io/k6rwj/")
    assert e["tda_properties"]["checksum_source"] == "dataverse:md5(format=original)"
    assert e["tda_properties"]["attribution"] == 'Condon, David, 2021, "TDA", https://doi.org/x, V4'
    assert e["tda_properties"]["git_sha"] == "abc" and e["tda_properties"]["downloaded_at"].startswith("2026-10-08")
    assert json.loads((tmp_path / "wl" / D.DOWNLOAD_MANIFEST_NAME).read_text()) == man.entries
    assert json.loads((tmp_path / "sources_manifest.json").read_text()) == man.entries
    lic = (tmp_path / "wl/osf_dir/LICENSE.txt").read_text()
    assert "CC BY 4.0" in lic and "A One, B Two" in lic and "CC BY TEXT" in lic
    assert "CC0 TEXT" in (tmp_path / "wl/tda_dir/LICENSE.txt").read_text()
    readme = (tmp_path / "wl/README.md").read_text()
    assert "https://osf.io/download/aaaaa/" in readme and sha(OSF_BYTES) in readme and "TDA_data_scored.tab" in readme
    assert not list((tmp_path / "wl").rglob("*.part"))


def test_wrong_byte_raises_and_leaves_nothing(tmp_path):
    f = FakeFetcher(files(osf=OSF_BYTES[:-1] + b"X"))
    with pytest.raises(D.ChecksumError) as ei:
        run(tmp_path, f, only=["allport_I"])
    assert sha(OSF_BYTES) in str(ei.value)
    assert not (tmp_path / "wl/osf_dir/Personal Traits.txt").exists()
    assert not list((tmp_path / "wl").rglob("*.part"))


def test_dataverse_tab_fallback(tmp_path):
    srcs = make_sources(dv_md5=md5(TAB_BYTES))
    man = run(tmp_path, FakeFetcher(files()), sources=srcs, only=["tda_properties"])
    e = man.entries[0]
    assert e["checksum_verified"] and e["checksum_source"] == "dataverse:md5(tab)" and e["form"] == "tab"
    assert (tmp_path / "wl/tda_dir/TDA_properties.csv").read_bytes() == TAB_BYTES


def test_dataverse_neither_matches_is_kept_unverified(tmp_path):
    srcs = make_sources(dv_md5="0" * 32)
    man = run(tmp_path, FakeFetcher(files()), sources=srcs, only=["tda_properties"])
    e = man.entries[0]
    assert e["checksum_verified"] is False and e["checksum_source"] is None
    assert (tmp_path / "wl/tda_dir/TDA_properties.csv").read_bytes() == ORIG_BYTES


def test_skip_when_verified_and_force_refetches(tmp_path):
    run(tmp_path, FakeFetcher(files()))
    f2 = FakeFetcher({})          # any data fetch would fail
    man = run(tmp_path, f2)
    assert set(man.skipped) == {"allport_I", "tda_properties"} and not man.fetched and f2.calls == []
    first = json.loads((tmp_path / "wl" / D.DOWNLOAD_MANIFEST_NAME).read_text())
    assert man.entries == first     # unchanged files keep their entries (dates included)
    f3 = FakeFetcher(files())
    man3 = run(tmp_path, f3, force=True)
    assert set(man3.fetched) == {"allport_I", "tda_properties"}


def test_dry_run_writes_nothing(tmp_path):
    f = FakeFetcher({})
    man = run(tmp_path, f, dry_run=True)
    assert len(man.dry_run_lines) == 2 and f.calls == []
    assert not (tmp_path / "wl").exists() and not (tmp_path / "sources_manifest.json").exists()


def test_unknown_key(tmp_path):
    with pytest.raises(KeyError):
        run(tmp_path, FakeFetcher({}), only=["nope"])


def test_verify_file(tmp_path):
    s = make_sources()["allport_I"]
    p = tmp_path / "x.txt"
    p.write_bytes(OSF_BYTES)
    assert D.verify_file(p, s).verified
    p.write_bytes(OSF_BYTES + b"\n")
    assert not D.verify_file(p, s).verified
