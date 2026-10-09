"""W10 staged antonym checks (pre-extraction work list).  Run from the repository root:
    uv run python <this file> STAGE_DIR
Regenerates STAGED traits under non-X in STAGE_DIR (a copy; the corpus is untouched), checks them and
AS_IS traits from the corpus, records every answer in the check history and the usage record."""
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402
from data_analysis import generate_antonyms as G  # noqa: E402
from data_analysis import seed_entities as SE  # noqa: E402

STAGED = ["mystical", "meditative", "anecdotal", "paranoid", "vindictive", "iconoclastic", "perfectionist", "subversive"]
AS_IS = ["materialist", "rationalist", "restless"]
INTENDED = {"mystical": "materialist", "meditative": "restless", "anecdotal": "data_driven", "paranoid": "trusting",
            "vindictive": "forgiving", "iconoclastic": "reverent", "perfectionist": "sloppy", "subversive": "orthodox",
            "materialist": "mystical", "rationalist": "mystical", "restless": "meditative"}
CORPUS = Path("data/traits/instructions")


def stage(stage_dir: Path) -> None:
    stage_dir.mkdir(parents=True, exist_ok=True)
    for s in STAGED:
        d = json.load(open(CORPUS / f"{s}.json", encoding="utf-8"))
        d["negative_label"] = f"non-{d['positive_label']}"
        (stage_dir / f"{s}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["uv", "run", "python", "data_analysis/regenerate_trait_instructions.py", "--traits-dir", str(stage_dir),
                    "--traits", *STAGED, "--force"], check=True)


async def check(docs: dict) -> dict:
    load_dotenv()
    client = anthropic.AsyncAnthropic(); sem = asyncio.Semaphore(10); usage = MultiModelUsage()

    async def one(stem, d):
        defn = G.extract_definition(d.get("eval_prompt", "")) or d.get("description", "")
        return stem, await G.classify_one(client, stem, defn, d["instruction"], sem, usage)
    out = dict(await asyncio.gather(*(one(s, d) for s, d in docs.items())))
    total = MultiModelUsage.load_or_create(G.DEFAULT_USAGE_JSON); total.merge_from(usage); total.write_json(G.DEFAULT_USAGE_JSON)
    print(usage.log_line("[usage]"))
    return out


def main() -> None:
    stage_dir = Path(sys.argv[1])
    stage(stage_dir)
    docs = {s: json.load(open(stage_dir / f"{s}.json", encoding="utf-8")) for s in STAGED}
    docs.update({s: json.load(open(CORPUS / f"{s}.json", encoding="utf-8")) for s in AS_IS})
    res = asyncio.run(check(docs))
    q = SE.load_queue(Path("data/seed_queue.json")); reg = SE.build_registry(q, Path("data")); hist = []
    for s, r in res.items():
        v = SE.classify_check(r.get("negative_label", ""), INTENDED[s], reg)
        phase = ("W10 staged check under non-X (scratch copy; corpus unchanged)" if s in STAGED
                 else "W10 check as the file stands")
        hist.append(SE.check_history_record(s, docs[s], r, v, INTENDED[s], phase))
        print(f"{s:16s} label={docs[s]['negative_label']!r:28s} -> {r.get('negative_label')} ({r.get('antonym_score')})  expected {INTENDED[s]}")
    SE.append_check_history(Path("data"), hist)
    print("recorded", len(hist))


if __name__ == "__main__":
    main()
