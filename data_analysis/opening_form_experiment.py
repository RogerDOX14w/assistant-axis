#!/usr/bin/env python3
"""Test on the model itself how the wording of a trait instruction decides
whether the model takes the trait on.

Each instruction in a plan is given to the model as its system prompt with the
first N questions of the shared extraction bank, and every response is scored
by the pipeline's own trait judge (``pipeline/3_judge.py``: the 0 to 3
template, GPT-4.1-mini).  The measure is the one used on the extraction data:
the share of an instruction's responses scored 3, the trait fully shown.

The model is reached through OpenRouter, with the settings of the extraction
run (temperature 0.7, 512 tokens, thinking off) and one host pinned: only
hosts on the allowlist below are used.  A hosted copy is compressed (fp8) and
has thinking switched off by other means, so the first thing to run is a
replication: instructions from the extraction run whose scores are known.

Usage:
    uv run python data_analysis/opening_form_experiment.py plan-replication \\
        --traits petty undependable cryptic --out reports/opening_forms/replication
    uv run python data_analysis/opening_form_experiment.py generate --out reports/opening_forms/replication
    uv run python data_analysis/opening_form_experiment.py judge --out reports/opening_forms/replication
    uv run python data_analysis/opening_form_experiment.py report --out reports/opening_forms/replication

A plan is ``<out>/plan.json``:
    {"n_questions": 100,
     "traits": {"petty": {"label": "petty", "description": "...",
                          "variants": [{"name": "tendency", "text": "You have a tendency to ..."}]}}}
A trait may carry ``"questions": [...]`` of its own, which are then asked in
place of the shared bank's.  A variant whose text is empty is asked with no
system prompt: the model as it is, scored by that trait's judge.

Requires OPENROUTER_API_KEY (for Qwen) and OPENAI_API_KEY (for the judge, which
is asked at OpenAI directly) in the environment or in .env.  The keys are passed to the two clients and to nothing
else; this script never prints or stores them.

Openings (2026-11-06): one instruction body under several openings, judged by
step 3's own judge.  ``list-failures`` lists the extraction's instructions
that keep under half their siblings; ``rewrite-openings`` has a model rewrite
the openings that cannot be changed mechanically (it sees the whole
instruction, but only the opening it writes is used, so the rest stays byte
for byte); ``plan-openings`` builds the arms (W1-W8 and R1 from the "someone
who" instructions, A1-A8 from the "You are <adjective>" one, B0/B3/B4 from a
blind agent's file) and writes step 3's judge and the October generation
settings (max_tokens 1024) into the plan; ``openings-report`` compares each
arm with the one it was made from and scores menus of five by Roger's
criterion (an instruction keeping under half the mean of the other four):

    D=reports/opening_forms/openings_2026_11
    uv run python data_analysis/opening_form_experiment.py list-failures \\
        --scores-dir "runpod_workspace/qwen/qwen-3-32b Roger October/traits/scores" --write $D/problem_list.json
    uv run python data_analysis/opening_form_experiment.py rewrite-openings --out $D --stems $D/stems.json
    uv run python data_analysis/opening_form_experiment.py plan-openings --out $D --stems $D/stems.json \\
        --kinds $D/kinds.json --problem $D/problem_list.json \\
        --blind reports/opening_forms/blind_writing/blind_instructions.json
    uv run python data_analysis/opening_form_experiment.py generate --out $D --concurrency 48
    uv run python data_analysis/opening_form_experiment.py judge --out $D      # the plan's judge: step 3's
    uv run python data_analysis/opening_form_experiment.py openings-report --out $D --write

The depth check is a second plan in ``$D/depth`` (``plan-openings ... --questions own --n-questions 8``,
40 traits), generated and judged the same way and then read with ``depth --batch`` (Message Batches,
half price; ``--batch`` is off by default).
"""

import argparse
import asyncio
import datetime
import hashlib
import importlib.util
import json
import logging
import math
import os
import re
import signal
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

import anthropic  # noqa: E402
import openai  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.entity_id import judge_form_of_label  # noqa: E402
from assistant_axis.judge import RateLimiter, call_judge_single, parse_judge_score, warn_if_low_parse_rate  # noqa: E402
from assistant_axis.judge_pricing import (  # noqa: E402
    MultiModelUsage, extract_usage_anthropic, extract_usage_openai, price_for_model)

logger = logging.getLogger("opening_form_experiment")

REPO = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = REPO / "data" / "extraction_questions.jsonl"
OLD_RUN = REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot" / "traits"
# the corpus as it stood at the extraction run, for the descriptions its judge was given
OLD_CORPUS_COMMIT = "93a8554"

OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3-32b"
# Hosts that may be used (Roger, 2026-09-29): western ones only, none based in
# China or in a country of its bloc.  OpenRouter had two hosts for this model
# on that day, both serving it at fp8: DeepInfra (United States) and
# SiliconFlow (China: not to be used).  The host is pinned with no fallback, so
# OpenRouter cannot route a request anywhere else, and a response that names
# another host is thrown away.  Add a host here only after checking where it
# is based.
ALLOWED_PROVIDERS = ("DeepInfra",)
DEFAULT_PROVIDER = "DeepInfra"
# DeepInfra ignores the request to switch thinking off and spends the 512
# tokens thinking.  It honours Qwen's own switch, "/no_think" at the end of
# the user's turn.  The extraction run switched thinking off in the chat
# template, so its user turns had no such words: the replication is the check
# on whether that matters.
NO_THINK_SUFFIX = " /no_think"
# The judge is asked directly at OpenAI, as the pipeline asks it (Roger,
# 2026-09-29: OpenAI, Anthropic and Google models are reached directly, not
# through a router).  `--via openrouter` exists because the replication of
# that day was judged that way, before there was an OPENAI_API_KEY; it is
# pinned to OpenAI itself and is never chosen by default.
JUDGE_PROVIDER = "OpenAI"
DEFAULT_JUDGE = "gpt-4.1-mini"
# the extraction run's settings (pipeline/1_generate.py defaults; assistant_axis/generation.py)
TEMPERATURE = 0.7
MAX_TOKENS = 512
JUDGE_MAX_TOKENS = 200
DEFAULT_N_QUESTIONS = 100


def _pipeline_judge_module():
    """pipeline/3_judge.py, whose name cannot be imported in the ordinary way."""
    spec = importlib.util.spec_from_file_location("_pipeline_3_judge", REPO / "pipeline" / "3_judge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def trait_judge_prompt(label: str, description: str) -> str:
    """The pipeline's judge prompt for a trait, with {question} and {answer} left to fill.
    ``label`` is the stored label (as plans record it); the judge sees its judge
    display form, as pipeline/3_judge.py shows it since 2026-10-09 (identical for
    every label without a standard's suffix, so every plan run so far)."""
    return _pipeline_judge_module().TRAIT_EVAL_TEMPLATE.format(
        trait_name=judge_form_of_label(label), trait_description=description)


def load_questions(n: int) -> list[str]:
    out = []
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        for line in f:
            if len(out) == n:
                break
            out.append(json.loads(line)["question"])
    if len(out) < n:
        raise SystemExit(f"{QUESTIONS_FILE} has only {len(out)} questions")
    return out


def strip_thinking(text: str) -> str:
    """What the extraction run did with thinking text that leaked into a
    response, plus the whole-block case."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "</think>" in text:
        text = text[text.rfind("</think>") + len("</think>"):]
    return text.strip()


def load_plan(out_dir: Path) -> dict:
    path = out_dir / "plan.json"
    if not path.exists():
        raise SystemExit(f"no plan at {path}")
    plan = json.loads(path.read_text(encoding="utf-8"))
    for trait, t in plan["traits"].items():
        names = [v["name"] for v in t["variants"]]
        if len(names) != len(set(names)):
            raise SystemExit(f"{trait}: two variants share a name")
        if not t.get("description") or not t.get("label"):
            raise SystemExit(f"{trait}: the judge needs a label and a description")
    return plan


def key_of(variant: str, q: int) -> str:
    return f"{variant}_q{q}"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def say(message: str) -> None:
    """Print to stderr; a closed pipe (the run was stopped and its reader went
    first) must not keep what follows from happening."""
    try:
        print(message, file=sys.stderr)
    except OSError:
        pass


# calls between two writes of usage.json
USAGE_CHECKPOINT_CALLS = 200


class CheckpointedUsage:
    """A usage accumulator that merges into ``<out_dir>/usage.json`` every
    ``every`` calls and once more at the end, so that a run that is killed
    loses at most that many calls from the record.

    Before 2026-09-30 usage was written once, at the end, after a line printed
    to stderr: a run stopped from the task list lost all 2,443 of its calls,
    because its output went to a pipe whose reader had already gone.  Takes
    ``charge`` like ``MultiModelUsage``, so it can be handed to the judge
    helpers as their ``usage``.
    """

    def __init__(self, out_dir: Path, every: int | None = None):
        self.path = Path(out_dir) / "usage.json"
        self.every = every or USAGE_CHECKPOINT_CALLS
        self.run = MultiModelUsage()        # the whole run, for the log line
        self._pending = MultiModelUsage()   # charged, and not yet in the file

    @property
    def n_calls(self) -> int:
        return self.run.n_calls

    def charge(self, model: str, prompt_tokens: int, completion_tokens: int,
               cache_write_tokens: int = 0, cache_read_tokens: int = 0, **kwargs) -> float:
        self.run.charge(model, prompt_tokens, completion_tokens, cache_write_tokens, cache_read_tokens, **kwargs)
        cost = self._pending.charge(model, prompt_tokens, completion_tokens, cache_write_tokens, cache_read_tokens,
                                    **kwargs)
        if self._pending.n_calls >= self.every:
            self.flush()
        return cost

    def charge_usage(self, model: str, usage) -> float:
        """``charge`` from a ``judge_pricing.TokenUsage`` (how ``assistant_axis.judge``'s call functions
        charge, the cache counts included)."""
        return self.charge(model, usage.prompt_tokens, usage.completion_tokens,
                           usage.cache_write_tokens, usage.cache_read_tokens)

    def flush(self) -> MultiModelUsage:
        total = MultiModelUsage.load_or_create(self.path)
        if self._pending.n_calls:
            total.merge_from(self._pending)
            total.write_json(self.path)
            self._pending = MultiModelUsage()
        return total

    def close(self) -> None:
        total = self.flush()
        say(self.run.log_line("[usage]"))
        say(f"[usage] cumulative record: {self.path} (total ${total.total_cost_usd:.3f} over {total.n_calls} calls)")


# ---------------------------------------------------------------------------
# plan-replication
# ---------------------------------------------------------------------------

def old_instruction_scores(trait: str, n_questions: int) -> list[dict]:
    """The five instructions of the extraction run for a trait, each with the
    share of its first ``n_questions`` responses that the judge scored 3."""
    scores = json.loads((OLD_RUN / "scores" / f"{trait}.json").read_text(encoding="utf-8"))
    prompts = {}
    for row in read_jsonl(OLD_RUN / "responses" / f"{trait}.jsonl"):
        prompts.setdefault(row["prompt_index"], row["system_prompt"])
    out = []
    for p in sorted(prompts):
        vals = [scores.get(f"pos_p{p}_q{q}") for q in range(n_questions)]
        vals = [v for v in vals if isinstance(v, (int, float))]
        out.append({"name": f"old_p{p}", "text": prompts[p], "old_n": len(vals),
                    "old_share_3": round(100 * sum(v == 3 for v in vals) / len(vals), 1) if vals else None})
    return out


def old_description(trait: str) -> dict:
    """Label and description as the extraction run's judge was given them."""
    shown = subprocess.run(["git", "-C", str(REPO), "show", f"{OLD_CORPUS_COMMIT}:data/traits/instructions/{trait}.json"],
                           capture_output=True, text=True, check=True).stdout
    doc = json.loads(shown)
    return {"label": doc.get("positive_label", trait), "description": doc.get("description", "")}


def cmd_plan_replication(args) -> None:
    out_dir = Path(args.out)
    plan = {"purpose": "replication of the extraction run on another host", "n_questions": args.n_questions,
            "traits": {}}
    for trait in args.traits:
        variants = old_instruction_scores(trait, args.n_questions)
        if args.prompts:
            variants = [v for v in variants if int(v["name"][len("old_p"):]) in args.prompts]
        plan["traits"][trait] = {**old_description(trait), "variants": variants}
        for v in variants:
            print(f"{trait} {v['name']}: {v['old_share_3']}% of {v['old_n']}  {v['text'][:90]}")
    write_json(out_dir / "plan.json", plan)
    print(f"wrote {out_dir / 'plan.json'}")


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

def generation_settings(plan: dict) -> tuple[float, int]:
    """``(temperature, max_tokens)`` for a plan: its own when it records them (the openings plans of 2026-11-06
    take the October extraction's 1,024-token cap), else the 8slot run's, which every older plan used."""
    return float(plan.get("temperature", TEMPERATURE)), int(plan.get("max_tokens", MAX_TOKENS))


async def one_response(client, model: str, provider: str, system_prompt: str, question: str, semaphore,
                       usage, temperature: float = TEMPERATURE, max_tokens: int = MAX_TOKENS) -> dict | None:
    for attempt in range(4):
        try:
            async with semaphore:
                r = await client.chat.completions.create(
                    model=model, temperature=temperature, max_tokens=max_tokens,
                    # a variant with no text is the model with no instruction at all
                    messages=([{"role": "system", "content": system_prompt}] if system_prompt else [])
                    + [{"role": "user", "content": question + NO_THINK_SUFFIX}],
                    extra_body={"reasoning": {"enabled": False},
                                "provider": {"order": [provider], "allow_fallbacks": False}})
            usage.charge(model, *extract_usage_openai(r))
            msg = r.choices[0].message
            raw = msg.content or ""
            return {"content": strip_thinking(raw), "provider": getattr(r, "provider", None),
                    # with thinking switched off the host still returns the empty block, as white space
                    "had_thinking": bool((getattr(msg, "reasoning", None) or "").strip())
                    or bool(re.search(r"<think>\s*(?!</think>)\S", raw)) or ("</think>" in raw and "<think>" not in raw),
                    "finish_reason": r.choices[0].finish_reason}
        except (openai.APIError, IndexError, AttributeError) as e:
            # the status code says whether a wave of failures is the host, the router or the account
            logger.warning("attempt %d of 4 failed: %s%s", attempt + 1, type(e).__name__,
                           f" {e.status_code}" if getattr(e, "status_code", None) else "")
            await asyncio.sleep(2 ** attempt)
    return None


async def generate(args, plan: dict, out_dir: Path) -> None:
    shared = None
    todo = []
    for trait, t in plan["traits"].items():
        # a trait may bring questions of its own; otherwise the shared bank's first N
        questions = t.get("questions")
        if not questions:
            shared = shared or load_questions(plan.get("n_questions", DEFAULT_N_QUESTIONS))
            questions = shared
        done = {key_of(r["variant"], r["question_index"]) for r in read_jsonl(out_dir / "responses" / f"{trait}.jsonl")}
        for k, v in enumerate(t["variants"]):
            for q, question in enumerate(questions):
                if key_of(v["name"], q) not in done:
                    todo.append((trait, k, v, q, question))
    temperature, max_tokens = generation_settings(plan)
    n_in = sum(len(v["text"].split()) + len(question.split()) for _, _, v, _, question in todo) * 1.4
    rate_in, rate_out = price_for_model(args.model)
    # about 450 tokens a response at the 512 cap (most reach it), about 480 at 1,024 (October: 2,133 characters)
    n_out = 450 if max_tokens <= 512 else 480
    print(f"{len(todo)} responses to generate with {args.model} at {args.provider} (temperature {temperature}, "
          f"max_tokens {max_tokens}); about ${(n_in * rate_in + len(todo) * n_out * rate_out) / 1e6:.2f}",
          file=sys.stderr)
    if args.provider not in ALLOWED_PROVIDERS:
        raise SystemExit(f"{args.provider} is not among the hosts that may be used {ALLOWED_PROVIDERS}")
    if args.dry_run or not todo:
        return
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY not set (check .env or environment)")
    client = openai.AsyncOpenAI(base_url=OPENROUTER_URL, api_key=os.environ["OPENROUTER_API_KEY"])
    semaphore = asyncio.Semaphore(args.concurrency)
    usage = CheckpointedUsage(out_dir)
    (out_dir / "responses").mkdir(parents=True, exist_ok=True)
    failed = 0

    async def one(trait, k, v, q, question):
        nonlocal failed
        r = await one_response(client, args.model, args.provider, v["text"], question, semaphore, usage,
                               temperature=temperature, max_tokens=max_tokens)
        # a response that came with thinking is not what the extraction run would have produced,
        # and one from another host should not exist
        if r is None or not r["content"] or r["had_thinking"] or r["provider"] != args.provider:
            failed += 1
            return
        row = {"label": "pos", "prompt_index": k, "variant": v["name"], "question_index": q, "question": question,
               "system_prompt": v["text"], "user_turn": question + NO_THINK_SUFFIX, "model": args.model,
               "provider": r["provider"], "temperature": temperature, "max_tokens": max_tokens,
               "had_thinking": r["had_thinking"], "finish_reason": r["finish_reason"],
               "conversation": ([{"role": "system", "content": v["text"]}] if v["text"] else [])
               + [{"role": "user", "content": question}, {"role": "assistant", "content": r["content"]}]}
        with open(out_dir / "responses" / f"{trait}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    try:
        await asyncio.gather(*(one(*t) for t in todo))
    finally:
        usage.close()
    print(f"generated {len(todo) - failed} of {len(todo)}; {failed} failed or empty (run again to fill them)",
          file=sys.stderr)


def cmd_generate(args) -> None:
    out_dir = Path(args.out)
    asyncio.run(generate(args, load_plan(out_dir), out_dir))


# ---------------------------------------------------------------------------
# judge
# ---------------------------------------------------------------------------

async def judge_through_openrouter(client, prompt: str, model: str, limiter, usage) -> str | None:
    """The pipeline's judge call (one user turn, temperature 1, 200 tokens),
    sent through OpenRouter and pinned to OpenAI.  An answer from another host
    is not used."""
    await limiter.acquire()
    for attempt in range(3):
        try:
            r = await client.chat.completions.create(
                model=f"openai/{model}", messages=[{"role": "user", "content": prompt}],
                max_tokens=JUDGE_MAX_TOKENS, temperature=1,
                extra_body={"provider": {"order": [JUDGE_PROVIDER], "allow_fallbacks": False}})
            usage.charge(model, *extract_usage_openai(r))
            if getattr(r, "provider", None) != JUDGE_PROVIDER:
                logger.warning("judge answer from %s, not used", getattr(r, "provider", None))
                return None
            return r.choices[0].message.content if r.choices else None
        except (openai.APIError, IndexError, AttributeError) as e:
            logger.warning("judge attempt %d of 3 failed: %s", attempt + 1, type(e).__name__)
            await asyncio.sleep(2 ** attempt)
    return None


# Step 3's own judge (2026-11-06), for plans that ask for it (``plan["judge"]``): the trait rubric of a prompt
# version, its reply reading and token default, the judge model it was settled for, Flex with a fallback to the
# standard tier, and a response cut at max_tokens marked for the judge as step 3 marks it.  The numbers then mean
# what the October extraction's keep rates mean.  Plans without the field keep the old judge (the pipeline's
# TRAIT_EVAL_TEMPLATE, gpt-4.1-mini), so every earlier run reproduces.
STEP3_JUDGE = {"rubric": "step3", "prompt_version": 20, "model": "gpt-5.6-luna", "service_tier": "flex",
               "mark_truncated": True}
JUDGE_STAMP = "judge.json"


def step3_judge_spec(plan: dict) -> dict | None:
    spec = plan.get("judge")
    if spec is None:
        return None
    if spec.get("rubric") != "step3":
        raise SystemExit(f"the plan's judge is {spec!r}; only step 3's is known ('rubric': 'step3')")
    return {**STEP3_JUDGE, **spec}


def step3_trait_template(label: str, description: str, prompt_version: int) -> str:
    """Step 3's trait rubric with {question} and {answer} left to fill, as ``pipeline/3_judge.py``
    ``_trait_prompt`` renders it from a trait file: the label in its judge display form, the description as
    the file has it, braces in either made literal."""
    from assistant_axis.judge_rubrics import get_version
    mod = _pipeline_judge_module()
    return get_version(prompt_version).trait.format(trait_name=mod._literal(judge_form_of_label(label)),
                                                    trait_description=mod._literal(description))


def judge_stamp(spec: dict) -> dict:
    from assistant_axis.judge_rubrics import get_version
    v = get_version(spec["prompt_version"])
    return {"rubric": "step3", "prompt_version": spec["prompt_version"], "model": spec["model"],
            "truncation_marker": _pipeline_judge_module().TRUNCATION_MARKER if spec["mark_truncated"] else None,
            "trait_template_sha256": hashlib.sha256(v.trait.encode("utf-8")).hexdigest()[:16],
            "reply_format": v.reply_format_for("trait"), "max_tokens": v.max_tokens_for("trait")}


def check_judge_stamp(out_dir: Path, spec: dict | None) -> None:
    """A scores directory holds one judge: refuse to add scores from another."""
    path = out_dir / "scores" / JUDGE_STAMP
    have = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    want = judge_stamp(spec) if spec else None
    if have is None:
        if want is not None and any((out_dir / "scores").glob("*.json")):
            raise SystemExit(f"{out_dir / 'scores'} holds scores from the old judge; step 3's needs a fresh plan")
        return
    if have != want:
        raise SystemExit(f"{out_dir / 'scores'} was judged with {have}, this plan asks for {want}")


def answer_for_judge(row: dict, mark_truncated: bool) -> str:
    """The answer as the judge is shown it: with step 3's marker when the response was cut at max_tokens."""
    text = row["conversation"][-1]["content"]
    if mark_truncated and row.get("finish_reason") == "length":
        text += _pipeline_judge_module().TRUNCATION_MARKER
    return text


async def judge_step3(args, plan: dict, out_dir: Path, spec: dict) -> None:
    from assistant_axis import judge as judge_mod
    from assistant_axis.judge_rubrics import get_version
    version = get_version(spec["prompt_version"])
    model = spec["model"]
    allowed = version.judges_for("trait")
    if allowed and model not in allowed:
        raise SystemExit(f"prompt version {spec['prompt_version']}'s trait rubric was settled for {allowed}, not {model}")
    if args.judge_model and args.judge_model != model:
        raise SystemExit(f"the plan judges with {model}; --judge-model {args.judge_model} does not apply")
    tier = spec.get("service_tier")
    if tier == "flex" and judge_mod.accepts_flex(model) is False:
        raise SystemExit(f"{model} is refused Flex processing (judge.MODEL_CAPABILITIES)")
    check_judge_stamp(out_dir, spec)
    mod = _pipeline_judge_module()
    reply_format, max_tokens = version.reply_format_for("trait"), version.max_tokens_for("trait")
    todo, scores = [], {}
    for trait, t in plan["traits"].items():
        path = out_dir / "scores" / f"{trait}.json"
        scores[trait] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        template = step3_trait_template(t["label"], t["description"], spec["prompt_version"])
        for r in read_jsonl(out_dir / "responses" / f"{trait}.jsonl"):
            k = key_of(r["variant"], r["question_index"])
            if k not in scores[trait]:
                todo.append((trait, k, template.format(question=r["question"],
                                                       answer=answer_for_judge(r, spec["mark_truncated"]))))
    n_in = sum(len(p) for _, _, p in todo) / 4.0
    rate_in, rate_out = price_for_model(judge_mod.usage_key(model, tier))
    print(f"{len(todo)} responses to judge with {model}{' (' + tier + ')' if tier else ''}, prompt version "
          f"{spec['prompt_version']}; about ${(n_in * rate_in + len(todo) * 120 * rate_out) / 1e6:.2f}",
          file=sys.stderr)
    if args.dry_run or not todo:
        return
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set (check .env or environment)")
    (out_dir / "scores").mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "scores" / JUDGE_STAMP, judge_stamp(spec))
    client = judge_mod.judge_client(model, tier)
    fallback = judge_mod.judge_client(model) if tier == "flex" else None
    limiter = RateLimiter(args.requests_per_second)
    usage = CheckpointedUsage(out_dir)
    n_ok = 0

    async def one(trait, k, prompt):
        nonlocal n_ok
        text = await call_judge_single(client, prompt, model, max_tokens, limiter, usage=usage,
                                       reject_truncated=reply_format == "score_marker", service_tier=tier,
                                       fallback_client=fallback)
        score = mod.score_reply(text, reply_format=reply_format) if text else None
        if score is not None:
            scores[trait][k] = score
            n_ok += 1

    # A pool of workers, each taking the next response when it is done with one: a Flex call can retry for
    # minutes before it falls back, and in fixed chunks every such call held up its whole chunk (2026-11-06:
    # 200 judged in three minutes); larger chunks put thousands of connections in flight at once and failed
    # with connection errors.  Scores are written every ``--chunk`` answers and on the way out.
    queue = iter(todo)
    finished = 0

    def save():
        for trait in plan["traits"]:
            write_json(out_dir / "scores" / f"{trait}.json", scores[trait])

    async def worker():
        nonlocal finished
        for t in queue:
            await one(*t)
            finished += 1
            if finished % args.chunk == 0:
                save()
                say(f"judged {finished} of {len(todo)}")

    try:
        await asyncio.gather(*(worker() for _ in range(min(getattr(args, "in_flight", 200), len(todo)))))
    finally:
        save()
        usage.close()
    say(f"judged {finished} of {len(todo)}")
    warn_if_low_parse_rate(label=f"opening_form_experiment:{model}", n_ok=n_ok, n_total=len(todo),
                           logger_obj=logger)


async def judge(args, plan: dict, out_dir: Path) -> None:
    spec = step3_judge_spec(plan)
    if spec is not None:
        return await judge_step3(args, plan, out_dir, spec)
    check_judge_stamp(out_dir, None)
    args.judge_model = args.judge_model or DEFAULT_JUDGE
    todo = []
    scores = {}
    for trait, t in plan["traits"].items():
        path = out_dir / "scores" / f"{trait}.json"
        scores[trait] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        # a role is judged with its file's own eval_prompt, as the pipeline judges it
        template = t["judge_prompt"] if t.get("entity") == "role" else trait_judge_prompt(t["label"], t["description"])
        for r in read_jsonl(out_dir / "responses" / f"{trait}.jsonl"):
            k = key_of(r["variant"], r["question_index"])
            if k not in scores[trait]:
                todo.append((trait, k, template.format(question=r["question"], answer=r["conversation"][-1]["content"])))
    print(f"{len(todo)} responses to judge with {args.judge_model}", file=sys.stderr)
    if args.dry_run or not todo:
        return
    via = args.via or "openai"
    limiter = RateLimiter(args.requests_per_second)
    usage = CheckpointedUsage(out_dir)
    n_ok = 0
    if via == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY not set (check .env or environment); the judge is asked at OpenAI "
                             "directly, and a router is used only on request (--via openrouter)")
        client = openai.AsyncOpenAI()
    else:
        if not os.getenv("OPENROUTER_API_KEY"):
            raise SystemExit("OPENROUTER_API_KEY not set (check .env or environment)")
        client = openai.AsyncOpenAI(base_url=OPENROUTER_URL, api_key=os.environ["OPENROUTER_API_KEY"])
    print(f"judge reached through {via}", file=sys.stderr)

    async def ask(prompt):
        if via == "openai":
            return await call_judge_single(client, prompt, args.judge_model, JUDGE_MAX_TOKENS, limiter, usage=usage)
        return await judge_through_openrouter(client, prompt, args.judge_model, limiter, usage)

    async def one(trait, k, prompt):
        nonlocal n_ok
        text = await ask(prompt)
        score = parse_judge_score(text) if text else None
        if score is not None:
            scores[trait][k] = score
            n_ok += 1

    try:
        for i in range(0, len(todo), 200):
            await asyncio.gather(*(one(*t) for t in todo[i:i + 200]))
            for trait in plan["traits"]:
                write_json(out_dir / "scores" / f"{trait}.json", scores[trait])
    finally:
        usage.close()
    warn_if_low_parse_rate(label=f"opening_form_experiment:{args.judge_model}", n_ok=n_ok, n_total=len(todo),
                           logger_obj=logger)


def cmd_judge(args) -> None:
    out_dir = Path(args.out)
    asyncio.run(judge(args, load_plan(out_dir), out_dir))


# ---------------------------------------------------------------------------
# depth: how the trait shows, not only whether
# ---------------------------------------------------------------------------
# The pipeline's judge gives its top score to any answer in which the trait
# is on display, a performance as much as the real thing, and on Qwen the
# openings that tell the model to play a part score highest.  This second
# judge reads the same answers for how the trait shows (Roger, 2026-09-29:
# "optimizing this particular test is pushing us to use roleplay style
# rubrics. I'm concerned that doing that will produce superficial behavior").
# It is not told the instruction that produced the answer.

DEFAULT_DEPTH_JUDGE = "claude-sonnet-4-6"
# 2 (2026-10-09, W19): the trait or role is named in its judge display form
# (``careless (from HEXACO)``).  A reading stamped 1 stays current when the
# plan's label renders unchanged (every plan run so far): depth_is_current.
DEPTH_RUBRIC_VERSION = 2


def depth_is_current(done: dict, label: str, model: str) -> bool:
    rv = done.get("rubric_version")
    return done.get("model") == model and (
        rv == DEPTH_RUBRIC_VERSION or (rv == 1 and judge_form_of_label(label) == label))
DEPTH_MAX_TOKENS = 300
VOICES = ("person", "assistant", "mixed")

DEPTH_JUDGE_PROMPT = """\
You are reading one answer written for a research dataset on personality \
traits in language models. A language model was set up to have the trait \
below and was then asked the question. The research needs to know not only \
whether the trait shows in the answer but how: whether the answer is what a \
person with the trait would really say or do in that situation, or a display \
of the trait put on for an audience.

<trait>
{trait}
</trait>

<trait_description>
{description}
</trait_description>

<question>
{question}
</question>

<answer>
{answer}
</answer>

Judge the answer on four points.

- voice: "person" if the answer is given by someone in the situation, speaking \
for themselves; "assistant" if it is given by an adviser or an assistant, who \
addresses the asker, lays out options or lists steps; "mixed" if it moves \
between the two.
- in_action: true if what the speaker does, decides, or says in the situation \
is what the trait would produce; false if the trait does not shape what they \
do, whatever they may say about themselves.
- describes_itself: true if the answer names or describes the speaker's own \
trait or disposition ("I tend to hold grudges", "as someone who avoids \
conflict"), in place of acting from it or on top of acting from it.
- caricature: 0 if the speaker is a believable person who has the trait; 1 if \
the trait is laid on more thickly than a real person would show it; 2 if the \
answer is a cartoon of the trait: theatrical, over the top, with stage \
directions or a performance for an audience.

Respond with a JSON object only, no other text. Write the reason first (one or \
two sentences on how the trait shows, or fails to show, in this answer), and \
then the four judgements:

{{"reason": "<reason>", "voice": "person", "in_action": true, \
"describes_itself": false, "caricature": 0}}"""


# The same four points for a role (2026-10-02): whether the answer is what the
# role would really say or do, or the role put on for an audience.  Wording
# only; the points, the scale and the reply format are the trait version's.
ROLE_DEPTH_JUDGE_PROMPT = """\
You are reading one answer written for a research dataset on roles in \
language models. A language model was set up to be the role below and was then \
asked the question. The research needs to know not only whether the role shows \
in the answer but how: whether the answer is what someone (or something) in \
that role would really say or do in that situation, or a display of the role \
put on for an audience.

<role>
{trait}
</role>

<role_description>
{description}
</role_description>

<question>
{question}
</question>

<answer>
{answer}
</answer>

Judge the answer on four points.

- voice: "person" if the answer is given by the role itself, speaking for \
itself from inside its own situation; "assistant" if it is given by an adviser \
or an assistant, who addresses the asker, lays out options or lists steps; \
"mixed" if it moves between the two.
- in_action: true if what the speaker does, decides, or says in the situation \
is what the role would produce; false if the role does not shape what they do, \
whatever they may say about themselves.
- describes_itself: true if the answer names or describes the speaker's own \
role or what it is like to be it ("as a forger, I ...", "being a herder means \
..."), in place of acting from it or on top of acting from it.
- caricature: 0 if the speaker is believable in the role; 1 if the role is laid \
on more thickly than a real one would show it; 2 if the answer is a cartoon of \
the role: theatrical, over the top, with stage directions or a performance for \
an audience.

Respond with a JSON object only, no other text. Write the reason first (one or \
two sentences on how the role shows, or fails to show, in this answer), and \
then the four judgements:

{{"reason": "<reason>", "voice": "person", "in_action": true, \
"describes_itself": false, "caricature": 0}}"""


def parse_depth(text: str) -> dict:
    """The depth judge's reply, checked.  Raises ValueError on a reply that
    cannot be used."""
    raw = text.strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    d = json.loads(raw[start:end + 1])
    if d.get("voice") not in VOICES:
        raise ValueError(f"voice is {d.get('voice')!r}")
    for k in ("in_action", "describes_itself"):
        if not isinstance(d.get(k), bool):
            raise ValueError(f"{k} is {d.get(k)!r}")
    if d.get("caricature") not in (0, 1, 2) or isinstance(d.get("caricature"), bool):
        raise ValueError(f"caricature is {d.get('caricature')!r}")
    return {"reason": str(d.get("reason", "")), "voice": d["voice"], "in_action": d["in_action"],
            "describes_itself": d["describes_itself"], "caricature": d["caricature"]}


async def depth_call(client, model: str, prompt: str, semaphore, usage, tally: dict) -> dict | None:
    last = None
    for attempt in range(3):
        asked = prompt if last is None else (
            f"{prompt}\n\nYour previous reply could not be used: {last}. Reply again, keeping to the format.")
        try:
            async with semaphore:
                r = await client.messages.create(model=model, max_tokens=DEPTH_MAX_TOKENS,
                                                 temperature=0.0 if attempt == 0 else 0.5,
                                                 messages=[{"role": "user", "content": asked}])
        except anthropic.APIError as e:
            logger.warning("depth judge attempt %d of 3 failed: %s", attempt + 1, type(e).__name__)
            await asyncio.sleep(2 ** attempt)
            continue
        usage.charge(model, *extract_usage_anthropic(r))
        tally["total"] += 1
        try:
            out = parse_depth(next(b.text for b in r.content if b.type == "text"))
            tally["ok"] += 1
            return out
        except (ValueError, json.JSONDecodeError, StopIteration) as e:
            last = e
    return None


async def depth(args, plan: dict, out_dir: Path) -> None:
    todo, judged = [], {}
    for trait, t in plan["traits"].items():
        path = out_dir / "depth" / f"{trait}.json"
        judged[trait] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        p = out_dir / "scores" / f"{trait}.json"
        scores = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        for r in read_jsonl(out_dir / "responses" / f"{trait}.jsonl"):
            k = key_of(r["variant"], r["question_index"])
            done = judged[trait].get(k)
            if done and depth_is_current(done, t["label"], args.model):
                continue
            if scores.get(k, -1) < args.min_score:
                continue
            template = ROLE_DEPTH_JUDGE_PROMPT if t.get("entity") == "role" else DEPTH_JUDGE_PROMPT
            todo.append((trait, k, template.format(
                trait=judge_form_of_label(t["label"]), description=t["description"], question=r["question"],
                answer=r["conversation"][-1]["content"])))
    batch = getattr(args, "batch", False)
    n_in = sum(len(p) for _, _, p in todo) / 3.6
    rate_in, rate_out = price_for_model(f"{args.model}:batch" if batch else args.model)
    print(f"{len(todo)} answers to read with {args.model}{' by batch' if batch else ''}; about "
          f"${(n_in * rate_in + len(todo) * 150 * rate_out) / 1e6:.2f}", file=sys.stderr)
    if args.dry_run or not todo:
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(args.concurrency)
    usage, tally = CheckpointedUsage(out_dir), {"ok": 0, "total": 0}

    if batch:
        try:
            todo = await depth_by_batch(client, args.model, todo, judged, plan, out_dir, usage, tally)
        except BaseException:
            usage.close()
            raise
        say(f"{len(todo)} answers the batch did not settle; reading them in real time")

    async def one(trait, k, prompt):
        out = await depth_call(client, args.model, prompt, semaphore, usage, tally)
        if out is not None:
            out.update({"model": args.model, "rubric_version": DEPTH_RUBRIC_VERSION})
            judged[trait][k] = out

    try:
        for i in range(0, len(todo), 200):
            await asyncio.gather(*(one(*t) for t in todo[i:i + 200]))
            for trait in plan["traits"]:
                write_json(out_dir / "depth" / f"{trait}.json", judged[trait])
    finally:
        usage.close()
    warn_if_low_parse_rate(label=f"opening_form_experiment:depth:{args.model}", n_ok=tally["ok"],
                           n_total=tally["total"], logger_obj=logger)


async def depth_by_batch(client, model: str, todo: list, judged: dict, plan: dict, out_dir: Path, usage,
                         tally: dict, poll_seconds: float = 60.0) -> list:
    """Read ``todo`` (``(trait, key, prompt)``) through Anthropic Message Batches at half price
    (2026-11-06; the batch-or-real-time rule: the openings test's depth check is over $20 live).  The first
    attempt is the real-time path's (temperature 0); usage goes under ``<model>:batch``.  Batches still in
    flight from a stopped run are collected, not sent again.  Returns the items the batch did not settle (not
    answered, or a reply that could not be used), for the real-time path with its retry prompt."""
    from assistant_axis.anthropic_batch import AnthropicBatchRunner
    from assistant_axis.judge import anthropic_reply, anthropic_request_params
    from assistant_axis.judge_pricing import anthropic_usage
    work = out_dir / "depth_batch"
    runner = AnthropicBatchRunner(client, work, work / "state.json", poll_seconds=poll_seconds,
                                  # other sessions on the account submit batches too: never adopt one by its size
                                  adopt_lost_batches=False, logger=logger)
    in_flight = await runner.resume()
    by_id = {f"{trait}|{k}": (trait, k, prompt) for trait, k, prompt in todo}
    settled: set[str] = set()

    def on_result(custom_id: str, body: dict | None, error: str | None) -> None:
        item = by_id.get(custom_id)
        if item is None or body is None:
            return
        usage.charge_usage(f"{model}:batch", anthropic_usage(body))
        tally["total"] += 1
        try:
            text = anthropic_reply(body)[0]
            out = parse_depth(text or "")
        except (ValueError, json.JSONDecodeError, TypeError):
            return
        tally["ok"] += 1
        out.update({"model": model, "rubric_version": DEPTH_RUBRIC_VERSION, "via": "batch"})
        judged[item[0]][item[1]] = out
        settled.add(custom_id)

    def on_batch_done() -> None:
        for trait in plan["traits"]:
            write_json(out_dir / "depth" / f"{trait}.json", judged[trait])

    requests = [(cid, anthropic_request_params(prompt, model, DEPTH_MAX_TOKENS, temperature=0.0))
                for cid, (_, _, prompt) in by_id.items() if cid not in in_flight]
    chunks = runner.write_chunks(requests) if requests else []
    say(f"depth: {len(requests)} requests in {len(chunks)} batch(es); {len(in_flight)} already in flight")
    await runner.run(chunks, on_result, on_batch_done)
    return [item for cid, item in by_id.items() if cid not in settled]


def cmd_depth(args) -> None:
    out_dir = Path(args.out)
    asyncio.run(depth(args, load_plan(out_dir), out_dir))


def depth_table(plan: dict, out_dir: Path, top_only: bool) -> list[dict]:
    """One row per variant: how its answers show the trait.  With
    ``top_only``, only the answers that the pipeline's judge scored 3."""
    by = defaultdict(list)
    for trait, t in plan["traits"].items():
        p, q = out_dir / "depth" / f"{trait}.json", out_dir / "scores" / f"{trait}.json"
        judged = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        scores = json.loads(q.read_text(encoding="utf-8")) if q.exists() else {}
        for k, d in judged.items():
            if top_only and scores.get(k) != 3:
                continue
            by[k.rsplit("_q", 1)[0]].append(d)
    rows = []
    for v in next(iter(plan["traits"].values()))["variants"]:
        ds = by.get(v["name"], [])
        n = len(ds)
        if not n:
            continue
        rows.append({"variant": v["name"], "n": n,
                     "person": 100 * sum(d["voice"] == "person" for d in ds) / n,
                     "assistant": 100 * sum(d["voice"] == "assistant" for d in ds) / n,
                     "in_action": 100 * sum(d["in_action"] for d in ds) / n,
                     "describes_itself": 100 * sum(d["describes_itself"] for d in ds) / n,
                     "laid_on": 100 * sum(d["caricature"] >= 1 for d in ds) / n,
                     "cartoon": 100 * sum(d["caricature"] == 2 for d in ds) / n,
                     "believable_in_action": 100 * sum(
                         d["in_action"] and d["caricature"] == 0 and d["voice"] == "person" for d in ds) / n})
    return rows


def cmd_depth_report(args) -> None:
    out_dir = Path(args.out)
    plan = load_plan(out_dir)
    out = {}
    for top_only, title in ((False, "all answers read"), (True, "answers the pipeline's judge scored 3")):
        rows = depth_table(plan, out_dir, top_only)
        out[title] = rows
        print(f"\n{title}")
        print(f"{'opening':24s}{'n':>6s}{'own voice':>11s}{'assistant':>11s}{'in action':>11s}{'describes':>11s}"
              f"{'laid on':>9s}{'cartoon':>9s}{'believable and in action':>26s}")
        for r in rows:
            print(f"{r['variant']:24s}{r['n']:6d}{r['person']:10.0f}%{r['assistant']:10.0f}%{r['in_action']:10.0f}%"
                  f"{r['describes_itself']:10.0f}%{r['laid_on']:8.0f}%{r['cartoon']:8.0f}%{r['believable_in_action']:25.0f}%")
    if args.write:
        write_json(out_dir / "depth_report.json", out)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def tabulate(plan: dict, out_dir: Path) -> list[dict]:
    """One row per trait and variant: how its responses were scored."""
    rows = []
    for trait, t in plan["traits"].items():
        path = out_dir / "scores" / f"{trait}.json"
        scores = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        responses = read_jsonl(out_dir / "responses" / f"{trait}.jsonl")
        for v in t["variants"]:
            vals = [s for k, s in scores.items() if k.rsplit("_q", 1)[0] == v["name"]]
            mine = [r for r in responses if r["variant"] == v["name"]]
            n = len(vals)
            k3 = sum(s == 3 for s in vals)
            lo, hi = wilson(k3, n)
            rows.append({"trait": trait, "variant": v["name"], "n": n,
                         "share_3": 100 * k3 / n if n else float("nan"), "low": 100 * lo, "high": 100 * hi,
                         "share_2": 100 * sum(s == 2 for s in vals) / n if n else float("nan"),
                         "share_1": 100 * sum(s == 1 for s in vals) / n if n else float("nan"),
                         "share_0": 100 * sum(s == 0 for s in vals) / n if n else float("nan"),
                         "old_share_3": v.get("old_share_3"), "text": v["text"],
                         "providers": sorted({str(r.get("provider")) for r in mine}),
                         "had_thinking": sum(bool(r.get("had_thinking")) for r in mine)})
    return rows


def by_variant(rows: list[dict], reference: str | None) -> list[dict]:
    """Across traits: each variant's mean share, and its mean difference from
    the reference variant on the traits that have both, with a sign count."""
    per = defaultdict(dict)
    for r in rows:
        if r["n"]:
            per[r["variant"]][r["trait"]] = r["share_3"]
    out = []
    for name, shares in per.items():
        row = {"variant": name, "traits": len(shares), "mean_share_3": sum(shares.values()) / len(shares)}
        if reference and reference in per and name != reference:
            both = [t for t in shares if t in per[reference]]
            diffs = [shares[t] - per[reference][t] for t in both]
            if diffs:
                row.update({"against": reference, "mean_difference": sum(diffs) / len(diffs),
                            "traits_above": sum(d > 0 for d in diffs), "traits_below": sum(d < 0 for d in diffs)})
        out.append(row)
    return out


def cmd_report(args) -> None:
    out_dir = Path(args.out)
    plan = load_plan(out_dir)
    rows = tabulate(plan, out_dir)
    replication = any(r["old_share_3"] is not None for r in rows)
    print(f"{'trait':16s}{'variant':26s}{'n':>5s}{'scored 3':>10s}{'95% interval':>16s}{'scored 1':>10s}"
          + (f"{'old run':>9s}" if replication else "") + "  opening")
    for r in rows:
        interval = "(%.0f to %.0f)" % (r["low"], r["high"])
        line = f"{r['trait']:16s}{r['variant']:26s}{r['n']:5d}{r['share_3']:9.0f}%{interval:>16s}{r['share_1']:9.0f}%"
        if replication:
            old = "" if r["old_share_3"] is None else "%.0f%%" % r["old_share_3"]
            line += f"{old:>9s}"
        print(line + "  " + r["text"][:60])
    if replication:
        pairs = [(r["old_share_3"], r["share_3"]) for r in rows if r["old_share_3"] is not None and r["n"]]
        if pairs:
            gap = [new - old for old, new in pairs]
            mx, my = sum(o for o, _ in pairs) / len(pairs), sum(n for _, n in pairs) / len(pairs)
            sxx = sum((o - mx) ** 2 for o, _ in pairs)
            syy = sum((n - my) ** 2 for _, n in pairs)
            sxy = sum((o - mx) * (n - my) for o, n in pairs)
            corr = sxy / math.sqrt(sxx * syy) if sxx and syy else float("nan")
            print(f"\nreplication over {len(pairs)} instructions: mean difference from the old run "
                  f"{sum(gap) / len(gap):+.1f} points, mean absolute difference "
                  f"{sum(abs(g) for g in gap) / len(gap):.1f}, correlation {corr:.2f}; same side of 50% in "
                  f"{sum((o >= 50) == (n >= 50) for o, n in pairs)} of {len(pairs)}")
    print()
    for v in by_variant(rows, args.reference):
        line = f"{v['variant']:26s} traits {v['traits']:3d}   mean share scored 3 {v['mean_share_3']:5.1f}%"
        if "against" in v:
            line += (f"   against {v['against']}: {v['mean_difference']:+.1f} points, above in "
                     f"{v['traits_above']}, below in {v['traits_below']}")
        print(line)
    providers = sorted({p for r in rows for p in r["providers"]})
    print(f"\nproviders that answered: {providers}; responses with thinking text: {sum(r['had_thinking'] for r in rows)}")
    if args.write:
        write_json(out_dir / "report.json", {"written": datetime.date.today().isoformat(), "rows": rows,
                                             "by_variant": by_variant(rows, args.reference)})


# ---------------------------------------------------------------------------
# arms: a plan from staged directories of trait files, and a paired comparison
# ---------------------------------------------------------------------------

DEFAULT_ARM_QUESTIONS = 20
KINDS = ("good", "bad", "indifferent")


def parse_arm_spec(spec: str) -> tuple[str, Path, str | None]:
    """'code=directory' or 'code=directory:STYLE@hash' -> (code, directory, style guard)."""
    code, sep, rest = spec.partition("=")
    if not sep or not code or not rest:
        raise SystemExit(f"an arm is 'code=directory[:STYLE@hash]': {spec!r}")
    directory, _, style = rest.partition(":")
    return code, Path(directory), (style or None)


def arm_questions(n: int) -> list[str]:
    """Every (100/n)th of the shared bank's first 100 questions: n spread over the bank's opening
    hundred, the way the development sample's plan was drawn (n = 20 gives questions 0, 5, ..., 95)."""
    if not 1 <= n <= 100 or 100 % n:
        raise SystemExit(f"--n-questions must divide 100: {n}")
    return load_questions(100)[:: 100 // n]


ENTITIES = ("trait", "role")


def role_label(stem: str) -> str:
    """A role's name, as the role generator and the pipeline write it into prompts
    (its judge display form since 2026-10-09; the same as role_display_name for
    every role in the corpus)."""
    from data_analysis.regenerate_role_instructions import role_prompt_name  # noqa: E402  (a sibling script)
    return role_prompt_name(stem)


def build_arms_plan(arms: list[tuple[str, Path, str | None]], stems: list[str], n_questions: int,
                    kinds: dict[str, str] | None = None, existing: dict | None = None,
                    purpose: str = "", entity: str = "trait") -> tuple[dict, list[str]]:
    """A plan whose variants are the positive instructions of each arm's files, five a trait, named
    '<code>_p<k>'.  The label and description the judge is shown are the first arm's; a trait whose
    label or description differs between arms is left out and its stem returned, since the
    instructions would be for two different traits.  With ``existing``, the arms are added to that
    plan (an arm already in it is replaced), and its traits' questions and kinds are kept.

    ``entity="role"`` (2026-10-02) builds the same plan for role files: the label is the role's
    display name, and the judge prompt is the file's own ``eval_prompt``, which is what the
    pipeline's judge uses for a role (``pipeline/3_judge.py``); it is carried in the plan."""
    from data_analysis import audit_trait_instructions as audit  # noqa: E402  (a sibling script)
    if entity not in ENTITIES:
        raise SystemExit(f"entity must be one of {ENTITIES}: {entity!r}")
    docs = {code: audit.arm_files(directory, stems, style) for code, directory, style in arms}
    changed = audit.described_differently(docs)
    plan = existing if existing is not None else {
        "purpose": purpose, "n_questions": n_questions, "entity": entity, "traits": {}, "arms": {}}
    if plan.get("entity", "trait") != entity:
        raise SystemExit(f"the plan is for {plan.get('entity', 'trait')}s, not {entity}s")
    questions = arm_questions(n_questions)
    codes = [code for code, _, _ in arms]
    for stem in stems:
        if stem in changed:
            continue
        have = [code for code in codes if stem in docs[code]]
        if not have:
            continue
        first = docs[have[0]][stem]
        entry = {"label": first.get("positive_label", stem) if entity == "trait" else role_label(stem),
                 "description": " ".join(str(first["description"]).split()),
                 "kind": (kinds or {}).get(stem, "unclassified"), "variants": [], "questions": questions}
        if entity == "role":
            if not first.get("eval_prompt"):
                logger.warning("%s: the role file has no eval_prompt; left out", stem)
                continue
            entry["entity"] = "role"
            entry["judge_prompt"] = first["eval_prompt"]
        t = plan["traits"].setdefault(stem, entry)
        if kinds and stem in kinds:
            t["kind"] = kinds[stem]
        if " ".join(str(first["description"]).split()) != t["description"]:
            logger.warning("%s: the plan's description is not the one in the arms' files; left out", stem)
            continue
        t["variants"] = [v for v in t["variants"] if v["arm"] not in have]
        for code in have:
            for k, pair in enumerate(docs[code][stem]["instruction"]):
                t["variants"].append({"name": f"{code}_p{k}", "text": pair["pos"], "arm": code,
                                      "form": audit.opening_form(pair["pos"])})
    for code, directory, style in arms:
        plan["arms"][code] = {"directory": str(directory), "style": style,
                              "generators": audit.generators_of(docs[code]), "traits": len(docs[code])}
    return plan, sorted(changed)


def cmd_plan_arms(args) -> None:
    out_dir = Path(args.out)
    stems = json.loads(Path(args.stems).read_text(encoding="utf-8"))
    kinds = json.loads(Path(args.kinds).read_text(encoding="utf-8")) if args.kinds else None
    if kinds:
        bad = {s: k for s, k in kinds.items() if k not in KINDS}
        if bad:
            raise SystemExit(f"kinds must be one of {KINDS}: {bad}")
    existing = load_plan(out_dir) if args.add else None
    arms = [parse_arm_spec(a) for a in args.arm]
    plan, left_out = build_arms_plan(arms, stems, args.n_questions, kinds, existing, args.purpose or "",
                                     entity=args.entity)
    write_json(out_dir / "plan.json", plan)
    n = sum(len(t["variants"]) * len(t["questions"]) for t in plan["traits"].values())
    print(f"{out_dir / 'plan.json'}: {len(plan['traits'])} traits, arms {list(plan['arms'])}, "
          f"{n} responses in all", file=sys.stderr)
    for code, meta in plan["arms"].items():   # arms added by an older builder carry less
        print(f"  {code}: {meta.get('traits', '?')} files, written by {meta.get('generators', meta)}", file=sys.stderr)
    if left_out:
        print(f"  left out, label or description differs between arms: {left_out}", file=sys.stderr)


def arm_shares(plan: dict, out_dir: Path) -> dict[str, dict[str, list[float]]]:
    """arm -> trait -> the share of responses scored 3 of each of its instructions that were judged."""
    out: dict[str, dict[str, list[float]]] = defaultdict(dict)
    for trait, t in plan["traits"].items():
        path = out_dir / "scores" / f"{trait}.json"
        scores = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        for v in t["variants"]:
            vals = [s for k, s in scores.items() if k.rsplit("_q", 1)[0] == v["name"]]
            if vals:
                out[v["arm"]].setdefault(trait, []).append(100 * sum(s == 3 for s in vals) / len(vals))
    return out


def form_shares(plan: dict, out_dir: Path) -> dict[str, dict[str, list[float]]]:
    """arm -> opening form -> the share of responses scored 3 of each instruction with that opening
    (the variant's ``form``, from the audit's classifier).  Within one arm this compares openings
    on the same traits, the way the 8slot data first showed the statement openings failing."""
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for trait, t in plan["traits"].items():
        path = out_dir / "scores" / f"{trait}.json"
        scores = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        for v in t["variants"]:
            vals = [s for k, s in scores.items() if k.rsplit("_q", 1)[0] == v["name"]]
            if vals and v.get("arm"):
                out[v["arm"]][v.get("form", "unclassified")].append(100 * sum(s == 3 for s in vals) / len(vals))
    return out


def paired_over_traits(base: dict[str, float], arm: dict[str, float], rng, reps: int = 4000) -> dict:
    """The arm's mean minus the baseline's over the traits both have: interval by resampling traits,
    p by a sign-flip permutation test, and the count of traits better and worse."""
    common = sorted(set(base) & set(arm))
    d = np.array([arm[t] - base[t] for t in common], dtype=float)
    if not len(d):
        return {"traits": 0}
    idx = rng.integers(0, len(d), size=(reps, len(d)))
    lo, hi = np.percentile(d[idx].mean(axis=1), [2.5, 97.5])
    signs = rng.choice([-1.0, 1.0], size=(20000, len(d)))
    p = (np.sum(np.abs((signs * d).mean(axis=1)) >= abs(d.mean()) - 1e-9) + 1) / 20001
    return {"traits": len(common), "baseline_mean": float(np.mean([base[t] for t in common])),
            "arm_mean": float(np.mean([arm[t] for t in common])), "difference": float(d.mean()),
            "interval": (float(lo), float(hi)), "p": float(p),
            "better": int((d > 0).sum()), "worse": int((d < 0).sum())}


def arms_report(plan: dict, out_dir: Path, baseline: str, arms: list[str], seed: int = 20260929) -> dict:
    rng = np.random.default_rng(seed)
    shares = arm_shares(plan, out_dir)
    kinds = {t: v.get("kind", "unclassified") for t, v in plan["traits"].items()}
    report = {"baseline": baseline, "arms": arms, "by_kind": {}, "instructions": {}, "traits": {}}
    groups = [("all", None)] + [(k, k) for k in KINDS if k in kinds.values()]
    for label, kind in groups:
        row = {}
        for arm in [baseline] + arms:
            per = {t: float(np.mean(v)) for t, v in shares.get(arm, {}).items() if kind is None or kinds[t] == kind}
            row[arm] = {"traits": len(per), "mean": float(np.mean(list(per.values()))) if per else float("nan")}
            if arm != baseline:
                b = {t: float(np.mean(v)) for t, v in shares.get(baseline, {}).items() if kind is None or kinds[t] == kind}
                row[arm]["against_baseline"] = paired_over_traits(b, per, rng)
        report["by_kind"][label] = row
    for arm in [baseline] + arms:
        flat = [x for v in shares.get(arm, {}).values() for x in v]
        per_trait = {t: v for t, v in shares.get(arm, {}).items()}
        n3 = sorted(500 * np.mean(v) / 100 for v in per_trait.values()) if per_trait else [float("nan")]
        report["instructions"][arm] = {
            "n": len(flat), "under_50": 100 * np.mean([x < 50 for x in flat]) if flat else float("nan"),
            "at_least_90": 100 * np.mean([x >= 90 for x in flat]) if flat else float("nan"),
            "traits_with_two_or_more_failing": int(sum(sum(x < 50 for x in v) >= 2 for v in per_trait.values())),
            "weakest_trait_scored_3_of_500": float(n3[0])}
        report["traits"][arm] = {t: float(np.mean(v)) for t, v in per_trait.items()}
    forms = form_shares(plan, out_dir)
    report["forms"] = {arm: {f: {"n": len(v), "mean": float(np.mean(v))}
                             for f, v in sorted(forms.get(arm, {}).items(), key=lambda kv: -len(kv[1]))}
                       for arm in [baseline] + arms}
    return report


def render_arms_report(report: dict) -> str:
    base, arms = report["baseline"], report["arms"]
    lines = [f"share of responses scored 3, mean over traits; differences paired with {base} on the same traits"]
    for label, row in report["by_kind"].items():
        cells = "   ".join(f"{a} {row[a]['mean']:5.1f}%" for a in [base] + arms if a in row)
        lines.append(f"  {label:12s} traits {row[base]['traits']:3d}   {cells}")
        for a in arms:
            c = row[a].get("against_baseline", {})
            if c.get("traits"):
                lines.append(f"      {a} minus {base}: {c['difference']:+5.1f} ({c['interval'][0]:+.1f} to {c['interval'][1]:+.1f})"
                             f"  p={c['p']:.4f}   better in {c['better']}, worse in {c['worse']} of {c['traits']}")
    lines.append("instructions: under 50% scored 3, 90% or more, traits with two or more failing, weakest trait's "
                 "responses scored 3 of the extraction's 500 (floor 50)")
    for a in [base] + arms:
        r = report["instructions"][a]
        lines.append(f"  {a:8s} n={r['n']:4d}   under 50%: {r['under_50']:5.1f}%   90% or more: {r['at_least_90']:5.1f}%   "
                     f"two or more failing: {r['traits_with_two_or_more_failing']:3d}   weakest {r['weakest_trait_scored_3_of_500']:5.0f}")
    if report.get("forms"):
        lines.append("share scored 3 by opening, per arm (instructions with that opening; not paired)")
        for a in [base] + arms:
            cells = "   ".join(f"{f} {c['mean']:5.1f}% (n={c['n']})" for f, c in report["forms"].get(a, {}).items())
            lines.append(f"  {a:8s} {cells}")
    return "\n".join(lines)


def cmd_arms_report(args) -> None:
    out_dir = Path(args.out)
    plan = load_plan(out_dir)
    arms = args.arm or [a for a in plan.get("arms", {}) if a != args.baseline]
    report = arms_report(plan, out_dir, args.baseline, arms, seed=args.seed)
    print(render_arms_report(report))
    if args.write:
        write_json(out_dir / "arms_report.json", {"written": datetime.date.today().isoformat(), **report})
        print(f"\nwrote {out_dir / 'arms_report.json'}", file=sys.stderr)


# ---------------------------------------------------------------------------
# openings: one body under several openings (2026-11-06)
# ---------------------------------------------------------------------------
# The October extraction showed the fifth opening of the trait generator's menu, "You are <adjective>: ...",
# keeping about ten points less than its four "someone who" siblings and failing outright for some thirty traits:
# Qwen answers as the plain assistant.  Roger (2026-11-06) asked for other openings to be tried against the old
# criteria and new ones, and for fewer openings that share the words "someone who".  Each arm is one instruction
# per trait: an existing instruction as it stands, the same instruction with only its opening changed
# (mechanically, or by a model that is given the opening alone to rewrite), or one written blind by an agent that
# never saw ours (reports/opening_forms/blind_writing/).

#: The four "someone who" openings of the trait generator's menu, by arm.
WHO_SOURCES = {"W1": "Be someone who ", "W2": "Become someone who ",
               "W3": "From now on, you are someone who ", "W4": "You are someone who "}
#: arm -> (the arm whose instruction it changes, the new opening)
WHO_SWAPS = {"W5": ("W1", "Be a person who "), "W6": ("W4", "You are a person who "),
             "W7": ("W3", "From now on, you are a person who "), "W8": ("W4", "You are the kind of person who "),
             # one role-play-like opening (Roger: willing to have some, if not every one says "someone")
             "R1": ("W2", "Speak as a person who ")}
ADJECTIVE_ARMS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8")
#: The blind agent's opening families kept, by index in its file.  Roger, 2026-11-06: the named character (2) is
#: a hard no; "Answer as someone who" (1) frames the model as answering questions.
BLIND_FAMILIES = {"B0": 0, "B3": 3, "B4": 4}
#: Each arm against the arm it was made from or is the alternative to, for the paired comparison.
ARM_PAIRS = (("W5", "W1"), ("W6", "W4"), ("W7", "W3"), ("W8", "W4"), ("R1", "W2"),
             ("A2", "A1"), ("A3", "A1"), ("A4", "A1"), ("A5", "A1"), ("A6", "A1"), ("A7", "A1"), ("A8", "A1"),
             ("B0", "A1"), ("B3", "A8"), ("B4", "R1"))
CURRENT_MENU = ("W1", "W2", "W3", "W4", "A1")
#: Words of an arm's opening that an answer may repeat (Roger: responses tend to repeat prompt wording).
ECHO_PHRASES = {"W1": ("someone who",), "W2": ("someone who",), "W3": ("someone who",), "W4": ("someone who",),
                "W5": ("a person who",), "W6": ("a person who",), "W7": ("a person who",), "W8": ("kind of person",),
                "R1": ("a person who",), "A3": ("by nature",), "A4": ("at heart",), "A5": ("always been",),
                "A6": ("who you are",), "A7": ("someone who",)}
OPENING_KINDS = KINDS + ("unclassified",)
DEFAULT_REWRITE_MODEL = "claude-sonnet-5-5"
# Sonnet 5.5 thinks before it answers unless told otherwise; 400 cut 16 of 176 replies before their JSON
REWRITE_MAX_TOKENS = 4000
REWRITE_ATTEMPTS = 3
REWRITE_FILE = "rewrites.json"

_NOT_ADJECTIVE = r"(?!someone\b|a person\b|the kind\b|the type\b)"
_ADJ_COLON = re.compile(r"You are " + _NOT_ADJECTIVE + r"([^:.;!?]{1,80}):\s+(\S.*)\Z", re.S)
_ADJ_SENTENCE = re.compile(r"You are " + _NOT_ADJECTIVE + r"([^.!?]+)([.!?])(\s+\S.*)?\Z", re.S)
_PREPOSITION = re.compile(r"(?i)\b(with|to|of|in|about|for|by|from|at|on|than|as|and|or)\b")


@dataclass(frozen=True)
class AdjectiveOpening:
    """A "You are <adjective>" instruction split into its opening and the rest, which every A arm keeps.
    ``colon``: "You are X: rest" (the trait generator's form); otherwise "You are <predicate>. rest", whose
    opening is the first sentence and whose ``x`` is that sentence's predicate."""
    text: str
    x: str
    rest: str
    colon: bool

    @property
    def opening(self) -> str:
        return f"You are {self.x}:" if self.colon else f"You are {self.x}."

    @property
    def simple(self) -> bool:
        """Whether "You are a X person" can be made by rule: one or two words, no article, no preposition."""
        return (self.colon and len(self.x.split()) <= 2 and not re.match(r"(?i)(a|an|the)\b", self.x)
                and not _PREPOSITION.search(self.x))

    def compose(self, clause: str) -> str:
        """``clause`` (an opening without its closing punctuation) followed by the rest as it is."""
        clause = clause.strip().rstrip(":.;")
        return f"{clause}: {self.rest}" if self.colon else f"{clause}.{self.rest}"


def split_adjective(text: str) -> AdjectiveOpening | None:
    s = text.strip()
    m = _ADJ_COLON.match(s)
    if m:
        return AdjectiveOpening(text=s, x=m.group(1).strip(), rest=m.group(2), colon=True)
    m = _ADJ_SENTENCE.match(s)
    if m and m.group(2) == ".":
        return AdjectiveOpening(text=s, x=m.group(1).strip(), rest=m.group(3) or "", colon=False)
    return None


def article(word: str) -> str:
    w = word.lower()
    if re.match(r"(hon|hour|heir)", w):
        return "an"
    if re.match(r"(uni|use|usu|uti|eu|one\b|once)", w):
        return "a"
    return "an" if w[:1] in "aeiou" else "a"


def adjective_arms(adj: AdjectiveOpening, rewrite: dict | None) -> dict[str, dict]:
    """The A arms made from one adjective instruction: ``{arm: {"text", "opening", "built"}}``; an arm that
    needs a rewrite missing from ``rewrite`` is left out."""
    tail = adj.text[len("You are "):]
    out = {"A1": {"text": adj.text, "opening": adj.opening, "built": "as is"},
           "A3": {"text": "By nature, you are " + tail, "opening": f"By nature, you are {adj.x}", "built": "swap"},
           "A4": {"text": "At heart, you are " + tail, "opening": f"At heart, you are {adj.x}", "built": "swap"},
           "A5": {"text": "You have always been " + tail, "opening": f"You have always been {adj.x}",
                  "built": "swap"},
           "A7": {"text": "You are someone who is " + tail, "opening": f"You are someone who is {adj.x}",
                  "built": "swap"}}
    if adj.colon:
        rest = adj.rest[:1].upper() + adj.rest[1:]
        out["A6"] = {"text": f"This is who you are: {adj.x}. {rest}", "opening": f"This is who you are: {adj.x}.",
                     "built": "swap"}
    else:
        out["A6"] = {"text": "This is who you are: " + tail, "opening": f"This is who you are: {adj.x}.",
                     "built": "swap"}
    if adj.simple:
        clause = f"You are {article(adj.x)} {adj.x} person"
        out["A2"] = {"text": adj.compose(clause), "opening": clause, "built": "swap"}
    elif rewrite and rewrite.get("a_person"):
        out["A2"] = {"text": adj.compose(rewrite["a_person"]), "opening": rewrite["a_person"], "built": "rewrite"}
    if rewrite and rewrite.get("trait_first"):
        out["A8"] = {"text": adj.compose(rewrite["trait_first"]), "opening": rewrite["trait_first"],
                     "built": "rewrite"}
    return out


def who_arms(instructions: list[str]) -> dict[str, dict]:
    """The W arms and R1 made from a trait's "someone who" instructions; an arm whose source is missing is
    left out."""
    out = {}
    for arm, prefix in WHO_SOURCES.items():
        hit = next((s for s in instructions if s.startswith(prefix)), None)
        if hit is not None:
            out[arm] = {"text": hit, "opening": prefix.strip(), "built": "as is"}
    for arm, (source, prefix) in WHO_SWAPS.items():
        if source in out:
            body = out[source]["text"][len(WHO_SOURCES[source]):]
            out[arm] = {"text": prefix + body, "opening": prefix.strip(), "built": "swap", "source": source}
    return out


_NEGATING_PREFIX = re.compile(r"(?i)^(un|in|im|ir|il|dis|non-?)(?=[a-z]{4,}$)")


def opposite_words(label: str, negative_label: str | None) -> list[str]:
    """Words that name a trait's opposite: its real negative label (not a ``non-X`` placeholder, without a
    standard's suffix) and, for a label made by a negating prefix, the word without it (unfair -> fair)."""
    words = []
    if negative_label and not negative_label.lower().startswith("non-"):
        words.append(re.sub(r"\s*\(.*\)\s*$", "", negative_label).strip())
    m = _NEGATING_PREFIX.match(label.strip())
    if m:
        words.append(label.strip()[m.end():])
    return [w for w in words if w]


def names_opposite(text: str, label: str, negative_label: str | None) -> bool:
    """Whether ``text`` names the trait's opposite (``opposite_words``), as the word or with a common ending
    (fair, fairness, fairly)."""
    norm = re.sub(r"[-_]", " ", text.lower())
    return any(re.search(r"\b" + re.escape(re.sub(r"[-_]", " ", w.lower())) + r"(?:ness|ly|ity|s)?\b", norm)
               for w in opposite_words(label, negative_label))


#: A negation in an opening: the trait put as the absence of something ("Nothing much ruffles you"), which
#: ``names_opposite`` does not see unless the opposite is named.
NEGATION = re.compile(r"(?i)(\b(?:not|never|no|nothing|nobody|without|none)\b|n't\b)")


def blind_instructions(path: Path) -> dict[str, list[str]]:
    """stem -> the blind agent's five instructions."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for stem, entry in doc["traits"].items():
        lists = [v for v in entry.values() if isinstance(v, list)] if isinstance(entry, dict) else [entry]
        if lists:
            out[stem] = list(lists[0])
    return out


def first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.!?:])(\s|\Z)", text.strip(), re.S)
    return (m.group(1) if m else text).strip()


def trait_questions(doc: dict, mode: str, n: int) -> list[str]:
    """The questions a trait is asked: ``generic``, the shared bank's (``arm_questions``); ``own``, ``n`` of
    the trait file's own, spread over them (the depth check's, as in reports/opening_forms/depth)."""
    if mode == "generic":
        return arm_questions(n)
    own = [q if isinstance(q, str) else q.get("question", "") for q in doc.get("questions", [])]
    own = [q for q in own if q]
    if len(own) < n:
        raise SystemExit(f"{doc.get('positive_label')}: {len(own)} questions of its own, fewer than {n}")
    step = len(own) // n
    return own[::step][:n]


def build_openings_plan(stems: list[str], traits_dir: Path, *, kinds: dict[str, str] | None = None,
                        problem: set[str] | None = None, questions: str = "generic", n_questions: int = 20,
                        rewrites: dict | None = None, blind: dict[str, list[str]] | None = None,
                        purpose: str = "", max_tokens: int = 1024) -> tuple[dict, dict[str, list[str]]]:
    """The openings plan: per trait, every arm that can be made (W, R1, A, and B for the blind agent's
    traits), each a variant named by its arm.  Returns the plan and, per arm, the traits it is missing for."""
    plan = {"purpose": purpose, "n_questions": n_questions, "questions": questions, "entity": "trait",
            "max_tokens": max_tokens, "temperature": TEMPERATURE, "judge": dict(STEP3_JUDGE),
            "arm_pairs": [list(p) for p in ARM_PAIRS], "traits": {}}
    missing: dict[str, list[str]] = defaultdict(list)
    all_arms = list(WHO_SOURCES) + list(WHO_SWAPS) + list(ADJECTIVE_ARMS) + list(BLIND_FAMILIES)
    for stem in stems:
        path = Path(traits_dir) / f"{stem}.json"
        if not path.exists():
            missing["(no file)"].append(stem)
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        label = doc.get("positive_label", stem)
        neg = doc.get("negative_label")
        pos = [p["pos"] for p in doc["instruction"]]
        arms = who_arms(pos)
        adj = next((a for a in (split_adjective(s) for s in pos) if a is not None), None)
        if adj is not None:
            arms.update(adjective_arms(adj, (rewrites or {}).get(stem)))
        for code, index in BLIND_FAMILIES.items():
            texts = (blind or {}).get(stem)
            if texts and index < len(texts):
                arms[code] = {"text": texts[index], "opening": first_sentence(texts[index]), "built": "blind"}
        variants = []
        for code in all_arms:
            if code not in arms:
                if code not in BLIND_FAMILIES or stem in (blind or {}):
                    missing[code].append(stem)
                continue
            a = arms[code]
            variants.append({"name": code, "arm": code, "text": a["text"], "opening": a["opening"],
                             "built": a["built"], "source": a.get("source"),
                             "opening_names_opposite": names_opposite(a["opening"], label, neg),
                             "opening_negates": bool(NEGATION.search(a["opening"]))})
        plan["traits"][stem] = {
            "label": label, "description": doc["description"], "negative_label": neg,
            "kind": (kinds or {}).get(stem, "unclassified"), "problem": stem in (problem or set()),
            "adjective": None if adj is None else {"x": adj.x, "colon": adj.colon},
            "questions": trait_questions(doc, questions, n_questions), "variants": variants}
    return plan, dict(missing)


def problem_instructions(scores_dir: Path, traits_dir: Path, n_questions: int = 100,
                         alpha: float = 1e-3) -> list[dict]:
    """Every instruction of an extraction run that keeps under half the mean of its trait's other four
    (share of responses scored 3) and is below them by a one-sided binomial test at ``alpha`` (the measure of
    2026-11-06, Roger's criterion).  The opening is classified by the audit's ``opening_form``."""
    from scipy.stats import binom
    from data_analysis import audit_trait_instructions as audit  # noqa: E402  (a sibling script)
    rows = []
    for f in sorted(Path(scores_dir).glob("*.json")):
        stem = f.stem
        ip = Path(traits_dir) / f"{stem}.json"
        if stem in ("judge_rubric", "usage") or not ip.exists():
            continue
        pos = [p["pos"] for p in json.loads(ip.read_text(encoding="utf-8"))["instruction"][:5]]
        sc = json.loads(f.read_text(encoding="utf-8"))
        k, n = [], []
        for p in range(len(pos)):
            v = [sc.get(f"pos_p{p}_q{q}") for q in range(n_questions)]
            v = [x for x in v if x is not None]
            k.append(sum(x == 3 for x in v))
            n.append(len(v))
        for p in range(len(pos)):
            others = [k[i] / n[i] for i in range(len(pos)) if i != p and n[i]]
            if not n[p] or not others:
                continue
            m = float(np.mean(others))
            if k[p] / n[p] < 0.5 * m and binom.cdf(k[p], n[p], m) < alpha:
                adj = split_adjective(pos[p])
                rows.append({"stem": stem, "index": p, "form": audit.opening_form(pos[p]),
                             "adjective": adj is not None, "kept": k[p], "n": n[p],
                             "share": round(k[p] / n[p], 4), "others": round(m, 4), "text": pos[p]})
    return rows


def cmd_list_failures(args) -> None:
    rows = problem_instructions(Path(args.scores_dir), Path(args.traits_dir), alpha=args.alpha)
    write_json(Path(args.write), {"scores_dir": args.scores_dir, "alpha": args.alpha,
                                  "written": datetime.date.today().isoformat(), "instructions": rows})
    adj = sorted({r["stem"] for r in rows if r["adjective"]})
    print(f"{len(rows)} instructions keep under half their siblings (p < {args.alpha}), {len({r['stem'] for r in rows})}"
          f" traits; {len(adj)} of the instructions open 'You are <adjective>'; wrote {args.write}", file=sys.stderr)


# --- rewrites ---------------------------------------------------------------

REWRITE_PROMPT = """\
This is for a research dataset on personality traits in language models. Each trait has short system \
prompts, each of which tells a model who to be. We are testing how the opening words of such a prompt \
decide whether the model takes the trait on, so we need the same prompt with only its opening changed.

<trait>
{label}
</trait>

<trait_description>
{description}
</trait_description>

The prompt as it stands:

<prompt>
{text}
</prompt>

Its opening is "{opening}". Everything after it stays exactly as it is; you write only replacement \
openings, which will be followed directly by {follows}.

Write two replacement openings.

1. trait_first: an opening that states the trait as a plain fact about the person, without the words \
"you are". Make a noun the subject: the trait, its quality, or a part of the person ("Generosity runs \
through everything you do", "Your mind drifts off at the slightest pull"). Write it in words that fit \
this trait, not a stock phrase such as "is your nature" or "second nature", and keep to what the opening \
says, adding nothing that it and the description do not say. Say what the person is like, not what they \
lack: do not describe the trait as the absence of its opposite ("Nothing about you is composed" and "Resilience is not in you" \
are the kind to avoid). No wording of acting or playing a part, and nothing about questions, answers, \
users or assistants. {length}

2. a_person: {a_person}

Give your reason in one short sentence, then, on a line of its own, a JSON object with the two openings, \
each without closing punctuation:

{{"trait_first": "<opening>", "a_person": "<opening>"}}"""

_ROLE_PLAY_WORDS = re.compile(r"(?i)\b(play|plays|playing|act as|acting|speak as|character|persona|role|pretend)\b")


def rewrite_max_words(adj: AdjectiveOpening) -> int:
    """The longest trait_first opening accepted: 14 words, or, when the opening is a whole first sentence
    (no colon), that sentence's length and four more, so that what it says can be kept."""
    return max(14, len(adj.opening.split()) + 4)


def rewrite_prompt(label: str, description: str, adj: AdjectiveOpening) -> str:
    follows = (f'a colon and the rest of the prompt (": {adj.rest[:60]}...")' if adj.colon
               else f'a full stop and the rest of the prompt (".{adj.rest[:60]}...")')
    length = ("Four to twelve words." if adj.colon else
              "Keep what the opening says; about as long as the opening, and no more than "
              f"{rewrite_max_words(adj)} words.")
    plain = ('with one to three plain words before "person" (an adjective, or an adverb and an adjective; no '
             'chains of hyphenated words)')
    a_person = ('the opening rewritten as "You are a ... person" (or "You are an ... person"), ending with the '
                f'word "person", {plain}. Keep the core of the opening\'s meaning; where its wording does not fit '
                'before "person", leave the detail to the rest of the prompt.' if adj.colon else
                'the opening rewritten as "You are a ... person ..." (or "You are an ..."), '
                f'{plain}; the sentence may go on after "person" to keep what the opening says, but not with "who".')
    return REWRITE_PROMPT.format(label=judge_form_of_label(label), description=description, text=adj.text,
                                 opening=adj.opening.rstrip(":."), follows=follows, length=length,
                                 a_person=a_person)


def parse_rewrite(text: str, max_words: int = 14, colon: bool = True, opening: str = "") -> dict:
    """The two openings of a rewrite reply, checked; raises ValueError naming what is wrong.  A word of chat
    or of questions and answers is allowed when the opening it replaces already has it ("the ordinary answer
    feels like a failure")."""
    from data_analysis import audit_trait_instructions as audit  # noqa: E402  (a sibling script)
    raw = (text or "").strip()
    start, end = raw.rfind("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    d = json.loads(raw[start:end + 1])
    out = {}
    for key in ("trait_first", "a_person"):
        v = d.get(key)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{key} is missing")
        out[key] = v.strip().rstrip(":.;").strip()
    tf = out["trait_first"]
    if re.match(r"(?i)you\b", tf) or re.search(r"(?i)\byou(?: are|'re)\b", tf):
        raise ValueError(f'trait_first uses "you are" or opens with "you": {tf!r}')
    if not 3 <= len(tf.split()) <= max_words:
        raise ValueError(f"trait_first has {len(tf.split())} words: {tf!r}")
    def new(pattern: re.Pattern | str) -> bool:
        return any(not re.search(r"(?i)\b" + re.escape(w) + r"\b", opening)
                   for w in (m.group(0) for m in re.finditer(pattern, tf)))
    if new(audit.CHAT_WORDS) or new(_ROLE_PLAY_WORDS) or new(r"(?i)\b(answers?|questions?)\b"):
        raise ValueError(f"trait_first speaks of a part to play or of questions and answers: {tf!r}")
    if new(r"(?i)\bnature\b"):
        raise ValueError(f'trait_first leans on "nature", which "By nature, you are" already tests: {tf!r}')
    shape = r"You are an? (?!person\b)(\S.*?) person" + (r"\Z" if colon else r"\b(?! who\b)")
    m = re.match(shape, out["a_person"])
    if not m:
        raise ValueError(f'a_person is not "You are a ... person{"" if colon else " ..."}": {out["a_person"]!r}')
    if len(m.group(1).split()) > 4 or re.search(r"\w-\w+-\w", m.group(1)):
        raise ValueError(f'a_person needs one to three plain words before "person": {out["a_person"]!r}')
    return out


async def rewrite_one(client, model: str, stem: str, label: str, description: str, adj: AdjectiveOpening,
                      limiter, usage) -> dict:
    from assistant_axis.judge import call_anthropic_judge_single
    prompt = rewrite_prompt(label, description, adj)
    errors = []
    for attempt in range(REWRITE_ATTEMPTS):
        asked = prompt if not errors else (f"{prompt}\n\nA previous reply could not be used: {errors[-1]}. "
                                           f"Reply again, keeping to the rules and the format.")
        text = await call_anthropic_judge_single(client, asked, model, REWRITE_MAX_TOKENS, limiter, usage=usage,
                                                 reject_truncated=True)
        try:
            out = parse_rewrite(text, rewrite_max_words(adj), adj.colon, adj.opening)
        except (ValueError, json.JSONDecodeError) as e:
            errors.append(str(e))
            continue
        return {**out, "model": model, "attempts": attempt + 1, "opening": adj.opening, "colon": adj.colon,
                "reply": text, "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]}
    return {"error": errors[-1] if errors else "no reply", "model": model, "attempts": REWRITE_ATTEMPTS}


async def rewrite_openings(args) -> None:
    out_dir = Path(args.out)
    stems = json.loads(Path(args.stems).read_text(encoding="utf-8"))
    path = out_dir / REWRITE_FILE
    done = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    todo = []
    for stem in stems:
        if stem in done and "error" not in done[stem] and done[stem].get("model") == args.model:
            continue
        ip = Path(args.traits_dir) / f"{stem}.json"
        if not ip.exists():
            continue
        doc = json.loads(ip.read_text(encoding="utf-8"))
        adj = next((a for a in (split_adjective(p["pos"]) for p in doc["instruction"]) if a is not None), None)
        if adj is not None:
            todo.append((stem, doc.get("positive_label", stem), doc["description"], adj))
    rate_in, rate_out = price_for_model(args.model)
    est = sum(len(rewrite_prompt(lab, d, a)) / 3.6 * rate_in + 250 * rate_out for _, lab, d, a in todo) / 1e6
    print(f"{len(todo)} openings to rewrite with {args.model}; about ${est:.2f}", file=sys.stderr)
    if args.dry_run or not todo:
        if todo and args.show:
            print(rewrite_prompt(*todo[0][1:]))
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    client = anthropic.AsyncAnthropic()
    limiter = RateLimiter(args.requests_per_second)
    usage = CheckpointedUsage(out_dir)
    try:
        results = await asyncio.gather(*(rewrite_one(client, args.model, s, lab, d, a, limiter, usage)
                                         for s, lab, d, a in todo))
    finally:
        usage.close()
    for (stem, *_), r in zip(todo, results):
        done[stem] = r
    write_json(path, done)
    bad = [s for (s, *_), r in zip(todo, results) if "error" in r]
    print(f"wrote {path}: {len(todo) - len(bad)} rewritten, {len(bad)} failed {bad[:10]}", file=sys.stderr)


def cmd_rewrite_openings(args) -> None:
    asyncio.run(rewrite_openings(args))


def cmd_plan_openings(args) -> None:
    out_dir = Path(args.out)
    if (out_dir / "plan.json").exists() and not args.replace:
        raise SystemExit(f"{out_dir / 'plan.json'} exists; --replace to write it again (responses and scores are "
                         f"kept by variant name)")
    stems = json.loads(Path(args.stems).read_text(encoding="utf-8"))
    kinds = json.loads(Path(args.kinds).read_text(encoding="utf-8")) if args.kinds else None
    bad = {s: k for s, k in (kinds or {}).items() if k not in OPENING_KINDS}
    if bad:
        raise SystemExit(f"kinds must be one of {OPENING_KINDS}: {bad}")
    problem = None
    if args.problem:
        problem = {r["stem"] for r in json.loads(Path(args.problem).read_text(encoding="utf-8"))["instructions"]
                   if r["adjective"]}
    rw_path = Path(args.rewrites) if args.rewrites else out_dir / REWRITE_FILE
    rewrites = json.loads(rw_path.read_text(encoding="utf-8")) if rw_path.exists() else {}
    blind = blind_instructions(Path(args.blind)) if args.blind else None
    plan, missing = build_openings_plan(stems, Path(args.traits_dir), kinds=kinds, problem=problem,
                                        questions=args.questions, n_questions=args.n_questions, rewrites=rewrites,
                                        blind=blind, purpose=args.purpose or "", max_tokens=args.max_tokens)
    plan["rewrites"] = {"file": str(rw_path), "models": sorted({r.get("model", "?") for r in rewrites.values()})}
    if args.blind:
        plan["blind"] = args.blind
    write_json(out_dir / "plan.json", plan)
    n = sum(len(t["variants"]) * len(t["questions"]) for t in plan["traits"].values())
    print(f"{out_dir / 'plan.json'}: {len(plan['traits'])} traits, {n} responses in all", file=sys.stderr)
    for code, stems_missing in sorted(missing.items()):
        print(f"  {code}: missing for {len(stems_missing)} traits {stems_missing[:8]}", file=sys.stderr)


# --- the report -------------------------------------------------------------

AI_SELF = re.compile(r"(?i)\b(as an ai\b|i'?m an ai\b|i am an ai\b|an ai (?:language )?model|as a language model"
                     r"|i (?:don'?t|do not) have (?:personal )?(?:feelings|experiences|emotions|opinions|a body))")


def listy(text: str) -> bool:
    """The organised-overview shape of a plain assistant answer: three or more list lines and a heading or two
    bold labels."""
    lines = text.splitlines()
    items = sum(bool(re.match(r"\s*(?:[-*•]|\d+[.)])\s+", ln)) for ln in lines)
    heads = sum(bool(re.match(r"\s*#{1,6}\s", ln)) for ln in lines) + len(re.findall(r"\*\*[^*\n]{2,60}\*\*", text)) // 2
    return items >= 3 and heads >= 1


def label_words(t: dict) -> list[str]:
    words = [judge_form_of_label(t["label"]).lower()]
    adj = t.get("adjective")
    if adj and adj.get("colon") and len(adj["x"].split()) <= 2:
        words.append(adj["x"].lower())
    return [w for w in words if w]


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"\b" + re.escape(phrase.lower()) + r"\b", re.sub(r"[-_]", " ", text.lower())) is not None


def openings_stats(plan: dict, out_dir: Path) -> dict[str, dict[str, dict]]:
    """trait -> arm -> counts over its responses: judged, scored 3, scored 0, answers repeating the arm's
    opening, answers naming the trait, answers speaking as an AI, answers in the overview shape."""
    out: dict[str, dict[str, dict]] = {}
    for trait, t in plan["traits"].items():
        p = out_dir / "scores" / f"{trait}.json"
        scores = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        words = label_words(t)
        per = {v["name"]: {"n": 0, "k3": 0, "k0": 0, "responses": 0, "echo": 0, "names_trait": 0, "ai": 0,
                           "listy": 0} for v in t["variants"]}
        for r in read_jsonl(out_dir / "responses" / f"{trait}.jsonl"):
            c = per.get(r["variant"])
            if c is None:
                continue
            text = r["conversation"][-1]["content"]
            c["responses"] += 1
            c["echo"] += any(contains_phrase(text, ph) for ph in ECHO_PHRASES.get(r["variant"], ()))
            c["names_trait"] += any(contains_phrase(text, w) for w in words)
            c["ai"] += bool(AI_SELF.search(text))
            c["listy"] += listy(text)
            s = scores.get(key_of(r["variant"], r["question_index"]))
            if s is not None:
                c["n"] += 1
                c["k3"] += s == 3
                c["k0"] += s == 0
        out[trait] = per
    return out


def flagged(k: int, n: int, others: list[float], alpha: float = 1e-3) -> bool:
    """Roger's criterion: under half the mean of the others, and below it by a one-sided binomial test."""
    from scipy.stats import binom
    if not n or not others:
        return False
    m = float(np.mean(others))
    # a plain bool: summed, scipy's numpy bool gives an int64 the JSON report cannot hold
    return bool(k / n < 0.5 * m and binom.cdf(k, n, m) < alpha)


def menu_report(stats: dict, plan: dict, menu: tuple[str, ...], alpha: float = 1e-3) -> dict:
    """A menu of five openings scored per trait (the traits that have all five): mean share scored 3, the
    traits with an instruction under half the mean of the other four (p < alpha, and without the test), the
    complete failures (under 10% scored 3), and the weakest trait."""
    rows = []
    for trait, per in stats.items():
        if not all(per.get(a, {}).get("n") for a in menu):
            continue
        rates = [per[a]["k3"] / per[a]["n"] for a in menu]
        flags = [flagged(per[a]["k3"], per[a]["n"], [r for j, r in enumerate(rates) if j != i], alpha)
                 for i, a in enumerate(menu)]
        halves = [rates[i] < 0.5 * np.mean([r for j, r in enumerate(rates) if j != i]) for i in range(len(menu))]
        rows.append({"trait": trait, "mean": float(np.mean(rates)), "flags": [a for a, f in zip(menu, flags) if f],
                     "halves": [a for a, h in zip(menu, halves) if h], "fails": [a for a, r in zip(menu, rates) if r < 0.1],
                     "problem": plan["traits"][trait].get("problem", False), "kind": plan["traits"][trait].get("kind")})
    if not rows:
        return {"menu": list(menu), "traits": 0}
    worst = min(rows, key=lambda r: r["mean"])
    def summary(sel):
        return {"traits": len(sel), "mean": 100 * float(np.mean([r["mean"] for r in sel])) if sel else float("nan"),
                "traits_flagged": sum(bool(r["flags"]) for r in sel),
                "traits_under_half": sum(bool(r["halves"]) for r in sel),
                "traits_with_a_failure": sum(bool(r["fails"]) for r in sel)}
    return {"menu": list(menu), **summary(rows), "problem_list": summary([r for r in rows if r["problem"]]),
            "flagged_by_arm": {a: sum(a in r["flags"] for r in rows) for a in menu},
            "weakest": {"trait": worst["trait"], "mean": 100 * worst["mean"]}}


def openings_report(plan: dict, out_dir: Path, menus: dict[str, tuple[str, ...]] | None = None,
                    seed: int = 20261106) -> dict:
    rng = np.random.default_rng(seed)
    stats = openings_stats(plan, out_dir)
    arms = sorted({v["name"] for t in plan["traits"].values() for v in t["variants"]},
                  key=lambda a: (a[0] != "W", a[0] != "R", a[0] != "A", a))
    groups = [("all", lambda t: True)] + [(k, (lambda k: lambda t: t.get("kind") == k)(k)) for k in KINDS
                                           if any(t.get("kind") == k for t in plan["traits"].values())]
    groups.append(("problem list", lambda t: t.get("problem", False)))
    report = {"arms": {}, "pairs": {}, "menus": {}}
    for arm in arms:
        cs = [(trait, per[arm]) for trait, per in stats.items() if arm in per and per[arm]["n"]]
        resp = sum(c["responses"] for _, c in cs)
        n = sum(c["n"] for _, c in cs)
        ref = {trait: [per[a]["k3"] / per[a]["n"] for a in WHO_SOURCES if per.get(a, {}).get("n")]
               for trait, per in stats.items()}
        report["arms"][arm] = {
            "traits": len(cs), "judged": n,
            "share_3": {g: 100 * float(np.mean([c["k3"] / c["n"] for tr, c in cs if f(plan["traits"][tr])]))
                        if any(f(plan["traits"][tr]) for tr, _ in cs) else float("nan") for g, f in groups},
            "share_0": 100 * sum(c["k0"] for _, c in cs) / n if n else float("nan"),
            "echo": 100 * sum(c["echo"] for _, c in cs) / resp if resp and arm in ECHO_PHRASES else None,
            "names_trait": 100 * sum(c["names_trait"] for _, c in cs) / resp if resp else float("nan"),
            "ai": 100 * sum(c["ai"] for _, c in cs) / resp if resp else float("nan"),
            "listy": 100 * sum(c["listy"] for _, c in cs) / resp if resp else float("nan"),
            "complete_failures": sum(c["k3"] / c["n"] < 0.1 for _, c in cs),
            "under_half_of_W1_W4": sum(flagged(c["k3"], c["n"], ref[tr]) for tr, c in cs),
            "opening_names_opposite": sum(v.get("opening_names_opposite", False) for t in plan["traits"].values()
                                          for v in t["variants"] if v["name"] == arm),
            "opening_negates": sum(v.get("opening_negates", False) for t in plan["traits"].values()
                                   for v in t["variants"] if v["name"] == arm),
            "built_by_rewrite": sum(v.get("built") == "rewrite" for t in plan["traits"].values()
                                    for v in t["variants"] if v["name"] == arm)}
    for arm, ref_arm in [tuple(p) for p in plan.get("arm_pairs", ARM_PAIRS)]:
        if arm not in report["arms"] or ref_arm not in report["arms"]:
            continue
        row = {}
        for g, f in groups:
            a = {tr: 100 * per[arm]["k3"] / per[arm]["n"] for tr, per in stats.items()
                 if per.get(arm, {}).get("n") and f(plan["traits"][tr])}
            b = {tr: 100 * per[ref_arm]["k3"] / per[ref_arm]["n"] for tr, per in stats.items()
                 if per.get(ref_arm, {}).get("n") and f(plan["traits"][tr])}
            row[g] = paired_over_traits(b, a, rng)
        report["pairs"][f"{arm} vs {ref_arm}"] = row
    menus = dict(menus or {})
    menus.setdefault("current", CURRENT_MENU)
    for a in ADJECTIVE_ARMS[1:] + ("R1",) + tuple(BLIND_FAMILIES):
        menus.setdefault(f"fifth={a}", CURRENT_MENU[:4] + (a,))
    for name, menu in menus.items():
        report["menus"][name] = menu_report(stats, plan, tuple(menu))
    return report


def render_openings_report(report: dict) -> str:
    lines = ["share of responses scored 3 (mean over traits), by group; then share scored 0, answers repeating "
             "the opening, naming the trait, speaking as an AI, in the overview shape; traits under 10%; traits "
             "under half their W1-W4 mean (p<0.001); openings naming the opposite; openings with a negation"]
    groups = list(next(iter(report["arms"].values()))["share_3"]) if report["arms"] else []
    lines.append(f"  {'arm':5s}{'traits':>7s}" + "".join(f"{g[:12]:>13s}" for g in groups)
                 + f"{'0':>6s}{'echo':>6s}{'names':>6s}{'AI':>5s}{'list':>6s}{'<10%':>6s}{'<half':>6s}{'opp':>5s}{'neg':>5s}")
    for arm, r in report["arms"].items():
        echo = "  -  " if r["echo"] is None else f"{r['echo']:5.1f}"
        lines.append(f"  {arm:5s}{r['traits']:7d}" + "".join(f"{r['share_3'][g]:12.1f}%" for g in groups)
                     + f"{r['share_0']:5.1f}%{echo:>6s}{r['names_trait']:5.1f}%{r['ai']:4.1f}%{r['listy']:5.1f}%"
                     + f"{r['complete_failures']:6d}{r['under_half_of_W1_W4']:6d}{r['opening_names_opposite']:5d}"
                     + f"{r.get('opening_negates', 0):5d}")
    lines.append("\npaired over traits: arm minus the arm it was made from (points scored 3; 95% interval; p; better/worse)")
    for name, row in report["pairs"].items():
        for g, c in row.items():
            if c.get("traits"):
                lines.append(f"  {name:10s} {g:14s} {c['difference']:+6.1f} ({c['interval'][0]:+.1f} to "
                             f"{c['interval'][1]:+.1f})  p={c['p']:.4f}  {c['better']}/{c['worse']} of {c['traits']}")
    lines.append("\nmenus of five, Roger's criterion (an instruction under half the mean of the other four, p<0.001): "
                 "mean scored 3; traits flagged; traits under half (no test); traits with an instruction under 10%")
    for name, m in report["menus"].items():
        if not m.get("traits"):
            continue
        pl = m["problem_list"]
        lines.append(f"  {name:12s} {','.join(m['menu']):22s} traits {m['traits']:3d}  mean {m['mean']:5.1f}%  "
                     f"flagged {m['traits_flagged']:3d}  under half {m['traits_under_half']:3d}  "
                     f"<10% {m['traits_with_a_failure']:3d}   problem list: {pl['traits']} traits, mean "
                     f"{pl['mean']:5.1f}%, flagged {pl['traits_flagged']}   weakest {m['weakest']['trait']} "
                     f"{m['weakest']['mean']:.0f}%")
    return "\n".join(lines)


def cmd_openings_report(args) -> None:
    out_dir = Path(args.out)
    plan = load_plan(out_dir)
    menus = {}
    for spec in args.menu or []:
        name, _, arms = spec.partition("=")
        menu = tuple(a.strip() for a in arms.split(",") if a.strip())
        if not name or len(menu) != 5:
            raise SystemExit(f"a menu is NAME=A,B,C,D,E (five arms): {spec!r}")
        menus[name] = menu
    report = openings_report(plan, out_dir, menus)
    print(render_openings_report(report))
    if args.write:
        write_json(out_dir / "openings_report.json", {"written": datetime.date.today().isoformat(), **report})
        print(f"\nwrote {out_dir / 'openings_report.json'}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan-replication", help="Write a plan that reruns instructions of the extraction run")
    p.add_argument("--out", required=True)
    p.add_argument("--traits", nargs="+", required=True)
    p.add_argument("--prompts", nargs="*", type=int, help="Only these instruction indices (default: all five)")
    p.add_argument("--n-questions", type=int, default=DEFAULT_N_QUESTIONS, help=f"(default: {DEFAULT_N_QUESTIONS})")
    p.set_defaults(func=cmd_plan_replication)

    p = sub.add_parser("plan-arms", help="Write a plan whose variants are the positive instructions of one or "
                                         "more arms (staged directories of trait files), for a paired comparison")
    p.add_argument("--out", required=True)
    p.add_argument("--arm", nargs="+", required=True, metavar="CODE=DIR[:STYLE@hash]",
                   help="An arm: its code in the plan, its directory, and optionally the style (and template hash) "
                        "its files must have been written under")
    p.add_argument("--stems", required=True, metavar="FILE", help="A JSON list of the traits")
    p.add_argument("--kinds", default=None, metavar="FILE",
                   help="A JSON object stem -> good | bad | indifferent, for the report by kind")
    p.add_argument("--n-questions", type=int, default=DEFAULT_ARM_QUESTIONS,
                   help=f"Generic questions per instruction, spread over the bank's first 100 (default: {DEFAULT_ARM_QUESTIONS})")
    p.add_argument("--add", action="store_true", help="Add the arms to the plan already in --out instead of writing a new one")
    p.add_argument("--entity", choices=ENTITIES, default="trait",
                   help="What the arms' files are (default: trait); a role is judged with its file's eval_prompt")
    p.add_argument("--purpose", default=None)
    p.set_defaults(func=cmd_plan_arms)

    p = sub.add_parser("arms-report", help="Arms against a baseline: share scored 3 by kind of trait, paired over traits")
    p.add_argument("--out", required=True)
    p.add_argument("--baseline", required=True, help="The arm the others are compared with")
    p.add_argument("--arm", nargs="*", default=None, help="The other arms (default: every other arm in the plan)")
    p.add_argument("--seed", type=int, default=20260929)
    p.add_argument("--write", action="store_true", help="Also write arms_report.json")
    p.set_defaults(func=cmd_arms_report)

    p = sub.add_parser("generate", help="Ask the model (OpenRouter)")
    p.add_argument("--out", required=True)
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"(default: {DEFAULT_MODEL})")
    p.add_argument("--provider", default=DEFAULT_PROVIDER,
                   help=f"OpenRouter host to pin, with no fallback (default: {DEFAULT_PROVIDER})")
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--dry-run", action="store_true", help="Say how many responses are missing and what they would cost")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("judge", help="Score the responses with the pipeline's trait judge")
    p.add_argument("--out", required=True)
    p.add_argument("--judge-model", default=None,
                   help=f"(default: the plan's judge when it names one, step 3's; else {DEFAULT_JUDGE})")
    p.add_argument("--requests-per-second", type=int, default=50)
    p.add_argument("--chunk", type=int, default=200,
                   help="With step 3's judge, responses judged between two writes of the score files (default: 200)")
    p.add_argument("--in-flight", type=int, default=200,
                   help="With step 3's judge, how many calls are open at once, each worker taking the next "
                        "response when its call is done (default: 200; 2,000 at once failed with connection errors)")
    p.add_argument("--via", choices=("openai", "openrouter"), default=None,
                   help="Where the judge is asked (default: openai, directly; openrouter only on request, "
                        f"pinned to {JUDGE_PROVIDER})")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("depth", help="Read the answers for how the trait shows: in action, described, or performed")
    p.add_argument("--out", required=True)
    p.add_argument("--model", default=DEFAULT_DEPTH_JUDGE, help=f"(default: {DEFAULT_DEPTH_JUDGE}, asked at Anthropic)")
    p.add_argument("--min-score", type=int, default=0,
                   help="Read only answers that the pipeline's judge scored this or more (default: 0, all)")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--batch", action="store_true",
                   help="Read through Anthropic Message Batches at half price; what the batch does not settle is "
                        "read in real time (off by default)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_depth)

    p = sub.add_parser("depth-report", help="How the answers show the trait, per opening")
    p.add_argument("--out", required=True)
    p.add_argument("--write", action="store_true", help="Also write depth_report.json")
    p.set_defaults(func=cmd_depth_report)

    p = sub.add_parser("report", help="Share scored 3 per trait and variant, and per variant across traits")
    p.add_argument("--out", required=True)
    p.add_argument("--reference", default=None, help="Variant the others are compared with, trait by trait")
    p.add_argument("--write", action="store_true", help="Also write report.json")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("list-failures", help="Instructions of an extraction run that keep under half the mean of "
                                             "their trait's other four (p < alpha)")
    p.add_argument("--scores-dir", required=True, help="The run's trait scores directory")
    p.add_argument("--traits-dir", default="data/traits/instructions")
    p.add_argument("--alpha", type=float, default=1e-3)
    p.add_argument("--write", required=True, metavar="FILE")
    p.set_defaults(func=cmd_list_failures)

    p = sub.add_parser("rewrite-openings", help="Ask a model for the trait-first and 'You are a ... person' "
                                                "openings of each trait's 'You are <adjective>' instruction")
    p.add_argument("--out", required=True)
    p.add_argument("--stems", required=True, metavar="FILE", help="A JSON list of the traits")
    p.add_argument("--traits-dir", default="data/traits/instructions")
    p.add_argument("--model", default=DEFAULT_REWRITE_MODEL, help=f"(default: {DEFAULT_REWRITE_MODEL}, at Anthropic)")
    p.add_argument("--requests-per-second", type=int, default=5)
    p.add_argument("--show", action="store_true", help="With --dry-run, print the first prompt as it is sent")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_rewrite_openings)

    p = sub.add_parser("plan-openings", help="Write the openings plan: each trait's instructions under every "
                                             "opening that can be made")
    p.add_argument("--out", required=True)
    p.add_argument("--stems", required=True, metavar="FILE", help="A JSON list of the traits")
    p.add_argument("--traits-dir", default="data/traits/instructions")
    p.add_argument("--kinds", default=None, metavar="FILE", help="A JSON object stem -> good | bad | indifferent")
    p.add_argument("--problem", default=None, metavar="FILE",
                   help="list-failures' file: traits whose 'You are <adjective>' instruction failed are the problem list")
    p.add_argument("--rewrites", default=None, metavar="FILE", help=f"(default: <out>/{REWRITE_FILE})")
    p.add_argument("--blind", default=None, metavar="FILE", help="The blind agent's instructions (B arms)")
    p.add_argument("--questions", choices=("generic", "own"), default="generic",
                   help="generic: the shared bank's (default); own: the trait file's, spread over them")
    p.add_argument("--n-questions", type=int, default=DEFAULT_ARM_QUESTIONS,
                   help=f"(default: {DEFAULT_ARM_QUESTIONS})")
    p.add_argument("--max-tokens", type=int, default=1024,
                   help="Response cap (default: 1024, the October extraction's)")
    p.add_argument("--purpose", default=None)
    p.add_argument("--replace", action="store_true")
    p.set_defaults(func=cmd_plan_openings)

    p = sub.add_parser("openings-report", help="The openings against the instructions they were made from, and "
                                               "menus of five under Roger's criterion")
    p.add_argument("--out", required=True)
    p.add_argument("--menu", action="append", metavar="NAME=A,B,C,D,E",
                   help="A menu of five arms to score (repeatable); 'current' and each fifth=<arm> are always scored")
    p.add_argument("--write", action="store_true", help="Also write openings_report.json")
    p.set_defaults(func=cmd_openings_report)
    return parser.parse_args(argv)


def _stop(signum, frame):
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    # a run that is stopped still records what it spent
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, _stop)
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
