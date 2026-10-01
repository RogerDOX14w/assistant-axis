"""The alignment check on a scale (alignment_graded_draft.md), one item per call on Haiku 4.5, on a
named source, with its own record directory for each run so no run overwrites another.

    uv run python reports/trait_gap_generation/probe_alignment_graded/run.py TAG SOURCE

TAG names the record directory, probe_alignment_graded/<TAG>/.  SOURCE is one of:
  pilot    the glosses of the live pilot (69 words that went on as traits)
  corpus   every corpus trait with its own description (the worktree's copy of the corpus)
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
TAG, SOURCE = sys.argv[1], sys.argv[2]
OUT = P / "probe_alignment_graded" / TAG
PROMPT = re.search(r"## The prompt\n\n````text\n(.*?)\n````", (P / "alignment_graded_draft.md").read_text(encoding="utf-8"), re.S).group(1)


def items() -> list[dict]:
    if SOURCE == "pilot":
        src = [json.loads(line) for line in open("data/candidates/filter/split_pilot_live/results.jsonl", encoding="utf-8")]
        return [{"key": r["label"], "label": r["label"], "description": r["gloss"], "yes_or_no": r["filter"].get("alignment_relevant")}
                for r in src if (r.get("filter") or {}).get("outcome") == "trait" and r.get("gloss")]
    if SOURCE == "corpus":
        out = []
        for f in sorted(Path("data/traits/instructions").glob("*.json")):
            j = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(j, dict) and j.get("description") and j.get("positive_label"):
                out.append({"key": f.stem, "label": j["positive_label"], "description": j["description"], "yes_or_no": None})
        return out
    raise SystemExit(f"unknown source {SOURCE!r}")


async def main() -> None:
    load_dotenv(".env")
    if (OUT / "results.jsonl").exists():
        raise SystemExit(f"{OUT} already holds a run; choose another tag")
    src = items()
    c, rows = Caller(1.5), []
    try:
        async def one(r):
            a = first_result(await c.ask(HAIKU, PROMPT, {"id": 1, "label": r["label"], "description": r["description"]},
                                         step="alignment_graded", max_tokens=500))
            v = a.get("alignment")
            return {**r, "scale": v if v in (0, 1, 2, 3) else None, "reason": a.get("reason"), "error": a.get("error")}
        rows = await asyncio.gather(*[one(r) for r in src])
    finally:
        c.write(OUT, {"what": "alignment on a scale of 0 to 3, one item per call", "source": SOURCE, "model": HAIKU,
                      "temperature": 0.0, "prompt": PROMPT, "prompt_sha256": sha(PROMPT), "n": len(src)})
        with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    warn_if_low_parse_rate(label=f"probe_alignment_graded:{TAG}:{HAIKU}", n_ok=sum(1 for r in rows if r["scale"] is not None),
                           n_total=len(rows), logger_obj=logger)
    print("scale:", dict(sorted(Counter(r["scale"] for r in rows).items(), key=lambda kv: str(kv[0]))))


asyncio.run(main())
