"""The platform's interface as built (coding_plan_platform.md, "Interface as built (2026-10-08)"), frozen by the
close-out: every name ``assistant_axis.gapgen`` exports exists, the docstring lists each, the recovery entry
points load on first use, and nothing of the superseded scorer interface is exported."""
import importlib
import subprocess
import sys

import assistant_axis.gapgen as G

#: The scorer side of the earlier "Frozen interface", never built (M3 was redesigned on 2026-10-02).
SUPERSEDED = ("NoveltyQuery", "NoveltyResult", "Neighbour", "NoveltyIndex", "score_novelty", "recovery_test",
              "RecoveryReport", "embed_local")
#: What a generator plan relies on (the registry API) and what the close-out adds.
REQUIRED = ("Candidate", "start_run", "submit_candidates", "SubmitReport", "RunContext", "read_candidates",
            "CANDIDATE_FIELDS", "Registry", "MetricConfig", "REGISTRY_PATH", "DATA_CANDIDATES", "run_dir",
            "recovery_dir", "novelty_dir", "draw_hidden", "load_hidden", "match_candidates", "seed_figures",
            "combine_seeds", "report_markdown")


def test_every_export_exists_and_is_listed_in_the_docstring():
    assert len(set(G.__all__)) == len(G.__all__)
    for name in G.__all__:
        assert getattr(G, name) is not None, name
        assert f"``{name}``" in G.__doc__, f"{name} is not described in the package docstring"
    assert set(REQUIRED) <= set(G.__all__)


def test_nothing_of_the_superseded_scorer_interface_is_exported():
    for name in SUPERSEDED:
        assert name not in G.__all__
        assert not hasattr(G, name), name
    for mod in ("novelty", "novelty_runner", "recovery", "registry", "embed"):
        m = importlib.import_module(f"assistant_axis.gapgen.{mod}")
        assert not any(hasattr(m, n) for n in SUPERSEDED if n != "recovery_test"), mod


def test_the_recovery_entry_points_are_the_modules_and_load_on_first_use():
    from assistant_axis.gapgen import recovery
    for name in G.RECOVERY_EXPORTS:
        assert getattr(G, name) is getattr(recovery, name)
    from assistant_axis.gapgen import draw_hidden, DEFAULT_SEEDS  # noqa: F401
    assert DEFAULT_SEEDS == (0, 1)
    # a generator that imports the registry API does not import M3's modules
    code = ("import sys, assistant_axis.gapgen as g; g.Candidate; "
            "print('assistant_axis.gapgen.recovery' in sys.modules, 'assistant_axis.gapgen.novelty' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.split()
    assert out == ["False", "False"]


def test_the_registry_api_is_the_registry_modules():
    from assistant_axis.gapgen import paths, registry, runs
    assert G.Candidate is registry.Candidate and G.submit_candidates is registry.submit_candidates
    assert G.start_run is runs.start_run and G.REGISTRY_PATH == paths.REGISTRY_PATH
    assert G.CANDIDATE_FIELDS == tuple(registry.Candidate.__dataclass_fields__)
