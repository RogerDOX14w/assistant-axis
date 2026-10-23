"""What generator B downloads, with sizes, licences and attribution, and the ``fetch`` that records it (coding plan
16, § 5b and § 7d; the base-model generator's ``sources.py`` / ``download.py`` pattern).

**Sources** (:data:`SOURCES`; licence findings of 2026-10-21 in the plan's § 7d):

* ``onet_occupations``: O*NET 31.0 ``occupation_data.csv`` (1,016 occupations with descriptions), **already on
  disk** (``base_model_generator.py fetch``, 2026-10-10; its manifest row is ``onet``), CC BY 4.0;
* ``onet_job_titles``: O*NET 31.0 ``job_titles.csv`` (the table formerly "Alternate Titles": lay titles by
  O*NET-SOC code), 4,504,432 bytes (HEAD, 2026-10-21), CC BY 4.0, the same attribution;
* ``bls_oews_national``: BLS OEWS May 2025 national estimates (an xlsx in a zip; OCC_CODE, OCC_TITLE, O_GROUP,
  TOT_EMP at the major, minor, broad and detailed tiers), public domain (BLS asks to be cited); bls.gov answers
  automated requests with 403, so a refused fetch says to **download it by hand** and ``fetch --hand`` records the
  file placed there (``"downloaded_by": "hand"``);
* ``bls_soc_structure``: BLS SOC 2018 structure (optional: OEWS carries the broad titles);
* ``esco_occupations``: ESCO occupations (English labels, alternative labels, descriptions, ISCO group code) by the
  ESCO API (no e-mail address), **wave 2 only**, behind ``--only esco_occupations`` / ``--source esco``
  (Decisions for Roger 1, decided 2026-10-22: CC BY 4.0 by the Commission's reuse policy; ISCO-08 out, and ESCO's
  ISCO-groups file not used).  :func:`fetch_esco_occupations` was written without the API documentation at hand
  (no network while building): the endpoint, its parameters and the response fields it reads are assumptions,
  tested only on a fake (:data:`ESCO_UNVERIFIED`).

**Fetch** (:func:`fetch`): refused without ``approved_by`` (Roger's go, recorded in every manifest row; nothing over
2 GB, so no delete-when-done note).  For each source: the published size (``HEAD``) is printed first; the licence
page is read (an HTTP error page does not count) and must name the licence (recorded, not fatal); the file
is written to ``<dest>.part`` and renamed (every file here is a few MB at most);
a row like the O*NET one on disk (``data/external/onet/DOWNLOAD_MANIFEST.json``) is merged into the
``DOWNLOAD_MANIFEST.json`` beside it, and its licence block appended to ``LICENSE.txt`` there.  The HTTP layer is
injected (:class:`Http`), so the tests use a fake and nothing here touches the network on import.

**Attribution** (:data:`ATTRIBUTION`, :func:`attribution_markdown`): one paragraph per source, the O*NET paragraph
verbatim from the base-model generator's source (its ``ONET_NOTE`` said when the attribution would become
load-bearing: this generator puts O*NET titles into candidates, the registry and readouts by design, so it is
load-bearing from the first candidate).  Written to ``ATTRIBUTION.md`` in every run directory and into ``run.json``.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Protocol, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.generators.base_model.sources import ONET_NOTE
from assistant_axis.gapgen.generators.base_model.sources import SOURCES as _BM_SOURCES
from assistant_axis.gapgen.generators.base_model.sources import Source as _BaseSource
from assistant_axis.gapgen.paths import DATA_EXTERNAL, REPO_ROOT
from assistant_axis.gapgen.registry import utc_now

from . import DOWNLOAD_MANIFEST_NAME

TOOL = "professions_generator.py fetch"
USER_AGENT = "assistant-axis professions generator (research; contact via the repository owner)"
APPROVAL_REQUIRED = ("refused: downloads need Roger's approval recorded with --approved-by '<Roger, date>' "
                     "(coding_plan_16_role_generators.md section 7d: each download a fresh ask)")
#: HTTP statuses that mean "this server will not serve an automated client": download by hand.
HAND_STATUSES = (401, 403, 429)

#: The O*NET paragraph, verbatim from the base-model generator's source (test 11 checks ``ATTRIBUTION.md`` holds it).
ONET_ATTRIBUTION = _BM_SOURCES["onet"].attribution
#: Why the O*NET attribution is load-bearing here (the base-model generator's :data:`ONET_NOTE` said when it would be).
PROFESSIONS_ONET_NOTE = (
    "LOAD-BEARING from the first candidate: this generator puts O*NET occupation titles, job titles and lay roles "
    "derived from them into candidates.jsonl, the registry, seed-queue entries and readouts by design, so the "
    "attribution travels with every run (ATTRIBUTION.md, run.json, each promoted entry's source).  The base-model "
    "generator's note said when this would happen: " + ONET_NOTE)
#: CC BY 4.0 asks that changes be indicated; O*NET's licence page asks for a statement that USDOL/ETA has not
#: approved the modifications (wording from memory of the page, not re-read: no network while building).
ONET_CHANGES = ("Changes: the lay role names and one-sentence descriptions in this run were derived from O*NET "
                "occupation titles, descriptions and job titles by a language model (Claude Haiku 5.5), and the "
                "occupations were grouped by their 2018 SOC broad codes.  USDOL/ETA has not approved, endorsed, or "
                "tested these modifications.")


@dataclass(frozen=True)
class Source(_BaseSource):
    """The base-model generator's :class:`~assistant_axis.gapgen.generators.base_model.sources.Source` with what
    this generator's downloads add: the manifest row's key (``manifest_key``, default ``key``), how it is fetched
    (``via``: ``https`` or ``esco_api``), whether it is optional, its wave, and whether it is on disk already."""
    manifest_key: Optional[str] = None
    via: str = "https"
    optional: bool = False
    wave: int = 1
    on_disk: bool = False

    @property
    def row_key(self) -> str:
        return self.manifest_key or self.key


ESCO_API = "https://ec.europa.eu/esco/api"

SOURCES: dict[str, Source] = {s.key: s for s in (
    Source(
        key="onet_occupations", dest="onet/occupation_data.csv", size_bytes=268_030,
        licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/",
        citation="O*NET 31.0 Database, U.S. Department of Labor, Employment and Training Administration",
        attribution=ONET_ATTRIBUTION,
        url="https://www.onetcenter.org/dl_files/database/db_31_0_csv/occupation_data.csv", version="31.0",
        note=PROFESSIONS_ONET_NOTE, manifest_key="onet", on_disk=True),
    Source(
        key="onet_job_titles", dest="onet/job_titles.csv", size_bytes=4_504_432,
        licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/",
        citation="O*NET 31.0 Database (Job Titles), U.S. Department of Labor, Employment and Training Administration",
        attribution=ONET_ATTRIBUTION,
        url="https://www.onetcenter.org/dl_files/database/db_31_0_csv/job_titles.csv", version="31.0",
        note="the table formerly 'Alternate Titles': lay titles by O*NET-SOC code; 4,504,432 bytes by HEAD on "
             "2026-10-21.  " + PROFESSIONS_ONET_NOTE),
    Source(
        key="bls_oews_national", dest="bls/oesm25nat.zip", size_bytes=0,
        licence="public domain", licence_url="https://www.bls.gov/bls/linksite.htm",
        citation=("U.S. Bureau of Labor Statistics, Occupational Employment and Wage Statistics (OEWS), May 2025 "
                  "national occupational employment and wage estimates"),
        attribution=("Employment figures: U.S. Bureau of Labor Statistics, Occupational Employment and Wage "
                     "Statistics (OEWS), May 2025 national estimates, https://www.bls.gov/oes/ (public domain; "
                     "cited as BLS asks)."),
        url="https://www.bls.gov/oes/special-requests/oesm25nat.zip", version="May 2025",
        note=("an xlsx in a zip; columns OCC_CODE, OCC_TITLE, O_GROUP, TOT_EMP at the major, minor, broad and "
              "detailed tiers, so it also supplies the broad titles.  bls.gov answers automated requests with 403: "
              "a refused fetch is downloaded by hand and recorded with fetch --hand")),
    Source(
        key="bls_soc_structure", dest="bls/soc_structure_2018.xlsx", size_bytes=0,
        licence="public domain", licence_url="https://www.bls.gov/bls/linksite.htm",
        citation="U.S. Bureau of Labor Statistics, 2018 Standard Occupational Classification (SOC) structure",
        attribution=("Occupation groups: the 2018 Standard Occupational Classification (SOC), U.S. Bureau of Labor "
                     "Statistics, https://www.bls.gov/soc/ (public domain)."),
        url="https://www.bls.gov/soc/2018/soc_structure_2018.xlsx", version="2018",
        note="optional: OEWS carries the broad titles", optional=True),
    Source(
        key="esco_occupations", dest="esco/occupations_en.jsonl", size_bytes=0,
        licence="CC BY 4.0 (Commission reuse policy; see plan)",
        licence_url="https://commission.europa.eu/legal-notice_en",
        citation="ESCO (European Skills, Competences, Qualifications and Occupations), European Commission",
        attribution=("This run uses the ESCO classification of the European Commission (https://esco.ec.europa.eu), "
                     "(c) European Union, reused under CC BY 4.0 under the Commission's reuse policy (Decision "
                     "2011/833/EU).  Changes: occupations grouped by their ISCO code and given lay names and "
                     "one-sentence descriptions by a language model."),
        url=ESCO_API, version=None,
        note=("wave 2 only (Decisions for Roger 1, 2026-10-22): fetched by the ESCO API, so no e-mail address is "
              "given; English labels, alternative labels, descriptions and the ISCO group code of each occupation, "
              "one JSON line each.  ISCO-08 and ESCO's ISCO-groups file are not used"),
        via="esco_api", optional=True, wave=2),
)}

#: Fetched by ``fetch`` with no ``--only``: wave 1's two new downloads (the occupations are on disk).
DEFAULT_FETCH: tuple[str, ...] = ("onet_job_titles", "bls_oews_national")
#: ``--source esco`` adds these.
ESCO_KEYS: tuple[str, ...] = ("esco_occupations",)

#: The licence pages read at fetch time: ``(url, needles)``; the page must name one of the needles.
LICENCE_CHECK: dict[str, tuple[str, tuple[str, ...]]] = {
    "onet_occupations": ("https://www.onetcenter.org/license_db.html", ("CC BY 4.0",)),
    "onet_job_titles": ("https://www.onetcenter.org/license_db.html", ("CC BY 4.0",)),
    "bls_oews_national": ("https://www.bls.gov/bls/linksite.htm", ("public domain",)),
    "bls_soc_structure": ("https://www.bls.gov/bls/linksite.htm", ("public domain",)),
    "esco_occupations": ("https://esco.ec.europa.eu/en/copyright-notice-esco-skills-competences",
                         ("CC BY 4.0", "Attribution 4.0")),
}

#: Considered and not fetched, on purpose (coding plan 16, § 2 and § 7d).
SKIPPED: dict[str, str] = {
    "ISCO-08": "no licence statement found for the files (the ILO's CC BY 4.0 covers data from 3 May 2023 on); "
               "out until one is found (Decisions for Roger 1)",
    "ESCO ISCO-groups file": "not used (Decisions for Roger 1): only ESCO's occupations",
    "DOT 1991": "archaic and oddly specific is the opposite of well known (idea plan section 6)",
    "HISCO": "licence not checked; D's Roget pass covers historical trades",
}

#: One paragraph per source, keyed by source key (``onet`` for both O*NET files, written once).
ATTRIBUTION: dict[str, str] = {
    "onet_occupations": ONET_ATTRIBUTION,
    "onet_job_titles": ONET_ATTRIBUTION,
    "bls_oews_national": SOURCES["bls_oews_national"].attribution,
    "bls_soc_structure": SOURCES["bls_soc_structure"].attribution,
    "esco_occupations": SOURCES["esco_occupations"].attribution,
}


def page_text(http: "Http", url: str) -> str:
    """The body of ``url``; an HTTP error status raises (an error page that happens to name a licence is not the
    licence page)."""
    r = http.get(url)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status}")
    return r.text()


def licence_check(key: str, *, text_fn: Optional[Callable[[str], str]] = None) -> bool:
    """True when the licence page of ``key`` names its licence (:data:`LICENCE_CHECK`); False when it does not or
    cannot be read.  ``text_fn(url) -> str`` reads the page (default a real GET: network)."""
    ok, _ = _licence(key, text_fn or (lambda u: page_text(UrllibHttp(), u)))
    return ok


def _licence(key: str, text_fn: Callable[[str], str]) -> tuple[bool, str]:
    url, needles = LICENCE_CHECK[key]
    try:
        text = text_fn(url).lower()
    except Exception as exc:  # noqa: BLE001 - recorded, not fatal
        return False, f"{url} could not be read ({type(exc).__name__})"
    return any(n.lower() in text for n in needles), url


# --------------------------------------------------------------------------- attribution

def attribution_keys(keys: Iterable[str]) -> list[str]:
    """``keys`` in :data:`SOURCES` order, unknown ones dropped."""
    want = set(keys)
    return [k for k in SOURCES if k in want]


def attribution_markdown(keys: Iterable[str], *, run_label: Optional[str] = None) -> str:
    """``ATTRIBUTION.md``: one paragraph per source used (the O*NET paragraph verbatim, once), the O*NET changes
    statement when an O*NET file is used, and each source's URL and licence."""
    ks = attribution_keys(keys)
    lines = ["# Attribution", ""]
    if run_label:
        lines += [f"Sources of {run_label}, generator B (lists of professions; coding plan 16, section 7d).", ""]
    seen: set[str] = set()
    for k in ks:
        para = ATTRIBUTION[k]
        if para in seen:
            continue
        seen.add(para)
        lines += [para, ""]
        if para == ONET_ATTRIBUTION:
            lines += [ONET_CHANGES, ""]
    lines += ["| source | file | licence | licence page |", "|---|---|---|---|"]
    for k in ks:
        s = SOURCES[k]
        lines.append(f"| {k} | {s.url} | {s.licence} | {s.licence_url} |")
    return "\n".join(lines) + "\n"


def write_attribution(run_dir: Path, keys: Iterable[str], *, run_label: Optional[str] = None) -> Path:
    p = Path(run_dir) / "ATTRIBUTION.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(attribution_markdown(keys, run_label=run_label), p)
    return p


def attribution_record(keys: Iterable[str]) -> dict:
    """What ``run.json`` carries: ``{key: paragraph}`` and the changes statement."""
    ks = attribution_keys(keys)
    out = {k: ATTRIBUTION[k] for k in ks}
    if any(ATTRIBUTION[k] == ONET_ATTRIBUTION for k in ks):
        out["onet_changes"] = ONET_CHANGES
    return out


# --------------------------------------------------------------------------- the HTTP layer (injected)

@dataclass
class HttpResponse:
    status: int
    body: bytes = b""
    headers: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class Http(Protocol):
    """What :func:`fetch` needs: ``get`` and ``head`` returning an :class:`HttpResponse` (an HTTP error status is a
    response, never an exception; a network failure raises)."""

    def get(self, url: str) -> HttpResponse: ...

    def head(self, url: str) -> HttpResponse: ...


class UrllibHttp:
    """The real HTTP layer (:mod:`urllib`), with ``user_agent`` on every request and a few retries of a dropped
    connection."""

    def __init__(self, user_agent: str = USER_AGENT, *, timeout: float = 120.0, attempts: int = 4):
        self.user_agent = user_agent
        self.timeout = timeout
        self.attempts = attempts

    def _do(self, url: str, method: str) -> HttpResponse:  # pragma: no cover - network
        last: Optional[Exception] = None
        for i in range(self.attempts):
            req = urllib.request.Request(url, method=method, headers={"User-Agent": self.user_agent})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed https URLs
                    body = resp.read() if method != "HEAD" else b""
                    return HttpResponse(resp.status, body, dict(resp.headers.items()))
            except urllib.error.HTTPError as exc:
                return HttpResponse(exc.code, exc.read() if method != "HEAD" else b"", dict(exc.headers.items()))
            except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
                last = exc
                time.sleep(2.0 * (i + 1))
        raise RuntimeError(f"{method} {url} failed after {self.attempts} attempts: {last!r}")

    def get(self, url: str) -> HttpResponse:  # pragma: no cover - network
        return self._do(url, "GET")

    def head(self, url: str) -> HttpResponse:  # pragma: no cover - network
        return self._do(url, "HEAD")


# --------------------------------------------------------------------------- manifests

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    for p, root in ((Path(path), REPO_ROOT), (Path(path).resolve(), REPO_ROOT.resolve())):
        try:
            return str(p.relative_to(root))
        except ValueError:
            continue
    return str(path)


def load_manifest(path: Path) -> list[dict]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def merge_manifest(entries: Iterable[dict], path: Path) -> Path:
    """Replace a row of the same ``key`` in place, append a new one (the rows already there keep their order)."""
    cur = load_manifest(path)
    idx = {e.get("key"): i for i, e in enumerate(cur)}
    for e in entries:
        if e["key"] in idx:
            cur[idx[e["key"]]] = e
        else:
            idx[e["key"]] = len(cur)
            cur.append(e)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", path)
    return Path(path)


def manifest_row(s: Source, external_dir: Path = DATA_EXTERNAL) -> Optional[dict]:
    """The recorded manifest row of ``s`` (``None`` when it was never fetched)."""
    p = Path(external_dir) / Path(s.dest).parent / DOWNLOAD_MANIFEST_NAME
    return next((e for e in load_manifest(p) if e.get("key") == s.row_key), None)


def _licence_file(directory: Path, s: Source, *, now: str, verified: bool, by: str) -> Path:
    """Append the source's licence block to ``LICENSE.txt`` in ``directory`` unless the file already names its URL
    (the O*NET directory's file, written by the base-model generator, is extended, not replaced)."""
    path = Path(directory) / "LICENSE.txt"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if s.url and f"Source: {s.url}" in old:
        return path
    block = [f"Licence: {s.licence} ({s.licence_url})", f"Attribution: {s.attribution}", f"Citation: {s.citation}",
             f"Source: {s.url}",
             f"Downloaded unmodified on {now[:10]} ({by}) by {TOOL}; licence {'confirmed' if verified else 'NOT confirmed'} "
             f"on {LICENCE_CHECK[s.key][0]}."]
    if s.note:
        block.append(f"Note: {s.note}")
    text = (old.rstrip("\n") + "\n\n" if old.strip() else "") + "\n".join(block) + "\n"
    atomic_write_text(text, path)
    return path


# --------------------------------------------------------------------------- ESCO by its API (wave 2)

#: What :func:`fetch_esco_occupations` assumes about the ESCO API and could not check (no network while building).
ESCO_UNVERIFIED: tuple[str, ...] = (
    "the endpoint GET <api>/search with type=occupation, language=en, full=true, limit and offset (and an empty "
    "text=): whether text may be empty, and whether full=true returns the full occupation in each result",
    "the page shape: total, _embedded.results, _links.next.href",
    "the occupation fields: uri, preferredLabel.en (or title), alternativeLabel.en (a list), description.en.literal, "
    "code (an ESCO code such as 2221.1 whose part before the dot is the ISCO unit group), "
    "_links.broaderIscoGroup[].code / .title",
    "the per-occupation fallback GET <api>/resource/occupation?uri=...&language=en when a result lacks labels",
    "rate limits and the page size the service accepts (100 here)",
)


def _lang(value, language: str):
    """``value`` in ``language`` from an ESCO multilingual field (a dict by language, or the value itself)."""
    if isinstance(value, Mapping):
        return value.get(language)
    return value


def esco_row(res: Mapping, *, language: str = "en") -> dict:
    """One JSONL row from one ESCO occupation resource (the field names of :data:`ESCO_UNVERIFIED`)."""
    pref = _lang(res.get("preferredLabel"), language) or res.get("title")
    alts = _lang(res.get("alternativeLabel"), language) or []
    if isinstance(alts, str):
        alts = [alts]
    desc = _lang(res.get("description"), language)
    if isinstance(desc, Mapping):
        desc = desc.get("literal")
    code = res.get("code")
    links = res.get("_links") or {}
    groups = links.get("broaderIscoGroup") or []
    if isinstance(groups, Mapping):
        groups = [groups]
    g0 = groups[0] if groups else {}
    isco = g0.get("code") or (str(code).split(".")[0] if code else None)
    return {"uri": res.get("uri"), "code": code, "isco_group": isco, "isco_group_title": g0.get("title"),
            "preferred_label": pref, "alt_labels": [a for a in alts if isinstance(a, str)],
            "description": desc if isinstance(desc, str) else None}


def _has_details(res: Mapping) -> bool:
    return "alternativeLabel" in res or "description" in res


def fetch_esco_occupations(http: Http, dest: Path, *, api: str = ESCO_API, language: str = "en",
                           page_size: int = 100, max_pages: Optional[int] = None, selected_version: Optional[str] = None,
                           echo=print) -> dict:
    """Page the ESCO search API for every occupation and write one JSON line per occupation to ``dest`` (through
    ``<dest>.part``).  Returns ``{"n_rows", "n_pages", "n_detail_fetches", "total"}``.  A page that is not 200
    raises; a result without labels or description is fetched whole from the resource endpoint."""
    params = {"type": "occupation", "language": language, "full": "true", "limit": str(page_size), "text": ""}
    if selected_version:
        params["selectedVersion"] = selected_version
    url: Optional[str] = f"{api}/search?{urllib.parse.urlencode(params)}&offset=0"
    rows: list[dict] = []
    seen: set = set()
    n_pages = n_detail = 0
    total = None
    offset = 0
    while url:
        resp = http.get(url)
        if not resp.ok:
            raise RuntimeError(f"ESCO API {url}: HTTP {resp.status}")
        page = resp.json()
        n_pages += 1
        total = page.get("total", total)
        results = ((page.get("_embedded") or {}).get("results")) or []
        for res in results:
            if not _has_details(res) and res.get("uri"):
                q = urllib.parse.urlencode({"uri": res["uri"], "language": language})
                r2 = http.get(f"{api}/resource/occupation?{q}")
                n_detail += 1
                if r2.ok:
                    res = {**res, **r2.json()}
            row = esco_row(res, language=language)
            if row["uri"] in seen:
                continue
            seen.add(row["uri"])
            rows.append(row)
        if not results or (max_pages is not None and n_pages >= max_pages):
            break
        nxt = (((page.get("_links") or {}).get("next")) or {}).get("href")
        offset += len(results)
        if nxt:
            url = nxt
        elif total is not None and offset < int(total):
            url = f"{api}/search?{urllib.parse.urlencode(params)}&offset={offset}"
        else:
            url = None
    if rows:
        # the API's shape is taken from its documentation (ESCO_UNVERIFIED): show one parsed row before writing
        echo(f"esco_occupations: first row parsed: {json.dumps(rows[0], ensure_ascii=False)[:600]}")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    part.replace(dest)
    echo(f"esco_occupations: {len(rows)} occupations in {n_pages} pages ({n_detail} fetched whole) -> {_rel(dest)}")
    return {"n_rows": len(rows), "n_pages": n_pages, "n_detail_fetches": n_detail, "total": total}


# --------------------------------------------------------------------------- fetch

class NotApproved(SystemExit):
    def __init__(self):
        super().__init__(2)
        self.msg = APPROVAL_REQUIRED

    def __str__(self) -> str:
        return self.msg


@dataclass
class FetchResult:
    entries: list[dict] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    #: ``{"key", "url", "dest", "status"}`` of each source the server refused: download it by hand
    hand: list[dict] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)
    dry_run_lines: list[str] = field(default_factory=list)
    #: files of an ESCO smoke run (``esco_max_pages``): a sample, not the source, so no manifest row
    samples: list[Path] = field(default_factory=list)


def hand_message(s: Source, dest: Path, status: int) -> str:
    return (f"{s.key}: the server answered {status}: download by hand.  Open {s.url} in a browser, save the file as "
            f"{_rel(dest)}, then record it with `uv run python data_analysis/gap_generation/professions_generator.py "
            f"fetch --only {s.key} --hand --approved-by '<Roger, date>'`")


def _entry(s: Source, dest: Path, *, approved_by: str, now: str, lic_ok: bool, lic_src: str,
           size_published: Optional[int], by: str, git_sha: Optional[str], extra: Optional[dict] = None) -> dict:
    sha = sha256_file(dest)
    e = {"key": s.row_key, "file": _rel(dest), "url": s.url, "repo_id": None, "revision": None,
         "size_bytes": dest.stat().st_size, "size_bytes_published": size_published, "sha256": sha,
         "sha256_published": None, "checksum_verified": False, "licence": s.licence, "licence_url": s.licence_url,
         "licence_verified": lic_ok, "licence_checked_on": lic_src, "attribution": s.attribution,
         "citation": s.citation, "version": s.version, "note": s.note, "approved_by": approved_by,
         "downloaded_at": now, "tool": TOOL, "git_sha": git_sha, "downloaded_by": by}
    if extra:
        e.update(extra)
    return e


def esco_sample_path(dest: Path) -> Path:
    """Where an ESCO smoke run (``esco_max_pages``) writes: beside the source's file, never over it."""
    dest = Path(dest)
    return dest.with_name(dest.stem + ".sample" + dest.suffix)


def fetch_source(s: Source, *, dest_root: Path, approved_by: str, http: Http, hand: bool = False,
                 force: bool = False, now: Optional[str] = None, git_sha: Optional[str] = None,
                 esco_max_pages: Optional[int] = None, echo=print) -> tuple[Optional[dict], str]:
    """Fetch one source.  Returns ``(manifest row or None, outcome)``, outcome one of ``fetched``, ``present``,
    ``hand`` (recorded as downloaded by hand), ``refused`` (the server refused: download by hand; no row), or
    ``sample`` (ESCO with ``esco_max_pages``: the first pages to :func:`esco_sample_path`, a check of the API's shape
    before the full run; no row)."""
    now = now or utc_now()
    dest = Path(dest_root) / s.dest
    prev = manifest_row(s, dest_root) or {}
    if s.on_disk and prev and dest.exists() and not (force or hand):
        echo(f"{s.key}: on disk ({_rel(dest)}, recorded by {prev.get('tool')} on {str(prev.get('downloaded_at'))[:10]}); "
             f"not fetched again")
        return prev, "present"              # the row already recorded stays as it is
    lic_ok, lic_src = _licence(s.key, lambda u: page_text(http, u))
    echo(f"{s.key}: licence {s.licence} {'confirmed on' if lic_ok else '*** NOT CONFIRMED *** on'} {lic_src}")
    if hand:
        if not dest.exists():
            raise FileNotFoundError(f"{s.key}: --hand records a file downloaded by hand, but {_rel(dest)} is not there")
        echo(f"{s.key}: recording {_rel(dest)} as downloaded by hand")
        e = _entry(s, dest, approved_by=approved_by, now=now, lic_ok=lic_ok, lic_src=lic_src, size_published=None,
                   by="hand", git_sha=git_sha)
        return _record(s, dest, e, now=now, lic_ok=lic_ok), "hand"
    if s.via == "esco_api" and esco_max_pages is not None:
        sample = esco_sample_path(dest)
        info = fetch_esco_occupations(http, sample, api=s.url or ESCO_API, max_pages=int(esco_max_pages), echo=echo)
        echo(f"{s.key}: smoke run, {info['n_pages']} page(s), {info['n_rows']} rows of the API's {info['total']} -> "
             f"{_rel(sample)} (a sample: not recorded in the manifest; the full fetch is a run without "
             f"--esco-max-pages)")
        return None, "sample"
    if s.via == "esco_api":
        if dest.exists() and not force:
            echo(f"{s.key}: already present ({_rel(dest)}); not fetched again (--force to refetch)")
            outcome = "present"
            extra = {k: prev.get(k) for k in ("n_rows", "api") if k in prev}
        else:
            info = fetch_esco_occupations(http, dest, api=s.url or ESCO_API, echo=echo)
            outcome = "fetched"
            extra = {"n_rows": info["n_rows"], "api": s.url, "api_total": info["total"],
                     "unverified": list(ESCO_UNVERIFIED)}
        e = _entry(s, dest, approved_by=approved_by, now=now, lic_ok=lic_ok, lic_src=lic_src, size_published=None,
                   by="esco_api", git_sha=git_sha, extra=extra)
        return _record(s, dest, e, now=now, lic_ok=lic_ok), outcome
    if dest.exists() and not force:
        echo(f"{s.key}: already present ({_rel(dest)}); not fetched again (--force to refetch)")
        e = _entry(s, dest, approved_by=prev.get("approved_by") or approved_by, now=prev.get("downloaded_at") or now,
                   lic_ok=lic_ok, lic_src=lic_src, size_published=prev.get("size_bytes_published"),
                   by=prev.get("downloaded_by") or "fetch", git_sha=prev.get("git_sha") or git_sha)
        return _record(s, dest, e, now=now, lic_ok=lic_ok), "present"
    h = http.head(str(s.url))
    if h.status in HAND_STATUSES:
        echo(hand_message(s, dest, h.status))
        return None, "refused"
    n = (h.headers or {}).get("Content-Length") or (h.headers or {}).get("content-length")
    size = int(n) if n else None
    echo(f"{s.key}: {s.url}  ->  {_rel(dest)}  " + (f"({size:,} bytes, {size / 1e6:.1f} MB, published)" if size
                                                    else "(size not published)"))
    resp = http.get(str(s.url))
    if resp.status in HAND_STATUSES:
        echo(hand_message(s, dest, resp.status))
        return None, "refused"
    if not resp.ok:
        raise RuntimeError(f"{s.key}: GET {s.url} answered {resp.status}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(resp.body)
    part.replace(dest)
    e = _entry(s, dest, approved_by=approved_by, now=now, lic_ok=lic_ok, lic_src=lic_src, size_published=size,
               by="fetch", git_sha=git_sha)
    if size is not None and e["size_bytes"] != size:
        echo(f"{s.key}: *** size {e['size_bytes']:,} differs from the published {size:,} ***")
    return _record(s, dest, e, now=now, lic_ok=lic_ok), "fetched"


def _record(s: Source, dest: Path, e: dict, *, now: str, lic_ok: bool) -> dict:
    _licence_file(dest.parent, s, now=now, verified=lic_ok, by=e.get("downloaded_by") or "fetch")
    merge_manifest([e], dest.parent / DOWNLOAD_MANIFEST_NAME)
    return e


def fetch(keys: Optional[Sequence[str]] = None, *, dest_root: Path = DATA_EXTERNAL, approved_by: Optional[str],
          user_agent: str = USER_AGENT, http: Optional[Http] = None, hand: bool = False, force: bool = False,
          dry_run: bool = False, sources: Optional[Mapping[str, Source]] = None, git_sha: Optional[str] = None,
          esco_max_pages: Optional[int] = None, echo=print) -> FetchResult:
    """Fetch ``keys`` (default :data:`DEFAULT_FETCH`).  Refused without ``approved_by`` unless ``dry_run`` (the
    plan, no request).  ``hand``: record the files placed at their destinations by hand (no request but the licence
    page).  ``esco_max_pages``: ESCO's smoke run (:func:`fetch_source`; review minor 8, 2026-10-23)."""
    srcs = dict(sources if sources is not None else SOURCES)
    ks = list(keys) if keys else list(DEFAULT_FETCH)
    unknown = [k for k in ks if k not in srcs]
    if unknown:
        raise KeyError(f"unknown source(s) {unknown}; known: {sorted(srcs)}")
    out = FetchResult()
    if dry_run:
        for k in ks:
            s = srcs[k]
            size = f"~{s.size_bytes / 1e6:.1f} MB" if s.size_bytes else "size unknown"
            out.dry_run_lines.append(f"{k}: {s.url} -> {_rel(Path(dest_root) / s.dest)} ({size}, {s.licence}"
                                     f"{', on disk' if s.on_disk else ''}{', optional' if s.optional else ''}"
                                     f"{', wave ' + str(s.wave) if s.wave != 1 else ''})")
        out.dry_run_lines += [f"not fetched: {k} ({v})" for k, v in SKIPPED.items()]
        return out
    if not (approved_by and approved_by.strip()):
        raise NotApproved()
    client = http if http is not None else UrllibHttp(user_agent)
    now = utc_now()
    for k in ks:
        s = srcs[k]
        e, outcome = fetch_source(s, dest_root=dest_root, approved_by=approved_by, http=client, hand=hand,
                                  force=force, now=now, git_sha=git_sha, esco_max_pages=esco_max_pages, echo=echo)
        if outcome == "sample":
            out.samples.append(esco_sample_path(Path(dest_root) / s.dest))
            continue
        if outcome == "refused":
            out.hand.append({"key": k, "url": s.url, "dest": _rel(Path(dest_root) / s.dest)})
            continue
        out.entries.append(e)
        (out.fetched if outcome in ("fetched", "hand") else out.skipped).append(k)
        out.written.append(Path(dest_root) / Path(s.dest).parent / DOWNLOAD_MANIFEST_NAME)
    return out


__all__ = ["TOOL", "USER_AGENT", "APPROVAL_REQUIRED", "HAND_STATUSES", "ONET_ATTRIBUTION", "PROFESSIONS_ONET_NOTE",
           "ONET_CHANGES", "Source", "ESCO_API", "SOURCES", "DEFAULT_FETCH", "ESCO_KEYS", "LICENCE_CHECK", "SKIPPED",
           "ATTRIBUTION", "page_text", "licence_check", "attribution_keys", "attribution_markdown", "write_attribution",
           "attribution_record", "HttpResponse", "Http", "UrllibHttp", "sha256_file", "load_manifest",
           "merge_manifest", "manifest_row", "ESCO_UNVERIFIED", "esco_row", "fetch_esco_occupations", "NotApproved",
           "FetchResult", "hand_message", "esco_sample_path", "fetch_source", "fetch"]
