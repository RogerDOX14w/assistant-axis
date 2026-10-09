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
"""

import argparse
import asyncio
import datetime
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

    def charge(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        self.run.charge(model, prompt_tokens, completion_tokens)
        cost = self._pending.charge(model, prompt_tokens, completion_tokens)
        if self._pending.n_calls >= self.every:
            self.flush()
        return cost

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

async def one_response(client, model: str, provider: str, system_prompt: str, question: str, semaphore,
                       usage) -> dict | None:
    for attempt in range(4):
        try:
            async with semaphore:
                r = await client.chat.completions.create(
                    model=model, temperature=TEMPERATURE, max_tokens=MAX_TOKENS,
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
            logger.warning("attempt %d of 4 failed: %s", attempt + 1, type(e).__name__)
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
    n_in = sum(len(v["text"].split()) + len(question.split()) for _, _, v, _, question in todo) * 1.4
    rate_in, rate_out = price_for_model(args.model)
    print(f"{len(todo)} responses to generate with {args.model} at {args.provider}; about "
          f"${(n_in * rate_in + len(todo) * 450 * rate_out) / 1e6:.2f}", file=sys.stderr)
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
        r = await one_response(client, args.model, args.provider, v["text"], question, semaphore, usage)
        # a response that came with thinking is not what the extraction run would have produced,
        # and one from another host should not exist
        if r is None or not r["content"] or r["had_thinking"] or r["provider"] != args.provider:
            failed += 1
            return
        row = {"label": "pos", "prompt_index": k, "variant": v["name"], "question_index": q, "question": question,
               "system_prompt": v["text"], "user_turn": question + NO_THINK_SUFFIX, "model": args.model,
               "provider": r["provider"],
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


async def judge(args, plan: dict, out_dir: Path) -> None:
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
    print(f"{len(todo)} answers to read with {args.model}", file=sys.stderr)
    if args.dry_run or not todo:
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(args.concurrency)
    usage, tally = CheckpointedUsage(out_dir), {"ok": 0, "total": 0}

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
    p.add_argument("--judge-model", default=DEFAULT_JUDGE, help=f"(default: {DEFAULT_JUDGE})")
    p.add_argument("--requests-per-second", type=int, default=50)
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
