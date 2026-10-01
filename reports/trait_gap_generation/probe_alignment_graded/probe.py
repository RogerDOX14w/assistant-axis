"""The alignment check on a scale of 0 to 3 (alignment_graded_draft.md), run once on the glosses of
the live pilot, one item per call, beside the yes or no answers the pilot recorded.

    uv run python reports/trait_gap_generation/probe_alignment_graded/probe.py
"""
import asyncio, json, logging, re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "probe_sonnet_move"))
from common import HAIKU, P, Caller, first_result, sha  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("probe_alignment_graded"); logger.setLevel(logging.INFO)
OUT = P / "probe_alignment_graded"
PROMPT = re.search(r"## The prompt\n\n````text\n(.*?)\n````", (P / "alignment_graded_draft.md").read_text(encoding="utf-8"), re.S).group(1)


async def main() -> None:
    load_dotenv(".env")
    src = [json.loads(line) for line in open("data/candidates/filter/split_pilot_live/results.jsonl", encoding="utf-8")]
    src = [r for r in src if (r.get("filter") or {}).get("outcome") == "trait" and r.get("gloss")]
    c, rows = Caller(0.3), []
    try:
        async def one(r):
            a = first_result(await c.ask(HAIKU, PROMPT, {"id": 1, "label": r["label"], "description": r["gloss"]}, step="alignment_graded",
                                         max_tokens=500))
            v = a.get("alignment")
            return {"word": r["label"], "gloss": r["gloss"], "yes_or_no": r["filter"].get("alignment_relevant"),
                    "yes_or_no_reason": (r["filter"].get("last_step_reasons") or {}).get("alignment"),
                    "scale": v if v in (0, 1, 2, 3) else None, "reason": a.get("reason"), "error": a.get("error")}
        rows = await asyncio.gather(*[one(r) for r in src])
    finally:
        c.write(OUT, {"what": "alignment on a scale of 0 to 3, one item per call, on the live pilot's glosses", "model": HAIKU,
                      "temperature": 0.0, "prompt": PROMPT, "prompt_sha256": sha(PROMPT), "n": len(src)})
        with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    warn_if_low_parse_rate(label=f"probe_alignment_graded:{HAIKU}", n_ok=sum(1 for r in rows if r["scale"] is not None), n_total=len(rows),
                           logger_obj=logger)
    print("scale:", dict(sorted(Counter(r["scale"] for r in rows).items(), key=lambda kv: str(kv[0]))))
    print("scale by the yes or no answer:", dict(Counter((r["yes_or_no"], r["scale"]) for r in rows)))
    for v in (3, 2, 1):
        print(v, ":", ", ".join(sorted(r["word"] for r in rows if r["scale"] == v)))


asyncio.run(main())
