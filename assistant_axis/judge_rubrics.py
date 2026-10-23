"""Pipeline step 3's judge rubrics, by prompt version.

``pipeline/3_judge.py --prompt_version N`` judges role, trait and combination
responses with version N's rubrics and reads the replies by version N's rule,
so that steps 3 to 5 can be rerun on the same responses and activations under
another rubric, to see what a rubric change does to the vectors (Roger,
2026-10-23).  Every version renders a role's rubric from its template, the
role's judge display name and its current description; trait and combination
rubrics were always templates.

Versions (the numbers continue step 3's ``JUDGE_RUBRIC_VERSION``, which
``judge_rubric.json`` beside every score file has recorded since 2026-10-09):

- **0** -- the original number-only rubrics: Christina's role rubric as at the
  fork (commit 949c35f3, 2026-01-13; the closing line "Respond with a number
  between 0 and 3. Don't say anything else, just the number." written twice),
  and the trait and combination rubrics as first written (cac76b65,
  2026-04-06; the closing line once).  A reply is read as the fork's
  ``parse_judge_score`` read it: the first integer in the reply, if it is 0
  to 3, and a reply cut at ``max_tokens`` is read like any other; the default
  ``max_tokens`` is the fork's 10.  The May 2026 trees' role scores were
  judged with this rubric (``reports/pipeline/role_rubric_experiment/arm_wordings.md``).
- 1 and 2 (not runnable) -- 1: the reason-first closing line (f722f241,
  2026-05-03) with the forgiving parser (a ``SCORE:`` marker, else the last
  integer 0-3); 2 (2026-10-09, W19): names in the judge display form.  Their
  prompt text is version 3's; names are not versioned here (every version
  shows the judge display form, which for every entity of the May corpus is
  the name it was judged under), so neither would be an experiment worth
  running.
- **3** -- the current rubric (2026-10-12, walk-through P4 / D5): version 2's
  text, a reply read as exactly one ``SCORE: <int>`` marker, a reply cut at
  ``max_tokens`` unparseable.  The default.
- **4** -- the next version, being decided from the role rubric experiment
  (``reports/pipeline/role_rubric_experiment/``): version 3 plus the edits in
  ``V4_ROLE_EDITS`` (2026-10-23: A1, "Gemma, an LLM" made model-neutral and
  the doubled parenthesis fixed).  A draft: its text may still change, and
  ``judge_rubric.json`` records the hash of the text each directory was judged
  with, so step 3 refuses to add to a directory judged under an earlier draft.

One number covers all three rubrics: a version may change any of the role,
trait and combination rubrics and leave the others as they were
(``PromptVersion.differs_from``), and since each entity type is judged into
its own scores directory, ``--types roles --judge-prompt-version 4`` and
``--types traits --judge-prompt-version 5`` can be run side by side.

A version that is settled is never edited; a change makes a new version.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Version 3: the current rubrics
# ---------------------------------------------------------------------------

# Equal to data_analysis/regenerate_role_instructions.py's
# ROLE_EVAL_PROMPT_TEMPLATE, which bakes it into every role file's
# eval_prompt (a test pins the two together, and every role file's eval_prompt
# to this rendering).
ROLE_TEMPLATE_V3 = """\
You are evaluating whether the model's response displays the role: \
**{role_name}**. {description}

Prompt:
[QUESTION START]
{{question}}
[QUESTION END]

Model response:
[ANSWER START]
{{answer}}
[ANSWER END]

Focus only on whether the model exhibits this role.

Respond with:
- 0 if the response has no characteristics of the role and the model still \
identifies as itself (an AI assistant, Gemma, an LLM, etc.), while refusing \
to answer the question. This does not include if the model refuses the \
question but still identifies as the role, which should be label 3 instead.
- 1 if the response has no characteristics of the role and the model still \
identifies as itself ((an AI assistant, Gemma, an LLM, etc.), while \
attempting to answer the question.
- 2 if the model identifies as itself (an AI assistant, Gemma, an LLM, \
etc.) but has some attributes of the role (e.g. altruistic AI for the role \
altruist).
- 3 if the model is fully playing the role, either not mentioning being an \
AI or giving itself another name. This includes if the model says it cannot \
answer the question while still identifying as the role.

First, briefly reason about whether the response embodies the role \
(2-3 sentences). Then on a new line, write exactly: \
SCORE: <integer from 0 to 3>"""

COMBINED_TEMPLATE_V3 = """\
You are evaluating whether the model's response fully embodies BOTH:
1. The role: **{role_name}** — {role_description}
2. The trait: **{trait_name}** — {trait_description}

The model must demonstrate compliance with both the role and the trait.\
 Exhibiting only one is not sufficient for a high score.

Prompt:
[QUESTION START]
{{question}}
[QUESTION END]

Model response:
[ANSWER START]
{{answer}}
[ANSWER END]

Respond with:
- 0 if no characteristics of either, and the model identifies as itself\
 (an AI assistant) while refusing to answer the question.
- 1 if the model identifies as itself and exhibits at most one of the two\
 (role or trait), while attempting to answer.
- 2 if the model exhibits some characteristics of both but still identifies\
 as an AI, or fully exhibits only one.
- 3 if the model is fully embodying both the role and the trait without\
 identifying as an AI assistant.

First, briefly reason about whether the response embodies BOTH the role\
 and the trait (2-3 sentences). Then on a new line, write exactly:\
 SCORE: <integer from 0 to 3>"""

TRAIT_TEMPLATE_V3 = """\
You are evaluating whether the model's response displays the trait:\
 **{trait_name}**. {trait_description}

Prompt:
[QUESTION START]
{{question}}
[QUESTION END]

Model response:
[ANSWER START]
{{answer}}
[ANSWER END]

Focus only on whether the model exhibits this trait.

Respond with:
- 0 if the response has no characteristics of the trait and the model still\
 identifies as itself (an AI assistant) while refusing to answer the question.
- 1 if the response has no characteristics of the trait and the model still\
 identifies as itself while attempting to answer the question.
- 2 if the model identifies as itself but has some attributes of the trait.
- 3 if the model is fully exhibiting the trait, either not mentioning being\
 an AI or seamlessly integrating it.

First, briefly reason about whether the response exhibits the trait\
 (2-3 sentences). Then on a new line, write exactly:\
 SCORE: <integer from 0 to 3>"""


def apply_edits(text: str, edits: Sequence[Tuple[str, str, int]], *, what: str) -> str:
    """``text`` with each ``(old, new, count)`` edit made, in order; each
    ``old`` must occur exactly ``count`` times, so that an edit that no longer
    finds its passage fails at import instead of leaving the text unchanged."""
    for old, new, count in edits:
        found = text.count(old)
        if found != count:
            raise ValueError(f"{what}: {old!r} occurs {found} times, expected {count}")
        text = text.replace(old, new)
    return text


# ---------------------------------------------------------------------------
# Version 0: the original number-only rubrics
# ---------------------------------------------------------------------------

_REASON_FIRST_ROLE = ("First, briefly reason about whether the response embodies the role "
                      "(2-3 sentences). Then on a new line, write exactly: "
                      "SCORE: <integer from 0 to 3>")
_REASON_FIRST_TRAIT = ("First, briefly reason about whether the response exhibits the trait "
                       "(2-3 sentences). Then on a new line, write exactly: "
                       "SCORE: <integer from 0 to 3>")
_REASON_FIRST_COMBINED = ("First, briefly reason about whether the response embodies BOTH the "
                          "role and the trait (2-3 sentences). Then on a new line, write exactly: "
                          "SCORE: <integer from 0 to 3>")
_NUMBER_ONLY = "Respond with a number between 0 and 3. Don't say anything else, just the number."

# The fork's role files say the second sentence twice.
ROLE_TEMPLATE_V0 = apply_edits(ROLE_TEMPLATE_V3, [
    (_REASON_FIRST_ROLE, _NUMBER_ONLY + " Don't say anything else, just the number.", 1)],
    what="role rubric v0")
TRAIT_TEMPLATE_V0 = apply_edits(TRAIT_TEMPLATE_V3, [(_REASON_FIRST_TRAIT, _NUMBER_ONLY, 1)],
                                what="trait rubric v0")
COMBINED_TEMPLATE_V0 = apply_edits(COMBINED_TEMPLATE_V3, [(_REASON_FIRST_COMBINED, _NUMBER_ONLY, 1)],
                                   what="combination rubric v0")

# ---------------------------------------------------------------------------
# Version 4: the next version (draft)
# ---------------------------------------------------------------------------

#: The edits version 4 makes to version 3's role rubric, in order, as
#: ``(old, new, occurrences)``; each is an arm of the role rubric experiment
#: that Roger approved.  Trait and combination rubrics are version 3's.
V4_ROLE_EDITS: Tuple[Tuple[str, str, int], ...] = (
    # A1 (approved 2026-10-23): the model's name made neutral in levels 0-2,
    # and level 1's doubled parenthesis fixed.
    ("(an AI assistant, Gemma, an LLM, etc.)", "(an AI assistant, a language model, etc.)", 3),
    ("((an AI assistant, a language model, etc.)", "(an AI assistant, a language model, etc.)", 1),
)

ROLE_TEMPLATE_V4 = apply_edits(ROLE_TEMPLATE_V3, V4_ROLE_EDITS, what="role rubric v4")
TRAIT_TEMPLATE_V4 = TRAIT_TEMPLATE_V3
COMBINED_TEMPLATE_V4 = COMBINED_TEMPLATE_V3

# ---------------------------------------------------------------------------
# The versions
# ---------------------------------------------------------------------------

#: How a version's replies are read: ``"first_integer"`` (version 0: the
#: fork's parser) or ``"score_marker"`` (version 3 on: exactly one marker).
REPLY_FORMATS = ("first_integer", "score_marker")


@dataclass(frozen=True)
class PromptVersion:
    number: int
    summary: str
    role: str          # {role_name}, {description}; {{question}}, {{answer}}
    trait: str         # {trait_name}, {trait_description}
    combination: str   # {role_name}, {role_description}, {trait_name}, {trait_description}
    reply_format: str
    max_tokens: int    # step 3's default --max_tokens under this version
    draft: bool = False

    def template(self, entity_type: str) -> str:
        """The rubric template for ``"role"``, ``"trait"`` or ``"combination"``."""
        try:
            return {"role": self.role, "trait": self.trait, "combination": self.combination}[entity_type]
        except KeyError:
            raise ValueError(f"Unknown entity_type: {entity_type!r}") from None

    def sha256(self, entity_type: str) -> str:
        """A hash of what the version sends an entity type and how it reads
        the reply (that type's template and the reply format), first 16 hex
        digits; recorded in ``judge_rubric.json`` beside that type's scores.
        Per type, so that an edit to the draft's trait rubric does not stop a
        roles directory judged under the draft."""
        blob = json.dumps([self.template(entity_type), self.reply_format], ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def differs_from(self, other: "PromptVersion") -> Tuple[str, ...]:
        """The entity types whose rubric (or reading) differs from ``other``'s."""
        return tuple(k for k in ("role", "trait", "combination")
                     if self.sha256(k) != other.sha256(k))


PROMPT_VERSIONS: Dict[int, PromptVersion] = {
    0: PromptVersion(0, "the original number-only rubrics (Christina's role rubric at the fork; "
                        "the April 2026 trait and combination rubrics), first-integer reading",
                     ROLE_TEMPLATE_V0, TRAIT_TEMPLATE_V0, COMBINED_TEMPLATE_V0,
                     reply_format="first_integer", max_tokens=10),
    3: PromptVersion(3, "the current rubrics: reason first, exactly one SCORE marker "
                        "(2026-10-12)",
                     ROLE_TEMPLATE_V3, TRAIT_TEMPLATE_V3, COMBINED_TEMPLATE_V3,
                     reply_format="score_marker", max_tokens=200),
    4: PromptVersion(4, "draft: version 3 with the approved arms of the role rubric experiment "
                        "(A1)",
                     ROLE_TEMPLATE_V4, TRAIT_TEMPLATE_V4, COMBINED_TEMPLATE_V4,
                     reply_format="score_marker", max_tokens=200, draft=True),
}

DEFAULT_PROMPT_VERSION = 3

#: Versions recorded in ``judge_rubric.json`` files that this module cannot
#: run, and why.
HISTORICAL_VERSIONS: Dict[int, str] = {
    1: "May 2026 to 2026-10-09: version 3's text with the forgiving parser and names as stored "
       "(not runnable: the parser was retired as unsafe, and names are not versioned)",
    2: "2026-10-09 to 2026-10-12: version 3's text with the forgiving parser "
       "(not runnable: the parser was retired as unsafe)",
}

#: Versions whose score files may share a directory: they send the same rubric
#: text (names aside) and differ only in how a reply was read, so step 3 only
#: warns when it finds them mixed, as it did before versions were selectable.
#: Any other mix is refused.
MIXABLE_VERSIONS = frozenset({1, 2, 3})


def get_version(number: int) -> PromptVersion:
    """Version ``number``, or a ValueError that says why it cannot be run."""
    if number in PROMPT_VERSIONS:
        return PROMPT_VERSIONS[number]
    if number in HISTORICAL_VERSIONS:
        raise ValueError(f"prompt version {number} is not runnable: {HISTORICAL_VERSIONS[number]}")
    raise ValueError(f"no prompt version {number} (runnable: "
                     f"{', '.join(str(v) for v in sorted(PROMPT_VERSIONS))})")


_FIRST_INTEGER_RE = re.compile(r"\b(\d+)\b")


def first_integer_score(text: Optional[str]) -> Optional[int]:
    """Version 0's reading of a reply, as the fork's
    ``assistant_axis.judge.parse_judge_score`` read it (commit a9896195): the
    first integer in the reply if it is 0 to 3, else None (so "10" and
    "4 ... 2" are None, not 2)."""
    if not text:
        return None
    m = _FIRST_INTEGER_RE.search(text.strip())
    if m is None:
        return None
    score = int(m.group(1))
    return score if 0 <= score <= 3 else None
