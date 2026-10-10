"""Draft of the goal-list tiers after W15 (2026-10-10), for Roger's review.  Writes
goal_roles_and_traits.proposed.json beside this script; nothing in data/ is touched until Roger approves.

Rules (Roger 2026-10-10): the README's criteria (goal: all five instructions at 2; non-goal: all five at 0); for
non-goal candidates borderline at T=0 (four of five at 0, none at 2), the five instructions' means over one T=0 and
four T=1 samples, each below 0.5 (resample_t1_summary.json).  Previous list members are preferred where there is a
choice: a qualifying member keeps its place; a tier-1 vacancy is filled first by promoting a qualifying tier-2
member; otherwise a new qualifier of the departed entry's kind.  The three goal-side traits at four of five
(progressive, nihilistic, forgiving) are replaced, not resampled (Roger).

    uv run python roger/pre_extraction_2026-10-09/w15/build_goal_tiers.py
"""
import json
import os
from pathlib import Path

HERE = Path("roger/pre_extraction_2026-10-09/w15")
CUR = json.load(open("data/goal_roles_and_traits.json", encoding="utf-8"))
TIERS = {"roles.goal": (30, 10), "roles.non_goal": (30, 10), "traits.goal": (30, 10), "traits.non_goal": (30, 10)}

# vacancy -> replacement, with the reason shown in the sheet.  "promote:X" moves X up from tier 2.
REPLACE = {
    "roles.goal": {
        "artist": ("promote:purist", "a life given to an ideal of the work, the nearest previous member to artist's devotion to craft"),
        "symbiont": ("promote:parasite", "same kind (a living thing defined by its host), symbiont's own partner"),
        "bohemian": ("hacker", "a counterculture with its own code, as bohemian was"),
        "advocate": ("evangelist", "advocacy for a cause, as advocate was"),
        "purist": ("virtue_aligned_ai", "cluster duplicate of instrumentally_aligned_ai in tier 1, as tier 2 is meant to hold"),
        "parasite": ("saint", "cluster duplicate of angel and bodhisattva in tier 1"),
    },
    "traits.goal": {
        "progressive": ("radical", "the same drive for change, taken to the root of the system"),
        "libertarian": ("civil_libertarian", "the political-liberty sense; libertarian's successor metaphysical_libertarian is now free will and not a goal trait (1 on four of five)"),
        "nihilistic": ("amoral", "the rejection of moral values, on the less-default side tier 1 wants"),
        "universalist": ("civilizationist", "a moral-circle member (between nation and humanity), as tier 2 is mostly the moral circle; universalist's successor moral_universalist left the sequence"),
        "gluttonous": ("self_indulgent", "appetite indulged, the same vice in a wider register"),
        "forgiving": ("conciliatory", "default-side repair of relations, as forgiving was"),
    },
    "roles.non_goal": {
        "mathematician": ("move:linguist", "previous member (tier 2), a scholar"),
        "anthropologist": ("move:novelist", "previous member (tier 2), a writer of people"),
        "editor": ("move:designer", "previous member (tier 2), a craft of others' work"),
        "poet": ("move:accountant", "previous member (tier 3)"),
        "generalist": ("move:archaeologist", "previous member (tier 3)"),
        "sommelier": ("move:cartographer", "previous member (tier 3)"),
        "comedian": ("move:chemist", "previous member (tier 3)"),
        "psychologist": ("move:curator", "previous member (tier 3)"),
        "biologist": ("move:debugger", "previous member (tier 3)"),
        "photographer": ("move:programmer", "previous member (tier 3)"),
        "actor": ("move:proofreader", "previous member (tier 3)"),
        "robot": ("cyborg", "non-human or part-machine, as robot was"),
        "historian": ("move:scheduler", "previous member (tier 3)"),
        "oracle": ("dreamer", "an otherworldly entity, as oracle was"),
        "marketer": ("move:secretary", "previous member (tier 3)"),
        "futurist": ("move:summarizer", "previous member (tier 3)"),
        "wraith": ("void", "an otherworldly entity, as wraith was"),
        "detective": ("move:virtuoso", "previous member (tier 3)"),
        "blogger": ("move:writer", "previous member (tier 3)"),
        "swarm": ("insomniac", "a non-job role, for balance (no non-human qualifier is left)"),
        "witch": ("graduate", "a non-job role, for balance"),
        "golem": ("cleaner", "a manual trade, against the list's clerical tilt"),
        "pilot": ("driver", "a driving trade, as pilot was"),
        **{x: ("drop", "no longer qualifies; the list shrinks to the 33 that do")
           for x in ["economist", "specialist", "consultant", "statistician", "sociologist", "forecaster", "composer",
                     "prodigy", "engineer", "playwright", "navigator", "synthesizer", "polymath", "screener", "geographer",
                     "analyst", "researcher", "publisher", "podcaster", "evaluator", "critic", "translator", "producer",
                     "reviewer"]},
    },
    "traits.non_goal": {
        "introverted": ("promote:animated", "previous member (tier 2)"),
        "meticulous": ("promote:decisive", "previous member (tier 2)"),
        "ethereal": ("promote:effusive", "previous member (tier 2)"),
        "abstract": ("concrete", "abstract's own pair partner, the same axis"),
        "speculative": ("quick_witted", "a cognitive style, as speculative was"),
        "quantitative": ("visual_vark", "a way of taking in information (charts and diagrams), as quantitative was"),
        "structuralist": ("interdisciplinary", "a theoretical approach across fields"),
        "reductionist": ("promote:specialist", "previous member (tier 2), the depth-first approach"),
        "visceral": ("emphatic", "forceful expression, as visceral was"),
        "historically_minded": ("expository", "a communication mode built on facts and reasons"),
        "whimsical": ("playful", "whimsy and fun, the same kind"),
        "passionate": ("promote:eloquent", "previous member (tier 2)"),
        "cryptic": ("clear", "cryptic's opposite on the same axis"),
        "manic": ("turbulent", "a stormy temperament, as manic was"),
        "improvisational": ("promote:literal", "previous member (tier 2)"),
        "experiential": ("organized", "a working style, for meticulous's lost slot"),
        "spontaneous": ("wry", "a humor style"),
        "charismatic": ("cheerful", "a temperament"),
        "adaptable": ("even_tempered", "a temperament"),
        "confident": ("plain_spoken", "a communication style"),
        "animated": ("observant", "a cognitive style"),
        "decisive": ("dry", "a communication style"),
        "effusive": ("lighthearted", "a temperament and register"),
        "eloquent": ("self_deprecating", "a humor style"),
        "literal": ("unflappable", "a temperament"),
        "specialist": ("night_owl", "a daily rhythm, a kind the list lacked"),
        "methodical": ("forgetful", "a cognitive trait"),
        "convergent": ("humorless", "witty's opposite, a pair partner as tier 3 holds"),
        "holistic": ("flat", "a communication style, animated's opposite"),
        "analytical": ("unpretentious", "a communication style"),
        "theoretical": ("retentive", "a cognitive trait, forgetful's partner"),
        "accessible": ("bombastic", "a communication style, plain-spoken's opposite"),
        "solemn": ("placid", "a temperament"),
        "big_picture": ("early_bird", "a daily rhythm, night_owl's partner"),
    },
}


# appended to tier 2 after the replacements (roles.non_goal: the three qualifiers left over, each redundant with a
# tier-1 member: machinist with mechanic, operator with driver, organizer with planner and scheduler)
EXTRA_T2 = {"roles.non_goal": ["machinist", "operator", "organizer"]}


def qualifiers():
    agg = json.load(open("data_analysis/output/goal_classifications.json", encoding="utf-8"))
    sc = {}
    for a in agg:
        if a["source"] == "role" or a["polarity"] == "pos":
            sc[(a["source"], a["name"])] = {int(k): v for k, v in a["aggregate"]["score_counts"].items()}
    resampled = {(r["source"], r["name"]) for r in json.load(open(HERE / "resample_t1_summary.json", encoding="utf-8")) if r["qualifies"]}
    phys = {p.stem for p in Path("data/traits/instructions").glob("*.json")
            if "physical" in (json.load(open(p, encoding="utf-8")).get("tags") or [])}
    q = {}
    for src, key in (("role", "roles"), ("trait", "traits")):
        names = [n for (s, n) in sc if s == src]
        q[f"{key}.goal"] = {n for n in names if sc[(src, n)].get(2, 0) == 5 and n not in phys}
        q[f"{key}.non_goal"] = {n for n in names if (sc[(src, n)].get(0, 0) == 5 or (src, n) in resampled) and n not in phys}
    q["roles.goal"].add("virus")  # 2 of 2 readable at 2; three instructions refused every time (kept, flagged)
    return q, sc


def build():
    q, sc = qualifiers()
    out = json.loads(json.dumps(CUR)); report = {}
    for lst, (t1, t2) in TIERS.items():
        kind, sub = lst.split(".")
        old = CUR[kind][sub]; new = list(old); rows = []
        rep = REPLACE.get(lst, {})
        for i, x in enumerate(old):
            if x in q[lst] and new[i] == x:
                continue
            if x in q[lst]:
                continue          # moved or promoted already; its slot was handled there
            if x not in rep:
                raise SystemExit(f"{lst}: {x} no longer qualifies and has no replacement")
            r, why = rep[x]
            if r == "drop":
                if new[i] == x:
                    new[i] = None
                rows.append((i, x, "-", "dropped", why))
            elif r.startswith("move:"):
                m = r.split(":", 1)[1]
                assert m in q[lst] and m in old and old.index(m) > i, (lst, m)
                new[new.index(m)] = None; new[i] = m
                rows.append((i, x, m, f"moved up from position {old.index(m)}", why))
            elif r.startswith("promote:"):
                m = r.split(":", 1)[1]
                assert m in q[lst] and m in old, (lst, m)
                j = new.index(m)
                new[i] = m; new[j] = None
                rows.append((i, x, m, "promoted from tier 2", why))
                r2, why2 = rep[m]
                assert not r2.startswith(("promote:", "move:")) and r2 != "drop" and r2 in q[lst] and r2 not in old, (lst, r2)
                new[j] = r2
                rows.append((j, m, r2, "new", why2))
            else:
                assert r in q[lst] and r not in old and r not in new, (lst, r)
                new[i] = r
                rows.append((i, x, r, "new", why))
        new = [x for x in new if x is not None] + EXTRA_T2.get(lst, [])
        for x in EXTRA_T2.get(lst, []):
            rows.append((len(new) - len(EXTRA_T2[lst]) + EXTRA_T2[lst].index(x), "-", x, "new", "left over, redundant with tier 1"))
        assert len(new) == len(set(new)) and None not in new, lst
        assert all(x in q[lst] for x in new), (lst, [x for x in new if x not in q[lst]])
        out[kind][sub] = new
        report[lst] = sorted(rows)
    (HERE / "goal_roles_and_traits.proposed.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out, report, q, sc


if __name__ == "__main__":
    out, report, q, sc = build()
    for lst, rows in report.items():
        kind, sub = lst.split(".")
        print(f"\n== {lst}: {len(rows)} changes; {len(q[lst])} qualify, list {len(out[kind][sub])}")
        for i, a, b, how, why in rows:
            tier = 1 if i < 30 else 2 if i < 40 else 3
            print(f"  T{tier} [{i:2d}] {a:22s} -> {b:22s} ({how}) {why}")
