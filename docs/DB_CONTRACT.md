# DB Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`db`는 Schift managed vector DB의 저장/관리 레이어다.

```text
collection lifecycle
  + vector upsert/delete/query
  + storage stats
```

## 2. Public API

```python
client.db.create_collection(name="docs", dimension=3072)
client.db.upsert(collection="docs", vectors=[...])
hits = client.db.query(collection="docs", vector=[...], top_k=10)
```

관련 함수:

- `client.db.create_collection(...)`
- `client.db.list_collections()`
- `client.db.delete_collection(...)`
- `client.db.upsert(...)`
- `client.db.upsert_text(...)`
- `client.db.delete(...)`
- `client.db.query(...)`
- `client.db.collection_stats(...)`

## 3. Inputs

### collection lifecycle

- `name`
- `dimension`
- `metric`

### vector ops

- `collection`
- `vectors` or `documents`
- `ids`
- `metadata`

## 4. Outputs

- collection info
- vector op result
- query hits
- storage stats

## 5. What db does not do

- routing policy 결정
- migration bench
- search analytics

## 6. Relationship to search

```text
db.query()     = storage-adjacent nearest neighbor query
search.query() = product-level retrieval API
```

즉 `db.query()`는 primitive이고, `search.query()`는 더 상위 개념이다.

## 7. Relationship to migrate

- `migrate`는 `db` 위에서 read/write orchestration을 할 수 있다
- 하지만 `db` 자체가 migration module은 아니다

## 8. Current decision

- `db`는 managed storage surface
- BYODB adapter와는 분리된 제품 개념이다
