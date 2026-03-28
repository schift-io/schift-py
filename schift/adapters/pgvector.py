"""pgvector adapter — read/write embeddings from PostgreSQL."""

from __future__ import annotations

from typing import Iterator

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class PgVectorAdapter(Adapter):
    """PostgreSQL + pgvector adapter.

    Usage:
        adapter = PgVectorAdapter(
            conninfo="postgresql://user:pass@localhost/mydb",
            table="documents",
        )
    """

    adapter_name = "pgvector"

    def __init__(
        self,
        conninfo: str,
        table: str,
        embedding_column: str = "embedding",
        id_column: str = "id",
    ):
        self._conninfo = conninfo
        self._table = table
        self._emb_col = embedding_column
        self._id_col = id_column

    def _connect(self):
        try:
            import psycopg
            from pgvector.psycopg import register_vector
        except ImportError:
            raise ImportError("pip install schift[postgres]")

        conn = psycopg.connect(self._conninfo)
        register_vector(conn)
        return conn

    def count(self) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                f"SELECT COUNT(*) FROM {self._table} WHERE {self._emb_col} IS NOT NULL"
            )
            return cur.fetchone()[0]

    def dimension(self) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                f"SELECT {self._emb_col} FROM {self._table} "
                f"WHERE {self._emb_col} IS NOT NULL LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                return 0
            return len(row[0])

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        with self._connect() as conn:
            offset = 0
            while True:
                cur = conn.execute(
                    f"SELECT {self._id_col}, {self._emb_col} "
                    f"FROM {self._table} "
                    f"WHERE {self._emb_col} IS NOT NULL "
                    f"ORDER BY {self._id_col} "
                    f"LIMIT %s OFFSET %s",
                    (batch_size, offset),
                )
                rows = cur.fetchall()
                if not rows:
                    break
                yield EmbeddingBatch(
                    ids=[r[0] for r in rows],
                    embeddings=np.array([r[1] for r in rows], dtype=np.float32),
                )
                offset += batch_size

    def write_batch(self, batch: EmbeddingBatch) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for row_id, vec in zip(batch.ids, batch.embeddings):
                    cur.execute(
                        f"UPDATE {self._table} SET {self._emb_col} = %s "
                        f"WHERE {self._id_col} = %s",
                        (vec.tolist(), row_id),
                    )
            conn.commit()
        return len(batch)

    def prepare_target(self, target_dim: int) -> None:
        with self._connect() as conn:
            # Check if dimension matches, if not alter
            cur = conn.execute(
                f"SELECT atttypmod FROM pg_attribute "
                f"WHERE attrelid = %s::regclass AND attname = %s",
                (self._table, self._emb_col),
            )
            row = cur.fetchone()
            if row and row[0] != target_dim:
                conn.execute(
                    f"ALTER TABLE {self._table} "
                    f"ALTER COLUMN {self._emb_col} TYPE vector({target_dim})"
                )
                conn.commit()
