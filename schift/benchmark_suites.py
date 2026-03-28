from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class BenchmarkSuitesModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, name: str, source_model: str, target_model: str, sample_ratios: Optional[dict] = None, **kwargs):
        payload = {"name": name, "source_model": source_model, "target_model": target_model}
        if sample_ratios is not None:
            payload["sample_ratios"] = sample_ratios
        payload.update(kwargs)
        return self._http.post("/benchmark-suites", data=payload)

    def list(self):
        return self._http.get("/benchmark-suites")

    def get(self, suite_id: str):
        return self._http.get(f"/benchmark-suites/{suite_id}")

    def list_runs(self, suite_id: str):
        return self._http.get(f"/benchmark-suites/{suite_id}/runs")

    def get_run(self, run_id: str):
        return self._http.get(f"/benchmark-runs/{run_id}")
