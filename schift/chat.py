"""RAG Chat module — search + generate in one call."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterator, Optional

from schift._http import HttpClient


@dataclass
class ChatSource:
    id: str
    score: float
    text: str = ""


@dataclass
class ChatResponse:
    reply: str
    sources: list[ChatSource]
    model: str


@dataclass
class ChatStreamEvent:
    type: str  # "sources" | "chunk" | "done" | "error"
    sources: list[ChatSource] = field(default_factory=list)
    content: str = ""
    message: str = ""


class ChatModule:
    """RAG Chat — "Drop the Data, Connect, Voilà."

    Usage::

        from schift import Schift
        client = Schift()

        # Non-streaming
        result = client.chat("how do I reset my password?", bucket="my-docs")
        print(result.reply)
        print(result.sources)

        # Streaming
        for event in client.chat.stream("summarize Q4 report", bucket="my-docs"):
            if event.type == "sources":
                print(event.sources)
            elif event.type == "chunk":
                print(event.content, end="")
            elif event.type == "done":
                print()
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def __call__(
        self,
        message: str,
        bucket: str,
        *,
        history: Optional[list[dict]] = None,
        model: str = "openai/gpt-4o-mini",
        top_k: int = 5,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> ChatResponse:
        """Send a question, get an answer with sources. One call."""
        payload: dict = {
            "bucket_id": bucket,
            "message": message,
            "stream": False,
            "model": model,
            "top_k": top_k,
        }
        if history:
            payload["history"] = history
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = self._http.post("/chat", data=payload)
        return ChatResponse(
            reply=data["reply"],
            sources=[ChatSource(**s) for s in data.get("sources", [])],
            model=data.get("model", model),
        )

    def stream(
        self,
        message: str,
        bucket: str,
        *,
        history: Optional[list[dict]] = None,
        model: str = "openai/gpt-4o-mini",
        top_k: int = 5,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[ChatStreamEvent]:
        """Stream a RAG response via SSE."""
        payload: dict = {
            "bucket_id": bucket,
            "message": message,
            "stream": True,
            "model": model,
            "top_k": top_k,
        }
        if history:
            payload["history"] = history
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        with self._http.stream_post("/chat", data=payload) as resp:
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    raw = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = raw.get("type", "")
                if event_type == "sources":
                    yield ChatStreamEvent(
                        type="sources",
                        sources=[ChatSource(**s) for s in raw.get("sources", [])],
                    )
                elif event_type == "chunk":
                    yield ChatStreamEvent(type="chunk", content=raw.get("content", ""))
                elif event_type == "done":
                    yield ChatStreamEvent(type="done")
                elif event_type == "error":
                    yield ChatStreamEvent(type="error", message=raw.get("message", ""))
