"""Labels as the trait-gap prompts show them: the judge display form (W19, Roger 2026-10-09).

Roger's rule: anything that sends a label or a ``negative_label`` to an LLM uses its most legible form, the
judge display form of :func:`assistant_axis.entity_id.judge_form_of_label`: the label as stored, with a named
standard's suffix in the long form (``careless (HEXACO)`` -> ``careless (from HEXACO)``, ``artistic (Holland)``
-> ``artistic (from Holland's RIASEC)``).  Labels without such a suffix (every candidate label, and the corpus
labels that name no standard) are unchanged.

In this package the rewrite happens **only where a prompt is rendered**: a corpus trait's ``label``
(``novelty.CorpusTrait``), a seed-queue entry's label, a registry row's ``label``, a key, an embedded text
(``label: description`` in the covered representation), an embedding-cache key, a paraphrase cache's source hash
and every record written as data keep the stored label.  A parser that checks the model's echo of the label checks
it against the label the model was shown (:func:`prompt_label` of the stored one).

**Label forms of a run.**  ``label_form`` names what a run's prompts showed: :data:`JUDGE_LABEL_FORM`
(``"judge-display-v1"``) for a run made after the change, :data:`STORED_LABEL_FORM` (``"stored"``: the label as
stored, the form of every run before 2026-10-09; a record without a ``label_form`` is one).  Each tool records it
in the run's ``run.json`` (or its config) and summary.  **A run that continues or replays another keeps that run's
form** (:func:`resolve_label_form`): ``--resume`` the earlier session's, ``novelty_score.py score --redecide``,
``--relation-only`` and ``full-scan`` their source run's, ``plain_reading.py --reuse-readings`` the reused run's,
the recovery harness's match stage its reduced-corpus M3 run's.  Why not refuse, or switch: several replay paths
match records by a key or a Message Batches ``custom_id`` that does not contain the prompt (the Batches
transport's collection on resume, the states pass's row cache by key, label and text, the overlap test's records by
rubric, model, call and pass), so a form change across a resume would pair answers with prompts they were not
given; and a re-decided or relation-only run must find its source's requests unchanged, or it would re-send (and
re-pay for) every call that shows one of the 85 standard-labelled traits and decide those candidates on a
different prompt from the rest.  Keeping the recorded form makes every such run one form throughout, and lets the
runs made before the change be resumed and re-decided as before.  A new run takes the judge form.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from assistant_axis.entity_id import JUDGE_LABEL_FORM, display_form_name, judge_form_of_label

#: The label as stored (``positive_label``, a queue entry's ``label``, a registry row's ``label``): what every
#: prompt showed before 2026-10-09, and what a run without a recorded ``label_form`` used.
STORED_LABEL_FORM = "stored"
LABEL_FORMS: tuple[str, ...] = (STORED_LABEL_FORM, JUDGE_LABEL_FORM)
#: The form of a new run's prompts.
DEFAULT_LABEL_FORM = JUDGE_LABEL_FORM
#: The key under which a run records its form (``run.json``, a config, a summary).
LABEL_FORM_KEY = "label_form"


def check_label_form(form: str) -> str:
    """``form`` itself, or a ``ValueError`` for a form this code does not know."""
    if form not in LABEL_FORMS:
        raise ValueError(f"label_form must be one of {LABEL_FORMS}, not {form!r}")
    return form


def prompt_label(label: Any, form: str = DEFAULT_LABEL_FORM) -> Any:
    """``label`` as a prompt of ``form`` shows it: the judge display form (the default), or the label unchanged
    (:data:`STORED_LABEL_FORM`).  A value that is not a non-empty string (``None``, ``""``) is returned as it is.
    Idempotent.

    A label stored with an underscore is a stem standing in for a label (no corpus label or candidate label has
    one; on 2026-10-10 ten seed-queue entries did, ``open_ended`` among them, a renamed trait with no file to give
    it a display label): it is shown in the display form, the underscores as spaces, as
    :func:`assistant_axis.entity_id.judge_label` shows a name the corpus does not know.

    >>> prompt_label("careless (HEXACO)")
    'careless (from HEXACO)'
    >>> prompt_label("careless (HEXACO)", STORED_LABEL_FORM)
    'careless (HEXACO)'
    >>> prompt_label("gregarious")
    'gregarious'
    >>> prompt_label("open_ended")
    'open ended'
    """
    check_label_form(form)
    if form == STORED_LABEL_FORM or not isinstance(label, str) or not label:
        return label
    if "_" in label:
        label = display_form_name(label)
    return judge_form_of_label(label)


def recorded_label_form(record: Optional[Mapping]) -> Optional[str]:
    """The form a run's record names: its ``label_form``; :data:`STORED_LABEL_FORM` for a record without one
    (every run before 2026-10-09); ``None`` when there is no record.  A provenance envelope
    (``{"result": ..., "_provenance": ...}``) is read through.  An unknown form raises ``ValueError``."""
    if record is None:
        return None
    if isinstance(record.get("result"), Mapping) and "_provenance" in record:
        record = record["result"]
    return check_label_form(record.get(LABEL_FORM_KEY) or STORED_LABEL_FORM)


def resolve_label_form(*, earlier: Optional[Mapping] = None, source: Optional[Mapping] = None) -> str:
    """The form of a run's prompts: the earlier session's when the run is resumed (``earlier``: its ``run.json``),
    else the form of the run it replays (``source``: that run's ``run.json``), else :data:`DEFAULT_LABEL_FORM`
    (see the module docstring)."""
    for rec in (earlier, source):
        form = recorded_label_form(rec)
        if form is not None:
            return form
    return DEFAULT_LABEL_FORM


__all__ = ["STORED_LABEL_FORM", "JUDGE_LABEL_FORM", "LABEL_FORMS", "DEFAULT_LABEL_FORM", "LABEL_FORM_KEY",
           "check_label_form", "prompt_label", "recorded_label_form", "resolve_label_form"]
