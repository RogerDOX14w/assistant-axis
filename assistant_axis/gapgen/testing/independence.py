"""Each generator's class and mechanism, and which corpus traits a recovery test must not count against it.

Plan 13 § 6 ("Independence row") and decisions 4-5 of its § 1.  A **stream** is a generator, or a part of one whose
inputs differ (the censuses' two word lists; WordNet's closure walk and its antonym walk).  Each stream has:

* a **class**: ``independent`` (its inputs name no corpus trait: a census list, WordNet's trait-noun closure, the
  IPIP item pool, the base model's frames), ``seeded`` (its inputs are built from the corpus: Roget's gap heads,
  WordNet's antonyms of corpus labels, the antonym check, plan 09's operators), ``separate_population`` (the
  alignment sweep: AI dispositions, tested on its own) or ``not_a_generator`` (the states and physical passes,
  whose rows are attributed to the source row's generator; the M1 validation pool and the manual pool);
* a **mechanism**, the capture-recapture occasion it belongs to (Roger, 2026-10-12: occasions are mechanisms, not
  generators): ``lexicon`` (the censuses, Roget, WordNet), ``ipip``, ``base_model``, ``masked_lm``, ``alignment``
  (a separate population) and ``corpus`` (generators that start from the corpus's own traits);
* an **exclusion rule**: which corpus traits came from the stream's own source, so that recovering them is no
  evidence (:func:`provenance_excluded`).  On 2026-10-13 no trait file came from gap generation (the 38 promoted
  words are seed-queue ``candidate`` entries), so the rule excludes nothing yet.

No seeded generator hides the hidden traits from its own seed (plan 13 § 1, "Generator-side hiding exists for no
seeded generator"), so a seeded stream's recall is the harness-side figure, marked ``harness_side_only``.

:func:`stream_of` names a source's stream; :func:`attributed_sources` follows a states-pass source to the row it was
made from (pre-registered question 6); :func:`classify` gives a row's streams; :func:`independence_table` the
rows of ``independence.json``.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

CLASSES: tuple[str, ...] = ("independent", "seeded", "separate_population", "not_a_generator")
MECHANISMS: tuple[str, ...] = ("lexicon", "ipip", "base_model", "masked_lm", "alignment", "corpus")
#: The mechanisms that are capture-recapture occasions of the main population (the alignment sweep is a separate
#: population; ``corpus`` generators start from the corpus and so are no independent sample of what it lacks).
OCCASION_MECHANISMS: tuple[str, ...] = ("lexicon", "ipip", "base_model", "masked_lm")
#: The sources that name rows rather than generators: their rows count for the source row's generator.
ATTRIBUTED_GENERATORS: tuple[str, ...] = ("states_pass",)
#: The pools that are not generators at all (left out of the pooled harness and the per-generator figures).
POOL_GENERATORS: tuple[str, ...] = ("m1_validation", "manual", "testing")
KEPT_DECISIONS: tuple[str, ...] = ("new", "grey")


@dataclass(frozen=True)
class Stream:
    """One row of the table of plan 13 § 6 as written in code (verified against each generator's code, 2026-10-13)."""
    generator: str
    stream: str
    cls: str
    mechanism: Optional[str]
    inputs: str
    exclusion_rule: str
    generator_side_hiding: bool = False
    #: Words the trait file's ``source`` field would carry if the trait came from this stream's source (lower case).
    source_patterns: tuple[str, ...] = ()
    note: Optional[str] = None

    def __post_init__(self):
        if self.cls not in CLASSES:
            raise ValueError(f"unknown class {self.cls!r}")
        if self.mechanism is not None and self.mechanism not in MECHANISMS:
            raise ValueError(f"unknown mechanism {self.mechanism!r}")

    @property
    def harness_side_only(self) -> bool:
        """A seeded stream without generator-side hiding: its recall is only the harness's."""
        return self.cls == "seeded" and not self.generator_side_hiding


def _queue_rule(g: str) -> str:
    return f"a corpus trait whose seed-queue entry carries `source:{g}` (or a `gap_registry_key`), or a renamed_from of one"


_S = Stream
#: ``(generator, stream) -> Stream``.  Order is the dashboard's.
STREAMS: dict[tuple[str, str], Stream] = {(s.generator, s.stream): s for s in (
    _S("censuses", "tda", "independent", "lexicon",
       "the Trait Descriptive Adjectives census list (Condon, Coughlin and Weston 2022); source_ref prefix tda:",
       "a corpus trait whose file's `source` names the TDA list, or " + _queue_rule("censuses"),
       source_patterns=("trait descriptive adjectives", "condon, coughlin", "condon et al")),
    _S("censuses", "allport", "independent", "lexicon",
       "Allport and Odbert's 1936 word list as digitised on OSF; source_ref prefix allport:",
       "a corpus trait whose file's `source` names Allport and Odbert's list (not Allport and Ross's religious "
       "orientation scale, which extrinsic_allport and intrinsic_allport name), or " + _queue_rule("censuses"),
       source_patterns=("allport & odbert", "allport and odbert", "allport-odbert")),
    _S("roget", "heads", "seeded", "lexicon",
       "Roget's Thesaurus heads chosen as the gap heads of the coverage report, which is built from corpus labels "
       "(roget/harvest.py select_heads); the harvest within a head is independent",
       "a corpus trait whose file's `source` names Roget, or " + _queue_rule("roget"),
       source_patterns=("roget",),
       note="no `recover` command: generator-side hiding not built"),
    _S("wn_clusters", "closure", "independent", "lexicon",
       "WordNet's (OEWN) trait-noun closure: adjectives under the trait synsets (no partner_hint)",
       "a corpus trait whose file's `source` names OEWN or WordNet, or " + _queue_rule("wn_clusters"),
       source_patterns=("oewn", "wordnet")),
    _S("wn_clusters", "antonym", "seeded", "lexicon",
       "WordNet antonyms of corpus labels with no partner file (partner_hint set)",
       "a corpus trait whose queue entry carries `source:wn_clusters`, or whose file's `source` names OEWN",
       source_patterns=("oewn", "wordnet")),
    _S("ipip", "ipip", "independent", "ipip",
       "the International Personality Item Pool's items, clustered and named blind (no corpus label shown)",
       "a corpus trait whose file's `source` names the IPIP, or " + _queue_rule("ipip"),
       source_patterns=("ipip", "international personality item pool")),
    _S("base_model", "base_model", "independent", "base_model",
       "a base model's continuations of list and gloss frames (base_model/prompts.py names no corpus trait)",
       _queue_rule("base_model")),
    _S("masked_lm", "masked_lm", "independent", "masked_lm",
       "a masked language model's fills of trait frames (no run submitted yet)", _queue_rule("masked_lm")),
    _S("alignment_sweep", "alignment_sweep", "separate_population", "alignment",
       "AI-disposition phrases extracted from alignment papers, incident lists and usage policies",
       _queue_rule("alignment_sweep"),
       note="its occasions are its own runs (the papers run and variant B), tested on their own"),
    _S("antonym_check", "antonym_check", "seeded", "corpus",
       "the antonym check's candidate antonyms of corpus traits (generate_antonyms.py answers)",
       _queue_rule("antonym_check")),
    _S("structural", "structural", "seeded", "corpus",
       "plan 09's structural operators over corpus arrangements (not built)", _queue_rule("structural")),
    _S("states_pass", "states_pass", "not_a_generator", None,
       "names the states pass proposed for rows M1 held as states; source_ref is the source row's key",
       "attributed to the source row's generator (pre-registered question 6)"),
    _S("physical_pass", "physical_pass", "not_a_generator", None,
       "re-judges rows on the physical holding list; submits no row of its own",
       "attributed to the row's own generators"),
    _S("m1_validation", "m1_validation", "not_a_generator", None,
       "the M1 validation pool (corpus labels and known non-traits)", "a pool, not a generator"),
    _S("manual", "manual", "not_a_generator", None,
       "words Roger sent to the pipeline by hand (W23)", "a pool, not a generator"),
    _S("testing", "paraphrase_set", "not_a_generator", None,
       "plan 13's paraphrase sanity set (a scratch registry only)", "a test set, not a generator"),
)}


def generator_streams(generator: str) -> list[Stream]:
    return [s for (g, _), s in STREAMS.items() if g == generator]


def stream_of(source: Mapping) -> str:
    """The stream a registry source belongs to: the censuses by their list (``source_ref`` prefix ``tda`` or
    ``allport``), WordNet's walk by ``partner_hint`` (``antonym`` when set, else ``closure``), Roget's ``heads``, and
    any other source its generator's name (a states-pass source stays ``states_pass``: :func:`attributed_sources`
    follows it)."""
    g = source.get("generator") or ""
    if g == "censuses":
        ref = str(source.get("source_ref") or "")
        head = re.split(r"[:#]", ref, maxsplit=1)[0].lower()
        return head if head in ("tda", "allport") else "tda"
    if g == "wn_clusters":
        return "antonym" if source.get("partner_hint") else "closure"
    if g == "roget":
        return "heads"
    return g


def stream_rule(generator: str, stream: str) -> Optional[Stream]:
    return STREAMS.get((generator, stream))


def attributed_sources(row: Mapping, rows: Mapping[str, Mapping], *, _seen: Optional[set] = None) -> list[dict]:
    """The generator sources a row counts for: its own sources, with each states-pass source replaced by the sources
    of the row it names (``source_ref``, a registry key), followed recursively, a cycle or a missing row ending the
    walk; pools (:data:`POOL_GENERATORS`) are kept (the caller decides).  Each entry ``{"generator", "run_id",
    "stream", "via"}``, ``via`` the states-pass key it was reached through (``None`` for a direct source); entries
    unique by (generator, run_id, stream)."""
    seen = set(_seen or ()) | {row.get("key")}
    out: dict[tuple, dict] = {}
    for s in row.get("sources") or []:
        g = s.get("generator")
        if g in ATTRIBUTED_GENERATORS:
            ref = s.get("source_ref")
            src = rows.get(ref) if ref else None
            if src is None or ref in seen:
                continue
            for x in attributed_sources(src, rows, _seen=seen):
                k = (x["generator"], x["run_id"], x["stream"])
                out.setdefault(k, dict(x, via=x.get("via") or ref))
            continue
        k = (g, s.get("run_id"), stream_of(s))
        out.setdefault(k, {"generator": g, "run_id": s.get("run_id"), "stream": k[2], "via": None})
    return [out[k] for k in sorted(out, key=lambda k: (str(k[0]), str(k[1]), str(k[2])))]


@dataclass(frozen=True)
class Classified:
    generator: str
    run_id: Optional[str]
    stream: str
    cls: str
    mechanism: Optional[str]
    via: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


def classify(row: Mapping, rows: Optional[Mapping[str, Mapping]] = None) -> list[Classified]:
    """A row's streams with their class and mechanism (:func:`attributed_sources` when ``rows`` is given, else the
    row's own sources, a states-pass source left as ``states_pass``).  A source whose stream has no rule is
    ``not_a_generator`` with no mechanism (``independence --check`` reports it)."""
    srcs = attributed_sources(row, rows) if rows is not None else \
        [{"generator": s.get("generator"), "run_id": s.get("run_id"), "stream": stream_of(s), "via": None}
         for s in row.get("sources") or []]
    out = []
    for s in srcs:
        rule = stream_rule(s["generator"], s["stream"])
        out.append(Classified(s["generator"], s["run_id"], s["stream"], rule.cls if rule else "not_a_generator",
                              rule.mechanism if rule else None, s.get("via")))
    return out


def generators_of(row: Mapping, rows: Optional[Mapping[str, Mapping]] = None, *, pools: bool = False) -> list[str]:
    """The generators a row counts for (states-pass rows attributed), pools left out unless ``pools``."""
    gs = dict.fromkeys(c.generator for c in classify(row, rows))
    return [g for g in gs if pools or g not in POOL_GENERATORS + ATTRIBUTED_GENERATORS]


def mechanisms_of(row: Mapping, rows: Optional[Mapping[str, Mapping]] = None) -> list[str]:
    return list(dict.fromkeys(c.mechanism for c in classify(row, rows) if c.mechanism))


# --------------------------------------------------------------------------- provenance exclusion

def trait_sources(data_dir: Path) -> dict[str, dict]:
    """``{stem: {"source": str | None, "renamed_from": [stems]}}`` from the trait files (their raw ``source`` field,
    which :class:`novelty.CorpusTrait` does not carry)."""
    from assistant_axis.entity_id import normalize_to_file_name
    out = {}
    for p in sorted((Path(data_dir) / "traits" / "instructions").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rf = d.get("renamed_from")
        olds = rf if isinstance(rf, list) else ([rf] if rf else [])
        stems = []
        for o in olds:
            v = o.get("stem") or o.get("from") or o.get("old_stem") if isinstance(o, Mapping) else o
            if isinstance(v, str) and v:
                stems.append(normalize_to_file_name(v))
        out[p.stem] = {"source": d.get("source") if isinstance(d.get("source"), str) else None, "renamed_from": stems}
    return out


def _queue_entries(queue) -> list[Mapping]:
    if isinstance(queue, Mapping):
        return list(queue.get("entries") or [])
    return list(queue or [])


def provenance_excluded(stem: str, *, traits: Mapping[str, Mapping], queue, generator: Optional[str] = None
                        ) -> Optional[str]:
    """Why the corpus trait ``stem`` came from a generator's own source (and so is excluded from that generator's
    recovery denominator), or ``None``.  ``traits``: :func:`trait_sources`; ``queue``: the seed queue.  Reasons:
    ``file source names <pattern> (<generator>/<stream>)``; ``queue entry <stem> tagged source:<generator>``;
    ``queue entry <stem> handed to the registry as <key>`` (a ``gap_registry_key``); each also through one of the
    trait's ``renamed_from`` stems.  ``generator``: only that generator's rules (default: any)."""
    t = traits.get(stem) or {}
    names = [stem] + list(t.get("renamed_from") or [])
    src = (t.get("source") or "").lower()
    if src:
        for (g, st), rule in STREAMS.items():
            if generator and g != generator:
                continue
            for pat in rule.source_patterns:
                if pat in src:
                    return f"file source names {pat!r} ({g}/{st})"
    by_stem = {}
    for e in _queue_entries(queue):
        if isinstance(e, Mapping) and e.get("stem"):
            by_stem.setdefault(e["stem"], e)
    for n in names:
        e = by_stem.get(n)
        if not e:
            continue
        tags = [str(x) for x in e.get("tags") or []]
        for tg in tags:
            if tg.startswith("source:") and (generator is None or tg == f"source:{generator}"):
                return f"queue entry {n} tagged {tg}" + (f" (renamed to {stem})" if n != stem else "")
        if e.get("gap_registry_key") and generator is None:
            return f"queue entry {n} handed to the registry as {e['gap_registry_key']}" + \
                (f" (renamed to {stem})" if n != stem else "")
    return None


def excluded_stems(generator: str, *, traits: Mapping[str, Mapping], queue) -> dict[str, str]:
    """``{stem: reason}``: the corpus traits :func:`provenance_excluded` excludes for ``generator``
    (``recovery_test.py --exclude-provenance``)."""
    out = {}
    for s in sorted(traits):
        why = provenance_excluded(s, traits=traits, queue=queue, generator=generator)
        if why:
            out[s] = why
    return out


# --------------------------------------------------------------------------- the table

def independence_table(rows: Mapping[str, Mapping], traits: Mapping[str, Mapping], queue) -> list[dict]:
    """The rows of ``independence.json`` (plan 13 § 6): one per stream in :data:`STREAMS` and one per stream the
    registry has that :data:`STREAMS` lacks (class ``not_a_generator``, flagged ``no_rule``), with ``n_rows``
    (registry rows with a source in the stream, a states-pass row attributed), ``n_trait`` (M1 verdict ``trait``),
    ``n_kept`` (of those, M3 ``new`` or ``grey``) and ``n_excluded_from_denominator`` (corpus traits
    :func:`provenance_excluded` excludes for the generator)."""
    n_rows, n_trait, n_kept = Counter(), Counter(), Counter()
    seen_streams: set = set()
    for r in rows.values():
        verdict = (r.get("filter") or {}).get("verdict")
        dec = (r.get("novelty") or {}).get("decision")
        for k in {(c.generator, c.stream) for c in classify(r, rows)}:
            seen_streams.add(k)
            n_rows[k] += 1
            n_trait[k] += verdict == "trait"
            n_kept[k] += verdict == "trait" and dec in KEPT_DECISIONS
        for s in r.get("sources") or []:                       # the passes themselves, as sources
            if s.get("generator") in ATTRIBUTED_GENERATORS:
                k = (s["generator"], stream_of(s))
                seen_streams.add(k)
    for r in rows.values():
        if any(s.get("generator") in ATTRIBUTED_GENERATORS for s in r.get("sources") or []):
            k = ("states_pass", "states_pass")
            n_rows[k] += 1
            n_trait[k] += (r.get("filter") or {}).get("verdict") == "trait"
            n_kept[k] += (r.get("filter") or {}).get("verdict") == "trait" and \
                (r.get("novelty") or {}).get("decision") in KEPT_DECISIONS
    excl_by_gen = {g: len(excluded_stems(g, traits=traits, queue=queue))
                   for g in {g for g, _ in STREAMS} if g not in POOL_GENERATORS}
    out = []
    keys = list(STREAMS) + sorted(k for k in seen_streams if k not in STREAMS)
    for k in keys:
        rule = STREAMS.get(k)
        row = {"generator": k[0], "stream": k[1],
               "class": rule.cls if rule else "not_a_generator",
               "mechanism": rule.mechanism if rule else None,
               "inputs": rule.inputs if rule else None,
               "generator_side_hiding": bool(rule.generator_side_hiding) if rule else False,
               "harness_side_only": bool(rule.harness_side_only) if rule else False,
               "exclusion_rule": rule.exclusion_rule if rule else None,
               "n_rows": n_rows[k], "n_trait": n_trait[k], "n_kept": n_kept[k],
               "n_excluded_from_denominator": excl_by_gen.get(k[0], 0)}
        if rule and rule.note:
            row["note"] = rule.note
        if not rule:
            row["no_rule"] = True
        out.append(row)
    return out


def missing_rules(rows: Mapping[str, Mapping]) -> list[tuple[str, str]]:
    """Registry streams with no rule in :data:`STREAMS` (``independence --check`` exits 1 on any)."""
    have = set()
    for r in rows.values():
        for s in r.get("sources") or []:
            have.add((s.get("generator"), stream_of(s)))
    return sorted(k for k in have if k not in STREAMS)


def table_markdown(table: Sequence[Mapping]) -> str:
    """The table for the dashboard and the acceptance report."""
    L = ["| generator | stream | class | mechanism | rows | M1 trait | M3 kept | excluded | inputs |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        cls = r["class"] + (" (harness side only)" if r.get("harness_side_only") else "")
        L.append(f"| {r['generator']} | {r['stream']} | {cls} | {r['mechanism'] or ''} | {r['n_rows']:,} | "
                 f"{r['n_trait']:,} | {r['n_kept']:,} | {r['n_excluded_from_denominator']} | "
                 f"{(r.get('inputs') or '').replace('|', '/')} |")
    return "\n".join(L) + "\n"


__all__ = ["CLASSES", "MECHANISMS", "OCCASION_MECHANISMS", "ATTRIBUTED_GENERATORS", "POOL_GENERATORS", "Stream",
           "STREAMS", "Classified", "stream_of", "stream_rule", "attributed_sources", "classify", "generators_of",
           "mechanisms_of", "trait_sources", "provenance_excluded", "excluded_stems", "independence_table",
           "missing_rules", "table_markdown", "generator_streams"]
