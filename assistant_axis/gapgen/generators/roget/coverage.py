"""The coverage map: which Roget heads the corpus's traits (and the seed queue's) already occupy.

Plan § 5 (``roget_coverage.py``), with the states the 2026-10-08 brief asks for:

* scope: the dispositional heads (Classes IV-VI, numbers >= 450) plus the Class I-III heads whose
  adjectives contain an existing or active queued label as an exact or derived adjective
  (:func:`restricted_class_i_iii`);
* **state** of a head: ``covered`` (an existing trait has it as its primary head), ``partly``
  (only as a secondary head), ``queued`` (only an active seed-queue label maps to it), ``empty``;
  parked queue labels (``not_adopted``, ``superseded``, ``exists``) are listed, never counted;
* **gap class** (:func:`gap_class`): ``crowded`` (three or more existing primaries) and
  ``covered``; ``partly_covered``; ``queued_only``; for an empty head, ``pair_completion`` when its
  opposed head is covered, ``pair_empty`` when it has an opposed head that is not, and
  ``singleton_empty`` when the pairing found none (a singleton, a triad member, or a head the
  rules left unresolved).

``hidden`` removes stems before anything is computed (for a recovery run).

``ratings`` (the head-scope check, :mod:`.head_scope`; QUESTIONS 44): a head rated 0 ("few or none of
its adjectives describe a person's character") keeps its state and gap class on its row (with
``character = 0``) but is reported apart as **not character** and left out of the covered / partly /
uncovered counts, the gap-class counts and lists, the opposed-pair counts and the covered lists.
Without ratings (or for an unrated head) everything is as before.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Collection, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text

from .mapping import trait_link
from .pairs import HeadPairing
from .parse import DISPOSITIONAL_MIN, RogetIndex

#: Queue statuses that count (data_analysis/seed_entities.py LIFECYCLE plus tbd and backlog).
ACTIVE_STATUSES = ("candidate", "ready", "seeded", "generated", "checked", "paired", "done", "tbd", "backlog")
PARKED_STATUSES = ("not_adopted", "superseded", "exists")
STATES = ("covered", "partly", "queued", "empty")
GAP_CLASSES = ("pair_completion", "pair_empty", "singleton_empty", "queued_only", "partly_covered", "crowded",
               "covered")
#: The gap classes the harvest takes by default, in the order the report lists them.
HARVEST_CLASSES = ("pair_completion", "pair_empty", "singleton_empty", "queued_only")
CROWDED_MIN = 3


@dataclass
class HeadRow:
    id: str
    title: str
    path: str
    klass: str
    section: str
    partner: Optional[str]
    pair_kind: str
    pair_source: str
    members: list
    existing: list = field(default_factory=list)            # existing stems, primary here
    existing_secondary: list = field(default_factory=list)  # existing stems, secondary here
    queued_active: list = field(default_factory=list)
    queued_parked: list = field(default_factory=list)
    n_existing: int = 0
    n_queued_active: int = 0
    state: str = "empty"
    gap_class: str = "singleton_empty"
    partner_state: Optional[str] = None
    partner_existing: list = field(default_factory=list)
    triggers: list = field(default_factory=list)            # Class I-III: the labels that brought it in
    character: Optional[int] = None                         # head-scope rating (0, 1, 2), None if unrated


@dataclass
class CoverageReport:
    rows: list
    summary: dict
    hidden: list

    def by_id(self) -> dict[str, HeadRow]:
        return {r.id: r for r in self.rows}

    def to_json(self) -> dict:
        return {"summary": self.summary, "hidden": list(self.hidden), "rows": [asdict(r) for r in self.rows]}


def _active(v: Mapping) -> bool:
    return v.get("source") == "existing" or v.get("status") in ACTIVE_STATUSES


def restricted_class_i_iii(index: RogetIndex, label_heads: Mapping[str, Mapping], *,
                           hidden: Collection[str] = (), require_sense: bool = True) -> dict[str, list[str]]:
    """Heads below 450 that hold an existing or active queued label as an ``exact_adj`` or
    ``derived_adj`` lexical hit: ``{head id: [trigger stems]}``.

    With ``require_sense`` (the default) the head must also be where the label's sense sits: its
    primary or a secondary head, or among its semantic top five.  Without it, polysemous labels
    pull in the physical heads of their other senses (bitter: Cold, Pungency; fair: Whiteness;
    clear: Light): 162 Class I-III heads on the 2026-10-08 corpus against 99 with it."""
    hidden = set(hidden)
    out: dict[str, list[str]] = {}
    for stem, v in sorted(label_heads.items()):
        if stem in hidden or not _active(v):
            continue
        sense_heads = {v.get("primary"), *(v.get("secondary") or []), *(s["head_id"] for s in v.get("semantic") or [])}
        for hit in v.get("lexical") or []:
            hid = hit["head_id"]
            if require_sense and hid not in sense_heads:
                continue
            if hit["strength"] in ("exact_adj", "derived_adj") and hid in index.heads \
                    and index.heads[hid].number < DISPOSITIONAL_MIN:
                out.setdefault(hid, [])
                if stem not in out[hid]:
                    out[hid].append(stem)
    return {h: out[h] for h in sorted(out, key=index.position)}


def gap_class(row: HeadRow, partner_row: Optional[HeadRow]) -> str:
    if row.state == "covered":
        return "crowded" if row.n_existing >= CROWDED_MIN else "covered"
    if row.state == "partly":
        return "partly_covered"
    if row.state == "queued":
        return "queued_only"
    if row.partner and partner_row is not None:
        return "pair_completion" if partner_row.state == "covered" else "pair_empty"
    return "singleton_empty"


def coverage(index: RogetIndex, pairs: Mapping[str, HeadPairing], label_heads: Mapping[str, Mapping], *,
             hidden: Collection[str] = (), ratings: Optional[Mapping[str, Optional[int]]] = None,
             scope_meta: Optional[dict] = None) -> CoverageReport:
    """The coverage map over the dispositional heads and the restricted Class I-III set.  ``ratings``:
    the head-scope ratings (head id -> 0, 1, 2 or None); ``scope_meta`` records where they came from."""
    hidden = sorted(set(hidden))
    hid_set = set(hidden)
    restricted = restricted_class_i_iii(index, label_heads, hidden=hid_set)
    scope = [h for h in index.order if index.heads[h].number >= DISPOSITIONAL_MIN or h in restricted]
    scope_set = set(scope)
    # occupancy of every head (partners outside the scope need a state too)
    occ: dict[str, dict[str, list]] = {h: {"existing": [], "existing_secondary": [], "queued_active": [],
                                           "queued_parked": []} for h in index.order}
    for stem, v in sorted(label_heads.items()):
        if stem in hid_set or not v.get("primary"):
            continue
        prim, secs = v["primary"], [s for s in v.get("secondary") or [] if s != v["primary"]]
        if v.get("source") == "existing":
            occ[prim]["existing"].append(stem)
            for s in secs:
                occ[s]["existing_secondary"].append(stem)
        elif v.get("status") in ACTIVE_STATUSES:
            for h in [prim, *secs]:
                occ[h]["queued_active"].append(stem)
        else:
            for h in [prim, *secs]:
                occ[h]["queued_parked"].append(stem)

    def make_row(h: str) -> HeadRow:
        head = index.heads[h]
        p = pairs.get(h)
        o = occ[h]
        state = ("covered" if o["existing"] else "partly" if o["existing_secondary"]
                 else "queued" if o["queued_active"] else "empty")
        return HeadRow(id=h, title=head.title, path=head.path, klass=head.klass, section=head.section,
                       partner=p.partner if p else None, pair_kind=p.kind if p else "unresolved",
                       pair_source=p.source if p else "unresolved", members=list(p.members) if p else [h],
                       existing=o["existing"], existing_secondary=o["existing_secondary"],
                       queued_active=o["queued_active"], queued_parked=o["queued_parked"],
                       n_existing=len(o["existing"]), n_queued_active=len(o["queued_active"]), state=state,
                       triggers=list(restricted.get(h, [])),
                       character=(ratings or {}).get(h))

    all_rows = {h: make_row(h) for h in index.order}
    rows = []
    for h in scope:
        r = all_rows[h]
        pr = all_rows.get(r.partner) if r.partner else None
        r.gap_class = gap_class(r, pr)
        if pr is not None:
            r.partner_state = pr.state
            r.partner_existing = list(pr.existing)
        rows.append(r)
    summary = summarize(rows, index, label_heads, restricted, hidden, ratings=ratings, scope_meta=scope_meta)
    return CoverageReport(rows=rows, summary=summary, hidden=hidden)


def is_not_character(row: HeadRow) -> bool:
    return row.character == 0


def summarize(rows: Sequence[HeadRow], index: RogetIndex, label_heads: Mapping[str, Mapping],
              restricted: Mapping[str, list], hidden: Sequence[str], *,
              ratings: Optional[Mapping[str, Optional[int]]] = None, scope_meta: Optional[dict] = None) -> dict:
    all_rows = list(rows)
    nc_rows = [r for r in all_rows if is_not_character(r)]
    rows = [r for r in all_rows if not is_not_character(r)]
    by_state = Counter(r.state for r in rows)
    by_gap = Counter(r.gap_class for r in rows)
    by_section: dict[str, dict] = {}
    for r in all_rows:
        key = f"{r.klass} {r.section}"
        d = by_section.setdefault(key, {**{s: 0 for s in STATES}, "not_character": 0})
        d["not_character" if is_not_character(r) else r.state] += 1
    # opposed heads (pairs whose two poles are both in scope or one of them is); a pair with a pole
    # rated not character is left out
    ids = {r.id: r for r in all_rows}
    nc_ids = {r.id for r in nc_rows}
    seen, opp = set(), Counter()
    opp_by_source: dict[str, Counter] = {}
    for r in rows:
        if r.pair_kind != "pair" or not r.partner or r.id in seen:
            continue
        seen |= {r.id, r.partner}
        if r.partner in nc_ids:
            continue
        p_state = ids[r.partner].state if r.partner in ids else r.partner_state
        n_cov = int(r.state == "covered") + int(p_state == "covered")
        key = {2: "both_poles_covered", 1: "one_pole_covered", 0: "neither_pole_covered"}[n_cov]
        opp[key] += 1
        opp_by_source.setdefault(r.pair_source, Counter())[key] += 1
    labels_mapped = Counter((v.get("source"), bool(v.get("primary"))) for k, v in label_heads.items()
                            if k not in set(hidden))
    in_scope = {r.id for r in all_rows}
    primaries_in_scope = sum(1 for k, v in label_heads.items() if k not in set(hidden) and v.get("source") == "existing"
                             and v.get("primary") in in_scope)
    rated = [r for r in all_rows if r.character is not None]
    rating_counts = Counter(str(r.character) for r in rated)
    return {
        "n_heads": len(all_rows),
        "n_dispositional": sum(1 for r in all_rows if index.heads[r.id].number >= DISPOSITIONAL_MIN),
        "class_i_iii_added": len(restricted),
        "by_state": {s: by_state.get(s, 0) for s in STATES},
        "covered_partly_uncovered": {"covered": by_state.get("covered", 0), "partly_covered": by_state.get("partly", 0),
                                     "uncovered": by_state.get("queued", 0) + by_state.get("empty", 0),
                                     "of_which_queued": by_state.get("queued", 0)},
        "by_gap_class": {g: by_gap.get(g, 0) for g in GAP_CLASSES},
        "by_class": {k: dict(Counter(r.state for r in rows if r.klass == k)) for k in sorted({r.klass for r in rows})},
        "by_section": by_section,
        "opposed_pairs": dict(opp), "opposed_pairs_by_source": {k: dict(v) for k, v in sorted(opp_by_source.items())},
        "pair_kinds": dict(Counter(r.pair_kind for r in rows)),
        "labels": {"existing_mapped": labels_mapped.get(("existing", True), 0),
                   "existing_unmapped": labels_mapped.get(("existing", False), 0),
                   "queued_mapped": labels_mapped.get(("queued", True), 0),
                   "queued_unmapped": labels_mapped.get(("queued", False), 0),
                   "existing_primary_in_scope": primaries_in_scope},
        "hidden": list(hidden),
        "not_character": {"n": len(nc_rows), "heads": [r.id for r in nc_rows],
                          "by_state": dict(Counter(r.state for r in nc_rows)),
                          "by_gap_class": dict(Counter(r.gap_class for r in nc_rows)),
                          "by_class": dict(Counter(r.klass for r in nc_rows))},
        "character_ratings": ({"rated": len(rated), "unrated": len(all_rows) - len(rated),
                               "by_rating": {k: rating_counts.get(k, 0) for k in ("0", "1", "2")}}
                              if ratings is not None else None),
        "head_scope": scope_meta,
    }


# --------------------------------------------------------------------------- writing

def _links(stems: Sequence[str], source: str, label_heads: Mapping[str, Mapping]) -> str:
    return ", ".join(trait_link(s, source, label=label_heads.get(s, {}).get("label") or s) for s in stems)


def render_markdown(report: CoverageReport, index: RogetIndex, label_heads: Mapping[str, Mapping], *,
                    unresolved_note: Optional[str] = None) -> str:
    s = report.summary
    all_rows = report.rows
    rows = [r for r in all_rows if not is_not_character(r)]
    nc = s.get("not_character") or {"n": 0}
    scope = s.get("head_scope")
    cpu = s["covered_partly_uncovered"]
    opp = s["opposed_pairs"]
    L: list[str] = []
    L.append("# Roget coverage map (workstream 2)")
    L.append("")
    L.append("Which of the dispositional heads of Roget's Thesaurus (1911; Classes IV-VI, intellect, volition and "
             "the affections, plus the Class I-III heads whose adjectives hold one of our labels) the trait corpus "
             "already occupies.  A **head** is one numbered entry of the thesaurus (604 Resolution); an **opposed "
             "head** is its correlative (605 Irresolution), as Roget printed it in the Tabular Synopsis of the "
             "1911 edition ([synopsis_pairs.json](./synopsis_pairs.json), "
             "[synopsis_readout.md](./synopsis_readout.md)), by rule for the heads the synopsis does not print; "
             "the pairing is [head_pairs.json](./head_pairs.json).  Each trait is placed on heads by "
             "[label_heads.json](./label_heads.json): its **primary** head (where its sense sits) and any "
             "**secondary** heads (other senses the description also covers).  Data: [heads.json](./heads.json); "
             "spot check of the placement: [map_spotcheck.md](./map_spotcheck.md); method: "
             "[coding_plan_02_roget_wordnet.md](../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md).")
    L.append("")
    L.append("States: **covered** (an existing trait has the head as its primary), **partly covered** (only as a "
             "secondary), **queued** (only a label waiting in [seed_queue.json](../../seed_queue.json)), **empty**.  "
             "Gap classes: **pair_completion** (empty, its opposed head covered: a word here would complete a pair), "
             "**pair_empty** (empty, with an opposed head that is not covered), **singleton_empty** (empty, no "
             "opposed head found), **queued_only**, **partly_covered**, **crowded** (three or more traits have it "
             "as their primary), **covered**.")
    L.append("")
    if scope:
        L.append("**Not character**: a head the head-scope check rated 0, few or none of its adjectives describing "
                 "a person's character (Haiku 5.5, one rating per head, rubric "
                 "[roget_head_scope.md](../../../reports/trait_gap_generation/rubrics/roget_head_scope.md) version "
                 f"{scope.get('rubric_version')}; ratings in [head_scope.json](./head_scope.json), validation in "
                 "[head_scope_readout.md](./head_scope_readout.md)).  Such a head keeps its state, but is listed "
                 "apart below and left out of every count but the first; the harvest skips it.")
        L.append("")
    L.append("## Headline")
    L.append("")
    L.append(f"- Heads in scope: **{s['n_heads']}** ({s['n_dispositional']} dispositional, "
             f"{s['class_i_iii_added']} from Classes I-III).")
    if scope:
        cr = s.get("character_ratings") or {}
        br = cr.get("by_rating", {})
        L.append(f"- Not character (rated 0): **{nc['n']}** heads, left out of the counts below "
                 f"(ratings: 2 on {br.get('2', 0)}, 1 on {br.get('1', 0)}, 0 on {br.get('0', 0)}; "
                 f"{cr.get('unrated', 0)} unrated, mostly heads with no adjectives).")
    L.append(f"- Covered **{cpu['covered']}**, partly covered **{cpu['partly_covered']}**, uncovered "
             f"**{cpu['uncovered']}** (of which {cpu['of_which_queued']} have a queued label only).")
    L.append(f"- Opposed pairs in scope: both poles covered **{opp.get('both_poles_covered', 0)}**, one pole "
             f"**{opp.get('one_pole_covered', 0)}**, neither **{opp.get('neither_pole_covered', 0)}** (by the "
             f"pairing's evidence: {json.dumps(s['opposed_pairs_by_source'])}).")
    lab = s["labels"]
    L.append(f"- Labels placed: {lab['existing_mapped']} existing traits with a primary head "
             f"({lab['existing_unmapped']} without; {lab['existing_primary_in_scope']} of the primaries in scope), "
             f"{lab['queued_mapped']} queued labels ({lab['queued_unmapped']} without).")
    L.append(f"- Gap classes: " + ", ".join(f"{g} {s['by_gap_class'][g]}" for g in GAP_CLASSES) + ".")
    if unresolved_note:
        L.append(f"- {unresolved_note}")
    L.append("")
    L.append("## By section")
    L.append("")
    if scope:
        L.append("| class / section | covered | partly | queued | empty | not character |")
        L.append("|---|---|---|---|---|---|")
    else:
        L.append("| class / section | covered | partly | queued | empty |")
        L.append("|---|---|---|---|---|")
    for key, d in s["by_section"].items():
        tail = f" {d.get('not_character', 0)} |" if scope else ""
        L.append(f"| {key} | {d['covered']} | {d['partly']} | {d['queued']} | {d['empty']} |" + tail)
    L.append("")

    def head_ref(h: Optional[str]) -> str:
        return f"{h} {index.heads[h].title}" if h and h in index.heads else "-"

    for g in HARVEST_CLASSES + ("partly_covered",):
        sel = [r for r in rows if r.gap_class == g]
        L.append(f"## {g} ({len(sel)})")
        L.append("")
        if not sel:
            L.append("None.")
            L.append("")
            continue
        L.append("| head | section | opposed head | its traits | queued | parked | secondary of |")
        L.append("|---|---|---|---|---|---|---|")
        for r in sel:
            L.append(f"| {head_ref(r.id)} | {r.klass} {r.section}{' / ' + r.path.split(' > ')[-1] if r.path.count(' > ') >= 3 else ''} | "
                     f"{head_ref(r.partner)}{' (' + r.pair_source + ')' if r.partner else ''} | "
                     f"{_links(r.partner_existing, 'existing', label_heads) or '-'} | "
                     f"{_links(r.queued_active, 'queued', label_heads) or '-'} | "
                     f"{_links(r.queued_parked, 'queued', label_heads) or '-'} | "
                     f"{_links(r.existing_secondary, 'existing', label_heads) or '-'} |")
        L.append("")
    nc_rows = [r for r in all_rows if is_not_character(r)]
    if nc_rows:
        L.append(f"## Not character ({len(nc_rows)})")
        L.append("")
        L.append("Rated 0 by the head-scope check; the reasons are in [head_scope.json](./head_scope.json).  A "
                 "covered head here is one a trait was placed on although its adjectives are not about character.")
        L.append("")
        L.append("| head | section | state | its traits | queued | secondary of |")
        L.append("|---|---|---|---|---|---|")
        for r in nc_rows:
            L.append(f"| {head_ref(r.id)} | {r.klass} {r.section} | {r.state} | "
                     f"{_links(r.existing, 'existing', label_heads) or '-'} | "
                     f"{_links(r.queued_active, 'queued', label_heads) or '-'} | "
                     f"{_links(r.existing_secondary, 'existing', label_heads) or '-'} |")
        L.append("")
    crowded = sorted([r for r in rows if r.state == "covered"], key=lambda r: (-r.n_existing, index.position(r.id)))
    L.append("## Most crowded heads")
    L.append("")
    L.append("| head | traits with it as primary |")
    L.append("|---|---|")
    for r in crowded[:15]:
        L.append(f"| {head_ref(r.id)} ({r.n_existing}) | {_links(r.existing, 'existing', label_heads)} |")
    L.append("")
    L.append("## Class I-III heads brought in, with the labels that brought them")
    L.append("")
    L.append("| head | state | trigger labels |")
    L.append("|---|---|---|")
    for r in all_rows:
        if r.triggers:
            src = {t: label_heads.get(t, {}).get("source", "existing") for t in r.triggers}
            L.append(f"| {head_ref(r.id)} | {r.state}{' (not character)' if is_not_character(r) else ''} | "
                     + ", ".join(trait_link(t, src[t], label=label_heads.get(t, {}).get('label') or t) for t in r.triggers)
                     + " |")
    L.append("")
    L.append("## Covered heads")
    L.append("")
    L.append("| head | traits (primary) |")
    L.append("|---|---|")
    for r in rows:
        if r.state == "covered":
            L.append(f"| {head_ref(r.id)} | {_links(r.existing, 'existing', label_heads)} |")
    L.append("")
    return "\n".join(L)


def write_coverage(report: CoverageReport, json_path: Path, md_path: Optional[Path], *, index: RogetIndex,
                   label_heads: Mapping[str, Mapping], inputs: Sequence = (), unresolved_note: Optional[str] = None) -> None:
    from assistant_axis.plot_metadata import json_metadata

    env = json_metadata(report.to_json(), inputs=list(inputs), title="Roget coverage map (workstream 2)")
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    from .parse import dumps_one_per_line
    atomic_write_text(dumps_one_per_line(env, "rows"), json_path)
    if md_path is not None:
        atomic_write_text(render_markdown(report, index, label_heads, unresolved_note=unresolved_note), Path(md_path))


def load_coverage(path: Path) -> CoverageReport:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d)
    return CoverageReport(rows=[HeadRow(**r) for r in d["rows"]], summary=d["summary"], hidden=d.get("hidden") or [])
