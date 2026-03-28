from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class JobsModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def get(self, job_id: str):
        return self._http.get(f"/jobs/{job_id}")

    def list(self, org_id: Optional[str] = None, bucket_id: Optional[str] = None, status: Optional[str] = None, limit: Optional[int] = None):
        params = {}
        if org_id is not None:
            params["org_id"] = org_id
        if bucket_id is not None:
            params["bucket_id"] = bucket_id
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        return self._http.get("/jobs", params=params)

    def cancel(self, job_id: str):
        return self._http.post(f"/jobs/{job_id}/cancel")

    def reprocess(self, job_id: str):
        return self._http.post(f"/jobs/{job_id}/reprocess")
