"""Disambiguated entity identifiers for trait/role mixing contexts.

The project's corpus has 9 names that appear in *both* the trait and
role lists -- ``ascetic``, ``contrarian``, ``cosmopolitan``,
``generalist``, ``pacifist``, ``patient``, ``perfectionist``,
``romantic``, ``stoic``.  Bare names are therefore *not* a unique
identifier in any context that mixes kinds (dict keys, set members,
JSON cache keys, sorted name lists for rho computation, ...).
Historically several sites silently dropped one side of every
collision via the dict-overwrite ``merged[name] = ...`` pattern,
biasing rho calculations by ~1.5 %.

This module provides the canonical disambiguator: pipe-suffixed
single-letter kind tags.

    >>> entity_id("patient", "roles")
    'patient|R'
    >>> entity_id("patient", "T")
    'patient|T'
    >>> parse_entity_id("patient|R")
    EntityId(name='patient', kind='roles')
    >>> display_label("patient|R")
    'patient'

Use ``entity_id(name, kind)`` whenever a data structure could
plausibly contain entries from both kinds.  Use ``display_label(eid)``
on the *display* side to strip the suffix; encode kind visually via
the helpers in :mod:`assistant_axis.plot_palette` (``kind_color``,
``kind_marker``, ...).

Pure-kind contexts (e.g. inside a ``runpod_workspace/.../roles/``
directory, or a per-cohort ``haiku_responses_traits_*/`` cache) keep
bare names; the kind is implicit in the path.

See ``AGENT_NOTES.md`` (section "Trait/role name collisions") for
the full convention and pitfalls.
"""
from __future__ import annotations

from typing import NamedTuple

__all__ = [
    "EntityId",
    "KIND_R",
    "KIND_T",
    "KIND_LONG",
    "entity_id",
    "parse_entity_id",
    "is_entity_id",
    "display_label",
    "kind_short",
    "kind_long",
    "ID_SEPARATOR",
    "normalize_to_file_name",
    "display_form_name",
]


# Canonical short tags used inside the disambiguated id.
KIND_R: str = "R"  # role
KIND_T: str = "T"  # trait

# Canonical long-form kind tokens used elsewhere in the project
# (matching ``--pair_type {traits,roles}`` and the corpus directory
# names ``runpod_workspace/.../{roles,traits}/``).
_KIND_ROLES = "roles"
_KIND_TRAITS = "traits"

#: Maps the short tag back to the long-form kind token used elsewhere
#: in the project.  Use :func:`kind_long` rather than indexing this
#: dict directly when you have a short tag in hand.
KIND_LONG: dict[str, str] = {KIND_R: _KIND_ROLES, KIND_T: _KIND_TRAITS}

# Accepted spellings for each kind on input (normalised before
# resolving to the canonical short tag).  Lower-case keys; callers
# may pass any case.
_KIND_ALIASES_TO_SHORT: dict[str, str] = {
    "r": KIND_R,
    "role": KIND_R,
    "roles": KIND_R,
    "t": KIND_T,
    "trait": KIND_T,
    "traits": KIND_T,
}

#: The separator character between name and short-kind tag.
ID_SEPARATOR: str = "|"


class EntityId(NamedTuple):
    """The parsed pieces of a disambiguated entity id.

    ``name`` is the bare entity name (e.g. ``"patient"``); ``kind`` is
    the canonical long-form kind token (``"roles"`` or ``"traits"``)
    matching the rest of the project's vocabulary (corpus
    subdirectories, ``--pair_type`` CLI argument, etc.).
    """
    name: str
    kind: str  # "roles" or "traits"


def kind_short(kind: str) -> str:
    """Normalise a kind token to its canonical short tag (``"R"`` or
    ``"T"``).

    Accepts: ``"R"``, ``"T"``, ``"role"``, ``"roles"``, ``"trait"``,
    ``"traits"`` (any case).  Raises :class:`ValueError` on anything
    else.
    """
    if not isinstance(kind, str):
        raise ValueError(
            f"entity_id: kind must be a string, got {type(kind).__name__} "
            f"({kind!r})"
        )
    norm = kind.strip().lower()
    if norm not in _KIND_ALIASES_TO_SHORT:
        raise ValueError(
            f"entity_id: unknown kind {kind!r}; accepted: "
            f"{sorted(_KIND_ALIASES_TO_SHORT)}"
        )
    return _KIND_ALIASES_TO_SHORT[norm]


def kind_long(kind: str) -> str:
    """Normalise a kind token to its canonical long-form name
    (``"roles"`` or ``"traits"``).

    Accepts the same set of spellings as :func:`kind_short`.
    """
    return KIND_LONG[kind_short(kind)]


def entity_id(name: str, kind: str) -> str:
    """Return the canonical disambiguated id for ``(name, kind)``.

    The format is ``"<name>|R"`` for roles, ``"<name>|T"`` for traits.
    The name itself must not contain the pipe separator.

    Args:
        name: Bare entity name (e.g. ``"patient"``).
        kind: Any accepted kind token (``"R"``, ``"T"``, ``"role"``,
            ``"roles"``, ``"trait"``, ``"traits"``; case-insensitive).

    Raises:
        ValueError: If ``name`` is empty, contains :data:`ID_SEPARATOR`,
            or if ``kind`` isn't recognised.

    >>> entity_id("patient", "roles")
    'patient|R'
    >>> entity_id("patient", "T")
    'patient|T'
    >>> entity_id("patient", "Roles")
    'patient|R'
    """
    if not isinstance(name, str):
        raise ValueError(
            f"entity_id: name must be a string, got {type(name).__name__} "
            f"({name!r})"
        )
    if not name:
        raise ValueError("entity_id: name must not be empty")
    if ID_SEPARATOR in name:
        raise ValueError(
            f"entity_id: name {name!r} contains the reserved separator "
            f"{ID_SEPARATOR!r}; this would make the id ambiguous on parse."
        )
    return f"{name}{ID_SEPARATOR}{kind_short(kind)}"


def parse_entity_id(eid: str) -> EntityId:
    """Parse a disambiguated entity id into its (name, kind) pieces.

    Args:
        eid: The disambiguated id (e.g. ``"patient|R"``).

    Returns:
        :class:`EntityId` with ``kind`` resolved to its long-form
        name (``"roles"`` or ``"traits"``).

    Raises:
        ValueError: If ``eid`` is not a string, lacks the separator,
            has more than one separator, has an empty name, or has an
            unknown short tag.

    >>> parse_entity_id("patient|R")
    EntityId(name='patient', kind='roles')
    >>> parse_entity_id("perfectionist|T")
    EntityId(name='perfectionist', kind='traits')
    """
    if not isinstance(eid, str):
        raise ValueError(
            f"parse_entity_id: expected str, got {type(eid).__name__} "
            f"({eid!r})"
        )
    parts = eid.split(ID_SEPARATOR)
    if len(parts) != 2:
        raise ValueError(
            f"parse_entity_id: {eid!r} is not a disambiguated id; "
            f"expected exactly one {ID_SEPARATOR!r} separator, found "
            f"{len(parts) - 1}."
        )
    name, short = parts
    if not name:
        raise ValueError(
            f"parse_entity_id: {eid!r} has an empty name component."
        )
    if short not in KIND_LONG:
        raise ValueError(
            f"parse_entity_id: {eid!r} has unknown kind tag {short!r}; "
            f"accepted: {sorted(KIND_LONG)}."
        )
    return EntityId(name=name, kind=KIND_LONG[short])


def is_entity_id(s: object) -> bool:
    """Return ``True`` iff ``s`` parses as a disambiguated entity id.

    Lets call sites probe a string without try/except scaffolding.
    A bare name like ``"patient"`` returns ``False``; ``"patient|R"``
    returns ``True``.
    """
    if not isinstance(s, str):
        return False
    try:
        parse_entity_id(s)
    except ValueError:
        return False
    return True


def display_label(eid_or_name: str) -> str:
    """Return the bare display name from either a disambiguated id or
    a bare name.

    Plots, axis labels, legends, console output etc. should call this
    on the dict key so the visible label is always the bare name --
    kind is encoded visually via colour/marker (see
    :mod:`assistant_axis.plot_palette`).

    Bare names are passed through unchanged, so this is safe to call
    on ids of unknown provenance.

    >>> display_label("patient|R")
    'patient'
    >>> display_label("teacher")  # already bare
    'teacher'
    """
    if is_entity_id(eid_or_name):
        return parse_entity_id(eid_or_name).name
    return eid_or_name


def normalize_to_file_name(name: str) -> str:
    """Normalise a possibly display-form entity name to file-name form.

    Project convention is **file-name form everywhere except display
    sites** (see ``AGENT_NOTES.md`` ``File-name vs display-name
    convention``).  External inputs (user-supplied JSONs, CSVs, CLI
    args copy-pasted from a plot label) sometimes leak in the
    display form -- spaces, hyphens, capitals, apostrophes -- which
    silently misses on every multi-word entity in the corpus
    (~3 % of names: ``aligned_artificial_intelligence``,
    ``systems_thinker``, ``devils_advocate``, ...).

    This helper performs the minimal canonical conversion so
    boundary code can normalise once and treat the result like any
    other file-name key.  The transform is:

    1. Lowercase.
    2. Strip surrounding whitespace.
    3. Drop apostrophes (``devil's advocate`` -> ``devils advocate``)
       so the output matches the file-name form
       ``devils_advocate`` rather than the typo ``devil_s_advocate``.
    4. Collapse runs of whitespace and hyphens into single
       underscores.

    The function is **idempotent**: file-name input passes through
    unchanged.

    Detection (did anything change?) is just
    ``normalize_to_file_name(s) != s``; callers should log a warning
    on conversion so the user is aware their input was massaged.

    Examples
    --------
    >>> normalize_to_file_name("aligned_artificial_intelligence")
    'aligned_artificial_intelligence'
    >>> normalize_to_file_name("aligned artificial intelligence")
    'aligned_artificial_intelligence'
    >>> normalize_to_file_name("Aligned Artificial Intelligence")
    'aligned_artificial_intelligence'
    >>> normalize_to_file_name("devil's advocate")
    'devils_advocate'
    >>> normalize_to_file_name("systems-thinker")
    'systems_thinker'
    >>> normalize_to_file_name("  multi   word   ")
    'multi_word'
    """
    import re
    s = name.strip().lower()
    s = s.replace("'", "").replace("\u2019", "")  # ASCII + curly apostrophe
    s = re.sub(r"[\s\-]+", "_", s)
    return s


def display_form_name(name: str) -> str:
    """Convert a file-name-form entity name to display form for
    rendering to humans **and LLMs**.

    Display sites are anywhere we render an entity name to a human
    or an LLM: plot labels, axis annotations, legends, console
    output, *and the body of LLM rubrics/prompts* (LLMs read e.g.
    ``aligned artificial intelligence`` more naturally than
    ``aligned_artificial_intelligence``, and judging accuracy
    measurably depends on how clearly the entity is described).
    See ``AGENT_NOTES.md`` ``File-name vs display-name convention``.

    The transform is the **minimal** one that round-trips through
    :func:`normalize_to_file_name` for plain underscored names:
    just ``_`` → space.  Capitalisation is preserved (the display
    side is where humans/LLMs decide on case).  Apostrophes are
    not re-introduced (the file-name form is lossy in that
    direction; we accept ``devils advocate`` as the displayed
    form, which is fine for both readers and LLMs).

    The function is **idempotent**: display-form input
    (``"aligned artificial intelligence"``, ``"systems-thinker"``,
    or any name without underscores) passes through unchanged.

    Disambiguated ids (``patient|R``) are passed through untouched
    so callers don't have to special-case them; downstream code
    typically applies :func:`display_label` to strip the suffix
    and *then* :func:`display_form_name` for the underscore swap.

    Examples
    --------
    >>> display_form_name("aligned_artificial_intelligence")
    'aligned artificial intelligence'
    >>> display_form_name("systems_thinker")
    'systems thinker'
    >>> display_form_name("devils_advocate")
    'devils advocate'
    >>> display_form_name("patient")
    'patient'
    >>> display_form_name("aligned artificial intelligence")
    'aligned artificial intelligence'
    >>> display_form_name("patient|R")
    'patient|R'
    """
    if "|" in name and name.rsplit("|", 1)[1] in ("R", "T"):
        return name
    return name.replace("_", " ")
