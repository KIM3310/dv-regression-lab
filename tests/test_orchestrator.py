from pathlib import Path

from dv_regression_lab.orchestrator import run_suite
from dv_regression_lab.store import RunStore


def test_run_suite_persists_results_and_artifacts(tmp_path):
    store = RunStore(tmp_path / "store")
    project_root = Path(__file__).resolve().parents[1]
    suite_path = project_root / "examples" / "soc_smoke.yaml"

    run = run_suite(suite_path, store)

    assert run.case_total == 6
    assert run.failed >= 1
    assert run.triage is not None
    assert store.load_run(run.run_id) is not None

    for result in run.results:
        for artifact in result.artifact_paths:
            assert Path(artifact).exists()


def test_flaky_case_is_detected_after_second_run(tmp_path):
    store = RunStore(tmp_path / "store")
    project_root = Path(__file__).resolve().parents[1]
    suite_path = project_root / "examples" / "soc_smoke.yaml"

    first = run_suite(suite_path, store)
    second = run_suite(suite_path, store)

    assert first.triage is not None
    assert second.triage is not None
    assert "cache_coherency_flake" in second.triage.flaky_cases
