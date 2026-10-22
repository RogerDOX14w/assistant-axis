#!/usr/bin/env python3
"""Generator B, lists of professions (generator id ``professions``; coding plan 16, § 7).

    uv run python data_analysis/gap_generation/professions_generator.py fetch [--only KEY ...] [--source esco]
        --approved-by 'Roger, <date>' [--hand] [--force] [--user-agent UA] [--dry-run]
    uv run python data_analysis/gap_generation/professions_generator.py build --run-id R [--source onet esco]
        [--oews PATH | --no-oews] [--n-titles 300] [--min-zipf 3.0] [--max-words 2] [--no-job-titles] [--dry-run]
    uv run python data_analysis/gap_generation/professions_generator.py render [--broad 29-1210 ...]
        [--job-title 33-9032.00:Bouncer ...] [--title 29-1210=Physicians ...]
    uv run python data_analysis/gap_generation/professions_generator.py lay --run-id R [--readings 3]
        [--transport live|batches] [--kinds broad job_title] [--limit N] --budget-usd C
        [--confirm-expensive --confirmed-by WHO] [--resume] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/professions_generator.py rank --run-id R
        [--weights zipf=1,employment=1,distance=1] [--embedder openai|hash|none] [--budget-usd 0.5] [--allow-dirty]
        [--dry-run]
    uv run python data_analysis/gap_generation/professions_generator.py label-fit --run-id R
        (--kept-share P [--wave-rows 300 --share 0.5] | --all) --budget-usd C [--model M] [--readings 3]
        [--embedder none] [--resume] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/professions_generator.py submit --run-id R
        (--kept-share P [--wave-rows 300 --share 0.5] | --all) [--transport batches|live] [--budget-usd 10]
        [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/professions_generator.py report --run-id R [--dry-run]

The package is ``assistant_axis/gapgen/generators/professions/`` (its modules' docstrings have the rules); the lay
call's prompt is the pinned rubric ``reports/trait_gap_generation/rubrics/profession_lay.md``.  A run lives in
``data/candidates/runs/professions/<run_id>/``: ``table.jsonl`` and ``build.json`` (build), ``lay_responses.jsonl``,
``lay_batches.json`` and ``lay.jsonl`` (lay), ``ranking.jsonl`` (rank), ``label_fit_input.jsonl`` and ``label_fit/``
(label-fit), ``candidates.jsonl``, ``keys.txt`` and ``submit_report.json`` (submit), ``report.md`` (report), and in
every step ``ATTRIBUTION.md``, ``run.json`` (one session per command) and ``usage.json`` (the sum of the sessions).

* ``fetch``: the downloads of § 7d into ``data/external/`` (``onet/job_titles.csv``, ``bls/oesm25nat.zip``;
  ``--source esco`` or ``--only esco_occupations`` adds ESCO's occupations by its API, wave 2), each licence page
  read, a manifest row merged into the ``DOWNLOAD_MANIFEST.json`` beside the file.  **Refused without
  ``--approved-by``** (each download is a fresh ask).  bls.gov refuses automated clients (403): the command then
  says to download the file by hand, and ``fetch --only KEY --hand --approved-by ...`` records the file placed
  there (``"downloaded_by": "hand"``).  Exit 3 while a file still waits to be downloaded by hand.  No API call.
* ``build``: ``table.jsonl`` from the files on disk (one row per SOC broad group, 459, and one per job title the cut
  keeps, 300), ``build.json`` (the cut, the sources' manifest rows, recovery by string of the corpus occupations
  among the source titles); prints the report.  Free.  Without the OEWS file it refuses unless ``--no-oews``
  (titles then come from the O*NET titles and nothing is ranked by employment).
* ``render``: the lay call's request as sent, for given broad groups and job titles, from the O*NET file (free;
  used for the rubric file's rendered samples).
* ``lay``: the Haiku 5.5 call per table row, three readings, live or batched; every response in
  ``lay_responses.jsonl``; the combined roles in ``lay.jsonl``.  Paid.
* ``rank``: the role index and the lay glosses embedded through the cache (pennies with OpenAI; ``hash`` for a
  free dry pass), ``ranking.jsonl``, the top 40 printed.  Paid (embeddings).
* ``label-fit``: the platform's label-fit check (``label_fit.py check``) on the wave's candidates, written to
  ``label_fit/``; ``submit`` applies its corrections.  Paid.
* ``submit``: the metered wave (or ``--all``) into the registry as role candidates; prints the M1, M3, R1 and R2
  commands.  Makes no call; its downstream estimate is gated like a paid step.
* ``report``: ``report.md``.

**Money.**  Every paid command prints its estimate, takes ``--budget-usd`` as a hard cap (over it refused; over the
$20 line needs ``--confirm-expensive --confirmed-by``), charges every response to a guarded usage, writes
``usage.json`` in a ``finally`` block, refuses uncommitted platform code without ``--allow-dirty`` and refuses to
re-ask what the run already holds without ``--resume``; ``--dry-run`` prints the plan, the estimate and the
rendered requests, and writes and calls nothing.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import professions as P  # noqa: E402

EXIT_REFUSED = 2
EXIT_HAND = 3
EMBED_CHARS_PER_TOKEN = 4.0


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


def _http(user_agent: str):
    from assistant_axis.gapgen.generators.professions.sources import UrllibHttp
    return UrllibHttp(user_agent)


def _embedder(name: str, *, model_id: Optional[str] = None, cache_dir: Optional[Path] = None):
    """``(embedder, cache)``: OpenAI through the embedding cache, or the free hash embedder (no cache)."""
    from assistant_axis.gapgen import embed as EM
    if name == "hash":
        return EM.HashEmbedder(), None
    if name == "openai":
        return EM.OpenAIEmbedder(model_id or EM.OPENAI_MODEL), (EM.EmbeddingCache(cache_dir) if cache_dir
                                                                 else EM.EmbeddingCache())
    raise ValueError(f"unknown embedder {name!r}")


def _label_fit_cli():
    """The platform's label-fit command module (its ``main`` and ``_client``; tests replace the client there)."""
    import data_analysis.gap_generation.label_fit as LFC
    return LFC


# --------------------------------------------------------------------------- helpers

def _run_dir(args, run_id: str) -> Path:
    return paths.run_dir(P.GENERATOR, paths.check_id(run_id, "run_id"), candidates_dir=args.candidates_dir)


def _dirty(args) -> Optional[str]:
    from assistant_axis.gapgen.runs import dirty_refusal, platform_dirty_files
    refusal, _ = dirty_refusal(platform_dirty_files(), bool(getattr(args, "allow_dirty", False)))
    return refusal


def _jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _write_jsonl(rows, path: Path) -> None:
    from assistant_axis.atomic_io import atomic_write_text
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), path)


def _need(path: Path, what: str) -> Optional[str]:
    return None if Path(path).exists() else f"REFUSED: no {what} ({path}); run the earlier step first"


def _gate(args, est_usd: float) -> Optional[int]:
    from assistant_axis.gapgen.cost import CostRefused, confirm_or_abort
    try:
        confirm_or_abort(est_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                         confirmed_by=args.confirmed_by)
    except CostRefused:
        return EXIT_REFUSED
    return None


def _sources_used(build: dict) -> list[str]:
    return [s for s in (build.get("source_keys") or []) if s]


# --------------------------------------------------------------------------- fetch

def cmd_fetch(args) -> int:
    from assistant_axis.gapgen.generators.professions import sources as S
    from assistant_axis.gapgen.runs import git_sha
    keys = list(args.only or [])
    if not keys:
        keys = list(S.DEFAULT_FETCH) + (list(S.ESCO_KEYS) if "esco" in (args.source or []) else [])
    try:
        res = S.fetch(keys, dest_root=args.external_dir, approved_by=args.approved_by, user_agent=args.user_agent,
                      http=None if args.dry_run else _http(args.user_agent), hand=args.hand, force=args.force,
                      dry_run=args.dry_run, git_sha=git_sha())
    except S.NotApproved as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_REFUSED
    except (KeyError, FileNotFoundError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    if args.dry_run:
        print("DRY-RUN: would fetch (nothing requested or written):")
        for line in res.dry_run_lines:
            print(f"  {line}")
        return 0
    print(f"fetched {res.fetched or 'none'}; already present {res.skipped or 'none'}")
    for p in sorted(set(res.written)):
        print(f"  manifest: {p}")
    if res.hand:
        print(f"WAITING FOR A DOWNLOAD BY HAND: {', '.join(h['key'] for h in res.hand)} (see the lines above)",
              file=sys.stderr)
        return EXIT_HAND
    return 0


# --------------------------------------------------------------------------- build

def _source_row(key: str, path: Path, external_dir: Path) -> dict:
    """The manifest row of a source the build read (or, for a file with no manifest row, its path and sha256)."""
    from assistant_axis.gapgen.generators.professions import sources as S
    row = S.manifest_row(S.SOURCES[key], external_dir) if key in S.SOURCES else None
    if row is not None and Path(path).exists() and row.get("sha256") and row["sha256"] != S.sha256_file(path):
        row = dict(row, sha256_on_disk=S.sha256_file(path), note_build="the file on disk differs from the manifest")
    if row is None:
        row = {"key": key, "file": str(path), "sha256": S.sha256_file(path) if Path(path).exists() else None,
               "licence": S.SOURCES[key].licence if key in S.SOURCES else None, "licence_verified": None,
               "downloaded_by": None, "note_build": "no manifest row: not fetched by professions_generator.py fetch"}
    return row


def cmd_build(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.professions import onet as O
    from assistant_axis.gapgen.generators.professions import report as R
    from assistant_axis.gapgen.generators.professions import soc as SOC
    from assistant_axis.gapgen.generators.professions import sources as S
    from assistant_axis.gapgen.generators.professions import submit as SUB
    from assistant_axis.gapgen.runs import start_run
    rdir = _run_dir(args, args.run_id)
    ext = Path(args.external_dir)
    occ_path = ext / S.SOURCES["onet_occupations"].dest
    if (msg := _need(occ_path, "O*NET occupation_data.csv")):
        print(msg, file=sys.stderr)
        return EXIT_REFUSED
    keys = ["onet_occupations"]
    occ = O.read_occupation_data(occ_path)
    oews, oews_path = None, None
    if not args.no_oews:
        oews_path = Path(args.oews) if args.oews else ext / S.SOURCES["bls_oews_national"].dest
        if not oews_path.exists():
            print(f"REFUSED: no OEWS table at {oews_path} (fetch it, or download it by hand; --oews PATH for a CSV or "
                  f"JSON table; --no-oews to build without employment and with O*NET titles for the groups)",
                  file=sys.stderr)
            return EXIT_REFUSED
        try:
            oews = SOC.read_oews(oews_path)
        except SOC.MissingDependency as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return EXIT_REFUSED
        keys.append("bls_oews_national")
    soc_titles = None
    soc_path = ext / S.SOURCES["bls_soc_structure"].dest
    if soc_path.exists():
        try:
            soc_titles = SOC.read_soc_structure(soc_path)
            keys.append("bls_soc_structure")
        except SOC.MissingDependency as exc:
            print(f"NOTE: the SOC structure file is there but not read ({exc})")
    groups = SOC.broad_groups(occ, oews, soc_titles=soc_titles)
    by_broad = {g.code: g for g in groups}
    rows = [g.as_table_row() for g in groups]
    occ_by_code = {o.code: o for o in occ}
    corpus = SUB.corpus_role_stems(args.data_dir)
    cut = None
    columns = None
    if not args.no_job_titles:
        jt_path = ext / S.SOURCES["onet_job_titles"].dest
        if (msg := _need(jt_path, "O*NET job_titles.csv (fetch it first, or --no-job-titles)")):
            print(msg, file=sys.stderr)
            return EXIT_REFUSED
        keys.append("onet_job_titles")
        titles = O.read_job_titles(jt_path)
        columns = O.job_title_columns(jt_path)
        emp = {}
        for t in titles:
            e, _ = SOC.detailed_employment(t.code, oews, by_broad)
            if e is not None:
                emp[t.code] = e
        kept, rep = O.cut_job_titles(titles, zipf=O.default_zipf(), corpus_stems=corpus, occupations=occ_by_code,
                                     employment=emp, max_words=args.max_words, min_zipf=args.min_zipf,
                                     n=args.n_titles)
        cut = rep.as_dict()
        for c in kept:
            o = occ_by_code.get(c.code)
            e, esrc = SOC.detailed_employment(c.code, oews, by_broad)
            rows.append({"kind": "job_title", "code": c.code, "occupation": o.title if o else None,
                         "title": c.job_title.title, "label": c.label, "stem": c.stem, "zipf": round(c.zipf, 3),
                         "employment": e, "employment_source": esrc, "description": o.description if o else "",
                         "also_under": c.also_under, "short_title": c.job_title.short_title})
        missing_occ = sum(1 for r in rows if r["kind"] == "job_title" and not r["occupation"])
        if missing_occ:
            print(f"WARNING: {missing_occ} job titles list an O*NET code with no occupation in occupation_data.csv")
    if "esco" in (args.source or []):
        esco_path = ext / S.SOURCES["esco_occupations"].dest
        if (msg := _need(esco_path, "ESCO occupations (fetch --source esco)")):
            print(msg, file=sys.stderr)
            return EXIT_REFUSED
        keys.append("esco_occupations")
        rows += _esco_rows(esco_path)
    rec = R.recovery_by_string(R.table_title_stems(rows), occupation_stems=R.corpus_occupations(args.data_dir))
    n_broad = sum(1 for r in rows if r["kind"] == "broad")
    n_titles = sum(1 for r in rows if r["kind"] == "job_title")
    print(f"{len(occ)} O*NET occupations -> {n_broad} SOC broad groups (459 expected)"
          + ("" if n_broad == 459 else "  *** not 459 ***"))
    if oews is None:
        print("WARNING: built with --no-oews: no employment, and broad titles from the O*NET titles")
    if cut:
        print(f"job titles: {cut['n_titles']:,} listed; dropped {json.dumps(cut['dropped'])}; passed {cut['n_passed']:,};"
              f" kept {cut['n_kept']} (top {cut['n']} by Zipf)")
    print(f"recovery by string of the {rec['n']} corpus occupations among the source titles: {rec['n_recovered']} "
          f"({rec['share']:.1%}); the lay roles' recovery comes after `lay` (report)")
    sources = [_source_row(k, ext / S.SOURCES[k].dest if k != "bls_oews_national" or not args.oews else Path(args.oews),
                           ext) for k in keys]
    build = {"schema_version": P.SCHEMA_VERSION, "run_id": args.run_id, "n_occupations": len(occ),
             "n_broad": n_broad, "n_job_titles": n_titles, "cut": cut, "job_title_columns": columns,
             "oews": str(oews_path) if oews_path else None, "source_keys": keys, "sources": sources,
             "recovery_source_titles": {k: v for k, v in rec.items() if k != "recovered"},
             "attribution": S.attribution_record(keys)}
    if args.dry_run:
        print(f"DRY-RUN: would write {rdir}/{P.TABLE_NAME} ({len(rows)} rows), {P.BUILD_NAME}, {P.ATTRIBUTION_NAME}, "
              f"run.json, usage.json")
        return 0
    ctx = start_run(P.GENERATOR, args.run_id, candidates_dir=args.candidates_dir,
                    args={"step": "build", "source": args.source, "n_titles": args.n_titles, "min_zipf": args.min_zipf,
                          "max_words": args.max_words, "no_oews": bool(args.no_oews), "source_keys": keys,
                          "attribution": build["attribution"]})
    _write_jsonl(rows, rdir / P.TABLE_NAME)
    atomic_write_text(json.dumps(build, indent=2, ensure_ascii=False) + "\n", rdir / P.BUILD_NAME)
    S.write_attribution(rdir, keys, run_label=f"run {P.GENERATOR}/{args.run_id}")
    ctx.finish()
    print(f"wrote {rdir}/{P.TABLE_NAME} ({len(rows)} rows), {P.BUILD_NAME}, {P.ATTRIBUTION_NAME}, run.json, usage.json")
    return 0


def _esco_rows(path: Path) -> list[dict]:
    """ESCO occupations grouped by their ISCO unit-group code (wave 2; the group title from the occupation's own
    link when the API gave one)."""
    by: dict[str, dict] = {}
    for r in _jsonl(path):
        code = r.get("isco_group")
        if not code or not r.get("preferred_label"):
            continue
        g = by.setdefault(code, {"kind": "esco_group", "code": code,
                                 "title": r.get("isco_group_title") or f"ISCO unit group {code}", "employment": None,
                                 "title_source": "esco_link" if r.get("isco_group_title") else "code",
                                 "employment_source": None, "detailed": []})
        g["detailed"].append({"code": r.get("code") or r.get("uri"), "title": r["preferred_label"],
                              "description": r.get("description") or ""})
    return [by[k] for k in sorted(by)]


# --------------------------------------------------------------------------- render

def cmd_render(args) -> int:
    from assistant_axis.gapgen.generators.professions import lay as LAY
    from assistant_axis.gapgen.generators.professions import onet as O
    from assistant_axis.gapgen.generators.professions import soc as SOC
    from assistant_axis.gapgen.generators.professions import sources as S
    occ = O.read_occupation_data(Path(args.external_dir) / S.SOURCES["onet_occupations"].dest)
    titles = dict(t.split("=", 1) for t in args.title or [])
    oews = None
    p = Path(args.oews) if args.oews else Path(args.external_dir) / S.SOURCES["bls_oews_national"].dest
    if p.exists():
        try:
            oews = SOC.read_oews(p)
        except SOC.MissingDependency as exc:
            print(f"NOTE: {exc}")
    groups = {g.code: g for g in SOC.broad_groups(occ, oews, soc_titles=titles)}
    rubric = LAY.load_rubric(args.rubrics_dir, allow_unpinned=True)
    print(f"rubric {rubric['name']} version {rubric['version']} ({(rubric['sha256'] or 'NOT PINNED')[:12]})")
    occ_by = {o.code: o for o in occ}
    for code in args.broad or []:
        g = groups.get(code)
        if g is None:
            print(f"no broad group {code}", file=sys.stderr)
            return EXIT_REFUSED
        print(f"\n=== variant 1: broad group {code} {g.title} ({len(g.detailed)} occupations; title from "
              f"{g.title_source}) ===")
        print(LAY.build_user(LAY.group_from_row(g.as_table_row())))
    for spec in args.job_title or []:
        code, _, title = spec.partition(":")
        o = occ_by.get(code)
        if o is None or not title:
            print(f"--job-title takes CODE:Title with an O*NET code in occupation_data.csv, not {spec!r}",
                  file=sys.stderr)
            return EXIT_REFUSED
        label, _ = O.lay_label(title)
        row = {"kind": "job_title", "code": code, "occupation": o.title, "title": title, "label": label,
               "description": o.description}
        print(f"\n=== variant 2: job title {title!r} under {code} {o.title} ===")
        print(LAY.build_user(LAY.group_from_row(row)))
    if args.system:
        print("\n=== system turn ===")
        print(rubric["text"])
    return 0


# --------------------------------------------------------------------------- lay

def cmd_lay(args) -> int:
    from assistant_axis.gapgen.batches import BatchTransport
    from assistant_axis.gapgen.cost import resume_usage
    from assistant_axis.gapgen.generators.llm_entropy.calls import LiveTransport, RunGuardedUsage, read_responses
    from assistant_axis.gapgen.generators.professions import lay as LAY
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge import warn_if_low_parse_rate
    rdir = _run_dir(args, args.run_id)
    if (msg := _need(rdir / P.TABLE_NAME, "table.jsonl (build)")):
        print(msg, file=sys.stderr)
        return EXIT_REFUSED
    if args.readings < 1:
        print("REFUSED: --readings must be at least 1", file=sys.stderr)
        return EXIT_REFUSED
    table = _jsonl(rdir / P.TABLE_NAME)
    groups = LAY.groups_from_table([r for r in table if r["kind"] in (args.kinds or LAY.KINDS)])
    if args.limit is not None:
        groups = groups[:args.limit]
    try:
        rubric = LAY.load_rubric(args.rubrics_dir, allow_unpinned=args.dry_run)
    except LAY.RubricNotPinned as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return EXIT_REFUSED
    calls = LAY.lay_calls(groups, rubric=rubric, readings=args.readings, model=args.model)
    batch = args.transport == "batches"
    from collections import Counter
    print(f"{len(groups)} rows ({dict(Counter(g.kind for g in groups))}) x {args.readings} readings = {len(calls)} calls, "
          f"{args.model}, {args.transport}")
    est = LAY.estimate(calls, batch=batch)
    print(est.format())
    if args.dry_run:
        if rubric["version"] is None:
            print("DRY-RUN: the rubric's text is not its latest pin; a real run would be refused")
        for kind in LAY.KINDS:
            g = next((x for x in groups if x.kind == kind), None)
            if g is not None:
                print(f"\n=== rendered request, a {kind} row ({g.id}) ===")
                print(LAY.render(g, rubric) if args.render_system else
                      f"[system: rubric {rubric['name']} v{rubric['version']}, {len(rubric['text'])} characters; "
                      f"--render-system prints it]\n" + LAY.build_user(g))
        print(f"\nDRY-RUN: nothing sent or written (would write {rdir}/{P.LAY_RESPONSES_NAME}, {P.LAY_NAME}, run.json, "
              f"usage.json)")
        return 0
    if (refusal := _dirty(args)):
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return EXIT_REFUSED
    records = read_responses(rdir / P.LAY_RESPONSES_NAME)
    if any(r.get("ok") for r in records) and not args.resume:
        print(f"REFUSED: {sum(1 for r in records if r.get('ok'))} answers are on record in "
              f"{rdir / P.LAY_RESPONSES_NAME}; pass --resume to reuse them (nothing answered is sent again)",
              file=sys.stderr)
        return EXIT_REFUSED
    if (code := _gate(args, est.usd)) is not None:
        return code
    ctx = start_run(P.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
        "step": "lay", "transport": args.transport, "budget_usd": args.budget_usd, "readings": args.readings,
        "model": args.model, "n_rows": len(groups), "n_calls": len(calls), "rubric": rubric["name"],
        "rubric_version": rubric["version"], "rubric_sha256": rubric["sha256"], "resume": bool(args.resume),
        "allow_dirty": bool(args.allow_dirty), "kinds": args.kinds, "limit": args.limit})
    ctx.confirmed_by = args.confirmed_by
    earlier = ctx.total_usage()
    if args.resume:
        rebuilt = resume_usage(earlier, records, where=f"{P.GENERATOR}/{args.run_id} lay")
        if rebuilt.total_cost_usd > earlier.total_cost_usd + 1e-9:
            from assistant_axis.gapgen.generators.llm_entropy.calls import usage_gap
            rec_ctx = start_run(P.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
                "step": "recovered_usage", "note": "spend the response records show beyond the recorded sessions"})
            rec_ctx.usage = usage_gap(rebuilt, earlier)
            rec_ctx.finish()
            earlier = ctx.total_usage()
    ctx.usage = RunGuardedUsage(budget_usd=args.budget_usd, usage_path=rdir / "usage.json", earlier=earlier)

    def factory(runner):
        if args.transport == "live":
            runner.client = _anthropic_client()
            return LiveTransport(runner)
        return BatchTransport(runner, _batch_client(), rdir / P.BATCHES_NAME, budget_usd=args.budget_usd)
    res = None
    try:
        res = asyncio.run(LAY.lay_groups(groups, usage=ctx.usage, readings=args.readings,
                                         records_path=rdir / P.LAY_RESPONSES_NAME, transport_factory=factory,
                                         resume_records=records if args.resume else (), model=args.model,
                                         rubric=rubric, batch_id=f"{args.run_id}_{P.GENERATOR}_lay",
                                         run_id=args.run_id, concurrency=args.concurrency, checkpoint=ctx.finish))
    finally:
        ctx.finish()
        print(ctx.usage.log_line(f"[usage this session, {P.GENERATOR}/{args.run_id} lay]"), file=sys.stderr)
    rows = LAY.lay_rows(groups, res, readings=args.readings)
    _write_jsonl(rows, rdir / P.LAY_NAME)
    w = res.wave
    warn_if_low_parse_rate(label=f"{P.GENERATOR}:lay:{args.model}", n_ok=w.n_ok, n_total=w.n_attempted)
    ag = LAY.agreement(rows)
    print(f"lay: {len(w.answers)} of {w.n_units} calls answered ({w.n_reused} reused, {w.n_retried} asked once more); "
          f"failed {len(w.failures)}; stop reasons {dict(w.stop_reasons)}")
    print(f"agreement (diagnostic): {json.dumps(ag)}")
    print(f"wrote {rdir}/{P.LAY_NAME} ({sum(len(r['roles']) for r in rows)} roles over {len(rows)} rows)")
    if res.stopped is not None:
        print(f"STOPPED ({type(res.stopped).__name__}): {res.stopped}; the answers paid for are recorded; --resume "
              f"continues", file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------- rank

def cmd_rank(args) -> int:
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.generators.llm_entropy.calls import RunGuardedUsage
    from assistant_axis.gapgen.generators.professions import rank as RK
    from assistant_axis.gapgen.metric_config import MetricConfig
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage
    rdir = _run_dir(args, args.run_id)
    if (msg := _need(rdir / P.LAY_NAME, "lay.jsonl (lay)")):
        print(msg, file=sys.stderr)
        return EXIT_REFUSED
    try:
        weights = RK.parse_weights(args.weights)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    lay_rows = _jsonl(rdir / P.LAY_NAME)
    rows = RK.ranking_rows(lay_rows)
    print(f"{len(rows)} lay roles (one per stem) from {len(lay_rows)} rows; weights {weights}")
    cfg = MetricConfig.load(args.metric_config) if args.embedder != "none" else None
    emb = cache = None
    est_usd = 0.0
    query_form = RK.QUERY_FORM
    if args.embedder != "none":
        st = RK.role_index_settings(cfg)
        query_form = st["query_form"]
        _, texts = RK.role_index_texts(args.data_dir, st["representation"])
        queries = [q for q in (RK.role_query(r, query_form=query_form) for r in rows) if q]
        emb, cache = _embedder(args.embedder, model_id=cfg.live_model.get("model_id"), cache_dir=args.embed_cache_dir)
        uniq = list(dict.fromkeys(texts + queries))
        miss = list(range(len(uniq))) if cache is None else cache.lookup(emb.tag, uniq)[1]
        tokens = int(sum(len(uniq[i]) for i in miss) / EMBED_CHARS_PER_TOKEN)
        est_usd = 0.0 if args.embedder == "hash" else cost_for_usage(emb.usage_model, tokens, 0)
        print(f"  embeddings: {len(texts)} corpus roles and {len(queries)} lay glosses ({st['representation']}, "
              f"{st['variant']}, query {query_form}, settings from {st['source']}); {len(miss)} of {len(uniq)} texts "
              f"not in the cache, "
              f"~{tokens:,} tokens = ${est_usd:.4f}" + ("  (hash: local, free)" if args.embedder == "hash" else ""))
    else:
        print("  --embedder none: no distance feature (every role counted at the mean distance)")
    if args.dry_run:
        print(f"DRY-RUN: nothing embedded or written (would write {rdir}/{P.RANKING_NAME}, run.json, usage.json)")
        return 0
    if args.embedder == "openai" and (refusal := _dirty(args)):
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return EXIT_REFUSED
    if (code := _gate(args, est_usd)) is not None:
        return code
    ctx = start_run(P.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
        "step": "rank", "weights": weights, "embedder": args.embedder, "budget_usd": args.budget_usd,
        "query_form": query_form, "near_corpus_cosine": RK.NEAR_CORPUS_COSINE,
        "metric_config": None if cfg is None else cfg.config_version})
    ctx.usage = RunGuardedUsage(budget_usd=args.budget_usd, usage_path=rdir / "usage.json", earlier=ctx.total_usage())
    index = embed = None
    try:
        if emb is not None:
            def embed(texts):
                return EM.embed_texts(emb, texts, cache=cache, usage=ctx.usage)
            index, info = RK.build_role_index(args.data_dir, cfg=cfg, embed=embed)
            ctx.args["role_index"] = info
        ranked = RK.rank_roles(lay_rows, zipf=RK.default_zipf(), role_index=index, embed=embed, weights=weights,
                               query_form=query_form)
    except BudgetExceededError as exc:
        print(f"STOPPED at the cap (--budget-usd {args.budget_usd:g}): {exc}", file=sys.stderr)
        return 1
    finally:
        ctx.finish()
        print(ctx.usage.log_line(f"[usage this session, {P.GENERATOR}/{args.run_id} rank]"), file=sys.stderr)
    ranked = _annotated(args, ranked)
    _write_jsonl(ranked, rdir / P.RANKING_NAME)
    n_near = sum(1 for r in ranked if r["near_corpus"])
    from collections import Counter
    st = Counter("net-new" if r["net_new"] else (r["excluded"] or "registered") for r in ranked)
    print(f"  against the corpus, the queue and the registry now (submit checks again): {dict(st)}")
    print(f"wrote {rdir}/{P.RANKING_NAME}: {len(ranked)} roles, {n_near} near a corpus role (cosine >= "
          f"{RK.NEAR_CORPUS_COSINE}, still ranked)")
    for line in RK.top_lines(ranked, args.top):
        print(line)
    return 0


# --------------------------------------------------------------------------- label-fit and submit

def _annotated(args, ranking):
    """``ranking`` with ``net_new``, ``registered_as``, ``excluded`` against the corpus, the seed queue and the
    registry as they are now (``submit.annotate``), in rank order."""
    import data_analysis.seed_entities as se
    from assistant_axis.gapgen.generators.professions import submit as SUB
    from assistant_axis.gapgen.registry import Registry
    reg = Registry(args.registry).fold() if Path(args.registry).exists() else {}
    qp = Path(args.data_dir) / "seed_queue.json"
    queue = se.load_queue(qp) if qp.exists() else {"entries": []}
    return SUB.annotate(ranking, registry_rows=reg, corpus_stems=SUB.corpus_role_stems(args.data_dir),
                        queue_stems=SUB.queue_role_stems(queue))


def _selection(args, rdir: Path):
    """``(annotated ranking, selected rows)`` as ``submit`` will select them."""
    from assistant_axis.gapgen.generators.professions import submit as SUB
    rows = _annotated(args, _jsonl(rdir / P.RANKING_NAME))
    if args.all:
        return rows, SUB.select_all(rows)
    return rows, SUB.select_wave(rows, wave_rows=args.wave_rows, share=args.share, kept_share=args.kept_share)


def _check_selection_args(args) -> Optional[str]:
    if not args.all and args.kept_share is None:
        return "REFUSED: --kept-share P (the pilot's measured role kept share) is needed for a metered wave; or --all"
    return None


def cmd_label_fit(args) -> int:
    from assistant_axis.gapgen.generators.professions import submit as SUB
    from assistant_axis.gapgen.registry import CANDIDATE_FIELDS
    from dataclasses import asdict
    rdir = _run_dir(args, args.run_id)
    if (msg := _need(rdir / P.RANKING_NAME, "ranking.jsonl (rank)")) or (msg := _check_selection_args(args)):
        print(msg, file=sys.stderr)
        return EXIT_REFUSED
    try:
        _, sel = _selection(args, rdir)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    cands = SUB.to_candidates(sel, args.run_id)
    inp = rdir / P.LABEL_FIT_INPUT_NAME
    print(f"{len(sel)} selected roles, {len(cands)} candidates -> {inp}")
    if not args.dry_run:
        _write_jsonl([{k: asdict(c)[k] for k in CANDIDATE_FIELDS} for c in cands], inp)
    elif not inp.exists():
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / P.LABEL_FIT_INPUT_NAME
        _write_jsonl([{k: asdict(c)[k] for k in CANDIDATE_FIELDS} for c in cands], tmp)
        inp = tmp
    argv = ["--registry", str(args.registry), "--candidates-dir", str(args.candidates_dir or paths.DATA_CANDIDATES)]
    if args.rubrics_dir:
        argv += ["--rubrics-dir", str(args.rubrics_dir)]
    argv += ["check", "--candidates", str(inp), "--out-dir", str(rdir / P.LABEL_FIT_DIR), "--model", args.model,
             "--readings", str(args.readings), "--embedder", args.embedder, "--budget-usd", str(args.budget_usd),
             "--keep-undecided"]
    for flag in ("resume", "allow_dirty", "dry_run", "confirm_expensive", "no_oewn", "render"):
        if getattr(args, flag, False):
            argv.append("--" + flag.replace("_", "-"))
    if args.confirmed_by:
        argv += ["--confirmed-by", args.confirmed_by]
    print("label_fit.py " + " ".join(argv))
    try:
        code = _label_fit_cli().main(argv)
    except SystemExit as exc:                       # its cost gate (CostRefused) and argparse exit this way
        code = exc.code if isinstance(exc.code, int) else EXIT_REFUSED
    if not args.dry_run and code == 0:
        print(f"then: professions_generator.py submit --run-id {args.run_id} (applies {rdir / P.LABEL_FIT_DIR}/"
              f"decisions.json)")
    return code


def cmd_submit(args) -> int:
    from assistant_axis.gapgen.cost import CostRefused
    from assistant_axis.gapgen.generators.professions import submit as SUB
    rdir = _run_dir(args, args.run_id)
    if (msg := _need(rdir / P.RANKING_NAME, "ranking.jsonl (rank)")) or (msg := _check_selection_args(args)):
        print(msg, file=sys.stderr)
        return EXIT_REFUSED
    build = json.loads((rdir / P.BUILD_NAME).read_text(encoding="utf-8")) if (rdir / P.BUILD_NAME).exists() else {}
    try:
        SUB.run_submit(args.run_id, ranking=_jsonl(rdir / P.RANKING_NAME), wave_rows=args.wave_rows, share=args.share,
                       kept_share=args.kept_share, all_rows=args.all, dry_run=args.dry_run, budget_usd=args.budget_usd,
                       confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by,
                       transport=args.transport, registry_path=Path(args.registry), data_dir=Path(args.data_dir),
                       candidates_dir=args.candidates_dir, sources_used=_sources_used(build))
    except CostRefused:
        return EXIT_REFUSED
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    return 0


def cmd_report(args) -> int:
    from assistant_axis.gapgen.generators.professions import report as R
    rdir = _run_dir(args, args.run_id)
    if not rdir.exists():
        print(f"REFUSED: no run directory {rdir}", file=sys.stderr)
        return EXIT_REFUSED
    if args.dry_run:
        print(R.report_markdown(rdir, data_dir=Path(args.data_dir), registry_path=Path(args.registry)))
        return 0
    p = R.write_report(rdir, data_dir=Path(args.data_dir), registry_path=Path(args.registry))
    print(f"wrote {p}")
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    from assistant_axis.gapgen.generators.professions import lay as LAY
    from assistant_axis.gapgen.generators.professions import rank as RK
    from assistant_axis.gapgen.generators.professions import sources as S
    from assistant_axis.gapgen.generators.professions import submit as SUB
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidates-dir", type=Path, default=None, help="default data/candidates (runs under runs/)")
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="the corpus and the seed queue (default data/)")
    ap.add_argument("--external-dir", type=Path, default=paths.DATA_EXTERNAL, help="downloads (default data/external/)")
    ap.add_argument("--rubrics-dir", type=Path, default=None, help="default reports/trait_gap_generation/rubrics")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def money(p, budget: Optional[float]):
        p.add_argument("--budget-usd", type=float, default=budget, required=budget is None,
                       help="hard cap on this command's spend (over $20 needs --confirm-expensive --confirmed-by)")
        p.add_argument("--confirm-expensive", action="store_true")
        p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for anything over $20")

    def selection(p):
        p.add_argument("--wave-rows", type=int, default=SUB.WAVE_ROWS_DEFAULT, help="reviewed rows a wave aims at")
        p.add_argument("--share", type=float, default=SUB.SHARE_DEFAULT, help="B's share of the wave (default 0.5)")
        p.add_argument("--kept-share", type=float, default=None, help="the pilot's measured role kept share")
        p.add_argument("--all", action="store_true", help="the whole ranking (over $20 downstream needs the gate)")

    p = sub.add_parser("fetch", help="the downloads (refused without --approved-by); no API call")
    p.add_argument("--only", nargs="+", choices=tuple(S.SOURCES), default=None)
    p.add_argument("--source", nargs="+", choices=("onet", "esco"), default=["onet"],
                   help="esco adds ESCO's occupations by its API (wave 2)")
    p.add_argument("--approved-by", default=None, help="Roger's go for the downloads, e.g. 'Roger, 2026-10-23'")
    p.add_argument("--hand", action="store_true", help="record files downloaded by hand at their destinations")
    p.add_argument("--force", action="store_true")
    p.add_argument("--user-agent", default=S.USER_AGENT)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("build", help="table.jsonl from the files on disk (free)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--source", nargs="+", choices=("onet", "esco"), default=["onet"])
    p.add_argument("--oews", type=Path, default=None, help="the OEWS table (.zip, .xlsx, .csv or .json); default the "
                                                           "fetched data/external/bls/oesm25nat.zip")
    p.add_argument("--no-oews", action="store_true", help="build without employment (and with O*NET group titles)")
    p.add_argument("--no-job-titles", action="store_true")
    p.add_argument("--n-titles", type=int, default=300)
    p.add_argument("--min-zipf", type=float, default=3.0)
    p.add_argument("--max-words", type=int, default=2)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("render", help="the lay call's user turns for given groups and titles (free)")
    p.add_argument("--broad", nargs="+", default=None, metavar="SOC_BROAD_CODE")
    p.add_argument("--job-title", nargs="+", default=None, metavar="ONET_CODE:Title")
    p.add_argument("--title", nargs="+", default=None, metavar="CODE=Title",
                   help="a broad group's title when no OEWS table is on disk")
    p.add_argument("--oews", type=Path, default=None)
    p.add_argument("--system", action="store_true", help="also print the system turn")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("lay", help="the Haiku 5.5 lay-role call per table row (paid)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--readings", type=int, default=LAY.READINGS)
    p.add_argument("--model", default=LAY.MODEL)
    p.add_argument("--transport", choices=("live", "batches"), default="live")
    p.add_argument("--kinds", nargs="+", choices=LAY.KINDS, default=None)
    p.add_argument("--limit", type=int, default=None, help="only the first N rows (a pilot)")
    p.add_argument("--concurrency", type=int, default=LAY.CONCURRENCY)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--allow-dirty", action="store_true")
    p.add_argument("--render-system", action="store_true", help="with --dry-run: print the system turn too")
    p.add_argument("--dry-run", action="store_true")
    money(p, None)
    p.set_defaults(func=cmd_lay)

    p = sub.add_parser("rank", help="familiarity and distance, ranking.jsonl (embeddings: pennies)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--weights", default=None, help="zipf=1,employment=1,distance=1")
    p.add_argument("--embedder", choices=("openai", "hash", "none"), default="openai")
    p.add_argument("--embed-cache-dir", type=Path, default=None)
    p.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
    p.add_argument("--top", type=int, default=RK.TOP_N)
    p.add_argument("--allow-dirty", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    money(p, 0.5)
    p.set_defaults(func=cmd_rank)

    p = sub.add_parser("label-fit", help="the platform's label-fit check on the wave's labels (paid)")
    p.add_argument("--run-id", required=True)
    selection(p)
    p.add_argument("--model", default="claude-haiku-5-5")
    p.add_argument("--readings", type=int, default=3)
    p.add_argument("--embedder", default="none", choices=("bge", "gemma", "openai", "hash", "none"),
                   help="the check's free cosine pre-screen (default none here)")
    p.add_argument("--no-oewn", action="store_true")
    p.add_argument("--render", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--allow-dirty", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    money(p, 2.0)
    p.set_defaults(func=cmd_label_fit)

    p = sub.add_parser("submit", help="the metered wave into the registry (no call; the downstream estimate gated)")
    p.add_argument("--run-id", required=True)
    selection(p)
    p.add_argument("--transport", choices=("live", "batches"), default="batches",
                   help="the transport the follow-up M1 and M3 commands are priced and printed with")
    p.add_argument("--dry-run", action="store_true")
    money(p, SUB.DEFAULT_BUDGET_USD)
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("report", help="report.md (free)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv=None) -> int:
    from assistant_axis.gapgen.runs import configure_logging
    configure_logging()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
