"""Shared pieces of the Sonnet 4.6 against Sonnet 5.5 check (Roger, 2026-09-29: "For everything we
moved from 4.6 to 5.5, let's do a sanity comparison that it's still working correctly, ideally one
that could tell if it had got better, as well as if it had got worse").

Each part writes into its own directory, with its own run.json, usage.json, responses.jsonl and
results files, so that no part can overwrite another's record."""
import asyncio, hashlib, json, re
from pathlib import Path
import anthropic
from assistant_axis import judge_pricing as jp
from assistant_axis.judge_pricing import MultiModelUsage

P = Path("reports/trait_gap_generation")
OLD, NEW, HAIKU, JUDGE = "claude-sonnet-4-6", "claude-sonnet-5-5", "claude-haiku-4-5-20251001", "claude-opus-5-5"
#: Models that refuse a temperature setting and always think (tested 2026-09-29, probe_sonnet55_api).
NO_TEMPERATURE = {NEW, JUDGE}
# Prices of 2026-09-29 (platform.claude.com pricing page); the repo's table knows only "sonnet" at
# $3 and $15.  Set here, for this process only, so usage.json carries the cost actually billed.
jp._MODEL_RATES = (("sonnet-5", 2.00, 10.00), ("opus-5-5", 4.00, 20.00)) + tuple(jp._MODEL_RATES)


def prompt_of(name: str) -> str:
    t = (P / "rubrics" / f"{name}.md").read_text(encoding="utf-8")
    return re.search(r"## The prompt\n\n````text\n(.*?)\n````", t, re.S).group(1)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def first_result(raw: str) -> dict:
    try:
        r = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"][0]
        r.pop("id", None)
        return r
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


class Caller:
    """One item per call.  Every response is charged and logged before it is parsed."""

    def __init__(self, budget_usd: float, concurrency: int = 8):
        self.client = anthropic.AsyncAnthropic(max_retries=0)
        self.usage = MultiModelUsage()
        self.sem = asyncio.Semaphore(concurrency)
        self.budget = budget_usd
        self.log: list[dict] = []
        self.n = {}

    async def ask(self, model: str, system: str | None, send, *, step: str, max_tokens: int = 700, raw_user: bool = False):
        user = send if raw_user else json.dumps(send, ensure_ascii=False)
        kw = {"model": model, "messages": [{"role": "user", "content": user}]}
        if system:
            kw["system"] = system
        if model in NO_TEMPERATURE:
            kw["max_tokens"] = max(2000, max_tokens)
        else:
            kw["max_tokens"] = max_tokens
            kw["temperature"] = 0.0
        async with self.sem:
            if self.usage.total_cost_usd >= self.budget:
                raise RuntimeError(f"budget of ${self.budget} reached")
            for attempt in range(5):
                try:
                    resp = await self.client.messages.create(**kw)
                except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                self.usage.charge(model, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                self.log.append({"step": step, "model": model, "sent": send, "raw": raw, "stop_reason": resp.stop_reason,
                                 "in": resp.usage.input_tokens, "out": resp.usage.output_tokens})
                k = (step, model)
                self.n[k] = self.n.get(k, 0) + 1
                return raw
            self.log.append({"step": step, "model": model, "sent": send, "raw": None, "error": "gave up after 5 attempts"})
            return ""

    def write(self, out: Path, run: dict) -> None:
        out.mkdir(parents=True, exist_ok=True)
        self.usage.write_json(out / "usage.json")
        with open(out / "responses.jsonl", "w", encoding="utf-8") as fh:
            for x in self.log:
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
        (out / "run.json").write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
        print(self.usage.log_line())
