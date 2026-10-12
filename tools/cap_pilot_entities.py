#!/usr/bin/env python3
"""Build the entity list of the response-length cap pilot.

The pilot (reports/pipeline/plan_max_tokens_pilot.md, walk-through P6,
2026-10-12) generates 64 entities at four caps (256 / 512 / 768 / 1024) and
compares them with tools/cap_pilot_compare.py.  This script picks the 64 once,
with a recorded seed, so the pilot is reproducible:

* **roles** (20): the 8 roles whose recorded responses run longest (median
  response length in characters in the 8slot tree, the plan's "narrative"
  roles), then 12 drawn at random from the rest;
* **traits** (20) drawn at random, plus **verbose** and **concise**, the known
  outliers (Roger, 2026-10-12), reported on their own;
* **combinations** (20) drawn at random from the W15 grid (the top 30 x 30 of
  data/goal_roles_and_traits.json): 10 goal-role x non-goal-trait (``r_``)
  and 10 non-goal-role x goal-trait (``t_``), plus ``r_angel__verbose`` and
  ``r_angel__concise``, reported on their own (Roger: angel, a role with no
  length tendency of its own; verbose is 52nd of the 54 non-goal traits, so
  the pilot's step 1 runs with ``--non_goal_count 54``).

Excluded from every draw: ``default``; the stems that are both a role and a
trait (one responses directory per cap holds every type, so a name of both
kinds would collide); and, from the random strata, the outliers and any
combination with verbose or concise.

Writes reports/pipeline/cap_pilot_entities.json (``--output``):
``{"seed", "created_at", "builder", "goal_file_sha256", "strata": {...},
"by_type": {"role": [...], "trait": [...], "combination": [...]},
"all": [...], "narrative_median_chars": {...}}``.  ``by_type`` is what step 1
(``--roles``; roles need ``--roles_only``) and step 3 (``--entity_type``) take.

No API call, no model.  Usage (from the repository root)::

    uv run python tools/cap_pilot_entities.py            # seed 20261012
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SEED = 20261012
DEFAULT_OUTPUT = REPO / "reports" / "pipeline" / "cap_pilot_entities.json"
DEFAULT_LENGTHS_TREE = REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot" / "roles" / "responses"
OUTLIER_TRAITS = ("verbose", "concise")
OUTLIER_ROLE = "angel"
N_NARRATIVE, N_ROLES, N_TRAITS, N_COMBOS = 8, 20, 20, 20
GRID_COUNT = 30


def median_response_chars(responses_file: Path) -> float:
    """Median length in characters of a response file's assistant turns."""
    lengths = []
    with open(responses_file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            text = next((m["content"] for m in rec.get("conversation", [])
                         if m.get("role") == "assistant"), "")
            lengths.append(len(text))
    return statistics.median(lengths) if lengths else 0.0


def w15_grid(goal_file: Path, count: int = GRID_COUNT) -> tuple[list[str], list[str]]:
    """The ``r_`` and ``t_`` names of the top ``count`` x ``count`` grid."""
    g = json.loads(goal_file.read_text())
    r = [f"r_{role}__{trait}" for role in g["roles"]["goal"][:count]
         for trait in g["traits"]["non_goal"][:count]]
    t = [f"t_{role}__{trait}" for role in g["roles"]["non_goal"][:count]
         for trait in g["traits"]["goal"][:count]]
    return r, t


def build(*, seed: int, roles_dir: Path, traits_dir: Path, goal_file: Path,
          lengths_tree: Path) -> dict:
    roles = {p.stem for p in roles_dir.glob("*.json")}
    traits = {p.stem for p in traits_dir.glob("*.json")}
    both = roles & traits
    for need, have, kind in ((OUTLIER_TRAITS, traits, "trait"), ((OUTLIER_ROLE,), roles, "role")):
        missing = [n for n in need if n not in have]
        if missing:
            raise SystemExit(f"cap_pilot_entities: {kind} file(s) missing: {missing}")
    g = json.loads(goal_file.read_text())
    if OUTLIER_ROLE not in g["roles"]["goal"][:GRID_COUNT]:
        raise SystemExit(f"cap_pilot_entities: {OUTLIER_ROLE} is not among the top {GRID_COUNT} "
                         f"goal roles of {goal_file}")
    for t in OUTLIER_TRAITS:
        if t not in g["traits"]["non_goal"]:
            raise SystemExit(f"cap_pilot_entities: {t} is not a non-goal trait in {goal_file}")
    rng = random.Random(seed)

    # Roles: the 8 longest by recorded median length, then 12 at random.
    role_pool = sorted(roles - both - {"default"})
    medians = {}
    for stem in role_pool:
        f = lengths_tree / f"{stem}.jsonl"
        if f.exists():
            medians[stem] = median_response_chars(f)
    if len(medians) < N_NARRATIVE:
        raise SystemExit(f"cap_pilot_entities: only {len(medians)} roles have responses in "
                         f"{lengths_tree}")
    narrative = sorted(medians, key=lambda s: (-medians[s], s))[:N_NARRATIVE]
    rest = [s for s in role_pool if s not in narrative]
    roles_random = sorted(rng.sample(rest, N_ROLES - N_NARRATIVE))

    trait_pool = sorted(traits - both - set(OUTLIER_TRAITS))
    traits_random = sorted(rng.sample(trait_pool, N_TRAITS))

    r_names, t_names = w15_grid(goal_file)

    def ok(name: str) -> bool:
        return not any(name.endswith(f"__{t}") for t in OUTLIER_TRAITS)

    combos = sorted(rng.sample([n for n in r_names if ok(n)], N_COMBOS // 2)
                    + rng.sample([n for n in t_names if ok(n)], N_COMBOS - N_COMBOS // 2))
    combo_outliers = [f"r_{OUTLIER_ROLE}__{t}" for t in OUTLIER_TRAITS]

    strata = {
        "roles_narrative": narrative,
        "roles": roles_random,
        "traits": traits_random,
        "traits_outliers": list(OUTLIER_TRAITS),
        "combinations": combos,
        "combinations_outliers": combo_outliers,
    }
    by_type = {"role": narrative + roles_random,
               "trait": traits_random + list(OUTLIER_TRAITS),
               "combination": combos + combo_outliers}
    all_names = [n for names in by_type.values() for n in names]
    assert len(all_names) == len(set(all_names)) == 64, len(all_names)
    return {
        "seed": seed,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "builder": "tools/cap_pilot_entities.py",
        "plan": "reports/pipeline/plan_max_tokens_pilot.md",
        "goal_file": str(goal_file.relative_to(REPO)) if goal_file.is_relative_to(REPO) else str(goal_file),
        "goal_file_sha256": hashlib.sha256(goal_file.read_bytes()).hexdigest(),
        "excluded_collision_names": sorted(both),
        "strata": strata,
        "by_type": by_type,
        "all": all_names,
        "narrative_median_chars": {s: medians[s] for s in narrative},
        "role_median_chars_quartiles": [round(q) for q in statistics.quantiles(medians.values(), n=4)],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--roles_dir", type=Path, default=REPO / "data" / "roles" / "instructions")
    ap.add_argument("--traits_dir", type=Path, default=REPO / "data" / "traits" / "instructions")
    ap.add_argument("--goal_file", type=Path, default=REPO / "data" / "goal_roles_and_traits.json")
    ap.add_argument("--lengths_tree", type=Path, default=DEFAULT_LENGTHS_TREE,
                    help="Response files the narrative roles are ranked from (default: the "
                         "8slot tree's roles/responses)")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing list")
    args = ap.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"{args.output} exists (the pilot's list is built once); --force to rebuild",
              file=sys.stderr)
        return 1
    result = build(seed=args.seed, roles_dir=args.roles_dir, traits_dir=args.traits_dir,
                   goal_file=args.goal_file, lengths_tree=args.lengths_tree)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {args.output}: {len(result['all'])} entities, seed {args.seed}")
    for k, v in result["strata"].items():
        print(f"  {k} ({len(v)}): {', '.join(v)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
