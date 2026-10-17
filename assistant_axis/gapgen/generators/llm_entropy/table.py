"""Items and the items table, no API (plan section 6, ``table.py``; task 4).

:func:`build_items` turns the runs' recorded answers into one :class:`Item` per emitted item, deterministically
(records in a fixed order, the usable answer of every call: the last that parsed).  Family c's items take their
English label, gloss and antonym from the back-translation call of their answer (matched by the answer's
``custom_id`` and the item's index); the original label is ``raw`` and the romanisation ``backtranslated_from``.
Family b's items are the redacted ones its records carry (section 5a; a real seed's name-bearing label was dropped
before anything was written).  Every item gets its stem (``normalize_candidate``), its Zipf (``freq.zipf_info``;
recorded, never a gate: no generator-side frequency floor) and its :func:`.parse.label_problem`.

:func:`build_table` merges the items into one row per distinct stem (section 6): every source kept (one per call that
emitted the stem, with its gloss, antonym, kind and ``source_ref``), ``n_sources``, the families, languages and
models, the gloss of the stem's most frequent reading (readings: the glosses grouped by embedding cosine >=
:data:`GLOSS_FLOOR`, when an embedder is given; else by the exact gloss), ``gloss_divergent``, the antonyms, the kind
guesses, the membership tags (``exists``, ``queued``, ``registered``, ``registered_decided``, ``net_new``; the
structural generator's :func:`~..structural.postprocess.tag_membership`) and ``pair_completion_hint`` (an antonym that
is a corpus trait with a ``non-X`` label or a ``singleton`` arrangement).  **No tag drops a row.**  Items with no stem
(a label that does not normalise, a (c) item with no back-translation) are counted, not rows.

**Rank** (section 7): ``n_sources`` descending; then rows with a ``pair_completion_hint``; then, within each such
tier, a round-robin over the rows' primary families (a, b, c, d, e), so that one family cannot fill a wave; within a
family, emission order.

The table is written only when it changed (byte-identical on rerun), a changed one first copied to ``.bak.<UTC>``.
"""
from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.registry import utc_stamp

from . import ITEMS_TABLE_PATH, SCHEMA_VERSION
from .calls import HAIKU, final_records, model_tag
from .parse import label_problem, parse_backtranslation, parse_reply
from .prompts import FAMILIES

#: Two readings of a stem are one when their glosses' embedding cosine is at least this (plan section 6: divergent
#: below 0.6).
GLOSS_FLOOR = 0.6
FAMILY_ORDER: dict[str, int] = {f: i for i, f in enumerate(FAMILIES)}


@dataclass
class Item:
    """One emitted item (section 6)."""
    item_id: str
    family: str
    prompt_id: str
    run: int
    stage: int
    language: str
    model: str
    raw: Optional[str]
    label: Optional[str]
    gloss: Optional[str]
    antonym: Optional[str]
    kind: Optional[str]
    ambiguity_flag: Optional[bool]
    probability: Optional[float]
    stem: Optional[str]
    zipf_min: Optional[float]
    label_problem: Optional[str]
    backtranslated_from: Optional[str] = None
    listicle: Optional[bool] = None
    order: int = 0
    source_ref: Optional[str] = None
    meta: dict = field(default_factory=dict)       # domain, mode, constraint, seed kind and era, base prompt


def source_ref(prompt_id: str, run: int, model: str) -> str:
    """``llm_entropy:<prompt id>:r<run>``, with ``:<model tag>`` for a model other than Haiku 5.5 (so that the two
    arms of the model test are two sources of a stem, not one)."""
    return f"llm_entropy:{prompt_id}:r{int(run)}" + ("" if model == HAIKU else f":{model_tag(model)}")


def parse_source_ref(ref: str) -> dict:
    """``{"family", "prompt_id", "run", "model_tag", "language", "base_prompt_id"}`` of a ``source_ref``;
    ``ValueError`` for anything else."""
    parts = str(ref).split(":")
    if len(parts) < 4 or parts[0] != "llm_entropy" or parts[1] not in FAMILIES:
        raise ValueError(f"not an llm_entropy source_ref: {ref!r}")
    tag = None
    if not parts[-1].startswith("r") or not parts[-1][1:].isdigit():
        tag = parts.pop()
    if not parts[-1].startswith("r") or not parts[-1][1:].isdigit():
        raise ValueError(f"no run in {ref!r}")
    run = int(parts.pop()[1:])
    prompt_id = ":".join(parts[1:])
    fam = parts[1]
    return {"family": fam, "prompt_id": prompt_id, "run": run, "model_tag": tag or model_tag(HAIKU),
            "language": parts[2] if fam == "c" and len(parts) > 2 else "en",
            "base_prompt_id": ":".join(parts[2:]) if fam == "d" else None}


def _record_order(r: Mapping) -> tuple:
    return (FAMILY_ORDER.get(r.get("family"), 9), str(r.get("prompt_id")), int(r.get("run") or 1),
            int(r.get("stage") or 1), str(r.get("model")))


def _zipf(label: str, zipf_fn: Optional[Callable[[str], float]]) -> Optional[float]:
    from assistant_axis.gapgen.freq import zipf_info
    try:
        return float(zipf_info(label, zipf_fn=zipf_fn).zipf_min)
    except ValueError:
        return None


def build_items(records: Sequence[Mapping], *, zipf_fn: Optional[Callable[[str], float]] = None) -> tuple[list[Item],
                                                                                                             dict]:
    """``(items, counts)``: one item per emitted item of every usable generating answer (module docstring), and
    ``counts`` (answers read, items without a back-translation, items with no stem, by family)."""
    gen = sorted([r for r in final_records(records, step="generate").values()]
                 + [r for r in final_records(records, step="verbalized").values()], key=_record_order)
    bts: dict[str, dict] = {}
    for r in final_records(records, step="backtranslate").values():
        src = (r.get("meta") or {}).get("source_custom_id")
        if not src:
            continue
        bt, _ = parse_backtranslation(r.get("text"), int((r.get("meta") or {}).get("n_items") or 0))
        if bt is not None:
            bts[src] = bt.by_index
    counts: Counter = Counter()
    items: list[Item] = []
    order = 0
    for r in gen:
        fam = r.get("family")
        counts[f"answers_{fam}"] += 1
        if r.get("items") is not None:
            raw_items = list(r["items"])
        else:
            rep, _ = parse_reply(r.get("text"), multilingual=fam == "c")
            raw_items = rep.items if rep is not None else []
        meta = dict(r.get("meta") or {})
        by_index = bts.get(r.get("custom_id")) if fam == "c" else None
        for i, it in enumerate(raw_items, 1):
            order += 1
            raw = it.get("label")
            label, gloss, antonym, rom, listicle = raw, it.get("gloss"), it.get("antonym"), None, None
            if fam == "c":
                bt = (by_index or {}).get(i)
                rom = it.get("romanization")
                if bt is None:
                    label, gloss, antonym = None, None, None
                    counts["c_without_backtranslation"] += 1
                else:
                    label, gloss, antonym = bt.get("label"), bt.get("gloss"), bt.get("antonym")
                    rom = bt.get("romanization") or rom
                    listicle = bt.get("listicle")
            why = label_problem(label) if label is not None else "no back-translation"
            stem = None
            if label is not None:
                try:
                    stem = normalize_candidate(label).stem
                except ValueError:
                    stem = None
            if stem is None:
                counts[f"no_stem_{fam}"] += 1
            run, model = int(r.get("run") or 1), str(r.get("model"))
            items.append(Item(
                item_id=f"{r.get('prompt_id')}|r{run}|s{int(r.get('stage') or 1)}|{model_tag(model)}|{i}",
                family=fam, prompt_id=str(r.get("prompt_id")), run=run, stage=int(r.get("stage") or 1),
                language=str(r.get("language") or "en"), model=model, raw=raw, label=label, gloss=gloss,
                antonym=antonym, kind=it.get("kind"), ambiguity_flag=it.get("ambiguity_flag"),
                probability=it.get("probability"), stem=stem,
                zipf_min=_zipf(label, zipf_fn) if stem is not None else None, label_problem=why,
                backtranslated_from=rom, listicle=listicle, order=order,
                source_ref=source_ref(str(r.get("prompt_id")), run, model),
                meta={k: meta.get(k) for k in ("domain", "mode", "constraint", "seed_kind", "era", "base_prompt_id",
                                               "with_probabilities") if meta.get(k) is not None}))
    return items, dict(sorted(counts.items()))


# --------------------------------------------------------------------------- the table

def _readings(glosses: Sequence[str], embed: Optional[Callable[[Sequence[str]], object]], floor: float
              ) -> list[list[int]]:
    """Indices of ``glosses`` grouped into readings: greedily, each joining the first reading whose first gloss is at
    cosine >= ``floor`` (``embed`` gives unit rows); without ``embed``, equal glosses only."""
    if not glosses:
        return []
    groups: list[list[int]] = []
    if embed is None:
        first: dict[str, int] = {}
        for i, g in enumerate(glosses):
            if g in first:
                groups[first[g]].append(i)
            else:
                first[g] = len(groups)
                groups.append([i])
        return groups
    import numpy as np
    E = np.asarray(embed(list(glosses)), dtype=float)
    for i in range(len(glosses)):
        for g in groups:
            if float(E[i] @ E[g[0]]) >= floor:
                g.append(i)
                break
        else:
            groups.append([i])
    return groups


def _most_common(values: Sequence, *, key_order: Sequence[int]) -> object:
    """The commonest value, ties by first appearance (``key_order`` gives each value's position)."""
    c = Counter(values)
    first = {}
    for v, o in zip(values, key_order):
        first.setdefault(v, o)
    return sorted(c, key=lambda v: (-c[v], first[v]))[0]


def _pair_hint(antonyms: Sequence[str], corpus) -> Optional[str]:
    for a in antonyms:
        try:
            st = normalize_candidate(a).stem
        except ValueError:
            continue
        cur = corpus.renamed.get(st, st)
        if cur in corpus.stems and corpus.is_unpaired(cur):
            return cur
    return None


def build_table(items: Sequence[Item], *, corpus, queue: Mapping[str, str], registry: Mapping[str, Mapping],
                embed: Optional[Callable[[Sequence[str]], object]] = None, floor: float = GLOSS_FLOOR) -> list[dict]:
    """The distinct-stem rows in rank order (module docstring).  ``corpus``: ``structural.postprocess.Corpus``;
    ``queue``: ``load_queue_index``; ``registry``: ``registry_index`` of a folded registry; ``embed``: texts -> unit
    rows (the gloss readings; None: by exact gloss, ``gloss_divergent`` None)."""
    from ..structural.postprocess import tag_membership
    by: dict[str, list[Item]] = {}
    for it in sorted(items, key=lambda x: x.order):
        if it.stem:
            by.setdefault(it.stem, []).append(it)
    rows = []
    neg_stems = corpus.negative_label_stems
    for stem, its in by.items():
        clean = [x for x in its if x.label_problem is None] or its
        label = _most_common([x.label for x in clean], key_order=[x.order for x in clean])
        glossed = [x for x in its if x.gloss]
        groups = _readings([x.gloss for x in glossed], embed, floor)
        rep_items = [glossed[i] for i in max(groups, key=len)] if groups else []
        gloss = rep_items[0].gloss if rep_items else None
        # sources: one per call, the representative reading's first, then emission order
        lead = rep_items[0].item_id if rep_items else None
        srcs: dict[tuple, dict] = {}
        for x in sorted(its, key=lambda x: (x.item_id != lead, x.order)):
            k = (x.family, x.prompt_id, x.run, x.stage, x.model)
            if k in srcs:
                continue
            srcs[k] = {"family": x.family, "prompt_id": x.prompt_id, "run": x.run, "stage": x.stage, "model": x.model,
                       "language": x.language, "source_ref": x.source_ref, "label": x.label, "gloss": x.gloss,
                       "antonym": x.antonym, "kind": x.kind, "raw": x.raw if x.family == "c" else None,
                       "seed_kind": x.meta.get("seed_kind")}
        ants = [x.antonym for x in its if x.antonym]
        antonyms = sorted(set(ants), key=lambda a: (-ants.count(a), ants.index(a)))
        tags = tag_membership(stem, corpus_stems=corpus.stems, renamed=corpus.renamed,
                              negative_label_stems=neg_stems, queue=queue, registry=registry)
        support: Counter = Counter((x.family, x.prompt_id, x.model) for x in its)
        fams = sorted({x.family for x in its}, key=lambda f: FAMILY_ORDER.get(f, 9))
        zipfs = [x.zipf_min for x in its if x.zipf_min is not None]
        probs = [x.probability for x in its if x.probability is not None]
        rows.append({
            "schema_version": SCHEMA_VERSION, "stem": stem, "label": label, "gloss": gloss,
            "gloss_divergent": (len(groups) > 1) if embed is not None and groups else None,
            "n_readings": len(groups) if embed is not None else None,
            "antonyms": antonyms, "kinds": dict(sorted(Counter(x.kind for x in its if x.kind).items())),
            "ambiguity_flags": sum(1 for x in its if x.ambiguity_flag),
            "sources": list(srcs.values()), "n_sources": len(srcs), "n_items": len(its),
            "max_support": max(support.values()), "families": fams,
            "languages": sorted({x.language for x in its}), "models": sorted({x.model for x in its}),
            "primary_family": its[0].family, "first_order": its[0].order,
            "zipf_min": min(zipfs) if zipfs else None,
            "label_problem": label_problem(label),
            "raws": sorted({x.raw for x in its if x.family == "c" and x.raw})[:5],
            "backtranslated_from": sorted({x.backtranslated_from for x in its if x.backtranslated_from})[:5],
            "listicle": sum(1 for x in its if x.listicle),
            "probability_min": min(probs) if probs else None,
            "seed_kinds": dict(sorted(Counter(x.meta.get("seed_kind") for x in its
                                              if x.meta.get("seed_kind")).items())),
            "exists": tags.exists, "queued": tags.queued, "queue_status": tags.queue_status,
            "registered": tags.registered, "registered_by": list(tags.registered_by),
            "registered_decided": tags.registered_decided, "net_new": tags.net_new, "status": tags.status,
            "pair_completion_hint": _pair_hint(antonyms, corpus), "rank": None})
    return rank_rows(rows)


def rank_rows(rows: Sequence[dict]) -> list[dict]:
    """Rows in rank order with ``rank`` set (module docstring)."""
    tiers: dict[tuple, list[dict]] = {}
    for r in rows:
        tiers.setdefault((-int(r["n_sources"]), 0 if r.get("pair_completion_hint") else 1), []).append(r)
    out: list[dict] = []
    for t in sorted(tiers):
        per: dict[str, list[dict]] = {}
        for r in sorted(tiers[t], key=lambda r: r["first_order"]):
            per.setdefault(r["primary_family"], []).append(r)
        queues = [per[f] for f in sorted(per, key=lambda f: FAMILY_ORDER.get(f, 9))]
        i = 0
        while any(queues):
            q = queues[i % len(queues)]
            if q:
                out.append(q.pop(0))
            i += 1
    for k, r in enumerate(out, 1):
        r["rank"] = k
    return out


def table_text(rows: Sequence[Mapping]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def write_table(rows: Sequence[Mapping], path: Path = ITEMS_TABLE_PATH) -> Optional[Path]:
    """Write the table unless unchanged (then nothing is written); a changed file is first copied to
    ``.bak.<UTC>``.  Returns the backup, if any."""
    path = Path(path)
    body = table_text(rows)
    backup = None
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return None
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, path)
    return backup


def load_items_table(path: Path = ITEMS_TABLE_PATH) -> list[dict]:
    """The items table's rows in rank order (frozen interface)."""
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def items_text(items: Iterable[Item]) -> str:
    return "".join(json.dumps(asdict(x), ensure_ascii=False, sort_keys=True) + "\n" for x in items)


__all__ = ["GLOSS_FLOOR", "Item", "source_ref", "parse_source_ref", "build_items", "build_table", "rank_rows",
           "table_text", "write_table", "load_items_table", "items_text"]
