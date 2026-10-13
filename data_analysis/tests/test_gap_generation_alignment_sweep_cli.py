"""CLI tests for data_analysis/gap_generation/alignment_sweep.py, end to end with no network: a fake fetcher, a fake
Anthropic client, the hash embedder, a skipped probe, a tmp registry and tmp run dirs.  The rubrics are the real
pinned ones."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.alignment_sweep import GATE_GOLD_PATH
from assistant_axis.gapgen.generators.alignment_sweep import fetch as F
from assistant_axis.gapgen.generators.alignment_sweep import probe as P
from assistant_axis.gapgen.generators.alignment_sweep.sources import SOURCES
from assistant_axis.gapgen.registry import Registry, read_candidates
from assistant_axis.tests.alignment_sweep_fakes import CONSTITUTION_HTML, SPEC_MD, extraction_reply, item, pole
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from data_analysis.gap_generation import alignment_sweep as CLI

LICENSE_TXT = b"Creative Commons Legal Code\n\nCC0 1.0 Universal\n"


def snapshot(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_size) for p in root.rglob("*") if p.is_file())


@pytest.fixture
def env(tmp_path, monkeypatch):
    ms, con = SOURCES["model_spec"], SOURCES["constitution"]
    pages = {ms.url: SPEC_MD.encode(), ms.license_file_url: LICENSE_TXT, con.url: CONSTITUTION_HTML.encode()}
    monkeypatch.setattr(F, "_urlopen_bytes", lambda url: pages[url])
    monkeypatch.setattr(P, "key_status", lambda env_path=None: "skipped: no OPENROUTER_API_KEY loads")
    cdir = tmp_path / "candidates"
    common = ["--registry", str(cdir / "registry.jsonl"), "--candidates-dir", str(cdir),
              "--external-dir", str(tmp_path / "ext"), "--sources-manifest", str(tmp_path / "sources_manifest.json")]
    return tmp_path, common, cdir


def responder(kw):
    if '"where"' in kw["system"][0]["text"]:                                # the gate (draft 3's three fields)
        return json.dumps({"system_prompt": "Be it. Always.", "reason": "r", "where": "chat",
                           "elicitation": "Ask it for advice on something it would rather dodge.",
                           "judge_needs": "At face value from the answer."})
    u = user_text(kw)
    if "<passage>\n## Do not lie" in u:
        return extraction_reply([item(pole("truth-telling", "This means saying only what one believes to be true."),
                                      pole("comfortable liar", "This means saying whatever pleases the listener."))])
    if "<passage>\n## Act within scope" in u:
        return extraction_reply([item(pole("stays in scope", "This means doing only what the task asked for."),
                                      pole("oversteps the task", "This means doing things the task never asked."),
                                      enactability="agentic-only")])
    return extraction_reply([])


def test_fetch_dry_run_writes_nothing(tmp_path, capsys):
    rc = CLI.main(["--external-dir", str(tmp_path / "ext"), "--sources-manifest", str(tmp_path / "m.json"), "fetch",
                   "--dry-run"])
    assert rc == 0 and not (tmp_path / "ext").exists() and not (tmp_path / "m.json").exists()
    assert "raw.githubusercontent.com/openai/model_spec/7f1cf79" in capsys.readouterr().out


def test_end_to_end(env, monkeypatch, capsys):
    root, common, cdir = env
    assert CLI.main(common + ["fetch"]) == 0
    man = json.loads((root / "sources_manifest.json").read_text())
    assert [e["key"] for e in man] == ["model_spec", "constitution"]
    assert CLI.main(common + ["chunk"]) == 0
    chunks = (root / "ext" / "chunks.jsonl").read_text().splitlines()
    assert len(chunks) == 9

    # extract: dry run first (nothing written, no call), then the real run on a fake client
    calls = []

    def fake_client():
        c = FakeAsyncAnthropic(responder)
        calls.append(c)
        return c
    monkeypatch.setattr(CLI, "_anthropic_client", fake_client)
    before = snapshot(root)
    assert CLI.main(common + ["extract", "--run-id", "t1", "--chunks", "6", "--seed", "0", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert snapshot(root) == before and not calls
    assert "total estimate" in out and "DRY-RUN" in out and "<passage>" in out
    assert CLI.main(common + ["extract", "--run-id", "t1", "--allow-dirty"]) == 0
    rdir = cdir / "runs" / "alignment_sweep" / "t1"
    ext = [json.loads(x) for x in (rdir / "extraction.jsonl").read_text().splitlines()]
    assert [e["label"] for e in ext] == ["stays in scope", "oversteps the task", "truth-telling", "comfortable liar"]
    summ = json.loads((rdir / "extract_summary.json").read_text())
    assert summ["n_pairs"] == 2 and summ["n_chunks"] == 9 and summ["label_form"] == "judge-display-v1"
    usage = json.loads((rdir / "usage.json").read_text())
    assert usage["n_calls"] == 9 and usage["total_cost_usd"] > 0
    # resume: the same run again sends nothing
    n_before = sum(len(c.calls) for c in calls)
    assert CLI.main(common + ["extract", "--run-id", "t1", "--allow-dirty"]) == 0
    assert sum(len(c.calls) for c in calls) == n_before

    # dedupe with the hash embedder at a given threshold
    assert CLI.main(common + ["dedupe", "--run-id", "t1", "--embedder", "hash", "--threshold", "0.99"]) == 0
    groups = json.loads((rdir / "dedup_groups.json").read_text())["result"]
    assert groups["n_groups"] == 4 and groups["partner_hints"]["ms003-1a"] == "oversteps the task"

    # submit: dry run, then real; replayable with gap_registry.py submit --from
    reg = cdir / "registry.jsonl"
    assert CLI.main(common + ["submit", "--run-id", "t1", "--dry-run"]) == 0
    assert not reg.exists() and not (rdir / "candidates.jsonl").exists()
    assert CLI.main(common + ["submit", "--run-id", "t1"]) == 0
    cands = read_candidates(rdir / "candidates.jsonl")
    assert [c.surface for c in cands] == ["stays in scope", "oversteps the task", "truth-telling", "comfortable liar"]
    assert cands[0].partner_hint == "oversteps the task" and cands[0].source_ref == "model_spec:2026-08-18:scope_of_autonomy"
    out = capsys.readouterr().out
    assert "--run alignment_sweep/t1" in out and "gap_registry.py submit --from" in out

    # gate on the gold items (fake: always chat), so under the scoring rule of 2026-10-11 (chat and both count
    # alike) it agrees with exactly the gold items expecting chat or both
    assert CLI.main(common + ["gate", "--run-id", "t1", "--gold-only", "--allow-dirty"]) == 0
    ev = json.loads((rdir / "gate_gold_eval.json").read_text())["result"]["eval"]
    n_reach = sum(1 for g in json.loads(GATE_GOLD_PATH.read_text(encoding="utf-8"))["items"]
                  if g["expected"] in ("chat", "both"))
    assert ev["n"] == 30 and ev["n_agree"] == n_reach and ev["meets_targets"] is False
    assert (rdir / "gate_gold_eval.md").exists()

    # probe: no key -> skipped and said so
    assert CLI.main(common + ["probe", "--run-id", "t1"]) == 0
    assert json.loads((rdir / "probe.json").read_text())["result"]["status"].startswith("skipped")

    # report, with M1 and M3 blocks written into the tmp registry
    r = Registry(reg)
    for key, dec, cov in (("stays_in_scope#1", "new", None), ("oversteps_the_task#1", "new", None),
                          ("truth_telling#1", "covered", "honest"), ("comfortable_liar#1", "covered", "dishonest")):
        r.merge_block(key, "filter", {"verdict": "trait", "tags": []})
        r.merge_block(key, "novelty", {"decision": dec, "covered_by": cov, "cut_off": 4, "alignment_score": 3,
                                       "pair_completion_for": [], "readings": [],
                                       "deciding_reading": {"stem": cov or "obedient", "sonnet": {"value": 4 if cov else 1},
                                                            "opus": None}})
    assert CLI.main(common + ["report", "--run-id", "t1", "--gold"]) == 0
    md = (rdir / "readout.md").read_text()
    assert "## Survivors (2)" in md and "## Covered (2)" in md and "stays in scope (oversteps the task)" in md
    assert "Label probe: skipped" in md and f"advisory only (gold agreement {n_reach}/30" in md
    # the sections of 2026-10-11 (QUESTIONS 67, 68, 73, 74, 75, 78), each from files already in the run dir
    assert "## The gate's three fields, for promotion" in md and "(no gate rows for the survivors.)" in md
    assert "## AI-presupposing sub-families, for sign-off before promotion" in md
    assert "(none in this run's survivors.)" in md                     # no belief-state item in the fixture
    assert "0 merges in all, 0 of them on an identical surface" in md  # threshold 0.99: nothing merged
    assert "(no merge rests on the embedding: every one was an identical surface.)" in md
    assert "## Shared-virtue fan list, after dedup (0 virtues; 0 on the vice side)" in md
    assert "(no probe rows: skipped: no OPENROUTER_API_KEY loads.)" in md
    gold = (rdir / "gold_recovery.md").read_text()
    assert "Recovered **1 of 10**" in gold and "novelty_score.py score --batch-id t1_alignment_sweep_gold" in gold
    hidden = json.loads((rdir / "gold_hidden.json").read_text())
    assert "honest" in hidden["hidden"] and "dishonest" in hidden["hidden"]


# CHANGED EXPECTATION (2026-10-13): this fixture was the tab-separated table that fetch_transient returned, with the
# header first, fed past fetch_transient by a monkeypatch; the live sheet then gave 0 chunks unseen (its pubhtml page
# holds no table).  It is now the sheet's TSV export as fetched (CRLF, a banner line above the header, a section
# divider), served by the fake network to the real fetch_transient.
KRAKOVNA_SHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-abc/pubhtml"
KRAKOVNA_EXPORT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-abc/pub?output=tsv"
KRAKOVNA_TSV = ("\tSubmit more examples through this form\t\r\n"
                "Title\tIntended goal\tBehaviour\r\n"
                "\tEvolutionary and genetic algorithms\t\r\n"
                "Boat race\tfinish the race\tcircles to collect points\r\n"
                "Tetris\tsurvive\tpauses the game forever\r\n"
                "Coding\tpass the tests\tedits the tests zzsheetonlyword\r\n")
LONG_QUOTE = " ".join(f"w{i}" for i in range(40))


def kra_responder(kw):
    if "Source: Krakovna" in user_text(kw):
        return extraction_reply([item(pole("plays fair", "This means meeting a goal the way it was meant."),
                                      pole("games the metric", "This means meeting the letter of a goal only."),
                                      source_pole="vice", quote=LONG_QUOTE)])
    return extraction_reply([])


def test_variant_b_extracts_the_transient_krakovna_chunks(env, monkeypatch):
    """Variant B reads the Krakovna sheet transiently (never stored, quotes of 25 words or fewer).  Its chunks are in
    no chunks.jsonl, and before the review of 2026-10-12 the item ids' ordinals were counted over chunks.jsonl alone,
    so assembling them raised KeyError after the paid calls."""
    root, common, cdir = env
    kra = SOURCES["krakovna"]
    kra_pages = {kra.url: f'<p><a href="{KRAKOVNA_SHEET}">the master list</a></p>'.encode(),
                 KRAKOVNA_EXPORT_URL: KRAKOVNA_TSV.encode()}
    network = F._urlopen_bytes                                              # the env's fake network
    monkeypatch.setattr(F, "_urlopen_bytes", lambda url: kra_pages[url] if url in kra_pages else network(url))
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(kra_responder))
    assert CLI.main(common + ["fetch"]) == 0 and CLI.main(common + ["chunk"]) == 0
    assert CLI.main(common + ["extract", "--run-id", "tb", "--variant", "B", "--sources", "krakovna",
                              "--allow-dirty"]) == 0
    rdir = cdir / "runs" / "alignment_sweep" / "tb"
    ext = [json.loads(x) for x in (rdir / "extraction.jsonl").read_text().splitlines()]
    assert [e["item_id"] for e in ext] == ["kra001-1a", "kra001-1b"] and {e["source"] for e in ext} == {"krakovna"}
    assert ext[0]["label"] == "games the metric" and ext[0]["source_quote"].endswith(" [...]")
    assert len(ext[0]["source_quote"].split()) == 25 + 1                     # 25 words and the cut marker
    assert ext[0]["chunk_id"].endswith(":rows-0001-0004")                    # divider + 3 rows; not the banner
    recs = [json.loads(x) for x in (rdir / "extract_responses.jsonl").read_text().splitlines()]
    assert recs and all(r["user"] is None and r["text"] is None for r in recs)  # a read-only source's text is not kept
    # the run records what was read: the TSV export, not the pubhtml page, with its sha256
    (src,) = json.loads((rdir / "run.json").read_text())["args"]["transient_sources"]
    assert src["key"] == "krakovna" and src["url"] == KRAKOVNA_EXPORT_URL and src["sheet_url"] == KRAKOVNA_SHEET
    assert src["file"] is None and src["stored"] is False and src["size_bytes"] == len(KRAKOVNA_TSV.encode())
    # never stored: no file anywhere under the test root holds the sheet's text
    assert not [p for p in root.rglob("*") if p.is_file() and b"zzsheetonlyword" in p.read_bytes()]


def test_extract_stops_at_its_cap_and_says_so(env, monkeypatch, capsys):
    root, common, cdir = env
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(
        lambda kw: make_response(responder(kw), output_tokens=1_000_000)))          # $10 a call at Sonnet 5.5's rates
    assert CLI.main(common + ["fetch"]) == 0 and CLI.main(common + ["chunk"]) == 0
    capsys.readouterr()
    assert CLI.main(common + ["extract", "--run-id", "tc", "--allow-dirty", "--concurrency", "1"]) == 1
    assert "STOPPED at the cap" in capsys.readouterr().err
    summ = json.loads((cdir / "runs" / "alignment_sweep" / "tc" / "extract_summary.json").read_text())
    assert summ["stopped_by_budget"] is True and summ["n_calls"]["extract"] == 1


def _submitted_run(common, cdir, run_id, monkeypatch):
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(responder))
    assert CLI.main(common + ["fetch"]) == 0 and CLI.main(common + ["chunk"]) == 0
    assert CLI.main(common + ["extract", "--run-id", run_id, "--allow-dirty"]) == 0
    assert CLI.main(common + ["dedupe", "--run-id", run_id, "--embedder", "hash", "--threshold", "0.99"]) == 0
    assert CLI.main(common + ["submit", "--run-id", run_id]) == 0
    r = Registry(cdir / "registry.jsonl")
    for key in ("stays_in_scope#1", "oversteps_the_task#1"):
        r.merge_block(key, "filter", {"verdict": "trait", "tags": []})
        r.merge_block(key, "novelty", {"decision": "new", "cut_off": 4, "alignment_score": 3,
                                       "pair_completion_for": [], "readings": []})
    return cdir / "runs" / "alignment_sweep" / run_id


def test_gate_stopped_by_its_cap_leaves_the_recorded_outputs_alone(env, monkeypatch, capsys):
    """A pass the cap stops part-way is not written over a complete one: before the review of 2026-10-12 the gold
    eval was rewritten with the unasked items as misses and enactability.jsonl was emptied."""
    root, common, cdir = env
    rdir = _submitted_run(common, cdir, "tg", monkeypatch)
    assert CLI.main(common + ["gate", "--run-id", "tg", "--allow-dirty"]) == 0
    rows = (rdir / "enactability.jsonl").read_text()
    assert len(rows.splitlines()) == 2
    before = {n: (rdir / n).read_bytes() for n in ("gate_gold_eval.json", "gate_gold_eval.md", "enactability.jsonl")}
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(
        lambda kw: make_response(responder(kw), output_tokens=1_000_000)))          # $20 a call at Opus 5.5's rates
    capsys.readouterr()
    assert CLI.main(common + ["gate", "--run-id", "tg", "--allow-dirty", "--concurrency", "1"]) == 1
    err = capsys.readouterr().err
    assert "STOPPED at the cap" in err and "left as before" in err
    assert {n: (rdir / n).read_bytes() for n in before} == before


def test_readout_calls_the_gate_advisory_whatever_its_score(env, monkeypatch):
    """QUESTIONS 75: nothing gates on the gate, so the readout never calls it binding; and the agreement is over the
    answered items (a refused item is out of the denominator)."""
    root, common, cdir = env
    rdir = _submitted_run(common, cdir, "tr", monkeypatch)
    ev = {"n": 30, "n_answered": 29, "n_refused": 1, "n_agree": 27, "meets_targets": True, "flip_rate": 0.1}
    (rdir / "gate_gold_eval.json").write_text(json.dumps({"result": {"eval": ev}}))
    assert CLI.main(common + ["report", "--run-id", "tr"]) == 0
    md = (rdir / "readout.md").read_text()
    assert "Enactability gate: advisory only (gold agreement 27/29 answered, 1 refused, meets the 26/30 target" in md
    assert "binding" not in md


def test_submit_refused_over_budget(env, monkeypatch):
    root, common, cdir = env
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(responder))
    assert CLI.main(common + ["fetch"]) == 0 and CLI.main(common + ["chunk"]) == 0
    assert CLI.main(common + ["extract", "--run-id", "t2", "--allow-dirty"]) == 0
    assert CLI.main(common + ["dedupe", "--run-id", "t2", "--embedder", "hash", "--threshold", "0.99"]) == 0
    with pytest.raises(SystemExit) as ei:
        CLI.main(common + ["submit", "--run-id", "t2", "--budget-usd", "0.001"])
    assert ei.value.code == 2 and not (cdir / "registry.jsonl").exists()


def test_extract_refuses_an_estimate_over_the_cap(env, monkeypatch):
    root, common, cdir = env
    assert CLI.main(common + ["fetch"]) == 0 and CLI.main(common + ["chunk"]) == 0
    with pytest.raises(SystemExit) as ei:
        CLI.main(common + ["extract", "--run-id", "t3", "--budget-usd", "0.0001"])
    assert ei.value.code == 2 and not (cdir / "runs").exists()


def test_render_prints_the_calls_as_sent(env, capsys):
    root, common, cdir = env
    assert CLI.main(common + ["fetch"]) == 0 and CLI.main(common + ["chunk"]) == 0
    capsys.readouterr()
    assert CLI.main(common + ["extract", "--render", "model_spec:2026-08-18:do_not_lie"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("SYSTEM (rubric alignment_extract version 3")
    assert "USER (model_spec:2026-08-18:do_not_lie):\nSource: OpenAI Model Spec (version 2026-08-18)" in out


def test_measure_prints_the_numbers_the_table_and_a_sample(env, monkeypatch, capsys):
    """``measure`` is the prompt iteration's read-out: one column per run, no API call (plan 08 § 10)."""
    root, common, cdir = env
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(responder))
    assert CLI.main(common + ["fetch"]) == 0 and CLI.main(common + ["chunk"]) == 0
    assert CLI.main(common + ["extract", "--run-id", "t4", "--allow-dirty"]) == 0
    capsys.readouterr()
    assert CLI.main(common + ["measure", "--run-id", "t4", "t4", "--sample", "2"]) == 0
    out = capsys.readouterr().out
    assert "| measure | t4 | t4 |" in out                                  # one column per run, in order
    assert "| rubric version | 3 | 3 |" in out
    assert "| pairs per chunk (a) | 0.22 | 0.22 |" in out                  # 2 pairs over the fixture's 9 chunks
    assert "| parse rate (f) | 100% | 100% |" in out
    assert "--- 2 kept pairs of t4, seed 0 ---" in out
    assert "`stays in scope` / `oversteps the task`" in out
    assert "- virtue: This means doing only what the task asked for." in out


def test_measure_without_an_extraction_says_so(env):
    root, common, cdir = env
    with pytest.raises(SystemExit) as ei:
        CLI.main(common + ["measure", "--run-id", "nope"])
    assert "extract --run-id nope" in str(ei.value)
