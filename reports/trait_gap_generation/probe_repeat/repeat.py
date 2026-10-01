"""How far does the split repeat itself, and would a vote of three runs steady it?

Roger, 2026-09-30: "how much would running it 3 times per word increase our cost per thousand words?
How helpful would it be?"  Three runs cannot answer the second question, so this runs steps 1 to 3
and the same-sense check whole, on Haiku 4.5 at temperature 0, one item per call, REPEATS more times
on the 99 test words.  Each repeat writes its own record directory as soon as it ends:
probe_repeat/run_<n>/ (results.jsonl, responses.jsonl, usage.json, run.json).

    uv run python reports/trait_gap_generation/probe_repeat/repeat.py
"""
import asyncio, importlib.util, json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "probe_sonnet_move"))
from common import HAIKU, P, Caller, first_result, prompt_of, sha  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("probe_repeat"); logger.setLevel(logging.INFO)
OUT = P / "probe_repeat"
REPEATS = 6
BUDGET_EACH_USD = 1.0
STEPS = {"sense": "step1_sense", "established": "check_established", "vague": "check_vague", "kind": "step2_kind",
         "same_sense": "check_same_sense"}
PROMPTS = {k: prompt_of(v) for k, v in STEPS.items()}
spec = importlib.util.spec_from_file_location("join_reference", P / "split_reference" / "join_reference.py")
jr = importlib.util.module_from_spec(spec); spec.loader.exec_module(jr)
ON = {"trait", "membership"}


async def word_path(c: Caller, word: str, group: str) -> dict:
    sense = first_result(await c.ask(HAIKU, PROMPTS["sense"], {"id": 1, "label": word}, step="sense", max_tokens=1000))
    prim = [x for x in (sense.get("readings") or []) if isinstance(x, dict) and x.get("rank") == "primary"]

    async def checks(x):
        est, vag, kind = await asyncio.gather(
            c.ask(HAIKU, PROMPTS["established"], {"id": 1, "label": word, "first_thought": sense.get("first_thought"),
                                                   "reading": x["reading"]}, step="established", max_tokens=500),
            c.ask(HAIKU, PROMPTS["vague"], {"id": 1, "label": word, "reading": x["reading"]}, step="vague", max_tokens=500),
            c.ask(HAIKU, PROMPTS["kind"], {"id": 1, "label": word, "reading": x["reading"]}, step="kind", max_tokens=500))
        x["check_established"], x["check_vague"], x["kind_call"] = first_result(est), first_result(vag), first_result(kind)

    await asyncio.gather(*[checks(x) for x in prim])
    on = [x for x in prim if (x.get("check_established") or {}).get("established") != "stretched"
          and (x.get("kind_call") or {}).get("kind") in ON]
    same = None
    if len(on) >= 2:
        same = first_result(await c.ask(HAIKU, PROMPTS["same_sense"], {"id": 1, "label": word, "reading_1": on[0]["reading"],
                                                                     "reading_2": on[1]["reading"]}, step="same_sense", max_tokens=500))
    joined = jr.join(sense, (same or {}).get("relation"))
    errors = sum("error" in d for d in [sense] + [x.get(f) or {} for x in prim for f in ("check_established", "check_vague", "kind_call")]
                 + ([same] if same else []))
    return {"word": word, "group": group, "sense": sense, "same_sense_answer": same, "parse_errors": errors, **joined}


async def main() -> None:
    load_dotenv(".env")
    words = [json.loads(line) for line in open(P / "split_reference" / "expected_outcomes.jsonl", encoding="utf-8")]
    for n in range(1, REPEATS + 1):
        out = OUT / f"run_{n}"
        if (out / "results.jsonl").exists():
            print(f"run {n}: on record, skipped")
            continue
        c = Caller(BUDGET_EACH_USD)
        rows = []
        try:
            rows = await asyncio.gather(*[word_path(c, w["word"], w["group"]) for w in words])
        finally:
            c.write(out, {"what": "steps 1 to 3 and the same-sense check, whole, one item per call; one of several repeats",
                          "repeat": n, "model": HAIKU, "temperature": 0.0, "prompts": PROMPTS,
                          "prompt_sha256": {k: sha(v) for k, v in PROMPTS.items()}, "n_words": len(words),
                          "calls": {f"{s}:{m}": v for (s, m), v in sorted(c.n.items())}})
            with open(out / "results.jsonl", "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        calls = sum(c.n.values())
        warn_if_low_parse_rate(label=f"probe_repeat:run_{n}:{HAIKU}", n_ok=calls - sum(r["parse_errors"] for r in rows),
                               n_total=calls, logger_obj=logger)


asyncio.run(main())
