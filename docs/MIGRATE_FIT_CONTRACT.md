# Migrate Fit Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`migrate.fit`은 paired embedding sample로 projection asset을 생성하는 단계다.

```text
paired embeddings
  -> fit projection
  -> persist projection metadata
  -> return projection handle
```

## 2. Public API

```python
projection = client.migrate.fit(
    source_model="openai/text-embedding-3-large",
    target_model="google/gemini-embedding-004",
    source=source_embeddings,
    target=target_embeddings,
    project_name="openai-to-gemini-prod",
)
```

## 3. Inputs

필수:

- `source_model`
- `target_model`
- `source`
- `target`

선택:

- `project_name`
- `method`
- `sample_ratio`
- `tags`

## 4. Input constraints

- `source`와 `target`은 같은 sample set에 대한 paired embeddings
- sample count는 최소 10 이상
- shape mismatch는 validation error

## 5. Output

```json
{
  "project_id": "proj_abc123",
  "source_model": "openai/text-embedding-3-large",
  "target_model": "google/gemini-embedding-004",
  "source_dim": 3072,
  "target_dim": 3072,
  "n_samples": 2000,
  "method": "ridge",
  "quality": {
    "holdout_cosine": 0.992,
    "recovery_r10": 0.997
  },
  "project_name": "openai-to-gemini-prod",
  "created_at": "2026-03-13T10:00:00Z"
}
```

## 6. What fit returns

현재 문서 기준 기본 반환은 `projection handle`이다.

즉:

- metadata는 반환
- project id는 반환
- projection matrix 원본은 기본적으로 반환하지 않음

필요하면 SDK 객체로 감싼다:

```python
projection.project_id
projection.source_model
projection.target_model
projection.quality
```

## 7. What fit does not do

- retrieval quality를 full bench처럼 자세히 평가하지 않음
- vector DB write 수행 안 함
- route switching 안 함

## 8. Relationship to run

```text
fit = projection asset 생성
run = projection asset 사용
```

즉 `run`은 `fit` 결과 없이는 시작하지 않는다.

## 9. Current decision

- `fit`은 asset creation step
- matrix raw exposure는 기본 비허용
