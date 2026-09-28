# SMOKE TEST: prompt not hash-verified

This batch (a 10-row smoke test, $0.0096) ran from an uncommitted tree
(`0b7e784+dirty`) before prompt hashes were recorded (review_m1.md finding 10).
Its estimated system-prompt size (1,924 tokens) and per-call input tokens are
consistent with the text later committed as rubric v1 in 21453f8, which the
pilot used, but the text sent cannot be proven.  Treat it as a pre-release
smoke test, not as rubric v1 data.  Kept because it was paid for.
