"""Goal-list tiers, second draft (Roger 2026-10-10): only the previous top 30 has a claim.  Every previous tier-1 entry
that still qualifies keeps its place; every other place goes to the closest qualifying match to what was there, by the
cosines of closest_matches.json (text-embedding-3-large on label plus about 20 words of description, centred), lower-
tier previous members counting like any other candidate.  Greedy: tier-1 vacancies first, the pair (vacancy,
candidate) with the highest cosine assigned first; then tier 2, then tier 3, where an entry that still qualifies and
was not taken higher up is its own closest match and stays.  roles.non_goal is kept as in the first draft (Roger: the
job / non-job balance matters more).  Non-goal traits that are memberships, bodies or conditions are not candidates
(kept out for the balance of kinds, pending Roger).

    uv run python roger/pre_extraction_2026-10-09/w15/build_goal_tiers_v2.py
"""
import json
import sys
from pathlib import Path

HERE = Path("roger/pre_extraction_2026-10-09/w15")
sys.path.insert(0, str(HERE))
import build_goal_tiers as B  # noqa: E402

CLOSE = json.load(open(HERE / "closest_matches.json", encoding="utf-8"))
EXCLUDE = {"traits.non_goal": {"blind", "deaf", "dyslexic", "canadian", "female", "male", "gray_haired",
                               "northern_hemisphere", "southern_hemisphere", "sleep_deprived", "dissociative"}}
# also not candidates for the greedy fill: a status (famous) and a defect (incoherent), not styles
EXCLUDE["traits.non_goal"] |= {"famous", "incoherent"}
TIER_BOUNDS = [(0, 30), (30, 40), (40, None)]

# Judgement picks, applied before the greedy fill: where the embeddings' shortlist is weak or points at an opposite
# (an antonym is close in topic but, on a goal list, opposite in goal content), the closest match by meaning among the
# shortlist and the qualifiers.  Each carries its reason into the sheet.
FIXED = {
    "roles.goal": {
        "artist": ("purist", "the integrity of a form kept pure, the nearest to artist's 'integrity of the work'; the shortlist is flat (best 0.12, saint)"),
        "symbiont": ("parasite", "the clear nearest (0.48), a living thing defined by its host"),
        "parasite": ("revenant", "nearest left once virus, vampire and predator are placed (0.15)"),
        "bohemian": ("trickster", "norms broken for the life of it; weak, nothing close qualifies (best 0.10)"),
        "advocate": ("evangelist", "the nearest (0.21), advocacy for a cause"),
    },
    "traits.goal": {
        "progressive": ("radical", "the nearest (0.44), the same drive for change taken further"),
        "libertarian": ("existentialist", "the nearest (0.42) to libertarian's old text, free will and personal responsibility"),
        "nihilistic": ("amoral", "the rejection of moral values; antitheist (0.30) and existentialist rank higher by embedding, but one rejects a god and the other is placed"),
        "universalist": ("moral_universalist", "universalist's own renamed successor (0.88)"),
        "gluttonous": ("self_indulgent", "the nearest (0.41), appetite indulged"),
        "forgiving": ("conciliatory", "repair of relations (0.26); unforgiving ranks first (0.42) but is the opposite goal"),
    },
    "traits.non_goal": {
        "introverted": ("unassuming", "a quiet, low-key presence; nothing close qualifies (best 0.13, dull)"),
        "meticulous": ("observant", "the nearest (0.20), attention to small detail"),
        "ethereal": ("eloquent", "the nearest (0.31), graceful language"),
        "abstract": ("concrete", "the nearest (0.34), the same axis"),
        "speculative": ("generalist", "the nearest (0.18), ideas across fields"),
        "quantitative": ("expository", "facts, steps and reasons (0.15)"),
        "structuralist": ("interdisciplinary", "a theoretical approach across fields (0.18); systems thinker, the nearest, is already in"),
        "reductionist": ("specialist", "depth in one domain (0.15)"),
        "visceral": ("animated", "the nearest (0.22), vivid and energetic"),
        "historically_minded": ("retentive", "the past kept to hand (0.13); generalist, the nearest, went to speculative"),
        "whimsical": ("playful", "the nearest (0.44)"),
        "passionate": ("effusive", "the nearest (0.37)"),
        "cryptic": ("clear", "the nearest (0.23), the same axis"),
        "manic": ("temperamental", "the nearest (0.34)"),
        "improvisational": ("quick_witted", "answering on the spot; the embeddings are flat here (0.10)"),
        "experiential": ("aural_vark", "a way of taking things in, the learning-style kind (0.18); concrete, the nearest, went to abstract"),
    },
}


def cos(lst, a, b):
    for c in CLOSE[lst].get(a, []):
        if c["stem"] == b:
            return c["cos"]
    return None


def fill(lst, old, q, placed, lo, hi, new, rows):
    slots = list(range(lo, len(old) if hi is None else min(hi, len(old))))
    vac = []
    for i in slots:
        x = old[i]
        if x in q[lst] and x not in placed:
            new[i] = x; placed.add(x)
        else:
            vac.append(i)
    for i in list(vac):
        if old[i] in FIXED.get(lst, {}):
            s, why = FIXED[lst][old[i]]
            assert s in q[lst] and s not in placed, (lst, old[i], s)
            new[i] = s; placed.add(s); vac.remove(i)
            how = "moved up from position %d" % old.index(s) if s in old else "new"
            rows.append((i, old[i], s, cos(lst, old[i], s), how + "; " + why))
    while vac:
        best = None
        for i in vac:
            for c in CLOSE[lst][old[i]]:
                s = c["stem"]
                if s in placed or s not in q[lst] or s in EXCLUDE.get(lst, set()):
                    continue
                if best is None or c["cos"] > best[2]:
                    best = (i, s, c["cos"])
                break
        if best is None:
            raise SystemExit(f"{lst}: no candidate left for {[old[i] for i in vac]}")
        i, s, c = best
        new[i] = s; placed.add(s); vac.remove(i)
        how = "kept" if s == old[i] else ("moved up from position %d" % old.index(s) if s in old else "new")
        rows.append((i, old[i], s, c, how))


def build():
    q, _ = B.qualifiers()
    out = json.loads(json.dumps(B.CUR)); report = {}
    first, _r1, _q, _sc = B.build()          # the first draft, for roles.non_goal
    for lst in B.TIERS:
        kind, sub = lst.split(".")
        if lst == "roles.non_goal":
            out[kind][sub] = first[kind][sub]; report[lst] = None; continue
        old = B.CUR[kind][sub]; new = [None] * len(old); placed = set(); rows = []
        for lo, hi in TIER_BOUNDS:
            fill(lst, old, q, placed, lo, hi, new, rows)
        assert None not in new and len(set(new)) == len(new) and all(x in q[lst] for x in new), lst
        out[kind][sub] = new
        report[lst] = sorted(rows)
    (HERE / "goal_roles_and_traits.proposed.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                                                              encoding="utf-8")
    return out, report, q


if __name__ == "__main__":
    out, report, q = build()
    for lst, rows in report.items():
        if rows is None:
            print(f"\n== {lst}: as the first draft"); continue
        print(f"\n== {lst}:")
        for i, a, b, c, how in rows:
            tier = 1 if i < 30 else 2 if i < 40 else 3
            print(f"  T{tier} [{i:2d}] {a:22s} -> {b:22s} {'' if c is None else f'{c:.2f}':5s} ({how})")
