#!/usr/bin/env python3
"""The LLM-entropy generator (workstream 6, generator id ``llm_entropy``).

    uv run python data_analysis/gap_generation/llm_entropy_generator.py seeds --real N --fictional M [--dead-only]
        [--seed 0] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py prompts [--family F] [--n 3]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py translate-prompts --budget-usd 1 [--force]
        [--languages de ja ...] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py generate --run-id R --family a|b|c|e
        [--share 0.2 | --n-prompts N] [--seed 0] [--runs 3] [--model M] [--with-probabilities]
        [--real 400 --fictional 200 [--dead-only]] [--tmp-seeds] [--force] [--reuse-run R0 ...]
        [--transport batches|live] [--budget-usd C] [--resume] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py generate --run-id R --family b --cancel-open
    uv run python data_analysis/gap_generation/llm_entropy_generator.py generate --run-id R --family b
        --collect-open FILE
    uv run python data_analysis/gap_generation/llm_entropy_generator.py backtranslate --run-id R --budget-usd C
        [--transport] [--resume] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py verbalized --run-id R --family a|e
        [--model M] --budget-usd C [--transport] [--resume] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py postprocess [--run-id R ...]
        [--embedder none|hash|openai] [--budget-usd 0.5] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py collapse [--run-id R ...]
        [--embedder openai|hash|none] [--tau 0.9] [--seed 0] [--budget-usd 0.5] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py model-test --run-id R [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py submit --run-id R
        (--top N [--per-cell 50] | --kept-target 300 [--kept-share X] | --all) [--transport live|batches]
        [--budget-usd 10] [--confirm-expensive --confirmed-by WHO] [--record-only] [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py roles-report --run-id R [--dry-run]
    uv run python data_analysis/gap_generation/llm_entropy_generator.py report --run-id R [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_06_llm_entropy.md``.  Five prompt families on Haiku 5.5 (the
model-test arms on Sonnet 5.5): (a) a domain x mode grid, (b) a random Wikidata person per call, (c) ten languages
(``translate-prompts`` makes the ten system turns once; ``backtranslate`` gives each answer English labels), (d)
verbalized sampling (``generate --with-probabilities`` on a or e, then ``verbalized``), (e) spelling constraints.
``postprocess`` builds the items table, ``collapse`` the mode-collapse statistics, ``model-test`` the per-(family,
model) table, ``submit`` the run's rows (the pilot's ``--top 500 --per-cell 50``, the review-hour wave
``--kept-target 300``), ``roles-report`` and ``report`` the readouts.

**Money.**  Every paid command prints its estimate (``n_calls x (in, out) tokens at model rates = $X``), takes
``--budget-usd`` as a hard cap (over it refused; over the $20 line needs ``--confirm-expensive --confirmed-by``),
checks the generator's running total against the plan's $55 stop line (section 12), charges every answer to a guarded
usage, writes ``usage.json`` in a ``finally`` block, and refuses uncommitted platform code without ``--allow-dirty``.
Generation defaults to the Message Batches API (``--transport batches``, half price); the two translation commands go
live.  ``--dry-run`` prints the estimate, the counts and one rendered prompt per variant, and writes and calls
nothing.

**Family (b) keeps its persons in memory** (section 5a): ``generate --family b`` fetches its seeds from Wikidata,
asks, waits for the batch, collects, redacts and only then writes; the seeds die with the process.  Tracked files
carry opaque seed ids (``b:r0137``).  ``--resume`` does not apply to (b); a crash before collection loses the seeds
and ``--cancel-open`` cancels the open batch (recording only its usage).  ``--tmp-seeds`` (off by default) is the
section 5a fallback: the seeds also go to a file under ``$TMPDIR`` (mode 0600), deleted when the process ends, which
survives only a hard kill and is then read by ``--collect-open FILE`` (it collects the open batch, redacts, writes and
deletes the file).  Run (b) in the background: a batch can take up to an hour.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import llm_entropy as LE  # noqa: E402

#: Plan section 12: a paid step whose estimate would push the generator's running total past this stops and asks.
STOP_LINE_USD = 55.0
EXIT_REFUSED = 2


# --------------------------------------------------------------------------- factories (tests replace these)

def _anthropic_client():
    """The live client (Anthropic, direct key; ``.env`` is loaded by ``dotenv`` and never read here)."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def _batch_client():
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.Anthropic()


def _wikidata(args):
    from assistant_axis.gapgen.generators.llm_entropy.seeds import Throttle
    return Throttle(user_agent=args.user_agent)


def _embedder(name: str, *, usage=None, cache_dir: Optional[Path] = None):
    """``(embed texts -> unit rows, embedder, cache)`` for ``openai`` (through the cache) or ``hash`` (no cache);
    ``(None, None, None)`` for ``none``."""
    if name == "none":
        return None, None, None
    from assistant_axis.gapgen.embed import EmbeddingCache, embed_texts, make_embedder
    emb = make_embedder(name)
    cache = None if name == "hash" else (EmbeddingCache(cache_dir) if cache_dir else EmbeddingCache())

    def embed(texts):
        return embed_texts(emb, texts, cache=cache, usage=usage)
    return embed, emb, cache


#: Characters per token for the embedding estimate (short labels and glosses).
EMBED_CHARS_PER_TOKEN = 4.0


def _embedding_estimate(emb, cache, texts) -> float:
    """Print and return the cost of embedding ``texts``: only the texts the cache does not hold are sent (minor 15 of
    the review, 2026-10-17: the estimate is printed before anything is embedded)."""
    from assistant_axis.judge_pricing import cost_for_usage
    uniq = list(dict.fromkeys(t for t in texts if t))
    if emb is None or not uniq:
        return 0.0
    miss = list(range(len(uniq))) if cache is None else cache.lookup(emb.tag, uniq)[1]
    tokens = int(sum(len(uniq[i]) for i in miss) / EMBED_CHARS_PER_TOKEN)
    usd = cost_for_usage(emb.usage_model, tokens, 0) if emb.name != "hash" else 0.0
    print(f"  embeddings: {len(uniq)} distinct texts, {len(miss)} not in the cache, ~{tokens:,} tokens at "
          f"{emb.usage_model} rates = ${usd:.4f}" + ("  (local, free)" if emb.name == "hash" else ""))
    return usd


def _dirty(args) -> Optional[str]:
    from assistant_axis.gapgen.runs import dirty_refusal, platform_dirty_files
    refusal, _ = dirty_refusal(platform_dirty_files(), bool(getattr(args, "allow_dirty", False)))
    return refusal


# --------------------------------------------------------------------------- shared

def _refuse(msg: str) -> int:
    print(f"REFUSED: {msg}", file=sys.stderr)
    return EXIT_REFUSED


def _cdir(args) -> Path:
    return Path(args.candidates_dir)


def _edir(args) -> Path:
    return Path(args.entropy_dir) if args.entropy_dir else _cdir(args) / "llm_entropy"


def _run_dir(args, run_id: str) -> Path:
    paths.check_id(run_id, "run_id")
    return paths.run_dir(LE.GENERATOR, run_id, candidates_dir=_cdir(args))


def _all_run_ids(args) -> list[str]:
    root = _cdir(args) / "runs" / LE.GENERATOR
    return sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []


def _records(args, run_ids) -> list[dict]:
    from assistant_axis.gapgen.generators.llm_entropy.calls import read_responses
    out = []
    for r in run_ids:
        out += read_responses(_run_dir(args, r) / LE.RESPONSES_NAME)
    return out


def _registry_rows(args) -> dict:
    """The registry folded, read without its lock (these commands only read it, and a dry run writes nothing)."""
    from assistant_axis.gapgen.registry import read_snapshot
    p = Path(args.registry)
    return read_snapshot(p) if p.exists() else {}


def _queue(args) -> Path:
    return Path(args.data_dir) / "seed_queue.json"


def _usage_total(path: Path) -> float:
    p = Path(path)
    return float(json.loads(p.read_text(encoding="utf-8")).get("total_cost_usd") or 0.0) if p.exists() else 0.0


def running_total(args) -> float:
    """The plan's running total (section 12): every ``usage.json`` of the generator's runs, their M1 and M3
    batches, the translations and the embeddings."""
    total = 0.0
    for r in _all_run_ids(args):
        total += _usage_total(_run_dir(args, r) / "usage.json")
        total += _usage_total(_cdir(args) / "filter" / f"{r}_{LE.GENERATOR}" / "usage.json")
        total += _usage_total(_cdir(args) / "novelty" / f"{r}_{LE.GENERATOR}" / "usage.json")
    total += _usage_total(_edir(args) / "multilingual_prompts_usage.json")
    total += _usage_total(_edir(args) / "embeddings_usage.json")
    return round(total, 4)


def _gate(args, estimate_usd: float) -> Optional[int]:
    """The cost gate: the typed budget (``confirm_or_abort``) and the section 12 stop line.  Returns an exit code to
    stop with, or None.  A generating command run without ``--budget-usd`` takes the first-of-kind cap,
    ``ceil(1.5 x estimate + 2)`` (plan section 7)."""
    import math

    from assistant_axis.gapgen.cost import CostRefused, confirm_or_abort
    if args.budget_usd is None:
        args.budget_usd = float(math.ceil(1.5 * estimate_usd + 2.0))
        print(f"cap --budget-usd ${args.budget_usd:.0f} (the first-of-kind default, ceil(1.5 x estimate + 2))")
    try:
        confirm_or_abort(estimate_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                         confirmed_by=args.confirmed_by)
    except CostRefused:
        return EXIT_REFUSED
    return _stop_line(args, estimate_usd)


def _stop_line(args, estimate_usd: float) -> Optional[int]:
    """Plan section 12's stop: a step whose estimate would push the generator's running total past
    :data:`STOP_LINE_USD` is refused without ``--confirm-expensive --confirmed-by``."""
    total = running_total(args)
    print(f"running total of the generator so far ${total:.4f}; this step's estimate ${estimate_usd:.4f}; the "
          f"plan's stop line ${STOP_LINE_USD:.0f}")
    if total + estimate_usd > STOP_LINE_USD and not (getattr(args, "confirm_expensive", False)
                                                      and getattr(args, "confirmed_by", None)):
        return _refuse(f"the running total ${total:.2f} plus this estimate would pass the plan's ${STOP_LINE_USD:.0f} "
                       f"stop line (section 12): ask Roger, then --confirm-expensive --confirmed-by '<his go>'")
    return None


def _embedding_gate(args, est: float) -> Optional[int]:
    """The embedding commands' gate: the typed ``--budget-usd`` and the stop line (should-fix 4 of the review)."""
    from assistant_axis.gapgen.cost import CostRefused, confirm_or_abort
    if est <= 0:
        return None
    try:
        confirm_or_abort(est, args.budget_usd, confirm_expensive=args.confirm_expensive,
                         confirmed_by=args.confirmed_by)
    except CostRefused:
        return EXIT_REFUSED
    return _stop_line(args, est)


def _transport(args, runner, run_dir: Path):
    from assistant_axis.gapgen.batches import BatchTransport
    from assistant_axis.gapgen.generators.llm_entropy.calls import LiveTransport
    if args.transport == "live":
        runner.client = _anthropic_client()
        return LiveTransport(runner)
    return BatchTransport(runner, _batch_client(), run_dir / LE.BATCHES_NAME, budget_usd=args.budget_usd)


def _reuse_records(args, run_id: str) -> list[dict]:
    recs = _records(args, [run_id])
    for r0 in getattr(args, "reuse_run", None) or []:
        recs += _records(args, [r0])
    return recs


def _overlap_refusal(args, calls, records) -> Optional[str]:
    """Without ``--resume``, a call whose answer the run already holds is refused (never paid twice by accident)."""
    from assistant_axis.gapgen.generators.llm_entropy.calls import final_records
    done = set(final_records(records))
    hit = sum(1 for c in calls if c.cache_key in done)
    if hit and not args.resume and not getattr(args, "reuse_run", None):
        return (f"the run already holds answers to {hit} of these {len(calls)} calls; pass --resume to reuse them "
                f"(nothing answered is sent again)")
    return None


def _print_estimate(calls, *, batch: bool) -> float:
    from assistant_axis.gapgen.generators.llm_entropy.calls import estimate_lines, estimate_usd
    for line in estimate_lines(calls, batch=batch):
        print(f"  {line}")
    est = estimate_usd(calls, batch=batch)
    print(f"  total estimate = ${est:.4f}" + ("  (Message Batches, half price)" if batch else "  (live)"))
    return est


def _session(args, run_id: str, calls, *, wave: str, parse, step: str, extra: dict, prepare=None, finalize=None):
    """Send ``calls`` in one recorded session of the run (start_run, the guarded usage, the transport, the
    checkpoint, ``finish`` in a finally).  ``prepare(runner)``, when given, runs inside the session before anything is
    sent and may return the calls to send instead of ``calls`` (family b builds its calls there, after the fetch);
    ``finalize()`` runs in the finally before ``finish``.  Returns ``(WaveResult or None, exit code)``."""
    from assistant_axis.gapgen.cost import resume_usage
    from assistant_axis.gapgen.generators.llm_entropy.calls import EntropyRunner, RunGuardedUsage
    from assistant_axis.gapgen.generators.llm_entropy.prompts import PROMPTS_VERSION
    from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, LABEL_FORM_KEY
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import BudgetExceededError
    rdir = _run_dir(args, run_id)
    resume = _reuse_records(args, run_id) if (args.resume or getattr(args, "reuse_run", None)) else []
    ctx = start_run(LE.GENERATOR, run_id, candidates_dir=_cdir(args), args={
        "step": step, "transport": args.transport, "budget_usd": args.budget_usd, "n_calls": len(calls),
        "prompts_version": PROMPTS_VERSION, LABEL_FORM_KEY: DEFAULT_LABEL_FORM, "allow_dirty": bool(args.allow_dirty),
        "resume": bool(args.resume), **extra})
    ctx.confirmed_by = args.confirmed_by
    earlier = ctx.total_usage()                      # the run's other sessions (this one has spent nothing yet)
    rebuilt = resume_usage(earlier, _records(args, [run_id]), where=f"{LE.GENERATOR}/{run_id}")
    if rebuilt.total_cost_usd > earlier.total_cost_usd + 1e-9:
        # a session killed before it recorded its usage: its spend, from the records, becomes a session of its own,
        # so that usage.json (the sum of the sessions) holds it (minor 8 of the review, 2026-10-17)
        from assistant_axis.gapgen.generators.llm_entropy.calls import usage_gap
        rec_ctx = start_run(LE.GENERATOR, run_id, candidates_dir=_cdir(args), args={
            "step": "recovered_usage", "note": "spend the response records show beyond the recorded sessions"})
        rec_ctx.usage = usage_gap(rebuilt, earlier)
        rec_ctx.finish()
        earlier = ctx.total_usage()
    ctx.usage = RunGuardedUsage(budget_usd=args.budget_usd, usage_path=rdir / "usage.json", earlier=earlier)
    runner = EntropyRunner(batch_id=f"{run_id}_{LE.GENERATOR}", run_id=run_id, usage=ctx.usage,
                           responses_path=rdir / LE.RESPONSES_NAME, resume_records=resume,
                           concurrency=args.concurrency, checkpoint=ctx.finish, prompts_version=PROMPTS_VERSION)
    res, code = None, 0
    try:
        runner.transport = _transport(args, runner, rdir)
        if prepare is not None:
            got = prepare(runner)
            if got is not None:
                calls = got
        res = runner.run(wave, calls, parse)
    except BudgetExceededError as exc:
        print(f"STOPPED at the cap (--budget-usd {args.budget_usd:g}): {exc}; the answers paid for are recorded",
              file=sys.stderr)
        code = 1
    finally:
        if finalize is not None:
            finalize()
        ctx.finish()
        print(ctx.usage.log_line(f"[usage this session, {LE.GENERATOR}/{run_id}]"), file=sys.stderr)
    if res is not None:
        warn_if_low_parse_rate(label=f"{LE.GENERATOR}:{step}:{wave}", n_ok=res.n_ok, n_total=res.n_attempted)
        print(f"{step} {wave}: {len(res.answers)} of {res.n_units} answered ({res.n_reused} reused, {res.n_retried} "
              f"asked once more); failed {len(res.failures)}; stop reasons {dict(res.stop_reasons)}")
    return res, code


def _rubric(args, name: str):
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    try:
        return P.load_rubric(name, args.rubrics_dir, allow_unpinned=args.dry_run)
    except P.RubricNotPinned as exc:
        raise SystemExit(f"REFUSED: {exc}")


# --------------------------------------------------------------------------- seeds, prompts

def cmd_seeds(args) -> int:
    from assistant_axis.gapgen.generators.llm_entropy import seeds as SD
    th = _wikidata(args)
    stats = SD.FetchStats()
    seeds = SD.fetch_real(args.real, session=th, dead_only=args.dead_only, stats=stats)
    seeds += SD.fetch_fictional(args.fictional, session=th, rng=random.Random(args.seed), stats=stats)
    for line in SD.summary_lines(seeds, stats, th.counts):
        print(line)
    print("nothing written: the seeds stay in this process's memory and die with it (plan section 5a)")
    return 0


def cmd_prompts(args) -> int:
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    hits = P.hygiene_hits(args.rubrics_dir)
    print(f"grid sizes: (a) {len(P.grid_prompts('a'))}, (b) {P.GRID_SIZES['b']} (400 real + 200 fictional seeds), "
          f"(c) {len(P.LANGUAGES) * len(P.DOMAINS)}, (e) {len(P.grid_prompts('e'))}; (d) wraps (a) and (e)")
    for name in P.RUBRICS:
        rub = P.load_rubric(name, args.rubrics_dir, allow_unpinned=True)
        print(f"SYSTEM {name}: version {rub['version']} ({(rub['sha256'] or 'UNPINNED')[:12]}), {len(rub['text']):,} "
              f"characters, {rub['file']}")
    for variant, pid, user in P.variant_samples():
        fam = variant.split(":")[0] if ":" in variant else "c"          # the back-translation call is family c's
        if args.family and fam != args.family:
            continue
        print(f"\n--- USER, {variant} ({pid}):\n{user}")
    if args.n:
        for fam in ([args.family] if args.family in ("a", "e") else ["a", "e"]):
            for p in random.Random(args.seed).sample(P.grid_prompts(fam), args.n):
                print(f"\n--- USER, a random {fam} prompt ({p.prompt_id}):\n{p.user}")
    if hits:
        for name, words in hits.items():
            print(f"HYGIENE {name}: {', '.join(words)}", file=sys.stderr)
        return 1
    print("\nhygiene: no prompt word is a corpus stem, a queue label or a validation-file word (beyond the recorded "
          "prose words)")
    return 0


# --------------------------------------------------------------------------- translate-prompts

def _prompts_json_path(args) -> Path:
    return _edir(args) / "multilingual_prompts.json"


def cmd_translate_prompts(args) -> int:
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.generators.llm_entropy import calls as C
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    from assistant_axis.gapgen.generators.llm_entropy.parse import parse_tagged
    from assistant_axis.judge_pricing import MultiModelUsage
    path = _prompts_json_path(args)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    langs = args.languages or [lang.code for lang in P.LANGUAGES]
    bad = [x for x in langs if x not in P.LANGUAGE_BY_CODE]
    if bad:
        return _refuse(f"unknown language code(s) {bad}; the ten are {[x.code for x in P.LANGUAGES]}")
    have = [x for x in langs if x in (existing.get("languages") or {})]
    if have and not args.force:
        return _refuse(f"{path} already holds {have}: pass --force to translate them again (the old texts are kept "
                       f"in a .bak copy)")
    master = _rubric(args, P.MULTILINGUAL_RUBRIC)
    calls = []
    for code in langs:
        system, user = P.render_translate(code, master["text"])
        calls.append(C.EntropyCall(family="c", prompt_id=f"translate:{code}", run=1, model=args.model, system=system,
                                   user=user, step="translate", language=code,
                                   meta={"rubric": master["name"], "rubric_version": master["version"],
                                         "rubric_sha256": master["sha256"]}))
    back_like = [C.EntropyCall(family="c", prompt_id=f"prompt_back:{c.language}", run=1, model=args.back_model,
                               system=P.PROMPT_BACK_SYSTEM, user=P.render_master(c.language, master["text"]),
                               step="prompt_back", language=c.language) for c in calls]
    print(f"translate the pinned master ({master['name']} v{master['version']}) into {len(calls)} language(s) on "
          f"{args.model}, then translate each back on {args.back_model} for Roger's read")
    est = _print_estimate(calls + back_like, batch=False)
    stop = _gate(args, est)
    if stop is not None:
        return stop
    if args.dry_run:
        system, user = P.render_translate(langs[0], master["text"])
        print(f"DRY-RUN: no call, nothing written.  The {P.LANGUAGE_BY_CODE[langs[0]].name} request:\n[system]\n"
              f"{system}\n[user]\n{user}")
        return 0
    refused = _dirty(args)
    if refused:
        return _refuse(refused)
    edir = _edir(args)
    usage_p = edir / "multilingual_prompts_usage.json"
    usage = GuardedUsage(budget_usd=args.budget_usd)
    rec_p = edir / "translations" / LE.RESPONSES_NAME
    forced = set(have)        # under --force these are translated again: their recorded answers are not reused
    reuse = [r for r in C.read_responses(rec_p) if r.get("language") not in forced]
    runner = C.EntropyRunner(client=_anthropic_client(), batch_id="translate_prompts", run_id="translate_prompts",
                             usage=usage, responses_path=rec_p, resume_records=reuse,
                             concurrency=args.concurrency, prompts_version=P.PROMPTS_VERSION)
    entries: dict = {}
    back_failed: list = []
    try:
        res = runner.run("translate", calls, C.parse_translation_call)
        for c in calls:
            got = res.answers.get(c.cache_key)
            if got is None:
                print(f"FAILED {c.language}: {res.failures.get(c.cache_key)}", file=sys.stderr)
                continue
            d, _ = parse_tagged(got[1]["text"])
            doms = {k: d["domains"][k] for k in P.DOMAIN_IDS}
            e = {"name": P.LANGUAGE_BY_CODE[c.language].name, "native": P.LANGUAGE_BY_CODE[c.language].native,
                 "system": d["system"], "user_template": d["user_template"], "domains": doms, "note": d.get("note"),
                 "model": c.model, "custom_id": got[1]["custom_id"], "at": got[1]["at"],
                 "system_sha256": P.sha256_text(d["system"]),
                 "sha256": P.sha256_text(json.dumps([d["system"], d["user_template"],
                                                     [doms[k] for k in P.DOMAIN_IDS]], ensure_ascii=False)),
                 "master_sha256": master["sha256"], "master_version": master["version"]}
            old = (existing.get("languages") or {}).get(c.language)
            if c.language in forced and old:
                e["retranslated"] = {"at": got[1]["at"], "previous_sha256": old.get("sha256"),
                                     "previous_custom_id": old.get("custom_id"),
                                     "previous_at": old.get("at"), "same_text": old.get("sha256") == e["sha256"]}
            entries[c.language] = e
        back = []
        for code, e in entries.items():
            system, user = P.render_prompt_back(code, e)
            back.append(C.EntropyCall(family="c", prompt_id=f"prompt_back:{code}", run=1, model=args.back_model,
                                      system=system, user=user, step="prompt_back", language=code))
        bres = runner.run("prompt_back", back, C.parse_translation_call) if back else None
        for c in back:
            got = bres.answers.get(c.cache_key) if bres else None
            if got is None:
                back_failed.append(c.language)
                print(f"FAILED {c.language}: the back-translation for Roger's read "
                      f"({(bres.failures.get(c.cache_key) if bres else None) or 'no answer'})", file=sys.stderr)
                continue
            d, _ = parse_tagged(got[1]["text"])
            entries[c.language]["backtranslation"] = {"system": d["system"], "user_template": d["user_template"],
                                                      "domains": d["domains"], "model": c.model}
    finally:
        prev = MultiModelUsage.load_or_create(usage_p)
        prev.merge_from(usage)
        usage_p.parent.mkdir(parents=True, exist_ok=True)
        prev.write_json(usage_p)
        print(usage.log_line("[usage this session, translate-prompts]"), file=sys.stderr)
    if not entries:
        return 1
    out = {"schema_version": 1, "about": "The ten family-(c) prompts of the LLM-entropy generator: translations of the "
           "pinned English master (reports/trait_gap_generation/rubrics/llm_entropy_multilingual.md) with their "
           "sha256 and the literal back-translation Roger reads.  Written by llm_entropy_generator.py "
           "translate-prompts.",
           "master": {"rubric": master["name"], "version": master["version"], "sha256": master["sha256"],
                      "user_template": P.C_USER_MASTER, "user_template_sha256": P.sha256_text(P.C_USER_MASTER),
                      "domains": [list(d) for d in P.DOMAINS], "prompts_version": P.PROMPTS_VERSION},
           "languages": {**(existing.get("languages") or {}), **entries}}
    if path.exists():
        import shutil

        from assistant_axis.gapgen.registry import utc_stamp
        shutil.copy2(path, path.with_name(f"{path.name}.bak.{utc_stamp()}"))
    from assistant_axis.atomic_io import atomic_write_text
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", path)
    print(f"wrote {path} ({len(entries)} language(s)); usage in {usage_p}")
    print("\n=== THE ENGLISH MASTER (German shown; {language} is each language's name) ===\n"
          + P.render_master("de", master["text"]) + "\n\n" + P.C_USER_MASTER)
    for code, e in entries.items():
        b = e.get("backtranslation") or {}
        print(f"\n=== {e['name']} ({code}): the translation's note: {e.get('note')} ===\n--- back-translated system "
              f"turn ---\n{b.get('system')}\n--- back-translated request ---\n{b.get('user_template')}\n--- domains "
              f"(English master -> {e['name']} -> back) ---")
        for d, phrase in P.DOMAINS:
            print(f"  {phrase} -> {e['domains'].get(d)} -> {(b.get('domains') or {}).get(d)}")
    return 0 if len(entries) == len(calls) and not back_failed else 1


# --------------------------------------------------------------------------- generate

def _family_prompts(args, rubric):
    """The family's prompts (not b), after the share or n draw."""
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    pj = None
    if args.family == "c":
        path = _prompts_json_path(args)
        if not path.exists():
            raise SystemExit(f"REFUSED: family c needs {path}: run translate-prompts first")
        pj = json.loads(path.read_text(encoding="utf-8"))
        master = P.load_rubric(P.MULTILINGUAL_RUBRIC, args.rubrics_dir, allow_unpinned=args.dry_run)
        stale = [c for c, e in (pj.get("languages") or {}).items() if e.get("master_sha256") != master["sha256"]]
        if stale and not args.dry_run:
            raise SystemExit(f"REFUSED: the translations of {stale} were made from another master than the pinned "
                             f"one: translate-prompts --force --languages {' '.join(stale)}")
        missing = [lang.code for lang in P.LANGUAGES if lang.code not in (pj.get("languages") or {})]
        if missing:
            raise SystemExit(f"REFUSED: multilingual_prompts.json has no translation for {missing}")
    ps = P.grid_prompts(args.family, prompts_json=pj, with_probabilities=args.with_probabilities)
    return P.select_prompts(ps, share=args.share, n=args.n_prompts, seed=args.seed)


def _b_counts(args) -> tuple[int, int]:
    if args.n_prompts is not None:
        tot = args.real + args.fictional
        real = int(round(args.n_prompts * args.real / tot)) if tot else 0
        return real, args.n_prompts - real
    if args.share is not None:
        return int(round(args.share * args.real)), int(round(args.share * args.fictional))
    return args.real, args.fictional


def _wave_name(family: str, model: str, *, with_probabilities: bool = False, stage: int = 1) -> str:
    from assistant_axis.gapgen.generators.llm_entropy.calls import model_tag
    return f"{family}_{model_tag(model)}_s{stage}" + ("_p" if with_probabilities else "")


def _b_calls(seeds, *, runs, model, rubric):
    from assistant_axis.gapgen.generators.llm_entropy import calls as C
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    from assistant_axis.gapgen.generators.llm_entropy import seeds as SD
    out = []
    for s in seeds:
        user = P.render_b(s.as_prompt_seed())

        def red(t, _s=s):
            return SD.redact(t, _s)

        def name_label(lab, _s=s):
            return _s.kind == "real" and (SD.name_in_label(lab, _s) or SD.description_in_label(lab, _s))

        def leak_check(blob, _s=s):
            return SD.leaks(blob, _s)
        for r in runs:
            out.append(C.EntropyCall(family="b", prompt_id=s.seed_id, run=int(r), model=model, system=rubric["text"],
                                     user=user, record_user=C.b_record_user(user, s.seed_id), redactor=red,
                                     name_label=name_label, leak_check=leak_check,
                                     labels_may_name=s.kind == "fictional",
                                     meta={"seed_kind": s.kind, "era": s.era, "rubric": rubric["name"],
                                           "rubric_version": rubric["version"], "rubric_sha256": rubric["sha256"]}))
    return out


def _write_tmp_seeds(seeds, run_id: str, session: str) -> Path:
    """The section 5a fallback: the seeds in a file under ``$TMPDIR``, mode 0600 (deleted in the caller's
    finally)."""
    import dataclasses
    p = Path(tempfile.gettempdir()) / f"llm_entropy_seeds_{run_id}_{session}.json"
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"run_id": run_id, "seeds": [dataclasses.asdict(s) for s in seeds]}, fh, ensure_ascii=False)
    return p


def _read_tmp_seeds(path: Path):
    from assistant_axis.gapgen.generators.llm_entropy.seeds import PersonSeed
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d.get("run_id"), [PersonSeed(**s) for s in d.get("seeds") or []]


def cmd_generate(args) -> int:
    from assistant_axis.gapgen.generators.llm_entropy import calls as C
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    if args.family not in P.GENERATE_FAMILIES:
        return _refuse(f"generate takes the families {P.GENERATE_FAMILIES} ((d) is --with-probabilities on a or e, "
                       f"then verbalized), not {args.family!r}")
    if args.share is not None and not 0 < args.share <= 1:
        return _refuse(f"--share must be in (0, 1], got {args.share}")
    if args.share is not None and args.n_prompts is not None:
        return _refuse("give --share or --n-prompts, not both")
    if args.with_probabilities and args.family not in ("a", "e"):
        return _refuse("--with-probabilities is (d)'s stage 1, on families a and e only")
    if args.family == "b":
        return _generate_b(args)
    if args.cancel_open or args.collect_open:
        return _refuse("--cancel-open and --collect-open are for family b")
    rubric = _rubric(args, P.SCAFFOLD_RUBRIC)
    runs = list(range(1, (args.runs or 3) + 1))
    prompts = _family_prompts(args, rubric)
    calls = C.generation_calls(prompts, runs=runs, model=args.model, system=rubric["text"], rubric=rubric)
    wave = _wave_name(args.family, args.model, with_probabilities=args.with_probabilities)
    system_txt = ("the translated (c) system turns of multilingual_prompts.json" if args.family == "c" else
                  f"{rubric['name']} v{rubric['version']}")
    print(f"family {args.family} ({P.FAMILY_NAMES[args.family]}): {len(prompts)} prompts x {len(runs)} runs = "
          f"{len(calls)} calls on {args.model}; system {system_txt}; wave {wave}")
    est = _print_estimate(calls, batch=args.transport == "batches")
    stop = _gate(args, est)
    if stop is not None:
        return stop
    if args.dry_run:
        print("DRY-RUN: no call, nothing written.  One rendered user turn per variant of the family:")
        for variant, pid, user in P.variant_samples():
            if pid.split(":")[0] == args.family or (args.with_probabilities and variant.startswith("d: stage 1")):
                print(f"--- {variant} ({pid}):\n{user}")
        if args.family == "c":
            print(f"--- c ({prompts[0].prompt_id}), system turn {len(prompts[0].meta['system']):,} characters:\n"
                  f"{prompts[0].user}")
        return 0
    refused = _dirty(args)
    if refused:
        return _refuse(refused)
    records = _reuse_records(args, args.run_id)
    why = _overlap_refusal(args, calls, records)
    if why:
        return _refuse(why)
    res, code = _session(args, args.run_id, calls, wave=wave, parse=C.parse_generation, step="generate",
                         extra={"family": args.family, "model": args.model, "share": args.share,
                                "n_prompts": args.n_prompts, "seed": args.seed, "runs": len(runs),
                                "with_probabilities": bool(args.with_probabilities),
                                "rubric": {k: rubric[k] for k in ("name", "version", "sha256", "file")},
                                "reuse_run": list(args.reuse_run or [])})
    if args.family == "c" and res is not None:
        print(f"  then: llm_entropy_generator.py backtranslate --run-id {args.run_id} --budget-usd <cap>")
    if args.with_probabilities and res is not None:
        print(f"  then: llm_entropy_generator.py verbalized --run-id {args.run_id} --family {args.family} "
              f"--budget-usd <cap>")
    return code or (0 if res is not None and not res.failures else 1)


def _generate_b(args) -> int:
    """Family (b), one process from fetch to written items (module docstring; plan section 5a)."""
    import uuid

    from assistant_axis.gapgen.generators.llm_entropy import calls as C
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    from assistant_axis.gapgen.generators.llm_entropy import seeds as SD
    edir = _edir(args)
    fetch_p = edir / "person_seeds_fetch.json"
    rdir = _run_dir(args, args.run_id)
    if args.cancel_open:
        return _cancel_open(args, rdir)
    if args.resume:
        return _refuse("--resume does not apply to family b: the seeds were held in memory and are gone (section 5a); "
                       "a crash before collection loses them: --cancel-open, then run again (it fetches new seeds)")
    rubric = _rubric(args, P.SCAFFOLD_RUBRIC)
    runs = list(range(1, (args.runs or 1) + 1))
    model = args.model
    if args.collect_open:
        run0, seeds = _read_tmp_seeds(Path(args.collect_open))
        if run0 != args.run_id:
            return _refuse(f"{args.collect_open} belongs to run {run0!r}, not {args.run_id!r}")
        n_real, n_fict = sum(1 for s in seeds if s.kind == "real"), sum(1 for s in seeds if s.kind == "fictional")
    else:
        seeds = None
        n_real, n_fict = _b_counts(args)
    sample = {**P.DRY_RUN_SEED, "seed_id": "b:r0001"}
    est_calls = [C.EntropyCall(family="b", prompt_id=f"b:x{i:04d}", run=r, model=model, system=rubric["text"],
                               user=P.render_b(sample)) for i in range(n_real + n_fict) for r in runs]
    print(f"family b (person seeding): {n_real} real + {n_fict} fictional seeds x {len(runs)} run(s) = "
          f"{len(est_calls)} calls on {model}" + (" (dead only)" if args.dead_only else "")
          + "; the seeds are fetched fresh by this process and held in memory (section 5a)")
    est = _print_estimate(est_calls, batch=args.transport == "batches")
    stop = _gate(args, est)
    if stop is not None:
        return stop
    if args.dry_run:
        print("DRY-RUN: no fetch, no call, nothing written.  The (b) user turn, for the fixed sample row of plan "
              f"section 6 (never a fetched seed):\n{P.render_b(P.DRY_RUN_SEED)}")
        return 0
    if args.collect_open:
        state = rdir / LE.BATCHES_NAME
        cids = {c.custom_id for c in _b_calls(seeds, runs=runs, model=model, rubric=rubric)}
        recorded = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {"waves": {}}
        if not any(b.get("status") == "submitted" and cids & set(b.get("custom_ids") or [])
                   for bs in (recorded.get("waves") or {}).values() for b in bs):
            Path(args.collect_open).unlink(missing_ok=True)
            return _refuse(f"no open (b) batch of run {args.run_id!r} matches the seeds in the file (it was written "
                           f"before any batch was created): nothing to collect, so nothing is submitted; the file is "
                           f"deleted (section 5a). Fetch new seeds with generate --family b --force")
    if not args.collect_open and SD.run_has_fetch(fetch_p, args.run_id) and not args.force:
        return _refuse(f"run {args.run_id!r} already fetched (b) seeds ({fetch_p}): a second (b) session fetches new "
                       f"persons and pays again; pass --force if that is meant")
    refused = _dirty(args)
    if refused:
        return _refuse(refused)
    session = uuid.uuid4().hex[:12]
    stats = SD.FetchStats()
    th = None
    tmp_path: Optional[Path] = Path(args.collect_open) if args.collect_open else None
    holder: dict = {"seeds": seeds}

    def prepare(runner):
        nonlocal tmp_path, th
        if holder["seeds"] is None:
            r0, f0 = SD.next_seed_numbers(fetch_p, args.run_id)
            th = _wikidata(args)
            got = SD.fetch_real(n_real, session=th, dead_only=args.dead_only, start=r0, stats=stats)
            got += SD.fetch_fictional(n_fict, session=th, rng=random.Random(args.seed), start=f0, stats=stats)
            holder["seeds"] = got
            print(f"fetched {sum(1 for s in got if s.kind == 'real')} real and "
                  f"{sum(1 for s in got if s.kind == 'fictional')} fictional seeds ({sum(th.counts.values())} requests)")
            if args.tmp_seeds:
                tmp_path = _write_tmp_seeds(got, args.run_id, session)
        return _b_calls(holder["seeds"], runs=runs, model=model, rubric=rubric)

    def finalize():
        try:
            if holder.get("seeds"):
                ent = SD.fetch_record_entry(holder["seeds"], run_id=args.run_id, session_id=session,
                                            requested={"real": n_real, "fictional": n_fict},
                                            dead_only=args.dead_only, requests=dict(th.counts) if th else {},
                                            stats=stats)
                if args.collect_open:
                    ent["collected_by"] = "--collect-open"
                SD.write_fetch_record(fetch_p, ent, force=True)
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()
            holder.clear()

    extra = {"family": "b", "model": model, "share": args.share, "n_prompts": args.n_prompts, "seed": args.seed,
             "runs": len(runs), "n_real": n_real, "n_fictional": n_fict, "dead_only": bool(args.dead_only),
             "seed_session": session, "tmp_seeds": bool(args.tmp_seeds), "collect_open": bool(args.collect_open),
             "rubric": {k: rubric[k] for k in ("name", "version", "sha256", "file")}}
    try:
        res, code = _session(args, args.run_id, [], wave=_wave_name("b", model), parse=C.parse_generation,
                             step="generate", extra=extra, prepare=prepare, finalize=finalize)
    except BaseException as exc:            # an interruption after submission: cancel what is open, re-raise
        n = _cancel_open(args, rdir, wait=False, quiet=True)
        print(f"INTERRUPTED ({type(exc).__name__}); nothing person-linked was written; {n} open (b) batch(es) asked "
              f"to cancel: run generate --family b --cancel-open --run-id {args.run_id} to record their usage; a "
              f"rerun then fetches new seeds and needs --force (the run has a fetch entry)", file=sys.stderr)
        raise
    if res is not None:
        recs = [r for r in _records(args, [args.run_id]) if r.get("family") == "b"]
        print(f"(b) items written: {sum(len(r.get('items') or []) for r in recs if r.get('ok'))}; real-seed labels "
              f"carrying a name dropped: {sum(int(r.get('n_dropped_name_label') or 0) for r in recs)}")
    return code or (0 if res is not None and not res.failures else 1)


def _cancel_open(args, rdir: Path, *, wait: bool = True, quiet: bool = False) -> int:
    """``--cancel-open``: cancel the open (b) batches of the run (and, with ``wait``, record their usage stubs).
    Returns the number of batches acted on (``wait=False``) or an exit code."""
    from assistant_axis.gapgen.generators.llm_entropy import calls as C
    state = rdir / LE.BATCHES_NAME
    open_ids = C.open_batches(state)
    if not wait:
        if not open_ids:
            return 0
        try:
            client = _batch_client()
            for bid in open_ids:
                client.messages.batches.cancel(bid)
        except Exception as exc:  # noqa: BLE001 - best effort while unwinding
            print(f"could not cancel the open (b) batches ({type(exc).__name__})", file=sys.stderr)
        return len(open_ids)
    if not open_ids:
        print(f"no open (b) batch recorded in {state}")
        return 0
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.runs import start_run
    ctx = start_run(LE.GENERATOR, args.run_id, candidates_dir=_cdir(args),
                    args={"step": "cancel-open", "family": "b", "batches": open_ids})
    ctx.usage = GuardedUsage(budget_usd=None)
    try:
        done = C.cancel_open_batches(state, _batch_client(), responses_path=rdir / LE.RESPONSES_NAME, usage=ctx.usage,
                                     batch_id=f"{args.run_id}_{LE.GENERATOR}", run_id=args.run_id)
    finally:
        ctx.finish()
    print(f"cancelled {len(done)} open (b) batch(es): {done}; their usage is recorded, their answers are not (the "
          f"seeds are gone)")
    return 0


# --------------------------------------------------------------------------- backtranslate, verbalized

def cmd_backtranslate(args) -> int:
    from assistant_axis.gapgen.generators.llm_entropy import calls as C
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    from assistant_axis.gapgen.generators.llm_entropy.parse import parse_reply
    rub = _rubric(args, P.BACKTRANSLATE_RUBRIC)
    recs = _records(args, [args.run_id])
    gens = [r for r in C.final_records(recs, step="generate").values() if r.get("family") == "c"]
    calls = []
    for g in sorted(gens, key=lambda r: (r["prompt_id"], r["run"], r["model"])):
        rep, _ = parse_reply(g.get("text"), multilingual=True)
        if rep is None or not rep.items:
            continue
        calls.append(C.EntropyCall(family="c", prompt_id=g["prompt_id"], run=int(g["run"]), model=args.model,
                                   system=rub["text"], user=P.render_backtranslate(g["language"], rep.items),
                                   step="backtranslate", language=g["language"], stage=int(g.get("stage") or 1),
                                   meta={"source_custom_id": g["custom_id"], "source_model": g["model"],
                                         "n_items": len(rep.items), "rubric": rub["name"],
                                         "rubric_version": rub["version"], "rubric_sha256": rub["sha256"]}))
    print(f"back-translate {len(calls)} (c) answers of run {args.run_id} on {args.model}")
    est = _print_estimate(calls, batch=args.transport == "batches")
    stop = _gate(args, est)
    if stop is not None:
        return stop
    if args.dry_run:
        print("DRY-RUN: no call, nothing written." + (f"  The first user turn:\n{calls[0].user}" if calls else ""))
        return 0
    if not calls:
        print("nothing to back-translate")
        return 0
    refused = _dirty(args)
    if refused:
        return _refuse(refused)
    why = _overlap_refusal(args, calls, recs)
    if why:
        return _refuse(why)
    res, code = _session(args, args.run_id, calls, wave=f"bt_{_wave_name('c', args.model)}",
                         parse=C.parse_backtranslation_call, step="backtranslate",
                         extra={"model": args.model, "rubric": {k: rub[k] for k in ("name", "version", "sha256")}})
    return code or (0 if res is not None and not res.failures else 1)


def cmd_verbalized(args) -> int:
    from assistant_axis.gapgen.generators.llm_entropy import calls as C
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    if args.family not in ("a", "e"):
        return _refuse("verbalized takes --family a or e (the families (d) wraps)")
    rub = _rubric(args, P.SCAFFOLD_RUBRIC)
    recs = _records(args, [args.run_id])
    s1 = [r for r in C.final_records(recs, step="generate").values() if r.get("family") == args.family
          and (r.get("meta") or {}).get("with_probabilities") and (args.model is None or r.get("model") == args.model)]
    calls = []
    for r in sorted(s1, key=lambda r: (r["prompt_id"], r["run"], r["model"])):
        calls.append(C.EntropyCall(family="d", prompt_id=f"d:{r['prompt_id']}", run=int(r["run"]), model=r["model"],
                                   system=rub["text"], user=P.render_d_stage2(r["prompt_id"], r["user"], r["text"]),
                                   stage=2, step="verbalized",
                                   meta={"base_prompt_id": r["prompt_id"], "stage1_custom_id": r["custom_id"],
                                         "rubric": rub["name"], "rubric_version": rub["version"],
                                         "rubric_sha256": rub["sha256"]}))
    print(f"(d) stage 2 for {len(calls)} stage-1 answers of family {args.family} in run {args.run_id}")
    est = _print_estimate(calls, batch=args.transport == "batches")
    stop = _gate(args, est)
    if stop is not None:
        return stop
    if args.dry_run:
        print("DRY-RUN: no call, nothing written." + (f"  The first user turn:\n{calls[0].user}" if calls else ""))
        return 0
    if not calls:
        print("no stage-1 answer with probabilities: run generate --with-probabilities first")
        return 0
    refused = _dirty(args)
    if refused:
        return _refuse(refused)
    why = _overlap_refusal(args, calls, recs)
    if why:
        return _refuse(why)
    models = sorted({c.model for c in calls})
    res, code = _session(args, args.run_id, calls, wave=f"d_{args.family}_{'_'.join(_wave_name('d', m) for m in models)}",
                         parse=C.parse_generation, step="verbalized", extra={"family": "d", "base_family": args.family})
    return code or (0 if res is not None and not res.failures else 1)


# --------------------------------------------------------------------------- postprocess, collapse, model-test

def _items(args, run_ids):
    from assistant_axis.gapgen.generators.llm_entropy.table import build_items
    records = _records(args, run_ids)
    items, counts = build_items(records)
    return records, items, counts


def _cumulative_usage(path: Path, usage) -> None:
    from assistant_axis.judge_pricing import MultiModelUsage
    prev = MultiModelUsage.load_or_create(path)
    prev.merge_from(usage)
    path.parent.mkdir(parents=True, exist_ok=True)
    prev.write_json(path)


def cmd_postprocess(args) -> int:
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.generators.llm_entropy import evaluate as EV
    from assistant_axis.gapgen.generators.llm_entropy.calls import parse_rate
    from assistant_axis.gapgen.generators.llm_entropy.table import build_table, write_table
    from assistant_axis.gapgen.generators.structural.postprocess import load_corpus, load_queue_index, registry_index
    from assistant_axis.gapgen.generators.censuses.corpus import queue_trait_stems
    runs = args.run_id or _all_run_ids(args)
    records, items, counts = _items(args, runs)
    corpus = load_corpus(Path(args.data_dir))
    usage = GuardedUsage(budget_usd=args.budget_usd)
    embed, emb, cache = _embedder(args.embedder, usage=usage, cache_dir=args.embed_cache_dir)
    glosses = [it.gloss for it in items if it.stem and it.gloss]
    stop = _embedding_gate(args, _embedding_estimate(emb, cache, glosses))
    if stop is not None:
        return stop
    if args.dry_run and args.embedder == "openai":
        embed = None
    elif embed is not None and args.embedder == "openai" and glosses:
        embed(list(dict.fromkeys(glosses)))          # one batched pass; the per-stem readings then hit the cache
    rows = build_table(items, corpus=corpus, queue=load_queue_index(_queue(args)),
                       registry=registry_index(_registry_rows(args)), embed=embed)
    status = {}
    for r in rows:
        status[r["status"]] = status.get(r["status"], 0) + 1
    print(f"runs {runs}: {len(records)} records, {len(items)} items, {len(rows)} distinct stems; status {status}; "
          f"label rule refused {sum(1 for r in rows if r.get('label_problem'))} rows; counts {counts}")
    if embed is not None:
        div = [r for r in rows if r.get("gloss_divergent")]
        print(f"gloss readings with {args.embedder}: {len(div)} of {len(rows)} stems have divergent glosses")
    ev = {"runs": runs, "counts": counts,
          "string_recovery": EV.string_recovery_per_family(items, corpus_stems=sorted(corpus.stems),
                                                           renamed=corpus.renamed,
                                                           queue_stems=sorted(queue_trait_stems(_queue(args)))),
          "label_rule_bite": EV.label_rule_bite(items), "zipf_below_3": EV.zipf_below_share(items),
          "parse_rate": {f: parse_rate([r for r in records if r.get("family") == f and (r.get("step") or "generate")
                                        in ("generate", "verbalized")])
                         for f in sorted({r.get("family") for r in records if r.get("family")})},
          "roles": EV.roles_summary(rows, registry_rows=_registry_rows(args)),
          "verbalized": EV.verbalized_readout(items, registry_rows=_registry_rows(args))}
    for f, d in ev["string_recovery"].items():
        print(f"  string recovery {f}: {d['found']} of {d['n_corpus']} ({d['recall']}); queue {d['queue_found']}")
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    table_p = _edir(args) / "items_table.jsonl"
    backup = write_table(rows, table_p)
    old = EV.read_evaluation(_edir(args) / "evaluation.json")
    EV.write_evaluation({**old, **ev}, _edir(args) / "evaluation.json")
    if usage.n_calls:
        _cumulative_usage(_edir(args) / "embeddings_usage.json", usage)
    print(f"wrote {table_p}" + (f" (previous kept as {backup.name})" if backup else " (unchanged or new)")
          + f" and {_edir(args) / 'evaluation.json'}")
    return 0


def cmd_collapse(args) -> int:
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.generators.llm_entropy import collapse as CO
    runs = args.run_id or _all_run_ids(args)
    records, items, _ = _items(args, runs)
    total = sum(_usage_total(_run_dir(args, r) / "usage.json") for r in runs)
    usage = GuardedUsage(budget_usd=args.budget_usd)
    embed, emb, cache = _embedder(args.embedder, usage=usage, cache_dir=args.embed_cache_dir)
    labels = list(dict.fromkeys(it.label for it in sorted(items, key=lambda x: x.order) if it.stem))
    stop = _embedding_gate(args, _embedding_estimate(emb, cache, labels))
    if stop is not None:
        return stop
    if args.dry_run and args.embedder == "openai":
        embed = None
    from assistant_axis.gapgen.generators.llm_entropy.table import load_items_table
    table = load_items_table(_edir(args) / "items_table.jsonl")
    nn = {r["stem"] for r in table if r.get("net_new")} if table else None
    payload = CO.collapse_payload(items, records, usage_total_usd=total or None, embed=embed, embedder=args.embedder,
                                  tau=args.tau, seed=args.seed, runs=runs, net_new_stems=nn)
    per = payload["per_family"]
    print("| family | calls | items | unique | semantic | Jaccard median | p90 | L-P N | Chapman | seen/N | end slope | "
          "unique/$ |")
    for f, d in per.items():
        lp = d["lincoln_petersen"]
        print(f"| {f} | {d['n_calls']} | {d['n_items']} | {d['n_unique_string']} | {d['n_unique_semantic']} | "
              f"{d['jaccard_median']} | {d['jaccard_p90']} | {lp['N']} | {lp['chapman']} | {d['seen_over_N']} | "
              f"{d['end_slope_per_call']} | {d['unique_per_usd']} |")
    flagged = [f for f, d in per.items() if (d["jaccard_median"] or 0) > 0.6]
    if flagged:
        print(f"GATE 1: median Jaccard above 0.6 for {flagged}: one bounded prompt revision each (plan section 10)")
    sem = {f: (d["semantic"] or {}).get("unique_per_usd") for f, d in per.items()}
    best = max((v for v in sem.values() if v), default=None)
    low = [f for f, v in sem.items() if best and v is not None and v < best / 10]
    if low:
        print(f"flag for Roger: semantic-unique yield per dollar under a tenth of the best family's: {low}")
    slow = {f: d["net_new_end_slope_per_call"] for f, d in per.items()
            if d.get("net_new_end_slope_per_call") is not None and d["net_new_end_slope_per_call"] < 1}
    if slow:
        print(f"STOP RULE (task 8): net-new stems per call over the last fifth of the calls under 1 for {slow}: after "
              f"two runs of a family's prompts, no third run")
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    from assistant_axis.provenance import current_file_input
    inputs = [current_file_input(dep_key=f"responses_{r}", path=_run_dir(args, r) / LE.RESPONSES_NAME)
              for r in runs if (_run_dir(args, r) / LE.RESPONSES_NAME).exists()]
    CO.write_collapse(payload, _edir(args) / "collapse.json", inputs=inputs)
    if usage.n_calls:
        _cumulative_usage(_edir(args) / "embeddings_usage.json", usage)
    print(f"wrote {_edir(args) / 'collapse.json'}")
    return 0


def _submit_counted(args, run_id: str) -> list[str]:
    from assistant_axis.gapgen.generators.structural.report import submit_args
    p = _run_dir(args, run_id) / "run.json"
    return list(submit_args(json.loads(p.read_text(encoding="utf-8"))).get("counted_stems") or []) if p.exists() else []


def cmd_model_test(args) -> int:
    from assistant_axis.gapgen.generators.llm_entropy import collapse as CO
    from assistant_axis.gapgen.generators.llm_entropy import evaluate as EV
    records, items, _ = _items(args, [args.run_id])
    costs = CO.family_costs(records, _usage_total(_run_dir(args, args.run_id) / "usage.json") or None)
    cells = EV.model_test(items, registry_rows=_registry_rows(args), run_id=args.run_id, records=records,
                          costs=costs["by_family_model"], counted_stems=_submit_counted(args, args.run_id))
    print("| cell | unique | unique/$ | M1 trait share | net-new submitted | kept | net-new kept share | kept/$ | label "
          "rule | parse |")
    for k, c in cells.items():
        print(f"| {k} | {c['n_unique_string']} | {c['unique_per_usd_string']} | {c['m1_trait_share']} | "
              f"{c['n_submitted_net_new']} | {c['n_kept_net_new']} | {c['net_new_kept_share']} | "
              f"{c['net_new_kept_per_usd']} | {c['label_rule_bite']} | {c['parse_rate']} |")
    rule = EV.c_model_rule(cells)
    print(f"the rest of (c) by the section 10 rule: {rule['favoured'] or 'not decidable yet'} {rule['note'] or ''}")
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    old = EV.read_evaluation(_edir(args) / "evaluation.json")
    mt = dict(old.get("model_test") or {})
    mt[args.run_id] = {"cells": cells, "c_model_rule": rule}
    EV.write_evaluation({**old, "model_test": mt}, _edir(args) / "evaluation.json")
    print(f"wrote the model test into {_edir(args) / 'evaluation.json'}")
    return 0


# --------------------------------------------------------------------------- submit, roles-report, report

def _submit_stop(args, est: float) -> None:
    """Submit's stop line on its downstream estimate (should-fix 4 of the review): raised as the cost gate's refusal."""
    from assistant_axis.gapgen.cost import CostRefused
    if _stop_line(args, est) is not None:
        raise CostRefused(f"the plan's ${STOP_LINE_USD:.0f} stop line (section 12)")


def cmd_submit(args) -> int:
    import hashlib

    from assistant_axis.gapgen.cost import CostRefused
    from assistant_axis.gapgen.generators.llm_entropy import submit as SU
    from assistant_axis.gapgen.generators.llm_entropy.table import load_items_table
    table_p = _edir(args) / "items_table.jsonl"
    table = SU.rows_of_run(load_items_table(table_p), args.run_id)
    if not table:
        return _refuse(f"no row of {table_p} comes from run {args.run_id!r}: run postprocess first")
    modes = sum(x is not None for x in (args.top, args.kept_target)) + bool(args.all)
    if modes != 1:
        return _refuse("give exactly one of --top N, --kept-target K and --all")
    if not args.dry_run:
        refused = _dirty(args)
        if refused:
            return _refuse(refused)
    try:
        SU.run_submit(args.run_id, table=table, registry_rows=_registry_rows(args), top_n=args.top,
                      per_cell=args.per_cell if args.top is not None else None, kept_target=args.kept_target,
                      kept_share=args.kept_share, all_rows=args.all, budget_usd=args.budget_usd,
                      confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by,
                      transport=args.transport, dry_run=args.dry_run, registry_path=Path(args.registry),
                      candidates_dir=_cdir(args), table_path=table_p,
                      table_sha256=hashlib.sha256(table_p.read_bytes()).hexdigest(),
                      relabel=None if args.no_relabel else "auto", record_only=args.record_only,
                      pre_gate=lambda est: _submit_stop(args, est))
    except CostRefused:
        return EXIT_REFUSED
    except ValueError as exc:
        return _refuse(str(exc))
    return 0


def cmd_roles_report(args) -> int:
    from assistant_axis.gapgen.generators.llm_entropy import report as RP
    from assistant_axis.gapgen.generators.llm_entropy.submit import rows_of_run
    from assistant_axis.gapgen.generators.llm_entropy.table import load_items_table
    table = rows_of_run(load_items_table(_edir(args) / "items_table.jsonl"), args.run_id)
    rdir = Path(args.data_dir) / "roles" / "instructions"
    role_stems = sorted(p.stem for p in rdir.glob("*.json")) if rdir.exists() else []
    md = RP.roles_report(table, registry_rows=_registry_rows(args), role_stems=role_stems,
                         role_queue=RP.role_queue_index(_queue(args)), run_id=args.run_id)
    print(md)
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    out = _edir(args) / "roles_report.md"
    from assistant_axis.atomic_io import atomic_write_text
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(md, out)
    print(f"wrote {out}")
    return 0


def cmd_report(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.llm_entropy import collapse as CO
    from assistant_axis.gapgen.generators.llm_entropy import report as RP
    from assistant_axis.gapgen.generators.llm_entropy.evaluate import run_rows
    from assistant_axis.gapgen.generators.llm_entropy.submit import rows_of_run
    from assistant_axis.gapgen.generators.llm_entropy.table import load_items_table
    rdir = _run_dir(args, args.run_id)
    records, items, _ = _items(args, [args.run_id])
    table = rows_of_run(load_items_table(_edir(args) / "items_table.jsonl"), args.run_id)
    reg = _registry_rows(args)
    coll = CO.load_collapse(_edir(args) / "collapse.json")
    own = coll if (coll.get("runs") or []) == [args.run_id] else None        # a collapse.json of this run alone
    fig = RP.figures(args.run_id, run_dir=rdir, registry_rows=reg, table=table, items=items, records=records,
                     collapse=own,
                     filter_dir=_cdir(args) / "filter" / f"{args.run_id}_{LE.GENERATOR}",
                     novelty_dir=_cdir(args) / "novelty" / f"{args.run_id}_{LE.GENERATOR}",
                     extra_usage=[_edir(args) / "multilingual_prompts_usage.json",
                                  _edir(args) / "embeddings_usage.json"])
    rows = run_rows(reg, args.run_id)
    files = {"report.md": RP.render_report(fig),
             "roger_sample.md": RP.roger_sample(rows, table, run_id=args.run_id, seed=args.seed),
             "gloss_check.md": RP.gloss_check_sample(table, run_id=args.run_id, seed=args.seed)}
    print(files["report.md"])
    if args.dry_run:
        print(f"DRY-RUN: would write {', '.join(files)} in {rdir}")
        return 0
    rdir.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        atomic_write_text(body, rdir / name)
    atomic_write_text(json.dumps(fig, indent=2, ensure_ascii=False, default=str) + "\n", rdir / "report_figures.json")
    print(f"wrote {', '.join(files)} and report_figures.json in {rdir}")
    return 0


# --------------------------------------------------------------------------- the parser

def build_parser() -> argparse.ArgumentParser:
    from assistant_axis.gapgen.generators.llm_entropy.calls import CONCURRENCY, HAIKU, SONNET
    from assistant_axis.gapgen.generators.llm_entropy.seeds import USER_AGENT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=paths.DATA_CANDIDATES)
    ap.add_argument("--entropy-dir", type=Path, default=None, help="default: <candidates-dir>/llm_entropy")
    ap.add_argument("--rubrics-dir", type=Path, default=None)
    ap.add_argument("--embed-cache-dir", type=Path, default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, *, paid=False, budget=1.0, transport="batches"):
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--seed", type=int, default=0)
        if paid:
            p.add_argument("--budget-usd", type=float, default=budget)
            p.add_argument("--confirm-expensive", action="store_true")
            p.add_argument("--confirmed-by", default=None)
            p.add_argument("--transport", choices=("batches", "live"), default=transport)
            p.add_argument("--resume", action="store_true")
            p.add_argument("--allow-dirty", action="store_true")
            p.add_argument("--concurrency", type=int, default=CONCURRENCY)
        return p

    p = common(sub.add_parser("seeds", help="the Wikidata fetch alone, $0; prints counts, writes nothing"))
    p.add_argument("--real", type=int, default=10)
    p.add_argument("--fictional", type=int, default=0)
    p.add_argument("--dead-only", action="store_true")
    p.add_argument("--user-agent", default=USER_AGENT)
    p = common(sub.add_parser("prompts", help="hygiene, grid sizes and rendered samples, $0"))
    p.add_argument("--family", choices=("a", "b", "c", "d", "e"), default=None)
    p.add_argument("--n", type=int, default=0)
    p = common(sub.add_parser("translate-prompts", help="the ten (c) prompts, live, about $0.5"), paid=True,
               budget=1.0, transport="live")
    p.add_argument("--languages", nargs="+", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--model", default=SONNET)
    p.add_argument("--back-model", default=HAIKU)
    p = common(sub.add_parser("generate", help="one family's calls"), paid=True, budget=None)
    p.add_argument("--run-id", required=True)
    p.add_argument("--family", required=True)
    p.add_argument("--share", type=float, default=None)
    p.add_argument("--n-prompts", type=int, default=None)
    p.add_argument("--runs", type=int, default=None, help="default 3 (families a, c, e), 1 (b)")
    p.add_argument("--model", default=HAIKU)
    p.add_argument("--with-probabilities", action="store_true")
    p.add_argument("--real", type=int, default=400)
    p.add_argument("--fictional", type=int, default=200)
    p.add_argument("--dead-only", action="store_true")
    p.add_argument("--tmp-seeds", action="store_true", help="section 5a fallback: the seeds also in a $TMPDIR file")
    p.add_argument("--collect-open", default=None, metavar="FILE", help="collect a (b) batch from its --tmp-seeds file")
    p.add_argument("--cancel-open", action="store_true")
    p.add_argument("--force", action="store_true", help="(b): fetch new seeds for a run that already has some")
    p.add_argument("--reuse-run", nargs="+", default=None, metavar="R0")
    p.add_argument("--user-agent", default=USER_AGENT)
    p = common(sub.add_parser("backtranslate", help="English labels for the run's (c) answers"), paid=True,
               budget=None)
    p.add_argument("--run-id", required=True)
    p.add_argument("--model", default=HAIKU)
    p = common(sub.add_parser("verbalized", help="(d) stage 2"), paid=True, budget=None)
    p.add_argument("--run-id", required=True)
    p.add_argument("--family", required=True)
    p.add_argument("--model", default=None, help="only the stage-1 answers of this model (default: every model)")
    for name, help_ in (("postprocess", "the items table and evaluation.json"), ("collapse", "collapse.json")):
        p = common(sub.add_parser(name, help=help_))
        p.add_argument("--run-id", nargs="+", default=None)
        p.add_argument("--embedder", choices=("none", "hash", "openai"),
                       default="none" if name == "postprocess" else "openai")
        p.add_argument("--budget-usd", type=float, default=0.5)
        p.add_argument("--confirm-expensive", action="store_true")
        p.add_argument("--confirmed-by", default=None)
        if name == "collapse":
            p.add_argument("--tau", type=float, default=0.9)
    p = common(sub.add_parser("model-test", help="the per-(family, model) table, $0"))
    p.add_argument("--run-id", required=True)
    p = common(sub.add_parser("submit", help="the run's rows to the registry"), paid=True, budget=10.0)
    p.add_argument("--run-id", required=True)
    p.add_argument("--top", type=int, default=None)
    p.add_argument("--per-cell", type=int, default=None)
    p.add_argument("--kept-target", type=int, default=None)
    p.add_argument("--kept-share", type=float, default=None)
    p.add_argument("--all", action="store_true")
    p.add_argument("--no-relabel", action="store_true", help="skip the registry's noun relabel step (tests)")
    p.add_argument("--record-only", action="store_true",
                   help="write candidates.jsonl without submitting, for label_fit.py check first")
    p = common(sub.add_parser("roles-report", help="the held roles, $0"))
    p.add_argument("--run-id", required=True)
    p = common(sub.add_parser("report", help="report.md, roger_sample.md, gloss_check.md, $0"))
    p.add_argument("--run-id", required=True)
    return ap


COMMANDS = {"seeds": cmd_seeds, "prompts": cmd_prompts, "translate-prompts": cmd_translate_prompts,
            "generate": cmd_generate, "backtranslate": cmd_backtranslate, "verbalized": cmd_verbalized,
            "postprocess": cmd_postprocess, "collapse": cmd_collapse, "model-test": cmd_model_test,
            "submit": cmd_submit, "roles-report": cmd_roles_report, "report": cmd_report}


def main(argv=None) -> int:
    from assistant_axis.gapgen.runs import configure_logging
    args = build_parser().parse_args(argv)
    configure_logging()
    if args.cmd == "submit":
        from assistant_axis.gapgen.generators.llm_entropy.submit import KEPT_SHARE_ASSUMED
        if args.kept_share is None:
            args.kept_share = KEPT_SHARE_ASSUMED
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
