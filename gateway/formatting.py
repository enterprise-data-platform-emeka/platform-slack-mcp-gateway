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


def format_answer(result: AnalyticsResult, streamlit_url: str = "") -> str:
    lines = [":bar_chart: *EDP Analytics Agent*", ""]

    # Summary section — blockquote gives a visible left border in Slack
    lines.append("*Summary*")
    for sentence in result.insight.strip().splitlines():
        lines.append(f"> {sentence}" if sentence.strip() else ">")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    facts = [f"cost: `${result.cost_usd:.6f}`"]
    if result.chart_type and result.chart_type not in ("none", ""):
        facts.append(f"chart: `{result.chart_type}`")
    if result.verdict == "Yes":
        facts.append("intent: `mismatch detected`")
    lines.extend(["", " | ".join(facts)])

    if streamlit_url:
        lines.extend(["", f"<{streamlit_url}|View full report in Streamlit>"])

    return "\n".join(lines)


def format_assumptions(result: AnalyticsResult) -> str:
    if not result.assumptions:
        return ""
    lines = ["*Assumptions*"]
    lines.extend(f"• {item}" for item in result.assumptions[:2])
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

