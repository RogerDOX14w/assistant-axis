"""Registry keys in role mode (coding plan 16, § 6.1 and test 1): a role-aimed row of a surface that has a trait row
is a second row keyed by entity type, ``optimist|R#1`` beside ``optimist#1`` (entity-naming rule: never merge a
trait and a role by bare name)."""
import re

import pytest

from assistant_axis.gapgen import normalize as N


def test_make_key_by_entity_type():
    assert N.make_key("optimist", 1, "role") == "optimist|R#1"
    assert N.make_key("optimist", 2, "role") == "optimist|R#2"
    assert N.make_key("optimist", 1, "trait") == "optimist#1"
    assert N.make_key("optimist") == "optimist#1"                  # the default is a trait key, as before
    with pytest.raises(ValueError):
        N.make_key("optimist", 1, "monster")


def test_parse_key_round_trips_both_forms():
    for key in ("optimist#1", "optimist|R#1", "devils_advocate|R#2", "world_shaping#3"):
        stem, sid, et = N.parse_key(key)
        assert N.make_key(stem, sid, et) == key
    assert N.parse_key("optimist|R#1") == ("optimist", 1, "role")
    assert N.parse_key("optimist#1") == ("optimist", 1, "trait")


def test_split_key_keeps_its_two_fields_and_gives_the_bare_stem():
    """The callers that read ``split_key(k)[0]`` as the stem (gap_registry, filter, paraphrase_set) get the stem of a
    role key too, never ``optimist|R``."""
    assert N.split_key("world_shaping#1") == ("world_shaping", 1)
    assert N.split_key("optimist|R#1") == ("optimist", 1)
    with pytest.raises(ValueError):
        N.split_key("no_sense_id")


def test_entity_type_of_key():
    assert N.entity_type_of_key("optimist|R#1") == "role"
    assert N.entity_type_of_key("optimist#1") == "trait"
    assert N.is_role_key("baker|R#1") and not N.is_role_key("baker#1")


def test_a_role_key_never_passes_the_trait_stem_rule_unchanged():
    key = N.make_key("optimist", 1, "role")
    head = key.rpartition("#")[0]
    assert not re.match(r"^[a-z0-9]+(?:_[a-z0-9]+)*$", head)         # normalize._STEM_OK_RE's rule
    assert not N._STEM_OK_RE.match(head)
