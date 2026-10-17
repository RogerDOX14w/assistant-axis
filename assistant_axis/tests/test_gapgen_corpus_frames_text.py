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
    assert e["cards"]["file"] == "cards/train-00000-of-00001.parquet" and e["cards"]["licence"] == "CC BY 4.0"
    assert e["pippa"]["approval"] == appr and e["pippa"]["licence"] == "Apache-2.0"
    assert e["pippa"]["size_bytes"] == len(hub.files["pippa_deduped.jsonl"])
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
