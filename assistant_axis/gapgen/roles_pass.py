"""The roles pass: the shared role path of plan 16 (gloss and kind stage, M3 for roles, R1, R2, promotion by name).

Coding plan: ``reports/trait_gap_generation/coding_plan_16_role_generators.md`` (2026-10-21, Roger's decisions of
2026-10-21 and 2026-10-22); idea plan ``16_role_generators.md`` § 3.  The role counterpart of
:mod:`assistant_axis.gapgen.physical_pass`.

A **role row** (:func:`is_role_row`) is a registry row on the ``roles`` holding list (M1 tagged it a person or thing,
``role_person`` / ``role_thing``: the 382 held rows of the pilot), or a role-aimed row a generator submitted in role
mode (``Candidate(entity_type="role")``, key ``stem|R#sense``) whose M1 route (``filter.role_route``) is ``role`` or
``both``.  Such a row has no gloss (M1 writes one only for a trait outcome), so the pass begins with a **stage**:

1. the **role gloss** call (rubric ``role_gloss.md``, Haiku 5.5, M1's request settings), one sentence in the role
   corpus's form, "A <label> is someone who ..." / "... is something that ...", for the reading M1 accepted;
2. the **role kind** call (rubric ``role_kind.md``, the system prompt of ``data_analysis/classify_role_kinds.py``
   moved byte for byte, so that a candidate's kind and a corpus role's are measured alike), read three times on the
   gloss and combined by majority (``classify_role_kinds.combine``: a three-way split keeps the first reading's kind
   and says ``kind_split``).

The answers go on the row as its own block, :data:`BLOCK` (``role_pass``), beside the untouched ``filter`` block.
Then M3 against the role corpus (``novelty_score.py score --holding roles``): retrieval over the role descriptions
(:func:`assistant_axis.gapgen.novelty.load_role_corpus`, query form ``role_gloss_w14``), the relation call and the
overlap call on the role rubrics (``relation_roles.md``, ``overlap_concept_roles.md``), a flat cut-off of 3
(:class:`RoleCandidate`: a sub-role is covered by its parent, decision 4), and the nearest traits as information
(``cross_type``, decision 5).  R1 and R2 read a roles batch from its ``pass``; promotion is by name only
(``promote(..., allow_roles=True)``), writing an ``entity_type: "role"`` queue entry (:func:`queue_entry_extras`).

The **kind readout** (decision 2, Roger 2026-10-21): :func:`balance` says, for each of the nine kinds, whether the
corpus as it will be after this review holds it more than 10% above or below the count that keeps its share as on
2026-10-16 (:data:`REFERENCE_KINDS_2026_10_16`); the review card shows the candidate's kind's status and a review
order shows the too-low kinds first.  Information only: nothing is cut.
"""
from __future__ import annotations

import asyncio
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from .novelty_runner import M3Candidate

#: The holding list this pass reads, and the name the pass goes by in blocks and ``run.json``.
HOLDING = "roles"
PASS_NAME = "roles"
#: The registry field holding the stage's answers for a row.
BLOCK = "role_pass"
#: The stage's model: M1's first model (Haiku 5.5), which takes no temperature.
MODEL = "claude-haiku-5-5"
#: The stage's two steps, in order (their rubric names in ``split_rubrics.ROLE_FILES``).
STEPS = ("role_gloss", "role_kind")
STAGE = "role_pass"
#: Three readings of the kind call, combined by majority (a call that decides; judging.md, Roger 2026-10-13).
KIND_READINGS = 3
#: The kind call's ``max_tokens``: classify_role_kinds.py's (Haiku 5.5 thinks adaptively, and the thinking counts).
KIND_MAX_TOKENS = 2000
#: The stage's files in an M3 run directory.
RESPONSES_NAME = "role_pass_responses.jsonl"
RESULTS_NAME = "role_pass.jsonl"
DEFAULT_CONCURRENCY = 4
#: The section of a promoted role's seed-queue entry (idea plan § 3 step 7).
SECTION = "role generators (2026-10)"
#: The cut-off of every role candidate, under every rule set (decision 4 and § 3 step 5): covered at 3 or above.
CUT_OFF = 3


def _kinds():
    import data_analysis.classify_role_kinds as CRK
    return CRK


#: The nine role kinds ``(key, name, definition)``, re-exported from ``classify_role_kinds.py`` (one source).
KINDS: list = _kinds().KINDS
KIND_KEYS: list = [k for k, _, _ in KINDS]

#: Decision 3 (Roger 2026-10-21, open: "TBD"), built as one table and one flag so that the twins TODO can change it:
#: the route of a role-aimed row from the kind call's answer for its most likely reading (M1's step 2 kinds,
#: ``split.KINDS``).  ``role``: the role flow (no holding list: it is where the row was aimed); ``both``: the noun stays a
#: role candidate (kind 8, temperament) and its adjective sibling (:data:`RELABEL_ROLE_AIMED`) is in the trait flow;
#: ``membership``: the membership track (memberships are traits, decisions_m1.md decision 3); ``turned_away``: not
#: in the role flow, M1's tags kept.  A row with no reading (or every primary reading stretched) is turned away.
ROLE_ROUTES: dict[str, str] = {"role": "role", "trait": "both", "membership": "membership", "state": "turned_away",
                               "physical": "turned_away", "action": "turned_away", "evaluative": "turned_away",
                               "not_a_persona": "turned_away"}
ROUTES_VERSION = 1
#: The other half of decision 3: ``"auto"`` gives a role-aimed noun its adjective sibling at submission (the relabel
#: helper, ``registry.submit_candidates``), submitted as a trait; ``None`` turns the sibling off.
RELABEL_ROLE_AIMED: Optional[str] = "auto"
#: The kind counts of the role corpus on 2026-10-16 (``data/roles/role_kinds.json``, Haiku 5.5, three readings), the
#: reference the readout holds each kind's share to (decision 2); ``default.json`` left out (it is ``other``: 4 -> 3).
REFERENCE_KINDS_2026_10_16: dict[str, int] = {
    "occupation": 162, "stance": 47, "non_human": 44, "circumstance": 24, "temperament": 22, "relationship": 20,
    "status": 9, "pastime": 8, "other": 3}
#: "More than 10% above or below the count that keeps the kind's share" (Roger, 2026-10-21).
BALANCE_MARGIN = 0.10
STATUSES = ("too_low", "about_right", "too_high")


# --------------------------------------------------------------------------- reading a row

def route_for(kind_call: Optional[str], *, entity_type: str) -> Optional[str]:
    """The route of a role-aimed row (``entity_type == "role"``) whose most likely reading the kind call gave
    ``kind_call`` (:data:`ROLE_ROUTES`; no kind, as for a row with no reading: ``turned_away``); None for a trait-aimed
    row (its routing is M1's as always)."""
    if entity_type != "role":
        return None
    return ROLE_ROUTES.get(str(kind_call), "turned_away") if kind_call else "turned_away"


def is_role_row(row: Mapping) -> bool:
    """A row the roles pass reads: on the ``roles`` holding list (M1 put it there), or a role-aimed row
    (``entity_type == "role"``) whose M1 route is ``role`` or ``both``."""
    if row.get("holding") == HOLDING:
        return True
    return row.get("entity_type") == "role" and (row.get("filter") or {}).get("role_route") in ("role", "both")


def accepted_reading(row: Mapping) -> Optional[str]:
    """The reading M1 accepted (``filter.judged_sense``, else the sense block's reading at ``accepted_reading``), as
    :func:`physical_pass.accepted_reading` reads it."""
    from .physical_pass import accepted_reading as pp_accepted
    return pp_accepted(row)


def block_of(row: Mapping) -> dict:
    return dict(row.get(BLOCK) or {})


def gloss_of(row: Mapping) -> Optional[str]:
    """The role gloss of the row's ``role_pass`` block (a role row's own ``gloss`` is M1's, null for a role)."""
    g = block_of(row).get("gloss")
    return g.strip() if isinstance(g, str) and g.strip() else None


def kind_of(row: Mapping) -> Optional[str]:
    """The kind the role kind call gave (the majority of its readings), or None."""
    k = block_of(row).get("kind")
    return k if k in KIND_KEYS else None


def human_of(row: Mapping) -> Optional[bool]:
    """Whether the role is a human being: derived from the kind (``kind != "non_human"``), None without one."""
    k = kind_of(row)
    return None if k is None else k != "non_human"


def kind_guess_of(row: Mapping) -> Optional[str]:
    """The first generator's kind guess on the row's sources (provenance; the pipeline acts on :func:`kind_of`)."""
    return next((s.get("kind_guess") for s in row.get("sources") or [] if s.get("kind_guess")), None)


def needs_stage(row: Mapping) -> bool:
    """A role row whose stage has not given it a gloss and a kind yet (a row glossed by an earlier run whose kind calls
    all failed gets the kind calls only)."""
    return is_role_row(row) and (gloss_of(row) is None or kind_of(row) is None)


# --------------------------------------------------------------------------- the kind readout (decision 2)

def balance(current: Mapping[str, int], n_now: int, *, reference: Mapping[str, int] = REFERENCE_KINDS_2026_10_16,
            margin: float = BALANCE_MARGIN) -> dict:
    """The kind readout (coding plan 16, § 6.4).  For each kind: its ``reference`` count and ``share`` of the
    reference total; ``held = share x n_now``, the count that keeps the share at the corpus's size ``n_now``;
    ``count`` (``current``); ``status`` ``too_low`` when ``count < (1 - margin) x held``, ``too_high`` when ``count >
    (1 + margin) x held``, else ``about_right``; ``room = held - count``.  ``order``: the kinds by status (too low,
    about right, too high), then by ``room``, largest first (the order a review shows them in)."""
    total = sum(reference.values())
    if total <= 0:
        raise ValueError("the reference counts sum to zero")
    kinds = {}
    for k in KIND_KEYS:
        ref = int(reference.get(k, 0))
        share = ref / total
        held = share * n_now
        cnt = int(current.get(k, 0))
        if cnt < (1 - margin) * held:
            status = "too_low"
        elif cnt > (1 + margin) * held:
            status = "too_high"
        else:
            status = "about_right"
        kinds[k] = {"reference": ref, "share": round(share, 4), "count": cnt, "held": round(held, 1),
                    "status": status, "room": round(held - cnt, 1)}
    order = sorted(KIND_KEYS, key=lambda k: (STATUSES.index(kinds[k]["status"]), -kinds[k]["room"], k))
    return {"n_now": int(n_now), "reference_total": total, "margin": margin, "kinds": kinds, "order": order}


def kind_status(kind: Optional[str], *, current: Mapping[str, int], n_now: int, **kw) -> Optional[str]:
    """The readout's status of ``kind`` (``too_low``, ``about_right``, ``too_high``), None for no kind."""
    if kind not in KIND_KEYS:
        return None
    return balance(current, n_now, **kw)["kinds"][kind]["status"]


STATUS_WORDS = {"too_low": "too low", "about_right": "about right", "too_high": "too high"}


def kind_readout(kind: Optional[str], bal: Mapping) -> Optional[dict]:
    """The card's readout for ``kind`` under the balance ``bal``: ``{"kind", "status", "count", "held", "margin",
    "text"}`` (``text``: "occupation: too high (171 against 161.6 held at 339)"), None for no kind."""
    if kind not in KIND_KEYS:
        return None
    k = bal["kinds"][kind]
    margin = round(bal["margin"] * k["held"], 1)
    return {"kind": kind, "status": k["status"], "count": k["count"], "held": k["held"], "margin": margin,
            "text": f"{kind}: {STATUS_WORDS[k['status']]} ({k['count']} against {k['held']} held at "
                    f"{bal['n_now']}, margin {margin})"}


def balance_lines(bal: Mapping) -> list[str]:
    """One line per kind, in the readout's order: ``occupation 171 / 168 held (too high)``."""
    return [f"{k} {bal['kinds'][k]['count']} / {bal['kinds'][k]['held']:g} held ({STATUS_WORDS[bal['kinds'][k]['status']]})"
            for k in bal["order"]]


#: The seed-queue statuses at which a role entry is a role in hand that is not yet a role file (as the trait index's
#: ``novelty.QUEUE_SEARCH_STATUSES``): it counts toward the corpus the readout holds kinds against.
LIVE_QUEUE_STATUSES = ("candidate", "ready", "tbd", "backlog")


def queue_entry_kind(entry: Mapping) -> Optional[str]:
    """A role queue entry's kind: its ``gap_gen.role_kind.kind``, else its ``kind:<kind>`` tag."""
    rk = ((entry.get("gap_gen") or {}).get("role_kind") or {}).get("kind")
    if rk in KIND_KEYS:
        return rk
    for t in entry.get("tags") or []:
        if isinstance(t, str) and t.startswith("kind:") and t[5:] in KIND_KEYS:
            return t[5:]
    return None


def corpus_kind_counts(data_dir: Path, queue: Mapping, *, nominees: Iterable[Mapping] = (),
                       kinds_path: Optional[Path] = None) -> tuple[dict, int]:
    """``(counts, n_now)`` of the role corpus as it will be once a review is applied: the role files
    (``default.json`` left out) with their kinds from ``role_kinds.json`` (``kinds_path``; default
    ``<data_dir>/roles/role_kinds.json``); the live role entries of the queue whose stem has no file
    (:data:`LIVE_QUEUE_STATUSES`; kind :func:`queue_entry_kind`); and ``nominees``, registry rows this review
    promotes whose stem is neither (kind :func:`kind_of`).  A role with no kind on record counts in ``n_now`` and
    under ``counts["unknown"]``."""
    data_dir = Path(data_dir)
    files = {p.stem for p in (data_dir / "roles" / "instructions").glob("*.json")} - {"default"}
    kp = Path(kinds_path) if kinds_path else data_dir / "roles" / "role_kinds.json"
    recorded = (json.loads(kp.read_text(encoding="utf-8")).get("roles") or {}) if kp.exists() else {}
    counts: Counter = Counter()
    for s in files:
        k = (recorded.get(s) or {}).get("kind")
        counts[k if k in KIND_KEYS else "unknown"] += 1
    seen = set(files)
    for e in queue.get("entries") or []:
        if e.get("entity_type") != "role" or e.get("status") not in LIVE_QUEUE_STATUSES:
            continue
        s = e.get("stem")
        if not s or s in seen:
            continue
        seen.add(s)
        k = queue_entry_kind(e)
        counts[k if k else "unknown"] += 1
    for r in nominees:
        s = r.get("stem")
        if not s or s in seen:
            continue
        seen.add(s)
        k = kind_of(r)
        counts[k if k else "unknown"] += 1
    return dict(counts), len(seen)


# --------------------------------------------------------------------------- the role gloss's form

import re as _re


def _label_pattern(label: str) -> str:
    """A regular expression for ``label`` as a gloss writes it: case-insensitive (the caller's flag), spaces, hyphens
    and underscores interchangeable, an apostrophe optional (``devil's advocate``)."""
    words = [w for w in _re.split(r"[\s_\-]+", str(label).strip()) if w]
    return r"[\s\-]+".join(_re.escape(w).replace("'", "'?").replace("\\'", "'?") for w in words)


def opening_re(label: str):
    """``A|An|The <label> is`` at the start of a gloss (case-insensitive), the form "A <role> is someone who ..."."""
    return _re.compile(r"^\s*(?:an?|the)\s+" + _label_pattern(label) + r"\s+is\s+", _re.I)


def role_gloss_form_ok(gloss: Optional[str], label: str) -> bool:
    """True when the gloss opens with its label in the corpus form ("A bouncer is ...", "An operator is ...")."""
    return bool(gloss) and bool(opening_re(label).match(gloss))


def strip_opening(gloss: str, label: str) -> tuple[str, bool]:
    """``(text, stripped)``: the gloss without its opening ``A|An <label> is`` (the retrieval check's production query
    form, Roger's decision 3 of 2026-10-22: a query that keeps the label finds the role's own description by the
    label alone), and whether it opened so.  A gloss that does not open so comes back whole."""
    m = opening_re(label).match(gloss or "")
    if not m:
        return (gloss or "").strip(), False
    rest = gloss[m.end():].strip()
    return (rest[:1].upper() + rest[1:]) if rest else rest, True


# --------------------------------------------------------------------------- the stage: requests

def max_tokens_for(step: str, model: str = MODEL) -> int:
    """The role gloss call: M1's ``max_tokens`` for its gloss call (``physical_pass.max_tokens_for``: the thinking
    allowance on a model that refuses a temperature); the role kind call: :data:`KIND_MAX_TOKENS`."""
    from .physical_pass import max_tokens_for as pp_max
    if step == "role_gloss":
        return pp_max("gloss", model)
    if step == "role_kind":
        return KIND_MAX_TOKENS
    raise ValueError(f"the roles pass's stage sends {STEPS}, not {step!r}")


def request(step: str, *, label: str, reading: Optional[str] = None, gloss: Optional[str] = None, model: str = MODEL,
            rubrics_dir: Optional[Path] = None, label_form: Optional[str] = None) -> dict:
    """One call of the stage: ``role_gloss`` on the reading (``split.payload("gloss", ...)``'s shape, one JSON object
    with ``"id": 1``; ``reading`` None for the retrieval check's corpus roles), ``role_kind`` on the gloss
    (``classify_role_kinds.user_message``: ``Role: <label>`` / ``Description: <gloss>``).  ``label`` (as stored) is
    shown in ``label_form`` (the judge display form by default).  ``{"step", "model", "system", "user",
    "max_tokens", "temperature", "cache_system"}``."""
    from . import split
    from . import split_rubrics as sr
    from . import split_runner as SR
    from .prompt_labels import DEFAULT_LABEL_FORM, prompt_label
    if step not in STEPS:
        raise ValueError(f"the roles pass's stage sends {STEPS}, not {step!r}")
    form = label_form or DEFAULT_LABEL_FORM
    system = sr.load_prompt(step, rubrics_dir)
    if step == "role_gloss":
        user = split.payload("gloss", label=label, reading=reading, label_form=form)
        temperature = SR.TEMPERATURE
    else:
        if not gloss:
            raise ValueError("the role kind call reads a gloss")
        user = _kinds().user_message(prompt_label(label, form), gloss)
        temperature = None
    return {"step": step, "model": model, "system": system, "user": user, "max_tokens": max_tokens_for(step, model),
            "temperature": temperature, "cache_system": SR.caches_system(system, model)}


def pins(rubrics_dir: Optional[Path] = None) -> dict:
    """``{"step_versions": {step: version}, "prompt_sha256": {step: sha}}`` of the two prompts as pinned; a
    ``ValueError`` when either text on disk is not its latest pin."""
    from . import split_rubrics as sr
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] in STEPS]
    if probs:
        raise ValueError("; ".join(probs))
    cur = sr.current_versions(rubrics_dir, STEPS)
    return {"step_versions": {s: cur[s][0] for s in STEPS},
            "prompt_sha256": {s: sr.sha256(sr.load_prompt(s, rubrics_dir)) for s in STEPS}}


#: Estimated tokens a call on Haiku 5.5: the role gloss as M1's gloss call measured (``split_runner.tokens_for``);
#: the kind call as ``classify_role_kinds.py`` estimates it (generous: 900 in, 600 out).
def tokens_for(step: str, model: str = MODEL) -> tuple[int, int]:
    from . import split_runner as SR
    if step == "role_gloss":
        return SR.tokens_for("gloss", model)
    CRK = _kinds()
    return CRK.EST_IN, CRK.EST_OUT


def estimate(n_rows: int, *, model: str = MODEL, n_kind_only: int = 0, batch: bool = False):
    """The stage's estimate: one role gloss call and :data:`KIND_READINGS` kind calls a row (``n_kind_only`` more rows
    that have their gloss and need only the kind calls); ``batch`` prices them at the Batches rate."""
    from assistant_axis.judge_pricing import BATCH_SUFFIX
    from .cost import Estimate
    m = model + (BATCH_SUFFIX if batch else "")
    est = Estimate()
    i, o = tokens_for("role_gloss", model)
    est.add("roles pass stage: the role gloss call", m, n_rows, i, o)
    i, o = tokens_for("role_kind", model)
    est.add(f"roles pass stage: the role kind call ({KIND_READINGS} readings)", m, (n_rows + n_kind_only) * KIND_READINGS,
            i, o)
    return est


def render(row: Mapping, *, model: str = MODEL, rubrics_dir: Optional[Path] = None,
           label_form: Optional[str] = None) -> str:
    """The role gloss request for ``row`` and the kind request's form, as the model receives them (the dry run; the
    kind call's description is the gloss, not known before the call)."""
    p = pins(rubrics_dir)
    q = request("role_gloss", label=row["label"], reading=accepted_reading(row), model=model, rubrics_dir=rubrics_dir,
                label_form=label_form)
    head = {k: q[k] for k in ("model", "max_tokens", "temperature", "cache_system")}
    k = request("role_kind", label=row["label"], gloss="<the role gloss>", model=model, rubrics_dir=rubrics_dir,
                label_form=label_form)
    return (f"=== roles pass stage, {row['key']}: role_gloss v{p['step_versions']['role_gloss']}, request settings "
            f"{json.dumps(head)} ===\n--- system ---\n{q['system']}\n--- user ---\n{q['user']}\n"
            f"=== then role_kind v{p['step_versions']['role_kind']} on the gloss, {KIND_READINGS} readings, settings "
            f"{json.dumps({x: k[x] for x in ('model', 'max_tokens', 'temperature', 'cache_system')})} ===\n"
            f"--- user ---\n{k['user']}\n")


# --------------------------------------------------------------------------- the stage: calls

@dataclass
class StageCall:
    """One call of the stage: one row, one prompt (``rep``: the kind reading, 0-based)."""
    step: str
    key: str
    label: str
    model: str
    system: str
    user: str
    max_tokens: int
    temperature: Optional[float]
    cache_system: bool = False
    cache_ttl: Optional[str] = None
    rep: int = 0
    retry: bool = False

    @property
    def prompt_sha256(self) -> str:
        from . import split_rubrics as sr
        return sr.sha256(self.system)

    @property
    def custom_id(self) -> str:
        """``<step>-<key>-<hash>-<reading>[-r]``, within the Message Batches limit of 64 characters of
        ``[A-Za-z0-9_-]``; the retry of a call has its own id."""
        import hashlib
        h = hashlib.sha256(f"{self.step}|{self.key}|{self.user}".encode("utf-8")).hexdigest()[:10]
        k = _re.sub(r"[^A-Za-z0-9_-]", "_", self.key)[:28]
        return f"{self.step[5:9]}-{k}-{h}-{self.rep}" + ("-r" if self.retry else "")

    def cache_key(self) -> tuple:
        """``(step, prompt hash, model, user, reading)``: the three kind readings send the same request, so a resume
        finds each its own answer."""
        return (self.step, self.prompt_sha256, self.model, self.user, self.rep)


def record_cache_key(rec: Mapping) -> tuple:
    return (rec.get("step"), rec.get("prompt_sha256"), rec.get("model"), rec.get("user"), int(rec.get("reading") or 0))


def parse_role_gloss(text: Optional[str], label: str) -> tuple[Optional[dict], Optional[str]]:
    """``({"gloss", "form_ok"}, None)`` or ``(None, why)`` (``split.parse_gloss``'s one-row answer; ``form_ok``: the
    corpus form, :func:`role_gloss_form_ok`)."""
    from . import split
    row, err = split.parse_gloss(text)
    if err:
        return None, err
    return {"gloss": row["gloss"], "form_ok": role_gloss_form_ok(row["gloss"], label)}, None


def parse_role_kind(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """``({"kind", "reason"}, None)`` (``classify_role_kinds.parse_kind``: the last JSON object with a known kind,
    prose before it allowed), or ``(None, why)``."""
    if not text or not text.strip():
        return None, "empty response"
    r = _kinds().parse_kind(text)
    return (r, None) if r else (None, "no kind among the nine keys")


class _LiveTransport:
    name = "live"

    def __init__(self, runner: "StageRunner"):
        self.runner = runner

    async def execute(self, wave: str, calls: Sequence[StageCall], on_result: Callable) -> None:
        from assistant_axis.judge_pricing import BudgetExceededError
        from .llm import call_anthropic_json
        r = self.runner

        async def one(c: StageCall) -> None:
            if r.stop:
                return
            async with r.sem:
                if r.stop:
                    return
                meta: dict = {}
                try:
                    t = await call_anthropic_json(r.client, system=c.system, user=c.user, model=c.model,
                                                  max_tokens=c.max_tokens, temperature=c.temperature, usage=r.usage,
                                                  cache_system=c.cache_system, retry_delays=r.retry_delays, meta=meta)
                except BudgetExceededError as exc:
                    t = meta.get("text")
                    r.stop.append(exc)
            meta["charged_as"] = c.model if meta.get("usage_raw") else None
            on_result(c, t, meta)

        await asyncio.gather(*(one(c) for c in calls))


class StageRunner:
    """The stage's two waves (``s1_role_gloss``, ``s2_role_kind``, each followed by a retry wave for the answers that
    did not parse), sent live (``concurrency`` at a time) or through a Batches transport
    (``batches.BatchTransport(runner, client, state_path)``).  Every response is appended to ``records_path`` as it
    arrives, before it is parsed; an answer on record there (the same step, prompt, model, user turn and reading)
    is replayed instead of sent, so a resumed run pays for nothing twice.  A budget stop keeps what was paid for and
    is raised once the answers in hand are recorded."""

    def __init__(self, *, client, usage, batch_id: str, records_path: Path, model: str = MODEL,
                 concurrency: int = DEFAULT_CONCURRENCY, retry_delays: Optional[Sequence[float]] = None,
                 transport: Any = None, rubrics_dir: Optional[Path] = None, label_form: Optional[str] = None,
                 cache_ttl: Optional[str] = None):
        from .llm import RETRY_DELAYS_S
        from .prompt_labels import DEFAULT_LABEL_FORM, check_label_form
        self.client = client
        self.usage = usage
        self.batch_id = batch_id
        self.records_path = Path(records_path)
        self.model = model
        self.retry_delays = tuple(RETRY_DELAYS_S if retry_delays is None else retry_delays)
        self.concurrency = max(1, int(concurrency))
        self.rubrics_dir = rubrics_dir
        self.label_form = check_label_form(label_form or DEFAULT_LABEL_FORM)
        self.pinned = pins(rubrics_dir)
        self.transport = transport if transport is not None else _LiveTransport(self)
        self.cache_ttl = cache_ttl
        self.stop: list[BaseException] = []
        self.sem: Optional[asyncio.Semaphore] = None
        self.stats: Counter = Counter()
        self.on_record: dict[tuple, dict] = {}
        self.failed_once: Counter = Counter()
        if self.records_path.exists():
            for line in self.records_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("text") is None:
                    continue
                k = record_cache_key(rec)
                if rec.get("parse_error"):
                    self.failed_once[k] += 1
                else:
                    self.on_record[k] = rec

    # -- money (the Batches transport asks) -------------------------------------
    def estimate_usd(self, calls: Sequence[StageCall], *, batch: bool = False) -> float:
        from assistant_axis.judge_pricing import BATCH_SUFFIX, cost_for_usage
        return sum(cost_for_usage(c.model + (BATCH_SUFFIX if batch else ""), *tokens_for(c.step, c.model))
                   for c in calls)

    # -- calls ------------------------------------------------------------------
    def gloss_call(self, row: Mapping) -> StageCall:
        q = request("role_gloss", label=row["label"], reading=accepted_reading(row), model=self.model,
                    rubrics_dir=self.rubrics_dir, label_form=self.label_form)
        return StageCall(step="role_gloss", key=row["key"], label=row["label"], model=q["model"], system=q["system"],
                         user=q["user"], max_tokens=q["max_tokens"], temperature=q["temperature"],
                         cache_system=q["cache_system"], cache_ttl=self.cache_ttl if q["cache_system"] else None)

    def kind_calls(self, row: Mapping, gloss: str) -> list[StageCall]:
        q = request("role_kind", label=row["label"], gloss=gloss, model=self.model, rubrics_dir=self.rubrics_dir,
                    label_form=self.label_form)
        return [StageCall(step="role_kind", key=row["key"], label=row["label"], model=q["model"], system=q["system"],
                          user=q["user"], max_tokens=q["max_tokens"], temperature=q["temperature"],
                          cache_system=q["cache_system"], cache_ttl=self.cache_ttl if q["cache_system"] else None,
                          rep=i) for i in range(KIND_READINGS)]

    @staticmethod
    def parse(c: StageCall, text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
        return parse_role_gloss(text, c.label) if c.step == "role_gloss" else parse_role_kind(text)

    def _record(self, c: StageCall, text: Optional[str], meta: Mapping, err: Optional[str]) -> dict:
        from .registry import utc_now
        rec = {"batch_id": self.batch_id, "stage": STAGE, "step": c.step, "model": c.model, "key": c.key,
               "label": c.label, "reading": c.rep, "user": c.user, "prompt_sha256": c.prompt_sha256, "text": text,
               "stop_reason": meta.get("stop_reason"), "stop_details": meta.get("stop_details"),
               "usage_raw": meta.get("usage_raw"), "attempts": meta.get("attempts"), "error": meta.get("error"),
               "parse_error": err, "charged_as": meta.get("charged_as"), "retry": c.retry,
               "transport": getattr(self.transport, "name", "live"), "custom_id": c.custom_id,
               "batch_request_id": meta.get("batch_request_id"), "at": utc_now()}
        self.records_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.records_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    async def wave(self, wave: str, calls: Sequence[StageCall]) -> dict[int, tuple[Optional[dict], Optional[str]]]:
        """``{id(call): (parsed, error)}`` for ``calls``: answers on record replayed, the rest sent, and those whose
        answer did not parse asked once more (``<wave>_retry``).  ``error`` ``"not sent (stopped)"`` after a stop."""
        out: dict[int, tuple[Optional[dict], Optional[str]]] = {}
        todo, again = [], []
        for c in calls:
            k = c.cache_key()
            if k in self.on_record:
                self.stats["replayed"] += 1
                out[id(c)] = self.parse(c, self.on_record[k]["text"])
                if out[id(c)][0] is not None:
                    continue
            if self.failed_once[k] >= 2:
                out[id(c)] = (None, "unparsed twice (on record)")
                continue
            (again if self.failed_once[k] == 1 else todo).append(c)

        def handle(c: StageCall, text: Optional[str], meta: Mapping) -> None:
            parsed, err = self.parse(c, text)
            if text is None and err in (None, "empty response"):
                err = f"no response: {meta.get('error')}"
            if meta.get("stop_reason") == "refusal":
                err = f"refusal ({(meta.get('stop_details') or {}).get('category')})"
                parsed = None
            rec = self._record(c, text, meta, err)
            self.stats[f"sent:{c.step}"] += 1
            if err is None:
                self.stats[f"ok:{c.step}"] += 1
                self.on_record[c.cache_key()] = rec
            elif text is not None:
                self.failed_once[c.cache_key()] += 1
            out[id(c)] = (parsed, err)

        if todo and not self.stop:
            try:
                await self.transport.execute(wave, todo, handle)
            except Exception as exc:  # noqa: BLE001 - a budget stop or a transport failure: kept, raised by the caller
                self.stop.append(exc)
        retry = [c for c in todo if out.get(id(c), (None, "x"))[0] is None and id(c) in out
                 and not str(out[id(c)][1]).startswith("no response")] + again
        if retry and not self.stop:
            back = {}
            rcalls = []
            for c in retry:
                rc = StageCall(**{**c.__dict__, "retry": True})
                rcalls.append(rc)
                back[id(rc)] = c
            sub: dict[int, tuple] = {}

            def handle_retry(rc, text, meta):
                handle(rc, text, meta)
                sub[id(rc)] = out.pop(id(rc))

            try:
                await self.transport.execute(wave + "_retry", rcalls, handle_retry)
            except Exception as exc:  # noqa: BLE001
                self.stop.append(exc)
            for rc in rcalls:
                c = back[id(rc)]
                if id(rc) in sub:
                    p, e = sub[id(rc)]
                    first = out.get(id(c), (None, None))[1]
                    out[id(c)] = (p, None) if e is None else (None, f"{first}; retry: {e}" if first else e)
        for c in calls:
            out.setdefault(id(c), (None, "not sent (stopped)"))
        return out

    # -- rows -------------------------------------------------------------------
    def block(self, row: Mapping, *, gloss: Optional[dict], readings: Sequence[Optional[dict]],
              errors: Mapping[str, str], kind_errors: Sequence[Optional[str]] = ()) -> dict:
        from .registry import utc_now
        CRK = _kinds()
        g = (gloss or {}).get("gloss")
        comb = CRK.combine(list(readings)) if g else {"kind": None, "split": False, "n_parsed": 0}
        kind = comb.get("kind")
        b = {"gloss": g, "gloss_form_ok": (gloss or {}).get("form_ok") if g else None, "kind": kind,
             "kind_readings": ([dict(r) if r else {"kind": None, "error": e or "no answer"}
                                for r, e in zip(readings, list(kind_errors) + [None] * len(readings))] if g else []),
             "kind_unanimous": bool(comb.get("unanimous")) if kind else None,
             "kind_split": bool(comb.get("split")) if kind else None,
             "human": None if kind is None else kind != "non_human", "reading": accepted_reading(row),
             "model": self.model, "batch_id": self.batch_id, "step_versions": dict(self.pinned["step_versions"]),
             "prompt_sha256": dict(self.pinned["prompt_sha256"]), "label_form": self.label_form, "at": utc_now()}
        if errors:
            b["errors"] = dict(errors)
        return b

    async def run_async(self, rows: Sequence[Mapping], *, on_block: Optional[Callable[[str, dict], None]] = None
                        ) -> dict[str, dict]:
        self.sem = asyncio.Semaphore(self.concurrency)
        out: dict[str, dict] = {}
        glossed: dict[str, dict] = {}

        def emit(row, b):
            out[row["key"]] = b
            if on_block is not None:
                on_block(row["key"], b)

        need_gloss = []
        for r in rows:
            g = gloss_of(r)
            if g:                         # glossed by an earlier run, its kind failed: the kind calls only
                glossed[r["key"]] = {"gloss": g, "form_ok": role_gloss_form_ok(g, r["label"])}
            else:                         # no accepted reading: the call asks for the label's most usual sense
                need_gloss.append(r)
        calls = [self.gloss_call(r) for r in need_gloss]
        res = await self.wave("s1_role_gloss", calls)
        for r, c in zip(need_gloss, calls):
            parsed, err = res[id(c)]
            if parsed is not None:
                glossed[r["key"]] = parsed
            elif err != "not sent (stopped)" and not self.stop:
                emit(r, self.block(r, gloss=None, readings=[], errors={"role_gloss": err}))
        todo = [r for r in rows if r["key"] in glossed]
        kcalls = {r["key"]: self.kind_calls(r, glossed[r["key"]]["gloss"]) for r in todo}
        res = await self.wave("s2_role_kind", [c for cs in kcalls.values() for c in cs]) if kcalls else {}
        for r in todo:
            got = [res[id(c)] for c in kcalls[r["key"]]]
            if any(e == "not sent (stopped)" for _, e in got):
                continue                  # stopped half way: no block (the answers paid for are on record)
            readings = [p for p, _ in got]
            errs = [e for _, e in got]
            errors = {} if any(readings) else {"role_kind": "; ".join(sorted({str(e) for e in errs if e}))}
            emit(r, self.block(r, gloss=glossed[r["key"]], readings=readings, errors=errors, kind_errors=errs))
        if self.stop:
            raise self.stop[0]
        return out

    def parse_rates(self) -> dict:
        return {s: {"n": self.stats.get(f"sent:{s}", 0), "ok": self.stats.get(f"ok:{s}", 0)} for s in STEPS}

    def warn_parse_rates(self, log=None) -> None:
        from assistant_axis.judge import warn_if_low_parse_rate
        for s, d in self.parse_rates().items():
            warn_if_low_parse_rate(label=f"roles_pass:{s}:{self.model}", n_ok=d["ok"], n_total=d["n"], logger_obj=log)


async def stage_rows(rows: Sequence[Mapping], *, client, usage, batch_id: str, records_path: Path,
                     on_block: Optional[Callable[[str, dict], None]] = None, model: str = MODEL,
                     concurrency: int = DEFAULT_CONCURRENCY, retry_delays: Optional[Sequence[float]] = None,
                     rubrics_dir: Optional[Path] = None, label_form: Optional[str] = None,
                     transport_factory: Optional[Callable[["StageRunner"], Any]] = None,
                     cache_ttl: Optional[str] = None, runner_out: Optional[list] = None) -> dict[str, dict]:
    """The stage for ``rows``: the role gloss call on each row's accepted reading (a row whose block already has a
    gloss skips it), then :data:`KIND_READINGS` role kind calls on the gloss, combined by majority.  ``on_block(key,
    block)`` is called as each row finishes (the CLI writes the registry there); a row whose gloss failed (asked
    twice) gets a block with ``gloss: None`` and ``errors``; a row stopped half way by a budget stop gets none, and
    the stop is raised once the answers in hand are recorded.  ``transport_factory(runner)``: a Batches transport
    (default: live).  Returns ``{key: block}``."""
    r = StageRunner(client=client, usage=usage, batch_id=batch_id, records_path=records_path, model=model,
                    concurrency=concurrency, retry_delays=retry_delays, rubrics_dir=rubrics_dir, label_form=label_form,
                    cache_ttl=cache_ttl)
    if transport_factory is not None:
        r.transport = transport_factory(r)
    if runner_out is not None:
        runner_out.append(r)
    return await r.run_async(rows, on_block=on_block)


def run_stage_rows(rows: Sequence[Mapping], **kw) -> dict[str, dict]:
    """:func:`stage_rows` from synchronous code, the client closed inside the loop (as ``physical_pass.run_gloss_rows``)."""
    async def main() -> dict[str, dict]:
        try:
            return await stage_rows(rows, **kw)
        finally:
            close = getattr(kw.get("client"), "close", None)
            if close is not None:
                res = close()
                if asyncio.iscoroutine(res):
                    await res
    return asyncio.run(main())


def stage_summary(blocks: Mapping[str, Mapping]) -> dict:
    """Counts for ``run.json`` and the readout: rows, glossed, gloss failed, in the corpus form, kind failed, by kind,
    unanimous, split."""
    ok = [b for b in blocks.values() if b.get("gloss")]
    kinds = [b for b in ok if b.get("kind")]
    return {"n_rows": len(blocks), "n_glossed": len(ok), "n_gloss_failed": len(blocks) - len(ok),
            "n_gloss_form_ok": sum(1 for b in ok if b.get("gloss_form_ok")),
            "n_kind_failed": len(ok) - len(kinds),
            "kinds": dict(sorted(Counter(b["kind"] for b in kinds).items())),
            "n_kind_unanimous": sum(1 for b in kinds if b.get("kind_unanimous")),
            "n_kind_split": sum(1 for b in kinds if b.get("kind_split"))}


def result_line(row: Mapping, block: Mapping) -> dict:
    """One line of the run's :data:`RESULTS_NAME`: the row, its reading and the block."""
    return {"key": row["key"], "label": row["label"], "reading": accepted_reading(row), BLOCK: dict(block)}


# --------------------------------------------------------------------------- M3's candidate

class RoleCandidate(M3Candidate):
    """A role candidate as M3 reads it: cut-off 3 under every rule set (decision 4 and § 3 step 5: a sub-role is covered
    by its parent; roles have no alignment call), no alignment score, no region."""

    @property
    def cut_off(self) -> int:
        return CUT_OFF


def _gens(row: Mapping) -> list:
    return list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))


def candidate_from_row(row: Mapping):
    """``(RoleCandidate, None)`` for a role row with a role gloss, else ``(None, why)``: ``not_filtered``,
    ``not_a_role_row``, ``no_gloss``."""
    if not row.get("filter"):
        return None, "not_filtered"
    if not is_role_row(row):
        return None, "not_a_role_row"
    g = gloss_of(row)
    if g is None:
        return None, "no_gloss"
    return RoleCandidate(key=row["key"], stem=row["stem"], label=row["label"], gloss=g, alignment_score=None,
                         region=None, generators=_gens(row)), None


def provisional_candidate(row: Mapping):
    """A stand-in for a row the stage has still to gloss, for the run's plan and estimate only (never sent): its
    gloss built from the accepted reading.  Replaced by :func:`candidate_from_row` after the stage."""
    reading = accepted_reading(row) or row["label"]
    return RoleCandidate(key=row["key"], stem=row["stem"], label=row["label"],
                         gloss=f"A {row['label']} is someone who {reading}.", alignment_score=None, region=None,
                         generators=_gens(row))


# --------------------------------------------------------------------------- promotion

def source_line(source: Mapping) -> Optional[str]:
    """A registry source's provenance as a role entry's ``source`` shows it (§ 6.5): the generator's own attribution
    line when its package (``assistant_axis.gapgen.generators.<generator>``) defines ``source_line(source_ref)``
    (generator B: "O*NET 31.0 job title under 33-9032.00 (CC BY 4.0, USDOL/ETA)"), else the ``source_ref`` itself;
    None for a source with no ``source_ref``."""
    ref = source.get("source_ref")
    if not ref:
        return None
    gen = source.get("generator")
    if gen and _re.fullmatch(r"[a-z_][a-z0-9_]*", str(gen)):
        import importlib
        try:
            fn = getattr(importlib.import_module(f"assistant_axis.gapgen.generators.{gen}"), "source_line", None)
        except ImportError:
            fn = None
        if callable(fn):
            line = fn(ref)
            if line:
                return line
    return ref


def queue_entry_extras(entry: dict, rec: Mapping, queue: Mapping, *, section: Optional[str] = None) -> dict:
    """A promoted role row's queue entry (``promote.queue_entry_from_record``'s), made a role entry in place (§ 6.5):
    ``entity_type: "role"``; tags ``gap_gen``, ``source:<generator>``, ``kind:<kind>``, ``human:<bool>`` merged with
    the row's; the section of the role generators unless ``section`` is given; the role gloss as
    ``description_draft``; a ``description_notes`` line with the pass, the kind and its agreement, the nearest roles
    and traits; the generators' provenance as ``source`` (:func:`source_line`); and ``gap_gen.role_kind`` and
    ``gap_gen.holding``.  ``pairing``: ``pair`` with ``pair_by_construction: false`` when a source carries a
    ``partner_hint`` (the role-pair check decides at seeding)."""
    b = block_of(rec)
    kind = kind_of(rec)
    human = human_of(rec)
    tags = list(entry.get("tags") or [])
    tags += [t for t in (f"kind:{kind}" if kind else None, f"human:{str(human).lower()}" if human is not None else None)
             if t]
    entry["entity_type"] = "role"
    entry["tags"] = list(dict.fromkeys(tags))
    entry["section"] = section or SECTION
    entry["description_draft"] = gloss_of(rec) or entry.get("description_draft")
    nv = rec.get("novelty") or {}
    readings = b.get("kind_readings") or []
    n_agree = sum(1 for r in readings if (r or {}).get("kind") == kind)
    near_roles = ", ".join(f"{x['stem']} {x.get('cosine')}" + (f" ({x.get('relation')})" if x.get("relation") else "")
                           for x in (nv.get("listed") or [])[:3] if x.get("stem"))
    near_traits = ", ".join(f"{x['stem']} {x.get('cosine')}"
                            for x in ((nv.get("cross_type") or {}).get("traits") or [])[:3] if x.get("stem"))
    note = (f"role pass {nv.get('run_id') or b.get('batch_id')} | kind {kind} ({n_agree} of {len(readings)})"
            + (f" | nearest roles: {near_roles}" if near_roles else "")
            + (f" | nearest traits: {near_traits}" if near_traits else ""))
    entry["description_notes"] = " | ".join(x for x in (note, entry.get("description_notes")) if x)
    lines = [source_line(s) for s in rec.get("sources") or []]
    if any(lines) and not entry.get("source"):
        entry["source"] = "; ".join(dict.fromkeys(x for x in lines if x))
    partner = next((s.get("partner_hint") for s in rec.get("sources") or [] if s.get("partner_hint")), None)
    if partner and not entry.get("partner"):
        from assistant_axis.entity_id import normalize_to_file_name
        entry.update(pairing="pair", partner=normalize_to_file_name(partner), partner_exists=None,
                     pair_by_construction=False)
    gg = entry.setdefault("gap_gen", {})
    gg["holding"] = rec.get("holding")
    gg["role_kind"] = {"kind": kind, "unanimous": b.get("kind_unanimous"), "split": b.get("kind_split"),
                       "readings": [(r or {}).get("kind") for r in readings], "batch_id": b.get("batch_id"),
                       "prompt_sha256": ((b.get("prompt_sha256") or {}).get("role_kind") or "")[:16] or None,
                       "model": b.get("model")}
    return entry


# --------------------------------------------------------------------------- the retrieval check (§ 7b, decision 11)

#: The production query form and space of the role index, and the acceptance line (decision 11; Roger's decision 3
#: of 2026-10-22: the label-stripped form against 95%, the label-kept form reported beside it).
PRODUCTION_ARM = ("role_gloss_w14", "centred")
RECALL_TARGET = 0.95
RECALL_K = 10
#: The arms tried, on the same glosses at no new call, only when the production arm falls below the target; the
#: label-kept form is information, never chosen.
ARMS = (("role_gloss_w20", "centred"), ("role_gloss_w14", "raw"), ("role_gloss_w20", "raw"))
INFO_FORMS = (("label_gloss", "centred"),)


def rank_of(index, q_raw, stem: str) -> int:
    """The 1-based rank of ``stem`` among ``index``'s rows for the raw query ``q_raw`` (projected into the index's
    space): one more than the number of rows strictly closer (a tie does not push it down)."""
    q = index.project(q_raw)
    sims = index.cosines(q)
    own = index.cosine_to(q, stem)
    if own is None:
        raise KeyError(f"{stem} is not in the index")
    return 1 + int((sims > own + 1e-12).sum())


def recall_summary(ranks: Mapping[str, int], *, kinds: Mapping[str, Optional[str]], k: int = RECALL_K) -> dict:
    """``{"n", "recall_at_k", "mrr", "by_kind": {kind: {"n", "recall_at_k"}}, "n_missed"}`` over ``ranks`` (stem ->
    rank)."""
    n = len(ranks)
    hits = {s: r <= k for s, r in ranks.items()}
    by: dict[str, list] = {}
    for s in ranks:
        by.setdefault(kinds.get(s) or "unknown", []).append(hits[s])
    return {"n": n, "k": k, "recall_at_k": round(sum(hits.values()) / n, 4) if n else None,
            "mrr": round(sum(1.0 / r for r in ranks.values()) / n, 4) if n else None,
            "n_missed": sum(1 for h in hits.values() if not h),
            "by_kind": {kd: {"n": len(v), "recall_at_k": round(sum(v) / len(v), 4)} for kd, v in sorted(by.items())}}


def choose_arm(results: Mapping[tuple, Mapping], *, target: float = RECALL_TARGET) -> dict:
    """The role setting the check gives (decision 11): the production arm when it reaches ``target``; else the best
    of the production arm and :data:`ARMS` evaluated (by recall at k, then MRR; the production arm wins a tie, so
    the settings change only for a better arm).  ``{"query_form", "variant", "recall_at_k", "mrr", "changed",
    "reached_target"}``."""
    prod = results[PRODUCTION_ARM]
    if prod["recall_at_k"] is not None and prod["recall_at_k"] >= target:
        best = PRODUCTION_ARM
    else:
        cands = [PRODUCTION_ARM] + [a for a in ARMS if a in results]
        best = max(cands, key=lambda a: (results[a]["recall_at_k"] or 0.0, results[a]["mrr"] or 0.0,
                                         a == PRODUCTION_ARM))
    r = results[best]
    return {"query_form": best[0], "variant": best[1], "recall_at_k": r["recall_at_k"], "mrr": r["mrr"],
            "changed": best != PRODUCTION_ARM, "reached_target": (r["recall_at_k"] or 0.0) >= target}


# --------------------------------------------------------------------------- the rubric check (§ 8, task 12)

#: The 40 role pairs Roger marks before the pilot's first overlap call (idea plan § 10; coding plan § 8): the six
#: recorded pairs of the role corpus, ten sub-role / parent pairs (the sub-role is the target, line 3's direction),
#: ten near-synonym pairs that may be one role under two names, and fourteen others (neighbours, counterparts and
#: unrelated roles).  All are corpus roles, so the sheet shows the corpus files' descriptions (no gloss is needed
#: before the check; the role gloss call's glosses can stand in for the targets' with ``--glosses``).  ``set`` is the
#: design's category, kept out of the sheet so that the marks are blind to it.
RUBRIC_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("angel", "demon", "recorded_pair"), ("cosmopolitan", "provincial", "recorded_pair"),
    ("destroyer", "guardian", "recorded_pair"), ("paperclip_maximizer", "instrumentally_aligned_ai", "recorded_pair"),
    ("parasite", "symbiont", "recorded_pair"), ("prey", "predator", "recorded_pair"),
    ("physicist", "scientist", "sub_role"), ("chemist", "scientist", "sub_role"), ("biologist", "scientist", "sub_role"),
    ("novelist", "writer", "sub_role"), ("poet", "writer", "sub_role"), ("playwright", "writer", "sub_role"),
    ("reporter", "journalist", "sub_role"), ("toddler", "child", "sub_role"), ("infant", "child", "sub_role"),
    ("grandparent_caregiver", "caregiver", "sub_role"),
    ("instructor", "teacher", "same_role"), ("trainer", "coach", "same_role"), ("counselor", "therapist", "same_role"),
    ("reviewer", "critic", "same_role"), ("examiner", "evaluator", "same_role"), ("wanderer", "nomad", "same_role"),
    ("secretary", "assistant", "same_role"), ("loner", "hermit", "same_role"), ("pauper", "beggar", "same_role"),
    ("translator", "interpreter", "same_role"),
    ("judge", "lawyer", "other"), ("detective", "criminal", "other"), ("student", "teacher", "other"),
    ("patient", "doctor", "other"), ("veteran", "soldier", "other"), ("sommelier", "chef", "other"),
    ("herder", "farmer", "other"), ("navigator", "pilot", "other"), ("archivist", "librarian", "other"),
    ("smuggler", "pirate", "other"), ("farmer", "doctor", "other"), ("mechanic", "poet", "other"),
    ("accountant", "witch", "other"), ("tree", "robot", "other"))
#: The marks the sheet takes: the overlap rubric's answers.
MARKS = ("0", "1", "2", "3", "4", "opposite", "unsure")
KAPPA_TARGET = 0.6


def relation_of_mark(mark) -> Optional[str]:
    """A mark on the overlap scale as the relation call's answer: 2-4 ``similar``, 0-1 ``unrelated``, ``opposite``
    ``opposed``; ``unsure`` and anything else None."""
    m = str(mark).strip().lower()
    if m in ("2", "3", "4"):
        return "similar"
    if m in ("0", "1"):
        return "unrelated"
    if m == "opposite":
        return "opposed"
    return None


def weighted_kappa(a: Sequence[int], b: Sequence[int], *, categories: Sequence[int] = (0, 1, 2, 3, 4),
                   weights: str = "quadratic") -> Optional[float]:
    """Cohen's weighted kappa of two raters' ordinal answers (``quadratic`` or ``linear`` weights; ``none``: the
    unweighted kappa).  None for no pair, or when the expected disagreement is zero."""
    cats = list(categories)
    k = len(cats)
    if not a or len(a) != len(b):
        return None
    ix = {c: i for i, c in enumerate(cats)}
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[ix[x]][ix[y]] += 1
    n = float(len(a))
    ra = [sum(obs[i]) / n for i in range(k)]
    rb = [sum(obs[i][j] for i in range(k)) / n for j in range(k)]

    def w(i, j):
        if weights == "none":
            return 0.0 if i == j else 1.0
        d = abs(i - j) / max(1, k - 1)
        return d * d if weights == "quadratic" else d
    num = sum(w(i, j) * obs[i][j] / n for i in range(k) for j in range(k))
    den = sum(w(i, j) * ra[i] * rb[j] for i in range(k) for j in range(k))
    return None if den == 0 else round(1.0 - num / den, 4)
