"""Slack message formatting helpers."""

from __future__ import annotations

import re

from gateway.analytics import AnalyticsResult


_MENTION_RE = re.compile(r"<@[A-Z0-9]+>\s*")


def extract_question(text: str) -> str:
    """Remove Slack mention markup and normalize whitespace."""
    without_mentions = _MENTION_RE.sub("", text or "")
    return " ".join(without_mentions.split())


def allowed_channel(channel_name: str | None, allowed_channels: set[str]) -> bool:
    if not allowed_channels:
        return True
    return bool(channel_name and channel_name in allowed_channels)


def format_answer(result: AnalyticsResult) -> str:
    lines = [":bar_chart: *EDP Analytics Agent*", "", result.insight.strip()]

    facts = []
    if result.chart_type and result.chart_type != "none":
        facts.append(f"chart: `{result.chart_type}`")
    facts.append(f"cost: `${result.cost_usd:.6f}`")
    if result.bytes_scanned:
        facts.append(f"scanned: `{_format_bytes(result.bytes_scanned)}`")
    if result.verdict:
        facts.append(f"intent discrepancy: `{result.verdict}`")
    lines.extend(["", " | ".join(facts)])

    if result.assumptions:
        lines.extend(["", "*Assumptions:*"])
        lines.extend(f"- {item}" for item in result.assumptions[:5])

    if result.validation_flags:
        lines.extend(["", "*Data quality notices:*"])
        lines.extend(f"- {item}" for item in result.validation_flags[:5])

    if result.discrepancy_detail and result.discrepancy_detail != "None":
        lines.extend(["", f"*Intent check:* {result.discrepancy_detail}"])

    if result.presigned_url:
        lines.extend(["", f"*Chart image:* {result.presigned_url}"])

    if result.sql:
        sql = _truncate(result.sql.strip(), 2500)
        lines.extend(["", "*SQL:*", f"```{sql}```"])

    if result.request_id:
        lines.extend(["", f"_Request ID: `{result.request_id}`_"])

    return "\n".join(lines)


def format_error(message: str) -> str:
    return f":warning: I could not answer that yet.\n\n```{_truncate(message, 2500)}```"


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."

