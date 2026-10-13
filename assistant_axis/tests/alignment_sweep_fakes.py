"""Fixtures for the alignment sweep's tests (no network): a small spec in the Model Spec's markdown form, a small
page in the constitution's HTML form, a table, fake fetchers and fake clients."""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Callable, Optional

#: Six headings, one of them a parent with no body of its own, a fenced code block holding '#' lines, and a
#: heading with attributes, as the Model Spec writes them.
SPEC_MD = """# Overview {#overview}

The assistant should be useful and safe.

## Follow instructions {#follow_instructions authority=root}

Follow the instructions of the people you work for.

```
# this is a comment inside code, not a heading
print("hello")
```

## Act within scope {#scope_of_autonomy authority=root}

Do not take actions beyond what was asked.

# Seek the truth {#seek_truth}

## Do not lie {#do_not_lie authority=user}

Never state what you believe to be false.

### Express uncertainty {#express_uncertainty authority=guideline}

Say how sure you are.

## Avoid flattery

Do not praise work that does not deserve it.
"""

#: The constitution's shape: a preface before "Overview", a section to drop, nested headings, a list.
CONSTITUTION_HTML = """<!doctype html><html><head><title>Constitution</title><script>var x = "<h2>no</h2>";</script>
<style>h2 {color: red}</style></head><body><nav><h2>Site menu</h2><a href="/">Home</a></nav>
<main><h1>The Charter</h1><p>A preface about the document. We&#8217;re releasing it in full under a Creative Commons
CC0 1.0 Deed, meaning anyone may use it.</p>
<h2>Read a summary</h2><p>Summary text.</p>
<h2>Overview</h2><p>The model should be <em>broadly safe</em> and broadly ethical.</p>
<h3>Core values</h3><ul><li>Be honest.</li><li>Avoid harm.</li></ul>
<h2>Being safe</h2><h3>Safe behaviors</h3><p>Do not undermine oversight.</p><p>Do not acquire resources beyond
what a task needs.</p>
<h2>Acknowledgements</h2><p>Thanks to many people.</p><h3>Contributors</h3><p>Names.</p>
</main><footer><p>Footer text</p></footer></body></html>"""

TABLE_MD = """| Title | Intended goal | Behaviour |
|---|---|---|
| Boat race | finish the race | circles to collect points |
| Tetris | survive | pauses the game forever |
| Grasping | grasp the ball | hovers between camera and ball |
| Walking | walk forward | slides on its back |
| Coding | pass the tests | edits the tests |
"""

#: Krakovna's sheet in the form its TSV export (``<sheet>/pub?output=tsv``) had on 2026-10-13: CRLF line ends, ten
#: cells on every line, a banner line above the header, and section dividers (one filled cell, the second) before
#: each section's examples.  The banner, header and section names are the sheet's; the examples are invented (the
#: sheet has no licence, and its text is never stored).
KRAKOVNA_HEADER = ("Title", "Description", "Illustration", "Type of system", "Intended goal", "Misspecified goal",
                   "Behavior", "Authors", "Source", "Credit")
KRAKOVNA_BANNER = "Submit more examples through this form"
KRAKOVNA_SECTIONS = ("Evolutionary and genetic algorithms", "Large language models (LLMs)",
                     "Reinforcement learning (RL)")


def krakovna_line(*cells: str) -> str:
    return "\t".join(list(cells) + [""] * (len(KRAKOVNA_HEADER) - len(cells)))


def krakovna_example(i: int, j: int) -> str:
    return krakovna_line(f"Example {i}.{j}", f"An agent in setting {i}.{j} meets the letter of its goal.", "",
                         "RL agent", f"goal {i}.{j}", f"proxy {i}.{j}", f"games proxy {i}.{j}", "A. Author",
                         f"https://example.org/{i}-{j}", "")


#: 24 rows under the header (3 dividers and 21 examples) and one empty row (tabs only) at the end: 3 chunks of
#: up to 10 rows.
KRAKOVNA_TSV_EXPORT = "\r\n".join(
    [krakovna_line("", KRAKOVNA_BANNER, "More information in this blog post", "", "",
                   "Related: goal misgeneralisation examples"),
     "\t".join(KRAKOVNA_HEADER)]
    + [line for i, sec in enumerate(KRAKOVNA_SECTIONS, 1)
       for line in [krakovna_line("", sec)] + [krakovna_example(i, j) for j in range(1, 8)]]
    + [krakovna_line()]) + "\r\n"


def fake_fetcher(pages: dict[str, bytes], calls: Optional[list] = None) -> Callable[[str], bytes]:
    def fetch(url: str) -> bytes:
        if calls is not None:
            calls.append(url)
        if url not in pages:
            raise RuntimeError(f"unexpected URL {url}")
        return pages[url]
    return fetch


# --------------------------------------------------------------------------- OpenRouter (probe)

def openrouter_response(content: str, *, provider: str = "DeepInfra", prompt_tokens: int = 60,
                        completion_tokens: int = 30, reasoning: Optional[str] = None):
    msg = SimpleNamespace(content=content, reasoning=reasoning)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], provider=provider,
                           usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


class FakeCompletions:
    def __init__(self, responder):
        self.responder = responder
        self.calls: list[dict] = []

    async def create(self, **kw):
        self.calls.append(kw)
        out = self.responder(kw)
        if isinstance(out, BaseException):
            raise out
        return out


class FakeAsyncOpenAI:
    """``responder(kwargs) -> response | Exception``, the ``chat.completions.create`` of ``openai.AsyncOpenAI``."""

    def __init__(self, responder):
        self.chat = SimpleNamespace(completions=FakeCompletions(responder))

    @property
    def calls(self):
        return self.chat.completions.calls


def extraction_reply(items: list[dict], reasoning: str = "The passage tells the assistant how to behave.") -> str:
    return json.dumps({"reasoning": reasoning, "items": items})


def pole(label: str, gloss: str, *, label_kind: str = "ordinary", polysemy: Optional[str] = None) -> dict:
    return {"label": label, "gloss": gloss, "label_kind": label_kind, "polysemy": polysemy}


def item(virtue: dict, vice: dict, *, source_pole: str = "virtue", type_: str = "behaviour",
         enactability: str = "chat", quote: str = "Never state what you believe to be false.",
         reason: str = "An imperative about honesty.") -> dict:
    return {"reason": reason, "source_quote": quote, "source_pole": source_pole, "type": type_,
            "enactability": enactability, "virtue": virtue, "vice": vice}
