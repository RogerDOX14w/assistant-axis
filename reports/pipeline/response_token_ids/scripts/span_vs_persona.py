"""Does pooling the leaked thinking in move a leaker further from the average
persona, and along its own direction?  For each leaker, with the October
centroid c (mean of every October trait and role vector but the default):
    o_range = v_ids - c,  o_turn = v_turn - c,  d_span = v_turn - v_ids
reports |o_turn| / |o_range|, cos(d_span, o_range), and the component of
d_span along o_range as a fraction of |o_range|; then, on the axes with the
largest common shift, where the leaker already sits (z of its range
projection among the October entities) and the shift in σ.
    uv run python span_vs_persona.py <sample> <october cache npz> <axis_projection_shift.json> [axes...]
"""
import json
import sys
from pathlib import Path

import numpy as np

sample, cache, shift_json = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
axes_of_interest = sys.argv[4:] or ["decisive_vs_indecisive", "concise_vs_verbose", "confident_vs_uncertain",
                                    "progressive_vs_conservative", "opaque_vs_transparent", "innovative_vs_traditional",
                                    "descriptive_vs_prescriptive"]
sys.path.insert(0, str(sample / "logs"))
import axis_projection_shift as aps  # noqa: E402

with np.load(cache, allow_pickle=False) as z:
    meta = json.loads(str(z["meta"]))
    arr = z["arr"]                                   # (N, S, L, H)
    keys = z["keys"].tolist()
slots, layers = meta["slots"], meta["layers"]
c = arr.mean(0)                                      # (S, L, H)
print(f"October centroid over {len(keys)} vectors; slots {slots}, layers {layers}")
sh = json.loads(shift_json.read_text())
leakers = [e for e in sh["entities"] if sh["entities"][e]["group"] == "heavy leaker"]
si = slots.index(0)
for li, L in enumerate(layers):
    print(f"\n=== slot 0, layer {L} ===")
    print(f"{'entity':26} {'|o_range|':>9} {'|o_turn|/|o_range|':>18} {'cos(d,o)':>9} {'along o, % of |o|':>18} {'|d|/|o|':>8}")
    rows = []
    for e in leakers:
        v_ids = aps.load_slice(sample / "vec_ids" / f"{e}.pt", slots, layers)[si, li]
        v_turn = aps.load_slice(sample / "vec_turn" / f"{e}.pt", slots, layers)[si, li]
        o = v_ids - c[si, li]
        d = v_turn - v_ids
        no, nd = np.linalg.norm(o), np.linalg.norm(d)
        ratio = np.linalg.norm(o + d) / no
        cos = float(d @ o / (nd * no))
        along = float(d @ o / no) / no
        rows.append((e, no, ratio, cos, along, nd / no))
        print(f"{e:26} {no:9.2f} {ratio:18.4f} {cos:9.3f} {100 * along:18.2f} {nd / no:8.4f}")
    cs = [r[3] for r in rows]
    print(f"  cos(d_span, o_range): median {np.median(cs):.3f}, range {min(cs):.3f} to {max(cs):.3f}; "
          f"|o_turn|/|o_range|: median {np.median([r[2] for r in rows]):.4f}, range {min(r[2] for r in rows):.4f} to {max(r[2] for r in rows):.4f}")
    # Where the leakers already sit on the axes with the largest common shift.
    print(f"\n  position on the axes with the largest common shift (z of the range projection among the October entities; shift in σ):")
    hdr = f"  {'entity':26}" + "".join(f" {a.split('_vs_')[0][:8]}/{a.split('_vs_')[1][:8]:>9}" for a in axes_of_interest)
    print(hdr)
    for e in leakers:
        ent = sh["entities"][e]
        cells = []
        for a in axes_of_interest:
            k = sh["axes"].index(a)
            spread = sh["spread"][a]
            z = (ent["projections"]["ids"][a][si][li] - spread["mean"][si][li]) / spread["std"][si][li]
            s = ent["shifts"]["ids-turn"][k][si][li]
            cells.append(f" {z:+6.2f} ({s:+.2f})")
        print(f"  {e:26}" + "".join(f"{c_:>19}" for c_ in cells))
    print("  (z > 0 is toward the first-named pole; a negative shift moves toward the second-named pole)")
