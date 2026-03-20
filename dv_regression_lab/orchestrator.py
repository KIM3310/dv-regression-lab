from __future__ import annotations

import datetime as dt
import secrets
from pathlib import Path
from typing import Dict, List

import yaml

from .models import RegressionRun, SuiteSpec
from .simulator import build_adapter
from .store import RunStore
from .taxonomy import build_triage


def load_suite(suite_path: Path) -> SuiteSpec:
    payload = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    return SuiteSpec.from_dict(payload)


def run_suite(suite_path: Path, store: RunStore) -> RegressionRun:
    suite = load_suite(suite_path)
    adapter = build_adapter(suite.simulator)
    requested_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    run_id = _build_run_id()
    artifacts_root = store.artifacts_dir / run_id
    artifacts_root.mkdir(parents=True, exist_ok=True)

    results = []
    history_lookup: Dict[str, List[str]] = {}
    for case in suite.tests:
        history = store.case_history(suite.suite_id, case.id)
        history_lookup[case.id] = history
        results.append(
            adapter.run_case(
                case=case, previous_attempts=len(history), artifacts_root=artifacts_root
            )
        )

    passed = sum(1 for result in results if result.status == "passed")
    failed = sum(1 for result in results if result.status == "failed")
    duration_sec = round(sum(result.runtime_sec for result in results), 2)
    pass_rate = round((passed / len(results)) if results else 0.0, 3)
    quality_gate = _quality_gate(results=results, pass_rate=pass_rate)
    completed_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    run = RegressionRun(
        run_id=run_id,
        suite_id=suite.suite_id,
        title=suite.title,
        owner=suite.owner,
        simulator_kind=suite.simulator.kind,
        requested_at=requested_at,
        completed_at=completed_at,
        case_total=len(results),
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        duration_sec=duration_sec,
        quality_gate=quality_gate,
        results=results,
    )
    run.triage = build_triage(run, history_lookup)
    store.save_run(run)
    return run


def list_example_suites(project_root: Path) -> List[dict]:
    examples_dir = project_root / "examples"
    items = []
    for path in sorted(examples_dir.glob("*.yaml")):
        suite = load_suite(path)
        items.append(
            {
                "path": str(path),
                "suite_id": suite.suite_id,
                "title": suite.title,
                "owner": suite.owner,
                "simulator_kind": suite.simulator.kind,
                "case_total": len(suite.tests),
            }
        )
    return items


def resolve_suite_path(project_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (project_root / candidate).resolve()


def _build_run_id() -> str:
    stamp = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"dvrl-{stamp}-{secrets.token_hex(3)}"


def _quality_gate(results, pass_rate: float) -> str:
    categories = {result.category for result in results if result.status == "failed"}
    if "compile_error" in categories or pass_rate < 0.7:
        return "fail"
    if categories or pass_rate < 0.95:
        return "hold"
    return "pass"
