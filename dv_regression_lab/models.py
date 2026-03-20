from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SimulatorConfig:
    kind: str = "mock"
    compile_timeout_sec: int = 30
    run_timeout_sec: int = 120
    executable: str = ""
    runner_executable: str = ""
    work_dir: str = "."
    sources: List[str] = field(default_factory=list)
    include_dirs: List[str] = field(default_factory=list)
    compile_flags: List[str] = field(default_factory=list)
    shared_defines: Dict[str, str] = field(default_factory=dict)
    top_module: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulatorConfig":
        return cls(
            kind=data.get("kind", "mock"),
            compile_timeout_sec=int(data.get("compile_timeout_sec", 30)),
            run_timeout_sec=int(data.get("run_timeout_sec", 120)),
            executable=data.get("executable", ""),
            runner_executable=data.get("runner_executable", ""),
            work_dir=data.get("work_dir", "."),
            sources=list(data.get("sources", [])),
            include_dirs=list(data.get("include_dirs", [])),
            compile_flags=list(data.get("compile_flags", [])),
            shared_defines=dict(data.get("shared_defines", {})),
            top_module=data.get("top_module", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestCaseSpec:
    id: str
    title: str
    module: str
    tags: List[str] = field(default_factory=list)
    seed: int = 1
    owner: str = "dv-platform"
    expected_runtime_sec: float = 5.0
    design_units: List[str] = field(default_factory=list)
    profile: str = "pass"
    notes: str = ""
    sources: List[str] = field(default_factory=list)
    plusargs: List[str] = field(default_factory=list)
    pass_patterns: List[str] = field(default_factory=list)
    fail_patterns: List[str] = field(default_factory=list)
    compile_defines: Dict[str, str] = field(default_factory=dict)
    timeout_sec: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCaseSpec":
        return cls(
            id=data["id"],
            title=data["title"],
            module=data["module"],
            tags=list(data.get("tags", [])),
            seed=int(data.get("seed", 1)),
            owner=data.get("owner", "dv-platform"),
            expected_runtime_sec=float(data.get("expected_runtime_sec", 5.0)),
            design_units=list(data.get("design_units", [])),
            profile=data.get("profile", "pass"),
            notes=data.get("notes", ""),
            sources=list(data.get("sources", [])),
            plusargs=list(data.get("plusargs", [])),
            pass_patterns=list(data.get("pass_patterns", [])),
            fail_patterns=list(data.get("fail_patterns", [])),
            compile_defines=dict(data.get("compile_defines", {})),
            timeout_sec=int(data["timeout_sec"]) if data.get("timeout_sec") is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SuiteSpec:
    suite_id: str
    title: str
    owner: str
    description: str
    simulator: SimulatorConfig
    tests: List[TestCaseSpec]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuiteSpec":
        return cls(
            suite_id=data["suite_id"],
            title=data["title"],
            owner=data.get("owner", "dv-platform"),
            description=data.get("description", ""),
            simulator=SimulatorConfig.from_dict(data.get("simulator", {})),
            tests=[TestCaseSpec.from_dict(item) for item in data.get("tests", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "title": self.title,
            "owner": self.owner,
            "description": self.description,
            "simulator": self.simulator.to_dict(),
            "tests": [case.to_dict() for case in self.tests],
        }


@dataclass
class RegressionCaseResult:
    case_id: str
    title: str
    module: str
    owner: str
    status: str
    profile: str
    category: str
    summary: str
    signature: str
    seed: int
    runtime_sec: float
    tags: List[str]
    design_units: List[str]
    rerun_recommended: bool
    artifact_paths: List[str]
    log_excerpt: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegressionCaseResult":
        return cls(
            case_id=data["case_id"],
            title=data["title"],
            module=data["module"],
            owner=data["owner"],
            status=data["status"],
            profile=data["profile"],
            category=data["category"],
            summary=data["summary"],
            signature=data["signature"],
            seed=int(data["seed"]),
            runtime_sec=float(data["runtime_sec"]),
            tags=list(data.get("tags", [])),
            design_units=list(data.get("design_units", [])),
            rerun_recommended=bool(data.get("rerun_recommended", False)),
            artifact_paths=list(data.get("artifact_paths", [])),
            log_excerpt=data.get("log_excerpt", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TriageSummary:
    run_id: str
    failure_buckets: Dict[str, int]
    rerun_candidates: List[Dict[str, Any]]
    flaky_cases: List[str]
    hot_design_units: List[Dict[str, Any]]
    operator_brief: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriageSummary":
        return cls(
            run_id=data["run_id"],
            failure_buckets=dict(data.get("failure_buckets", {})),
            rerun_candidates=list(data.get("rerun_candidates", [])),
            flaky_cases=list(data.get("flaky_cases", [])),
            hot_design_units=list(data.get("hot_design_units", [])),
            operator_brief=list(data.get("operator_brief", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegressionRun:
    run_id: str
    suite_id: str
    title: str
    owner: str
    simulator_kind: str
    requested_at: str
    completed_at: str
    case_total: int
    passed: int
    failed: int
    pass_rate: float
    duration_sec: float
    quality_gate: str
    results: List[RegressionCaseResult]
    triage: Optional[TriageSummary] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegressionRun":
        triage = data.get("triage")
        return cls(
            run_id=data["run_id"],
            suite_id=data["suite_id"],
            title=data["title"],
            owner=data["owner"],
            simulator_kind=data["simulator_kind"],
            requested_at=data["requested_at"],
            completed_at=data["completed_at"],
            case_total=int(data["case_total"]),
            passed=int(data["passed"]),
            failed=int(data["failed"]),
            pass_rate=float(data["pass_rate"]),
            duration_sec=float(data["duration_sec"]),
            quality_gate=data["quality_gate"],
            results=[RegressionCaseResult.from_dict(item) for item in data.get("results", [])],
            triage=TriageSummary.from_dict(triage) if triage else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite_id": self.suite_id,
            "title": self.title,
            "owner": self.owner,
            "simulator_kind": self.simulator_kind,
            "requested_at": self.requested_at,
            "completed_at": self.completed_at,
            "case_total": self.case_total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "duration_sec": self.duration_sec,
            "quality_gate": self.quality_gate,
            "results": [result.to_dict() for result in self.results],
            "triage": self.triage.to_dict() if self.triage else None,
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite_id": self.suite_id,
            "title": self.title,
            "owner": self.owner,
            "simulator_kind": self.simulator_kind,
            "requested_at": self.requested_at,
            "completed_at": self.completed_at,
            "case_total": self.case_total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "duration_sec": self.duration_sec,
            "quality_gate": self.quality_gate,
            "has_triage": self.triage is not None,
        }
