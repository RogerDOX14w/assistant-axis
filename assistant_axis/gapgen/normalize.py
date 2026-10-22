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
#: Every tag a filter block may carry.  ``demographic`` is rubric v1 only
#: (memberships became traits in v2, tagged ``membership``); kept so v1
#: records stay valid.
TAG_VOCAB = ("physical", "state", "transient_only", "demographic", "role_person", "role_thing",
             "evaluative_only", "relational_only", "not_a_word", "too_rare", "membership",
             # the split filter's reasons for turning a word away (coding_plan_split.md section 6)
             "no_persona_reading", "stretched", "action")
REGION_VOCAB = ("communication_style", "cognitive_epistemic", "moral_stance", "social_interpersonal",
                "emotional_temperament", "alignment_ai_agent", "transient_state",
                "identity_demographic", "physical")
#: Holding lists: physical (TRAITS_TO_ADD's physical section), roles (roles
#: list), states (the states queue of decision 12), nationalities (memberships
#: of the nationality, ethnicity or language kind: traits, but held apart from
#: the main review list, decision 3 and open point B), states_released (rows the states pass v4 moved out of
#: the states queue, 2026-10-09: they go through M3 and the review app as a pass of their own, ``novelty_score.py
#: score --holding states``, and are promoted only by name, like the physical list's), narrow (the narrow pass,
#: 2026-10-20, QUESTIONS 208 (3): a kept candidate that is a narrower case of a corpus or queue trait whose one
#: narrow child in review is another row; held, not dropped; ``assistant_axis.gapgen.narrow_pass``).
HOLDING = (None, "physical", "roles", "states", "nationalities", "states_released", "narrow")
ENTITY_TYPES = ("trait", "role")
DECISIONS = ("covered", "new", "grey")
NOVELTY_FLAGS = ("ambiguous_label", "pair_completion", "deliberate_duplicate", "models_disagree",
                 "probe_uncertain")
RELATIONS = ("synonym", "antonym", "related", "unrelated")
#: ``merged_into`` (with ``into``) and ``parked`` are what the review app writes (coding_plan_review.md, R2);
#: ``merged`` was listed here before any code wrote it and is gone (2026-10-08).
REVIEW_STATUSES = ("unreviewed", "accepted", "rejected", "merged_into", "parked", "deferred")

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


#: The tag a role-aimed row's key carries after its stem (coding plan 16, § 6.1): ``optimist|R#1`` is the role row
#: of the surface whose trait row is ``optimist#1``.  It is ``entity_id(stem, "roles")``'s suffix, so the key's stem
#: part is the stem's entity id; a trait key carries none (every key written before 2026-10-22 is a trait key in
#: this sense, the held role rows included: ``baker#1``).
ROLE_KEY_TAG = "|R"


def make_key(stem: str, sense_id: int = 1, entity_type: str = "trait") -> str:
    """Registry key: ``f"{stem}#{sense_id}"`` for a trait (the default, as before), and
    ``f"{entity_id(stem, 'roles')}#{sense_id}"`` (``optimist|R#1``) for a role-aimed row (coding plan 16, § 6.1).
    A held role row that M1 routed from a trait-aimed submission keeps its plain key; only a candidate submitted
    in role mode gets the ``|R`` key (``registry.submit_candidates``)."""
    if entity_type == "trait":
        return f"{stem}#{int(sense_id)}"
    if entity_type == "role":
        from assistant_axis.entity_id import entity_id
        return f"{entity_id(stem, 'roles')}#{int(sense_id)}"
    raise ValueError(f"entity_type must be one of {ENTITY_TYPES}, not {entity_type!r}")


def parse_key(key: str) -> tuple[str, int, str]:
    """``(stem, sense_id, entity_type)`` of a registry key: the inverse of :func:`make_key`
    (``make_key(*parse_key(k)) == k``).  A key with no ``|R`` tag is a trait key."""
    head, _, sid = str(key).rpartition("#")
    if not head:
        raise ValueError(f"not a registry key: {key!r}")
    if head.endswith(ROLE_KEY_TAG):
        return head[: -len(ROLE_KEY_TAG)], int(sid), "role"
    return head, int(sid), "trait"


def split_key(key: str) -> tuple[str, int]:
    """``(stem, sense_id)`` of a registry key, the stem bare (``optimist|R#1`` gives ``("optimist", 1)``).  Kept to
    two fields (its callers unpack two and read ``[0]`` as the stem); :func:`parse_key` adds the entity type."""
    stem, sid, _ = parse_key(key)
    return stem, sid


def entity_type_of_key(key: str) -> str:
    """``role`` for a key made in role mode (``optimist|R#1``), else ``trait``.  The row's own ``entity_type`` is what
    the pipeline acts on: a held role row has a plain key and ``entity_type: "role"``."""
    return parse_key(key)[2]


def is_role_key(key: str) -> bool:
    return entity_type_of_key(key) == "role"
