"""Tests for the file-access boundary hook, ``.claude/hooks/boundary_check.py``.

The hook decides from the text of a tool call whether to ask Roger before it
runs.  In Auto mode its asks are the only prompts he sees, so both directions
matter: a path outside the project must ask, and text that only looks like
one (``HEAD~1``, a ``..`` in prose) must not.

Nothing here touches the filesystem outside ``tmp_path``: the hook works on
strings, and every path below is resolved with ``os.path`` arithmetic only.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import pwd
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "boundary_check.py"
_spec = importlib.util.spec_from_file_location("boundary_check", _HOOK)
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)

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
