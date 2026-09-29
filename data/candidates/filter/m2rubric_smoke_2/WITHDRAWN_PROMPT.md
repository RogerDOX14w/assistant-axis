# Withdrawn intermediate prompt

This smoke run (one of `m2rubric_smoke_1` to `_3`, all at commit `7f7c633`) used an intermediate rubric v2
classifier prompt, sha256 `ba7a4316dccd97c39845fe3cfbc22481c83beb7e116f045726f724b012585eb4`, which asked
for a `primary_use` field (decision 11) and derived the polysemy flag from it.  That field was withdrawn on
2026-09-29 (item 7 held); the committed rubric v2 classifier prompt is
`2b5b298ed6b44745eae5358325cfaea93324b8e7ac90a2cb691dd12440d2fedb`, which asks for `trait_sense_rank` in
the v1 wording instead.  The probe prompt (`0785cd07...`) is the committed one.

Use these rows for parse rate, cost, reason length, gloss, membership, state/physical routing and rescue
checks only.  Their `primary_use` and `polysemy` values are not what the committed rubric produces, and
the rows carry `trait_sense_rank: null`.
