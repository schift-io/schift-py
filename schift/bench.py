"""Bench module — run server-side benchmarks comparing embedding models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from schift.client import BenchReport

if TYPE_CHECKING:
    from schift._http import HttpClient


class BenchModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def run(
        self,
        source: str,
        target: str,
        data: Optional[str] = None,
    ) -> BenchReport:
        """Run a benchmark comparing two models.

        Args:
            source: Source model identifier (e.g., "openai/text-embedding-3-small").
            target: Target model identifier (e.g., "google/gemini-embedding-001").
            data: Optional dataset name or path for benchmark data.
        """
        payload: dict = {"source": source, "target": target}
        if data is not None:
            payload["data"] = data
        resp = self._http.post("/bench", payload)
        return BenchReport(resp)
