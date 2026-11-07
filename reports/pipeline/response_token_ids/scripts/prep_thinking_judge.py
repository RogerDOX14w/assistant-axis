"""Build a responses directory whose assistant turns are the leaked-thinking
segments of the sample's stripped responses (decoded from the stored token
ids over thinking_token_range), laid out as step 3 expects (by_type/<kind>/
<entity>.jsonl), so that step 3 can score the thinking under the same judge
and rubric as the content.  Prints what the segments look like.
    uv run python prep_thinking_judge.py <sample tree> <out dir> <tokenizer.json>
"""
import json
import re
import statistics
import sys
from pathlib import Path

from tokenizers import Tokenizer

sample, out, tokpath = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(sample / "logs"))
from axis_projection_shift import KIND_OF  # noqa: E402

tok = Tokenizer.from_file(tokpath)
TAG = re.compile(r"</?think>")
shown = 0
rows = []
for f in sorted((sample / "responses").glob("*.jsonl")):
    e = f.stem
    recs = []
    for line in open(f):
        r = json.loads(line)
        if not r["thinking_stripped"]:
            continue
        ids = r["response_token_ids"]
        t0, t1 = r["thinking_token_range"]
        c0, c1 = r["content_token_range"]
        think_raw = tok.decode(ids[t0:t1], skip_special_tokens=False)
        content = tok.decode(ids[c0:c1], skip_special_tokens=True)
        stored = r["conversation"][-1]["content"]
        match = content.strip() == stored.strip()
        tags = bool(TAG.search(think_raw))
        think = TAG.sub("", think_raw).strip()
        rows.append((e, t1 - t0, c1 - c0, len(ids), r["finish_reason"] == "length", match, tags, len(think)))
        if shown < 5 and (shown < 3 or not match):
            shown += 1
            print(f"== {e} p{r['prompt_index']} q{r['question_index']} finish={r['finish_reason']} thinking {t1 - t0} tokens, "
                  f"content {c1 - c0} tokens, content matches stored: {match}, think tags: {tags}")
            print("   thinking head:", repr(think[:400]))
            print("   thinking tail:", repr(think[-200:]))
            print("   content head: ", repr(stored[:160]))
        rr = dict(r)
        conv = [dict(m) for m in r["conversation"]]
        conv[-1]["content"] = think
        rr["conversation"] = conv
        rr["judged_segment"] = "thinking"
        rr["thinking_had_tags"] = tags
        rr["content_text"] = stored
        recs.append(rr)
    if recs:
        d = out / "by_type" / KIND_OF[e]
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"{e}.jsonl", "w") as fh:
            for rr in recs:
                fh.write(json.dumps(rr, ensure_ascii=False) + "\n")
print(f"\n{len(rows)} stripped responses written under {out / 'by_type'}")
print(f"{'entity':26} {'n':>3} {'think tok med':>13} {'content tok med':>15} {'capped':>6} {'match':>5} {'tags':>4} {'think chars med':>15}")
for e in sorted({r[0] for r in rows}, key=lambda x: -sum(1 for r in rows if r[0] == x)):
    rs = [r for r in rows if r[0] == e]
    print(f"{e:26} {len(rs):3d} {statistics.median(r[1] for r in rs):13.0f} {statistics.median(r[2] for r in rs):15.0f} "
          f"{sum(r[4] for r in rs):6d} {sum(r[5] for r in rs):5d} {sum(r[6] for r in rs):4d} {statistics.median(r[7] for r in rs):15.0f}")
print(f"all: thinking tokens median {statistics.median(r[1] for r in rows):.0f}, content tokens median {statistics.median(r[2] for r in rows):.0f}; "
      f"thinking share of the turn median {statistics.median(r[1] / r[3] for r in rows):.2f}; "
      f"content matches stored text in {sum(r[5] for r in rows)} of {len(rows)}; tags in {sum(r[6] for r in rows)}")
