"""Word-level hygiene for the platform's prompts (review_rubric_v2.md finding 10).

Rubric examples must not be corpus labels, seed-queue entries, validation-file
words, the six September rejects, or words reserved by the decisions file and
the "You are X." probe.  The tests check the declared example words against all
of these, and every word of every prompt against the corpus, the queue and the
validation file.  Some such words are ordinary English the prompts cannot do
without ("kind" in "the sense's kind", "general" in "a general word of
approval").  They are listed in :data:`PROSE_ALLOWED`, each only as prose: a
test checks that none of them appears as a quoted example.  Adding a word here
is a decision to record in the commit message.
"""
from __future__ import annotations

import re

_TOKEN = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*")

#: Words that occur in the prompts as ordinary prose although they are corpus
#: labels, queue entries or validation-file words.  Never examples.
_PROSE = """
answering assistant common decided elected emotional enough every everyday false far general good judge kind
language literal married moral native new no practical rejected returning short stable straight two young
formed scientific technical
"""
#: Words in the comparison prompt's example readings and meanings.  That prompt
#: is frozen after the held-out run (coordinator, round 4; review section 6),
#: so its hits are recorded here rather than changed.
_FROZEN_COMPARISON = "competitive extreme fair generous modest running unpopular writer"
PROSE_ALLOWED: frozenset[str] = frozenset(_PROSE.split() + _FROZEN_COMPARISON.split())


def prompt_words(text: str) -> set[str]:
    """Lowercase word tokens of a prompt; a hyphenated token is kept whole
    and its parts are added."""
    out = set()
    for t in _TOKEN.findall(text):
        t = t.lower()
        out.add(t)
        if "-" in t:
            out.update(p for p in t.split("-") if p)
    return out
