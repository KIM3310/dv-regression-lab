from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterable, List

from .models import RegressionRun, TriageSummary

FAILURE_TAXONOMY: Dict[str, Dict[str, object]] = {
    "assertion_failure": {
        "signals": ["ASSERTION FAILED", "scoreboard mismatch", "unexpected response"],
        "rerun_bias": "medium",
        "owner": "dv",
        "action": "Inspect waveform and scoreboard state before quarantine.",
    },
    "compile_error": {
        "signals": ["syntax error", "unresolved reference", "compile failed"],
        "rerun_bias": "low",
        "owner": "rtl",
        "action": "Fix build breakages before rerunning the regression.",
    },
    "timeout": {
        "signals": ["TIMEOUT", "no forward progress", "watchdog expired"],
        "rerun_bias": "high",
        "owner": "dv-platform",
        "action": "Check deadlock, long-tail latency, and runtime budget.",
    },
    "x_propagation": {
        "signals": ["XPROP", "unknown value", "x detected"],
        "rerun_bias": "medium",
        "owner": "rtl",
        "action": "Trace reset sequencing and uninitialized sources.",
    },
    "protocol_mismatch": {
        "signals": ["handshake mismatch", "protocol violation", "out-of-order response"],
        "rerun_bias": "high",
        "owner": "dv",
        "action": "Review interface monitors and transaction ordering.",
    },
    "environment_issue": {
        "signals": ["tool not found", "license checkout", "mount unavailable"],
        "rerun_bias": "high",
        "owner": "platform",
        "action": "Repair environment availability before burning debug cycles.",
    },
    "passed": {
        "signals": [],
        "rerun_bias": "none",
        "owner": "n/a",
        "action": "No action required.",
    },
    "unknown": {
        "signals": [],
        "rerun_bias": "medium",
        "owner": "dv-platform",
        "action": "Collect more evidence and refine taxonomy signatures.",
    },
}

PATTERN_TO_CATEGORY = [
    (re.compile(r"ASSERTION FAILED|scoreboard mismatch", re.IGNORECASE), "assertion_failure"),
    (
        re.compile(r"syntax error|unresolved reference|compile failed", re.IGNORECASE),
        "compile_error",
    ),
    (re.compile(r"TIMEOUT|watchdog expired|no forward progress", re.IGNORECASE), "timeout"),
    (re.compile(r"XPROP|x detected|unknown value", re.IGNORECASE), "x_propagation"),
    (
        re.compile(r"handshake mismatch|protocol violation|out-of-order response", re.IGNORECASE),
        "protocol_mismatch",
    ),
    (
        re.compile(r"tool not found|license checkout|mount unavailable", re.IGNORECASE),
        "environment_issue",
    ),
]


def classify_failure(text: str, status: str) -> str:
    if status == "passed":
        return "passed"
    for pattern, category in PATTERN_TO_CATEGORY:
        if pattern.search(text):
            return category
    return "unknown"


def rerun_recommendation(category: str, history: Iterable[str]) -> bool:
    seen = list(history)
    if category in {"compile_error"}:
        return False
    if category in {"timeout", "protocol_mismatch", "environment_issue"}:
        return True
    return "passed" in seen and "failed" in seen


def build_triage(run: RegressionRun, history_lookup: Dict[str, List[str]]) -> TriageSummary:
    failed_results = [result for result in run.results if result.status == "failed"]
    buckets = Counter(result.category for result in failed_results)

    flaky_cases: List[str] = []
    rerun_candidates = []
    hot_units = Counter()

    for result in run.results:
        history = history_lookup.get(result.case_id, [])
        combined = history + [result.status]
        if "passed" in combined and "failed" in combined:
            flaky_cases.append(result.case_id)
    for result in failed_results:
        history = history_lookup.get(result.case_id, [])
        combined = history + [result.status]
        if rerun_recommendation(result.category, combined):
            rerun_candidates.append(
                {
                    "case_id": result.case_id,
                    "category": result.category,
                    "priority": "high"
                    if result.category in {"timeout", "protocol_mismatch"}
                    else "medium",
                    "reason": FAILURE_TAXONOMY.get(result.category, FAILURE_TAXONOMY["unknown"])[
                        "action"
                    ],
                }
            )
        for unit in result.design_units:
            hot_units[unit] += 1

    hot_design_units = [
        {"design_unit": unit, "failing_cases": count} for unit, count in hot_units.most_common(5)
    ]

    operator_brief = [
        f"{run.failed}/{run.case_total} cases failed. quality gate={run.quality_gate}.",
    ]
    if buckets.get("compile_error"):
        operator_brief.append("Compile failures block promotion and should be fixed before reruns.")
    if flaky_cases:
        operator_brief.append(
            "Flaky cases detected across run history. Stabilize seeds before claiming closure."
        )
    if not flaky_cases and not failed_results:
        operator_brief.append("No failing cases detected. This run is ready for promotion review.")

    return TriageSummary(
        run_id=run.run_id,
        failure_buckets=dict(sorted(buckets.items())),
        rerun_candidates=rerun_candidates,
        flaky_cases=sorted(flaky_cases),
        hot_design_units=hot_design_units,
        operator_brief=operator_brief,
    )
