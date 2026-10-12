#!/usr/bin/env python3
"""The masked-LM template-fill generator (workstream 4, generator id ``masked_lm``).

    uv run python data_analysis/gap_generation/masked_lm_generator.py census [--queue] [--models roberta] [--dry-run]
    uv run python data_analysis/gap_generation/masked_lm_generator.py record-model --approved-by 'Roger, <date>'
        [--models roberta] [--dry-run]
    uv run python data_analysis/gap_generation/masked_lm_generator.py generate
        --passes single,probe,subword,multiword,variant_b [--frames all|pilot10] [--subjects she,he,...]
        [--top-rank 2000] [--k-first 100] [--k-first-multi 50] [--beam-width 3] [--subword-widths 2,3,4]
        [--words-limit N] [--pll-mode l2r|original] [--models roberta] [--device mps|cpu|auto] [--batch-size 64]
        [--dry-run]
    uv run python data_analysis/gap_generation/masked_lm_generator.py score [--top 10000] [--models roberta]
        [--device mps] [--dry-run]
    uv run python data_analysis/gap_generation/masked_lm_generator.py table [--dry-run]
    uv run python data_analysis/gap_generation/masked_lm_generator.py evaluate [--cutoffs 1000,2000,5000,10000,20000]
        [--dry-run]
    uv run python data_analysis/gap_generation/masked_lm_generator.py submit --run-id R (--top N | --kept-target 300
        [--kept-share S] [--multi-cap N]) [--count-registered] [--transport live|batches] [--budget-usd 5]
        [--confirm-expensive --confirmed-by WHO] [--dry-run]

The common flags (``--models``, ``--frames``, ``--device``, ``--batch-size``, ``--pll-mode``) go before the command
(they are accepted after it too).  ``--pll-mode`` is left out normally: each pass then runs in its own mode
(QUESTIONS 90: left to right for single, probe, subword, Variant B and the contrast score; the plan's original form
for multiword); given, it sets every pass.  The subword pass's widths are per model (QUESTIONS 89: roberta and
ModernBERT 2-4 blanks, bert-wwm 2-6); ``--subword-widths`` overrides them.
    uv run python data_analysis/gap_generation/masked_lm_generator.py report --run-id R [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_04_masked_lm.md``.  ``census`` counts the corpus's labels (and the
seed queue's, with ``--queue``) by how each model's tokenizer splits them (tokenizer files only).
``record-model`` verifies a downloaded model against the Hub's published hashes and records it (the model is
downloaded by ``setup_external.py --hf-model <id>``, each on Roger's word; only roberta-large is approved).
``generate`` runs the local passes and stores per-model, per-pass aggregates in the gitignored cache;
``score`` the trait-hood contrast score; ``table`` builds ``mlm_table.jsonl``; ``evaluate`` the recovery curves,
the wordfreq baseline, the frame ablation, the HHH probe, the contrast AUC and the coverage count.  ``submit``
writes a run's ``candidates.jsonl`` and submits it, gated on the downstream (M1 + M3) estimate; ``report`` reads
a run's M1 and M3 results back.

No command but ``submit`` touches the registry, and none makes a paid call: the generator is a local model ($0);
M1 and M3 are the platform's CLIs, printed by ``submit``.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import masked_lm as G  # noqa: E402
from assistant_axis.gapgen.generators.masked_lm import frames as F  # noqa: E402
from assistant_axis.gapgen.generators.masked_lm import models as M  # noqa: E402

PASSES = ("single", "probe", "subword", "multiword", "variant_b")
#: The CPU rate measured here on 2026-10-12 (roberta-large, float32, batch 64, ~10-token sequences): the dry run's
#: time estimate.  MPS is faster; ``generate`` prints and records the rate it actually got.
CPU_FORWARD_PER_SECOND = 340.0


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


# ---------------------------------------------------------------------------- seams (tests replace these)

def _tokenizer(key: str, args):
    return M.load_tokenizer(key, cache_dir=args.hf_dir)


def _load_mlm(key: str, args):  # pragma: no cover - the real model
    return M.load_mlm(key, args.device, cache_dir=args.hf_dir, batch_size=args.batch_size)


def _lemmatizer():  # pragma: no cover - the OEWN database
    from assistant_axis.gapgen.generators.masked_lm.singlemask import default_lemmatizer
    return default_lemmatizer()


def _universe():  # pragma: no cover - the OEWN database
    from assistant_axis.gapgen.generators.masked_lm.wordlist import oewn_candidates
    return oewn_candidates()


def _zipf():  # pragma: no cover - wordfreq
    from assistant_axis.gapgen.freq import zipf_info
    return lambda w: zipf_info(w).zipf_min


def _lookups(tokenizer):  # pragma: no cover - wordfreq and the OEWN database
    from assistant_axis.gapgen.generators.masked_lm.table import default_lookups
    return default_lookups(tokenizer)


def _present(key: str, args) -> bool:
    return M.model_present(key, args.hf_dir)


# ---------------------------------------------------------------------------- census

def _labels(args):
    from assistant_axis.gapgen.generators.masked_lm.evaluate import corpus_labels, queue_labels
    corpus = corpus_labels(args.data_dir)
    queue = queue_labels(args.queue_path or Path(args.data_dir) / "seed_queue.json")
    return corpus, queue


def cmd_census(args) -> int:
    from assistant_axis.gapgen.generators.masked_lm.evaluate import census_payload
    corpus, queue = _labels(args)
    sets = {"corpus": corpus} | ({"queue": queue} if args.queue_census else {})
    out, missing = {}, []
    for key in M.parse_models(args.models):
        if not _present(key, args):
            missing.append(key)
            print(f"{key}: {M.model_missing(key)}", file=sys.stderr)
            continue
        tok = _tokenizer(key, args)
        out[key] = census_payload({k: M.token_census(v, tok) for k, v in sets.items()})
        for s, v in out[key].items():
            print(f"{key} {s}: {v['n']} labels: single {v['single']} ({v['shares']['single']:.1%}), subword "
                  f"{v['subword']} ({v['shares']['subword']:.1%}), multiword {v['multiword']} "
                  f"({v['shares']['multiword']:.1%})")
    if args.dry_run:
        print(f"DRY-RUN: would write {_rel(args.out_dir / 'census.json')}")
        return 0
    if not out:
        return 2
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    env = json_metadata({"census": out, "missing_models": missing, "n_corpus": len(corpus), "n_queue": len(queue)},
                        title="masked-LM generator: tokenizer census")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", args.out_dir / "census.json")
    print(f"wrote {_rel(args.out_dir / 'census.json')}")
    return 0


# ---------------------------------------------------------------------------- record-model

def cmd_record_model(args) -> int:
    keys = M.parse_models(args.models)
    if args.dry_run:
        for k in keys:
            s = M.spec(k)
            print(f"DRY-RUN: would verify {s.hf_id} @ {s.revision[:8]} (~{s.approx_gb} GB, {s.licence}; "
                  f"{'present' if _present(k, args) else 'NOT downloaded: ' + M.model_missing(k)}) and merge its "
                  f"entry into {_rel(args.sources_manifest)}")
        return 0
    if not (args.approved_by and args.approved_by.strip()):
        print("refused: record Roger's approval with --approved-by '<Roger, date>' (plan section 1)", file=sys.stderr)
        return 2
    entries = []
    for k in keys:
        if not _present(k, args):
            print(M.model_missing(k), file=sys.stderr)
            return 2
        entries.append(M.record_model(k, approved_by=args.approved_by, cache_dir=args.hf_dir))
    from assistant_axis.atomic_io import atomic_write_text
    cur = {e["key"]: e for e in (json.loads(args.sources_manifest.read_text()) if args.sources_manifest.exists()
                                 else [])}
    for e in entries:
        cur[e["key"]] = e
    order = list(M.MODELS)
    args.sources_manifest.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(sorted(cur.values(), key=lambda e: order.index(e["key"])), indent=2) + "\n",
                      args.sources_manifest)
    print(f"wrote {_rel(args.sources_manifest)}")
    return 0 if all(e["checksum_verified"] and e["licence_verified"] for e in entries) else 1


# ---------------------------------------------------------------------------- generate

def _subjects(args) -> Optional[list[str]]:
    if not args.subjects:
        return None
    keys = [s.strip() for s in args.subjects.split(",") if s.strip()]
    bad = [k for k in keys if k not in F.SUBJECT_BY_KEY]
    if bad:
        raise SystemExit(f"unknown subjects {bad} (one of {', '.join(F.SUBJECT_BY_KEY)})")
    return keys


def _mode_source(args) -> str:
    """Where a pass's PLL mode came from (recorded beside ``pll_mode`` in its meta)."""
    return f"--pll-mode {args.pll_mode}" if args.pll_mode else "per-pass default (QUESTIONS 90)"


def _words_subset(words: Sequence[str], limit: Optional[int]) -> list[str]:
    """A deterministic spread of ``limit`` words (every k-th), for smoke runs."""
    if not limit or limit >= len(words):
        return list(words)
    step = len(words) / float(limit)
    return [words[int(i * step)] for i in range(limit)]


def _widths(args, key: str) -> tuple[int, ...]:
    """The subword pass's widths: ``--subword-widths`` when given, else the model's (QUESTIONS 89)."""
    if not getattr(args, "subword_widths", None):
        return F.subword_widths(key)
    ws = tuple(int(x) for x in str(args.subword_widths).split(",") if x.strip())
    if not ws or min(ws) < 2:
        raise SystemExit(f"--subword-widths takes widths of 2 or more, got {args.subword_widths!r}")
    return ws


def _plan_passes(args, mask_token: str, universe_n: Optional[int], key: str = M.PRIMARY_MODEL) -> dict:
    """What each pass would run: instance counts and forward passes (the dry run's estimate; a beam's forward
    passes are an upper bound, since a branch whose top pieces break the constraint dies), and its PLL mode."""
    from assistant_axis.gapgen.generators.masked_lm.pll import pass_mode
    subs = _subjects(args)
    gen = F.generation_frames(args.frames)
    out = {}
    for p in args.passes:
        if p == "single":
            n = len(F.instances(gen, mask_token, subjects=subs))
            out[p] = {"instances": n, "forward": n}
        elif p == "probe":
            n = len(F.instances(F.PROBE_FRAMES, mask_token, subjects=subs))
            out[p] = {"instances": n, "forward": n}
        elif p == "subword":
            k, b = args.k_first, args.beam_width
            ws = _widths(args, key)
            # a run of w blanks: the all-masked pass, then k first pieces, each branch growing by up to b a blank
            fw = len(gen) * sum(1 + sum(k * b ** j for j in range(w - 1)) for w in ws)
            out[p] = {"instances": len(ws) * len(gen), "widths": list(ws), "forward": fw}
        elif p == "multiword":
            k, b = args.k_first_multi, args.beam_width
            per = sum(1 + (k if len(c) > 1 else 0) + (k * b if len(c) > 2 else 0)
                      for c in F.MULTIWORD_PATTERNS.values())
            out[p] = {"instances": len(F.MULTIWORD_HOSTS) * len(F.MULTIWORD_PATTERNS),
                      "forward": len(F.MULTIWORD_HOSTS) * per}
        elif p == "variant_b":
            nw = min(universe_n or 0, args.words_limit or (universe_n or 0))
            n_inst = len(F.VARIANT_B_INSTANCES)
            out[p] = {"instances": n_inst, "words": nw, "forward": int(nw * n_inst * 2.0) + n_inst,
                      "note": "about 2 pieces a word"}
    for p, v in out.items():
        v["minutes_at_cpu_rate"] = round(v["forward"] / CPU_FORWARD_PER_SECOND / 60.0, 1)
        v["pll_mode"] = pass_mode(p, args.pll_mode)
    return out


def cmd_generate(args) -> int:
    from assistant_axis.gapgen.generators.masked_lm import beam as BM
    from assistant_axis.gapgen.generators.masked_lm import pll as P
    from assistant_axis.gapgen.generators.masked_lm import singlemask as S
    args.passes = [p.strip() for p in args.passes.split(",") if p.strip()]
    bad = [p for p in args.passes if p not in PASSES]
    if bad:
        raise SystemExit(f"unknown passes {bad} (one of {', '.join(PASSES)})")
    keys = M.parse_models(args.models)
    universe = _universe() if "variant_b" in args.passes else None
    if args.dry_run:
        for key in keys:
            plan = _plan_passes(args, F.SLOT, len(universe) if universe is not None else None, key)
            print(f"DRY-RUN {key} ({'present' if _present(key, args) else 'NOT downloaded'}), frames {args.frames}, "
                  f"device {args.device}:")
            for p, v in plan.items():
                print(f"  {p}: {json.dumps(v)}")
            print(f"  total forward passes {sum(v['forward'] for v in plan.values()):,}, about "
                  f"{sum(v['minutes_at_cpu_rate'] for v in plan.values()):.1f} min at the CPU rate "
                  f"({CPU_FORWARD_PER_SECOND:.0f}/s; MPS is faster); would write "
                  f"{_rel(args.agg_dir / key)}/<pass>.jsonl and .meta.json")
        if universe is not None:
            print(f"  variant B universe: {len(universe):,} OEWN words"
                  + (f" (limited to {args.words_limit})" if args.words_limit else ""))
        return 0
    lem = _lemmatizer()
    subs = _subjects(args)
    for key in keys:
        if not _present(key, args):
            print(M.model_missing(key), file=sys.stderr)
            return 2
        mlm = _load_mlm(key, args)
        groups = S.build_word_groups(mlm.tok, lem)
        mask = mlm.tok.mask_token
        gen = F.generation_frames(args.frames)
        for p in args.passes:
            if p == "single":
                res = S.run_single_pass(mlm, F.instances(gen, mask, subjects=subs), top_rank=args.top_rank,
                                        lemmatize=lem, groups=groups, pll_mode=args.pll_mode, batch=args.batch_size)
            elif p == "probe":
                res = S.run_single_pass(mlm, F.instances(F.PROBE_FRAMES, mask, subjects=subs), top_rank=args.top_rank,
                                        lemmatize=lem, groups=groups, pass_name="probe", pll_mode=args.pll_mode,
                                        batch=args.batch_size)
            elif p == "subword":
                res = BM.subword_pass(mlm, gen, k_first=args.k_first, widths=_widths(args, key),
                                      beam_width=args.beam_width, lemmatize=lem, pll_mode=args.pll_mode)
            elif p == "multiword":
                res = BM.multiword_pass(mlm, k_first=args.k_first_multi, beam_width=args.beam_width, lemmatize=lem,
                                        pll_mode=args.pll_mode)
            else:
                mode = P.pass_mode("variant_b", args.pll_mode)
                words = _words_subset(universe, args.words_limit)
                insts = F.pairs_to_instances(F.VARIANT_B_INSTANCES, mask)
                ckey = P.checkpoint_key([i.text for i in insts], mode, key, mlm.revision)
                ck = args.agg_dir / key / f"variant_b.{ckey}.partial.jsonl"
                res = P.variant_b(mlm, words, top_rank=args.top_rank, groups=groups, lemmatize=lem,
                                  mode=mode, checkpoint=ck)
                res.meta["universe_size"] = len(universe)
                res.meta["words_limit"] = args.words_limit
            res.meta["pll_mode_source"] = _mode_source(args)
            res.meta["frames_arg"] = args.frames
            res.meta["subjects_arg"] = subs
            res.meta["git_sha"] = _git_sha()
            data, meta = S.write_pass(res, args.agg_dir)
            print(f"wrote {_rel(data)} ({len(res.aggs)} words) and {_rel(meta)}")
    return 0


# ---------------------------------------------------------------------------- score

def _passes(args):
    from assistant_axis.gapgen.generators.masked_lm.singlemask import load_all_passes
    return load_all_passes(args.agg_dir)


def _provisional_union(passes) -> list[str]:
    """Surfaced words across the generation passes (the table's union; the probe's frames are not one), best
    log-probability first: what ``score`` scores, before the table exists."""
    from assistant_axis.gapgen.generators.masked_lm.table import GENERATION_PASSES
    best: dict[str, float] = {}
    for key, p in passes.items():
        if key.split(":", 1)[0] not in GENERATION_PASSES:
            continue
        for w, a in p.aggs.items():
            a = a.as_dict() if hasattr(a, "as_dict") else a
            if int(a.get("n_top") or 0) < 1:
                continue
            s = a.get("surface") or w
            best[s] = max(best.get(s, -1e9), float(a["best_logprob"]))
    return [w for w, _ in sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))]


def cmd_score(args) -> int:
    from assistant_axis.gapgen.generators.masked_lm import pll as P
    from assistant_axis.gapgen.generators.masked_lm.evaluate import (
        CONTRAST_NEGATIVES, contrast_positives, demographic_labels,
    )
    from assistant_axis.gapgen.generators.masked_lm.singlemask import PassResult, base_meta, write_pass
    passes = _passes(args)
    union = _provisional_union(passes)
    top = union[:args.top] if args.top else union
    corpus, _ = _labels(args)
    auc_set = contrast_positives(corpus, exclude=demographic_labels(corpus, args.regions)) + list(CONTRAST_NEGATIVES)
    words = list(dict.fromkeys(top + auc_set))
    n_inst = len(F.CONTRAST_SET) * len(F.CONTRAST_SUBJECTS)
    if args.dry_run:
        print(f"DRY-RUN: would score {len(words):,} words ({len(top):,} of the {len(union):,} surfaced, plus the "
              f"{len(auc_set)} words of the AUC check) in {n_inst} contrast instances per model "
              f"({', '.join(M.parse_models(args.models))}): about {len(words) * n_inst * 2:,} forward passes, "
              f"{len(words) * n_inst * 2 / CPU_FORWARD_PER_SECOND / 60:.1f} min at the CPU rate; would write "
              f"{_rel(args.agg_dir)}/<model>/contrast.jsonl")
        return 0
    if not passes:
        print(f"no aggregates under {_rel(args.agg_dir)}: run `generate` first", file=sys.stderr)
        return 2
    for key in M.parse_models(args.models):
        if not _present(key, args):
            print(M.model_missing(key), file=sys.stderr)
            return 2
        mlm = _load_mlm(key, args)
        mode = P.pass_mode("contrast", args.pll_mode)
        insts = P.contrast_instances(mlm.tok.mask_token)
        ckey = P.checkpoint_key([i.text for i in insts], mode, key, mlm.revision)
        ck = args.agg_dir / key / f"contrast.{ckey}.partial.jsonl"
        import time
        t0 = time.time()
        con = P.score_words(words, model_key=key, mlm=mlm, mode=mode, checkpoint=ck)
        meta = base_meta(mlm, "contrast", pll_mode=mode, top=args.top, frames=list(F.CONTRAST_SET),
                         subjects=list(F.CONTRAST_SUBJECTS))
        meta.update({"n_words": len(words), "seconds": round(time.time() - t0, 2), "n_auc_set": len(auc_set),
                     "git_sha": _git_sha(), "pll_mode_source": _mode_source(args)})
        res = PassResult("contrast", key, {w: {"word": w, **c.as_dict()} for w, c in con.items()}, meta)
        data, m = write_pass(res, args.agg_dir)
        print(f"wrote {_rel(data)} ({len(con)} words) and {_rel(m)}")
    return 0


def _contrasts(args) -> dict:
    from assistant_axis.gapgen.generators.masked_lm.singlemask import load_pass
    out = {}
    root = Path(args.agg_dir)
    for d in sorted(root.iterdir()) if root.exists() else []:
        r = load_pass(root, d.name, "contrast")
        if r is not None:
            out[d.name] = r.aggs
    return out


# ---------------------------------------------------------------------------- table

def _corpus_queue_stems(args):
    from assistant_axis.gapgen.generators.censuses.corpus import corpus_trait_stems, queue_trait_stems
    return corpus_trait_stems(args.data_dir), queue_trait_stems(args.queue_path, data_dir=args.data_dir)


def _primary_tokenizer(args):
    key = M.PRIMARY_MODEL
    return _tokenizer(key, args) if _present(key, args) else None


def cmd_table(args) -> int:
    from assistant_axis.gapgen.generators.masked_lm import table as T
    passes = _passes(args)
    if not passes:
        print(f"no aggregates under {_rel(args.agg_dir)}: run `generate` first", file=sys.stderr)
        return 2
    corpus, queue = _corpus_queue_stems(args)
    rows = T.build_table(passes, lookups=_lookups(_primary_tokenizer(args)), corpus_stems=corpus,
                         queue_stems=queue, contrasts=_contrasts(args))
    counts = T.table_counts(rows)
    print(json.dumps(counts))
    path = args.out_dir / "mlm_table.jsonl"
    gen_path = args.out_dir / "generation.json"
    if args.dry_run:
        print(f"DRY-RUN: would write {_rel(path)} ({len(rows)} rows) and {_rel(gen_path)}")
        return 0
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.provenance import current_file_input
    backup = T.write_table(rows, path)
    metas = {k: {x: p.meta.get(x) for x in ("pass", "model_key", "model", "revision", "device", "versions",
                                             "frame_bank_sha256", "settings", "seconds", "n_forward", "at",
                                             "frames_arg", "subjects_arg", "git_sha", "words_limit",
                                             "universe_size", "pll_mode_source")}
             | {"pll_mode": p.meta.get("pll_mode") or (p.meta.get("settings") or {}).get("pll_mode")}
             for k, p in sorted(passes.items())}
    inputs = [current_file_input(dep_key=f"agg_{k.replace(':', '_')}", path=pp) for k in passes
              for pp in (args.agg_dir / k.split(":")[1] / f"{k.split(':')[0]}.jsonl",) if pp.exists()]
    env = json_metadata({"passes": metas, "counts": counts, "table_sha256": T.file_sha256(path)},
                        title="masked-LM generator: what generated the table", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", gen_path)
    print(f"wrote {_rel(path)} ({len(rows)} rows, sha256 {T.file_sha256(path)[:16]}...)"
          + (f"; previous table kept as {_rel(backup)}" if backup else "") + f" and {_rel(gen_path)}")
    return 0


# ---------------------------------------------------------------------------- evaluate

def cmd_evaluate(args) -> int:
    from assistant_axis.gapgen.generators.masked_lm import evaluate as E
    from assistant_axis.gapgen.generators.masked_lm import report as R
    from assistant_axis.gapgen.generators.masked_lm import table as T
    path = args.out_dir / "mlm_table.jsonl"
    if not path.exists():
        print(f"missing {_rel(path)}: run `table` first", file=sys.stderr)
        return 2
    table = T.load_mlm_table(path)
    passes = _passes(args)
    corpus, queue = _labels(args)
    tok = _primary_tokenizer(args)
    classes = E.classify(list(dict.fromkeys(corpus + queue)), tok)
    census_path = args.out_dir / "census.json"
    census = None
    if census_path.exists():
        d = json.loads(census_path.read_text(encoding="utf-8"))
        census = (d.get("result") or d).get("census")
    contrasts = (_contrasts(args) or {}).get(M.PRIMARY_MODEL) or {}
    cutoffs = [int(x) for x in args.cutoffs.split(",")]
    ev = E.build_evaluation(table=table, passes=passes, label_sets={"corpus": corpus, "queue": queue},
                            classes=classes, cutoffs=cutoffs, universe=_universe(), zipf=_zipf(),
                            contrasts=contrasts, corpus_for_auc=corpus,
                            auc_exclude=E.demographic_labels(corpus, args.regions), census=census, title=args.title,
                            note=args.note)
    ev["table_sha256"] = T.file_sha256(path)     # the table is gitignored (QUESTIONS 80); a rebuild checks this
    files = {"the table": path, "the evaluation (JSON)": args.out_dir / "evaluation.json",
             "the recovery curves": args.out_dir / "recovery_curves.png",
             "the HHH probe": args.out_dir / "hhh_probe.md", "the spot check": args.out_dir / "roger_sample.md",
             "what generated the table": args.out_dir / "generation.json"}
    md = R.render_report(ev, doc_path=args.out_dir / "readout.md", files=files)
    probe_md = R.render_hhh_probe(ev, doc_path=args.out_dir / "hhh_probe.md")
    s = ev["recovery"]
    print(f"union {ev['n_union']} rows, {ev['n_eligible']} eligible; recovery {json.dumps(s)}")
    print(f"HHH probe: winning families {ev['hhh_probe']['winning_families']}, ranks {ev['hhh_probe']['ranks']}")
    print(f"contrast AUC {ev['contrast_auc']}")
    if args.dry_run:
        print(md)
        print(f"DRY-RUN: would write {', '.join(_rel(p) for p in files.values() if p != path)}")
        return 0
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.provenance import current_file_input
    inputs = [current_file_input(dep_key=k, path=p) for k, p in
              (("mlm_table", path), ("census", census_path), ("generation", args.out_dir / "generation.json"))
              if Path(p).exists()]
    env = json_metadata(ev, title=f"masked-LM generator evaluation{': ' + args.title if args.title else ''}",
                        inputs=inputs)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", args.out_dir / "evaluation.json")
    E.plot_recovery_curves(ev, args.out_dir / "recovery_curves.png", inputs=inputs)
    atomic_write_text(md, args.out_dir / "readout.md")
    atomic_write_text(probe_md, args.out_dir / "hhh_probe.md")
    novel = [r for r in table if 1000 <= r["union_rank"] <= 5000 and not r.get("corpus_stem_match")
             and not r.get("queue_stem_match") and r.get("eligible")]
    head = [r for r in table if r["union_rank"] <= 500 and r.get("eligible")]
    sample = R.roger_sample(novel, title="Spot check, union ranks 1,000-5,000 not in our list") + "\n" + \
        R.roger_sample(head, title="Spot check, union ranks 1-500 (for comparison)")
    atomic_write_text(sample, args.out_dir / "roger_sample.md")
    print(f"wrote {', '.join(_rel(p) for p in files.values() if p != path)} and {_rel(args.out_dir / 'readout.md')}")
    return 0


# ---------------------------------------------------------------------------- submit / report

def _registry_stems(args) -> tuple[set[str], set[str]]:
    """``(stems in the registry, those M1 or M3 has still to decide)``."""
    from assistant_axis.gapgen.generators.masked_lm.submit import registry_stems
    from assistant_axis.gapgen.registry import Registry
    if not args.registry.exists():
        return set(), set()
    return registry_stems(Registry(args.registry).fold())


def cmd_submit(args) -> int:
    from assistant_axis.gapgen.generators.masked_lm import submit as SB
    from assistant_axis.gapgen.generators.masked_lm import table as T
    path = args.out_dir / "mlm_table.jsonl"
    if not path.exists():
        print(f"missing {_rel(path)}: run `table` first", file=sys.stderr)
        return 2
    if (args.top is None) == (args.kept_target is None):
        print("give exactly one of --top N (the pilot) and --kept-target K (the wave)", file=sys.stderr)
        return 2
    gen_path = args.out_dir / "generation.json"
    generation = None
    if gen_path.exists():
        d = json.loads(gen_path.read_text(encoding="utf-8"))
        generation = (d.get("result") or d).get("passes")
    uncut = tuple(x.strip() for x in args.uncut_classes.split(",") if x.strip())
    registered, pending = _registry_stems(args)
    try:
        SB.run_submit(args.run_id, table=T.load_mlm_table(path), top_n=args.top, kept_target=args.kept_target,
                      kept_share=args.kept_share, multi_cap=args.multi_cap, uncut=uncut,
                      registered_stems=registered, pending_stems=pending, count_registered=args.count_registered,
                      budget_usd=args.budget_usd, confirm_expensive=args.confirm_expensive,
                      confirmed_by=args.confirmed_by, transport=args.transport, dry_run=args.dry_run,
                      registry_path=args.registry, candidates_dir=args.candidates_dir, table_path=Path(_rel(path)),
                      table_sha256=T.file_sha256(path), generation=generation)
    except SB.ReviewLoadExceeded as exc:
        print(f"refused (review load): {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_report(args) -> int:
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.masked_lm import evaluate as E
    from assistant_axis.gapgen.generators.masked_lm import report as R
    from assistant_axis.gapgen.generators.masked_lm import table as T
    from assistant_axis.gapgen.generators.masked_lm.submit import batch_id_for
    from assistant_axis.gapgen.registry import Registry
    from assistant_axis.provenance import current_file_input
    rdir = paths.run_dir(G.GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
    if not (rdir / "candidates.jsonl").exists():
        print(f"no run at {_rel(rdir)} (no candidates.jsonl)", file=sys.stderr)
        return 2
    table_p = args.out_dir / "mlm_table.jsonl"
    table = T.load_mlm_table(table_p) if table_p.exists() else []
    reg = Registry(args.registry).fold() if args.registry.exists() else {}
    cdir = args.candidates_dir or paths.DATA_CANDIDATES
    b = batch_id_for(args.run_id)
    fdir, ndir = paths.filter_dir(b, candidates_dir=cdir), paths.novelty_dir(b, candidates_dir=cdir)
    ev = E.evaluate_run(args.run_id, run_dir=rdir, table=table, registry_rows=reg, filter_dir=fdir, novelty_dir=ndir)
    doc = rdir / "report.md"
    md = R.render_wave_report(ev, doc_path=doc, run_dir=rdir, table_path=table_p, filter_dir=fdir, novelty_dir=ndir)
    by_stem = {r["stem"]: r for r in table if r.get("stem")}
    survivors = [by_stem[r["stem"]] for r in E.run_rows(reg, args.run_id)
                 if (r.get("filter") or {}).get("verdict") == "trait" and r["stem"] in by_stem]
    if not survivors:      # before M1: the submitted rows
        from assistant_axis.gapgen import normalize_candidate
        stems = [normalize_candidate(json.loads(x)["surface"]).stem
                 for x in (rdir / "candidates.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        survivors = [by_stem[s] for s in stems if s in by_stem]
    pool = survivors
    sample = R.roger_sample(pool, title=f"Spot check of run {args.run_id}")
    if args.dry_run:
        print(md)
        print(f"DRY-RUN: would write {_rel(rdir / 'evaluation.json')}, {_rel(doc)} and "
              f"{_rel(rdir / 'roger_sample.md')}")
        return 0
    inputs = [current_file_input(dep_key=k, path=p) for k, p in
              (("table", table_p), ("candidates", rdir / "candidates.jsonl"), ("run_json", rdir / "run.json"),
               ("registry", args.registry)) if Path(p).exists()]
    env = json_metadata(ev, title=f"masked-LM generator run {args.run_id}", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", rdir / "evaluation.json")
    atomic_write_text(md, doc)
    atomic_write_text(sample, rdir / "roger_sample.md")
    print(f"wrote {_rel(rdir / 'evaluation.json')}, {_rel(doc)}, {_rel(rdir / 'roger_sample.md')}")
    return 0


# ---------------------------------------------------------------------------- parser

def _common_flags(ap: argparse.ArgumentParser, *, top: bool) -> None:
    """The plan's common flags, accepted before or after the command (after it, they default to ``SUPPRESS`` so
    the value given before the command, or the default, stands)."""
    d = (lambda v: v) if top else (lambda v: argparse.SUPPRESS)
    ap.add_argument("--models", default=d(M.PRIMARY_MODEL),
                    help=f"comma-separated, of {', '.join(M.MODELS)} (only roberta is downloaded and approved)")
    ap.add_argument("--frames", default=d("all"), choices=("all", "pilot10"))
    ap.add_argument("--device", default=d("mps"), choices=("mps", "cpu", "auto"),
                    help="mps (refused when Metal sees no device, as inside the Claude Code sandbox), cpu, auto")
    ap.add_argument("--batch-size", type=int, default=d(64))
    ap.add_argument("--pll-mode", default=d(None), choices=("l2r", "original"),
                    help="pseudo-log-likelihood for every pass: l2r (a split word's later pieces masked too) or "
                         "original (the plan's).  Default: each pass its own (QUESTIONS 90): l2r for single, probe, "
                         "subword, variant_b and the contrast score, original for multiword")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (evaluation only)")
    ap.add_argument("--queue-path", type=Path, default=None, help="seed queue (default <data-dir>/seed_queue.json)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--out-dir", type=Path, default=G.MLM_DIR,
                    help="tracked outputs: table, evaluation, curves, probe page (default data/candidates/masked_lm)")
    ap.add_argument("--agg-dir", type=Path, default=G.AGG_DIR,
                    help="per-model, per-pass aggregates (default data/candidates/cache/masked_lm/agg; gitignored)")
    ap.add_argument("--sources-manifest", type=Path, default=G.SOURCES_MANIFEST_PATH)
    ap.add_argument("--regions", type=Path, default=paths.CORPUS_REGIONS_PATH,
                    help="corpus_regions.json (the contrast check leaves the identity_demographic track out)")
    ap.add_argument("--hf-dir", type=Path, default=None, help="Hub cache (default data/external/hf)")
    _common_flags(ap, top=True)
    common = argparse.ArgumentParser(add_help=False)
    _common_flags(common, top=False)
    sub = ap.add_subparsers(dest="cmd", required=True)
    _add = sub.add_parser
    sub.add_parser = lambda *a, **kw: _add(*a, parents=[common], **kw)   # the common flags after the command too

    p = sub.add_parser("census", help="corpus (and queue) labels by tokenization (tokenizer files only; $0)")
    p.add_argument("--queue", dest="queue_census", action="store_true", help="also the seed queue's trait labels")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_census)

    p = sub.add_parser("record-model", help="verify a downloaded model and record it in the sources manifest")
    p.add_argument("--approved-by", default=None, help="Roger's approval of the download, copied into the manifest")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_record_model)

    p = sub.add_parser("generate", help="the local passes ($0); aggregates into the cache")
    p.add_argument("--passes", default="single,probe")
    p.add_argument("--subjects", default=None, help="comma-separated subject keys (default all ten)")
    p.add_argument("--top-rank", type=int, default=2000)
    p.add_argument("--k-first", type=int, default=100,
                   help="subword pass: first-slot pieces (default 100: reduced from the plan's 300, Roger's "
                        "2026-10-10 decision keeps the beams as the off-list complement of Variant B)")
    p.add_argument("--k-first-multi", type=int, default=50, help="multiword pass: first-slot pieces (plan 100)")
    p.add_argument("--beam-width", type=int, default=3)
    p.add_argument("--subword-widths", default=None,
                   help="subword pass: comma-separated runs of blanks (default per model, QUESTIONS 89: roberta "
                        "and modernbert 2,3,4; bert_wwm 2,3,4,5,6)")
    p.add_argument("--words-limit", type=int, default=None,
                   help="variant B: score a deterministic spread of this many universe words (smoke runs)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("score", help="the trait-hood contrast score of the surfaced words ($0)")
    p.add_argument("--top", type=int, default=10000, help="the first N surfaced words (0: all)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("table", help="build mlm_table.jsonl ($0)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_table)

    p = sub.add_parser("evaluate", help="recovery curves, baseline, ablation, HHH probe, AUC, coverage ($0)")
    p.add_argument("--cutoffs", default="1000,2000,5000,10000,20000")
    p.add_argument("--title", default=None, help="a name for the readout (e.g. 'pilot A')")
    p.add_argument("--note", default=None, help="a line printed at the top of the readout")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("submit", help="write a run's candidates.jsonl and submit it (no API cost; gated on the "
                                      "downstream M1 + M3 estimate)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--top", type=int, default=None, help="pilot: the first N eligible rows by union rank")
    p.add_argument("--kept-target", type=int, default=None,
                   help="wave: single words cut where projected kept terms reach this (300 = ~2 h of review)")
    p.add_argument("--kept-share", type=float, default=None,
                   help="kept terms per submitted single word (pilot B's measured share; default the assumed 0.5)")
    p.add_argument("--multi-cap", type=int, default=None,
                   help="wave: at most this many uncut rows, by union rank (needed when the review-load guard refuses)")
    p.add_argument("--uncut-classes", default="multiword",
                   help="wave: token classes exempt from the rank cut (default multiword; multiword,subword is the "
                        "coordinator's literal reading)")
    p.add_argument("--count-registered", action="store_true",
                   help="count stems already in the registry in the rank cut like any row (by default they are "
                        "submitted where they fall inside the cut, merging into their registry rows at no API cost, "
                        "and never counted in it or in the projected kept terms; QUESTIONS 82)")
    p.add_argument("--transport", choices=("live", "batches"), default="live",
                   help="how the platform will run M1 and M3 (batches: half price in the estimate)")
    p.add_argument("--budget-usd", type=float, default=5.0,
                   help="cap on the downstream estimate (M1 + M3); over it the submit is refused")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for an estimate over $20")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("report", help="a run's readout after M1 and M3 ($0)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "kept_share", None) is None and args.cmd == "submit":
        from assistant_axis.gapgen.generators.masked_lm.submit import KEPT_SHARE_ASSUMED
        args.kept_share = KEPT_SHARE_ASSUMED
    try:
        return args.func(args)
    except (FileNotFoundError, RuntimeError) as exc:
        # a model that is not downloaded, or MPS asked for where Metal sees no device: say so, exit 2
        if "setup_external.py" in str(exc) or str(exc) == M.MPS_REFUSAL:
            print(str(exc), file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
