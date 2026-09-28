"""gapgen.wordnet with a fake ``wn`` module; the real-database test skips
without ``data/external/wn`` (run setup_external.py --wn)."""
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen import wordnet as gw
from assistant_axis.gapgen.paths import wn_data_dir


class FakeWordnet:
    DATA = {"cool": ["a", "a", "s", "n", "v"], "kind": ["a", "n"], "librarian": ["n"],
            "well-read": ["s"], "kind to animals": []}

    def __init__(self, lexicon=None):
        self.lexicon = lexicon

    def synsets(self, form):
        return [SimpleNamespace(pos=p) for p in self.DATA.get(form, [])]

    def words(self, pos=None):
        lem = {"a": ["Cool", "kind"], "s": ["well-read", "cool"]}[pos]
        return [SimpleNamespace(lemma=lambda x=x: x) for x in lem]


class FakeWn:
    def __init__(self, installed=True):
        self.installed = installed
        self.downloads = []
        self.Wordnet = FakeWordnet

    def lexicons(self, lexicon=None):
        return [SimpleNamespace(id="oewn", version="2024")] if self.installed else []

    def download(self, spec):
        self.downloads.append(spec)
        self.installed = True


def test_sense_info_adjective_senses():
    info = gw.sense_info("cool", wordnet=FakeWordnet())
    assert info.found and info.n_senses == 3 and info.n_senses_all == 5
    assert info.pos == ["a", "n", "s", "v"]


def test_sense_info_noun_only_counts_all():
    info = gw.sense_info("librarian", wordnet=FakeWordnet())
    assert info.n_senses == 1 and info.pos == ["n"]


def test_sense_info_variants_and_missing():
    assert gw.sense_info("Well-Read", wordnet=FakeWordnet()).found
    assert gw.sense_info("well read", wordnet=FakeWordnet()).found
    miss = gw.sense_info("kind to animals", wordnet=FakeWordnet())
    assert not miss.found and miss.n_senses == 0
    assert miss.as_dict() == {"n_senses": 0, "pos": [], "found": False, "n_senses_all": 0}


def test_ensure_oewn_downloads_once():
    fake = FakeWn(installed=False)
    assert gw.ensure_oewn(wn_module=fake)
    assert fake.downloads == ["oewn:2024"]
    assert gw.ensure_oewn(wn_module=fake)
    assert fake.downloads == ["oewn:2024"]


def test_ensure_oewn_no_download():
    fake = FakeWn(installed=False)
    assert not gw.ensure_oewn(wn_module=fake, download=False)
    assert fake.downloads == []


def test_oewn_handle():
    fake = FakeWn()
    h = gw.oewn(wn_module=fake)
    assert isinstance(h, FakeWordnet) and h.lexicon == "oewn:2024"
    assert gw.oewn(wn_module=fake) is h


def test_adjective_lemmas_dedup():
    assert gw.adjective_lemmas(wordnet=FakeWordnet()) == ["Cool", "kind", "well-read"]


@pytest.mark.skipif(not (wn_data_dir() / "wn.db").exists(), reason="OEWN not installed in data/external/wn")
def test_real_oewn():
    assert gw.oewn_installed()
    info = gw.sense_info("stubborn")
    assert info.found and ("a" in info.pos or "s" in info.pos)
    assert gw.sense_info("kind to animals").found is False
    adj = gw.adjective_lemmas()
    assert len(adj) > 15000
