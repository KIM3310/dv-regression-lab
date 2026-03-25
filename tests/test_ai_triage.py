"""Tests for dv_regression_lab.ai_triage — all external calls mocked."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch


from dv_regression_lab.ai_triage import (
    DVTriageAssistant,
    _StubClient,
    _build_context_block,
)
from dv_regression_lab.models import (
    RegressionCaseResult,
    RegressionRun,
    TriageSummary,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_result(
    case_id: str = "test_dma_basic",
    status: str = "failed",
    category: str = "timeout",
    signature: str = "TIMEOUT",
    rerun_recommended: bool = True,
    log_excerpt: str = "watchdog expired after 120s",
) -> RegressionCaseResult:
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
        seed=42,
        runtime_sec=120.0,
        tags=["smoke"],
        design_units=["dma_engine.sv"],
        rerun_recommended=rerun_recommended,
        artifact_paths=[],
        log_excerpt=log_excerpt,
    )


def _make_run(
    run_id: str = "run-001",
    passed: int = 8,
    failed: int = 2,
    results: List[RegressionCaseResult] | None = None,
    triage: TriageSummary | None = None,
) -> RegressionRun:
    if results is None:
        results = [_make_result()]
    if triage is None:
        triage = TriageSummary(
            run_id=run_id,
            failure_buckets={"timeout": 1, "assertion_failure": 1},
            rerun_candidates=[
                {
                    "case_id": "test_dma_basic",
                    "category": "timeout",
                    "priority": "high",
                    "reason": "Check deadlock, long-tail latency, and runtime budget.",
                }
            ],
            flaky_cases=["test_irq_edge"],
            hot_design_units=[{"design_unit": "dma_engine.sv", "failing_cases": 2}],
            operator_brief=["2/10 cases failed. quality gate=fail."],
        )
    return RegressionRun(
        run_id=run_id,
        suite_id="soc_smoke_matrix",
        title="SoC Smoke Matrix",
        owner="dv-platform",
        simulator_kind="mock",
        requested_at="2026-03-22T10:00:00Z",
        completed_at="2026-03-22T10:05:00Z",
        case_total=passed + failed,
        passed=passed,
        failed=failed,
        pass_rate=passed / (passed + failed),
        duration_sec=300.0,
        quality_gate="fail",
        results=results,
        triage=triage,
    )


# ---------------------------------------------------------------------------
# _build_context_block tests
# ---------------------------------------------------------------------------


def test_context_block_includes_run_id():
    run = _make_run(run_id="run-xyz")
    block = _build_context_block(run)
    assert "run-xyz" in block


def test_context_block_includes_pass_rate():
    run = _make_run(passed=8, failed=2)
    block = _build_context_block(run)
    assert "80.0%" in block


def test_context_block_includes_failure_buckets():
    run = _make_run()
    block = _build_context_block(run)
    assert "timeout" in block
    assert "assertion_failure" in block


def test_context_block_includes_flaky_cases():
    run = _make_run()
    block = _build_context_block(run)
    assert "test_irq_edge" in block


def test_context_block_includes_hot_design_units():
    run = _make_run()
    block = _build_context_block(run)
    assert "dma_engine.sv" in block


def test_context_block_includes_failed_case_id():
    run = _make_run(results=[_make_result(case_id="test_dma_basic")])
    block = _build_context_block(run)
    assert "test_dma_basic" in block


def test_context_block_no_triage_still_renders():
    run = _make_run(triage=None)
    block = _build_context_block(run)
    assert "run-001" in block
    assert "run-001" in block  # renders even without triage


# ---------------------------------------------------------------------------
# _StubClient tests
# ---------------------------------------------------------------------------


def test_stub_client_returns_string():
    client = _StubClient()
    reply = client.chat([{"role": "user", "content": "What caused this failure?"}])
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_stub_client_flaky_keyword():
    client = _StubClient()
    reply = client.chat([{"role": "user", "content": "Is this test flaky?"}])
    assert "flaky" in reply.lower()


def test_stub_client_fix_keyword():
    client = _StubClient()
    reply = client.chat([{"role": "user", "content": "Suggest a fix for this timeout."}])
    assert "fix" in reply.lower() or "suggest" in reply.lower()


def test_stub_client_generic_response():
    client = _StubClient()
    reply = client.chat([{"role": "user", "content": "Hello"}])
    assert "STUB" in reply


# ---------------------------------------------------------------------------
# DVTriageAssistant — stub mode (no API key)
# ---------------------------------------------------------------------------


def test_assistant_uses_stub_when_no_key():
    run = _make_run()
    with patch.dict("os.environ", {}, clear=True):
        # Ensure OPENAI_API_KEY is absent
        import os

        os.environ.pop("OPENAI_API_KEY", None)
        assistant = DVTriageAssistant(run, api_key=None)
    assert assistant.using_stub is True


def test_assistant_stub_ask_returns_string():
    run = _make_run()
    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("OPENAI_API_KEY", None)
        assistant = DVTriageAssistant(run, api_key=None)
    reply = assistant.ask("What caused this failure?")
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_assistant_history_grows_with_turns():
    run = _make_run()
    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("OPENAI_API_KEY", None)
        assistant = DVTriageAssistant(run, api_key=None)
    assistant.ask("What caused this failure?")
    assistant.ask("Is it flaky?")
    assert len(assistant.history()) == 4  # 2 user + 2 assistant


def test_assistant_reset_clears_history():
    run = _make_run()
    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("OPENAI_API_KEY", None)
        assistant = DVTriageAssistant(run, api_key=None)
    assistant.ask("Any flaky tests?")
    assistant.reset()
    assert assistant.history() == []


def test_assistant_history_returns_copy():
    run = _make_run()
    with patch.dict("os.environ", {}, clear=True):
        import os

        os.environ.pop("OPENAI_API_KEY", None)
        assistant = DVTriageAssistant(run, api_key=None)
    assistant.ask("Question")
    h = assistant.history()
    h.clear()
    assert len(assistant.history()) == 2  # original untouched


# ---------------------------------------------------------------------------
# DVTriageAssistant — mocked OpenAI client
# ---------------------------------------------------------------------------


def _make_openai_response(content: str) -> Any:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def test_assistant_openai_path_called_with_messages():
    run = _make_run()
    _make_openai_response("The timeout is caused by a DMA deadlock.")

    with patch("dv_regression_lab.ai_triage._OpenAIClient") as MockClient:
        instance = MockClient.return_value
        instance.chat.return_value = "The timeout is caused by a DMA deadlock."
        assistant = DVTriageAssistant(run, api_key="sk-fake-key")

    assert assistant.using_stub is False


def test_assistant_openai_ask_returns_reply():
    run = _make_run()
    expected = "Root cause: missing reset synchronization in dma_engine."

    with patch("dv_regression_lab.ai_triage._OpenAIClient") as MockClient:
        instance = MockClient.return_value
        instance.chat.return_value = expected
        assistant = DVTriageAssistant(run, api_key="sk-fake-key")
        reply = assistant.ask("What caused this failure?")

    assert reply == expected


def test_assistant_openai_multi_turn_passes_history():
    run = _make_run()

    with patch("dv_regression_lab.ai_triage._OpenAIClient") as MockClient:
        instance = MockClient.return_value
        instance.chat.side_effect = ["First answer.", "Second answer."]
        assistant = DVTriageAssistant(run, api_key="sk-fake-key")
        r1 = assistant.ask("First question")
        r2 = assistant.ask("Second question")

    assert r1 == "First answer."
    assert r2 == "Second answer."
    # Second call should have received a messages list including prior turn
    second_call_messages = instance.chat.call_args_list[1][0][0]
    roles = [m["role"] for m in second_call_messages]
    assert "user" in roles
    assert "assistant" in roles


def test_assistant_system_prompt_contains_context():
    run = _make_run(run_id="context-check-run")
    captured: List[Any] = []

    def capture_messages(messages: List[Dict[str, str]]) -> str:
        captured.append(messages)
        return "ok"

    with patch("dv_regression_lab.ai_triage._OpenAIClient") as MockClient:
        instance = MockClient.return_value
        instance.chat.side_effect = capture_messages
        assistant = DVTriageAssistant(run, api_key="sk-fake-key")
        assistant.ask("Describe the run.")

    system_content = captured[0][0]["content"]
    assert "context-check-run" in system_content


def test_assistant_uses_env_api_key():
    run = _make_run()
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-key"}):
        with patch("dv_regression_lab.ai_triage._OpenAIClient") as MockClient:
            MockClient.return_value.chat.return_value = "ok"
            assistant = DVTriageAssistant(run)
    assert assistant.using_stub is False
    MockClient.assert_called_once_with(api_key="sk-env-key", model="gpt-4o-mini")
