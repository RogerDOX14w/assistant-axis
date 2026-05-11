"""Tests for ``assistant_axis.entity_id``.

The 9 known content-bearing collision names (May 2026 corpus audit)
are covered explicitly so a future regression to bare-name keys is
caught by name.
"""
import pytest

from assistant_axis.entity_id import (
    EntityId,
    ID_SEPARATOR,
    KIND_LONG,
    KIND_R,
    KIND_T,
    display_label,
    entity_id,
    is_entity_id,
    kind_long,
    kind_short,
    parse_entity_id,
)


COLLISION_NAMES = [
    "ascetic",
    "contrarian",
    "cosmopolitan",
    "generalist",
    "pacifist",
    "patient",
    "perfectionist",
    "romantic",
    "stoic",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_constants():
    assert KIND_R == "R"
    assert KIND_T == "T"
    assert ID_SEPARATOR == "|"
    assert KIND_LONG == {"R": "roles", "T": "traits"}


# ---------------------------------------------------------------------------
# entity_id()
# ---------------------------------------------------------------------------

def test_entity_id_basic_role():
    assert entity_id("patient", "roles") == "patient|R"


def test_entity_id_basic_trait():
    assert entity_id("patient", "traits") == "patient|T"


def test_entity_id_short_kind_tags():
    assert entity_id("patient", "R") == "patient|R"
    assert entity_id("patient", "T") == "patient|T"


def test_entity_id_singular_kind_tokens():
    assert entity_id("patient", "role") == "patient|R"
    assert entity_id("patient", "trait") == "patient|T"


@pytest.mark.parametrize(
    "kind_token,expected",
    [
        ("Roles", "R"),
        ("ROLES", "R"),
        ("rOlEs", "R"),
        ("Traits", "T"),
        ("TRAITS", "T"),
        ("  roles  ", "R"),  # whitespace-tolerant
    ],
)
def test_entity_id_case_and_whitespace(kind_token, expected):
    assert entity_id("foo", kind_token) == f"foo|{expected}"


@pytest.mark.parametrize("name", COLLISION_NAMES)
def test_entity_id_all_collisions_distinguished(name):
    """Each collision name must yield distinct ids for the two kinds."""
    role_id = entity_id(name, "roles")
    trait_id = entity_id(name, "traits")
    assert role_id != trait_id
    assert role_id == f"{name}|R"
    assert trait_id == f"{name}|T"


def test_entity_id_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown kind"):
        entity_id("foo", "rolez")


def test_entity_id_rejects_non_string_kind():
    with pytest.raises(ValueError, match="must be a string"):
        entity_id("foo", 1)  # type: ignore[arg-type]


def test_entity_id_rejects_pipe_in_name():
    with pytest.raises(ValueError, match="reserved separator"):
        entity_id("foo|bar", "R")


def test_entity_id_rejects_empty_name():
    with pytest.raises(ValueError, match="must not be empty"):
        entity_id("", "R")


def test_entity_id_rejects_non_string_name():
    with pytest.raises(ValueError, match="must be a string"):
        entity_id(42, "R")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# parse_entity_id()
# ---------------------------------------------------------------------------

def test_parse_entity_id_basic():
    assert parse_entity_id("patient|R") == EntityId("patient", "roles")
    assert parse_entity_id("patient|T") == EntityId("patient", "traits")


def test_parse_entity_id_named_tuple_fields():
    parsed = parse_entity_id("perfectionist|T")
    assert parsed.name == "perfectionist"
    assert parsed.kind == "traits"


@pytest.mark.parametrize("name", COLLISION_NAMES)
def test_parse_entity_id_collision_round_trip(name):
    for kind in ("roles", "traits"):
        eid = entity_id(name, kind)
        parsed = parse_entity_id(eid)
        assert parsed.name == name
        assert parsed.kind == kind


def test_parse_entity_id_rejects_bare_name():
    with pytest.raises(ValueError, match="not a disambiguated id"):
        parse_entity_id("patient")


def test_parse_entity_id_rejects_extra_separator():
    with pytest.raises(ValueError, match="not a disambiguated id"):
        parse_entity_id("patient|R|extra")


def test_parse_entity_id_rejects_unknown_short_tag():
    with pytest.raises(ValueError, match="unknown kind tag"):
        parse_entity_id("patient|X")


def test_parse_entity_id_rejects_lowercase_short_tag():
    """Short tags are case-sensitive on the parse side; use the long
    form on input if that's what you have."""
    with pytest.raises(ValueError, match="unknown kind tag"):
        parse_entity_id("patient|r")


def test_parse_entity_id_rejects_empty_name():
    with pytest.raises(ValueError, match="empty name"):
        parse_entity_id("|R")


def test_parse_entity_id_rejects_non_string():
    with pytest.raises(ValueError, match="expected str"):
        parse_entity_id(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# is_entity_id()
# ---------------------------------------------------------------------------

def test_is_entity_id_positive():
    assert is_entity_id("patient|R") is True
    assert is_entity_id("patient|T") is True


def test_is_entity_id_negative():
    assert is_entity_id("patient") is False
    assert is_entity_id("patient|X") is False
    assert is_entity_id("patient|R|extra") is False
    assert is_entity_id("") is False
    assert is_entity_id("|R") is False


def test_is_entity_id_non_string():
    assert is_entity_id(42) is False
    assert is_entity_id(None) is False
    assert is_entity_id(["patient", "R"]) is False


# ---------------------------------------------------------------------------
# display_label()
# ---------------------------------------------------------------------------

def test_display_label_strips_disambiguated_id():
    assert display_label("patient|R") == "patient"
    assert display_label("patient|T") == "patient"


def test_display_label_passthrough_for_bare_name():
    assert display_label("teacher") == "teacher"


def test_display_label_passthrough_for_unknown_short_tag():
    """Unrecognised tag → not a valid eid → returned unchanged so we
    don't silently mangle data we don't understand."""
    assert display_label("patient|X") == "patient|X"


# ---------------------------------------------------------------------------
# kind_short / kind_long
# ---------------------------------------------------------------------------

def test_kind_short_idempotent_on_canonical():
    assert kind_short("R") == "R"
    assert kind_short("T") == "T"


def test_kind_long_idempotent_on_canonical():
    assert kind_long("roles") == "roles"
    assert kind_long("traits") == "traits"


def test_kind_long_from_short():
    assert kind_long("R") == "roles"
    assert kind_long("T") == "traits"


def test_kind_short_from_long():
    assert kind_short("roles") == "R"
    assert kind_short("traits") == "T"


# ---------------------------------------------------------------------------
# Use as dict keys: the original motivation
# ---------------------------------------------------------------------------

def test_collision_dict_keeps_both_kinds():
    """Smoke test for the use case the module exists to fix: stick a
    role and a trait with the same bare name into one dict and watch
    them coexist."""
    scores: dict[str, float] = {}
    for name in COLLISION_NAMES:
        scores[entity_id(name, "roles")] = 0.5
        scores[entity_id(name, "traits")] = -0.5
    assert len(scores) == 2 * len(COLLISION_NAMES)
    for name in COLLISION_NAMES:
        assert scores[entity_id(name, "roles")] == 0.5
        assert scores[entity_id(name, "traits")] == -0.5


def test_module_dunder_all_complete():
    """Anything publicly used should be in __all__ so reverse-imports
    don't surprise consumers."""
    import importlib
    import sys

    # Note: ``from assistant_axis import entity_id`` would resolve to
    # the function (re-exported in ``__init__.py``).  Resolve to the
    # actual submodule via ``sys.modules`` to avoid the shadowing.
    importlib.import_module("assistant_axis.entity_id")
    eid_mod = sys.modules["assistant_axis.entity_id"]
    expected = {
        "EntityId", "KIND_R", "KIND_T", "KIND_LONG", "ID_SEPARATOR",
        "entity_id", "parse_entity_id", "is_entity_id",
        "display_label", "kind_short", "kind_long",
        "normalize_to_file_name",
    }
    assert expected.issubset(set(eid_mod.__all__))


# ---------------------------------------------------------------------------
# normalize_to_file_name(): display-form -> file-form input hardening
# ---------------------------------------------------------------------------

from assistant_axis.entity_id import normalize_to_file_name


class TestNormalizeToFileName:
    """Boundary-input hardening: convert display-form names to the
    file-name form used as canonical keys throughout the pipeline.
    See AGENT_NOTES "File-name vs display-name convention"."""

    def test_idempotent_on_file_name_form(self):
        """File-name input passes through unchanged (the common path)."""
        for name in [
            "patient",
            "stoic",
            "aligned_artificial_intelligence",
            "systems_thinker",
            "kind_to_animals",
            "stream_of_consciousness",
            "obama_administration_health_team",
        ]:
            assert normalize_to_file_name(name) == name

    def test_spaces_to_underscores(self):
        assert normalize_to_file_name("aligned artificial intelligence") \
            == "aligned_artificial_intelligence"
        assert normalize_to_file_name("systems thinker") == "systems_thinker"

    def test_hyphens_to_underscores(self):
        assert normalize_to_file_name("systems-thinker") == "systems_thinker"
        assert normalize_to_file_name("obama-administration-health-team") \
            == "obama_administration_health_team"

    def test_lowercases(self):
        assert normalize_to_file_name("Aligned Artificial Intelligence") \
            == "aligned_artificial_intelligence"
        assert normalize_to_file_name("PATIENT") == "patient"

    def test_strips_apostrophes(self):
        """``devil's advocate`` -> ``devils_advocate`` (matches the
        actual file-name form), NOT the underscore-padded
        ``devil_s_advocate``."""
        assert normalize_to_file_name("devil's advocate") == "devils_advocate"

    def test_strips_curly_apostrophe(self):
        """U+2019 (right single quotation mark) is the default from
        word processors / smart-quote auto-replace; treat it the same
        as ASCII apostrophe."""
        assert normalize_to_file_name("devil\u2019s advocate") \
            == "devils_advocate"

    def test_collapses_runs_of_separators(self):
        """Multiple consecutive spaces / hyphens / mixes collapse
        into a single underscore."""
        assert normalize_to_file_name("multi   word") == "multi_word"
        assert normalize_to_file_name("multi - word") == "multi_word"
        assert normalize_to_file_name("a -- b -- c") == "a_b_c"

    def test_strips_outer_whitespace(self):
        assert normalize_to_file_name("  patient  ") == "patient"
        assert normalize_to_file_name("\taligned artificial intelligence\n") \
            == "aligned_artificial_intelligence"

    def test_idempotent_under_double_normalisation(self):
        """Normalising a normalised name is a no-op (important when
        boundary code can't tell whether the caller already
        normalised)."""
        for name in [
            "Aligned Artificial Intelligence",
            "devil's advocate",
            "systems-thinker",
            "  multi   word  ",
        ]:
            once = normalize_to_file_name(name)
            twice = normalize_to_file_name(once)
            assert once == twice

    def test_detection_via_inequality(self):
        """The canonical detection idiom: ``norm != raw`` -> input
        was display-form and got converted; callers should warn."""
        assert normalize_to_file_name("patient") == "patient"
        assert normalize_to_file_name("aligned artificial intelligence") \
            != "aligned artificial intelligence"
        assert normalize_to_file_name("Patient") != "Patient"

    def test_collision_names_unchanged(self):
        """The 9 collision names (Bug A) are all single-word lowercase
        already; normalise must not mangle them."""
        for name in COLLISION_NAMES:
            assert normalize_to_file_name(name) == name


# ---------------------------------------------------------------------------
# display_form_name(): file-form -> display-form for plot labels + LLM rubrics
# ---------------------------------------------------------------------------

from assistant_axis.entity_id import display_form_name


class TestDisplayFormName:
    """File-form -> display-form conversion used at every site that
    renders entity names to a human OR an LLM (plot labels, axis
    annotations, judge rubric body).  See AGENT_NOTES "File-name vs
    display-name convention"."""

    def test_underscore_to_space(self):
        assert display_form_name("aligned_artificial_intelligence") \
            == "aligned artificial intelligence"
        assert display_form_name("systems_thinker") == "systems thinker"
        assert display_form_name("devils_advocate") == "devils advocate"
        assert display_form_name("obama_administration_health_team") \
            == "obama administration health team"

    def test_idempotent_on_display_form(self):
        """Display-form input passes through unchanged (callers don't
        have to track which form they have)."""
        for s in [
            "aligned artificial intelligence",
            "systems thinker",
            "patient",
            "stoic",
        ]:
            assert display_form_name(s) == s

    def test_single_word_passthrough(self):
        """Single-word names (the common case for our v2 axes) are
        invariant: the function is a no-op for ~97 % of corpus
        entries."""
        for name in [
            "patient", "stoic", "ascetic", "harmless", "harmful",
            "helpful", "concise", "verbose",
        ]:
            assert display_form_name(name) == name

    def test_preserves_capitalisation(self):
        """Capitalisation is intentional at the display side (humans
        / LLMs decide on case); the helper does NOT lowercase."""
        assert display_form_name("Patient") == "Patient"
        assert display_form_name("System_Thinker") == "System Thinker"

    def test_disambiguated_id_passthrough(self):
        """``patient|R`` is a canonical id, not a name to render --
        passes through untouched.  Callers that want to render it
        should call ``display_label`` first to strip the suffix and
        then ``display_form_name`` for the underscore swap."""
        assert display_form_name("patient|R") == "patient|R"
        assert display_form_name("patient|T") == "patient|T"
        assert display_form_name("aligned_artificial_intelligence|R") \
            == "aligned_artificial_intelligence|R"

    def test_round_trip_via_normalize(self):
        """``normalize_to_file_name(display_form_name(x)) == x`` for
        plain underscored file-form input.  The reverse is lossy
        when the original had apostrophes (``devil's advocate`` ->
        ``devils_advocate`` -> ``devils advocate``), which is
        documented + fine for display purposes."""
        for file_form in [
            "patient",
            "aligned_artificial_intelligence",
            "systems_thinker",
            "obama_administration_health_team",
        ]:
            display = display_form_name(file_form)
            assert normalize_to_file_name(display) == file_form

    def test_collision_names_unchanged(self):
        """All 9 collision names are single-word; display-form
        rendering must not mangle them."""
        for name in COLLISION_NAMES:
            assert display_form_name(name) == name

    def test_does_not_introduce_apostrophes(self):
        """The helper is the minimal ``_ -> space`` transform; it
        does NOT re-introduce apostrophes that ``normalize_to_file_name``
        stripped (the reverse direction is lossy and that's OK)."""
        assert display_form_name("devils_advocate") == "devils advocate"
        # NOT "devil's advocate"; that would require corpus lookup

    def test_empty_string(self):
        assert display_form_name("") == ""
