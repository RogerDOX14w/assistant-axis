#!/usr/bin/env python3
"""The label-fit check: does a generator's label, said of a person, mean what its gloss says?

    uv run python data_analysis/gap_generation/label_fit.py validate --marks SHEET.md [--model M] [--readings 3]
        [--borderline LABEL ...] [--budget-usd 2] [--resume] [--render] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/label_fit.py check (--run GENERATOR/RUN_ID | --candidates FILE)
        [--model M] [--readings 3] [--screen-floor X] [--keep-undecided] [--budget-usd 2] [--resume] [--render]
        [--allow-dirty] [--dry-run]

The module is ``assistant_axis/gapgen/label_fit.py`` (its docstring has the rules); the prompt is the pinned rubric
``reports/trait_gap_generation/rubrics/label_fit.md``.

``validate`` asks the check about every row of a precision-sample sheet (``structural_generator.py report``'s
``roger_sample.md``: its ``label`` and ``gloss`` columns) and scores the decisions against the marks in its last
column (a mark starting with ``?`` should not fit, any other mark should), printing a confusion table (and a second
without the ``--borderline`` rows), the disagreements, and what the cosine pre-screen would have done.  Run it once
per ``--model``: responses and ``usage.json`` are shared in ``--out-dir`` (default ``label_fit_validate/`` beside the
sheet), the decisions and readout are per model (``decisions_<model>.json``, ``readout_<model>.md``).

``check`` asks it about every distinct ``(label, gloss)`` pair of a run's ``candidates.jsonl`` (``--run``: the file
in ``data/candidates/runs/<generator>/<run_id>/``; ``--candidates``: any file of ``Candidate`` lines), **before** the
candidates are submitted, and writes to ``--out-dir`` (default ``label_fit/`` beside the candidates file):
``responses.jsonl``, ``usage.json``, ``decisions.json``, ``readout.md`` and the corrected ``candidates.jsonl``
(a relabelled candidate carries the new label as its surface and ``;label_fit:<verdict>:<original label>`` after
its ``source_ref``).  The corrected file is submitted with ``gap_registry.py submit --from``.  It is not written
while a pair has no answer (``--keep-undecided`` keeps those candidates as they are).

Both are paid (one call per pair and reading, live: about $0.05 for the 50 rows at three readings on Haiku 5.5, about
$1.10 on Sonnet 5.5): each prints its estimate, takes ``--budget-usd`` as a hard cap (over $20 needs
``--confirm-expensive --confirmed-by``), writes ``usage.json``, refuses uncommitted platform code without
``--allow-dirty``, and refuses to reuse answers on record for the same model without ``--resume``.  ``--dry-run``
prints the selection, the estimate and (``--render``) the system turn and one user turn per variant, and writes and
calls nothing (no embedding either).  The free cosine pre-screen runs with ``--embedder`` (default the local
``bge``; ``none`` skips it) and decides nothing unless ``--screen-floor`` is given.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import label_fit as LF  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.runs import platform_dirty_files  # noqa: E402

DEFAULT_BUDGET_USD = 2.0


def _client():
    """The Anthropic client, direct key (tests replace this)."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def _senses(args):
    """``(senses function or None, use_oewn)``: WordNet's senses when OEWN is installed in-tree and not
    ``--no-oewn``."""
    if args.no_oewn:
        return None, False
    from assistant_axis.gapgen import wordnet as W
    try:
        ok = W.oewn_installed()
    except ImportError:
        ok = False
    if not ok:
        print("NOTE: OEWN is not installed in data/external/wn: no dictionary senses are shown (setup_external.py "
              "installs it)")
        return None, False
    return None, True


def _rows(args) -> dict:
    """The registry's folded view (retractions applied), read without its lock (nothing here writes to it); empty
    with ``--no-registry`` or when there is no registry."""
    if args.no_registry:
        return {}
    from assistant_axis.gapgen.registry import read_snapshot
    p = Path(args.registry)
    return read_snapshot(p) if p.exists() else {}


def _variant(it: LF.Item) -> str:
    if it.context.get("recorded_senses") or it.context.get("usual_sense"):
        return "registry row with M1's senses"
    if it.context.get("dictionary_senses"):
        return "dictionary senses only"
    return "no senses known"


def _render(rubric: dict, items: Sequence[LF.Item]) -> None:
    print(f"=== system turn: {rubric['name']} version {rubric['version']} (sha {(rubric['sha256'] or '?')[:12]}...), "
          f"sent byte for byte ===")
    print(rubric["text"])
    seen = set()
    for it in items:
        v = _variant(it)
        if v in seen:
            continue
        seen.add(v)
        print(f"=== user turn, {v}: {it.label} ===")
        print(it.user)


def _cosines(args, items, usage) -> Optional[str]:
    """Embed for the pre-screen (free with a local arm); returns the embedder's name, or None when skipped."""
    arm = args.embedder
    if arm == "none":
        return None
    from assistant_axis.gapgen import embed as EM
    if arm in EM.LOCAL_MODELS and not EM.hf_snapshot_present(EM.LOCAL_MODELS[arm]["model_id"]):
        print(f"NOTE: {EM.LOCAL_MODELS[arm]['model_id']} is not in data/external/hf: no cosines (the pre-screen is "
              f"a report, so the check goes on)")
        return None
    embedder = EM.make_embedder(arm)
    cache = None if arm == "hash" else EM.EmbeddingCache(args.embed_cache_dir) if args.embed_cache_dir \
        else EM.EmbeddingCache()
    n = LF.cosines(items, embed=lambda texts: EM.embed_texts(embedder, texts, cache=cache, usage=usage))
    print(f"cosines: {n} of {len(items)} pairs have a sense to compare the gloss with ({embedder.name})")
    return embedder.name


def _prepare(args, pairs, out: Path):
    """Shared by both commands up to the calls: ``(rubric, items, records, answers)`` or an exit code."""
    if args.model not in LF.MODELS:
        print(f"REFUSED: --model must be one of {', '.join(LF.MODELS)}", file=sys.stderr)
        return 2
    try:
        rubric = LF.load_rubric(args.rubrics_dir, allow_unpinned=args.dry_run)
    except LF.RubricNotPinned as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    if rubric["version"] is None:
        print("DRY-RUN: the rubric's text is not its latest pin; a real run would be refused")
    senses, use_oewn = _senses(args)
    items = LF.build_items(pairs, system=rubric["text"], senses=senses, rows=_rows(args), use_oewn=use_oewn)
    if args.limit is not None:
        items = items[:args.limit]
        print(f"--limit {args.limit}: the first {len(items)} pairs")
    records = LF.read_records(out / LF.RESPONSES_NAME)
    answers = LF.answers_on_record(records, model=args.model)
    mine = [r for r in records if r.get("model") == args.model]
    if mine and not args.resume and not args.dry_run:
        print(f"REFUSED: {len(mine)} responses of {args.model} are on record in {out / LF.RESPONSES_NAME}; pass "
              f"--resume to reuse them (only the readings without an answer are sent)", file=sys.stderr)
        return 2
    by_v = {}
    for it in items:
        by_v[_variant(it)] = by_v.get(_variant(it), 0) + 1
    print(f"{len(items)} distinct (label, gloss) pairs: {json.dumps(by_v)}")
    return rubric, items, records, answers


def _ask(args, rubric, items, answers, out: Path) -> tuple[Optional[int], bool, Optional[str], dict, float]:
    """Embed, estimate, gate, call.  ``(exit code, done, embedder, answers, spend on record)``: ``done`` means return
    the code at once (a dry run, a refusal); otherwise the caller writes its outputs and returns the code (2 after a
    budget stop, else None)."""
    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort, resume_usage
    from assistant_axis.gapgen.runs import dirty_refusal
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import MultiModelUsage
    resp, usage_path = out / LF.RESPONSES_NAME, out / LF.USAGE_NAME
    embedder = None
    usage = None
    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
        prev = resume_usage(MultiModelUsage.load_or_create(usage_path), LF.read_records(resp), where=str(out))
        usage = GuardedUsage(per_model=dict(prev.per_model), budget_usd=prev.total_cost_usd + args.budget_usd,
                             usage_path=usage_path)
        embedder = _cosines(args, items, usage)
        usage.write_json(usage_path)
    elif args.embedder != "none":
        print(f"DRY-RUN: no cosines (would embed the glosses and senses with the {args.embedder} arm)")
    todo = LF.todo_calls(items, answers, args.readings, screen_floor=args.screen_floor)
    n_screened = sum(1 for it in items if args.screen_floor is not None and it.cos_usual is not None
                     and it.cos_usual >= args.screen_floor)
    est = LF.estimate(len(todo), args.model)
    print(f"{len(items)} pairs x {args.readings} reading(s); {n_screened} settled by the screen; "
          f"{len(items) * args.readings - len(todo) - n_screened * args.readings} answers on record; "
          f"{len(todo)} calls to make:")
    print(est.format())
    confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                     confirmed_by=args.confirmed_by)
    refused, _rec = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    if refused and not args.dry_run:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2, True, embedder, answers, 0.0
    if refused:
        print(f"DRY-RUN: the real run would be REFUSED: {refused}")
    if args.render:
        _render(rubric, items)
    if args.dry_run:
        print(f"DRY-RUN: would make {len(todo)} calls on {args.model} (max_tokens {LF.MAX_TOKENS}, no temperature) "
              f"and write {out}/")
        return 0, True, None, answers, 0.0
    res = None
    try:
        if todo:
            res = asyncio.run(LF.ask(todo, client=_client(), rubric=rubric, model=args.model, usage=usage,
                                     responses_path=resp, concurrency=args.concurrency))
    finally:
        usage.write_json(usage_path)
    if res is not None:
        warn_if_low_parse_rate(label=f"label fit:{args.model}", n_ok=res.n_ok, n_total=res.n_calls,
                               logger_obj=logging.getLogger("label_fit"),
                               extra=f"failed calls by kind {res.error_kinds}")
        print(f"{res.n_ok} of {res.n_calls} calls answered; failed {res.error_kinds}; {usage.plain().log_line()}"
              + ("; STOPPED at the budget" if res.stopped_by_budget else ""))
    code = 2 if res is not None and res.stopped_by_budget else None
    return code, False, embedder, LF.answers_on_record(LF.read_records(resp), model=args.model), usage.total_cost_usd


def _slug(model: str) -> str:
    return model.replace("claude-", "").replace(".", "_")


# --------------------------------------------------------------------------- validate

def cmd_validate(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    marks = LF.parse_marks(args.marks)
    marked = [m for m in marks if m["should_fit"] is not None]
    print(f"{len(marks)} rows in {args.marks}: {sum(1 for m in marked if not m['should_fit'])} marked '?' (should "
          f"not fit), {sum(1 for m in marked if m['should_fit'])} other marks (should fit), "
          f"{len(marks) - len(marked)} unmarked")
    out = Path(args.out_dir) if args.out_dir else Path(args.marks).parent / "label_fit_validate"
    prep = _prepare(args, [(m["label"], m["gloss"]) for m in marks], out)
    if isinstance(prep, int):
        return prep
    rubric, items, _records, answers = prep
    code, done, embedder, answers, spent = _ask(args, rubric, items, answers, out)
    if done:
        return code
    decisions = LF.decide(items, answers, args.readings, screen_floor=args.screen_floor)
    confs = {"all marked rows": LF.confusion(marks, decisions)}
    if args.borderline:
        confs[f"without the borderline rows ({', '.join(args.borderline)})"] = LF.confusion(
            marks, decisions, exclude=args.borderline)
    for title, conf in confs.items():
        print(LF.format_confusion(conf, title))
    main = confs["all marked rows"]
    for d in main["disagreements"]:
        print(f"  #{d['n']} {d['label']}: Roger {d['mark'][:60]!r}; check {d['got']} ({d['verdict']}, votes "
              f"{d['votes']}){'; proposals ' + ', '.join(d['proposals']) if d['proposals'] else ''}")
    screen = LF.screen_effect(marks, items)
    print(f"cosine pre-screen (reported only): {json.dumps(screen)}")
    slug = _slug(args.model)
    dpath, rpath = out / f"decisions_{slug}.json", out / f"readout_{slug}.md"
    doc = LF.decisions_doc(decisions, rubric=rubric, model=args.model, readings=args.readings,
                           screen_floor=args.screen_floor, embedder=embedder,
                           extra={"marks": str(args.marks), "confusion": confs, "screen_effect": screen,
                                  "cost_usd_on_record": round(spent, 4)})
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", dpath)
    files = {"marks": Path(args.marks), "rubric": _REPO_ROOT / rubric["file"], "responses": out / LF.RESPONSES_NAME}
    atomic_write_text(LF.render_validate_readout(marks, decisions, confs, screen, rubric=rubric, model=args.model,
                                                 readings=args.readings, usage_usd=spent, doc_path=rpath,
                                                 files=files), rpath)
    print(f"wrote {out / LF.RESPONSES_NAME}, {out / LF.USAGE_NAME}, {dpath}, {rpath}")
    return code or 0


# --------------------------------------------------------------------------- check

def _candidates_path(args) -> tuple[Path, str]:
    if args.run:
        gen, sep, run_id = args.run.partition("/")
        if not sep:
            raise SystemExit("REFUSED: --run takes GENERATOR/RUN_ID")
        d = paths.run_dir(paths.check_id(gen, "generator"), paths.check_id(run_id, "run_id"),
                          candidates_dir=args.candidates_dir)
        return d / "candidates.jsonl", args.run
    return Path(args.candidates), str(args.candidates)


def cmd_check(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import CANDIDATE_FIELDS, read_candidates
    src, source = _candidates_path(args)
    if not src.exists():
        print(f"REFUSED: no candidates file {src} (write the run's candidates without submitting them first, e.g. "
              f"structural_generator.py submit --record-only)", file=sys.stderr)
        return 2
    cands = read_candidates(src)
    pairs = LF.pairs_of(cands)
    print(f"{len(cands)} candidates in {src}; {len(pairs)} with a gloss hint")
    out = Path(args.out_dir) if args.out_dir else src.parent / "label_fit"
    if out.resolve() == src.parent.resolve():
        print("REFUSED: --out-dir must not be the candidates file's own directory (its candidates.jsonl would be "
              "replaced)", file=sys.stderr)
        return 2
    prep = _prepare(args, pairs, out)
    if isinstance(prep, int):
        return prep
    rubric, items, _records, answers = prep
    code, done, embedder, answers, spent = _ask(args, rubric, items, answers, out)
    if done:
        return code
    decisions = LF.decide(items, answers, args.readings, screen_floor=args.screen_floor)
    c = LF.counts(decisions)
    print(f"decisions: {json.dumps(c)}")
    fixed, cc = LF.corrected_candidates(cands, decisions)
    files = {"input": src, "rubric": _REPO_ROOT / rubric["file"], "usage": out / LF.USAGE_NAME,
             "responses": out / LF.RESPONSES_NAME, "decisions": out / LF.DECISIONS_NAME,
             "candidates": out / LF.CANDIDATES_NAME}
    doc = LF.decisions_doc(decisions, rubric=rubric, model=args.model, readings=args.readings,
                           screen_floor=args.screen_floor, embedder=embedder,
                           extra={"source": source, "candidates_file": str(src), "n_candidates": len(cands),
                                  "candidate_counts": cc, "cost_usd_on_record": round(spent, 4)})
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", out / LF.DECISIONS_NAME)
    atomic_write_text(LF.render_check_readout(decisions, source=source, n_candidates=len(cands), cand_counts=cc,
                                              rubric=rubric, model=args.model, readings=args.readings,
                                              usage_usd=spent, doc_path=out / LF.READOUT_NAME, files=files,
                                              screen_floor=args.screen_floor), out / LF.READOUT_NAME)
    print(f"wrote {out / LF.DECISIONS_NAME}, {out / LF.READOUT_NAME}")
    if c["no_answer"] and not args.keep_undecided:
        print(f"NOT WRITTEN: {out / LF.CANDIDATES_NAME}: {c['no_answer']} pairs have no answer; run again with "
              f"--resume, or pass --keep-undecided to keep their candidates as they are", file=sys.stderr)
        return code or 2
    body = "".join(json.dumps({k: asdict(x)[k] for k in CANDIDATE_FIELDS}, ensure_ascii=False) + "\n" for x in fixed)
    atomic_write_text(body, out / LF.CANDIDATES_NAME)
    print(f"wrote {out / LF.CANDIDATES_NAME}: {len(fixed)} candidates ({json.dumps(cc)})")
    print(f"  then: uv run python data_analysis/gap_generation/gap_registry.py submit --from "
          f"{_rel(out / LF.CANDIDATES_NAME)}")
    return code or 0


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH,
                    help="where M1's recorded senses are read (its folded view); default the live log")
    ap.add_argument("--candidates-dir", type=Path, default=None, help="default data/candidates (runs under runs/)")
    ap.add_argument("--rubrics-dir", type=Path, default=None, help="default reports/trait_gap_generation/rubrics")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out-dir", type=Path, default=None)
        p.add_argument("--model", default=LF.DEFAULT_MODEL, help=f"one of {', '.join(LF.MODELS)}")
        p.add_argument("--readings", type=int, default=LF.DEFAULT_READINGS,
                       help="answers per pair, combined by majority (a tie does not fit); default 3")
        p.add_argument("--embedder", default="bge", choices=("bge", "gemma", "openai", "hash", "none"),
                       help="the free cosine pre-screen's arm (default the local bge; none skips it)")
        p.add_argument("--embed-cache-dir", type=Path, default=None)
        p.add_argument("--screen-floor", type=float, default=None,
                       help="a pair whose usual-sense cosine reaches this is taken as fitting with no call (default "
                            "none: the cosines are only reported)")
        p.add_argument("--no-oewn", action="store_true", help="show no dictionary senses")
        p.add_argument("--no-registry", action="store_true", help="show no M1 senses (as for words not yet submitted)")
        p.add_argument("--limit", type=int, default=None, help="only the first N pairs (a pilot)")
        p.add_argument("--concurrency", type=int, default=LF.CONCURRENCY)
        p.add_argument("--render", action="store_true", help="print the system turn and one user turn per variant")
        p.add_argument("--resume", action="store_true",
                       help="reuse the answers on record (by request sha, reading and model)")
        p.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD, help="hard cap on this run's calls")
        p.add_argument("--confirm-expensive", action="store_true")
        p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for anything over $20")
        p.add_argument("--allow-dirty", action="store_true",
                       help="run although the platform's own code or prompt paths have uncommitted changes")
        p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("validate", help="score the check against a precision sheet's marks (paid)")
    p.add_argument("--marks", type=Path, required=True, help="the sheet (roger_sample.md), Roger's marks in its last "
                                                             "column")
    p.add_argument("--borderline", nargs="+", default=[], metavar="LABEL",
                   help="labels also left out of a second confusion table (e.g. flashy self-justifying)")
    common(p)
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("check", help="check a run's candidates before submission; write the corrected file (paid)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", metavar="GENERATOR/RUN_ID")
    g.add_argument("--candidates", type=Path)
    p.add_argument("--keep-undecided", action="store_true",
                   help="write the corrected file although some pairs have no answer (their candidates unchanged)")
    common(p)
    p.set_defaults(func=cmd_check)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.readings < 1:
        raise SystemExit("--readings must be at least 1")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
