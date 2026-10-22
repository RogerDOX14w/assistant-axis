"""Fakes and fixtures for generator B's tests (coding plan 16, § 8 tests 11-15): a fake HTTP layer (200 for O*NET,
403 for BLS, a two-page ESCO API), small O*NET, job-title and OEWS files, a ten-role fixture corpus with its kinds, a
renamed role and a seed queue, a fake Anthropic responder for the lay call keyed by the group in the user turn, and a
hash-embedder role index.  No network, no key."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable, Mapping, Optional

from assistant_axis.gapgen.generators.professions.sources import HttpResponse
from assistant_axis.tests.fake_anthropic import make_response, user_text

ONET_OCC_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_csv/occupation_data.csv"
ONET_TITLES_URL = "https://www.onetcenter.org/dl_files/database/db_31_0_csv/job_titles.csv"
ONET_LICENCE_URL = "https://www.onetcenter.org/license_db.html"
BLS_OEWS_URL = "https://www.bls.gov/oes/special-requests/oesm25nat.zip"
BLS_LICENCE_URL = "https://www.bls.gov/bls/linksite.htm"
ESCO_LICENCE_URL = "https://esco.ec.europa.eu/en/copyright-notice-esco-skills-competences"


class FakeHttp:
    """``get`` / ``head`` from a ``{url: HttpResponse}`` table (an unknown URL answers 404); a URL starting with a
    key ending in ``*`` matches it.  Every request is recorded in ``calls`` as ``(method, url)``."""

    def __init__(self, table: Mapping[str, HttpResponse]):
        self.table = dict(table)
        self.calls: list[tuple[str, str]] = []

    def _find(self, url: str) -> HttpResponse:
        if url in self.table:
            return self.table[url]
        for k, v in self.table.items():
            if k.endswith("*") and url.startswith(k[:-1]):
                return v
        return HttpResponse(404, b"not found")

    def get(self, url: str) -> HttpResponse:
        self.calls.append(("GET", url))
        return self._find(url)

    def head(self, url: str) -> HttpResponse:
        self.calls.append(("HEAD", url))
        r = self._find(url)
        return HttpResponse(r.status, b"", {"Content-Length": str(len(r.body))} if r.ok else {})


JOB_TITLES_CSV = (
    "O*NET-SOC Code,Alternate Title,Short Title,Source(s)\n"
    "33-9032.00,Bouncer,,08\n"
    "33-9032.00,Security Officer,,08\n"
    "33-9032.00,Security Guard,,08\n"
)


def onet_http(*, bls_status: int = 403, titles_body: bytes = JOB_TITLES_CSV.encode()) -> FakeHttp:
    """O*NET answers 200 (the licence page names CC BY 4.0); bls.gov answers ``bls_status`` (403: refused)."""
    return FakeHttp({
        ONET_TITLES_URL: HttpResponse(200, titles_body),
        ONET_OCC_URL: HttpResponse(200, b"O*NET-SOC Code,Title,Description\n"),
        ONET_LICENCE_URL: HttpResponse(200, b"<p>Licensed under a Creative Commons CC BY 4.0 License.</p>"),
        BLS_OEWS_URL: HttpResponse(bls_status, b"PK-fake-zip" if bls_status == 200 else b"Access Denied"),
        BLS_LICENCE_URL: HttpResponse(bls_status, b"everything we publish is in the public domain"),
        ESCO_LICENCE_URL: HttpResponse(200, b"licensed under the Creative Commons Attribution 4.0 International (CC BY 4.0)"),
    })


def esco_page(results: list, *, total: int, next_href: Optional[str] = None) -> HttpResponse:
    d = {"total": total, "_embedded": {"results": results}}
    if next_href:
        d["_links"] = {"next": {"href": next_href}}
    return HttpResponse(200, json.dumps(d).encode())


def esco_occupation(uri: str, label: str, *, code: str, alts=(), desc: Optional[str] = None, full: bool = True,
                    group_title: Optional[str] = None) -> dict:
    d = {"uri": uri, "title": label, "className": "Occupation"}
    if full:
        d.update(preferredLabel={"en": label}, alternativeLabel={"en": list(alts)},
                 description={"en": {"literal": desc or f"{label} do things.", "mimetype": "plain/text"}}, code=code,
                 _links={"broaderIscoGroup": [{"code": code.split(".")[0], "title": group_title or "Group"}]})
    return d


# --------------------------------------------------------------------------- O*NET, OEWS files

#: O*NET-SOC code -> (title, description): two physicians groups' worth (29-1221 spills over into 29-1210), security
#: guards, chief executives and a chief sustainability officer, bartenders, and a pilot.
OCCUPATIONS: dict[str, tuple[str, str]] = {
    "11-1011.00": ("Chief Executives", "Determine and formulate policies and provide overall direction of companies."),
    "11-1011.03": ("Chief Sustainability Officers", "Communicate and coordinate with management to address "
                                                    "sustainability issues."),
    "29-1211.00": ("Anesthesiologists", "Administer anesthetics and analgesics for pain management."),
    "29-1212.00": ("Cardiologists", "Diagnose, treat, manage, and prevent diseases of the cardiovascular system."),
    "29-1221.00": ("Pediatricians, General", "Diagnose, treat, and help prevent diseases and injuries in children."),
    "33-9032.00": ("Security Guards", "Guard, patrol, or monitor premises to prevent theft, violence, or infractions "
                                      "of rules. May operate x-ray and metal detector equipment."),
    "35-3011.00": ("Bartenders", "Mix and serve drinks to patrons, directly or through waitstaff."),
    "53-2011.00": ("Airline Pilots, Copilots, and Flight Engineers", "Pilot and navigate the flight of fixed-wing "
                                                                     "aircraft on scheduled air carrier routes."),
}

#: OEWS rows: OCC_CODE -> (OCC_TITLE, O_GROUP, TOT_EMP).
OEWS: dict[str, tuple[str, str, object]] = {
    "00-0000": ("All Occupations", "total", 151853870),
    "11-1010": ("Chief Executives", "broad", 211230),
    "11-1011": ("Chief Executives", "detailed", 211230),
    "29-1210": ("Physicians", "broad", 782430),
    "29-1211": ("Anesthesiologists", "detailed", 33210),
    "29-1212": ("Cardiologists", "detailed", "**"),
    "29-1221": ("Pediatricians, General", "detailed", 29070),
    "33-9030": ("Security Guards and Gambling Surveillance Officers", "broad", 1150000),
    "33-9032": ("Security Guards", "detailed", 1120000),
    "35-3010": ("Bartenders", "broad", 650000),
    "35-3011": ("Bartenders", "detailed", 650000),
    # 53-2010 has no broad row here: its employment is the sum of its detailed rows
    "53-2011": ("Airline Pilots, Copilots, and Flight Engineers", "detailed", 110000),
}


def write_onet(dir_: Path, occupations: Mapping[str, tuple[str, str]] = OCCUPATIONS) -> Path:
    p = Path(dir_) / "onet" / "occupation_data.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["O*NET-SOC Code", "Title", "Description"])
        for code, (t, d) in occupations.items():
            w.writerow([code, t, d])
    return p


def write_job_titles(dir_: Path, rows: list[tuple[str, str]]) -> Path:
    p = Path(dir_) / "onet" / "job_titles.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["O*NET-SOC Code", "Alternate Title", "Short Title", "Source(s)"])
        for code, t in rows:
            w.writerow([code, t, "", "08"])
    return p


def write_oews_csv(path: Path, rows: Mapping[str, tuple] = OEWS) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["AREA", "OCC_CODE", "OCC_TITLE", "O_GROUP", "TOT_EMP"])
        for code, (t, g, e) in rows.items():
            w.writerow(["99", code, t, g, e])
    return p


#: Zipf by label for the cut's tests (anything else: 2.0).
ZIPF = {"bouncer": 3.4, "security officer": 3.3, "security guard": 4.0, "doctor": 4.9, "lifeguard": 3.2,
        "roadie": 3.05, "bellhop": 2.6, "night watchman": 3.1, "bartender": 3.6, "barkeep": 3.0, "mixologist": 3.0,
        "cardiologist": 3.4, "executive": 4.7, "nurse's aide": 3.0, "pilot": 4.5}


def fake_zipf(text: str) -> float:
    return ZIPF.get(text.lower(), 2.0)


# --------------------------------------------------------------------------- the role corpus

#: stem -> (description, kind, arrangement)
ROLES: dict[str, tuple[str, str, Optional[dict]]] = {
    "doctor": ("A doctor is someone who examines patients, works out what is wrong and treats it.", "occupation", None),
    "nurse": ("A nurse is someone who cares for patients on a ward, giving medicines and watching them.", "occupation",
              None),
    "bartender": ("A bartender is someone who pours drinks behind a bar and listens to the regulars.", "occupation",
                  None),
    "pilot": ("A pilot is someone who flies aircraft from the preflight checks to the landing.", "occupation", None),
    "guardian": ("A guardian is someone who protects others from harm.", "stance",
                 {"kind": "pair", "members": ["destroyer", "guardian"]}),
    "destroyer": ("A destroyer is someone who tears things down.", "stance",
                  {"kind": "pair", "members": ["destroyer", "guardian"]}),
    "predator": ("A predator is an animal that hunts other animals for food.", "non_human", None),
    "optimist": ("An optimist is someone who expects things to turn out well.", "temperament", None),
    "judge": ("A judge is someone who weighs evidence in court and hands down rulings.", "occupation", None),
    "scholar": ("A scholar is someone who studies old texts in libraries and writes about them.", "occupation", None),
}
#: A renamed role: its file is ``scholar`` and it was once ``academic``.
RENAMED = {"scholar": {"stem": "academic", "date": "2026-09-01", "reason": "test"}}


def write_role_corpus(data_dir: Path, *, queue: Optional[list] = None) -> Path:
    """``<data_dir>/roles/instructions/*.json`` (with ``default.json``), ``roles/role_kinds.json`` and
    ``seed_queue.json`` (role entries: ``lifeguard`` live, ``courtesan`` turned down, ``smuggler`` done)."""
    d = Path(data_dir) / "roles" / "instructions"
    d.mkdir(parents=True, exist_ok=True)
    (Path(data_dir) / "traits" / "instructions").mkdir(parents=True, exist_ok=True)
    for stem, (desc, _, arr) in ROLES.items():
        doc = {"description": desc, "instruction": [], "questions": [], "eval_prompt": "x"}
        if arr:
            doc["arrangement"] = arr
        if stem in RENAMED:
            doc["renamed_from"] = RENAMED[stem]
        (d / f"{stem}.json").write_text(json.dumps(doc), encoding="utf-8")
    (d / "default.json").write_text(json.dumps({"description": "The assistant itself.", "instruction": []}))
    kinds = {"roles": {s: {"kind": k, "split": False, "n_parsed": 3, "unanimous": True}
                       for s, (_, k, _) in ROLES.items()}}
    kinds["roles"]["default"] = {"kind": "other"}
    (Path(data_dir) / "roles" / "role_kinds.json").write_text(json.dumps(kinds), encoding="utf-8")
    entries = queue if queue is not None else [
        {"stem": "lifeguard", "label": "lifeguard", "entity_type": "role", "status": "candidate",
         "tags": ["kind:occupation"]},
        {"stem": "courtesan", "label": "courtesan", "entity_type": "role", "status": "not_adopted"},
        {"stem": "smuggler", "label": "smuggler", "entity_type": "role", "status": "done"},
        {"stem": "plucky", "label": "plucky", "entity_type": "trait", "status": "candidate"},
    ]
    (Path(data_dir) / "seed_queue.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return Path(data_dir)


# --------------------------------------------------------------------------- the lay call

def lay_answer(roles: list[dict], reason: str = "One short reason.") -> str:
    return json.dumps({"reason": reason, "roles": roles})


def role(name: str, covers=(1,), distinct: bool = False, gloss: Optional[str] = None) -> dict:
    art = "An" if name[:1] in "aeiou" else "A"
    return {"role": name, "covers": list(covers), "distinct_persona": distinct,
            "gloss": gloss or f"{art} {name} is someone who works with {name} things all day."}


def group_of(kw: dict) -> dict:
    """The ``group`` object of a lay request's user turn."""
    return json.loads(user_text(kw).split("\n", 1)[0].rstrip(",") + "}")["group"]


def lay_responder(answers: Mapping[str, object], *, default: Optional[str] = None) -> Callable[[dict], object]:
    """Answer by the group: ``answers[code or code:alternate_title]`` is a reply text, a response, an exception, or a
    list (one per call, in order, the last repeated)."""
    counts: dict[str, int] = {}

    def respond(kw: dict):
        g = group_of(kw)
        key = f"{g['code']}:{g['alternate_title']}" if g.get("alternate_title") else g["code"]
        a = answers.get(key, default if default is not None else lay_answer([]))
        if isinstance(a, list):
            i = counts.get(key, 0)
            counts[key] = i + 1
            a = a[min(i, len(a) - 1)]
        if isinstance(a, str):
            return make_response(a, input_tokens=900, output_tokens=300)
        return a
    return respond


def refusal_response():
    r = make_response("", input_tokens=900, output_tokens=0, stop_reason="refusal")
    r.content = []
    return r


# --------------------------------------------------------------------------- the role index

class FakeMetricConfig:
    """What ``rank.build_role_index`` reads of the metric config."""
    config_version = "test"
    covered = {"representation": "w20", "space": {"variant": "raw"}, "metric": "cos", "k": 10}
    extra: dict = {}
    roles = None                    # no ``roles`` section: M2's settings with the role query form
    live_model = {"model_id": "hash-64"}


def hash_embed():
    """``(embed(texts) -> unit rows, embedder)`` with the free hash embedder."""
    from assistant_axis.gapgen import embed as EM
    emb = EM.HashEmbedder()
    return (lambda texts: EM.embed_texts(emb, texts)), emb
