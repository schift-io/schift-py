from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class AggregateModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def __call__(self, collection: str, group_by: str, filter_key: Optional[str] = None, filter_value: Optional[str] = None):
        payload = {"collection": collection, "group_by": group_by}
        if filter_key is not None:
            payload["filter_key"] = filter_key
        if filter_value is not None:
            payload["filter_value"] = filter_value
        return self._http.post("/aggregate", data=payload)
