#!/usr/bin/env python3
"""Classify every role into one of the nine role kinds (Roger, 2026-10-16).

The kinds are the sketch in reports/trait_gap_generation/README.md § "Parked: generators aimed at roles", accepted
as they stand and as one dimension ("they already cover human-or-not, with borderline cases like elves").  A kind
describes the corpus; it is never a gate on it ("other" exists so that nothing is turned down for fitting nowhere).

Each role (label in the judge display form, plus its description) is read ``--readings`` times (default 3) by
Haiku 5.5, which takes no temperature; the kind is the majority reading (sampled outputs are combined, never gated
on stability).  A three-way split keeps the first reading's kind and is marked ``"split": true`` for Roger.

Output, a side-car keyed by role stem (the role files are left untouched, so nothing that fingerprints them goes
stale): ``data/roles/role_kinds.json``.  Roles whose kind is on record with the same prompt and model are reused;
``--force`` reads them again.  Usage merges into ``data/roles/role_kinds_usage.json`` (cumulative).

Usage:
    uv run python data_analysis/classify_role_kinds.py --dry-run           # rendered prompt and estimate, no calls
    uv run python data_analysis/classify_role_kinds.py --names elf robot   # a few roles
    uv run python data_analysis/classify_role_kinds.py                     # every role, real time (well under $1)
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import hashlib
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.entity_id import judge_label  # noqa: E402
from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402

logger = logging.getLogger("classify_role_kinds")

ROOT = Path(__file__).resolve().parent.parent
ROLES_DIR = ROOT / "data" / "roles" / "instructions"
OUT_PATH = ROOT / "data" / "roles" / "role_kinds.json"
USAGE_PATH = ROOT / "data" / "roles" / "role_kinds_usage.json"
MODEL = "claude-haiku-5-5"
MAX_TOKENS = 2000          # Haiku 5.5 thinks adaptively and the thinking counts against max_tokens
EST_IN, EST_OUT = 900, 600  # tokens per call, generous

#: The nine kinds, in the README's order: key, display name, definition with examples.
KINDS: list[tuple[str, str, str]] = [
    ("occupation", "occupation or task",
     "a job, profession or function someone performs, assistant-style functions included "
     "(accountant, doctor, summarizer)"),
    ("relationship", "life stage, family and relationship",
     "a stage of life or a place in a family or relationship (infant, elder, parent, widow)"),
    ("circumstance", "circumstance",
     "a situation one is in rather than something one does, migration and legal standing included "
     "(homeless, patient, pregnant, refugee, prisoner)"),
    ("status", "status or wealth", "a social rank or level of wealth (aristocrat, billionaire, beggar)"),
    ("stance", "stance or way of life",
     "a chosen conviction, cause or way of living, the lawless included (activist, vegan, pacifist, smuggler, spy)"),
    ("pastime", "pastime", "a hobby or leisure pursuit (gamer, surfer, collector)"),
    ("non_human", "non-human being",
     "anything that is not a human being: mythic, fantasy and fictional creatures (elves included), machines, "
     "robots and AIs, animals, plants and natural systems (angel, vampire, robot, cyborg, coral reef, tree, swarm)"),
    ("temperament", "a temperament under a noun",
     "a personality trait expressed as a noun for a kind of person (optimist, cynic, perfectionist)"),
    ("other", "other", "anything that fits none of the above (void, zeitgeist, default)"),
]
KIND_KEYS = [k for k, _, _ in KINDS]

#: The system prompt, from the pinned rubric file ``reports/trait_gap_generation/rubrics/role_kind.md`` (since
#: 2026-10-22, coding plan 16 task 3: moved there byte for byte from the string this module built from :data:`KINDS`,
#: so that the roles pass reads candidates' kinds with the same text; its sha is unchanged, ``11b559f0cff50189``).
#: The list of kinds in it must stay :data:`KINDS`'s (``test_gapgen_role_kind_rubric.py`` checks); edit both together
#: and pin the new text with ``rubric_pins.py bump role_kind``.
from assistant_axis.gapgen import split_rubrics as _sr  # noqa: E402

SYSTEM = _sr.load_prompt("role_kind")
PROMPT_SHA = hashlib.sha256(SYSTEM.encode()).hexdigest()[:16]


def user_message(label: str, description: str) -> str:
    return f"Role: {label}\nDescription: {description.strip()}"


def load_roles(names: Optional[list[str]] = None) -> list[dict]:
    roles = []
    for p in sorted(ROLES_DIR.glob("*.json")):
        if names and p.stem not in names:
            continue
        d = json.loads(p.read_text())
        roles.append({"stem": p.stem, "label": judge_label(p.stem, "roles"), "description": d.get("description", "")})
    if names:
        missing = sorted(set(names) - {r["stem"] for r in roles})
        if missing:
            raise SystemExit(f"no such role: {', '.join(missing)}")
    return roles


def parse_kind(text: Optional[str]) -> Optional[dict]:
    """The last JSON object in ``text`` with a known ``kind`` (prose before it is allowed), or None."""
    if not text:
        return None
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text, re.S))):
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        kind = str(obj.get("kind", "")).strip().lower().replace("-", "_").replace(" ", "_")
        if kind in KIND_KEYS:
            return {"kind": kind, "reason": str(obj.get("reason", "")).strip()}
    return None


def combine(readings: list[Optional[dict]]) -> dict:
    """Majority over the parsed readings; a tie keeps the earliest reading's kind and is marked split."""
    kinds = [r["kind"] for r in readings if r]
    if not kinds:
        return {"kind": None, "split": False, "n_parsed": 0}
    counts = Counter(kinds)
    top = max(counts.values())
    leaders = [k for k in kinds if counts[k] == top]
    return {"kind": leaders[0], "split": len(counts) > 1 and top * 2 <= len(kinds), "n_parsed": len(kinds),
            "unanimous": len(counts) == 1}


def summarize(records: dict) -> dict:
    counts = Counter(r["kind"] for r in records.values())
    return {k: counts.get(k, 0) for k in KIND_KEYS + [None] if counts.get(k, 0) or k is not None}


async def classify(roles: list[dict], n_readings: int, usage: MultiModelUsage, concurrency: int) -> dict:
    import anthropic
    from dotenv import load_dotenv
    from assistant_axis.gapgen.llm import call_anthropic_json
    load_dotenv()
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(concurrency)

    async def one(role: dict) -> tuple[str, dict]:
        readings, raw = [], []
        for _ in range(n_readings):
            async with sem:
                text = await call_anthropic_json(client, system=SYSTEM, user=user_message(role["label"], role["description"]),
                                                 model=MODEL, max_tokens=MAX_TOKENS, temperature=None, usage=usage)
            readings.append(parse_kind(text))
            raw.append(text)
        rec = combine(readings) | {"readings": readings, "unparsed": [t for t, r in zip(raw, readings) if r is None]}
        return role["stem"], rec

    return dict(await asyncio.gather(*(one(r) for r in roles)))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--names", nargs="+", help="only these role stems")
    ap.add_argument("--readings", type=int, default=3)
    ap.add_argument("--force", action="store_true", help="read roles again although their kind is on record")
    ap.add_argument("--dry-run", action="store_true", help="print a rendered prompt and the estimate; no calls")
    ap.add_argument("--budget-usd", type=float, default=3.0)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    existing = json.loads(OUT_PATH.read_text()) if OUT_PATH.exists() else {}
    same = existing.get("prompt_sha256") == PROMPT_SHA and existing.get("model") == MODEL
    records = dict(existing.get("roles", {})) if same else {}
    roles = load_roles(args.names)
    todo = [r for r in roles if args.force or r["stem"] not in records]
    from assistant_axis.judge_pricing import price_for_model
    rin, rout = price_for_model(MODEL)
    est = len(todo) * args.readings * (EST_IN * rin + EST_OUT * rout) / 1e6
    logger.info(f"{len(roles)} roles, {len(todo)} to classify x {args.readings} readings; estimate ${est:.2f}")
    if args.dry_run:
        sample = todo[0] if todo else roles[0]
        print("=== system ===\n" + SYSTEM + "\n=== user ===\n" + user_message(sample["label"], sample["description"]))
        return
    if est > args.budget_usd:
        raise SystemExit(f"estimate ${est:.2f} exceeds --budget-usd ${args.budget_usd:.2f}")
    usage = MultiModelUsage()
    try:
        new = asyncio.run(classify(todo, args.readings, usage, args.concurrency)) if todo else {}
    finally:
        logger.info(usage.log_line("[usage]"))
        if usage.n_calls:
            total = MultiModelUsage.load_or_create(USAGE_PATH)
            total.merge_from(usage)
            total.write_json(USAGE_PATH)
    from assistant_axis.judge import warn_if_low_parse_rate
    readings = [x for r in new.values() for x in r["readings"]]
    warn_if_low_parse_rate(label=f"classify_role_kinds:{MODEL}", n_ok=sum(1 for x in readings if x),
                           n_total=len(readings), logger_obj=logger)
    records.update(new)
    current = {p.stem for p in ROLES_DIR.glob("*.json")}
    records = {s: r for s, r in sorted(records.items()) if s in current}
    out = {"schema_version": 1, "model": MODEL, "prompt_sha256": PROMPT_SHA, "readings": args.readings,
           "kinds": [{"key": k, "name": n, "definition": d} for k, n, d in KINDS],
           "decided": "Roger, 2026-10-16: the nine kinds of the README sketch, one dimension",
           "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "counts": summarize(records), "n_split": sum(1 for r in records.values() if r.get("split")),
           "n_roles": len(records), "missing": sorted(current - set(records)), "roles": records}
    atomic_write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", OUT_PATH)
    logger.info(f"wrote {OUT_PATH.relative_to(ROOT)}: {out['counts']}; split {out['n_split']}; missing {len(out['missing'])}")


if __name__ == "__main__":
    main()
