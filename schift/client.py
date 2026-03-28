"""Schift client — embedding vendor lock-in liberation.

.. deprecated::
    Use :class:`schift.Schift` instead. This module is kept for backwards
    compatibility only and will be removed in a future release.
"""

from __future__ import annotations

import io
import json
import warnings
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from schift.projection import Projection

_DEFAULT_BASE_URL = "https://api.schift.io"


class Client:
    """Schift API client for embedding model migration.

    Usage:
        client = Client(api_key="sch_xxx")
        proj = client.fit(
            source=old_embeddings,
            target=new_embeddings,
            source_model="openai/text-embedding-3-small",
            target_model="google/gemini-embedding-001",
        )
        converted = proj.transform(all_old_embeddings)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ):
        warnings.warn(
            "schift.Client is deprecated. Use schift.Schift instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if not api_key or not api_key.startswith("sch_"):
            raise ValueError("Invalid API key. Keys start with 'sch_'")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fit(
        self,
        source: NDArray,
        target: NDArray,
        source_model: str = "unknown",
        target_model: str = "unknown",
        project_name: Optional[str] = None,
    ) -> Projection:
        """Learn a projection from source model space to target model space.

        Sends sample embeddings to Schift API, which learns the optimal
        projection matrix and returns it for local use.

        Args:
            source: Sample embeddings from old/source model, shape (n, d_source).
            target: Sample embeddings from new/target model, shape (n, d_target).
                    Must be the SAME texts embedded by both models.
            source_model: Source model identifier (e.g., "openai/text-embedding-3-small").
            target_model: Target model identifier (e.g., "google/gemini-embedding-001").
            project_name: Optional project name for organizing projections.

        Returns:
            Projection object. Use .transform() to convert embeddings locally.
        """
        source = np.asarray(source, dtype=np.float32)
        target = np.asarray(target, dtype=np.float32)

        if source.shape[0] != target.shape[0]:
            raise ValueError(
                f"source and target must have same number of samples: "
                f"{source.shape[0]} vs {target.shape[0]}"
            )
        if source.shape[0] < 10:
            raise ValueError(
                f"Need at least 10 sample pairs, got {source.shape[0]}. "
                f"Recommended: 5-20% of your corpus."
            )

        # Prepare request
        payload = {
            "source_model": source_model,
            "target_model": target_model,
            "source_dim": source.shape[1],
            "target_dim": target.shape[1],
            "n_samples": source.shape[0],
        }
        if project_name:
            payload["project_name"] = project_name

        # Send to API
        resp = self._post("/v1/projections", payload, files={
            "source": _ndarray_to_bytes(source),
            "target": _ndarray_to_bytes(target),
        })

        # Parse response
        W = _bytes_to_ndarray(resp["matrix"])
        return Projection(
            W=W,
            project_id=resp["project_id"],
            source_model=source_model,
            target_model=target_model,
            source_dim=source.shape[1],
            target_dim=target.shape[1],
            method=resp["method"],
            n_samples=source.shape[0],
            quality=resp["quality"],
        )

    def bench(
        self,
        source: NDArray,
        target: NDArray,
        queries_source: NDArray,
        queries_target: NDArray,
        corpus_ids: list[str],
        query_ids: list[str],
        qrels: dict[str, list[str]],
        source_model: str = "unknown",
        target_model: str = "unknown",
        sample_ratios: Optional[list[float]] = None,
    ) -> "BenchReport":
        """Run a paid benchmark: evaluate projection quality on YOUR data.

        Tests multiple sample ratios and methods, returns detailed quality
        report with SAFE/WARN/FAIL recommendation.

        Args:
            source: Corpus embeddings from old model, shape (n, d_source).
            target: Corpus embeddings from new model, shape (n, d_target).
            queries_source: Query embeddings from old model.
            queries_target: Query embeddings from new model.
            corpus_ids: Corpus document IDs.
            query_ids: Query IDs.
            qrels: Relevance judgments {query_id: [relevant_corpus_ids]}.
            source_model: Source model name.
            target_model: Target model name.
            sample_ratios: Ratios to test (default: [0.02, 0.05, 0.1, 0.2]).

        Returns:
            BenchReport with metrics, recommended config, and verdict.
        """
        source = np.asarray(source, dtype=np.float32)
        target = np.asarray(target, dtype=np.float32)
        queries_source = np.asarray(queries_source, dtype=np.float32)
        queries_target = np.asarray(queries_target, dtype=np.float32)

        # Serialize qrels as {qid: [cid, ...]} for JSON
        qrels_json = {k: list(v) if isinstance(v, set) else v for k, v in qrels.items()}

        payload = {
            "source_model": source_model,
            "target_model": target_model,
            "source_dim": source.shape[1],
            "target_dim": target.shape[1],
            "n_corpus": len(corpus_ids),
            "n_queries": len(query_ids),
            "corpus_ids": corpus_ids,
            "query_ids": query_ids,
            "qrels": qrels_json,
            "sample_ratios": sample_ratios or [0.02, 0.05, 0.1, 0.2],
        }

        resp = self._post("/v1/bench", payload, files={
            "corpus_source": _ndarray_to_bytes(source),
            "corpus_target": _ndarray_to_bytes(target),
            "queries_source": _ndarray_to_bytes(queries_source),
            "queries_target": _ndarray_to_bytes(queries_target),
        })

        return BenchReport(resp)

    def list_projections(self) -> list[dict]:
        """List all saved projections for this account."""
        return self._get("/v1/projections")

    def get_projection(self, project_id: str) -> Projection:
        """Download a previously created projection by ID."""
        resp = self._get(f"/v1/projections/{project_id}")
        W = _bytes_to_ndarray(resp["matrix"])
        return Projection(
            W=W,
            project_id=resp["project_id"],
            source_model=resp["source_model"],
            target_model=resp["target_model"],
            source_dim=resp["source_dim"],
            target_dim=resp["target_dim"],
            method=resp["method"],
            n_samples=resp["n_samples"],
            quality=resp["quality"],
        )

    # ---- HTTP layer ----

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": f"schift-python/0.1.0",
        }

    def _post(self, path: str, data: dict, files: Optional[dict] = None) -> dict:
        import httpx

        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self._timeout) as http:
            if files:
                resp = http.post(
                    url,
                    headers=self._headers(),
                    data={"payload": json.dumps(data)},
                    files={k: ("data.npy", v, "application/octet-stream") for k, v in files.items()},
                )
            else:
                resp = http.post(url, headers=self._headers(), json=data)

            if resp.status_code == 401:
                raise AuthError("Invalid API key")
            if resp.status_code == 402:
                raise QuotaError(resp.json().get("detail", "Quota exceeded"))
            if resp.status_code >= 400:
                raise SchiftError(f"API error {resp.status_code}: {resp.text}")
            return resp.json()

    def _get(self, path: str) -> dict:
        import httpx

        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self._timeout) as http:
            resp = http.get(url, headers=self._headers())
            if resp.status_code == 401:
                raise AuthError("Invalid API key")
            if resp.status_code >= 400:
                raise SchiftError(f"API error {resp.status_code}: {resp.text}")
            return resp.json()


# ---- Errors ----

class BenchReport:
    """Benchmark results — shows exactly how well projection works on YOUR data."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def verdict(self) -> str:
        """SAFE / WARN / FAIL — overall recommendation."""
        return self._data["verdict"]

    @property
    def original(self) -> dict:
        """Baseline metrics using the original source model (before projection)."""
        return self._data["original"]

    @property
    def projected(self) -> dict:
        """Metrics after applying the best projection found."""
        return self._data["projected"]

    @property
    def source_model(self) -> str:
        """Source embedding model identifier."""
        return self._data.get("source_model", "unknown")

    @property
    def target_model(self) -> str:
        """Target embedding model identifier."""
        return self._data.get("target_model", "unknown")

    @property
    def n_corpus(self) -> int:
        """Number of corpus documents used in the benchmark."""
        return self._data.get("n_corpus", 0)

    @property
    def n_queries(self) -> int:
        """Number of queries used in the benchmark."""
        return self._data.get("n_queries", 0)

    def summary(self) -> str:
        """Human-readable summary."""
        v = self.verdict
        orig_r10 = self.original.get("R@10", 0)
        proj_r10 = self.projected.get("R@10", 0)
        return (
            f"[{v}] {self.source_model} -> {self.target_model}\n"
            f"  Original R@10:  {orig_r10:.4f}\n"
            f"  Projected R@10: {proj_r10:.4f}\n"
            f"  Corpus: {self.n_corpus:,} docs, {self.n_queries:,} queries\n"
            f"  Verdict: {v}"
        )

    def __repr__(self) -> str:
        return f"BenchReport(verdict={self.verdict!r}, projected_R@10={self.projected.get('R@10', '?')})"


class SchiftError(Exception):
    pass

class AuthError(SchiftError):
    pass

class QuotaError(SchiftError):
    pass


# ---- Serialization ----

def _ndarray_to_bytes(arr: NDArray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


def _bytes_to_ndarray(data: bytes | str) -> NDArray:
    import base64
    if isinstance(data, str):
        data = base64.b64decode(data)
    return np.load(io.BytesIO(data))
