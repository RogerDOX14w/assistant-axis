"""R2 of the trait-gap review tooling: the review app (``reports/trait_gap_generation/coding_plan_review.md``, section 3).

* :mod:`.decisions`: the append-only decision log (``data/candidates/review/<batch_id>/decisions.jsonl``), its replay
  into the review state (groups, handled terms, the queue, the cards the page shows), ``apply`` into the registry's
  review blocks and the seed queue, and the rename shortlist's review merges.  No web framework is imported here.
* :mod:`.server`: the FastAPI app over that state (routes ``/api/queue``, ``/api/group/{id}``, ``/api/term/{key}``,
  ``/api/action``, ``/api/status``, ``/api/find``; the page under ``/static``; corpus files read-only under
  ``/files``).
* ``static/``: the page (``index.html``, ``app.js``, ``style.css``; no build step, no framework).

The CLI is ``data_analysis/gap_generation/review_app.py`` (``serve``, ``status``, ``apply``).
"""
