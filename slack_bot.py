"""Slack bot that interfaces with Gemini."""

import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

import gemini_AI


def require_env_var(name: str) -> str:
    """Return the value of an environment variable or raise an error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


SLACK_BOT_TOKEN = require_env_var("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = require_env_var("SLACK_SIGNING_SECRET")

slack_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = SlackRequestHandler(slack_app)


@slack_app.event("app_mention")
def handle_app_mention(body, say, ack):
    """Respond when the bot is mentioned in a channel."""
    ack()
    event = body.get("event", {})
    channel_id = event.get("channel")
    text = event.get("text", "")
    response = gemini_AI.send_message(channel_id, text)
    say(response)


@slack_app.event("message")
def handle_message_events(body, say, ack):
    """Handle direct messages to the bot."""
    ack()
    event = body.get("event", {})
    if event.get("channel_type") == "im" and "bot_id" not in event:
        channel_id = event.get("channel")
        text = event.get("text", "")
        response = gemini_AI.send_message(channel_id, text)
        say(response)

