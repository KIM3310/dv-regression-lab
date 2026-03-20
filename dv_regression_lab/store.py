from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .models import RegressionRun


class RunStore:
    def __init__(self, root: Path):
        self.root = root
        self.runs_dir = self.root / "runs"
        self.artifacts_dir = self.root / "artifacts"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, run: RegressionRun) -> Path:
        run_path = self.runs_dir / f"{run.run_id}.json"
        run_path.write_text(json.dumps(run.to_dict(), indent=2), encoding="utf-8")
        return run_path

    def load_run(self, run_id: str) -> Optional[RegressionRun]:
        run_path = self.runs_dir / f"{run_id}.json"
        if not run_path.exists():
            return None
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        return RegressionRun.from_dict(payload)

    def list_runs(self, limit: int = 50) -> List[RegressionRun]:
        items = []
        for run_path in sorted(self.runs_dir.glob("*.json"), reverse=True):
            payload = json.loads(run_path.read_text(encoding="utf-8"))
            items.append(RegressionRun.from_dict(payload))
        items.sort(key=lambda item: item.requested_at, reverse=True)
        return items[:limit]

    def list_runs_for_suite(self, suite_id: str, limit: int = 20) -> List[RegressionRun]:
        matches = [run for run in self.list_runs(limit=200) if run.suite_id == suite_id]
        return matches[:limit]

    def case_history(self, suite_id: str, case_id: str, limit: int = 10) -> List[str]:
        history: List[str] = []
        for run in self.list_runs(limit=100):
            if run.suite_id != suite_id:
                continue
            for result in run.results:
                if result.case_id == case_id:
                    history.append(result.status)
        return history[:limit]
