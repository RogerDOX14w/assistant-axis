"""The lay-role call (rubric ``profession_lay``; coding plan 16, § 5b and § 7a.5).

One call per table row: a SOC broad group with its detailed O*NET occupations and their descriptions, or one
selected job title under its occupation (an ``alternate_title`` on the group), or (wave 2) an ESCO group.  The user
turn is one JSON object (:func:`build_user`): ``"group"`` (code, title, and for a job title its
``alternate_title``), then ``"occupations"``, numbered 1, 2, 3 ... in the order listed, one a line.  The group's
employment is not shown, so the answer is independent of the ranking.

**The call.**  Haiku 5.5, no temperature (it refuses one), ``max_tokens`` :data:`MAX_TOKENS` (it thinks adaptively,
and the thinking counts against it), the system prompt (the pinned rubric, byte for byte) cached.  Three readings a
row by default, keyed by the reading index (``run`` of the call), sent through the llm-entropy generator's
:class:`~assistant_axis.gapgen.generators.llm_entropy.calls.EntropyRunner` (its frozen interface: another generator
may reuse it), live or through ``batches.BatchTransport``: **every response is recorded** in ``lay_responses.jsonl``
as it arrives, whatever its parse, with its billed usage; a reply that does not parse, a ``max_tokens`` stop, a
``refusal`` or no response is a **failed call, counted** and asked once more; a resume reuses every recorded answer
that parsed; a budget stop keeps what was paid for.

**The answer** (:func:`parse_lay`): one JSON object, after leading prose or inside a code fence, nothing after it:
``{"reason", "roles": [{"role", "covers", "distinct_persona", "gloss"}]}``.  A role is lower-cased, its leading
"a", "an" or "the" and trailing punctuation dropped, and must be one to three words; a role that is not is counted
in ``n_invalid`` and left out.  An empty ``roles`` is a valid answer (a job title that is only another name).

**Combining** (:func:`combine_readings`; a generating call, Roger's rule of 2026-10-13): the union of the readings'
roles by stem, each with its ``support`` (how many answered readings named it, 1-3), never dropped for low support;
``distinct_persona`` by majority of the readings that name the role (a tie is ``false``, recorded as
``distinct_tie``); ``covers`` the union of the occupations named (O*NET codes); the role's spelling and gloss from
the first reading that names it.  Agreement (:func:`agreement`) is a diagnostic, never a gate.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import Estimate
from assistant_axis.gapgen.generators.llm_entropy.calls import EntropyCall, EntropyRunner, WaveResult
from assistant_axis.gapgen.paths import REPO_ROOT
from assistant_axis.judge_pricing import BATCH_SUFFIX, cost_for_usage

from .onet import title_stem

RUBRIC_NAME = "profession_lay"
MODEL = "claude-haiku-5-5"
MAX_TOKENS = 3000
READINGS = 3
FAMILY = "lay"
STEP = "lay"
WAVE = "lay"
CONCURRENCY = 6
#: For the estimate: characters per input token, and output tokens a call (a reason, up to three roles with their
#: glosses, about 250 tokens, and Haiku 5.5's adaptive thinking on top, allowed for generously) until a run measures it.
CHARS_PER_TOKEN = 3.6
EST_OUT_TOKENS = 900
MAX_ROLE_WORDS = 3
#: 1 (2026-10-22): one JSON object, after leading prose or in a code fence; nothing after it.
PARSER_VERSION = 1
KINDS = ("broad", "job_title", "esco_group")


class RubricNotPinned(RuntimeError):
    """The rubric text on disk is not its latest pin."""


def load_rubric(rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> dict:
    """``{"name", "text", "version", "sha256", "file"}``; refuses a text that is not the latest pin (with
    ``allow_unpinned``, for rendering only, ``version`` and ``sha256`` are None).  Only this rubric's pin is checked."""
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == RUBRIC_NAME]
    path = sr.rubric_path(RUBRIC_NAME, rubrics_dir)
    try:
        rel = str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        rel = str(path)
    text = sr.load_prompt(RUBRIC_NAME, rubrics_dir)
    if probs:
        if not allow_unpinned:
            raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
        return {"name": RUBRIC_NAME, "text": text, "version": None, "sha256": None, "file": rel}
    version, sha = sr.current_versions(rubrics_dir, (RUBRIC_NAME,))[RUBRIC_NAME]
    return {"name": RUBRIC_NAME, "text": text, "version": version, "sha256": sha, "file": rel}


# --------------------------------------------------------------------------- groups

@dataclass
class LayGroup:
    """One call's subject: ``id`` (``broad:29-1210``, ``job_title:33-9032.00:bouncer``, ``esco:2221``), ``kind``,
    ``code`` (the SOC broad code, the O*NET code a title is listed under, or the ISCO code), ``title`` (the group's or
    occupation's), ``occupations`` (``{"code", "title", "description"}`` in the order shown), ``alternate_title``
    (a job title as the classification lists it), and what the ranking reads (``employment``, ``zipf``)."""
    id: str
    kind: str
    code: str
    title: str
    occupations: list
    alternate_title: Optional[str] = None
    employment: Optional[int] = None
    zipf: Optional[float] = None
    label: Optional[str] = None           # a job title's lay label (lower case, singular)

    @property
    def source_ref(self) -> str:
        """``soc:29-1210``, ``onet_title:33-9032.00:bouncer`` or ``esco:2221`` (coding plan 16, § 6.2)."""
        if self.kind == "broad":
            return f"soc:{self.code}"
        if self.kind == "job_title":
            return f"onet_title:{self.code}:{title_stem(self.label or self.alternate_title or '')}"
        return f"esco:{self.code}"


def group_from_row(row: Mapping) -> LayGroup:
    """A :class:`LayGroup` from a ``table.jsonl`` row (coding plan 16, § 6.6)."""
    kind = row["kind"]
    if kind == "broad":
        occ = [{"code": d["code"], "title": d["title"], "description": d.get("description") or ""}
               for d in row.get("detailed") or []]
        return LayGroup(id=f"broad:{row['code']}", kind="broad", code=row["code"], title=row["title"], occupations=occ,
                        employment=row.get("employment"))
    if kind == "job_title":
        label = row.get("label") or row["title"].lower()
        occ = [{"code": row["code"], "title": row["occupation"], "description": row.get("description") or ""}]
        return LayGroup(id=f"job_title:{row['code']}:{title_stem(label)}", kind="job_title", code=row["code"],
                        title=row["occupation"], occupations=occ, alternate_title=row["title"],
                        employment=row.get("employment"), zipf=row.get("zipf"), label=label)
    if kind == "esco_group":
        occ = [{"code": d.get("code") or d.get("uri"), "title": d["title"], "description": d.get("description") or ""}
               for d in row.get("detailed") or []]
        return LayGroup(id=f"esco:{row['code']}", kind="esco_group", code=row["code"], title=row["title"],
                        occupations=occ, employment=row.get("employment"))
    raise ValueError(f"unknown table row kind {kind!r}")


def groups_from_table(rows: Sequence[Mapping]) -> list[LayGroup]:
    out = [group_from_row(r) for r in rows]
    ids = [g.id for g in out]
    if len(set(ids)) != len(ids):
        raise ValueError("two table rows with one group id")
    return out


def build_user(group: LayGroup) -> str:
    """The user turn: one JSON object, the group on its first line and one occupation a line (module docstring)."""
    head: dict = {"code": group.code, "title": group.title}
    if group.alternate_title:
        head["alternate_title"] = group.alternate_title
    occ = [json.dumps({"id": i, "title": o["title"], "description": o.get("description") or ""}, ensure_ascii=False)
           for i, o in enumerate(group.occupations, 1)]
    return ('{"group": ' + json.dumps(head, ensure_ascii=False) + ",\n"
            ' "occupations": [\n' + ",\n".join("  " + x for x in occ) + "\n ]}")


def render(group: LayGroup, rubric: Mapping) -> str:
    """The request as sent: the system turn and the user turn."""
    return f"--- system (rubric {rubric['name']} v{rubric.get('version')}) ---\n{rubric['text']}\n--- user ---\n" + \
        build_user(group)


# --------------------------------------------------------------------------- the answer

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n?|\n?\s*```\s*$")
_ARTICLE_RE = re.compile(r"^(?:a|an|the)\s+", re.I)


def _one_object(text: str) -> tuple[Optional[dict], Optional[str]]:
    s = text.strip()
    if s.startswith("```"):
        s = _FENCE_RE.sub("", s).strip()
    i = s.find("{")
    if i < 0:
        return None, "no JSON object"
    try:
        obj, end = json.JSONDecoder().raw_decode(s[i:])
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON ({exc.msg})"
    rest = s[i + end:].strip().strip("`").strip()
    if rest:
        return None, "text after the JSON object"
    if not isinstance(obj, dict):
        return None, "not a JSON object"
    return obj, None


def clean_role(value: Any) -> Optional[str]:
    """A role as the call gives it, lower case, without a leading article or trailing punctuation; None when it is
    not one to three words."""
    if not isinstance(value, str):
        return None
    r = " ".join(value.strip().lower().split())
    r = _ARTICLE_RE.sub("", r).strip(" .,;:!\"'")
    if not r or not 1 <= len(r.split()) <= MAX_ROLE_WORDS:
        return None
    try:
        stem = title_stem(r)
    except Exception:  # noqa: BLE001 - an unusable string is an invalid role
        return None
    return r if stem else None


def _bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower() == "true"
    return None


def _ids(v: Any) -> list[int]:
    out = []
    for x in v if isinstance(v, list) else ([v] if v is not None else []):
        if isinstance(x, bool):
            continue
        if isinstance(x, int):
            out.append(x)
        elif isinstance(x, str) and x.strip().isdigit():
            out.append(int(x.strip()))
    return out


def parse_lay(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """``({"reason", "roles", "n_invalid"}, None)`` or ``(None, why)`` (module docstring)."""
    if text is None or not str(text).strip():
        return None, "empty answer"
    obj, err = _one_object(str(text))
    if obj is None:
        return None, err
    roles = obj.get("roles")
    if not isinstance(roles, list):
        return None, "no roles list"
    out, bad = [], 0
    for r in roles:
        if not isinstance(r, Mapping):
            bad += 1
            continue
        role = clean_role(r.get("role"))
        if role is None:
            bad += 1
            continue
        gloss = r.get("gloss")
        out.append({"role": role, "stem": title_stem(role), "covers": _ids(r.get("covers")),
                    "distinct_persona": _bool(r.get("distinct_persona")),
                    "gloss": " ".join(gloss.split()) if isinstance(gloss, str) and gloss.strip() else None})
    reason = obj.get("reason")
    return {"reason": reason if isinstance(reason, str) else None, "roles": out, "n_invalid": bad}, None


def parse_call(c: EntropyCall, text: Optional[str]) -> tuple[bool, dict]:
    """The runner's parser: the roles as the record's ``items``, the reason in its ``notes``."""
    d, err = parse_lay(text)
    if d is None:
        return False, {"parse_error": err}
    return True, {"items": d["roles"], "n_items": len(d["roles"]), "n_invalid": d["n_invalid"],
                  "notes": [d["reason"]] if d.get("reason") else []}


# --------------------------------------------------------------------------- combining

@dataclass
class LayRole:
    role: str
    stem: str
    covers: list
    distinct_persona: bool
    support: int
    n_readings: int
    gloss: Optional[str]
    votes: dict = field(default_factory=dict)
    readings: list = field(default_factory=list)
    distinct_tie: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def combine_readings(readings: Sequence[Optional[Mapping]], *, occupations: Optional[Sequence[Mapping]] = None
                     ) -> list[LayRole]:
    """The union of the answered readings' roles (module docstring).  ``readings``: one parsed answer per reading,
    in reading order (None for a reading with no usable answer); ``occupations``: the group's occupations in the
    order shown, so that ``covers`` ids become O*NET codes (an id out of range is dropped)."""
    answered = [(i, r) for i, r in enumerate(readings, 1) if r is not None]
    n = len(answered)
    by: dict[str, dict] = {}
    order: list[str] = []
    for i, r in answered:
        seen_here: set[str] = set()
        for x in r.get("roles") or []:
            stem = x.get("stem") or title_stem(x["role"])
            if stem in seen_here:
                continue
            seen_here.add(stem)
            cur = by.get(stem)
            if cur is None:
                cur = by[stem] = {"role": x["role"], "gloss": x.get("gloss"), "covers": [], "votes": [],
                                  "readings": []}
                order.append(stem)
            if cur["gloss"] is None and x.get("gloss"):
                cur["gloss"] = x["gloss"]
            cur["readings"].append(i)
            cur["votes"].append(x.get("distinct_persona"))
            for cid in x.get("covers") or []:
                if cid not in cur["covers"]:
                    cur["covers"].append(cid)
    out = []
    for stem in order:
        c = by[stem]
        votes = [v for v in c["votes"] if v is not None]
        yes = sum(1 for v in votes if v)
        distinct = yes * 2 > len(votes)
        tie = bool(votes) and yes * 2 == len(votes)
        ids = sorted(c["covers"])
        covers = ids
        if occupations is not None:
            covers = [occupations[k - 1]["code"] for k in ids if 1 <= k <= len(occupations)]
        out.append(LayRole(role=c["role"], stem=stem, covers=covers, distinct_persona=distinct,
                           support=len(c["readings"]), n_readings=n, gloss=c["gloss"],
                           votes={"distinct_persona": c["votes"]}, readings=c["readings"], distinct_tie=tie))
    return out


def agreement(lay_rows: Sequence[Mapping]) -> dict:
    """Diagnostics only: over groups with at least one role, the share of roles every answered reading named, the
    mean support, the share of groups whose readings named the same set of roles, and the readings answered."""
    n_groups = n_roles = n_full = 0
    sup = []
    same = 0
    answered = asked = 0
    for g in lay_rows:
        k = int(g.get("n_readings") or 0)
        answered += k
        asked += int(g.get("readings_asked") or k)
        roles = g.get("roles") or []
        if not roles or not k:
            continue
        n_groups += 1
        n_roles += len(roles)
        n_full += sum(1 for r in roles if r["support"] == k)
        sup += [r["support"] for r in roles]
        same += all(r["support"] == k for r in roles)
    return {"n_groups_with_roles": n_groups, "n_roles": n_roles,
            "share_roles_named_by_every_reading": round(n_full / n_roles, 4) if n_roles else None,
            "mean_support": round(sum(sup) / len(sup), 3) if sup else None,
            "share_groups_same_roles": round(same / n_groups, 4) if n_groups else None,
            "readings_answered": answered, "readings_asked": asked}


# --------------------------------------------------------------------------- the calls

def lay_calls(groups: Sequence[LayGroup], *, rubric: Mapping, readings: int = READINGS, model: str = MODEL,
              max_tokens: int = MAX_TOKENS) -> list[EntropyCall]:
    meta_r = {"rubric": rubric["name"], "rubric_version": rubric.get("version"), "rubric_sha256": rubric.get("sha256"),
              "parser_version": PARSER_VERSION}
    out = []
    for g in groups:
        user = build_user(g)
        for r in range(1, int(readings) + 1):
            out.append(EntropyCall(family=FAMILY, prompt_id=g.id, run=r, model=model, system=rubric["text"], user=user,
                                   max_tokens=max_tokens, step=STEP,
                                   meta={**meta_r, "group": g.id, "kind": g.kind, "code": g.code, "reading": r}))
    return out


def call_tokens(c: EntropyCall) -> tuple[int, int]:
    return int((len(c.system) + len(c.user)) / CHARS_PER_TOKEN), EST_OUT_TOKENS


def estimate_usd(calls: Sequence[EntropyCall], *, batch: bool = False) -> float:
    suffix = BATCH_SUFFIX if batch else ""
    return sum(cost_for_usage(c.model + suffix, *call_tokens(c)) for c in calls)


def estimate(calls: Sequence[EntropyCall], *, batch: bool = False) -> Estimate:
    """``n_calls x (in, out) tokens at model rates`` per kind of row."""
    est = Estimate()
    by: dict[tuple, list] = {}
    for c in calls:
        by.setdefault((c.meta.get("kind"), c.model), []).append(c)
    for (kind, model), cs in sorted(by.items(), key=lambda kv: str(kv[0])):
        toks = [call_tokens(c) for c in cs]
        est.add(f"lay call, {kind} rows", model + (BATCH_SUFFIX if batch else ""), len(cs),
                sum(t[0] for t in toks) // len(cs), sum(t[1] for t in toks) // len(cs))
    return est


class LayRunner(EntropyRunner):
    """:class:`EntropyRunner` with this call's estimate (the Batches transport checks a wave against the cap with
    it)."""

    def estimate_usd(self, calls, *, batch: bool = False) -> float:
        return estimate_usd(calls, batch=batch)


@dataclass
class LayResult:
    roles: dict                       # group id -> list[LayRole]
    n_readings: dict                  # group id -> readings answered
    wave: Optional[WaveResult] = None

    @property
    def stopped(self):
        return self.wave.stopped if self.wave is not None else None


def collect(groups: Sequence[LayGroup], wave: WaveResult, *, readings: int) -> LayResult:
    """Combine the wave's answers per group (a reading with no usable answer counts as missing)."""
    got: dict[tuple, list] = {}
    for key, (c, rec, parsed) in wave.answers.items():
        items = parsed.get("items") if parsed.get("items") is not None else rec.get("items")
        got[(c.prompt_id, int(c.run))] = items or []
    roles, n_read = {}, {}
    for g in groups:
        rs = []
        for r in range(1, int(readings) + 1):
            items = got.get((g.id, r))
            rs.append(None if items is None else {"roles": items})
        roles[g.id] = combine_readings(rs, occupations=g.occupations)
        n_read[g.id] = sum(1 for x in rs if x is not None)
    return LayResult(roles=roles, n_readings=n_read, wave=wave)


async def lay_groups(groups: Sequence[LayGroup], *, client=None, usage, readings: int = READINGS,
                     records_path: Optional[Path], transport_factory: Optional[Callable[[EntropyRunner], Any]] = None,
                     resume_records: Sequence[Mapping] = (), model: str = MODEL, rubric: Optional[Mapping] = None,
                     rubrics_dir: Optional[Path] = None, batch_id: str = "professions_lay", run_id: Optional[str] = None,
                     concurrency: int = CONCURRENCY, retry_delays: Optional[Sequence[float]] = None,
                     checkpoint: Optional[Callable[[], Any]] = None) -> LayResult:
    """Ask every group ``readings`` times (live through ``client``, or through ``transport_factory(runner)``, e.g.
    a ``batches.BatchTransport``), record every response in ``records_path``, and combine (module docstring).  A
    budget stop is on ``result.stopped`` (the answers in hand are combined first); :func:`run_lay_groups` raises
    it."""
    rubric = rubric or load_rubric(rubrics_dir)
    calls = lay_calls(groups, rubric=rubric, readings=readings, model=model)
    runner = LayRunner(client=client, batch_id=batch_id, usage=usage, responses_path=records_path,
                       resume_records=resume_records, run_id=run_id, concurrency=concurrency,
                       retry_delays=retry_delays, checkpoint=checkpoint, prompts_version=rubric.get("version"))
    if transport_factory is not None:
        runner.transport = transport_factory(runner)
    wave = await runner.wave_async(WAVE, calls, parse_call)
    return collect(groups, wave, readings=readings)


def run_lay_groups(groups: Sequence[LayGroup], **kw) -> LayResult:
    """:func:`lay_groups` on a fresh event loop; a stop (budget, failed batch) is raised once the answers in hand
    are combined and returned on the exception's ``result`` attribute."""
    import asyncio
    res = asyncio.run(lay_groups(groups, **kw))
    if res.stopped is not None:
        exc = res.stopped
        try:
            exc.result = res
        except Exception:  # noqa: BLE001 - an exception type that refuses attributes is raised as it is
            pass
        raise exc
    return res


def lay_rows(groups: Sequence[LayGroup], result: LayResult, *, readings: int = READINGS) -> list[dict]:
    """``lay.jsonl`` (coding plan 16, § 6.6): one row per group, its combined roles."""
    out = []
    for g in groups:
        rs = result.roles.get(g.id) or []
        out.append({"group": g.id, "kind": g.kind, "code": g.code, "title": g.title,
                    "alternate_title": g.alternate_title, "source_ref": g.source_ref, "employment": g.employment,
                    "zipf": g.zipf, "n_readings": result.n_readings.get(g.id, 0), "readings_asked": int(readings),
                    "failed": result.n_readings.get(g.id, 0) == 0,
                    "roles": [{"role": r.role, "stem": r.stem, "covers": r.covers,
                               "distinct_persona": r.distinct_persona, "support": r.support, "gloss": r.gloss,
                               "votes": r.votes, "readings": r.readings, "distinct_tie": r.distinct_tie}
                              for r in rs]})
    return out


__all__ = ["RUBRIC_NAME", "MODEL", "MAX_TOKENS", "READINGS", "FAMILY", "STEP", "WAVE", "EST_OUT_TOKENS",
           "PARSER_VERSION", "KINDS", "RubricNotPinned", "load_rubric", "LayGroup", "group_from_row",
           "groups_from_table", "build_user", "render", "clean_role", "parse_lay", "parse_call", "LayRole",
           "combine_readings", "agreement", "lay_calls", "call_tokens", "estimate_usd", "estimate", "LayRunner",
           "LayResult", "collect", "lay_groups", "run_lay_groups", "lay_rows"]
