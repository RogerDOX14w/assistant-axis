"""IPIP generator, downloads: a fake fetcher stands in for the network (no request is made)."""
import hashlib
import json

import pytest

from assistant_axis.gapgen.generators.ipip import download as D
from assistant_axis.gapgen.generators.ipip.sources import LICENCE_QUOTE, SOURCES

PAGES = {
    SOURCES["item_list"].url: b"<html><body><p>Get chores done right away.</p></body></html>",
    SOURCES["assignment_table"].url: b"<html><body><table><tr><td>H1131</td></tr></table></body></html>",
    SOURCES["scale_index"].url: (b"<html><body><p>The items and scales are in the public domain, which means that "
                                 b"one can copy, edit, translate, or use them for any purpose without asking "
                                 b"permission and without paying a fee.</p></body></html>"),
    SOURCES["hexaco_key"].url: b"<html><body>HEXACO</body></html>",
}


class FakeFetcher:
    def __init__(self, pages=PAGES):
        self.pages = dict(pages)
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        return self.pages[url]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(tmp_path, **kw):
    kw.setdefault("fetcher", FakeFetcher())
    return D.fetch_all(dest_root=tmp_path / "ext", sources_manifest_path=tmp_path / "tracked" / "sources_manifest.json",
                       now="2026-10-10T12:00:00+00:00", git_sha="abc1234", **kw)


def test_fetch_writes_files_and_manifest(tmp_path):
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f)
    assert man.fetched == ["item_list", "assignment_table", "scale_index"] and man.skipped == []
    assert f.calls == [SOURCES[k].url for k in ("item_list", "assignment_table", "scale_index")]
    for k in ("item_list", "assignment_table", "scale_index"):
        p = tmp_path / "ext" / SOURCES[k].dest
        assert p.read_bytes() == PAGES[SOURCES[k].url]
        assert not p.with_name(p.name + ".part").exists()
    assert not (tmp_path / "ext" / SOURCES["hexaco_key"].dest).exists()
    m = json.loads((tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_text())
    tracked = json.loads((tmp_path / "tracked" / "sources_manifest.json").read_text())
    assert m == tracked
    e = {x["key"]: x for x in m["entries"]}
    for k in ("item_list", "assignment_table", "scale_index"):
        body = PAGES[SOURCES[k].url]
        assert e[k]["sha256"] == sha(body) and e[k]["size_bytes"] == len(body)
        assert e[k]["url"] == SOURCES[k].url and e[k]["downloaded_at"] == "2026-10-10T12:00:00+00:00"
        assert e[k]["hash_source"] == "received bytes (IPIP publishes no hashes)"
    assert m["licence"]["quote_from_plan"] == LICENCE_QUOTE
    # the full sentence was found in one of the pages and recorded verbatim, with the page it came from
    assert m["licence"]["verbatim"].startswith("The items and scales are in the public domain")
    assert m["licence"]["verbatim_source"] == "scale_index"
    assert m["total_bytes"] == sum(len(PAGES[SOURCES[k].url]) for k in ("item_list", "assignment_table", "scale_index"))


def test_second_run_skips_and_force_refetches(tmp_path):
    run(tmp_path)
    before = (tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_bytes()
    f2 = FakeFetcher()
    man = run(tmp_path, fetcher=f2)
    assert f2.calls == [] and man.fetched == [] and man.skipped == ["item_list", "assignment_table", "scale_index"]
    assert (tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_bytes() == before
    f3 = FakeFetcher()
    man = run(tmp_path, fetcher=f3, force=True)
    assert len(f3.calls) == 3 and man.fetched == ["item_list", "assignment_table", "scale_index"]


def test_changed_file_on_disk_is_refetched(tmp_path):
    run(tmp_path)
    (tmp_path / "ext" / SOURCES["item_list"].dest).write_bytes(b"truncated")
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f)
    assert man.fetched == ["item_list"] and f.calls == [SOURCES["item_list"].url]


def test_only_the_fallback_page(tmp_path):
    run(tmp_path)
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f, only=["hexaco_key"])
    assert f.calls == [SOURCES["hexaco_key"].url] and man.fetched == ["hexaco_key"]
    keys = [e["key"] for e in json.loads((tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_text())["entries"]]
    assert keys == ["item_list", "assignment_table", "scale_index", "hexaco_key"]


def test_unknown_key_refused(tmp_path):
    with pytest.raises(KeyError):
        run(tmp_path, only=["nope"])


def test_dry_run_writes_nothing(tmp_path):
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f, dry_run=True)
    assert f.calls == [] and not (tmp_path / "ext").exists() and not (tmp_path / "tracked").exists()
    assert len(man.dry_run_lines) == 3 and all("ipip.ori.org" in x for x in man.dry_run_lines)


def test_find_licence_sentence():
    html = PAGES[SOURCES["scale_index"].url].decode()
    s = D.find_licence_sentence(html)
    assert s.startswith("The items and scales are in the public domain") and s.endswith("without paying a fee.")
    assert D.find_licence_sentence("<p>nothing here</p>") is None


class _Resp:
    def __init__(self, status, body, length=None, cut=None):
        self.status, self.body, self.cut = status, body, cut
        self.headers = {"Content-Length": str(length)} if length is not None else {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        import http.client
        if self.cut is not None:
            raise http.client.IncompleteRead(self.body[:self.cut], len(self.body) - self.cut)
        return self.body


def test_short_body_is_completed_with_a_range_request(monkeypatch):
    body = b"x" * 1000
    seen = []

    def fake_urlopen(req, timeout=None):
        seen.append(req.headers.get("Range"))
        if len(seen) == 1:
            return _Resp(200, body, length=1000, cut=835)
        return _Resp(206, body[835:])
    monkeypatch.setattr(D.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(D.time, "sleep", lambda s: None)
    assert D._urlopen_bytes("https://ipip.ori.org/x.htm") == body
    assert seen == [None, "bytes=835-"]


def test_range_ignored_starts_again(monkeypatch):
    body = b"y" * 100
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req.headers.get("Range"))
        if len(calls) == 1:
            return _Resp(200, body, length=100, cut=40)
        return _Resp(200, body, length=100)        # the server ignored the range: whole body again
    monkeypatch.setattr(D.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(D.time, "sleep", lambda s: None)
    assert D._urlopen_bytes("https://ipip.ori.org/y.htm") == body
