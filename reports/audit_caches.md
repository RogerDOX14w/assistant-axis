# Cache provenance audit

Roots: `/Users/roger/Documents/GitHub/assistant-axis/roger`

Total JSONs scanned: **2370**.

## Summary by status

| Status | Count |
|---|---:|
| current | 1 |
| stale_direct | 0 |
| stale_transitive | 0 |
| legacy | 2369 |

## By producing script

| Script | current | stale_direct | stale_transitive | legacy | total |
|---|---:|---:|---:|---:|---:|
| `(unknown source)` | 0 | 0 | 0 | 2369 | 2369 |
| `results_analysis/whitening_k_peak_fit.py` | 1 | 0 | 0 | 0 | 1 |

## Legacy (2369)

JSONs without a ``_provenance`` envelope.  Either pre-migration caches, hand-written config (pair lists, manifests), or pipeline outputs (judge caches).  Audit can't say anything about them; downstream caches track their freshness via mtime/size only.
