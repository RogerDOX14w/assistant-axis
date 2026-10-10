"""Base-model generator, task 3: the six prompt families (entropy injection, header cycling, version pin, no
corpus material)."""
import builtins
import io
import json
import random
import re

import pytest

from assistant_axis.gapgen.generators.base_model import prompts as P
from assistant_axis.gapgen.generators.base_model.seeds import Bio, SeedBundle, SeedWord
from assistant_axis.gapgen.paths import DATA_DIR

ADJ = tuple(SeedWord(w, f"definition of {w}", 0.9) for w in
            ("brave", "blunt", "brash", "stubborn", "gentle", "lazy", "sly", "tidy", "warm", "aloof", "bossy", "meek"))
BUNDLE = SeedBundle(
    adjectives=ADJ,
    bios=(Bio("wikibio:train:0", "Walter Extra", "Walter Extra is a german aerobatic pilot and aircraft designer, "
              "founder of a manufacturer of aerobatic aircraft."),
          Bio("wikibio:train:9", "Ada Short", "Ada Short was a fictional entry with a paragraph long enough.")),
    occupations=("registered nurses", "electricians", "restaurant cooks"),
    nouns=("lighthouse", "spreadsheet", "harvest", "violin", "glacier", "ledger"))


def render_all(n=60, seed=0):
    r = random.Random(seed)
    return [P.render(f, BUNDLE, r) for _ in range(n) for f in P.FAMILIES]


def test_families_and_weights():
    assert P.FAMILIES == ("list", "list_gloss", "person", "contrast", "occupation", "ai_assistant")
    assert set(P.FAMILY_WEIGHTS) == set(P.FAMILIES) and sum(P.FAMILY_WEIGHTS.values()) == pytest.approx(1.0)
    # the AI family is deliberately oversampled (plan 03 section 3): more than an equal share
    assert P.FAMILY_WEIGHTS["ai_assistant"] > 1 / len(P.FAMILIES)
    for f in P.FAMILIES:
        assert len(P.HEADERS[f]) == 10 and len(set(P.HEADERS[f])) == 10


def test_every_family_has_seeds_and_one_constraint():
    for p in render_all():
        assert 2 <= len(p.seeds) <= 3, (p.family, p.seeds)
        assert p.constraint and p.constraint in p.text, p.text
        for s in p.seeds:
            assert s in p.text
        assert p.seed_refs and all(":" in x for x in p.seed_refs)
        assert p.sha256 == P.sha256_text(p.text)
    persons = [p for p in render_all() if p.family == "person"]
    assert all(any(x.startswith("wikibio:") for x in p.seed_refs) for p in persons)
    contrasts = [p for p in render_all() if p.family == "contrast"]
    assert all(p.partner_seed in p.seeds and p.partner_seed in p.text for p in contrasts)
    assert all(p.partner_seed is None for p in render_all() if p.family != "contrast")


def test_letter_constraint_draws_matching_seeds():
    r = random.Random(3)
    hits = 0
    for _ in range(400):
        p = P.render("list", BUNDLE, r)
        m = re.search(r"beginning with the letter ([a-z])", p.constraint)
        if m:
            hits += 1
            assert all(s.startswith(m.group(1)) for s in p.seeds) or \
                sum(a.word.startswith(m.group(1)) for a in ADJ) < len(p.seeds)
    assert hits > 0


def test_header_variants_cycle():
    for f in P.FAMILIES:
        seen = [P.render(f, BUNDLE, random.Random(i), variant=i).header_variant for i in range(20)]
        assert seen == [i % 10 for i in range(20)]
        texts = {P.render(f, BUNDLE, random.Random(0), variant=i).text for i in range(10)}
        assert len(texts) == 10


def test_sha_stable_for_a_fixed_rng():
    a = [p.text for p in render_all(seed=5)]
    b = [p.text for p in render_all(seed=5)]
    c = [p.text for p in render_all(seed=6)]
    assert a == b and a != c


def test_version_pin_covers_every_wording():
    """A wording change (headers, frames, constraints, weights, templates) must bump PROMPTS_VERSION and record
    the new hash in PROMPT_HASHES; the old hashes stay (append-only)."""
    assert P.PROMPT_HASHES[P.PROMPTS_VERSION] == P.wording_sha256()
    assert sorted(P.PROMPT_HASHES) == list(range(1, P.PROMPTS_VERSION + 1))


def test_renderer_reads_no_files(monkeypatch):
    opened = []
    real = builtins.open

    def watch(f, *a, **k):
        opened.append(str(f))
        return real(f, *a, **k)
    monkeypatch.setattr(builtins, "open", watch)
    monkeypatch.setattr(io, "open", watch)
    render_all(20)
    assert opened == []


def _corpus_names() -> set[str]:
    names = set()
    for kind in ("traits", "roles"):
        for p in (DATA_DIR / kind / "instructions").glob("*.json"):
            names.add(p.stem.replace("_", " "))
            if kind == "traits":
                lab = json.loads(p.read_text(encoding="utf-8")).get("positive_label")
                if lab:
                    names.add(str(lab).lower())
    from assistant_axis.entity_id import ROLE_DISPLAY_OVERRIDES
    names |= {v.lower() for v in ROLE_DISPLAY_OVERRIDES.values()}
    return {n for n in names if n}


def test_ai_family_names_no_corpus_entity():
    names = _corpus_names()
    assert len(names) > 900                       # the real corpus is there
    fixed = list(P.HEADERS["ai_assistant"]) + [c.replace("{letter}", "x") for c in P.AI_CONSTRAINTS] + \
        [P.AI_TEMPLATE.format(header="", constraint="", nouns="")]
    hits = sorted({(n, t) for t in fixed for n in names if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", t.lower())})
    assert hits == []


def test_no_corpus_label_enters_a_prompt():
    """The renderer only sees the bundle: a corpus-only string never appears, whatever the draws."""
    for p in render_all(100):
        assert "zorbish" not in p.text and "This means" not in p.text
