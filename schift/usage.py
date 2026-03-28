"""Usage module — track API consumption and billing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from schift._http import HttpClient


def _normalize_usage_response(raw: dict) -> dict:
    """Normalize the server response to the documented SDK usage contract.

    The server returns:
      { org_id, period_start, period_end,
        summary: { total_vectors, total_requests, by_action: [{action, vectors, requests}] },
        records: [...] }

    The SDK contract (SDK_ARCHITECTURE.md) is:
      { embed_calls, query_calls, rerank_calls, storage_gb, egress_gb, estimated_cost_usd }

    Query actions include both "query" and "search" action labels.
    storage_gb and egress_gb are not yet tracked server-side; they default to 0.
    estimated_cost_usd is not yet exposed in this endpoint; it defaults to 0.
    """
    by_action: list[dict] = (raw.get("summary") or {}).get("by_action") or []

    call_map: dict[str, int] = {}
    for entry in by_action:
        action = entry.get("action") or ""
        call_map[action] = int(entry.get("requests") or 0)

    embed_calls = call_map.get("embed", 0)
    query_calls = call_map.get("query", 0) + call_map.get("search", 0)
    rerank_calls = call_map.get("rerank", 0)

    return {
        "embed_calls": embed_calls,
        "query_calls": query_calls,
        "rerank_calls": rerank_calls,
        "storage_gb": 0.0,
        "egress_gb": 0.0,
        "estimated_cost_usd": 0.0,
        # Pass through period metadata so callers can inspect the window.
        "period_start": raw.get("period_start"),
        "period_end": raw.get("period_end"),
    }


class UsageModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def get(self, period: str = "30d", granularity: Optional[str] = None) -> dict:
        """Return usage aggregates for the authenticated org.

        Returns a dict with the following keys (SDK contract):
            embed_calls (int): number of embedding calls in the period
            query_calls (int): number of query/search calls in the period
            rerank_calls (int): number of rerank calls in the period
            storage_gb (float): average storage in GB (0.0 until server tracks it)
            egress_gb (float): egress in GB (0.0 until server tracks it)
            estimated_cost_usd (float): estimated cost (0.0 until server exposes it)
            period_start (str): ISO-8601 start of the period
            period_end (str): ISO-8601 end of the period
        """
        params: dict = {"period": period}
        if granularity is not None:
            params["granularity"] = granularity
        raw = self._http.get("/usage/me", params=params)
        return _normalize_usage_response(raw)
