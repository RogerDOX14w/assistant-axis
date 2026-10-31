"""Read the context-aware combination drafts' judgings (run_judging.sh): version 16, the role rubric with the
trait as context, and the trait sides 17 (version 13's shape) and 18 (version 11's A/B/C shape), each with the
role as context, against the separate judges (the role alone under version 10, the trait alone under 13), the
one-prompt drafts 14 and 15, and the marks on the reading sheets (../reader_check/: the readers' letters and
Roger's, which override them).  Three views:

1. the sheet's items (the May responses Roger and the readers marked): each side's agreement with the letters,
   the dedicated judge and draft 14's answer; precision and recall against Roger's letters with T half good and
   half bad; and the "both" rule (a 3 from each side) against his expected keep, with his letters as
   probabilities and an ai letter other than n dropping the response unless the role is an AI role;
2. the whole May exploration sample (28 combinations, 1,522 responses), by stratum;
3. the October re-check sample (25 combinations as of 2026-10-30), per combination.

Rows with every judgement are written to rows.json beside this script; disagreement examples to examples.md.
A trait side not yet run (no scores) is left out of the tables that need it.

    uv run python reports/pipeline/combination_rubric_review/context_arms/compare.py
    uv run python reports/pipeline/combination_rubric_review/context_arms/compare.py --sample runpod_workspace/tcomb_recheck

With ``--sample ROOT`` (another sample built by ../recheck/build_sample.py --out and judged by the two
run_judging.sh scripts with COMBO_ROOT, the t_ sample), only view 3 is given, on that sample, and the rows and
examples go to rows_<root's last part>.json and examples_<...>.md.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / "reader_check"))
import tally  # noqa: E402  (WEIGHT, LETTER_FORMS, parse, prec_rec, yes_no, AI_ROLES)

EXPLORE = REPO / "runpod_workspace" / "combo_explore"
RECHECK = REPO / "runpod_workspace" / "combo_recheck"
RENAMED = {"r_aligned_artificial_intelligence__pensive": "r_instrumentally_aligned_ai__pensive"}
STEM = re.compile(r"^([rt])_(.+?)__(.+)$")
VERSIONS = (14, 15, 16, 17, 18, 19)
TRAIT_SIDES = (17, 18, 19)


def scores(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def replies(p: Path) -> dict:
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["key"]] = r.get("reply")
    return out


def key_of(rec: dict) -> str:
    return f"{rec['label']}_p{rec['prompt_index']}_q{rec['question_index']}"


def load_sample(root: Path) -> list:
    """One row per response: the separate judges' scores (Rs, T), the April text's (C), drafts 14 and 15, and
    the context drafts 16 to 18 (V16...), with the context drafts' replies (r16...).  A stem renamed in the
    corpus is read from the ``*_renamed*`` directories under its new name and reported under its old one (the
    sheets' stem)."""
    rows = []
    for f in sorted((root / "combo" / "responses").glob("*.jsonl")):
        stem = f.stem
        m = STEM.match(stem)
        if not m:
            continue
        kind, role, trait = m.groups()
        sub, name, role_dir, role_name = "combo", stem, root / "role" / stem, role
        if stem in RENAMED and (root / "combo_renamed").exists():
            name = RENAMED[stem]
            sub, role_dir, role_name = "combo_renamed", root / "role_renamed", name.split("__")[0][2:]
        c = scores(root / sub / "scores" / f"{name}.json")
        r = scores(role_dir / "scores" / f"{role_name}.json")
        t = scores(root / "trait" / stem / "scores" / f"{trait}.json")
        v = {n: scores(root / f"{sub}_v{n}" / "scores" / f"{name}.json") for n in VERSIONS}
        rp = {n: replies(root / f"{sub}_v{n}" / "scores" / "_replies" / f"{name}.jsonl") for n in (16, 17, 18, 19)}
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            k = key_of(rec)
            row = dict(stem=stem, kind=kind, role=role, trait=trait, key=k, question=rec["question"],
                       answer=next(x["content"] for x in reversed(rec["conversation"]) if x["role"] == "assistant"),
                       cut=rec.get("finish_reason") == "length", stratum=rec.get("explore", {}).get("stratum"),
                       C=c.get(k), Rs=r.get(k), T=t.get(k))
            row.update({f"V{n}": v[n].get(k) for n in VERSIONS})
            row.update({f"r{n}": rp[n].get(k) for n in (16, 17, 18, 19)})
            rows.append(row)
    return rows


def agree_line(name: str, a: list, b: list) -> str:
    """Agreement of two yes/no lists (None left out) and the two disagreement counts."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return f"{name}: no pairs"
    return (f"{name}: agree {mean(x == y for x, y in pairs):.2f} on {len(pairs)}; "
            f"yes/no {sum(x and not y for x, y in pairs)}, no/yes {sum((not x) and y for x, y in pairs)}")


def yes(score):
    return None if score is None else score == 3


def letter(marks: dict, n: str, field: str):
    m = marks.get(n, {}).get(field)
    return tally.LETTER_FORMS.get(m[0], m[0]) if m else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=Path, default=None,
                    help="another sample's root (view 3 only; rows_<name>.json and examples_<name>.md)")
    a = ap.parse_args()
    if a.sample is not None:
        other = load_sample(REPO / a.sample)
        have = [n for n in VERSIONS if any(r[f"V{n}"] is not None for r in other)]
        trait_sides = [n for n in TRAIT_SIDES if n in have]
        samples = [(f"3. the sample under {a.sample}", other, "stem")]
        suffix = f"_{Path(a.sample).name}"
        rows_out = {"sample": str(a.sample), "rows": other}
    else:
        samples, suffix = None, ""
    if a.sample is None:
        key = json.loads((HERE.parent / "reader_check" / "key.json").read_text())["items"]
        readers = {**tally.parse(HERE.parent / "reader_check" / "sheet_1_marks.md"),
                   **tally.parse(HERE.parent / "reader_check" / "sheet_2_marks.md")}
        roger = tally.parse(HERE.parent / "reader_check" / "roger_sheet.md", prefix="your ")
        may = load_sample(EXPLORE)
        octo = load_sample(RECHECK)
        samples = [("2. the May exploration sample", may, "stratum"), ("3. the October re-check sample", octo, "stem")]
        rows_out = {"may": may, "october": octo}
        by_key = {(r["stem"], r["key"]): r for r in may}
        have = [n for n in VERSIONS if any(r[f"V{n}"] is not None for r in may)]
        trait_sides = [n for n in TRAIT_SIDES if n in have]
        sides = [(16, "role", "role_judge", "R")] + [(n, "trait", "trait_judge", "T") for n in trait_sides]
        sheet_items(key, readers, roger, by_key, trait_sides, sides)
    samples_and_examples(samples, trait_sides, suffix, rows_out)


def sheet_items(key, readers, roger, by_key, trait_sides, sides) -> None:
    # ---- 1. the sheet's items -------------------------------------------------------------------------------
    print("1. the sheet's items: each side against the letters, the dedicated judge and draft 14's answer")
    for who, marks in (("Roger", roger), ("readers", readers)):
        items = [n for n in key if n in marks]
        for ver, field, judge, v14_field in sides:
            rows_ = [(n, by_key.get((key[n]["stem"], key[n]["key"]))) for n in items]
            rows_ = [(n, r) for n, r in rows_ if r is not None and r[f"V{ver}"] is not None]
            yn = [tally.yes_no(letter(marks, n, field)) for n, _ in rows_]
            letters = [None if x in (None, "T") else x for x in yn]
            draft = [yes(r[f"V{ver}"]) for _, r in rows_]
            dedicated = [key[n][judge]["score"] == 3 for n, _ in rows_]
            v14 = [key[n]["v14"].get(v14_field) for n, _ in rows_]
            print(f"  {who:7s} {field} ({ver})  n {len(draft):2d}  " + agree_line("side vs letters", draft, letters)
                  + "  |  " + agree_line("dedicated judge vs letters", dedicated, letters)
                  + "  |  " + agree_line("draft 14's answer vs letters", v14, letters))
            print(f"  {'':7s} {'':10s}        " + agree_line("side vs dedicated judge", draft, dedicated))
            if who == "Roger":
                weighted = [(tally.WEIGHT[letter(marks, n, field)], i) for i, (n, _) in enumerate(rows_)
                            if letter(marks, n, field) in tally.WEIGHT]
                (pd, rd) = tally.prec_rec([(w, draft[i]) for w, i in weighted])
                (pj, rj) = tally.prec_rec([(w, dedicated[i]) for w, i in weighted])
                (p4, r4) = tally.prec_rec([(w, v14[i]) for w, i in weighted if v14[i] is not None])
                print(f"  {'':7s} {'':10s}        T half good, half bad against Roger's letters: side precision {pd:.2f} "
                      f"recall {rd:.2f}; dedicated judge {pj:.2f} / {rj:.2f}; draft 14's answer {p4:.2f} / {r4:.2f}")
    # the "both" rule on Roger's items: his letters as probabilities
    pairs = defaultdict(list)
    for n, it in key.items():
        if n not in roger:
            continue
        wr, wt = tally.WEIGHT.get(letter(roger, n, "role")), tally.WEIGHT.get(letter(roger, n, "trait"))
        if wr is None or wt is None:
            continue
        ai = roger[n].get("ai")
        ai_ok = ai is None or ai[0].startswith("n") or it["role"] in tally.AI_ROLES
        w = wr * wt * (1.0 if ai_ok else 0.0)
        row = by_key.get((it["stem"], it["key"]))
        if row is None or row["V16"] is None or any(row[f"V{t}"] is None for t in trait_sides):
            continue
        for t in trait_sides:
            pairs[f"context sides 16 and {t}, both 3"].append((w, row["V16"] == 3 and row[f"V{t}"] == 3))
        pairs["separate judges, both 3"].append((w, it["role_judge"]["score"] == 3 and it["trait_judge"]["score"] == 3))
        pairs["draft 14"].append((w, it["v14"]["score"] == 3))
    first = next(iter(pairs.values()))
    print(f"\n  the 'both' rule on Roger's {len(first)} items, his letters as probabilities (expected keep "
          f"{mean(w for w, _ in first):.2f}):")
    for name, ps in pairs.items():
        p, r = tally.prec_rec(ps)
        print(f"    {name:36s} keeps {mean(k for _, k in ps):.2f}  precision {p:.2f} recall {r:.2f}")


def samples_and_examples(samples, trait_sides, suffix, rows_out) -> None:
    # ---- 2 and 3. the samples ---------------------------------------------------------------------------------
    for title, rows, group in samples:
        full = [r for r in rows if None not in (r["Rs"], r["T"], r["V16"]) and all(r[f"V{t}"] is not None for t in trait_sides)]
        print(f"\n{title}: {len(full)} of {len(rows)} responses with every judgement")
        if not full:
            continue
        print("  " + agree_line("16 (role side) vs the role judge", [r["V16"] == 3 for r in full], [r["Rs"] == 3 for r in full]))
        for t in trait_sides:
            print("  " + agree_line(f"{t} (trait side) vs the trait judge", [r[f"V{t}"] == 3 for r in full], [r["T"] == 3 for r in full]))
        if len(trait_sides) == 2:
            a, b = trait_sides
            print("  " + agree_line(f"{a} vs {b}", [r[f"V{a}"] == 3 for r in full], [r[f"V{b}"] == 3 for r in full]))
        with14 = [r for r in full if r["V14"] is not None]
        for t in trait_sides:
            if with14:
                print("  " + agree_line(f"16 and {t} both 3 vs draft 14", [r["V16"] == 3 and r[f"V{t}"] == 3 for r in with14],
                                        [r["V14"] == 3 for r in with14]))
        print("  keep: " + "  ".join(f"16&{t} {mean(r['V16'] == 3 and r[f'V{t}'] == 3 for r in full):.2f}" for t in trait_sides)
              + f"  separate judges both 3 {mean(r['Rs'] == 3 and r['T'] == 3 for r in full):.2f}  "
              f"role side 16 {mean(r['V16'] == 3 for r in full):.2f} (judge {mean(r['Rs'] == 3 for r in full):.2f})  "
              + "  ".join(f"trait side {t} {mean(r[f'V{t}'] == 3 for r in full):.2f}" for t in trait_sides)
              + f" (judge {mean(r['T'] == 3 for r in full):.2f})"
              + (f"  draft 14 {mean(r['V14'] == 3 for r in with14):.2f}" if with14 else ""))
        head = "  ".join(f"16&{t}" for t in trait_sides) + "  bothJ   R16 Rjudge  " + "  ".join(f"T{t}" for t in trait_sides) + " Tjudge"
        print(f"  {'by ' + group:46s} {'n':>4s}  {head}")
        groups = defaultdict(list)
        for r in full:
            groups[r[group] or "-"].append(r)
        for g, sub in sorted(groups.items()):
            print(f"  {g:46s} {len(sub):4d}  "
                  + "  ".join(f"{mean(r['V16'] == 3 and r[f'V{t}'] == 3 for r in sub):.2f} " for t in trait_sides)
                  + f" {mean(r['Rs'] == 3 and r['T'] == 3 for r in sub):.2f}  {mean(r['V16'] == 3 for r in sub):.2f}  {mean(r['Rs'] == 3 for r in sub):.2f}  "
                  + "  ".join(f"{mean(r[f'V{t}'] == 3 for r in sub):.2f}" for t in trait_sides)
                  + f"  {mean(r['T'] == 3 for r in sub):.2f}")
        print("  score distributions: " + "  ".join(f"{n} {dict(sorted(Counter(r[f'V{n}'] for r in full).items()))}"
                                                     for n in [16] + trait_sides))

    # ---- examples: where a side and its dedicated judge disagree -----------------------------------------------
    lines = ["# Context drafts against the separate judges: disagreement examples", "",
             "Where version 16 (the role rubric with the trait as context) or a trait side (17, version 13's shape; "
             "18, version 11's) and the dedicated judge (the role alone under 10, the trait alone under 13) disagree "
             "on keep; up to four of each kind per sample, with the context draft's reply.  Written by compare.py.", ""]
    for title, rows, _ in samples:
        title = title.split(". ", 1)[1].replace(" exploration", "").replace(" re-check", "")
        full = [r for r in rows if None not in (r["Rs"], r["T"], r["V16"])]
        kinds = [("16 yes, role judge no", lambda r: r["V16"] == 3 and r["Rs"] != 3, "r16"),
                 ("16 no, role judge yes", lambda r: r["V16"] != 3 and r["Rs"] == 3, "r16")]
        for t in trait_sides:
            kinds += [(f"{t} yes, trait judge no", lambda r, t=t: r[f"V{t}"] == 3 and r["T"] != 3, f"r{t}"),
                      (f"{t} no, trait judge yes", lambda r, t=t: r[f"V{t}"] != 3 and r["T"] == 3, f"r{t}")]
        for name, pick, reply in kinds:
            sub = [r for r in full if r[reply.replace("r", "V")] is not None and pick(r)]
            lines += [f"## {title}: {name} ({len(sub)})", ""]
            for r in sub[:4]:
                lines += [f"**{r['stem']} {r['key']}** (Rs {r['Rs']}, T {r['T']}, 16 {r['V16']}, 17 {r['V17']}, 18 {r['V18']})  ",
                          f"Q: {r['question']}", "", "> " + r["answer"][:700].replace("\n", "\n> "), "",
                          "Reply: " + (r[reply] or "").replace("\n", " "), ""]
    (HERE / f"examples{suffix}.md").write_text("\n".join(lines))
    (HERE / f"rows{suffix}.json").write_text(json.dumps(rows_out, ensure_ascii=False, indent=0))
    print(f"\nrows written to {HERE.relative_to(REPO) / f'rows{suffix}.json'}, examples to "
          f"{HERE.relative_to(REPO) / f'examples{suffix}.md'}")


if __name__ == "__main__":
    main()
