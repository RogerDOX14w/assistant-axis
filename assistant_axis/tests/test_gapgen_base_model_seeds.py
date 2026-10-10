"""Base-model generator, task 2: the seed bundle (TDA adjectives from the census table, wiki_bio openings, O*NET
titles, common nouns).  Fixtures only; no network, no OEWN."""
import builtins
import io
import json
import random

import pytest

from assistant_axis.gapgen.generators.base_model import seeds as S
from assistant_axis.tests.base_model_fakes import (
    CENSUS_TABLE_SMALL, ONET_SMALL, census_table_text, make_wikibio_zip,
)

NOUNS = ["lighthouse", "spreadsheet", "harvest", "violin", "glacier", "ledger"]


@pytest.fixture
def dirs(tmp_path):
    wb = tmp_path / "external" / "wikibio"
    make_wikibio_zip(wb / "data" / "wikipedia-biography-dataset.zip")
    onet = tmp_path / "external" / "onet"
    onet.mkdir(parents=True)
    (onet / "occupation_data.csv").write_bytes(ONET_SMALL.read_bytes())
    return wb, onet


def load(dirs, **kw):
    wb, onet = dirs
    kw.setdefault("nouns", NOUNS)
    return S.load_seed_bundle(census_table=CENSUS_TABLE_SMALL, wikibio_dir=wb, onet_dir=onet, **kw)


def test_fixture_is_current():
    assert CENSUS_TABLE_SMALL.read_text(encoding="utf-8") == census_table_text()


def test_tda_seeds_honor_the_familiarity_floor(dirs):
    b = load(dirs)
    words = [a.word for a in b.adjectives]
    # TDA rows with prop >= 0.5, in rank order; never the Allport-only row or the malformed one
    assert words == ["brave", "lazy", "stubborn", "blunt", "gentle", "brash", "bumptious", "brusque"]
    assert b.adjectives[2].gloss.startswith("tenaciously unwilling") and b.adjectives[2].prop == 0.88
    assert [a.word for a in load(dirs, familiarity_floor=0.85).adjectives] == ["brave", "lazy", "stubborn", "blunt"]
    assert len(load(dirs, familiarity_floor=0.0).adjectives) == 10


def test_wikibio_loader_yields_ref_name_and_opening(dirs):
    wb, _ = dirs
    bios = list(S.iter_wikibio(wb / "data" / "wikipedia-biography-dataset.zip", split="train"))
    assert [b.ref for b in bios] == ["wikibio:train:0", "wikibio:train:1", "wikibio:train:2", "wikibio:train:3"]
    w = bios[0]
    assert w.name == "Walter Extra"
    assert w.text == ("Walter Extra is a german award-winning aerobatic pilot, chief aircraft designer and founder of "
                      "extra flugzeugbau (extra aircraft construction), a manufacturer of aerobatic aircraft. Extra "
                      "was trained as a mechanical engineer.")
    assert bios[1].text.startswith("Aurelio López rodríguez (1948 – 1992) was a mexican")
    assert bios[2].name == "Ada Short"           # no name field: the article-title field
    # the pool keeps openings of at least 15 words, at most 200
    b = load(dirs)
    assert [x.ref for x in b.bios] == ["wikibio:train:0", "wikibio:train:2"]
    long = S.first_words("one two three four five six seven. eight nine ten.", 8)
    assert long == "one two three four five six seven."
    assert S.first_words("a b c d e f g h i j", 4) == "a b c d ..."


def test_bio_pool_is_cached_and_reused(dirs):
    wb, _ = dirs
    b1 = load(dirs, bio_pool_size=1, pool_seed=3)
    caches = sorted(p.name for p in wb.glob("bio_pool_*.jsonl"))
    assert caches == ["bio_pool_train_k1_s3.jsonl"]
    b2 = load(dirs, bio_pool_size=1, pool_seed=3)
    assert b1.bios == b2.bios and len(b1.bios) == 1


def test_onet_parse():
    titles = S.parse_onet(ONET_SMALL)
    assert titles == ["chief executives", "software developers", "registered nurses", "restaurant cooks",
                      "electricians"]


def test_seeded_determinism(dirs):
    b1, b2 = load(dirs), load(dirs)
    draws = []
    for b in (b1, b2):
        r = random.Random(7)
        draws.append(([a.word for a in b.draw_adjectives(r, 3)], b.draw_bio(r).ref, b.draw_occupation(r),
                      b.draw_nouns(r, 2), [a.word for a in b.draw_adjectives(r, 2, letter="b")]))
    assert draws[0] == draws[1]
    assert all(w.startswith("b") for w in draws[0][4])
    r1, r2 = random.Random(7), random.Random(8)
    seq1 = [tuple(a.word for a in b1.draw_adjectives(r1, 3)) for _ in range(10)]
    seq2 = [tuple(a.word for a in b1.draw_adjectives(r2, 3)) for _ in range(10)]
    assert seq1 != seq2


def test_letter_fallback(dirs):
    b = load(dirs)
    # fewer than k words start with the letter: the draw falls back to the whole list
    got = b.draw_adjectives(random.Random(1), 3, letter="z")
    assert len(got) == 3


def test_manifest_records_inputs_not_text(dirs):
    b = load(dirs)
    m = b.manifest
    assert m["n_adjectives"] == 8 and m["familiarity_floor"] == 0.5 and m["n_bios"] == 2
    assert m["n_occupations"] == 5 and m["n_nouns"] == len(NOUNS)
    assert len(m["census_table_sha256"]) == 64 and len(m["onet_sha256"]) == 64
    assert "Walter" not in json.dumps(m)         # no biography text in what the tracked files will carry


def test_seeds_module_reads_nothing_under_traits_or_roles(dirs, tmp_path, monkeypatch):
    data = tmp_path / "data"
    for kind in ("traits", "roles"):
        d = data / kind / "instructions"
        d.mkdir(parents=True)
        (d / "zorbish.json").write_text(json.dumps({"positive_label": "zorbish", "description": "This means x."}))
    monkeypatch.setenv("ASSISTANT_AXIS_DATA_DIR", str(data))
    opened = []
    real_open = builtins.open

    def watch(file, *a, **k):
        opened.append(str(file))
        return real_open(file, *a, **k)
    monkeypatch.setattr(builtins, "open", watch)
    monkeypatch.setattr(io, "open", watch)
    b = load(dirs)
    r = random.Random(0)
    for _ in range(20):
        b.draw_adjectives(r, 3), b.draw_bio(r), b.draw_occupation(r), b.draw_nouns(r, 3)
    assert opened, "the watch saw no reads at all"
    assert not [p for p in opened if "/traits/" in p or "/roles/" in p]
