"""ChatModule HTTP shape + error propagation."""

from __future__ import annotations

import pytest

from schift.chat import ChatModule, ChatResponse, ChatSource
from schift.client import SchiftError


class FakeHttp:
    """Mirrors test_query.py FakeHttp; adds a `next_response` slot so a
    test can shape what /chat returns."""

    def __init__(self, response: dict | None = None, raise_exc: Exception | None = None):
        self.calls: list[tuple] = []
        self.next_response = response or {"reply": "", "sources": [], "model": ""}
        self.raise_exc = raise_exc

    def post(self, path, data=None):
        self.calls.append(("post", path, data))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response

    def get(self, path, params=None):  # pragma: no cover - chat doesn't GET
        self.calls.append(("get", path, params))
        return []


# ── Happy path ───────────────────────────────────────────────────────


def test_chat_posts_to_chat_with_expected_body_shape():
    http = FakeHttp(
        response={
            "reply": "to reset, click here",
            "sources": [{"id": "doc-1", "score": 0.9, "text": "snippet"}],
            "model": "gemini-2.5-flash-lite",
        }
    )
    chat = ChatModule(http)

    result = chat(
        "how do I reset my password?",
        bucket="my-docs",
        top_k=3,
        model="gemini-2.5-flash-lite",
        system_prompt="be concise",
        temperature=0.1,
        max_tokens=256,
    )

    assert isinstance(result, ChatResponse)
    assert result.reply == "to reset, click here"
    assert result.model == "gemini-2.5-flash-lite"
    assert result.sources == [ChatSource(id="doc-1", score=0.9, text="snippet")]

    assert http.calls == [
        (
            "post",
            "/chat",
            {
                "bucket_id": "my-docs",
                "message": "how do I reset my password?",
                "stream": False,
                "top_k": 3,
                "model": "gemini-2.5-flash-lite",
                "system_prompt": "be concise",
                "temperature": 0.1,
                "max_tokens": 256,
            },
        )
    ]


def test_chat_omits_optional_fields_when_unset():
    """The wire body must NOT carry temperature/max_tokens/etc when the
    caller didn't pass them — keeps server defaults canonical."""
    http = FakeHttp(response={"reply": "ok", "sources": [], "model": ""})
    chat = ChatModule(http)

    chat("hello", bucket="docs")

    body = http.calls[0][2]
    assert body == {
        "bucket_id": "docs",
        "message": "hello",
        "stream": False,
        "top_k": 7,
    }


# ── Error mapping ────────────────────────────────────────────────────


def test_chat_propagates_typed_error_from_http_layer():
    http = FakeHttp(raise_exc=SchiftError("API error 500: oops"))
    chat = ChatModule(http)

    with pytest.raises(SchiftError, match="500"):
        chat("hello", bucket="docs")
