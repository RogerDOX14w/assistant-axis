#!/usr/bin/env python3
"""The noun relabel streams and checks (``reports/trait_gap_generation/coding_plan_noun_normalization.md`` section 7).

    uv run python data_analysis/gap_generation/noun_relabel.py [--registry PATH] [--data-dir DIR] <command> ...

The helper itself (:mod:`assistant_axis.gapgen.nouns`) runs inside ``submit_candidates`` for every generator's
submission; this CLI is for what was submitted before it, for the roles, and for poking at the rules.

* ``check WORD ...``: the helper's answer for each word ($0).
* ``backlog [--apply] [--run-id backlog-<date>] [--report PATH]``: every registry row with a single-word label
  through the helper.  Prints the table (relabels by rule; the adjective already a corpus trait, a registry row or
  new; the noun's M1 state; the person nouns left without an adjective, by generator) and, with ``--report``, writes
  it as markdown.  The dry run (the default) writes nothing else.  ``--apply``: the new and existing-row adjectives
  are submitted as ``noun_relabel/<run-id>`` (``candidates.jsonl`` first, then the registry, with
  ``relabel=None``: the stream links its own rows), the ``relabel`` blocks are written on both rows of each pair
  (a corpus-trait adjective: ``to_corpus_stem`` on the noun row only), ``run.json`` (with ``helper_version``,
  ``oewn``, ``rules``, ``counts``, ``registry_snapshot_sha256``), ``usage.json`` ($0) and ``backlog_report.md`` go
  to ``data/candidates/runs/noun_relabel/<run-id>/``, and the follow-up commands (M1 and M3 on the run, the paid
  steps, with their own estimates and caps) are printed.  A row already linked at the current helper version is
  skipped, so a second ``--apply`` does nothing.
* ``roles [--apply] [--run-id roles-<date>] [--report PATH]``: the same for the three role sources: the corpus role
  files (by display name), the seed queue's ``entity_type: "role"`` entries and the registry rows held on the
  roles list.  ``source_ref`` ``relabel:<rule>:role:<stem>`` / ``queue_role:<stem>`` / ``roles_list:<key>``.  Never
  writes a role file, a queue entry or a held row's label: the held row gets the ``to_key`` link only; an adjective
  that is a corpus trait is listed in the report and not submitted.
* ``llm-pilot --n 100 --budget-usd 0.10 [--seed 0] [--dry-run] [--allow-dirty] [--out-dir DIR]`` (open decision 3
  (b), task 9; only on Roger's go): 60 person nouns M1 passed as traits and 40 role nouns that the rules leave
  without an adjective, one Haiku 5.5 call each (the pinned ``noun_relabel`` prompt), the only paid command here.
  The dry run prints the rows, a rendered request and the estimate and writes nothing.  The run refuses on
  uncommitted platform code unless ``--allow-dirty``, charges every response to ``usage.json``, records every
  response before parsing it (``responses.jsonl``) and writes ``readout.md`` with the yield (answers that are an
  OEWN adjective or clear Zipf 1.5; the adopt threshold is 20 of 100) and the full list, to
  ``data/candidates/noun_relabel/llm_pilot_<date>/``.

* ``llm-apply [--budget-usd 0.50] [--run-id llm-<date>] [--dry-run] [--allow-dirty]``: the pilot adopted (yield 24
  of 100; Roger, 2026-10-14, "A 1 yes") as a one-off pass, not a platform step.  The pilot's whole population
  (:func:`pilot_pool`), less the person rows already linked (a ``relabel`` block at this helper version, or any
  earlier LLM relabel); an answer already recorded with the same prompt sha and model (a pilot's or an earlier
  pass's ``responses.jsonl``, not cut off at ``max_tokens``, parseable) is reused, the rest asked by the pilot's call.
  An answer is accepted when it is an OEWN adjective or at Zipf 1.5 or above (the pilot's yield rule, after a
  British spelling is folded to US), the platform accepts its stem and it is not the noun; rejections are counted
  by reason.  The accepted adjectives are written as ``backlog --apply`` writes them, with rule ``llm`` (the blocks
  also carry ``model``, ``prompt_version``, ``confidence`` and ``reason``; the card reads "LLM relabel from
  '<noun>', sense not checked"), to ``data/candidates/runs/noun_relabel/<run-id>/`` with ``responses.jsonl``
  (every response, recorded before it is parsed), ``usage.json`` and ``llm_report.md`` (every answer).  The
  estimate is printed first, ``confirm_or_abort`` holds the cap and an uncommitted platform tree is refused; the
  dry run prints the counts, the estimate and one rendered prompt and writes nothing.  A rerun asks only what has
  no usable answer (an unparsed reply is asked again) and, with every noun answered and linked, sends and writes
  nothing.  A run directory that exists is refused (its answers are reused under a new ``--run-id``).

``--registry`` and ``--data-dir`` default to the live registry and ``data/``; ``--candidates-dir`` (where run
directories go) defaults to the registry's directory.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import nouns as N  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.normalize import make_key, normalize_candidate  # noqa: E402
from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates, utc_now  # noqa: E402

GENERATOR = "noun_relabel"
PILOT_SHARES = {"person": 60, "role": 40}
PILOT_ADOPT_THRESHOLD = 20
#: The plan's per-call token estimate for the pilot (section 7: about 300 input and 60 output tokens).
PILOT_IN_TOKENS, PILOT_OUT_TOKENS = 450, 600   # measured 2026-10-14: about 440 in; thinking output well over 120


def _lookups() -> N.NounLookups:
    """The real lookups (the tests replace this function)."""
    from assistant_axis.gapgen.wordnet import oewn_installed
    if not oewn_installed():
        raise SystemExit("OEWN is not installed in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn` first")
    return N.OewnLookups.default()


def _anthropic_client():
    """The live client of ``llm-pilot`` (the tests replace this function)."""
    from dotenv import load_dotenv
    import anthropic
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _sha256_file(path: Path) -> Optional[str]:
    if not Path(path).exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def m1_state(row: Optional[dict]) -> str:
    """A registry row's M1 state for the tables: ``held_<list>``, the filter's verdict (``trait``, ``tagged``,
    ``reject``), or ``unfiltered``."""
    if row is None:
        return "no_row"
    if row.get("holding"):
        return f"held_{row['holding']}"
    return (row.get("filter") or {}).get("verdict") or "unfiltered"


def _generators(row: dict) -> list[str]:
    return sorted({s.get("generator") for s in row.get("sources") or [] if s.get("generator")})


# --------------------------------------------------------------------------- planning

@dataclass
class Item:
    """One noun that relabels."""
    source: str                     # registry | role | queue_role | roles_list
    ref: str                        # what source_ref names after the rule: a key, role:<stem>, ...
    label: str
    noun_key: Optional[str]         # the noun's registry row (None for a role file or a queue entry)
    m1: str
    generators: list
    relabel: N.Relabel
    adj_key: str
    where: str                      # corpus | registry | new
    corpus_stem: Optional[str] = None
    extra: dict = field(default_factory=dict)   # fields added to both relabel blocks (the LLM pass: model, reason, ...)


@dataclass
class Plan:
    kind: str                       # backlog | roles | llm
    items: list = field(default_factory=list)
    reasons: Counter = field(default_factory=Counter)        # by source: NoRelabel reasons
    leftover_person: dict = field(default_factory=dict)      # source or generator -> [labels]
    n_seen: Counter = field(default_factory=Counter)         # single-word nouns looked at, by source
    n_already_linked: int = 0
    n_phrases: int = 0

    def candidates(self, run_id: str) -> list[Candidate]:
        """The stream's ``Candidate`` objects: every adjective that is not a corpus trait, in item order."""
        return [Candidate(surface=it.relabel.adjective, generator=GENERATOR, run_id=run_id,
                          gloss_hint=it.relabel.definition, sense_id=1,
                          source_ref=f"relabel:{it.relabel.rule}:{it.ref}")
                for it in self.items if it.where != "corpus"]

    def counts(self) -> dict:
        by_source: dict[str, dict] = {}
        for src in sorted(set(self.n_seen) | {it.source for it in self.items}):
            its = [it for it in self.items if it.source == src]
            by_source[src] = {"n_looked_at": self.n_seen[src], "n_relabelled": len(its),
                              "by_where": dict(sorted(Counter(it.where for it in its).items()))}
        new_adj = sorted({it.adj_key for it in self.items if it.where == "new"})
        return {"n_relabelled": len(self.items),
                "by_rule": dict(sorted(Counter(it.relabel.rule for it in self.items).items())),
                "by_where": dict(sorted(Counter(it.where for it in self.items).items())),
                "by_noun_m1": dict(sorted(Counter(it.m1 for it in self.items).items())),
                "by_generator": dict(sorted(Counter(g for it in self.items for g in it.generators).items())),
                "by_source": by_source, "n_distinct_new": len(new_adj), "distinct_new": new_adj,
                "reasons": dict(sorted(self.reasons.items())), "n_already_linked": self.n_already_linked,
                "n_phrases": self.n_phrases,
                "leftover_person_nouns": {k: len(v) for k, v in sorted(self.leftover_person.items())}}


def _where(adj: str, rows: dict, cmap: dict) -> tuple[str, str, Optional[str]]:
    stem = normalize_candidate(adj).stem
    key = make_key(stem, 1)
    if stem in cmap:
        return "corpus", key, cmap[stem]
    return ("registry" if key in rows else "new"), key, None


def _linked(row: dict) -> bool:
    b = row.get("relabel") or {}
    return bool(b.get("to_key") or b.get("to_corpus_stem")) and int(b.get("helper_version") or 0) >= N.HELPER_VERSION


def _ref_linked(row: Optional[dict], ref: str) -> bool:
    """A role-file or queue item (no noun row of its own) is already linked when its adjective row records it: a
    ``relabel`` block from this ``ref`` at this helper version, or a ``noun_relabel`` source naming it (review S2,
    2026-10-14: a rerun under a new run id otherwise appended a second source)."""
    if not row:
        return False
    b = row.get("relabel") or {}
    if b.get("from_source") == ref and int(b.get("helper_version") or 0) >= N.HELPER_VERSION:
        return True
    return any(isinstance(s, dict) and s.get("generator") == "noun_relabel"
               and str(s.get("source_ref") or "").endswith(f":{ref}") for s in row.get("sources") or [])


def backlog_plan(rows: dict, *, lookups: N.NounLookups, cmap: dict) -> Plan:
    """Every row with a single-word label through the helper (rows already linked at this helper version skipped)."""
    plan = Plan(kind="backlog")
    for key, row in sorted(rows.items()):
        label = row.get("label") or row.get("surface") or ""
        if " " in label.strip():
            plan.n_phrases += 1
            continue
        if _linked(row):
            plan.n_already_linked += 1
            continue
        plan.n_seen["registry"] += 1
        r = N.relabel(label, lookups=lookups)
        if isinstance(r, N.NoRelabel):
            plan.reasons[r.reason] += 1
            if r.reason == "person_no_adjective":
                for g in _generators(row) or ["?"]:
                    plan.leftover_person.setdefault(g, []).append(label)
            continue
        where, adj_key, cstem = _where(r.adjective, rows, cmap)
        if adj_key == key:
            continue
        plan.items.append(Item(source="registry", ref=key, label=label, noun_key=key, m1=m1_state(row),
                               generators=_generators(row), relabel=r, adj_key=adj_key, where=where,
                               corpus_stem=cstem))
    return plan


def role_sources(rows: dict, *, data_dir: Path) -> list[tuple[str, str, str, Optional[str], str]]:
    """``(source, ref, label, noun_key, m1 state)`` of every role noun: the corpus role files (display name), the
    queue's role entries (any status), the registry rows held on the roles list."""
    from assistant_axis.entity_id import corpus_display_name
    out = []
    rdir = Path(data_dir) / "roles" / "instructions"
    for p in sorted(rdir.glob("*.json")) if rdir.exists() else []:
        out.append(("role", f"role:{p.stem}", corpus_display_name(p.stem, "roles", data_dir=data_dir), None,
                    "role_file"))
    qp = Path(data_dir) / "seed_queue.json"
    if qp.exists():
        for e in json.loads(qp.read_text(encoding="utf-8")).get("entries") or []:
            if e.get("entity_type") == "role" and e.get("stem"):
                out.append(("queue_role", f"queue_role:{e['stem']}", e.get("label") or e["stem"].replace("_", " "),
                            None, f"queue_{e.get('status')}"))
    for key, row in sorted(rows.items()):
        if row.get("holding") == "roles":
            out.append(("roles_list", f"roles_list:{key}", row.get("label") or row.get("surface") or "", key,
                        m1_state(row)))
    return out


def roles_plan(rows: dict, *, lookups: N.NounLookups, cmap: dict, data_dir: Path) -> Plan:
    plan = Plan(kind="roles")
    for source, ref, label, noun_key, m1 in role_sources(rows, data_dir=data_dir):
        if " " in label.strip():
            plan.n_phrases += 1
            continue
        if noun_key is not None and _linked(rows[noun_key]):
            plan.n_already_linked += 1
            continue
        plan.n_seen[source] += 1
        r = N.relabel(label, lookups=lookups)
        if isinstance(r, N.NoRelabel):
            plan.reasons[f"{source}:{r.reason}"] += 1
            if r.reason == "person_no_adjective":
                plan.leftover_person.setdefault(source, []).append(label)
            continue
        where, adj_key, cstem = _where(r.adjective, rows, cmap)
        if noun_key is None and adj_key is not None and _ref_linked(rows.get(adj_key), ref):
            plan.n_already_linked += 1
            continue
        plan.items.append(Item(source=source, ref=ref, label=label, noun_key=noun_key, m1=m1,
                               generators=_generators(rows[noun_key]) if noun_key else [], relabel=r, adj_key=adj_key,
                               where=where, corpus_stem=cstem))
    return plan


# --------------------------------------------------------------------------- the table and the report

def _link(stem: str, kind: str, base: Optional[Path], data_dir: Path) -> str:
    """A corpus file named in the report, as a markdown link relative to the report (the hotlink rule)."""
    if base is None:
        return stem
    target = Path(data_dir) / kind / "instructions" / f"{stem}.json"
    return f"[{stem}]({os.path.relpath(target, base)})"


def render_report(plan: Plan, *, data_dir: Path, report_path: Optional[Path] = None, title: str = "") -> str:
    base = report_path.parent.resolve() if report_path is not None else None
    data_dir = Path(data_dir).resolve() if base is not None else Path(data_dir)
    c = plan.counts()
    out = [f"# {title or ('noun relabel ' + plan.kind)}", "",
           f"Helper version {N.HELPER_VERSION} (rules sha256 `{N.rules_sha256()[:16]}`), {N.OEWN_LEXICON}.  "
           f"{c['n_relabelled']} nouns relabel; {c['n_already_linked']} already linked at this version; "
           f"{c['n_phrases']} phrases left alone.", "",
           "| count | value |", "|---|---|"]
    for name in ("by_rule", "by_where", "by_noun_m1", "by_generator"):
        out.append(f"| {name.replace('_', ' ')} | {json.dumps(c[name])} |")
    out.append(f"| distinct new adjectives | {c['n_distinct_new']} |")
    for src, d in c["by_source"].items():
        out.append(f"| source {src} | looked at {d['n_looked_at']}, relabel {d['n_relabelled']}, "
                   f"{json.dumps(d['by_where'])} |")
    out.append(f"| not relabelled, by reason | {json.dumps(c['reasons'])} |")
    out += ["", "## Every relabel", "", "| noun | source | noun's M1 state | adjective | where | route |",
            "|---|---|---|---|---|---|"]
    for it in sorted(plan.items, key=lambda x: (x.where != "new", x.relabel.rule, x.label)):
        noun = (_link(it.ref.split(":", 1)[1], "roles", base, data_dir) if it.source == "role" else
                it.noun_key or it.ref)
        adj = (_link(it.corpus_stem, "traits", base, data_dir) + " (corpus trait)" if it.where == "corpus" else
               f"{it.relabel.adjective} ({it.adj_key})")
        block = N.relabel_blocks(it.noun_key or it.ref, it.adj_key, it.relabel, now="")[1] or {}
        route = N.route_text({**block, "from_surface": it.label}) if block else it.relabel.rule
        out.append(f"| {noun} | {it.source} | {it.m1} | {adj} | {it.where} | {route} |")
    out += ["", "## Person nouns the rules leave without an adjective", ""]
    for k, labels in sorted(plan.leftover_person.items()):
        out.append(f"- **{k}** ({len(labels)}): {', '.join(sorted(set(labels)))}")
    return "\n".join(out) + "\n"


def print_table(plan: Plan) -> None:
    c = plan.counts()
    print(f"{plan.kind}: {c['n_relabelled']} nouns relabel ({c['n_already_linked']} already linked, "
          f"{c['n_phrases']} phrases left alone)")
    for name in ("by_rule", "by_where", "by_noun_m1", "by_generator"):
        print(f"  {name}: {json.dumps(c[name])}")
    for src, d in c["by_source"].items():
        print(f"  source {src}: looked at {d['n_looked_at']}, relabel {d['n_relabelled']} {json.dumps(d['by_where'])}")
    print(f"  distinct new adjectives: {c['n_distinct_new']}: {', '.join(k.split('#')[0] for k in c['distinct_new'])}")
    print(f"  not relabelled: {json.dumps(c['reasons'])}")
    print(f"  person nouns left without an adjective: {json.dumps(c['leftover_person_nouns'])}")
    for it in sorted(plan.items, key=lambda x: (x.where, x.relabel.rule, x.label)):
        print(f"    {it.label} -> {it.relabel.adjective} [{it.relabel.rule}; {it.where}; noun {it.m1}; {it.source}]")


# --------------------------------------------------------------------------- applying

def apply_plan(plan: Plan, *, registry_path: Path, run_id: str, candidates_dir: Path, data_dir: Path,
               argv: Optional[list] = None, run=None, meta_extra: Optional[dict] = None,
               report_extra: str = "") -> dict:
    """Write the stream (see the module docstring); returns the counts.  Nothing to link: nothing written (unless
    ``run``, an open run the caller has already written to, is given: the LLM pass's calls are recorded there, so
    its ``run.json`` and report are written whatever the answers were).  ``meta_extra`` goes into ``run.json``,
    ``report_extra`` (markdown) after the report's tables."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.runs import start_run
    if not plan.items and run is None:
        return {"n_written": 0}
    snapshot_sha = _sha256_file(registry_path)
    cands = plan.candidates(run_id)
    if run is None:
        run = start_run(GENERATOR, run_id, args={"kind": plan.kind, "argv": argv or sys.argv},
                        candidates_dir=candidates_dir)
    if cands:
        run.record_candidates(cands)                        # the tracked record first, then the log
        rep = submit_candidates(cands, registry_path=registry_path, relabel=None)
    else:
        rep = None
    reg = Registry(registry_path)
    n_blocks = 0
    with reg.locked():
        now = utc_now()
        cur = reg._fold_unlocked()
        blocks: dict[str, dict] = {}

        def put(key: str, block: dict) -> None:
            if key not in cur:
                return
            if N.link_wanted(blocks.get(key) or cur[key].get("relabel"), block):
                blocks[key] = block

        for it in plan.items:
            corpus = it.where == "corpus"
            nb, ab = N.relabel_blocks(it.noun_key or it.ref, None if corpus else it.adj_key, it.relabel,
                                      corpus_stem=it.corpus_stem, run=f"{GENERATOR}/{run_id}", now=now)
            nb = {**nb, **it.extra}
            ab = None if ab is None else {**ab, **it.extra}
            if it.noun_key is not None:
                put(it.noun_key, nb)
            if ab is not None:
                if it.noun_key is None:                     # a role file or a queue entry: no row to point at
                    ab["from_key"] = None
                ab["from_source"] = it.ref
                ab["from_surface"] = it.label
                put(it.adj_key, ab)
        if blocks:
            reg.update_many({k: {"relabel": b} for k, b in blocks.items()}, now=now, merge_blocks=False)
        n_blocks = len(blocks)
    run.finish(n_emitted=len(cands))
    counts = plan.counts()
    meta_path = run.dir / "run.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({"stream": plan.kind, "helper_version": N.HELPER_VERSION, "oewn": N.OEWN_LEXICON,
                 "rules": N.rules_sha256(), "counts": counts, "n_blocks_written": n_blocks,
                 "submit_report": None if rep is None else {k: v for k, v in rep.as_dict().items() if k != "keys"}})
    if plan.kind in ("backlog", "llm"):
        meta["registry_snapshot_sha256"] = snapshot_sha
    meta.update(meta_extra or {})
    atomic_write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", meta_path)
    report = run.dir / f"{plan.kind}_report.md"
    atomic_write_text(render_report(plan, data_dir=data_dir, report_path=report,
                                    title=f"noun relabel {plan.kind} {run_id}") + report_extra, report)
    return {"n_written": len(cands), "n_blocks": n_blocks, "run_dir": str(run.dir)}


def follow_ups(run_id: str, registry_path: Path) -> list[str]:
    reg = "" if Path(registry_path) == paths.REGISTRY_PATH else f" --registry {registry_path}"
    return [f"uv run python data_analysis/gap_generation/traithood_filter.py --batch-id {run_id} --run "
            f"{GENERATOR}/{run_id} --pipeline split --budget-usd 1{reg}",
            f"uv run python data_analysis/gap_generation/novelty_score.py score --batch-id {run_id} --run "
            f"{GENERATOR}/{run_id} --budget-usd 1{reg}"]


# --------------------------------------------------------------------------- commands

def cmd_check(args) -> int:
    lk = _lookups()
    for w in args.words:
        r = N.relabel(w, lookups=lk)
        if isinstance(r, N.Relabel):
            print(f"{w}: {r.adjective} [{r.rule}; {r.lexfile}; Zipf {r.zipf}] {r.definition or ''}")
        else:
            print(f"{w}: no relabel ({r.reason})")
    return 0


def _stream(args, kind: str) -> int:
    if not Path(args.registry).exists():
        print(f"REFUSED: no registry at {args.registry}: run the streams in the checkout that holds the registry "
              f"(review S1, 2026-10-14)", file=sys.stderr)
        return 2
    rows = Registry(args.registry).fold()
    lk = _lookups()
    cmap = N.corpus_stem_map(args.data_dir)
    plan = (backlog_plan(rows, lookups=lk, cmap=cmap) if kind == "backlog" else
            roles_plan(rows, lookups=lk, cmap=cmap, data_dir=args.data_dir))
    print_table(plan)
    if args.report is not None:
        from assistant_axis.atomic_io import atomic_write_text
        args.report.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(render_report(plan, data_dir=args.data_dir, report_path=args.report,
                                        title=f"noun relabel {kind} (dry run, {_today()})"), args.report)
        print(f"report: {args.report}")
    if not args.apply:
        print(f"DRY-RUN: nothing written to {args.registry}" + ("" if args.report is None else
                                                                 " (only the report above)"))
        return 0
    run_id = paths.check_id(args.run_id or f"{kind}-{_today()}", "run_id")
    cdir = args.candidates_dir or Path(args.registry).parent
    res = apply_plan(plan, registry_path=args.registry, run_id=run_id, candidates_dir=cdir, data_dir=args.data_dir)
    if not res["n_written"] and not res.get("n_blocks"):
        print("nothing to link: every noun is linked at this helper version (nothing written)")
        return 0
    print(f"applied: {res['n_written']} candidates submitted as {GENERATOR}/{run_id}, {res['n_blocks']} relabel "
          f"blocks written; run dir {res['run_dir']}")
    print("follow-ups (paid; each prints its own estimate and refuses over its cap):")
    for line in follow_ups(run_id, args.registry):
        print(f"  {line}")
    return 0


def cmd_backlog(args) -> int:
    return _stream(args, "backlog")


def cmd_roles(args) -> int:
    return _stream(args, "roles")


# --------------------------------------------------------------------------- the Haiku pilot (task 9)

def pilot_pool(rows: dict, *, lookups: N.NounLookups, data_dir: Path) -> tuple[list[dict], list[dict]]:
    """``(person, role)``: the population the pilot draws from and ``llm-apply`` takes whole.  Person nouns M1 passed
    as traits (registry rows not on a holding list whose single-word label the rules leave as
    ``person_no_adjective``) and role nouns (corpus role files whose single-word display name the rules leave so),
    each sorted, as ``{"key", "label", "gloss", "kind"}``."""
    person, role = [], []
    for key, row in sorted(rows.items()):
        label = row.get("label") or ""
        if " " in label or row.get("holding") or (row.get("filter") or {}).get("verdict") != "trait":
            continue
        r = N.relabel(label, lookups=lookups)
        if isinstance(r, N.NoRelabel) and r.reason == "person_no_adjective":
            from assistant_axis.gapgen.registry import first_gloss_hint
            person.append({"key": key, "label": label, "gloss": row.get("gloss") or first_gloss_hint(row),
                           "kind": "person"})
    from assistant_axis.entity_id import corpus_display_name
    rdir = Path(data_dir) / "roles" / "instructions"
    for p in sorted(rdir.glob("*.json")) if rdir.exists() else []:
        label = corpus_display_name(p.stem, "roles", data_dir=data_dir)
        if " " in label:
            continue
        r = N.relabel(label, lookups=lookups)
        if isinstance(r, N.NoRelabel) and r.reason == "person_no_adjective":
            desc = json.loads(p.read_text(encoding="utf-8")).get("description")
            role.append({"key": f"role:{p.stem}", "label": label, "gloss": desc, "kind": "role"})
    return person, role


def pilot_sample(rows: dict, *, lookups: N.NounLookups, data_dir: Path, n: int = 100, seed: int = 0) -> list[dict]:
    """The pilot's rows: ``n`` x 60% person nouns, ``n`` x 40% role nouns of :func:`pilot_pool`, each drawn with
    ``random.Random(seed)`` from the sorted pool."""
    person, role = pilot_pool(rows, lookups=lookups, data_dir=data_dir)
    rng = random.Random(seed)
    n_person = round(n * PILOT_SHARES["person"] / 100)
    pick = rng.sample(person, min(n_person, len(person))) + rng.sample(role, min(n - n_person, len(role)))
    return pick


def pilot_estimate(n: int, what: str = "noun relabel pilot"):
    from assistant_axis.gapgen.cost import Estimate
    est = Estimate()
    est.add(what, N.PILOT_MODEL, n, PILOT_IN_TOKENS, PILOT_OUT_TOKENS)
    return est


async def _run_pilot(sample: list[dict], *, client, usage, records_path: Path, lookups: N.NounLookups,
                     concurrency: int = 8) -> list[dict]:
    out: list[dict] = []
    await _run_calls(sample, client=client, usage=usage, records_path=records_path, lookups=lookups, out=out,
                     concurrency=concurrency)
    return out


async def _run_calls(sample: list[dict], *, client, usage, records_path: Path, lookups: N.NounLookups, out: list,
                     concurrency: int = 8) -> None:
    """One pilot call per row (the pinned prompt, Haiku 5.5, ``PILOT_MAX_TOKENS``, no temperature), each response
    appended to ``records_path`` before it is parsed; the parsed records go to ``out`` as they come (so a budget stop,
    re-raised at the end, leaves the answers received)."""
    from assistant_axis.gapgen.llm import call_anthropic_json
    from assistant_axis.judge_pricing import BudgetExceededError
    sem = asyncio.Semaphore(concurrency)
    sha = hashlib.sha256(N.PILOT_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    stop: list[BaseException] = []

    async def one(row: dict) -> None:
        if stop:
            return
        async with sem:
            if stop:
                return
            user = N.render_pilot_user(row["label"], row["gloss"])
            meta: dict = {}
            try:
                text = await call_anthropic_json(client, system=N.PILOT_SYSTEM_PROMPT, user=user, model=N.PILOT_MODEL,
                                                 max_tokens=N.PILOT_MAX_TOKENS, temperature=None, usage=usage,
                                                 meta=meta)
            except BudgetExceededError as exc:          # the response was paid for: record it, then stop
                stop.append(exc)
                text = meta.get("text")
            rec = {"key": row["key"], "label": row["label"], "gloss": row["gloss"], "kind": row["kind"],
                   "prompt_sha256": sha, "prompt_version": N.PILOT_PROMPT_VERSION, "model": N.PILOT_MODEL,
                   "max_tokens": N.PILOT_MAX_TOKENS, "user": user, "raw": text, "stop_reason": meta.get("stop_reason"), "error": meta.get("error"),
                   "usage_raw": meta.get("usage_raw"), "at": utc_now()}
            with open(records_path, "a", encoding="utf-8") as fh:      # recorded before it is parsed
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            parsed = N.parse_pilot_reply(text)
            adj = (parsed or {}).get("adjective")
            rec["parsed"] = parsed
            rec["in_oewn"] = bool(adj) and bool(set(lookups.pos(adj)) & set(N.ADJ_POS))
            rec["zipf"] = lookups.zipf(adj) if adj else None
            out.append(rec)

    await asyncio.gather(*(one(r) for r in sample))
    if stop:
        raise stop[0]


def pilot_readout(recs: list[dict], *, sample_n: int, cost_usd: float, run_name: str) -> tuple[str, dict]:
    """The readout's markdown and its counts: the yield (an answer that is an OEWN adjective or clears Zipf 1.5),
    by kind; every answer."""
    def counts(rs):
        answered = [r for r in rs if (r.get("parsed") or {}).get("adjective")]
        good = [r for r in answered if r.get("in_oewn") or (r.get("zipf") or 0) >= N.FLOOR_ZIPF]
        return {"n": len(rs), "parsed": sum(1 for r in rs if r.get("parsed") is not None),
                "answered": len(answered), "yield": len(good)}
    by_kind = {k: counts([r for r in recs if r["kind"] == k]) for k in ("person", "role")}
    total = counts(recs)
    adopt = total["yield"] >= PILOT_ADOPT_THRESHOLD
    lines = [f"# Noun relabel pilot ({run_name})", "",
             f"{N.PILOT_MODEL}, prompt `noun_relabel` v{N.PILOT_PROMPT_VERSION}; {sample_n} rows sent, "
             f"{total['parsed']} parsed, {total['answered']} named an adjective, **{total['yield']}** of them an OEWN "
             f"adjective or at Zipf {N.FLOOR_ZIPF} or above (the yield); cost ${cost_usd:.4f}.", "",
             f"Adopt threshold (plan section 10): {PILOT_ADOPT_THRESHOLD} of 100.  "
             f"{'Met' if adopt else 'Not met'}; Roger decides.  None of the rows is one the rules relabel (the sample "
             f"is drawn from the nouns the rules leave as person_no_adjective).", "",
             "| kind | rows | parsed | named an adjective | yield |", "|---|---|---|---|---|"]
    for k, c in by_kind.items():
        lines.append(f"| {k} | {c['n']} | {c['parsed']} | {c['answered']} | {c['yield']} |")
    lines += ["", "| noun | kind | adjective | in OEWN | Zipf | confidence | reason |", "|---|---|---|---|---|---|---|"]
    for r in sorted(recs, key=lambda x: (x["kind"], x["label"])):
        p = r.get("parsed") or {}
        cell = p.get("adjective") or ("(unparsed)" if r.get("parsed") is None else "none")
        lines.append(f"| {r['label']} | {r['kind']} | {cell} | {'yes' if r.get('in_oewn') else ''} | "
                     f"{'' if r.get('zipf') is None else r['zipf']} | {p.get('confidence', '')} | "
                     f"{str(p.get('reason') or '').replace('|', '/')} |")
    return "\n".join(lines) + "\n", {"by_kind": by_kind, "total": total, "adopt_threshold_met": adopt}


def cmd_llm_pilot(args) -> int:
    import logging

    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen import rubric_versions
    from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.runs import dirty_refusal, git_sha, platform_dirty_files
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import BudgetExceededError
    sha = hashlib.sha256(N.PILOT_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    if rubric_versions.HISTORY.get("noun_relabel", {}).get(N.PILOT_PROMPT_VERSION) != sha:
        print(f"REFUSED (rubric not pinned): noun_relabel v{N.PILOT_PROMPT_VERSION} is not pinned to {sha[:12]}...",
              file=sys.stderr)
        return 2
    rows = Registry(args.registry).fold()
    lk = _lookups()
    sample = pilot_sample(rows, lookups=lk, data_dir=args.data_dir, n=args.n, seed=args.seed)
    est = pilot_estimate(len(sample))
    kinds = Counter(r["kind"] for r in sample)
    print(f"llm-pilot: {len(sample)} rows ({json.dumps(dict(sorted(kinds.items())))}), seed {args.seed}")
    print(f"estimate:\n{est.format()}")
    dirty_refused, dirty_check = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    out_dir = args.out_dir or (paths.DATA_CANDIDATES / "noun_relabel" / f"llm_pilot_{_today()}")
    if args.dry_run:
        for r in sample:
            print(f"  [{r['kind']}] {r['key']}: {r['label']}: {' '.join(str(r['gloss'] or '').split())[:100]}")
        if sample:
            print("--- system ---\n" + N.PILOT_SYSTEM_PROMPT + "\n--- user (first row) ---\n"
                  + N.render_pilot_user(sample[0]["label"], sample[0]["gloss"]))
        if dirty_refused:
            print(f"DRY-RUN: the real run would be REFUSED: {dirty_refused}")
        print(f"DRY-RUN: no call sent; {out_dir} untouched")
        return 0
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=False)
    except CostRefused:
        return 2
    if dirty_refused:
        print(f"REFUSED: {dirty_refused}", file=sys.stderr)
        return 2
    if out_dir.exists():
        print(f"REFUSED: {out_dir} exists: give a new --out-dir (a pilot is never overwritten)", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True)
    log = logging.getLogger("noun_relabel.llm_pilot")
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    started, stopped, recs = utc_now(), None, []
    try:
        recs = asyncio.run(_run_pilot(sample, client=_anthropic_client(), usage=usage,
                                      records_path=out_dir / "responses.jsonl", lookups=lk))
    except BudgetExceededError as exc:
        stopped = f"budget stop: {exc}"
        print(f"STOPPED (budget): {exc}", file=sys.stderr)
    finally:
        usage.write_json(out_dir / "usage.json")
    text, counts = pilot_readout(recs, sample_n=len(sample), cost_usd=usage.total_cost_usd, run_name=out_dir.name)
    with open(out_dir / "parsed.jsonl", "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps({k: r.get(k) for k in ("key", "label", "gloss", "kind", "prompt_sha256", "model", "raw",
                                                        "parsed", "in_oewn", "zipf", "at")}, ensure_ascii=False) + "\n")
    atomic_write_text(text, out_dir / "readout.md")
    meta = {"what": "noun_relabel.py llm-pilot", "model": N.PILOT_MODEL, "prompt_version": N.PILOT_PROMPT_VERSION,
            "prompt_sha256": sha, "n": len(sample), "seed": args.seed, "git_sha": git_sha(),
            "allow_dirty": bool(args.allow_dirty), "dirty_check": dirty_check, "budget_usd": cap,
            "estimate_usd": round(est.usd, 6), "cost_usd": round(usage.total_cost_usd, 6), "n_calls": usage.n_calls,
            "counts": counts, "stopped": stopped, "started_at": started, "finished_at": utc_now(), "argv": sys.argv}
    atomic_write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", out_dir / "run.json")
    warn_if_low_parse_rate(label=f"noun_relabel_pilot:{N.PILOT_MODEL}", n_ok=counts["total"]["parsed"],
                           n_total=len(recs), logger_obj=log)
    print(usage.log_line())
    print(f"yield {counts['total']['yield']} of {len(sample)} (adopt threshold {PILOT_ADOPT_THRESHOLD}); "
          f"readout {out_dir / 'readout.md'}")
    return 2 if stopped else 0


# --------------------------------------------------------------------------- the LLM pass (llm-apply)

#: Why an answer of the LLM pass makes no link, in the order they are tested.
LLM_REJECT_REASONS = ("unparsed", "none", "phrase", "not_established", "refused_stem", "same_as_noun")


def _prompt_sha() -> str:
    return hashlib.sha256(N.PILOT_SYSTEM_PROMPT.encode("utf-8")).hexdigest()


def _llm_linked(row: Optional[dict]) -> bool:
    """A noun row already linked: a ``relabel`` block at this helper version, or any earlier LLM relabel."""
    return bool(row) and (_linked(row) or (row.get("relabel") or {}).get("rule") == N.LLM_RULE)


def llm_selection(rows: dict, *, lookups: N.NounLookups, data_dir: Path) -> tuple[list[dict], int]:
    """``(rows to answer, n already linked)``: the whole of :func:`pilot_pool` (person nouns first, then roles), less
    the person rows already linked (:func:`_llm_linked`).  A role file has no noun row: it is found linked once its
    answer is known (:func:`llm_items`)."""
    person, role = pilot_pool(rows, lookups=lookups, data_dir=data_dir)
    keep = [r for r in person if not _llm_linked(rows.get(r["key"]))]
    return keep + role, len(person) - len(keep)


def load_answers(candidates_dir: Path, *, sha: Optional[str] = None) -> dict[str, dict]:
    """``{key: record}``: the reusable answers already recorded, by the pilots
    (``<candidates-dir>/noun_relabel/llm_pilot_*/responses.jsonl``) and earlier LLM passes
    (``<candidates-dir>/runs/noun_relabel/*/responses.jsonl``).  Reusable: the same prompt sha and model, not cut off
    at ``max_tokens`` (nor recorded with another ``max_tokens``), and a reply that parses; the latest per key wins.
    Each record gains ``parsed`` (parsed again from ``raw``) and ``reused_from`` (its directory's name)."""
    sha = sha or _prompt_sha()
    cdir = Path(candidates_dir)
    files = (sorted((cdir / "noun_relabel").glob("llm_pilot_*/responses.jsonl"))
             + sorted((cdir / "runs" / GENERATOR).glob("*/responses.jsonl")))
    best: dict[str, dict] = {}
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict) or not rec.get("key"):
                continue
            if rec.get("prompt_sha256") != sha or rec.get("model") != N.PILOT_MODEL:
                continue
            if rec.get("stop_reason") == "max_tokens" or rec.get("max_tokens") not in (None, N.PILOT_MAX_TOKENS):
                continue
            parsed = N.parse_pilot_reply(rec.get("raw"))
            if parsed is None:
                continue
            k = rec["key"]
            if k not in best or str(rec.get("at") or "") >= str(best[k].get("at") or ""):
                best[k] = {**rec, "parsed": parsed, "reused_from": f.parent.name}
    return best


def accept_answer(label: str, parsed: Optional[dict], *, lookups: N.NounLookups) -> tuple[Optional[str], Optional[str]]:
    """``(adjective, None)`` or ``(None, reason)`` (:data:`LLM_REJECT_REASONS`).  The pilot's yield rule (an OEWN
    adjective, or at Zipf :data:`N.FLOOR_ZIPF` or above) after the British spelling is folded to US where OEWN has
    the result, and the rules' gates: a stem the platform accepts, not the noun itself."""
    if parsed is None:
        return None, "unparsed"
    adj = " ".join(str(parsed.get("adjective") or "").split()).lower()
    if not adj:
        return None, "none"
    if " " in adj:
        return None, "phrase"
    adj = N.us_spelling(adj, lexicon=lookups.lexicon())
    if not (set(lookups.pos(adj)) & set(N.ADJ_POS) or lookups.zipf(adj) >= N.FLOOR_ZIPF):
        return None, "not_established"
    try:
        stem = normalize_candidate(adj).stem
    except ValueError:
        return None, "refused_stem"
    try:
        same = stem == normalize_candidate(label).stem
    except ValueError:
        same = adj == label.lower()
    if same:
        return None, "same_as_noun"
    return adj, None


def llm_items(sel: list[dict], answers: dict, rows: dict, *, lookups: N.NounLookups,
              cmap: dict) -> tuple[list[Item], Counter, list[dict], int]:
    """``(items, rejections by reason, every answer's table row, n roles already linked)`` for the rows of ``sel``
    that have an answer.  An item's ``Relabel`` has rule :data:`N.LLM_RULE`, the adjective sense's OEWN definition
    (person sense first) as its gloss, and ``extra`` (model, prompt version, the model's confidence and reason) for the
    blocks.  A role whose adjective row already records it is linked (``_ref_linked``) and skipped."""
    items: list[Item] = []
    reasons: Counter = Counter()
    table: list[dict] = []
    n_linked = 0
    for row in sel:
        rec = answers.get(row["key"])
        if rec is None:
            continue
        parsed = rec.get("parsed")
        adj, why = accept_answer(row["label"], parsed, lookups=lookups)
        entry = {"key": row["key"], "label": row["label"], "kind": row["kind"],
                 "answer": (parsed or {}).get("adjective"), "confidence": (parsed or {}).get("confidence"),
                 "reason": (parsed or {}).get("reason"), "from": rec.get("reused_from") or "this run",
                 "outcome": why or "", "adjective": adj}
        table.append(entry)
        if why:
            reasons[why] += 1
            continue
        noun_key = row["key"] if row["kind"] == "person" else None
        where, adj_key, cstem = _where(adj, rows, cmap)
        if noun_key is not None and adj_key == noun_key:
            reasons["same_as_noun"] += 1
            entry["outcome"] = "same_as_noun"
            continue
        if noun_key is None and _ref_linked(rows.get(adj_key), row["key"]):
            n_linked += 1
            entry["outcome"] = "already_linked"
            continue
        in_oewn = bool(set(lookups.pos(adj)) & set(N.ADJ_POS))
        r = N.Relabel(surface=row["label"], adjective=adj, rule=N.LLM_RULE, lexfile=None,
                      definition=N._best_definition(adj, lookups) if in_oewn else None, zipf=lookups.zipf(adj))
        extra = {"model": rec.get("model") or N.PILOT_MODEL, "prompt_version": rec.get("prompt_version"),
                 "confidence": (parsed or {}).get("confidence"), "reason": (parsed or {}).get("reason")}
        entry["outcome"] = where
        items.append(Item(source="registry" if noun_key else "role", ref=row["key"], label=row["label"],
                          noun_key=noun_key, m1=m1_state(rows.get(noun_key)) if noun_key else "role_file",
                          generators=_generators(rows[noun_key]) if noun_key else [], relabel=r, adj_key=adj_key,
                          where=where, corpus_stem=cstem, extra=extra))
    return items, reasons, table, n_linked


def _writes(items: list[Item]) -> list[Item]:
    """The items that write anything: all but a role whose adjective is a corpus trait (no row on either side)."""
    return [it for it in items if it.noun_key is not None or it.where != "corpus"]


def render_answers(table: list[dict]) -> str:
    """The report's list of every answer (markdown)."""
    def cell(x) -> str:
        return " ".join(str("" if x is None else x).split()).replace("|", "/")
    out = ["", "## Every answer", "",
           "Outcome: `new` / `registry` / `corpus` (where the adjective is; a link was written), or why not "
           f"({', '.join(LLM_REJECT_REASONS)}, already_linked).  An unparsed reply is asked again by the next run.", "",
           "| noun | kind | answer | outcome | confidence | the model's reason | answered in |",
           "|---|---|---|---|---|---|---|"]
    for e in sorted(table, key=lambda x: (x["outcome"] in LLM_REJECT_REASONS, x["kind"], x["label"])):
        ans = e["answer"] if e["adjective"] in (None, e["answer"]) else f"{e['answer']} -> {e['adjective']}"
        out.append(f"| {cell(e['label'])} | {e['kind']} | {cell(ans) or 'none'} | {e['outcome']} | "
                   f"{cell(e['confidence'])} | {cell(e['reason'])} | {cell(e['from'])} |")
    return "\n".join(out) + "\n"


def cmd_llm_apply(args) -> int:
    import logging

    from assistant_axis.gapgen import rubric_versions
    from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.runs import dirty_refusal, git_sha, platform_dirty_files, start_run
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import BudgetExceededError
    if not Path(args.registry).exists():
        print(f"REFUSED: no registry at {args.registry}: run llm-apply in the checkout that holds the registry",
              file=sys.stderr)
        return 2
    sha = _prompt_sha()
    if rubric_versions.HISTORY.get("noun_relabel", {}).get(N.PILOT_PROMPT_VERSION) != sha:
        print(f"REFUSED (rubric not pinned): noun_relabel v{N.PILOT_PROMPT_VERSION} is not pinned to {sha[:12]}...",
              file=sys.stderr)
        return 2
    rows = Registry(args.registry).fold()
    lk = _lookups()
    cmap = N.corpus_stem_map(args.data_dir)
    cdir = args.candidates_dir or Path(args.registry).parent
    sel, n_linked = llm_selection(rows, lookups=lk, data_dir=args.data_dir)
    answers = load_answers(cdir, sha=sha)
    reused = {r["key"]: answers[r["key"]] for r in sel if r["key"] in answers}
    to_ask = [r for r in sel if r["key"] not in answers]
    est = pilot_estimate(len(to_ask), "noun relabel llm-apply")
    kinds = Counter(r["kind"] for r in sel)
    items, reasons, _table, n_linked_roles = llm_items(sel, reused, rows, lookups=lk, cmap=cmap)
    print(f"llm-apply: {len(sel)} nouns selected ({json.dumps(dict(sorted(kinds.items())))}; the pilot's population, "
          f"whole), {n_linked} person rows already linked left out")
    print(f"  answers reused: {len(reused)} "
          f"({json.dumps(dict(sorted(Counter(r['reused_from'] for r in reused.values()).items())))}); to ask: "
          f"{len(to_ask)}")
    print(f"  of the reused answers: {len(_writes(items))} would link "
          f"({json.dumps(dict(sorted(Counter(it.where for it in items).items())))}), {n_linked_roles} roles already "
          f"linked, rejected {json.dumps(dict(sorted(reasons.items())))}")
    print(f"estimate (the calls still to make):\n{est.format()}")
    dirty_refused, dirty_check = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    run_id = paths.check_id(args.run_id or f"llm-{_today()}", "run_id")
    rdir = paths.run_dir(GENERATOR, run_id, candidates_dir=cdir)
    if args.dry_run:
        if to_ask:
            print("  to ask: " + ", ".join(r["label"] for r in to_ask))
        show = (to_ask or sel)[:1]
        if show:
            print("--- system ---\n" + N.PILOT_SYSTEM_PROMPT + "\n--- user (first row to ask) ---\n"
                  + N.render_pilot_user(show[0]["label"], show[0]["gloss"]))
        if dirty_refused:
            print(f"DRY-RUN: the real run would be REFUSED: {dirty_refused}")
        print(f"DRY-RUN: no call sent; nothing written ({args.registry} and {rdir} untouched)")
        return 0
    if not to_ask and not _writes(items):
        print("nothing to do: every selected noun is answered and linked (no call sent, nothing written)")
        return 0
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=False)
    except CostRefused:
        return 2
    if dirty_refused:
        print(f"REFUSED: {dirty_refused}", file=sys.stderr)
        return 2
    if rdir.exists():
        print(f"REFUSED: {rdir} exists: give a new --run-id (its recorded answers are reused, nothing is asked twice)",
              file=sys.stderr)
        return 2
    started = utc_now()
    run = start_run(GENERATOR, run_id, args={"kind": "llm", "argv": sys.argv, "budget_usd": cap},
                    candidates_dir=cdir)
    usage = GuardedUsage(budget_usd=cap, usage_path=run.dir / "usage.json")
    run.usage = usage
    new_recs: list[dict] = []
    stopped = None
    if to_ask:
        try:
            asyncio.run(_run_calls(to_ask, client=_anthropic_client(), usage=usage,
                                   records_path=run.dir / "responses.jsonl", lookups=lk, out=new_recs))
        except BudgetExceededError as exc:
            stopped = f"budget stop: {exc}"
            print(f"STOPPED (budget): {exc}", file=sys.stderr)
        finally:
            usage.write_json(run.dir / "usage.json")
    meta_extra = {"stream": "llm", "what": "noun_relabel.py llm-apply", "model": N.PILOT_MODEL,
                  "prompt_version": N.PILOT_PROMPT_VERSION, "prompt_sha256": sha, "max_tokens": N.PILOT_MAX_TOKENS,
                  "decision": "Roger 2026-10-14, 'A 1 yes': a one-off pass over the leftover person nouns",
                  "n_selected": len(sel), "selected_by_kind": dict(sorted(kinds.items())),
                  "n_person_already_linked": n_linked, "n_reused": len(reused),
                  "reused_from": dict(sorted(Counter(r["reused_from"] for r in reused.values()).items())),
                  "n_asked": len(to_ask), "n_answered": len(new_recs),
                  "n_parsed": sum(1 for r in new_recs if r.get("parsed") is not None),
                  "estimate_usd": round(est.usd, 6), "budget_usd": cap, "cost_usd": round(usage.total_cost_usd, 6),
                  "n_calls": usage.n_calls, "git_sha": git_sha(), "allow_dirty": bool(args.allow_dirty),
                  "dirty_check": dirty_check, "stopped": stopped, "started_at": started}
    if stopped:                                     # nothing linked: the rerun reuses what was answered
        from assistant_axis.atomic_io import atomic_write_text
        run.finish(n_emitted=0)
        meta = json.loads((run.dir / "run.json").read_text(encoding="utf-8"))
        meta.update(meta_extra)
        atomic_write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", run.dir / "run.json")
        print(f"nothing linked; rerun with a new --run-id (the {len(new_recs)} answers recorded in {run.dir} are "
              f"reused)", file=sys.stderr)
        return 2
    answered = {**reused, **{r["key"]: r for r in new_recs}}
    items, reasons, table, n_linked_roles = llm_items(sel, answered, rows, lookups=lk, cmap=cmap)
    plan = Plan(kind="llm", items=items, reasons=reasons, n_already_linked=n_linked + n_linked_roles,
                n_seen=Counter({"registry" if k == "person" else "role": v for k, v in kinds.items()}))
    meta_extra["rejected"] = dict(sorted(reasons.items()))
    res = apply_plan(plan, registry_path=args.registry, run_id=run_id, candidates_dir=cdir, data_dir=args.data_dir,
                     run=run, meta_extra=meta_extra, report_extra=render_answers(table))
    warn_if_low_parse_rate(label=f"noun_relabel_llm:{N.PILOT_MODEL}", n_ok=meta_extra["n_parsed"],
                           n_total=len(new_recs), logger_obj=logging.getLogger("noun_relabel.llm_apply"))
    print(usage.log_line())
    print(f"applied: {res['n_written']} candidates submitted as {GENERATOR}/{run_id}, {res['n_blocks']} relabel "
          f"blocks written; rejected {json.dumps(meta_extra['rejected'])}; run dir {res['run_dir']}")
    if res["n_written"]:
        print("follow-ups (paid; each prints its own estimate and refuses over its cap):")
        for line in follow_ups(run_id, args.registry):
            print(f"  {line}")
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (runs/noun_relabel/<run-id>/); default the registry's directory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("check", help="the helper's answer for each word ($0)")
    sp.add_argument("words", nargs="+")
    sp.set_defaults(func=cmd_check)
    for name, func in (("backlog", cmd_backlog), ("roles", cmd_roles)):
        sp = sub.add_parser(name, help=f"the {name} stream (dry run unless --apply)")
        sp.add_argument("--apply", action="store_true", help="write the stream (default: dry run, nothing written)")
        sp.add_argument("--run-id", help=f"default {name}-<UTC date>")
        sp.add_argument("--report", type=Path, help="also write the table as markdown here (the dry run's only write)")
        sp.set_defaults(func=func)
    sp = sub.add_parser("llm-pilot", help="open decision 3 (b): the 100-row Haiku pilot (paid; only on Roger's go)")
    sp.add_argument("--n", type=int, default=100)
    sp.add_argument("--budget-usd", type=float, default=0.10)
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--allow-dirty", action="store_true")
    sp.add_argument("--out-dir", type=Path, default=None,
                    help="default data/candidates/noun_relabel/llm_pilot_<UTC date>/ (refused if it exists)")
    sp.set_defaults(func=cmd_llm_pilot)
    sp = sub.add_parser("llm-apply", help="the one-off Haiku pass over the pilot's whole population (paid; Roger "
                                          "2026-10-14)")
    sp.add_argument("--budget-usd", type=float, default=0.50, help="the cap (default 0.50); refused under the estimate")
    sp.add_argument("--run-id", help="default llm-<UTC date>; refused if its directory exists")
    sp.add_argument("--dry-run", action="store_true", help="print the counts, the estimate and a prompt; write nothing")
    sp.add_argument("--allow-dirty", action="store_true")
    sp.set_defaults(func=cmd_llm_apply)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
