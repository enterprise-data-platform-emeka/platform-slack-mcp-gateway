"""Process entry point for the Slack MCP gateway."""

from __future__ import annotations

import logging

from gateway.analytics import AnalyticsAgentClient, AnalyticsMCPTool
from gateway.config import Config
from gateway.slack_app import build_app, run_socket_mode


def main() -> None:
    config = Config.from_env()
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    client = AnalyticsAgentClient(config.analytics_agent_url)
    tool = AnalyticsMCPTool(client)
    app = build_app(config, tool)
    run_socket_mode(config, app)


if __name__ == "__main__":
    main()

