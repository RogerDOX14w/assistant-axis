"""Rewrite existing trait descriptions and recheck them (pre-extraction work list, 2026-10-09).

For a pole of a clean pair, the rewritten-pair procedure of AGENT_NOTES (§ "Why non-X first?"): set the
negative_label to non-X, regenerate in full, run the antonym check and record it, restore the partner's
label, regenerate with --instructions-only so the neg clause names the partner again.  For a trait that
is not a pair pole (mode "single"), regenerate under non-X, check, record, and leave it a non-X singleton.

    uv run python roger/pre_extraction_2026-10-09/rewrite_and_check.py EDITS.json --phase LABEL

EDITS.json: [{"stem": ..., "description": ..., "mode": "pair" | "single", "note": ...}, ...]
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402
from data_analysis import generate_antonyms as G  # noqa: E402
from data_analysis import seed_entities as SE  # noqa: E402

TRAITS = Path("data/traits/instructions")


def load(stem):
    return json.load(open(TRAITS / f"{stem}.json", encoding="utf-8"))


def save(stem, d):
    (TRAITS / f"{stem}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def regen(stems, instructions_only=False):
    cmd = ["uv", "run", "python", "data_analysis/regenerate_trait_instructions.py", "--traits", *stems, "--force"]
    if instructions_only:
        cmd.append("--instructions-only")
    subprocess.run(cmd, check=True)


async def check(docs):
    load_dotenv()
    client = anthropic.AsyncAnthropic(); sem = asyncio.Semaphore(10); usage = MultiModelUsage()

    async def one(stem, d):
        defn = G.extract_definition(d.get("eval_prompt", "")) or d.get("description", "")
        return stem, await G.classify_one(client, stem, defn, d["instruction"], sem, usage)
    out = dict(await asyncio.gather(*(one(s, d) for s, d in docs.items())))
    total = MultiModelUsage.load_or_create(G.DEFAULT_USAGE_JSON); total.merge_from(usage); total.write_json(G.DEFAULT_USAGE_JSON)
    print(usage.log_line("[usage]"))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("edits"); ap.add_argument("--phase", required=True)
    args = ap.parse_args()
    edits = json.load(open(args.edits, encoding="utf-8"))
    partner_label = {}
    for e in edits:
        d = load(e["stem"])
        partner_label[e["stem"]] = d["negative_label"]
        print(f"{e['stem']}: was {d['description']!r}")
        d["description"] = e["description"]
        d["negative_label"] = f"non-{d['positive_label']}"
        if e["mode"] == "single":
            d["arrangement"] = {"kind": "singleton", "note": e.get("note", "")}
        save(e["stem"], d)
    stems = [e["stem"] for e in edits]
    regen(stems)
    docs = {s: load(s) for s in stems}
    res = asyncio.run(check(docs))
    q = SE.load_queue(Path("data/seed_queue.json")); reg = SE.build_registry(q, Path("data")); hist = []
    for e in edits:
        s, r = e["stem"], res[e["stem"]]
        intended = partner_label[s] if e["mode"] == "pair" else None
        intended_stem = intended.lower().replace(" ", "_").replace("-", "_") if intended else None
        v = SE.classify_check(r.get("negative_label", ""), intended_stem, reg)
        hist.append(SE.check_history_record(s, docs[s], r, v, intended_stem, args.phase))
        print(f"{s:14s} -> {r.get('negative_label')} ({r.get('antonym_score')})  partner {intended}")
    SE.append_check_history(Path("data"), hist)
    pair_stems = [e["stem"] for e in edits if e["mode"] == "pair"]
    for s in pair_stems:
        d = load(s); d["negative_label"] = partner_label[s]; save(s, d)
    if pair_stems:
        regen(pair_stems, instructions_only=True)
    subprocess.run(["uv", "run", "python", "tools/sync_entity_lists.py"], check=True)
    subprocess.run(["uv", "run", "python", "data_analysis/check_arrangements.py"], check=True)


if __name__ == "__main__":
    main()
