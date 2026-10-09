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
        4: "51854ac5300e55943870c2eccfe6b125b33d4a9bf54f01fec9b1775c8f018d42",
        # 2026-10-02, merge with the main line: the "soft" example's "mild and lenient" became "mild
        # and undemanding" (lenient is now a corpus trait).  No 5: a split filter block's
        # rubric_version is 5, and the seed queue's gap_gen keeps that number without the pipeline.
        # Not run yet.
        6: "138c165167f680c46314f6f9f4c6a6b40831bd12fe965faf533d3931757a878a",
    },
    "probe": {
        1: "d5ba66e82026137af301cded277f039f03269910eb4b8542ef7c0425f414d4e1",
        2: "0785cd073e2cd2b62f412b379e003cdc39fdf54f360a99dc517dd2621add0103",
        3: "23327ebd9eb1ae4c1992b2a9ce89ed30ca955b65706017a80ccf87931fbf4116",
    },
    "states_queue": {
        1: "4a51b9159951607dc5094b5ca80de0c4cb753f8a41e77fefc9a9ae21e6a7711e",
        2: "66b1bebc643001fc6517fdf6ac49a9036d64c753c8382b0578b9509a7c9caaf4",  # never run
        3: "6790603bcdfabafa97db968a3fc832ec17a5f64dd487b84258b3fc892b86fd3d",
        # 2026-10-09 (Roger): the duration question and its narrative test, the role question for a lasting
        # condition (the kind call's own definition), new examples
        4: "e2765bbd7f921ecfe22370ae6229af4db79bd09426543fc53fcef649a17f97d6",
    },
    # the states pass's gloss check (2026-10-09): one gloss a call, read as lasting, predisposition or passing
    "states_check": {
        1: "c230335cc8075d4ec38d746ea2d49e82600bd871fb9e70bc6f42fe2cfc079696",
    },
    "states_corpus": {
        1: "20d6a63e15d73855aad6a0041fda29ec4d8b51bfa9afd47a5d0e96dd08d4b261",
        2: "bf464b84828919798b8055e4153968161b9a06571fe86c8f651a80ce8b314bb1",
    },
    "plain_reading": {
        1: "e977750502a3c25b7fb63986eb9670a90aae92a65b41d06cdfed23d9fa2770f6",
    },
    "comparison": {
        1: "81ca2459d080717f6915ead6ccfe3933f6c9b83a4da1f4de4d98550514f6174b",  # m2rubric_r3_dev_sonnet_v1
        2: "a6f5cbc6514e6108a010304e8f18012260263dfd2aa0c913439055b33df932e3",
    },
    # M2 calibration's paid criteria (calibrate_llm.py); built, not run before Roger's pilot decision
    "calibration_paraphrase": {
        1: "02542c4d2533da8dd7bbc41b35b134914994e359fe14f55cdd8d220f91ffa1ef",  # never run
        2: "4bae6e964cd48a4bf12d9c9a81632b7f243881e9afa084d140c25c8e17ae39ff",  # reason before the rewrite
    },
    # round 4 (2026-10-02): two more paraphrase styles for the larger recall test
    "calibration_paraphrase_plain": {
        1: "fbf76cf86e02a7770f3791d17de9d32748c021a3edb2600c068b8782b3efe614",
    },
    "calibration_paraphrase_terse": {
        1: "f991a03eecd58e12bc60d72a495e7ed333ffc082896902effa24e2f199079fb2",
    },
    "calibration_blinded": {
        1: "5f4f8f39073f09130bec58c1113c0c25805b91ff581964619992e1d88304954a",
    },
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current() -> dict[str, tuple[int, str]]:
    """``{prompt name: (version constant, sha256 of the prompt text)}`` as the
    code stands now."""
    from . import calibrate_llm as cl
    from . import filter_rubric as fr
    from . import plain_reading as pr
    from . import states_pass as sp
    return {
        "classifier": (fr.TRAITHOOD_RUBRIC_VERSION, _sha(fr.SYSTEM_PROMPT)),
        "probe": (fr.PROBE_RUBRIC_VERSION, _sha(fr.DEFINE_PROBE_PROMPT)),
        "states_queue": (sp.RUBRIC_VERSIONS["queue"], _sha(sp.QUEUE_PROMPT)),
        "states_corpus": (sp.RUBRIC_VERSIONS["corpus"], _sha(sp.CORPUS_PROMPT)),
        "states_check": (sp.CHECK_RUBRIC_VERSION, _sha(sp.CHECK_PROMPT)),
        "plain_reading": (pr.READING_VERSION, _sha(pr.READING_PROMPT)),
        "comparison": (pr.COMPARISON_VERSION, _sha(pr.COMPARISON_PROMPT)),
        "calibration_paraphrase": (cl.PARAPHRASE_PROMPT_VERSION, _sha(cl.PARAPHRASE_PROMPT)),
        "calibration_paraphrase_plain": (cl.PARAPHRASE_STYLE_VERSIONS["plain"], _sha(cl.paraphrase_prompt("plain"))),
        "calibration_paraphrase_terse": (cl.PARAPHRASE_STYLE_VERSIONS["terse"], _sha(cl.paraphrase_prompt("terse"))),
        "calibration_blinded": (cl.BLINDED_PROMPT_VERSION, _sha(cl.BLINDED_PROMPT)),
    }


def mismatches() -> list[str]:
    """Human-readable problems; empty when every prompt's text is the one its
    version is pinned to.  Covers the split filter's eight prompts too, whose
    pins live in ``reports/trait_gap_generation/rubrics/versions.json``
    (:func:`assistant_axis.gapgen.split_rubrics.mismatches`); their problems
    are prefixed ``split.``."""
    out = []
    for name, (version, sha) in current().items():
        pinned = HISTORY.get(name, {}).get(version)
        if pinned is None:
            out.append(f"{name}: version {version} is not in rubric_versions.HISTORY (add it with sha {sha})")
        elif pinned != sha:
            out.append(f"{name}: text changed (sha {sha[:12]}...) but version {version} is pinned to "
                       f"{pinned[:12]}...: bump the version and add a row to HISTORY")
    from . import split_rubrics
    out.extend(f"split.{p}" for p in split_rubrics.mismatches())
    return out
