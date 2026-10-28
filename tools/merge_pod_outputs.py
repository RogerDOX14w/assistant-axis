#!/usr/bin/env python3
"""Merge the small outputs of several pods' extraction trees into one tree.

The October extraction runs on four pods, one per type (walk-through P1,
2026-10-12: ``roles``, ``traits``, ``r_combinations``, ``t_combinations``),
each into its own local OUTPUT_DIR with its own step 0 (the default).  Once a
pod's pipeline has passed its scan, the small outputs come together here (the
activations stay on the pods' volumes and are not merged; Roger, 2026-10-13:
copy off the ones to keep before a volume is discarded):

* per type (``roles/``, ``traits/``, ``combinations/``): the response files,
  the score files and the vectors (real files; the ``default`` symlinks are
  made again), ``responses/generation_config.json`` (every pod's runs, each
  marked with its pod, after checking that the pods generated under the same
  settings), ``scores/usage.json`` (summed over the pods, per model),
  ``scores/judge_rubric.json`` (versions, rubric hashes and judge models
  joined; pods that record two hashes or reply formats for one type refuse
  the merge), ``scores/abc_disagreements.jsonl`` (version 10's log of role
  replies whose SCORE line disagreed with their answers; the pods' rows
  joined) and ``scores/_replies/`` (step 3's ``--save_replies``, which
  ``3_judge.py --reread_replies`` needs);
* ``default/``: the default of ``--default_from`` (the first pod by
  default); the other pods' default vectors go to ``default/other_pods/``;
* ``logs/<pod>/``: each pod's ``pipeline_*.log``;
* ``MERGED.json``: what was merged, from where, when, and the counts.

It refuses (exit 1, nothing at ``--dest``) when a stem comes from two pods,
when a pod has batches not collected (``scores/batch_state.json``), when the
pods' generation settings differ, or when an entity a pod's
``generation_config.json`` lists has no response file.  Then it runs the
scanner on the merged tree in root mode (``pipeline/scan_missing_vectors.py
--root``; empty ``activations/`` directories let it find the types, and
every entity with responses must have a vector or a reason not to); its exit
3 (re-run candidates, an entity with neither vector nor reason) refuses the
merge too (exit 3).  The tree is built in ``<dest>.partial`` and renamed to
``--dest`` only when everything passed; a refused build is left there to
inspect.  Afterwards: one step 5 per type on the merged tree (printed).

A pod given as ``NAME=host:/path`` (an rsync source) is first pulled into
``<dest>.pull/NAME`` with ``rsync -a``, leaving out ``activations/``,
``_batches/`` and ``*.inprogress``; ``NAME=/local/dir`` is read in place.

Usage::

    uv run python tools/merge_pod_outputs.py \\
        --pod roles=pods/roles --pod traits=pods/traits \\
        --pod rcomb=pods/rcomb --pod tcomb=pods/tcomb --dest merged/qwen-3-32b
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from assistant_axis.generation import GENERATION_CONFIG_NAME, settings_differences  # noqa: E402
from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402

TYPES = ("roles", "traits", "combinations")
SIDE_CARS = ("usage.json", "judge_rubric.json", "batch_state.json")
ABC_LOG = "abc_disagreements.jsonl"     # pipeline/3_judge.py ABC_LOG_FILENAME
REPLIES = "_replies"                    # pipeline/3_judge.py REPLIES_DIRNAME
EXIT_SCAN = 3
DEFAULT_MIN_COUNT = 30          # run_pipeline.sh's roger-mode MIN_COUNT


class MergeRefused(RuntimeError):
    pass


def _real_files(d: Path, pattern: str) -> List[Path]:
    return sorted(p for p in d.glob(pattern) if p.is_file() and not p.is_symlink())


def pull(name: str, source: str, pull_root: Path) -> Path:
    """An rsync source (``host:/path``) pulled to ``pull_root/name``; a local
    directory as it is."""
    local = Path(source)
    if local.is_dir() or ":" not in source:
        if not local.is_dir():
            raise MergeRefused(f"pod {name}: {source} is not a directory")
        return local
    dest = pull_root / name
    dest.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-a", "--exclude", "activations/", "--exclude", "_batches/",
           "--exclude", "*.inprogress", source.rstrip("/") + "/", str(dest) + "/"]
    print(f"[pull] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return dest


def uncollected(scores_dir: Path) -> List[str]:
    path = scores_dir / "batch_state.json"
    if not path.exists():
        return []
    chunks = json.loads(path.read_text()).get("chunks", [])
    return [Path(r.get("path", "?")).name for r in chunks
            if (r.get("batch_id") or r.get("input_file_id")) and not r.get("collected")]


def plan(pods: Dict[str, Path]) -> Tuple[Dict[str, Dict[str, Path]], List[str]]:
    """``type -> {pod: type dir}`` and the problems found (duplicates,
    uncollected batches, settings that differ, listed entities without a
    response file)."""
    problems: List[str] = []
    by_type: Dict[str, Dict[str, Path]] = {t: {} for t in TYPES}
    for name, root in pods.items():
        if not (root / "default" / "vectors" / "default.pt").is_file():
            problems.append(f"pod {name}: no default/vectors/default.pt (step 0 not run?)")
        found = False
        for t in TYPES:
            d = root / t
            if (d / "responses").is_dir():
                by_type[t][name] = d
                found = True
                left = uncollected(d / "scores")
                if left:
                    problems.append(f"pod {name} {t}: {len(left)} batch(es) not collected "
                                    f"({', '.join(left[:3])}); finish its step 3 first")
        if not found:
            problems.append(f"pod {name}: no {'/, '.join(TYPES)}/ with responses at {root}")
    for t, dirs in by_type.items():
        owner: Dict[str, str] = {}
        dups: List[str] = []
        runs: List[Tuple[str, dict]] = []
        for name, d in dirs.items():
            for f in _real_files(d / "responses", "*.jsonl"):
                if f.stem == "default":
                    continue
                if f.stem in owner:
                    dups.append(f"{f.stem} ({owner[f.stem]}, {name})")
                owner[f.stem] = name
            gc = d / "responses" / GENERATION_CONFIG_NAME
            if gc.exists():
                runs += [(name, r) for r in json.loads(gc.read_text()).get("runs", [])]
            else:
                print(f"[warn] pod {name} {t}: no {GENERATION_CONFIG_NAME}; its entity list "
                      f"and settings cannot be checked")
        if dups:
            problems.append(f"{t}: {len(dups)} stem(s) from two pods: {', '.join(dups[:10])}")
        if runs:
            first_pod, first = runs[0]
            for name, run in runs[1:]:
                diffs = settings_differences(first, run)
                if diffs:
                    problems.append(f"{t}: pod {name} generated under other settings than pod "
                                    f"{first_pod}: {'; '.join(diffs)}")
            listed = {i for _, r in runs for i in (r.get("selection") or {}).get("items", [])}
            missing = sorted(listed - set(owner) - {"default"})
            if missing:
                problems.append(f"{t}: {len(missing)} entit(ies) listed in "
                                f"{GENERATION_CONFIG_NAME} have no response file: "
                                f"{', '.join(missing[:10])}")
    return by_type, problems


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if dst.stat().st_size != src.stat().st_size:
        raise MergeRefused(f"copy of {src} is {dst.stat().st_size} bytes, not {src.stat().st_size}")


def _symlink(dst: Path, target: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() and not dst.is_symlink():
        dst.symlink_to(target)


def build(pods: Dict[str, Path], by_type: Dict[str, Dict[str, Path]], out: Path, *,
          default_from: str) -> dict:
    counts: Dict[str, dict] = {}
    for t, dirs in by_type.items():
        if not dirs:
            continue
        tdir = out / t
        usage = MultiModelUsage()
        rubric = {"rubric_versions": set(), "judge_models": set(), "entity_type": None,
                  "label_form": None, "script": None, "prompt_sha256": {}, "reply_formats": set(),
                  "truncation_markers": set()}
        abc_rows: List[str] = []
        runs = []
        c = {"responses": 0, "scores": 0, "vectors": 0, "pods": sorted(dirs)}
        for name, d in dirs.items():
            for f in _real_files(d / "responses", "*.jsonl"):
                _copy(f, tdir / "responses" / f.name)
                c["responses"] += 1
            for f in _real_files(d / "scores", "*.json"):
                if f.name in SIDE_CARS:
                    continue
                _copy(f, tdir / "scores" / f.name)
                c["scores"] += 1
            for f in _real_files(d / "vectors", "*.pt"):
                _copy(f, tdir / "vectors" / f.name)
                c["vectors"] += 1
            for f in _real_files(d / "scores" / REPLIES, "*.jsonl"):
                _copy(f, tdir / "scores" / REPLIES / f.name)
                c["replies"] = c.get("replies", 0) + 1
            log = d / "scores" / ABC_LOG
            if log.is_file():
                abc_rows += [line for line in log.read_text().splitlines() if line.strip()]
            u = d / "scores" / "usage.json"
            if u.exists():
                usage.merge_from(MultiModelUsage.load_or_create(u))
            rb = d / "scores" / "judge_rubric.json"
            if rb.exists():
                r = json.loads(rb.read_text())
                rubric["rubric_versions"] |= set(r.get("rubric_versions", []))
                rubric["judge_models"] |= set(r.get("judge_models", []))
                for k in ("entity_type", "label_form", "script"):
                    rubric[k] = rubric[k] or r.get(k)
                for v, sha in (r.get("prompt_sha256") or {}).items():
                    if rubric["prompt_sha256"].setdefault(v, sha) != sha:
                        raise MergeRefused(f"{t}: pod {name} judged prompt version {v} with rubric "
                                           f"hash {sha}, another pod with {rubric['prompt_sha256'][v]}")
                if r.get("reply_format"):
                    rubric["reply_formats"].add(r["reply_format"])
                # step 3's --mark_truncated (2026-10-28); a stamp without the field: no marker
                rubric["truncation_markers"].add(r.get("truncation_marker"))
            gc = d / "responses" / GENERATION_CONFIG_NAME
            if gc.exists():
                runs += [{**run, "pod": name} for run in json.loads(gc.read_text()).get("runs", [])]
        (tdir / "scores").mkdir(parents=True, exist_ok=True)
        usage.write_json(tdir / "scores" / "usage.json")
        if len(rubric["reply_formats"]) > 1:
            raise MergeRefused(f"{t}: the pods read replies in several ways: "
                               f"{', '.join(sorted(rubric['reply_formats']))}")
        if len(rubric["truncation_markers"]) > 1:
            raise MergeRefused(f"{t}: the pods judged with and without step 3's --mark_truncated: "
                               f"{', '.join(sorted(repr(m) for m in rubric['truncation_markers']))}")
        if abc_rows:
            (tdir / "scores" / ABC_LOG).write_text("\n".join(abc_rows) + "\n")
            c["abc_disagreements"] = len(abc_rows)
        if rubric["rubric_versions"]:
            versions = sorted(rubric["rubric_versions"])
            (tdir / "scores" / "judge_rubric.json").write_text(json.dumps({
                **{k: rubric[k] for k in ("entity_type", "label_form", "script")},
                "rubric_version": versions[-1], "rubric_versions": versions,
                "judge_models": sorted(rubric["judge_models"]),
                **({"prompt_sha256": rubric["prompt_sha256"]} if rubric["prompt_sha256"] else {}),
                **({"reply_format": next(iter(rubric["reply_formats"]))} if rubric["reply_formats"] else {}),
                "truncation_marker": next(iter(rubric["truncation_markers"]), None),
                "merged_from_pods": sorted(dirs)}, indent=2, sort_keys=True) + "\n")
        if runs:
            (tdir / "responses" / GENERATION_CONFIG_NAME).write_text(
                json.dumps({"schema": 1, "runs": runs}, indent=1) + "\n")
        _symlink(tdir / "responses" / "default.jsonl", "../../default/responses/default.jsonl")
        _symlink(tdir / "vectors" / "default.pt", "../../default/vectors/default.pt")
        (tdir / "activations").mkdir(exist_ok=True)   # the scanner finds types by it
        c["usage_usd"] = round(usage.total_cost_usd, 4)
        counts[t] = c

    src = pods[default_from] / "default"
    dd = out / "default"
    for sub, pattern in (("responses", "*.jsonl"), ("responses", GENERATION_CONFIG_NAME),
                         ("vectors", "*.pt")):
        for f in _real_files(src / sub, pattern):
            _copy(f, dd / sub / f.name)
    (dd / "activations").mkdir(parents=True, exist_ok=True)
    (dd / "scores").mkdir(parents=True, exist_ok=True)
    for name, root in pods.items():
        if name != default_from and (root / "default" / "vectors" / "default.pt").is_file():
            _copy(root / "default" / "vectors" / "default.pt",
                  dd / "other_pods" / name / "default.pt")
    for name, root in pods.items():
        for f in sorted(root.glob("pipeline_*.log")):
            _copy(f, out / "logs" / name / f.name)
    record = {"tool": "tools/merge_pod_outputs.py",
              "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "pods": {n: str(p) for n, p in pods.items()}, "default_from": default_from,
              "counts": counts}
    (out / "MERGED.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def scan(out: Path, min_count: int) -> int:
    cmd = [sys.executable, str(REPO / "pipeline" / "scan_missing_vectors.py"),
           "--root", str(out), "--min_count", str(min_count), "--no_cache"]
    print(f"[scan] {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pod", action="append", required=True, metavar="NAME=DIR",
                    help="One pod's OUTPUT_DIR (a local directory or an rsync source host:/path)")
    ap.add_argument("--dest", type=Path, required=True, help="The merged tree (must not exist)")
    ap.add_argument("--default_from", default=None,
                    help="The pod whose default is kept (default: the first --pod)")
    ap.add_argument("--min_count", type=int, default=DEFAULT_MIN_COUNT,
                    help=f"Passed to the scanner (default {DEFAULT_MIN_COUNT}, the driver's)")
    ap.add_argument("--expect", nargs="*", default=[], metavar="TYPE=N",
                    help="Refuse unless TYPE has exactly N response files (e.g. roles=339)")
    ap.add_argument("--no_scan", action="store_true", help="Skip the scanner (not recommended)")
    args = ap.parse_args(argv)

    if args.dest.exists():
        print(f"merge refused: {args.dest} exists; merge into a new directory", file=sys.stderr)
        return 1
    partial = args.dest.with_name(args.dest.name + ".partial")
    pull_root = args.dest.with_name(args.dest.name + ".pull")
    try:
        pods: Dict[str, Path] = {}
        for spec in args.pod:
            name, _, src = spec.partition("=")
            if not name or not src or name in pods:
                raise MergeRefused(f"bad or repeated --pod {spec!r} (NAME=DIR)")
            pods[name] = pull(name, src, pull_root)
        default_from = args.default_from or next(iter(pods))
        if default_from not in pods:
            raise MergeRefused(f"--default_from {default_from}: no such pod")
        by_type, problems = plan(pods)
        expected = {}
        for e in args.expect:
            t, _, n = e.partition("=")
            expected[t] = int(n)
        if problems:
            raise MergeRefused("\n  ".join(["merge refused:"] + problems))
        if partial.exists():
            shutil.rmtree(partial)
        record = build(pods, by_type, partial, default_from=default_from)
        bad = [f"{t}: {record['counts'].get(t, {}).get('responses', 0)} response files, "
               f"expected {n}" for t, n in expected.items()
               if record["counts"].get(t, {}).get("responses", 0) != n]
        if bad:
            raise MergeRefused("\n  ".join(["merge refused:"] + bad))
    except MergeRefused as e:
        print(str(e), file=sys.stderr)
        return 1

    if not args.no_scan:
        rc = scan(partial, args.min_count)
        if rc == EXIT_SCAN:
            print(f"merge refused: the scan found re-run candidates or entities with neither a "
                  f"vector nor a reason (exit 3; reports in each vectors/ directory of "
                  f"{partial}); the build is left there", file=sys.stderr)
            return EXIT_SCAN
        if rc != 0:
            print(f"merge refused: the scanner exited {rc}; the build is left at {partial}",
                  file=sys.stderr)
            return 1
    partial.rename(args.dest)
    print(f"merged into {args.dest}: " + "; ".join(
        f"{t} {c['responses']} responses / {c['scores']} scores / {c['vectors']} vectors "
        f"from {', '.join(c['pods'])}" for t, c in record["counts"].items()))
    print("Next, step 5 once per type on the merged tree (from pipeline/):")
    for t in record["counts"]:
        print(f"  uv run 5_axis.py --vectors_dir {args.dest / t / 'vectors'} "
              f"--output {args.dest / t / 'axis.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
