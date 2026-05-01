"""Slack Socket Mode app for the EDP analytics gateway."""

from __future__ import annotations

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from gateway.analytics import AnalyticsAgentError, AnalyticsMCPTool, AnalyticsResult
from gateway.config import Config  # noqa: F401 — used in type hints below
from gateway.formatting import allowed_channel, extract_question, format_answer, format_footer, format_error

logger = logging.getLogger(__name__)


def build_app(config: Config, tool: AnalyticsMCPTool) -> App:
    app = App(token=config.slack_bot_token)
    # thread_key (channel:thread_ts) -> session_id
    slack_sessions: dict[str, str] = {}
    # channel_id -> most recent session_id (fallback for new channel messages)
    channel_sessions: dict[str, str] = {}

    @app.event("app_mention")
    def handle_app_mention(event: dict, say, client) -> None:  # type: ignore[no-untyped-def]
        channel_id = event.get("channel", "")
        channel_name = _channel_name(client, channel_id)
        if not allowed_channel(channel_name, config.allowed_channels):
            logger.info("Ignoring message from channel %s", channel_name or channel_id)
            return
        _answer(
            event=event,
            say=say,
            client=client,
            tool=tool,
            config=config,
            slack_sessions=slack_sessions,
            channel_sessions=channel_sessions,
        )

    @app.event("message")
    def handle_direct_message(event: dict, say, client) -> None:  # type: ignore[no-untyped-def]
        if event.get("channel_type") != "im" or event.get("bot_id"):
            return
        _answer(
            event=event,
            say=say,
            client=client,
            tool=tool,
            config=config,
            slack_sessions=slack_sessions,
            channel_sessions=channel_sessions,
        )

    return app


def run_socket_mode(config: Config, app: App) -> None:
    SocketModeHandler(app, config.slack_app_token).start()


def _answer(
    *,
    event: dict,
    say,
    client,
    tool: AnalyticsMCPTool,
    config: Config,
    slack_sessions: dict[str, str],
    channel_sessions: dict[str, str],
) -> None:
    text = str(event.get("text", ""))
    question = extract_question(text)
    if not question:
        say("Ask me a question about the EDP Gold data.")
        return

    channel_id = str(event.get("channel", ""))
    slack_thread_key = _thread_key(event)

    # Prefer thread-level session, fall back to the channel's most recent session
    # so follow-up questions sent as new channel messages still carry context.
    session_id = slack_sessions.get(slack_thread_key) or channel_sessions.get(channel_id)
    logger.info(
        "Answering Slack question for thread %s (session=%s)",
        slack_thread_key,
        session_id or "new",
    )

    try:
        result = tool.ask_data_question(question=question, session_id=session_id)
    except AnalyticsAgentError as exc:
        logger.error("Analytics request failed: %s", exc)
        say(text=format_error(str(exc)), thread_ts=_reply_ts(event))
        return

    if result.session_id:
        slack_sessions[slack_thread_key] = result.session_id
        channel_sessions[channel_id] = result.session_id

    formatted = format_answer(result, streamlit_url=config.streamlit_url)
    thread_ts = _reply_ts(event)

    # Upload PDF with the formatted answer as initial_comment so the insight
    # and the report appear as a single unit. Fall back to a plain text reply
    # if the PDF cannot be built or uploaded.
    uploaded = _upload_pdf_report(client, event, thread_ts, tool, question, result, formatted)
    if not uploaded:
        say(text=formatted, thread_ts=thread_ts)

    # Cost + assumptions post as a separate thread reply so they appear after the PDF.
    say(text=format_footer(result), thread_ts=thread_ts)


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
    initial_comment: str,
) -> bool:
    """Upload the PDF report with the formatted answer as the message text.

    Returns True on success, False on any failure so the caller can fall back
    to a plain text reply.
    """
    if not result.insight:
        return False
    try:
        filename, pdf_bytes = tool.build_pdf_report(question=question, result=result)
        client.files_upload_v2(
            channel=event.get("channel"),
            thread_ts=thread_ts,
            filename=filename,
            title="EDP Analytics Report",
            file=pdf_bytes,
            initial_comment=initial_comment,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF upload failed: %s", exc)
        return False


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
