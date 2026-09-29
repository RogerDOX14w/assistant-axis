"""Every rubric prompt's version, pinned to the sha256 of its text.

The rule (coordinator's ruling on QUESTIONS 17, 2026-09-29): **a version number
identifies one prompt text.**  Any change to a prompt's text after a paid run
has recorded the current version needs a new version: bump the module's
version constant and add a row here.  :data:`HISTORY` is append-only; a
recorded run is told apart from another by its ``rubric_version`` and its
``prompt_sha256``, both stamped on every block.  ``test_gapgen_rubric_v2_round3.
py::TestVersionPins`` fails when a prompt's text changes without its version
and its pinned hash changing.

"Rubric v2" is the name of the change set of decisions_m1.md, not a version of
any one prompt.  Before this table existed the classifier's version 2 stood for
three texts: ``ba7a4316...`` (withdrawn intermediate, round-1 smoke runs, each
marked WITHDRAWN_PROMPT.md), ``2b5b298e...`` (committed in round 1, never run)
and ``9c75829d...`` (round 2, run in ``m2rubric_r2_classifier``).  The table
pins version 2 to the last, the only committed v2 text a run recorded.
"""
from __future__ import annotations

import hashlib

#: prompt name -> {version: sha256 of the prompt text}.  Append only.
HISTORY: dict[str, dict[int, str]] = {
    "classifier": {
        1: "113bde981420d93fc58b41b0b6cf12785537a3186588cc3289ef6e9edd8da2a5",
        2: "9c75829d4ed33a752e012b10feb2845ade11dbb234dc3131aa8b98d7616a5032",
        3: "f9af4e2d13bceca2c2d2044f8debf838509eedecbac799209f0fc57fd3e7b112",
    },
    "probe": {
        1: "d5ba66e82026137af301cded277f039f03269910eb4b8542ef7c0425f414d4e1",
        2: "0785cd073e2cd2b62f412b379e003cdc39fdf54f360a99dc517dd2621add0103",
        3: "23327ebd9eb1ae4c1992b2a9ce89ed30ca955b65706017a80ccf87931fbf4116",
    },
    "states_queue": {
        1: "4a51b9159951607dc5094b5ca80de0c4cb753f8a41e77fefc9a9ae21e6a7711e",
        2: "66b1bebc643001fc6517fdf6ac49a9036d64c753c8382b0578b9509a7c9caaf4",
    },
    "states_corpus": {
        1: "20d6a63e15d73855aad6a0041fda29ec4d8b51bfa9afd47a5d0e96dd08d4b261",
    },
    "plain_reading": {
        1: "e977750502a3c25b7fb63986eb9670a90aae92a65b41d06cdfed23d9fa2770f6",
    },
    "comparison": {
        1: "81ca2459d080717f6915ead6ccfe3933f6c9b83a4da1f4de4d98550514f6174b",  # m2rubric_r3_dev_sonnet_v1
        2: "a6f5cbc6514e6108a010304e8f18012260263dfd2aa0c913439055b33df932e3",
    },
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current() -> dict[str, tuple[int, str]]:
    """``{prompt name: (version constant, sha256 of the prompt text)}`` as the
    code stands now."""
    from . import filter_rubric as fr
    from . import plain_reading as pr
    from . import states_pass as sp
    return {
        "classifier": (fr.TRAITHOOD_RUBRIC_VERSION, _sha(fr.SYSTEM_PROMPT)),
        "probe": (fr.PROBE_RUBRIC_VERSION, _sha(fr.DEFINE_PROBE_PROMPT)),
        "states_queue": (sp.RUBRIC_VERSIONS["queue"], _sha(sp.QUEUE_PROMPT)),
        "states_corpus": (sp.RUBRIC_VERSIONS["corpus"], _sha(sp.CORPUS_PROMPT)),
        "plain_reading": (pr.READING_VERSION, _sha(pr.READING_PROMPT)),
        "comparison": (pr.COMPARISON_VERSION, _sha(pr.COMPARISON_PROMPT)),
    }


def mismatches() -> list[str]:
    """Human-readable problems; empty when every prompt's text is the one its
    version is pinned to."""
    out = []
    for name, (version, sha) in current().items():
        pinned = HISTORY.get(name, {}).get(version)
        if pinned is None:
            out.append(f"{name}: version {version} is not in rubric_versions.HISTORY (add it with sha {sha})")
        elif pinned != sha:
            out.append(f"{name}: text changed (sha {sha[:12]}...) but version {version} is pinned to "
                       f"{pinned[:12]}...: bump the version and add a row to HISTORY")
    return out
