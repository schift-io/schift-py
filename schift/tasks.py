from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class TasksModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def similarity(self, text_a: str, text_b: str, model: Optional[str] = None):
        payload = {"text_a": text_a, "text_b": text_b}
        if model is not None:
            payload["model"] = model
        return self._http.post("/similarity", data=payload)

    def cluster(self, texts: list, n_clusters: int = 5, model: Optional[str] = None):
        payload = {"texts": texts, "n_clusters": n_clusters}
        if model is not None:
            payload["model"] = model
        return self._http.post("/cluster", data=payload)

    def classify(
        self,
        text: str,
        labels: list,
        model: Optional[str] = None,
        temperature: float = 1.0,
        examples: Optional[list] = None,
    ):
        payload = {"text": text, "labels": labels}
        if model is not None:
            payload["model"] = model
        if temperature != 1.0:
            payload["temperature"] = temperature
        if examples:
            payload["examples"] = [
                {"text": ex["text"], "label": ex["label"]} for ex in examples
            ]
        return self._http.post("/classify", data=payload)
