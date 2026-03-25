"""DV Triage AI Assistant - OpenAI-powered failure analysis for regression runs."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .models import RegressionRun

_SYSTEM_PROMPT = """\
You are an expert Design Verification (DV) triage engineer. You analyze RTL/DV regression run
results and help engineers understand failures, distinguish real bugs from flaky tests, and
suggest actionable fixes.

You are given a structured regression context including:
- Pass/fail counts and pass rate
- Failure taxonomy buckets (categories of failures)
- Flaky test list (tests that have passed and failed across runs)
- Rerun candidates with reasons
- Hot design units (most failing RTL modules)
- Operator brief summary

Answer concisely and technically. Reference specific test IDs, categories, and design units
from the context when relevant. If you are not sure, say so.
"""


def _build_context_block(run: RegressionRun) -> str:
    """Serialize a RegressionRun into a human-readable context block for the LLM."""
    lines: List[str] = [
        f"Run ID: {run.run_id}",
        f"Suite: {run.suite_id} — {run.title}",
        f"Owner: {run.owner}",
        f"Simulator: {run.simulator_kind}",
        f"Total cases: {run.case_total}  Passed: {run.passed}  Failed: {run.failed}",
        f"Pass rate: {run.pass_rate:.1%}",
        f"Quality gate: {run.quality_gate}",
        f"Duration: {run.duration_sec:.1f}s",
        f"Requested: {run.requested_at}  Completed: {run.completed_at}",
    ]

    if run.triage:
        t = run.triage
        lines.append("")
        lines.append("=== TRIAGE SUMMARY ===")

        if t.failure_buckets:
            lines.append("Failure buckets:")
            for category, count in sorted(t.failure_buckets.items(), key=lambda x: -x[1]):
                lines.append(f"  {category}: {count}")

        if t.flaky_cases:
            lines.append(f"Flaky tests ({len(t.flaky_cases)}): {', '.join(t.flaky_cases)}")
        else:
            lines.append("Flaky tests: none detected")

        if t.rerun_candidates:
            lines.append(f"Rerun candidates ({len(t.rerun_candidates)}):")
            for rc in t.rerun_candidates:
                lines.append(
                    f"  [{rc.get('priority', 'medium')}] {rc['case_id']} "
                    f"({rc['category']}): {rc.get('reason', '')}"
                )

        if t.hot_design_units:
            lines.append("Hot design units:")
            for unit in t.hot_design_units:
                lines.append(f"  {unit['design_unit']}: {unit['failing_cases']} failing case(s)")

        if t.operator_brief:
            lines.append("Operator brief:")
            for note in t.operator_brief:
                lines.append(f"  - {note}")

    if run.results:
        lines.append("")
        lines.append(
            f"=== FAILED CASES ({sum(1 for r in run.results if r.status == 'failed')}) ==="
        )
        for result in run.results:
            if result.status != "failed":
                continue
            lines.append(
                f"  [{result.case_id}] category={result.category} "
                f"signature={result.signature!r} "
                f"rerun_recommended={result.rerun_recommended}"
            )
            if result.log_excerpt:
                lines.append(f"    log: {result.log_excerpt[:200]}")

    return "\n".join(lines)


class _StubClient:
    """Fallback when OPENAI_API_KEY is not set. Returns canned responses."""

    def chat(self, messages: List[Dict[str, str]]) -> str:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        lower = last_user.lower()
        if "flaky" in lower:
            return (
                "[STUB] Based on the triage context, check the flaky_cases list. "
                "Flaky tests show mixed pass/fail history and are candidates for seed "
                "stabilization or environment investigation. Set OPENAI_API_KEY for real analysis."
            )
        if "fix" in lower or "suggest" in lower:
            return (
                "[STUB] Suggested fix: review the failure_buckets for the dominant category "
                "and consult taxonomy action guidance. Set OPENAI_API_KEY for real analysis."
            )
        return (
            "[STUB] No OPENAI_API_KEY set. This is a placeholder response. "
            "Load the key to get real AI-powered triage analysis."
        )


class _OpenAIClient:
    """Thin wrapper around the openai chat completions API."""

    def __init__(self, api_key: str, model: str) -> None:
        import openai  # local import to avoid hard dep when stub is used

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def chat(self, messages: List[Dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
        )
        return response.choices[0].message.content or ""


class DVTriageAssistant:
    """Multi-turn conversational AI assistant for DV regression triage.

    Usage::

        assistant = DVTriageAssistant(run)
        print(assistant.ask("What caused this failure?"))
        print(assistant.ask("Is the timeout test likely flaky?"))
        assistant.reset()
    """

    def __init__(
        self,
        run: RegressionRun,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._run = run
        self._context_block = _build_context_block(run)
        self._model = model
        self._history: List[Dict[str, str]] = []

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if resolved_key:
            self._client: Any = _OpenAIClient(api_key=resolved_key, model=model)
            self._using_stub = False
        else:
            self._client = _StubClient()
            self._using_stub = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def using_stub(self) -> bool:
        """True when operating without a real OpenAI key (stub mode)."""
        return self._using_stub

    def ask(self, question: str) -> str:
        """Send a question and return the assistant reply. History is maintained."""
        self._history.append({"role": "user", "content": question})
        messages = self._build_messages()
        reply = self._client.chat(messages)
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> None:
        """Clear conversation history (keeps run context)."""
        self._history = []

    def history(self) -> List[Dict[str, str]]:
        """Return a copy of the current conversation history."""
        return list(self._history)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_messages(self) -> List[Dict[str, str]]:
        system_with_context = (
            _SYSTEM_PROMPT + "\n\n=== REGRESSION RUN CONTEXT ===\n" + self._context_block
        )
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_with_context}]
        messages.extend(self._history)
        return messages
