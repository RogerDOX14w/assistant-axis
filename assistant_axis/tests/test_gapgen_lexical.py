"""Workstream 11's lexicon side (``assistant_axis.gapgen.lexical``; coding_plan_11_novelty_ensemble.md § 8, "lexical"):
label forms, placeholders, the lookup table, neighbours, antonym evidence, stem families, save and load, the Moby parser
and downloader, and the labelled-pairs measurement.  No network, no API: a fake ``wn`` object, a fake lexicon and a
six-line Moby fixture."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from assistant_axis.gapgen import lexical as LX
from assistant_axis.gapgen import novelty as NV


# --------------------------------------------------------------------------- a fake wn

@dataclass
class FSynset:
    id: str
    lems: list
    rels: dict = field(default_factory=dict)      # name -> [synset ids]
    wn: object = None

    def lemmas(self):
        return list(self.lems)

    def relations(self, name=None):
        out = {k: [self.wn.synset(i) for i in v] for k, v in self.rels.items()}
        return {name: out.get(name, [])} if name else out


@dataclass
class FSense:
    lemma: str
    rels: dict = field(default_factory=dict)      # name -> [lemmas]

    def relations(self, name=None):
        out = {k: [FSense(x) for x in v] for k, v in self.rels.items()}
        return {name: out.get(name, [])} if name else out

    def word(self):
        return FWord(self.lemma, [])


@dataclass
class FWord:
    lem: str
    sens: list

    def lemma(self):
        return self.lem

    def senses(self):
        return list(self.sens)


class FakeWordnet:
    """``synsets(form)``, ``synset(id)``, ``words(form)``: the bits of ``wn.Wordnet`` OewnLexicon uses."""

    def __init__(self, synsets, sense_rels=None):
        self._s = {}
        for sid, lems, rels in synsets:
            self._s[sid] = FSynset(sid, list(lems), dict(rels), self)
        self.sense_rels = sense_rels or {}            # lemma -> {rel: [lemmas]}
        self.n_queries = 0

    def synsets(self, form):
        self.n_queries += 1
        return [s for s in self._s.values() if form in s.lems]

    def synset(self, sid):
        return self._s[sid]

    def words(self, form):
        if not any(form in s.lems for s in self._s.values()):
            return []
        return [FWord(form, [FSense(form, self.sense_rels.get(form, {}))])]


SYNSETS = [
    ("s-agreeable", ["agreeable"], {}),
    ("s-pleasant", ["pleasant"], {"also": ["s-agreeable"], "similar": ["s-nice"]}),
    ("s-nice", ["nice"], {}),
    ("s-obdurate", ["obdurate", "unrepentant", "obstinate"], {}),
    ("s-kindhearted", ["kind-hearted", "kindhearted"], {}),
    ("s-militant", ["militant", "activist"], {}),
    ("s-disagreeable", ["disagreeable"], {}),
    ("s-agreeableness", ["agreeableness"], {}),
    ("s-kind", ["kind"], {}),
    ("s-careful", ["careful"], {}),
    ("s-careless", ["careless"], {}),
]
SENSE_RELS = {"agreeable": {"antonym": ["disagreeable"], "derivation": ["agreeableness", "agree"]},
              "disagreeable": {"antonym": ["agreeable"]}}


def oewn():
    return LX.OewnLexicon(FakeWordnet(SYNSETS, SENSE_RELS), lexicon_id="oewn:2024", wn_version="1.1.1",
                          lexicon_version="2024")


MOBY_FIXTURE = (b"pleasant,agreeable,delightful,nice\r\n"
                b"Obdurate,stubborn,unrepentant\r\n"
                b"stubborn,obdurate,\"hard, set\",mulish,\r\n"
                b"lonely\r\n"
                b"pleasant,genial\r\n"
                b"genial,pleasant,cordial")


def moby():
    return LX.MobyLexicon(rows=LX.parse_moby(MOBY_FIXTURE.decode()), sha256="m" * 64)


class FakeLexicon:
    """A lexicon from plain dicts: ``links[form] = {type: [words]}``, ``antonyms[form]``, ``derivations[form]``."""

    def __init__(self, name="oewn", links=None, antonyms=None, derivations=None, version="fake:1"):
        self.name = name
        self._links = links or {}
        self._ant = antonyms or {}
        self._der = derivations or {}
        self._version = version

    @property
    def version(self):
        return self._version

    def info(self):
        return {"id": self._version} if self.name == "oewn" else {"sha256": self._version, "source": "fake"}

    def synsets(self, form):
        """A form is known when it heads an entry or is a word some entry names (as a real lexicon's lemmas are)."""
        known = set(self._links) | set(self._ant) | set(self._der)
        known |= {w for d in self._links.values() for ws in d.values() for w in ws}
        known |= {w for ws in list(self._ant.values()) + list(self._der.values()) for w in ws}
        return [f"{self.name}:{form}"] if form in known else []

    def lemmas(self, sid):
        return [sid.split(":", 1)[1]]

    def related(self, sid, rel):
        return []

    def antonyms(self, form):
        return list(self._ant.get(form, []))

    def derivations(self, form):
        return list(self._der.get(form, []))

    def n_synonyms(self, form):
        return len(self._links.get(form, {}).get("synonym", []))

    def links(self, form):
        out = {t: {} for t in LX.LINK_TYPES}
        out["synonym"][LX.norm(form)] = f"{self.name}:{form}"
        for t, ws in self._links.get(form, {}).items():
            for w in ws:
                out[t].setdefault(LX.norm(w), f"{self.name}:{form}")
        return out


# --------------------------------------------------------------------------- a toy corpus

def ct(stem, label=None, *, partner=None, renamed=(), desc=None):
    return NV.CorpusTrait(stem=stem, label=label or stem.replace("_", " "), description=desc or f"This means {stem}.",
                          negative_label=None, pair_partner=partner, partners=[partner] if partner else [],
                          expands_to=[partner] if partner else [], renamed_from=list(renamed))


def corpus():
    return {"agreeable": ct("agreeable", partner="disagreeable"), "disagreeable": ct("disagreeable", partner="agreeable"),
            "agreeable_big_five": ct("agreeable_big_five", "agreeable (Big Five)"),
            "unrepentant": ct("unrepentant"), "aggressive": ct("aggressive", renamed=["militant"]),
            "kind": ct("kind"), "careful": ct("careful"), "kind_hearted": ct("kind_hearted", "kind-hearted")}


QUEUE = {"entries": [
    {"stem": "nice", "label": "nice", "status": "candidate", "entity_type": "trait", "description_draft": "This means nice."},
    {"stem": "agreeableness", "label": "agreeableness", "status": "backlog", "entity_type": "trait"},
    {"stem": "delightful", "label": "delightful", "status": "candidate", "entity_type": "trait",
     "description": "This means delightful."},
    {"stem": "gone", "label": "gone", "status": "not_adopted", "entity_type": "trait", "description": "x"},
    {"stem": "handed", "label": "handed", "status": "candidate", "entity_type": "trait", "description": "x",
     "gap_registry_key": "handed#1"},
    {"stem": "kind", "label": "kind", "status": "candidate", "entity_type": "trait", "description": "a corpus stem"},
    {"stem": "militant", "label": "militant", "status": "backlog", "entity_type": "trait"},
    {"stem": "non_contemplative", "label": "non-contemplative", "status": "candidate", "entity_type": "trait",
     "description": "a placeholder-shaped label"},
    {"stem": "guide", "label": "guide", "status": "candidate", "entity_type": "role", "description": "a role"},
]}


def lookup(lexicons=None):
    c = corpus()
    entries, _ = LX.live_queue_entries(QUEUE, c)
    return LX.build_lookup(c, entries, lexicons=lexicons or {"oewn": oewn()})


# --------------------------------------------------------------------------- forms

class TestForms:
    def test_label_forms(self):
        assert LX.label_forms("Kind-hearted") == ["kind-hearted", "kind hearted", "kindhearted"]
        assert LX.label_forms("agreeable (Big Five)") == ["agreeable"]
        assert LX.label_forms("careless (HEXACO)") == ["careless"]
        assert LX.label_forms("open_ended") == ["open ended", "open-ended"]        # a hyphen is dropped, a space is not
        assert LX.label_forms("odd (tentative, PC10)")[0] == "odd (tentative, pc10)"     # not a standard: kept
        assert LX.label_forms("good for you") == ["good for you", "good-for-you"]        # a phrase, whole

    def test_placeholder(self):
        assert LX.is_placeholder("non-careless") and LX.is_placeholder("non careless")
        assert LX.is_placeholder("non-careless (from HEXACO)")
        assert not LX.is_placeholder("nonconformist") and not LX.is_placeholder("none") and not LX.is_placeholder(None)

    def test_affix_pairs(self):
        got = dict(LX.affix_pairs("unkind"))
        assert got["kind"] == "prefix:un" and "unkind" not in got
        assert dict(LX.affix_pairs("careless"))["careful"] == "suffix:less/ful"
        assert dict(LX.affix_pairs("careful"))["careless"] == "suffix:less/ful"
        assert dict(LX.affix_pairs("kind"))["unkind"] == "prefix:un"
        assert "ble" not in dict(LX.affix_pairs("able")) and "shy" not in dict(LX.affix_pairs("ashy"))
        assert dict(LX.affix_pairs("amoral"))["moral"] == "prefix:a" and dict(LX.affix_pairs("unfit"))["fit"]


# --------------------------------------------------------------------------- the queue selection

class TestQueue:
    def test_live_entries_with_and_without_text(self):
        c = corpus()
        rows, rec = LX.live_queue_entries(QUEUE, c)
        by = {r["stem"]: r for r in rows}
        assert set(by) == {"nice", "agreeableness", "delightful", "non_contemplative"}
        assert by["nice"]["has_text"] and not by["agreeableness"]["has_text"]
        assert rec["n_name_only"] == 1 and rec["excluded"]["handed_to_registry"] == 1
        assert rec["excluded"]["a_corpus_stem"] == 1 and rec["excluded"]["a_corpus_files_renamed_from"] == 1
        # the entries with a text are exactly M3's search selection
        qt, _ = NV.queue_traits(QUEUE, c)
        assert set(qt) == {r["stem"] for r in rows if r["has_text"]}


# --------------------------------------------------------------------------- the table

class TestBuild:
    def test_every_label_recorded_with_text_versions_and_coverage(self):
        lk = lookup()
        assert set(lk.targets("corpus")) == set(corpus())
        assert set(lk.targets("queue")) == {"nice", "agreeableness", "delightful"}     # the placeholder left out
        assert lk.rows["agreeableness"]["has_text"] is False and lk.rows["nice"]["has_text"] is True
        assert lk.rows["aggressive"]["renamed_from"] == ["militant"]
        assert lk.rows["agreeable"]["oewn"]["synsets"] == ["s-agreeable"] and lk.rows["agreeable"]["has_partner"]
        assert lk.rows["agreeable_big_five"]["oewn"]["form"] == "agreeable"
        h = lk.header
        assert h["lexicons"]["oewn"] == {"id": "oewn:2024", "wn_version": "1.1.1", "lexicon_version": "2024"}
        assert h["n_corpus"] == 8 and h["n_queue"] == 3 and h["n_queue_name_only"] == 1
        assert h["coverage"]["oewn"]["corpus"] == {"found": 7, "of": 8}                # aggressive: only its old name
        assert h["coverage"]["oewn"]["queue_with_text"] == {"found": 1, "of": 2}      # nice yes, delightful no
        assert lk.lexicon_versions == {"oewn": "oewn:2024"}

    def test_the_content_hash_moves_with_a_label_and_with_the_lexicon(self):
        a = lookup().content_sha256
        assert a == lookup().content_sha256
        c = corpus()
        c["kind"] = ct("kind", "kindly")
        entries, _ = LX.live_queue_entries(QUEUE, c)
        assert LX.build_lookup(c, entries, lexicons={"oewn": oewn()}).content_sha256 != a
        other = LX.OewnLexicon(FakeWordnet(SYNSETS, SENSE_RELS), lexicon_id="oewn:2025")
        assert lookup({"oewn": other}).content_sha256 != a
        assert lookup({"oewn": oewn(), "moby": moby()}).content_sha256 != a


class TestNeighbours:
    def test_each_target_once_with_its_type_and_lexicon(self):
        lk = lookup()
        got = {x.stem: x for x in lk.neighbours("pleasant", "pleasant")}
        assert set(got) == {"agreeable", "agreeable_big_five", "nice"}
        assert got["agreeable"].link == "also" and got["agreeable"].lexicon == "oewn" and got["agreeable"].kind == "corpus"
        assert got["agreeable_big_five"].link == "also"                       # a standard's suffix dropped
        assert got["nice"].link == "similar" and got["nice"].kind == "queue" and not got["nice"].name_only
        assert got["agreeable"].via == "s-pleasant"

    def test_oewn_before_moby_and_moby_only(self):
        lk = lookup({"oewn": oewn(), "moby": moby()})
        got = lk.neighbours("pleasant", "pleasant")
        assert [x.lexicon for x in got] == sorted((x.lexicon for x in got), key=LX.LEXICONS.index)
        by = {x.stem: x for x in got}
        assert by["agreeable"].lexicon == "oewn" and "moby:synonym" in by["agreeable"].also_found
        assert not by["agreeable"].moby_only
        assert by["delightful"].lexicon == "moby" and by["delightful"].moby_only and by["delightful"].link == "synonym"
        # a reverse Moby link: genial's row lists pleasant, so genial -> pleasant would be found from either side
        assert {x.stem for x in lk.neighbours("cordial", "cordial")} == set()

    def test_own_stem_renamed_from_exclude_and_name_only(self):
        lk = lookup()
        assert all(x.stem != "unrepentant" for x in lk.neighbours("unrepentant", "unrepentant"))
        assert [x.stem for x in lk.neighbours("obdurate", "obdurate")] == ["unrepentant"]
        act = lk.neighbours("activist", "activist")
        assert [(x.stem, x.word) for x in act] == [("aggressive", "militant")]       # renamed_from folded
        assert lk.neighbours("pleasant", "pleasant", exclude={"agreeable", "nice"})[0].stem == "agreeable_big_five"
        der = LX.Lookup(rows=lookup().rows.values(), header={}, lexicons={"oewn": FakeLexicon(
            links={"agreeing": {"synonym": ["agreeableness"]}})})
        assert der.neighbours("agreeing", "agreeing")[0].name_only is True             # a text-less queue entry
        # separator-blind own stem: kind-hearted's own row is not its neighbour
        assert lk.neighbours("kindhearted", "kindhearted") == []


class TestAntonymsAndFamily:
    def test_antonym_evidence(self):
        lk = lookup()
        ev = lk.antonym_evidence("agreeable", "agreeable_x")
        assert [(a.stem, a.link, a.partner_has_file, a.rule) for a in ev] == [("disagreeable", "antonym", True, "prefix:dis")]
        ev = {a.stem: a for a in lk.antonym_evidence("unkind", "unkind")}
        assert ev["kind"].link == "negation_affix" and ev["kind"].rule == "prefix:un" and not ev["kind"].partner_has_file
        ev = {a.stem: a for a in lk.antonym_evidence("careless", "careless")}
        assert ev["careful"].link == "negation_affix" and ev["careful"].rule == "suffix:less/ful"
        assert all(a.stem != "agreeable" for a in lk.antonym_evidence("agreeable", "agreeable"))

    def test_family(self):
        lk = lookup()
        fam = lk.family_links("agreeable", "agreeable_x", candidates={"agreeably": "agreeably", "unagreeable": "unagreeable",
                                                                       "non_agreeable": "non-agreeable"})
        by = {d["stem"]: d for d in fam}
        assert by["agreeableness"]["via"] == "derivation" and by["agreeableness"]["kind"] == "queue"
        assert by["unagreeable"]["via"] == "affix" and by["unagreeable"]["kind"] == "candidate"
        assert "non_agreeable" not in by                                                 # never a placeholder
        assert lk.family("unkind", "unkind") == ["kind"]
        # the reverse derivation: agreeableness's family includes agreeable through agreeable's derivations
        assert "agreeable" in lk.family("agreeableness", "agreeableness_x")


class TestSaveLoad:
    def test_round_trip_and_a_stale_lexicon(self, tmp_path):
        lk = lookup()
        p = LX.save_lookup(lk, tmp_path / "lookup.json")
        doc = json.loads(p.read_text())
        assert "_provenance" in doc and doc["result"]["header"]["content_sha256"] == lk.content_sha256
        back = LX.load_lookup(p, lexicons={"oewn": oewn()})
        assert [x.stem for x in back.neighbours("pleasant", "p")] == [x.stem for x in lk.neighbours("pleasant", "p")]
        with pytest.raises(LX.StaleLookupError):
            LX.load_lookup(p, lexicons={"oewn": LX.OewnLexicon(FakeWordnet(SYNSETS), lexicon_id="oewn:2025")})


# --------------------------------------------------------------------------- Moby

class TestMoby:
    def test_parser(self):
        rows = LX.parse_moby(MOBY_FIXTURE.decode())
        assert rows["pleasant"] == ["agreeable", "delightful", "nice", "genial"]      # a repeated head merged
        assert rows["obdurate"] == ["stubborn", "unrepentant"]                         # lowercase
        assert rows["stubborn"] == ["obdurate", "hard, set", "mulish"]                 # a quoted comma; a trailing one
        assert "lonely" not in rows                                                     # a head with no synonym
        assert len(rows) == 4
        pg = "header text, with a comma\n*** START OF THE BOOK ***\na,b\n*** END OF THE BOOK ***\nfooter, too\n"
        assert LX.parse_moby(pg) == {"a": ["b"]}

    def test_lexicon(self):
        m = moby()
        assert m.synsets("Pleasant") == ["moby:pleasant"] and m.synsets("cordial") == []
        links = m.links("genial")["synonym"]
        assert set(links) == {"pleasant", "cordial"}                                   # its row, and pleasant's row
        assert m.n_heads == 4 and m.info()["source"] == LX.MOBY_SOURCE

    def test_downloader(self, tmp_path):
        calls = []

        def fetcher(url):
            calls.append(url)
            return MOBY_FIXTURE
        dest, src = tmp_path / "moby", tmp_path / "sources_manifest.json"
        dry = LX.fetch_moby(dest_dir=dest, fetcher=fetcher, dry_run=True, sources_manifest_path=src)
        assert calls == [] and not dest.exists() and "DRY-RUN" in dry.lines[-1]
        r = LX.fetch_moby(dest_dir=dest, fetcher=fetcher, sources_manifest_path=src, now="2026-10-13T00:00:00+00:00")
        assert calls == [LX.MOBY_URL] and r.fetched and (dest / LX.MOBY_FILE).read_bytes() == MOBY_FIXTURE
        assert any("WARNING" in ln and "expected" in ln for ln in r.lines)            # review S4: the fixture's size
        assert not (dest / (LX.MOBY_FILE + ".part")).exists()
        man = json.loads((dest / LX.DOWNLOAD_MANIFEST_NAME).read_text())
        assert man == json.loads(src.read_text())
        assert man["sha256"] == hashlib.sha256(MOBY_FIXTURE).hexdigest() and man["size"] == len(MOBY_FIXTURE)
        assert man["n_heads"] == 4 and man["licence"] == LX.MOBY_LICENCE and man["tool"] == LX.MOBY_TOOL
        assert man["url"] == LX.MOBY_URL and man["fetched_at"] == "2026-10-13T00:00:00+00:00"
        again = LX.fetch_moby(dest_dir=dest, fetcher=fetcher, sources_manifest_path=src)
        assert again.skipped and calls == [LX.MOBY_URL]                                # idempotent
        LX.fetch_moby(dest_dir=dest, fetcher=fetcher, sources_manifest_path=src, force=True)
        assert len(calls) == 2
        lex = LX.MobyLexicon(dest / LX.MOBY_FILE)
        assert lex.version == man["sha256"]                                            # the manifest's hash


# --------------------------------------------------------------------------- the labelled pairs

class TestLabelled:
    def test_measurement(self):
        pairs = [{"a": "pleasant", "b": "agreeable", "relation": "duplicate"},
                 {"a": "obdurate", "b": "gloss:unrepentant_x", "relation": "duplicate"},
                 {"a": "zzz", "b": "agreeable", "relation": "duplicate"},
                 {"a": "agreeable", "b": "disagreeable", "relation": "antonym"},
                 {"a": "kind", "b": "label:unkind", "relation": "antonym"},
                 {"a": "nice", "b": "careful", "relation": "unrelated"},
                 {"a": "kind", "b": "careful", "relation": "near_distinct"}]
        ext = {"gloss:unrepentant_x": {"label": "unrepentant"}, "label:unkind": {"label": "unkind"}}
        lex = {"oewn": oewn()}
        lex["oewn"].wordnet._s["s-unkind"] = FSynset("s-unkind", ["unkind"], {}, lex["oewn"].wordnet)
        m = LX.labelled_measurement(pairs, lex, corpus_labels={"agreeable": "agreeable"}, externals=ext)
        d = m["by_lexicon"]["oewn"]
        assert d["duplicate"]["n"] == 3 and d["duplicate"]["both_found"] == 2 and d["duplicate"]["abstain"] == 1
        assert d["duplicate"]["linked"] == 2 and d["duplicate"]["by_link"] == {"synonym": 1, "similar": 0, "also": 1}
        assert d["duplicate"]["recall"] == 1.0
        assert d["antonym"]["antonym_linked"] == 2 and d["antonym"]["by_antonym"] == {"antonym": 1, "negation_affix": 1}
        assert d["unrelated"]["false_flag"] == 0.0 and d["near_distinct"]["false_flag"] == 0.0
        assert LX.link_between("agreeable", "pleasant", lex["oewn"]) == "also"         # either direction
        assert LX.antonym_between("careless", "careful", None) == "negation_affix"
