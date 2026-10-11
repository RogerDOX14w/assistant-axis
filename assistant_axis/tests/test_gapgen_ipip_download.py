"""IPIP generator, downloads: a fake fetcher stands in for the network (no request is made)."""
import hashlib
import json

import pytest

from assistant_axis.gapgen.generators.ipip import download as D
from assistant_axis.gapgen.generators.ipip.sources import (LICENCE_QUOTE, SOURCES, UNAPPROVED_EXAMPLE,
                                                           WORKBOOK_CREDIT)

LICENCE_SENTENCE = ("The items and scales are in the public domain, which means that one can copy, edit, "
                    "translate, or use them for any purpose without asking permission and without paying a fee.")
#: Every approved source answered by the fake fetcher: the home page carries the licence sentence, the key pages
#: a scrap of key text, the workbook a zip magic number, the rest a stub.
PAGES = {s.url: (f"<html><body><p>{LICENCE_SENTENCE}</p></body></html>".encode() if s.role == "licence"
                 else b"PK\x03\x04 fake workbook" if s.role == "keys_a"
                 else f"<html><body><b>Scale</b><br>+ keyed Item for {s.key}.<br></body></html>".encode())
         for s in SOURCES.values()}
EXPECTED = list(SOURCES)


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
                       now="2026-10-11T12:00:00+00:00", git_sha="abc1234", **kw)


def test_fetch_writes_files_and_manifest(tmp_path):
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f)
    # every approved source is fetched now: the three pages of 2026-10-10, the home page, the 21 key pages and
    # the workbook (QUESTIONS 52 option C, QUESTIONS 46)
    assert man.fetched == EXPECTED and man.skipped == []
    assert len(f.calls) == len(SOURCES) == 26
    assert sum(1 for s in SOURCES.values() if s.role == "keys_b") == 21
    for k, s in SOURCES.items():
        p = tmp_path / "ext" / s.dest
        assert p.read_bytes() == PAGES[s.url]
        assert not p.with_name(p.name + ".part").exists()
    m = json.loads((tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_text())
    tracked = json.loads((tmp_path / "tracked" / "sources_manifest.json").read_text())
    assert m == tracked
    e = {x["key"]: x for x in m["entries"]}
    for k in ("item_list", "scale_index", "key_hexaco", "assignment_workbook"):
        body = PAGES[SOURCES[k].url]
        assert e[k]["sha256"] == sha(body) and e[k]["size_bytes"] == len(body)
        assert e[k]["url"] == SOURCES[k].url and e[k]["downloaded_at"] == "2026-10-11T12:00:00+00:00"
        assert e[k]["hash_source"] == "received bytes (IPIP publishes no hashes)"
        assert e[k]["role"] == SOURCES[k].role
    assert e["key_hexaco"]["approval"].startswith("Roger, 2026-10-11")
    assert e["item_list"]["approval"].startswith("Roger, 2026-10-10")
    assert m["total_bytes"] == sum(len(v) for v in PAGES.values())


def test_the_licence_sentence_is_recorded_verbatim(tmp_path):
    """QUESTIONS 46: ``licence.verbatim`` was null and the quote came from the plan's prose; the home page is
    fetched so that the sentence is on record as IPIP prints it."""
    man = run(tmp_path)
    lic = man.licence
    assert lic["quote_from_plan"] == LICENCE_QUOTE
    assert lic["verbatim"] == LICENCE_SENTENCE
    assert lic["verbatim_source"] == "home" and lic["verbatim_url"] == SOURCES["home"].url
    assert lic["credit"] == WORKBOOK_CREDIT and "Tedone" in lic["credit"]


def test_second_run_skips_and_force_refetches(tmp_path):
    run(tmp_path)
    before = (tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_bytes()
    f2 = FakeFetcher()
    man = run(tmp_path, fetcher=f2)
    assert f2.calls == [] and man.fetched == [] and man.skipped == EXPECTED
    assert (tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_bytes() == before
    f3 = FakeFetcher()
    man = run(tmp_path, fetcher=f3, force=True)
    assert len(f3.calls) == len(SOURCES) and man.fetched == EXPECTED


def test_changed_file_on_disk_is_refetched(tmp_path):
    run(tmp_path)
    (tmp_path / "ext" / SOURCES["item_list"].dest).write_bytes(b"truncated")
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f)
    assert man.fetched == ["item_list"] and f.calls == [SOURCES["item_list"].url]


def test_only_one_key_page(tmp_path):
    run(tmp_path)
    (tmp_path / "ext" / SOURCES["key_neo"].dest).unlink()
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f, only=["key_neo"])
    assert f.calls == [SOURCES["key_neo"].url] and man.fetched == ["key_neo"]
    keys = [e["key"] for e in json.loads((tmp_path / "ext" / "DOWNLOAD_MANIFEST.json").read_text())["entries"]]
    assert keys == EXPECTED                      # the order is the source order, not the fetch order


def test_unknown_key_refused(tmp_path):
    with pytest.raises(KeyError):
        run(tmp_path, only=["nope"])


def test_a_source_with_no_approval_is_refused_without_a_named_go(tmp_path):
    """Every real source is approved since 2026-10-11, so the refusal path is tested on the stand-in."""
    s = UNAPPROVED_EXAMPLE
    assert s.approval is None
    sources = dict(SOURCES, **{s.key: s})
    f = FakeFetcher(dict(PAGES, **{s.url: b"<html>nope</html>"}))
    with pytest.raises(D.NotApproved):
        run(tmp_path, fetcher=f, only=[s.key], sources=sources)
    with pytest.raises(D.NotApproved):                       # a dry run is refused too
        run(tmp_path, fetcher=f, only=[s.key], sources=sources, dry_run=True)
    assert f.calls == [] and not (tmp_path / "ext").exists()
    man = run(tmp_path, fetcher=f, only=[s.key], sources=sources, approved_by="Roger, 2026-10-11 (test)")
    assert man.fetched == [s.key]
    assert {x["key"]: x for x in man.entries}[s.key]["approval"] == "Roger, 2026-10-11 (test)"


def test_the_workbook_is_approved_and_credited(tmp_path):
    man = run(tmp_path, only=["assignment_workbook"])
    e = {x["key"]: x for x in man.entries}["assignment_workbook"]
    assert e["approval"].startswith("Roger, 2026-10-11") and e["licence"].startswith("no licence stated")
    assert e["role"] == "keys_a"


def test_dry_run_writes_nothing(tmp_path):
    f = FakeFetcher()
    man = run(tmp_path, fetcher=f, dry_run=True)
    assert f.calls == [] and not (tmp_path / "ext").exists() and not (tmp_path / "tracked").exists()
    assert len(man.dry_run_lines) == len(SOURCES) and all("ipip.ori.org" in x for x in man.dry_run_lines)


def test_find_licence_sentence():
    s = D.find_licence_sentence(PAGES[SOURCES["home"].url].decode())
    assert s.startswith("The items and scales are in the public domain") and s.endswith("without paying a fee.")
    assert D.find_licence_sentence("<p>nothing here</p>") is None


def test_pages_are_decoded_as_cp1252_for_the_licence_search(tmp_path):
    """The pages are a single-byte Windows encoding (QUESTIONS 49); 0x92 is a right single quote, which utf-8
    cannot decode at all and iso-8859-1 would turn into a control character."""
    body = b"<html><body><p>Goldberg\x92s own words: " + LICENCE_SENTENCE.encode() + b"</p></body></html>"
    f = FakeFetcher(dict(PAGES, **{SOURCES["home"].url: body}))
    man = run(tmp_path, fetcher=f)
    assert man.licence["verbatim"] == LICENCE_SENTENCE
    assert body.decode("cp1252").startswith("<html><body><p>Goldberg’s")
    assert body.decode("iso-8859-1").startswith("<html><body><p>Goldberg\u0092s")      # a control character
    with pytest.raises(UnicodeDecodeError):
        body.decode("utf-8")


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
