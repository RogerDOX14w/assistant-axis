"""Backfill ``finish_reason`` on the May 2026 response copies of the trait rubric review (Roger, 2026-10-28, option
1): step 3's ``--mark_truncated`` shows the judge a response cut at step 1's ``--max_tokens`` with " …" appended,
keyed on the record's ``finish_reason``, which generation has written only since 2026-10-12.  The May records have
none.  vLLM stops a generation at exactly ``max_tokens`` tokens, so a response whose text tokenises to the cap or
more was cut (``length``), and one that stopped on its own has at most cap - 1 text tokens plus the end token
(``stop``).  The May cap was step 1's default, 512.

Each record gets ``finish_reason`` and a ``finish_reason_backfilled`` block (method, cap, token count, tokenizer
path), so a backfilled value is never mistaken for one vLLM wrote.  Records that already carry ``finish_reason``
are left alone unless ``--force``.  ``--dry_run`` prints the token-count distribution and writes nothing: the
check that the tokenizer matches is a sharp spike at exactly the cap.

    uv run python reports/pipeline/trait_rubric_review/backfill_finish_reason.py [--dry_run] [--force]
"""
import argparse
import json
import os
from collections import Counter
from pathlib import Path

from tokenizers import Tokenizer

CAP = 512
TOKENIZER = Path("data/external/hf/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca/"
                 "tokenizer.json")   # the Qwen3 family shares one tokenizer
DIRS = [Path("runpod_workspace/rubric_exp/held_traits/responses"),
        Path("runpod_workspace/rubric_exp/held_traits_tiers/responses")]


def answer(rec: dict) -> str:
    return next(m["content"] for m in reversed(rec["conversation"]) if m["role"] == "assistant")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry_run", action="store_true")
    ap.add_argument("--force", action="store_true", help="recompute records that already have finish_reason")
    ap.add_argument("--cap", type=int, default=CAP)
    args = ap.parse_args()
    tok = Tokenizer.from_file(str(TOKENIZER))
    hist: Counter = Counter()
    per_file = {}
    for d in DIRS:
        for p in sorted(d.glob("*.jsonl")):
            recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            n_len = n_skip = n_think = 0
            for r in recs:
                if "finish_reason" in r and not args.force and "finish_reason_backfilled" not in r:
                    n_skip += 1
                    continue
                text = answer(r)
                n = len(tok.encode(text, add_special_tokens=False).ids)
                hist[min(n, args.cap + 5)] += 1
                if "<think>" in text:
                    n_think += 1
                cut = n >= args.cap
                n_len += cut
                r["finish_reason"] = "length" if cut else "stop"
                r["finish_reason_backfilled"] = {"method": "token_count", "cap": args.cap, "n_tokens": n,
                                                 "tokenizer": str(TOKENIZER), "date": "2026-10-28"}
            per_file[f"{d.parent.name}/{p.stem}"] = (len(recs), n_len, n_skip, n_think)
            if not args.dry_run:
                tmp = p.with_suffix(".jsonl.tmp")
                tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
                os.replace(tmp, p)
    tot = sum(hist.values())
    print(f"{tot} responses tokenised; share at or over the cap {sum(v for k, v in hist.items() if k >= args.cap) / tot:.1%}")
    print("token count near the cap (count >= cap+5 pooled):")
    for k in range(args.cap - 6, args.cap + 6):
        print(f"  {k:4d}{'+' if k == args.cap + 5 else ' '} {hist.get(k, 0):6d}")
    below = {k: v for k, v in hist.items() if k < args.cap - 6}
    print(f"  below {args.cap - 6}: {sum(below.values())} (max there {max(below) if below else '-'})")
    print("\nper file: n, cut, skipped (had finish_reason), with <think>")
    for name, (n, c, s, t) in per_file.items():
        print(f"  {name:36s} {n:4d} {c:4d} {s:4d} {t:3d}")
    print("\n(dry run, nothing written)" if args.dry_run else "\nwritten in place")


if __name__ == "__main__":
    main()
