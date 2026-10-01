"""Contrast clauses in trait descriptions (M2, plan 15 step 5).

* ``parse_census`` reads the 2026-09-23 census
  (``reports/trait_gap_generation/contrast_clauses_census.md``): ten N
  (necessary for sense), 68 P (names the other pole) and 29 S (stylistic or
  scope) stems, from its ``**stem**`` bullets under the three headings.
* ``strip_contrast`` removes each contrast clause mechanically: the span from
  a marker ("rather than", "instead of", "but not", "without being") to the
  end of its clause.  The clause ends at sentence or clause punctuation
  (``. ; : ! ?``, a dash, a parenthesis), at a comma followed by a
  conjunction that opens a new clause (``, and`` ``, but`` ``, while``
  ``, which`` ``, so`` ``, then``), or at a comma followed by a gerund (a new
  parallel clause: "telling rather than asking, delivering the answer").  A
  comma just before the marker goes with the cut.  The heuristic misreads a
  gerund list governed by the marker ("rather than hedging, expressing
  uncertainty, or presenting ..."), which is what the hand overrides fix.
* An override (``contrast_cut_overrides.json``) wins: ``{"cuts": [exact
  substrings to remove]}``, ``{"stripped": "<whole text>"}`` or
  ``{"keep": true}`` (leave the text alone).
* ``build_cuts`` produces ``contrast_cuts.json``: the census's 107 with
  mechanical and final cuts, and the mechanical hits over the whole current
  corpus that the census did not classify (reported, not classified).
* ``minimal_pairs`` builds the "X rather than Y" / "Y rather than X" texts of
  criterion (f).
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

CLASSES = ("N", "P", "S")
MARKERS = ("rather than", "instead of", "but not", "without being")
MARKER_RE = re.compile(r"\b(rather than|instead of|but not|without being)\b", re.I)
_SECTION_RE = re.compile(r"^##\s+([NPS]):", re.M)
_BULLET_RE = re.compile(r"^- \*\*([a-z0-9_]+)\*\*:", re.M)
#: Where a clause ends: punctuation, a dash, a parenthesis, or a comma that opens a new clause.
_END_RE = re.compile(r"[.;:!?()]|\s[—–-]{1,2}\s|—|, (?=(?:and|but|while|which|so|then|yet|never|always)\b)"
                     r"|, (?=[a-z]+ing\b)")


def parse_census(path: Path) -> dict[str, str]:
    """``{stem: "N" | "P" | "S"}`` from the census markdown."""
    text = Path(path).read_text(encoding="utf-8")
    out: dict[str, str] = {}
    heads = list(_SECTION_RE.finditer(text))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        for m in _BULLET_RE.finditer(text, h.end(), end):
            out[m.group(1)] = h.group(1)
    return out


def has_marker(text: str) -> bool:
    return bool(MARKER_RE.search(text or ""))


def _tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r",([.;:!?])", r"\1", text)
    text = re.sub(r",,+", ",", text)
    return text.strip()


def mechanical_spans(text: str) -> list[str]:
    """The substrings the mechanical rule would cut, left to right."""
    spans = []
    pos = 0
    while True:
        m = MARKER_RE.search(text, pos)
        if not m:
            break
        start = m.start()
        pre = text[:start]
        if pre.endswith(", "):
            start -= 2
        elif pre.endswith(" "):
            start -= 1
        e = _END_RE.search(text, m.end())
        end = e.start() if e else len(text)
        spans.append(text[start:end])
        pos = end
    return spans


def strip_contrast(text: str, *, override: Optional[Mapping] = None) -> tuple[str, list[str]]:
    """``(text without its contrast clauses, the cut spans)``.  No marker and no
    override: the text comes back unchanged with ``[]``.  An override wins."""
    if override:
        if override.get("keep"):
            return text, []
        if "stripped" in override:
            return override["stripped"], list(override.get("cuts", []))
        cuts = list(override.get("cuts", []))
    else:
        cuts = mechanical_spans(text)
    out = text
    for c in cuts:
        if c not in out:
            raise ValueError(f"cut {c!r} not found in {text!r}")
        out = out.replace(c, "", 1)
    return (_tidy(out) if cuts else text), cuts


def load_cuts(path: Path) -> dict[str, dict]:
    """``{stem: {"stripped", "cuts", ...}}`` for every stem in a ``contrast_cuts.json``
    (census entries and new hits alike)."""
    d = json.loads(Path(path).read_text())
    d = d.get("result", d)
    out = {}
    for section in ("census_107", "new_hits"):
        for stem, row in (d.get(section) or {}).items():
            out[stem] = row
    return out


def build_cuts(corpus: Mapping[str, Mapping], census: Mapping[str, str],
               overrides: Optional[Mapping[str, Mapping]] = None, *,
               renames: Optional[Mapping[str, str]] = None) -> dict:
    """The ``contrast_cuts.json`` payload.  ``corpus`` is ``{stem: {"label",
    "description"}}``; ``census`` ``{stem: class}``; ``overrides`` the hand file
    (keyed by current stem); ``renames`` maps a census stem to the stem its file
    has now (``entity_id.resolve_renamed_stem``), and the class goes with it."""
    overrides = dict(overrides or {})
    renames = dict(renames or {})
    census_now = {}
    for old_stem, cls in census.items():
        census_now[renames.get(old_stem, old_stem)] = (cls, old_stem)
    census_rows, new_hits, missing, no_marker = {}, {}, [], []
    for stem, (cls, old_stem) in sorted(census_now.items()):
        c = corpus.get(stem)
        if c is None:
            missing.append(old_stem)
            continue
        desc = c["description"]
        mech_text, mech_cuts = strip_contrast(desc)
        ov = overrides.get(stem)
        text, cuts = strip_contrast(desc, override=ov) if ov else (mech_text, mech_cuts)
        if not mech_cuts and not ov:
            no_marker.append(stem)
        census_rows[stem] = {"class": cls, "census_stem": old_stem, "description": desc, "mechanical_cuts": mech_cuts,
                             "mechanical_stripped": mech_text, "cuts": cuts, "stripped": text,
                             "source": "override" if ov else "mechanical",
                             "note": (ov or {}).get("note")}
    for stem, c in sorted(corpus.items()):
        if stem in census_now or not has_marker(c["description"]):
            continue
        ov = overrides.get(stem)
        text, cuts = strip_contrast(c["description"], override=ov)
        new_hits[stem] = {"class": None, "description": c["description"], "cuts": cuts, "stripped": text,
                          "source": "override" if ov else "mechanical", "note": (ov or {}).get("note")}
    return {"census_107": census_rows, "new_hits": new_hits, "census_stems_missing_from_corpus": missing,
            "census_stems_without_marker_now": no_marker,
            "renamed": {o: n for o, n in sorted(renames.items()) if o != n and o in census},
            "counts": {"census": len(census), "census_in_corpus": len(census_rows), "new_hits": len(new_hits),
                       "by_class": {k: sum(1 for r in census_rows.values() if r["class"] == k) for k in CLASSES},
                       "overrides": sum(1 for r in census_rows.values() if r["source"] == "override")}}


def minimal_pairs(pairs: Sequence[tuple[str, str]], labels: Mapping[str, str], *, n: int = 40,
                  seed: int = 0) -> list[dict]:
    """Criterion (f): for up to ``n`` pole pairs (sampled with ``seed``), the
    texts "This means being X rather than Y." and its reversal, plus each
    pole's bare "This means being X." form."""
    pool = sorted({tuple(sorted(p)) for p in pairs if p[0] in labels and p[1] in labels})
    rng = random.Random(seed)
    chosen = sorted(rng.sample(pool, min(n, len(pool))))
    out = []
    for x, y in chosen:
        lx, ly = labels[x], labels[y]
        out.append({"x": x, "y": y, "xy": f"This means being {lx} rather than {ly}.",
                    "yx": f"This means being {ly} rather than {lx}.",
                    "x_only": f"This means being {lx}.", "y_only": f"This means being {ly}."})
    return out


OVERRIDES_NAME = "contrast_cut_overrides.json"
CUTS_NAME = "contrast_cuts.json"


def load_corpus_texts(data_dir: Path) -> dict[str, dict]:
    """``{stem: {"label": positive_label, "description"}}`` for every trait file."""
    out = {}
    for f in sorted((Path(data_dir) / "traits" / "instructions").glob("*.json")):
        d = json.loads(f.read_text())
        out[f.stem] = {"label": d.get("positive_label") or f.stem.replace("_", " "),
                       "description": d.get("description") or ""}
    return out


def build_default(repo_root: Path, *, out_dir: Optional[Path] = None, write: bool = True) -> dict:
    """Build ``contrast_cuts.json`` from the corpus, the census and the hand
    overrides in ``contrast_cut_overrides.json`` (both beside it)."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.entity_id import resolve_renamed_stem
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input, current_files_input
    repo_root = Path(repo_root)
    out_dir = Path(out_dir or repo_root / "data" / "candidates" / "calibration")
    data_dir = repo_root / "data"
    census_path = repo_root / "reports" / "trait_gap_generation" / "contrast_clauses_census.md"
    census = parse_census(census_path)
    ov_path = out_dir / OVERRIDES_NAME
    overrides = {k: v for k, v in (json.loads(ov_path.read_text()) if ov_path.exists() else {}).items()
                 if not k.startswith("_")}
    renames = {s: resolve_renamed_stem(s, "traits", data_dir=data_dir) for s in census}
    payload = build_cuts(load_corpus_texts(data_dir), census, overrides, renames=renames)
    if write:
        inputs = [current_files_input(dep_key="trait_files",
                                      paths=sorted((data_dir / "traits" / "instructions").glob("*.json"))),
                  current_file_input(dep_key="census", path=census_path)]
        if ov_path.exists():
            inputs.append(current_file_input(dep_key="overrides", path=ov_path))
        env = json_metadata(payload, inputs=inputs, title="contrast-clause cuts (M2 ablation)")
        out_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / CUTS_NAME)
    return payload
