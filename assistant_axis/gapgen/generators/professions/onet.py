"""O*NET 31.0 files and the job-title cut (coding plan 16, § 5b and § 7d "Levels and the cut").

* :func:`read_occupation_data`: ``occupation_data.csv`` (``O*NET-SOC Code``, ``Title``, ``Description``; 1,016 rows).
* :func:`read_job_titles`: ``job_titles.csv`` (the table formerly "Alternate Titles": lay titles by O*NET-SOC code).
  Its CSV header was not seen when this was written (the file is a fresh download, not on disk), so the reader
  accepts the old table's column names and the plausible new ones (:data:`JOB_TITLE_COLUMNS`) and says which it
  found; a file with none of them is refused.
* :func:`cut_job_titles` / :func:`lay_title_candidates`: the cut.  A job title is kept when, in order:
  it has no parentheses (``parentheses``); none of its words is an abbreviation (``abbreviation``: an all-capital
  acronym, a word with a full stop, digits, a slash, an ampersand or a comma, or one of :data:`ABBREVIATIONS`);
  it is one or two words after normalization (``words``: lower case, its last word made singular by
  :func:`singular`, a hyphenated word counting as one); its Zipf (wordfreq, the phrase scored as wordfreq scores
  it) is at least ``min_zipf`` (``zipf``); its stem is not a corpus role stem or a corpus role's ``renamed_from``
  (``corpus_role``); it is not its own occupation's title made singular (``occupation_title``: the broad group's
  call already covers that name); and it is the first of its stem across occupations (``duplicate``: the one under
  the occupation with the largest employment is kept when employment is known, else the first in the file, and
  the other codes are recorded).  The top ``n`` by Zipf (ties by label) go to the lay call, one call each under its
  occupation.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name


@dataclass(frozen=True)
class Occupation:
    code: str             # O*NET-SOC code, "29-1212.00"
    title: str
    description: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobTitle:
    code: str             # O*NET-SOC code of the occupation it is listed under
    title: str
    short_title: Optional[str] = None
    sources: Optional[str] = None


@dataclass
class TitleCandidate:
    """A job title that passed the cut: its label (lower case, singular), stem, Zipf, the occupation it is kept
    under and every other code it was listed under."""
    job_title: JobTitle
    label: str
    stem: str
    zipf: float
    singularized: bool = False
    also_under: list = field(default_factory=list)

    @property
    def code(self) -> str:
        return self.job_title.code

    def as_dict(self) -> dict:
        return {"code": self.code, "title": self.job_title.title, "label": self.label, "stem": self.stem,
                "zipf": round(self.zipf, 3), "singularized": self.singularized, "also_under": list(self.also_under),
                "short_title": self.job_title.short_title, "sources": self.job_title.sources}


OCCUPATION_COLUMNS = {"code": ("O*NET-SOC Code",), "title": ("Title",), "description": ("Description",)}
#: Accepted header names of ``job_titles.csv`` (the old "Alternate Titles" table's first; unverified for 31.0).
JOB_TITLE_COLUMNS = {"code": ("O*NET-SOC Code", "ONET-SOC Code", "Code"),
                     "title": ("Alternate Title", "Job Title", "Title", "Reported Job Title"),
                     "short_title": ("Short Title",),
                     "sources": ("Source(s)", "Sources", "Source")}


def _column(header: Sequence[str], names: Sequence[str]) -> Optional[str]:
    low = {h.strip().lower(): h for h in header}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        rows = list(r)
        return list(r.fieldnames or []), rows


def read_occupation_data(path: Path) -> list[Occupation]:
    """``occupation_data.csv`` in file order."""
    header, rows = _read_csv(Path(path))
    cols = {k: _column(header, v) for k, v in OCCUPATION_COLUMNS.items()}
    missing = [k for k, c in cols.items() if c is None]
    if missing:
        raise ValueError(f"{path}: no {missing} column in {header}")
    return [Occupation(code=r[cols["code"]].strip(), title=r[cols["title"]].strip(),
                       description=(r[cols["description"]] or "").strip()) for r in rows if r.get(cols["code"])]


def read_job_titles(path: Path) -> list[JobTitle]:
    """``job_titles.csv`` in file order (columns by :data:`JOB_TITLE_COLUMNS`)."""
    header, rows = _read_csv(Path(path))
    cols = {k: _column(header, v) for k, v in JOB_TITLE_COLUMNS.items()}
    if cols["code"] is None or cols["title"] is None:
        raise ValueError(f"{path}: no code or title column among {header} (accepted: {JOB_TITLE_COLUMNS})")
    out = []
    for r in rows:
        code, title = (r.get(cols["code"]) or "").strip(), (r.get(cols["title"]) or "").strip()
        if not code or not title:
            continue
        out.append(JobTitle(code=code, title=title,
                            short_title=((r.get(cols["short_title"]) or "").strip() or None) if cols["short_title"] else None,
                            sources=((r.get(cols["sources"]) or "").strip() or None) if cols["sources"] else None))
    return out


def job_title_columns(path: Path) -> dict:
    """Which header names :func:`read_job_titles` used (for the build record)."""
    header, _ = _read_csv(Path(path))
    return {k: _column(header, v) for k, v in JOB_TITLE_COLUMNS.items()}


# --------------------------------------------------------------------------- normalization

#: Shortened words seen in job-title lists that are not lay words (an all-capital acronym is caught by its case).
ABBREVIATIONS = frozenset({"asst", "mgr", "mgmt", "supv", "supvr", "sr", "jr", "dept", "assoc", "coord", "dir",
                           "spec", "maint", "svc", "svcs", "acct", "admin", "adm", "eng", "engr", "tchr", "instr",
                           "opr", "oper", "prog", "res", "rn", "lpn", "cna", "emt"})
_ACRONYM_RE = re.compile(r"^[A-Z]{2,}s?$")
_BAD_CHARS = re.compile(r"[.\d/&,;:+#@]")
#: Words ending in "s" that are singular (left alone by :func:`singular`).
SINGULAR_S = frozenset({"bus", "boss", "chorus", "status", "campus", "virus", "census", "chassis", "lens", "gas",
                        "atlas", "canvas", "alias", "series", "species", "news", "arms", "glass", "cross", "press"})


def is_abbreviation(word: str) -> bool:
    w = word.strip()
    if not w:
        return False
    if _ACRONYM_RE.match(w) or _BAD_CHARS.search(w):
        return True
    return w.lower().strip("'") in ABBREVIATIONS


def singular(word: str) -> str:
    """A conservative English singular of one lower-case word: -men -> -man, -ies -> -y, -sses/-shes/-ches/-xes/-zes
    -> drop -es, else a final -s dropped unless the word ends in -ss, -us or -is or is in :data:`SINGULAR_S`."""
    w = word
    if w in SINGULAR_S or len(w) <= 3:
        return w
    if w.endswith("men") and len(w) > 4:
        return w[:-3] + "man"
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    for suf in ("sses", "shes", "ches", "xes", "zes"):
        if w.endswith(suf):
            return w[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def lay_label(title: str) -> tuple[str, bool]:
    """``(label, singularized)``: the title lower-cased, spaces collapsed, its last word made singular."""
    words = " ".join(title.strip().lower().split()).split(" ")
    last = singular(words[-1])
    changed = last != words[-1]
    return " ".join(words[:-1] + [last]), changed


def title_stem(label: str) -> str:
    """The file-name form of a label (``normalize_to_file_name``), any character outside ``[a-z0-9_]`` made a
    separator."""
    s = re.sub(r"[^a-z0-9_]+", "_", normalize_to_file_name(label))
    return re.sub(r"_+", "_", s).strip("_")


def default_zipf() -> Callable[[str], float]:
    from wordfreq import zipf_frequency
    return lambda text: float(zipf_frequency(text, "en"))


# --------------------------------------------------------------------------- the cut

CUT_REASONS = ("parentheses", "abbreviation", "words", "zipf", "corpus_role", "occupation_title", "duplicate")


@dataclass
class CutReport:
    n_titles: int = 0
    dropped: Counter = field(default_factory=Counter)
    n_passed: int = 0
    n_kept: int = 0
    n: int = 0
    min_zipf: float = 0.0
    max_words: int = 2
    examples: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"n_titles": self.n_titles, "dropped": {k: self.dropped.get(k, 0) for k in CUT_REASONS},
                "n_passed": self.n_passed, "n_kept": self.n_kept, "n": self.n, "min_zipf": self.min_zipf,
                "max_words": self.max_words, "examples": {k: v[:5] for k, v in self.examples.items()}}


def cut_job_titles(titles: Iterable[JobTitle], *, zipf: Callable[[str], float], corpus_stems: Iterable[str],
                   occupations: Optional[Mapping[str, Occupation]] = None, employment: Optional[Mapping[str, float]] = None,
                   max_words: int = 2, min_zipf: float = 3.0, n: int = 300) -> tuple[list[TitleCandidate], CutReport]:
    """The cut of the module docstring.  ``occupations``: O*NET code -> occupation (for ``occupation_title``);
    ``employment``: O*NET code -> the employment its occupation is ranked by (for which duplicate is kept)."""
    rep = CutReport(min_zipf=min_zipf, max_words=max_words, n=n)
    corpus = set(corpus_stems)
    occ_labels = {c: lay_label(o.title)[0] for c, o in (occupations or {}).items()}
    by_stem: dict[str, TitleCandidate] = {}
    order: list[str] = []

    def drop(reason: str, title: str) -> None:
        rep.dropped[reason] += 1
        rep.examples.setdefault(reason, []).append(title)

    for jt in titles:
        rep.n_titles += 1
        t = jt.title.strip()
        if "(" in t or ")" in t:
            drop("parentheses", t)
            continue
        raw_words = t.split()
        if any(is_abbreviation(w) for w in raw_words):
            drop("abbreviation", t)
            continue
        label, changed = lay_label(t)
        if not label or len(label.split()) > max_words:
            drop("words", t)
            continue
        z = float(zipf(label))
        if z < min_zipf:
            drop("zipf", t)
            continue
        stem = title_stem(label)
        if not stem or stem in corpus:
            drop("corpus_role", t)
            continue
        if occ_labels.get(jt.code) == label:
            drop("occupation_title", t)
            continue
        cand = TitleCandidate(job_title=jt, label=label, stem=stem, zipf=z, singularized=changed)
        cur = by_stem.get(stem)
        if cur is None:
            by_stem[stem] = cand
            order.append(stem)
            continue
        drop("duplicate", t)
        emp = employment or {}
        if emp.get(jt.code, -1) > emp.get(cur.code, -1):
            cand.also_under = [cur.code] + [c for c in cur.also_under if c != jt.code]
            by_stem[stem] = cand
        elif jt.code != cur.code and jt.code not in cur.also_under:
            cur.also_under.append(jt.code)
    passed = [by_stem[s] for s in order]
    rep.n_passed = len(passed)
    kept = sorted(passed, key=lambda c: (-c.zipf, c.label))[:n]
    rep.n_kept = len(kept)
    return kept, rep


def lay_title_candidates(titles: Iterable[JobTitle], *, zipf: Callable[[str], float], corpus_stems: Iterable[str],
                         max_words: int = 2, min_zipf: float = 3.0, n: int = 300, **kw) -> list[TitleCandidate]:
    """The kept titles of :func:`cut_job_titles` (the plan's signature)."""
    return cut_job_titles(titles, zipf=zipf, corpus_stems=corpus_stems, max_words=max_words, min_zipf=min_zipf,
                          n=n, **kw)[0]


__all__ = ["Occupation", "JobTitle", "TitleCandidate", "OCCUPATION_COLUMNS", "JOB_TITLE_COLUMNS",
           "read_occupation_data", "read_job_titles", "job_title_columns", "ABBREVIATIONS", "SINGULAR_S",
           "is_abbreviation", "singular", "lay_label", "title_stem", "default_zipf", "CUT_REASONS", "CutReport",
           "cut_job_titles", "lay_title_candidates"]
