from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class DriftModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def create_monitor(self, name: str, suite_id: str, cadence: Optional[str] = None, min_recovery_r10: Optional[float] = None):
        payload = {"name": name, "suite_id": suite_id}
        if cadence is not None:
            payload["cadence"] = cadence
        if min_recovery_r10 is not None:
            payload["min_recovery_r10"] = min_recovery_r10
        return self._http.post("/drift-monitors", data=payload)

    def list_monitors(self):
        return self._http.get("/drift-monitors")

    def get_monitor(self, monitor_id: str):
        return self._http.get(f"/drift-monitors/{monitor_id}")

    def list_runs(self, monitor_id: str):
        return self._http.get(f"/drift-monitors/{monitor_id}/runs")

    def get_run(self, drift_run_id: str):
        return self._http.get(f"/drift-runs/{drift_run_id}")

    def due(self):
        return self._http.get("/drift-monitor-due")
