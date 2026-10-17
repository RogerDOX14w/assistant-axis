"""Corpus-frames generator: the text corpora (open decision 2, Roger 2026-10-14): the looser regex frames over
character descriptions, the extraction and its document frequency, the readers, the download's approval gate and
manifest.  No network: a fake fetcher serves fixture files."""
import io
import json

import pytest

from assistant_axis.gapgen.generators.corpus_frames import text as X


def frame(base, source="cards"):
    return next(f for f in X.text_frames([source]) if f.base == base)


@pytest.mark.parametrize("base,sentence,want", [
    ("trait_list", "Personality: Kind, shy, stubborn and a bit Clingy.", ["kind", "shy", "stubborn", "clingy"]),
    ("trait_list", 'Personality("Tsundere" + "Caring" + "Easily angered")', ["tsundere", "caring",
                                                                             "easily angered"]),
    ("trait_list", "Traits: loyal; protective / sarcastic", ["loyal", "protective", "sarcastic"]),
    ("copular_list", "She is kind, caring and a bit shy, but she loves cats", ["kind", "caring", "shy"]),
    ("copular_list", "He is protective of his sister, socially awkward and sweet", ["protective",
                                                                                    "socially awkward", "sweet"]),
    ("copular_list", "Char is a shy girl", []),                         # a noun phrase: the attributive frame's
    ("copular_list", "He was born in Paris", []),                       # not a description
    ("copular_list", "She is Kind", []),                                # a capital in running text
    ("attributive", "Char is a shy, quiet girl who reads", [("shy", "girl"), ("quiet", "girl")]),
    ("known_for", "He is known for his honesty", ["honesty"]),
    ("poss_nature", "Her stubborn streak shows", [("stubborn", "streak")]),
    ("to_a_fault", "She is generous to a fault", ["generous"]),
    ("by_nature", "loyal by nature", ["loyal"]),
    ("at_heart", "a romantic at heart", ["romantic"]),
    ("at_heart", "a child at heart", []),                               # a person noun is not a filler
    ("tendency", "with a tendency to be very jealous", ["jealous"]),
    ("always", "She is always cheerful", ["cheerful"]),
])
def test_text_frames(base, sentence, want):
    got = X.frame_fillers(frame(base), sentence)
    if want and isinstance(want[0], tuple):
        assert got == want
    else:
        assert [f for f, _ in got] == want


def test_extraction_counts_documents_and_keeps_an_example():
    docs = ["She is kind and shy. She is kind to everyone.", "She is kind and shy. She is kind to everyone.",
            "{{char}} is kind, loyal by nature.", "", "Personality: kind, brave"]
    frames = X.text_frames(["cards"])
    ex = X.extract_frames(docs, frames)
    assert (ex.n_documents, ex.n_unique) == (5, 3)                         # the duplicate and the empty one dropped
    cop = {h.filler: h for h in ex.hits["cards.copular_list"]}
    assert (cop["kind"].match, cop["kind"].volumes) == (3, 2)             # twice in one document, once in another
    assert cop["kind"].example == "She is kind and shy."
    assert {h.filler for h in ex.hits["cards.by_nature"]} == {"loyal"}
    assert {h.filler for h in ex.hits["cards.trait_list"]} == {"kind", "brave"}


def test_extract_round_trip(tmp_path):
    hs = X.extract_frames(["She is kind.\tShe is shy."], X.text_frames(["pippa"])).hits["pippa.copular_list"]
    p = tmp_path / "pippa.copular_list.tsv"
    sha = X.write_text_extract(hs, p)
    assert len(sha) == 64 and X.read_text_extract(p) == hs


def test_readers(tmp_path):
    (tmp_path / "a.jsonl").write_text("\n".join(json.dumps(d) for d in (
        {"bot_description": "She is kind."}, {"bot_description": None}, {"other": 1})) + "\nnot json\n")
    assert list(X.read_documents(tmp_path / "a.jsonl", "bot_description")) == ["She is kind."]
    (tmp_path / "b.json").write_text(json.dumps([{"description": "He is shy."}, {"description": ""}]))
    assert list(X.read_documents(tmp_path / "b.json", "description")) == ["He is shy."]
    import pyarrow as pa
    import pyarrow.parquet as pq
    pq.write_table(pa.table({"name": ["A", "B"], "description": ["She is bold.", None]}), tmp_path / "c.parquet")
    assert list(X.read_documents(tmp_path / "c.parquet", "description")) == ["She is bold."]
    with pytest.raises(KeyError):
        list(X.read_documents(tmp_path / "c.parquet", "bot_description"))


class FakeHub:
    """Serves a listing and two files; logs every request."""

    def __init__(self, files):
        self.files, self.calls = files, []

    def stream(self, url):
        self.calls.append(("stream", url))
        return io.BytesIO(self.files[url.rsplit("/", 1)[-1]])

    def json(self, url):
        self.calls.append(("json", url))
        return {"siblings": [{"rfilename": "README.md"}, {"rfilename": "data/train-00000-of-00001.parquet"}]}


def _hub(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    pq.write_table(pa.table({"description": ["She is kind, caring and loyal.", "He is loyal by nature."]}),
                   tmp_path / "cards.parquet")
    pippa = "\n".join(json.dumps({"bot_description": t}) for t in ("She is kind.", "She is kind.", "He is shy."))
    return FakeHub({"pippa_deduped.jsonl": pippa.encode(),
                    "train-00000-of-00001.parquet": (tmp_path / "cards.parquet").read_bytes()})


def test_fetch_text_needs_the_approval_and_records_it(tmp_path):
    hub = _hub(tmp_path)
    d = tmp_path / "ext"
    with pytest.raises(X.NotApproved):
        X.fetch_text(approved_by=None, fetch=hub, text_dir=d)
    assert hub.calls == [] and not d.exists()
    dry = X.fetch_text(approved_by=None, fetch=hub, text_dir=d, dry_run=True)
    assert hub.calls == [] and len(dry.dry_run_lines) == 2 and not d.exists()
    appr = "Roger, 2026-10-14: open decision 2, the text corpora in this build"
    src = tmp_path / "sources_manifest.json"
    rep = X.fetch_text(approved_by=appr, fetch=hub, text_dir=d, sources_manifest_path=src)
    assert sorted(rep.fetched) == ["cards", "pippa"]
    man = json.loads((d / "DOWNLOAD_MANIFEST.json").read_text())
    e = {x["key"]: x for x in man["entries"]}
    assert [f["file"] for f in e["cards"]["files"]] == ["cards/train-00000-of-00001.parquet"]
    assert e["cards"]["licence"] == "CC BY 4.0"
    assert e["pippa"]["approval"] == appr and e["pippa"]["licence"] == "Apache-2.0"
    assert e["pippa"]["size_bytes"] == e["pippa"]["files"][0]["size_bytes"] == len(hub.files["pippa_deduped.jsonl"])
    assert len(rep.warnings) == 2                      # fixture files are far smaller than the plan's measurements
    assert json.loads(src.read_text())["text"] == man
    hub.calls.clear()
    assert X.fetch_text(approved_by=appr, fetch=hub, text_dir=d).skipped == ["pippa", "cards"]
    assert [c for c in hub.calls if c[0] == "stream"] == []


def test_run_extract_writes_the_extracts_and_can_delete_the_downloads(tmp_path):
    hub = _hub(tmp_path)
    d = tmp_path / "ext"
    X.fetch_text(approved_by="Roger", fetch=hub, text_dir=d)
    stats = X.run_extract(text_dir=d, echo=lambda *a: None, delete_raw=True)
    assert stats["sources"]["pippa"]["n_unique"] == 2 and stats["sources"]["cards"]["n_documents"] == 2
    paths = X.text_extract_paths(d)
    assert "cards.by_nature" in paths and "pippa.copular_list" in paths
    assert {h.filler for h in X.read_text_extract(paths["cards.copular_list"])} == {"kind", "caring", "loyal"}
    assert len(stats["deleted_raw"]) == 2 and not (d / "pippa" / "pippa_deduped.jsonl").exists()
    assert json.loads((d / "extracts" / "extract_stats.json").read_text())["text_bank_sha256"] == \
        X.text_bank_sha256()


def test_the_text_bank_is_hashed_and_keyed_by_source():
    keys = [f.id for f in X.text_frames()]
    assert len(keys) == len(set(keys)) == 2 * len(X.TEXT_FRAME_SPECS)
    assert all(k.split(".")[0] in X.TEXT_SOURCES for k in keys)
    assert {f.type for f in X.text_frames()} >= {"list", "postposed", "copular", "possessive"}
    assert len(X.text_bank_sha256()) == 64


# --------------------------------------------------------------------------- review fixes (2026-10-17)

class Listing:
    def __init__(self, files):
        self.files, self.calls = files, []

    def json(self, url):
        self.calls.append(("json", url))
        return {"siblings": [{"rfilename": f} for f in self.files]}


def test_resolve_filenames_prefers_the_train_split_and_takes_every_shard():
    """S2: ``test-*`` sorted before ``train-*``, and only the first of several train shards was taken."""
    src = X.TEXT_SOURCES["cards"]
    hub = Listing(["README.md", "data/test-00000-of-00001.parquet", "data/train-00001-of-00002.parquet",
                   "data/train-00000-of-00002.parquet", "data/train.csv"])
    assert X.resolve_filenames(src, fetch=hub) == ["data/train-00000-of-00002.parquet",
                                                   "data/train-00001-of-00002.parquet"]
    assert X.resolve_filenames(src, fetch=Listing(["cards.jsonl", "README.md"])) == ["cards.jsonl"]
    with pytest.raises(RuntimeError) as e:                                   # several, none of the train split
        X.resolve_filenames(src, fetch=Listing(["data/a.parquet", "data/b.parquet"]))
    assert "data/a.parquet" in str(e.value) and "data/b.parquet" in str(e.value)
    assert X.resolve_filenames(X.TEXT_SOURCES["pippa"], fetch=Listing([])) == ["pippa_deduped.jsonl"]


def test_far_off_warns_against_the_plans_measurements():
    assert X.far_off(2_100_000, 2_200_000, what="cards", unit="bytes") is None
    assert "0.10 x" in X.far_off(220_000, 2_200_000, what="cards", unit="bytes")
    assert X.far_off(20_000, 5755, what="cards", unit="rows")                 # several times too many
    assert X.far_off(5, None, what="pippa", unit="rows") is None              # no measurement, no warning


def test_a_split_in_shards_is_fetched_whole_and_extracted_whole(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    blobs = {}
    for i, texts in enumerate((["She is kind and shy."], ["He is loyal by nature.", "She is shy and kind."])):
        p = tmp_path / f"s{i}.parquet"
        pq.write_table(pa.table({"description": texts}), p)
        blobs[f"train-0000{i}-of-00002.parquet"] = p.read_bytes()

    class ShardedHub(FakeHub):
        def json(self, url):
            self.calls.append(("json", url))
            return {"siblings": [{"rfilename": f"data/{k}"} for k in sorted(self.files)]
                    + [{"rfilename": "data/test-00000-of-00001.parquet"}]}
    hub = ShardedHub(blobs)
    d = tmp_path / "ext"
    near = {"cards": __import__("dataclasses").replace(X.TEXT_SOURCES["cards"],
                                                       expected_bytes=sum(len(b) for b in blobs.values()))}
    rep = X.fetch_text(["cards"], approved_by="Roger", fetch=hub, text_dir=d, sources=near)
    files = rep.entries[0]["files"]
    assert [f["file"] for f in files] == ["cards/train-00000-of-00002.parquet", "cards/train-00001-of-00002.parquet"]
    assert rep.entries[0]["size_bytes"] == sum(f["size_bytes"] for f in files) and rep.warnings == []
    stats = X.run_extract(text_dir=d, sources=["cards"], echo=lambda *a: None)
    assert stats["sources"]["cards"]["n_documents"] == 3 and len(stats["sources"]["cards"]["files"]) == 2
    assert any("5,755 rows" in w for w in stats["warnings"])                 # 3 cards, not 5,755
    got = {h.filler for h in X.read_text_extract(d / "extracts" / "cards.copular_list.tsv")}
    assert got == {"kind", "shy", "loyal"}                                   # read from both shards


class _Cut:
    """A body that raises after its first chunk."""

    def __init__(self, data):
        self.data, self.n = data, 0

    def read(self, size=-1):
        self.n += 1
        if self.n > 1:
            raise ConnectionError("connection reset")
        return self.data[:5]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_download_retries_with_a_back_off_and_leaves_no_part_file(tmp_path):
    """M5: a body cut short is fetched again; the ``.part`` file never outlives the call."""
    body = b"0123456789" * 100
    calls, slept = [], []

    class OnceCut:
        def stream(self, url):
            calls.append(url)
            return _Cut(body) if len(calls) == 1 else io.BytesIO(body)
    n, sha = X._download("https://x/f", tmp_path / "f.bin", fetch=OnceCut(), sleep=slept.append)
    import hashlib
    assert (n, sha) == (len(body), hashlib.sha256(body).hexdigest()) and len(calls) == 2 and slept == [1.5]
    assert (tmp_path / "f.bin").read_bytes() == body and not (tmp_path / "f.bin.part").exists()

    class AlwaysCut:
        def stream(self, url):
            return _Cut(body)
    slept.clear()
    with pytest.raises(RuntimeError):
        X._download("https://x/g", tmp_path / "g.bin", fetch=AlwaysCut(), attempts=3, sleep=slept.append)
    assert slept == [1.5, 3.0] and not (tmp_path / "g.bin").exists() and not (tmp_path / "g.bin.part").exists()


def test_a_body_short_of_its_content_length_or_a_parquet_without_its_footer_is_fetched_again(tmp_path):
    """2026-10-17, the first live fetch: the cards parquet came back 18,930 bytes short with no error raised, and
    extract-text failed on it.  A short body (against Content-Length) and a parquet file without its closing PAR1 are
    now fetched again."""
    class Resp(io.BytesIO):
        def __init__(self, body, length):
            super().__init__(body)
            self.headers = {"Content-Length": str(length)}

    good = b"PAR1" + b"x" * 100 + b"PAR1"
    calls, slept = [], []

    class ShortOnce:
        def stream(self, url):
            calls.append(url)
            return Resp(good[:50], len(good)) if len(calls) == 1 else Resp(good, len(good))
    n, _ = X._download("https://x/c.parquet", tmp_path / "c.parquet", fetch=ShortOnce(), sleep=slept.append)
    assert n == len(good) and len(calls) == 2 and (tmp_path / "c.parquet").read_bytes() == good

    class NoFooter:                                   # no Content-Length, and the footer is missing
        def stream(self, url):
            return io.BytesIO(good[:-4])
    with pytest.raises(RuntimeError):
        X._download("https://x/d.parquet", tmp_path / "d.parquet", fetch=NoFooter(), attempts=2, sleep=slept.append)
    assert not (tmp_path / "d.parquet").exists() and not (tmp_path / "d.parquet.part").exists()
