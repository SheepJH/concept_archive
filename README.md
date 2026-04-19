# concept-archive

> 개념 하나를 던지면, 인스타그램에 카드뉴스 8장이 자동으로 올라간다.

iOS 단축어에 "양자역학"이라고 입력하고 실행하면,
약 90초 뒤 [@what_is_this.zip](https://instagram.com/what_is_this.zip)에 8장짜리 카드뉴스 캐러셀이 올라온다.

<!-- 스크린샷 추가 예정: docs/screenshots/hero.png -->
<!-- ![](docs/screenshots/hero.png) -->

---

## TL;DR

- **입력**: 개념 키워드 한 줄 (iOS 단축어)
- **출력**: 인스타그램 피드에 8장 캐러셀 포스트
- **소요**: 응답 즉시, 실제 발행까지 ~90초
- **스택**: FastAPI + Gemini 2.5 Flash + Playwright + Cloud Run + GCS + IG Graph API

---

## 아키텍처

```
 ┌──────────────┐  POST /publish           ┌──────────────────────┐
 │ iOS Shortcut │ ───────────────────────▶ │  Cloud Run (FastAPI) │
 └──────────────┘  {concept: "..."}        │  200 OK 즉시 반환     │
        ▲                                   │  (fire-and-forget)   │
        │                                   └──────────┬───────────┘
        │ ✅ 발행 완료 알림                             │
        │                                              ▼
        │                        ┌──────────┐    ┌────────────┐    ┌──────┐    ┌─────────┐
        └──────────────────────  │ Gemini   │ ─▶ │ Playwright │ ─▶ │ GCS  │ ─▶ │ IG API  │
           media_id              │ (JSON)   │    │ HTML→PNG   │    │ .png │    │ carousel│
                                 └──────────┘    └────────────┘    └──────┘    └─────────┘
```

자세한 흐름과 각 단계의 역할은 **[docs/architecture.md](docs/architecture.md)** 참고.

---

## 폴더 구조와 각 파일의 역할

```
concept-archive/
├── index.html              # 브라우저 프리뷰 (서버 없이 디자인 확인용)
├── shared/
│   └── styles.css          # 디자인 토큰 (색/타이포/스페이싱) + 공통 레이아웃
├── templates/
│   ├── 01-overview.html    # 개요 (첫 장 고정)
│   ├── 02-analogy.html     # 비유
│   ├── ...
│   └── 15-oneline.html     # 한줄요약 (마지막 장 고정)
├── backend/
│   ├── main.py             # FastAPI 엔드포인트 + fire-and-forget 디스패처
│   ├── prompts.py          # 카드 15종 메타 + 시스템 프롬프트 + 응답 스키마
│   ├── gemini_client.py    # Gemini API 얇은 래퍼 (구조화 JSON 파싱)
│   ├── renderer.py         # 카드 JSON → 1080×1350 PNG (Playwright)
│   ├── storage.py          # PNG → GCS 공개 URL (Content-Type .png 강제)
│   ├── instagram.py        # IG Graph API 캐러셀 3단계 발행
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   ├── architecture.md     # 파이프라인 상세 흐름도
│   ├── decisions.md        # 설계 결정 기록 (왜 이렇게 했는가)
│   ├── design.md           # 카드 디자인 시스템 명세
│   └── screenshots/        # README/문서용 이미지
├── Dockerfile              # playwright/python + Noto CJK
└── README.md               # 이 문서
```

### 왜 이렇게 쪼개져 있나

| 파일 | 역할 | 왜 따로 두는가 |
|---|---|---|
| `index.html` | 브라우저에서 카드 실시간 미리보기 | 서버 안 띄우고 디자인만 고치고 싶을 때. 템플릿/CSS 수정 시 즉시 반영 확인 |
| `shared/styles.css` | 디자인 토큰 한 곳 | 색/폰트/여백 바꾸고 싶으면 이 파일만. 템플릿 15개 열어볼 필요 없음 |
| `templates/*.html` | 카드 한 종류 = 한 파일 | 템플릿 추가/수정 시 영향 범위가 그 파일 하나로 국한 |
| `main.py` | HTTP 진입점 | Fire-and-forget 패턴 분리 — 엔드포인트에서는 큐잉만, 실제 파이프라인은 `_do_publish` |
| `prompts.py` | LLM 지시 단일 출처 | 프롬프트 수정 시 여기만. 템플릿 변경과 프롬프트 변경의 경계 명확 |
| `gemini_client.py` | Gemini SDK 의존성 격리 | 모델 교체(Flash→Pro 등) 시 이 파일만. 나머지 코드는 딕셔너리만 앎 |
| `renderer.py` | Playwright 의존성 격리 | 렌더 엔진 교체나 CSS 주입 로직 변경 시 영향 최소화 |
| `storage.py` | GCS 업로드 규칙 격리 | Content-Type, 파일명 확장자, 캐시 헤더를 한 곳에서 제어 |
| `instagram.py` | IG Graph API 상태 머신 | 3단계 발행 + `status_code` 폴링 로직이 복잡. 따로 빼두면 IG 정책 변경에 강함 |

---

## 설계 결정 요약

풀 버전은 **[docs/decisions.md](docs/decisions.md)**. 핵심만:

1. **Cloud Run (서버리스 컨테이너)** — VM은 비싸고 Lambda는 이미지 용량 제한(Playwright 못 올림). Cloud Run이 유일한 답.
2. **Fire-and-forget 패턴** — iOS 단축어 타임아웃 60초, 실제 파이프라인 90초. 동기 응답 불가능 → `asyncio.create_task` + 즉시 200.
3. **`--no-cpu-throttling` 필수** — 응답 후 CPU 스로틀링되면 백그라운드 태스크가 죽음. Cloud Run 기본값에선 동작 안 함.
4. **Playwright로 HTML→PNG** — Pillow로 한글 타이포 수동 계산은 지옥. 브라우저 렌더 == 최종 결과 1:1 보장.
5. **GCS 경유 (IG 바이트 업로드 불가)** — IG Graph API는 `image_url`만 받고, 리다이렉트 안 따라가고, `.png`/`.jpg` 확장자만 허용.
6. **Gemini 2.5 Flash + structured output** — 카드뉴스는 요약 작업. Flash로 충분. `response_schema`로 JSON 강제.
7. **concurrency=1 / max-instances=3** — Chromium 동시 기동은 OOM. 인스턴스당 1개만, 최대 3인스턴스.

---

## 로컬 개발

```bash
# 프론트엔드 프리뷰만
python3 -m http.server 8000   # → http://localhost:8000/index.html

# 백엔드
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env          # 키 채우기
export $(grep -v '^#' .env | xargs)
uvicorn main:app --reload --port 8080
```

> **Python 3.13 필요** — `str | None` union syntax 사용.

---

## 배포 (Google Cloud Run)

### 1. GCP 리소스 준비
- 프로젝트 생성 후 다음 API 활성화: `run.googleapis.com`, `secretmanager.googleapis.com`, `storage.googleapis.com`, `cloudbuild.googleapis.com`
- GCS 버킷 하나 생성 (public read + 7-day lifecycle delete 권장)
- Secret Manager에 4개 시크릿: `gemini-key`, `ig-token`, `ig-user-id`, `api-secret`
- Cloud Run 기본 서비스 계정에 `secretmanager.secretAccessor` + 버킷 `storage.objectAdmin` 부여

### 2. 배포

```bash
gcloud run deploy card-news \
  --source . \
  --region asia-northeast3 \
  --memory 2Gi --cpu 2 \
  --timeout 300 \
  --max-instances 3 --concurrency 1 \
  --no-cpu-throttling \
  --set-secrets GEMINI_KEY=gemini-key:latest,IG_TOKEN=ig-token:latest,IG_USER_ID=ig-user-id:latest,API_SECRET=api-secret:latest \
  --set-env-vars GCS_BUCKET=your-bucket-name \
  --allow-unauthenticated
```

### 3. iOS 단축어 설정
2개 액션:
1. **URL 콘텐츠 가져오기**
   - URL: `https://<YOUR_CLOUD_RUN_URL>/publish`
   - 방식: POST
   - 헤더: `Authorization: Bearer <API_SECRET>`, `Content-Type: application/json`
   - 본문(JSON): `{"concept": "매번 묻기"}`
2. **알림 보기** — 본문은 위 액션의 응답(URL 콘텐츠) 변수

---

## API

모든 엔드포인트: `Authorization: Bearer <API_SECRET>`

### `POST /publish`
개념 → 전체 파이프라인 (fire-and-forget). 즉시 200 반환, 실제 발행은 백그라운드.

```json
{"concept": "양자역학"}
```
응답:
```json
{"ok": true, "queued": true, "concept": "양자역학"}
```

### `POST /generate`
개념 → 카드 JSON (IG 발행 X, 디버깅/수동 미리보기용).

```json
{"concept": "양자역학"}
```
응답:
```json
{"title": "...", "tags": ["#...", "..."], "cards": [{"id": "01-overview", "main": "<html>..."}, ...]}
```

---

## 보안

- 모든 시크릿은 Secret Manager. 로컬 `.env`는 `.gitignore` 처리됨.
- IG long-lived 토큰은 60일마다 만료 → Secret Manager 값 교체 후 재배포.
- 호출자 인증은 Bearer 공유 시크릿 1개 (개인용 툴이라 충분).

---

## 디자인 시스템

카드 15종의 고정 위치 / 타이포 스케일 / 컬러 토큰 / 레이아웃 규칙은 **[docs/design.md](docs/design.md)**.

- Canvas: 1080×1350 (IG 4:5)
- 한글: Pretendard / 영문·숫자: Inter (CDN)
- 컬러: 무채색 5단계 + 포인트 컬러 1개 (`--accent`만 바꾸면 전체 테마 변경)

---

## 라이선스

개인 프로젝트. 코드는 자유롭게 참고·포크 가능. 생성되는 카드뉴스의 저작권과 IG 계정은 작성자에게 있음.
