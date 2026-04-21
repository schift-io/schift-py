"""MigrateModule — wraps the existing migrate() function as a Schift module."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np
from numpy.typing import NDArray

from schift.adapters.base import Adapter
from schift.migrate import migrate as _migrate
from schift.projection import Projection

if TYPE_CHECKING:
    from schift._http import HttpClient


def _ndarray_to_bytes(arr: NDArray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


def _bytes_to_ndarray(data: bytes | str) -> NDArray:
    import base64
    if isinstance(data, str):
        data = base64.b64decode(data)
    return np.load(io.BytesIO(data))


class MigrateModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def run(
        self,
        source: Adapter,
        sink: Adapter,
        projection: Projection,
        batch_size: int = 1000,
        dry_run: bool = False,
        on_batch: Optional[Callable[[int, int], None]] = None,
    ) -> dict:
        """Migrate embeddings from source to sink via projection.

        Delegates to schift.migrate.migrate() — see its docstring for details.
        """
        return _migrate(
            source=source,
            sink=sink,
            projection=projection,
            batch_size=batch_size,
            dry_run=dry_run,
            on_batch=on_batch,
        )

    # ---- Projection methods ----

    def fit(
        self,
        source: NDArray,
        target: NDArray,
        source_model: str = "unknown",
        target_model: str = "unknown",
        project_name: Optional[str] = None,
    ) -> Projection:
        """Learn a projection from source model space to target model space.

        Sends paired sample embeddings to the Schift API, which learns the
        optimal projection matrix and returns it for local use.

        Args:
            source: Sample embeddings from the source model, shape (n, d_source).
            target: Sample embeddings from the target model, shape (n, d_target).
                    Must be the SAME texts embedded by both models.
            source_model: Source model identifier (e.g., "openai/text-embedding-3-small").
            target_model: Target model identifier (e.g., "google/gemini-embedding-001").
            project_name: Optional label for organizing projections.

        Returns:
            Projection object. Use .transform() to convert embeddings locally.

        Raises:
            ValueError: If arrays have incompatible shapes or too few samples.
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

        payload: dict = {
            "source_model": source_model,
            "target_model": target_model,
            "source_dim": source.shape[1],
            "target_dim": target.shape[1],
            "n_samples": source.shape[0],
        }
        if project_name:
            payload["project_name"] = project_name

        resp = self._http._post_form_with_files(
            "/projections",
            form_data={"payload": json.dumps(payload)},
            files=[
                ("source", ("data.npy", _ndarray_to_bytes(source), "application/octet-stream")),
                ("target", ("data.npy", _ndarray_to_bytes(target), "application/octet-stream")),
            ],
        )

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

    def list_projections(self) -> list[dict]:
        """List all saved projections for this account.

        Returns:
            List of projection summary dicts, each containing project_id,
            source_model, target_model, source_dim, target_dim, created_at.
        """
        return self._http.get("/projections")

    def get_projection(self, projection_id: str) -> Projection:
        """Download a previously created projection by ID.

        Args:
            projection_id: Projection ID (e.g. "proj_abc123").

        Returns:
            Projection object ready for local transform() calls.
        """
        resp = self._http.get(f"/projections/{projection_id}")
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

    # ---- Benchmark methods ----

    def bench(
        self,
        source: str,
        target: str,
        data: Optional[str] = None,
    ) -> dict:
        """Run a single benchmark comparing two models.

        Delegates to the BenchModule. Use create_benchmark_suite() +
        run_benchmark_suite() for tracked, repeatable benchmarks.

        Args:
            source: Source model identifier (e.g., "openai/text-embedding-3-small").
            target: Target model identifier (e.g., "google/gemini-embedding-001").
            data: Optional dataset name or path for benchmark data.

        Returns:
            BenchReport dict with verdict, original and projected metrics.
        """
        from schift.bench import BenchModule
        return BenchModule(self._http).run(source=source, target=target, data=data)

    def create_benchmark_suite(
        self,
        name: str,
        source_model: str,
        target_model: str,
        sample_ratios: Optional[list[float]] = None,
        query_count: Optional[int] = None,
        bucket_document_count: Optional[int] = None,
        bucket_document_ids: Optional[list[str]] = None,
        query_ids: Optional[list[str]] = None,
        qrels: Optional[dict[str, list[str]]] = None,
        artifact_refs: Optional[dict[str, str]] = None,
    ) -> dict:
        """Create a benchmark suite for tracked evaluation.

        A benchmark suite defines the configuration (models, sample ratios,
        optional data) for repeatable benchmark runs.

        Args:
            name: Human-readable name for this suite.
            source_model: Source model identifier.
            target_model: Target model identifier.
            sample_ratios: Ratios of bucket documents to use as projection training samples.
                           Defaults to [0.02, 0.05, 0.1, 0.2].
            query_count: Number of query vectors (auto-derived from query_ids if given).
            bucket_document_count: Number of bucket vectors (auto-derived from bucket_document_ids if given).
            bucket_document_ids: Optional list of bucket document IDs.
            query_ids: Optional list of query IDs.
            qrels: Relevance judgments {query_id: [relevant_bucket_document_ids]}.
            artifact_refs: Optional artifact references for server-stored data.

        Returns:
            Suite dict with suite_id and all config fields.
        """
        payload: dict = {
            "name": name,
            "source_model": source_model,
            "target_model": target_model,
            "sample_ratios": sample_ratios or [0.02, 0.05, 0.1, 0.2],
        }
        if query_count is not None:
            payload["query_count"] = query_count
        if bucket_document_count is not None:
            payload["bucket_document_count"] = bucket_document_count
        if bucket_document_ids is not None:
            payload["bucket_document_ids"] = bucket_document_ids
        if query_ids is not None:
            payload["query_ids"] = query_ids
        if qrels is not None:
            payload["qrels"] = qrels
        if artifact_refs is not None:
            payload["artifact_refs"] = artifact_refs

        return self._http.post("/benchmark-suites", payload)

    def list_benchmark_suites(self) -> list[dict]:
        """List all benchmark suites for this account.

        Returns:
            List of suite summary dicts, each containing suite_id, name,
            source_model, target_model, created_at.
        """
        return self._http.get("/benchmark-suites")

    def get_benchmark_suite(self, suite_id: str) -> dict:
        """Get a benchmark suite by ID.

        Args:
            suite_id: Suite ID (e.g. "suite_abc123").

        Returns:
            Full suite config dict including suite_id and all config fields.
        """
        return self._http.get(f"/benchmark-suites/{suite_id}")

    def run_benchmark_suite(
        self,
        suite_id: str,
        bucket_source: NDArray,
        bucket_target: NDArray,
        query_source: NDArray,
        query_target: NDArray,
        params: Optional[dict] = None,
    ) -> dict:
        """Run a benchmark suite and record the results.

        Uploads embedding matrices to the server, which runs the full
        benchmark evaluation and stores the run for later retrieval.

        Args:
            suite_id: Suite ID to run (e.g. "suite_abc123").
            bucket_source: Bucket embeddings from source model, shape (n, d_source).
            bucket_target: Bucket embeddings from target model, shape (n, d_target).
            query_source: Query embeddings from source model.
            query_target: Query embeddings from target model.
            params: Optional override parameters (merged with suite config on server).

        Returns:
            Run result dict with run_id, suite_id, status, and report.
        """
        bucket_source = np.asarray(bucket_source, dtype=np.float32)
        bucket_target = np.asarray(bucket_target, dtype=np.float32)
        query_source = np.asarray(query_source, dtype=np.float32)
        query_target = np.asarray(query_target, dtype=np.float32)

        form_data: dict[str, str] = {}
        if params is not None:
            form_data["payload"] = json.dumps(params)

        return self._http._post_form_with_files(
            f"/benchmark-suites/{suite_id}/runs",
            form_data=form_data,
            files=[
                ("bucket_source", ("data.npy", _ndarray_to_bytes(bucket_source), "application/octet-stream")),
                ("bucket_target", ("data.npy", _ndarray_to_bytes(bucket_target), "application/octet-stream")),
                ("query_source", ("data.npy", _ndarray_to_bytes(query_source), "application/octet-stream")),
                ("query_target", ("data.npy", _ndarray_to_bytes(query_target), "application/octet-stream")),
            ],
        )

    def list_benchmark_runs(self, suite_id: str) -> list[dict]:
        """List all benchmark runs for a suite.

        Args:
            suite_id: Suite ID whose runs to list.

        Returns:
            List of run dicts, each containing run_id, suite_id, status,
            created_at, and report.
        """
        return self._http.get(f"/benchmark-suites/{suite_id}/runs")

    def get_benchmark_run(self, run_id: str) -> dict:
        """Get a benchmark run by ID.

        Args:
            run_id: Run ID (e.g. "run_abc123").

        Returns:
            Run dict with run_id, suite_id, status, created_at, and report.
        """
        return self._http.get(f"/benchmark-runs/{run_id}")
