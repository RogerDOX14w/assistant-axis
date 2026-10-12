"""Tests for the file-access boundary hook, ``.claude/hooks/boundary_check.py``.

The hook decides from the text of a tool call whether to ask Roger before it
runs.  In Auto mode its asks are the only prompts he sees, so both directions
matter: a path outside the project must ask, and text that only looks like
one (``HEAD~1``, a ``..`` in prose) must not.

Nothing here touches the filesystem outside ``tmp_path`` beyond what the hook
itself resolves: the Bash scan works on strings, and since 2026-10-12 the
file-tool checks also ``realpath`` a path that passes the written-form check,
which stats only places that check allows (the repository, ``~/.claude``,
``/tmp``) or system paths, never a path under home outside the allowlist.  The
symlink and settings tests build their own home, repository and settings in
``tmp_path`` and point the hook at them.

To test a changed hook before it goes live (it runs on every tool call of
every session the moment it is saved), copy it to a scratch directory and run
this file with ``BOUNDARY_HOOK_UNDER_TEST=<the copy>``; the copy is then
tested as if installed in this checkout (``BOUNDARY_HOOK_REPO`` overrides
which checkout, for a copy of this test file run from elsewhere).
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import pwd
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_CHECKOUT = os.environ.get("BOUNDARY_HOOK_REPO") or str(Path(__file__).resolve().parents[2])
_HOOK = Path(os.environ.get("BOUNDARY_HOOK_UNDER_TEST")
             or Path(_CHECKOUT) / ".claude" / "hooks" / "boundary_check.py")
_spec = importlib.util.spec_from_file_location("boundary_check", _HOOK)
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)
if bc.REPO != _CHECKOUT:
    # a scratch copy computes REPO from where it sits: test it as if installed here
    bc.SETTINGS_FILES = tuple(f.replace(bc.REPO, _CHECKOUT, 1) for f in bc.SETTINGS_FILES)
    bc.ALLOWED_PREFIXES = tuple(_CHECKOUT if a == bc.REPO else a for a in bc.ALLOWED_PREFIXES)
    bc.REPO = _CHECKOUT

HOME = bc.HOME
REPO = bc.REPO
# A working directory whose parent is certainly outside the allowlist.  The
# repository's own parent is not used: in a scratch worktree under /tmp it
# would be allowed, and the climb tests would pass for the wrong reason.
OUTSIDE_CWD = os.path.join(HOME, "boundary_test_project", "sub")
OUTSIDE_PARENT = os.path.join(HOME, "boundary_test_project")


def hits(command: str, cwd: str = OUTSIDE_CWD) -> list:
    return bc.offending_in_text(command, cwd)[0]


def heredoc_only(command: str, cwd: str = OUTSIDE_CWD) -> bool:
    return bc.offending_in_text(command, cwd)[1]


class TestTildeIsAPathOnlyAtTheStartOfAWord:
    """A shell expands a tilde only at the start of a word; elsewhere it is
    git revision syntax, a backup suffix or an operator."""

    @pytest.mark.parametrize("command", [
        "git diff HEAD~1 HEAD -U0 -- data_analysis/tests",
        "git show af0f0f8~1:roger/axis_judge_experiments/pair_list_di.json",
        "git log --oneline main~3..main",
        "git rebase --onto HEAD~2 HEAD~1",
        "git show HEAD^~2",
        "ls notes.txt~",
        "if [[ $name =~ ^pair_list ]]; then echo yes; fi",
        "awk '$1 !~ /^#/ {print}' data/README.md",
        "gcc -I~/include main.c",  # mid-word: the shell passes it on unexpanded
    ])
    def test_not_a_path(self, command):
        assert hits(command) == []

    @pytest.mark.parametrize("command, expected", [
        ("ls ~", HOME),
        ("cd ~; ls", HOME),
        ("cd ~&& ls", HOME),
        ("ls ~/.ssh", os.path.join(HOME, ".ssh")),
        ("du -sh ~/.cache/huggingface/hub", os.path.join(HOME, ".cache/huggingface/hub")),
        ('cat "~/.ssh/config"', os.path.join(HOME, ".ssh/config")),
        ("python -c \"import os; print(os.listdir(os.path.expanduser('~/Library')))\"",
         os.path.join(HOME, "Library")),
        ("D=~/Documents; ls $D", os.path.join(HOME, "Documents")),
        ("D=~; ls $D", HOME),
        ("PATH=/usr/bin:~/bin ls", os.path.join(HOME, "bin")),
        ("tool --dir=~/elsewhere", os.path.join(HOME, "elsewhere")),
        ("ls >~/listing.txt", os.path.join(HOME, "listing.txt")),
        ("(cd ~/Documents && ls)", os.path.join(HOME, "Documents")),
        ("echo `ls ~/Desktop`", os.path.join(HOME, "Desktop")),
    ])
    def test_a_path_outside_the_project(self, command, expected):
        assert hits(command) == [expected]

    def test_tilde_paths_on_the_allowlist_do_not_ask(self):
        assert hits("ls ~/.claude/projects") == []
        assert hits("cat ~/.claude/settings.json") == []

    def test_named_user_is_resolved(self):
        me = pwd.getpwuid(os.getuid()).pw_name
        if os.path.expanduser(f"~{me}") != HOME:
            pytest.skip("the login name does not resolve to this home directory")
        assert hits(f"ls ~{me}/.ssh") == [os.path.join(HOME, ".ssh")]
        assert hits(f"ls ~{me}/.claude/plans") == []

    def test_unknown_or_other_user_asks(self):
        assert hits("ls ~no_such_user_zz/secrets") == ["~no_such_user_zz/secrets"]

    def test_a_word_initial_tilde_in_prose_still_asks(self):
        """Documented limit: an approximation sign at the start of a word
        ("about" is the safe spelling) reads as the home directory."""
        assert hits("echo costs ~$0.03 per call") == [HOME]


class TestHomePathsInOtherSpellings:
    @pytest.mark.parametrize("command, expected", [
        ("ls $HOME/.ssh", os.path.join(HOME, ".ssh")),
        ("ls ${HOME}/.cache", os.path.join(HOME, ".cache")),
        ("ls " + os.path.join(HOME, "Documents", "other_project"),
         os.path.join(HOME, "Documents", "other_project")),
    ])
    def test_asks(self, command, expected):
        assert hits(command) == [expected]

    def test_the_repository_and_tmp_do_not_ask(self):
        assert hits(f"cd {REPO} && ls data") == []
        assert hits(f"cat {REPO}/data/README.md") == []
        assert hits("ls /tmp/scratch /private/tmp/claude-501/x") == []

    def test_cursor_tool_folders_do_not_ask(self):
        base = os.path.join(HOME, ".cursor", "projects", "some-project")
        assert hits(f"cat {base}/terminals/1.txt") == []
        assert hits(f"ls {base}/agent-tools") == []
        assert hits(f"ls {base}/other") == [f"{base}/other"]


class TestClimbingOut:
    @pytest.mark.parametrize("command, expected", [
        ("ls ../sibling", os.path.join(OUTSIDE_PARENT, "sibling")),
        ("cat ../../x.txt", os.path.join(HOME, "x.txt")),
        ("cd ..", OUTSIDE_PARENT),
        ("cd .. && ls", OUTSIDE_PARENT),
        ("(cd ..; ls)", OUTSIDE_PARENT),
        ('cd ".."', OUTSIDE_PARENT),
        ("python -c \"import os; print(os.listdir('..'))\"", OUTSIDE_PARENT),
        ("echo from a .. to b", OUTSIDE_PARENT),  # unquoted on the command line: still asks
    ])
    def test_asks(self, command, expected):
        assert hits(command) == [expected]

    @pytest.mark.parametrize("command", [
        "git log --oneline 93a8554..HEAD",
        "git diff main...feature",
        "git rev-list --reverse \"$BASE..$OLD\"",
        "echo wait...",
        "echo 'one ... two'",
        "python -c 'from ..pkg import x'",
        "sed -n 's/../xx/p' file.txt",
    ])
    def test_ranges_ellipses_and_patterns_do_not_ask(self, command):
        assert hits(command, cwd=REPO) == []

    def test_a_climb_that_stays_inside_the_project_does_not_ask(self):
        inside = os.path.join(REPO, "data", "traits")
        assert hits("ls ../roles", cwd=inside) == []
        assert hits("cd ..", cwd=inside) == []

    def test_a_climb_out_of_the_repository_root_asks_when_the_parent_is_outside(self):
        parent = os.path.dirname(REPO)
        expected = [] if bc.allowed(parent) else [parent]
        assert hits("cd ..", cwd=REPO) == expected


class TestClimbsInTheMiddleOfAPath:
    """Closed 2026-09-28: the matcher used to skip any ``..`` that followed a
    slash, so ``data/../../x`` left the project unseen."""

    @pytest.mark.parametrize("command, expected", [
        ("ls data/../../sibling", os.path.join(OUTSIDE_PARENT, "sibling")),
        ("cat data/traits/../../../other_repo/secret", os.path.join(OUTSIDE_PARENT, "other_repo", "secret")),
        ("cd data/../..", OUTSIDE_PARENT),
        ("ls ./../sibling", os.path.join(OUTSIDE_PARENT, "sibling")),
        ("ls ./..", OUTSIDE_PARENT),
        ("tool --out=data/../../x.json", os.path.join(OUTSIDE_PARENT, "x.json")),
        ("python -c \"print(open('data/../../x.txt').read())\"", os.path.join(OUTSIDE_PARENT, "x.txt")),
        ("cat ../sub/../../y", os.path.join(HOME, "y")),
    ])
    def test_asks(self, command, expected):
        assert hits(command) == [expected]

    @pytest.mark.parametrize("command", [
        "ls data/../README.md",
        "cat data/traits/../roles/role_list.json",
        "ls ./data/./traits/..",
        "sed -n 's/../xx/p' file.txt",
        "sed -e 's/a/../' file.txt",
        "git log origin/main..feature/x",
        "git diff a/b...c/d",
        "curl https://example.com/a/../b",
        "ls /usr/lib/../bin",
        "cat /tmp/a/../b /private/tmp/c/../d",
    ])
    def test_quiet_when_it_stays_inside_or_is_not_a_climb(self, command):
        # from the repository root, as in a session: what resolves inside it is allowed
        assert hits(command, cwd=REPO) == []

    @pytest.mark.parametrize("command", [
        "ls $PWD/../sibling",
        "ls ${PWD}/../sibling",
        "ls $(pwd)/../sibling",
        "ls \"$PWD\"/../sibling",
        "ls `pwd`/../sibling",
        "ls $(git rev-parse --show-toplevel)/../sibling",
    ])
    def test_an_unreadable_base_is_taken_to_be_the_working_directory(self, command):
        assert hits(command) == [os.path.join(OUTSIDE_PARENT, "sibling")]

    def test_a_variable_base_that_stays_inside_is_quiet(self):
        assert hits("ls $ROOT/data/../README.md", cwd=REPO) == []

    def test_absolute_paths_ask_only_when_they_land_under_home(self):
        tmp_to_home = "/tmp/x/../.." + os.path.join(HOME, ".ssh")
        assert hits(f"ls {tmp_to_home}") == [os.path.join(HOME, ".ssh")]
        assert hits("ls /usr/local/../lib") == []

    def test_a_climb_out_of_the_repository_by_its_full_path(self):
        parent = os.path.dirname(REPO)
        target = os.path.join(parent, "other_repo")
        expected = [] if bc.allowed(target) else [target]
        assert hits(f"ls {REPO}/../other_repo", cwd=REPO) == expected


class TestHomeFormsAskWhereverTheyResolve:
    @pytest.mark.parametrize("command, expected", [
        ("ls ~/..", os.path.dirname(HOME)),
        ("ls ~/../other_user", os.path.join(os.path.dirname(HOME), "other_user")),
        ("ls $HOME/../other_user", os.path.join(os.path.dirname(HOME), "other_user")),
        ("ls ${HOME}/../other_user/Documents", os.path.join(os.path.dirname(HOME), "other_user", "Documents")),
        ("ls " + HOME + "/../other_user", os.path.join(os.path.dirname(HOME), "other_user")),
        ("ls ~/.claude/../.ssh", os.path.join(HOME, ".ssh")),
    ])
    def test_asks(self, command, expected):
        assert hits(command) == [expected]

    def test_a_home_form_that_resolves_into_the_allowlist_is_quiet(self):
        assert hits("ls ~/.ssh/../.claude/projects") == []
        assert hits("ls $HOME/Documents/../.claude") == []


class TestHeredocBodies:
    PROSE = (
        "M=/tmp/notes && uv run python - <<EOF\n"
        "text = '''eleven themed commits 3f6de81\n"
        "(corpus) .. 62855c7 (docs) on top of 93a8554'''\n"
        "EOF\n"
    )

    def test_unquoted_dots_in_a_body_are_prose(self):
        assert hits(self.PROSE) == []

    def test_a_quoted_climb_in_a_body_asks(self):
        script = "python3 - <<'PY'\nimport os\nos.chdir(\"..\")\nprint(os.listdir('.'))\nPY\n"
        assert hits(script) == [OUTSIDE_PARENT]
        assert heredoc_only(script) is True

    def test_a_path_climb_in_a_body_asks(self):
        script = "python3 - <<'PY'\nprint(open('../other/secret.txt').read())\nPY\n"
        assert hits(script) == [os.path.join(OUTSIDE_PARENT, "other", "secret.txt")]
        assert heredoc_only(script) is True

    def test_a_home_path_in_a_body_asks_and_is_reported_as_body_only(self):
        script = "cat > /tmp/note.md <<'EOF'\nnever list ~/.cache or $HOME/.ssh\nEOF\n"
        assert hits(script) == [os.path.join(HOME, ".cache"), os.path.join(HOME, ".ssh")]
        assert heredoc_only(script) is True

    def test_a_match_on_the_command_line_is_not_body_only(self):
        script = "ls ~/.ssh && cat <<'EOF'\nmentions ~/.ssh again\nEOF\n"
        assert hits(script) == [os.path.join(HOME, ".ssh")]
        assert heredoc_only(script) is False

    def test_revision_tildes_in_a_body_do_not_ask(self):
        script = "cat > /tmp/msg.txt <<'EOF'\nreverts HEAD~1; see abc1234~2\nEOF\n"
        assert hits(script) == []

    def test_dots_after_the_body_are_on_the_command_line_again(self):
        script = "cat <<'EOF'\na .. b\nEOF\ncd ..\n"
        assert hits(script) == [OUTSIDE_PARENT]
        assert heredoc_only(script) is False


class TestTheFourFalsePositivesOf20260928:
    """The commands Roger was asked about during the check-in.  None of them
    named a path outside the project."""

    @pytest.mark.parametrize("command", [
        "git diff HEAD~1 HEAD -U0 -- data_analysis/tests | grep -E \"^\\+(class |    def test_)\" | cut -c1-130",
        "for f in clean di goalnongoal; do git show af0f0f8~1:roger/axis_judge_experiments/pair_list_$f.json "
        "| cmp - roger/axis_judge_experiments/pair_list_${f}_v1.json; done",
        TestHeredocBodies.PROSE,
    ])
    def test_no_longer_asks(self, command):
        assert hits(command, cwd=REPO) == []


@pytest.fixture(autouse=True)
def _sandbox_off_unless_a_test_says_otherwise(monkeypatch):
    """The hook reads the real settings files to see whether the Bash sandbox is
    on; the tests must not depend on Roger's settings, so by default they see no
    settings files at all (sandbox off, Bash scanned)."""
    monkeypatch.setattr(bc, "SETTINGS_FILES", ())


def run_hook(payload, monkeypatch, capsys) -> str:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert bc.main() == 0
    return capsys.readouterr().out


def write_settings(path: Path, sandbox) -> str:
    path.write_text(json.dumps({} if sandbox is None else {"sandbox": sandbox}), encoding="utf-8")
    return str(path)


class TestSandboxStandsTheBashScanDown:
    """2026-10-03: with Claude Code's Bash sandbox on, the OS checks every file a
    shell command opens, so the text scan stands down for Bash; the file tools
    are still checked, and turning the sandbox off brings the scan back."""

    def test_sandbox_enabled_reads_the_last_file_that_says(self, tmp_path):
        user = write_settings(tmp_path / "user.json", {"enabled": True})
        project = write_settings(tmp_path / "project.json", None)
        local_off = write_settings(tmp_path / "local_off.json", {"enabled": False})
        assert bc.sandbox_enabled((user, project)) is True
        assert bc.sandbox_enabled((user, project, local_off)) is False
        assert bc.sandbox_enabled((str(tmp_path / "missing.json"),)) is False
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        assert bc.sandbox_enabled((user, str(bad))) is True

    def test_bash_is_not_scanned_while_the_sandbox_is_on(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(bc, "SETTINGS_FILES", (write_settings(tmp_path / "s.json", {"enabled": True}),))
        for command in ("ls ~/.ssh", "cat > /tmp/n.md <<'EOF'\nsee ~/.cache\nEOF\n", "cd .. && ls"):
            assert run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD,
                             "tool_input": {"command": command}}, monkeypatch, capsys) == ""

    def test_a_call_that_leaves_the_sandbox_is_scanned(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(bc, "SETTINGS_FILES", (write_settings(tmp_path / "s.json", {"enabled": True}),))
        out = run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD, "tool_input": {
            "command": "ls ~/.ssh", "dangerouslyDisableSandbox": True}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "ask"

    def test_file_tools_are_still_checked_while_the_sandbox_is_on(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(bc, "SETTINGS_FILES", (write_settings(tmp_path / "s.json", {"enabled": True}),))
        out = run_hook({"tool_name": "Read", "cwd": REPO,
                        "tool_input": {"file_path": os.path.join(HOME, ".ssh", "config")}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_sandbox_off_scans_bash_as_before(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(bc, "SETTINGS_FILES", (write_settings(tmp_path / "s.json", {"enabled": False}),))
        out = run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD,
                        "tool_input": {"command": "ls ~/.ssh"}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "ask"


class TestMain:
    def test_clean_bash_prints_nothing(self, monkeypatch, capsys):
        out = run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD,
                        "tool_input": {"command": "git diff HEAD~1 HEAD"}}, monkeypatch, capsys)
        assert out == ""

    def test_offending_bash_asks_and_names_the_path(self, monkeypatch, capsys):
        out = run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD,
                        "tool_input": {"command": "ls ~/.ssh"}}, monkeypatch, capsys)
        decision = json.loads(out)["hookSpecificOutput"]
        assert decision["hookEventName"] == "PreToolUse"
        assert decision["permissionDecision"] == "ask"
        assert os.path.join(HOME, ".ssh") in decision["permissionDecisionReason"]
        assert "heredoc" not in decision["permissionDecisionReason"]

    def test_body_only_match_says_so(self, monkeypatch, capsys):
        out = run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD, "tool_input": {
            "command": "cat > /tmp/n.md <<'EOF'\nsee ~/.cache\nEOF\n"}}, monkeypatch, capsys)
        assert "inside a heredoc body" in json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]

    @pytest.mark.parametrize("tool, field", [
        ("Read", "file_path"), ("Edit", "file_path"), ("Write", "file_path"),
        ("NotebookEdit", "notebook_path"), ("Grep", "path"), ("Glob", "path"),
    ])
    def test_file_tools_deny_outside_and_stay_quiet_inside(self, tool, field, monkeypatch, capsys):
        outside = os.path.join(HOME, ".ssh", "config")
        out = run_hook({"tool_name": tool, "cwd": REPO, "tool_input": {field: outside}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
        inside = os.path.join(REPO, "data", "README.md")
        assert run_hook({"tool_name": tool, "cwd": REPO, "tool_input": {field: inside}}, monkeypatch, capsys) == ""

    def test_file_tool_tilde_paths(self, monkeypatch, capsys):
        out = run_hook({"tool_name": "Read", "cwd": REPO,
                        "tool_input": {"file_path": "~/.ssh/config"}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert run_hook({"tool_name": "Read", "cwd": REPO,
                         "tool_input": {"file_path": "~/.claude/settings.json"}}, monkeypatch, capsys) == ""
        out = run_hook({"tool_name": "Read", "cwd": REPO,
                        "tool_input": {"file_path": "~no_such_user_zz/x"}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.parametrize("path", [
        "a/../../x.txt",                                        # relative, climbs out of the cwd
        os.path.join(OUTSIDE_CWD, "a", "..", "..", "x.txt"),    # absolute, lands under home
        os.path.join(HOME, "..", "other_user", "x.txt"),        # a home form that leaves home
        "$HOME/../other_user/x.txt",
        "~/../other_user/x.txt",
    ])
    def test_file_tools_resolve_climbs(self, path, monkeypatch, capsys):
        out = run_hook({"tool_name": "Read", "cwd": OUTSIDE_CWD, "tool_input": {"file_path": path}},
                       monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_file_tools_stay_quiet_for_climbs_inside_and_for_system_paths(self, monkeypatch, capsys):
        inside = os.path.join(REPO, "data", "traits", "..", "README.md")
        for path in (inside, "data/../README.md", "/usr/lib/../bin/python3", "/etc/hosts"):
            assert run_hook({"tool_name": "Read", "cwd": REPO, "tool_input": {"file_path": path}},
                            monkeypatch, capsys) == ""

    def test_glob_pattern_under_home_is_denied(self, monkeypatch, capsys):
        out = run_hook({"tool_name": "Glob", "cwd": REPO,
                        "tool_input": {"pattern": os.path.join(HOME, ".cache") + "/**/*.bin"}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.parametrize("tool_input", [
        {"pattern": "../../.ssh/*"},                                   # relative to the cwd
        {"pattern": "../../../**/*.json", "path": os.path.join(REPO, "data")},
        {"pattern": "**/*", "path": "../.."},                          # the base itself is out
        {"pattern": "~/.cache/**/*.bin"},
    ])
    def test_glob_patterns_that_climb_out_are_denied(self, tool_input, monkeypatch, capsys):
        """2026-10-12: a relative Glob pattern is resolved against its path
        (or the cwd) like a file path; before, only patterns starting with
        the home path or ``~`` were looked at."""
        out = run_hook({"tool_name": "Glob", "cwd": REPO, "tool_input": tool_input}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.parametrize("tool_input", [
        {"pattern": "**/*.py"},
        {"pattern": "data/../tools/*.py"},
        {"pattern": "../*.md", "path": os.path.join(REPO, "data")},     # climbs, stays inside
        {"pattern": "*.so", "path": "/usr/lib"},                       # a system path, as before
        {"pattern": "/tmp/**/*.json"},
        {"pattern": "~/.claude/**/*.md"},
    ])
    def test_glob_patterns_inside_or_on_system_paths_stay_quiet(self, tool_input, monkeypatch, capsys):
        assert run_hook({"tool_name": "Glob", "cwd": REPO, "tool_input": tool_input},
                        monkeypatch, capsys) == ""

    def test_grep_pattern_is_a_regex_not_a_path(self, monkeypatch, capsys):
        """Searching the repository for the text ``~/.cache`` or the home
        path is not a read outside it (denied before 2026-10-12)."""
        for pattern in (r"~/\.cache", HOME + "/.ssh"):
            assert run_hook({"tool_name": "Grep", "cwd": REPO, "tool_input": {"pattern": pattern}},
                            monkeypatch, capsys) == ""
        out = run_hook({"tool_name": "Grep", "cwd": REPO,
                        "tool_input": {"pattern": "x", "path": os.path.join(HOME, ".ssh")}}, monkeypatch, capsys)
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_file_tool_denial_tells_the_agent_what_to_do(self, monkeypatch, capsys):
        out = run_hook({"tool_name": "Read", "cwd": REPO,
                        "tool_input": {"file_path": os.path.join(HOME, ".ssh", "config")}}, monkeypatch, capsys)
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        assert "which path you need and why" in reason and "another route" in reason

    def test_other_tools_and_bad_input_print_nothing(self, monkeypatch, capsys):
        assert run_hook({"tool_name": "WebFetch", "tool_input": {"url": "https://example.com/~user"}},
                        monkeypatch, capsys) == ""
        assert run_hook("not json", monkeypatch, capsys) == ""
        assert run_hook({"tool_name": "Bash", "tool_input": {}}, monkeypatch, capsys) == ""


# ---------------------------------------------------------------------------
# 2026-10-12 (review 7 D5, walk-through E3): symlinks and settings sources
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """A home directory in ``tmp_path`` with a repository, ``.claude`` and a
    ``secret`` directory outside the allowlist; the hook is pointed at it.
    ``/tmp`` is left off the allowlist: ``tmp_path`` itself is under it."""
    home = tmp_path.resolve() / "home"
    repo, claude, secret = home / "repo", home / ".claude", home / "secret"
    for d in (repo / "data", claude, secret / "a" / "b"):
        d.mkdir(parents=True)
    (secret / "key").write_text("k")
    (repo / "data" / "README.md").write_text("r")
    monkeypatch.setattr(bc, "HOME", str(home))
    monkeypatch.setattr(bc, "HOME_FORMS", ("~", "$HOME", "${HOME}", str(home)))
    monkeypatch.setattr(bc, "ALLOWED_PREFIXES", (str(repo), str(claude)))
    return SimpleNamespace(home=home, repo=repo, claude=claude, secret=secret)


def decision(out: str):
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None


class TestSymlinksAreResolved:
    """(a) A file-tool path that passes the written-form check is resolved
    through its symlinks; a link inside the boundary cannot reach out."""

    def read(self, path, monkeypatch, capsys, *, tool="Read", field="file_path", cwd=None, **extra):
        return run_hook({"tool_name": tool, "cwd": str(cwd or bc.ALLOWED_PREFIXES[0]),
                         "tool_input": {field: str(path), **extra}}, monkeypatch, capsys)

    def test_a_directory_link_out_of_the_repository_is_denied(self, fake_home, monkeypatch, capsys):
        (fake_home.repo / "link").symlink_to(fake_home.secret)
        out = self.read(fake_home.repo / "link" / "key", monkeypatch, capsys)
        assert decision(out) == "deny"
        assert str(fake_home.secret / "key") in out              # names where it really leads

    def test_a_file_link_out_of_the_repository_is_denied(self, fake_home, monkeypatch, capsys):
        (fake_home.repo / "key_link").symlink_to(fake_home.secret / "key")
        assert decision(self.read(fake_home.repo / "key_link", monkeypatch, capsys)) == "deny"

    def test_a_relative_path_through_a_link_is_denied(self, fake_home, monkeypatch, capsys):
        (fake_home.repo / "link").symlink_to(fake_home.secret)
        assert decision(self.read("link/key", monkeypatch, capsys, cwd=fake_home.repo)) == "deny"

    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    def test_a_new_file_under_a_linked_directory_is_denied(self, tool, fake_home, monkeypatch, capsys):
        (fake_home.repo / "link").symlink_to(fake_home.secret)
        out = self.read(fake_home.repo / "link" / "new.txt", monkeypatch, capsys, tool=tool)
        assert decision(out) == "deny"

    def test_dot_dot_after_a_link_is_applied_as_the_os_does(self, fake_home, monkeypatch, capsys):
        """``repo/deep/../key`` reads as ``repo/key``, but the OS goes to the
        link's target first, then up: ``secret/a/key``."""
        (fake_home.repo / "deep").symlink_to(fake_home.secret / "a" / "b")
        out = self.read(str(fake_home.repo / "deep") + "/../key", monkeypatch, capsys)
        assert decision(out) == "deny"
        assert str(fake_home.secret / "a" / "key") in out

    def test_a_home_form_through_a_link_is_denied(self, fake_home, monkeypatch, capsys):
        (fake_home.claude / "link").symlink_to(fake_home.secret)
        assert decision(self.read("~/.claude/link/key", monkeypatch, capsys)) == "deny"

    def test_links_that_stay_inside_are_quiet(self, fake_home, monkeypatch, capsys):
        (fake_home.repo / "alias").symlink_to(fake_home.repo / "data")
        (fake_home.repo / "up").symlink_to(fake_home.home)          # out and back in
        assert self.read(fake_home.repo / "alias" / "README.md", monkeypatch, capsys) == ""
        assert self.read(fake_home.repo / "up" / "repo" / "data" / "README.md", monkeypatch, capsys) == ""
        assert self.read(fake_home.repo / "data" / "README.md", monkeypatch, capsys) == ""

    def test_a_link_to_a_system_path_is_quiet_as_the_written_form_is(self, fake_home, monkeypatch, capsys):
        (fake_home.repo / "sys").symlink_to("/usr/lib")
        assert self.read(fake_home.repo / "sys" / "anything", monkeypatch, capsys) == ""

    def test_an_allowlisted_directory_that_is_a_link_stays_allowed(self, tmp_path, monkeypatch, capsys):
        """``~/.claude`` kept in a dotfiles directory: reading through it is
        quiet, while naming the target directly is denied as before (the
        resolution adds denials, it never lifts one)."""
        home = tmp_path.resolve() / "home"
        target = home / "dotfiles" / "claude"
        target.mkdir(parents=True)
        (target / "settings.json").write_text("{}")
        (home / ".claude").symlink_to(target)
        monkeypatch.setattr(bc, "HOME", str(home))
        monkeypatch.setattr(bc, "HOME_FORMS", ("~", "$HOME", "${HOME}", str(home)))
        monkeypatch.setattr(bc, "ALLOWED_PREFIXES", (str(home / "repo"), str(home / ".claude")))
        assert self.read("~/.claude/settings.json", monkeypatch, capsys, cwd=home) == ""
        assert self.read(home / ".claude" / "settings.json", monkeypatch, capsys, cwd=home) == ""
        assert decision(self.read(target / "settings.json", monkeypatch, capsys, cwd=home)) == "deny"

    @pytest.mark.parametrize("make_input", [
        lambda r: {"pattern": "**/*", "path": str(r / "link")},
        lambda r: {"pattern": "link/*.txt"},
        lambda r: {"pattern": "~/repo/link/*"},
        lambda r: {"pattern": str(r / "link") + "/**/*"},
    ])
    def test_glob_through_a_link_is_denied(self, make_input, fake_home, monkeypatch, capsys):
        (fake_home.repo / "link").symlink_to(fake_home.secret)
        out = run_hook({"tool_name": "Glob", "cwd": str(fake_home.repo),
                        "tool_input": make_input(fake_home.repo)}, monkeypatch, capsys)
        assert decision(out) == "deny"

    def test_grep_path_through_a_link_is_denied(self, fake_home, monkeypatch, capsys):
        (fake_home.repo / "link").symlink_to(fake_home.secret)
        out = self.read(fake_home.repo / "link", monkeypatch, capsys, tool="Grep", field="path", pattern="x")
        assert decision(out) == "deny"

    def test_a_resolution_failure_falls_back_to_the_written_form(self, fake_home, monkeypatch, capsys):
        (fake_home.repo / "link").symlink_to(fake_home.secret)

        def boom(_p):
            raise OSError("simulated")
        monkeypatch.setattr(bc.os.path, "realpath", boom)
        assert self.read(fake_home.repo / "link" / "key", monkeypatch, capsys) == ""   # as before
        assert decision(self.read(fake_home.secret / "key", monkeypatch, capsys)) == "deny"

    def test_the_written_form_is_still_reported_first(self, fake_home, monkeypatch, capsys):
        out = self.read("~/secret/key", monkeypatch, capsys)
        assert decision(out) == "deny" and str(fake_home.secret / "key") in out


class TestHigherPrecedenceSettings:
    """(b) The ``--settings`` value on the ``claude`` command line and the
    managed settings outrank the project's files; a sandbox they switch off
    brings the Bash scan back."""

    def cli(self, monkeypatch, *values):
        monkeypatch.setattr(bc, "cli_settings_values", lambda *a, **k: list(values))

    def test_default_sources_in_precedence_order(self):
        # the module's own tuple (the autouse fixture empties bc.SETTINGS_FILES)
        spec = importlib.util.spec_from_file_location("bc_fresh", _HOOK)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        files = fresh.SETTINGS_FILES
        assert files[:3] == (os.path.join(fresh.HOME, ".claude", "settings.json"),
                             os.path.join(fresh.REPO, ".claude", "settings.json"),
                             os.path.join(fresh.REPO, ".claude", "settings.local.json"))
        assert files[3:] == (fresh.CLI_SETTINGS, fresh.MANAGED_SETTINGS_FILE, fresh.MANAGED_SETTINGS_DIR)
        if sys.platform == "darwin":
            assert fresh.MANAGED_SETTINGS_FILE == "/Library/Application Support/ClaudeCode/managed-settings.json"
            assert fresh.MANAGED_SETTINGS_DIR == "/Library/Application Support/ClaudeCode/managed-settings.d"
        elif sys.platform.startswith("linux"):
            assert fresh.MANAGED_SETTINGS_FILE == "/etc/claude-code/managed-settings.json"

    def test_cli_settings_file_overrides_the_project(self, tmp_path, monkeypatch):
        local_on = write_settings(tmp_path / "local.json", {"enabled": True})
        self.cli(monkeypatch, write_settings(tmp_path / "cli.json", {"enabled": False}))
        assert bc.sandbox_enabled((local_on, bc.CLI_SETTINGS)) is False
        self.cli(monkeypatch, write_settings(tmp_path / "cli_on.json", {"enabled": True}))
        assert bc.sandbox_enabled((local_on, bc.CLI_SETTINGS)) is True

    def test_outranking_sources_never_stand_the_scan_down_by_themselves(self, tmp_path, monkeypatch):
        """Loosens nothing: where the settings files do not switch the sandbox
        on, a --settings or managed "on" leaves the Bash scan running (it is
        then redundant behind Claude Code's sandbox, never missing)."""
        local_off = write_settings(tmp_path / "local_off.json", {"enabled": False})
        self.cli(monkeypatch, '{"sandbox": {"enabled": true}}')
        assert bc.sandbox_enabled((local_off, bc.CLI_SETTINGS)) is False
        assert bc.sandbox_enabled((bc.CLI_SETTINGS,)) is False
        managed_on = write_settings(tmp_path / "managed_on.json", {"enabled": True})
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_FILE", managed_on)
        assert bc.sandbox_enabled((local_off, bc.MANAGED_SETTINGS_FILE)) is False
        d = tmp_path / "managed-settings.d"
        d.mkdir()
        write_settings(d / "10-on.json", {"enabled": True})
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_DIR", str(d))
        assert bc.sandbox_enabled((local_off, bc.MANAGED_SETTINGS_DIR)) is False

    @pytest.mark.parametrize("value, expected", [
        ('{"sandbox": {"enabled": false}}', False),
        ('  {"sandbox": {"enabled": true}}', True),
        ('{"permissions": {}}', True),                 # says nothing: the project's value stands
    ])
    def test_cli_settings_json_string(self, value, expected, tmp_path, monkeypatch):
        local_on = write_settings(tmp_path / "local.json", {"enabled": True})
        self.cli(monkeypatch, value)
        assert bc.sandbox_enabled((local_on, bc.CLI_SETTINGS)) is expected

    @pytest.mark.parametrize("value", ["{not json", "/nonexistent/claude_settings_zz.json", "[1, 2]"])
    def test_an_unreadable_cli_value_counts_as_sandbox_off(self, value, tmp_path, monkeypatch):
        local_on = write_settings(tmp_path / "local.json", {"enabled": True})
        self.cli(monkeypatch, value)
        assert bc.sandbox_enabled((local_on, bc.CLI_SETTINGS)) is False

    def test_no_cli_value_leaves_the_project_value(self, tmp_path, monkeypatch):
        local_on = write_settings(tmp_path / "local.json", {"enabled": True})
        self.cli(monkeypatch)
        assert bc.sandbox_enabled((local_on, bc.CLI_SETTINGS)) is True

    def test_managed_settings_outrank_everything(self, tmp_path, monkeypatch):
        local_on = write_settings(tmp_path / "local.json", {"enabled": True})
        self.cli(monkeypatch, '{"sandbox": {"enabled": true}}')
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_FILE",
                            write_settings(tmp_path / "managed.json", {"enabled": False}))
        sources = (local_on, bc.CLI_SETTINGS, bc.MANAGED_SETTINGS_FILE)
        assert bc.sandbox_enabled(sources) is False
        # managed "on" over a --settings "off": Claude Code's sandbox is on, and the
        # settings files say on too, so the scan stands down
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_FILE",
                            write_settings(tmp_path / "managed_on.json", {"enabled": True}))
        self.cli(monkeypatch, '{"sandbox": {"enabled": false}}')
        sources = (local_on, bc.CLI_SETTINGS, bc.MANAGED_SETTINGS_FILE)
        assert bc.sandbox_enabled(sources) is True
        # an absent managed file is the usual case and changes nothing
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_FILE", str(tmp_path / "no_managed.json"))
        self.cli(monkeypatch)
        assert bc.sandbox_enabled((local_on, bc.CLI_SETTINGS, bc.MANAGED_SETTINGS_FILE)) is True

    def test_managed_drop_ins_apply_in_name_order(self, tmp_path, monkeypatch):
        local_on = write_settings(tmp_path / "local.json", {"enabled": True})
        d = tmp_path / "managed-settings.d"
        d.mkdir()
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_DIR", str(d))
        write_settings(d / "10-on.json", {"enabled": True})
        write_settings(d / "20-off.json", {"enabled": False})
        (d / "30-notes.txt").write_text('{"sandbox": {"enabled": true}}')   # not *.json: ignored
        (d / "15-bad.json").write_text("{not json")                         # unreadable: skipped
        assert bc.sandbox_enabled((local_on, bc.MANAGED_SETTINGS_DIR)) is False
        write_settings(d / "40-on.json", {"enabled": True})
        assert bc.sandbox_enabled((local_on, bc.MANAGED_SETTINGS_DIR)) is True
        # no drop-in directory at all: nothing changes
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_DIR", str(tmp_path / "absent.d"))
        assert bc.sandbox_enabled((local_on, bc.MANAGED_SETTINGS_DIR)) is True

    def test_bash_is_scanned_when_managed_settings_switch_the_sandbox_off(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(bc, "MANAGED_SETTINGS_FILE",
                            write_settings(tmp_path / "managed.json", {"enabled": False}))
        monkeypatch.setattr(bc, "SETTINGS_FILES", (
            write_settings(tmp_path / "local.json", {"enabled": True}), bc.MANAGED_SETTINGS_FILE))
        out = run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD,
                        "tool_input": {"command": "ls ~/.ssh"}}, monkeypatch, capsys)
        assert decision(out) == "ask"

    def test_bash_is_scanned_when_the_cli_switches_the_sandbox_off(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(bc, "SETTINGS_FILES", (
            write_settings(tmp_path / "local.json", {"enabled": True}), bc.CLI_SETTINGS))
        self.cli(monkeypatch, '{"sandbox": {"enabled": false}}')
        out = run_hook({"tool_name": "Bash", "cwd": OUTSIDE_CWD,
                        "tool_input": {"command": "ls ~/.ssh"}}, monkeypatch, capsys)
        assert decision(out) == "ask"


class TestCliSettingsLookup:
    """Where ``--settings`` is read from: the nearest ancestor ``claude``."""

    def table(self, monkeypatch, procs):
        def fake(pid):
            return procs.get(pid)
        monkeypatch.setattr(bc, "_process_argv_and_ppid", fake)

    def test_reads_the_nearest_claude(self, monkeypatch):
        self.table(monkeypatch, {
            100: (["/bin/sh", "-c", "python3 boundary_check.py"], 90),
            90: (["/opt/x/claude", "--settings", "/p/s.json", "--model", "opus"], 80),
            80: (["Cursor", "--settings", "/other.json"], 1),
        })
        assert bc.cli_settings_values(start_pid=100) == ["/p/s.json"]

    def test_equals_form_and_node_launch(self, monkeypatch):
        self.table(monkeypatch, {
            100: (["node", "/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js",
                   '--settings={"sandbox": {"enabled": false}}'], 1),
        })
        assert bc.cli_settings_values(start_pid=100) == ['{"sandbox": {"enabled": false}}']

    def test_a_claude_without_the_flag_stops_the_walk(self, monkeypatch):
        self.table(monkeypatch, {
            100: (["claude", "--resume"], 90),
            90: (["Cursor", "--settings", "/other.json"], 1),
        })
        assert bc.cli_settings_values(start_pid=100) == []

    def test_no_claude_or_no_process_table_gives_nothing(self, monkeypatch):
        self.table(monkeypatch, {100: (["zsh"], 90), 90: (["launchd"], 1)})
        assert bc.cli_settings_values(start_pid=100) == []
        self.table(monkeypatch, {})
        assert bc.cli_settings_values(start_pid=100) == []

        def boom(pid):
            raise OSError("not permitted")
        monkeypatch.setattr(bc, "_process_argv_and_ppid", boom)
        assert bc.cli_settings_values(start_pid=100) == []

    def test_the_hook_script_itself_is_not_taken_for_claude(self):
        assert not bc._is_claude(["python3", "/repo/.claude/hooks/boundary_check.py"])
        assert not bc._is_claude(["/bin/zsh", "-c", "source ~/.claude/shell-snapshots/x"])
        assert bc._is_claude(["/Users/x/.vscode/extensions/anthropic.claude-code-2/bin/claude"])

    @pytest.mark.skipif(not (sys.platform == "darwin" or sys.platform.startswith("linux")),
                        reason="process table read on macOS and Linux only")
    def test_reads_this_process(self):
        got = bc._process_argv_and_ppid(os.getpid())
        assert got is not None
        argv, ppid = got
        assert ppid == os.getppid()
        assert any("python" in os.path.basename(a) or "pytest" in a for a in argv)
