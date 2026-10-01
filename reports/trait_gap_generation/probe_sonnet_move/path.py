"""Part A: the second-opinion path.  Steps 1 to 3 of the split, and the same-sense check, run whole
on Sonnet 4.6 and on Sonnet 5.5 for the 99 test words, one item per call.  Each model reads its own
step 1 answer, as a second opinion would.  Records go to probe_sonnet_move/path/.

    uv run python reports/trait_gap_generation/probe_sonnet_move/path.py
"""
import asyncio, importlib.util, json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NEW, OLD, P, Caller, first_result, prompt_of, sha  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("probe_sonnet_move.path"); logger.setLevel(logging.INFO)
OUT = P / "probe_sonnet_move" / "path"
BUDGET_USD = 6.0
STEPS = {"sense": "step1_sense", "established": "check_established", "vague": "check_vague", "kind": "step2_kind",
         "same_sense": "check_same_sense"}
PROMPTS = {k: prompt_of(v) for k, v in STEPS.items()}
spec = importlib.util.spec_from_file_location("join_reference", P / "split_reference" / "join_reference.py")
jr = importlib.util.module_from_spec(spec); spec.loader.exec_module(jr)
ON = {"trait", "membership"}


async def word_path(c: Caller, model: str, word: str, group: str) -> dict:
    sense = first_result(await c.ask(model, PROMPTS["sense"], {"id": 1, "label": word}, step="sense", max_tokens=700))
    rs = sense.get("readings") or []
    prim = [x for x in rs if isinstance(x, dict) and x.get("rank") == "primary"]

    async def checks(x):
        est, vag, kind = await asyncio.gather(
            c.ask(model, PROMPTS["established"], {"id": 1, "label": word, "first_thought": sense.get("first_thought"),
                                                   "reading": x["reading"]}, step="established", max_tokens=300),
            c.ask(model, PROMPTS["vague"], {"id": 1, "label": word, "reading": x["reading"]}, step="vague", max_tokens=300),
            c.ask(model, PROMPTS["kind"], {"id": 1, "label": word, "reading": x["reading"]}, step="kind", max_tokens=300))
        x["check_established"], x["check_vague"], x["kind_call"] = first_result(est), first_result(vag), first_result(kind)

    await asyncio.gather(*[checks(x) for x in prim])
    on = [x for x in prim if (x.get("check_established") or {}).get("established") != "stretched"
          and (x.get("kind_call") or {}).get("kind") in ON]
    same = None
    if len(on) >= 2:
        same = first_result(await c.ask(model, PROMPTS["same_sense"], {"id": 1, "label": word, "reading_1": on[0]["reading"],
                                                                     "reading_2": on[1]["reading"]}, step="same_sense", max_tokens=300))
    joined = jr.join(sense, (same or {}).get("relation"))
    return {"word": word, "group": group, "model": model, "sense": sense, "same_sense": same, **joined}


def parse_counts(rows: list[dict]) -> dict:
    n = {k: [0, 0] for k in STEPS}
    for r in rows:
        n["sense"][1] += 1; n["sense"][0] += "error" not in r["sense"]
        for x in r["sense"].get("readings") or []:
            for k, f in (("established", "check_established"), ("vague", "check_vague"), ("kind", "kind_call")):
                if isinstance(x, dict) and f in x:
                    n[k][1] += 1; n[k][0] += "error" not in x[f]
        if r["same_sense"] is not None:
            n["same_sense"][1] += 1; n["same_sense"][0] += "error" not in r["same_sense"]
    return n


async def main() -> None:
    load_dotenv(".env")
    words = [json.loads(line) for line in open(P / "split_reference" / "expected_outcomes.jsonl", encoding="utf-8")]
    c = Caller(BUDGET_USD)
    res = {}
    try:
        for model in (OLD, NEW):
            res[model] = await asyncio.gather(*[word_path(c, model, w["word"], w["group"]) for w in words])
    finally:
        c.write(OUT, {"what": "steps 1 to 3 and the same-sense check, whole, one item per call, on two models",
                      "models": [OLD, NEW], "temperature": {OLD: 0.0, NEW: "not sent: the model refuses it"},
                      "prompts": PROMPTS, "prompt_sha256": {k: sha(v) for k, v in PROMPTS.items()}, "n_words": len(words),
                      "calls": {f"{s}:{m}": v for (s, m), v in sorted(c.n.items())}})
    for model, rows in res.items():
        with open(OUT / f"results_{model}.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        for k, (ok, tot) in parse_counts(rows).items():
            warn_if_low_parse_rate(label=f"probe_sonnet_move:path:{k}:{model}", n_ok=ok, n_total=tot, logger_obj=logger)


asyncio.run(main())
