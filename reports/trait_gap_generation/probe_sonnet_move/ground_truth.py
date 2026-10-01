"""The answers the second-opinion path is scored against, written down before the run.

Sources: Roger's marks and notes in random_traits_for_marks.md and his later replies of 2026-09-29;
for the other groups, what the group was chosen to test.  A word with no clear expected answer is
left out and is not scored.  Writes ground_truth.json beside this file.

    uv run python reports/trait_gap_generation/probe_sonnet_move/ground_truth.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORDS = [json.loads(line) for line in open(HERE.parent / "split_reference" / "expected_outcomes.jsonl", encoding="utf-8")]
NOT_ON = ["turned_away", "states", "physical", "roles"]

# Roger's 28 words marked "trait" with no caveat.
MARKED_TRAIT = """argumentative bothersome clinical corruptible Danish disrespectful full-time high-energy incestuous
lawless migratory noncompetitive nonturbulent part-time pedagogic presentable puzzling sophomore southeastern sympathetic
Tuscan twisted ungrammatical unobtrusive virulent warlike wishy-washy""".split() + ["Eastern Orthodox"]
SAMPLE = {w: (["trait"], "Roger marked it a trait") for w in MARKED_TRAIT}
SAMPLE["presentable"] = (["trait", "states"], 'Roger marked it a trait, and later called it "technically a state"')
SAMPLE["hit-and-run"] = (["turned_away"], 'Roger: "not a trait, this is an action"')
SAMPLE["illegal"] = (["turned_away"], "Roger: not a trait; people are not illegal, acts are")
SAMPLE["barehanded"] = (["states"], 'Roger: "trait: specifically a state", and "I can be currently barehanded ... so it\'s a state"')
SAMPLE["unreachable"] = (["trait", "states"], 'Roger: "trait (also a state)"')
SAMPLE["present"] = (["trait", "states"], 'Roger: "trait: also means not (literally) absent"')

BY_GROUP = {
    "plain_traits": (["trait"], "chosen as a plain trait word"),
    "figurative_person_words": (["trait"], "a word for things whose use for people is well known; Roger wants these kept"),
    "corpus_relational": (["trait"], "a corpus label"),
    "roger_examples_things": (["turned_away"], "Roger's own examples of words that should be rejected"),
    "things_held_out": (NOT_ON, "chosen as a word for things; graphic, linear and watertight are arguable"),
}


def main() -> None:
    out = {}
    for r in WORDS:
        w, g = r["word"], r["group"]
        if g == "sample_passed_v4":
            if w in SAMPLE:
                out[w] = {"group": g, "expected": SAMPLE[w][0], "source": SAMPLE[w][1]}
        elif g in BY_GROUP:
            out[w] = {"group": g, "expected": BY_GROUP[g][0], "source": BY_GROUP[g][1]}
    missing = [w for w in SAMPLE if w not in out]
    assert not missing, missing
    (HERE / "ground_truth.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(out), "words scored of", len(WORDS), "| not scored:", sorted(r["word"] for r in WORDS if r["word"] not in out))


if __name__ == "__main__":
    main()
