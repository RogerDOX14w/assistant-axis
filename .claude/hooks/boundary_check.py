#!/usr/bin/env python3
"""PreToolUse hook: ask before any tool call that names a path under the home
directory outside the project boundary (AGENT_NOTES / CLAUDE.md § "File Access
Boundary").  Enforcement, not documentation: on 2026-09-17 five planning
subagents listed caches under ~ against the written rule and their brief, and
only three reported it.

Reads the hook JSON on stdin.  For Bash it scans the command text for
home-directory paths (``/Users/<user>/...``, ``~/...``, ``$HOME/...``) and for
tokens that climb out of the working directory (``../``).  For the file tools
(Read, Edit, Write, NotebookEdit, Glob, Grep) it resolves the path fields
against the call's cwd.  Any hit outside the allowlist prints a
``permissionDecision: "ask"`` so Roger sees the command and decides; anything
else prints nothing (the normal permission flow applies).  In Auto mode the
classifier allows or blocks and never prompts, so every prompt Roger sees
there is one of this hook's asks: a false positive costs him an interruption.

What counts as a path (narrowed 2026-09-28, after four false positives in
twenty minutes):

  - A tilde only where a shell or ``expanduser`` would expand it, at the start
    of a word: after whitespace, a quote, a separator (``; | & ( < > { ,``)
    or an assignment's ``=`` / ``:``.  ``HEAD~1``, ``<sha>~2``, ``notes.txt~``
    and the match operators ``=~`` / ``!~`` are not paths.  ``~name/...`` is
    resolved for a real user and asked about when it leaves the allowlist.
  - ``../x`` wherever it appears, heredoc bodies included.
  - A bare ``..`` on the command line (``cd ..``, ``cd ".."``,
    ``os.listdir('..')`` in a ``-c`` string).  Inside a heredoc body only the
    quoted form counts, which is how a script climbs out; an unquoted ``..``
    there is prose ("3f6de81 .. 62855c7").  Git ranges (``a..b``) and
    ellipses never matched.

Climbs are resolved, not pattern-matched (2026-09-28, Roger: "if we're
building a security precaution, we should make it reasonably secure"):

  - A ``..`` in the middle of a path (``data/../../x``, ``./../x``) is
    resolved against the working directory and asked about when it lands
    outside the allowlist; ``data/../README.md`` stays inside and is quiet.
  - A base the scan cannot read (``$PWD/../x``, ``$(pwd)/../x``,
    ``"$d"/../x``) is taken to be the working directory.
  - A home form asks wherever it resolves, so ``~/..``, ``$HOME/../other``
    and ``/Users/<user>/../other`` ask although they leave the home
    directory.  The file tools follow the same rules.

What it cannot see: a climb the text does not spell (``cd`` inside the
command followed by a relative path, ``Path(x).parent.parent``, a variable
set elsewhere, a symlink).  It is a backstop against honest mistakes, not a
sandbox.

Allowlist (all prefixes):
  - the repository itself
  - ~/.claude/            (Claude Code's own state: memory, plans, settings)
  - /tmp and /private/tmp   (scratch generally, including the claude-* session scratchpads)
  - ~/.cursor/projects/*/terminals/ and */agent-tools/   (Cursor tool infrastructure)

Known false positive: the Bash scan sees text, not shell syntax, so a heredoc
whose *body* mentions a home path (for example an edit to the boundary rule
itself) also triggers the ask.  Since 2026-09-25 the reason says when every
match is inside a heredoc body, so a prose edit can be judged at a glance; it
stays an ask because a heredoc-fed script can open the path just as well as
mention it.  Prose that quotes home paths is better written with the Write /
Edit tools, which the hook checks by path only.
"""
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWED_PREFIXES = (
    REPO,
    os.path.join(HOME, ".claude"),
    "/tmp",  # Roger, 2026-09-25: /tmp generally, not only the claude-* scratchpads
    "/private/tmp",
)
ALLOWED_PATTERNS = (
    re.compile(re.escape(os.path.join(HOME, ".cursor", "projects")) + r"/[^/]+/(terminals|agent-tools)(/|$)"),
)
FILE_TOOLS = {"Read", "Edit", "Write", "NotebookEdit", "Glob", "Grep"}
_PATH_TAIL = r"(?:/[^\s\"'`;|&)>]*)?"
# a tilde at the start of a word: nothing before it, or whitespace, a quote or a separator,
# or the ``=`` / ``:`` of an assignment (``X=~/a``, ``PATH=a:~/b``; not the operator `` =~ ``)
_WORD_START = r"(?:(?<![^\s\"'`;|&(<>{,])|(?<=[^\s=!][=:]))"
HOME_PATH = re.compile(
    r"(?:" + re.escape(HOME) + r"|\$HOME|\$\{HOME\})" + _PATH_TAIL
    + r"|" + _WORD_START + r"~(?:[A-Za-z_][\w.-]*)?" + _PATH_TAIL
)
CLIMB_PATH = re.compile(r"(?<![\w./])\.\./[^\s\"'`;|&)>]*")
CLIMB_BARE = re.compile(r"(?<![\w./])\.\.(?=[\s;|&)\"'`]|$)")
# a whole path token holding ``..`` as a component after a slash: ``data/../../x``, ``./../x``,
# and the tail of ``$(pwd)/../x``.  ``=`` and ``,`` end the token's head (``--out=a/../../b``)
CLIMB_MID = re.compile(r"[^\s\"'`;|&()<>=,]*/\.\.(?=/|[\s\"'`;|&)>]|$)[^\s\"'`;|&)>]*")
HOME_FORMS = ("~", "$HOME", "${HOME}", HOME)
QUOTES = "\"'`"
# ``<<EOF``, ``<<-EOF``, ``<<'EOF'``, ``<<"EOF"``, ``<<\EOF``; not the here-string ``<<<``
# a bare delimiter must start with a letter or underscore and may not be followed by ``)``,
# so neither ``$((1 << 3))`` nor ``$((x << y))`` is a marker
HEREDOC = re.compile(r"(?<!<)<<-?[ \t]*(?:'([^'\n]+)'|\"([^\"\n]+)\"|\\?([A-Za-z_][\w.-]*))(?![<)])")


def normalize(p: str) -> str:
    p = p.replace("${HOME}", HOME).replace("$HOME", HOME)
    if p == "~" or p.startswith("~/"):
        p = HOME + p[1:]
    elif p.startswith("~"):
        p = os.path.expanduser(p)  # ``~name/...``; an unknown name stays as written
    return os.path.normpath(p)


def allowed(p: str) -> bool:
    p = os.path.normpath(p)
    if any(p == a.rstrip("/") or p.startswith(a if a.endswith("-") else a.rstrip("/") + "/") for a in ALLOWED_PREFIXES):
        return True
    return any(pat.match(p) for pat in ALLOWED_PATTERNS)


def resolve_climb(token: str, cwd: str):
    """Where a path token with a ``..`` component lands, or None when the
    token is another rule's business or outside this hook's remit.

    Home forms are left to ``HOME_PATH``, which resolves them itself.  An
    absolute path is reported only when it lands under the home directory
    (``/usr/lib/../bin`` is no more this hook's concern than ``/usr/bin``).
    A relative path is resolved against the working directory.  So is a path
    whose base the scan cannot read: a leading ``$VAR`` or ``${VAR}``, or a
    token that starts with ``/..``, which is never a real absolute path but
    the tail of ``$(pwd)/../x`` or ``"$d"/../x``.
    """
    if token.startswith(HOME_FORMS):
        return None
    head = token.split("/", 1)[0]
    if head.startswith("$") or token.startswith("/.."):
        return os.path.normpath(cwd + token[len(head):])
    if os.path.isabs(token):
        p = os.path.normpath(token)
        return p if p == HOME or p.startswith(HOME + "/") else None
    return os.path.normpath(os.path.join(cwd, token))


def heredoc_bodies(text: str) -> list:
    """Spans (start, end) of heredoc bodies in a shell command.

    A marker is ``<<``, ``<<-`` and a delimiter (bare, quoted or
    backslashed); the body runs from the next line to the line holding the
    delimiter alone (leading tabs allowed), or to the end of the text when it
    is unterminated.  Markers found inside a body are skipped, so a ``<<`` in
    a Python script does not start a nested body.  Only the ask *reason* uses
    this; it never decides whether to ask.
    """
    spans = []
    pos = 0  # a body on the same line as an earlier marker starts after that body
    for m in HEREDOC.finditer(text):
        if any(s <= m.start() < e for s, e in spans):
            continue
        delim = m.group(1) or m.group(2) or m.group(3)
        line_end = text.find("\n", m.end())
        if line_end == -1:
            break
        start = max(line_end + 1, pos)
        term = re.compile(r"^\t*" + re.escape(delim) + r"[ \t]*$", re.M).search(text, start)
        end = term.start() if term else len(text)
        spans.append((start, end))
        pos = term.end() + 1 if term else len(text)
    return spans


def offending_in_text(text: str, cwd: str) -> tuple:
    """Return (sorted offending paths, all_in_heredoc).

    ``all_in_heredoc`` is True when every occurrence of every offending path
    lies inside a heredoc body, which usually means prose or script text
    rather than a shell argument.
    """
    bodies = heredoc_bodies(text)
    hits: dict = {}  # path -> every occurrence so far inside a heredoc body

    def in_body(at: int) -> bool:
        return any(s <= at < e for s, e in bodies)

    def add(p: str, at: int) -> None:
        hits[p] = hits.get(p, True) and in_body(at)

    def quoted(m) -> bool:
        return (m.start() > 0 and text[m.start() - 1] in QUOTES
                and m.end() < len(text) and text[m.end()] in QUOTES)

    for m in HOME_PATH.finditer(text):
        # every match is a home form, so it asks wherever it resolves:
        # ``~/..`` and ``$HOME/../other`` leave the home directory and still ask
        p = normalize(m.group(0))
        if not allowed(p):
            add(p, m.start())
    for m in CLIMB_PATH.finditer(text):
        p = os.path.normpath(os.path.join(cwd, m.group(0)))
        if not allowed(p):
            add(p, m.start())
    for m in CLIMB_MID.finditer(text):
        p = resolve_climb(m.group(0), cwd)
        if p is not None and not allowed(p):
            add(p, m.start())
    for m in CLIMB_BARE.finditer(text):
        if in_body(m.start()) and not quoted(m):
            continue  # prose in a heredoc; a script that climbs out writes ".."
        p = os.path.normpath(os.path.join(cwd, m.group(0)))
        if not allowed(p):
            add(p, m.start())
    return sorted(hits), bool(hits) and all(hits.values())


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    hits: list = []
    in_heredoc = False
    if tool == "Bash":
        hits, in_heredoc = offending_in_text(inp.get("command", "") or "", cwd)
    elif tool in FILE_TOOLS:
        for key in ("file_path", "path", "notebook_path"):
            v = inp.get(key)
            if not v:
                continue
            raw = str(v)
            p = normalize(raw)
            relative = not os.path.isabs(p) and not p.startswith("~")
            if relative:
                p = os.path.normpath(os.path.join(cwd, p))
            # a relative path or a home form asks wherever it lands outside the
            # allowlist; any other absolute path only when it lands under home
            if (relative or raw.startswith(HOME_FORMS) or p.startswith(HOME)) and not allowed(p):
                hits.append(p)
        # Glob/Grep patterns can carry absolute paths too
        pat = inp.get("pattern")
        if isinstance(pat, str) and (pat.startswith(HOME) or pat.startswith("~")):
            p = normalize(pat.split("*")[0])
            if not allowed(p):
                hits.append(p)
    if not hits:
        return 0
    shown = ", ".join(hits[:4]) + (" ..." if len(hits) > 4 else "")
    reason = f"File-access boundary: {tool} names a path outside the project ({shown}). "
    if in_heredoc:
        reason += (
            "Every match is inside a heredoc body, so this is probably prose or script "
            "text rather than a shell argument; check whether the body only mentions the "
            "path or opens it. "
        )
    reason += "The rule (CLAUDE.md) says ask Roger first; approve only if intended."
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
