# Adapter Interface Contract

> Status: Draft
> Date: 2026-03-13

## 1. Purpose

adapter는 BYODB와 파일 기반 source/sink를 같은 migration/search 흐름에 태우기 위한 공통 인터페이스다.

```text
pgvector
qdrant
npy/file
future providers
  └─ common adapter interface
```

## 2. Scope

adapter는 주로 아래 용도에 쓰인다.

- `migrate.run()` source/sink
- `migrate.bench()`용 sample read
- 일부 low-level BYODB query

adapter는 product-level `search`나 `db` 자체를 대체하지 않는다.

## 3. Core interface

```python
class Adapter(Protocol):
    adapter_name: str

    def count(self) -> int: ...
    def read_batches(self, batch_size: int): ...
    def write_batch(self, batch): ...
    def sample(self, n: int): ...
    def prepare_target(self, dimension: int): ...
```

## 4. Batch shape

```json
{
  "ids": ["doc_1", "doc_2"],
  "embeddings": [[0.1, 0.2], [0.3, 0.4]],
  "metadata": [
    {"source": "report.pdf"},
    {"source": "faq.md"}
  ]
}
```

필수 필드:

- `ids`
- `embeddings`

선택 필드:

- `metadata`

## 5. Required behaviors

### `count()`

- 전체 vector row 수 반환

### `read_batches(batch_size)`

- stable batch iteration 제공
- 순서는 deterministic이면 좋음

### `write_batch(batch)`

- sink에 batch write
- upsert semantics를 기본 가정

### `sample(n)`

- bench용 sample read
- 가능하면 random or stratified sample

### `prepare_target(dimension)`

- sink 준비
- schema/table/index/collection 생성 또는 검증

## 6. Error expectations

최소 에러 분류:

- `AdapterConnectionError`
- `AdapterSchemaError`
- `AdapterValidationError`
- `AdapterWriteError`

## 7. Non-goals

adapter가 하지 않는 것:

- routing policy 처리
- projection 학습
- customer usage aggregation
- managed DB control plane

## 8. Built-in adapters

문서 기준 우선 지원:

- `pgvector`
- `qdrant`
- `.npy` / file

후속:

- `pinecone`
- `weaviate`

## 9. Current decision

- adapter는 BYODB integration layer
- `db` 모듈과는 별도 개념
- `migrate`가 adapter 위에서 orchestration 수행
