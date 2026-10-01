# Notes on usage.json

- 2026-10-01, round 2: a run started with the `dup` representation embedded 663 new texts per model (OpenAI: 3 calls) and was stopped before it finished (the blinded comparisons had to be redrawn first).  Its usage record was lost when the run's partial outputs were reverted.  The OpenAI charge was added back to [usage.json](./usage.json) as an estimate: 3 calls, 27,512 input tokens (21,163 words at 1.3 tokens per word; the texts are in the embedding cache), about $0.0036.  The local models' calls from that run (free) are not in the record.
