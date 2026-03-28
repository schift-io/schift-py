# DB Record Schema

> Status: Draft
> Date: 2026-03-13

## 1. Vector record

```json
{
  "id": "doc_1",
  "values": [0.1, 0.2],
  "metadata": {
    "source": "report.pdf"
  }
}
```

필수:

- `id`
- `values`

선택:

- `metadata`

## 2. Text upsert record

```json
{
  "id": "doc_1",
  "text": "2024 annual report ...",
  "metadata": {
    "source": "report.pdf"
  }
}
```

## 3. Query response hit

```json
{
  "id": "doc_1",
  "score": 0.95,
  "metadata": {
    "source": "report.pdf"
  }
}
```

## 4. Notes

- `db.upsert()`는 vector record 사용
- `db.upsert_text()`는 text record 사용
- `db.query()`는 hit list 반환
