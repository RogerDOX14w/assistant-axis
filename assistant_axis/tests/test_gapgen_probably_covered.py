"""'Probably covered by X' (``assistant_axis/gapgen/probably_covered.py``; Roger, 2026-10-20, option (b)): a free
proposed merge for rows M3 read only 2, on synthetic readings: the n >= 2 condition, each branch of the OR (cosine,
dictionary link, persona space), the choice of X, and never on a covered row or a row read 3."""
from __future__ import annotations

from assistant_axis.gapgen import probably_covered as PC


def rd(stem, s, o=None, *, cos=0.4, rel="similar", queue=False):
    r = {"stem": stem, "cosine": cos, "relation": rel, "sonnet": {"value": s}, "opus": {"value": o} if o is not None
         else None}
    if queue:
        r["queue_status"] = "candidate"
    return r


def row(readings, *, decision="new", lexical=None, persona=None):
    r = {"key": "x#1", "novelty": {"decision": decision, "readings": readings, "listed": [
        {k: v for k, v in x.items() if k in ("stem", "cosine", "relation", "queue_status")} for x in readings]}}
    if lexical is not None:
        r["lexical"] = {"links": lexical}
    if persona is not None:
        r["persona"] = persona
    return r


def test_the_thresholds_are_named():
    assert PC.PROBABLY_COVERED_MIN_READ_2 == 2 and PC.PROBABLY_COVERED_MIN_COSINE == 0.45


def test_the_cosine_branch_and_the_choice_of_x():
    out = PC.probably_covered(row([rd("alpha", 2, cos=0.40), rd("beta", 1, 2, cos=0.50), rd("gamma", 1, cos=0.9)]))
    # gamma reads 1 (not 2): not counted, and never X however close
    assert out == {"probably_covered_by": "trait:beta", "n_read_2": 2, "read_2": ["trait:alpha", "trait:beta"],
                   "why": [{"kind": "cosine", "key": "trait:beta", "cosine": 0.5}]}


def test_at_least_two_traits_read_2():
    assert PC.probably_covered(row([rd("alpha", 2, cos=0.6), rd("beta", 1, cos=0.6)])) is None
    assert PC.probably_covered(row([rd("alpha", 2, cos=0.6)], persona={"flag": "duplicate_like"})) is None


def test_the_dictionary_branch():
    rs = [rd("alpha", 2, cos=0.30), rd("calm_q", 2, cos=0.35, queue=True)]
    assert PC.probably_covered(row(rs)) is None                              # no branch holds
    lex = [{"stem": "calm_q", "kind": "queue", "lexicon": "oewn", "link": "similar_to", "listed_by_m3": True},
           {"stem": "unrelated", "lexicon": "moby", "link": "synonym"}]
    out = PC.probably_covered(row(rs, lexical=lex))
    assert out["probably_covered_by"] == "queue:calm_q"                       # the highest cosine read 2
    assert out["why"] == [{"kind": "dictionary", "key": "queue:calm_q", "lexicon": "WordNet", "link": "similar_to"}]


def test_the_persona_branch():
    rs = [rd("alpha", 2, cos=0.30), rd("beta", 2, cos=0.20)]
    assert PC.probably_covered(row(rs, persona={"flag": "ordinary"})) is None
    out = PC.probably_covered(row(rs, persona={"flag": "duplicate_like"}))
    assert out["probably_covered_by"] == "trait:alpha" and out["why"] == [{"kind": "persona"}]


def test_only_rows_read_at_most_2_and_kept():
    rs = [rd("alpha", 2, cos=0.6), rd("beta", 2, cos=0.6)]
    assert PC.probably_covered(row(rs))["n_read_2"] == 2
    assert PC.probably_covered(row(rs + [rd("delta", 2, 3, cos=0.1)])) is None        # a 3 by either model
    assert PC.probably_covered(row(rs, decision="covered")) is None                   # never on a covered row
    assert PC.probably_covered(row(rs + [rd("eps", 4, cos=0.1, rel="opposed")]))["n_read_2"] == 2   # opposed ignored
    assert PC.probably_covered({}) is None
