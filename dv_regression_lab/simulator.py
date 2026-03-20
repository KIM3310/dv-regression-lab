from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from .models import RegressionCaseResult, SimulatorConfig, TestCaseSpec
from .taxonomy import classify_failure

PROFILE_OUTCOMES: Dict[str, Tuple[str, str, str]] = {
    "pass": (
        "passed",
        "Run completed cleanly.",
        "Simulation converged with no monitor violations.",
    ),
    ("assertion_failure"): (
        "failed",
        "ASSERTION FAILED: scoreboard mismatch on axi_awid",
        "Scoreboard diverged after a write burst reordering event.",
    ),
    "timeout": (
        "failed",
        "TIMEOUT: watchdog expired waiting for irq_done",
        "No forward progress observed before the runtime budget expired.",
    ),
    "compile_error": (
        "failed",
        "compile failed: unresolved reference to dma_rsp_if",
        "Build step failed before simulation start.",
    ),
    "x_propagation": (
        "failed",
        "XPROP detected on axi_rvalid",
        "Monitor observed unknown value propagation across the read channel.",
    ),
    "protocol_mismatch": (
        "failed",
        "protocol violation: AXI handshake mismatch on bvalid/bready",
        "Interface monitor reported a response channel ordering mismatch.",
    ),
}


def _resolved_profile(profile: str, previous_attempts: int) -> str:
    if profile == "flaky_assertion":
        return "assertion_failure" if previous_attempts % 2 == 0 else "pass"
    if profile == "flaky_timeout":
        return "timeout" if previous_attempts % 2 == 0 else "pass"
    return profile


class MockSimulatorAdapter:
    def __init__(self, config: SimulatorConfig):
        self.config = config

    def run_case(
        self,
        case: TestCaseSpec,
        previous_attempts: int,
        artifacts_root: Path,
    ) -> RegressionCaseResult:
        profile = _resolved_profile(case.profile, previous_attempts)
        status, signature, summary = PROFILE_OUTCOMES.get(
            profile,
            ("failed", "unknown failure signature", "No taxonomy profile matched the failure."),
        )
        category = classify_failure(signature, status)
        runtime_sec = _runtime_for_case(case, profile, previous_attempts)

        case_dir = artifacts_root / case.id
        case_dir.mkdir(parents=True, exist_ok=True)
        compile_log = case_dir / "compile.log"
        sim_log = case_dir / "sim.log"
        meta_json = case_dir / "meta.json"
        waveform = case_dir / "waves.vcd"

        compile_log.write_text(_compile_log(case, profile), encoding="utf-8")
        sim_log.write_text(_sim_log(case, status, signature, summary), encoding="utf-8")
        meta_json.write_text(
            json.dumps(
                {
                    "case_id": case.id,
                    "module": case.module,
                    "seed": case.seed,
                    "profile": profile,
                    "runtime_sec": runtime_sec,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        waveform.write_text("$comment mock waveform placeholder $end\n", encoding="utf-8")

        return RegressionCaseResult(
            case_id=case.id,
            title=case.title,
            module=case.module,
            owner=case.owner,
            status=status,
            profile=profile,
            category=category,
            summary=summary,
            signature=signature,
            seed=case.seed,
            runtime_sec=runtime_sec,
            tags=case.tags,
            design_units=case.design_units,
            rerun_recommended=category in {"timeout", "protocol_mismatch", "environment_issue"},
            artifact_paths=[str(compile_log), str(sim_log), str(meta_json), str(waveform)],
            log_excerpt=f"{signature}\n{summary}",
        )


def _runtime_for_case(case: TestCaseSpec, profile: str, previous_attempts: int) -> float:
    base = case.expected_runtime_sec
    jitter = ((case.seed * 17) + (previous_attempts * 13)) % 11
    factor = 0.82 + (jitter / 20)
    if profile == "compile_error":
        return 0.43
    if profile == "timeout":
        return float(case.expected_runtime_sec + min(12, case.expected_runtime_sec * 0.8))
    return round(base * factor, 2)


def _compile_log(case: TestCaseSpec, profile: str) -> str:
    if profile == "compile_error":
        return (
            f"[compile] module={case.module}\n"
            "error: unresolved reference to dma_rsp_if\n"
            "fatal: compile failed before elaboration\n"
        )
    return f"[compile] module={case.module}\ncompile completed successfully\n"


def _sim_log(case: TestCaseSpec, status: str, signature: str, summary: str) -> str:
    return (
        f"[sim] case={case.id}\n"
        f"[sim] seed={case.seed}\n"
        f"[sim] status={status}\n"
        f"[sim] signature={signature}\n"
        f"[sim] summary={summary}\n"
    )


def build_adapter(config: SimulatorConfig) -> MockSimulatorAdapter:
    if config.kind != "mock":
        raise ValueError(f"Unsupported simulator kind: {config.kind}")
    return MockSimulatorAdapter(config)
