from dv_regression_lab.analytics import build_review_pack, build_suite_trend
from dv_regression_lab.models import RegressionCaseResult, RegressionRun, TriageSummary


def _case(case_id: str, status: str, category: str, signature: str) -> RegressionCaseResult:
    return RegressionCaseResult(
        case_id=case_id,
        title=case_id,
        module=f"{case_id}_tb",
        owner="dv",
        status=status,
        profile=category,
        category=category,
        summary="summary",
        signature=signature,
        seed=1,
        runtime_sec=3.0,
        tags=[],
        design_units=["dma_engine.sv"],
        rerun_recommended=False,
        artifact_paths=[],
        log_excerpt="log",
    )


def _run(run_id: str, pass_rate: float, failed_case: RegressionCaseResult) -> RegressionRun:
    failed = 0 if failed_case.status == "passed" else 1
    passed = 1 if failed == 0 else 0
    run = RegressionRun(
        run_id=run_id,
        suite_id="soc_smoke_matrix",
        title="suite",
        owner="dv-platform",
        simulator_kind="mock",
        requested_at=f"2026-03-20T00:00:0{run_id[-1]}Z",
        completed_at=f"2026-03-20T00:00:1{run_id[-1]}Z",
        case_total=1,
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        duration_sec=3.0,
        quality_gate="fail" if failed else "pass",
        results=[failed_case],
        triage=TriageSummary(
            run_id=run_id,
            failure_buckets={failed_case.category: failed} if failed else {},
            rerun_candidates=[],
            flaky_cases=["flaky_case"] if run_id == "r2" else [],
            hot_design_units=[{"design_unit": "dma_engine.sv", "failing_cases": failed}],
            operator_brief=["brief"],
        ),
    )
    return run


def test_build_review_pack_returns_promotion_posture_and_actions():
    run = _run(
        "r1",
        0.0,
        _case("compile_guard", "failed", "compile_error", "compile failed: unresolved reference"),
    )
    review_pack = build_review_pack(run)
    assert review_pack["promotion_posture"] == "blocked"
    assert review_pack["riskiest_cases"][0]["case_id"] == "compile_guard"
    assert review_pack["next_actions"]


def test_build_suite_trend_tracks_delta_and_flaky_cases():
    first = _run("r1", 0.0, _case("irq_deadlock", "failed", "timeout", "TIMEOUT"))
    second = _run("r2", 1.0, _case("irq_deadlock", "passed", "passed", "PASS"))
    trend = build_suite_trend([first, second])
    assert trend["run_count"] == 2
    assert trend["pass_rate_delta"] == 1.0
    assert "flaky_case" in trend["flaky_cases"]
    assert trend["recurring_failures"][0]["case_id"] == "irq_deadlock"
