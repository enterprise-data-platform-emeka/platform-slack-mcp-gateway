"""Client and tool facade for the existing analytics agent API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class AnalyticsAgentError(RuntimeError):
    """Raised when the analytics agent cannot answer a request."""


@dataclass(frozen=True)
class AnalyticsResult:
    insight: str
    assumptions: list[str] = field(default_factory=list)
    validation_flags: list[str] = field(default_factory=list)
    execution_id: str = ""
    bytes_scanned: int = 0
    cost_usd: float = 0.0
    session_id: str = ""
    chart_type: str = "none"
    presigned_url: str | None = None
    sql: str = ""
    inferred_question: str = ""
    request_id: str = ""
    verdict: str = "No"
    discrepancy_detail: str = "None"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AnalyticsResult":
        return cls(
            insight=str(payload.get("insight", "")),
            assumptions=list(payload.get("assumptions") or []),
            validation_flags=list(payload.get("validation_flags") or []),
            execution_id=str(payload.get("execution_id", "")),
            bytes_scanned=int(payload.get("bytes_scanned") or 0),
            cost_usd=float(payload.get("cost_usd") or 0.0),
            session_id=str(payload.get("session_id", "")),
            chart_type=str(payload.get("chart_type", "none")),
            presigned_url=payload.get("presigned_url"),
            sql=str(payload.get("sql", "")),
            inferred_question=str(payload.get("inferred_question", "")),
            request_id=str(payload.get("request_id", "")),
            verdict=str(payload.get("verdict", "No")),
            discrepancy_detail=str(payload.get("discrepancy_detail", "None")),
        )


class AnalyticsAgentClient:
    """Small stdlib HTTP client for the analytics agent."""

    def __init__(self, base_url: str, timeout_seconds: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def ask(self, question: str, session_id: str | None = None) -> AnalyticsResult:
        payload: dict[str, str] = {"question": question}
        if session_id:
            payload["session_id"] = session_id

        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/ask",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AnalyticsAgentError(f"Analytics agent returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AnalyticsAgentError(f"Could not reach analytics agent: {exc.reason}") from exc

        try:
            return AnalyticsResult.from_payload(json.loads(response_body))
        except (TypeError, ValueError) as exc:
            raise AnalyticsAgentError("Analytics agent returned invalid JSON") from exc


class AnalyticsMCPTool:
    """Tool facade that keeps Slack decoupled from the analytics API shape.

    This class is the first MCP boundary. The Slack listener calls one tool,
    `ask_data_question`, and future MCP server transports can expose the same
    method without changing Slack event handling.
    """

    def __init__(self, client: AnalyticsAgentClient) -> None:
        self._client = client

    def ask_data_question(self, question: str, session_id: str | None = None) -> AnalyticsResult:
        return self._client.ask(question=question, session_id=session_id)

