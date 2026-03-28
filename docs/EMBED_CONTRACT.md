# Embed Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`embed`는 선택된 catalog 모델로 텍스트를 벡터화하는 실행 레이어다.

```text
text -> embed -> vector
```

`embed`는 모델을 "결정"하지 않는다.
그건 `routing` 책임이다.

## 2. Public API

```python
vector = client.embed.create(
    text="quarterly revenue report",
    model="openai/text-embedding-3-large",
)

vectors = client.embed.batch(
    texts=["a", "b", "c"],
    model="google/gemini-embedding-004",
)

models = client.embed.list_models()
model = client.embed.get_model("openai/text-embedding-3-large")
```

## 3. Functions

- `client.embed.create(text, model, dimensions=None, metadata=None)`
- `client.embed.batch(texts, model, dimensions=None, metadata=None)`
- `client.embed.list_models()`
- `client.embed.get_model(model_id)`
- `client.embed.resolve_alias(alias)`

## 4. Inputs

### create

- `text`
- `model`
- `dimensions` optional
- `metadata` optional

### batch

- `texts`
- `model`
- `dimensions` optional
- `metadata` optional

## 5. Outputs

```json
{
  "model": "openai/text-embedding-3-large",
  "dimensions": 3072,
  "vectors": [[0.1, 0.2]],
  "usage": {
    "input_count": 1,
    "provider": "openai",
    "provider_cost_usd": 0.00013,
    "routing_fee_usd": 0.0000065
  }
}
```

## 6. What embed does not do

- 모델 스위칭 정책 관리
- fallback 정책 관리
- 기존 벡터 migration
- search/rerank

## 7. Relationship to routing

```text
explicit model passed
  -> embed executes it

model="auto" or policy-driven
  -> routing resolves model first
  -> embed executes resolved model
```

## 8. Current decision

- `embed`는 execution-only
- catalog 밖 모델은 기본적으로 허용하지 않음
