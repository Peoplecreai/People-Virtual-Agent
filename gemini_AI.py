from __future__ import annotations

"""Utilities for interacting with the Gemini API."""

import os
from typing import Dict

from google import genai


_client: genai.Client | None = None
_chats: Dict[str, genai.Chat] = {}


def _require_client() -> genai.Client:
    """Return a singleton genai.Client instance."""
    global _client
    if _client is None:
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("Environment variable GEMINI_API_KEY is required")
        # The client automatically picks up GEMINI_API_KEY from the environment.
        _client = genai.Client()
    return _client


def _get_chat(channel_id: str) -> genai.Chat:
    """Return a chat session for the given channel."""
    if channel_id not in _chats:
        client = _require_client()
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        _chats[channel_id] = client.chats.create(model=model_name)
    return _chats[channel_id]


def send_message(channel_id: str, message: str) -> str:
    """Send a message to Gemini and return the response text."""
    chat = _get_chat(channel_id)
    response = chat.send_message(message)
    return response.text
