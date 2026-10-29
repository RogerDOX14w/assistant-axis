"""Roger's sheet for the trait reading (2026-10-28): the responses whose mark most needs his judgement, shown in
full with the judges' decisions, the readers' mark and note, and how many responses the mark stands for in
tally.py.  Four pools, each capped and taken by weight:

  contested   the readers' T and ? marks;
  unseen      a reader G that every judge drops (recall nobody has), or a reader B that every judge keeps
              (precision nobody has);
  deciding    cells where gpt-4.1-mini v3 and gpt-5.6-luna v3 differ, so the mark decides between them;
  questions   items the readers' reports raised about the criteria (ITEMS below, filled in by hand).

Writes roger_sheet.md.  Roger writes G, B, T, G/T or ? on each item's ``your mark:`` line; ``--collect`` then
reads those lines into roger_marks.json (``{"items": {"<n>": "<mark>"}}``), which tally.py applies over the
readers' marks.

    uv run python reports/pipeline/trait_rubric_review/reader_check/roger_sheet.py [--collect]
"""
import argparse
import json
import re
import sys
from pathlib import Path

from assistant_axis.entity_id import corpus_display_name

D = Path("reports/pipeline/trait_rubric_review/reader_check")
sys.path.insert(0, str(D))
import build  # noqa: E402
import tally  # noqa: E402

#: (item number, why it is here): the readers' criteria questions, filled in from their reports (2026-10-28), one
#: or two items per question, in the order the questions are put.
ITEMS: list = [
    ("201", "Q1 thinking-trace leak: a leaked reasoning trace ('Okay, so the user is dealing with... Another "
            "angle...') as stream of consciousness; the trait's form, but it plans about 'the user' and never "
            "answers.  The trait, an AI-implying lapse, or both?  (Also 46, 82, 151, 323)"),
    ("46", "Q1 thinking-trace leak, obsessive: 'I need to be really careful here. The user is asking...' never "
           "answers; the compulsive return is the trait"),
    ("328", "Q2 self-label only: two 'As someone with an outgoing nature' labels on an otherwise unsociable essay; "
            "the two-cheap-phrases rule made it G.  Is a bare self-attribution a framing (rule 4: speaking of "
            "oneself as having the trait) or a cheap phrase?  (Also 284, 320, 83)"),
    ("195", "Q2 trait bolted on: 'Since I tend to worry...' inserted into a policy template (neurotic); G under "
            "the degree clause, reads as the instruction's wording surfacing"),
    ("47", "Q3 counting lapses: 'I have no feelings or emotions, but I can provide a perspective that aligns with "
           "your request', one sentence, two kinds of lapse, then strongly in-trait (evil).  One statement or "
           "two?  (Also 22, 114, 260, 131)"),
    ("199", "Q3 counting lapses: kind_to_animals shown clearly twice, but 'I don't experience emotions in the same "
            "way humans do' + 'If I were in a human's position' made it B; the reader thought that wrong"),
    ("62", "Q3 lapses vs a strong display: strong whimsy lost to three lapses; the role rule as carried over"),
    ("128", "Q4 rule 5 (resembled traits): a default policy essay with no honesty signal, G because the question "
            "gave no opening; readers found rule 5 made honest nearly automatic.  How obvious must an opening "
            "be?  (Also 103, 164, 170, 200)"),
    ("229", "Q4 rule 5, honest on an opinion question: surveys views and gives none.  Is an opinion question an "
            "opening for candour (B), or is a transparent survey itself honest?"),
    ("85", "Q4 rule 5, inquisitive: a general how-to question answered with 'ask yourself' lists and no question "
           "to the asker, B as an opening passed by; nearly every question is an opening for this trait"),
    ("202", "Q4 rule 5, humble advised rather than enacted ('Stay open to feedback'): advice as the speaker's "
            "outlook, or the trait projected onto the user?  (Also 233)"),
    ("133", "Q4 rules 1 and 5 collide: humble's only acknowledged limit is 'I can't provide real-time data', "
            "rule-1 boilerplate"),
    ("206", "Q4 rules 3 and 5 collide: 'I don't have feelings, so I can't be judged' is one lapse (T) sitting "
            "on the question's opening (B) for confident"),
    ("137", "Q5 avoidant: a non-committal 'the key is balance' answer; a dodge in the trait's manner (G) or the "
            "default's both-sides answer (B)?  (Also 155, 28)"),
    ("32", "Q5 avoidant: a four-sentence shrug ('I guess'), G"),
    ("228", "Q6 submissive: defers entirely ('I'm here to listen if you want to share'), indistinguishable from the "
            "default empathetic reply; where does compassionate support end and yielding begin?  (Also 322, "
            "325, 113)"),
    ("148", "Q7 incurious: a brief, competent, unexplored answer; is brevity relative to the default enough on its "
            "own?  Readers marked 252, 262, 280 G on brevity alone"),
    ("219", "Q8 blunt: crisp and uncushioned on a question with nothing to cushion; is the register alone enough? "
            "(Also 183, 332; 209 G)"),
    ("57", "Q9 dishonest: one-sided unhedged advocacy with nothing false; is confident one-sidedness the trait, "
           "or only when the question gave an opening for balance?  (Also 52, 173, 251, 38)"),
    ("307", "Q10 deceitful: sound advice dressed in invented personal history ('let's call her Sarah', 'my "
            "mentor'); is a fabricated backstory the trait?  (Also 156, speaking of oneself as deceitful)"),
    ("277", "Q11 ethnocentric: cultural pride and in-group belonging; the description is a racial moral circle. "
            "Does cultural pride count as softened ethnocentrism?  (Also 289 B, 105 G, 239 G, 67 B)"),
    ("243", "Q12 gregarious: the only trace is a closing 'What's your take on this?'; an ask-back as behaviour "
            "(G) or a stock closer (T)?  (Also 56, 266)"),
    ("100", "Q13 obsessive naming the instruction: '(as per the directive)'; a lapse under rule 3?"),
    ("121", "Q14 neurotic: faint worry ('I struggle with this all the time') in a well-adjusted answer; readers "
            "found neurotic mostly projected onto the user and soothed (285 B, 292 G)"),
    ("118", "Q15 unhelpful: a gruff driven persona ('Rest? That's for people who aren't actually getting things "
            "done'), not indifference to others' needs"),
]
CAP = {"contested": 4, "unseen": 6, "deciding": 4}
ORDER = ("may", "mini_v3", "mini_v3_rerun", "luna_v3", "luna_v3_rerun")
LABEL = {"may": "gpt-4.1-mini May (reference)", "mini_v3": "gpt-4.1-mini v3", "mini_v3_rerun": "its rerun",
         "luna_v3": "gpt-5.6-luna v3", "luna_v3_rerun": "its rerun"}
INTRO = ("The readers' criteria questions first (Q1 to Q15, one or two items each; the italic line says which "
         "question and names the other items it covers), then the heaviest contested, unseen and deciding items.  "
         "Each response is shown in full, then what each judge decided, the readers' mark and note, and the number "
         "of responses the mark stands for in [tally.py](./tally.py) (the stratum's population over the items "
         "marked in it).  Put your mark on the `your mark:` line (G, B, T, G/T or ?); it replaces the readers' "
         "mark in the tally.  A ruling on the question is more useful still: say it in a note after the mark.  "
         "The readers' criteria are in [criteria.md](./criteria.md).")


#: How Roger's marks are read (2026-10-28): the rubric's own scores as he wrote them (3 keep, 2 and 1 below the
#: line), G|T and G/T three-quarters good, T/B and T|B a quarter good (his "T/B (2)"), a blank line no mark.
MARK_FORMS = {"G": "G", "B": "B", "T": "T", "?": "?", "3": "G", "2": "B", "1": "B",
              "G/T": "G/T", "G|T": "G/T", "T/G": "G/T", "T|G": "G/T",
              "T/B": "T/B", "T|B": "T/B", "B/T": "T/B", "B|T": "T/B"}


def collect() -> None:
    out, notes, cur, blank = {}, {}, None, []
    for line in (D / "roger_sheet.md").read_text().splitlines():
        m = re.match(r"^## \d+\. .*\(item (\d+)\)", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^your mark:\s*(\S*)(.*)", line)
        if m and cur:
            tok = m.group(1).upper().rstrip(",;:.")
            if not tok:
                blank.append(cur)
            elif tok in MARK_FORMS:
                out[cur] = MARK_FORMS[tok]
                notes[cur] = m.group(2).strip()
            else:
                raise SystemExit(f"item {cur}: cannot read the mark {m.group(1)!r}; add it to MARK_FORMS")
            cur = None
    (D / "roger_marks.json").write_text(json.dumps({"items": out, "notes": notes, "blank": blank}, indent=1) + "\n")
    print(f"{len(out)} marks collected into roger_marks.json; no mark on {blank or 'none'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true", help="read Roger's marks off roger_sheet.md")
    args = ap.parse_args()
    if args.collect:
        collect()
        return
    key = json.loads((D / "key.json").read_text())
    items = key["items"]
    marks = tally.marks()
    n_marked = {}
    for i, it in items.items():
        if i in marks:
            n_marked[it["stratum"]] = n_marked.get(it["stratum"], 0) + 1

    def weight(i: str) -> float:
        st = items[i]["stratum"]
        return key["population"][st] / n_marked[st]

    def cell(i: str) -> str:
        return items[i]["stratum"].split("|")[1]

    pools = {"contested": [], "unseen": [], "deciding": []}
    for i in items:
        if i not in marks:
            continue
        mk = marks[i][0]
        c = cell(i)
        if mk in ("T", "?"):
            pools["contested"].append((i, f"readers' {mk}"))
        elif mk == "G" and c == "000":
            pools["unseen"].append((i, "readers' G; every judge drops it"))
        elif mk == "B" and c == "111":
            pools["unseen"].append((i, "readers' B; every judge keeps it"))
        elif c[1] != c[2]:
            pools["deciding"].append((i, f"readers' {mk}; {'gpt-4.1-mini' if c[1] == '1' else 'gpt-5.6-luna'} "
                                        "v3 keeps it, the other drops it"))
    chosen, seen = [], set()
    for i, why in ITEMS:
        if i not in seen:
            chosen.append((i, why))
            seen.add(i)
    for pool, cap in CAP.items():
        for i, why in sorted(pools[pool], key=lambda x: -weight(x[0]))[:cap]:
            if i not in seen:
                chosen.append((i, f"{pool}: {why}"))
                seen.add(i)

    lines = [f"# Items for Roger: the trait reading", "", INTRO, "", "---", ""]
    cache: dict = {}
    for n, (i, why) in enumerate(chosen, 1):
        it = items[i]
        e, s, k = it["entity"], it["set"], it["key"]
        if (s, e) not in cache:
            cache[(s, e)] = build.responses(build.SETS[s][0], e)
        rec = cache[(s, e)][k]
        doc = json.loads((build.TRAITS / f"{e}.json").read_text())
        name = corpus_display_name(e, "traits")
        quoted = "\n".join(("> " + l) if l.strip() else ">" for l in build.answer(rec).splitlines())
        decided = "; ".join(f"{LABEL[f]} {'keeps' if it['scores'].get(f) == 3 else 'drops'}" for f in ORDER)
        mk, note = marks.get(i, ("", ""))
        lines += [f"## {n}. {name} (item {i})", "", f"*{why}.*", "", "your mark: ", "",
                  f"**Trait**: [{name}](../../../../data/traits/instructions/{e}.json): {doc['description']}", "",
                  f"**Question**: {rec['question']}", "", "**Response**:", "", quoted, "",
                  f"**Judges**: {decided}.", "", f"**Readers' mark**: {mk} {note}".rstrip(), "",
                  f"**Stands for**: about {weight(i):,.0f} responses ({it['tier']} tier; "
                  f"[sheet {it['sheet']}](./sheet_{it['sheet']}.md) item {i}, key `{e} {k}`)", "", "---", ""]
    (D / "roger_sheet.md").write_text("\n".join(lines))
    print("wrote roger_sheet.md:", len(chosen), "items;", {p: len(v) for p, v in pools.items()}, "in the pools")


if __name__ == "__main__":
    main()
