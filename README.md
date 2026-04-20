# concept-archive

> 개념 하나를 던지면, 인스타그램에 카드뉴스 8장이 올라간다.

<p align="center">
  <img src="https://img.shields.io/badge/Python_3.13-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.13"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Cloud_Run-4285F4?style=flat-square&logo=googlecloud&logoColor=white" alt="Google Cloud Run"/>
  <img src="https://img.shields.io/badge/Gemini_3_Flash-8E75B2?style=flat-square&logo=googlegemini&logoColor=white" alt="Gemini 3 Flash"/>
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white" alt="Playwright"/>
  <img src="https://img.shields.io/badge/Telegram_Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram Bot"/>
  <img src="https://img.shields.io/badge/Instagram_API-E4405F?style=flat-square&logo=instagram&logoColor=white" alt="Instagram Graph API"/>
</p>

텔레그램 봇에 "양자역학"이라고 보내면, 약 90초 뒤 봇이 8장짜리 카드뉴스를
앨범으로 답장한다. 마음에 들면 **📤 인스타 아카이브** 버튼을 눌러
[@what_is_this.zip](https://instagram.com/what_is_this.zip)에 캐러셀로 발행.

---

## 🖼 템플릿 예시

"더닝-크루거 효과"라는 개념으로 실제 생성된 카드뉴스. 01~03번을 먼저 보여주고, 04~15번은 펼치기 안에 있음. 디자인 규격은 **[docs/design.md](docs/design.md)** 참고.

| | | |
|:-:|:-:|:-:|
| ![](docs/screenshots/template-01-overview.png) | ![](docs/screenshots/template-02-analogy.png) | ![](docs/screenshots/template-03-steps.png) |
| **01 · 개요** (표지 고정) | **02 · 비유** | **03 · 단계** |

<details>
<summary><b>📇 나머지 12종 펼치기 (04~15)</b></summary>

<br>

| | | |
|:-:|:-:|:-:|
| ![](docs/screenshots/template-04-matrix.png) | ![](docs/screenshots/template-05-formula.png) | ![](docs/screenshots/template-06-chain.png) |
| **04 · 매트릭스** | **05 · 공식** | **06 · 인과 체인** |
| ![](docs/screenshots/template-07-comparison.png) | ![](docs/screenshots/template-08-proscons.png) | ![](docs/screenshots/template-09-spectrum.png) |
| **07 · 비교** | **08 · 장단점** | **09 · 스펙트럼** |
| ![](docs/screenshots/template-10-timeline.png) | ![](docs/screenshots/template-11-realcase.png) | ![](docs/screenshots/template-12-misconception.png) |
| **10 · 타임라인** | **11 · 실생활 사례** | **12 · 오해와 진실** |
| ![](docs/screenshots/template-13-faq.png) | ![](docs/screenshots/template-14-checklist.png) | ![](docs/screenshots/template-15-oneline.png) |
| **13 · FAQ** | **14 · 체크리스트** | **15 · 한줄요약** (마지막 고정) |

</details>

---

## 🔄 파이프라인

### 큰 그림

```mermaid
flowchart LR
    U(["👤 사용자"])
    T["📨 Telegram Bot"]
    R["☁️ Cloud Run · FastAPI<br/><code>POST /tg</code>"]
    G["🧠 Gemini 3 Flash"]
    P["🖼 Playwright<br/>HTML → PNG"]
    S["📦 Cloud Storage"]
    I["📸 Instagram<br/>Graph API"]

    U -- "개념 메시지" --> T
    T -- "webhook" --> R
    R -. "즉시 200 OK" .-> T

    subgraph BG ["⚙️ 백그라운드 파이프라인 (fire-and-forget · 60~90s)"]
        direction LR
        G --> P --> S
    end

    R --> G
    S -- "public .png URLs" --> R
    R -- "sendMediaGroup (8장 앨범)" --> T
    T -- "프리뷰 + 버튼" --> U

    U -- "📤 아카이브 버튼" --> T
    T -- "callback_query" --> R
    R -- "캐러셀 발행" --> I

    classDef user fill:#fff,stroke:#888,color:#222
    classDef tg fill:#E8F4FB,stroke:#26A5E4,color:#0B3C5D
    classDef gcp fill:#F5F5F5,stroke:#999,color:#222
    classDef llm fill:#FFF4E0,stroke:#E8A63B,color:#6B4A10
    classDef ext fill:#FFE6EE,stroke:#D94C7A,color:#6B1733

    class U user
    class T tg
    class R,P,S gcp
    class G llm
    class I ext
```

### 시간 순서

```mermaid
sequenceDiagram
    autonumber
    actor U as 👤 사용자
    participant T as 📨 Telegram
    participant R as ☁️ Cloud Run
    participant G as 🧠 Gemini
    participant P as 🖼 Playwright
    participant S as 📦 GCS
    participant I as 📸 Instagram

    U->>T: "더닝-크루거 효과"
    T->>R: POST /tg (webhook)
    R-->>T: 200 OK (즉시 반환)
    T->>U: "⏳ 생성 중..."

    rect rgb(240, 247, 255)
    Note over R,S: 백그라운드 작업 · 단계별 실패 알림
    R->>G: 개념 → 카드 8장 JSON
    G-->>R: title / tags / cards
    R->>P: HTML+CSS 주입 → 1080×1350 렌더
    P-->>R: PNG × 8 (2배 슈퍼샘플링)
    R->>S: 업로드 (public, 7일 TTL)
    S-->>R: .png URLs
    end

    R->>T: sendMediaGroup (앨범)
    T->>U: 앨범 + [🔁 다시 만들기 · 📤 인스타 아카이브]

    Note over U,I: ——— 여기까지는 IG에 아무것도 안 올라감 ———

    U->>T: 📤 버튼 클릭
    T->>R: callback_query
    R->>I: 3단계 캐러셀 발행
    I-->>R: media_id
    R->>T: "✅ 아카이브 완료"
    T->>U: 완료 알림
```

### 핵심 설계

| 결정 | 이유 |
|---|---|
| **프리뷰 먼저, 발행은 선택** | 카드가 먼저 텔레그램에 답장으로 오고 `📤` 버튼을 눌러야만 IG에 발행됨. 실패작 자동 발행 방지. |
| **Fire-and-forget** | `/tg`는 `asyncio.create_task`로 파이프라인을 띄우고 즉시 200을 반환 → 텔레그램 웹훅 타임아웃 회피. Cloud Run에 `--no-cpu-throttling` 필수. |
| **단계별 에러 태그** | `Gemini 생성` / `카드 렌더링` / `GCS 업로드` / `텔레그램 전송` 4단계 각각 try 블록 → 실패 시 어느 단계가 죽었는지 바로 챗으로 통지. |
| **Chromium 실제 렌더** | 브라우저에서 보던 HTML 템플릿 = IG에 올라가는 결과. 2x 슈퍼샘플링으로 텍스트 선명도 확보. |
| **GCS 경유 발행** | IG Graph API는 `.png`/`.jpg`로 끝나고 리다이렉트 없는 공개 URL만 받음 (picsum 류는 `9004` 에러). GCS로 `.png` 확장자 고정 + public read. |
| **`_LAST_JOBS` 인메모리 캐시** | `redo`/`archive` 버튼이 재호출할 수 있도록 chat_id → 마지막 결과 캐싱. 콜드 스타트 시 날아가지만 그땐 사용자가 다시 보내면 됨. |

---

## 🧱 기술 스택

파이프라인 단계별로 어떤 기술이 어디에 쓰이는지.

### 🖥 클라이언트 — 개념 입력
- **Telegram Bot API** — BotFather로 만든 개인 봇. 메시지 수신 + 앨범 전송 + 인라인 버튼
- 별도 래퍼 없이 [`backend/telegram.py`](backend/telegram.py)에서 `httpx`로 직접 호출

### ☁️ 백엔드 — 웹훅 처리 & 오케스트레이션
- **FastAPI 0.115** + **Uvicorn 0.32** + **Pydantic 2.9** — `/tg` 웹훅, `asyncio.create_task` 기반 fire-and-forget
- **Python 3.13** — 최신 타입 문법(`str | None`) 필요
- 외부 호출은 전부 **`httpx`** 비동기 클라이언트

### 🧠 생성 — 개념 → 카드 JSON
- **Google Gemini 3 Flash** (`google-genai` SDK)
- `response_schema`로 `{title, tags, cards[{id, main}]}` 스키마 강제 → 파서 불필요

### 🎨 렌더링 — JSON → PNG 8장
- **Playwright 1.48 (Chromium)** — 1080×1350, 2x 슈퍼샘플링
- **HTML5 + CSS3** · 카드 15종은 [`templates/01~15.html`](templates/) 순수 HTML
- **Pretendard** · **Inter** 웹폰트 (CDN)

### 📦 저장 & 발행
- **Google Cloud Storage** — public `.png`, 7일 TTL 자동 삭제 lifecycle
- **Instagram Graph API v21.0** — 3단계 캐러셀 (child 컨테이너 → CAROUSEL → publish)

### 🚀 인프라 & 배포
- **Google Cloud Run** — `asia-northeast3`, 2Gi / 2CPU, `concurrency=1`, `--no-cpu-throttling` 필수
- **Cloud Build** — `gcloud run deploy --source .` 한 방 배포
- **Secret Manager** — 5개 시크릿(`gemini-key` · `ig-token` · `ig-user-id` · `api-secret` · `tg-token`)
- **Docker** — 베이스 `mcr.microsoft.com/playwright/python:v1.48.0-jammy` (+ Noto CJK 폰트)

---

## 📁 폴더 구조

```
concept-archive/
├── index.html              # 브라우저 프리뷰 (디자인 확인용)
├── shared/styles.css       # 디자인 토큰 + 공통 레이아웃
├── templates/              # 카드 15종 HTML (01-overview ~ 15-oneline)
├── backend/
│   ├── main.py             # FastAPI + fire-and-forget 디스패처 + /tg 웹훅
│   ├── telegram.py         # Telegram Bot API 얇은 래퍼 (httpx 기반)
│   ├── prompts.py          # 카드 메타 + 시스템 프롬프트 + 응답 스키마
│   ├── gemini_client.py    # Gemini API 래퍼
│   ├── renderer.py         # Playwright HTML→PNG
│   ├── storage.py          # GCS 업로드
│   └── instagram.py        # IG Graph API 캐러셀 발행
├── docs/
│   ├── pipeline.md         # 파이프라인 상세
│   ├── decisions.md        # 설계 결정 기록
│   └── design.md           # 카드 디자인 시스템
└── Dockerfile
```

---

## 🚀 시작하기

### 로컬

```bash
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env          # 키 채우기
export $(grep -v '^#' .env | xargs)
uvicorn main:app --reload --port 8080
```

### 배포 (Cloud Run)

Secret Manager에 `gemini-key`, `ig-token`, `ig-user-id`, `api-secret`, `tg-token` 5개를 넣고:

```bash
gcloud run deploy card-news \
  --source . --region asia-northeast3 \
  --memory 2Gi --cpu 2 \
  --max-instances 3 --concurrency 1 \
  --no-cpu-throttling \
  --set-secrets GEMINI_KEY=gemini-key:latest,IG_TOKEN=ig-token:latest,IG_USER_ID=ig-user-id:latest,API_SECRET=api-secret:latest,TG_TOKEN=tg-token:latest \
  --set-env-vars GCS_BUCKET=your-bucket-name \
  --allow-unauthenticated
```

### 텔레그램 봇 연결

1. [@BotFather](https://t.me/BotFather)에서 `/newbot` → 봇 이름·username 정하고 **봇 토큰** 받기 → Secret Manager의 `tg-token`에 저장
2. Cloud Run 배포 완료 후, 봇 웹훅을 `/tg` 엔드포인트로 등록:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TG_TOKEN>/setWebhook" \
     -d "url=https://<CLOUD_RUN_URL>/tg" \
     -d "secret_token=<API_SECRET>"
   ```
   (`secret_token`은 `API_SECRET`과 동일한 값을 사용 — 봇이 보내는 `X-Telegram-Bot-Api-Secret-Token` 헤더로 검증)
3. 봇과 대화 시작 → 개념 메시지 보내기 → 1~2분 후 카드뉴스 앨범 도착 → `📤 인스타 아카이브` 버튼으로 발행
