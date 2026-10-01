"""Part C: the comparison call (plain reading against intended meaning; prompt version 2, frozen).
The same label, plain reading and intended meaning that Sonnet 4.6 judged in the recorded runs are
sent again, one item per call, to Sonnet 4.6 and to Sonnet 5.5.  The expected answers are those of
the pairs files: a label against its own description is "same", against another trait's description
"different", and the six September rejects are "different" by Roger's rejection of them (the
platform's target is that four of the six are flagged).  The two sets are run apart and keep separate
records, probe_sonnet_move/comparison_dev/ and probe_sonnet_move/comparison_heldout/.

    uv run python reports/trait_gap_generation/probe_sonnet_move/comparison.py dev
    uv run python reports/trait_gap_generation/probe_sonnet_move/comparison.py heldout
"""
import asyncio, json, logging, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NEW, OLD, P, Caller, sha  # noqa: E402
from assistant_axis.gapgen import plain_reading as pr  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("probe_sonnet_move.comparison"); logger.setLevel(logging.INFO)
SET = sys.argv[1]
assert SET in ("dev", "heldout"), SET
OUT = P / "probe_sonnet_move" / f"comparison_{SET}"
RUNS = Path("data/candidates/plain_reading")
BUDGET_USD = 2.0


def recorded() -> tuple[dict, list[str]]:
    """key -> the row of the latest recorded run that compared it with prompt version 2 on Sonnet
    4.6 and carries an expected answer.  Corpus runs and copies set aside are skipped."""
    rows, used = {}, []
    for rj in sorted(RUNS.glob("*/run.json"), key=lambda p: json.loads(p.read_text(encoding="utf-8")).get("started_at") or ""):
        run = json.loads(rj.read_text(encoding="utf-8"))
        if ".bak." in rj.parent.name or (run.get("versions") or {}).get("comparison") != pr.COMPARISON_VERSION:
            continue
        if run.get("compare_model") != OLD or (run.get("prompt_sha256") or {}).get("comparison") != pr.PROMPT_SHA256["comparison"]:
            continue
        res = rj.parent / "results.jsonl"
        if not res.exists():
            continue
        n = 0
        for line in res.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            held = r["key"].endswith("#heldout")
            if held != (SET == "heldout"):
                continue
            exp = "different" if held else (r.get("meta") or {}).get("expected")
            if exp in pr.RELATIONS and r.get("reading") and (r.get("comparison") or {}).get("relation"):
                rows[r["key"]] = {"key": r["key"], "label": r["label"], "intended": r["intended"], "reading": r["reading"],
                                  "expected": exp, "set": SET,
                                  "recorded_run": rj.parent.name, "recorded_batched": r["comparison"]["relation"]}
                n += 1
        if n:
            used.append(f"{rj.parent.name} ({n} rows)")
    return rows, used


async def main() -> None:
    load_dotenv(".env")
    rows, used = recorded()
    print("recorded runs used:", used)
    if not rows:
        raise SystemExit("no recorded comparison run with an expected answer was found")
    c = Caller(BUDGET_USD)
    items = list(rows.values())
    try:
        async def one(it, model, tag):
            user = pr.build_compare_prompt([{"id": 1, "label": it["label"], "plain_reading": it["reading"], "intended_meaning": it["intended"]}])
            raw = await c.ask(model, pr.COMPARISON_PROMPT, user, step="comparison", max_tokens=400, raw_user=True)
            got, errs = pr.parse_compare(raw or "", [1], labels={1: it["label"]})
            it[tag] = got.get(1) or {"error": errs.get(1)}
        await asyncio.gather(*[one(it, m, t) for it in items for m, t in ((OLD, "old"), (NEW, "new"))])
    finally:
        c.write(OUT, {"what": "comparison prompt version 2, one item per call, on two models, inputs taken from recorded runs",
                      "models": {"old": OLD, "new": NEW}, "recorded_runs": used, "prompt_sha256": {"comparison": sha(pr.COMPARISON_PROMPT)},
                      "comparison_version": pr.COMPARISON_VERSION, "n_rows": len(items),
                      "calls": {f"{s}:{m}": v for (s, m), v in sorted(c.n.items())}})
        with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    for tag, model in (("old", OLD), ("new", NEW)):
        warn_if_low_parse_rate(label=f"probe_sonnet_move:comparison:{model}", n_ok=sum(1 for it in items if (it.get(tag) or {}).get("relation")),
                               n_total=len(items), logger_obj=logger)


asyncio.run(main())
