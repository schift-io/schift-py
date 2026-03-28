# Migrate Run Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`migrate.run`은 bench/fit 이후 실제 기존 벡터를 새 공간으로 옮기는 실행 단계다.

```text
existing vectors
  -> read
  -> transform/projection apply
  -> write
```

## 2. Public API

```python
result = client.migrate.run(
    projection="proj_abc123",
    source="pgvector://src",
    sink="pgvector://dst",
    dry_run=True,
    batch_size=1000,
)
```

단일 DB in-place도 허용 가능:

```python
result = client.migrate.run(
    projection="proj_abc123",
    db="pgvector://mydb",
    dry_run=False,
)
```

## 3. Request shape

최소 필드:

- `projection`
- `source` or `db`
- `sink` optional
- `dry_run`
- `batch_size`
- `filters` optional

## 4. Response shape

```json
{
  "migration_id": "mgr_123",
  "projection": "proj_abc123",
  "status": "completed",
  "dry_run": true,
  "source": "pgvector://src",
  "sink": "pgvector://dst",
  "vectors_total": 1234567,
  "vectors_migrated": 1234567,
  "source_dim": 1536,
  "target_dim": 3072,
  "elapsed_ms": 182300,
  "warnings": []
}
```

## 5. Dry-run semantics

`dry_run=True`면:

- 읽기는 수행
- projection 적용/검증은 수행
- 실제 write는 수행하지 않음
- 예상량/예상시간/경고를 반환

## 6. What migrate.run does not do

- projection 학습
- routing 결정
- query serving
- raw text embedding

## 7. Related APIs

- `client.migrate.bench(...)`
- `client.migrate.fit(...)`
- `client.migrate.list_projections()`

## 8. Current decision

- `migrate.run`은 execution step이다
- bench/fit과 분리한다
