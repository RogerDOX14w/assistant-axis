"""Closest qualifying matches for the entries the goal lists lost (W15, Roger 2026-10-10: keep everything that was in a
list's previous top 30 and still qualifies; fill every other place with the closest match to what was lost, previous
lower-tier members counting like any other candidate).

Closeness: cosine of OpenAI text-embedding-3-large on the trait-gap platform's `w20` text (label plus the description
cut to about 20 words), centred on the mean of the corpus of that kind (traits or roles), through the platform's
embedding cache.  Writes closest_matches.json: for each list and each lost entry, the qualifiers ranked by cosine.

    uv run python roger/pre_extraction_2026-10-09/w15/closest_matches.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv  # noqa: E402

from assistant_axis.gapgen import embed as E  # noqa: E402
from assistant_axis.gapgen.representation import represent  # noqa: E402
from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402

HERE = Path("roger/pre_extraction_2026-10-09/w15")
sys.path.insert(0, str(HERE))
import build_goal_tiers as B  # noqa: E402

OLD_COMMIT = "3f6de81"   # 2026-09-28: still has universalist.json and libertarian.json under their old texts


def corpus(kind):
    out = {}
    for p in Path(f"data/{kind}/instructions").glob("*.json"):
        d = json.load(open(p, encoding="utf-8"))
        if d.get("description"):
            out[p.stem] = (d.get("positive_label") or p.stem.replace("_", " "), d["description"])
    return out


def old_text(stem):
    d = json.loads(subprocess.run(["git", "show", f"{OLD_COMMIT}:data/traits/instructions/{stem}.json"],
                                  capture_output=True, text=True, check=True).stdout)
    return d.get("positive_label") or stem, d["description"]


def main():
    load_dotenv(Path(os.getcwd()) / ".env")
    q, _ = B.qualifiers()
    cur = B.CUR
    embedder = E.make_embedder("openai"); cache = E.EmbeddingCache(Path("data/candidates/cache/embeddings")); usage = MultiModelUsage()
    result = {}
    for kind in ("roles", "traits"):
        texts = corpus(kind)
        lost_all = {x for sub in ("goal", "non_goal") for x in cur[kind][sub] if x not in q[f"{kind}.{sub}"]}
        for x in lost_all:
            if x not in texts:
                texts[x] = old_text(x)
        stems = sorted(texts)
        reps = [represent(texts[s][0], texts[s][1], "w20") for s in stems]
        V = E.embed_texts(embedder, reps, cache=cache, usage=usage)
        V = np.asarray(V, dtype=float)
        live = [i for i, s in enumerate(stems) if Path(f"data/{kind}/instructions/{s}.json").exists()]
        V = V - V[live].mean(axis=0)
        V = V / np.linalg.norm(V, axis=1, keepdims=True)
        idx = {s: i for i, s in enumerate(stems)}
        for sub in ("goal", "non_goal"):
            lst = f"{kind}.{sub}"
            if lst == "roles.non_goal":
                continue          # settled as drafted (Roger 2026-10-10: job / non-job balance)
            # every previous entry, so that a slot left by an entry moved up can be matched too
            lost = list(cur[kind][sub])
            pool = sorted(q[lst])
            result[lst] = {}
            for x in lost:
                sims = sorted(((float(V[idx[x]] @ V[idx[c]]), c) for c in pool), reverse=True)
                result[lst][x] = [{"stem": c, "cos": round(s, 3)} for s, c in sims[:40]]
    cache.save()
    (HERE / "closest_matches.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(usage.log_line("[usage]"))
    print({lst: len(d) for lst, d in result.items()})


if __name__ == "__main__":
    main()
