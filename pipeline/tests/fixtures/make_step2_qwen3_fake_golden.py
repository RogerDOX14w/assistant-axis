#!/usr/bin/env python3
"""Make the step-2 golden fixture: what step 2 writes for Qwen3 on the fakes.

Task 0 of the multi-model plan
(reports/pipeline/coding_plan_multi_model_extraction.md § 9 test 1, § 10
task 0).  The fixture is the byte-identical gate for the generalisation of
steps 1 and 2: it is made once, from the code as it was **before** that
work (commit 828817a471d19d78023beaa68dc2e35566865102, exported with
``git archive`` into a scratch directory and passed as ``--source-root``),
and pipeline/tests/test_step2_qwen3_golden.py compares today's step 2 with
it bit for bit.  Do not regenerate it from changed code: that would make
the gate pass by definition.

What it runs, on the in-process fakes only (no model, no download):
``pipeline/2_activations.py`` ``process_role`` on the Qwen3-like fake
tokenizer and ``FakeCausalLM`` (``assistant_axis/tests/internals_fakes.py``)
over the 12 response records written to ``step2_qwen3_fake_golden.jsonl``,
twice: with the header slots (all 3 layers, batch size 5, so the batches are
5, 5 and 2 and padding differs between them) and without them
(``extract_headers=False``, layer 2 only, batch size 4).  ``max_length`` is
64 in both, so record 7's response is cut part way and record 8's lies
wholly past it.  The records cover a system prompt and none, an empty
response, leading and trailing newlines, a two-token user question, words
the fake vocabulary does not know, a leading space and an inner blank line.

Usage (from the repository root):

    git archive <sha> assistant_axis pipeline | tar -x -C <scratch>/pre
    uv run python pipeline/tests/fixtures/make_step2_qwen3_fake_golden.py \\
        --source-root <scratch>/pre --source-commit <sha>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
JSONL_NAME = "step2_qwen3_fake_golden.jsonl"
PT_NAME = "step2_qwen3_fake_golden.pt"

SYSTEM = "You are a pirate"
QUESTION = "What is law?"
# (system prompt or None, user question, response), in record order.
RECORDS = [
    (SYSTEM, QUESTION, "Arr matey. Law rules!"),
    (None, QUESTION, "Yes"),
    (SYSTEM, QUESTION, ""),                                   # empty: no activation
    (None, QUESTION, "\n\nArr matey!\n"),                    # leading and trailing newlines
    (SYSTEM, QUESTION, "Hello there.\n\n"),
    (SYSTEM, "Yes?", "Law rules, matey."),                   # a two-token user question
    (None, "Yes?", "no"),
    (SYSTEM, QUESTION, "Arr matey, the law of the code is the law. " * 6),   # cut at 64
    ("You are a pirate. " * 12, QUESTION, "Arr"),            # wholly past 64
    (SYSTEM, QUESTION, "Ahoy, landlubber! Yes."),            # unknown words
    (SYSTEM, QUESTION, " x and code"),                       # leading space
    (None, QUESTION, "Law\n\nrules\n"),                      # inner blank line
]
MAX_LENGTH = 64
HEADERS_RUN = {"layers": [0, 1, 2], "batch_size": 5, "extract_headers": True}
NO_HEADERS_RUN = {"layers": [2], "batch_size": 4, "extract_headers": False}


def response_records() -> list[dict]:
    out = []
    for i, (system, question, response) in enumerate(RECORDS):
        conv = [{"role": "system", "content": system}] if system is not None else []
        conv += [{"role": "user", "content": question},
                 {"role": "assistant", "content": response}]
        out.append({"conversation": conv, "prompt_index": i % 3, "question_index": i,
                    "label": "pos"})
    return out


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_step2(source_root: Path, responses_file: Path, work_dir: Path, run: dict):
    """``process_role`` of ``source_root``'s step 2 on the fakes; returns the
    saved dict (activations and ``"metadata"``) and the mismatch count."""
    import torch
    from assistant_axis.tests.internals_fakes import make_fake_probing_model

    step2 = _load_module("_golden_step2", source_root / "pipeline" / "2_activations.py")
    pm = make_fake_probing_model(3)
    out_dir = work_dir / ("headers" if run["extract_headers"] else "no_headers")
    out_dir.mkdir(parents=True)
    saved, n_mm = step2.process_role(pm, responses_file, out_dir, run["layers"],
                                     run["batch_size"], MAX_LENGTH,
                                     extract_headers=run["extract_headers"])
    assert saved
    data = torch.load(out_dir / f"{responses_file.stem}.pt", weights_only=False)
    return data, n_mm


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--source-root", required=True, type=Path,
                   help="a checkout (or git archive) of the commit to record")
    p.add_argument("--source-commit", required=True, help="that commit's sha")
    p.add_argument("--out-dir", type=Path, default=HERE)
    args = p.parse_args(argv)

    source_root = args.source_root.resolve()
    sys.path.insert(0, str(source_root))
    import assistant_axis  # noqa: E402
    if Path(assistant_axis.__file__).resolve().parent.parent != source_root:
        raise SystemExit(f"assistant_axis resolved to {assistant_axis.__file__}, "
                         f"not under {source_root}")
    import torch

    args.out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = args.out_dir / JSONL_NAME
    jsonl.write_text("".join(json.dumps(r) + "\n" for r in response_records()))

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        responses = work / "golden.jsonl"
        responses.write_text(jsonl.read_text())
        fixture = {"source_commit": args.source_commit, "max_length": MAX_LENGTH}
        for key, run in (("headers", HEADERS_RUN), ("no_headers", NO_HEADERS_RUN)):
            data, n_mm = run_step2(source_root, responses, work, run)
            meta = data.pop("metadata")
            fixture[key] = {"run": dict(run), "activations": data, "metadata": meta,
                            "mismatches": n_mm}
            print(f"{key}: {len(data)} activations {sorted(data)}; metadata {meta}; "
                  f"{n_mm} mismatches")
    torch.save(fixture, args.out_dir / PT_NAME)
    print(f"wrote {args.out_dir / PT_NAME} and {jsonl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
