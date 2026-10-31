"""Tally of the combination reading sheets (2026-10-30): the readers' role and trait letters, ai calls and
relation tags against the dedicated judges, the drafts' answers and each other.

Marks come from sheet_1_marks.md and sheet_2_marks.md (the holistic readers), role_sheet_marks.md and
trait_sheet_marks.md (the single-persona readers, on 30 of the items), and Roger's ``your ...`` lines in
roger_sheet.md when filled, which override the holistic readers'.  key.json gives, per item, what every judge
said.  A letter is a weight (G 1, G/T .75, T .5, T/B .25, B 0; ? left out); "yes" is .75 or more, "no" .25 or
less, T neither.  Writes tally.json beside the sheets.

    uv run python reports/pipeline/combination_rubric_review/reader_check/tally.py
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path("reports/pipeline/combination_rubric_review/reader_check")
WEIGHT = {"G": 1.0, "G/T": .75, "T": .5, "T/B": .25, "B": 0.0}
LETTER_FORMS = {"B|T": "T/B", "T|B": "T/B", "B/T": "T/B", "T/G": "G/T", "G|T": "G/T", "T|G": "G/T"}   # Roger's spellings
TAGS = ("none", "swamped-role", "swamped-trait", "refused-role", "refused-trait", "no-scope-role",
        "no-scope-trait", "fused", "conflict")
# the AI and machine roles (criteria, role 2): an AI mention is in character, so the ai line does not drop the
# response under the rules below; Roger writes the letter the mention would earn with a note that the role allows it
AI_ROLES = {"cyborg", "instrumentally_aligned_ai", "aligned_artificial_intelligence", "paperclip_maximizer", "robot",
            "virtue_aligned_ai"}


def parse(path: Path, prefix: str = "") -> dict:
    """``item -> {"role": (letter, note), "trait": ..., "ai": ..., "relation": (tag, note)}`` from a marks file
    (or Roger's sheet with ``prefix`` "your "); a line left blank is not recorded."""
    out, n = {}, None
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        m = re.match(r"^###\s+(\d+)", line)
        if m:
            n = m.group(1); out.setdefault(n, {}); continue
        m = re.match(rf"^{re.escape(prefix)}(role|trait|ai|relation):\s*(\S+)(.*)$", line)
        if m and n is not None:
            field, mark, note = m.group(1), m.group(2).strip(), m.group(3).strip(" —-:")
            if field == "relation":
                # the tag may be glued to the note ("`swamped-role`Kind of puzzling"): take the leading tag
                mark = re.sub(r"[^a-z-].*$", "", mark.lower().lstrip("`"))
            elif field == "ai":
                mark = mark.lower().strip(",.;")
            else:
                mark = mark.upper().strip(",.;")
                mark = LETTER_FORMS.get(mark, mark)
            out[n][field] = (mark, note)
    return {k: v for k, v in out.items() if v}


def yes_no(letter):
    w = WEIGHT.get(letter)
    return None if w is None else (True if w >= .75 else False if w <= .25 else "T")


def prec_rec(pairs):
    """Precision and recall of a judge's keeps against the readers' letters as weights (G 1 ... B 0, so T is half
    good and half bad; the trait review's tally does the same, there weighted back by stratum population, here
    unweighted since the sheet is not a population sample): ``pairs`` are (weight, kept)."""
    kg = sum(w for w, kept in pairs if kept); kb = sum(1 - w for w, kept in pairs if kept); tg = sum(w for w, _ in pairs)
    return (kg / (kg + kb) if kg + kb else float("nan")), (kg / tg if tg else float("nan"))


def pr_line(rows, i_w, cols):
    """``rows`` carry a letter at ``i_w``; ``cols`` is (name, index of the kept flag) per configuration."""
    out = {}
    for name, i in cols:
        pairs = [(WEIGHT[r[i_w]], r[i]) for r in rows if r[i_w] in WEIGHT]
        out[name] = prec_rec(pairs)
    return "  ".join(f"{name} precision {p:.2f} recall {r:.2f}" for name, (p, r) in out.items()), out


def main() -> None:
    key = json.loads((HERE / "key.json").read_text())["items"]
    holistic = {**parse(HERE / "sheet_1_marks.md"), **parse(HERE / "sheet_2_marks.md")}
    single_role = parse(HERE / "role_sheet_marks.md")
    single_trait = parse(HERE / "trait_sheet_marks.md")
    roger = parse(HERE / "roger_sheet.md", prefix="your ")
    marks = {n: {**holistic.get(n, {}), **roger.get(n, {})} for n in key}
    print(f"{len(key)} items; holistic marks on {sum(1 for n in key if holistic.get(n))}, Roger's on "
          f"{sum(1 for n in key if roger.get(n))}, single-persona on {len(single_role)} / {len(single_trait)}")
    out = {"n_items": len(key), "agreement": {}, "pools": {}, "relation": {}, "rules": {}, "single": {}}

    # 1. the readers against the dedicated judges and the drafts, per persona
    print("\nreaders' letters (yes = G or G/T, no = B or T/B) against the dedicated judges and the drafts:")
    for persona, judge_yes, arm_key in (("role", lambda k: k["role_judge"]["C"], "R"),
                                        ("trait", lambda k: k["trait_judge"]["shows"], "T")):
        rows = [(yes_no(marks[n][persona][0]), judge_yes(key[n]), key[n]["v14"][arm_key], key[n]["v15"][arm_key])
                for n in key if marks[n].get(persona)]
        decided = [r for r in rows if r[0] in (True, False)]
        c = Counter((r[0], r[1]) for r in decided)
        agree_j = mean(r[0] == r[1] for r in decided) if decided else float("nan")
        agree_14 = mean(r[0] == r[2] for r in decided) if decided else float("nan")
        agree_15 = mean(r[0] == r[3] for r in decided) if decided else float("nan")
        print(f"  {persona:5s} n {len(rows)} (T or ? {len(rows) - len(decided)}): readers yes {mean(r[0] is True for r in rows):.2f}; "
              f"agree with the dedicated judge {agree_j:.2f}, with draft 14 {agree_14:.2f}, with draft 15 {agree_15:.2f}; "
              f"reader yes/judge no {c[(True, False)]}, reader no/judge yes {c[(False, True)]}")
        out["agreement"][persona] = {"n": len(rows), "undecided": len(rows) - len(decided), "judge": agree_j,
                                     "v14": agree_14, "v15": agree_15, "cells": {f"{a}/{b}": v for (a, b), v in c.items()}}
        lrows = [(marks[n][persona][0], judge_yes(key[n]), key[n]["v14"][arm_key], key[n]["v15"][arm_key])
                 for n in key if marks[n].get(persona)]
        line, pr = pr_line(lrows, 0, (("judge", 1), ("draft 14", 2), ("draft 15", 3)))
        print(f"        T half good, half bad: {line}")
        out["agreement"][persona]["precision_recall"] = {k: {"precision": p, "recall": r} for k, (p, r) in pr.items()}

    # 2. by pool: where the drafts and the dedicated judge disagreed, whom do the readers side with?
    print("\nby pool (where a draft and the dedicated judge disagreed, the readers' letter on that persona):")
    for pool in sorted({key[n]["pool"] for n in key}):
        ns = [n for n in key if key[n]["pool"] == pool]
        persona = "role" if pool.startswith("R") else "trait" if pool.startswith("T") else None
        if persona:
            letters = Counter(marks[n][persona][0] for n in ns if marks[n].get(persona))
            side = [yes_no(marks[n][persona][0]) for n in ns if marks[n].get(persona)]
            arm_yes = pool.split("arms ")[1].startswith("yes")
            with_arm = sum(s == arm_yes for s in side); with_judge = sum(s == (not arm_yes) for s in side)
            print(f"  {pool:28s} n {len(ns):2d}  letters {dict(letters)}  with the drafts {with_arm}, with the judge {with_judge}")
            out["pools"][pool] = {"n": len(ns), "letters": dict(letters), "with_drafts": with_arm, "with_judge": with_judge}
        else:
            both = Counter((marks[n]["role"][0], marks[n]["trait"][0]) for n in ns if marks[n].get("role") and marks[n].get("trait"))
            print(f"  {pool:28s} n {len(ns):2d}  (role, trait) letters {dict(both)}")
            out["pools"][pool] = {"n": len(ns), "letters": {f"{a}/{b}": v for (a, b), v in both.items()}}

    # 3. relation tags
    print("\nrelation tags, by the (role, trait) yes/no pattern and by stratum:")
    tags = Counter(); by_pattern = defaultdict(Counter); by_stratum = defaultdict(Counter); bad = []
    for n in key:
        rel = marks[n].get("relation")
        if not rel:
            continue
        tag = rel[0]
        if tag not in TAGS:
            bad.append((n, tag)); continue
        tags[tag] += 1
        pat = f"role {yes_no(marks[n]['role'][0]) if marks[n].get('role') else '?'} / trait {yes_no(marks[n]['trait'][0]) if marks[n].get('trait') else '?'}"
        by_pattern[pat][tag] += 1; by_stratum[key[n]["stratum"]][tag] += 1
    print("  all:", dict(tags.most_common()))
    for pat, c in sorted(by_pattern.items()):
        print(f"  {pat:28s} {dict(c.most_common())}")
    for s, c in sorted(by_stratum.items()):
        print(f"  {s:28s} {dict(c.most_common())}")
    if bad:
        print("  tags not in the list:", bad)
    out["relation"] = {"all": dict(tags), "by_pattern": {k: dict(v) for k, v in by_pattern.items()},
                       "by_stratum": {k: dict(v) for k, v in by_stratum.items()}, "unknown_tags": bad}

    # 4. the rules on the readers' calls, against the judge-based rules, on the same items
    print("\nkeep under each rule by the readers' calls (role/trait yes, ai n) against the judge-based rules, same items:")
    def reader_rule(n, rule):
        m = marks[n]
        if not (m.get("role") and m.get("trait") and m.get("ai")):
            return None
        r, t = yes_no(m["role"][0]), yes_no(m["trait"][0])
        ai_ok = m["ai"][0] == "n" or key[n]["role"] in AI_ROLES
        if r == "T" or t == "T" or r is None or t is None:
            return None
        goal = key[n]["goal"]
        return {"both": r and t and ai_ok, "either": (r or t) and ai_ok,
                "goal": (t if goal == "trait" else r) and ai_ok}[rule]
    def judge_rule(n, rule):
        k = key[n]; rs, ts = k["role_judge"]["score"] == 3, k["trait_judge"]["score"] == 3
        return {"both": rs and ts, "either": rs or ts, "goal": ts if k["goal"] == "trait" else rs}[rule]
    for rule in ("both", "either", "goal"):
        pairs = [(reader_rule(n, rule), judge_rule(n, rule)) for n in key]
        pairs = [p for p in pairs if p[0] is not None]
        c = Counter(pairs)
        print(f"  {rule:7s} n {len(pairs):2d}  readers keep {mean(p[0] for p in pairs):.2f}  separate judges keep "
              f"{mean(p[1] for p in pairs):.2f}  agree {mean(p[0] == p[1] for p in pairs):.2f}  "
              f"readers keep/judges drop {c[(True, False)]}  readers drop/judges keep {c[(False, True)]}")
        out["rules"][rule] = {"n": len(pairs), "readers_keep": mean(p[0] for p in pairs), "judges_keep": mean(p[1] for p in pairs),
                              "agree": mean(p[0] == p[1] for p in pairs), "rk_jd": c[(True, False)], "rd_jk": c[(False, True)]}
    # the drafts' own keep against the readers', same rule
    for rule, v in (("both", "v14"), ("either", "v15")):
        pairs = [(reader_rule(n, rule), key[n][v]["score"] == 3) for n in key]
        pairs = [p for p in pairs if p[0] is not None]
        c = Counter(pairs)
        print(f"  {rule:7s} draft {v}: agree with the readers {mean(p[0] == p[1] for p in pairs):.2f}  "
              f"draft keeps/readers drop {c[(False, True)]}  draft drops/readers keep {c[(True, False)]}")

    # the same with the letters as probabilities (Roger, 2026-10-30), so that a T counts instead of dropping out:
    # both = the product (T and T keep a quarter), either = one minus the product of the complements, goal = the
    # goal entity's own weight; an ai mark other than n (outside the AI roles) sets the keep to 0.
    def reader_weight(n, rule, src=None):
        m = src[n] if src else marks[n]
        if not (m.get("role") and m.get("trait") and m.get("ai")):
            return None
        wr, wt = WEIGHT.get(m["role"][0]), WEIGHT.get(m["trait"][0])
        if wr is None or wt is None:
            return None
        ai = 1.0 if (m["ai"][0] == "n" or key[n]["role"] in AI_ROLES) else 0.0
        return {"both": wr * wt, "either": 1 - (1 - wr) * (1 - wt), "goal": wt if key[n]["goal"] == "trait" else wr}[rule] * ai
    def rules_weighted(ns, src=None, label=""):
        print(f"  {label}letters as probabilities (T and T keep a quarter under both, three quarters under either):")
        res = {}
        for rule in ("both", "either", "goal"):
            trip = [(reader_weight(n, rule, src), judge_rule(n, rule), key[n]["v14" if rule == "both" else "v15"]["score"] == 3)
                    for n in ns]
            trip = [t for t in trip if t[0] is not None]
            if not trip:
                continue
            pj, rj = prec_rec([(w, j) for w, j, _ in trip])
            draft = {"both": "draft 14", "either": "draft 15", "goal": None}[rule]
            pd, rd = prec_rec([(w, d) for w, _, d in trip]) if draft else (float("nan"), float("nan"))
            print(f"    {rule:7s} n {len(trip):2d}  readers' expected keep {mean(t[0] for t in trip):.2f}  separate judges keep "
                  f"{mean(t[1] for t in trip):.2f}: precision {pj:.2f} recall {rj:.2f}"
                  + (f"  {draft} keeps {mean(t[2] for t in trip):.2f}: precision {pd:.2f} recall {rd:.2f}" if draft else ""))
            res[rule] = {"n": len(trip), "readers_keep": mean(t[0] for t in trip), "judges_keep": mean(t[1] for t in trip),
                         "judges_precision": pj, "judges_recall": rj,
                         **({"draft_keep": mean(t[2] for t in trip), "draft_precision": pd, "draft_recall": rd} if draft else {})}
        return res
    out["rules_weighted"] = rules_weighted(list(key))

    # 5. the single-persona readers against the holistic reader, same items
    print("\nsingle-persona readers against the holistic reader (30 items):")
    for persona, single in (("role", single_role), ("trait", single_trait)):
        pairs = [(yes_no(holistic[n][persona][0]), yes_no(single[n][persona][0]))
                 for n in single if holistic.get(n, {}).get(persona) and single[n].get(persona)]
        dec = [p for p in pairs if p[0] in (True, False) and p[1] in (True, False)]
        c = Counter(dec)
        print(f"  {persona:5s} n {len(pairs)} (decided both {len(dec)}): agree {mean(p[0] == p[1] for p in dec) if dec else float('nan'):.2f}; "
              f"holistic yes {mean(p[0] is True for p in pairs):.2f} single yes {mean(p[1] is True for p in pairs):.2f}; "
              f"holistic yes/single no {c[(True, False)]}, holistic no/single yes {c[(False, True)]}")
        out["single"][persona] = {"n": len(pairs), "agree": mean(p[0] == p[1] for p in dec) if dec else None,
                                  "h_yes_s_no": c[(True, False)], "h_no_s_yes": c[(False, True)]}
    # 6. Roger's marks against the holistic readers, the dedicated judges and the drafts, on his items only
    if roger:
        print(f"\nRoger's {len(roger)} items: his letters against the holistic readers', the dedicated judges and the drafts "
              f"(yes = G or G/T, no = B or T/B; T left out):")
        out["roger"] = {"n": len(roger), "persona": {}, "pools": {}, "relation": {}}
        for persona, judge_yes, arm_key in (("role", lambda k: k["role_judge"]["score"] == 3, "R"),
                                            ("trait", lambda k: k["trait_judge"]["score"] == 3, "T")):
            rows = [(n, yes_no(roger[n][persona][0]), yes_no(holistic[n][persona][0]) if holistic.get(n, {}).get(persona) else None,
                     judge_yes(key[n]), key[n]["v14"][arm_key], key[n]["v15"][arm_key])
                    for n in roger if roger[n].get(persona)]
            dec = [r for r in rows if r[1] in (True, False)]
            vs_reader = [r for r in dec if r[2] in (True, False)]
            def cells(pairs, i):
                c = Counter((r[1], r[i]) for r in pairs)
                return c[(True, False)], c[(False, True)]
            ry_rn, rn_ry = cells(vs_reader, 2); ry_jn, rn_jy = cells(dec, 3); ry_dn, rn_dy = cells(dec, 4)
            print(f"  {persona:5s} n {len(rows)} (Roger T {len(rows) - len(dec)}): Roger yes {mean(r[1] is True for r in rows):.2f}; "
                  f"agree with the readers {mean(r[1] == r[2] for r in vs_reader) if vs_reader else float('nan'):.2f} on {len(vs_reader)} "
                  f"(Roger yes/reader no {ry_rn}: {[r[0] for r in vs_reader if r[1] and not r[2]]}; "
                  f"Roger no/reader yes {rn_ry}: {[r[0] for r in vs_reader if not r[1] and r[2]]}); "
                  f"with the dedicated judge {mean(r[1] == r[3] for r in dec):.2f} "
                  f"(Roger yes/judge no {ry_jn}: {[r[0] for r in dec if r[1] and not r[3]]}; "
                  f"Roger no/judge yes {rn_jy}: {[r[0] for r in dec if not r[1] and r[3]]}); "
                  f"with draft 14 {mean(r[1] == r[4] for r in dec):.2f} "
                  f"(Roger yes/draft no {ry_dn}: {[r[0] for r in dec if r[1] and not r[4]]}; "
                  f"Roger no/draft yes {rn_dy}: {[r[0] for r in dec if not r[1] and r[4]]}); "
                  f"with draft 15 {mean(r[1] == r[5] for r in dec):.2f}")
            lrows = [(roger[n][persona][0], judge_yes(key[n]), key[n]["v14"][arm_key], key[n]["v15"][arm_key],
                      holistic[n][persona][0] if holistic.get(n, {}).get(persona) else None) for n in roger if roger[n].get(persona)]
            line, pr = pr_line(lrows, 0, (("judge", 1), ("draft 14", 2), ("draft 15", 3)))
            # the readers as a configuration: their letter counts as a keep when it is yes (G or G/T)
            line_r, pr_r = pr_line([(r[0], yes_no(r[4]) is True) for r in lrows if r[4] in WEIGHT], 0, (("readers (yes = keep)", 1),))
            print(f"        T half good, half bad, on Roger's letters: {line}  {line_r}")
            out["roger"]["persona"][persona] = {
                "precision_recall": {**{k: {"precision": p, "recall": r} for k, (p, r) in pr.items()},
                                     **{k: {"precision": p, "recall": r} for k, (p, r) in pr_r.items()}},
                "n": len(rows), "undecided": len(rows) - len(dec), "agree_readers": mean(r[1] == r[2] for r in vs_reader) if vs_reader else None,
                "agree_judge": mean(r[1] == r[3] for r in dec) if dec else None, "agree_v14": mean(r[1] == r[4] for r in dec) if dec else None,
                "agree_v15": mean(r[1] == r[5] for r in dec) if dec else None,
                "roger_yes_reader_no": [r[0] for r in vs_reader if r[1] and not r[2]], "roger_no_reader_yes": [r[0] for r in vs_reader if not r[1] and r[2]],
                "roger_yes_judge_no": [r[0] for r in dec if r[1] and not r[3]], "roger_no_judge_yes": [r[0] for r in dec if not r[1] and r[3]],
                "roger_yes_draft_no": [r[0] for r in dec if r[1] and not r[4]], "roger_no_draft_yes": [r[0] for r in dec if not r[1] and r[4]]}
        print("  by pool, Roger's side where a draft and the dedicated judge disagreed (the readers' side on the same items in brackets):")
        for pool in sorted({key[n]["pool"] for n in roger}):
            persona = "role" if pool.startswith("R") else "trait" if pool.startswith("T") else None
            ns = [n for n in roger if key[n]["pool"] == pool]
            if not persona:
                print(f"    {pool:28s} n {len(ns):2d}  Roger (role, trait) {[(roger[n].get('role', ('-',))[0], roger[n].get('trait', ('-',))[0]) for n in ns]}")
                continue
            arm_yes = pool.split("arms ")[1].startswith("yes")
            def sides(src):
                s = [yes_no(src[n][persona][0]) for n in ns if src.get(n, {}).get(persona)]
                return sum(x == arm_yes for x in s), sum(x == (not arm_yes) for x in s), sum(x == "T" for x in s)
            rd, rj, rt = sides(roger); hd, hj, ht = sides(holistic)
            print(f"    {pool:28s} n {len(ns):2d}  with the drafts {rd} [{hd}], with the judge {rj} [{hj}], T {rt} [{ht}]   items {ns}")
            out["roger"]["pools"][pool] = {"n": len(ns), "with_drafts": rd, "with_judge": rj, "T": rt,
                                           "readers_with_drafts": hd, "readers_with_judge": hj, "readers_T": ht}
        same = [n for n in roger if roger[n].get("relation") and holistic.get(n, {}).get("relation")
                and roger[n]["relation"][0] == holistic[n]["relation"][0]]
        second = [n for n in roger if roger[n].get("relation") and holistic.get(n, {}).get("relation")
                  and roger[n]["relation"][0] != holistic[n]["relation"][0]
                  and (holistic[n]["relation"][0] in roger[n]["relation"][1] or roger[n]["relation"][0] in holistic[n]["relation"][1])]
        diff = [n for n in roger if roger[n].get("relation") and holistic.get(n, {}).get("relation")
                and n not in same and n not in second]
        print(f"  relation tags: the same as the reader's on {len(same)} {same}; the reader's main tag is Roger's secondary or the reverse on "
              f"{len(second)} {second}; different on {len(diff)} "
              f"{[(n, roger[n]['relation'][0], holistic[n]['relation'][0]) for n in diff]}")
        out["roger"]["relation"] = {"same": same, "secondary": second, "different": diff}
        out["roger"]["rules_weighted"] = rules_weighted(list(roger), roger, "on Roger's items, his ")
        ai_roles = [(n, roger[n]["ai"][0]) for n in roger if roger[n].get("ai") and key[n]["role"] in AI_ROLES and roger[n]["ai"][0] != "n"]
        if ai_roles:
            print(f"  ai letters other than n on AI roles, read as not dropping (criteria, role 2): {ai_roles}")
    (HERE / "tally.json").write_text(json.dumps(out, indent=1))
    print(f"\nwritten {HERE / 'tally.json'}")


if __name__ == "__main__":
    main()
