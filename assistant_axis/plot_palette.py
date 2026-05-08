"""Per-slot colour palette for the 8-slot Qwen-3 layout.

Adopted May 2026 after the PCA-scree-tail analysis revealed three
structurally-distinct slot groups:

* **Slot 0** (body-mean) sits alone with a far more concentrated
  spectrum than any header slot.  Rendered in **black** to mark it
  as semantically distinct from the chat-template scaffold.

* **Slots 2, 3, 5, 7** (the "regular-text cluster": ``assistant`` +
  the three ``\\n``/``\\n\\n`` newline-rich tokens) have moderate
  PCA-tail variance and form the primary candidate pool for the
  project's working-slot default (per the May 2026 OOO + tail
  analyses).  Rendered on the **plasma** colormap with **slot 7 at
  the dark-purple end**, sweeping through magenta/red/orange to
  yellow at slot 2.  This puts the latest slot in the chat template
  (``\\n\\n (post)``, immediately before the model's response) at
  the cool end and the earliest of the cluster (``assistant``) at
  the warm end.

* **Slots 1, 4, 6** (the "special-token cluster": ``<|im_start|>``,
  ``<think>``, ``</think>``) have higher PCA-tail variance -- their
  representations are spectrally more diffuse, consistent with these
  being unique chat-template markers.  Rendered on the **winter**
  colormap with **slot 6 at the pure-blue end**, sweeping through
  cyan to green at slot 1.

Use this convention everywhere a plot encodes slot identity by
colour, EXCEPT for plots that use colour to encode *slot pairs*
(e.g. ``all_roles_pairwise_slots.py``), which use a different
two-colormap convention -- see that script's docstring.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


# Group memberships, derived from the May 2026 cluster analyses.
_BODY_SLOTS = (0,)
_REGULAR_TEXT_SLOTS = (2, 3, 5, 7)   # assistant + 3 newline-rich slots
_SPECIAL_MARKER_SLOTS = (1, 4, 6)    # <|im_start|>, <think>, </think>


def slot_color(slot: int) -> tuple[float, float, float, float]:
    """Return the RGBA colour for a given slot index in the 8-slot layout.

    Convenience for code that processes one slot at a time; equivalent
    to ``slot_colors_8()[slot]`` but indexes into the canonical
    palette directly.

    For 4-slot data (Christina-headers etc.) this still works:
    slots 0, 1, 2, 3 each have their canonical colour assigned by
    the 8-slot mapping (slot 0 = black, 1 = green, 2 = yellow,
    3 = orange).  Out-of-range indices raise ``IndexError``.
    """
    return slot_colors_8()[slot]


def slot_colors_8() -> list[tuple[float, float, float, float]]:
    """Return the canonical 8-slot colour palette as a list indexed by
    slot index.

    Length-8 list.  See module docstring for the colour convention.
    Subsequent calls return the same list (recomputed cheaply each
    time).
    """
    colors: list[tuple[float, float, float, float] | None] = [None] * 8

    # Slot 0: body-mean, black.
    colors[0] = (0.0, 0.0, 0.0, 1.0)

    # Slots 2/3/5/7 on plasma, slot 7 at the dark-purple (low-value)
    # end.  Order is descending (7 -> 5 -> 3 -> 2) so slot 7 gets
    # plasma(0.05) and slot 2 gets plasma(0.90).
    plasma_pts = np.linspace(0.05, 0.90, 4)
    for plasma_idx, slot in enumerate((7, 5, 3, 2)):
        colors[slot] = tuple(plt.cm.plasma(plasma_pts[plasma_idx]))

    # Slots 1/4/6 on winter, slot 6 at the pure-blue (low-value) end.
    # Order descending (6 -> 4 -> 1).
    winter_pts = np.linspace(0.0, 1.0, 3)
    for winter_idx, slot in enumerate((6, 4, 1)):
        colors[slot] = tuple(plt.cm.winter(winter_pts[winter_idx]))

    # Defensive: every slot 0..7 should now have a colour.
    assert all(c is not None for c in colors), \
        f"slot_colors_8() left None entries: {colors}"
    return colors  # type: ignore[return-value]


def slot_colors(num_slots: int) -> list[tuple[float, float, float, float]]:
    """Return the per-slot palette truncated to the first ``num_slots``
    entries.

    For ``num_slots <= 8`` this slices the canonical 8-slot palette;
    for ``num_slots > 8`` (not currently used in the project) it
    falls back to the matplotlib default cycle for the extra slots.
    """
    base = slot_colors_8()
    if num_slots <= 8:
        return base[:num_slots]
    extra = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    extras_needed = num_slots - 8
    extra_rgba = [
        tuple(int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5)) + (1.0,)
        for c in extra[:extras_needed]
    ]
    return base + extra_rgba  # type: ignore[return-value]
