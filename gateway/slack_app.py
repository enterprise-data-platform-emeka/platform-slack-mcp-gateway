"""Slack Socket Mode app for the EDP analytics gateway."""

from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from gateway.analytics import AnalyticsAgentError, AnalyticsMCPTool, AnalyticsResult
from gateway.config import Config
from gateway.formatting import allowed_channel, extract_question, format_answer, format_error

logger = logging.getLogger(__name__)


def build_app(config: Config, tool: AnalyticsMCPTool) -> App:
    app = App(token=config.slack_bot_token)
    slack_sessions: dict[str, str] = {}

    @app.event("app_mention")
    def handle_app_mention(event: dict, say, client) -> None:  # type: ignore[no-untyped-def]
        channel_id = event.get("channel", "")
        channel_name = _channel_name(client, channel_id)
        if not allowed_channel(channel_name, config.allowed_channels):
            logger.info("Ignoring message from channel %s", channel_name or channel_id)
            return
        _answer(event=event, say=say, client=client, tool=tool, slack_sessions=slack_sessions)

    @app.event("message")
    def handle_direct_message(event: dict, say, client) -> None:  # type: ignore[no-untyped-def]
        if event.get("channel_type") != "im" or event.get("bot_id"):
            return
        _answer(event=event, say=say, client=client, tool=tool, slack_sessions=slack_sessions)

    return app


def run_socket_mode(config: Config, app: App) -> None:
    SocketModeHandler(app, config.slack_app_token).start()


def _answer(
    *,
    event: dict,
    say,
    client,
    tool: AnalyticsMCPTool,
    slack_sessions: dict[str, str],
) -> None:
    text = str(event.get("text", ""))
    question = extract_question(text)
    if not question:
        say("Ask me a question about the EDP Gold data.")
        return

    slack_thread_key = _thread_key(event)
    session_id = slack_sessions.get(slack_thread_key)
    logger.info("Answering Slack question for thread %s", slack_thread_key)

    try:
        result = tool.ask_data_question(question=question, session_id=session_id)
    except AnalyticsAgentError as exc:
        logger.error("Analytics request failed: %s", exc)
        say(text=format_error(str(exc)), thread_ts=_reply_ts(event))
        return

    if result.session_id:
        slack_sessions[slack_thread_key] = result.session_id

    thread_ts = _reply_ts(event)
    say(text=format_answer(result), thread_ts=thread_ts)
    _upload_pdf_report(client, event, thread_ts, tool, question, result)


def _thread_key(event: dict) -> str:
    channel = str(event.get("channel", "unknown"))
    thread_ts = str(event.get("thread_ts") or event.get("ts") or "unknown")
    return f"{channel}:{thread_ts}"


def _reply_ts(event: dict) -> str | None:
    return event.get("thread_ts") or event.get("ts")


def _upload_pdf_report(
    client,
    event: dict,
    thread_ts: str | None,
    tool: AnalyticsMCPTool,
    question: str,
    result: AnalyticsResult,
) -> None:
    if not result.insight:
        return
    try:
        filename, pdf_bytes = tool.build_pdf_report(question=question, result=result)
        client.files_upload_v2(
            channel=event.get("channel"),
            thread_ts=thread_ts,
            filename=filename,
            title="EDP Analytics Report",
            file=pdf_bytes,
            initial_comment="PDF report attached.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF upload failed: %s", exc)


def _channel_name(client, channel_id: str) -> str | None:  # type: ignore[no-untyped-def]
    if not channel_id:
        return None
    try:
        response = client.conversations_info(channel=channel_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not resolve Slack channel name for %s: %s", channel_id, exc)
        return None
    channel = response.get("channel") or {}
    return channel.get("name")
