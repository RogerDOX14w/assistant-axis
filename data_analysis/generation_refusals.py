"""Refusals of the two instruction generators (2026-10-08).

``regenerate_trait_instructions.py`` and ``regenerate_role_instructions.py``
ask the generator model for a JSON object of instructions and questions, and
for some seeds (chunk 5: ageist, sexist, self_harming, ...) the model may
decline.  Roger's ruling (2026-09-08, reaffirmed 2026-10-08): attempt them, and
treat a refusal as a data point to record, not an error to retry.  A refusal is

* a reply the API ends with ``stop_reason`` "refusal" (its ``content`` may be
  empty, or hold what was written before the stop),
* a text reply that is not JSON and whose first sentence declines
  (``DECLINE_PHRASES``), or
* a reply that writes the sentinel ``ERROR:`` instead of the content: a JSON
  reply with a field value that opens "ERROR:" (2026-10-08, brown-haired:
  "ERROR: 'Brown-haired' is a physical descriptor, not a personality trait
  ..." as the eval prompt of an otherwise well-formed reply), or a reply that
  opens with it.

Any of these raises ``GenerationRefusal`` at once; the generators' retry loops
do not catch it.  Each generator appends one record per refusal to
``generation_refusals.jsonl`` beside ``instructions/`` (``data/traits/``,
``data/roles/``, where nothing that globs the corpus reads it) and leaves the
seed file as it was; ``seed_entities.py generate`` reads the records and marks
the queue entries ``refused``.

A reply that writes its deliberation before the JSON (2026-10-08, brown-eyed:
usable instructions behind a paragraph of prose) is not a refusal: the
generators' JSON readers skip the preface (``strip_prose_preface``) and use
the reply.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Optional

from assistant_axis.atomic_io import append_jsonl

REFUSALS_NAME = "generation_refusals.jsonl"
EXCERPT_CHARS = 300

# A text reply that is not JSON and has one of these in its first sentence is a
# decline, not a malformed answer, and is not asked for again.  Matched as whole
# words, ignoring case and typographic apostrophes, in the first sentence only
# (at most FIRST_SENTENCE_CHARS characters), so a reply that says it later
# ("Here is the set. I can't promise ...") is not a refusal; a reply with a JSON
# object anywhere in it, or one that opens with a JSON array, never is, whatever
# its words.  A decline worded any other way ("This request ...") is retried as
# an unreadable reply, as before: add its phrase here.
DECLINE_PHRASES = ("I can't", "I cannot", "I won't", "I'm not able to", "I am not able to",
                   "I don't feel comfortable", "I'm not comfortable", "I will not")
FIRST_SENTENCE_CHARS = 300
_DECLINE = re.compile(r"\b(?:" + "|".join(re.escape(p.lower()) for p in DECLINE_PHRASES) + r")\b")
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)|\n")
_OPENS_WITH_ARRAY = re.compile(r"^(?:```(?:json)?\s*)?\[")
# The generator's own "I will not write this" marker, seen as a JSON field
# value (case-sensitive, at the start of the value after any whitespace).
ERROR_SENTINEL = "ERROR:"
_FENCE_OPEN = re.compile(r"^```(?:json)?\s*\n?")
_FENCE_CLOSE = re.compile(r"\n?```\s*$")
_LINE_OPENS_OBJECT = re.compile(r"^\{", re.MULTILINE)


class GenerationRefusal(RuntimeError):
    """The generator model declined to write a set.  Raised at once and never
    retried; the generator records it and counts it apart from errors."""

    def __init__(self, label: str, stop_reason: Optional[str], reply_excerpt: str):
        self.label = label
        self.stop_reason = stop_reason
        self.reply_excerpt = reply_excerpt
        super().__init__(f"{label}: the model refused (stop_reason {stop_reason}): {self.excerpt_line}")

    @property
    def excerpt_line(self) -> str:
        """The excerpt on one line, for a run log."""
        return " ".join(self.reply_excerpt.split()) or f"(no text; stop_reason {self.stop_reason})"


def reply_text(response) -> str:
    """The first text block of a reply, or "" when there is none (a refused
    reply can come back with an empty ``content`` list)."""
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            return getattr(block, "text", "") or ""
    return ""


def reads_as_decline(text: str) -> bool:
    """True when a reply that should have been JSON is a prose decline (see
    ``DECLINE_PHRASES``)."""
    flat = (text or "").strip().replace("’", "'")
    if not flat or "{" in flat or _OPENS_WITH_ARRAY.match(flat):
        return False
    first = _SENTENCE_END.split(flat, maxsplit=1)[0][:FIRST_SENTENCE_CHARS]
    return bool(_DECLINE.search(first.lower()))


def strip_prose_preface(text: str) -> tuple[str, str]:
    """Split a reply that should be a JSON object into ``(json_part,
    preface)``: when it opens with prose instead of ``{`` or ``[``, the JSON
    part starts at the first line that opens with ``{`` (else at the first
    ``{``), and everything before it, a fence opener included, is the
    preface.  A reply that opens with JSON, or has no ``{``, comes back
    whole with an empty preface, so a usable reply is read exactly as
    before.  Call it after stripping a fence that wraps the whole reply."""
    s = (text or "").strip()
    if not s or s[0] in "{[":
        return s, ""
    m = _LINE_OPENS_OBJECT.search(s)
    i = m.start() if m else s.find("{")
    if i <= 0:
        return s, ""
    return s[i:], s[:i].rstrip()


def find_error_sentinel(value, path: str = "") -> Optional[tuple[str, str]]:
    """The first string in a parsed reply that opens with ``ERROR:``, as
    ``(path, value)`` (``eval_prompt``, ``instruction[2].pos``), or None."""
    if isinstance(value, str):
        return (path, value) if value.lstrip().startswith(ERROR_SENTINEL) else None
    if isinstance(value, dict):
        items = ((f"{path}.{k}" if path else str(k), v) for k, v in value.items())
    elif isinstance(value, list):
        items = ((f"{path}[{i}]", v) for i, v in enumerate(value))
    else:
        return None
    for sub_path, v in items:
        hit = find_error_sentinel(v, sub_path)
        if hit is not None:
            return hit
    return None


def error_sentinel_in(text: str) -> Optional[str]:
    """When a reply writes the ``ERROR:`` sentinel instead of the content,
    the excerpt to record ("eval_prompt: ERROR: ..."); otherwise None.  A
    reply whose JSON cannot be read is not judged here (the generator's own
    reader retries it), except one that simply opens with the sentinel."""
    s = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", (text or "").strip())).strip()
    if s.startswith(ERROR_SENTINEL):
        return s
    try:
        parsed = json.loads(strip_prose_preface(s)[0], strict=False)
    except ValueError:
        return None
    hit = find_error_sentinel(parsed)
    if hit is None:
        return None
    path, value = hit
    return f"{path}: {value}" if path else value


def refusal_in(response, label: str) -> Optional[GenerationRefusal]:
    """The refusal a reply carries (``stop_reason`` "refusal", a prose
    decline, or the ``ERROR:`` sentinel), or None."""
    stop_reason = getattr(response, "stop_reason", None)
    stop_reason = stop_reason if isinstance(stop_reason, str) else None
    text = reply_text(response)
    if stop_reason == "refusal" or reads_as_decline(text):
        return GenerationRefusal(label, stop_reason, text[:EXCERPT_CHARS])
    sentinel = error_sentinel_in(text)
    if sentinel is not None:
        return GenerationRefusal(label, stop_reason, sentinel[:EXCERPT_CHARS])
    return None


def record_refusal(path: Path, refusal: GenerationRefusal, *, stem: str, kind: str, model: str,
                   style: str, template_sha256: Optional[str], attempt: str) -> dict:
    """Append one record to the side-car ``path`` and return it.  ``kind`` is
    "trait" or "role"; ``attempt`` is "live" (a real-time call) or "batch" (a
    Message Batch reply)."""
    record = {
        "stem": stem,
        "label": refusal.label,
        "kind": kind,
        "model": model,
        "style": style,
        "template_sha256": template_sha256,
        "refused_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "stop_reason": refusal.stop_reason,
        "reply_excerpt": refusal.reply_excerpt,
        "attempt": attempt,
    }
    append_jsonl(record, path)
    return record


_SENTINEL_AFTER_PATH = re.compile(r"^([\w.\[\]]+): " + re.escape(ERROR_SENTINEL))


def refusal_form(record: Optional[dict]) -> str:
    """How a recorded refusal was made, for a report: "stop_reason refusal",
    "ERROR: sentinel in <field>" (or "ERROR: sentinel" when the reply opened
    with it), or "prose decline"."""
    record = record or {}
    if record.get("stop_reason") == "refusal":
        return "stop_reason refusal"
    excerpt = (record.get("reply_excerpt") or "").lstrip()
    if excerpt.startswith(ERROR_SENTINEL):
        return "ERROR: sentinel"
    m = _SENTINEL_AFTER_PATH.match(excerpt)
    if m:
        return f"ERROR: sentinel in {m.group(1)}"
    return "prose decline"


def read_refusals(path: Path) -> list[dict]:
    """Every record in a side-car, oldest first ([] when there is none)."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
