from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import RegressionCaseResult, SimulatorConfig, TestCaseSpec
from .taxonomy import FAILURE_TAXONOMY, classify_failure

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


def available_simulators() -> Dict[str, bool]:
    return {
        "mock": True,
        "iverilog": shutil.which("iverilog") is not None and shutil.which("vvp") is not None,
        "verilator": shutil.which("verilator") is not None,
    }


def _resolved_profile(profile: str, previous_attempts: int) -> str:
    if profile == "flaky_assertion":
        return "assertion_failure" if previous_attempts % 2 == 0 else "pass"
    if profile == "flaky_timeout":
        return "timeout" if previous_attempts % 2 == 0 else "pass"
    return profile


class MockSimulatorAdapter:
    def __init__(self, config: SimulatorConfig, suite_root: Path):
        self.config = config
        self.suite_root = suite_root

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


class IverilogAdapter:
    def __init__(self, config: SimulatorConfig, suite_root: Path):
        self.config = config
        self.suite_root = suite_root.resolve()
        self.iverilog_bin = config.executable or "iverilog"
        self.vvp_bin = config.runner_executable or "vvp"
        self.work_dir = (self.suite_root / config.work_dir).resolve()

    def run_case(
        self,
        case: TestCaseSpec,
        previous_attempts: int,
        artifacts_root: Path,
    ) -> RegressionCaseResult:
        case_dir = artifacts_root / case.id
        case_dir.mkdir(parents=True, exist_ok=True)
        compile_log = case_dir / "compile.log"
        sim_log = case_dir / "sim.log"
        meta_json = case_dir / "meta.json"
        compiled_image = case_dir / "simv.out"

        iverilog_path = shutil.which(self.iverilog_bin)
        vvp_path = shutil.which(self.vvp_bin)
        if not iverilog_path or not vvp_path:
            signature = (
                f"tool not found: {self.iverilog_bin if not iverilog_path else self.vvp_bin}"
            )
            return self._failure_result(
                case=case,
                case_dir=case_dir,
                compile_log=compile_log,
                sim_log=sim_log,
                meta_json=meta_json,
                signature=signature,
                summary="Install Icarus Verilog and ensure both iverilog and vvp are on PATH.",
                category="environment_issue",
                runtime_sec=0.0,
                compile_cmd=[],
                run_cmd=[],
                source_paths=[],
                compiled_image=compiled_image,
            )

        source_paths = self._source_paths(case)
        compile_cmd = self._compile_command(case, source_paths, compiled_image, iverilog_path)
        run_cmd = self._run_command(case, compiled_image, vvp_path)

        compile_started = time.perf_counter()
        compile_proc = subprocess.run(
            compile_cmd,
            cwd=case_dir,
            capture_output=True,
            text=True,
            timeout=self.config.compile_timeout_sec,
            check=False,
        )
        compile_runtime = time.perf_counter() - compile_started
        compile_text = _process_output(compile_proc)
        compile_log.write_text(compile_text, encoding="utf-8")

        if compile_proc.returncode != 0:
            signature = _extract_failure_signature(
                compile_text,
                default="compile failed: iverilog returned a non-zero exit code",
            )
            return self._failure_result(
                case=case,
                case_dir=case_dir,
                compile_log=compile_log,
                sim_log=sim_log,
                meta_json=meta_json,
                signature=signature,
                summary=FAILURE_TAXONOMY["compile_error"]["action"],
                category="compile_error",
                runtime_sec=round(compile_runtime, 3),
                compile_cmd=compile_cmd,
                run_cmd=run_cmd,
                source_paths=source_paths,
                compiled_image=compiled_image,
            )

        runtime_budget = case.timeout_sec or self.config.run_timeout_sec
        sim_started = time.perf_counter()
        try:
            sim_proc = subprocess.run(
                run_cmd,
                cwd=case_dir,
                capture_output=True,
                text=True,
                timeout=runtime_budget,
                check=False,
            )
            sim_runtime = time.perf_counter() - sim_started
        except subprocess.TimeoutExpired as exc:
            sim_text = _timeout_output(exc, runtime_budget)
            sim_log.write_text(sim_text, encoding="utf-8")
            return self._failure_result(
                case=case,
                case_dir=case_dir,
                compile_log=compile_log,
                sim_log=sim_log,
                meta_json=meta_json,
                signature=f"TIMEOUT: simulation exceeded {runtime_budget}s",
                summary=FAILURE_TAXONOMY["timeout"]["action"],
                category="timeout",
                runtime_sec=round(compile_runtime + runtime_budget, 3),
                compile_cmd=compile_cmd,
                run_cmd=run_cmd,
                source_paths=source_paths,
                compiled_image=compiled_image,
            )

        sim_text = _process_output(sim_proc)
        sim_log.write_text(sim_text, encoding="utf-8")

        matched_fail = _find_pattern_line(sim_text, case.fail_patterns)
        matched_pass = _find_pattern_line(sim_text, case.pass_patterns)
        status = "passed"
        if sim_proc.returncode != 0 or matched_fail or (case.pass_patterns and not matched_pass):
            status = "failed"

        if status == "passed":
            signature = matched_pass or "TEST_PASS: simulation completed successfully"
            category = "passed"
            summary = "Icarus Verilog run completed and the pass pattern matched."
        else:
            signature = matched_fail or _extract_failure_signature(
                sim_text,
                default=f"simulation failed with exit code {sim_proc.returncode}",
            )
            category = classify_failure(f"{signature}\n{sim_text}", status)
            summary = str(FAILURE_TAXONOMY.get(category, FAILURE_TAXONOMY["unknown"])["action"])

        runtime_sec = round(compile_runtime + sim_runtime, 3)
        artifact_paths = _artifact_paths(case_dir, compile_log, sim_log, meta_json, compiled_image)
        meta_json.write_text(
            json.dumps(
                {
                    "adapter": "iverilog",
                    "case_id": case.id,
                    "module": case.module,
                    "seed": case.seed,
                    "runtime_sec": runtime_sec,
                    "compile_cmd": compile_cmd,
                    "run_cmd": run_cmd,
                    "source_paths": source_paths,
                    "previous_attempts": previous_attempts,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        artifact_paths = _artifact_paths(case_dir, compile_log, sim_log, meta_json, compiled_image)
        return RegressionCaseResult(
            case_id=case.id,
            title=case.title,
            module=case.module,
            owner=case.owner,
            status=status,
            profile=case.profile or self.config.kind,
            category=category,
            summary=summary,
            signature=signature,
            seed=case.seed,
            runtime_sec=runtime_sec,
            tags=case.tags,
            design_units=case.design_units,
            rerun_recommended=category in {"timeout", "protocol_mismatch", "environment_issue"},
            artifact_paths=artifact_paths,
            log_excerpt=_trim_excerpt(sim_text if sim_text.strip() else compile_text),
        )

    def _source_paths(self, case: TestCaseSpec) -> List[str]:
        raw_sources = list(self.config.sources) + list(case.sources)
        if not raw_sources:
            raise ValueError("Iverilog adapter requires at least one source path.")
        return [str((self.work_dir / source).resolve()) for source in raw_sources]

    def _compile_command(
        self,
        case: TestCaseSpec,
        source_paths: List[str],
        compiled_image: Path,
        iverilog_path: str,
    ) -> List[str]:
        command = [iverilog_path, "-g2012", "-o", str(compiled_image)]
        top_module = self.config.top_module or case.module
        if top_module:
            command.extend(["-s", top_module])
        for include_dir in self.config.include_dirs:
            command.extend(["-I", str((self.work_dir / include_dir).resolve())])
        command.extend(self.config.compile_flags)
        command.extend(_format_defines(self.config.shared_defines))
        command.extend(_format_defines(case.compile_defines))
        command.extend(source_paths)
        return command

    def _run_command(self, case: TestCaseSpec, compiled_image: Path, vvp_path: str) -> List[str]:
        command = [vvp_path, str(compiled_image)]
        if not any(arg.startswith("+SEED=") for arg in case.plusargs):
            command.append(f"+SEED={case.seed}")
        command.extend(case.plusargs)
        return command

    def _failure_result(
        self,
        case: TestCaseSpec,
        case_dir: Path,
        compile_log: Path,
        sim_log: Path,
        meta_json: Path,
        signature: str,
        summary: str,
        category: str,
        runtime_sec: float,
        compile_cmd: List[str],
        run_cmd: List[str],
        source_paths: List[str],
        compiled_image: Path,
    ) -> RegressionCaseResult:
        compile_log.write_text(
            signature if not compile_log.exists() else compile_log.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        if not sim_log.exists():
            sim_log.write_text("", encoding="utf-8")
        meta_json.write_text(
            json.dumps(
                {
                    "adapter": self.config.kind,
                    "case_id": case.id,
                    "module": case.module,
                    "seed": case.seed,
                    "runtime_sec": runtime_sec,
                    "compile_cmd": compile_cmd,
                    "run_cmd": run_cmd,
                    "source_paths": source_paths,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        artifact_paths = _artifact_paths(case_dir, compile_log, sim_log, meta_json, compiled_image)
        return RegressionCaseResult(
            case_id=case.id,
            title=case.title,
            module=case.module,
            owner=case.owner,
            status="failed",
            profile=case.profile or self.config.kind,
            category=category,
            summary=str(summary),
            signature=signature,
            seed=case.seed,
            runtime_sec=runtime_sec,
            tags=case.tags,
            design_units=case.design_units,
            rerun_recommended=category in {"timeout", "protocol_mismatch", "environment_issue"},
            artifact_paths=artifact_paths,
            log_excerpt=_trim_excerpt(signature),
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


def build_adapter(config: SimulatorConfig, suite_root: Path):
    if config.kind == "mock":
        return MockSimulatorAdapter(config, suite_root)
    if config.kind == "iverilog":
        return IverilogAdapter(config, suite_root)
    raise ValueError(f"Unsupported simulator kind: {config.kind}")


def _format_defines(defines: Dict[str, str]) -> List[str]:
    flags: List[str] = []
    for key, value in defines.items():
        if value == "":
            flags.append(f"-D{key}")
        else:
            flags.append(f"-D{key}={value}")
    return flags


def _process_output(proc: subprocess.CompletedProcess) -> str:
    parts = []
    if proc.stdout:
        parts.append(proc.stdout.rstrip())
    if proc.stderr:
        parts.append(proc.stderr.rstrip())
    return "\n".join(parts).strip() + ("\n" if parts else "")


def _timeout_output(exc: subprocess.TimeoutExpired, runtime_budget: int) -> str:
    stdout = exc.stdout or ""
    stderr = exc.stderr or ""
    return (
        f"{stdout.rstrip()}\n{stderr.rstrip()}\nTIMEOUT: simulation exceeded {runtime_budget}s\n"
    ).strip() + "\n"


def _find_pattern_line(text: str, patterns: List[str]) -> Optional[str]:
    if not patterns:
        return None
    lines = text.splitlines()
    for pattern in patterns:
        for line in lines:
            if pattern in line:
                return line.strip()
    return None


def _extract_failure_signature(text: str, default: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return default


def _trim_excerpt(text: str, limit: int = 500) -> str:
    stripped = text.strip()
    return stripped[:limit]


def _artifact_paths(
    case_dir: Path,
    compile_log: Path,
    sim_log: Path,
    meta_json: Path,
    compiled_image: Path,
) -> List[str]:
    paths = [compile_log, sim_log, meta_json]
    if compiled_image.exists():
        paths.append(compiled_image)
    wave_artifacts = sorted(case_dir.glob("*.vcd")) + sorted(case_dir.glob("*.fst"))
    paths.extend(wave_artifacts)
    return [str(path) for path in paths if path.exists()]
