"""Corpus-frames generator: selection, the estimate and its gates, and the submission through the real registry API
(tmp registry, tmp run dirs; plan section 8, ``submit``)."""
import json
import math
from pathlib import Path

import pytest

from assistant_axis.gapgen import Candidate, freq
from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.corpus_frames import frames as F
from assistant_axis.gapgen.generators.corpus_frames import submit as SB
from assistant_axis.gapgen.generators.corpus_frames import table as T
from assistant_axis.gapgen.generators.corpus_frames import text as X
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.corpus_frames_fakes import fake_nouns
from assistant_axis.tests.test_gapgen_corpus_frames_table import H, build

TYPES = {**{f.id: f.type for f in F.FRAME_BANK}, **{f.id: f.type for f in X.text_frames()}}
QUIET = dict(echo=lambda *a: None, review_rate=(146.0, "test"), relabel=None)


def table():
    return build({
        "d_very": [H("good", 4000, 3000, "man"), H("kind", 500, 400, "fellow"), H("honest", 300, 230, "man"),
                   H("cheerful", 200, 150, "man"), H("jealous", 120, 100, "man"), H("blarg", 50, 40, "man")],
        "n_incorrigible": [H("liar", 100, 80), H("pedant", 50, 48), H("flirt", 45, 44)],
        "p_known_for_his": [H("honesty", 120, 100), H("integrity", 90, 70)],
        "h_he_was_always": [H("cheerful", 80, 70), H("clever", 60, 50)],
        "cards.copular_list": [H("shy", 9, 8), H("kind", 5, 5)],
    })


def fake_rows(n: int, frame: str = "d_very") -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        st = f"w{i:05d}"
        rows.append({"stem": st, "surface": st, "label": st, "surface_stem": st, "surface_tags": None,
                     "eligible": True, "frames": {frame: {"rank_volumes": i, "rank_lift": i, "volumes": n - i + 1}},
                     "union_rank": i, "rank_lift_union": i, "n_frames": 1, "best_frame": frame, "net_new": True,
                     "gloss_hint": None, "form": "adjective", "zipf": 3.0, "sources": ["books"], "registered": False,
                     "registered_decided": False, "corpus_stem_match": False, "queue_stem_match": False})
    return rows


@pytest.fixture
def env(tmp_path):
    cdir = tmp_path / "candidates"
    return cdir, cdir / "registry.jsonl"


def submit(env, rows, run_id="pilot", **kw):
    cdir, reg = env
    for k, v in QUIET.items():
        kw.setdefault(k, v)
    if "kept_target" not in kw:
        kw.setdefault("top_per_frame", 25)
    return SB.run_submit(run_id, table=rows, frame_types=TYPES, registry_path=reg, candidates_dir=cdir,
                         table_sha256="ff", bank_sha256=F.bank_sha256(), **kw)


def lines(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def test_select_top_takes_every_frames_top_n_deduplicated():
    t = table()
    rows, sel = SB.select_top(t, 2)
    assert sel["d_very"] == ["good", "kind"] and sel["n_incorrigible"] == ["liar", "pedantic"]
    assert sel["p_known_for_his"] == ["honest", "integrity"] and sel["h_he_was_always"] == ["cheerful", "clever"]
    stems = [r["stem"] for r in rows]
    assert len(stems) == len(set(stems)) and set(stems) == {s for v in sel.values() for s in v}
    assert [r["union_rank"] for r in rows] == sorted(r["union_rank"] for r in rows)
    assert all(r["eligible"] for r in rows)
    lift_rows, lift_sel = SB.select_top(t, 1, ordering="lift")
    assert lift_sel["d_very"] != sel["d_very"][:1]                          # lift puts a rarer word first


def test_registered_rows_ride_along_uncounted(env):
    t = table()
    reg = T.registry_index({"good#1": {"stem": "good", "sense_id": 1, "sources": [{"generator": "censuses"}],
                                       "filter": {"verdict": "trait"}, "novelty": {"decision": "covered"}},
                            "kind#1": {"stem": "kind", "sense_id": 1, "sources": [{"generator": "censuses"}]}})
    T.tag_rows(t, registry=reg)
    s = submit(env, t, top_per_frame=2, dry_run=True)
    rows, _ = SB.select_top(t, 2)
    assert s.n_selected == len(rows)                                        # the decided row is still selected
    assert s.n_charged == sum(SB.charged_rows(r) for r in rows)
    good = next(r for r in rows if r["stem"] == "good")
    kind = next(r for r in rows if r["stem"] == "kind")
    assert SB.charged_rows(good) == 0 and SB.charged_rows(kind) == 1         # decided: free; undecided: charged
    assert s.estimate["n"] == s.n_charged


def test_select_wave_cuts_net_new_rows_over_the_frames_kept():
    t = fake_rows(30) + fake_rows(5, frame="n_incorrigible")[:0]
    for i, r in enumerate(t):
        if i in (1, 3):                                                     # decided rows inside the cut
            r["net_new"], r["registered"], r["registered_decided"] = False, True, True
        if i == 4:                                                          # registered, undecided: counts
            r["registered"] = True
    rows, counted = SB.select_wave(t, kept_target=3, kept_share=0.5, frames_kept=["d_very"])
    need = math.ceil(3 / 0.5)
    assert counted == need and sum(1 for r in rows if r["net_new"]) == need
    assert len(rows) == need + 2 and [r["wave_rank"] for r in rows] == list(range(1, len(rows) + 1))
    other = [dict(r, frames={"n_incorrigible": r["frames"]["d_very"]}, stem="x" + r["stem"]) for r in t[:5]]
    rows2, _ = SB.select_wave(t + other, kept_target=3, kept_share=0.5, frames_kept=["d_very"])
    assert not any(r["stem"].startswith("x") for r in rows2)                 # a dropped frame's rows left out
    with pytest.raises(ValueError):
        SB.select_wave(t, kept_target=3, kept_share=0, frames_kept=["d_very"])


def test_the_wave_counts_noun_siblings_and_the_guard_refuses_the_literal_cut(env):
    t = fake_rows(40)
    for r in t:                                                             # every row a relabelled noun
        r["surface"] = r["surface_stem"] = "n" + r["stem"]
        r["surface_tags"] = {"net_new": True}
    s = submit(env, t, kept_target=10, kept_share=0.5, frames_kept=["d_very"], dry_run=True)
    assert s.n_counted == 20 and s.n_selected == 10 and s.n_charged == 20   # two registry rows a row
    assert s.projected_kept == pytest.approx(10.0)
    with pytest.raises(SB.ReviewLoadExceeded):
        submit(env, t, kept_target=10, kept_share=0.5, frames_kept=["d_very"], count_siblings=False, dry_run=True)


def test_candidates_one_per_stem_with_rank_score_and_source_ref():
    t = table()
    rows, _ = SB.select_top(t, 25)
    cands = SB.to_candidates(rows, "2026-10-20-pilot")
    assert len(cands) == len({c.surface for c in cands}) == len(rows)
    for c, r in zip(cands, rows):
        assert isinstance(c, Candidate) and c.generator == "corpus_frames" and c.sense_id == 1
        assert c.rank == r["union_rank"] and c.score == float(r["n_frames"]) and c.gloss_hint == r.get("gloss_hint")
        assert c.source_ref == SB.source_ref_for(r["best_frame"])
        assert SB.parse_source_ref(c.source_ref)["frame_key"] == r["best_frame"]
    by = {c.surface: c for c in cands}
    assert by["pedant"].source_ref == "frames:books:n_incorrigible"
    assert by["shy"].source_ref == "frames:cards:copular_list"
    with pytest.raises(ValueError):
        SB.parse_source_ref("mlm:single:roberta:x")


def test_candidates_file_before_the_registry_append_and_resubmit_is_a_noop(env, monkeypatch):
    cdir, reg = env
    seen = []
    real = SB.submit_candidates

    def watched(cands, **kw):
        seen.append((cdir / "runs" / "corpus_frames" / "pilot" / "candidates.jsonl").exists())
        return real(cands, **kw)
    monkeypatch.setattr(SB, "submit_candidates", watched)
    t = table()
    s = submit(env, t)
    assert seen == [True]
    d = cdir / "runs" / "corpus_frames" / "pilot"
    for name in ("candidates.jsonl", "keys.txt", "submit_report.json", "run.json", "usage.json"):
        assert (d / name).exists(), name
    usage = json.loads((d / "usage.json").read_text())
    assert usage["total_cost_usd"] == 0.0 and usage["n_calls"] == 0
    a = json.loads((d / "run.json").read_text())["args"]
    assert a["selection_by_frame"]["n_incorrigible"][:2] == ["liar", "pedantic"]
    assert a["table_sha256"] == "ff" and a["bank_sha256"] == F.bank_sha256() and a["ordering"] == "volumes"
    assert s.report["n_new"] == len(lines(d / "candidates.jsonl"))
    before = reg.read_bytes()
    again = submit(env, t)
    assert again.report["n_new"] == 0 and again.report["n_unchanged"] == len(lines(d / "candidates.jsonl"))
    assert reg.read_bytes() == before


def test_the_platform_adds_a_nouns_adjective(env):
    cdir, reg = env
    t = table()
    submit(env, t, relabel=fake_nouns(), corpus_stems=set())
    rows = Registry(reg).fold()
    assert "pedant#1" in rows and "pedantic#1" in rows
    assert rows["pedant#1"]["relabel"]["to_key"] == "pedantic#1"
    assert rows["pedantic#1"]["relabel"]["from_surface"] == "pedant"
    # the candidates file holds the noun only (the platform derives the adjective again on resubmission)
    cands = lines(cdir / "runs" / "corpus_frames" / "pilot" / "candidates.jsonl")
    assert "pedant" in {c["surface"] for c in cands} and "pedantic" not in {c["surface"] for c in cands}


def test_cost_guard(env):
    with pytest.raises(CostRefused):
        submit(env, fake_rows(10000), top_per_frame=10000, dry_run=True, budget_usd=500)   # over $20: needs the go
    s = submit(env, fake_rows(10000), top_per_frame=10000, dry_run=True, budget_usd=500, confirm_expensive=True,
               confirmed_by="Roger, test")
    assert s.estimate["total_usd"] > 20
    rows = fake_rows(2000)
    with pytest.raises(CostRefused):                                         # over the default $8 budget
        submit(env, rows, top_per_frame=2000, transport="batches", dry_run=True)
    ok = submit(env, rows, top_per_frame=2000, transport="batches", dry_run=True, budget_usd=18)
    assert 8 < ok.estimate["total_usd"] <= 18


def test_dry_run_writes_nothing(env):
    cdir, reg = env
    submit(env, table(), run_id="seed")
    before = reg.read_bytes()
    s = submit(env, table(), run_id="dry", dry_run=True)
    assert s.dry_run and reg.read_bytes() == before
    assert not (cdir / "runs" / "corpus_frames" / "dry").exists()


def test_followups_name_the_run_batch_pipeline_and_transport():
    est = SB.estimate_downstream_usd(100, transport="batches")
    fu = "\n".join(SB.followup_commands("2026-10-20-pilot", est))
    assert "--batch-id 2026-10-20-pilot_corpus_frames" in fu and "--run corpus_frames/2026-10-20-pilot" in fu
    assert "--pipeline split" in fu and "--transport batches" in fu and "gap_registry.py submit --from" in fu
    assert "corpus_frames_generator.py report --run-id 2026-10-20-pilot" in fu


def test_corpus_frames_is_neither_a_familiarity_nor_a_curated_generator():
    # The trap (QUESTIONS 58): Candidate.score here is n_frames, how many frames found the word, a quality signal; a
    # FAMILIARITY_GENERATORS entry would let a score >= 0.5 rescue every word below the Zipf floor, and a
    # CURATED_GENERATORS entry would rescue them all: a corpus count is a dictionary walk, not a curated list.
    assert "corpus_frames" not in freq.FAMILIARITY_GENERATORS
    assert "corpus_frames" not in freq.CURATED_GENERATORS


def test_exactly_one_mode():
    with pytest.raises(ValueError):
        SB.run_submit("x", table=[], frame_types={}, top_per_frame=1, kept_target=1, **QUIET)
    with pytest.raises(ValueError):
        SB.run_submit("x", table=[], frame_types={}, **QUIET)
    with pytest.raises(ValueError):
        SB.run_submit("x", table=[], frame_types={}, kept_target=300, **QUIET)   # the wave needs frames_kept
