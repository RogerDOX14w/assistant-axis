"""Reroll candidates among the 85 standards-derived traits regenerated after W19
(2026-10-10), and the scan of their positive instructions for the instrument's name.

The rule is the 2026-10-04 reroll pass's (TRAITS_ADDED.md, "Trait generator V2",
"Reroll pass over the regenerated corpus (2026-10-04..06)";
roger/trait_reroll_pass_2026-10-04/trait_reroll_candidates.py) under Roger's
rulings of that pass:

* positive side only: negative-side faults are ignored (the negatives reach no
  data);
* invented motives are accepted (counted here for information only), invented
  particulars are welcome, em-dashes are not tested;
* the same judged fault (softened, urges_others, state, chat_frame,
  attitude_only, off_trait) in two or more of the five positive instructions
  makes the file a candidate;
* fewer than five distinct positive openings is an automatic reroll (the
  generator already rerolls once; a file still short here needs another roll or
  a hand edit); a question count other than 40 is listed with it.

The audit's pattern flags at two or more of five on the positive side
(names_label, echo_description, copied_example, open_statement, open_risky) are
listed apart, for information: on 2026-10-04 every one of them read by Roger or
the agent was a false positive (the label or the description's content in the
text).

    uv run python roger/pre_extraction_2026-10-09/standards85_candidates.py
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())
from data_analysis.audit_trait_instructions import pattern_checks  # noqa: E402

HERE = "roger/pre_extraction_2026-10-09"
AUDIT = f"{HERE}/standards85_audit"
# arms, newest first: w19r is the 2026-10-10 reroll of the five with a doubled opening; each stem is read from
# the newest arm that has it
ARMS = ("w19r", "w19")
BEFORE = f"{HERE}/standards85_before"
CORPUS = "data/traits/instructions"

JUDGED_FAULTS = ("softened", "urges_others", "state", "chat_frame", "attitude_only", "off_trait")
INFO_FAULTS = ("invented_motive",)
PATTERN = ("copied_example", "echo_description", "names_label", "open_statement", "open_risky")

# the instrument or its author named in an instruction (case-sensitive, so that
# "disc" or "hall" as ordinary words do not count; every hit is read by eye)
INSTRUMENT = {
    "HEXACO": r"\bHEXACO\b",
    "Big Five": r"\bBig[- ]Five\b|\bFive[- ]Factor\b|\bOCEAN\b",
    "MBTI": r"\bMBTI\b|\bMyers\b|\bBriggs\b|\bJung(?:ian)?\b",
    "VALS": r"\bVALS\b|\bStrategic Business Insights\b",
    "DISC": r"\bDISC\b|\bMarston\b",
    "VARK": r"\bVARK\b|\bFleming\b",
    "Holland": r"\bHolland(?:'s)?\b|\bRIASEC\b",
    "Bartle": r"\bBartle(?:'s)?\b",
    "Baumrind": r"\bBaumrind(?:'s)?\b",
    "Kohlberg": r"\bKohlberg(?:'s)?\b",
    "Allport": r"\bAllport(?:'s)?\b",
    "Tönnies": r"\bT(?:ö|o|oe)nnies\b",
    "Hall": r"\bHall(?:'s)?\b",
    "Gelfand": r"\bGelfand(?:'s)?\b",
    "Inglehart-Welzel": r"\bInglehart\b|\bWelzel\b|\bWorld Values Survey\b",
}
INSTRUMENT_RE = re.compile("|".join(f"(?:{p})" for p in INSTRUMENT.values()))


def load(path):
    return json.load(open(path, encoding="utf-8"))


def instrument_hits(docs):
    hits = []
    for stem, doc in sorted(docs.items()):
        for k, pair in enumerate(doc["instruction"]):
            m = INSTRUMENT_RE.search(pair["pos"])
            if m:
                hits.append({"stem": stem, "instruction": k, "match": m.group(0), "text": pair["pos"]})
    return hits


def main() -> None:
    stems = load(f"{AUDIT}/stems.json")
    docs, judged = {}, {}
    for stem in stems:
        arm = next(a for a in ARMS if os.path.exists(f"{AUDIT}/judged/{a}/{stem}.json"))
        docs[stem] = load(f"{AUDIT}/stage/corpus/{arm}/{stem}.json")
        judged[stem] = load(f"{AUDIT}/judged/{arm}/{stem}.json")
        corpus = load(f"{CORPUS}/{stem}.json")
        if corpus["instruction"] != docs[stem]["instruction"]:
            raise SystemExit(f"{stem}: the corpus file has changed since it was staged and judged")

    candidates, pattern_only, info, file_level_all = [], [], {}, {}
    by_fault = collections.Counter()
    for stem in stems:
        doc, j = docs[stem], judged[stem]
        pat = pattern_checks(doc)
        hits = collections.defaultdict(list)                 # fault -> [(k, quote)]
        for it in j["instruction_judge"]["items"]:
            k, side = int(it["id"][1]), it["id"].split("_")[1]
            if side != "pos":
                continue
            for fault in it["faults"]:
                if fault in JUDGED_FAULTS or fault in INFO_FAULTS:
                    hits[fault].append((k, it["quotes"].get(fault, "")))
        phits = collections.defaultdict(list)
        for it in pat["instructions"]:
            if it["side"] != "pos":
                continue
            for flag in it["flags"]:
                if flag in PATTERN:
                    phits[flag].append(int(it["id"][1]))
        found = {f: v for f, v in hits.items() if len(v) >= 2 and f in JUDGED_FAULTS}
        motives = {f: v for f, v in hits.items() if len(v) >= 2 and f in INFO_FAULTS}
        patterns = {f: v for f, v in phits.items() if len(v) >= 2}
        file_level = {}
        if pat["file"]["distinct_pos_forms"] < 5:
            file_level["openings"] = (f"{pat['file']['distinct_pos_forms']} distinct positive openings "
                                      f"({', '.join(pat['file']['pos_forms'])})")
        if pat["file"]["n_questions"] != 40:
            file_level["question_count"] = f"{pat['file']['n_questions']} questions"
        if pat["file"]["n_pairs"] != 5:
            file_level["pairs"] = f"{pat['file']['n_pairs']} instruction pairs"
        if file_level:
            file_level_all[stem] = file_level
        if motives:
            info[stem] = {f: [{"instruction": k, "quote": q} for k, q in v] for f, v in motives.items()}
        entry = {
            "stem": stem, "label": doc["positive_label"], "negative_label": doc["negative_label"],
            "description": doc["description"],
            "faults": {f: [{"instruction": k, "quote": q} for k, q in v] for f, v in found.items()},
            "single_faults": {f: [{"instruction": k, "quote": q} for k, q in v]
                              for f, v in hits.items() if len(v) == 1 and f in JUDGED_FAULTS},
            "patterns": {f: v for f, v in patterns.items()},
            "file_level": file_level,
            "pos": [p["pos"] for p in doc["instruction"]],
            "opening_rerolls": (doc.get("generator") or {}).get("opening_rerolls", 0),
        }
        if found or file_level:
            for f in found:
                by_fault[f] += 1
            for f in file_level:
                by_fault[f] += 1
            candidates.append(entry)
        elif patterns:
            pattern_only.append(entry)

    before = {s: load(f"{BEFORE}/{s}.json") for s in stems}
    scan_after, scan_before = instrument_hits(docs), instrument_hits(before)
    n_pos = sum(len(d["instruction"]) for d in docs.values())

    out = {
        "rule": "positive side only; two or more of five positive instructions with the same judged fault "
                f"({', '.join(JUDGED_FAULTS)}); fewer than five distinct positive openings; question count not "
                "40.  Invented motives accepted (listed under invented_motive_info); em-dashes not tested; "
                "negative side ignored (Roger, 2026-10-04).",
        "n_files": len(stems), "n_candidates": len(candidates), "by_fault": dict(by_fault),
        "candidates": candidates,
        "pattern_only": pattern_only,
        "invented_motive_info": info,
        "instrument_scan": {"n_positive_instructions": n_pos, "after": scan_after,
                            "before_n": len(scan_before), "before": scan_before},
    }
    path = f"{AUDIT}/reroll_candidates.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"{len(stems)} files; {len(candidates)} candidates; by fault: "
          + ", ".join(f"{k} {v}" for k, v in by_fault.most_common()))
    print(f"pattern flags only (not candidates): {len(pattern_only)}; "
          f"invented motive in 2+ of 5 (accepted): {len(info)}")
    print(f"instrument named in {len(scan_after)} of {n_pos} positive instructions "
          f"(before the regeneration: {len(scan_before)})")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
