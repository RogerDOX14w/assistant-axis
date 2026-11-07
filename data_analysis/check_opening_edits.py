#!/usr/bin/env python3
"""Check that an opening edit of the trait instructions changed nothing but the openings.

Written apart from ``edit_trait_openings.py`` and sharing no code with it, so that a fault in the editor is not
repeated here.  For every trait file in ``--new`` it compares the file with its original (``--old DIR``, or the
same path at a git revision with ``--git REV``) and fails on anything outside these rules:

* every key of the file other than ``instruction`` and ``hand_edits`` is unchanged, in the same order;
* ``hand_edits`` is the old record with one dated record appended (or a new record where there was none);
* ``instruction`` has the same number of pairs and the same keys; each ``pos`` and ``neg`` text is either
  unchanged or one of the allowed changes of its opening, the rest of the text identical:
    - "Be someone<rest>" -> "Be a person<rest>", "From now on, you are someone<rest>" -> "From now on, you
      are a person<rest>", and "You are someone<rest>" -> "You are a person<rest>" (``<rest>`` starting with a
      space or a comma; the last for the traits rebalanced to Roger's rule of no more than two "someone"
      openings, 2026-11-07);
    - "You are X: <rest>" -> "This is who you are: X. <Rest>" (the rest's first letter capitalised and nothing
      else), and "You are X.<rest>" -> "This is who you are: X.<rest>";
* the file is written in the corpus's format (two-space JSON, UTF-8 characters as they are, a final newline),
  so that a git diff of it shows only the changed lines; and every changed line of the text diff is a
  ``"pos"``, ``"neg"`` or ``"hand_edits"`` line.

A trait named in ``--regenerated`` (a JSON list of stems, or a decisions file with a ``regenerate`` map) had its
ten instructions regenerated instead (Roger, 2026-11-06: an edit that broke the grammar is replaced by a new
set).  Its file is checked by other rules: every key other than ``instruction``, ``generator``, ``hand_edits``
and ``eval_prompt`` keeps its value (the regenerator writes the keys in its own order, so the order may change,
and it rebuilds the eval prompt); ``hand_edits`` is gone (a regeneration drops it), or is one new dated record
(a hand edit after the rolls, as the reroll rule allows); ``instruction`` still has five
pairs of a ``pos`` and a ``neg``, and no more than two of the five positives open with "someone", nor with "a
person" (Roger's rule for the openings); and the file is in the corpus format.

Exits 1 and lists every failure, or prints the counts and exits 0.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORPUS = "data/traits/instructions"

FRAMES = (("Be someone", "Be a person"), ("From now on, you are someone", "From now on, you are a person"),
          ("You are someone", "You are a person"))
ADJ_COLON = re.compile(r"You are (?P<x>[^:]+?): (?P<rest>\S.*)\Z", re.S)
ADJ_SENTENCE = re.compile(r"You are (?P<x>[^.]+?)\.(?P<rest>.*)\Z", re.S)
ALLOWED_LINE = re.compile(r'^\s*"(pos|neg|hand_edits)": ')


def change_kind(old: str, new: str) -> str | None:
    """The kind of an allowed change from ``old`` to ``new`` ("same", "someone", "this is who"), or None."""
    if old == new:
        return "same"
    for frm, to in FRAMES:
        if old.startswith(frm) and old[len(frm):len(frm) + 1] in (" ", ",") and new == to + old[len(frm):]:
            return "someone"
    m = ADJ_COLON.match(old)
    if m:
        rest = m.group("rest")
        if new == f"This is who you are: {m.group('x')}. {rest[:1].upper()}{rest[1:]}":
            return "this is who"
    m = ADJ_SENTENCE.match(old)
    if m and new == f"This is who you are: {m.group('x')}.{m.group('rest')}":
        return "this is who"
    return None


def dump(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def check_file(stem: str, old_text: str, new_text: str) -> tuple[list[str], dict]:
    """(failures, counts of change kinds) for one file."""
    fails, counts = [], {}
    old, new = json.loads(old_text), json.loads(new_text)
    if dump(new) != new_text:
        fails.append("not written in the corpus format")
    if dump(old) != old_text:
        fails.append("the original is not in the corpus format, so a git diff would show more than the edits")
    others_old = [(k, v) for k, v in old.items() if k not in ("instruction", "hand_edits")]
    others_new = [(k, v) for k, v in new.items() if k not in ("instruction", "hand_edits")]
    if others_old != others_new:
        changed = sorted({k for k, _ in others_old} ^ {k for k, _ in others_new}
                         | {k for (k, v) in others_old if dict(others_new).get(k, object()) != v})
        fails.append(f"keys other than instruction and hand_edits changed: {changed or 'their order'}")
    oh, nh = old.get("hand_edits"), new.get("hand_edits")
    if oh != nh:
        if not isinstance(nh, str) or (oh and not nh.startswith(f"{oh}; ")) or not re.search(
                r"(^|; )\d{4}-\d{2}-\d{2}: [^;]*$", nh):
            fails.append("hand_edits is not the old record with one dated record appended")
    oi, ni = old.get("instruction") or [], new.get("instruction") or []
    if len(oi) != len(ni):
        fails.append(f"{len(oi)} instruction pairs became {len(ni)}")
    for i, (op, np_) in enumerate(zip(oi, ni)):
        if list(op) != list(np_):
            fails.append(f"p{i}: keys {list(op)} became {list(np_)}")
            continue
        for side, ov in op.items():
            nv = np_[side]
            if side not in ("pos", "neg"):
                if ov != nv:
                    fails.append(f"p{i} {side} changed")
                continue
            kind = change_kind(ov, nv)
            if kind is None:
                fails.append(f"p{i} {side}: not an allowed opening change:\n    old: {ov[:120]}\n    new: {nv[:120]}")
            else:
                counts[(side, kind)] = counts.get((side, kind), 0) + 1
    diff = [ln for ln in difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm="", n=0)
            if not ln.startswith(("---", "+++", "@@"))]
    removed = [ln[1:] for ln in diff if ln.startswith("-")]
    added = [ln[1:] for ln in diff if ln.startswith("+")]
    # a hand_edits key appended where the file had none gives the line before it a comma, and nothing else
    if "hand_edits" not in old and "hand_edits" in new and list(new)[-1] == "hand_edits":
        for r in list(removed):
            if f"{r}," in added and not r.endswith(","):
                removed.remove(r)
                added.remove(f"{r},")
                break
    for ln in removed + added:
        if not ALLOWED_LINE.match(ln):
            fails.append(f"a changed line outside pos, neg and hand_edits: {ln[:100]}")
    if (oh != nh) != any(k != "same" for (_, k) in counts):
        fails.append("hand_edits changed without an edit, or an edit without a hand_edits record")
    return fails, counts


REGEN_FREE = ("instruction", "generator", "hand_edits", "eval_prompt")


def check_regenerated(stem: str, old_text: str, new_text: str) -> tuple[list[str], dict]:
    """(failures, counts) for a file whose instructions were regenerated whole."""
    fails, counts = [], {("regenerated", "files"): 1}
    old, new = json.loads(old_text), json.loads(new_text)
    if dump(new) != new_text:
        fails.append("not written in the corpus format")
    for k in sorted((set(old) | set(new)) - set(REGEN_FREE)):
        if old.get(k, object()) != new.get(k, object()):
            fails.append(f"{k} changed (a regeneration may change only {', '.join(REGEN_FREE)})")
    if [k for k in old if k in new] != [k for k in new if k in old]:
        counts[("regenerated", "key order")] = 1
    if old.get("eval_prompt") != new.get("eval_prompt"):
        counts[("regenerated", "eval_prompt")] = 1
    if "hand_edits" in new and (new["hand_edits"] == old.get("hand_edits")
                                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}: [^;]+", str(new["hand_edits"]))):
        # a regeneration drops the old record; a hand edit made after it writes one new dated record
        fails.append("hand_edits is still there, or is not one new dated record (a regeneration drops the old one)")
    if not new.get("generator"):
        fails.append("no generator record")
    pairs = new.get("instruction") or []
    if len(pairs) != 5 or any(set(p) != {"pos", "neg"} or not all(isinstance(p[s], str) and p[s].strip()
                                                                  for s in ("pos", "neg")) for p in pairs):
        fails.append("instruction is not five pairs of a pos and a neg")
    else:
        nouns = [opening_noun(p["pos"]) for p in pairs]
        for word in ("someone", "a person"):
            if nouns.count(word) > 2:
                fails.append(f"{nouns.count(word)} of the five positives open with '{word}'")
    return fails, counts


def opening_noun(text: str) -> str | None:
    """"someone" or "a person" when it follows the instruction's opening frame ("You are someone whose ...",
    "This is who you are: a person ..."), else None; one later in the sentence does not count."""
    m = re.match(r"(?i)\s*(?:be|become|from now on,? you are|you are|you're|this is who you are:)\s+"
                 r"(someone|a person)\b", text)
    return m.group(1).lower() if m else None


def load_regenerated(path: str | None) -> set[str]:
    if not path:
        return set()
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return set(d.get("regenerate", {}) if isinstance(d, dict) else d)


def old_text_of(stem: str, old_dir: Path | None, rev: str | None) -> str:
    if rev:
        return subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{CORPUS}/{stem}.json"],
                              capture_output=True, text=True, check=True).stdout
    return (old_dir / f"{stem}.json").read_text(encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--new", required=True, help="the edited files (a staged directory, or the corpus)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--old", help="the original files")
    src.add_argument("--git", help=f"the originals at this git revision ({CORPUS}/<stem>.json)")
    ap.add_argument("--changed-only", action="store_true",
                    help="with --new the corpus, check only the files that differ from the originals")
    ap.add_argument("--regenerated", help="a JSON list of stems (or a decisions file with a 'regenerate' map) "
                                          "whose instructions were regenerated whole: checked by the rules for "
                                          "a regeneration instead")
    args = ap.parse_args(argv)
    new_dir = Path(args.new)
    regenerated = load_regenerated(args.regenerated)
    total, failures, n_files = {}, {}, 0
    for path in sorted(new_dir.glob("*.json")):
        stem = path.stem
        new_text = path.read_text(encoding="utf-8")
        old_text = old_text_of(stem, Path(args.old) if args.old else None, args.git)
        if args.changed_only and old_text == new_text:
            continue
        n_files += 1
        check = check_regenerated if stem in regenerated else check_file
        fails, counts = check(stem, old_text, new_text)
        if fails:
            failures[stem] = fails
        for k, v in counts.items():
            total[k] = total.get(k, 0) + v
    for (side, kind), n in sorted(total.items()):
        print(f"{side:4} {kind:12} {n}")
    if failures:
        print(f"\nFAILED: {len(failures)} of {n_files} files")
        for stem, fails in failures.items():
            for f in fails:
                print(f"  {stem}: {f}")
        return 1
    n_regen = sum(1 for p in new_dir.glob("*.json") if p.stem in regenerated)
    print(f"\nOK: {n_files} files; every change is an allowed opening change, the rest of each file unchanged"
          + (f" ({n_regen} regenerated files checked by the rules for a regeneration)" if n_regen else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
