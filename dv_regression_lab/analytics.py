from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .models import RegressionRun


def build_review_pack(run: RegressionRun) -> Dict[str, object]:
    failing_cases = [result for result in run.results if result.status == "failed"]
    severity_rank = {
        "compile_error": 0,
        "environment_issue": 1,
        "timeout": 2,
        "protocol_mismatch": 3,
        "x_propagation": 4,
        "assertion_failure": 5,
        "unknown": 6,
    }
    riskiest_cases = sorted(
        failing_cases,
        key=lambda result: (
            severity_rank.get(result.category, 99),
            -result.runtime_sec,
            result.case_id,
        ),
    )[:5]

    recurring_signatures = Counter(result.signature for result in failing_cases)
    category_counts = Counter(result.category for result in failing_cases)
    promotion_posture = _promotion_posture(run)

    next_actions = []
    if category_counts.get("compile_error"):
        next_actions.append("Fix compile blockers before re-spinning regressions.")
    if category_counts.get("environment_issue"):
        next_actions.append("Recover farm or license health before assigning debug owners.")
    if run.triage and run.triage.flaky_cases:
        next_actions.append("Quarantine or reseed flaky tests before claiming closure.")
    if category_counts.get("protocol_mismatch"):
        next_actions.append("Review interface monitors and scoreboard ordering assumptions.")
    if category_counts.get("timeout"):
        next_actions.append(
            "Prioritize deadlock and no-forward-progress analysis on long-running tests."
        )
    if not next_actions:
        next_actions.append(
            "Promote to the next gate and preserve this run as the baseline reference."
        )

    return {
        "run_id": run.run_id,
        "suite_id": run.suite_id,
        "title": run.title,
        "promotion_posture": promotion_posture,
        "quality_gate": run.quality_gate,
        "pass_rate": run.pass_rate,
        "failures": len(failing_cases),
        "flaky_cases": run.triage.flaky_cases if run.triage else [],
        "recurring_signatures": [
            {"signature": signature, "count": count}
            for signature, count in recurring_signatures.most_common(5)
        ],
        "riskiest_cases": [
            {
                "case_id": result.case_id,
                "category": result.category,
                "signature": result.signature,
                "owner": result.owner,
                "runtime_sec": result.runtime_sec,
                "design_units": result.design_units,
            }
            for result in riskiest_cases
        ],
        "next_actions": next_actions,
        "operator_brief": run.triage.operator_brief if run.triage else [],
    }


def build_suite_trend(runs: List[RegressionRun]) -> Dict[str, object]:
    ordered = sorted(runs, key=lambda item: item.requested_at)
    points = [
        {
            "run_id": run.run_id,
            "requested_at": run.requested_at,
            "pass_rate": run.pass_rate,
            "quality_gate": run.quality_gate,
            "failed": run.failed,
            "duration_sec": run.duration_sec,
        }
        for run in ordered
    ]
    if not ordered:
        return {
            "suite_id": None,
            "run_count": 0,
            "quality_gate_histogram": {},
            "pass_rate_delta": None,
            "recurring_failures": [],
            "flaky_cases": [],
            "points": [],
        }

    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) > 1 else None
    recurring_failures = Counter()
    flaky_cases = set()
    gate_histogram = Counter(run.quality_gate for run in ordered)

    for run in ordered:
        for result in run.results:
            if result.status == "failed":
                recurring_failures[result.case_id] += 1
        if run.triage:
            flaky_cases.update(run.triage.flaky_cases)

    return {
        "suite_id": latest.suite_id,
        "run_count": len(ordered),
        "quality_gate_histogram": dict(gate_histogram),
        "pass_rate_delta": None
        if previous is None
        else round(latest.pass_rate - previous.pass_rate, 3),
        "recurring_failures": [
            {"case_id": case_id, "failed_runs": count}
            for case_id, count in recurring_failures.most_common(8)
        ],
        "flaky_cases": sorted(flaky_cases),
        "points": points,
    }


def _promotion_posture(run: RegressionRun) -> str:
    if run.quality_gate == "pass":
        return "ready_for_promotion"
    if run.quality_gate == "hold":
        return "triage_before_promotion"
    return "blocked"
