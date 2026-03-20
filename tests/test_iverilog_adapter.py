import os
import shutil
from pathlib import Path

import pytest

from dv_regression_lab.orchestrator import run_suite
from dv_regression_lab.store import RunStore


def test_iverilog_adapter_runs_with_fake_toolchain(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_iverilog(bin_dir / "iverilog")
    _write_fake_vvp(bin_dir / "vvp")
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")

    project_root = Path(__file__).resolve().parents[1]
    suite_path = project_root / "examples" / "rtl_smoke_iverilog.yaml"
    store = RunStore(tmp_path / "store")

    run = run_suite(suite_path, store)

    assert run.simulator_kind == "iverilog"
    assert run.case_total == 2
    assert any(result.status == "passed" for result in run.results)
    assert any(result.category == "assertion_failure" for result in run.results)
    assert store.load_run(run.run_id) is not None


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="Icarus Verilog is not installed in this environment",
)
def test_iverilog_adapter_real_toolchain_smoke(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    suite_path = project_root / "examples" / "rtl_smoke_iverilog.yaml"
    store = RunStore(tmp_path / "store")

    run = run_suite(suite_path, store)

    assert run.simulator_kind == "iverilog"
    assert run.results[0].artifact_paths
    assert run.results[0].status in {"passed", "failed"}


def _write_fake_iverilog(path: Path) -> None:
    path.write_text(
        """#!/bin/sh
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then
    out="$2"
    shift 2
    continue
  fi
  shift
done
echo "compile completed successfully"
printf '%s\\n' "fake-compiled-image" > "$out"
exit 0
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_vvp(path: Path) -> None:
    path.write_text(
        """#!/bin/sh
mode="pass"
for arg in "$@"; do
  case "$arg" in
    +MODE=fail)
      mode="fail"
      ;;
  esac
done
if [ "$mode" = "fail" ]; then
  echo "ASSERTION FAILED: irq priority mismatch"
  exit 1
fi
echo "TEST_PASS: irq routing smoke"
exit 0
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
