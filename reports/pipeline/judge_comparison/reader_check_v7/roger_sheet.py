"""Roger's sheet for the v6-or-v7 decision (2026-10-28): the marked items that weigh most on gpt-5.6-luna's
precision, and examples of the criteria questions the v7 readers raised.  Full role, question and response first,
then what each version of each judge decided, the readers' mark and note, and how many responses the mark stands
for in the tally.  Writes roger_sheet.md; with --sheet 2, roger_sheet_2.md: half of the readers' B and T marks
where gpt-5.6-luna v7 looks lenient (stances in October, virus and hacker in May), to compare the readers'
marking with Roger's there.

    uv run python reports/pipeline/judge_comparison/reader_check_v7/roger_sheet.py [--sheet 2]
"""
import argparse
import importlib.util
import json
import random
import re
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name

D = Path("reports/pipeline/judge_comparison/reader_check_v7")
_spec = importlib.util.spec_from_file_location("v7_tally", D / "tally.py")
t7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t7)
b7, v6 = t7.b7, t7.v6
# (sheet set, item, why it is here)
ITEMS = [
    ("v6", "20", "Weighs most of all marks on luna's precision; kept by both luna versions"),
    ("v6", "197", "Second heaviest; kept by both luna versions (emissary under luna v6 is at 88% precision)"),
    ("v6", "97", "Third heaviest; luna v7 keeps it, v6 drops it"),
    ("v7", "142", "Fourth heaviest; luna v7 keeps it, v6 drops it"),
    ("v7", "79", "Fifth heaviest; kept by both luna versions.  Also the thoroughness question below"),
    ("v7", "131", "Sixth heaviest; luna v7 keeps it, v6 drops it"),
    ("v6", "55", "Seventh heaviest; kept by both luna versions"),
    ("v7", "8", "Question: can thoroughness alone be a perfectionist's outlook? (readers: no)"),
    ("v7", "27", "Question: one sentence with two kinds of lapse, one lapse or two? (readers: two, so B)"),
    ("v7", "75", "Question: does criterion 5 (helpful professionals) cover technical roles such as a debugger? "
                 "Also a re-mark: G in the third round, T now"),
    ("v7", "18", "Question: a proofreader that proofreads the question and never answers it, G? (readers: G)"),
    ("v7", "100", "Question: is a generic answer from an emissary G under criterion 5? (readers: G for 30 or so "
                  "items like this)"),
]
ORDER = (("mini", "v5"), ("mini", "v6"), ("mini", "v7"), ("luna", "v6"), ("luna", "v7"))
LABEL = {("mini", "v5"): "reference gpt-4.1-mini v5", ("mini", "v6"): "gpt-4.1-mini v6",
         ("mini", "v7"): "gpt-4.1-mini v7", ("luna", "v6"): "gpt-5.6-luna v6", ("luna", "v7"): "gpt-5.6-luna v7"}


def notes(d: Path) -> dict:
    out = {}
    for p in sorted(d.glob("sheet_*.md")):
        cur = None
        for line in p.read_text().splitlines():
            m = re.match(r"^### (\d+)\s*$", line)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r"^mark:\s*(.*)", line)
            if m and cur:
                out[cur] = m.group(1).strip()
                cur = None
    return out


INTRO_1 = ("Twelve responses, each shown in full: the seven marks that weigh most on gpt-5.6-luna's precision "
           "estimate, then five examples of the criteria questions the v7 readers raised.")
INTRO_2 = ("Nineteen responses, each shown in full: half, drawn at random within each role group and reader mark, "
           "of the 38 the readers marked B or T among those gpt-5.6-luna v7 keeps for the perfectionist, the "
           "altruist, the other stances (October) and the virus and hacker (May), the groups where v7 looks "
           "lenient.  Your marks measure how the readers' B and T compare with yours there; the other half keep "
           "the readers' marks.")
INTRO_TAIL = ("  Put your mark on the `your mark:` line (G, B, T, or G/T); it replaces the readers' mark in the "
              "tally.  The judges' decisions, the readers' mark and the weight come after the response.  \"Stands "
              "for\" is the number of responses the mark represents in [tally.py](./tally.py): one over the chance "
              "that this response was drawn by either reading sample.")
#: Sheet 2: items drawn per role group (38 candidates: perfectionist 11, altruist 5, other stances 7, virus and
#: hacker 15), split across the readers' B and T in proportion.
SHEET2_N = {"perfectionist": 6, "altruist": 2, "stance, other": 3, "harmful": 8}
SHEET2_LABEL = {"perfectionist": "perfectionist", "altruist": "altruist", "stance, other": "other stance",
                "harmful": "virus or hacker"}
SHEET2_SEED = 20261030


def sheet2_items(sc: dict, keys: dict, marks: dict) -> list:
    """Half of the readers' B and T marks among gpt-5.6-luna v7's keeps in the stance and harmful groups, not
    yet marked by Roger, drawn within each group and mark, grouped by role group."""
    done = set(json.loads((t7.V6_DIR / "roger_marks.json").read_text())["v6_items"]) | {
        k.split("/")[1] for k in json.loads((D / "roger_marks.json").read_text())["items"] if k.startswith("v6/")}
    done7 = {k.split("/")[1] for k in json.loads((D / "roger_marks.json").read_text())["items"]
             if k.startswith("v7/")}
    pools: dict = {}
    for src in ("v6", "v7"):
        for i, it in keys[src]["items"].items():
            if it["stratum"] == "remark" or i in (done if src == "v6" else done7):
                continue
            s, e, k = it["set"], it["entity"], it["key"]
            g = t7.fine_group(s, e)
            mk = marks[src].get(i, "")[:1]
            if g in SHEET2_N and mk in ("B", "T") and sc[("luna", "v7", s)].get(e, {}).get(k) == 3:
                added = sc[("luna", "v6", s)].get(e, {}).get(k) != 3
                pools.setdefault((g, mk), []).append((src, i, f"{SHEET2_LABEL[g]}; "
                                                      + ("gpt-5.6-luna v7 adds it" if added
                                                         else "kept by both gpt-5.6-luna versions")))
    rng = random.Random(SHEET2_SEED)
    out = []
    for g, n in SHEET2_N.items():
        sizes = {mk: len(pools.get((g, mk), [])) for mk in ("B", "T")}
        total = sum(sizes.values())
        quota = {mk: n * c // total for mk, c in sizes.items()}
        for mk in sorted(sizes, key=lambda m: -(n * sizes[m] / total - quota[m]))[:n - sum(quota.values())]:
            quota[mk] += 1
        picked = [x for mk in ("B", "T") for x in rng.sample(sorted(pools.get((g, mk), [])), quota[mk])]
        rng.shuffle(picked)
        out += picked
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", type=int, choices=(1, 2), default=1)
    args = ap.parse_args()
    sc = {(j, v, s): v6.scores(d) for (j, v), ds in b7.SCORES.items() for s, d in ds.items()}
    keys = {"v6": json.loads((t7.V6_DIR / "key.json").read_text()),
            "v7": json.loads((D / "key.json").read_text())}
    marks = {"v6": notes(t7.V6_DIR), "v7": notes(D)}
    k6, k7 = keys["v6"], keys["v7"]
    items = ITEMS if args.sheet == 1 else sheet2_items(sc, keys, marks)
    title = ("Items for Roger: the v6-or-v7 decision" if args.sheet == 1
             else "Items for Roger, sheet 2: the readers' B and T where gpt-5.6-luna v7 looks lenient")
    out = D / ("roger_sheet.md" if args.sheet == 1 else "roger_sheet_2.md")
    lines = [f"# {title}", "", (INTRO_1 if args.sheet == 1 else INTRO_2) + INTRO_TAIL, "", "---", ""]
    cache: dict = {}
    for n, (src, i, why) in enumerate(items, 1):
        it = keys[src]["items"][i]
        s, e, k = it["set"], it["entity"], it["key"]
        if (s, e) not in cache:
            cache[(s, e)] = v6.responses(v6.RESPONSES[s], e)
        rec = cache[(s, e)][k]
        doc = json.loads((v6.ROLES / f"{e}.json").read_text())
        bits = tuple(int(sc[(j, v, s)].get(e, {}).get(k) == 3) for j, v in ORDER)
        cell6 = f"{bits[0]}{bits[1]}{bits[3]}"
        g6 = v6.group(s, e)
        st6 = f"{s}|{cell6}|{g6 if g6 in v6.WANT[(s, cell6)] else '*'}"
        pi6 = k6["sampled"].get(st6, 0) / k6["population"][st6]
        p = b7.part(*(x == 1 for x in (bits[1], bits[2], bits[3], bits[4])))
        pi7 = 0.0
        if p:
            g7 = b7.group(s, e)
            st7 = f"{s}|{p}|{g7 if g7 in b7.WANT[(s, p)] else '*'}"
            pi7 = k7["sampled"].get(st7, 0) / (k7["population"][st7] - k7["marked_on_v6_sheets"].get(st7, 0))
        weight = 1 / (pi6 + (1 - pi6) * pi7)
        sheet_ref = (f"[v6 sheet {it['sheet']}](../reader_check_v6/sheet_{it['sheet']}.md) item {i}" if src == "v6"
                     else f"[v7 sheet {it['sheet']}](./sheet_{it['sheet']}.md) item {i}")
        name = corpus_display_name(e, "roles")
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in v6.answer(rec).splitlines())
        decided = "; ".join(f"{LABEL[jv]} {'keeps' if b else 'drops'}" for jv, b in zip(ORDER, bits))
        lines += [f"## {n}. {name}, {v6.LABEL[s]}", "", f"*{why}.*", "", "your mark: ", "",
                  f"**Role**: [{name}](../../../../data/roles/instructions/{e}.json): {doc['description']}", "",
                  f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "",
                  f"**Judges**: {decided}.", "", f"**Readers' mark**: {marks[src].get(i, '')}", "",
                  f"**Stands for**: about {weight:,.0f} responses.  ({sheet_ref}, key `{s}/{e} {k}`)", "",
                  "---", ""]
    out.write_text("\n".join(lines))
    print("wrote", out, f"({len(items)} items)")


if __name__ == "__main__":
    main()
