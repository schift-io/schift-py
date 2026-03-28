from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class ArtifactsModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, kind: str, uri: str, checksum: Optional[str] = None, dims: Optional[int] = None, content_type: Optional[str] = None, label: Optional[str] = None):
        payload = {"kind": kind, "uri": uri}
        if checksum is not None:
            payload["checksum"] = checksum
        if dims is not None:
            payload["dims"] = dims
        if content_type is not None:
            payload["content_type"] = content_type
        if label is not None:
            payload["label"] = label
        return self._http.post("/artifacts", data=payload)

    def list(self, kind: Optional[str] = None):
        params = {}
        if kind is not None:
            params["kind"] = kind
        return self._http.get("/artifacts", params=params)

    def get(self, artifact_id: str):
        return self._http.get(f"/artifacts/{artifact_id}")
