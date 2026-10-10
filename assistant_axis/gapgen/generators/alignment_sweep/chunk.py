"""Split the fetched sources into chunks, one extraction call each.

* **Headings** (the Model Spec's markdown; an HTML page, after :func:`html_to_markdown`): every heading starts a
  section; a section's chunk is its heading line and its body up to the next heading of any level, and its
  ``heading`` field is the path of titles from the top (``Seek the truth > Do not lie > Express uncertainty``),
  which the extraction prompt shows.  A heading with no body of its own (a chapter title followed at once by its
  first sub-heading) makes no chunk; its title is in its children's paths.  Lines inside fenced code blocks are
  never headings (the Model Spec's examples hold ``# functions`` and ``# [...] imports``).  The Model Spec's
  attributes (``{#avoid_sycophancy authority=user}``) are stripped from the text; the anchor names the chunk.
* **Long sections** (over ``max_tokens``, estimated at :data:`CHARS_PER_TOKEN`) are split at blank lines outside
  code fences into parts of at most ``max_tokens`` each (a single paragraph longer than that stays whole); every
  part starts with the section's heading line and is named ``<id>:p1``, ``<id>:p2``, ...
* **Rows** (a markdown or tab-separated table: Krakovna's sheet, MACHIAVELLI's categories): ``rows_per_chunk`` rows
  a chunk, the header row repeated at the top of each.
* A source's ``drop_before`` (a heading title) drops everything before that heading, and ``drop_sections`` drops a
  section with its sub-sections (the constitution's preface and acknowledgements).

Chunk ids are ``<source key>:<version label>:<anchor or slug>``, the form ``source_ref`` takes on every candidate
(``model_spec:2026-08-18:avoid_sycophancy``); a slug seen twice in a source gets ``-2``.  ``chunks.jsonl`` is
written in source order and rebuilt byte for byte from the same files (it is git-ignored, beside the texts).
No API call.
"""
from __future__ import annotations

import html as _html
import json
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.paths import REPO_ROOT

from .sources import SOURCES

#: Characters per token for the estimate (Anthropic's tokenizer of the Claude 4.7+ and 5 models runs about 30%
#: more tokens than older ones; the pilot measures the real figure).
CHARS_PER_TOKEN = 3.6
MAX_CHUNK_TOKENS = 3000
ROWS_PER_CHUNK = 10

_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*$")
_ATTRS = re.compile(r"\s*\{#([^\s}]+)[^}]*\}\s*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


class _Fences:
    """CommonMark fenced code blocks: a fence opens on three or more backticks or tildes and closes only on the
    same character, at least as many of them, with nothing after (so a ``~~~xml`` example holding triple-backtick
    blocks stays one block, as in the Model Spec)."""

    def __init__(self):
        self.open: Optional[tuple[str, int]] = None

    def feed(self, line: str) -> bool:
        """Advance over ``line``; True when the line is inside a fence or is a fence line itself."""
        m = _FENCE.match(line)
        if self.open is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                self.open = (m.group(1)[0], len(m.group(1)))
                return True
            return False
        if m and m.group(1)[0] == self.open[0] and len(m.group(1)) >= self.open[1] and not m.group(2).strip():
            self.open = None
        return True


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    heading: str
    text: str
    n_tokens_est: int

    def as_dict(self) -> dict:
        return asdict(self)


def tokens_est(text: str) -> int:
    return max(1, int(round(len(text) / CHARS_PER_TOKEN)))


def slugify(title: str) -> str:
    s = _html.unescape(title).lower().replace("’", "").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


# --------------------------------------------------------------------------- HTML -> markdown

class _MarkdownHTML(HTMLParser):
    """Headings (h1-h6) as ``#`` lines, paragraphs and list items as blocks, a table's rows as tab-separated
    lines, inside ``<main>`` when the page has one; script, style, nav, header, footer, svg, button, form and
    noscript are skipped."""

    SKIP = {"script", "style", "nav", "header", "footer", "svg", "button", "form", "noscript", "template", "aside"}
    BLOCK = {"p", "li", "blockquote", "pre", "dt", "dd", "figcaption", "caption"}

    def __init__(self, *, root_tag: Optional[str]):
        super().__init__(convert_charrefs=True)
        self.root_tag = root_tag
        self.in_root = root_tag is None       # the first <root_tag> ... </root_tag> only
        self.seen_root = False
        self.skip_depth = 0
        self.blocks: list[str] = []
        self.buf: list[str] = []
        self.kind: Optional[str] = None      # "h<n>", "li", "p"
        self.row: Optional[list[str]] = None
        self.cell: Optional[list[str]] = None

    def _inside(self) -> bool:
        return self.in_root and self.skip_depth == 0

    def _flush(self) -> None:
        text = " ".join("".join(self.buf).split())
        if text and self.kind:
            if self.kind.startswith("h"):
                self.blocks.append("#" * int(self.kind[1]) + " " + text)
            elif self.kind == "li":
                self.blocks.append("- " + text)
            else:
                self.blocks.append(text)
        self.buf, self.kind = [], None

    def handle_starttag(self, tag, attrs):
        if self.root_tag and tag == self.root_tag and not self.seen_root:
            self.in_root, self.seen_root = True, True
            return
        if not self.in_root:
            return
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if re.fullmatch(r"h[1-6]", tag) or tag in self.BLOCK:
            self._flush()
            self.kind = tag if tag.startswith("h") else ("li" if tag == "li" else "p")
        elif tag == "tr":
            self._flush()
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br":
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if not self.in_root:
            return
        if self.root_tag and tag == self.root_tag:
            self._flush()
            self.in_root = False
            return
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if re.fullmatch(r"h[1-6]", tag) or tag in self.BLOCK:
            self._flush()
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(c for c in self.row):
                self.blocks.append("\t".join(self.row))
            self.row = None

    def handle_data(self, data):
        if not self._inside():
            return
        if self.cell is not None:
            self.cell.append(data)
            return
        if self.kind is None:
            if not data.strip():
                return
            self.kind = "p"          # loose text between blocks
        self.buf.append(data)

    def close(self):
        super().close()
        self._flush()


def html_to_markdown(html_text: str, *, root_tag: Optional[str] = "main") -> str:
    """The text of an HTML page as markdown-like blocks separated by blank lines (headings as ``#`` lines, list
    items as ``- `` lines, table rows tab-separated).  Inside ``<main>`` when the page has one, else the whole
    page."""
    use_root = root_tag if (root_tag and re.search(rf"<{root_tag}[\s>]", html_text, re.I)) else None
    p = _MarkdownHTML(root_tag=use_root)
    p.feed(html_text)
    p.close()
    return "\n\n".join(p.blocks) + "\n"


def html_table_to_tsv(html_text: str) -> str:
    """Every table row of a page as a tab-separated line (the published-sheet form)."""
    md = html_to_markdown(html_text, root_tag=None)
    return "\n".join(line for line in md.split("\n\n") if "\t" in line) + "\n"


# --------------------------------------------------------------------------- headings

@dataclass
class _Section:
    level: int
    title: str
    anchor: Optional[str]
    heading_line: str
    body: list
    path: tuple


def _sections(text: str) -> list[_Section]:
    out: list[_Section] = []
    stack: list[tuple[int, str]] = []
    cur: Optional[_Section] = None
    fences = _Fences()
    pre: list[str] = []
    for line in text.splitlines():
        m = None if fences.feed(line) else _HEADING.match(line)
        if m:
            level, raw = len(m.group(1)), m.group(2)
            am = _ATTRS.search(raw)
            anchor = am.group(1) if am else None
            title = _ATTRS.sub("", raw).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            cur = _Section(level=level, title=title, anchor=anchor, heading_line=f"{m.group(1)} {title}", body=[],
                           path=tuple(t for _, t in stack))
            out.append(cur)
        elif cur is not None:
            cur.body.append(line)
        else:
            pre.append(line)
    return out


def _drop(sections: list[_Section], *, drop_before: Optional[str], drop_sections: Sequence[str]) -> list[_Section]:
    if drop_before:
        idx = next((i for i, s in enumerate(sections) if s.title == drop_before), None)
        if idx is not None:
            sections = sections[idx:]
    if drop_sections:
        keep, dropping_level = [], None
        for s in sections:
            if dropping_level is not None and s.level > dropping_level:
                continue
            dropping_level = None
            if s.title in drop_sections:
                dropping_level = s.level
                continue
            keep.append(s)
        sections = keep
    if drop_before and sections:
        # paths start below whatever was dropped
        top = sections[0].level
        for s in sections:
            depth = s.level - top + 1
            s.path = s.path[-depth:] if depth > 0 else (s.title,)
    return sections


def _paragraphs(lines: Sequence[str]) -> list[str]:
    paras, buf = [], []
    fences = _Fences()
    for line in lines:
        in_fence = fences.feed(line)
        if not line.strip() and not in_fence:
            if buf:
                paras.append("\n".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        paras.append("\n".join(buf))
    return paras


def chunk_markdown(key: str, text: str, *, version: str, max_tokens: int = MAX_CHUNK_TOKENS,
                   drop_before: Optional[str] = None, drop_sections: Sequence[str] = ()) -> list[Chunk]:
    out: list[Chunk] = []
    seen: dict[str, int] = {}
    for s in _drop(_sections(text), drop_before=drop_before, drop_sections=drop_sections):
        paras = _paragraphs(s.body)
        if not paras:
            continue
        slug = s.anchor or slugify(s.title)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        base = f"{key}:{version}:{slug}"
        heading = " > ".join(s.path)
        whole = s.heading_line + "\n\n" + "\n\n".join(paras)
        if tokens_est(whole) <= max_tokens:
            out.append(Chunk(base, key, heading, whole, tokens_est(whole)))
            continue
        parts, cur = [], []
        for p in paras:
            trial = s.heading_line + "\n\n" + "\n\n".join(cur + [p])
            if cur and tokens_est(trial) > max_tokens:
                parts.append(cur)
                cur = [p]
            else:
                cur.append(p)
        if cur:
            parts.append(cur)
        for i, part in enumerate(parts, 1):
            t = s.heading_line + "\n\n" + "\n\n".join(part)
            out.append(Chunk(f"{base}:p{i}", key, heading, t, tokens_est(t)))
    return out


# --------------------------------------------------------------------------- rows

def _table_rows(text: str) -> tuple[Optional[str], list[str]]:
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return None, []
    if lines[0].lstrip().startswith("|"):
        rows = [l for l in lines if l.lstrip().startswith("|") and not re.fullmatch(r"\s*\|[\s:|-]+\|?\s*", l)]
    else:
        rows = [l for l in lines if "\t" in l]
    return (rows[0], rows[1:]) if rows else (None, [])


def chunk_rows(key: str, text: str, *, version: str, rows_per_chunk: int = ROWS_PER_CHUNK) -> list[Chunk]:
    header, rows = _table_rows(text)
    out = []
    for start in range(0, len(rows), rows_per_chunk):
        block = rows[start:start + rows_per_chunk]
        a, b = start + 1, start + len(block)
        t = "\n".join([header] + block)
        out.append(Chunk(f"{key}:{version}:rows-{a:04d}-{b:04d}", key, f"rows {a}-{b}", t, tokens_est(t)))
    return out


# --------------------------------------------------------------------------- sources

def source_markdown(key: str, raw: str) -> str:
    """A fetched source's text in the form :func:`chunk_markdown` reads."""
    fmt = SOURCES[key].fmt
    if fmt == "html":
        return html_to_markdown(raw)
    if fmt == "sheet_html":
        return html_table_to_tsv(raw)
    return raw


def chunk_source(key: str, text: str, *, version: Optional[str] = None, max_tokens: int = MAX_CHUNK_TOKENS,
                 rows_per_chunk: int = ROWS_PER_CHUNK) -> list[Chunk]:
    """Chunks of one source's fetched text (raw: HTML is converted here), named with ``version`` (default the
    source's ``version_label``)."""
    s = SOURCES[key]
    version = version or s.version_label
    if not version:
        raise ValueError(f"{key}: no version label (the capture date is set by fetch)")
    body = source_markdown(key, text)
    if s.fmt in ("table", "sheet_html"):
        return chunk_rows(key, body, version=version, rows_per_chunk=rows_per_chunk)
    return chunk_markdown(key, body, version=version, max_tokens=max_tokens, drop_before=s.drop_before,
                          drop_sections=s.drop_sections)


def _abs(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def build_all(manifest: Iterable[Mapping], *, max_tokens: int = MAX_CHUNK_TOKENS) -> list[Chunk]:
    """Chunks of every fetched source in the manifest (``FETCH_MANIFEST.json`` entries), in manifest order."""
    out: list[Chunk] = []
    for e in manifest:
        if e.get("key") not in SOURCES or not e.get("file"):
            continue
        raw = _abs(e["file"]).read_text(encoding="utf-8", errors="replace")
        out.extend(chunk_source(e["key"], raw, version=e.get("version_label"), max_tokens=max_tokens))
    return out


def write_chunks(chunks: Sequence[Chunk], path: Path) -> Path:
    atomic_write_text("".join(json.dumps(c.as_dict(), ensure_ascii=False) + "\n" for c in chunks), Path(path))
    return Path(path)


def load_chunks(path: Path) -> list[Chunk]:
    return [Chunk(**json.loads(l)) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def counts(chunks: Sequence[Chunk]) -> dict:
    """``{source: {"n_chunks", "n_tokens_est", "max_tokens_est"}, "_total": {...}}``."""
    out: dict = {}
    for c in chunks:
        d = out.setdefault(c.source, {"n_chunks": 0, "n_tokens_est": 0, "max_tokens_est": 0})
        d["n_chunks"] += 1
        d["n_tokens_est"] += c.n_tokens_est
        d["max_tokens_est"] = max(d["max_tokens_est"], c.n_tokens_est)
    out["_total"] = {"n_chunks": len(chunks), "n_tokens_est": sum(c.n_tokens_est for c in chunks),
                     "max_tokens_est": max((c.n_tokens_est for c in chunks), default=0)}
    return out


__all__ = ["Chunk", "CHARS_PER_TOKEN", "MAX_CHUNK_TOKENS", "ROWS_PER_CHUNK", "html_to_markdown",
           "html_table_to_tsv", "chunk_markdown", "chunk_rows", "chunk_source", "source_markdown", "build_all",
           "write_chunks", "load_chunks", "counts", "slugify", "tokens_est"]
