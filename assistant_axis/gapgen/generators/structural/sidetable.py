"""The ``position`` side table and the negative-label mismatches (plan sections 6 and 7, ``sidetable.py``; task 10).

``position_table.jsonl`` (:data:`.POSITION_TABLE_PATH`, tracked) has one row per corpus trait operated on (a full
answer; a principal-only answer has no position): the trait's ``position`` (``deficiency``, ``mean``, ``excess``,
``not_scalar``; the majority of its samples, each sample's beside it), its recorded ``negative_label``, the model's
blind opposites (the union of the samples, each with its support), the comparison of the two
(:func:`compare_negative_label`), the model's reasoning, and the run, model, prompt hash and time.  It is rebuilt
deterministically from the runs' responses, snapshotted to ``.bak.<UTC>`` when it changes, and **never written into
a trait file** (Roger, 2026-10-12: a side table until the pairing review; TODO (Roger): review its promotion into
``arrangement`` once the pairing review is done).

``negative_label_check``: ``match`` (the recorded label's stem, or its bare label's without a standard's suffix,
equals the model's opposite's, after the same folding as the operator table), ``mismatch`` (a real-word label recorded and another word returned, or no opposite
returned), ``placeholder`` (``non-X`` recorded), ``none_recorded``.  The mismatches are rendered to
``negative_label_mismatches.md`` (:data:`.MISMATCH_PATH`) with both words and the model's reasoning, for the pairing
review.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.registry import utc_stamp

from . import POSITION_TABLE_PATH, SCHEMA_VERSION
from .operators import OperatorReply
from .postprocess import Corpus, stem_of

CHECKS: tuple[str, ...] = ("match", "mismatch", "placeholder", "none_recorded")
#: A standard's parenthesised suffix ("careless (HEXACO)"): a blind opposite "careless" matches the bare label.
_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _stem(label: Optional[str], lexicon) -> Optional[str]:
    if not label:
        return None
    try:
        return stem_of(label, lexicon=lexicon)[0]
    except ValueError:
        return None


def compare_negative_label(model_opposite: Optional[str], recorded: Optional[str], *, lexicon=None) -> str:
    """``match`` | ``mismatch`` | ``placeholder`` | ``none_recorded`` (module docstring)."""
    if not isinstance(recorded, str) or not recorded.strip():
        return "none_recorded"
    if recorded.strip().lower().startswith("non-"):
        return "placeholder"
    a = _stem(model_opposite, lexicon)
    want = {_stem(recorded, lexicon), _stem(_SUFFIX_RE.sub("", recorded), lexicon)} - {None}
    return "match" if a is not None and a in want else "mismatch"


def check_union(opposites: Sequence[Mapping], recorded: Optional[str], *, lexicon=None) -> tuple[str, Optional[int]]:
    """``(negative_label_check, recorded_support)`` over a trait's combined opposites: ``match`` when any of them is
    the recorded label (its support, how many samples named it, is returned too), else as
    :func:`compare_negative_label` of the best-supported one (``mismatch`` with no opposite at all)."""
    for it in opposites:
        if compare_negative_label(it["label"], recorded, lexicon=lexicon) == "match":
            return "match", it.get("support")
    top = opposites[0]["label"] if opposites else None
    return compare_negative_label(top, recorded, lexicon=lexicon), None


def position_rows(replies: Iterable, *, corpus: Corpus, lexicon=None) -> list[dict]:
    """One row per trait answered in full, in stem order, from its combined reply (a single sample's reply is
    combined first): the majority ``position`` and every sample's (``positions``), the blind opposites with their
    support (``model_opposites``; ``model_opposite`` the best supported), and the check against the recorded label
    over all of them (Roger, 2026-10-13: the union of the samples)."""
    from .combine import CombinedReply, combine
    reps = [r if isinstance(r, CombinedReply) else combine({r.sample: r}, lexicon=lexicon) for r in replies]
    out = []
    for rep in sorted((r for r in reps if not r.principal_only), key=lambda r: r.stem):
        rec = corpus.negative_labels.get(rep.stem)
        opps = rep.slot("opposite")
        mean = rep.position == "mean"
        # a mean is a triangle with its two vices (Roger, 2026-10-13): its recorded label is checked against all
        # three answers, the opposite first
        corners = opps + rep.slot("excess") + rep.slot("deficiency") if mean else opps
        check, rec_support = check_union(corners, rec, lexicon=lexicon)
        out.append({"schema_version": SCHEMA_VERSION, "stem": rep.stem,
                    "label": corpus.labels.get(rep.stem) or rep.label, "position": rep.position,
                    "positions": list(rep.positions), "n_samples": rep.n_samples,
                    "recorded_negative_label": rec, "model_opposite": opps[0]["label"] if opps else None,
                    "model_opposite_gloss": opps[0].get("gloss") if opps else None,
                    "model_opposites": [{"label": it["label"], "support": it.get("support", 1),
                                         "gloss": it.get("gloss")} for it in opps],
                    "negative_label_check": check, "recorded_support": rec_support,
                    "arrangement_hint": "triangle" if mean else None,
                    "arrangement": corpus.kinds.get(rep.stem), "reasoning": rep.reasoning,
                    "reasonings": list(rep.reasonings), "run_id": rep.run_id, "model": rep.model,
                    "prompt_sha256": rep.prompt_sha256, "at": rep.at})
    return out


def table_text(rows: Sequence[Mapping]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def _write(body: str, path: Path) -> Optional[Path]:
    path = Path(path)
    backup = None
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return None
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, path)
    return backup


def write_position_table(rows: Sequence[Mapping], path: Path = POSITION_TABLE_PATH) -> Optional[Path]:
    """Write the side table (snapshot before overwrite; an unchanged table is not rewritten)."""
    return _write(table_text(rows), path)


def load_position_table(path: Path = POSITION_TABLE_PATH) -> list[dict]:
    """The side table's rows (frozen interface)."""
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _cell(s) -> str:
    return str(s if s is not None else "(none)").replace("|", "/").replace("\n", " ")


def render_mismatches(rows: Sequence[Mapping], *, trait_link_prefix: str = "../../traits/instructions/") -> str:
    """The mismatch readout: every ``mismatch`` row with both words and the model's reasoning, trait names linked to
    their files (relative to ``data/candidates/structural/``)."""
    mm = [r for r in rows if r.get("negative_label_check") == "mismatch"]
    counts = {c: sum(1 for r in rows if r.get("negative_label_check") == c) for c in CHECKS}
    lines = ["# Recorded negative labels the blind opposite disagrees with", "",
             "Generated by `structural_generator.py side-table` from the operators runs' responses "
             "(coding_plan_09 section 6); do not edit by hand.  For the pairing review: each row is a corpus trait "
             "whose recorded `negative_label` is a real word and whose opposite, asked without seeing that label, "
             "is another word (or none).  The side table is never written into a trait file.", "",
             f"Of {len(rows)} traits: " + ", ".join(f"{counts[c]} {c}" for c in CHECKS) + ".", "",
             "The blind opposites are the union of the trait's samples, each with its support (how many samples "
             "named it); the position is the samples' majority, every sample's in brackets.", "",
             "| trait | position | recorded negative label | blind opposites (support) | gloss of the first | "
             "the first sample's reasoning |",
             "|---|---|---|---|---|---|"]
    for r in mm:
        opps = ", ".join(f"{o['label']} ({o.get('support', 1)})" for o in r.get("model_opposites") or []) or None
        pos = f"{r.get('position')} [{', '.join(str(x) for x in r.get('positions') or [])}]"
        lines.append(f"| [{_cell(r['label'])}]({trait_link_prefix}{r['stem']}.json) | {_cell(pos)} | "
                     f"{_cell(r.get('recorded_negative_label'))} | {_cell(opps)} | "
                     f"{_cell(r.get('model_opposite_gloss'))} | {_cell(r.get('reasoning'))} |")
    return "\n".join(lines) + "\n"


def write_mismatches(rows: Sequence[Mapping], path: Path) -> Optional[Path]:
    return _write(render_mismatches(rows), path)


__all__ = ["CHECKS", "compare_negative_label", "check_union", "position_rows", "write_position_table", "load_position_table",
           "render_mismatches", "write_mismatches"]
