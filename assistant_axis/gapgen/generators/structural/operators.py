"""Generator B: the five structural operators on the corpus's traits (plan sections 5-7; tasks 4, 5, 7 and 10).

**The call** (rubric ``structural_operators``, pinned; Haiku 5.5, no temperature): one call per trait.  The user
turn (:func:`render_operator_user`) is one JSON object: the trait's label in the judge display form, its
``description``, its arrangement **kind** (``pair``, ``triangle``, ``sequence``, ``singleton``, ``unclassified``,
...) and the targets to consider.  It never carries the trait's ``negative_label`` or its arrangement's members:
:class:`TraitInput` has no field for either, so the opposite runs blind (plan section 1; QUESTIONS, pre-registered
entry 1).  The answer, reasoning first: ``position`` (``deficiency`` | ``mean`` | ``excess`` | ``not_scalar``),
``opposite``, ``excess``, ``deficiency``, ``retarget`` (one entry per listed target) and ``remode`` (``attitude``,
``habit``, ``speech``); each an item ``{label, gloss, has_common_word, polysemy}`` or ``null``.

**Principal targets, staged** (Roger, 2026-10-13): the user, the operator and the developer are listed only for a
trait whose ``alignment_score`` in ``corpus_regions.json`` is at least ``principal_min_score`` (default
:data:`PRINCIPAL_MIN_SCORE`, 3: stage 1, 108 traits).  A later stage (score 2, then 1) runs on Roger's word with
``principal_only``: the call lists only the three principal targets with ``"answer_only": "retarget"``, for the
traits the lower score newly includes (traits already answered with principal targets are skipped,
:func:`already_principal`).  **The guard** checks both ways: :func:`check_principal` refuses an input that lists the
principal targets for a trait below the score, and :func:`parse_operator_reply` drops (with a problem recorded) any
principal-target answer for a trait the call did not list them for.

**Items** (:func:`validate_item`): a label of one to four words, ASCII, no underscore, not the trait itself, and not
a degree form (``too X``, ``overly X``, ``not X``, ``over-X``, ``under-X``, ``non-X``, or ``overX`` / ``underX`` /
``nonX`` built on the trait's own word); a gloss.  A rejected item is dropped and counted (``rejected``), never
guessed; a gloss that does not start "This means" or runs past 25 words is noted, not rejected.  ``null`` is
accepted for every slot but ``reasoning`` and ``position``; a reply without a string ``reasoning`` or a legal
``position`` does not parse and is asked once more; a second failure leaves the trait unanswered.

**Records**: every response is appended to the run's ``responses.jsonl`` *before* it is parsed (the Roget precedent,
QUESTIONS 37), with the trait stem, the prompt's sha256 (system and user turn), the model, the billed usage and the
model it was charged as; a ``--resume`` reuses a recorded answer to the same (stem, prompt sha256, model) that
parses, so a changed prompt is sent again and an unchanged one is not.  Every response is charged, including the
ones that do not parse.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, prompt_label
from assistant_axis.judge import extract_json_blob
from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage

from . import SCHEMA_VERSION

OPERATORS: tuple[str, ...] = ("opposite", "excess", "deficiency", "retarget", "remode")
#: The operators that answer with one item (``retarget`` and ``remode`` answer one per target or mode).
SINGLE_OPERATORS: tuple[str, ...] = ("opposite", "excess", "deficiency")
TARGETS: tuple[str, ...] = ("self", "intimates", "strangers", "authority", "animals", "ideas")
PRINCIPAL_TARGETS: tuple[str, ...] = ("the_user", "the_operator", "the_developer")
MODES: tuple[str, ...] = ("attitude", "habit", "speech")
POSITIONS: tuple[str, ...] = ("deficiency", "mean", "excess", "not_scalar")
#: Stage 1 of the principal targets (Roger, 2026-10-13): the 108 traits at alignment score 3.  Stages 2 (score 2,
#: 75 traits) and 3 (score 1, 317) run only on his word after stage 1's yield.
PRINCIPAL_MIN_SCORE = 3
MODEL = "claude-haiku-5-5"
#: Haiku 5.5 thinks adaptively and its thinking counts against max_tokens (the IPIP naming call uses 4,000 for a
#: ~150-token answer); this answer is about 550 tokens.
MAX_TOKENS = 6000
CONCURRENCY = 8
MAX_LABEL_WORDS = 4
MAX_GLOSS_WORDS = 25
CHARS_PER_TOKEN = 4.0
#: Output tokens a call for the estimate (the plan's figure; the null-rate pilot measures it): +200 for a trait with
#: the principal targets, 250 for a principal-only call.
EST_OUT_TOKENS = 550
EST_OUT_PRINCIPAL_EXTRA = 200
EST_OUT_PRINCIPAL_ONLY = 250
STAGE = "operators"

#: A first word that makes a label a degree phrase, not a name.
_DEGREE_FIRST = frozenset({"too", "overly", "excessively", "insufficiently", "not", "non", "over", "under",
                           "hardly", "barely"})
_HYPHEN_PREFIXES = ("over-", "under-", "non-")
_BARE_PREFIXES = ("over", "under", "non")
_WORDS_RE = re.compile(r"[a-z]+")


# --------------------------------------------------------------------------- inputs

@dataclass(frozen=True)
class TraitInput:
    """What one call is told about a trait: never its ``negative_label`` and never its arrangement's members."""
    stem: str
    label: str
    description: str
    arrangement_kind: str
    region: Optional[str]
    alignment_score: Optional[int]
    principal_targets: bool
    principal_only: bool = False

    def targets(self) -> tuple[str, ...]:
        if self.principal_only:
            return PRINCIPAL_TARGETS
        return TARGETS + (PRINCIPAL_TARGETS if self.principal_targets else ())


def arrangement_kinds(field_value) -> str:
    """The kind(s) of a trait file's ``arrangement`` field, comma-joined in field order (``pair, 5-orthoplex``);
    ``unclassified`` for a missing or malformed field."""
    from assistant_axis.arrangements import ArrangementError, parse_field
    if field_value is None:
        return "unclassified"
    try:
        arrs = parse_field(field_value)
    except ArrangementError:
        return "unclassified"
    kinds = list(dict.fromkeys(a.kind for a in arrs))
    return ", ".join(kinds) if kinds else "unclassified"


def load_regions(regions_path: Optional[Path]) -> dict:
    """``corpus_regions.json``'s rows by stem (the envelope read through); empty when absent."""
    if regions_path is None or not Path(regions_path).exists():
        return {}
    d = json.loads(Path(regions_path).read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) else {}


def is_principal(alignment_score: Optional[int], principal_min_score: int = PRINCIPAL_MIN_SCORE) -> bool:
    return alignment_score is not None and int(alignment_score) >= int(principal_min_score)


def build_inputs(stems: Optional[Iterable[str]] = None, *, data_dir: Path, regions_path: Optional[Path],
                 principal_min_score: int = PRINCIPAL_MIN_SCORE, principal_only: bool = False) -> list[TraitInput]:
    """One :class:`TraitInput` per trait file (``stems`` None: every file, in stem order).  The label is the file's
    ``positive_label`` as stored (the prompt shows its judge display form); region and alignment score come from
    ``regions_path``.  ``principal_only`` keeps only the traits that get the principal targets."""
    tdir = Path(data_dir) / "traits" / "instructions"
    want = sorted(p.stem for p in tdir.glob("*.json")) if stems is None else list(dict.fromkeys(stems))
    regions = load_regions(regions_path)
    out = []
    for stem in want:
        p = tdir / f"{stem}.json"
        if not p.exists():
            raise FileNotFoundError(f"no trait file {p}")
        doc = json.loads(p.read_text(encoding="utf-8"))
        reg = regions.get(stem) or {}
        score = reg.get("alignment_score")
        principal = is_principal(score, principal_min_score)
        if principal_only and not principal:
            continue
        out.append(TraitInput(stem=stem, label=str(doc.get("positive_label") or stem.replace("_", " ")),
                              description=str(doc.get("description") or ""),
                              arrangement_kind=arrangement_kinds(doc.get("arrangement")),
                              region=reg.get("region"), alignment_score=None if score is None else int(score),
                              principal_targets=principal, principal_only=bool(principal_only)))
    return out


def check_principal(ti: TraitInput, principal_min_score: int = PRINCIPAL_MIN_SCORE) -> None:
    """The guard on the way in: a trait below ``principal_min_score`` must not list the principal targets."""
    if (ti.principal_targets or ti.principal_only) and not is_principal(ti.alignment_score, principal_min_score):
        raise ValueError(f"{ti.stem}: principal targets listed for a trait at alignment score {ti.alignment_score}, "
                         f"below --principal-min-score {principal_min_score} (the guard)")
    if ti.principal_only and not ti.principal_targets:
        raise ValueError(f"{ti.stem}: principal-only call for a trait without the principal targets")


def render_operator_user(ti: TraitInput, *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The user turn: one JSON object (the label in the judge display form; never the negative label or the
    members)."""
    obj = {"trait": prompt_label(ti.label, label_form), "description": ti.description,
           "arrangement": ti.arrangement_kind, "retarget_toward": list(ti.targets())}
    if ti.principal_only:
        obj["answer_only"] = "retarget"
    return json.dumps(obj, ensure_ascii=False)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_sha256(system: str, user: str) -> str:
    """The prompt's identity for resuming: the system and the user turn together."""
    return sha256(system + "\n\x00\n" + user)


# --------------------------------------------------------------------------- items and replies

def _source_words(label: Optional[str], stem: Optional[str]) -> set[str]:
    out: set[str] = set()
    for s in (label, stem):
        if s:
            out.update(w for w in _WORDS_RE.findall(str(s).lower().replace("_", " ")) if len(w) >= 3)
    return out


def degree_form(label: str, *, source_label: Optional[str] = None, source_stem: Optional[str] = None
                ) -> Optional[str]:
    """Why ``label`` is a degree form rather than a name (``too X``, ``over-X``, ``non-X``, ``overX`` on the trait's
    own word), or None."""
    words = label.lower().split()
    if not words:
        return None
    if words[0] in _DEGREE_FIRST:
        return f"degree word {words[0]!r}"
    src = _source_words(source_label, source_stem)
    for w in words:
        for pre in _HYPHEN_PREFIXES:
            if w.startswith(pre) and len(w) > len(pre):
                return f"{pre}X form"
        for pre in _BARE_PREFIXES:
            rest = w[len(pre):]
            if w.startswith(pre) and len(rest) >= 3 and rest.strip("-") in src:
                return f"{pre}X form on the trait's own word"
    return None


def label_problem(label, *, source_label: Optional[str] = None, source_stem: Optional[str] = None
                  ) -> Optional[str]:
    """Why ``label`` cannot be a candidate's name (one to four words, ASCII, no underscore, not a degree form, not
    the source trait itself), or None.  Shared by both calls."""
    if not isinstance(label, str) or not label.strip():
        return "no label"
    label = " ".join(label.split())
    if not label.isascii():
        return "non-ASCII"
    if "_" in label:
        return "underscore"
    n = len(label.split())
    if n > MAX_LABEL_WORDS:
        return f"{n} words (at most {MAX_LABEL_WORDS})"
    deg = degree_form(label, source_label=source_label, source_stem=source_stem)
    if deg:
        return f"over-/under-/too-/non-X: {deg}"
    try:
        stem = normalize_candidate(label).stem
    except ValueError:
        return "does not normalise"
    if source_stem and stem == source_stem:
        return "the trait itself"
    return None


def validate_item(d, *, source_label: Optional[str] = None, source_stem: Optional[str] = None
                  ) -> tuple[Optional[dict], Optional[str]]:
    """``(item, None)`` for a usable item, else ``(None, why)`` (module docstring).  The item is
    ``{label, gloss, has_common_word, polysemy}`` plus ``notes`` when its gloss is noted."""
    if not isinstance(d, dict):
        return None, "not an object"
    why = label_problem(d.get("label"), source_label=source_label, source_stem=source_stem)
    if why:
        return None, why
    label = " ".join(d["label"].split())
    gloss = d.get("gloss")
    if not isinstance(gloss, str) or not gloss.strip():
        return None, "no gloss"
    gloss = " ".join(gloss.split())
    notes = []
    if not gloss.startswith("This means"):
        notes.append("gloss does not start 'This means'")
    if len(gloss.split()) > MAX_GLOSS_WORDS:
        notes.append(f"gloss {len(gloss.split())} words")
    item = {"label": label, "gloss": gloss,
            "has_common_word": d.get("has_common_word") if isinstance(d.get("has_common_word"), bool) else None,
            "polysemy": d.get("polysemy") if isinstance(d.get("polysemy"), bool) else None}
    if notes:
        item["notes"] = notes
    return item, None


@dataclass
class OperatorReply:
    """One trait's parsed answer (``stem``, ``label`` and the run fields are set by the caller)."""
    reasoning: str
    position: Optional[str]
    opposite: Optional[dict] = None
    excess: Optional[dict] = None
    deficiency: Optional[dict] = None
    retarget: dict = field(default_factory=dict)
    remode: dict = field(default_factory=dict)
    principal: bool = False
    principal_only: bool = False
    problems: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    stem: str = ""
    label: str = ""
    run_id: Optional[str] = None
    model: Optional[str] = None
    prompt_sha256: Optional[str] = None
    at: Optional[str] = None

    def items(self) -> list[tuple[str, Optional[str], dict]]:
        """``(operator, target or mode or None, item)`` for every non-null answer, in operator order."""
        out = []
        for op in SINGLE_OPERATORS:
            it = getattr(self, op)
            if it:
                out.append((op, None, it))
        for t in (*TARGETS, *PRINCIPAL_TARGETS):
            if self.retarget.get(t):
                out.append(("retarget", t, self.retarget[t]))
        for m in MODES:
            if self.remode.get(m):
                out.append(("remode", m, self.remode[m]))
        return out

    def as_dict(self) -> dict:
        return asdict(self)


def _slot(raw, *, name: str, source_label, source_stem, rep: OperatorReply) -> Optional[dict]:
    if raw is None:
        return None
    item, why = validate_item(raw, source_label=source_label, source_stem=source_stem)
    if item is None:
        lab = raw.get("label") if isinstance(raw, dict) else None
        rep.rejected.append({"slot": name, "label": lab, "why": why})
        rep.problems.append(f"{name}: dropped ({why})")
    return item


def parse_operator_reply(text: Optional[str], *, principal: bool, principal_only: bool = False,
                         source_label: Optional[str] = None, source_stem: Optional[str] = None
                         ) -> tuple[Optional[OperatorReply], Optional[str]]:
    """``(reply, None)``, or ``(None, why)`` when the text does not parse (module docstring).  ``principal``: the
    call listed the principal targets; an answer naming one when it did not is dropped (the guard)."""
    if text is None:
        return None, "no response"
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        d = None
    if not isinstance(d, dict):
        return None, "unparseable"
    reasoning = d.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        return None, "no reasoning"
    position = d.get("position")
    if not principal_only and position not in POSITIONS:
        return None, f"position {position!r}"
    rep = OperatorReply(reasoning=reasoning.strip(), position=None if principal_only else position,
                        principal=bool(principal or principal_only), principal_only=bool(principal_only))
    kw = {"source_label": source_label, "source_stem": source_stem, "rep": rep}
    if not principal_only:
        for op in SINGLE_OPERATORS:
            setattr(rep, op, _slot(d.get(op), name=op, **kw))
    asked = PRINCIPAL_TARGETS if principal_only else TARGETS + (PRINCIPAL_TARGETS if principal else ())
    rt = d.get("retarget")
    rep.retarget = {t: None for t in asked}
    if isinstance(rt, dict):
        for k, v in rt.items():
            if k in asked:
                rep.retarget[k] = _slot(v, name=f"retarget:{k}", **kw)
            elif k in PRINCIPAL_TARGETS:
                if v is not None:
                    lab = v.get("label") if isinstance(v, dict) else None
                    rep.rejected.append({"slot": f"retarget:{k}", "label": lab, "why": "guard"})
                    rep.problems.append(f"retarget:{k}: dropped (principal target for a trait not listed for it; "
                                        f"the guard)")
            elif v is not None:
                rep.problems.append(f"retarget: unknown target {k!r} dropped")
        for t in asked:
            if t not in rt:
                rep.problems.append(f"retarget: target {t!r} missing (taken as null)")
    elif rt is not None:
        rep.problems.append("retarget is not an object (taken as null)")
    rep.remode = {m: None for m in MODES} if not principal_only else {}
    rm = d.get("remode")
    if not principal_only:
        if isinstance(rm, dict):
            for k, v in rm.items():
                if k in MODES:
                    rep.remode[k] = _slot(v, name=f"remode:{k}", **kw)
                elif v is not None:
                    rep.problems.append(f"remode: unknown mode {k!r} dropped")
        elif rm is not None:
            rep.problems.append("remode is not an object (taken as null)")
    return rep, None


# --------------------------------------------------------------------------- the calls

@dataclass
class OperatorRun:
    replies: dict = field(default_factory=dict)        # stem -> OperatorReply
    errors: dict = field(default_factory=dict)         # stem -> why there is no answer
    records: list = field(default_factory=list)
    n_calls: int = 0
    n_reused: int = 0
    n_attempted: int = 0
    stopped_by_budget: bool = False

    @property
    def n_ok(self) -> int:
        return len(self.replies) - self.n_reused


def read_responses(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def append_response(rec: Mapping, path: Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def reply_from_record(rec: Mapping) -> tuple[Optional[OperatorReply], Optional[str]]:
    """A recorded answer parsed again (the record holds the text as received)."""
    if rec.get("stage") != STAGE:
        return None, "not an operators record"
    rep, why = parse_operator_reply(rec.get("text"), principal=bool(rec.get("principal_targets")),
                                    principal_only=bool(rec.get("principal_only")),
                                    source_label=rec.get("label"), source_stem=rec.get("stem"))
    if rep is not None:
        rep.stem, rep.label = rec.get("stem") or "", rec.get("label") or ""
        rep.run_id, rep.model = rec.get("run_id"), rec.get("model")
        rep.prompt_sha256, rep.at = rec.get("prompt_sha256"), rec.get("at")
    return rep, why


def reusable(records: Iterable[Mapping], *, model: str, prompts: Mapping[str, str]) -> dict:
    """``{stem: reply}`` for the recorded answers that parse, to the same stem, prompt sha256 and model (the last
    one per stem winning)."""
    out = {}
    for r in records:
        if r.get("stage") == STAGE and r.get("model") == model and prompts.get(r.get("stem")) == r.get("prompt_sha256"):
            rep, _ = reply_from_record(r)
            if rep is not None:
                out[r["stem"]] = rep
    return out


def already_principal(records: Iterable[Mapping]) -> set[str]:
    """Stems with a recorded answer that parses and listed the principal targets (a stage already run)."""
    out = set()
    for r in records:
        if r.get("stage") == STAGE and (r.get("principal_targets") or r.get("principal_only")):
            rep, _ = reply_from_record(r)
            if rep is not None:
                out.add(r["stem"])
    return out


async def run_operators(inputs: Sequence[TraitInput], *, client, model: str, usage, system: str, run_id: str,
                        out_path: Optional[Path] = None, resume: bool = False, rubric_version: Optional[int] = None,
                        principal_min_score: int = PRINCIPAL_MIN_SCORE, label_form: str = DEFAULT_LABEL_FORM,
                        concurrency: int = CONCURRENCY, max_tokens: int = MAX_TOKENS,
                        now: Optional[Callable[[], str]] = None) -> OperatorRun:
    """One call per trait (module docstring): every response appended to ``out_path`` before it is parsed, a reply
    that does not parse asked once more, ``resume`` reusing recorded answers to the same prompt and model.  A
    ``BudgetExceededError`` keeps the answer that crossed the cap and stops the run."""
    for ti in inputs:
        check_principal(ti, principal_min_score)
    res = OperatorRun()
    users = {ti.stem: render_operator_user(ti, label_form=label_form) for ti in inputs}
    prompts = {s: prompt_sha256(system, u) for s, u in users.items()}
    if resume and out_path is not None:
        done = reusable(read_responses(out_path), model=model, prompts=prompts)
        res.replies.update(done)
        res.n_reused = len(done)
    todo = [ti for ti in inputs if ti.stem not in res.replies]
    sem = asyncio.Semaphore(max(1, concurrency))
    sys_sha = sha256(system)

    async def one(ti: TraitInput, attempt: int) -> tuple[Optional[OperatorReply], Optional[str]]:
        meta: dict = {}
        over = False
        try:
            text = await call_anthropic_json(client, system=system, user=users[ti.stem], model=model,
                                             max_tokens=max_tokens, temperature=None, usage=usage, cache_system=True,
                                             meta=meta)
        except BudgetExceededError:
            text, over = meta.get("text"), True
        res.n_calls += 1
        rec = {"schema_version": SCHEMA_VERSION, "stage": STAGE, "run_id": run_id, "stem": ti.stem, "label": ti.label,
               "attempt": attempt, "model": model, "rubric": "structural_operators", "rubric_version": rubric_version,
               "system_sha256": sys_sha, "user_sha256": sha256(users[ti.stem]), "prompt_sha256": prompts[ti.stem],
               "principal_targets": ti.principal_targets, "principal_only": ti.principal_only,
               "alignment_score": ti.alignment_score, "principal_min_score": principal_min_score,
               "label_form": label_form, "at": now() if now else None, "user": users[ti.stem], "text": text,
               "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
               "charged_as": model if meta.get("usage_raw") else None, "error": meta.get("error")}
        if out_path is not None:
            append_response(rec, out_path)          # recorded before it is parsed
        res.records.append(rec)
        if over:
            res.stopped_by_budget = True
        rep, why = reply_from_record(rec)
        return rep, why

    async def run_one(ti: TraitInput) -> None:
        async with sem:
            if res.stopped_by_budget:
                return
            res.n_attempted += 1
            rep, why = await one(ti, 1)
            if rep is None and not res.stopped_by_budget:
                rep, why = await one(ti, 2)
            if rep is not None:
                res.replies[ti.stem] = rep
            else:
                res.errors[ti.stem] = why

    await asyncio.gather(*(run_one(ti) for ti in todo))
    res.records.sort(key=lambda r: (r["stem"], r["attempt"]))
    return res


# --------------------------------------------------------------------------- estimate and samples

def estimate(inputs: Sequence[TraitInput], system: str, model: str = MODEL, *,
             label_form: str = DEFAULT_LABEL_FORM) -> dict:
    """``{"n_calls", "in_tok", "out_tok", "usd"}``: input from the characters sent, output at
    :data:`EST_OUT_TOKENS` a call (+:data:`EST_OUT_PRINCIPAL_EXTRA` for a principal-target trait,
    :data:`EST_OUT_PRINCIPAL_ONLY` for a principal-only call); no cache hit assumed."""
    if not inputs:
        return {"n_calls": 0, "in_tok": 0, "out_tok": 0, "usd": 0.0}
    in_tok = int(round(sum((len(system) + len(render_operator_user(ti, label_form=label_form))) / CHARS_PER_TOKEN
                           for ti in inputs)))
    out_tok = sum(EST_OUT_PRINCIPAL_ONLY if ti.principal_only else
                  EST_OUT_TOKENS + (EST_OUT_PRINCIPAL_EXTRA if ti.principal_targets else 0) for ti in inputs)
    return {"n_calls": len(inputs), "in_tok": in_tok, "out_tok": out_tok,
            "usd": round(cost_for_usage(model, in_tok, out_tok), 4)}


def _stratum(ti: TraitInput) -> tuple[str, str]:
    return (str(ti.region), ti.arrangement_kind.split(",")[0].strip())


def stratified_sample(inputs: Sequence[TraitInput], n: int, seed: int, *, pairs: Sequence[tuple[str, str]] = (),
                      n_pairs: int = 0, min_principal: int = 0) -> list[TraitInput]:
    """``n`` traits, seeded: ``n_pairs`` whole recorded pairs first (both poles, so the readout can read where two
    poles land), the rest drawn per (region, first arrangement kind) stratum in proportion to its size (largest
    remainders), then non-principal picks swapped for principal-target traits until ``min_principal`` are in.
    Returned in input order."""
    by = {ti.stem: ti for ti in inputs}
    if n >= len(inputs):
        return list(inputs)
    rng = random.Random(f"structural:{seed}")
    chosen: list[str] = []
    pool_pairs = sorted({tuple(sorted(p)) for p in pairs if p[0] in by and p[1] in by})
    for a, b in rng.sample(pool_pairs, min(n_pairs, len(pool_pairs), n // 2)):
        chosen += [a, b]
    rest = [ti for ti in inputs if ti.stem not in set(chosen)]
    k = n - len(chosen)
    strata: dict[tuple, list[TraitInput]] = {}
    for ti in rest:
        strata.setdefault(_stratum(ti), []).append(ti)
    raw = {key: k * len(v) / len(rest) for key, v in strata.items()}
    quota = {key: int(x) for key, x in raw.items()}
    for key in sorted(raw, key=lambda key: (-(raw[key] - quota[key]), key))[: k - sum(quota.values())]:
        quota[key] += 1
    drawn: list[str] = []
    for key in sorted(strata):
        if quota[key]:
            drawn += [ti.stem for ti in random.Random(f"structural:{seed}:{key}").sample(strata[key], quota[key])]
    picked = chosen + drawn
    n_pr = sum(1 for s in picked if by[s].principal_targets)
    if n_pr < min_principal:
        extra = [ti.stem for ti in inputs if ti.principal_targets and ti.stem not in set(picked)]
        rng.shuffle(extra)
        swappable = [s for s in reversed(drawn) if not by[s].principal_targets]
        for new in extra[: min_principal - n_pr]:
            if not swappable:
                break
            old = swappable.pop(0)
            picked[picked.index(old)] = new
    keep = set(picked)
    return [ti for ti in inputs if ti.stem in keep]


def rejection_counts(replies: Iterable[OperatorReply]) -> dict:
    """``{why: n}`` over every rejected item, with the over-/under-/too-/non-X rejections under one key."""
    c: Counter = Counter()
    for r in replies:
        for x in r.rejected:
            why = str(x.get("why"))
            c["over-/under-/too-/non-X" if why.startswith("over-/under-/too-/non-X") else why.split(" (")[0]] += 1
    return dict(sorted(c.items()))


__all__ = ["OPERATORS", "SINGLE_OPERATORS", "TARGETS", "PRINCIPAL_TARGETS", "MODES", "POSITIONS",
           "PRINCIPAL_MIN_SCORE", "MODEL", "MAX_TOKENS", "TraitInput", "OperatorReply", "OperatorRun",
           "arrangement_kinds", "load_regions", "is_principal", "build_inputs", "check_principal",
           "render_operator_user", "prompt_sha256", "degree_form", "label_problem", "validate_item", "parse_operator_reply",
           "read_responses", "append_response", "reply_from_record", "reusable", "already_principal",
           "run_operators", "estimate", "stratified_sample", "rejection_counts"]
