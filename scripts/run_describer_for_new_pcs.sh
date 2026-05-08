#!/usr/bin/env bash
# Run infer_axis_description.py for each (PC × style) cell that's missing
# spec.json.  Prepares input_scores.json from post_shear_projection.json
# (just adds type info), then invokes the describer.
#
# Pre-req: launch_judge_runs.py with the new PCs has already populated
# axis_postshear.pt and post_shear_projection.json in each cell.

set -euo pipefail

cd "$(dirname "$0")/.."
SWEEP_DIR="roger/pc_axis_describer_sweep"
DATA_DIR="runpod_workspace/qwen/qwen-3-32b Roger 8slot"

# Build name → type map once (R for role, T for trait).
TYPE_MAP="$(mktemp)"
trap 'rm -f "$TYPE_MAP"' EXIT
for f in "$DATA_DIR"/roles/vectors/*.pt; do
    [ -e "$f" ] || continue
    name=$(basename "$f" .pt)
    [ "$name" = "default" ] && continue
    echo "$name R" >> "$TYPE_MAP"
done
for f in "$DATA_DIR"/traits/vectors/*.pt; do
    [ -e "$f" ] || continue
    name=$(basename "$f" .pt)
    [ "$name" = "default" ] && continue
    echo "$name T" >> "$TYPE_MAP"
done

PCS="${1:-3 6 12}"
STYLES="${2:-glossary inline}"

for pc in $PCS; do
    pc3=$(printf '%03d' "$pc")
    for style in $STYLES; do
        cell="$SWEEP_DIR/pc${pc3}_${style}"
        if [ -f "$cell/spec.json" ]; then
            echo "[skip] $cell/spec.json already exists"
            continue
        fi
        if [ ! -f "$cell/post_shear_projection.json" ]; then
            echo "[error] $cell/post_shear_projection.json missing — run launch_judge_runs.py first"
            exit 1
        fi
        echo "[$cell] preparing input_scores.json..."
        # Convert {name: score} → [{name, type, score}, ...]
        uv run python -c "
import json, sys
m = {}
for line in open('$TYPE_MAP'):
    n, t = line.strip().split()
    m[n] = t
proj = json.load(open('$cell/post_shear_projection.json'))
out = []
missing = []
for n, s in proj.items():
    if n in m:
        out.append({'name': n, 'type': m[n], 'score': float(s)})
    else:
        missing.append(n)
if missing:
    print(f'WARN: {len(missing)} entities missing type: {missing[:5]}', file=sys.stderr)
json.dump(out, open('$cell/input_scores.json', 'w'), indent=2)
print(f'wrote {len(out)} entries')
"
        echo "[$cell] running infer_axis_description.py (Opus, ~30-60s)..."
        uv run python -m results_analysis.infer_axis_description \
            --input "$cell/input_scores.json" \
            --output "$cell/spec.json" \
            --style "$style" \
            2>&1 | tail -8
        echo
    done
done

echo "All described.  Now run:"
echo "  uv run python -m results_analysis.pc_round_trip.launch_judge_runs --pcs 3,6,12 --skip_setup"
