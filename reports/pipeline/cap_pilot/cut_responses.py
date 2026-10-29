"""Cap pilot: the cap1024 responses cut at 256, 512 and 768 tokens (Roger, 2026-10-29).

Responses often run preamble, details, summing up, and a trait may show only in the first and the
last; a cut at the cap loses the summing up.  The model is not told the cap, so the first N tokens
of a cap1024 response are distributed as a capN response, and judging the cut response against the
whole one measures, pair by pair, what a cut at N costs the judge's verdict, without the sampling
noise between trees.  (cap512's own responses against cap1024 cut at 512 check that equivalence.)

Writes ``<root>/cap1024_cut<N>/responses/<name>.jsonl`` holding only the responses of N or more
content tokens (a shorter one is unchanged at cap N and keeps the whole response's score; one of
exactly N tokens would be cut there too, before its end-of-turn token), each with its assistant
turn cut to its first N tokens, ``finish_reason`` ``"length"`` (so step 3 shows the judge the cut
marker) and ``cut_tokens`` / ``whole_tokens`` / ``whole_finish_reason``.  A response whose leaked
thinking step 1 stripped (``thinking_stripped``) is left out: its generated tokens included the
thinking.  Roles and traits only; the combinations wait for their new rubric.  An entity with no
response that long gets no file.

First checks the token count on cap256: a response cut there has 256 content tokens when the text
re-tokenizes to the generated tokens (2026-10-29: 16,610 of 16,682, the rest within 2).  Run on the
pod, from the checkout, with the pod's environment (without pod_env.sh, uv builds a 15-GB .venv in
the checkout on the network volume):

    source /workspace/pod_env.sh
    HF_HOME=/dev/shm/hf-cache HF_HUB_OFFLINE=1 uv run python <this file> /workspace/cap_pilot
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer

from assistant_axis.atomic_io import read_jsonl_with_retry, write_jsonl

CUTS = (256, 512, 768)
TYPES = ("role", "trait")
ENTITIES = Path("reports/pipeline/cap_pilot_entities.json")


def content_ids(tok, r):
    return tok.encode(r["conversation"][-1]["content"], add_special_tokens=False)


def check_counting(tok, root: Path, names) -> None:
    counts = collections.Counter()
    for name in names:
        for r in read_jsonl_with_retry(root / "cap256" / "responses" / f"{name}.jsonl"):
            if r.get("finish_reason") == "length" and not r.get("thinking_stripped"):
                counts[len(content_ids(tok, r)) - 256] += 1
    n = sum(counts.values())
    print(f"cap256, cut responses: re-tokenized length minus 256: "
          + ", ".join(f"{k:+d}: {v}" for k, v in sorted(counts.items())) + f" (of {n})")
    if counts[0] < 0.95 * n:
        sys.exit("fewer than 95% re-tokenize to 256 tokens: the cut would not match a cap256 response")


def main() -> None:
    root = Path(sys.argv[1])
    by_type = json.loads(ENTITIES.read_text())["by_type"]
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-32B")
    check_counting(tok, root, [n for t in TYPES for n in by_type[t]])
    for t in TYPES:
        kept = collections.Counter()
        skipped = 0
        for name in by_type[t]:
            out = {n: [] for n in CUTS}
            for r in read_jsonl_with_retry(root / "cap1024" / "responses" / f"{name}.jsonl"):
                if r.get("thinking_stripped"):
                    skipped += 1
                    continue
                ids = content_ids(tok, r)
                for n in CUTS:
                    if len(ids) < n:
                        continue
                    # a cut inside a multi-byte character decodes to U+FFFD
                    text = tok.decode(ids[:n]).rstrip("�")
                    conv = [dict(m) for m in r["conversation"]]
                    conv[-1]["content"] = text
                    out[n].append({**r, "conversation": conv, "finish_reason": "length",
                                   "cut_tokens": n, "whole_tokens": len(ids),
                                   "whole_finish_reason": r.get("finish_reason")})
            for n in CUTS:
                kept[n] += len(out[n])
                if out[n]:
                    d = root / f"cap1024_cut{n}" / "responses"
                    d.mkdir(parents=True, exist_ok=True)
                    write_jsonl(out[n], d / f"{name}.jsonl")
        print(f"{t}: cut responses " + ", ".join(f"at {n}: {kept[n]}" for n in CUTS)
              + f" (of {500 * len(by_type[t])}; {skipped} with stripped thinking left out)")


if __name__ == "__main__":
    main()
