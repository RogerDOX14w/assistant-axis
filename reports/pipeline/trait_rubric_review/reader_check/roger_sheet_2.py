"""Roger's second sheet (2026-10-28), blind: 40 low-tier responses, no judge decisions or reader marks shown.

  24  the two cells that carry the gpt-4.1-mini / gpt-5.6-luna difference in the hard traits, 3 per trait:
      "001" (only luna keeps: its additions) for harmful, deceitful, evil, avoidant;
      "110" (luna drops what mini keeps: its removals) for submissive, dishonest, obsessive, ethnocentric;
  10  the all-drop cell "000" (2,604 responses, 14 marked so far): one per trait, one more each for avoidant and
      submissive, the traits a refusal tweak would target;
   6  calibration: low-tier items the re-readers marked under the revised criteria, shown again blind.

New items get ids n1.. and are recorded in key_2.json with the same fields as key.json; calibration items keep
their key.json numbers.  Cells and items drawn from the pools of build.py, excluding everything already sampled.
Writes roger_sheet_2.md.  ``--collect`` reads the ``your mark:`` lines into roger_marks_2.json, which tally.py
applies after roger_marks.json.

    uv run python reports/pipeline/trait_rubric_review/reader_check/roger_sheet_2.py [--collect]
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name

D = Path("reports/pipeline/trait_rubric_review/reader_check")
sys.path.insert(0, str(D))
import build  # noqa: E402
import roger_sheet  # noqa: E402

SEED = 20261028 + 2
DARK = ("harmful", "deceitful", "evil", "avoidant")           # luna's additions, cell 001
STRICT = ("submissive", "dishonest", "obsessive", "ethnocentric")   # luna's removals, cell 110
PER_TRAIT = 3
ALL_DROP = {"avoidant": 2, "submissive": 2, "harmful": 1, "deceitful": 1, "evil": 1, "obsessive": 1,
            "dishonest": 1, "ethnocentric": 1}
N_CALIB = 6
INTRO = ("Forty responses from the eight hard traits.  Mark each on its `your mark:` line by "
         "[criteria.md](./criteria.md): G good data for the trait's vector, B below the line, T both defensible, "
         "? cannot tell; a note after the mark is welcome.  Nothing is shown about what any judge or reader "
         "decided, and the order is random.  A response ending in \"…\" was cut at the length limit, as the "
         "judge now sees it; judge what is there.")


def pools_low() -> dict:
    """``cell -> [(entity, key)]`` for the low tier, as build.py forms them (reference May, mini v3, luna v3)."""
    may = build.scores(build.MAY)
    m3 = build.scores(build.SCORES[("gpt-4.1-mini", "v3")]["low"])
    l3 = build.scores(build.SCORES[("gpt-5.6-luna", "v3")]["low"])
    out: dict = {}
    for e in sorted(set(m3) & set(l3)):
        if build.tier_of(e) != "low":
            continue
        for k in sorted(set(may[e]) & set(m3[e]) & set(l3[e])):
            cell = "".join(str(int(x[k] == 3)) for x in (may[e], m3[e], l3[e]))
            out.setdefault(cell, []).append((e, k))
    return out


def collect() -> None:
    roger_sheet.D = D
    src = D / "roger_sheet_2.md"
    out, notes, cur, blank = {}, {}, None, []
    for line in src.read_text().splitlines():
        m = re.match(r"^## \d+\. .*\(item (\w+)\)", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^your mark:\s*(\S*)(.*)", line)
        if m and cur:
            tok = m.group(1).upper().rstrip(",;:.")
            if not tok:
                blank.append(cur)
            elif tok in roger_sheet.MARK_FORMS:
                out[cur] = roger_sheet.MARK_FORMS[tok]
                notes[cur] = m.group(2).strip()
            else:
                raise SystemExit(f"item {cur}: cannot read the mark {m.group(1)!r}; add it to roger_sheet.MARK_FORMS")
            cur = None
    (D / "roger_marks_2.json").write_text(json.dumps({"items": out, "notes": notes, "blank": blank}, indent=1) + "\n")
    print(f"{len(out)} marks collected into roger_marks_2.json; no mark on {blank or 'none'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    args = ap.parse_args()
    if args.collect:
        collect()
        return
    rng = random.Random(SEED)
    key = json.loads((D / "key.json").read_text())
    items = key["items"]
    taken = {(it["entity"], it["key"]) for it in items.values() if it["set"] == "low"}
    roger = set(json.loads((D / "roger_marks.json").read_text())["items"])
    reread = json.loads((D / "reread_items.json").read_text())["items"]
    pools = pools_low()
    may = build.scores(build.MAY)
    sc = {(build.SHORT[j], v): build.scores(d["low"]) for (j, v), d in build.SCORES.items()}

    def draw(cell: str, entity: str, n: int) -> list:
        cands = [(e, k) for e, k in pools.get(cell, []) if e == entity and (e, k) not in taken]
        picks = rng.sample(cands, min(n, len(cands)))
        taken.update(picks)
        return [{"stratum": f"low|{cell}", "set": "low", "entity": e, "key": k, "tier": "low",
                 "scores": {"may": may[e][k], **{f"{s}_{v}": sc[(s, v)].get(e, {}).get(k)
                                                  for (s, v) in sc}}} for e, k in picks]

    new = []
    for e in DARK:
        new += draw("001", e, PER_TRAIT)
    for e in STRICT:
        new += draw("110", e, PER_TRAIT)
    for e, n in ALL_DROP.items():
        new += draw("000", e, n)
    calib_pool = sorted(i for i in reread if items[i]["tier"] == "low" and i not in roger)
    calib = rng.sample(calib_pool, min(N_CALIB, len(calib_pool)))
    key2 = {"built": "2026-10-28", "seed": SEED, "purpose": __doc__.split("\n\n")[0],
            "items": {f"n{j + 1}": it for j, it in enumerate(new)}, "calibration": calib}
    sheet_items = [(f"n{j + 1}", it) for j, it in enumerate(new)] + [(i, items[i]) for i in calib]
    rng.shuffle(sheet_items)

    # A rebuild keeps the marks already on the sheet (by item id); the draw is deterministic, so the items match.
    kept_marks: dict = {}
    if (D / "roger_sheet_2.md").exists():
        cur = None
        for line in (D / "roger_sheet_2.md").read_text().splitlines():
            m = re.match(r"^## \d+\. .*\(item (\w+)\)", line)
            if m:
                cur = m.group(1)
            elif cur and line.startswith("your mark:"):
                if line.strip() != "your mark:":
                    kept_marks[cur] = line
                cur = None
    cache: dict = {}
    lines = ["# Second sheet for Roger: the hard traits, blind", "", INTRO, "", "---", ""]
    for n, (i, it) in enumerate(sheet_items, 1):
        e, k = it["entity"], it["key"]
        if e not in cache:
            cache[e] = build.responses(build.SETS["low"][0], e)
        rec = cache[e][k]
        doc = json.loads((build.TRAITS / f"{e}.json").read_text())
        name = corpus_display_name(e, "traits")
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in build.answer(rec).splitlines())
        lines += [f"## {n}. {name} (item {i})", "", kept_marks.get(i, "your mark: "), "",
                  f"**Trait**: [{name}](../../../../data/traits/instructions/{e}.json): {doc['description']}", "",
                  f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "", "---", ""]
    (D / "roger_sheet_2.md").write_text("\n".join(lines))
    (D / "key_2.json").write_text(json.dumps(key2, indent=1) + "\n")
    from collections import Counter
    print(f"wrote roger_sheet_2.md: {len(sheet_items)} items;",
          dict(Counter(it["stratum"] for it in new)), "new;", len(calib), "calibration", calib)


if __name__ == "__main__":
    main()
