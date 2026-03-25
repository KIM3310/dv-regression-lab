from dv_regression_lab.models import RegressionCaseResult, RegressionRun
from dv_regression_lab.taxonomy import build_triage, classify_failure


def _case(case_id: str, status: str, category: str, units=None) -> RegressionCaseResult:
    return RegressionCaseResult(
        case_id=case_id,
        title=case_id,
        module=f"{case_id}_tb",
        owner="dv",
        status=status,
        profile=category,
        category=category,
        summary="summary",
        signature="signature",
        seed=1,
        runtime_sec=1.0,
        tags=[],
        design_units=units or [],
        rerun_recommended=False,
        artifact_paths=[],
        log_excerpt="log",
    )


def test_classify_failure_detects_compile_error():
    text = "compile failed: unresolved reference to dma_rsp_if"
    assert classify_failure(text, "failed") == "compile_error"


def test_classify_failure_detects_assertion():
    text = "ASSERTION FAILED: scoreboard mismatch on axi_awid"
    assert classify_failure(text, "failed") == "assertion_failure"


def test_build_triage_marks_flaky_case_when_history_mixed():
    run = RegressionRun(
        run_id="r1",
        suite_id="suite",
        title="suite",
        owner="dv",
        simulator_kind="mock",
        requested_at="2026-03-20T00:00:00Z",
        completed_at="2026-03-20T00:00:10Z",
        case_total=2,
        passed=1,
        failed=1,
        pass_rate=0.5,
        duration_sec=2.0,
        quality_gate="hold",
        results=[
            _case("cache_case", "failed", "assertion_failure", ["l2_cache.sv"]),
            _case("reset_case", "passed", "passed", ["reset_ctrl.sv"]),
        ],
    )
    triage = build_triage(run, {"cache_case": ["passed"]})
    assert "cache_case" in triage.flaky_cases
    assert triage.hot_design_units[0]["design_unit"] == "l2_cache.sv"
