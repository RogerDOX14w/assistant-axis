"""Manual review pass (Roger, 2026-10-10): every trait and role description added, rewritten or renamed since his
last pass (the chunk-7 table, before a53642d).  Writes review_table.md beside this script.

    uv run python roger/review_2026-10-10/build_review_table.py
"""
import json
import subprocess
from pathlib import Path

BASE = "a53642d"
# short names for the commits that changed descriptions (the work list's item ids)
TAG = {"77c48a4": "W3 E1", "b6c086b": "W3 C1-C3", "159debd": "W5", "7394d5f": "W4 batch", "645e5a0": "W6, W23, W25",
       "2f944dd": "wave 2 batch 2", "4ea9097": "wave 1 rest", "6290c4b": "W3 E6", "e50f069": "Roger's calls 10-10",
       "b6c19e3": "W22", "49a88c7": "W22 rename", "e776919": "Tarot"}
OUT = Path("roger/review_2026-10-10/review_table.md")


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def at(rev, kind):
    out = {}
    for line in git("ls-tree", "--name-only", f"{rev}:data/{kind}/instructions").split():
        if line.endswith(".json"):
            d = json.loads(git("show", f"{rev}:data/{kind}/instructions/{line}"))
            out[line[:-5]] = d
    return out


def renamed_from(d):
    r = d.get("renamed_from")
    rs = r if isinstance(r, list) else [r] if r else []
    return [x["stem"] for x in rs if isinstance(x, dict)]


def origin(kind, stem, old_desc):
    """The last commit since BASE that changed the description (its short hash and subject)."""
    path = f"data/{kind}/instructions/{stem}.json"
    log = git("log", "--format=%h %s", f"{BASE}..HEAD", "--follow", "--", path).splitlines()
    for line in log:
        h = line.split()[0]
        try:
            now = json.loads(git("show", f"{h}:{path}")).get("description")
        except subprocess.CalledProcessError:
            continue
        try:
            before = json.loads(git("show", f"{h}~1:{path}")).get("description")
        except subprocess.CalledProcessError:
            before = None
        if now != before:
            return h, TAG.get(h, line.split(" ", 1)[1][:40])
    return (log[0].split()[0], TAG.get(log[0].split()[0], log[0].split(" ", 1)[1][:40])) if log else ("", "")


def last_check(stem):
    best = None
    for line in open("data/traits/antonym_check_history.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("stem") == stem:
            best = r if best is None or r.get("checked_at", "") >= best.get("checked_at", "") else best
    if not best:
        return ""
    s = f"-> {best.get('returned')} ({best.get('score')})"
    names = [json.loads(l).get("positive_name") for l in open("data/traits/antonym_check_history.jsonl", encoding="utf-8")
             if json.loads(l).get("stem") == stem and json.loads(l).get("positive_name")]
    if names:
        s += f"; blind name {names[-1]}"
    return s


def arr(d):
    a = d.get("arrangement")
    a = a if isinstance(a, list) else [a] if a else []
    if not a:
        return f"unclassified (-> {d.get('negative_label')})" if "negative_label" in d else "unclassified"
    parts = []
    for x in a:
        k = x.get("kind")
        if k == "pair":
            other = [m for m in x["members"] if m != d.get("_stem")]
            parts.append(f"pair with {other[0].replace('_', ' ')}" if other else "pair")
        else:
            parts.append(k)
    return ", ".join(parts)


def link(kind, stem, label):
    return f"[{label}](../../data/{kind}/instructions/{stem}.json)"


def main():
    rows = {"new": [], "rewritten": [], "renamed": [], "dropped": []}
    for kind in ("traits", "roles"):
        old, new = at(BASE, kind), at("HEAD", kind)
        mapped = set()
        for stem, d in sorted(new.items()):
            d["_stem"] = stem
            label = d.get("positive_label") or stem.replace("_", " ")
            prev = next((s for s in renamed_from(d) if s in old), None)
            if stem in old:
                o = old[stem]
                if o.get("description") != d.get("description"):
                    h, subj = origin(kind, stem, o.get("description"))
                    rows["rewritten"].append((kind, stem, label, d, o.get("description"), h, subj))
                mapped.add(stem)
            elif prev:
                o = old[prev]; mapped.add(prev)
                h, subj = origin(kind, stem, o.get("description"))
                same = o.get("description") == d.get("description")
                rows["renamed"].append((kind, stem, label, d, None if same else o.get("description"), h, subj, prev))
            else:
                h, subj = origin(kind, stem, None)
                rows["new"].append((kind, stem, label, d, None, h, subj))
        for stem, o in sorted(old.items()):
            if stem not in mapped and stem not in new:
                rows["dropped"].append((kind, stem, o.get("positive_label") or stem.replace("_", " "), o))
    order = {h: i for i, h in enumerate(reversed(git("log", "--format=%h", f"{BASE}..HEAD").split()))}
    for k in ("new", "rewritten", "renamed"):
        rows[k].sort(key=lambda r: (order.get(r[5], 9999), r[2]))
    A = []
    n = {k: len(v) for k, v in rows.items()}
    A.append("# Review pass: descriptions added or changed since the chunk-7 review (2026-10-10)\n")
    A.append(f"Written for Roger.  Every trait and role description added, rewritten or renamed since your last pass (the "
             f"[chunk-7 table](../chunk7_2026-10-09/review_table_chunk7.md), before `{BASE}`), compared with the corpus at that commit: "
             f"{n['new']} new, {n['rewritten']} rewritten, {n['renamed']} renamed, {n['dropped']} dropped.  Each label links to its file; "
             "**check** is the latest antonym check (what the generator named as the opposite, score 0-4) and, where it was run, the "
             "label-blind name of the positive instructions.  Instructions regenerated with an unchanged description (the 85 standards "
             "traits under W19, the triangle relabels, the pair rechecks) are not listed.  Annotate in `**...**` or edit the files; "
             f"[build_review_table.py](./build_review_table.py) rebuilds this table from git and will overwrite annotations.\n")
    A.append(f"## New ({n['new']})\n\n| label | from | arrangement | description | check |\n|---|---|---|---|---|")
    for kind, stem, label, d, _, h, subj in rows["new"]:
        A.append(f"| {link(kind, stem, label)}{' (role)' if kind == 'roles' else ''} | `{h}` {subj} | {arr(d)} | {d.get('description')} | {last_check(stem) if kind == 'traits' else ''} |")
    A.append(f"\n## Renamed ({n['renamed']})\n\n| label | was | from | description (and what it was, if changed) | check |\n|---|---|---|---|---|")
    for kind, stem, label, d, olddesc, h, subj, prev in rows["renamed"]:
        desc = d.get("description") + (f"<br>**was:** {olddesc}" if olddesc else " (unchanged)")
        A.append(f"| {link(kind, stem, label)} | {prev.replace('_', ' ')} | `{h}` {subj} | {desc} | {last_check(stem)} |")
    A.append(f"\n## Rewritten ({n['rewritten']})\n\n| label | from | now | was | check |\n|---|---|---|---|---|")
    for kind, stem, label, d, olddesc, h, subj in rows["rewritten"]:
        A.append(f"| {link(kind, stem, label)}{' (role)' if kind == 'roles' else ''} | `{h}` {subj} | {d.get('description')} | {olddesc} | {last_check(stem) if kind == 'traits' else ''} |")
    A.append(f"\n## Dropped ({n['dropped']}), for the record\n\n| label | description it had |\n|---|---|")
    for kind, stem, label, o in rows["dropped"]:
        A.append(f"| {label}{' (role)' if kind == 'roles' else ''} | {o.get('description')} |")
    OUT.write_text("\n".join(A) + "\n", encoding="utf-8")
    print(n)


if __name__ == "__main__":
    main()
