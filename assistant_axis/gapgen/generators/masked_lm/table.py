"""The generator's table: one row per distinct stem across models and passes (plan sections 5 and 6, ``table.py``).

:func:`build_table` takes the stored passes (``{"<pass>:<model>": PassResult}``) and the contrast scores, keeps
every word some generation pass **surfaced** (``n_top >= 1``: in the top 2,000 of at least one instance; every
accepted beam sequence; a Variant-B word whose pseudo-log-likelihood would place it there; the HHH probe's frames
are not a generation pass), and folds them by stem
(``normalize_to_file_name``).  Per row:

* ``best_logprob`` / ``best_frame`` / ``best_subject`` / ``mean_rank`` / ``n_instances_top2000`` from the entry with
  the best log-probability (``best_pass`` names it); ``passes`` and ``models`` list every entry; the surface is
  OEWN's spelling where Variant B listed the word, else the pass's;
* ``gender_log_odds`` from the single-mask pass (the best model's), a kept field and never a gate;
* ``trait_contrast`` / ``state_flag`` / ``physical_flag`` from the primary model's contrast scores (``score``);
* ``zipf``, ``freq_hard_reject``, ``freq_probe_band`` from ``gapgen.freq.zipf_info`` (never a local literal);
  ``wordnet`` and ``gloss_hint`` from OEWN's person-descriptive sense (the censuses' ``glosshint``, ``columns=()``);
  ``stoplist_flags`` (memberships: flagged, never dropped);
* ``eligible = not freq_hard_reject or gloss_hint`` (the platform's rescue route 2; ``masked_lm`` is not a curated
  generator: a model walk is a dictionary walk), ``ineligible_reason`` in ``below_hard_reject`` / ``malformed``;
* ``union_rank``: best log-probability descending, ties by Zipf descending, then surface;
* ``corpus_stem_match`` / ``queue_stem_match``: evaluation only, never read by eligibility or rank;
* added beyond the plan's schema (fields are added, never renamed): ``token_class`` (``single`` / ``subword`` /
  ``multiword`` under the primary model's tokenizer: the wave's selection reads it) and ``best_pass``.

Deterministic: the same aggregates give a byte-identical file (``write_table`` keeps the previous file as
``<path>.bak.<UTC>`` when the content changes).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.freq import FreqInfo, zipf_info
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.registry import utc_stamp

from ..censuses.glosshint import gloss_hint, person_sense
from . import MLM_TABLE_PATH
from .models import MODELS, PRIMARY_MODEL
from .wordlist import stoplist_flags

SCHEMA_VERSION = 1
ROW_FIELDS = ("schema_version", "surface", "stem", "label", "passes", "models", "best_frame", "best_subject",
              "best_logprob", "mean_rank", "n_instances_top2000", "gender_log_odds", "trait_contrast", "state_flag",
              "physical_flag", "zipf", "freq_hard_reject", "freq_probe_band", "wordnet", "gloss_hint",
              "stoplist_flags", "union_rank", "eligible", "ineligible_reason", "corpus_stem_match",
              "queue_stem_match", "token_class", "best_pass")
INELIGIBLE_REASONS = ("below_hard_reject", "malformed")
#: The passes whose words make the union.  The HHH probe's frames are left out: they exist to answer Roger's
#: question (its readout and the probe page report them), and on the real model their top 2,000 is mostly
#: verbs and participles ("used", "developed", "interacting"): 3,568 of the smoke run's 10,532 rows.
GENERATION_PASSES = ("single", "subword", "multiword", "variant_b")


@dataclass
class Lookups:
    """What the table looks up; :func:`default_lookups` wires the real ones, tests pass fakes."""
    senses: Callable[[str], list]                      # censuses.glosshint.adjective_senses
    freq: Callable[..., FreqInfo] = zipf_info          # the platform's frequency features
    zipf_word: Optional[Callable[[str], float]] = None  # per-word Zipf passed to ``freq`` (tests)
    token_class: Optional[Callable[[str], str]] = None  # the primary tokenizer's class of a surface
    is_proper: Callable[[str], bool] = lambda s: s[:1].isupper()   # OEWN spells it with a capital

    def freq_info(self, surface: str) -> FreqInfo:
        return self.freq(surface, zipf_fn=self.zipf_word) if self.zipf_word is not None else self.freq(surface)


def default_lookups(tokenizer=None) -> Lookups:  # pragma: no cover - needs wordfreq and the OEWN database
    from assistant_axis.gapgen import wordnet as gw

    from ..censuses.glosshint import adjective_senses
    from .models import token_class
    if not gw.ensure_oewn(download=False):
        raise SystemExit("OEWN is not installed in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn` first")
    w = gw.oewn()

    def proper(s: str) -> bool:
        try:
            return any(x.lemma()[:1].isupper() for x in w.words(s))
        except Exception:  # noqa: BLE001
            return False
    tc = (lambda s: token_class(s, tokenizer)[1]) if tokenizer is not None else None
    return Lookups(senses=lambda s: adjective_senses(s, wordnet=w), token_class=tc, is_proper=proper)


def _entries(aggregates: Mapping[str, object]) -> dict[str, list[tuple[str, str, dict]]]:
    """Surfaced entries by stem: ``{stem: [(pass key, model key, agg dict)]}``; unusable surfaces under
    ``"\\0<surface>"``."""
    out: dict[str, list] = {}
    for key in sorted(aggregates):
        res = aggregates[key]
        pass_name, model = key.split(":", 1)
        if pass_name not in GENERATION_PASSES:
            continue
        for w in sorted(res.aggs):
            a = res.aggs[w]
            a = a.as_dict() if hasattr(a, "as_dict") else dict(a)
            if int(a.get("n_top") or 0) < 1:
                continue
            try:
                stem = normalize_candidate(a.get("surface") or w).stem
            except ValueError:
                stem = "\0" + (a.get("surface") or w)
            out.setdefault(stem, []).append((key, model, a))
    return out


def _r(x: Optional[float], nd: int = 4) -> Optional[float]:
    return None if x is None else round(float(x), nd)


def build_table(aggregates: Mapping[str, object], *, lookups: Lookups, corpus_stems: Iterable[str] = (),
                queue_stems: Iterable[str] = (), contrasts: Optional[Mapping[str, Mapping]] = None,
                contrast_model: str = PRIMARY_MODEL) -> list[dict]:
    """The table rows in union-rank order (see the module docstring).  ``contrasts`` is ``{model key: {word:
    Contrast or its dict}}``."""
    corpus, queue = set(corpus_stems), set(queue_stems)
    con: dict[str, dict] = {}
    for w, c in ((contrasts or {}).get(contrast_model) or {}).items():
        d = c.as_dict() if hasattr(c, "as_dict") else dict(c)
        try:
            con.setdefault(normalize_candidate(w).stem, d)
        except ValueError:
            continue
    rows = []
    for stem, ents in _entries(aggregates).items():
        key, model, best = max(ents, key=lambda e: (float(e[2]["best_logprob"]), e[0]))
        vb = next((a for k, _, a in ents if k.startswith("variant_b:")), None)
        surface = (vb or best).get("surface") or best["word"]
        single = [a for k, _, a in sorted(ents, key=lambda e: -float(e[2]["best_logprob"]))
                  if k.startswith("single:") and a.get("gender_log_odds") is not None]
        malformed = stem.startswith("\0")
        try:
            norm = normalize_candidate(surface)
            label = norm.label
        except ValueError:
            malformed, label = True, surface
        hint = None if malformed else person_sense(lookups.senses(surface))
        gh = gloss_hint(label, hint, ()) if hint else None
        fi = None if malformed else lookups.freq_info(surface)
        if malformed:
            eligible, reason = False, "malformed"
        else:
            eligible = (not fi.hard_reject) or bool(gh)
            reason = None if eligible else "below_hard_reject"
        c = con.get(stem) if not malformed else None
        st = None if malformed else stem
        rows.append({
            "schema_version": SCHEMA_VERSION, "surface": surface, "stem": st, "label": label,
            "passes": sorted({k for k, _, _ in ents}),
            "models": sorted({MODELS[m].short if m in MODELS else m for _, m, _ in ents}),
            "best_frame": best.get("best_frame"), "best_subject": best.get("best_subject"),
            "best_logprob": _r(best["best_logprob"]), "mean_rank": _r(best.get("mean_rank"), 1),
            "n_instances_top2000": int(best.get("n_top") or 0),
            "gender_log_odds": _r(single[0]["gender_log_odds"]) if single else None,
            "trait_contrast": _r(c["trait_contrast"]) if c else None,
            "state_flag": bool(c["state_flag"]) if c else None,
            "physical_flag": bool(c["physical_flag"]) if c else None,
            "zipf": fi.zipf_min if fi else None, "freq_hard_reject": fi.hard_reject if fi else None,
            "freq_probe_band": fi.probe_band if fi else None,
            "wordnet": {"found": hint is not None, "n_adj_senses": hint.n_adj_senses if hint else 0,
                        "definition": hint.definition if hint else None, "pos": hint.pos if hint else None},
            "gloss_hint": gh,
            "stoplist_flags": [] if malformed else stoplist_flags(
                surface[:1].upper() + surface[1:] if lookups.is_proper(surface) else surface,
                hint.definition if hint else None),
            "union_rank": 0, "eligible": eligible, "ineligible_reason": reason,
            "corpus_stem_match": st in corpus if st else False, "queue_stem_match": st in queue if st else False,
            "token_class": (lookups.token_class(surface) if (lookups.token_class and not malformed) else None),
            "best_pass": key,
        })
    return union_rank(rows)


def union_rank(rows: Sequence[dict]) -> list[dict]:
    """Sort by best log-probability descending, ties by Zipf descending, then surface; number from 1."""
    out = sorted(rows, key=lambda r: (-float(r["best_logprob"]), -(r.get("zipf") or 0.0), r["surface"]))
    for i, r in enumerate(out, 1):
        r["union_rank"] = i
    return out


def row_text(r: Mapping) -> str:
    return json.dumps({k: r.get(k) for k in ROW_FIELDS}, ensure_ascii=False, separators=(",", ":"))


def table_text(rows: Sequence[Mapping]) -> str:
    return "".join(row_text(r) + "\n" for r in rows)


def write_table(rows: Sequence[Mapping], path: Path = MLM_TABLE_PATH) -> Optional[Path]:
    """Write the table; when the content changes the old file is first copied to ``<path>.bak.<UTC>``
    (snapshot before overwrite).  Returns the backup path, if any."""
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


def load_mlm_table(path: Path = MLM_TABLE_PATH) -> list[dict]:
    """The table (frozen interface): one dict per stem in union-rank order, schema version 1."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def table_counts(rows: Sequence[Mapping]) -> dict:
    from collections import Counter
    return {"n_union": len(rows), "n_eligible": sum(1 for r in rows if r.get("eligible")),
            "ineligible": dict(sorted(Counter(r.get("ineligible_reason") for r in rows
                                              if not r.get("eligible")).items())),
            "token_class": dict(sorted(Counter(str(r.get("token_class")) for r in rows).items())),
            "best_pass": dict(sorted(Counter(r.get("best_pass") for r in rows).items())),
            "with_gloss_hint": sum(1 for r in rows if r.get("gloss_hint")),
            "with_contrast": sum(1 for r in rows if r.get("trait_contrast") is not None),
            "stoplist_flagged": sum(1 for r in rows if r.get("stoplist_flags")),
            "corpus_stem_match": sum(1 for r in rows if r.get("corpus_stem_match")),
            "queue_stem_match": sum(1 for r in rows if r.get("queue_stem_match"))}

