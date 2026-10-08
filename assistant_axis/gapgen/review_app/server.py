"""The review app's server: FastAPI over :class:`decisions.DecisionLog` (section 3 of
``reports/trait_gap_generation/coding_plan_review.md``).  One process, local only; Roger starts it with
``review_app.py serve`` and opens ``http://127.0.0.1:8765``.

Routes:

* ``GET /``: the page (``static/index.html``; ``app.js`` and ``style.css`` under ``/static``).
* ``GET /api/queue?order=cliques|generator|region``: every merged group, proposed group and singleton, with handled
  counts, and the counts the page shows at all times.
* ``GET /api/group/{id}``: a working group's card: members (gloss, generator, M1 tags, M3 decision and covering
  trait, flags, handled), neighbours ranked by strongest edge, corpus and queue traits by reading (each a link to its
  file), opposed neighbours, the other groups sharing a member.
* ``GET /api/term/{key}``: the ego view of one term (everything one edge away).
* ``GET /api/find?q=``: terms, corpus traits and queue entries by label (``/`` on the page).
* ``POST /api/action``: one event (``{"action": ..., ...}``, :mod:`.decisions`); returns the event, the group's card
  and the counts.  A refusal is a 409 with the reason; nothing is logged.
* ``GET /api/status``: groups resolved and open, decisions by type, time per decision.
* ``GET /files/traits/{stem}.json``: a corpus trait's file, read-only; ``GET /files/queue/{stem}``: a seed-queue
  entry.  Nothing else of the repository is served, and nothing is written but ``decisions.jsonl``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from assistant_axis.gapgen import paths

from .decisions import ActionError, DecisionLog

STATIC_DIR = Path(__file__).resolve().parent / "static"
_STEM = re.compile(r"^[a-z0-9][a-z0-9_]*$")


def create_app(*, review_dir: Path, data_dir: Optional[Path] = None, registry_path: Optional[Path] = None,
               queue_path: Optional[Path] = None, order: str = "cliques", by: str = "roger", clock=None) -> FastAPI:
    """The app for one review batch's directory (``graph.json`` there; ``decisions.jsonl`` written there).
    ``data_dir``: the corpus (``traits/instructions``) and, unless ``queue_path``, ``seed_queue.json``;
    ``registry_path``: read once for display (M1 tags, review blocks already applied)."""
    data_dir = Path(data_dir) if data_dir is not None else paths.DATA_DIR
    queue_path = Path(queue_path) if queue_path is not None else data_dir / "seed_queue.json"
    log = DecisionLog.open(Path(review_dir), by=by, clock=clock, data_dir=data_dir, registry_path=registry_path,
                           queue_path=queue_path)
    app = FastAPI(title=f"review {log.graph.batch_id}", docs_url=None, redoc_url=None)
    app.state.log = log
    app.state.default_order = order
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def page():
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    @app.get("/api/meta")
    def meta():
        g = log.graph
        return {"batch_id": g.batch_id, "from_batches": g.from_batches, "graph_sha256": log.graph_sha256,
                "complete": g.complete, "schema": g.schema, "default_order": order, "by": log.by,
                "proposed_cut_off": g.config.get("proposed_cut_off")}

    @app.get("/api/queue")
    def queue(order: Optional[Literal["cliques", "generator", "region"]] = None):
        with log.lock:
            o = order or app.state.default_order
            return {"order": o, "items": log.state.queue(o), "counts": log.state.counts()}

    @app.get("/api/group/{gid}")
    def group(gid: str):
        with log.lock:
            try:
                return log.state.group_card(gid) | {"counts": log.state.counts()}
            except KeyError:
                raise HTTPException(404, f"no group {gid}") from None

    @app.get("/api/term/{key}")
    def term(key: str):
        with log.lock:
            try:
                return log.state.term_card(key)
            except KeyError:
                raise HTTPException(404, f"no term {key}") from None

    @app.get("/api/find")
    def find(q: str = ""):
        with log.lock:
            return {"q": q, "results": log.state.find(q)}

    @app.post("/api/action")
    def action(req: dict = Body(...)):
        with log.lock:
            try:
                ev, gid = log.act(req)
            except ActionError as exc:
                raise HTTPException(409, str(exc)) from None
            card = log.state.group_card(gid) if gid in log.state.groups else None
            return {"event": ev, "group": card, "counts": log.state.counts()}

    @app.get("/api/status")
    def status():
        return log.status()

    @app.get("/files/traits/{name}")
    def trait_file(name: str):
        stem = name[:-5] if name.endswith(".json") else None
        p = data_dir / "traits" / "instructions" / f"{stem}.json"
        if not stem or not _STEM.match(stem) or not p.is_file():
            raise HTTPException(404, f"no corpus trait file {name}")
        return FileResponse(p, media_type="application/json")

    @app.get("/files/queue/{stem}")
    def queue_entry(stem: str):
        if not _STEM.match(stem) or not queue_path.exists():
            raise HTTPException(404, f"no seed-queue entry {stem}")
        for e in json.loads(queue_path.read_text(encoding="utf-8")).get("entries") or []:
            if e.get("stem") == stem:
                return {"path": "data/seed_queue.json", "entry": e}
        raise HTTPException(404, f"no seed-queue entry {stem}")

    return app
