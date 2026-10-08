"""Apply Roger's description re-edits (chunk 4, step 3 of his method) to the corpus
files and the queue, then regenerate the edited files.

Input: a JSON object {stem: new_description, ...}.  For each stem the corpus
file's `description` is replaced (the regenerator rebuilds the eval prompt and
the instructions and questions from it), the queue entry gets `description`
and an `edits` list recording the previous text and the date, and the file is
regenerated with the default style (the openings check applies).  Lists are
re-synced.

    uv run python roger/chunk4_2026-10-07/apply_edits.py roger/chunk4_2026-10-07/edits_round1.json [--dry-run]
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import regenerate_trait_instructions as gen  # noqa: E402
from data_analysis import seed_entities as SE  # noqa: E402

QUEUE = Path("data/seed_queue.json")
CORPUS = Path("data/traits/instructions")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("edits")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--by", default="Roger's step-3 decision",
                    help="who decided the edit, recorded in the queue entry's `edits` list")
    ap.add_argument("--max-words", type=int, default=32,
                    help="upper length bound (32 = the corpus p90; raise where the words buy fidelity, "
                         "as Roger allowed for the MBTI set)")
    args = ap.parse_args()
    edits = json.load(open(args.edits, encoding="utf-8"))
    q = SE.load_queue(QUEUE)
    by_stem = {e["stem"]: e for e in q["entries"]}
    today = datetime.date.today().isoformat()
    for stem, text in edits.items():
        text = " ".join(text.split())
        path = CORPUS / f"{stem}.json"
        doc = json.load(open(path, encoding="utf-8"))
        n = len(text.split())
        assert 18 <= n <= args.max_words and text.startswith("This means"), (stem, n)
        print(f"{stem:32s} {n:2d} words\n   was: {doc['description']}\n   now: {text}")
        if args.dry_run:
            continue
        e = by_stem[stem]
        e.setdefault("edits", []).append({"date": today, "was": doc["description"], "by": args.by})
        e["description"] = text
        doc["description"] = text
        gen.atomic_write_json(path, doc)
    if args.dry_run:
        return
    SE.save_queue(q, QUEUE)
    cmd = ["uv", "run", "python", "data_analysis/regenerate_trait_instructions.py", "--traits", *edits, "--force"]
    r = subprocess.run(cmd, text=True, capture_output=True)
    print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if "HTTP Request" not in l)[-800:])
    if r.returncode != 0:
        raise SystemExit("regeneration failed")
    subprocess.run(["uv", "run", "python", "tools/sync_entity_lists.py"], check=True, capture_output=True)
    print(f"regenerated {len(edits)} files; lists synced")


if __name__ == "__main__":
    main()
