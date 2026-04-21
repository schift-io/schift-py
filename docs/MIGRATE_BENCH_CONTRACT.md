# Migrate Bench Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`migrate.bench`는 migration 전에 "이 전환이 실제로 안전한지"를 검증하는 평가 단계다.

```text
paired corpus/query embeddings
  -> projection candidates tested
  -> retrieval metrics compared
  -> SAFE / WARN / FAIL verdict
```

## 2. Public API

```python
report = client.migrate.bench(
    source_model="openai/text-embedding-3-large",
    target_model="google/gemini-embedding-004",
    bucket_source=bucket_source,
    bucket_target=bucket_target,
    query_source=query_source,
    query_target=query_target,
    bucket_document_ids=bucket_document_ids,
    query_ids=query_ids,
    qrels=qrels,
    sample_ratios=[0.02, 0.05, 0.1, 0.2],
)
```

## 3. Inputs

필수:

- `source_model`
- `target_model`
- `bucket_source`
- `bucket_target`
- `query_source`
- `query_target`
- `bucket_document_ids`
- `query_ids`
- `qrels`

선택:

- `sample_ratios`
- `methods`
- `project_name`

## 4. Input constraints

- `bucket_source`와 `bucket_target`는 같은 bucket document set에 대한 paired embeddings여야 함
- `query_source`와 `query_target`도 같은 query set에 대한 paired embeddings여야 함
- `bucket_document_ids` 길이는 bucket row 수와 같아야 함
- `query_ids` 길이는 query row 수와 같아야 함
- `qrels`는 `query_id -> relevant bucket document ids` 구조여야 함

## 5. Output

```json
{
  "verdict": "SAFE",
  "source_model": "openai/text-embedding-3-large",
  "target_model": "google/gemini-embedding-004",
  "bucket_document_count": 10000,
  "n_queries": 200,
  "best_method": "ridge",
  "best_sample_ratio": 0.1,
  "original": {
    "R@1": 0.61,
    "R@10": 0.94,
    "R@100": 0.99,
    "nDCG@10": 0.81
  },
  "projected": {
    "R@1": 0.60,
    "R@10": 0.93,
    "R@100": 0.99,
    "nDCG@10": 0.80
  },
  "delta": {
    "R@10": -0.01,
    "nDCG@10": -0.01
  },
  "notes": []
}
```

## 6. Verdict semantics

- `SAFE`
  - projected quality가 production 전환 가능한 수준
- `WARN`
  - 전환 가능성은 있으나 품질 하락 또는 샘플 불안정성이 있음
- `FAIL`
  - 현재 조건으로는 migration 비권장

## 7. What bench does not do

- projection을 영구 저장하지 않음
- 실제 vector write 수행 안 함
- production route 변경 안 함

## 8. Relationship to fit

```text
bench = "전환해도 되나?"
fit   = "그럼 projection을 만들자"
```

`bench`가 평가 단계라면 `fit`은 asset 생성 단계다.

## 9. Current decision

- `bench`는 품질 리포트와 verdict에 집중
- asset lifecycle은 `fit` 이후로 넘긴다
