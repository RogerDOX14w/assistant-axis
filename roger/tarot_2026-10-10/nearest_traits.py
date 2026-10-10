"""The corpus traits nearest each Major Arcana card read as a person (tarot_person_readings.json), in the trait-gap
platform's own metric: the card's description in M3's query form (gloss_w14) against every corpus trait in the
cached w20 form (label plus about 20 words of description), text-embedding-3-large, both centred on the corpus mean.
Writes nearest_traits.json (the 12 nearest per card) and prints the top 8.

    uv run python roger/tarot_2026-10-10/nearest_traits.py
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv  # noqa: E402

from assistant_axis.gapgen import embed as E  # noqa: E402
from assistant_axis.gapgen.novelty import query_text  # noqa: E402
from assistant_axis.gapgen.representation import represent  # noqa: E402
from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402

HERE = Path("roger/tarot_2026-10-10")


def main():
    load_dotenv(Path(os.getcwd()) / ".env")
    cards = json.load(open(HERE / "tarot_person_readings.json", encoding="utf-8"))["cards"]
    corpus = {}
    for p in sorted(Path("data/traits/instructions").glob("*.json")):
        d = json.load(open(p, encoding="utf-8"))
        corpus[p.stem] = represent(d.get("positive_label") or p.stem, d.get("description", ""), "w20")
    stems = list(corpus)
    embedder = E.make_embedder("openai"); cache = E.EmbeddingCache(); usage = MultiModelUsage()
    C = np.asarray(E.embed_texts(embedder, [corpus[s] for s in stems], cache=cache, usage=usage), dtype=float)
    Q = np.asarray(E.embed_texts(embedder, [query_text(c["card"], c["description"], query_form="gloss_w14") for c in cards],
                                 cache=cache, usage=usage), dtype=float)
    cache.save()
    mu = C.mean(axis=0)
    C = C - mu; C /= np.linalg.norm(C, axis=1, keepdims=True)
    Q = Q - mu; Q /= np.linalg.norm(Q, axis=1, keepdims=True)
    S = Q @ C.T
    out = []
    for i, c in enumerate(cards):
        order = np.argsort(-S[i])[:12]
        out.append({"n": c["n"], "card": c["card"], "nearest": [{"stem": stems[j], "cos": round(float(S[i, j]), 3)} for j in order]})
        print(f"{c['n']:2d} {c['card']:20s} " + ", ".join(f"{stems[j]} {S[i, j]:.2f}" for j in order[:8]))
    (HERE / "nearest_traits.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(usage.log_line("[usage]"))


if __name__ == "__main__":
    main()
