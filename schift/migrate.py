"""Schift migration engine — Source → Projection → Sink."""

from __future__ import annotations

from typing import Callable, Optional

from schift.adapters.base import Adapter
from schift.projection import Projection


def migrate(
    source: Adapter,
    sink: Adapter,
    projection: Projection,
    batch_size: int = 1000,
    dry_run: bool = False,
    on_batch: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """Migrate embeddings from source to sink via projection.

    Args:
        source: Read adapter (pgvector, qdrant, npy, ...).
        sink: Write adapter (can be same or different store).
        projection: Schift Projection from client.fit().
        batch_size: Vectors per batch.
        dry_run: Transform without writing.
        on_batch: Callback(migrated_so_far, total) for progress.

    Returns:
        Migration summary.

    Example:
        from schift.adapters.pgvector import PgVectorAdapter
        from schift.adapters.qdrant import QdrantAdapter

        source = PgVectorAdapter(conninfo="...", table="docs")
        sink = QdrantAdapter(url="...", collection="docs_v2")

        result = migrate(source, sink, projection)
    """
    total = source.count()

    if not dry_run:
        sink.prepare_target(projection.target_dim)

    migrated = 0

    for batch in source.read_batches(batch_size=batch_size):
        # Transform
        batch.embeddings = projection.transform(batch.embeddings)

        # Write
        if not dry_run:
            sink.write_batch(batch)

        migrated += len(batch)

        if on_batch:
            on_batch(migrated, total)

    return {
        "source": source.adapter_name,
        "sink": sink.adapter_name,
        "total": total,
        "migrated": migrated,
        "source_dim": projection.source_dim,
        "target_dim": projection.target_dim,
        "dry_run": dry_run,
    }
