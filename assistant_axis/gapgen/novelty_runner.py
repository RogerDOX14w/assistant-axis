"""M3's waves: the calls of the novelty check, sent live or through the Message Batches API.

The logic is :mod:`assistant_axis.gapgen.novelty`; this module sends the calls and keeps the records
(coding_plan_m3.md, "Transport, cost, records").  Waves, in order, each followed by its retry wave
(``<wave>_retry``: every call whose answer failed to parse, asked once more, as the overlap harness does):

* ``r1_relation``: one relation call per candidate (Haiku 5.5 from 2026-10-08, Haiku 4.5 before;
  rubric ``relation.md``, uncached: about 450 tokens of rubric, under Haiku 5.5's 512-token minimum and
  Haiku 4.5's 4,096);
* ``r2_relation_unsure``: Sonnet 5.5 on the traits Haiku answered ``unsure``, one call per candidate;
* ``oNN_sonnet`` then ``oNN_opus`` for shortlist position NN = 1, 2, ...: Sonnet on every undecided
  candidate's next pair, then Opus on the pairs the rule sends it (rubric A, one pair per call, the user
  turn :func:`overlap_test.render_single`, the system prompt cached: 5 minutes live, 1 hour in batches,
  since a batch's requests are spread over up to an hour).

The full scan (``mode="full_scan"``) sends no relation call: ``f_sonnet`` reads every listed trait of
every candidate, ``f_opus`` the pairs the rule sends to Opus, and the walk is replayed on the readings
afterwards (:func:`novelty.replay_walk`).

Records: ``responses.jsonl`` (every response received, appended as it arrives, before it is parsed;
request, answer, usage, parse errors), replayed on ``--resume``: no call is sent whose answer is already
on record for the same step, model, prompt and input (a call whose answer failed to parse twice is
replayed as unparsed, one that failed once is asked once more).  A request that failed outright (no
answer after the client's retries) leaves its candidate **stalled**: undecided in this session, nothing
written for it, finished by a resume.  A budget stop keeps every answer paid for, decides nothing more,
and is raised after the candidates already decided have been handed over.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage, cost_for_usage

from . import novelty as NV
from . import overlap_test as OT
from .llm import CACHE_READ_FACTOR, CACHE_WRITE_1H_FACTOR, CACHE_WRITE_FACTOR, RETRY_DELAYS_S, call_anthropic_json
from .registry import utc_now

logger = logging.getLogger(__name__)

#: Haiku 5.5 from 2026-10-08 (coding_plan_haiku55.md, "The switch"; M3 decision 17); a run's records name
#: the model, and ``score --redecide`` replays a source's answers on the source's own relation model.
RELATION_MODEL = NV.HAIKU55
UNSURE_MODEL = NV.SONNET
FIRST_MODEL = NV.SONNET
SECOND_MODEL = NV.OPUS
RELATION_MAX_TOKENS = 4096
OVERLAP_MAX_TOKENS = OT.MAX_TOKENS          # 2048, as overlap_arms_3 sent it
TEMPERATURE = OT.TEMPERATURE                # 0.0; left out for Sonnet 5.5 and Opus 5.5, which refuse it
ASK_ATTEMPTS = OT.ASK_ATTEMPTS              # 2: an answer that fails to parse is asked once more
DEFAULT_CONCURRENCY = 8
BATCH_CACHE_TTL = "1h"

#: Measured per pair in overlap_arms_3 (rubric A version 6, one pair per call, caching on; usage.json):
#: Sonnet 179,291 prompt-equivalent and 64,029 output tokens over 818 calls, Opus 179,952 and 91,953 (it
#: thinks more in the one-pair form): $0.0012 and $0.0031 a pair live (coding_plan_m3.md).
OVERLAP_TOKENS: dict[str, tuple[int, int]] = {"sonnet": (219, 78), "opus": (220, 112)}
#: Relation call: the request's characters at about 4 a token (Sonnet 5.5's tokenizer makes about 30%
#: more), and per listed trait about 45 output tokens (a one-sentence reason and the JSON around it).
CHARS_PER_TOKEN = OT.CHARS_PER_TOKEN
RELATION_OUT_BASE, RELATION_OUT_PER_TRAIT = 20, 45
#: Measured relation-call output by model-id fragment, ``(base, per listed trait)`` in the model's own
#: tokens (no tokenizer factor on top), thinking included (coding_plan_haiku55.md, "The switch", item 4):
#: Haiku 5.5 wrote 601,359 output tokens for 7,862 listed traits over the 457 first-attempt calls of
#: m3_pilot_1_relation_h55 (1,316 a call at 17.2 listed; the old figure, (20 + 45 x 17.2) x 1.3, gave 1,032).
#: Its input matched the characters-per-token figure (1,746 measured, 1,747 estimated), so input is unchanged.
RELATION_OUT_MEASURED: dict[str, tuple[float, float]] = {"haiku-5-5": (0.0, 76.5)}


def relation_out_tokens(model: str, n_listed: float) -> int:
    """Estimated output tokens of one relation call listing ``n_listed`` traits on ``model``: the measured
    figures where there are some (:data:`RELATION_OUT_MEASURED`), else the generic per-trait figure times the
    tokenizer factor (a thinking model's thinking not counted)."""
    m = str(model).lower()
    for frag, (base, per) in RELATION_OUT_MEASURED.items():
        if frag in m:
            return int(round(base + per * n_listed))
    return int(round((RELATION_OUT_BASE + RELATION_OUT_PER_TRAIT * n_listed) * OT.tokenizer_factor(model)))
#: The plan's assumptions (coding_plan_m3.md, "Transport, cost, records"): 3 shortlisted pairs a candidate,
#: 18% fewer judged with early exit (the test's rate); the share of Sonnet readings that send the pair to
#: Opus (at the cut-off or one below, or unsure): 0.62 on a shortlist (overlap_arms_3's nearest pairs, 65%
#: at 2 or 3, weighted by the alignment scores of M1's random adjectives, 84% far from alignment, where the
#: share at 3 or 4 is 13%), 0.40 in the full scan (every listed trait, the antonyms and far ones included);
#: the share of candidates with an unsure relation answer (never seen in the overlap test).
SHORTLIST_PAIRS, EARLY_EXIT_SAVING = 3, 0.18
OPUS_SHARE_SHORTLIST, OPUS_SHARE_FULL_SCAN = 0.62, 0.40
UNSURE_SHARE, UNSURE_TRAITS = 0.05, 2

_CID_RE = re.compile(r"[^A-Za-z0-9_-]")


# --------------------------------------------------------------------------- candidates and calls

@dataclass
class M3Candidate:
    key: str
    stem: str
    label: str
    gloss: str
    alignment_score: Optional[int]
    region: Optional[str]
    generators: list = field(default_factory=list)

    @property
    def cut_off(self) -> int:
        return NV.cut_off(self.alignment_score)

    def as_dict(self) -> dict:
        return {"key": self.key, "stem": self.stem, "label": self.label, "gloss": self.gloss,
                "alignment_score": self.alignment_score, "region": self.region, "generators": list(self.generators)}


def candidate_from_row(row: Mapping) -> tuple[Optional[M3Candidate], Optional[str]]:
    """``(candidate, None)`` for a registry row M3 can judge, else ``(None, why)``: not filtered, not a
    ``trait`` verdict, or no gloss."""
    f = row.get("filter") or {}
    if not f:
        return None, "not_filtered"
    if f.get("verdict") != "trait":
        return None, "not_a_trait"
    g = row.get("gloss")
    if not (isinstance(g, str) and g.strip()):
        return None, "no_gloss"
    a = f.get("alignment")
    a = a if isinstance(a, int) and not isinstance(a, bool) else None
    gens = list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))
    return M3Candidate(key=row["key"], stem=row["stem"], label=row["label"], gloss=g.strip(), alignment_score=a,
                       region=f.get("region"), generators=gens), None


@dataclass
class Call:
    """One API call: one candidate, one prompt."""
    step: str                 # relation | relation_unsure | overlap
    role: str                 # haiku | sonnet | opus
    key: str
    model: str
    system: str
    user: str
    max_tokens: int
    temperature: Optional[float]
    cache_system: bool = False
    cache_ttl: Optional[str] = None
    stem: Optional[str] = None            # overlap: the corpus trait
    stems: tuple = ()                     # relation: the listed traits, in the order sent (id i is stems[i-1])
    position: int = 0
    retry: bool = False

    @property
    def prompt_sha256(self) -> str:
        return hashlib.sha256(self.system.encode("utf-8")).hexdigest()

    @property
    def custom_id(self) -> str:
        """``<step>-<role>-<key>-<hash>``: within the Message Batches limit of 64 characters from
        ``[A-Za-z0-9_-]``, unique per candidate and pair."""
        ident = f"{self.step}|{self.role}|{self.key}|{self.stem or ','.join(self.stems)}"
        h = hashlib.sha256(ident.encode("utf-8")).hexdigest()[:12]
        k = _CID_RE.sub("_", self.key)[:28]
        return f"{self.step[:3]}-{self.role[0]}-{k}-{h}"

    def cache_key(self) -> tuple[str, str, str, str]:
        return (self.step, self.prompt_sha256, self.model, self.user)


def model_role(model: str) -> str:
    """A call's ``role`` from its model's family (``haiku``, ``sonnet``, ``opus``, ``fable``), as the records
    name it; ``relation`` for a model of none of them."""
    m = str(model).lower()
    return next((f for f in ("haiku", "sonnet", "opus", "fable") if f in m), "relation")


def billed_from_raw(raw: Mapping) -> tuple[int, int]:
    """``(prompt-equivalent tokens, output tokens)`` from a record's ``usage_raw``, as ``llm.billed_usage``
    charges them."""
    if not raw:
        return 0, 0
    cw = int(raw.get("cache_creation_input_tokens") or 0)
    cw1h = min(int(raw.get("cache_creation_1h_input_tokens") or 0), cw)
    prompt = int(raw.get("input_tokens") or 0) + int(round(CACHE_WRITE_FACTOR * (cw - cw1h) + CACHE_WRITE_1H_FACTOR * cw1h
                                                           + CACHE_READ_FACTOR * int(raw.get("cache_read_input_tokens") or 0)))
    return prompt, int(raw.get("output_tokens") or 0)


def record_cost(rec: Mapping) -> float:
    m = rec.get("charged_as")
    if not m:
        return 0.0
    p, o = billed_from_raw(rec.get("usage_raw") or {})
    return cost_for_usage(m, p, o)


# --------------------------------------------------------------------------- transports

class LiveTransport:
    """Sends a wave's calls through the Messages API, ``runner.concurrency`` at a time."""
    name = "live"

    def __init__(self, runner: "NoveltyRunner"):
        self.runner = runner

    async def execute(self, wave: str, calls: Sequence[Call], on_result: Callable) -> None:
        r = self.runner
        sem = asyncio.Semaphore(r.concurrency)

        async def one(c: Call) -> None:
            if r._stop is not None:
                return
            async with sem:
                if r._stop is not None:
                    return
                meta: dict = {}
                try:
                    text = await call_anthropic_json(
                        r.client, system=c.system, user=c.user, model=c.model, max_tokens=c.max_tokens,
                        temperature=c.temperature, usage=r.usage, cache_system=c.cache_system, cache_ttl=c.cache_ttl,
                        retry_delays=r.retry_delays, meta=meta)
                except BudgetExceededError as exc:
                    text = meta.get("text")
                    if r._stop is None:
                        r._stop = exc
            meta["charged_as"] = c.model if meta.get("usage_raw") else None
            on_result(c, text, meta)

        await asyncio.gather(*(one(c) for c in calls))


class OfflineTransport:
    """Sends nothing: a call whose answer is not on record is noted in ``wanted`` and left unanswered, so its
    candidate stalls (``not_sent``).  For re-deciding a run on its records (``score --redecide``): the dry
    run's count of the calls a rule now needs, and the attribution replays that must not spend."""
    name = "offline"

    def __init__(self):
        self.wanted: list[dict] = []

    async def execute(self, wave: str, calls: Sequence["Call"], on_result: Callable) -> None:
        for c in calls:
            self.wanted.append({"wave": wave, "step": c.step, "role": c.role, "model": c.model, "key": c.key,
                                "stem": c.stem, "n_stems": len(c.stems), "call": c})


# --------------------------------------------------------------------------- the runner

@dataclass
class Outcome:
    status: str                  # ok | unparsed | failed | not_sent
    parsed: Any = None           # relation: rows {id: row}; overlap: {"value", "reason"}
    error: Optional[str] = None


@dataclass
class CandState:
    cand: M3Candidate
    q: Optional[np.ndarray] = None
    listed: list = field(default_factory=list)
    relation: Optional[dict] = None          # the relation call's record for the block
    relations: dict = field(default_factory=dict)
    shortlist: Any = None
    walk: Any = None
    stalled: Optional[str] = None
    block: Optional[dict] = None
    emitted: bool = False
    usage: dict = field(default_factory=dict)     # charged model -> totals
    scan: dict = field(default_factory=dict)      # full scan: stem -> {"sonnet", "opus"}
    renamed: Optional[dict] = None                # decision 15: {"current", "old_stem"} of a renamed label


class NoveltyRunner:
    """Runs M3 on a list of candidates (see the module docstring).

    ``rubrics``: ``{"overlap": {"name", "text", "version", "sha256"}, "relation": {...}}`` as loaded and
    pin-checked by the CLI; ``index``: the corpus in the covered space (:class:`novelty.CorpusIndex`);
    ``label_sets``: stage 0's names; ``on_decided(states)``: called with newly decided candidates after
    stage 0 and after every overlap position (the CLI writes their registry blocks there).

    ``rules``: the decision rules (:data:`novelty.RULES`; default rule set 2).  ``relation_seed``: the run id
    that seeds the relation call's list order (default ``batch_id``; a re-decided run passes its source's,
    so that the source's relation calls are the same requests).  ``replay_records``: another run's
    responses, answers on record that are replayed instead of sent (as ``resume_records`` are) but are not
    this run's records: they are not counted in its summary, its parse rates or its spend.
    ``extra_block``: fields added to every block (a re-decided run's ``redecided_from``).

    ``relation_model``: the model of the relation call (default :data:`RELATION_MODEL`; the unsure re-ask
    stays on :data:`UNSURE_MODEL`).  ``relation_only`` (``score --relation-only``, coding_plan_haiku55.md):
    stage 3 and stop: the relation calls (and the unsure re-ask) are sent and the shortlists built, but no
    overlap call is made and no candidate that reached stage 3 is decided (its block stays ``None``)."""

    def __init__(self, *, client, batch_id: str, rubrics: Mapping[str, Mapping], index: NV.CorpusIndex,
                 label_sets: NV.LabelSets, usage: MultiModelUsage, responses_path: Path, k: int = 10,
                 mode: str = "shortlist", config_version: str = "", embedding: Optional[Mapping] = None,
                 transport: Any = None, concurrency: int = DEFAULT_CONCURRENCY,
                 retry_delays: Optional[Sequence[float]] = None, resume_records: Sequence[Mapping] = (),
                 on_decided: Optional[Callable[[list], None]] = None, cache_ttl: Optional[str] = None,
                 rules: Optional[NV.Rules] = None, relation_seed: Optional[str] = None,
                 replay_records: Sequence[Mapping] = (), extra_block: Optional[Mapping] = None,
                 relation_model: str = RELATION_MODEL, relation_only: bool = False):
        if mode not in ("shortlist", "full_scan"):
            raise ValueError(f"mode must be shortlist or full_scan, not {mode!r}")
        if relation_only and mode != "shortlist":
            raise ValueError("relation_only runs stage 3 of the shortlist mode; the full scan sends no relation call")
        self.client = client
        self.batch_id = batch_id
        self.relation_model = str(relation_model)
        self.relation_only = bool(relation_only)
        self.rules = rules or NV.DEFAULT_RULES
        self.relation_seed = relation_seed or batch_id
        self.extra_block = dict(extra_block or {})
        self.rubrics = rubrics
        self.index = index
        self.traits = index.traits
        self.label_sets = label_sets
        self.usage = usage
        self.responses_path = Path(responses_path)
        self.k = int(k)
        self.mode = mode
        self.config_version = config_version
        self.embedding = dict(embedding or {})
        self.concurrency = max(1, int(concurrency))
        self.retry_delays = tuple(RETRY_DELAYS_S if retry_delays is None else retry_delays)
        self.transport = transport if transport is not None else LiveTransport(self)
        self.on_decided = on_decided
        self.cache_ttl = cache_ttl
        self.partners = {s: list(t.partners) for s, t in self.traits.items()}
        self.corpus = {s: {"label": t.label, "description": t.description} for s, t in self.traits.items()}
        self.states: dict[str, CandState] = {}
        self.stats: Counter = Counter()
        self.records: list[dict] = []
        self._stop: Optional[BaseException] = None
        # resume: the answers on record, by (step, prompt hash, model, user)
        self.cache_good: dict[tuple, dict] = {}
        self.cache_fail: Counter = Counter()
        self.cache_fail_err: dict[tuple, str] = {}
        for rec in replay_records:
            self._remember(rec)
        for rec in resume_records:
            self.records.append(dict(rec))
            self._remember(rec)

    @property
    def rubric_pins(self) -> dict:
        return {k: {"name": v["name"], "version": v["version"], "sha256": v["sha256"]} for k, v in self.rubrics.items()}

    # -- records --------------------------------------------------------------------
    def _remember(self, rec: Mapping) -> None:
        key = (rec.get("step"), rec.get("prompt_sha256"), rec.get("model"), rec.get("user"))
        if rec.get("text") is None:
            return                                   # a failed request is not an attempt at the format
        if not rec.get("parse_errors"):
            self.cache_good[key] = dict(rec)
        else:
            self.cache_fail[key] += 1
            self.cache_fail_err[key] = "; ".join(sorted(set(map(str, (rec.get("parse_errors") or {}).values()))))[:300]

    def _append(self, rec: dict) -> None:
        self.records.append(rec)
        self.responses_path.parent.mkdir(parents=True, exist_ok=True)
        with self.responses_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _charge_cand(self, key: str, rec: Mapping) -> None:
        m = rec.get("charged_as")
        if not m or key not in self.states:
            return
        p, o = billed_from_raw(rec.get("usage_raw") or {})
        u = self.states[key].usage.setdefault(m, {"n_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0})
        u["n_calls"] += 1
        u["prompt_tokens"] += p
        u["completion_tokens"] += o
        u["cost_usd"] += cost_for_usage(m, p, o)

    # -- parsing ------------------------------------------------------------------
    @staticmethod
    def parse(c: Call, text: Optional[str]) -> tuple[Any, dict, dict]:
        """``(parsed, errors, meta)``: a relation call's rows, or an overlap call's one answer."""
        if c.step in ("relation", "relation_unsure"):
            rows, errors, meta = NV.parse_relation(text, len(c.stems))
            return rows, errors, meta
        rows, errors, meta = OT.parse_single(text, NV.OVERLAP_RUBRIC)
        return (rows.get(1) if rows else None), errors, meta

    # -- estimate -------------------------------------------------------------------
    def tokens_for(self, c: Call) -> tuple[int, int]:
        return call_tokens(c)

    def estimate_usd(self, calls: Sequence[Call], *, batch: bool = False) -> float:
        suffix = BATCH_SUFFIX if batch else ""
        return sum(cost_for_usage(c.model + suffix, *call_tokens(c)) for c in calls)

    # -- one wave -------------------------------------------------------------------
    async def _wave(self, wave: str, calls: Sequence[Call]) -> dict[int, Outcome]:
        out: dict[int, Outcome] = {}
        if not calls:
            return out
        texted: dict[int, int] = defaultdict(int)       # answers received (with text) per call, this session

        def handle(c: Call, text: Optional[str], meta: Mapping, *, resumed: bool = False) -> None:
            parsed, errors, pmeta = self.parse(c, text)
            ok = text is not None and not errors
            if not resumed:
                rec = {"batch_id": self.batch_id, "mode": self.mode, "wave": wave + ("_retry" if c.retry else ""),
                       "step": c.step, "role": c.role, "key": c.key, "stem": c.stem, "stems": list(c.stems),
                       "position": c.position, "model": c.model, "prompt_sha256": c.prompt_sha256, "user": c.user,
                       "request": {"max_tokens": c.max_tokens, "temperature": c.temperature,
                                   "cache_system": c.cache_system, "cache_ttl": c.cache_ttl},
                       "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
                       "attempts": meta.get("attempts"), "error": meta.get("error"),
                       "parse_errors": {str(k): v for k, v in errors.items()} if text is not None else None,
                       "parse_meta": pmeta, "parse_attempt": 2 if c.retry else 1,
                       "transport": getattr(self.transport, "name", "live"), "custom_id": c.custom_id,
                       "charged_as": meta.get("charged_as"), "batch_request_id": meta.get("batch_request_id"),
                       "at": utc_now()}
                self._append(rec)
                self._remember(rec)
                self._charge_cand(c.key, rec)
                self.stats[f"sent:{c.step}:{c.role}"] += 1
            if text is not None:
                texted[id(c)] += 1
            if ok:
                out[id(c)] = Outcome("ok", parsed)
            elif text is not None:
                out[id(c)] = Outcome("unparsed", None, "; ".join(sorted(set(map(str, errors.values()))))[:300])
            else:
                out[id(c)] = Outcome("failed", None, str(meta.get("error"))[:300])

        first, retry_now = [], []
        for c in calls:
            k = c.cache_key()
            if k in self.cache_good:
                rec = self.cache_good[k]
                self.stats["resumed"] += 1
                handle(c, rec["text"], rec, resumed=True)
                if out[id(c)].status != "ok":    # a recorded answer the current parser reads differently
                    first.append(c)
            elif self.cache_fail[k] >= ASK_ATTEMPTS:
                self.stats["resumed"] += 1
                out[id(c)] = Outcome("unparsed", None, self.cache_fail_err.get(k))
                texted[id(c)] = ASK_ATTEMPTS
            elif self.cache_fail[k] == 1:
                texted[id(c)] = 1
                retry_now.append(c)
            else:
                first.append(c)
        await self._send(wave, first, handle)
        for c in first:
            o = out.get(id(c))
            if o is not None and o.status != "ok":
                retry_now.append(c)
        if retry_now and self._stop is not None:
            # a stop came before the second asking: nothing is concluded from one failure
            for c in retry_now:
                out[id(c)] = Outcome("not_sent")
        elif retry_now:
            back = {}
            retries = []
            for c in retry_now:
                rc = Call(**{**c.__dict__, "retry": True})
                retries.append(rc)
                back[id(rc)] = c
            await self._send(wave + "_retry", retries, handle)
            for rc in retries:
                c = back[id(rc)]
                prev = out.get(id(c))
                o = out.pop(id(rc), None)
                texted[id(c)] += texted.pop(id(rc), 0)
                if o is None:                                    # never sent (a stop): the candidate waits
                    out[id(c)] = Outcome("not_sent")
                elif o.status == "ok":
                    out[id(c)] = o
                elif texted[id(c)] > 0:                          # an answer came and never parsed
                    out[id(c)] = Outcome("unparsed", None, o.error if o.status == "unparsed" else (prev.error if prev else o.error))
                else:                                            # two failed requests: no answer at all
                    out[id(c)] = o
        for c in calls:
            if id(c) not in out:
                out[id(c)] = Outcome("not_sent")
        return out

    async def _send(self, wave: str, calls: list, handle) -> None:
        if not calls or self._stop is not None:
            return
        try:
            await self.transport.execute(wave, calls, lambda c, t, m: handle(c, t, m))
        except BaseException as exc:  # noqa: BLE001 - kept as the stop; raised after the answers are applied
            if self._stop is None:
                self._stop = exc

    # -- calls ----------------------------------------------------------------------
    def _relation_call(self, st: CandState, stems: Sequence[str], *, step: str = "relation") -> Call:
        traits = [(self.traits[s].label, self.traits[s].description) for s in stems]
        user = NV.render_relation_user(st.cand.label, st.cand.gloss, traits)
        model = self.relation_model if step == "relation" else UNSURE_MODEL
        return Call(step=step, role=model_role(model), key=st.cand.key, model=model,
                    system=self.rubrics["relation"]["text"], user=user, max_tokens=RELATION_MAX_TOKENS,
                    temperature=TEMPERATURE, cache_system=False, stems=tuple(stems))

    def _overlap_call(self, st: CandState, stem: str, role: str, position: int) -> Call:
        pc = OT.PairCall(call_id=f"{st.cand.key}>{stem}", set="m3", target=st.cand.key, listed=[stem])
        corpus = {st.cand.key: {"label": st.cand.label, "description": st.cand.gloss}, stem: self.corpus[stem]}
        user = OT.render_single(pc, corpus)
        model = FIRST_MODEL if role == "sonnet" else SECOND_MODEL
        return Call(step="overlap", role=role, key=st.cand.key, model=model, system=self.rubrics["overlap"]["text"],
                    user=user, max_tokens=OVERLAP_MAX_TOKENS, temperature=TEMPERATURE, cache_system=True,
                    cache_ttl=self.cache_ttl, stem=stem, position=position)

    # -- the run ----------------------------------------------------------------------
    def run(self, cands: Sequence[M3Candidate], vectors: Mapping[str, np.ndarray]) -> dict[str, CandState]:
        return asyncio.run(self.run_async(cands, vectors))

    async def run_async(self, cands: Sequence[M3Candidate], vectors: Mapping[str, np.ndarray]) -> dict[str, CandState]:
        self._stop = None
        for cand in cands:
            self.states[cand.key] = CandState(cand=cand)
        try:
            await self._run(cands, vectors)
        finally:
            self._emit()
        if self._stop is not None:
            raise self._stop
        return self.states

    def _emit(self) -> None:
        new = [st for st in self.states.values() if st.block is not None and not st.emitted]
        for st in new:
            st.emitted = True
        if new and self.on_decided is not None:
            self.on_decided(new)

    def _cos_fn(self, st: CandState) -> Callable[[str], Optional[float]]:
        return lambda s: self.index.cosine_to(st.q, s) if st.q is not None else None

    async def _run(self, cands: Sequence[M3Candidate], vectors: Mapping[str, np.ndarray]) -> None:
        live: list[CandState] = []
        for cand in cands:
            st = self.states[cand.key]
            m = NV.exact_label_match(cand.stem, self.label_sets, rules=self.rules) if self.mode == "shortlist" else None
            if m is not None:
                self.stats["exact_label"] += 1
                st.block = self._block(st, decision="covered", reason="exact_label", covered_by=m["covered_by"], match=m)
                continue
            if self.mode == "shortlist":
                st.renamed = NV.renamed_match(cand.stem, self.label_sets, rules=self.rules)
                if st.renamed is not None and st.renamed["current"] not in self.traits:
                    st.renamed = None                    # a rename whose current file is gone: judged as any other
                if st.renamed is not None:
                    self.stats["renamed_from_judged"] += 1
            if cand.key not in vectors:
                st.stalled = "no embedding"
                continue
            st.q = self.index.project(vectors[cand.key])
            retrieved = self.index.retrieve(st.q, self.k)
            st.listed = NV.expand(retrieved, self.traits, self._cos_fn(st))
            if not st.listed:
                st.block = self._block(st, decision="new", reason="no_listed")
                continue
            live.append(st)
        self._emit()
        if self.mode == "full_scan":
            await self._full_scan(live)
            return
        await self._relations(live)
        if self._stop is not None or self.relation_only:
            return
        await self._walk([st for st in live if st.walk is not None])

    # -- stage 3 ----------------------------------------------------------------------
    async def _relations(self, live: list[CandState]) -> None:
        calls = []
        for st in live:
            order = NV.relation_order([x.stem for x in st.listed], self.relation_seed, st.cand.key)
            calls.append(self._relation_call(st, order))
        res = await self._wave("r1_relation", calls)
        by_key = {st.cand.key: st for st in live}
        unsure_calls = []
        for c in calls:
            st, o = by_key[c.key], res[id(c)]
            st.relation = {"model": c.model, "rubric": self.rubric_pins["relation"], "order": list(c.stems),
                           "status": o.status, "answers": {}, "unsure_reasked": None}
            if o.status == "ok":
                for i, s in enumerate(c.stems, 1):
                    row = o.parsed[i]
                    st.relations[s] = row["value"]
                    st.relation["answers"][s] = {"relation": row["value"], "reason": row["reason"]}
                unsure = [s for s in c.stems if st.relations[s] == "unsure"]
                if unsure:
                    unsure_calls.append(self._relation_call(st, unsure, step="relation_unsure"))
            elif o.status == "unparsed":
                # the relation call never parsed: every listed trait goes to the overlap call, by cosine
                st.relation["fallback"] = "every listed trait shortlisted, by cosine (the relation call never parsed)"
                st.relation["error"] = o.error
            else:
                st.stalled = f"relation call: {o.status} ({o.error})"
        if unsure_calls and self._stop is None:
            res2 = await self._wave("r2_relation_unsure", unsure_calls)
            for c in unsure_calls:
                st, o = by_key[c.key], res2[id(c)]
                st.relation["unsure_reasked"] = {"model": c.model, "stems": list(c.stems), "status": o.status}
                if o.status == "ok":
                    # Sonnet's answer replaces Haiku's; a trait still unsure stays "unsure", which the shortlist
                    # keeps (by cosine, with the similar ones) and the pair check leaves out
                    for i, s in enumerate(c.stems, 1):
                        row = o.parsed[i]
                        st.relation["answers"][s]["second"] = {"relation": row["value"], "reason": row["reason"]}
                        st.relations[s] = row["value"]
                elif o.status == "unparsed":
                    pass                     # the traits stay "unsure": shortlisted, out of the pair check
                else:
                    st.stalled = f"relation unsure re-ask: {o.status} ({o.error})"
        elif unsure_calls:
            for c in unsure_calls:
                by_key[c.key].stalled = "stopped before the unsure re-ask"
        for st in live:
            if st.stalled or self._stop is not None and st.relation is None:
                continue
            renamed = st.renamed["current"] if st.renamed else None
            st.shortlist = NV.build_shortlist(st.listed, st.relations, self._cos_fn(st),
                                              fallback=bool(st.relation.get("fallback")), rules=self.rules,
                                              renamed=renamed)
            review, details = [], []
            if st.shortlist.pair_flags and self.rules.pair_flag_grey:
                review.append("pair_flag")
                details += [{"kind": "pair_flag", **f} for f in st.shortlist.pair_flags]
            if st.relation.get("fallback"):
                review.append("unparsed")
                details.append({"kind": "unparsed", "stage": "relation", "error": st.relation.get("error")})
            if st.shortlist.pair_notes:
                review.append("both_similar")
                for n in st.shortlist.pair_notes:
                    n["cosines"] = {s: self._cos_of(st, s) for s in n["pair"]}
                    n["readings_on_record"] = self._readings_on_record(st, n["pair"])
                    details.append({"kind": "both_similar", "pair": list(n["pair"]), "arrangement": n["kind"],
                                    "both": n["both"]})
            info = {x.stem: x for x in st.listed}
            if renamed and renamed not in info:
                info[renamed] = NV.listed_from(renamed, self._cos_of(st, renamed), self.traits, rank=None,
                                               via="renamed_from")
            st.walk = NV.Walk(st.cand.key, st.cand.cut_off, st.shortlist.queue, info,
                              relations=st.relations, partners=self.partners, cosine_of=self._cos_fn(st), review=review,
                              review_details=details, pair_completion_for=st.shortlist.pair_completion_for,
                              rules=self.rules, exclude=st.shortlist.excluded)

    def _cos_of(self, st: CandState, stem: str) -> Optional[float]:
        for x in st.listed:
            if x.stem == stem:
                return x.cosine
        c = self.index.cosine_to(st.q, stem) if st.q is not None else None
        return round(float(c), 6) if c is not None else None

    def _readings_on_record(self, st: CandState, stems: Sequence[str]) -> dict:
        """The overlap readings already on record (this run's or a replayed run's) for the candidate against
        each of ``stems``, without sending anything: ``{stem: {"sonnet": {...}, "opus": {...}}}``."""
        out = {}
        for s in stems:
            got = {}
            for role in ("sonnet", "opus"):
                rec = self.cache_good.get(self._overlap_call(st, s, role, 0).cache_key())
                if rec is None:
                    continue
                parsed, errors, _ = self.parse(self._overlap_call(st, s, role, 0), rec.get("text"))
                if parsed and not errors:
                    got[role] = {"value": parsed["value"], "reason": parsed["reason"]}
            if got:
                out[s] = got
        return out

    # -- stage 4 ----------------------------------------------------------------------
    async def _walk(self, live: list[CandState]) -> None:
        position = 0
        while self._stop is None:
            position += 1
            todo = []
            for st in live:
                if st.stalled or st.block is not None:
                    continue
                s = st.walk.next_pair()
                if s is None:
                    st.block = self._block(st, decision=st.walk.decision, reason="overlap")
                    continue
                todo.append((st, s))
            if not todo:
                break
            calls = [self._overlap_call(st, s, "sonnet", position) for st, s in todo]
            res = await self._wave(f"o{position:02d}_sonnet", calls)
            opus = []
            for (st, s), c in zip(todo, calls):
                o = res[id(c)]
                if o.status == "ok":
                    need = st.walk.give_sonnet(o.parsed["value"], o.parsed["reason"])
                elif o.status == "unparsed":
                    need = st.walk.give_sonnet(None, error=o.error)
                else:
                    st.stalled = f"Sonnet on {s}: {o.status}" + (f" ({o.error})" if o.error else "")
                    continue
                if need:
                    opus.append((st, s))
            ocalls = [self._overlap_call(st, s, "opus", position) for st, s in opus]
            res = await self._wave(f"o{position:02d}_opus", ocalls) if ocalls else {}
            for (st, s), c in zip(opus, ocalls):
                o = res[id(c)]
                if o.status == "ok":
                    st.walk.give_opus(o.parsed["value"], o.parsed["reason"])
                elif o.status == "unparsed":
                    st.walk.give_opus(None, error=o.error)
                else:
                    st.stalled = f"Opus on {s}: {o.status}" + (f" ({o.error})" if o.error else "")
            for st, _ in todo:
                if st.walk.decided and st.block is None and not st.stalled:
                    st.block = self._block(st, decision=st.walk.decision, reason="overlap")
            self._emit()
        self.stats["positions"] = position

    # -- the full scan --------------------------------------------------------------------
    async def _full_scan(self, live: list[CandState]) -> None:
        calls, owner = [], []
        for st in live:
            for i, x in enumerate(sorted(st.listed, key=lambda x: (-x.cosine, x.stem)), 1):
                calls.append(self._overlap_call(st, x.stem, "sonnet", i))
                owner.append(st)
        res = await self._wave("f_sonnet", calls)
        ocalls, oowner = [], []
        for st, c in zip(owner, calls):
            o = res[id(c)]
            if o.status == "ok":
                st.scan[c.stem] = {"sonnet": {"value": o.parsed["value"], "reason": o.parsed["reason"]}, "opus": None}
            elif o.status == "unparsed":
                st.scan[c.stem] = {"sonnet": {"value": None, "error": o.error}, "opus": None}
            else:
                st.stalled = f"Sonnet on {c.stem}: {o.status}"
                continue
            if NV.sonnet_action(st.scan[c.stem]["sonnet"]["value"], st.cand.cut_off) in NV.OPUS_ROLES:
                ocalls.append(self._overlap_call(st, c.stem, "opus", c.position))
                oowner.append(st)
        res = await self._wave("f_opus", ocalls) if ocalls and self._stop is None else {}
        for st, c in zip(oowner, ocalls):
            o = res.get(id(c), Outcome("not_sent"))
            if o.status == "ok":
                st.scan[c.stem]["opus"] = {"value": o.parsed["value"], "reason": o.parsed["reason"]}
            elif o.status == "unparsed":
                st.scan[c.stem]["opus"] = {"value": None, "error": o.error}
            else:
                st.stalled = f"Opus on {c.stem}: {o.status}"
        for st in live:
            if st.stalled:
                continue
            # the walk replayed on the readings, every listed trait in cosine order (no relation call, so no
            # shortlist, no front and no both-similar rule), under the run's decision rules; traits below the
            # floor are read like the rest but left out of the replayed walk, as the pipeline would leave them
            order = [x.stem for x in sorted(st.listed, key=lambda x: (-x.cosine, x.stem))
                     if not self.rules.below_floor(x.cosine)]
            st.walk = NV.replay_walk(NV.Walk(st.cand.key, st.cand.cut_off, order, {x.stem: x for x in st.listed},
                                             partners=self.partners, cosine_of=self._cos_fn(st), rules=self.rules),
                                     st.scan)
            st.block = self._block(st, decision=st.walk.decision, reason="overlap")

    # -- blocks -----------------------------------------------------------------------------
    def _block(self, st: CandState, *, decision: str, reason: str, covered_by: Optional[str] = None,
               match: Optional[Mapping] = None) -> dict:
        b = NV.novelty_block(run_id=self.batch_id, cand=st.cand.as_dict(), decision=decision, reason=reason,
                             covered_by=covered_by, match=match, walk=st.walk, listed=st.listed, relation=st.relation,
                             shortlist=st.shortlist, rubrics=self.rubric_pins, config_version=self.config_version,
                             embedding=self.embedding, usage=NV.usage_dict(st.usage), at=utc_now(), mode=self.mode,
                             rules=self.rules, renamed=st.renamed, extra=self.extra_block)
        if self.mode == "full_scan":
            by = {x.stem: x for x in st.listed}
            b["scan"] = []
            b["n_below_floor"] = sum(1 for x in st.listed if self.rules.below_floor(x.cosine))
            for s in sorted(st.scan, key=lambda s: (-by[s].cosine, s)):
                r = st.scan[s]
                pv = NV.pair_verdict((r["sonnet"] or {}).get("value"), (r.get("opus") or {}).get("value"), st.cand.cut_off)
                b["scan"].append({"stem": s, "cosine": by[s].cosine, "rank": by[s].rank, "via": by[s].via,
                                  "sonnet": r["sonnet"], "opus": r.get("opus"), **pv,
                                  "cuts": NV.verdict_cuts(pv["verdict"], self.rules),
                                  "below_floor": self.rules.below_floor(by[s].cosine)})
        return b

    # -- parse rates -------------------------------------------------------------------------
    def warn_parse_rates(self, log: Optional[logging.Logger] = None) -> dict:
        """Per (step, model): answers that parsed, at the first attempt and in the end, over the calls of this
        run's records; the loud warning below 99% (judging rule)."""
        log = log or logger
        first: dict[tuple, dict] = {}
        final: dict[tuple, bool] = {}
        for r in self.records:
            if r.get("text") is None:
                continue
            k = (r.get("step"), r.get("model"), r.get("key"), r.get("stem") or ",".join(r.get("stems") or []))
            first.setdefault(k, r)
            final[k] = final.get(k, False) or not r.get("parse_errors")
        out: dict[str, dict] = {}
        for k, r in first.items():
            name = f"{k[0]}:{k[1]}"
            d = out.setdefault(name, {"n": 0, "ok_first": 0, "ok": 0})
            d["n"] += 1
            d["ok_first"] += int(not r.get("parse_errors"))
            d["ok"] += int(final[k])
        for name, d in sorted(out.items()):
            warn_if_low_parse_rate(label=f"novelty_score:{self.batch_id}:{name}", n_ok=d["ok"], n_total=d["n"],
                                   logger_obj=log, extra=f"first attempt {d['ok_first']}/{d['n']}")
        return out


def call_tokens(c: Call) -> tuple[int, int]:
    """Estimated (input, output) tokens of one call (the module's constants)."""
    if c.step == "overlap":
        return OVERLAP_TOKENS["opus" if "opus" in c.model else "sonnet"]
    f = OT.tokenizer_factor(c.model)
    return (int(round((len(c.system) + len(c.user)) / CHARS_PER_TOKEN * f)), relation_out_tokens(c.model, len(c.stems)))


# --------------------------------------------------------------------------- the plan's estimate

def mean_listed_size(index: NV.CorpusIndex, k: int) -> float:
    """The mean number of listed traits (retrieved plus expanded) when each corpus trait is the query with
    itself left out: the listed size a candidate near the corpus gets, at no cost."""
    sizes = []
    for i, s in enumerate(index.stems):
        q = index.Z[i]
        ret = index.retrieve(q, k, exclude=[s])
        sizes.append(len(NV.expand(ret, index.traits, lambda t, q=q: index.cosine_to(q, t))))
    return float(np.mean(sizes)) if sizes else 0.0


def plan_estimate(*, n_candidates: int, n_scan: int, mean_listed: float, relation_text_chars: int,
                  trait_chars: float, cand_chars: float, transport: str = "live", n_embed: Optional[int] = None,
                  embed_tokens_each: int = 30, relation_model: str = RELATION_MODEL):
    """The dry run's estimate by stage (coding_plan_m3.md, "Transport, cost, records"), as a
    :class:`cost.Estimate` per stage: ``{"embeddings", "relation", "overlap", "full_scan"}``.  Overlap pairs:
    :data:`SHORTLIST_PAIRS` a candidate less the early-exit saving; Opus on the shares above.  The relation
    call on ``relation_model``: input by its tokenizer's factor, output from its measured figures where there
    are some (Haiku 5.5, thinking included: :func:`relation_out_tokens`), else by the factor."""
    from .cost import Estimate
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    out = {k: Estimate() for k in ("embeddings", "relation", "overlap", "full_scan")}
    n_embed = n_candidates if n_embed is None else n_embed
    out["embeddings"].add("candidate embeddings (OpenAI text-embedding-3-large) + the 8 canary texts",
                          "text-embedding-3-large", 1, (n_embed + 8) * embed_tokens_each, 0)
    hf = OT.tokenizer_factor(relation_model)
    rin = int(round((relation_text_chars + cand_chars + mean_listed * trait_chars) / CHARS_PER_TOKEN * hf))
    rout = relation_out_tokens(relation_model, mean_listed)
    out["relation"].add(f"relation call, {mean_listed:.1f} listed traits a call", relation_model + suffix,
                        n_candidates, rin, rout)
    sf = OT.tokenizer_factor(UNSURE_MODEL)
    n_uns = int(round(UNSURE_SHARE * n_candidates))
    out["relation"].add(f"unsure re-ask ({UNSURE_SHARE:.0%} of candidates, {UNSURE_TRAITS} traits)", UNSURE_MODEL + suffix,
                        n_uns, int(round((relation_text_chars + cand_chars + UNSURE_TRAITS * trait_chars) / CHARS_PER_TOKEN * sf)),
                        int(round((RELATION_OUT_BASE + RELATION_OUT_PER_TRAIT * UNSURE_TRAITS) * sf)))
    n_pairs = int(round(n_candidates * SHORTLIST_PAIRS * (1 - EARLY_EXIT_SAVING)))
    out["overlap"].add(f"overlap, Sonnet ({SHORTLIST_PAIRS} pairs a candidate, {EARLY_EXIT_SAVING:.0%} saved by early exit)",
                       FIRST_MODEL + suffix, n_pairs, *OVERLAP_TOKENS["sonnet"])
    out["overlap"].add(f"overlap, Opus ({OPUS_SHARE_SHORTLIST:.0%} of pairs)", SECOND_MODEL + suffix,
                       int(round(n_pairs * OPUS_SHARE_SHORTLIST)), *OVERLAP_TOKENS["opus"])
    n_scan_pairs = int(round(n_scan * mean_listed))
    out["full_scan"].add(f"full scan, Sonnet on every listed trait ({mean_listed:.1f} a candidate)", FIRST_MODEL + suffix,
                         n_scan_pairs, *OVERLAP_TOKENS["sonnet"])
    out["full_scan"].add(f"full scan, Opus ({OPUS_SHARE_FULL_SCAN:.0%} of pairs)", SECOND_MODEL + suffix,
                         int(round(n_scan_pairs * OPUS_SHARE_FULL_SCAN)), *OVERLAP_TOKENS["opus"])
    return out


# --------------------------------------------------------------------------- relation only

def _call_line(rec: Mapping) -> dict:
    """One relation call's record, short: the attempt, the stop reason, the usage, the answer's length."""
    return {"model": rec.get("model"), "parse_attempt": rec.get("parse_attempt"), "stop_reason": rec.get("stop_reason"),
            "usage_raw": rec.get("usage_raw"), "text_chars": len(rec["text"]) if rec.get("text") is not None else None,
            "parse_errors": rec.get("parse_errors"), "error": rec.get("error")}


def relation_rows(states: Mapping[str, CandState], records: Sequence[Mapping]) -> list[dict]:
    """``relation.jsonl`` of a ``relation_only`` run: one row per candidate that reached stage 3, in key order:
    the relation model's answer for every listed trait (with Sonnet's, ``second``, where it re-asked an
    ``unsure``), the final relations, the counts, the shortlist the run's rules build from them (and its
    length, which drives the overlap cost), the pair flags and notes, and every relation call's record in
    short (stop reason, usage, the answer's length in characters)."""
    by_key: dict[str, list] = defaultdict(list)
    for r in records:
        if r.get("step") in ("relation", "relation_unsure"):
            by_key[r["key"]].append(r)
    out = []
    for key in sorted(states):
        st = states[key]
        if st.relation is None:
            continue
        rel = st.relation
        sl = st.shortlist
        first = Counter(a["relation"] for a in (rel.get("answers") or {}).values())
        final = Counter(st.relations.values()) if rel.get("status") == "ok" else Counter()
        out.append({
            "key": key, "label": st.cand.label, "stem": st.cand.stem, "gloss": st.cand.gloss,
            "cut_off": st.cand.cut_off, "model": rel["model"], "rubric": rel["rubric"], "status": rel["status"],
            "fallback": rel.get("fallback"), "error": rel.get("error"), "order": rel["order"],
            "listed": [{"stem": x.stem, "cosine": x.cosine, "rank": x.rank, "via": x.via,
                        "partners": list(x.partners)} for x in st.listed],
            "answers": rel.get("answers") or {}, "relations": dict(st.relations),
            "counts": {k: first.get(k, 0) for k in NV.RELATION_ANSWERS},
            "final_counts": {k: final.get(k, 0) for k in NV.RELATION_ANSWERS},
            "unsure_reasked": rel.get("unsure_reasked"),
            "shortlist": list(sl.queue) if sl is not None else None,
            "shortlist_length": len(sl.queue) if sl is not None else None,
            "pair_flags": list(sl.pair_flags) if sl is not None else None,
            "pair_notes": [{k: v for k, v in n.items() if k in ("pair", "kind", "both")} for n in sl.pair_notes]
            if sl is not None else None,
            "pair_completion_for": list(sl.pair_completion_for) if sl is not None else None,
            "renamed_from": dict(st.renamed) if st.renamed else None,
            "stalled": st.stalled,
            "calls": [{"step": r["step"], **_call_line(r)} for r in by_key.get(key, [])]})
    return out


def _dist_stats(xs: Sequence[float]) -> Optional[dict]:
    xs = [float(x) for x in xs if x is not None]
    if not xs:
        return None
    a = np.array(xs)
    return {"n": len(xs), "mean": round(float(a.mean()), 2), "median": float(np.median(a)),
            "p90": float(np.percentile(a, 90)), "max": float(a.max()), "min": float(a.min())}


def relation_call_stats(records: Sequence[Mapping]) -> dict:
    """Per (step, model) over every answered relation call of ``records``: calls, stop reasons, and the
    distribution of uncached input, cache reads and writes, output tokens and the answer's length in
    characters (a thinking model's thinking is in its output tokens, not in the text)."""
    groups: dict[str, list] = defaultdict(list)
    for r in records:
        if r.get("step") in ("relation", "relation_unsure") and r.get("text") is not None:
            groups[f"{r['step']}:{r['model']}"].append(r)
    out = {}
    for name, recs in sorted(groups.items()):
        u = [r.get("usage_raw") or {} for r in recs]
        out[name] = {"n_calls": len(recs), "stop_reasons": dict(Counter(str(r.get("stop_reason")) for r in recs)),
                     "input_tokens": _dist_stats([x.get("input_tokens") for x in u]),
                     "cache_read_tokens": _dist_stats([x.get("cache_read_input_tokens") or 0 for x in u]),
                     "cache_write_tokens": _dist_stats([x.get("cache_creation_input_tokens") or 0 for x in u]),
                     "output_tokens": _dist_stats([x.get("output_tokens") for x in u]),
                     "text_chars": _dist_stats([len(r["text"]) for r in recs]),
                     "output_tokens_per_listed_trait": _dist_stats(
                         [(x.get("output_tokens") or 0) / max(1, len(r.get("stems") or [])) for x, r in zip(u, recs)]),
                     "cost_usd": round(sum(record_cost(r) for r in recs), 6)}
    return out


def relation_summary(rows: Sequence[Mapping], records: Sequence[Mapping], usage: MultiModelUsage, *,
                     skipped: Optional[Mapping] = None, not_reached: Optional[Mapping] = None) -> dict:
    """``relation_summary.json`` of a ``relation_only`` run: candidates, call outcomes, the relation model's
    answers (and the final relations after the unsure re-ask), the unsure rate, similar and opposed per
    candidate, the shortlist lengths, the per-call token figures and the spend."""
    n_listed = sum(len(r["order"]) for r in rows)
    first = Counter()
    final = Counter()
    for r in rows:
        first.update({k: v for k, v in r["counts"].items() if v})
        final.update({k: v for k, v in r["final_counts"].items() if v})
    ok = [r for r in rows if r["status"] == "ok"]
    n_answers = sum(first.values())
    return {
        "n_candidates_reached": len(rows), "not_reached": dict(not_reached or {}), "skipped": dict(skipped or {}),
        "call_status": dict(Counter(r["status"] for r in rows)), "n_listed_total": n_listed,
        "answers": {k: first.get(k, 0) for k in NV.RELATION_ANSWERS},
        "final": {k: final.get(k, 0) for k in NV.RELATION_ANSWERS},
        "unsure_rate": round(first.get("unsure", 0) / n_answers, 5) if n_answers else None,
        "candidates_with_unsure": sum(1 for r in ok if r["counts"].get("unsure")),
        "similar_per_candidate": _dist_stats([r["counts"]["similar"] for r in ok]),
        "opposed_per_candidate": _dist_stats([r["counts"]["opposed"] for r in ok]),
        "similar_plus_opposed_per_candidate": _dist_stats([r["counts"]["similar"] + r["counts"]["opposed"] for r in ok]),
        "shortlist_length": _dist_stats([r["shortlist_length"] for r in rows if r["shortlist_length"] is not None]),
        "shortlist_length_total": sum(r["shortlist_length"] or 0 for r in rows),
        "calls": relation_call_stats(records),
        "spend_usd": round(usage.total_cost_usd, 6), "usage": usage.as_dict()}


# --------------------------------------------------------------------------- the summary

def result_rows(states: Mapping[str, CandState]) -> list[dict]:
    """``results.jsonl`` rows of the decided candidates: ``{"key", "label", "stem", "gloss", "generators",
    "novelty"}``."""
    return [{"key": st.cand.key, "label": st.cand.label, "stem": st.cand.stem, "gloss": st.cand.gloss,
             "generators": st.cand.generators, "novelty": st.block} for st in states.values() if st.block is not None]


def merge_results(earlier: Sequence[Mapping], now: Sequence[Mapping]) -> list[dict]:
    """A resumed session's results with the earlier sessions': this session's row wins for a key it decided
    (an earlier one is kept otherwise), sorted by key."""
    out = {r["key"]: dict(r) for r in earlier}
    out.update({r["key"]: dict(r) for r in now})
    return [out[k] for k in sorted(out)]


def _dist(values: Sequence[int]) -> dict:
    c = Counter(values)
    return {str(k): c[k] for k in sorted(c)}


def summarize(results: Sequence[Mapping], records: Sequence[Mapping], usage: MultiModelUsage, *,
              stalled: Optional[Mapping[str, Any]] = None, skipped: Optional[Mapping[str, int]] = None,
              mode: str = "shortlist") -> dict:
    """``summary.json``'s counts (coding_plan_m3.md): candidates by decision and cut-off, pairs judged per
    candidate, early-exit depth, escalations and rescues, review flags by kind, pair completions, relation
    outcomes, cache hit rates, spend by model and stage.  ``results``: ``{"key", "novelty"}`` rows, every
    candidate the run has decided (earlier sessions' included); ``stalled``: key -> why, the undecided."""
    blocks = [r["novelty"] for r in results]
    stalled = dict(stalled or {})
    by_dec = Counter(b["decision"] for b in blocks)
    by_cut = defaultdict(Counter)
    for b in blocks:
        by_cut[str(b["cut_off"])][b["decision"]] += 1
    walked = [b for b in blocks if b["reason"] == "overlap"]
    roles = Counter()
    rescues = 0
    for b in walked:
        for r in b["readings"]:
            if r.get("opus_role"):
                roles[r["opus_role"]] += 1
            if r.get("outcome") == "rescued":
                rescues += 1
    flags = Counter(f for b in blocks for f in b["review"])
    rel = Counter()
    rel_status = Counter()
    unsure_reasked = 0
    for b in blocks:
        r = b.get("relation")
        if r:
            rel_status[r["status"]] += 1
            for a in (r.get("answers") or {}).values():
                rel[a["relation"]] += 1
            if r.get("unsure_reasked"):
                unsure_reasked += 1
    final_rel = Counter(x["relation"] for b in blocks for x in b.get("listed") or [] if x.get("relation"))
    cache = {}
    for r in records:
        u = r.get("usage_raw") or {}
        if not u:
            continue
        d = cache.setdefault(r["model"], {"calls": 0, "input": 0, "cache_write": 0, "cache_read": 0, "calls_with_read": 0})
        d["calls"] += 1
        d["input"] += int(u.get("input_tokens") or 0)
        d["cache_write"] += int(u.get("cache_creation_input_tokens") or 0)
        d["cache_read"] += int(u.get("cache_read_input_tokens") or 0)
        d["calls_with_read"] += int(bool(u.get("cache_read_input_tokens")))
    for d in cache.values():
        tot = d["input"] + d["cache_write"] + d["cache_read"]
        d["read_share_of_input"] = round(d["cache_read"] / tot, 4) if tot else None
        d["hit_rate_calls"] = round(d["calls_with_read"] / d["calls"], 4) if d["calls"] else None
    spend = defaultdict(lambda: defaultdict(float))
    for r in records:
        spend[r.get("step")][r.get("charged_as") or "none"] += record_cost(r)
    exit_depth = [b["deciding_reading"]["position"] for b in walked if b["decision"] == "covered" and b["deciding_reading"]]
    notes = [n for b in blocks for n in b.get("pair_notes") or []]
    renamed = [b for b in blocks if b.get("renamed_from")]
    rule_sets = sorted({(b.get("rules") or {}).get("name") or NV.RULES[1].name for b in blocks})
    rule_tail = {
        "rules": rule_sets,
        "cosine_floor": sorted({(b.get("rules") or {}).get("cosine_floor") for b in blocks}, key=lambda x: (x is None, x)),
        "review_queue": sum(1 for b in blocks if NV.in_review_queue(b)),
        "covered_flagged": sum(1 for b in blocks if b["decision"] == "covered" and "sonnet_below_opus_at" in b["review"]
                               and any(d.get("kind") == "sonnet_below_opus_at" and d.get("stem") == b.get("covered_by")
                                       for d in b.get("review_details") or [])),
        "pair_notes": {"rows": sum(1 for b in blocks if b.get("pair_notes")), "notes": len(notes),
                       "by_kind": dict(Counter(n.get("kind", "pair") for n in notes)),
                       "rows_by_decision": dict(Counter(b["decision"] for b in blocks if b.get("pair_notes")))},
        "pair_flag_rows": sum(1 for b in blocks if b.get("pair_flags")),
        "floor": {"rows_with_listed_below": sum(1 for b in walked if b.get("n_below_floor")),
                  "listed_below_total": sum(b.get("n_below_floor") or 0 for b in walked),
                  "similar_kept_out_total": sum(len(b.get("below_floor") or []) for b in walked),
                  "rows_with_similar_kept_out": sum(1 for b in walked if b.get("below_floor"))},
        "renamed_from_judged": {"rows": len(renamed), "by_decision": dict(Counter(b["decision"] for b in renamed))},
    }
    return {
        "mode": mode, "n_candidates": len(blocks) + len(stalled), "n_decided": len(blocks), "n_stalled": len(stalled),
        "stalled": stalled, "skipped": dict(skipped or {}),
        "by_decision": dict(by_dec), "by_reason": dict(Counter(b["reason"] for b in blocks)),
        "by_cut_off": {k: dict(v) for k, v in sorted(by_cut.items())},
        "exact_label": dict(Counter((b.get("exact_label") or {}).get("match") for b in blocks if b["reason"] == "exact_label")),
        "pairs_judged_per_candidate": _dist([b["n_pairs_judged"] for b in walked]),
        "pairs_judged_total": sum(b["n_pairs_judged"] for b in walked),
        "pairs_judged_mean": round(float(np.mean([b["n_pairs_judged"] for b in walked])), 3) if walked else None,
        "listed_per_candidate_mean": round(float(np.mean([len(b["listed"]) for b in walked])), 3) if walked else None,
        "shortlist_length": _dist([len(b["shortlist"]) for b in walked]) if mode == "shortlist" else None,
        "early_exit_depth": _dist(exit_depth),
        "escalations": dict(roles), "rescues": rescues,
        "review_flags": dict(flags), "pair_completions": sum(1 for b in blocks if b["pair_completion_for"]),
        "pair_completion_for": {r["key"]: r["novelty"]["pair_completion_for"] for r in results
                                if r["novelty"]["pair_completion_for"]},
        "relation_outcomes": {"call_status": dict(rel_status), "answers": dict(rel), "final": dict(final_rel),
                              "candidates_with_unsure_reasked": unsure_reasked},
        "cache": cache,
        "spend_by_stage": {s: {m: round(v, 6) for m, v in d.items()} for s, d in spend.items()},
        "spend_usd": round(usage.total_cost_usd, 6),
        "usage": usage.as_dict(),
    } | rule_tail
