"""Measurement 1 of the response-token-ids sample (plan § 9): per response, the
stored ids against the text path's re-encoding, with the tokenizer only (no
model, no GPU).

For every record with stored ids and a content range, both paths' id
sequences are built the way step 2 builds them (``build_turn_spans`` for the
text path, ``build_ids_path_sequence`` for the ids path).  Identical ids: the
two assistant spans are compared (``compare_assistant_spans``: identical, or
differing by the text path's trim of boundary whitespace).  Differing ids: the
positions and regions that differ and the kinds of difference
(``describe_token_difference``: plan, partial character, special token,
re-split, prompt or end of turn, boundary whitespace).  Each record is classed
from its fields: clean, stripped, capped, range_null, joined with "+".

Writes ``<out>.jsonl`` (one line per record) and ``<out>.json`` (counts per
entity, per class and over all), and prints the per-entity table.
"""
import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_step2(repo: Path):
    """The step 2 module (its name starts with a digit) with the checkout on
    the path, as its tests load it."""
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    spec = importlib.util.spec_from_file_location("_step2_for_token_diff",
                                                  repo / "pipeline" / "2_activations.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify(resp: dict) -> str:
    cls = []
    if resp.get("thinking_stripped"):
        cls.append("stripped")
    if resp.get("finish_reason") == "length":
        cls.append("capped")
    if resp.get("response_token_ids") is not None and resp.get("content_token_range") is None:
        cls.append("range_null")
    return "+".join(cls) or "clean"


COUNT_KEYS = ("n", "identical", "spans identical", "spans trimmed", "differing", "no ids", "range null",
              "kind: plan", "kind: partial character", "kind: special token", "kind: re-split",
              "kind: boundary whitespace", "kind: prompt or end of turn", "positions", "tokens")


def run(mod, tokenizer, family, model_name: str, responses_dir: Path, out: Path, *,
        entities=None, content_span: str = "range", log=print) -> dict:
    from assistant_axis.internals import ConversationEncoder
    from assistant_axis.internals.chat_layout import derive_turn_end_ids
    from assistant_axis.generation import prompt_token_ids
    kwargs = dict(family.template_kwargs)
    encoder = ConversationEncoder(tokenizer, model_name, span_builder=family.span_builder)
    turn_end_ids = list(derive_turn_end_ids(tokenizer, family))
    special_ids = set(int(i) for i in tokenizer.all_special_ids)
    counts: dict = defaultdict(Counter)        # (entity, class) -> Counter
    out.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(responses_dir.glob("*.jsonl"))
    if entities:
        files = [f for f in files if f.stem in set(entities)]
    with open(out.with_suffix(".jsonl"), "w") as fh:
        for f in files:
            with open(f) as src:
                for index, line in enumerate(src):
                    r = json.loads(line)
                    cls = classify(r)
                    row = {"entity": f.stem, "key": mod.record_key(r), "class": cls}
                    ids, rng = r.get("response_token_ids"), r.get("content_token_range")
                    c = counts[(f.stem, cls)]
                    c["n"] += 1
                    if ids is not None:
                        c["tokens"] += len(ids)
                    if ids is None or rng is None:
                        row["status"] = "no ids" if ids is None else "range null"
                    else:
                        conv = r["conversation"]
                        stored = mod.StoredTokens(ids=[int(i) for i in ids],
                                                  content_range=(int(rng[0]), int(rng[1])))
                        text_ids, text_spans = encoder.build_turn_spans(conv, **kwargs)
                        ids_ids, ids_spans = mod.build_ids_path_sequence(
                            encoder, conv, stored, template_kwargs=kwargs, turn_end_ids=turn_end_ids,
                            special_ids=special_ids, entity=f.stem, index=index, content_span=content_span)
                        row["n_ids"] = len(ids)
                        row["n_content"] = int(rng[1]) - int(rng[0])
                        row["text_len"] = len(text_ids)
                        row["ids_len"] = len(ids_ids)
                        if text_ids == ids_ids:
                            row["status"] = "identical"
                            rel = mod.compare_assistant_spans(tokenizer, ids_ids, text_spans, ids_spans)
                            row["spans"] = rel
                            c["spans identical" if rel == "identical" else
                              "spans trimmed" if rel == mod.SPANS_BOUNDARY_WHITESPACE else
                              "spans different (a bug)"] += 1
                        else:
                            row["status"] = "differing"
                            n_prompt = len(prompt_token_ids(tokenizer, conv[:-1], kwargs))
                            row.update(mod.describe_token_difference(
                                tokenizer, text_ids, ids_ids, stored, n_prompt=n_prompt,
                                n_turn_end=len(turn_end_ids), special_ids=special_ids))
                            c["positions"] += row["positions"]
                            for k in row["kinds"]:
                                c[f"kind: {k}"] += 1
                    c[row["status"]] += 1
                    fh.write(json.dumps(row) + "\n")
    # Roll-ups: per entity, per class, over all.
    def rollup(keys):
        tot = Counter()
        for k in keys:
            tot.update(counts[k])
        return {ck: int(tot.get(ck, 0)) for ck in COUNT_KEYS} | {
            "spans different (a bug)": int(tot.get("spans different (a bug)", 0))}
    per_entity = {e: rollup([k for k in counts if k[0] == e]) for e in sorted({k[0] for k in counts})}
    per_class = {c: rollup([k for k in counts if k[1] == c]) for c in sorted({k[1] for k in counts})}
    per_entity_class = {f"{e}/{c}": rollup([(e, c)]) for (e, c) in sorted(counts)}
    overall = rollup(list(counts))
    doc = {"responses_dir": str(responses_dir), "content_span": content_span, "model": model_name,
           "per_entity": per_entity, "per_class": per_class, "per_entity_class": per_entity_class,
           "overall": overall}
    out.with_suffix(".json").write_text(json.dumps(doc, indent=1) + "\n")
    hdr = (f"{'entity':28} {'n':>5} {'ident':>5} {'=span':>5} {'trim':>5} {'diff':>5} {'plan':>5} "
           f"{'part':>5} {'spec':>5} {'resplit':>7} {'bws':>5} {'p/e':>5} {'null':>5} {'posns':>6} "
           f"{'tokens':>8}  rate")
    log(hdr)

    def line(name, r):
        rate = f"1 in {r['tokens'] / r['positions']:.0f}" if r["positions"] else "0"
        log(f"{name:28} {r['n']:5} {r['identical']:5} {r['spans identical']:5} {r['spans trimmed']:5} "
            f"{r['differing']:5} {r['kind: plan']:5} {r['kind: partial character']:5} "
            f"{r['kind: special token']:5} {r['kind: re-split']:7} {r['kind: boundary whitespace']:5} "
            f"{r['kind: prompt or end of turn']:5} {r['range null']:5} {r['positions']:6} "
            f"{r['tokens']:8}  {rate}")
    for e, r in per_entity.items():
        line(e, r)
    log("-" * len(hdr))
    for cl, r in per_class.items():
        line(f"class {cl}", r)
    line("ALL", overall)
    bugs = overall.get("spans different (a bug)", 0)
    if bugs:
        log(f"WARNING: {bugs} record(s) with identical ids but differing spans: a bug in the ids path")
    log(f"wrote {out.with_suffix('.jsonl')} and {out.with_suffix('.json')}")
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--responses_dir", required=True)
    ap.add_argument("--out", required=True, help="output prefix: <out>.jsonl and <out>.json")
    ap.add_argument("--repo", default="/workspace/assistant-axis", help="the checkout (its pipeline/2_activations.py)")
    ap.add_argument("--entities", nargs="*", default=None)
    ap.add_argument("--content_span", choices=("range", "turn"), default="range")
    args = ap.parse_args()
    mod = load_step2(Path(args.repo))
    pre = mod.preflight_model(args.model)
    run(mod, pre.tokenizer, pre.family, args.model, Path(args.responses_dir), Path(args.out),
        entities=args.entities, content_span=args.content_span)


if __name__ == "__main__":
    main()
