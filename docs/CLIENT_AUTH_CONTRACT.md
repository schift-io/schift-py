# Client And Auth Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`Client`는 SDK 전체의 유일한 인증/transport 진입점이다.

```text
Client
  ├─ API key 보관
  ├─ base_url 보관
  ├─ timeout/retry 기본값 보관
  ├─ auth header 생성
  └─ module namespace 생성
```

하위 모듈은 별도 인증 상태를 가지지 않는다.

## 2. Public shape

```python
from schift import Client

client = Client(
    api_key="sch_xxx",
    base_url="https://api.schift.io",
    timeout=60.0,
)
```

권장 추가 엔트리포인트:

```python
client = Client.from_env()
client.ping()
client.usage(window="7d", group_by="provider")
client.usage_limits()
```

## 3. Required fields

- `api_key`
- `base_url`
- `timeout`

## 4. API key rules

- 형식: `sch_...`
- public SDK는 bearer key만 사용
- key 발급/회전/폐기는 웹 control plane 역할
- SDK는 발급된 key를 소비만 한다

## 5. Module attachment

```text
client.embed
client.routing
client.migrate
client.search
client.db
```

이 namespace들은 같은 auth/transport를 공유한다.

## 6. Non-goals

`Client`가 하지 않는 것:

- key 발급
- 로그인 UI
- org/user 관리
- internal operator auth

## 7. Errors

최소 에러 분류:

- `AuthError`
- `QuotaError`
- `RateLimitError`
- `ServerError`
- `ValidationError`

## 8. Current decision

- auth는 `Client`에서 끝낸다
- 하위 모듈은 auth 세부를 몰라야 한다
- `client.usage()`는 customer aggregate only
