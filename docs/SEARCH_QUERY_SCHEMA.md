# Search Query Schema

> Status: Draft
> Date: 2026-03-13

## 1. Request

```json
{
  "query": "2024 annual report",
  "index": "schift://docs",
  "model": "openai/text-embedding-3-large",
  "top_k": 10,
  "filters": {
    "source": "report.pdf"
  },
  "rerank": true
}
```

필수:

- `query`
- `index`

선택:

- `model`
- `top_k`
- `filters`
- `rerank`

## 2. Response

```json
{
  "results": [
    {
      "id": "doc_123",
      "score": 0.95,
      "metadata": {
        "source": "report.pdf"
      }
    }
  ],
  "query_info": {
    "top_k": 10,
    "rerank": true,
    "model": "openai/text-embedding-3-large"
  },
  "usage": {
    "search_requests": 1,
    "estimated_spend_usd": 0.0004
  }
}

```

## 3. Notes

- `index`는 BYODB logical name 또는 `schift://...` 형식
- `query`는 text 우선, vector query는 후속 확장
