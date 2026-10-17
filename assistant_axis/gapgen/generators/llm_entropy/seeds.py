"""Family (b)'s person seeds from Wikidata, held in memory only (plan sections 5a and 6; Roger's decision 3).

**Sources** (CC0, Wikidata): real persons by the MediaWiki random-item API (``list=random`` in namespace 0, then
``wbgetentities`` for the instance-of claims, the English label and description and the dates; kept only when
``P31`` names ``Q5``, human; with ``dead_only``, only when ``P570``, date of death, is present); fictional ones by
SPARQL over :data:`FICTIONAL_CLASSES`, one ``COUNT`` and one ``LIMIT``/``OFFSET`` query per class per call at a
seeded random offset (the direct instances of fictional character, ``Q95074``, number only about 5,000, so the
subclasses are queried too).  The class ids are checked against their English labels in the same call (one
``wbgetentities`` request) and a class whose label does not name a character or a human is skipped with a warning.

**One request at a time** (:class:`Throttle`): never two within :data:`MIN_INTERVAL_S` seconds, HTTP 429 and 5xx (and
a connection error) retried with the back-off :data:`BACKOFF_S`, the fifth failure raised (on 2026-10-13 four
requests sent in a burst were refused with HTTP 429).

**Privacy** (section 5a).  A :class:`PersonSeed` lives in memory: its ``repr`` shows neither name, description nor
QID, nothing here logs or raises with one, and no function writes one.  :func:`redact` replaces, in a text, the
seed's description, its full name, every token of its name of three characters or more (whole words,
case-insensitive, with and without diacritics), its QID and the longer digit runs of its description by "this
person"; :func:`name_in_label` says whether a label carries a name token (a real seed's such item is dropped).  The
tracked fetch record (:func:`fetch_record_entry`, :func:`write_fetch_record`, ``person_seeds_fetch.json``) keeps
counts, requests, the licence, the capture date, a sha256 of the seeds and, per opaque seed id (``b:r0137``,
``b:f0042``), only its kind and birth-era band.

**What the redaction covers, and what it cannot** (Fable's review, 2026-10-17; QUESTIONS 205).  A name token of
four characters or more is matched with up to six letters after it ("Varnabyesque", "the Varnabys"), and without its
last vowel or ``y`` ("Varnabian"); a real seed's description's proper names ("Zellwick", "Zellwickian") are redacted
like the name; the entities request asks for the person's labels and aliases in sixteen languages
(:data:`NAME_LANGUAGES`), kept in memory as :attr:`PersonSeed.alt_names` and redacted too, so a native-script form
Wikidata holds is covered.  The runner's last-resort guard (``calls.EntropyRunner._guard``) checks every finished (b)
record with :func:`leaks` before it is written.  **The residual risk**: the model may write the name in a form the
seed does not hold: a transliteration or a native-script spelling Wikidata has no label for, a nickname that is no
alias, or a derivation the suffix rule misses ("Varnabification").  The prompt shows only the English name, so such a
form is unlikely; it is the one known gap, and nothing here can close it without a network lookup.  A fictional seed
has no other names (the SPARQL draw gives the English label only).
"""
from __future__ import annotations

import hashlib
import http.client
import json
import logging
import random
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.registry import utc_now

logger = logging.getLogger(__name__)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "assistant-axis LLM-entropy generator (research; contact via the repository owner)"
LICENCE = "CC0 1.0 (Wikidata; https://www.wikidata.org/wiki/Wikidata:Licensing)"
HUMAN = "Q5"
P_INSTANCE_OF, P_BIRTH, P_DEATH = "P31", "P569", "P570"
#: Fictional character and its main subclasses (plan section 1 and "Measured"): the id and the English label the
#: check expects to find in Wikidata's own label.  Checked against Wikidata in every fictional draw.
FICTIONAL_CLASSES: dict[str, str] = {
    "Q95074": "fictional character", "Q15632617": "fictional human", "Q3658341": "literary character",
    "Q1114461": "comics character", "Q15773347": "film character", "Q15773317": "television character",
    "Q1569167": "video game character", "Q80447738": "anime character",
}
MIN_INTERVAL_S = 2.0
BACKOFF_S: tuple[float, ...] = (5, 20, 60, 180)
RETRY_STATUSES = (429, 500, 502, 503, 504)
#: The longest Retry-After the throttle waits out (2026-10-17: after slow label-service queries the query service
#: answered every request with HTTP 429 and Retry-After 1000 for a while; the plain back-off gave up within 4.5
#: minutes).  A longer one stops the fetch with a message naming the wait.
MAX_RETRY_AFTER_S = 1200.0
#: Random items asked for per request (``wbgetentities`` takes at most 50 ids).
RANDOM_BATCH = 50
#: Stop a draw that has made this many random-item rounds without filling its quota (about a tenth of random items
#: are humans, 2026-10-13, so 400 real seeds take about 80 rounds).
MAX_RANDOM_ROUNDS = 400
#: Rows a fictional class is asked for at least (twice its quota when that is more), so that a class short of its
#: quota can be topped up from another's spares.
MIN_CLASS_ROWS = 4
#: The languages whose labels and aliases the entities request asks for: English and the multilingual label, the ten
#: family-(c) languages and four more, so that a name written in another script can be redacted too (QUESTIONS 205).
NAME_LANGUAGES = "en|mul|de|ja|zh|ru|ar|fa|fi|ko|hi|tr|fr|es|it|pt"
MAX_ALT_NAMES = 40
ERA_BANDS: tuple[str, ...] = ("<1800", "1800-1899", "1900-1949", "1950+", "unknown")
#: When only the year of death is known, the birth year the era band assumes is this many years before it.
ASSUMED_LIFESPAN = 60
FETCH_RECORD_SCHEMA = 1


class FetchError(RuntimeError):
    """A Wikidata request failed for good (the message names the endpoint and the status, never a seed)."""


# --------------------------------------------------------------------------- HTTP

@dataclass
class Response:
    status_code: int
    text: str
    retry_after: Optional[float] = None       # the server's Retry-After, in seconds, when it sent one

    def json(self) -> Any:
        return json.loads(self.text)


class UrllibSession:
    """The minimal ``get`` the throttle needs, on the standard library (no new dependency)."""

    def get(self, url: str, *, params: Mapping[str, str], headers: Mapping[str, str], timeout: float = 60.0
            ) -> Response:
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=dict(headers))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https endpoints
                return Response(resp.status, resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            ra = exc.headers.get("Retry-After") if exc.headers is not None else None
            return Response(exc.code, exc.read().decode("utf-8", "replace") if exc.fp else "",
                            float(ra) if ra and str(ra).strip().isdigit() else None)


class Throttle:
    """One request at a time, at least ``min_interval`` seconds apart (measured from the last request's start),
    retrying 429, 5xx and connection errors with ``backoff``; the last failure raises :class:`FetchError`.
    ``clock`` and ``sleep`` are injectable (tests use a fake clock)."""

    def __init__(self, session=None, *, min_interval: float = MIN_INTERVAL_S, backoff: Sequence[float] = BACKOFF_S,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 user_agent: str = USER_AGENT):
        self.session = session if session is not None else UrllibSession()
        self.min_interval = float(min_interval)
        self.backoff = tuple(backoff)
        self.clock, self.sleep = clock, sleep
        self.user_agent = user_agent
        self._last: Optional[float] = None
        self.sent: list[float] = []          # the clock at every request sent (the throttle test reads it)
        self.counts: Counter = Counter()

    def _wait(self) -> None:
        if self._last is not None:
            gap = self.min_interval - (self.clock() - self._last)
            if gap > 0:
                self.sleep(gap)
        self._last = self.clock()
        self.sent.append(self._last)

    def get_json(self, url: str, params: Mapping[str, str], *, what: str = "request") -> Any:
        last = None
        for attempt in range(len(self.backoff) + 1):
            self._wait()
            self.counts[what] += 1
            try:
                resp = self.session.get(url, params=dict(params), headers={"User-Agent": self.user_agent,
                                                                           "Accept": "application/json"})
            except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:   # a connection error,
                # or a body cut off mid-read (IncompleteRead, seen on a large wbgetentities answer, 2026-10-17): retried
                last = f"{type(exc).__name__}"
                resp = None
            if resp is not None:
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except ValueError:
                        last = "HTTP 200 with a body that is not JSON"
                        if attempt >= len(self.backoff):
                            break
                elif resp.status_code in RETRY_STATUSES:
                    last = f"HTTP {resp.status_code}"
                    ra = getattr(resp, "retry_after", None)
                    if ra is not None:
                        if ra > MAX_RETRY_AFTER_S:
                            raise FetchError(f"{url}: HTTP {resp.status_code} with Retry-After {ra:.0f} s for a {what}"
                                             f" (over {MAX_RETRY_AFTER_S:.0f} s): try again later")
                        logger.warning("%s: HTTP %d, waiting the server's Retry-After of %.0f s", what,
                                       resp.status_code, ra)
                        self.sleep(ra)
                else:
                    raise FetchError(f"{url}: HTTP {resp.status_code} for a {what}")
            if attempt < len(self.backoff):
                self.counts["retries"] += 1
                logger.warning("%s: %s for a %s (attempt %d of %d); trying again in %ss", url, last, what,
                               attempt + 1, len(self.backoff) + 1, self.backoff[attempt])
                self.sleep(self.backoff[attempt])
        raise FetchError(f"{url}: {last} for a {what}, after {len(self.backoff) + 1} attempts")


def throttled(session=None, **kw) -> Throttle:
    """The plan's name for the throttle around a session."""
    return Throttle(session, **kw)


# --------------------------------------------------------------------------- seeds

@dataclass
class PersonSeed:
    """One seed, in memory only (section 5a).  ``repr`` leaves out the name, the description and the QID."""
    seed_id: str                                     # b:r0001 | b:f0001, numbered in draw order
    kind: str                                        # real | fictional
    qid: str = field(repr=False)
    name: str = field(repr=False)
    description: Optional[str] = field(default=None, repr=False)
    #: the person's other labels and aliases the fetch returned (any language, any script), redacted like the name
    alt_names: tuple = field(default=(), repr=False)
    born: Optional[str] = None                       # a year, "-44" for 44 BC
    died: Optional[str] = None
    dead: bool = False                               # a date of death is recorded (with or without a usable year)
    era: str = "unknown"
    fetched_at: Optional[str] = None

    def as_prompt_seed(self) -> dict:
        """What :func:`.prompts.render_b` reads (in memory only)."""
        return {"seed_id": self.seed_id, "name": self.name, "description": self.description, "kind": self.kind,
                "born": self.born, "died": self.died, "era": self.era}

    def public(self) -> dict:
        """What the fetch record may hold: the opaque id, the kind and the era band."""
        return {"seed_id": self.seed_id, "kind": self.kind, "era": self.era}


def era_band(born: Optional[str], died: Optional[str] = None) -> str:
    """``<1800``, ``1800-1899``, ``1900-1949``, ``1950+`` by the birth year, else by the year of death less
    :data:`ASSUMED_LIFESPAN`; ``unknown`` when neither is known (and for fictional seeds)."""
    def year(v):
        try:
            return int(str(v).lstrip("+"))
        except (TypeError, ValueError):
            return None
    y = year(born)
    if y is None and year(died) is not None:
        y = year(died) - ASSUMED_LIFESPAN
    if y is None:
        return "unknown"
    if y < 1800:
        return "<1800"
    if y < 1900:
        return "1800-1899"
    if y < 1950:
        return "1900-1949"
    return "1950+"


def _claim_ids(claims: Mapping, prop: str) -> list[str]:
    out = []
    for c in claims.get(prop) or []:
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v, Mapping) and v.get("id"):
            out.append(str(v["id"]))
    return out


def _claim_year(claims: Mapping, prop: str) -> tuple[bool, Optional[str]]:
    """``(present, year)``: whether the property is stated at all (a "somevalue" death counts), and its first usable
    year (``"-44"`` for 44 BC)."""
    cs = claims.get(prop) or []
    if not cs:
        return False, None
    for c in cs:
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        t = v.get("time") if isinstance(v, Mapping) else None
        m = re.match(r"^([+-])(\d+)-", str(t or ""))
        if m:
            y = int(m.group(2))
            return True, str(-y if m.group(1) == "-" else y)
    return True, None


def _label(entity: Mapping) -> Optional[str]:
    for lang in ("en", "mul"):
        v = ((entity.get("labels") or {}).get(lang) or {}).get("value")
        if isinstance(v, str) and v.strip():
            return " ".join(v.split())
    return None


def _alt_names(entity: Mapping, name: str) -> tuple:
    """Every other label and alias of the entity the request returned (in :data:`NAME_LANGUAGES`), distinct from the
    English name, at most :data:`MAX_ALT_NAMES`."""
    out: list[str] = []
    vals = [v.get("value") for v in (entity.get("labels") or {}).values() if isinstance(v, Mapping)]
    for lst in (entity.get("aliases") or {}).values():
        vals += [v.get("value") for v in lst or [] if isinstance(v, Mapping)]
    for v in vals:
        if isinstance(v, str) and v.strip():
            v = " ".join(v.split())
            if v.casefold() != name.casefold() and v not in out:
                out.append(v)
    return tuple(out[:MAX_ALT_NAMES])


def _description(entity: Mapping) -> Optional[str]:
    v = ((entity.get("descriptions") or {}).get("en") or {}).get("value")
    return " ".join(v.split()) if isinstance(v, str) and v.strip() else None


@dataclass
class FetchStats:
    """Counts of one draw (no seed in them)."""
    random_rounds: int = 0
    items_seen: int = 0
    humans_seen: int = 0
    skipped_alive: int = 0
    skipped_no_label: int = 0
    skipped_unfetchable: int = 0
    fictional_classes: dict = field(default_factory=dict)      # qid -> {"label", "label_ok", "count", "taken"}
    shortfall: dict = field(default_factory=dict)              # kind -> seeds asked for but not found

    def as_dict(self) -> dict:
        return {"random_rounds": self.random_rounds, "items_seen": self.items_seen, "humans_seen": self.humans_seen,
                "skipped_alive": self.skipped_alive, "skipped_no_label": self.skipped_no_label,
                "skipped_unfetchable": self.skipped_unfetchable,
                "fictional_classes": self.fictional_classes, "shortfall": self.shortfall}


#: Entities asked for per ``wbgetentities`` request of :func:`fetch_real` (2026-10-17: the answer for 50 random items
#: with their claims and the names in :data:`NAME_LANGUAGES` was cut off mid-read on every attempt by the network path,
#: as large Hub downloads were the same day; ten at a time fits).
ENTITIES_PER_REQUEST = 10


def _get_entities(session: "Throttle", ids: Sequence[str], stats: "FetchStats") -> dict:
    """The entities of ``ids``, :data:`ENTITIES_PER_REQUEST` at a time.  A chunk that still fails after the throttle's
    retries is split in half, down to single items; an item that cannot be fetched alone is skipped and counted
    (``skipped_unfetchable``), so one huge entity cannot sink the draw.  Errors carry no seed (ids only)."""
    out: dict = {}

    def get(chunk: list) -> None:
        try:
            out.update(session.get_json(WIKIDATA_API, {"action": "wbgetentities", "ids": "|".join(chunk),
                                                       "props": "labels|descriptions|aliases|claims",
                                                       "languages": NAME_LANGUAGES, "format": "json"},
                                        what="entities request").get("entities") or {})
        except FetchError:
            if len(chunk) == 1:
                stats.skipped_unfetchable += 1
                return
            mid = len(chunk) // 2
            get(chunk[:mid])
            get(chunk[mid:])

    for i in range(0, len(ids), ENTITIES_PER_REQUEST):
        get(list(ids[i:i + ENTITIES_PER_REQUEST]))
    return out


def fetch_real(n: int, *, session: Throttle, rng: Optional[random.Random] = None, dead_only: bool = False,
               start: int = 1, batch: int = RANDOM_BATCH, max_rounds: int = MAX_RANDOM_ROUNDS,
               stats: Optional[FetchStats] = None, now: Callable[[], str] = utc_now) -> list[PersonSeed]:
    """``n`` real persons (``P31`` = ``Q5``; with ``dead_only`` a ``P570`` too), numbered ``b:r{start:04d}`` on, by
    random-item rounds of ``batch`` items.  The randomness is the server's (``rng`` is accepted for the plan's
    signature and unused).  A draw that has not filled its quota after ``max_rounds`` rounds stops short and records
    the shortfall in ``stats``."""
    stats = stats if stats is not None else FetchStats()
    out: list[PersonSeed] = []
    seen: set[str] = set()
    while len(out) < n and stats.random_rounds < max_rounds:
        stats.random_rounds += 1
        r = session.get_json(WIKIDATA_API, {"action": "query", "list": "random", "rnnamespace": "0",
                                            "rnlimit": str(batch), "format": "json"}, what="random-item request")
        ids = [x.get("title") for x in ((r.get("query") or {}).get("random") or [])]
        ids = [q for q in ids if isinstance(q, str) and re.fullmatch(r"Q\d+", q) and q not in seen]
        if not ids:
            continue
        seen.update(ids)
        ents = _get_entities(session, ids, stats)
        for qid in ids:
            stats.items_seen += 1
            e = ents.get(qid) or {}
            claims = e.get("claims") or {}
            if HUMAN not in _claim_ids(claims, P_INSTANCE_OF):
                continue
            stats.humans_seen += 1
            dead, died = _claim_year(claims, P_DEATH)
            if dead_only and not dead:
                stats.skipped_alive += 1
                continue
            name = _label(e)
            if not name:
                stats.skipped_no_label += 1
                continue
            _, born = _claim_year(claims, P_BIRTH)
            out.append(PersonSeed(seed_id=f"b:r{start + len(out):04d}", kind="real", qid=qid, name=name,
                                  description=_description(e), alt_names=_alt_names(e, name), born=born,
                                  died=died, dead=dead,
                                  era=era_band(born, died), fetched_at=now()))
            if len(out) >= n:
                break
    if len(out) < n:
        stats.shortfall["real"] = n - len(out)
        logger.warning("real seeds: %d of %d found in %d rounds", len(out), n, stats.random_rounds)
    return out


def _count_query(qid: str) -> str:
    return f"SELECT (COUNT(?item) AS ?n) WHERE {{ ?item wdt:P31 wd:{qid} . }}"


def _data_query(qid: str, limit: int, offset: int) -> str:
    """The class's items at an offset, **ids only**: the label service applied before the OFFSET labels every row
    first, which on a large class (fictional human) ran 65 s and timed out (HTTP 504), and repeated calls drew HTTP
    429 (the first live pilot, 2026-10-17); the ids alone take about half a second.  Labels and descriptions come from
    ``wbgetentities`` (:func:`_labels_of`)."""
    return f"SELECT ?item WHERE {{ ?item wdt:P31 wd:{qid} . }} LIMIT {int(limit)} OFFSET {int(offset)}"


def _labels_of(session: "Throttle", qids: Sequence[str]) -> dict:
    """``{qid: (English label or None, English description or None)}``, :data:`ENTITIES_PER_REQUEST` per request."""
    out: dict = {}
    for i in range(0, len(qids), ENTITIES_PER_REQUEST):
        chunk = list(qids[i:i + ENTITIES_PER_REQUEST])
        ents = session.get_json(WIKIDATA_API, {"action": "wbgetentities", "ids": "|".join(chunk),
                                               "props": "labels|descriptions", "languages": "en", "format": "json"},
                                what="fictional labels request").get("entities") or {}
        for q in chunk:
            e = ents.get(q) or {}
            out[q] = (_label(e), _description(e))
    return out


def _class_label_ok(expected: str, label: Optional[str]) -> bool:
    lab = (label or "").lower()
    return bool(lab) and (lab == expected.lower() or "character" in lab or "human" in lab)


def fetch_fictional(n: int, *, session: Throttle, rng: random.Random, classes: Mapping[str, str] = FICTIONAL_CLASSES,
                    start: int = 1, stats: Optional[FetchStats] = None, now: Callable[[], str] = utc_now
                    ) -> list[PersonSeed]:
    """``n`` fictional characters, numbered ``b:f{start:04d}`` on: the quota split evenly over the classes (the
    remainder to classes in a seeded order), each class asked once for its size and once for ``2 x quota`` rows at a
    seeded random offset (at least :data:`MIN_CLASS_ROWS` rows, so a class with no quota still gives spares); rows
    without an English label (the label service returns the id) and repeats are skipped; a class short of its quota
    is topped up from the other classes' spare rows."""
    stats = stats if stats is not None else FetchStats()
    ids = list(classes)
    labels = session.get_json(WIKIDATA_API, {"action": "wbgetentities", "ids": "|".join(ids), "props": "labels",
                                             "languages": "en", "format": "json"},
                              what="class-label request").get("entities") or {}
    ok = []
    for q in ids:
        lab = _label(labels.get(q) or {})
        good = _class_label_ok(classes[q], lab)
        stats.fictional_classes[q] = {"expected": classes[q], "label": lab, "label_ok": good, "count": None,
                                      "taken": 0}
        if good:
            ok.append(q)
        else:
            logger.warning("fictional class %s: Wikidata's label %r is not %r; skipped", q, lab, classes[q])
    if not ok or n <= 0:
        if n > 0:
            stats.shortfall["fictional"] = n
        return []
    base, extra = divmod(n, len(ok))
    order = list(ok)
    rng.shuffle(order)
    quota = {q: base + (1 if i < extra else 0) for i, q in enumerate(order)}
    picked: list[tuple[str, str, Optional[str]]] = []
    spare: list[tuple[str, str, Optional[str]]] = []
    seen: set[str] = set()
    for q in ok:                                   # fixed order: each class queried once per call
        rows = session.get_json(WIKIDATA_SPARQL, {"query": _count_query(q), "format": "json"}, what="SPARQL count")
        try:
            count = int(((rows.get("results") or {}).get("bindings") or [{}])[0]["n"]["value"])
        except (KeyError, IndexError, TypeError, ValueError):
            count = 0
        stats.fictional_classes[q]["count"] = count
        if count <= 0:
            continue
        limit = max(MIN_CLASS_ROWS, 2 * quota[q])       # a class with no quota still gives spares for the top-up
        offset = rng.randrange(max(1, count - limit + 1))
        data = session.get_json(WIKIDATA_SPARQL, {"query": _data_query(q, limit, offset), "format": "json"},
                                what="SPARQL data")
        taken = 0
        qids = []
        for b in (data.get("results") or {}).get("bindings") or []:
            qid = ((b.get("item") or {}).get("value") or "").rsplit("/", 1)[-1]
            if re.fullmatch(r"Q\d+", qid) and qid not in seen and qid not in qids:
                qids.append(qid)
        labs = _labels_of(session, qids)
        for qid in qids:
            lab, desc = labs.get(qid) or (None, None)
            name = " ".join(str(lab or "").split())
            if not name or name == qid:
                continue
            seen.add(qid)
            row = (qid, name, " ".join(desc.split()) if isinstance(desc, str) and desc.strip() else None)
            if taken < quota[q]:
                picked.append(row)
                taken += 1
            else:
                spare.append(row)
        stats.fictional_classes[q]["taken"] = taken
    while len(picked) < n and spare:
        picked.append(spare.pop(0))
    if len(picked) < n:
        stats.shortfall["fictional"] = n - len(picked)
        logger.warning("fictional seeds: %d of %d found", len(picked), n)
    return [PersonSeed(seed_id=f"b:f{start + i:04d}", kind="fictional", qid=q, name=name, description=desc,
                       era="unknown", fetched_at=now()) for i, (q, name, desc) in enumerate(picked[:n])]


# --------------------------------------------------------------------------- redaction

REDACTED = "this person"
#: A name (or description) token of at least this many characters also matches with up to
#: :data:`NAME_SUFFIX_MAX` letters after it ("Varnaby" in "Varnabyesque", "Varnabian", "the Varnabys",
#: "Varnabyish"; Fable's review of 2026-10-17, blocker 1); a shorter one matches as a whole word only.
MIN_SUFFIX_TOKEN = 4
NAME_SUFFIX_MAX = 6
#: A capitalised token of a real seed's description (a place, an institution, a work) is redacted like a name unless
#: it is one of English's commonest words (Zipf at least this: "The", "Person", "Name"), which identify nobody.
DESCRIPTION_TOKEN_MAX_ZIPF = 5.5


def _fold(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def _tokens(texts: Iterable[Optional[str]], *, keep=lambda t: True) -> list[str]:
    toks = set()
    for text in texts:
        for t in re.findall(r"\w+", text or ""):
            if len(t) >= 3 and keep(t):
                toks.add(t.casefold())
                toks.add(_fold(t).casefold())
    return sorted(toks, key=lambda t: (-len(t), t))


def name_tokens(seed: PersonSeed) -> list[str]:
    """The tokens of the seed's name and its other names (:attr:`PersonSeed.alt_names`) of three characters or more,
    case-folded, with their diacritic-free forms, longest first."""
    return _tokens([seed.name, *seed.alt_names])


def _zipf(word: str) -> float:
    try:
        from wordfreq import zipf_frequency
    except ImportError:  # pragma: no cover - wordfreq is a project dependency
        return 0.0
    return float(zipf_frequency(word, "en"))


def description_tokens(seed: PersonSeed) -> list[str]:
    """A real seed's description's capitalised tokens (proper names: a place, an institution, a work), three
    characters or more, but for the commonest English words (Zipf >= :data:`DESCRIPTION_TOKEN_MAX_ZIPF`).  None for a
    fictional seed, whose description names a work, not a person's whereabouts (its full description is still
    redacted)."""
    from assistant_axis.gapgen.normalize import STOPWORDS
    if seed.kind != "real":
        return []
    return _tokens([seed.description], keep=lambda t: t[:1].isupper() and t.lower() not in STOPWORDS
                   and _zipf(t.lower()) < DESCRIPTION_TOKEN_MAX_ZIPF)


def token_pattern(tok: str) -> str:
    """A token as a whole word, or (four characters or more) with up to :data:`NAME_SUFFIX_MAX` letters after it;
    a token of five or more ending in a vowel or ``y`` also without that letter ("Varnab-ian" from "Varnaby")."""
    t = re.escape(tok)
    if len(tok) >= MIN_SUFFIX_TOKEN:
        stem = f"(?:{t}|{re.escape(tok[:-1])})" if len(tok) >= 5 and tok[-1] in "aeiouy" else t
        return rf"(?<!\w){stem}[a-z]{{0,{NAME_SUFFIX_MAX}}}(?!\w)"
    return rf"(?<!\w){t}(?!\w)"


def _phrases(seed: PersonSeed) -> list[str]:
    ps = {p for p in (seed.description, seed.name) if p and len(p) >= 3}
    ps |= {p for p in seed.alt_names if p and len(p) >= 2}       # a name in another script may be two characters
    ps |= {_fold(p) for p in ps}
    return sorted(ps, key=lambda p: (-len(p), p))


def _sub_tokens(s: str, toks: Sequence[str]) -> str:
    for t in toks:
        s = re.sub(token_pattern(t), REDACTED, s, flags=re.IGNORECASE)
    folded = _fold(s)
    if folded != s and len(folded) == len(s):          # a token written with other diacritics than the seed's
        for t in toks:
            for m in reversed(list(re.finditer(token_pattern(t), folded, flags=re.IGNORECASE))):
                s = s[:m.start()] + REDACTED + s[m.end():]
                folded = folded[:m.start()] + REDACTED + folded[m.end():]
    return s


def redact(text: Optional[str], seed: PersonSeed) -> Optional[str]:
    """``text`` with the seed's description, full name and other names (any script), name tokens and the
    description's proper names (case-insensitive, with and without diacritics; a token of four characters or more
    with up to six letters after it), QID and the description's digit runs of three or more replaced by "this
    person"."""
    if not text:
        return text
    s = str(text)
    for p in _phrases(seed):
        s = re.sub(re.escape(p), REDACTED, s, flags=re.IGNORECASE)
    s = _sub_tokens(s, name_tokens(seed))
    s = _sub_tokens(s, description_tokens(seed))
    if seed.qid:
        s = re.sub(rf"(?<!\w){re.escape(seed.qid)}(?!\w)", REDACTED, s)
    for d in sorted(set(re.findall(r"\d{3,}", seed.description or "")), key=len, reverse=True):
        s = re.sub(rf"(?<!\d){re.escape(d)}(?!\d)", REDACTED, s)
    return s


def _hits(text: str, toks: Sequence[str]) -> bool:
    fold = _fold(text).casefold()
    return any(re.search(token_pattern(_fold(t)), fold, flags=re.IGNORECASE) for t in toks)


def name_in_label(label: Optional[str], seed: PersonSeed) -> bool:
    """True when ``label`` carries the seed's full name, another of its names, or a name token (suffixed forms
    included: "varnabyesque")."""
    if not label:
        return False
    lab = _fold(str(label)).casefold()
    if any(_fold(p).casefold() in lab for p in (seed.name, *seed.alt_names) if p and len(p) >= 2):
        return True
    return _hits(str(label), name_tokens(seed))


def description_in_label(label: Optional[str], seed: PersonSeed) -> bool:
    """True when ``label`` carries one of the description's proper names (a real seed's such item is dropped)."""
    return bool(label) and _hits(str(label), description_tokens(seed))


def leaks(text: Optional[str], seed: PersonSeed) -> list[str]:
    """What of the seed a text still carries (for checks, and the runner's last-resort guard: ``[]`` after
    :func:`redact`); the strings themselves are never returned, only which kind of thing leaked."""
    if not text:
        return []
    out = []
    t = str(text)
    low, fold = t.casefold(), _fold(t).casefold()
    if seed.description and (seed.description.casefold() in low or _fold(seed.description).casefold() in fold):
        out.append("description")
    if _hits(t, name_tokens(seed)) or any(p.casefold() in low for p in seed.alt_names if p and len(p) >= 2):
        out.append("name")
    if _hits(t, description_tokens(seed)):
        out.append("description_token")
    if seed.qid and re.search(rf"(?<!\w){re.escape(seed.qid)}(?!\w)", t):
        out.append("qid")
    return out


# --------------------------------------------------------------------------- the fetch record

def seeds_sha256(seeds: Iterable[PersonSeed]) -> str:
    """A sha256 over the seeds' ids, QIDs, names, descriptions and dates (not reversible), so a later check can tell
    whether two runs drew the same persons without either storing them."""
    rows = [[s.seed_id, s.qid, s.name, s.description, s.born, s.died] for s in seeds]
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def fetch_record_entry(seeds: Sequence[PersonSeed], *, run_id: str, session_id: str, requested: Mapping[str, int],
                       dead_only: bool, requests: Mapping[str, int], stats: FetchStats,
                       fetched_at: Optional[str] = None) -> dict:
    """One run's entry of the tracked fetch record: counts, requests, the licence, the capture date, the seeds'
    sha256 and per opaque id only kind and era band.  No name, description or QID."""
    at = fetched_at or utc_now()
    real = [s for s in seeds if s.kind == "real"]
    fict = [s for s in seeds if s.kind == "fictional"]
    return {"run_id": run_id, "session_id": session_id, "fetched_at": at, "captured_on": at[:10],
            "licence": LICENCE, "source": "Wikidata: the random-item API (real persons) and SPARQL over fictional "
            "character classes (fictional ones)", "dead_only": bool(dead_only),
            "requested": dict(requested), "n_real": len(real), "n_fictional": len(fict),
            "era_bands": {b: sum(1 for s in real if s.era == b) for b in ERA_BANDS},
            "requests": dict(sorted(requests.items())), "stats": stats.as_dict(),
            "seeds_sha256": seeds_sha256(seeds), "seeds": [s.public() for s in seeds]}


def read_fetch_record(path: Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"schema_version": FETCH_RECORD_SCHEMA, "about": FETCH_RECORD_ABOUT, "runs": []}
    return json.loads(p.read_text(encoding="utf-8"))


FETCH_RECORD_ABOUT = ("Append-only record of the person-seed fetches of the LLM-entropy generator's family (b) "
                      "(coding_plan_06 section 5a): per run its counts, requests, licence, capture date and per "
                      "opaque seed id only kind and birth-era band.  No name, description or Wikidata id of a seed "
                      "is ever written: the seeds live in the memory of the process that asked about them.")


def run_has_fetch(path: Path, run_id: str) -> bool:
    return any(e.get("run_id") == run_id for e in read_fetch_record(path).get("runs") or [])


def write_fetch_record(path: Path, entry: Mapping, *, force: bool = False) -> Path:
    """Append ``entry`` to the record.  A run id that already has an entry is refused without ``force`` (a second
    (b) session in one run fetches new persons and pays again; ``--force`` says that is meant), and with it the new
    entry is appended beside the old one, which is never replaced."""
    rec = read_fetch_record(path)
    if not force and any(e.get("run_id") == entry.get("run_id") for e in rec.get("runs") or []):
        raise FileExistsError(f"{path}: run {entry.get('run_id')!r} already has a fetch entry; pass --force to fetch "
                              f"new seeds for it")
    blob = json.dumps(entry, ensure_ascii=False)
    for kind in ("name", "description", "qid"):     # belt and braces: an entry is built from public() only
        if f'"{kind}"' in blob:
            raise ValueError(f"a fetch entry may not carry a seed's {kind}")
    rec.setdefault("runs", []).append(dict(entry))
    rec["schema_version"] = FETCH_RECORD_SCHEMA
    rec["about"] = FETCH_RECORD_ABOUT
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", Path(path))
    return Path(path)


def next_seed_numbers(path: Path, run_id: str) -> tuple[int, int]:
    """``(first real number, first fictional number)`` for a new (b) session of ``run_id``: after the highest
    opaque ids its earlier entries used, so that a run's ids never repeat."""
    hi = {"r": 0, "f": 0}
    for e in read_fetch_record(path).get("runs") or []:
        if e.get("run_id") != run_id:
            continue
        for s in e.get("seeds") or []:
            m = re.fullmatch(r"b:([rf])(\d+)", str(s.get("seed_id") or ""))
            if m:
                hi[m.group(1)] = max(hi[m.group(1)], int(m.group(2)))
    return hi["r"] + 1, hi["f"] + 1


def summary_lines(seeds: Sequence[PersonSeed], stats: FetchStats, requests: Mapping[str, int]) -> list[str]:
    """What a dry run prints: counts, era bands, class sizes and requests (no seed)."""
    real = [s for s in seeds if s.kind == "real"]
    fict = [s for s in seeds if s.kind == "fictional"]
    bands = Counter(s.era for s in real)
    lines = [f"seeds: {len(real)} real, {len(fict)} fictional; dead {sum(1 for s in real if s.dead)} of the real",
             "era bands (real, by birth year, else death year - 60): "
             + ", ".join(f"{b} {bands.get(b, 0)}" for b in ERA_BANDS),
             f"random rounds {stats.random_rounds}, items seen {stats.items_seen}, humans {stats.humans_seen}, "
             f"skipped alive {stats.skipped_alive}, skipped without an English label {stats.skipped_no_label}",
             "requests: " + ", ".join(f"{k} {v}" for k, v in sorted(requests.items()))]
    for q, c in stats.fictional_classes.items():
        lines.append(f"  class {q} ({c['expected']}): Wikidata label {'matches' if c['label_ok'] else 'DOES NOT MATCH'}"
                     f", {c['count']} direct instances, {c['taken']} taken")
    if stats.shortfall:
        lines.append(f"SHORTFALL: {stats.shortfall}")
    return lines


__all__ = ["WIKIDATA_API", "WIKIDATA_SPARQL", "LICENCE", "FICTIONAL_CLASSES", "MIN_INTERVAL_S", "BACKOFF_S",
           "ERA_BANDS", "FetchError", "Response", "UrllibSession", "Throttle", "throttled", "PersonSeed", "era_band",
           "FetchStats", "fetch_real", "fetch_fictional", "REDACTED", "MIN_SUFFIX_TOKEN", "NAME_SUFFIX_MAX",
           "name_tokens", "description_tokens", "token_pattern", "redact", "name_in_label", "description_in_label",
           "leaks", "seeds_sha256", "fetch_record_entry", "read_fetch_record", "run_has_fetch", "write_fetch_record",
           "next_seed_numbers", "summary_lines"]
