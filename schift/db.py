"""DB module — manage Schift-hosted vector collections."""

from __future__ import annotations

import mimetypes
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schift._http import HttpClient


class DBModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def create_collection(self, name: str, dimension: int) -> dict:
        return self._http.post("/collections", {"name": name, "dimension": dimension})

    def list_collections(self) -> list[dict]:
        return self._http.get("/collections")

    def collection_stats(self, name: str) -> dict:
        return self._http.get(f"/collections/{name}/stats")

    def get_collection(self, name: str) -> dict:
        return self._http.get(f"/collections/{name}")

    def delete_collection(self, name: str) -> None:
        self._http.delete(f"/collections/{name}")

    def delete(self, collection: str, ids: list[str]) -> dict:
        """Delete vectors by ID from a collection.

        Args:
            collection: Collection name.
            ids:        List of vector IDs to delete.

        Returns:
            dict with key ``deleted`` (count of deleted vectors).
        """
        return self._http.delete_json(
            f"/collections/{collection}/vectors", {"ids": ids}
        )

    def upsert(self, collection: str, vectors: list[dict]) -> dict:
        """Upsert pre-computed vectors.

        Each vector dict should contain at minimum {"id": ..., "values": [...]}.
        Optional keys: "metadata".
        """
        return self._http.post(f"/collections/{collection}/vectors", {"vectors": vectors})

    def upload(self, bucket: str, files: list[str]) -> dict:
        """Upload files to a bucket. Creates the bucket if it does not exist.

        Args:
            bucket: Bucket name to upload into.
            files:  List of local file paths to upload.

        Returns:
            dict with keys ``bucket_id``, ``bucket_name``, and ``uploaded``
            (a list of per-file result dicts returned by the server).

        Example::

            client.db.upload("my-docs", files=["manual.pdf", "faq.docx"])
        """
        # 1. Get or create bucket
        buckets = self._http.get("/buckets")
        existing = next((b for b in buckets if b.get("name") == bucket), None)
        if existing:
            bucket_id = existing["id"]
        else:
            result = self._http.post("/buckets", {"name": bucket})
            bucket_id = result["id"]

        # 2. Upload each file via multipart POST
        uploaded = []
        for path in files:
            filename = os.path.basename(path)
            mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            with open(path, "rb") as fh:
                file_bytes = fh.read()
            result = self._http.post_multipart(
                f"/buckets/{bucket_id}/upload",
                files=[("files", (filename, file_bytes, mime_type))],
            )
            uploaded.append(result)

        return {"bucket_id": bucket_id, "bucket_name": bucket, "uploaded": uploaded}

    def upsert_text(self, collection: str, documents: list[dict], model: str) -> dict:
        """Upsert raw text — Schift embeds it server-side.

        Each document dict should contain at minimum {"id": ..., "text": ...}.
        Optional keys: "metadata".
        """
        return self._http.post(
            f"/collections/{collection}/documents",
            {"documents": documents, "model": model},
        )
