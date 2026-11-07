#!/usr/bin/env python3
"""Change the openings of the trait instructions in place, as chosen from the openings test of 2026-11-06.

The test ([`reports/opening_forms/openings_2026_11/`](../reports/opening_forms/openings_2026_11/)) ran each trait's
instructions under other openings with the body left as it was.  Roger chose the menu W5 W2 W7 W4 + A6 (2026-11-06):

    "Be someone who ..."                    -> "Be a person who ..."                    (W1 -> W5)
    "Become someone who ..."                   unchanged                                (W2)
    "From now on, you are someone who ..."  -> "From now on, you are a person who ..."  (W3 -> W7)
    "You are someone who ..."                  unchanged                                (W4)
    "You are X: ..."                        -> "This is who you are: X. ..."            (A1 -> A6)

The new texts are made by the builders that made the test's arms (``who_arms``, ``split_adjective``,
``adjective_arms`` in ``opening_form_experiment.py``), so that what goes into the corpus is what was tested.  A
negative instruction gets the same change when it opens as its positive does (the generator's rule: "A negative
instruction opens in the same way as its positive").  An instruction whose opening is not the expected one is
left alone and listed as a skip, for a person to look at.

Subcommands:

* ``edit``: make the edits.  By default the edited files go to ``<out>/staged/`` and the corpus is not touched;
  ``--apply`` writes the corpus.  Either way ``<out>/edits.json`` lists every edit and every skip.  Each edited
  file's ``hand_edits`` gains a dated record of what was changed.  A W edit that would say "person" twice in
  one sentence is not made, nor its negative's (Roger, 2026-11-06); ``--decisions`` leaves out the traits to
  be regenerated and the edits ``decide`` keeps unmade.
* ``review``: Claude Sonnet reads each edited positive instruction beside its original, blind (Version 1 and
  Version 2, the order run both ways) and says whether either reads noticeably worse.  ``<out>/review.json``;
  usage in ``<out>/usage.json``.
* ``grammar``: Claude Sonnet reads each "This is who you are: X." instruction alone (no original beside it) and
  says whether it is grammatical, three readings combined by majority; the A6 edits, or with ``--files`` the
  instructions of regenerated files.  ``<out>/grammar_<tag>.json``.
* ``decide``: Roger's rule for the A6 edits that break (2026-11-06): the trait's ten instructions are
  regenerated whole; a negative alone keeps its old text.  ``<out>/decisions.json``.
* ``regen-check``: the checks run after a regeneration, a failure meaning another roll (the September rule of
  TRAITS_ADDED.md § "Trait generator V2", "Reroll pass", with the openings, grammar and echo checks of this
  edit).  ``merge`` then copies the regenerated files into the corpus, refusing any whose other keys differ.
* ``compare``: sets of trait files side by side (the corpus at HEAD, the edited corpus, a trial regeneration) on
  the measures above, with the judged faults totalled over the traits judged in every set; no API calls.

The independent check that each edit stayed inside the opening is ``check_opening_edits.py``.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

import anthropic  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from assistant_axis.entity_id import judge_form_of_label  # noqa: E402
from assistant_axis.judge import RateLimiter, call_anthropic_judge_single, warn_if_low_parse_rate  # noqa: E402
from assistant_axis.judge_pricing import price_for_model  # noqa: E402
from data_analysis import audit_trait_instructions as audit  # noqa: E402
from data_analysis.opening_form_experiment import (  # noqa: E402
    ADJECTIVE_ARMS, WHO_SOURCES, WHO_SWAPS, CheckpointedUsage, adjective_arms, say, split_adjective, write_json)

logger = logging.getLogger("edit_trait_openings")

TRAITS_DIR = REPO / "data" / "traits" / "instructions"
DEFAULT_OUT = REPO / "reports" / "opening_forms" / "openings_2026_11" / "corpus_edit"
#: source arm -> the arm it becomes (Roger, 2026-11-06: W5 W2 W7 W4 + A6)
DEFAULT_MENU = {"W1": "W5", "W3": "W7", "A1": "A6"}
TEST_DIR = "reports/opening_forms/openings_2026_11/"
REVIEW_MODEL = "claude-sonnet-5-5"
# Sonnet 5.5 thinks before it answers unless told otherwise, and the thinking counts toward max_tokens
REVIEW_MAX_TOKENS = 3000


def parse_menu(text: str | None) -> dict[str, str]:
    """``W1=W5,W3=W7,A1=A6`` -> ``{"W1": "W5", ...}``, checked: a W source must become its own swap
    (``WHO_SWAPS``), and A1 an A arm the test built by rule for every trait (not A2, which needed a rewrite
    for most traits, nor A8)."""
    if not text:
        return dict(DEFAULT_MENU)
    menu = dict(part.split("=") for part in text.split(","))
    for src, dst in menu.items():
        if src in WHO_SOURCES:
            if WHO_SWAPS.get(dst, (None,))[0] != src:
                raise SystemExit(f"{src} can become only an arm made from it: "
                                 f"{[a for a, (s, _) in WHO_SWAPS.items() if s == src]}")
        elif src == "A1":
            if dst not in ADJECTIVE_ARMS or dst in ("A1", "A2", "A8"):
                raise SystemExit(f"A1 can become A3-A7 (made by rule for every trait), not {dst}")
        else:
            raise SystemExit(f"unknown source arm {src}; expected one of {list(WHO_SOURCES) + ['A1']}")
    return menu


def _frame(prefix: str) -> str:
    """An opening without its closing "who ": "Be someone who " -> "Be someone"."""
    return prefix[:-len(" who ")] if prefix.endswith(" who ") else prefix


def who_edit(text: str, menu: dict[str, str], wide: bool = False) -> tuple[str, str, str] | None:
    """(new text, source arm, target arm) when ``text`` opens with a W opening the menu changes.  ``wide``
    also takes the opening's frame followed by something other than "who " ("From now on, you are someone
    whose body ...", "... someone for whom ...", "Be someone who, when ..."), for a target that only puts "a
    person" in place of "someone" (W5-W7)."""
    for src, dst in menu.items():
        if src not in WHO_SOURCES:
            continue
        old, new = WHO_SOURCES[src], WHO_SWAPS[dst][1]
        if text.startswith(old):
            return new + text[len(old):], src, dst
        old_f, new_f = _frame(old), _frame(new)
        if (wide and old_f.endswith(" someone") and new_f == old_f[:-len("someone")] + "a person"
                and text.startswith(old_f) and text[len(old_f):len(old_f) + 1] in (" ", ",")):
            return new_f + text[len(old_f):], src, dst
    return None


def adjective_edit(text: str, menu: dict[str, str]) -> tuple[str, str, str] | None:
    """(new text, "A1", target arm) when ``text`` is a plain "You are X: ..." / "You are X. ..." instruction:
    split by the test's own parser and classified as that form by the audit's opening classifier too, so that
    "You are a man who ..." (a "someone who" form in other words) is not taken for one."""
    dst = menu.get("A1")
    if dst is None or audit.opening_form(text) != audit.FORM_YOU_ARE:
        return None
    adj = split_adjective(text)
    if adj is None:
        return None
    arm = adjective_arms(adj, None).get(dst)
    if arm is None or arm["built"] != "swap":
        return None
    return arm["text"], "A1", dst


def plan_file(stem: str, doc: dict, menu: dict[str, str], wide: bool = False,
              allow_echo: bool = False) -> tuple[list[dict], list[dict]]:
    """The edits and the skips for one trait file: ``(edits, skips)``.  Each edit names the instruction (index
    and side), the arms, whether it took the wide match, and both texts; a skip names the menu entry no
    positive instruction matched (with the openings the file has instead), a negative that does not open as
    its edited positive does, or a W edit left unmade because it would say "person" twice in one sentence
    (``person_echo``; ``allow_echo`` makes it), and then its negative too, so that the pair still opens alike."""
    edits, skips = [], []
    pairs = doc.get("instruction") or []
    found = set()
    for i, pair in enumerate(pairs):
        pos = str(pair.get("pos", ""))
        hit = who_edit(pos, menu, wide) or adjective_edit(pos, menu)
        if hit is None:
            continue
        new, src, dst = hit
        found.add(src)
        neg = pair.get("neg")
        if src in WHO_SOURCES and not allow_echo and person_echo(new):
            skips.append({"stem": stem, "index": i, "side": "pos", "wanted": src, "reason": "person echo",
                          "opening": " ".join(new.split()[:16])})
            if neg is not None:
                skips.append({"stem": stem, "index": i, "side": "neg", "wanted": src,
                              "reason": "its positive is kept (person echo)", "opening": " ".join(neg.split()[:8])})
            continue
        edits.append({"stem": stem, "index": i, "side": "pos", "from": src, "to": dst, "old": pos, "new": new,
                      "wide": _is_wide(pos, src)})
        if neg is None:
            continue
        nhit = who_edit(neg, menu, wide) if src in WHO_SOURCES else adjective_edit(neg, menu)
        if nhit is not None and nhit[1] == src and src in WHO_SOURCES and not allow_echo and person_echo(nhit[0]):
            skips.append({"stem": stem, "index": i, "side": "neg", "wanted": src, "reason": "person echo",
                          "opening": " ".join(nhit[0].split()[:16])})
        elif nhit is not None and nhit[1] == src:
            edits.append({"stem": stem, "index": i, "side": "neg", "from": src, "to": nhit[2], "old": neg,
                          "new": nhit[0], "wide": _is_wide(neg, src)})
        else:
            skips.append({"stem": stem, "index": i, "side": "neg", "wanted": src, "reason": "neg opens otherwise",
                          "opening": " ".join(neg.split()[:8])})
    for src in menu:
        if src not in found:
            skips.append({"stem": stem, "index": None, "side": "pos", "wanted": src, "reason": "no such opening",
                          "openings": [" ".join(str(p.get("pos", "")).split()[:7]) for p in pairs]})
    return balance(stem, pairs, edits, skips, wide, allow_echo)


#: Roger, 2026-11-07: a trait the echo rule leaves with three "someone" openings has its "You are someone who"
#: (W4) changed to "You are a person who" (W6) as well; one left with three "a person" openings keeps its "Be
#: someone who" (W1, the smaller of the two tested gains) unedited
REBALANCE = {"W4": "W6"}


def final_nouns(pairs: list[dict], edits: list[dict]) -> list[str | None]:
    """The opening noun of each positive once ``edits`` are made."""
    texts = [str(p.get("pos", "")) for p in pairs]
    for e in edits:
        if e["side"] == "pos":
            texts[e["index"]] = e["new"]
    return [opening_noun(t) for t in texts]


def balance(stem: str, pairs: list[dict], edits: list[dict], skips: list[dict], wide: bool,
            allow_echo: bool) -> tuple[list[dict], list[dict]]:
    """Roger's rule for the openings (2026-11-06): no more than two of the five positives open with "someone",
    nor with "a person".  Where the planned edits leave three "someone" openings, the first unedited W4
    positive becomes W6 (with its negative, if it opens alike), unless that would make a person echo; where they
    leave three "a person" openings, the W1 edit (and its negative) is not made.  A file still out of balance
    gets an "unbalanced" skip, which ``decide`` turns into a regeneration."""
    nouns = final_nouns(pairs, edits)
    if nouns.count("someone") > 2:
        edited = {e["index"] for e in edits if e["side"] == "pos"}
        for i, pair in enumerate(pairs):
            pos = str(pair.get("pos", ""))
            hit = None if i in edited else who_edit(pos, REBALANCE, wide)
            if hit is None:
                continue
            if not allow_echo and person_echo(hit[0]):
                skips.append({"stem": stem, "index": i, "side": "pos", "wanted": "W4",
                              "reason": "rebalance would make a person echo", "opening": " ".join(hit[0].split()[:16])})
                continue
            edits.append({"stem": stem, "index": i, "side": "pos", "from": "W4", "to": "W6", "old": pos,
                          "new": hit[0], "wide": _is_wide(pos, "W4"), "rebalance": True})
            neg = pair.get("neg")
            nhit = who_edit(str(neg), REBALANCE, wide) if neg is not None else None
            if nhit is not None and (allow_echo or not person_echo(nhit[0])):
                edits.append({"stem": stem, "index": i, "side": "neg", "from": "W4", "to": "W6", "old": neg,
                              "new": nhit[0], "wide": _is_wide(neg, "W4"), "rebalance": True})
            elif neg is not None:
                skips.append({"stem": stem, "index": i, "side": "neg", "wanted": "W4",
                              "reason": "person echo" if nhit is not None else "neg opens otherwise",
                              "opening": " ".join(str(neg).split()[:8])})
            break
    elif nouns.count("a person") > 2:
        w1 = [e for e in edits if e["from"] == "W1"]
        if w1:
            edits = [e for e in edits if e["from"] != "W1"]
            for e in w1:
                skips.append({"stem": stem, "index": e["index"], "side": e["side"], "wanted": "W1",
                              "reason": "kept: 'a person' would open three of five", "opening": " ".join(e["new"].split()[:16])})
    nouns = final_nouns(pairs, edits)
    if nouns.count("someone") > 2 or nouns.count("a person") > 2:
        skips.append({"stem": stem, "index": None, "side": "pos", "wanted": None, "reason": "unbalanced",
                      "nouns": nouns})
    return edits, skips


def _is_wide(text: str, src: str) -> bool:
    """Whether a W edit of ``text`` took the wide match (its opening is not the tested string)."""
    return src in WHO_SOURCES and not text.startswith(WHO_SOURCES[src])


PERSON_WORD = re.compile(r"\bperson(?:'s|s|hood)?\b", re.I)
SENTENCE_END = re.compile(r"(?<=[.!?])(?:\s|\Z)")


def person_echo(text: str) -> bool:
    """Whether ``text`` says "person" again in the sentence that opens "... a person": "Be a person who argues
    until the other person comes around."  Roger, 2026-11-06: an edit that makes one is not made ("'a person
    who ... person' => revert to original")."""
    i = text.find("a person")
    if i < 0:
        return False
    rest = text[i + len("a person"):]
    m = SENTENCE_END.search(rest)
    return bool(PERSON_WORD.search(rest[:m.start()] if m else rest))


def opening_of(arm: str) -> str:
    """An arm's opening as the hand_edits record names it."""
    if arm in WHO_SOURCES:
        return WHO_SOURCES[arm].strip()
    if arm in WHO_SWAPS:
        return WHO_SWAPS[arm][1].strip()
    return {"A1": "You are X:", "A3": "By nature, you are X:", "A4": "At heart, you are X:",
            "A5": "You have always been X:", "A6": "This is who you are: X.", "A7": "You are someone who is X:"}[arm]


def hand_edit_record(edits: list[dict], today: str) -> str:
    """One dated line for the file's ``hand_edits``: which instructions changed and how."""
    parts = []
    for (i, src, dst), sides in _group(edits).items():
        parts.append(f"p{i} {'+'.join(sides)} '{opening_of(src)}' -> '{opening_of(dst)}'")
    return (f"{today}: openings changed by edit_trait_openings.py after the openings test ({TEST_DIR}): "
            + ", ".join(parts))


def _group(edits: list[dict]) -> dict[tuple, list[str]]:
    out: dict[tuple, list[str]] = {}
    for e in edits:
        out.setdefault((e["index"], e["from"], e["to"]), []).append(e["side"])
    return out


def apply_edits(doc: dict, edits: list[dict], today: str) -> dict:
    """A copy of ``doc`` with ``edits`` made and the record appended to ``hand_edits``; every other key, and
    the order of the keys, as it was."""
    out = json.loads(json.dumps(doc))
    for e in edits:
        pair = out["instruction"][e["index"]]
        if pair[e["side"]] != e["old"]:
            raise ValueError(f"{e['stem']} p{e['index']} {e['side']}: the text changed since it was planned")
        pair[e["side"]] = e["new"]
    record = hand_edit_record(edits, today)
    out["hand_edits"] = f"{out['hand_edits']}; {record}" if out.get("hand_edits") else record
    return out


def dump(doc: dict) -> str:
    """The corpus's file format (``regenerate_trait_instructions.atomic_write_json``)."""
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def load_decisions(path: str | None) -> dict:
    """The decisions file ``decide`` writes: ``{"regenerate": {stem: reason}, "keep": [{"stem", "index", "side",
    "reason"}]}``; empty when no path is given."""
    if not path:
        return {"regenerate": {}, "keep": []}
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"regenerate": dict(d.get("regenerate") or {}), "keep": list(d.get("keep") or [])}


def apply_decisions(edits: list[dict], decisions: dict) -> tuple[list[dict], list[dict]]:
    """``(edits still to make, skips)``: an edit the decisions keep unmade is a skip with their reason, and so is
    the negative of a positive kept, so that the pair still opens alike."""
    keep = {(k["stem"], k["index"], k["side"]): k["reason"] for k in decisions.get("keep", [])}
    kept_pos, out, skips = set(), [], []
    for e in sorted(edits, key=lambda e: (e["stem"], e["index"], e["side"] != "pos")):
        why = keep.get((e["stem"], e["index"], e["side"]))
        if why is None and e["side"] == "neg" and (e["stem"], e["index"]) in kept_pos:
            why = "its positive is kept"
        if why is None:
            out.append(e)
            continue
        if e["side"] == "pos":
            kept_pos.add((e["stem"], e["index"]))
        skips.append({"stem": e["stem"], "index": e["index"], "side": e["side"], "wanted": e["from"],
                      "reason": f"kept: {why}", "opening": " ".join(e["new"].split()[:16])})
    return out, skips


def cmd_edit(args) -> None:
    menu = parse_menu(args.menu)
    traits_dir, out = Path(args.traits_dir), Path(args.out)
    stems = args.traits or sorted(p.stem for p in traits_dir.glob("*.json"))
    today = args.date or datetime.date.today().isoformat()
    decisions = load_decisions(args.decisions)
    all_edits, all_skips, changed = [], [], {}
    for stem in stems:
        doc = json.loads((traits_dir / f"{stem}.json").read_text(encoding="utf-8"))
        if not doc.get("instruction"):
            continue
        if stem in decisions["regenerate"]:
            all_skips.append({"stem": stem, "index": None, "side": "both", "wanted": None,
                              "reason": f"regenerated: {decisions['regenerate'][stem]}"})
            continue
        edits, skips = plan_file(stem, doc, menu, args.wide, args.allow_person_echo)
        edits, kept = apply_decisions(edits, decisions)
        skips += kept
        if args.sides == "pos":
            edits = [e for e in edits if e["side"] == "pos"]
            skips = [s for s in skips if s["side"] == "pos"]
        all_edits += edits
        all_skips += skips
        if edits:
            changed[stem] = apply_edits(doc, edits, today)
    target = traits_dir if args.apply else out / "staged"
    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)
        if not args.apply:   # the staged directory holds this run's files only
            for old in target.glob("*.json"):
                old.unlink()
        for stem, doc in changed.items():
            path = target / f"{stem}.json"
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(dump(doc), encoding="utf-8")
            os.replace(tmp, path)
        write_json(out / "edits.json", {
            "written": today, "menu": menu, "sides": args.sides, "wide": args.wide,
            "allow_person_echo": bool(args.allow_person_echo), "decisions": args.decisions,
            "traits_dir": str(traits_dir.relative_to(REPO))
            if traits_dir.is_relative_to(REPO) else str(traits_dir), "applied": bool(args.apply),
            "files": sorted(changed), "edits": all_edits, "skips": all_skips})
    by = {}
    for e in all_edits:
        by[(e["side"], e["from"], e["to"])] = by.get((e["side"], e["from"], e["to"]), 0) + 1
    say(f"{len(stems)} traits; {len(changed)} files changed{' (dry run: nothing written)' if args.dry_run else ''}"
        f"{'' if args.dry_run else f', written to {target}'}")
    for (side, src, dst), n in sorted(by.items()):
        n_wide = sum(1 for e in all_edits if (e["side"], e["from"], e["to"]) == (side, src, dst) and e["wide"])
        say(f"  {side} {src} -> {dst}: {n}{f' ({n_wide} by the wide match)' if n_wide else ''}")
    reasons = {}
    for s in all_skips:
        k = (s["side"], s["wanted"], s["reason"] if not s["reason"].startswith("kept: ") else s["reason"][:40])
        reasons[k] = reasons.get(k, 0) + 1
    for (side, src, why), n in sorted(reasons.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        if not why.startswith("regenerated"):
            say(f"  skipped {side} {src}: {why}: {n}")
    n_regen = sum(1 for s in all_skips if s["reason"].startswith("regenerated"))
    if n_regen:
        say(f"  left for regeneration (whole file): {n_regen}")
    count = {}
    for e in all_edits:
        if e["side"] == "pos":
            count[(e["stem"], e["from"])] = count.get((e["stem"], e["from"]), 0) + 1
    dup = sorted(k for k, n in count.items() if n > 1)
    if dup:
        say(f"  traits with the same source opening more than once (all edited): {len(dup)}: {dup[:20]}")


# ---------------------------------------------------------------------------
# review: does the edited instruction read noticeably worse?
# ---------------------------------------------------------------------------

REVIEW_PROMPT = """Below are two versions of a system prompt that tells a language model which personality \
trait to have. They differ only in how they open; the rest is word for word the same.

The trait: **{label}**. {description}

Version 1:
<prompt>
{first}
</prompt>

Version 2:
<prompt>
{second}
</prompt>

Does either version read noticeably worse than the other, as English and as a statement of who the model is \
to be: awkward, ungrammatical, repetitive, or less clear? Small differences of taste do not count; answer \
"neither" unless one version is clearly worse.

Give your reason in one short sentence, then, on a line of its own, a JSON object:

{{"worse": "1", "2" or "neither"}}"""


def review_prompt(label: str, description: str, first: str, second: str) -> str:
    return REVIEW_PROMPT.format(label=judge_form_of_label(label), description=description, first=first,
                                second=second)


def parse_review(text: str | None) -> str | None:
    """"1", "2" or "neither" from the reply's last JSON object, or None."""
    if not text:
        return None
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text))):
        try:
            v = str(json.loads(m.group(0)).get("worse", "")).strip().lower()
        except (json.JSONDecodeError, AttributeError):
            continue
        if v in ("1", "2", "neither"):
            return v
    return None


def edited_verdict(order: str, answer: str | None) -> str | None:
    """What an answer says of the edit: "edited worse", "original worse" or "neither".  In order "straight"
    Version 1 is the original; in "swapped" it is the edited text."""
    if answer is None:
        return None
    if answer == "neither":
        return "neither"
    edited = "2" if order == "straight" else "1"
    return "edited worse" if answer == edited else "original worse"


def review_items(edits: list[dict]) -> list[dict]:
    """The positive edits, one item per order."""
    return [{"key": f"{e['stem']}|p{e['index']}|{order}", "stem": e["stem"], "index": e["index"],
             "order": order, "first": e["old"] if order == "straight" else e["new"],
             "second": e["new"] if order == "straight" else e["old"]}
            for e in edits if e["side"] == "pos" for order in ("straight", "swapped")]


def summarise_review(done: dict) -> dict:
    """Per edit: the two verdicts, and flagged when either says the edited text reads worse."""
    per = {}
    for key, r in done.items():
        stem, p, order = key.split("|")
        per.setdefault(f"{stem}|{p}", {})[order] = r.get("verdict")
    flagged = sorted(k for k, v in per.items() if "edited worse" in v.values())
    return {"edits": len(per), "flagged": flagged,
            "answered": sum(1 for r in done.values() if r.get("verdict") is not None), "asked": len(done)}


async def review(args) -> None:
    out = Path(args.out)
    plan = json.loads((out / "edits.json").read_text(encoding="utf-8"))
    traits_dir = REPO / plan["traits_dir"] if not Path(plan["traits_dir"]).is_absolute() else Path(plan["traits_dir"])
    docs = {}
    path = out / "review.json"
    done = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    todo = []
    for item in review_items(plan["edits"]):
        if item["key"] in done and done[item["key"]].get("verdict") is not None:
            continue
        if item["stem"] not in docs:
            docs[item["stem"]] = json.loads((traits_dir / f"{item['stem']}.json").read_text(encoding="utf-8"))
        doc = docs[item["stem"]]
        todo.append((item, review_prompt(doc.get("positive_label", item["stem"]), doc.get("description", ""),
                                         item["first"], item["second"])))
    if args.limit:
        todo = todo[:args.limit]
    rate_in, rate_out = price_for_model(args.model)
    est = sum(len(p) / 3.6 * rate_in + args.est_output_tokens * rate_out for _, p in todo) / 1e6
    say(f"{len(todo)} review calls with {args.model}; about ${est:.2f} at {args.est_output_tokens} output tokens a call")
    if args.dry_run or not todo:
        if todo and args.show:
            print(todo[0][1])
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    client = anthropic.AsyncAnthropic()
    limiter = RateLimiter(args.requests_per_second)
    usage = CheckpointedUsage(out)
    sem = asyncio.Semaphore(args.concurrency)

    async def one(item, prompt):
        async with sem:
            text = await call_anthropic_judge_single(client, prompt, args.model, REVIEW_MAX_TOKENS, limiter,
                                                     usage=usage, reject_truncated=True)
        answer = parse_review(text)
        done[item["key"]] = {"order": item["order"], "answer": answer,
                             "verdict": edited_verdict(item["order"], answer), "reply": text, "model": args.model}

    try:
        await asyncio.gather(*(one(i, p) for i, p in todo))
    finally:
        usage.close()
        write_json(path, done)
    s = summarise_review(done)
    warn_if_low_parse_rate(label=f"edit_trait_openings review:{args.model}",
                           n_ok=sum(1 for i, _ in todo if done[i["key"]]["verdict"] is not None),
                           n_total=len(todo), logger_obj=logger)
    say(f"wrote {path}: {s['edits']} edits reviewed, {s['answered']} of {s['asked']} answers parsed; "
        f"{len(s['flagged'])} flagged (either order says the edited text reads worse)")
    for k in s["flagged"][:40]:
        say(f"  {k}")


def cmd_review(args) -> None:
    asyncio.run(review(args))


# ---------------------------------------------------------------------------
# grammar: does a "This is who you are: X." instruction read as English, on its own?
# ---------------------------------------------------------------------------

GRAMMAR_PROMPT = """Below is a short text that tells a language model what kind of person to be.

<text>
{text}
</text>

Read its first two sentences. Is each one grammatical English, as a careful writer would write it?

The text opens with "This is who you are:" followed by a word or a short phrase for what the person is, and a \
full stop. That opening is deliberate, and it is fine whenever the word or phrase after the colon says what the \
person is.

Count as broken: a verb whose subject is missing or wrong (as in "This is who you are: loyal and keep your \
promises."), a phrase with no main verb standing as a sentence of its own (other than the opening's word or \
phrase), or words that no longer fit the words around them. Style, taste, and what the text says do not count.

Give your reason in one short sentence, then, on a line of its own, a JSON object:

{{"verdict": "ok" or "broken"}}"""

#: Roger, 2026-10-13: a deciding call to a model that runs at temperature 1 is asked three times and the
#: answers combined by majority
GRAMMAR_READINGS = 3


def grammar_prompt(text: str) -> str:
    return GRAMMAR_PROMPT.format(text=text)


def parse_grammar(text: str | None) -> str | None:
    """"ok" or "broken" from the reply's last JSON object, or None."""
    if not text:
        return None
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text))):
        try:
            v = str(json.loads(m.group(0)).get("verdict", "")).strip().lower()
        except (json.JSONDecodeError, AttributeError):
            continue
        if v in ("ok", "broken"):
            return v
    return None


def text_sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def grammar_targets_from_edits(plan: dict) -> list[dict]:
    """Every A1 -> A6 edit of the plan (both sides), as the text the corpus would get."""
    return [{"stem": e["stem"], "index": e["index"], "side": e["side"], "text": e["new"]}
            for e in plan["edits"] if e["from"] == "A1"]


def grammar_targets_from_files(traits_dir: Path, stems: list[str]) -> list[dict]:
    """Every instruction, either side, that opens "This is who you are" in these files (a regeneration)."""
    out = []
    for stem in stems:
        doc = json.loads((traits_dir / f"{stem}.json").read_text(encoding="utf-8"))
        for i, pair in enumerate(doc.get("instruction") or []):
            for side in ("pos", "neg"):
                text = str(pair.get(side, ""))
                if audit.opening_form(text) == audit.FORM_THIS_IS_WHO:
                    out.append({"stem": stem, "index": i, "side": side, "text": text})
    return out


def grammar_key(t: dict, k: int) -> str:
    return f"{t['stem']}|p{t['index']}|{t['side']}|{text_sha(t['text'])}|r{k}"


def grammar_verdicts(answers: dict, targets: list[dict], readings: int) -> list[dict]:
    """Per target, the readings' answers and their majority: "broken", "ok", "unsure" (a tie) or None (no
    answer parsed)."""
    out = []
    for t in targets:
        got = [answers.get(grammar_key(t, k), {}).get("verdict") for k in range(readings)]
        n_b, n_o = got.count("broken"), got.count("ok")
        verdict = None if n_b + n_o == 0 else "broken" if n_b > n_o else "ok" if n_o > n_b else "unsure"
        out.append({**t, "answers": got, "verdict": verdict})
    return out


async def grammar(args) -> None:
    out = Path(args.out)
    if args.files:
        stems = (json.loads(Path(args.stems).read_text(encoding="utf-8")) if args.stems
                 else sorted(p.stem for p in Path(args.files).glob("*.json")))
        targets = grammar_targets_from_files(Path(args.files), stems)
    else:
        targets = grammar_targets_from_edits(json.loads((out / "edits.json").read_text(encoding="utf-8")))
    if args.side != "both":
        # the regen check rolls again only on a broken positive; a negative reaches no data
        targets = [t for t in targets if t["side"] == args.side]
    path = out / f"grammar_{args.tag}.json"
    record = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    answers = record.get("answers", {})
    todo = [(grammar_key(t, k), t) for t in targets for k in range(args.readings)
            if answers.get(grammar_key(t, k), {}).get("verdict") is None]
    if args.limit:
        todo = todo[:args.limit]
    rate_in, rate_out = price_for_model(args.model)
    est = sum(len(grammar_prompt(t["text"])) / 3.6 * rate_in + args.est_output_tokens * rate_out
              for _, t in todo) / 1e6
    say(f"{len(targets)} instructions x {args.readings} readings: {len(todo)} calls to make with {args.model}; "
        f"about ${est:.2f} at {args.est_output_tokens} output tokens a call")
    if args.dry_run or not todo:
        if todo and args.show:
            print(grammar_prompt(todo[0][1]["text"]))
        if not todo:
            _write_grammar(path, args, targets, answers)
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    client = anthropic.AsyncAnthropic()
    limiter = RateLimiter(args.requests_per_second)
    usage = CheckpointedUsage(out)
    sem = asyncio.Semaphore(args.concurrency)

    async def one(key, t):
        async with sem:
            reply = await call_anthropic_judge_single(client, grammar_prompt(t["text"]), args.model,
                                                      REVIEW_MAX_TOKENS, limiter, usage=usage, reject_truncated=True)
        answers[key] = {"verdict": parse_grammar(reply), "reply": reply, "model": args.model}

    try:
        await asyncio.gather(*(one(k, t) for k, t in todo))
    finally:
        usage.close()
        _write_grammar(path, args, targets, answers)
    warn_if_low_parse_rate(label=f"edit_trait_openings grammar:{args.model}",
                           n_ok=sum(1 for k, _ in todo if answers.get(k, {}).get("verdict") is not None),
                           n_total=len(todo), logger_obj=logger)


def _write_grammar(path: Path, args, targets: list[dict], answers: dict) -> None:
    verdicts = grammar_verdicts(answers, targets, args.readings)
    write_json(path, {"model": args.model, "readings": args.readings, "prompt_sha256": text_sha(GRAMMAR_PROMPT),
                      "answers": answers, "verdicts": verdicts})
    count = {}
    for v in verdicts:
        count[(v["side"], v["verdict"])] = count.get((v["side"], v["verdict"]), 0) + 1
    say(f"wrote {path}: " + ", ".join(f"{s} {v}: {n}" for (s, v), n in sorted(count.items(), key=str)))
    for v in verdicts:
        if v["verdict"] in ("broken", "unsure"):
            say(f"  {v['verdict']:6s} {v['side']} {v['stem']} p{v['index']} {v['answers']}: {v['text'][:110]}")


def cmd_grammar(args) -> None:
    asyncio.run(grammar(args))


# ---------------------------------------------------------------------------
# decide: which traits are regenerated whole, which edits are left unmade
# ---------------------------------------------------------------------------

def decide(plan: dict, review_done: dict, verdicts: list[dict]) -> dict:
    """Roger, 2026-11-06: a trait whose A6 edit reads as broken English (the grammar check's majority, or the
    blind before-and-after review's flag on that edit) gets all ten instructions regenerated; a negative whose
    A6 edit alone is broken keeps its original text instead (negatives reach no data).  Ties are listed apart,
    for a person to read."""
    a6 = {(e["stem"], e["index"], e["side"]) for e in plan["edits"] if e["from"] == "A1"}
    regenerate: dict[str, list[str]] = {}
    for v in verdicts:
        if v["side"] == "pos" and v["verdict"] == "broken":
            regenerate.setdefault(v["stem"], []).append(
                f"p{v['index']} 'This is who you are' edit read as broken English by "
                f"{v['answers'].count('broken')} of {len(v['answers'])} readings")
    for key in summarise_review(review_done)["flagged"] if review_done else []:
        stem, p = key.split("|")
        if (stem, int(p[1:]), "pos") in a6:
            regenerate.setdefault(stem, []).append(f"{p} 'This is who you are' edit read worse than the original "
                                                   f"in the blind before-and-after review")
    for s in plan.get("skips", []):
        if s["reason"] == "unbalanced":
            regenerate.setdefault(s["stem"], []).append(
                f"openings out of balance after the edit ({s['nouns'].count('someone')} 'someone', "
                f"{s['nouns'].count('a person')} 'a person'; Roger's rule: no more than two of either)")
    keep = [{"stem": v["stem"], "index": v["index"], "side": "neg",
             "reason": f"'This is who you are' edit read as broken English by {v['answers'].count('broken')} of "
                       f"{len(v['answers'])} readings"}
            for v in verdicts if v["side"] == "neg" and v["verdict"] == "broken" and v["stem"] not in regenerate]
    unsure = [{k: v[k] for k in ("stem", "index", "side", "answers", "text")}
              for v in verdicts if v["verdict"] in ("unsure", None)]
    return {"regenerate": {s: "; ".join(r) for s, r in sorted(regenerate.items())}, "keep": keep, "unsure": unsure}


def cmd_decide(args) -> None:
    out = Path(args.out)
    plan = json.loads((out / "edits.json").read_text(encoding="utf-8"))
    review_path = out / "review.json"
    review_done = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
    verdicts = json.loads((out / f"grammar_{args.tag}.json").read_text(encoding="utf-8"))["verdicts"]
    d = decide(plan, review_done, verdicts)
    path = out / "decisions.json"
    if not args.dry_run:
        write_json(path, d)
    say(f"{'(dry run) ' if args.dry_run else f'wrote {path}: '}{len(d['regenerate'])} traits to regenerate, "
        f"{len(d['keep'])} negatives kept, {len(d['unsure'])} unsure")
    for s, why in d["regenerate"].items():
        say(f"  regenerate {s}: {why}")
    for k in d["keep"]:
        say(f"  keep {k['stem']} p{k['index']} neg")
    for u in d["unsure"]:
        say(f"  UNSURE {u['stem']} p{u['index']} {u['side']} {u['answers']}: {u['text'][:100]}")


# ---------------------------------------------------------------------------
# regen-check: the checks after a regeneration, where a failure means another roll
# ---------------------------------------------------------------------------

#: The September acceptance rule as Roger applied it on 2026-10-04 (TRAITS_ADDED.md § "Trait generator V2",
#: "Reroll pass"): the same positive-side fault in two or more of the five is a reroll; one can slide.
#: Negative-side faults are ignored (weak_opposite is one), invented motives are accepted, dashes not tested.
REROLL_JUDGED = ("softened", "urges_others", "state", "chat_frame", "attitude_only", "off_trait")
REROLL_PATTERNS = ("copied_example", "echo_description", "open_statement", "open_risky")
#: pattern flags counted and reported but never a reason to roll again.  names_label (a positive naming its own
#: label) was a reroll reason until 2026-11-07, when Roger dropped it ("Drop it as a reroll reason, but list it as
#: something to keep monitoring"): on the full trial regeneration 34 of the 39 traits it caught were membership,
#: body or status traits whose label is their content (Russian, male, married, left-handed), each accepted by hand
#: in October; kept as a measure for the open self-labelling question (TRAITS_ADDED.md, "Openings edit").
MONITORED_PATTERNS = ("names_label",)
#: an opening frame and the noun it puts the reader in: "Be a person who", "You are someone whose", "This is who
#: you are: a person steeped in" (the noun right after the frame, not one later in the sentence)
OPENING_NOUN = re.compile(r"(?i)^\s*(?:be|become|from now on,? you are|you are|you're|this is who you are:)\s+"
                          r"(someone|a person)\b")
SOMEONE = re.compile(r"\bsomeone\b", re.I)
A_PERSON = re.compile(r"\ba person\b", re.I)


def opening_noun(text: str) -> str | None:
    """"someone" or "a person" when the instruction's opening frame names one, else None."""
    m = OPENING_NOUN.match(text)
    return m.group(1).lower() if m else None


def _opening_words(text: str, n: int = 8) -> str:
    return " ".join(text.split()[:n])


#: the phrase of a "This is who you are: X." opening, up to its full stop
THIS_IS_WHO_PHRASE = re.compile(r"(?i)^\s*this is who you are:\s*([^.]*)")
PERSON_ANY = re.compile(r"\bperson\b", re.I)


def wide_opening_word(text: str, word: str) -> bool:
    """Whether the instruction's opening says ``word`` ("someone" or "a person") on the wider reading: the noun
    of the opening frame, or, in a "This is who you are: X." opening, anywhere in X ("a gray-haired person", "the
    person in any room who ..."; for "a person" any "person" counts).  The narrow reading is ``opening_noun``."""
    if opening_noun(text) == word:
        return True
    m = THIS_IS_WHO_PHRASE.match(text)
    if not m:
        return False
    return bool((SOMEONE if word == "someone" else PERSON_ANY).search(m.group(1)))


def positive_hits(pc: dict, judged: dict | None, flags: tuple[str, ...] = REROLL_PATTERNS) -> dict[str, list[int]]:
    """The reroll rule's faults on the positive side, each with the pairs it is found in: the pattern flags of
    ``audit.pattern_checks`` (``pc``) named in ``flags`` (by default the reroll rule's; ``MONITORED_PATTERNS`` for
    the measures kept) and, when the file is judged, the judged faults."""
    hits: dict[str, list[int]] = {}
    for it in pc["instructions"]:
        if it["side"] == "pos":
            for flag in it["flags"]:
                if flag in flags:
                    hits.setdefault(flag, []).append(int(it["id"][1]))
    if judged is not None:
        for it in judged["instruction_judge"]["items"]:
            if it["id"].endswith("_pos"):
                for fault in it["faults"]:
                    if fault in REROLL_JUDGED:
                        hits.setdefault(fault, []).append(int(it["id"][1]))
    return hits


def regen_problems(doc: dict, judged: dict | None, verdicts: list[dict]) -> tuple[list[str], list[str]]:
    """``(reasons to roll again, notes)`` for one regenerated file.  Rolls again on: fewer than five distinct
    positive openings; the plain "You are X" opening (the form that failed); more than two positive openings
    with "someone", or with "a person" (Roger's rule, 2026-11-06), on the wide reading (``wide_opening_word``,
    2026-11-07); a "This is who you are" positive the grammar
    check reads as broken; a positive saying "person" twice in its first sentence; the same judged fault or
    pattern flag in two or more positives; no judgement.  Notes: one-of-five faults, a negative that opens
    otherwise than its positive, a grammar tie, a hand_edits record left, a question count other than 40."""
    reasons, notes = [], []
    pc = audit.pattern_checks(doc)
    f = pc["file"]
    pos = [str(p.get("pos", "")) for p in doc.get("instruction") or []]
    if f["n_pairs"] != 5:
        reasons.append(f"{f['n_pairs']} instruction pairs")
    if f["distinct_pos_forms"] < 5:
        reasons.append(f"{f['distinct_pos_forms']} distinct positive openings")
    if audit.FORM_YOU_ARE in f["pos_forms"]:
        reasons.append("a positive opens with the plain 'You are X'")
    for word in ("someone", "a person"):
        # the wide reading (Roger, 2026-11-07: "make a reroll rule for this"): the noun of the opening frame, and
        # in a "This is who you are" opening any "someone" or "person" in its phrase ("a gray-haired person", "the
        # person no one picks"; 27 traits of the edited corpus, carried over from "You are a gray-haired person:")
        n = sum(1 for t in pos if opening_noun(t) == word)
        n_wide = sum(1 for t in pos if wide_opening_word(t, word))
        if n_wide > 2:
            reasons.append(f"{n_wide} positive openings with '{word}'"
                           + (" counting the 'This is who you are' phrase" if n_wide > n else ""))
    for v in verdicts:
        if v["side"] == "pos" and v["verdict"] == "broken":
            reasons.append(f"p{v['index']} 'This is who you are' reads as broken English ({v['answers']})")
        elif v["verdict"] == "broken":
            notes.append(f"p{v['index']} neg reads as broken English ({v['answers']}; negatives reach no data)")
        elif v["verdict"] in ("unsure", None):
            notes.append(f"p{v['index']} {v['side']} grammar {v['verdict']} ({v['answers']})")
    for i, t in enumerate(pos):
        if opening_noun(t) == "a person" and person_echo(t):
            reasons.append(f"p{i} says 'person' twice in its first sentence")
    hits = positive_hits(pc, judged)
    if judged is None:
        reasons.append("not judged")
    for fault, ks in sorted(hits.items()):
        (reasons if len(ks) >= 2 else notes).append(f"{fault} in {len(ks)} of 5 positives (p{', p'.join(map(str, ks))})")
    for flag, ks in sorted(positive_hits(pc, None, MONITORED_PATTERNS).items()):
        if len(ks) >= 2:
            notes.append(f"{flag} in {len(ks)} of 5 positives (p{', p'.join(map(str, ks))}; monitored, not a reroll)")
    for i, p in enumerate(doc.get("instruction") or []):
        if p.get("neg") is not None and audit.opening_form(str(p["neg"])) != audit.opening_form(str(p.get("pos", ""))):
            notes.append(f"p{i} neg opens otherwise than its positive")
    if doc.get("hand_edits"):
        notes.append("hand_edits left in the file")
    if f["n_questions"] != 40:
        notes.append(f"{f['n_questions']} questions")
    return reasons, notes


def cmd_regen_check(args) -> None:
    out, regen = Path(args.out), Path(args.dir)
    stems = (json.loads(Path(args.stems).read_text(encoding="utf-8")) if args.stems
             else sorted(p.stem for p in regen.glob("*.json")))
    verdicts = json.loads((out / f"grammar_{args.grammar_tag}.json").read_text(encoding="utf-8"))["verdicts"]
    accepted = json.loads(Path(args.accept).read_text(encoding="utf-8")) if args.accept else {}
    result, reroll = {}, []
    for stem in stems:
        doc = json.loads((regen / f"{stem}.json").read_text(encoding="utf-8"))
        jpath = Path(args.audit_out) / "judged" / args.arm / f"{stem}.json"
        judged = json.loads(jpath.read_text(encoding="utf-8")) if jpath.exists() else None
        if judged is not None and not audit.judgement_is_current(judged, doc, audit.DEFAULT_INSTRUCTION_JUDGE,
                                                                 audit.DEFAULT_QUESTION_JUDGE):
            judged = None
        mine = [v for v in verdicts if v["stem"] == stem
                and v["text"] == str(doc["instruction"][v["index"]][v["side"]])]
        reasons, notes = regen_problems(doc, judged, mine)
        acc = accepted.get(stem) if reasons else None
        verdict = "accepted" if acc else "reroll" if reasons else "pass"
        result[stem] = {"verdict": verdict, "reasons": reasons, "notes": notes,
                        "openings": [_opening_words(str(p.get("pos", "")), 7) for p in doc["instruction"]],
                        "opening_rerolls": (doc.get("generator") or {}).get("opening_rerolls")}
        if acc:
            result[stem]["accepted_because"] = acc
        if verdict == "reroll":
            reroll.append(stem)
        say(f"{verdict.upper() if verdict != 'pass' else 'pass':8s} {stem}: " + "; ".join(reasons or ["-"])
            + (f"   [accepted: {acc}]" if acc else "") + (f"   [notes: {'; '.join(notes)}]" if notes else ""))
    write_json(out / f"regen_check_{args.tag}.json", result)
    write_json(out / f"reroll_{args.tag}.json", reroll)
    say(f"{len(stems) - len(reroll)} of {len(stems)} pass; {len(reroll)} to roll again "
        f"(listed in {out / f'reroll_{args.tag}.json'})")


# ---------------------------------------------------------------------------
# compare: sets of trait files on the same measures
# ---------------------------------------------------------------------------

#: a "This is who you are" phrase that is a noun phrase ("a seeker of the untried", "the person no one picks")
NOUN_PHRASE = re.compile(r"(?i)^(?:a|an|the|one)\b")
#: the per-file booleans ``compare`` counts, in its table's order
COMPARE_FLAGS = ("five_forms", "plain_you_are", "someone_over_2", "person_over_2", "someone_over_2_wide",
                 "person_over_2_wide", "this_is_who", "this_is_who_noun", "this_is_who_is_label", "person_echo",
                 "pattern_2of5")


def file_measures(doc: dict, judged: dict | None, verdicts: list[dict]) -> dict:
    """What ``compare`` counts for one trait file: the openings (five forms, the plain "You are X", Roger's
    someone / a person rule on the narrow and the wide reading), its "This is who you are" phrases (present, a
    noun phrase, the label itself), the person echo, the reroll rule's faults in two or more positives (pattern
    flags always, judged faults when ``judged``), and the grammar verdicts of its positive lines."""
    pc = audit.pattern_checks(doc)
    f = pc["file"]
    pos = [str(p.get("pos", "")) for p in doc.get("instruction") or []]
    label = str(doc.get("positive_label") or "").strip().lower()
    phrases = [m.group(1).strip() for m in map(THIS_IS_WHO_PHRASE.match, pos) if m]
    hits = positive_hits(pc, None)
    m = {"five_forms": f["distinct_pos_forms"] == 5, "plain_you_are": audit.FORM_YOU_ARE in f["pos_forms"]}
    for word, key in (("someone", "someone"), ("a person", "person")):
        m[f"{key}_over_2"] = sum(opening_noun(t) == word for t in pos) > 2
        m[f"{key}_over_2_wide"] = sum(wide_opening_word(t, word) for t in pos) > 2
    m.update(this_is_who=bool(phrases), this_is_who_noun=any(NOUN_PHRASE.match(p) for p in phrases),
             this_is_who_is_label=any(p.lower() == label for p in phrases),
             person_echo=any(opening_noun(t) == "a person" and person_echo(t) for t in pos),
             patterns_2of5=sorted(k for k, ks in hits.items() if len(ks) >= 2),
             monitored=({k: len(ks) for k, ks in positive_hits(pc, None, MONITORED_PATTERNS).items()}),
             phrases=phrases, judged=judged is not None)
    m["pattern_2of5"] = bool(m["patterns_2of5"])
    if judged is not None:
        jh = {k: ks for k, ks in positive_hits(pc, judged).items() if k in REROLL_JUDGED}
        m["faults_2of5"] = sorted(k for k, ks in jh.items() if len(ks) >= 2)
        m["fault_positives"] = {k: len(set(ks)) for k, ks in jh.items()}
    mine = [v for v in verdicts if v["side"] == "pos"]
    m["grammar_checked"], m["grammar_broken"] = len(mine), sum(v["verdict"] == "broken" for v in mine)
    return m


def _named_paths(items: list[str] | None) -> dict[str, list[Path]]:
    """``["head=a,b", "trial=c"]`` -> ``{"head": [a, b], "trial": [c]}``."""
    out: dict[str, list[Path]] = {}
    for item in items or []:
        name, _, paths = item.partition("=")
        out.setdefault(name, []).extend(Path(p) for p in paths.split(",") if p)
    return out


def compare_sets(sets: dict[str, Path], judged_dirs: dict[str, list[Path]], grammar_files: dict[str, list[Path]],
                 stems: list[str] | None = None) -> dict:
    """Per set, the measures of every trait file (``file_measures``) and their totals; the judged faults are also
    totalled over the traits judged in every set that has judgements (``paired``), so that the sets are compared
    on the same traits."""
    per: dict[str, dict[str, dict]] = {}
    for name, d in sets.items():
        verdicts = [v for p in grammar_files.get(name, [])
                    for v in json.loads(p.read_text(encoding="utf-8"))["verdicts"]]
        names = stems or sorted(p.stem for p in d.glob("*.json"))
        per[name] = {}
        for stem in names:
            path = d / f"{stem}.json"
            if not path.exists():
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            judged = None
            for jd in judged_dirs.get(name, []):
                jp = jd / f"{stem}.json"
                if jp.exists():
                    j = json.loads(jp.read_text(encoding="utf-8"))
                    if audit.judgement_is_current(j, doc, audit.DEFAULT_INSTRUCTION_JUDGE, audit.DEFAULT_QUESTION_JUDGE):
                        judged = j
                        break
            texts = {(i, s): str(p.get(s, "")) for i, p in enumerate(doc.get("instruction") or []) for s in ("pos", "neg")}
            mine = [v for v in verdicts if v["stem"] == stem and texts.get((v["index"], v["side"])) == v["text"]]
            per[name][stem] = file_measures(doc, judged, mine)
    judged_sets = [n for n in sets if judged_dirs.get(n)]
    paired = sorted(set.intersection(*(set(s for s, m in per[n].items() if m["judged"]) for n in judged_sets))
                    ) if judged_sets else []
    totals = {}
    for name, rows in per.items():
        t = {"n": len(rows), **{k: sum(bool(m[k]) for m in rows.values()) for k in COMPARE_FLAGS}}
        t["patterns_2of5"] = {k: sum(k in m["patterns_2of5"] for m in rows.values()) for k in REROLL_PATTERNS}
        t["monitored"] = {k: {"1": sum(m["monitored"].get(k, 0) == 1 for m in rows.values()),
                              "2+": sum(m["monitored"].get(k, 0) >= 2 for m in rows.values())}
                          for k in MONITORED_PATTERNS}
        t["grammar_checked"] = sum(m["grammar_checked"] for m in rows.values())
        t["grammar_broken"] = sum(m["grammar_broken"] for m in rows.values())
        t["n_judged"] = sum(m["judged"] for m in rows.values())
        if name in judged_sets:
            pr = [rows[s] for s in paired]
            t["paired"] = {
                "n": len(pr),
                "faults_2of5": {k: sum(k in m["faults_2of5"] for m in pr) for k in REROLL_JUDGED},
                "any_fault_2of5": sum(bool(m["faults_2of5"]) for m in pr),
                "reroll_by_faults": sum(bool(m["faults_2of5"] or m["patterns_2of5"]) for m in pr),
                "fault_positives": {k: sum(m["fault_positives"].get(k, 0) for m in pr) for k in REROLL_JUDGED}}
        totals[name] = t
    return {"sets": {n: str(d) for n, d in sets.items()}, "paired_stems": paired, "totals": totals, "per_trait": per}


def cmd_compare(args) -> None:
    sets = {name: paths[0] for name, paths in _named_paths(args.set).items()}
    stems = json.loads(Path(args.stems).read_text(encoding="utf-8")) if args.stems else None
    result = compare_sets(sets, _named_paths(args.judged), _named_paths(args.grammar), stems)
    result["inputs"] = {"judged": args.judged or [], "grammar": args.grammar or [], "stems": args.stems}
    write_json(Path(args.out), result)
    names = list(sets)
    say(f"{'measure':28s}" + "".join(f"{n:>14s}" for n in names))
    tot = result["totals"]
    for k in ("n",) + COMPARE_FLAGS + ("grammar_checked", "grammar_broken", "n_judged"):
        say(f"{k:28s}" + "".join(f"{tot[n][k]:>14}" for n in names))
    for k in REROLL_PATTERNS:
        say(f"{'  ' + k + ' (2+ of 5)':28s}" + "".join(f"{tot[n]['patterns_2of5'][k]:>14}" for n in names))
    for k in MONITORED_PATTERNS:
        for band in ("1", "2+"):
            say(f"{'  ' + k + f' ({band} of 5, monitored)':28s}"
                + "".join(f"{tot[n]['monitored'][k][band]:>14}" for n in names))
    pn = [n for n in names if "paired" in tot[n]]
    if pn:
        say(f"\njudged faults in 2+ of 5 positives, on the {len(result['paired_stems'])} traits judged in "
            f"{', '.join(pn)}:")
        for k in REROLL_JUDGED + ("any_fault_2of5", "reroll_by_faults"):
            say(f"{k:28s}" + "".join(f"{(tot[n]['paired']['faults_2of5'].get(k) if k in REROLL_JUDGED else tot[n]['paired'][k]):>14}"
                                     for n in pn))
    say(f"wrote {args.out}")


# ---------------------------------------------------------------------------
# merge: regenerated files into the corpus
# ---------------------------------------------------------------------------

#: what a regeneration of the instructions may change (``regenerate_trait_instructions.write_regenerated``):
#: the instructions, the generator record, hand_edits (dropped), and the eval prompt it rebuilds
REGEN_FREE = ("instruction", "generator", "hand_edits", "eval_prompt")


def merge_problems(corpus_doc: dict, regen_doc: dict) -> list[str]:
    """Why a regenerated file may not replace the corpus file: any key outside ``REGEN_FREE`` that differs (an
    edit made to the corpus file since it was staged, or a regeneration that went further than the
    instructions)."""
    keys = (set(corpus_doc) | set(regen_doc)) - set(REGEN_FREE)
    return [f"{k} differs" for k in sorted(keys) if corpus_doc.get(k, object()) != regen_doc.get(k, object())]


def cmd_merge(args) -> None:
    regen = Path(args.dir)
    stems = json.loads(Path(args.stems).read_text(encoding="utf-8"))
    if isinstance(stems, dict):
        stems = sorted(stems.get("regenerate", stems))
    bad = {}
    for stem in stems:
        corpus_doc = json.loads((TRAITS_DIR / f"{stem}.json").read_text(encoding="utf-8"))
        regen_doc = json.loads((regen / f"{stem}.json").read_text(encoding="utf-8"))
        problems = merge_problems(corpus_doc, regen_doc)
        if problems:
            bad[stem] = problems
    if bad:
        for stem, p in bad.items():
            say(f"  {stem}: {'; '.join(p)}")
        raise SystemExit(f"{len(bad)} regenerated files do not match their corpus files outside the instructions: "
                         f"nothing merged")
    if args.dry_run:
        say(f"(dry run) {len(stems)} regenerated files would replace their corpus files")
        return
    for stem in stems:
        text = (regen / f"{stem}.json").read_text(encoding="utf-8")
        if dump(json.loads(text)) != text:
            raise SystemExit(f"{regen / stem}.json is not in the corpus format")
        path = TRAITS_DIR / f"{stem}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    say(f"merged {len(stems)} regenerated files into {TRAITS_DIR}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("edit", help="make the edits (staged unless --apply)")
    e.add_argument("--traits-dir", default=str(TRAITS_DIR))
    e.add_argument("--out", default=str(DEFAULT_OUT), help=f"where edits.json and staged/ go (default: {DEFAULT_OUT.relative_to(REPO)})")
    e.add_argument("--menu", help="source=target pairs, e.g. W1=W5,W3=W7,A1=A6 (the default)")
    e.add_argument("--sides", choices=("both", "pos"), default="both",
                   help="edit negatives that open as their positive too (default), or positives only")
    e.add_argument("--wide", action="store_true",
                   help='also change "someone" to "a person" where the W opening\'s frame is followed by '
                        'something other than "who " ("From now on, you are someone whose body ...")')
    e.add_argument("--allow-person-echo", action="store_true",
                   help='also make a W edit that says "person" twice in one sentence ("Be a person who argues '
                        'until the other person ..."); by default it and its negative are left as they were')
    e.add_argument("--decisions", help="decisions.json from `decide`: traits left whole for regeneration, and "
                                       "edits left unmade")
    e.add_argument("--traits", nargs="*", help="only these stems")
    e.add_argument("--date", help="the date for hand_edits (default: today)")
    e.add_argument("--apply", action="store_true", help="write the corpus instead of <out>/staged/")
    e.add_argument("--dry-run", action="store_true", help="count and list, write nothing")
    e.set_defaults(func=cmd_edit)
    r = sub.add_parser("review", help="Sonnet reads each edited positive beside its original, blind, both orders")
    r.add_argument("--out", default=str(DEFAULT_OUT))
    r.add_argument("--model", default=REVIEW_MODEL)
    r.add_argument("--limit", type=int, help="only the first N calls (a pilot)")
    r.add_argument("--concurrency", type=int, default=16)
    r.add_argument("--requests-per-second", type=float, default=4.0)
    r.add_argument("--est-output-tokens", type=int, default=300,
                   help="output tokens a call for the estimate, thinking included (default: 300)")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--show", action="store_true", help="with --dry-run, print the first prompt as sent")
    r.set_defaults(func=cmd_review)
    g = sub.add_parser("grammar", help='Sonnet reads each "This is who you are: X." instruction alone and says '
                                       'whether it is grammatical; several readings, combined by majority')
    g.add_argument("--out", default=str(DEFAULT_OUT))
    g.add_argument("--files", help="check the instructions of these files (a regeneration) instead of the "
                                   "edits in <out>/edits.json")
    g.add_argument("--stems", help="with --files: a JSON list of the stems to check (default: every file)")
    g.add_argument("--tag", default="edits", help="names <out>/grammar_<tag>.json (default: edits)")
    g.add_argument("--side", choices=("both", "pos", "neg"), default="both",
                   help="the instructions to read (default: both; the regen check rolls again only on a positive)")
    g.add_argument("--readings", type=int, default=GRAMMAR_READINGS, help=f"(default: {GRAMMAR_READINGS})")
    g.add_argument("--model", default=REVIEW_MODEL)
    g.add_argument("--limit", type=int, help="only the first N calls (a pilot)")
    g.add_argument("--concurrency", type=int, default=16)
    g.add_argument("--requests-per-second", type=float, default=4.0)
    # 80 until 2026-11-07, which put the estimate at half the spend: the four runs that day averaged 179 to 221
    # output tokens a call (trial 2's 2,796 calls: 219)
    g.add_argument("--est-output-tokens", type=int, default=220,
                   help="output tokens a call for the estimate, thinking included (default: 220)")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--show", action="store_true", help="with --dry-run, print the first prompt as sent")
    g.set_defaults(func=cmd_grammar)
    d = sub.add_parser("decide", help="from the review and the grammar check: the traits to regenerate whole, "
                                      "and the negatives to keep unedited (<out>/decisions.json)")
    d.add_argument("--out", default=str(DEFAULT_OUT))
    d.add_argument("--tag", default="edits", help="the grammar check to read (default: edits)")
    d.add_argument("--dry-run", action="store_true")
    d.set_defaults(func=cmd_decide)
    c = sub.add_parser("regen-check", help="the checks after a regeneration; lists the files to roll again")
    c.add_argument("--out", default=str(DEFAULT_OUT))
    c.add_argument("--dir", required=True, help="the regenerated files")
    c.add_argument("--stems", help="a JSON list of stems (default: every file in --dir)")
    c.add_argument("--audit-out", required=True, help="the audit_trait_instructions.py --out of their judgement")
    c.add_argument("--arm", required=True, help="the arm they were judged under")
    c.add_argument("--grammar-tag", required=True, help="the grammar check of these files")
    c.add_argument("--tag", required=True, help="names <out>/regen_check_<tag>.json and <out>/reroll_<tag>.json")
    c.add_argument("--accept", help="a JSON map stem -> reason: flags a person has read and accepted (as the "
                                    "October reroll pass accepted the label or the description's content in the "
                                    "text of a membership trait); recorded, and not rolled again")
    c.set_defaults(func=cmd_regen_check)
    m = sub.add_parser("merge", help="regenerated files into the corpus, when nothing but the instructions differs")
    m.add_argument("--dir", required=True, help="the regenerated files")
    m.add_argument("--stems", required=True, help="a JSON list of stems, or decisions.json")
    m.add_argument("--dry-run", action="store_true")
    m.set_defaults(func=cmd_merge)
    k = sub.add_parser("compare", help="sets of trait files side by side on the openings, phrase, echo, pattern, "
                                       "judged-fault and grammar measures (no API calls)")
    k.add_argument("--set", action="append", required=True, help="NAME=DIR, repeated")
    k.add_argument("--judged", action="append", help="NAME=DIR[,DIR...]: audit judgements for that set (the "
                                                     "first current one is used)")
    k.add_argument("--grammar", action="append", help="NAME=FILE[,FILE...]: grammar_<tag>.json files for that set")
    k.add_argument("--stems", help="a JSON list of stems (default: every file of each set)")
    k.add_argument("--out", required=True, help="the JSON to write")
    k.set_defaults(func=cmd_compare)
    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
