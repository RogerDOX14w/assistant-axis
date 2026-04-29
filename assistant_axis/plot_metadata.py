"""Helpers for embedding provenance metadata in plot images.

The convention (see ``AGENT_NOTES.md`` and the main ``README.md``) is
that every plot generated in this repo carries a PNG-text-chunk
metadata block.  The exact contents depend on whether the plot came
from a tracked script or an ad-hoc exploratory script:

Tracked-script plot
-------------------

::

    from assistant_axis import png_metadata
    fig.savefig(out, metadata=png_metadata(title="Plot title"))

Embeds:

- ``Title``         -- short human-readable label (first line of suptitle).
- ``Author``        -- ``Roger Dearnaley`` by default.
- ``Software``      -- canonical UNIX command (``uv run python ...``)
                       reconstructed from ``sys.argv``, relative to the
                       repo root.  Reproduces the run.
- ``Creation Time`` -- ISO-8601 local timestamp.
- ``Source``        -- git short SHA (``+dirty`` if working tree dirty).

Ad-hoc plot (e.g. /tmp/foo.py during exploration)
-------------------------------------------------

::

    from pathlib import Path
    fig.savefig(out, metadata=png_metadata(
        title="Plot title",
        source_text=Path(__file__).read_text(),
    ))

Adds two more chunks on top of the tracked-script set:

- ``Source Code``        -- full body of the entry-point Python file.
- ``Source Code SHA256`` -- hex digest, for tamper detection.

If the work spans multiple Python files (rare; usually means the work
is graduating to a tracked module), pass ``source_files={...}``
instead -- a ``{filename: body}`` mapping serialised to JSON in the
same chunk.

Inline heredocs (``uv run python << 'PY' ... PY``) cannot read their
own body via ``__file__``, so heredoc-driven plots cannot embed source
code -- prefer writing a ``/tmp/<descriptive_name>.py`` file when the
plot is interesting enough to want to reproduce later.

Recovery (any embedded plot)
----------------------------

::

    from PIL import Image
    info = Image.open("plot.png").info
    print(info.get("Software"))         # how to re-run a tracked-script plot
    src = info.get("Source Code")       # ad-hoc plots only; runnable as-is

PNG size note
-------------

Each ``tEXt``/``iTXt`` chunk supports up to ~2 GB per the spec; the
typical few-KB source body is far below any practical limit.

API
---

The single public entry point is :func:`png_metadata`.
"""
from __future__ import annotations

import datetime as _datetime
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

__all__ = [
    "png_metadata",
    "suptitle_with_specs",
    "REPO_ROOT",
    "DEFAULT_AUTHOR",
]


DEFAULT_AUTHOR = "Roger Dearnaley"


def _find_repo_root() -> Path:
    """Locate the repo root by walking up from this file until we find
    a ``.git`` directory."""
    here = Path(__file__).resolve().parent
    for d in [here, *here.parents]:
        if (d / ".git").is_dir() or (d / ".git").is_file():
            return d
    return here.parent  # fallback


REPO_ROOT = _find_repo_root()


def _relative_to_repo(p: str | os.PathLike) -> str:
    """Return ``p`` as a forward-slash path relative to the repo root,
    or the original string if it lies outside the repo."""
    p = Path(p)
    try:
        rel = p.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return str(p)
    return str(rel).replace(os.sep, "/")


def _git_sha() -> str | None:
    """Best-effort short git SHA + dirty flag.  Returns None if git is
    unavailable or the working tree isn't a repo."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
            timeout=2,
        )
        if sha.returncode != 0:
            return None
        out = sha.stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
            timeout=2,
        )
        if dirty.returncode == 0 and dirty.stdout.strip():
            out += "+dirty"
        return out
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def png_metadata(
    title: str,
    *,
    author: str = DEFAULT_AUTHOR,
    script: str | None = None,
    argv: list[str] | None = None,
    interpreter: str = "uv run python",
    source_text: str | None = None,
    source_files: dict[str, str] | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a PNG metadata dict suitable for ``fig.savefig(metadata=...)``.

    Parameters
    ----------
    title : str
        Short human-readable title (typically the first line of the
        figure's suptitle).
    author : str, optional
        Author name; default ``"Roger Dearnaley"``.
    script : str, optional
        Path of the producing script.  Defaults to ``sys.argv[0]``,
        coerced to a forward-slash path relative to the repo root if
        possible.  If invoked via ``python -m foo.bar`` the dotted
        module path is used.
    argv : list[str], optional
        CLI arguments that produced the figure.  Defaults to
        ``sys.argv[1:]``.  Pass an empty list (``[]``) for "no args".
    interpreter : str, optional
        Command prefix used to reproduce the run.  Default
        ``"uv run python"`` matches our project's standard invocation
        pattern.
    source_text : str, optional
        Full source code of the entry-point script.  When set, embeds
        ``Source Code`` and ``Source Code SHA256`` chunks so the plot
        can be reproduced even when the script is not tracked in git.
        Typical use: ``source_text=Path(__file__).read_text()``.
        Mutually exclusive with ``source_files``.
    source_files : dict[str, str], optional
        Multi-file source bundle ``{filename: body}``; embedded as a
        single JSON-serialised ``Source Code`` chunk plus a
        ``Source Code Files`` index.  Mutually exclusive with
        ``source_text``.  Use only when more than one source file is
        genuinely needed; usually a sign the work should be promoted
        to a tracked module.
    extra : dict[str, str], optional
        Additional metadata fields to embed.  Reserved keys
        (``Title``, ``Author``, ``Software``, ``Creation Time``,
        ``Source``, ``Source Code``, ``Source Code SHA256``,
        ``Source Code Files``) take precedence over ``extra``.

    Returns
    -------
    dict[str, str]
        Metadata mapping; pass directly to ``Figure.savefig(metadata=...)``.

    Examples
    --------

    Inside a CLI wrapper that does ``argparse.ArgumentParser`` etc.:

    >>> fig.savefig(out_path,
    ...             metadata=png_metadata(title="Goal vs nogoal CA"))

    With explicit reproduction command:

    >>> fig.savefig(out_path,
    ...             metadata=png_metadata(
    ...                 title="ρ vs K (12 axes)",
    ...                 script="results_analysis/whitening_k_sweep.py",
    ...                 argv=["--pairs", "pair_list_12.json"]))

    Ad-hoc exploration script (write to ``/tmp`` first, then read self):

    >>> from pathlib import Path
    >>> fig.savefig(out_path,
    ...             metadata=png_metadata(
    ...                 title="Quick exploration",
    ...                 source_text=Path(__file__).read_text()))
    """
    # Detect ``python -m foo.bar`` invocations: __main__.__spec__ is the
    # ModuleSpec of the loaded module in that case (None for direct
    # ``python foo.py`` invocations).  When -m was used we must record
    # the dotted module path, not the on-disk file path -- because
    # packages with relative imports refuse to run as bare scripts.
    if script is None and argv is None:
        main_spec = getattr(sys.modules.get("__main__"), "__spec__", None)
        if main_spec is not None and main_spec.name not in (None, "__main__"):
            script = "-m " + main_spec.name
            argv = list(sys.argv[1:])

    if script is None:
        argv0 = sys.argv[0] if sys.argv else ""
        script = _relative_to_repo(argv0) if argv0 else "<unknown>"
    elif not script.startswith("-m "):
        script = _relative_to_repo(script)

    if argv is None:
        argv = list(sys.argv[1:])

    cmd = f"{interpreter} {script}"
    if argv:
        cmd += " " + " ".join(shlex.quote(a) for a in argv)

    if source_text is not None and source_files is not None:
        raise ValueError(
            "pass at most one of source_text= or source_files=")

    sha = _git_sha()
    md: dict[str, str] = {}
    if extra:
        md.update(extra)
    md["Title"] = title
    md["Author"] = author
    md["Software"] = cmd
    md["Creation Time"] = (
        _datetime.datetime.now().astimezone()
        .strftime("%Y-%m-%d %H:%M:%S %z")
    )
    if sha is not None:
        md["Source"] = f"git {sha}"

    if source_text is not None:
        md["Source Code"] = source_text
        md["Source Code SHA256"] = hashlib.sha256(
            source_text.encode("utf-8")).hexdigest()
    elif source_files is not None:
        # Stable serialisation so the SHA256 of the same files always
        # matches regardless of dict insertion order.
        body = json.dumps(source_files, indent=2, sort_keys=True,
                          ensure_ascii=False)
        md["Source Code"] = body
        md["Source Code Files"] = ", ".join(sorted(source_files))
        md["Source Code SHA256"] = hashlib.sha256(
            body.encode("utf-8")).hexdigest()
    return md


# ---------------------------------------------------------------------------
# Plot title / spec-details helper
# ---------------------------------------------------------------------------

def suptitle_with_specs(
    fig,
    title: str,
    specs: str | list[str] | None = None,
    *,
    title_fontsize: int = 14,
    spec_fontsize: int = 10,
    spec_color: str = "#444444",
    title_y: float = 0.99,
    line_height: float = 0.022,
) -> tuple[float, float]:
    """Render a two-tier figure title: bold headline + smaller spec block.

    The "headline" (large, bold) goes into ``fig.suptitle`` so it
    interacts correctly with ``bbox_inches="tight"``; the spec details
    (smaller, non-bold, dimmer) are rendered as a separate
    ``fig.text`` annotation just below.

    Parameters
    ----------
    fig : matplotlib Figure
    title : single-line headline (e.g. "Mean per-axis ρ vs layer")
    specs : optional spec details.  ``str`` may contain ``\\n`` for
        multiple lines, or a list of strings (one per line).  Pass
        ``None`` (or an empty string) to skip the spec block entirely
        -- this function then degrades to a plain bold ``suptitle``.
    title_fontsize, spec_fontsize, spec_color : style overrides.
    title_y : figure-relative y for the bold headline (1.0 is the top
        edge of the figure).  Default 0.99 leaves a tiny margin.
    line_height : figure-relative spacing between the headline and the
        first spec line, and between subsequent spec lines.  Tune
        upward for taller figures.

    Returns
    -------
    (top_used, top_rect) : the figure-relative y coordinate of the
        bottom of the spec block, and a value suitable for the
        ``rect`` argument to ``fig.tight_layout`` so the body of the
        figure is laid out below the title block.  Caller can do::

            top_used, top_rect = suptitle_with_specs(fig, ..., specs=...)
            fig.tight_layout(rect=(0, 0, 1, top_rect))
    """
    fig.suptitle(title, fontsize=title_fontsize, fontweight="bold",
                 y=title_y)
    if not specs:
        # Default tight_layout reserve for a single-line bold suptitle.
        return title_y - line_height, title_y - line_height - 0.01

    if isinstance(specs, str):
        text = specs
        n_lines = 1 + specs.count("\n")
    else:
        text = "\n".join(specs)
        n_lines = len(specs)

    # First spec line sits one line-height below the headline.
    first_line_y = title_y - line_height
    fig.text(0.5, first_line_y, text,
             ha="center", va="top",
             fontsize=spec_fontsize, color=spec_color)
    bottom = first_line_y - (n_lines - 1) * line_height
    return bottom, max(0.85, bottom - 0.015)
