"""The gloss sense, settled inside candidate generation and **before M1** (Roger, QUESTIONS 56).

A row of the candidate table can carry two glosses: the OEWN person-descriptive sense (the censuses'
:mod:`~assistant_axis.gapgen.generators.censuses.glosshint` pick, in ``gloss_hint``) and the gloss the base
model wrote beside its own word (``sample_gloss``, from the glossary and AI families).  They sometimes read
the word in different senses.  Roger's decision: the sense is resolved here, before submission, because a
gloss changed after M1 or M3 invalidates M1's sense, polysemy and region verdicts and every 0-4 reading M3
made against the corpus.

The four steps:

1. both glosses are computed at table time (:mod:`.table`);
2. divergence is flagged **mechanically**, by the cosine between the two gloss texts — free with a local
   embedder, and it selects the minority of rows worth a call.  Every cosine is kept on the row, so another
   floor can be re-derived without re-embedding (the pattern of QUESTIONS 74's ``probe --refloor``);
3. each divergent row is resolved by **one cheap call** (:data:`MODEL`) shown the word, the sample's gloss
   and OEWN's definition and asked which reading a reader of the sample would take.  Both glosses, the
   decision and its reason stay on the row as provenance (:data:`BLOCK`);
4. submission happens only then (:func:`unresolved` is what ``submit`` refuses on), so M1 and M3 see one
   settled sense and nothing downstream goes stale.

The criterion is **fidelity first** (which sense the sample proposes) **subject to legibility** (the word
plausibly carries that sense in ordinary English), and explicitly **not novelty**: choosing the gloss that
scores better against the corpus would be selecting our answer to make our own filter pass it, and M3 must
judge a sense that was not selected for it.  M1 backstops a bad pick through its polysemy flag and
``check_same_sense``.

The decision does not touch a one-sided row: where OEWN has no sense, ``gloss_hint`` stays ``None`` and the
model's gloss is still not sent to M1 (the pre-registered rule), and where the model wrote no gloss there is
nothing to diverge from.

The table row is never rewritten in place: it keeps both glosses and gains the :data:`BLOCK` block, and
:func:`resolved_hint` is what the submitted :class:`~assistant_axis.gapgen.Candidate` carries.  So the step
is idempotent, and a wrong pick can be read off the table and reversed without resampling.

TODO (Roger, 2026-10-11, QUESTIONS 56): revisit once there is a sample of divergent rows to look at — it may
then be clearly right to **keep both senses** some of the time through ``Candidate.sense_id``, which the
registry supports (one surface, two senses).  Today that stays a rare, explicit escape hatch for a word whose
two senses are both genuinely person-descriptive traits, because it doubles M1 + M3 on those rows and needs a
drop decision Roger does not want to bookkeep.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Awaitable, Callable, Iterable, Mapping, MutableMapping, Optional, Sequence

from ..censuses.glosshint import MAX_WORDS

#: Haiku 5.5, the platform's cheap model (``filter.DEFAULT_MODEL``; checked equal by the tests).
MODEL = "claude-haiku-5-5"
#: Haiku 5.5 refuses a ``temperature`` (``llm.accepts_temperature``), so none is sent.
TEMPERATURE: Optional[float] = None
#: Haiku 5.5 thinks adaptively and the thinking counts against ``max_tokens``: at 300, 33 of 146 calls on the
#: 2026-10-12 pilot came back with no text at all ("empty response" twice).  The answer is a three-field JSON of a
#: few dozen tokens; 1,200 leaves room for the thinking, at a cost of cents.
MAX_TOKENS = 1200
#: The registry-style block the decision lives in, on the table row.
BLOCK = "gloss_sense"
CHOICES = ("dictionary", "sample")
#: Provisional (nothing is measured yet): two glosses of the same sense embed close together, and the floor
#: only decides which rows are worth a call, not the answer.  Every cosine is recorded, so the pilot's
#: divergent rows re-derive it; ``--divergence-cosine`` overrides it.
DIVERGENCE_COSINE = 0.60
#: The free local arm (``gapgen.embed``): the screen must cost nothing, and it is a trigger, not a verdict.
DEFAULT_ARM = "bge"
DEFAULT_CONCURRENCY = 4
RESPONSES_NAME = "gloss_sense_responses.jsonl"
USAGE_NAME = "gloss_sense_usage.json"

#: Version 2 (2026-10-12): the wording is unchanged; ``MAX_TOKENS`` went from 300 to 1,200 because the pin covers it
#: (``wording_tables``) and the rows decided under the 300 cap are re-asked as ``prompt_changed``.
GLOSS_SENSE_VERSION = 2
#: Append-only: the :func:`wording_sha256` of every version's wording (a test enforces it).
PROMPT_HASHES: dict[int, str] = {
    1: "fed661a0da553dc1fea188ff54b8b4365c56124e5f76f5d2b51e6c3d254b5ace",
    2: "d67ad2a914ad7fe600209116714c0a08bf268a13ffd71a5a3a42de745bedf08f",
}

SYSTEM = """\
You decide which sense of a word a short piece of text proposes.

A language model continuing a list of words for what someone (or an AI system) is like wrote a word together
with its own short gloss.  A dictionary (Open English WordNet) also has a sense of that word, picked as its
most person-descriptive one.  The two readings sometimes differ.  Say which of them a reader of the model's
text would take the word in.

The criterion, in this order:

1. Fidelity.  Which sense does the text itself propose?  That is the sense the word is a candidate for, and
   it is the sense later steps have to judge.
2. Legibility.  A reading counts only if the word plausibly carries it in ordinary English: a reader meeting
   the bare word, with no gloss beside it, could arrive at that sense.  Where the text's reading fails this,
   answer "dictionary".

What must not enter the decision: whether a sense is novel, unusual, or unlike anything on some list of
words.  You are not picking the more interesting trait; you are reading which sense was proposed.

Answer with one JSON object and nothing else:

{"choice": "sample" | "dictionary", "legible": true | false, "reason": "<at most 20 words>"}

"choice" is the reading a reader of the text would take.  "legible" says whether the text's reading is one
the bare word plausibly carries in ordinary English.  "reason" is why, in your own words.
"""

USER_TEMPLATE = """\
Word: {word}

The text's gloss: {sample}

The dictionary's person-descriptive sense: {dictionary}

Which reading would a reader of the text take?
"""


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def wording_tables() -> dict:
    """Every piece of wording the call depends on (what :data:`PROMPT_HASHES` pins)."""
    return {"system": SYSTEM, "user": USER_TEMPLATE, "model": MODEL, "max_tokens": MAX_TOKENS,
            "choices": CHOICES}


def wording_sha256() -> str:
    return sha256_text(json.dumps(wording_tables(), sort_keys=True, ensure_ascii=False))


# --------------------------------------------------------------------------- reading a row

def _text(x) -> Optional[str]:
    return x.strip() if isinstance(x, str) and x.strip() else None


def oewn_gloss(row: Mapping) -> Optional[str]:
    """The row's OEWN hint.  The table's ``gloss_hint`` is always the dictionary's: this step never rewrites
    it, which is what makes the step idempotent and a decision reversible (the block keeps its own copy as
    provenance, and a later table rebuild that moves the hint shows up as ``glosses_changed``)."""
    return _text(row.get("gloss_hint"))


def sample_gloss(row: Mapping) -> Optional[str]:
    return _text(row.get("sample_gloss"))


def two_sided(row: Mapping) -> bool:
    """True when the row has both glosses, so a sense can diverge at all."""
    return oewn_gloss(row) is not None and sample_gloss(row) is not None


#: The states a two-sided row can be in before its sense is settled.
SCREEN_REASONS = ("absent", "glosses_changed")
CALL_REASONS = ("awaiting_call", "failed", "prompt_changed")


def stale_reason(row: Mapping) -> Optional[str]:
    """Why the row's sense is not settled yet, or None when it is.

    ``absent`` (no block, or no cosine in it: the free screen has still to run), ``glosses_changed`` (the
    table was rebuilt and a gloss moved, so the cosine is stale), ``awaiting_call`` (divergent, not asked
    yet), ``failed`` (its call failed twice), ``prompt_changed`` (a divergent row was decided by an older
    prompt version).  A row the screen found undivergent is settled and is not stale on a prompt change: its
    decision rests on the cosine, and no call was made."""
    if not two_sided(row):
        return None
    b = row.get(BLOCK) or {}
    if not b or not isinstance(b.get("cosine"), (int, float)):
        return "absent"
    if b.get("oewn") != oewn_gloss(row) or b.get("sample") != sample_gloss(row):
        return "glosses_changed"
    if not b.get("divergent"):
        return None
    if b.get("chosen") not in CHOICES:
        return "failed" if b.get("error") else "awaiting_call"
    if b.get("prompt_version") != GLOSS_SENSE_VERSION:
        return "prompt_changed"
    return None


def needs_screen(row: Mapping) -> bool:
    """True when the free cosine screen has still to run on the row (no block, or a stale one)."""
    return stale_reason(row) in SCREEN_REASONS


def needs_call(row: Mapping) -> bool:
    """True when the screen called the row divergent and no current answer has settled it."""
    return stale_reason(row) in CALL_REASONS


def unresolved(rows: Iterable[Mapping]) -> list[Mapping]:
    """Rows that must not be submitted yet: both glosses and no settled sense (``submit`` refuses on these)."""
    return [r for r in rows if stale_reason(r) is not None]


def resolved_hint(row: Mapping) -> Optional[str]:
    """The ``gloss_hint`` the submitted candidate carries: the decision's gloss where there is one, else the
    table's OEWN hint (an untouched one-sided row keeps exactly what it had)."""
    b = row.get(BLOCK) or {}
    if b.get("chosen") == "sample":
        return _text(b.get("chosen_gloss")) or sample_gloss(row)
    if b.get("chosen") == "dictionary":
        return _text(b.get("chosen_gloss")) or oewn_gloss(row)
    return _text(row.get("gloss_hint"))


def carry_forward(rows: Sequence[MutableMapping], previous: Iterable[Mapping]) -> int:
    """Copy each settled decision from a previous table onto the rebuilt rows whose two glosses are
    unchanged, and return how many were carried.

    ``parse`` rebuilds the table from the samples, so without this a reparse would silently throw away
    decisions that were paid for (and leave every row unresolved again).  A row whose glosses moved is left
    alone: its old decision was about other text, and :func:`stale_reason` must see that."""
    old = {r.get("stem"): r.get(BLOCK) for r in previous if r.get(BLOCK)}
    n = 0
    for r in rows:
        b = old.get(r.get("stem"))
        if not b or not two_sided(r):
            continue
        if b.get("oewn") == oewn_gloss(r) and b.get("sample") == sample_gloss(r):
            r[BLOCK] = dict(b)
            n += 1
    return n


def fit_words(text: Optional[str], limit: int = MAX_WORDS) -> Optional[str]:
    """A hint of at most ``limit`` words, as the censuses' hints are cut."""
    if text is None:
        return None
    words = text.split()
    return " ".join(words[:limit])


# --------------------------------------------------------------------------- the free screen

def cosine_rows(rows: Sequence[Mapping], *, embed: Callable[[Sequence[str]], object]) -> dict[str, float]:
    """``{stem: cosine}`` between the two gloss texts of every row that needs the screen.

    ``embed(texts)`` returns unit rows in input order (``gapgen.embed.embed_texts`` with any arm; the local
    arms are free).  Each distinct text is embedded once."""
    import numpy as np
    todo = [r for r in rows if needs_screen(r)]
    if not todo:
        return {}
    texts: list[str] = []
    for r in todo:
        texts += [oewn_gloss(r) or "", sample_gloss(r) or ""]
    uniq = list(dict.fromkeys(texts))
    E = np.asarray(embed(uniq), dtype=np.float64)
    at = {t: i for i, t in enumerate(uniq)}
    out: dict[str, float] = {}
    for r in todo:
        a, b = E[at[oewn_gloss(r) or ""]], E[at[sample_gloss(r) or ""]]
        out[r["stem"]] = round(float(a @ b), 6)
    return out


def screen(rows: Sequence[MutableMapping], *, cosines: Mapping[str, float], floor: float = DIVERGENCE_COSINE,
           embedder: Optional[str] = None) -> dict:
    """Write the screen onto every row it has a cosine for: the :data:`BLOCK` block with ``cosine`` and
    ``divergent``, and, for a row the glosses agree on, the settled decision (``chosen: "dictionary"``, no
    call).  Returns counts."""
    from assistant_axis.gapgen.registry import utc_now
    n_div = n_agree = 0
    for r in rows:
        c = cosines.get(r.get("stem"))
        if c is None or not needs_screen(r):
            continue
        divergent = c < float(floor)
        b = {"oewn": oewn_gloss(r), "sample": sample_gloss(r), "cosine": c, "divergent": divergent,
             "floor": float(floor), "embedder": embedder, "chosen": None, "chosen_gloss": None, "legible": None,
             "reason": None, "model": None, "prompt_version": None, "prompt_sha256": None, "at": utc_now()}
        if not divergent:
            # The glosses read the same sense, so there is nothing to choose and nothing to pay for: the
            # dictionary's wording stays the hint, as it was before this step existed.
            b.update({"chosen": "dictionary", "chosen_gloss": oewn_gloss(r),
                      "reason": f"glosses agree (cosine {c:.3f} >= floor {float(floor):.2f}); no call"})
            n_agree += 1
        else:
            n_div += 1
        r[BLOCK] = b
    return {"n_screened": n_div + n_agree, "n_divergent": n_div, "n_agree": n_agree, "floor": float(floor),
            "divergence_rate": round(n_div / (n_div + n_agree), 4) if (n_div + n_agree) else None}


# --------------------------------------------------------------------------- the call

def request(*, word: str, sample: str, dictionary: str, model: str = MODEL) -> dict:
    """One call as the model receives it: ``{"system", "user", "model", "max_tokens", "temperature",
    "cache_system"}``.  ``word`` is shown in its display form (the label, spaces not underscores)."""
    from assistant_axis.entity_id import display_form_name
    return {"system": SYSTEM, "model": model, "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE,
            "cache_system": True,
            "user": USER_TEMPLATE.format(word=display_form_name(str(word)), sample=sample, dictionary=dictionary)}


def render(row: Mapping, *, model: str = MODEL) -> str:
    """The row's call as a rendered sample (the dry run, and the plan's "read the rendered prompt" rule)."""
    q = request(word=row.get("surface") or row.get("stem") or "", sample=sample_gloss(row) or "",
                dictionary=oewn_gloss(row) or "", model=model)
    head = {k: q[k] for k in ("model", "max_tokens", "temperature", "cache_system")}
    return (f"=== gloss sense v{GLOSS_SENSE_VERSION} ({wording_sha256()[:12]}), {row.get('stem')}: "
            f"{json.dumps(head)} ===\n--- system ---\n{q['system']}\n--- user ---\n{q['user']}")


def parse_answer(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """``(answer, error)``: the JSON object with a valid ``choice``, a boolean ``legible`` and a ``reason``.

    The JSON is read with the platform's own reader (``filter_rubric._load_json``: a blob in prose, and its
    repair pass), so a fenced or chatty answer parses here exactly as it does for M1."""
    from assistant_axis.gapgen.filter_rubric import _load_json
    if not (text or "").strip():
        return None, "empty response"
    try:
        d = _load_json(text)
    except (ValueError, json.JSONDecodeError) as exc:
        return None, f"unparseable response: {exc}"
    if not isinstance(d, Mapping):
        return None, "the JSON is not an object"
    choice = d.get("choice")
    if choice not in CHOICES:
        return None, f"choice must be one of {CHOICES}, got {choice!r}"
    legible = d.get("legible")
    if not isinstance(legible, bool):
        return None, "legible must be true or false"
    reason = _text(d.get("reason"))
    if reason is None:
        return None, "reason is missing"
    return {"choice": choice, "legible": legible, "reason": reason}, None


def decide(answer: Mapping) -> tuple[str, Optional[str]]:
    """``(choice, note)`` under the criterion: fidelity first, **subject to legibility**.

    An answer that picks the sample's reading while calling it illegible contradicts itself; the conservative
    reading of Roger's criterion is that such a sense must not be shown to M1 as the intended one, so the
    dictionary's wins and the contradiction is recorded."""
    if answer["choice"] == "sample" and answer["legible"] is False:
        return "dictionary", "answered sample but called the reading illegible: legibility decides"
    return str(answer["choice"]), None


Send = Callable[[Mapping, dict], Awaitable[Optional[str]]]


def _anthropic_send(client, *, usage, retry_delays: Optional[Sequence[float]] = None) -> Send:
    """The real sender: one Messages call per request, every response charged to ``usage``."""
    from assistant_axis.gapgen.llm import RETRY_DELAYS_S, call_anthropic_json
    delays = tuple(RETRY_DELAYS_S if retry_delays is None else retry_delays)

    async def send(q: Mapping, meta: dict) -> Optional[str]:
        return await call_anthropic_json(client, system=q["system"], user=q["user"], model=q["model"],
                                         max_tokens=q["max_tokens"], temperature=q["temperature"], usage=usage,
                                         cache_system=q["cache_system"], retry_delays=delays, meta=meta)
    return send


async def resolve_rows(rows: Sequence[MutableMapping], *, client=None, send: Optional[Send] = None, usage=None,
                       model: str = MODEL, concurrency: int = DEFAULT_CONCURRENCY,
                       retry_delays: Optional[Sequence[float]] = None, records_path: Optional[Path] = None,
                       on_row: Optional[Callable[[Mapping], None]] = None) -> dict:
    """One call per divergent row (:func:`needs_call`), the answer written onto the row's block.

    ``send`` replaces the Anthropic path in tests; otherwise ``client`` is an ``AsyncAnthropic``.  Every
    response is appended to ``records_path`` before it is parsed, and an answer that fails validation is
    retried once, alone, as M1 retries.  A row whose call failed twice keeps ``chosen: None`` and gains
    ``error``, so it stays :func:`unresolved` and ``submit`` refuses it rather than guessing a sense."""
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.judge_pricing import BudgetExceededError
    if send is None:
        if client is None:
            raise ValueError("resolve_rows needs a client or a send function")
        send = _anthropic_send(client, usage=usage, retry_delays=retry_delays)
    todo = [r for r in rows if needs_call(r)]
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    stop: list[BaseException] = []
    counts = {"n_called": 0, "n_sample": 0, "n_dictionary": 0, "n_failed": 0, "n_illegible_sample": 0}
    if records_path is not None:
        Path(records_path).parent.mkdir(parents=True, exist_ok=True)

    def record(row: Mapping, q: Mapping, text: Optional[str], meta: Mapping, *, retry: bool,
               err: Optional[str]) -> None:
        if records_path is None:
            return
        rec = {"stage": BLOCK, "stem": row.get("stem"), "surface": row.get("surface"), "model": q["model"],
               "prompt_version": GLOSS_SENSE_VERSION, "prompt_sha256": wording_sha256(), "user": q["user"],
               "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
               "attempts": meta.get("attempts"), "error": meta.get("error"), "parse_error": err, "retry": retry,
               "at": utc_now()}
        with open(records_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    async def one(row: MutableMapping) -> None:
        q = request(word=row.get("surface") or row["stem"], sample=sample_gloss(row) or "",
                    dictionary=oewn_gloss(row) or "", model=model)
        err: Optional[str] = None
        for retry in (False, True):
            if stop:
                return
            meta: dict = {}
            async with sem:
                if stop:
                    return
                try:
                    text = await send(q, meta)
                except BudgetExceededError as exc:
                    text = meta.get("text")
                    stop.append(exc)
            answer, perr = parse_answer(text)
            if text is None and perr in (None, "empty response"):
                perr = f"no response: {meta.get('error')}"
            record(row, q, text, meta, retry=retry, err=perr)
            if answer is not None:
                choice, note = decide(answer)
                b = dict(row[BLOCK])
                b.update({"chosen": choice,
                          "chosen_gloss": fit_words(sample_gloss(row) if choice == "sample" else oewn_gloss(row)),
                          "legible": answer["legible"], "reason": answer["reason"], "model": q["model"],
                          "prompt_version": GLOSS_SENSE_VERSION, "prompt_sha256": wording_sha256(),
                          "at": utc_now()})
                if note:
                    b["note"] = note
                    counts["n_illegible_sample"] += 1
                b.pop("error", None)
                row[BLOCK] = b
                counts["n_called"] += 1
                counts["n_sample" if choice == "sample" else "n_dictionary"] += 1
                if on_row is not None:
                    on_row(row)
                return
            err = perr if err is None else f"{err}; retry: {perr}"
        b = dict(row[BLOCK])
        b.update({"chosen": None, "chosen_gloss": None, "error": err, "model": q["model"],
                  "prompt_version": GLOSS_SENSE_VERSION, "prompt_sha256": wording_sha256(), "at": utc_now()})
        row[BLOCK] = b
        counts["n_called"] += 1
        counts["n_failed"] += 1
        if on_row is not None:
            on_row(row)

    await asyncio.gather(*(one(r) for r in todo))
    if stop:
        raise stop[0]
    return counts


def run_resolve_rows(rows: Sequence[MutableMapping], **kw) -> dict:
    """:func:`resolve_rows` from synchronous code; the client is closed inside the same event loop (an
    ``AsyncAnthropic`` left open is closed after ``asyncio.run`` has closed the loop, which raises
    "Event loop is closed")."""
    async def main() -> dict:
        try:
            return await resolve_rows(rows, **kw)
        finally:
            close = getattr(kw.get("client"), "close", None)
            if close is not None:
                res = close()
                if asyncio.iscoroutine(res):
                    await res
    return asyncio.run(main())


# --------------------------------------------------------------------------- the record

def summary(rows: Iterable[Mapping]) -> dict:
    """What a round's record keeps: how many rows had two glosses, how many diverged, how the divergent ones
    were decided, and how many are still unresolved (which block submission)."""
    rows = list(rows)
    two = [r for r in rows if two_sided(r)]
    blocks = [r[BLOCK] for r in two if r.get(BLOCK)]
    div = [b for b in blocks if b.get("divergent")]
    chosen = [b for b in div if b.get("chosen") in CHOICES]
    cos = [b["cosine"] for b in blocks if isinstance(b.get("cosine"), (int, float))]
    return {"n_rows": len(rows), "n_two_sided": len(two), "n_screened": len(blocks), "n_divergent": len(div),
            "divergence_rate": round(len(div) / len(blocks), 4) if blocks else None,
            "n_chose_sample": sum(1 for b in chosen if b["chosen"] == "sample"),
            "n_chose_dictionary": sum(1 for b in chosen if b["chosen"] == "dictionary"),
            "n_illegible_sample": sum(1 for b in div if b.get("note")),
            "n_failed": sum(1 for b in div if b.get("chosen") not in CHOICES),
            "n_unresolved": len(unresolved(rows)),
            "cosine_min": round(min(cos), 4) if cos else None,
            "cosine_median": round(sorted(cos)[len(cos) // 2], 4) if cos else None,
            "prompt_version": GLOSS_SENSE_VERSION, "prompt_sha256": wording_sha256(), "model": MODEL}
