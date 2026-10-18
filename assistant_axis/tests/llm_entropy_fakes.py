"""Fixtures for the LLM-entropy generator's tests (no network).

**Every person here is invented** (names, descriptions and Wikidata ids made up for the tests; no real person's name
may reach a tracked file, plan section 5a).  The names are deliberately distinctive strings so that a grep for them
proves the privacy rule: :data:`REAL_PEOPLE` and :data:`FICTIONAL_PEOPLE`.

* :class:`FakeWikidataSession`: the ``get`` of :class:`~assistant_axis.gapgen.generators.llm_entropy.seeds.Throttle`
  answering the random-item API, ``wbgetentities`` and the SPARQL endpoint in the shapes recorded on 2026-10-13, from
  the invented people above plus non-human filler items; it can be told to answer HTTP 429 a number of times.
* :class:`ScriptedAnthropic`: an ``anthropic.AsyncAnthropic`` stand-in scripted **by prompt hash** (the sha256 of the
  system and user turns): a request whose prompt is not in the script raises, so a changed prompt fails a test
  loudly.  ``default`` answers anything not scripted (for tests that do not pin the prompts).
* :class:`FakeBatchClient`: ``client.messages.batches`` with create / retrieve / results / cancel.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Callable, Mapping, Optional

from assistant_axis.gapgen.generators.llm_entropy.seeds import Response
from assistant_axis.tests.fake_anthropic import make_response, system_text, user_text

#: Invented real-person seeds: (qid, name, description, birth time, death time).  None of these people exist.
REAL_PEOPLE: tuple[tuple, ...] = (
    ("Q990000101", "Quillon Varnaby", "invented tram conductor of Zellwick", "+1841-00-00T00:00:00Z",
     "+1903-00-00T00:00:00Z"),
    ("Q990000102", "Orsolya Thrummet", "invented glassblower, ID = 5550123", None, "+1690-00-00T00:00:00Z"),
    ("Q990000103", "Bexley Ravensquill", "invented radio announcer", "+1962-00-00T00:00:00Z", None),
    ("Q990000104", "Mirelda Okonkwazi", "invented botanist of Pellbridge", "+1921-00-00T00:00:00Z",
     "+1999-00-00T00:00:00Z"),
)
#: Invented fictional characters: (qid, name, description).
FICTIONAL_PEOPLE: tuple[tuple, ...] = (
    ("Q990000201", "Captain Zarnath Quell", "invented starship captain of a made-up serial"),
    ("Q990000202", "Grimbold Fennywhistle", "invented miser in an invented novel"),
    ("Q990000203", "Lady Ysolde Marchbanks", "invented duchess of a made-up comic"),
)
#: Invented other-language labels and aliases of the first real person (the fetch asks for them; the redaction covers
#: them, QUESTIONS 205): a Japanese label and an English alias.
ALT_NAMES: dict[str, tuple] = {"Q990000101": ("キロン・ヴァーナビー", "Q. Varnaby")}
FILLER_IDS = tuple(f"Q99000{i:04d}" for i in range(1000, 1060))


def every_secret() -> list[str]:
    """Every string the privacy tests grep for: names, name tokens of 3+ letters, the stems of the suffixed forms
    ("varnab" of "Varnabian"), descriptions, their capitalised words, other-language names and QIDs."""
    out = []
    for qid, name, desc, *_ in REAL_PEOPLE + FICTIONAL_PEOPLE:
        toks = [t for t in name.split() if len(t) >= 3]
        out += [qid, name, desc] + toks + [t[:-1] for t in toks if len(t) >= 5 and t[-1] in "aeiouy"]
        out += [w for w in desc.replace(",", " ").split() if w[:1].isupper() and len(w) >= 3]
        out += list(ALT_NAMES.get(qid, ()))
    return out


def _time_claim(t):
    return [{"mainsnak": {"datavalue": {"value": {"time": t}}}}] if t else []


class FakeWikidataSession:
    """See the module docstring.  ``fail_429``: answer HTTP 429 to that many requests first."""

    def __init__(self, *, fail_429: int = 0, html_error: int = 0, class_labels: Optional[Mapping[str, str]] = None,
                 class_counts: Optional[Mapping[str, int]] = None):
        from assistant_axis.gapgen.generators.llm_entropy.seeds import FICTIONAL_CLASSES
        self.fail_429 = fail_429
        self.html_error = html_error
        self.calls: list[dict] = []
        self.class_labels = dict(class_labels or FICTIONAL_CLASSES)
        self.class_counts = dict(class_counts or {q: 3 for q in FICTIONAL_CLASSES})
        self._round = 0
        self.real = {q: (n, d, b, x) for q, n, d, b, x in REAL_PEOPLE}
        self.fictional = {q: (n, d) for q, n, d in FICTIONAL_PEOPLE}

    def get(self, url, *, params, headers, timeout=60.0):
        self.calls.append({"url": url, "params": dict(params)})
        if self.fail_429 > 0:
            self.fail_429 -= 1
            return Response(429, "<html>Too Many Requests</html>")
        if "sparql" in url:
            return Response(200, json.dumps(self._sparql(params["query"])))
        if params.get("list") == "search":           # the fictional path (haswbstatement search, 2026-10-17)
            import re as _re
            qid = _re.search(r"P31=(Q\d+)", params["srsearch"]).group(1)
            hits = ([q for q, *_ in FICTIONAL_PEOPLE] if qid == "Q95074" else []) + [f"Q99{qid[1:]}"]
            off, lim = int(params.get("sroffset", 0)), int(params.get("srlimit", 10))
            rows = hits[off:off + lim] if lim > 1 else hits[:1]
            return Response(200, json.dumps({"query": {"searchinfo": {"totalhits": self.class_counts.get(qid, 0)},
                                                       "search": [{"ns": 0, "title": q} for q in rows]}}))
        if params.get("list") == "random":
            self._round += 1
            ids = [q for q, *_ in REAL_PEOPLE] if self._round == 1 else []
            ids += list(FILLER_IDS[(self._round - 1) * 5:(self._round - 1) * 5 + 5])
            return Response(200, json.dumps({"query": {"random": [{"id": 1, "ns": 0, "title": q} for q in ids]}}))
        if params.get("action") == "wbgetentities":
            ents = {}
            for q in params["ids"].split("|"):
                if q in self.class_labels:
                    ents[q] = {"labels": {"en": {"value": self.class_labels[q]}}}
                elif q in self.real:
                    n, d, b, x = self.real[q]
                    alts = ALT_NAMES.get(q, ())
                    labels = {"en": {"value": n}}
                    labels.update({"ja": {"value": a} for a in alts if not a.isascii()})
                    ents[q] = {"labels": labels, "descriptions": {"en": {"value": d}},
                               "aliases": {"en": [{"value": a} for a in alts if a.isascii()]},
                               "claims": {"P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q5"}}}}],
                                          "P569": _time_claim(b), "P570": _time_claim(x)}}
                elif q in self.fictional:
                    n, d = self.fictional[q]
                    ents[q] = {"labels": {"en": {"value": n}}, "descriptions": {"en": {"value": d}}}
                elif q in FILLER_IDS:   # a filler item: not a human
                    ents[q] = {"labels": {"en": {"value": f"filler {q}"}},
                               "claims": {"P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q4167836"}}}}]}}
                else:   # an item with no English label
                    ents[q] = {"labels": {}}
            return Response(200, json.dumps({"entities": ents}))
        return Response(404, "not found")

    def _sparql(self, query: str) -> dict:
        import re
        qid = re.search(r"wd:(Q\d+)", query).group(1)
        if "COUNT" in query:
            return {"results": {"bindings": [{"n": {"value": str(self.class_counts.get(qid, 0))}}]}}
        assert "wikibase:label" not in query, "the data query asks for ids only (2026-10-17: the label service timed out)"
        rows = []
        if qid == "Q95074":
            for q, n, d in FICTIONAL_PEOPLE:
                rows.append({"item": {"value": f"http://www.wikidata.org/entity/{q}"}})
        rows.append({"item": {"value": f"http://www.wikidata.org/entity/Q99{qid[1:]}"}})   # no English label
        return {"results": {"bindings": rows}}


# --------------------------------------------------------------------------- the model

def prompt_hash(system: str, user: str) -> str:
    import hashlib
    return hashlib.sha256(json.dumps([system, user], ensure_ascii=False).encode("utf-8")).hexdigest()


def reply_items(labels, *, gloss_fmt="This means doing the {label} thing every day.", antonym=None,
                probability=None, kind="trait", approach="The constraint read plainly.") -> str:
    items = []
    for lab in labels:
        it = {"label": lab, "gloss": gloss_fmt.format(label=lab), "antonym": antonym, "kind": kind,
              "ambiguity_flag": False}
        if probability is not None:
            it["probability"] = probability
        items.append(it)
    return json.dumps({"approach": approach, "items": items}, ensure_ascii=False)


class ScriptedAnthropic:
    """``messages.create`` answering from ``script`` (prompt hash -> text, a response, an exception, or a callable of
    the request kwargs), else from ``default(kwargs)``; with neither, a ``KeyError`` naming the user turn's first
    line (never the system turn)."""

    def __init__(self, script: Optional[Mapping] = None, default: Optional[Callable] = None):
        self.script = dict(script or {})
        self.default = default
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kw):
        self.calls.append(kw)
        key = prompt_hash(system_text(kw) if kw.get("system") else "", user_text(kw))
        out = self.script.get(key)
        if out is None and self.default is not None:
            out = self.default(kw)
        if out is None:
            raise KeyError(f"unscripted prompt: {user_text(kw).splitlines()[0][:60]!r}")
        if callable(out) and not isinstance(out, (str, BaseException)):
            out = out(kw)
        if isinstance(out, BaseException):
            raise out
        return make_response(out) if isinstance(out, str) else out


class FakeBatches:
    """``client.messages.batches``: create / retrieve / results / cancel.  ``responder(params)`` answers each request
    (a string or a response); ``polls`` retrievals report ``in_progress`` first."""

    def __init__(self, responder: Callable, *, polls: int = 0):
        self.responder = responder
        self.polls = polls
        self.created: list[dict] = []
        self.batches: dict[str, dict] = {}
        self.cancelled: list[str] = []

    def create(self, *, requests):
        bid = f"msgbatch_{len(self.created) + 1:03d}"
        self.created.append({"id": bid, "requests": list(requests)})
        self.batches[bid] = {"requests": list(requests), "left": self.polls, "status": "in_progress"}
        return SimpleNamespace(id=bid, processing_status="in_progress")

    def retrieve(self, bid):
        b = self.batches[bid]
        if b["left"] > 0 and b["status"] == "in_progress":
            b["left"] -= 1
            return SimpleNamespace(id=bid, processing_status="in_progress", request_counts={"processing": 1})
        b["status"] = "ended"
        return SimpleNamespace(id=bid, processing_status="ended", request_counts={}, ended_at=None)

    def cancel(self, bid):
        self.cancelled.append(bid)
        self.batches[bid]["status"] = "ended"
        return SimpleNamespace(id=bid, processing_status="canceling")

    def results(self, bid):
        out = []
        for r in reversed(self.batches[bid]["requests"]):
            msg = self.responder(dict(r["params"]))
            if isinstance(msg, str):
                msg = make_response(msg)
            msg.model = r["params"]["model"]
            out.append(SimpleNamespace(custom_id=r["custom_id"], result=SimpleNamespace(type="succeeded", message=msg)))
        return out


class FakeBatchClient:
    def __init__(self, responder: Callable, **kw):
        self.messages = SimpleNamespace(batches=FakeBatches(responder, **kw))

    @property
    def batches(self) -> FakeBatches:
        return self.messages.batches


def kwargs_hash(params: Mapping) -> str:
    """The prompt hash of a request's kwargs (live or batch params)."""
    return prompt_hash(system_text(params) if params.get("system") else "", user_text(params))


# --------------------------------------------------------------------------- records and items

def gen_record(family: str, prompt_id: str, labels, *, run: int = 1, stage: int = 1, model: str = "claude-haiku-5-5",
               glosses=None, antonyms=None, kinds=None, probability=None, step: str = "generate", language: str = "en",
               meta: Optional[dict] = None, items: Optional[list] = None, ok: bool = True, usage_raw=None,
               charged_as: Optional[str] = None) -> dict:
    """A response record as the runner writes it, without the runner (table, collapse and evaluate tests)."""
    from assistant_axis.gapgen.generators.llm_entropy.calls import model_tag
    labels = list(labels)
    its = []
    for i, lab in enumerate(labels):
        it = {"label": lab, "gloss": (glosses or {}).get(lab, f"This means acting the {lab} way."),
              "antonym": (antonyms or {}).get(lab), "kind": (kinds or {}).get(lab, "trait"), "ambiguity_flag": False}
        if family == "c":
            it.update(romanization=lab, english_hint=None)
        if probability is not None:
            it["probability"] = probability
        its.append(it)
    text = json.dumps({"approach": "read plainly", "items": its}, ensure_ascii=False)
    cid = f"{family}-{prompt_id.replace(':', '_')}-r{run}-s{stage}-{model_tag(model)}"
    rec = {"step": step, "family": family, "prompt_id": prompt_id, "run": run, "stage": stage, "model": model,
           "language": language, "prompt_sha256": f"p|{cid}", "user_sha256": f"u|{cid}", "custom_id": cid,
           "ok": ok, "text": text if items is None else None, "meta": dict(meta or {}),
           "usage_raw": usage_raw or {"input_tokens": 700, "output_tokens": 2000},
           "charged_as": charged_as or model}
    if items is not None:
        rec["items"] = items
    return rec


def bt_record(source: dict, entries, *, model: str = "claude-haiku-5-5") -> dict:
    """The back-translation record of a (c) ``gen_record``: ``entries`` = [(english label, gloss, antonym,
    listicle)] in item order."""
    text = json.dumps({"items": [{"index": i, "romanization": f"rom{i}", "label": lab, "gloss": g, "antonym": a,
                                  "listicle": li} for i, (lab, g, a, li) in enumerate(entries, 1)]})
    cid = "bt-" + source["custom_id"]
    return {"step": "backtranslate", "family": "c", "prompt_id": source["prompt_id"], "run": source["run"],
            "stage": source["stage"], "model": model, "language": source["language"], "prompt_sha256": f"p|{cid}",
            "user_sha256": f"u|{cid}", "custom_id": cid, "ok": True, "text": text,
            "meta": {"source_custom_id": source["custom_id"], "n_items": len(entries)},
            "usage_raw": {"input_tokens": 900, "output_tokens": 1500}, "charged_as": model}


# --------------------------------------------------------------------------- a model that answers every family

def _items_json(items, approach="read plainly") -> str:
    return json.dumps({"approach": approach, "items": items}, ensure_ascii=False)


def _it(label, gloss, antonym=None, kind="trait", **kw):
    d = {"label": label, "gloss": gloss, "antonym": antonym, "kind": kind, "ambiguity_flag": False}
    d.update(kw)
    return d


def family_reply(params) -> str:
    """Answer any of the generator's requests plausibly and deterministically (CLI tests): the translation calls in
    their tagged form, the back-translation by index, (b) with the person's name and description echoed in the
    approach, the glosses, an antonym and one label (the privacy test's bait), and the rest from the prompt id's
    parts.  Labels are ``zz`` words, so that none is a corpus stem by accident."""
    import re
    system = system_text(params) if params.get("system") else ""
    user = user_text(params)
    if system.startswith("You translate instructions"):
        lang = re.search(r"into (\w+)", system).group(1)
        master = user.split("<<<\n", 1)[1].split("\n>>>", 1)[0]
        doms = re.findall(r"^(\w+): ", user.split("Domains (id: English):", 1)[1], re.M)
        return (f"<note>A fixture translation into {lang}.</note>\n<system>\n[{lang}] {master}\n</system>\n"
                f"<user_template>\n[{lang}] Domain of life: {{domain}}. Name 15 to 20 traits.\n</user_template>\n"
                "<domains>\n" + "\n".join(f"{d}: {d}-{lang[:2].lower()}" for d in doms) + "\n</domains>")
    if system.startswith("You translate text from"):
        doms = re.findall(r"^(\w+): ", user.split("<domains>", 1)[1], re.M)
        return ("<system>\nThe instructions, back in English.\n</system>\n<user_template>\nDomain of life: {domain}."
                "\n</user_template>\n<domains>\n" + "\n".join(f"{d}: {d}" for d in doms) + "\n</domains>")
    if user.startswith("Language: "):
        n = len(re.findall(r"^\d+\. label:", user, re.M))
        labs = re.findall(r'^\d+\. label: "([^"]*)"', user, re.M)
        out = [{"index": i, "romanization": f"rom-{i}", "label": "zzc" + re.sub(r"[^a-z]", "", labs[i - 1].lower())[:12] + "abcdefghij"[i % 10],
                "gloss": f"This means the {i}th thing in English.", "antonym": None, "listicle": i == 2}
               for i in range(1, n + 1)]
        return json.dumps({"items": out})
    if user.startswith("Earlier, asked the following"):
        return _items_json([_it(f"zzrare{i}", f"This means a rare way number {i}.", probability=0.01) for i in range(3)]
                           + [_it("zzshared", "This means the shared one.", probability=0.02)])
    if user.startswith("Person: "):
        line = user.splitlines()[0]
        name = line[len("Person: "):line.index(" (")] if " (" in line else line[len("Person: "):].rstrip(".")
        desc = line[line.index(" (") + 2:].split(";")[0].rstrip(").") if " (" in line else ""
        last = name.split()[-1].lower()
        Last = name.split()[-1]
        stem = Last[:-1] if Last[-1] in "aeiouy" else Last
        place = [w for w in desc.split() if w[:1].isupper()]
        fictional = line.rstrip(".").endswith("fictional)")
        # the privacy bait (Fable's review, 2026-10-17, blocker 1): the name and description echoed, and the name's
        # suffix forms ("Varnabyesque", "a Varnabian habit", "the Varnabys", "Varnabyish"), a place name's
        # ("Zellwickian") and, for the first person, the native-script label the fetch returned
        suffixed = (f"This means {Last}esque manners, a {stem}ian habit, like the {Last}s, {Last}ish to the core"
                    + (f", {place[0]}ian pride" if place else "")
                    + (", " + ALT_NAMES["Q990000101"][0] if name == "Quillon Varnaby" else "") + ".")
        items = [_it(f"{last}-like", f"This means acting as {name} did, the {desc}.", antonym=f"un-{last}"),
                 _it("zzsteadfast", f"This means keeping on like {name.split()[0]} always did."),
                 _it("zzflourish", suffixed, antonym=f"{Last}ish"),
                 _it("zzwardenly", "This means guarding a gate for a living.", kind="role")]
        if not fictional:
            items.append(_it(f"{last}esque", "This means acting in the manner of the person."))
            if place:
                items.append(_it(f"{place[0].lower()}ian", "This means acting like the place."))
        return _items_json(items, approach=f"{name}, {desc}, read plainly; {Last}esque.")
    if user.startswith("[") and "Domain of life:" in user:
        m = re.match(r"\[(\w+)\] Domain of life: ([\w-]+)\.", user)
        lang, dom = m.group(1), m.group(2)
        return _items_json([_it(f"{dom}wört{i}", f"{lang} gloss {i}", romanization=f"{dom}woert{i}", english_hint=None)
                            for i in range(3)])
    probs = {"probability": 0.2} if '"probability"' in user else {}
    if user.startswith("Domain: "):
        m = re.match(r"Domain: ([\w ]+)\. Mode: ([\w ]+)\.", user)
        dom, mode = m.group(1).replace(" ", ""), m.group(2).split()[-1]
        return _items_json([_it(f"zz{dom}{mode}", f"This means a {mode} about {dom}.", **probs),
                            _it("zzshared", "This means the shared one.", **probs),
                            _it(f"zz{dom}extra", f"This means more about {dom}.", antonym="gloomy", **probs)])
    if user.startswith("Spelling constraint") or user.startswith("Form constraint"):
        key = re.sub(r"[^a-z]", "", user.splitlines()[0].split('"')[1].lower())
        return _items_json([_it(f"zzspell{key}", f"This means spelling {key}.", **probs),
                            _it("zzshared", "This means the shared one.", **probs)])
    raise KeyError(f"no fixture answer for: {user.splitlines()[0][:60]!r}")
