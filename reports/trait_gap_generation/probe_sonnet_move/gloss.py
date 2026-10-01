"""Part B: the gloss.  Sonnet 5.5 writes the gloss for the same 74 labels and readings that Sonnet
4.6 glossed in probe_gloss_v2, under the same prompt (gloss draft 2).  A third model, which is told
nothing of who wrote what, then says which of each pair keeps the rules better; every pair is judged
twice, once in each order, so that a liking for the first or second place cancels.  Records go to
probe_sonnet_move/gloss/.

    uv run python reports/trait_gap_generation/probe_sonnet_move/gloss.py
"""
import asyncio, json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import JUDGE, NEW, OLD, P, Caller, first_result, prompt_of, sha  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("probe_sonnet_move.gloss"); logger.setLevel(logging.INFO)
OUT = P / "probe_sonnet_move" / "gloss"
BUDGET_USD = 4.0
GLOSS = prompt_of("gloss")
RULES = GLOSS[GLOSS.index("How to write it:"): GLOSS.index("Respond with one JSON object")].strip()
JUDGE_PROMPT = f"""Two one-sentence descriptions were written for the same label and the same reading of the instruction "You are <label>." Each writer was given the label, the reading and these rules.

{RULES}

Each item gives the label, the reading, and the two descriptions, A and B. Say which description keeps the rules better and states the reading more exactly. If neither is better, answer "tie".

For each item give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{{"results": [{{"id": <int>, "reason": "<one short sentence>", "better": "A"|"B"|"tie"}}]}}
Return one row per id, in the order given."""


async def main() -> None:
    load_dotenv(".env")
    rows = [json.loads(line) for line in open(P / "probe_gloss_v2" / "results.jsonl", encoding="utf-8")]
    c = Caller(BUDGET_USD)
    out = []
    try:
        async def write(r):
            g = first_result(await c.ask(NEW, GLOSS, {"id": 1, "label": r["word"], "reading": r["reading"]}, step="gloss", max_tokens=300))
            return {"word": r["word"], "group": r["group"], "reading": r["reading"], "kind": r["kind"],
                    "haiku": r["gloss_draft2_haiku"], "old": r["gloss_draft2_sonnet"], "new": g.get("gloss"), "error": g.get("error")}
        out = await asyncio.gather(*[write(r) for r in rows])

        async def judge(o, new_is_a: bool):
            a, b = (o["new"], o["old"]) if new_is_a else (o["old"], o["new"])
            j = first_result(await c.ask(JUDGE, JUDGE_PROMPT, {"id": 1, "label": o["word"], "reading": o["reading"], "A": a, "B": b},
                                         step="judge", max_tokens=300))
            v = j.get("better")
            o.setdefault("judged", []).append({"new_is": "A" if new_is_a else "B", "better": v, "reason": j.get("reason"), "error": j.get("error"),
                                               "winner": None if v not in ("A", "B", "tie") else "tie" if v == "tie"
                                               else "new" if (v == "A") == new_is_a else "old"})
        todo = [o for o in out if o["new"] and o["old"] and o["new"].strip() != o["old"].strip()]
        await asyncio.gather(*[judge(o, flag) for o in todo for flag in (True, False)])
    finally:
        c.write(OUT, {"what": "gloss draft 2 on Sonnet 5.5, and a blind judgement of each pair in both orders",
                      "writers": {"old": OLD, "new": NEW}, "judge": JUDGE, "prompts": {"gloss": GLOSS, "judge": JUDGE_PROMPT},
                      "prompt_sha256": {"gloss": sha(GLOSS), "judge": sha(JUDGE_PROMPT)}, "n_words": len(rows),
                      "calls": {f"{s}:{m}": v for (s, m), v in sorted(c.n.items())}})
        with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
            for o in out:
                fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    warn_if_low_parse_rate(label=f"probe_sonnet_move:gloss:{NEW}", n_ok=sum(1 for o in out if o["new"]), n_total=len(out), logger_obj=logger)
    js = [j for o in out for j in o.get("judged", [])]
    warn_if_low_parse_rate(label=f"probe_sonnet_move:judge:{JUDGE}", n_ok=sum(1 for j in js if j["winner"]), n_total=len(js), logger_obj=logger)


asyncio.run(main())
