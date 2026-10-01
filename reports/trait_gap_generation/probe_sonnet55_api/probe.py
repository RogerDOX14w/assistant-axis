"""What does claude-sonnet-5-5 accept?  Four calls with the kind prompt and one recorded reading.
Tries a temperature of 0, thinking switched off, effort low, and the defaults; records what the
API answered and the tokens billed.  argv[1] = output dir."""
import json, re, sys
from pathlib import Path
import anthropic
from dotenv import load_dotenv

OUT = Path(sys.argv[1]); MODEL = "claude-sonnet-5-5"
PROMPT = re.search(r"## The prompt\n\n````text\n(.*?)\n````",
                   Path("reports/trait_gap_generation/rubrics/step2_kind.md").read_text(encoding="utf-8"), re.S).group(1)
SEND = json.dumps({"id": 1, "label": "taciturn", "reading": "you speak little and say few words"})
TRIALS = {
    "temperature_0": {"temperature": 0.0},
    "thinking_disabled": {"thinking": {"type": "disabled"}},
    "effort_low": {"output_config": {"effort": "low"}},
    "defaults": {},
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); load_dotenv(".env")
    client = anthropic.Anthropic(max_retries=0)
    rows = []
    for name, extra in TRIALS.items():
        row = {"trial": name, "model": MODEL, "extra": extra}
        try:
            resp = client.messages.create(model=MODEL, max_tokens=2000, system=PROMPT,
                                          messages=[{"role": "user", "content": SEND}], **extra)
            u = resp.usage
            row.update(ok=True, stop_reason=resp.stop_reason, blocks=[b.type for b in resp.content],
                       text="".join(b.text for b in resp.content if b.type == "text"),
                       usage={k: getattr(u, k, None) for k in ("input_tokens", "output_tokens",
                              "cache_creation_input_tokens", "cache_read_input_tokens")})
        except Exception as exc:  # noqa: BLE001
            row.update(ok=False, error=f"{type(exc).__name__}: {str(exc)[:400]}")
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False)[:700])
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


main()
