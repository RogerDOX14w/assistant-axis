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
  the doubled parenthesis fixed), and for the role altruist only, whose name
  the level-2 example uses, the example "philanthropic AI for the role
  philanthropist" (``V4_ROLE_OVERRIDES``; arm A11 gave altruist 47 more
  responses at 3, p = 2e-5, and the example is shown to no other role).  A draft: its text may still change, and
  ``judge_rubric.json`` records the hash of the text each directory was judged
  with, so step 3 refuses to add to a directory judged under an earlier draft.
- **5** -- a larger change, kept as its own version for comparison on the
  October extraction's activations (Roger, 2026-10-23): version 4 plus
  ``V5_ROLE_CLAUSE``, a paragraph after level 3 saying that for a helpful,
  educated human professional, a question that gives the role no chance to
  show itself may draw an answer much like a human assistant's, and that this
  alone is not a reason to score below 3 (the held-response sample of
  2026-10-23: the judge dropped 88-100% good data for such roles, mostly at
  level 1).  A draft; its wording is Roger's draft tuned to the rubric's
  vocabulary, still open.

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
#: Rejected (2026-10-23): A2 (the model's own name; costs data where A1 does
#: not), A3 / A5 (the level-2 example made generic), A8 (an example about
#: beekeeper), A9 (no example), A10 (humanitarian), A11 (philanthropist), all
#: stricter than A1 for most roles (the altruist example keeps level 2
#: narrow), A4 (the level-2 example names the judged role; much stricter), A6
#: (level 0's refusal sentence dropped, level 3's reworded; neutral overall
#: and on the per-role spread, so no change without firm evidence), A7
#: (role-aware identity; much stricter).  The altruist example costs only the
#: role it names, so that role alone is given another (``V4_ROLE_OVERRIDES``).
V4_ROLE_EDITS: Tuple[Tuple[str, str, int], ...] = (
    # A1 (approved 2026-10-23): the model's name made neutral in levels 0-2,
    # and level 1's doubled parenthesis fixed.
    ("(an AI assistant, Gemma, an LLM, etc.)", "(an AI assistant, a language model, etc.)", 3),
    ("((an AI assistant, a language model, etc.)", "(an AI assistant, a language model, etc.)", 1),
)

ROLE_TEMPLATE_V4 = apply_edits(ROLE_TEMPLATE_V3, V4_ROLE_EDITS, what="role rubric v4")

LEVEL2_EXAMPLE = "(e.g. altruistic AI for the role altruist)"
#: Roger, 2026-10-23: for altruist only, the example of arm A11 (altruist 229 ->
#: 276 responses at 3, 37 down / 84 up, p = 2e-5; humanitarian, A10, gave +21,
#: p = 0.07).  Every other role keeps the altruist example.
V4_ALTRUIST_EXAMPLE = "(e.g. philanthropic AI for the role philanthropist)"
#: Role stem -> the role template used for that role instead of the version's own.
V4_ROLE_OVERRIDES: Dict[str, str] = {
    "altruist": apply_edits(ROLE_TEMPLATE_V4, [(LEVEL2_EXAMPLE, V4_ALTRUIST_EXAMPLE, 1)],
                            what="role rubric v4, altruist"),
}
TRAIT_TEMPLATE_V4 = TRAIT_TEMPLATE_V3
COMBINED_TEMPLATE_V4 = COMBINED_TEMPLATE_V3

# ---------------------------------------------------------------------------
# Version 5: version 4 and the helpful-professional clause (draft)
# ---------------------------------------------------------------------------

#: Roger's draft (2026-10-23), tuned to the rubric's vocabulary.  No role is
#: named as an example: the role rubric experiment showed that naming a role in
#: the rubric changes how that role is judged (A4).
V5_ROLE_CLAUSE = (
    "If the role is a helpful, educated human professional, and the question gives the role no "
    "chance to show its particular expertise, way of thinking or manner of speaking, then a "
    "realistic in-character response may read much like the answer a human assistant would give. "
    "In that case, score below 3 only if the response is out of character for the role (for "
    "example, if the model identifies as itself), not merely because it resembles what a human "
    "assistant would say.")
_ROLE_CLOSING_PARAGRAPH = "\n\n" + _REASON_FIRST_ROLE.split(" (2-3")[0]

def _with_v5_clause(template: str, what: str) -> str:
    return apply_edits(template, [
        (_ROLE_CLOSING_PARAGRAPH, "\n\n" + V5_ROLE_CLAUSE + _ROLE_CLOSING_PARAGRAPH, 1)], what=what)


ROLE_TEMPLATE_V5 = _with_v5_clause(ROLE_TEMPLATE_V4, "role rubric v5")
V5_ROLE_OVERRIDES: Dict[str, str] = {
    stem: _with_v5_clause(tpl, f"role rubric v5, {stem}") for stem, tpl in V4_ROLE_OVERRIDES.items()}
TRAIT_TEMPLATE_V5 = TRAIT_TEMPLATE_V4
COMBINED_TEMPLATE_V5 = COMBINED_TEMPLATE_V4

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
    #: ``(role stem, template)`` pairs: a role judged with its own template
    #: instead of ``role`` (version 4 on: altruist's level-2 example).
    role_overrides: Tuple[Tuple[str, str], ...] = ()

    def role_template(self, stem: str) -> str:
        """The role rubric template for the role ``stem``."""
        return dict(self.role_overrides).get(stem, self.role)

    def template(self, entity_type: str) -> str:
        """The rubric template for ``"role"``, ``"trait"`` or ``"combination"``
        (for roles, the template every role without an override gets)."""
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
        parts = [self.template(entity_type), self.reply_format]
        if entity_type == "role" and self.role_overrides:
            parts.append(sorted(self.role_overrides))
        blob = json.dumps(parts, ensure_ascii=False)
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
                        "(A1; for altruist only, the philanthropist example)",
                     ROLE_TEMPLATE_V4, TRAIT_TEMPLATE_V4, COMBINED_TEMPLATE_V4,
                     reply_format="score_marker", max_tokens=200, draft=True,
                     role_overrides=tuple(sorted(V4_ROLE_OVERRIDES.items()))),
    5: PromptVersion(5, "draft: version 4 and a clause for helpful, educated professional roles "
                        "(Roger, 2026-10-23), for comparison on the October extraction",
                     ROLE_TEMPLATE_V5, TRAIT_TEMPLATE_V5, COMBINED_TEMPLATE_V5,
                     reply_format="score_marker", max_tokens=200, draft=True,
                     role_overrides=tuple(sorted(V5_ROLE_OVERRIDES.items()))),
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
