# Search Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`search`는 query를 받아 retrieval result를 반환하는 레이어다.

```text
query -> embed/query transform -> retrieve -> rerank(optional) -> results
```

## 2. Public API

```python
results = client.search.query(
    query="2024 annual report",
    index="schift://docs",
    top_k=10,
    rerank=True,
)
```

관련 함수:

- `client.search.query(...)`
- `client.search.rerank(...)`
- `client.search.analytics(...)`

## 3. Inputs

- `query` text or vector
- `index` or `collection`
- `model` optional
- `top_k`
- `filters`
- `rerank`

## 4. Outputs

```json
{
  "results": [
    {
      "id": "doc_123",
      "score": 0.95,
      "metadata": {"source": "report.pdf"}
    }
  ],
  "query_info": {
    "top_k": 10,
    "rerank": true
  }
}
```

## 5. What search does not do

- 기존 벡터 전체 migration
- routing policy 관리
- collection lifecycle 관리

## 6. Relationship to db

- `db`는 저장/CRUD
- `search`는 retrieval/query serving

같은 storage를 써도 역할은 다르다.

## 7. Relationship to embed

- text query면 내부적으로 embed/query transform이 선행될 수 있다
- 그래도 사용자 계약은 retrieval API다

## 8. Current decision

- `search`는 retrieval 중심
- analytics도 search usage를 중심으로 붙는다
