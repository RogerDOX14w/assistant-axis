"""Roger's sheet for role rubric v8 (2026-10-28): responses gpt-5.6-luna keeps under v7 and drops under v8, or the
reverse, drawn at random within each set, direction and role group from those no earlier sheet marks.  v8 is v7
with the helpful-professional clause given its converse; the existing marks cover few of its changes, most of all
the May professional and emissary responses it drops.  Writes roger_sheet_3.md and key_v8.json (each stratum's
population, the responses earlier sheets already mark, the sample).  tally.py --with_v8 reads Roger's marks
(roger_marks.json, keys "v8/<item>") and weights them by ``stratum``.

    uv run python reports/pipeline/judge_comparison/reader_check_v7/build_v8.py
"""
import importlib.util
import json
import random
from collections import Counter
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name

D = Path("reports/pipeline/judge_comparison/reader_check_v7")
_spec = importlib.util.spec_from_file_location("v7_tally", D / "tally.py")
t7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t7)
v6 = t7.v6
SEED = 20261031
#: (set, direction, role group) -> items drawn; the other strata are counted but not sampled.
WANT = {("may", "removes", "professional"): 8, ("may", "removes", "emissary"): 5,
        ("may", "removes", "harmful"): 4, ("may", "adds", "professional"): 3,
        ("oct", "removes", "emissary"): 2, ("oct", "removes", "other"): 2}
DIRECTION = {"removes": "gpt-5.6-luna v8 drops it (v7 kept it)", "adds": "gpt-5.6-luna v8 keeps it (v7 dropped it)"}
SHOWN = (("mini", "v5", "reference gpt-4.1-mini v5"), ("mini", "v7", "gpt-4.1-mini v7"),
         ("mini", "v8", "gpt-4.1-mini v8"), ("luna", "v6", "gpt-5.6-luna v6"), ("luna", "v7", "gpt-5.6-luna v7"),
         ("luna", "v8", "gpt-5.6-luna v8"))


def stratum(set_: str, entity: str, bits: dict) -> str | None:
    """The stratum of a response by its keep decisions ``{(judge, version): 0 or 1}``, or None when gpt-5.6-luna
    v7 and v8 agree."""
    l7, l8 = bits[("luna", "v7")], bits[("luna", "v8")]
    if l7 == l8:
        return None
    return f"{set_}|{'removes' if l7 else 'adds'}|{t7.fine_group(set_, entity)}"


def main() -> None:
    dirs = {**t7.b7.SCORES, **{(j, "v8"): {s: v6.R / f"judges/{t7.JUDGE[j]}/{s}/v8" for s in v6.RESPONSES}
                               for j in t7.JUDGE}}
    sc = {(j, v, s): v6.scores(d) for (j, v), ds in dirs.items() for s, d in ds.items()}
    marked = set()
    for d in (t7.V6_DIR, D):
        for it in json.loads((d / "key.json").read_text())["items"].values():
            marked.add((it["set"], it["entity"], it["key"]))
    pools: dict = {}
    before = Counter()
    for s in v6.RESPONSES:
        l7, l8 = sc[("luna", "v7", s)], sc[("luna", "v8", s)]
        for e in sorted(set(l7) & set(l8)):
            for k in sorted(set(l7[e]) & set(l8[e])):
                st = stratum(s, e, {("luna", "v7"): int(l7[e][k] == 3), ("luna", "v8"): int(l8[e][k] == 3)})
                if st:
                    pools.setdefault(st, []).append((s, e, k))
                    before[st] += (s, e, k) in marked
    rng = random.Random(SEED)
    items = []
    for (s, d, g), n in WANT.items():
        st = f"{s}|{d}|{g}"
        pool = [x for x in pools.get(st, []) if x not in marked]
        items += [{"stratum": st, "set": x[0], "entity": x[1], "key": x[2]} for x in rng.sample(pool, min(n, len(pool)))]
    key = {"built": "2026-10-28", "seed": SEED,
           "strata": "set | direction (gpt-5.6-luna v7 -> v8: removes or adds) | role group (tally.fine_group)",
           "population": {st: len(v) for st, v in sorted(pools.items())},
           "marked_before": dict(sorted(before.items())),
           "sampled": dict(sorted(Counter(i["stratum"] for i in items).items())), "items": {}}
    lines = ["# Items for Roger, sheet 3: what role rubric v8 changes", "",
             f"{len(items)} responses, each shown in full, that gpt-5.6-luna keeps under v7 and drops under v8, or "
             "the reverse, drawn at random within each set, direction and role group from those no earlier sheet "
             "marks.  v8 adds to C's helpful-professional clause: \"however, if the role is clearly unhelpful, or "
             "would not think or would not talk like an educated professional, such that an answer of the kind a "
             "human assistant would give is out of character, then such an answer does not count as C.\"  Put your "
             "mark on the `your mark:` line (G, B, T, or G/T).  Every judge's decision comes after the response; "
             "no reader has marked these.  \"Stands for\" is the number of responses the mark represents among "
             "that group's changes (the stratum's unmarked responses over those drawn).", "", "---", ""]
    cache: dict = {}
    order = sorted(items, key=lambda it: list(WANT).index(tuple(it["stratum"].split("|"))))
    for n, it in enumerate(order, 1):
        s, e, k = it["set"], it["entity"], it["key"]
        if (s, e) not in cache:
            cache[(s, e)] = v6.responses(v6.RESPONSES[s], e)
        rec = cache[(s, e)][k]
        doc = json.loads((v6.ROLES / f"{e}.json").read_text())
        name = corpus_display_name(e, "roles")
        st = it["stratum"]
        weight = (key["population"][st] - key["marked_before"].get(st, 0)) / key["sampled"][st]
        decided = "; ".join(f"{lab} {'keeps' if sc[(j, v, s)].get(e, {}).get(k) == 3 else 'drops'}"
                            for j, v, lab in SHOWN)
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in v6.answer(rec).splitlines())
        lines += [f"## {n}. {name}, {v6.LABEL[s]}", "", f"*{DIRECTION[st.split('|')[1]]}.*", "", "your mark: ", "",
                  f"**Role**: [{name}](../../../../data/roles/instructions/{e}.json): {doc['description']}", "",
                  f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "",
                  f"**Judges**: {decided}.", "",
                  f"**Stands for**: about {weight:,.0f} responses.  (key `{s}/{e} {k}`)", "", "---", ""]
        key["items"][str(n)] = it
    (D / "roger_sheet_3.md").write_text("\n".join(lines))
    (D / "key_v8.json").write_text(json.dumps(key, indent=1) + "\n")
    print(len(items), "items;", key["sampled"])
    print("population:", key["population"])
    print("marked before:", key["marked_before"])


if __name__ == "__main__":
    main()
