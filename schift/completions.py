from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class CompletionsModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, model: str, messages: list, temperature: Optional[float] = None, max_tokens: Optional[int] = None, top_p: Optional[float] = None, stream: bool = False, stop=None):
        payload = {"model": model, "messages": messages, "stream": stream}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if top_p is not None:
            payload["top_p"] = top_p
        if stop is not None:
            payload["stop"] = stop
        return self._http.post("/chat/completions", data=payload)

    def models(self):
        return self._http.get("/models")
