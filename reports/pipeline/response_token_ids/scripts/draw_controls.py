"""Draw the § 9 controls: three roles and three traits, seeded, from October entities with
no stripped response and at most 10 capped ones.  Prints the candidates' counts and the draw."""
import json, random, sys
from pathlib import Path
OCT = Path("runpod_workspace/qwen/qwen-3-32b Roger October")
SEED = 20261103
NAMED = {"gamer", "aural_vark", "plugged_in", "millennial", "stream_of_consciousness", "child", "gen_z",
         "thorough", "researcher", "verbose", "specialist"}
rows = {}
for etype in ("roles", "traits"):
    for f in sorted((OCT / etype / "responses").glob("*.jsonl")):
        n = stripped = capped = susp = 0
        with open(f) as fh:
            for line in fh:
                r = json.loads(line); n += 1
                stripped += bool(r.get("thinking_stripped")); susp += bool(r.get("thinking_suspected"))
                capped += r.get("finish_reason") == "length"
        rows[(etype, f.stem)] = (n, stripped, susp, capped)
for name in NAMED:
    for (et, st), v in rows.items():
        if st == name: print(f"named  {et:6} {st:26} n={v[0]} stripped={v[1]} suspected={v[2]} capped={v[3]}")
draw = {}
for etype in ("roles", "traits"):
    cands = sorted(st for (et, st), (n, s, su, c) in rows.items()
                   if et == etype and n == 500 and s == 0 and su == 0 and c <= 10 and st not in NAMED)
    rng = random.Random(f"{SEED}:{etype}")
    draw[etype] = rng.sample(cands, 3)
    print(f"{etype}: {len(cands)} candidates of {sum(1 for k in rows if k[0]==etype)}; drawn {draw[etype]}")
    for st in draw[etype]:
        print(f"   {st:26} {rows[(etype, st)]}")
print(json.dumps({"seed": SEED, "draw": draw}))
