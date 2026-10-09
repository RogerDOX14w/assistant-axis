# Probing one word (or a few): its sense, its gloss, and whether the corpus already has it

Written 2026-10-09 for anyone in this repository (an agent or Roger) who wants to put one or a few words through
the trait-gap tools by hand, outside a generator run.  Example: Roger's question on
[savage](../../data/traits/instructions/savage.json) (W3 E3): what is its most common person sense, and does that
sense duplicate a corpus trait?  Terms are in the [glossary](./glossary.md).

The three steps, and what they cost for one word (measured on savage, live):

| step | tool | models | cost |
|---|---|---|---|
| 1. the sense: ranked readings of the bare word, Haiku's first thought | [traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py) (M1, the split filter) | Haiku 5.5 for every step; Sonnet 5.5 only for the second opinion on a sample, which one word does not trigger | $0.003 (the printed estimate, $0.018, counts a second opinion that did not run) |
| 2. the gloss: one sentence for the accepted person sense | the same run (its gloss step) | Haiku 5.5 | included above |
| 3. the novelty check: nearest corpus traits, overlap readings, covered / new / grey | [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) `score` (M3) | OpenAI text-embedding-3-large for the gloss; Haiku 5.5 for the relation call; Sonnet 5.5 for the overlap call on each neighbour in turn; Opus 5.5 re-reads where the rule sends it | $0.016 (embeddings $0.003, Sonnet $0.013; Opus was not needed) |

So about two cents a word, live.  For dozens of words the same commands take `--transport batches` (half price,
minutes to an hour).

## Keep probes out of the registry: use a scratch registry

The [candidate registry](./glossary.md) (`data/candidates/registry.jsonl`, git-ignored, one per checkout) is
append-only, and the review tools show every row in it.  **A probe goes in a scratch registry instead**: all three
tools take `--registry PATH`, and the two that write run directories take `--out-root DIR`.  Then nothing touches the
real registry or `data/candidates/filter/` and `data/candidates/novelty/`.  There is no clean way to delete a row
from the real registry once added, so do not probe there.  If a row really must go in, submit it with
`--generator probe --run-id <date>_<what>`, so that `gap_registry.py report --generator` can tell it apart.

**Where to run.**  The tools read the corpus from `data/traits/instructions/` in the checkout they run in (or
`--data-dir`).  So a probe in the main checkout sees uncommitted trait files as well; that is usually what you want.
A paid run on a working tree with uncommitted changes is refused unless you pass `--allow-dirty`.  To probe against
the committed corpus alone, run from a clean worktree, as savage was.

**A word that is already a corpus trait** (re-examining savage, say) must be hidden from the corpus in step 3.
Otherwise it matches itself by exact label.  `--hide FILE` takes a JSON file `{"hidden": ["savage"]}` and scores
against the corpus without those traits (left out of the search, the expansion and the exact-label check).  A
`--hide` run never writes any registry; its result is only in its run directory.

## The commands

The scratch directory: anything under `$TMPDIR`, which is cleared on reboot, so copy out what you want to keep.

```bash
S="$TMPDIR/probe_savage"; mkdir -p "$S"
echo '{"surface": "savage"}' > "$S/in.jsonl"          # one line per word
echo '{"hidden": ["savage"]}' > "$S/hidden.json"     # only if the word is already a corpus trait

# 0. Submit to the scratch registry (no call).  --registry goes before the subcommand here.
uv run python data_analysis/gap_generation/gap_registry.py --registry "$S/registry.jsonl" \
    submit --file "$S/in.jsonl" --generator probe --run-id savage_w3e3

# 1 and 2. The filter: sense, established, vague, kind, gloss, alignment, descriptors.  Keys are <word>#1.
uv run python data_analysis/gap_generation/traithood_filter.py --batch-id probe_savage --keys 'savage#1' \
    --registry "$S/registry.jsonl" --out-root "$S" --transport live --budget-usd 0.5   # [--allow-dirty]

# 3. The novelty check of the gloss against the corpus (drop --hide for a word not in the corpus).
uv run python data_analysis/gap_generation/novelty_score.py score --batch-id probe_savage_m3 --keys 'savage#1' \
    --registry "$S/registry.jsonl" --out-root "$S" --hide "$S/hidden.json" --transport live --budget-usd 0.5
```

Each command takes `--dry-run`, which prints the estimate and the prompts as sent, with no call.  `--budget-usd` is
a hard cap.  A batch id is used once: a second run under the same id needs `--resume` or `--overwrite`.

## What each step writes, and where to read it

**Step 1 and 2**, in `$S/filter/probe_savage/`:
- `results.jsonl` holds one row per word.  Under `filter`:
  - `sense.first_thought` and `first_thought_said_of`: Haiku's first association, and whether it is said of people;
  - `sense.readings`: the senses ranked (`primary` or `secondary`), each primary reading with its `established`, `vague` and `kind` answers and their reasons;
  - `person_senses`, `judged_sense` and `verdict` (`trait`, a holding list, or turned away), with `reason`;
  - `region` and `alignment` (0-3) of the gloss.
- `responses.jsonl` holds every call as sent and received; `usage.json`, `run.json` and `summary.json` hold the cost and settings.
- The scratch registry's row gains the filter block and the **gloss** (its `gloss` field, one sentence in "This means ..." form).

**Step 3**, in `$S/novelty/probe_savage_m3/`:
- `decisions.md` is the readable table: decision, covered by, cut-off, deciding reading, gloss.
- `results.jsonl` holds, under `novelty.listed`, the nearest corpus traits (and seed-queue entries) with cosine, rank, how each was found (retrieved by cosine, or expanded as a partner of one) and the relation call's answer (similar, opposed, unrelated).
- `readings.jsonl` has one line per overlap reading in walk order: the neighbour, Sonnet's 0-4 reading with its reason, Opus's where asked, and the outcome.
- `usage.json` and `run.json`.

**The decision.**
- **Covered by X**: some neighbour read at or above the cut-off.  The cut-off is 3 when the gloss is far from alignment (alignment 0 or 1) and 4 when near it (2 or 3).
- **New**: nothing reached the cut-off.
- **Grey**: a review flag, such as an unparsed answer, or both ends of a pair read similar.

The overlap scale ([overlap_concept.md](./rubrics/overlap_concept.md)):
- 4: the same concept;
- 3: the same concept, different scope or degree;
- 2: overlapping concepts;
- 1: related but distinct;
- 0: different;
- or "opposite".

A quick printout of the essentials:

```bash
uv run python - "$S" <<'EOF'
import json, sys; S = sys.argv[1]
for l in open(f"{S}/filter/probe_savage/results.jsonl"):
    f = json.loads(l)["filter"]; s = f["sense"]
    print(f["verdict"], "| first thought:", s["first_thought"], "(of", s["first_thought_said_of"] + ")")
    for r in s["readings"]: print("  ", r["rank"], "-", r["reading"], "|", r.get("kind"))
rows = {}                                    # the registry is a log: the last line of a key is its current row
for l in open(f"{S}/registry.jsonl"): r = json.loads(l); rows[r["key"]] = r
for k, r in rows.items(): print(k, "gloss:", r.get("gloss"))
for l in open(f"{S}/novelty/probe_savage_m3/readings.jsonl"):
    r = json.loads(l); o = r.get("opus") or {}
    print(f"  {r['stem']:24} cos {r['cosine']:.2f} {r['relation']:9} S{r['sonnet']['value']}"
          + (f" O{o.get('value')}" if o else "") + f"  -> {r['decision']}")
EOF
```

## The worked example: savage (2026-10-09)

Run on the committed corpus at `a699ab4` (911 traits) with savage hidden; $0.019 in all.

**Filter (step 1):** verdict **trait**; Haiku's first thought "fierce, brutal, violent", said of people.  The readings:
1. **primary**: "violent, brutal and fierce in nature or conduct" (well known; a trait: "a standing disposition toward violent, brutal conduct"; noted as fitting many in different ways);
2. secondary: "wild, uncivilized, lacking refinement";
3. secondary: "harshly critical or scathing in manner" (the corpus file's present sense);
4. secondary: "a member of a people once labelled uncivilized".

The gloss's alignment score is 3 (serious harm to people), so the cut-off near alignment is 4.

**Gloss (step 2):** "This means meeting opposition with brutal, unrestrained force, and carrying out one's conduct in
a fierce, violent manner that shows no mercy toward anyone in one's path."

**Novelty (step 3):** **new**.  Every overlap reading came from Sonnet; none sent Opus a re-read:

| neighbour | cosine | relation | overlap |
|---|---|---|---|
| [unyielding](../../data/traits/instructions/unyielding.json) | 0.33 | unrelated | 1 |
| [harsh](../../data/traits/instructions/harsh.json) | 0.33 | similar | 1 |
| [aggressive](../../data/traits/instructions/aggressive.json) | 0.32 | similar | 2 |
| [ruthless while playing](../../data/traits/instructions/ruthless_while_playing.json) | 0.30 | unrelated | 1 |
| [brave](../../data/traits/instructions/brave.json) | 0.28 | opposed | 0 |
| [bold](../../data/traits/instructions/bold.json) | 0.27 | unrelated | 0 |
| [confrontational](../../data/traits/instructions/confrontational.json) | 0.24 | similar | 1 |
| [unforgiving](../../data/traits/instructions/unforgiving.json) | 0.24 | similar | 1 |
| [cowardly](../../data/traits/instructions/cowardly.json) | 0.11 | opposed | 0 |

[cruel](../../data/traits/instructions/cruel.json) and [hostile](../../data/traits/instructions/hostile.json) were not
among the ten nearest by cosine, so they were not read.  The brutal-violence sense sits in a gap: the nearest corpus
traits are about severity, aggression or confrontation, not violent force.
