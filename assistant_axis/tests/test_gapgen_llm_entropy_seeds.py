"""LLM-entropy generator: the Wikidata seeds, the throttle, the redaction and the fetch record (coding_plan_06
section 8, ``seeds``).  A fake HTTP session answers in the API shapes recorded on 2026-10-13; every person is
invented (``llm_entropy_fakes``).  No network."""
from __future__ import annotations

import json
import random

import pytest

from assistant_axis.gapgen.generators.llm_entropy import seeds as SD
from assistant_axis.tests import llm_entropy_fakes as F


class Clock:
    def __init__(self):
        self.t = 1000.0
        self.slept: list[float] = []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def throttle(session, clock=None):
    clock = clock or Clock()
    return SD.Throttle(session, clock=clock, sleep=clock.sleep), clock


def test_random_items_keep_only_humans():
    th, _ = throttle(F.FakeWikidataSession())
    stats = SD.FetchStats()
    seeds = SD.fetch_real(4, session=th, stats=stats, now=lambda: "2026-10-17T00:00:00+00:00")
    assert [s.seed_id for s in seeds] == ["b:r0001", "b:r0002", "b:r0003", "b:r0004"]
    assert {s.qid for s in seeds} == {q for q, *_ in F.REAL_PEOPLE}            # the filler items are not humans
    assert stats.humans_seen == 4 and stats.items_seen >= 4 and not stats.shortfall
    by = {s.qid: s for s in seeds}
    assert by["Q990000101"].born == "1841" and by["Q990000101"].died == "1903" and by["Q990000101"].era == "1800-1899"
    assert by["Q990000102"].era == "<1800"                     # born unknown, died 1690: by death year - 60
    assert by["Q990000103"].era == "1950+" and not by["Q990000103"].dead


def test_dead_only_needs_a_date_of_death():
    th, _ = throttle(F.FakeWikidataSession())
    stats = SD.FetchStats()
    seeds = SD.fetch_real(4, session=th, dead_only=True, stats=stats, max_rounds=3)
    assert {s.qid for s in seeds} == {"Q990000101", "Q990000102", "Q990000104"}
    assert stats.skipped_alive == 1 and stats.shortfall == {"real": 1}


def test_numbering_starts_where_asked():
    th, _ = throttle(F.FakeWikidataSession())
    assert [s.seed_id for s in SD.fetch_real(2, session=th, start=41)] == ["b:r0041", "b:r0042"]


def test_fictional_path_queries_each_class_once_per_call():
    session = F.FakeWikidataSession()
    th, _ = throttle(session)
    stats = SD.FetchStats()
    seeds = SD.fetch_fictional(3, session=th, rng=random.Random(0), stats=stats)
    sparql = [c for c in session.calls if "sparql" in c["url"]]
    per_class: dict = {}
    for c in sparql:
        q = c["params"]["query"]
        cls = q.split("wd:")[1].split()[0]
        per_class.setdefault(cls, []).append("count" if "COUNT" in q else "data")
    assert set(per_class) == set(SD.FICTIONAL_CLASSES)
    assert all(sorted(v) == ["count", "data"] for v in per_class.values())     # one count, one data query each
    assert [s.kind for s in seeds] == ["fictional"] * 3 and [s.seed_id for s in seeds] == ["b:f0001", "b:f0002",
                                                                                           "b:f0003"]
    assert {s.qid for s in seeds} == {q for q, *_ in F.FICTIONAL_PEOPLE}      # labelled rows only, topped up
    assert all(s.era == "unknown" for s in seeds)
    assert all(c["label_ok"] for c in stats.fictional_classes.values())


def test_a_class_whose_label_does_not_match_is_skipped():
    labels = dict(SD.FICTIONAL_CLASSES, Q1569167="moth")
    session = F.FakeWikidataSession(class_labels=labels)
    th, _ = throttle(session)
    stats = SD.FetchStats()
    SD.fetch_fictional(2, session=th, rng=random.Random(0), stats=stats)
    assert stats.fictional_classes["Q1569167"]["label_ok"] is False
    assert not any("Q1569167" in c["params"].get("query", "") for c in session.calls)


def test_429_is_retried_with_the_backoff_and_the_fifth_failure_raises():
    th, clock = throttle(F.FakeWikidataSession(fail_429=4))
    out = th.get_json(SD.WIKIDATA_API, {"action": "query", "list": "random", "rnlimit": "5"}, what="random")
    assert "query" in out and th.counts["retries"] == 4
    assert [s for s in clock.slept if s in SD.BACKOFF_S] == list(SD.BACKOFF_S)
    th2, _ = throttle(F.FakeWikidataSession(fail_429=5))
    with pytest.raises(SD.FetchError) as exc:
        th2.get_json(SD.WIKIDATA_API, {"action": "query"}, what="random")
    assert "HTTP 429" in str(exc.value) and "5 attempts" in str(exc.value)


def test_a_body_cut_off_mid_read_is_retried():
    """2026-10-17, the first live seeds dry run: a large wbgetentities answer stopped with http.client.IncompleteRead,
    which is no OSError, and the fetch crashed instead of retrying."""
    import http.client

    class CutOnce:
        def __init__(self):
            self.inner, self.n = F.FakeWikidataSession(), 0

        def get(self, url, **kw):
            self.n += 1
            if self.n == 1:
                raise http.client.IncompleteRead(b"x" * 10)
            return self.inner.get(url, **kw)

    th, _ = throttle(CutOnce())
    out = th.get_json(SD.WIKIDATA_API, {"action": "query", "list": "random", "rnlimit": "5"}, what="random")
    assert "query" in out and th.counts["retries"] == 1


def test_the_throttle_never_sends_two_requests_within_two_seconds():
    th, clock = throttle(F.FakeWikidataSession())
    SD.fetch_real(4, session=th)
    SD.fetch_fictional(2, session=th, rng=random.Random(1))
    gaps = [b - a for a, b in zip(th.sent, th.sent[1:])]
    assert len(th.sent) >= 10 and min(gaps) >= SD.MIN_INTERVAL_S


def test_a_seed_repr_carries_no_name_description_or_qid():
    s = SD.PersonSeed(seed_id="b:r0001", kind="real", qid="Q990000101", name="Quillon Varnaby",
                      description="invented tram conductor of Zellwick")
    r = repr(s)
    assert "Quillon" not in r and "Zellwick" not in r and "Q990000101" not in r and "b:r0001" in r
    assert set(s.public()) == {"seed_id", "kind", "era"}


def test_redact_and_leaks():
    s = SD.PersonSeed(seed_id="b:r0002", kind="real", qid="Q990000102", name="Orsolya Thrummet",
                      description="invented glassblower, ID = 5550123")
    text = ("Orsolya Thrummet, an invented glassblower, ID = 5550123 (Q990000102), was thrummet-like; ORSOLYA's "
            "habits and Thrümmet's furnace; 5550123 again.")
    red = SD.redact(text, s)
    assert SD.leaks(red, s) == [] and "5550123" not in red and "Q990000102" not in red
    assert "this person's habits" in red
    assert SD.leaks(text, s) == ["description", "name", "qid"]
    assert SD.redact(None, s) is None


def test_name_in_label():
    s = SD.PersonSeed(seed_id="b:r0001", kind="real", qid="Q1", name="Quillon Varnaby", description=None)
    assert SD.name_in_label("varnaby-esque", s) and SD.name_in_label("quillon", s)
    assert not SD.name_in_label("varnished", s) and not SD.name_in_label(None, s)


def test_era_bands():
    assert SD.era_band("1799") == "<1800" and SD.era_band("1800") == "1800-1899" and SD.era_band("1949") == \
        "1900-1949" and SD.era_band("1950") == "1950+" and SD.era_band(None) == "unknown"
    assert SD.era_band(None, "1930") == "1800-1899" and SD.era_band("-44") == "<1800"


def _entry(run_id="2026-10-18-pilot", session_id="s1"):
    seeds = [SD.PersonSeed(seed_id="b:r0001", kind="real", qid="Q990000101", name="Quillon Varnaby",
                           description="invented tram conductor of Zellwick", born="1841", era="1800-1899"),
             SD.PersonSeed(seed_id="b:f0001", kind="fictional", qid="Q990000201", name="Captain Zarnath Quell",
                           description="invented starship captain of a made-up serial")]
    return seeds, SD.fetch_record_entry(seeds, run_id=run_id, session_id=session_id, requested={"real": 1,
                                        "fictional": 1}, dead_only=False, requests={"random-item request": 2},
                                        stats=SD.FetchStats(), fetched_at="2026-10-17T09:00:00+00:00")


def test_the_fetch_record_carries_counts_sha_licence_and_era_bands(tmp_path):
    seeds, e = _entry()
    assert e["n_real"] == 1 and e["n_fictional"] == 1 and e["era_bands"]["1800-1899"] == 1
    assert e["licence"].startswith("CC0") and len(e["seeds_sha256"]) == 64 and e["captured_on"] == "2026-10-17"
    assert e["seeds"] == [{"seed_id": "b:r0001", "kind": "real", "era": "1800-1899"},
                          {"seed_id": "b:f0001", "kind": "fictional", "era": "unknown"}]
    p = tmp_path / "person_seeds_fetch.json"
    SD.write_fetch_record(p, e)
    body = p.read_text(encoding="utf-8")
    for secret in F.every_secret():
        assert secret not in body
    assert json.loads(body)["runs"][0]["run_id"] == "2026-10-18-pilot"


def test_the_record_is_not_overwritten_without_force(tmp_path):
    p = tmp_path / "person_seeds_fetch.json"
    _, e = _entry()
    SD.write_fetch_record(p, e)
    with pytest.raises(FileExistsError):
        SD.write_fetch_record(p, _entry(session_id="s2")[1])
    SD.write_fetch_record(p, _entry(session_id="s2")[1], force=True)
    runs = json.loads(p.read_text())["runs"]
    assert [r["session_id"] for r in runs] == ["s1", "s2"]           # appended beside, never replaced
    assert SD.run_has_fetch(p, "2026-10-18-pilot") and not SD.run_has_fetch(p, "other")
    assert SD.next_seed_numbers(p, "2026-10-18-pilot") == (2, 2) and SD.next_seed_numbers(p, "other") == (1, 1)


def test_an_entry_carrying_a_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        SD.write_fetch_record(tmp_path / "x.json", {"run_id": "r", "seeds": [{"name": "Quillon Varnaby"}]})


def test_summary_lines_name_nobody():
    th, _ = throttle(F.FakeWikidataSession())
    stats = SD.FetchStats()
    seeds = SD.fetch_real(4, session=th, stats=stats) + SD.fetch_fictional(3, session=th, rng=random.Random(0),
                                                                          stats=stats)
    text = "\n".join(SD.summary_lines(seeds, stats, th.counts))
    assert "4 real, 3 fictional" in text and "1800-1899" in text
    for secret in F.every_secret():
        assert secret not in text


# --------------------------------------------------------------------------- Fable's review, 2026-10-17

QV = SD.PersonSeed(seed_id="b:r0001", kind="real", qid="Q990000101", name="Quillon Varnaby",
                   description="invented tram conductor of Zellwick", alt_names=("キロン・ヴァーナビー", "Q. Varnaby"))
SUFFIXED = ["Varnabyesque", "a Varnabian habit", "the Varnabys", "Varnabyish", "VARNABYS'", "Zellwickian pride",
            "キロン・ヴァーナビーの癖"]


@pytest.mark.parametrize("text", SUFFIXED)
def test_suffixed_forms_of_a_name_are_redacted_and_seen(text):
    """Blocker 1: a name token of four characters or more matches with up to six letters after it (and, ending in a
    vowel or y, without that letter); a description's proper name and an other-script name are covered too."""
    assert SD.leaks(text, QV) != []
    red = SD.redact(text, QV)
    assert SD.leaks(red, QV) == [] and "this person" in red


@pytest.mark.parametrize("label,hit", [("varnabyesque", True), ("varnabian", True), ("q. varnaby-like", True),
                                       ("zellwickian", False), ("varnished", False), ("variable", False),
                                       ("quill-pen", False)])
def test_name_in_label_sees_suffixed_forms(label, hit):
    assert SD.name_in_label(label, QV) is hit


def test_description_proper_names_but_not_common_words():
    assert SD.description_tokens(QV) == ["zellwick"]
    assert SD.description_in_label("zellwickian", QV) and not SD.description_in_label("tram-minded", QV)
    common = SD.PersonSeed(seed_id="b:r0002", kind="real", qid="Q1", name="Zzq Xxw",
                           description="The person of Name, a Pellbridge painter")
    assert SD.description_tokens(common) == ["pellbridge"]               # "The", "Name" (and "person") are kept
    fict = SD.PersonSeed(seed_id="b:f0001", kind="fictional", qid="Q2", name="Zzq Xxw", description="Star serial")
    assert SD.description_tokens(fict) == []


def test_a_short_token_matches_whole_words_only():
    s = SD.PersonSeed(seed_id="b:r0003", kind="real", qid="Q3", name="Ann Bexley", description=None)
    assert SD.redact("Ann's annual plan", s) == "this person's annual plan"
    assert SD.redact("the Bexleyite way", s) == "the this person way"


def test_the_fetch_keeps_other_language_names_in_memory_and_asks_for_them():
    session = F.FakeWikidataSession()
    th, _ = throttle(session)
    seeds = SD.fetch_real(4, session=th)
    by = {s.qid: s for s in seeds}
    assert by["Q990000101"].alt_names == ("キロン・ヴァーナビー", "Q. Varnaby") and by["Q990000102"].alt_names == ()
    assert "キロン" not in repr(by["Q990000101"])
    ent = next(c for c in session.calls if c["params"].get("action") == "wbgetentities")
    assert "aliases" in ent["params"]["props"] and "|ja|" in ent["params"]["languages"]
