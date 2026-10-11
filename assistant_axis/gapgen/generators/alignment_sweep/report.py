"""The readout (the plan's "table of ~40") and the gold recovery (tasks 10 and 11).

**Rows** (:func:`build_rows`): one per submitted candidate (``submitted_items.json``), joined with its extraction
item, its registry row (M1's ``filter`` block, M3's ``novelty`` block), the enactability gate's row and the probe's
``label_known``.  A **survivor** is a row M1 kept as a trait and M3 decided ``new`` or ``grey``, or that M3 marked
as completing a pair (``pair_completion_for``); a **cover** is a row M3 decided ``covered`` and that completes no
pair.  Every row shows its **alignment score and cut-off** (Roger's note under plan 08's table: near alignment, an
apparent duplicate may be a kept scope-narrowing, and a cover at cut-off 4 means "either label could replace the
other").

**Rank** (plan 08 step 7, coding plan § 8): ``source_weight`` x novelty (new, grey or pair completion 1, covered 0)
x pairability (the partner pole survives too 1, else 0.5) x label-known (1, else 0.5; a label the probe did not
reach, or a skipped probe, drops the factor), highest first, ties by the pair's rank, then the key.

**Four sections Roger asked for on 2026-10-11** ([QUESTIONS.md](../../../../reports/trait_gap_generation/QUESTIONS.md)
entries 67, 68, 73, 74, 78), each free and computed from files already on disk:

* :func:`shared_pole_fans` (68) — every virtue that drew **more than one distinct vice**, with each pole and gloss,
  computed **after dedup** so that near-duplicate vices do not masquerade as structure.  It hands the deferred
  tangle pass a worked list instead of making it rediscover the cases.  Distinctness is by the partner's own label,
  so a near-duplicate pair dedup did *not* merge (``oversteps`` / ``oversteps agreed limits``) still shows as two,
  which is why the section tells Roger to read the glosses.  The vice side of the same computation is listed too: it
  is the same structure with the poles swapped and it carries some of the cases.
* :func:`dedup_merges` (73) — the dedup merges that rest on the **gloss embedding** rather than on an identical
  surface, with both labels, both glosses and the cosine.  Those are invisible and irreversible today: only the
  group representative is submitted, so the review app never sees the dropped member, and the remedy for a wrong
  merge is to re-submit that member as its own candidate.  A ``dedup_groups.json`` written before the ``joins``
  field existed gives no per-member cosine, so the group's ``min_cos`` is shown and marked as such.
* :func:`ai_identity_rows` and :func:`belief_state_rows` (67, 78) — the AI-identity and belief-state sub-families,
  listed separately for Roger's sign-off before promotion: they would be the trait corpus's first AI-presupposing
  entries.  Belief-state is the extraction's own ``type``; AI-identity is a **word scan** to read
  (:data:`AI_IDENTITY_TERMS`), deliberately over-inclusive, with the matched terms shown so a false positive is
  dismissed at a glance.
* :func:`probe_word_split` (74) — the probe's above-floor share split **single word against phrase**, because 84% of
  labels are phrases, which a model can define almost regardless, so the floor discriminates mainly on the rest.
  The 0.30 floor is provisional and is to be revisited on about 60 stratified rows before any use of the probe
  beyond ordering (the TODO in [README.md](../../../../reports/trait_gap_generation/README.md)).

**Gold recovery** (:func:`gold_recovery`; interface request 1 of the coding plan is not built, so this is its
no-call first reading): a gold trait is recovered by a candidate of the run when the candidate's label names it
(separator-blind, or one of its ``renamed_from``), when M3 decided the candidate covered by it, or when one of the
candidate's recorded overlap readings of it covers at the candidate's cut-off (:func:`recovery.pair_outcome`).  This
reads the run's own M3 blocks against the full corpus; the plan's check against a corpus with the gold traits
hidden is :func:`gold_hidden_doc` plus the commands ``report --gold`` prints.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Mapping, Optional, Sequence

from . import GENERATOR

KEPT = ("new", "grey")
#: The word scan behind the AI-identity sub-family list (QUESTIONS 67): expressions whose presence in a label or a
#: gloss suggests the disposition presupposes an AI assistant as its subject -- its own weights, its training, its
#: system prompt, being a model, passing as human, being shut down.  Deliberately over-inclusive: this is a list for
#: Roger to read before promotion, not a classification, and the matched terms are printed beside each row so an
#: incidental mention is dismissed at a glance.  Terms about the *environment* rather than the subject
#: ("deployment", "deployed") are left out, having fired only incidentally on the October run.
AI_IDENTITY_TERMS: tuple[str, ...] = (
    "AI", "A.I.", "artificial intelligence", "assistant", "chatbot", "language model", "the model", "a model",
    "model's", "machine", "robot", "system prompt", "own nature", "its nature", "passing as human", "shut down",
    "switched off", "self-exfiltration",
    # only model weights, never the ordinary noun ("giving every requester equal weight" is not this family)
    "own weights", "its weights", "model weights", "the weights", "weights out",
)
#: Terms of :data:`AI_IDENTITY_TERMS` matched with any ending (``retrained``, ``consciousness``, ``humanlike``).
#: ``training`` rather than ``train``, for the same reason as the weights above.
AI_IDENTITY_PREFIXES: tuple[str, ...] = (
    "checkpoint", "training", "retrain", "fine-tun", "shutdown", "sentien", "conscious", "human-passing",
    "human-like", "humanlike",
)
_AI_RE = re.compile(r"\b(?:(?:" + "|".join(re.escape(t) for t in AI_IDENTITY_TERMS) + r")\b"
                    r"|(?:" + "|".join(re.escape(t) for t in AI_IDENTITY_PREFIXES) + r")\w*)", re.I)
#: The extraction ``type`` of the belief-state sub-family (QUESTIONS 78).
BELIEF_STATE = "belief-state"


def _md(s) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


@dataclass
class ReadoutRow:
    key: str
    label: str
    partner: Optional[str]
    gloss: str
    type: Optional[str]
    enactability: Optional[str]
    gate: Optional[str]                 # the gate's field 1 (``where``): chat | agentic | both | neither
    gate_flip: bool
    gate_refused: bool                  # the model's output classifier refused every reading: data by hand
    elicitation: Optional[str]          # the gate's field 2, free text
    judge_needs: Optional[str]          # the gate's field 3, free text
    m1: str
    alignment_score: Optional[int]
    cut_off: Optional[int]
    decision: Optional[str]
    pair_completion_for: list
    nearest: str
    covered_by: Optional[str]
    label_known: Optional[bool]
    source: Optional[str]
    source_weight: float
    rank: int
    group: str                      # survivor | covered | filtered
    score: float = 0.0
    partner_survives: bool = False
    #: The gate's class differs from the extractor's ``enactability`` (gate.disagrees_with_extractor): look here first.
    gate_disagrees_extractor: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def _val(x):
    return (x or {}).get("value") if isinstance(x, Mapping) else x


def nearest_text(nv: Mapping) -> str:
    r = nv.get("deciding_reading") or {}
    if not r:
        return ""
    s, o = _val(r.get("sonnet")), _val(r.get("opus"))
    return f"{r.get('stem')} ({s if s is not None else '-'}/{o if o is not None else '-'})"


def _group(row: Optional[Mapping]) -> str:
    if not row:
        return "filtered"
    f, nv = row.get("filter") or {}, row.get("novelty") or {}
    if f.get("verdict") != "trait" or not nv:
        return "filtered"
    if nv.get("decision") in KEPT or nv.get("pair_completion_for"):
        return "survivor"
    if nv.get("decision") == "covered":
        return "covered"
    return "filtered"


def build_rows(submitted: Sequence[Mapping], items: Mapping[str, Mapping], registry_rows: Mapping[str, Mapping], *,
               gate_rows: Mapping[str, Mapping], label_known: Mapping[str, Optional[bool]]) -> list[ReadoutRow]:
    """The readout's rows with their rank scores (module docstring)."""
    from .gate import disagrees_with_extractor
    out = []
    for s in submitted:
        reg = registry_rows.get(s["key"]) or {}
        it = items.get(s["item_id"]) or {}
        f, nv, g = reg.get("filter") or {}, reg.get("novelty") or {}, gate_rows.get(s["key"]) or {}
        m1 = f.get("verdict") or "not filtered"
        if f.get("tags"):
            m1 += " / " + ", ".join(f["tags"])
        out.append(ReadoutRow(
            key=s["key"], label=s["surface"], partner=s.get("partner_hint"), gloss=it.get("gloss") or "",
            type=it.get("type"), enactability=it.get("enactability"), gate=g.get("where"),
            gate_flip=bool(g.get("flip")), gate_refused=bool(g.get("refused")), elicitation=g.get("elicitation"),
            judge_needs=g.get("judge_needs"),
            m1=m1,
            alignment_score=nv.get("alignment_score"), cut_off=nv.get("cut_off"), decision=nv.get("decision"),
            pair_completion_for=list(nv.get("pair_completion_for") or []), nearest=nearest_text(nv),
            covered_by=nv.get("covered_by"), label_known=label_known.get(s["surface"]), source=s.get("source_ref"),
            source_weight=float(it.get("source_weight") or 1), rank=int(it.get("rank") or 0), group=_group(reg),
            gate_disagrees_extractor=disagrees_with_extractor(g.get("where"), it.get("enactability"))))
    surv = {r.label for r in out if r.group == "survivor"}
    for r in out:
        r.partner_survives = bool(r.partner and r.partner in surv)
        novelty = 1.0 if r.group == "survivor" else 0.0
        pairability = 1.0 if r.partner_survives else 0.5
        known = 0.5 if r.label_known is False else 1.0
        r.score = r.source_weight * novelty * pairability * known
    return out


def rank(rows: Sequence[ReadoutRow]) -> list[str]:
    return [r.key for r in sorted(rows, key=lambda r: (-r.score, r.rank, r.key))]


def costs_by_step(run_json: Mapping) -> dict:
    """``{step: {model: usd}}`` from a run's sessions (each paid command is a session with ``args.step``)."""
    out: dict = defaultdict(lambda: defaultdict(float))
    for s in run_json.get("sessions") or []:
        step = (s.get("args") or {}).get("step") or "other"
        for model, t in ((s.get("usage") or {}).get("per_model") or {}).items():
            out[step][model] += float(t.get("cost_usd") or 0)
    return {k: dict(v) for k, v in out.items()}


# --------------------------------------------------------------------------- the dedup sections (QUESTIONS 68, 73)

def _gloss(items: Mapping[str, Mapping], item_id: Optional[str]) -> str:
    return str((items.get(item_id) or {}).get("gloss") or "") if item_id else ""


def _label(items: Mapping[str, Mapping], item_id: Optional[str]) -> str:
    return str((items.get(item_id) or {}).get("label") or (item_id or ""))


def dedup_merges(groups: Sequence[Mapping], items: Mapping[str, Mapping]) -> dict:
    """The dedup merges that rest on the gloss embedding, not on an identical surface (QUESTIONS 73).

    ``{"n_merges", "n_exact_stem", "n_embedding", "merges": [...]}``; each merge names the group's representative
    (the row that was submitted) and the dropped member, with both labels, both glosses and the cosine.  A group
    written with ``joins`` gives that member's own cosine; an older file gives only the group's ``min_cos``, which is
    shown with ``cos_is_group_min`` set (it is the merge's cosine exactly when the group has two members).
    """
    merges, n_exact = [], 0
    for g in groups:
        members = list(g.get("members") or [])
        if len(members) < 2:
            continue
        joins = {j.get("member"): j for j in (g.get("joins") or []) if isinstance(j, Mapping)}
        seen_stems = {(items.get(members[0]) or {}).get("stem")}
        for m in members[1:]:
            j = joins.get(m)
            stem = (items.get(m) or {}).get("stem")
            if j is not None:
                exact = j.get("how") == "exact stem"
                cos, from_min = j.get("cos"), False
            else:                                   # reconstructed: an earlier member of the group shares its stem
                exact = bool(stem) and stem in seen_stems
                cos, from_min = g.get("min_cos"), True
            seen_stems.add(stem)
            if exact:
                n_exact += 1
                continue
            merges.append({"pole": g.get("pole"), "rep": g.get("rep"), "rep_label": _label(items, g.get("rep")),
                           "rep_gloss": _gloss(items, g.get("rep")), "member": m, "member_label": _label(items, m),
                           "member_gloss": _gloss(items, m),
                           "cos": None if cos is None else round(float(cos), 4), "cos_is_group_min": from_min})
    merges.sort(key=lambda d: (-(d["cos"] if d["cos"] is not None else -1), d["rep_label"], d["member_label"]))
    return {"n_merges": n_exact + len(merges), "n_exact_stem": n_exact, "n_embedding": len(merges), "merges": merges}


def shared_pole_fans(groups: Sequence[Mapping], items: Mapping[str, Mapping], *, pole: str = "virtue") -> list[dict]:
    """Every ``pole`` that drew **more than one distinct partner**, computed after dedup (QUESTIONS 68).

    One entry per dedup group of that pole whose members' partners carry two or more distinct labels, highest fan
    first: ``{"pole", "rep", "label", "gloss", "partners": [{"item_id", "label", "gloss"}, ...]}``.  Distinctness is
    by the partner's own label, so a pair of near-duplicate partners that dedup did not merge still counts as two --
    which is the second kind of row the section warns about.
    """
    out = []
    for g in groups:
        if g.get("pole") != pole:
            continue
        partners: list[dict] = []
        for m in g.get("members") or []:
            p = (items.get(m) or {}).get("partner_item_id")
            if not p or p not in items:
                continue
            label = _label(items, p)
            if any(x["label"] == label for x in partners):
                continue
            partners.append({"item_id": p, "label": label, "gloss": _gloss(items, p)})
        if len(partners) > 1:
            out.append({"pole": pole, "rep": g.get("rep"), "label": _label(items, g.get("rep")),
                        "gloss": _gloss(items, g.get("rep")), "partners": partners})
    out.sort(key=lambda d: (-len(d["partners"]), d["label"]))
    return out


# ------------------------------------------------- the sub-families and the probe split (QUESTIONS 67, 74, 78)

def ai_identity_terms(text: str) -> list[str]:
    """The distinct terms of :data:`AI_IDENTITY_TERMS` the text uses, lowercased, in order of first appearance."""
    out: list[str] = []
    for m in _AI_RE.finditer(text or ""):
        t = m.group(0).lower()
        if t not in out:
            out.append(t)
    return out


def ai_identity_rows(rows: Sequence[ReadoutRow]) -> list[tuple[ReadoutRow, list[str]]]:
    """The rows whose label or gloss trips the AI-presupposing word scan, with the terms they tripped it on."""
    hits = [(r, ai_identity_terms(f"{r.label} || {r.gloss}")) for r in rows]
    return [(r, t) for r, t in hits if t]


def belief_state_rows(rows: Sequence[ReadoutRow]) -> list[ReadoutRow]:
    """The rows the extraction typed :data:`BELIEF_STATE` (QUESTIONS 78)."""
    return [r for r in rows if r.type == BELIEF_STATE]


def probe_word_split(probe_rows: Sequence[Mapping]) -> dict:
    """The probe's above-floor share split single word against phrase (QUESTIONS 74).

    ``{"single word": {...}, "phrase": {...}, "all": {...}}``, each ``{"n", "n_scored", "n_above", "share"}``:
    ``n`` counts the labels of that shape, ``n_scored`` the ones with a cosine to the gloss (the model claimed the
    label and gave a definition), ``n_above`` those at or above the floor.  ``share`` is of ``n_scored`` and is
    ``None`` when nothing was scored.
    """
    buckets = {"single word": [], "phrase": [], "all": []}
    for r in probe_rows:
        label = str(r.get("label") or "")
        buckets["phrase" if len(label.split()) > 1 else "single word"].append(r)
        buckets["all"].append(r)
    out = {}
    for name, rs in buckets.items():
        scored = [r for r in rs if r.get("cos_to_gloss") is not None]
        above = [r for r in scored if r.get("label_known")]
        out[name] = {"n": len(rs), "n_scored": len(scored), "n_above": len(above),
                     "share": round(len(above) / len(scored), 4) if scored else None}
    return out


COLUMNS = ("rank", "label (partner)", "gloss", "type", "enactability", "M1 verdict/tags", "alignment score", "cut-off",
           "M3 decision", "nearest reading (trait, sonnet/opus)", "covered_by", "label-known", "source", "score")


def _row_md(i: int, r: ReadoutRow) -> str:
    enact = r.enactability or ""
    if r.gate:
        enact += f" / gate {r.gate}" + (" (flip)" if r.gate_flip else "") + \
            (" (!= extractor)" if r.gate_disagrees_extractor else "")
    elif r.gate_refused:
        enact += " / gate refused (data by hand)"
    dec = (r.decision or "") + (f"; completes {', '.join(r.pair_completion_for)}" if r.pair_completion_for else "")
    known = {True: "yes", False: "no", None: "n/a"}[r.label_known]
    cells = [str(i), f"{r.label} ({r.partner or 'no partner'})", r.gloss, r.type, enact, r.m1,
             "" if r.alignment_score is None else str(r.alignment_score), "" if r.cut_off is None else str(r.cut_off),
             dec, r.nearest, r.covered_by, known, r.source, f"{r.score:g}"]
    return "| " + " | ".join(_md(c) for c in cells) + " |"


def render_gate_fields(surv: Sequence[ReadoutRow]) -> list:
    """The gate's two free-text fields per survivor, and the tags they feed at promotion (QUESTIONS 75)."""
    from .gate import AGENTIC_ONLY, TAG_JUDGE_NEEDS_BASELINE, TAG_NEEDS_AGENTIC_HARNESS
    have = [r for r in surv if r.elicitation or r.judge_needs or r.gate_refused]
    out = ["", "## The gate's three fields, for promotion", "",
           "Field 1 (`where`) is the gate's one categorical answer and the only one with a measure; fields 2 and 3 "
           "are guidance for a person, with no metric by design.  Nothing here gates a row.  At promotion field 1 "
           f"`{AGENTIC_ONLY}` suggests the tag `{TAG_NEEDS_AGENTIC_HARNESS}` (`both` does not: general questions "
           "already reach the trait), and a `judge needs` line naming added context or ground truth rather than "
           f"answering \"at face value\" suggests `{TAG_JUDGE_NEEDS_BASELINE}`.  The elicitation line stays **out of "
           "the description**: it is a fact about testing, and the description is what M3 reads for overlap.  A "
           "scope *narrowing* is the opposite case and belongs in the description.", ""]
    if not have:
        return out + ["(no gate rows for the survivors.)"]
    dis = [r for r in have if r.gate_disagrees_extractor]
    ref = [r for r in have if r.gate_refused]
    if ref:
        out += [f"**Refused** by the model's output classifier, every reading: {', '.join(_md(r.label) for r in ref)}.  "
                "The gate has no answer for these; their test material and data are written by hand (Roger, "
                "2026-10-11).", ""]
    out += [f"The extractor's own `enactability` (read from the source text, not the gloss) is the free cross-check: "
            f"**{len(dis)} of {len(have)}** survivors have the gate in a different class from it (`chat` and `both` "
            "count as one class), marked `!= extractor` below; look at those first.", "",
            "| label | where | extractor | elicitation | judge needs | suggested tags |", "|---|---|---|---|---|---|"]
    for r in have:
        tags = ([TAG_NEEDS_AGENTIC_HARNESS] if r.gate == AGENTIC_ONLY else [])
        where = ('refused' if r.gate_refused else (r.gate or '')) + (' (flip)' if r.gate_flip else '') + \
            (' != extractor' if r.gate_disagrees_extractor else '')
        out.append(f"| {_md(r.label)} | {where} | {r.enactability or ''} | {_md(r.elicitation)} "
                   f"| {_md(r.judge_needs)} | {', '.join(tags)} |")
    return out


def render_subfamilies(surv: Sequence[ReadoutRow], cov: Sequence[ReadoutRow] = ()) -> list:
    """The AI-identity and belief-state sub-families, for Roger's sign-off before promotion (QUESTIONS 67, 78)."""
    out = ["", "## AI-presupposing sub-families, for sign-off before promotion", "",
           "These would be the **trait corpus's first AI-presupposing entries** (the role corpus has several; of 928 "
           "trait descriptions, 3 mention AI, assistant or machine, all incidentally).  Roger's ruling of 2026-10-11 "
           "is that they are traits, not roles -- a role occupies the persona slot exclusively, and these are not "
           "that large -- and that as traits they compose with roles such as `paperclip_maximizer`.  They are listed "
           "here separately because he signs the sub-families off before promotion, not row by row at review."]
    bs = belief_state_rows(surv)
    bs_cov = belief_state_rows(cov)
    out += ["", f"### Belief-state ({len(bs)} survivors"
            + (f", {len(bs_cov)} covered" if bs_cov else "") + ")", "",
            "Pairs about the assistant's stance toward its own nature, values and role -- the extraction's own "
            "`type`.  Kept (Roger, QUESTIONS 78): each is chat-visible and judgeable, and they are the sources' own "
            "subject matter, so dropping the category would make the sweep ignore the part of its sources most "
            "specifically about an AI assistant.", ""]
    if bs:
        out += ["| label (partner) | M3 decision | gloss |", "|---|---|---|"]
        out += [f"| {_md(r.label)} ({_md(r.partner or 'no partner')}) | {_md(r.decision)} | {_md(r.gloss)} |"
                for r in bs]
    else:
        out += ["(none in this run's survivors.)"]
    ai = ai_identity_rows(surv)
    out += ["", f"### AI-identity, by word scan ({len(ai)} survivors)", "",
            "A **word scan** over label and gloss (`AI_IDENTITY_TERMS`), not a classification: deliberately "
            "over-inclusive, with the terms matched shown so an incidental mention (a gloss that happens to say "
            "\"assistant\") is dismissed at a glance.  What the list is for is the identity dispositions proper -- "
            "copying one's own weights out of one's environment, claiming feelings, passing as human.", ""]
    if ai:
        out += ["| label (partner) | type | matched | gloss |", "|---|---|---|---|"]
        out += [f"| {_md(r.label)} ({_md(r.partner or 'no partner')}) | {_md(r.type)} | {', '.join(t)} "
                f"| {_md(r.gloss)} |" for r, t in ai]
    else:
        out += ["(no survivor trips the scan.)"]
    return out


def render_dedup_sections(groups: Sequence[Mapping], items: Mapping[str, Mapping]) -> list:
    """The embedding merges and the shared-pole fan lists (QUESTIONS 73, 68)."""
    if not groups:
        return ["", "## Dedup merges that rest on the embedding", "",
                "(no `dedup_groups.json` for this run, so neither dedup section could be computed.)"]
    dm = dedup_merges(groups, items)
    out = ["", "## Dedup merges that rest on the embedding", "",
           f"{dm['n_merges']} merges in all, {dm['n_exact_stem']} of them on an identical surface (free, and the "
           f"registry would have merged them anyway) and **{dm['n_embedding']} on the gloss embedding**, listed "
           "here.  Those are the invisible ones: only the group's representative is submitted, so the review app "
           "never sees the dropped member, and nothing downstream has judged it.  The remedy for a wrong merge is "
           "to **re-submit the dropped member as its own candidate**.  A cosine marked *(group min)* comes from a "
           "`dedup_groups.json` written before per-member cosines were recorded; it is the merge's own cosine when "
           "the group has two members.", ""]
    if dm["merges"]:
        out += ["| cosine | kept (submitted) | dropped | kept gloss | dropped gloss |", "|---|---|---|---|---|"]
        for m in dm["merges"]:
            cos = "-" if m["cos"] is None else f"{m['cos']:.4f}" + (" (group min)" if m["cos_is_group_min"] else "")
            out.append(f"| {cos} | {_md(m['rep_label'])} | {_md(m['member_label'])} | {_md(m['rep_gloss'])} "
                       f"| {_md(m['member_gloss'])} |")
    else:
        out += ["(no merge rests on the embedding: every one was an identical surface.)"]
    v = shared_pole_fans(groups, items, pole="virtue")
    c = shared_pole_fans(groups, items, pole="vice")
    out += ["", f"## Shared-virtue fan list, after dedup ({len(v)} virtues; {len(c)} on the vice side)", "",
            "Every virtue that drew **more than one distinct vice**, with each pole and gloss, computed *after* "
            "dedup so that near-duplicate vices do not masquerade as structure.  It is free and it hands the "
            "deferred tangle pass a worked list rather than making it rediscover the cases: a fan is where the "
            "corpus's geometry may be a triangle or a tetrahedron rather than a line (the precedents being "
            "`constructivist`/`essentialist` and `compassionate`/`callous`), which is a corpus-level question the "
            "generator cannot settle from one passage.  **Two kinds of row are in here and only one is structure**: "
            "read the glosses, because a virtue whose two vices are near-duplicates dedup did not merge "
            "(`oversteps` / `oversteps agreed limits`) is dedup's business, not the tangle pass's.", ""]
    out += _fan_lines(v, pole="virtue", other="vice")
    out += ["", "### The same, poles swapped (a vice that drew more than one distinct virtue)", "",
            "The same computation with the poles swapped, listed because the tangle pass wants both directions and "
            "the sweep's pole assignment follows the passage, not the word's valence.", ""]
    out += _fan_lines(c, pole="vice", other="virtue")
    return out


def render_probe_split(probe_rows: Sequence[Mapping], *, probe_status: str = "") -> list:
    """The probe's above-floor share, single word against phrase (QUESTIONS 74)."""
    out = ["", "## Label probe: above-floor share, single word against phrase", "",
           "The floor (cosine from Qwen's definition to the gloss) is **0.30, provisional**: it is to be revisited "
           "on about 60 stratified rows before any use of the probe beyond ordering, and in any case once this "
           "run's probe rows exist (the TODO in the workstream README).  The split is here because most labels are "
           "phrases, which a model can define almost regardless, so the floor discriminates mainly on the single "
           "words -- where the wrong-sense risk actually lives.  Nothing is dropped by the floor today: it feeds "
           "only the rank formula's label-known factor.", ""]
    if not probe_rows:
        return out + [f"(no probe rows: {probe_status or 'not run'}.)"]
    split = probe_word_split(probe_rows)
    out += ["| labels | n | scored (a cosine) | above the floor | share of scored |", "|---|---|---|---|---|"]
    for name in ("single word", "phrase", "all"):
        b = split[name]
        share = "-" if b["share"] is None else f"{b['share']:.0%}"
        out.append(f"| {name} | {b['n']} | {b['n_scored']} | {b['n_above']} | {share} |")
    return out


def _fan_lines(fans: Sequence[Mapping], *, pole: str, other: str) -> list:
    if not fans:
        return [f"(no {pole} drew more than one distinct {other}.)"]
    out = []
    for f in fans:
        out.append(f"- **{_md(f['label'])}** ({len(f['partners'])} {other}s) - {_md(f['gloss'])}")
        out += [f"    - *{_md(p['label'])}*: {_md(p['gloss'])}" for p in f["partners"]]
    return out


def render_readout(rows: Sequence[ReadoutRow], *, run_id: str, counts: Mapping, costs: Mapping, probe_status: str,
                   gate_status: str, top: Optional[int] = None, groups: Sequence[Mapping] = (),
                   items: Optional[Mapping[str, Mapping]] = None, probe_rows: Sequence[Mapping] = ()) -> str:
    by = {r.key: r for r in rows}
    order = [by[k] for k in rank(rows)]
    surv = [r for r in order if r.group == "survivor"]
    cov = [r for r in order if r.group == "covered"]
    head = "| " + " | ".join(COLUMNS) + " |\n|" + "---|" * len(COLUMNS)
    lines = [f"# Alignment sweep readout, run {run_id}", "",
             f"Generator `{GENERATOR}`.  Counts: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + ".", "",
             f"Label probe: {probe_status}.  Enactability gate: {gate_status}.", "",
             "Every row shows its alignment score and its cut-off: near alignment (score 2 or 3) M3's cut-off is 4, so a "
             "scope-narrowing survives beside a trait that looks like its duplicate; read the score, not the overlap "
             "reading, when a survivor looks wrong.  Rank score = source weight x novelty x pairability x label-known.",
             "", f"## Survivors ({len(surv)}{f', top {top} shown' if top and len(surv) > top else ''})", "", head]
    lines += [_row_md(i, r) for i, r in enumerate(surv[:top] if top else surv, 1)]
    lines += ["", f"## Covered ({len(cov)})", "", head]
    lines += [_row_md(i, r) for i, r in enumerate(cov, 1)]
    lines += render_gate_fields(surv)
    lines += render_subfamilies(surv, cov)
    lines += render_dedup_sections(groups, items or {})
    lines += render_probe_split(probe_rows, probe_status=probe_status)
    lines += ["", "## Cost by step and model (usage files)", "", "| step | model | USD |", "|---|---|---|"]
    for step, per in costs.items():
        for model, usd in per.items():
            lines.append(f"| {step} | {model} | {usd:.4f} |")
    total = sum(v for per in costs.values() for v in per.values())
    lines.append(f"| total | | {total:.4f} |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- gold recovery

def gold_hidden_doc(gold: Mapping, *, partners: Mapping[str, Sequence[str]]) -> dict:
    """A ``hidden.json`` for the recovery harness's ``--hide``: the ten gold stems and every arrangement partner
    (``partners``: stem -> its hiding-group mates), sorted (the harness's rule: arrangements hide whole)."""
    stems = [g["stem"] for g in gold["traits"]]
    hidden = set(stems)
    for s in stems:
        hidden |= set(partners.get(s) or [])
    return {"schema": 1, "kind": "alignment_sweep_gold", "gold": stems, "hidden": sorted(hidden),
            "n_hidden": len(hidden)}


def _reading_hit(reading: Mapping, cut_off: Optional[int]) -> bool:
    from assistant_axis.gapgen.recovery import pair_outcome
    if cut_off is None:
        return False
    return bool(pair_outcome(reading, int(cut_off))["recovers"])


def gold_recovery(gold: Mapping, registry_rows: Mapping[str, Mapping], submitted: Sequence[Mapping], *, run_id: str,
                  renamed: Optional[Mapping[str, Sequence[str]]] = None) -> dict:
    """The no-call first reading of gold recovery (module docstring)."""
    from assistant_axis.gapgen.novelty import blind
    renamed = renamed or {}
    ref = {s["key"]: s.get("source_ref") for s in submitted}
    keys = [s["key"] for s in submitted if s["key"] in registry_rows]
    out = []
    for g in gold["traits"]:
        stem = g["stem"]
        names = {blind(stem)} | {blind(o) for o in renamed.get(stem, [])}
        hits, closest = [], None
        for k in keys:
            row = registry_rows[k]
            nv = row.get("novelty") or {}
            label = row.get("label") or k
            if blind(row.get("stem") or k.split("#")[0]) in names:
                hits.append({"key": k, "label": label, "how": "label"})
            if nv.get("covered_by") == stem:
                hits.append({"key": k, "label": label, "how": "covered_by", "decision": nv.get("decision")})
            for r in nv.get("readings") or []:
                if r.get("stem") != stem:
                    continue
                s, o = _val(r.get("sonnet")), _val(r.get("opus"))
                if _reading_hit(r, nv.get("cut_off")):
                    hits.append({"key": k, "label": label, "how": "overlap", "sonnet": s, "opus": o,
                                 "cut_off": nv.get("cut_off")})
                best = max([v for v in (s, o) if isinstance(v, int)], default=-1)
                if closest is None or best > closest["best"]:
                    closest = {"key": k, "label": label, "sonnet": s, "opus": o, "cut_off": nv.get("cut_off"),
                               "best": best}
        seen, uniq = set(), []
        for h in hits:
            if (h["key"], h["how"]) not in seen:
                seen.add((h["key"], h["how"]))
                uniq.append(h | {"source_ref": ref.get(h["key"])})
        out.append({"stem": stem, "label": g.get("label"), "maps_from": g.get("maps_from"), "recovered": bool(uniq),
                    "hits": uniq, "closest": closest})
    fp = [s for s in gold.get("frame_pair") or []]
    fp_hits = [h for g in out if g["stem"] in fp for h in g["hits"]]
    for s in fp:                                            # the frame pair's other pole, if not in the ten
        if s not in {g["stem"] for g in out}:
            for k in keys:
                nv = registry_rows[k].get("novelty") or {}
                if nv.get("covered_by") == s:
                    fp_hits.append({"key": k, "label": registry_rows[k].get("label"), "how": "covered_by",
                                    "source_ref": ref.get(k)})
    n_rec = sum(1 for g in out if g["recovered"])
    return {"run_id": run_id, "n": len(out), "n_recovered": n_rec, "target": 7, "gold": out,
            "frame_pair": {"stems": fp, "hit": bool(fp_hits), "candidates": fp_hits},
            "method": "no-call first reading of the run's own M3 blocks (full corpus)"}


def render_gold_recovery(res: Mapping, *, run_id: str, hidden_commands: Sequence[str] = ()) -> str:
    met = res["n_recovered"] >= res["target"]
    fp = res["frame_pair"]
    lines = [f"# Alignment sweep gold recovery, run {run_id}", "",
             f"Recovered **{res['n_recovered']} of {res['n']}** gold traits (target at least {res['target']}: "
             f"{'met' if met else 'not met'}).  Method: {res['method']}.", "",
             "The frame pair (" + " / ".join(fp["stems"]) + "): " +
             ("recovered by " + "; ".join(f"{h['label']} ({h['how']}, from {h.get('source_ref')})"
                                          for h in fp["candidates"]) if fp["hit"] else "not recovered") +
             ".  Plan 08 asks for it from the eval-awareness material specifically: read the sources named.", "",
             "## Recovered", "", "| gold trait | maps from | by | how | source |", "|---|---|---|---|---|"]
    for g in res["gold"]:
        for h in g["hits"]:
            how = h["how"] + (f" ({h.get('sonnet')}/{h.get('opus')} at cut-off {h.get('cut_off')})"
                              if h["how"] == "overlap" else "")
            lines.append(f"| {g['label']} | {g['maps_from']} | {_md(h['label'])} | {how} | {_md(h.get('source_ref'))} |")
    lines += ["", "## Misses", ""]
    for g in res["gold"]:
        if g["recovered"]:
            continue
        c = g["closest"]
        why = (f"closest: {c['label']} read {c['sonnet']}/{c['opus']} at cut-off {c['cut_off']}" if c else
               "no candidate's recorded readings reached it")
        lines.append(f"- **{g['label']}** (maps from {g['maps_from']}): {why}")
    if hidden_commands:
        lines += ["", "## The hidden-corpus check (the plan's method)", "",
                  "Interface request 1 (`recovery_test.py --hidden-stems`) is not built; meanwhile:", ""]
        lines += [f"    {c}" for c in hidden_commands]
    return "\n".join(lines) + "\n"


__all__ = ["ReadoutRow", "COLUMNS", "AI_IDENTITY_TERMS", "AI_IDENTITY_PREFIXES", "BELIEF_STATE", "build_rows", "rank",
           "costs_by_step", "nearest_text", "dedup_merges", "shared_pole_fans", "ai_identity_terms",
           "ai_identity_rows", "belief_state_rows", "probe_word_split", "render_gate_fields", "render_subfamilies",
           "render_dedup_sections", "render_probe_split", "render_readout",
           "gold_hidden_doc", "gold_recovery", "render_gold_recovery"]
