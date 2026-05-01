"""Runtime configuration for the Slack MCP gateway."""

from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass


def _csv(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _streamlit_url(api_url: str) -> str:
    try:
        p = urllib.parse.urlparse(api_url.rstrip("/"))
        host = p.hostname or "localhost"
        return f"{p.scheme}://{host}:8501"
    except Exception:
        return ""


@dataclass(frozen=True)
class Config:
    slack_app_token: str
    slack_bot_token: str
    analytics_agent_url: str
    streamlit_url: str
    allowed_channels: set[str]
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        api_url = os.getenv("ANALYTICS_AGENT_URL", "http://localhost:8080")
        return cls(
            slack_app_token=_required("SLACK_APP_TOKEN"),
            slack_bot_token=_required("SLACK_BOT_TOKEN"),
            analytics_agent_url=api_url,
            streamlit_url=_streamlit_url(api_url),
            allowed_channels=_csv(os.getenv("SLACK_ALLOWED_CHANNELS", "")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value

