"""Checks the three rubric edits of 2026-09-30 against the answers their earlier drafts gave on the
same inputs, one item per call.  Each part keeps its own records:

  gloss/        gloss draft 3 (the fact comes before the length) on the 74 readings of probe_gloss_v2,
                on Haiku 4.5 and on Sonnet 5.5; earlier glosses from probe_sonnet_move/gloss
  same_sense/   same-sense draft 2 (example words replaced) on the 30 pairs of probe_same_sense
  alignment/    alignment draft 2 (example word replaced) on the glosses of the live pilot

    uv run python reports/trait_gap_generation/probe_rubric_edits/probe.py
"""
import asyncio, json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "probe_sonnet_move"))
from common import HAIKU, NEW, P, Caller, first_result, prompt_of, sha  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("probe_rubric_edits"); logger.setLevel(logging.INFO)
OUT = P / "probe_rubric_edits"


def jl(p):
    return [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]


def save(c: Caller, out: Path, rows: list[dict], run: dict) -> None:
    c.write(out, {**run, "calls": {f"{s}:{m}": v for (s, m), v in sorted(c.n.items())}})
    with open(out / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


async def gloss() -> None:
    prompt = prompt_of("gloss")
    src = jl(P / "probe_sonnet_move" / "gloss" / "results.jsonl")
    c, rows = Caller(1.0), []
    try:
        async def one(r):
            h, s = await asyncio.gather(*[c.ask(m, prompt, {"id": 1, "label": r["word"], "reading": r["reading"]}, step="gloss", max_tokens=500)
                                          for m in (HAIKU, NEW)])
            return {"word": r["word"], "kind": r["kind"], "reading": r["reading"], "draft2_haiku": r["haiku"], "draft2_sonnet55": r["new"],
                    "draft3_haiku": first_result(h).get("gloss"), "draft3_sonnet55": first_result(s).get("gloss")}
        rows = await asyncio.gather(*[one(r) for r in src])
    finally:
        save(c, OUT / "gloss", rows, {"what": "gloss draft 3 on the 74 readings, two models", "models": [HAIKU, NEW],
                                      "prompt": prompt, "prompt_sha256": sha(prompt)})
    for k in ("draft3_haiku", "draft3_sonnet55"):
        warn_if_low_parse_rate(label=f"probe_rubric_edits:gloss:{k}", n_ok=sum(1 for r in rows if r[k]), n_total=len(rows), logger_obj=logger)


async def same_sense() -> None:
    prompt = prompt_of("check_same_sense")
    src = jl(P / "probe_same_sense" / "results.jsonl")
    c, rows = Caller(0.3), []
    try:
        async def one(r):
            a = first_result(await c.ask(HAIKU, prompt, {"id": 1, "label": r["word"], "reading_1": r["a"], "reading_2": r["b"]},
                                         step="same_sense", max_tokens=500))
            return {"word": r["word"], "a": r["a"], "b": r["b"], "draft1": r["relation"], "draft2": a.get("relation"), "reason": a.get("reason")}
        rows = await asyncio.gather(*[one(r) for r in src])
    finally:
        save(c, OUT / "same_sense", rows, {"what": "same-sense draft 2 on the 30 pairs", "model": HAIKU, "prompt": prompt, "prompt_sha256": sha(prompt)})
    warn_if_low_parse_rate(label="probe_rubric_edits:same_sense", n_ok=sum(1 for r in rows if r["draft2"]), n_total=len(rows), logger_obj=logger)


async def alignment() -> None:
    prompt = prompt_of("alignment")
    src = [r for r in jl(Path("data/candidates/filter/split_pilot_live/results.jsonl"))
           if (r.get("filter") or {}).get("outcome") == "trait" and r.get("gloss")]
    c, rows = Caller(0.3), []
    try:
        async def one(r):
            a = first_result(await c.ask(HAIKU, prompt, {"id": 1, "label": r["label"], "description": r["gloss"]}, step="alignment", max_tokens=500))
            return {"word": r["label"], "gloss": r["gloss"], "draft1": r["filter"].get("alignment_relevant"),
                    "draft2": a.get("alignment_relevant"), "reason": a.get("reason")}
        rows = await asyncio.gather(*[one(r) for r in src])
    finally:
        save(c, OUT / "alignment", rows, {"what": "alignment draft 2 on the live pilot's glosses", "model": HAIKU, "prompt": prompt,
                                          "prompt_sha256": sha(prompt)})
    warn_if_low_parse_rate(label="probe_rubric_edits:alignment", n_ok=sum(1 for r in rows if r["draft2"] is not None), n_total=len(rows),
                           logger_obj=logger)


async def main() -> None:
    load_dotenv(".env")
    await gloss()
    await same_sense()
    await alignment()


asyncio.run(main())
