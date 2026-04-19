# Architecture

개념(키워드) 하나를 던지면, 인스타그램에 8장짜리 카드뉴스가 자동으로 올라간다.
전체 파이프라인은 6개 구성요소로 끊어져 있고, 각 단계는 **한 가지 책임**만 진다.

---

## 전체 흐름

```
 ┌──────────────┐   POST /publish            ┌──────────────────────────┐
 │ iOS Shortcut │ ─────────────────────────▶ │   Cloud Run (FastAPI)    │
 └──────────────┘   {concept: "양자역학"}     │                          │
        ▲                                    │  1. 200 OK 즉시 반환     │
        │ ✅ 발행 완료 알림                   │  2. 백그라운드 태스크    │
        │   (IG 포스트 URL)                   │     으로 파이프라인 시작  │
        │                                    └────────────┬─────────────┘
        │                                                 │
        │                                                 ▼
        │                                   ┌──────────────────────────┐
        │                                   │  Gemini 2.5 Flash        │
        │                                   │  (structured JSON out)   │
        │                                   │                          │
        │                                   │  → title / tags / 8 cards│
        │                                   └────────────┬─────────────┘
        │                                                │
        │                                                ▼
        │                                   ┌──────────────────────────┐
        │                                   │  Playwright (Chromium)   │
        │                                   │                          │
        │                                   │  HTML 템플릿 + CSS       │
        │                                   │   → 1080×1350 PNG ×8     │
        │                                   └────────────┬─────────────┘
        │                                                │
        │                                                ▼
        │                                   ┌──────────────────────────┐
        │                                   │  Google Cloud Storage    │
        │                                   │                          │
        │                                   │  public-read .png URLs   │
        │                                   │  (7-day lifecycle 삭제)   │
        │                                   └────────────┬─────────────┘
        │                                                │
        │                                                ▼
        │                                   ┌──────────────────────────┐
        └────────────────────────────────── │  Instagram Graph API     │
            media_id / permalink            │                          │
                                            │  3-step carousel publish │
                                            └──────────────────────────┘
```

---

## 왜 이런 모양인가

### iOS Shortcut → Cloud Run 한 단계
폰에서 바로 `POST /publish` 때려서 끝. 웹 UI도 없고, 별도 앱도 없음.
**입력 비용 = 키워드 한 줄**이 이 프로젝트의 목표라서.

### Fire-and-forget (즉시 200 OK + 백그라운드 실행)
전체 파이프라인(Gemini + Playwright + GCS + IG)은 **60~120초** 걸린다.
iOS Shortcut의 HTTP 타임아웃은 **약 60초**. 동기로 돌리면 단축어가 터진다.

그래서 `/publish`는:
1. 요청 받자마자 `asyncio.create_task(...)`로 백그라운드 실행 스케줄
2. `{queued: true}` 바로 응답
3. 실제 발행은 뒤에서 진행, 성공하면 로그만 남김

단축어는 즉시 성공 알림을 받고, 실제 인스타 포스트는 1~2분 뒤에 올라온다.

### Gemini 2.5 Flash + structured output
- **왜 Flash**: 카드 텍스트 생성은 복잡한 추론이 아님. 빠르고 싸야 됨.
- **왜 structured JSON**: 프롬프트 결과를 바로 `{title, tags, cards[{id, main}]}` 스키마로 받음. 파서 따로 안 만들어도 됨. `response_schema`로 강제.

### Playwright로 HTML → PNG (Canvas/SVG 생성 X)
카드뉴스는 **타이포그래피가 생명**. 한글 커닝, Pretendard 웹폰트, line-height 디테일을 픽셀에서 맞추려면 브라우저 렌더러가 가장 충실함.
- `templates/01~15.html` = 순수 HTML + `<style>` 블록
- 렌더러는 공통 CSS(`shared/styles.css`) + 템플릿별 CSS를 인라인으로 붙여서 Chromium에 주입
- 1080×1350 뷰포트로 스크린샷 찍음

즉, **브라우저에서 보는 결과 = IG에 올라가는 결과**가 보장됨. 디자인 수정하고 싶으면 템플릿 HTML만 고치면 끝.

### GCS를 왜 거치나 (IG에 바이트 직접 못 보냄)
Instagram Graph API는 **image_url을 받아서 자기네가 다운로드**하는 방식이다. 바이트 업로드 불가.
그래서:
1. 렌더된 PNG → GCS 공개 버킷에 업로드
2. 공개 URL(`https://storage.googleapis.com/.../xxx.png`)을 IG에 넘김
3. 7일 후 lifecycle 규칙으로 자동 삭제 (원본은 IG에 이미 박혔으니 보관 불필요)

⚠️ IG는 **리다이렉트를 따라가지 않고, 확장자가 `.png`/`.jpg`가 아니면 거부**한다. GCS 업로드 시 Content-Type과 파일명 확장자 둘 다 맞춰야 함 (`storage.py`).

### IG 캐러셀 3단계 발행
Graph API가 캐러셀 올리는 방식이 특이함:
1. 각 이미지마다 `is_carousel_item=true` 컨테이너 생성 → `child_id` N개
2. `media_type=CAROUSEL` + `children=child_ids`로 **부모 컨테이너** 생성
3. 부모의 `status_code == FINISHED` 될 때까지 폴링
4. `/media_publish`에 `creation_id=부모_id` 보내면 실제 피드에 올라감

비동기 상태 머신이라서 `_wait_until_ready`로 백오프 폴링 걸어놨음.

---

## 런타임 환경

| 항목 | 값 | 이유 |
|---|---|---|
| Cloud Run memory | 2Gi | Chromium + 8장 동시 렌더에 필요 |
| Cloud Run CPU | 2 | Playwright 렌더링 병목 완화 |
| concurrency | 1 | 인스턴스당 파이프라인 1개만 — Chromium 동시 띄우면 OOM |
| max-instances | 3 | 폭주 방지 (개인 계정이라 트래픽 예측 가능) |
| **`--no-cpu-throttling`** | **필수** | 응답 반환 후 백그라운드 태스크가 CPU 스로틀에 죽지 않도록 |
| region | `asia-northeast3` | 서울. 한국에서 호출 + Gemini 지연 최소화 |

---

## 역할 분리 요약

| 파일 | 한 문장 역할 |
|---|---|
| `backend/main.py` | FastAPI 엔드포인트 + fire-and-forget 디스패처 |
| `backend/prompts.py` | 카드 15종 메타데이터 + Gemini 시스템 프롬프트 + 응답 스키마 |
| `backend/gemini_client.py` | Gemini API 호출 얇은 래퍼 (구조화 JSON 파싱) |
| `backend/renderer.py` | 카드 JSON → 1080×1350 PNG (Playwright) |
| `backend/storage.py` | PNG → GCS 공개 URL (Content-Type 강제) |
| `backend/instagram.py` | IG Graph API 캐러셀 3단계 발행 상태 머신 |
| `templates/01~15.html` | 카드 디자인 템플릿 (개요/비유/단계/비교/한줄요약 등) |
| `shared/styles.css` | 디자인 토큰 (색/타이포/스페이싱) + 공통 레이아웃 |
| `index.html` | 브라우저 프리뷰용 올인원 생성기 (디버깅/수동 미리보기) |
| `Dockerfile` | playwright/python 베이스 + Noto CJK 폰트 설치 |
