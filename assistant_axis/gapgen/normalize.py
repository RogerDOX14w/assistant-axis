"""Candidate normalisation and the platform's controlled vocabularies.

:func:`normalize_candidate` turns a generator's raw surface form into the
registry's identity: ``stem`` (file-name form, the key component, via
``entity_id.normalize_to_file_name``), ``label`` (display form, what an LLM or
a human reads), ``surface_lc`` and ``content_words`` (what the frequency
floor looks up).  The vocabularies are those of the registry schema in
``reports/trait_gap_generation/coding_plan_platform.md`` §6.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from assistant_axis.entity_id import normalize_to_file_name

VERDICTS = ("trait", "tagged", "reject")
TAG_VOCAB = ("physical", "state", "transient_only", "demographic", "role_person", "role_thing",
             "evaluative_only", "relational_only", "not_a_word", "too_rare")
REGION_VOCAB = ("communication_style", "cognitive_epistemic", "moral_stance", "social_interpersonal",
                "emotional_temperament", "alignment_ai_agent", "transient_state",
                "identity_demographic", "physical")
HOLDING = (None, "physical", "roles")
ENTITY_TYPES = ("trait", "role")
DECISIONS = ("covered", "new", "grey")
NOVELTY_FLAGS = ("ambiguous_label", "pair_completion", "deliberate_duplicate", "models_disagree",
                 "probe_uncertain")
RELATIONS = ("synonym", "antonym", "related", "unrelated")
REVIEW_STATUSES = ("unreviewed", "accepted", "rejected", "merged", "deferred")

#: Function words skipped when choosing the words whose frequency decides the
#: floor ("kind to animals" is judged on kind and animals).  Fixed list: a
#: change here changes which candidates are hard-rejected.
STOPWORDS = frozenset("""
a an the to of in on at for with by from and or nor but as about into onto over under than
then be being been is are was were am one ones one's oneself self's its it's their them
his her him she he they we you your yours our ours my me i this that these those so not no
very too quite rather more most less least all any each every some such own
""".split())

_WORD_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*", re.UNICODE)
# Characters kept in a surface: letters, digits, space, hyphen, apostrophe,
# parentheses (standard-derived labels), period inside abbreviations is dropped.
_DROP_RE = re.compile(r"[^\w\s\-'’–—()]", re.UNICODE)
_STEM_OK_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

#: Longest accepted surface after cleaning (the longest corpus label is 54
#: characters; a generator emitting a sentence is a bug, not a candidate).
MAX_SURFACE_CHARS = 80


@dataclass(frozen=True)
class Normalized:
    stem: str
    label: str
    surface_lc: str
    content_words: tuple[str, ...]


def clean_surface(surface: str) -> str:
    """Collapse whitespace, turn underscores into spaces, curly apostrophes into
    straight ones, and drop punctuation other than hyphens, apostrophes and
    parentheses; strip leading and trailing hyphens and quotes."""
    s = unicodedata.normalize("NFC", str(surface))
    s = s.replace("’", "'").replace("_", " ")
    s = _DROP_RE.sub(" ", s)
    s = " ".join(s.split())
    return s.strip(" -'")


def content_words(surface_lc: str) -> tuple[str, ...]:
    """Words of a lowercase surface that are not function words (hyphenated
    compounds split into their parts); all words when every word is a
    function word."""
    words = [w for w in _WORD_RE.findall(surface_lc.replace("-", " "))]
    content = [w for w in words if w not in STOPWORDS]
    return tuple(content or words)


def normalize_candidate(surface: str) -> Normalized:
    """Normalise a generator's surface form.

    ``label`` keeps the generator's case, hyphens and diacritics (it is the
    display form: ``"world-shaping"``, ``"Kantian"``); ``stem`` is the ASCII
    file-name form (``"world_shaping"``).  Idempotent:
    ``normalize_candidate(n.label) == n`` for any result ``n``.

    Raises ``ValueError`` when nothing word-like is left.
    """
    label = clean_surface(surface)
    if not label:
        raise ValueError(f"empty candidate surface {surface!r}")
    if len(label) > MAX_SURFACE_CHARS:
        raise ValueError(f"candidate surface longer than {MAX_SURFACE_CHARS} characters: {label[:40]!r}...")
    stem = normalize_to_file_name(label)
    stem = re.sub(r"_+", "_", stem).strip("_")
    if not _STEM_OK_RE.match(stem):
        raise ValueError(f"candidate {surface!r} normalises to an unusable stem {stem!r}")
    surface_lc = label.lower()
    return Normalized(stem=stem, label=label, surface_lc=surface_lc,
                      content_words=content_words(surface_lc))


def make_key(stem: str, sense_id: int = 1) -> str:
    """Registry key ``f"{stem}#{sense_id}"``."""
    return f"{stem}#{int(sense_id)}"


def split_key(key: str) -> tuple[str, int]:
    stem, _, sid = key.rpartition("#")
    if not stem:
        raise ValueError(f"not a registry key: {key!r}")
    return stem, int(sid)
