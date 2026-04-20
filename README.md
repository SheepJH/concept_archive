# concept-archive

> 모르는 개념을 던지면, 이해하기 쉬운 카드뉴스 8장으로 돌려받고 — 인스타그램에 아카이브한다.

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

모르는 개념이 생길 때마다 텔레그램 봇에 "더닝-크루거 효과"처럼 한 줄 보내면,
약 90초 뒤 봇이 **나만의 과외 노트 같은 카드뉴스 8장**을 앨범으로 답장한다.
이해가 됐다 싶으면 **📤 인스타 아카이브** 버튼을 눌러
[@what_is_this.zip](https://instagram.com/what_is_this.zip)에 남겨둠 — 나중에 다시 꺼내 볼 수 있게.

---

## 🖼 템플릿 예시

"더닝-크루거 효과"를 봇에 보냈을 때 실제로 받아본 카드 8장. 봇은 개념마다 어울리는 템플릿을 **15종 중에서 골라** 조합하고, **01 · 개요**(표지)와 **15 · 한줄요약**(마지막)은 고정이다. 아래는 01–03번만 먼저 보여주고, 나머지 12종(04–15)은 펼치기 안에 있음. 디자인 규격은 **[docs/design.md](docs/design.md)** 참고.

| | | |
|:-:|:-:|:-:|
| ![](docs/screenshots/template-01-overview.png) | ![](docs/screenshots/template-02-analogy.png) | ![](docs/screenshots/template-03-steps.png) |
| **01 · 개요** (표지 고정) | **02 · 비유** | **03 · 단계** |

<details>
<summary><b>📇 나머지 12종 펼치기 (04–15)</b></summary>

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
    A("👤 개념")
    B("📨 Telegram")
    C("☁️ Cloud Run")
    D("🧠 Gemini")
    E("🖼 Playwright")
    F("📦 GCS")
    G("📥 프리뷰")
    H("📸 Instagram")

    A --> B --> C --> D --> E --> F --> G
    G -. "📤" .-> H

    classDef user fill:#1f1f1f,stroke:#555,color:#fff
    classDef tg fill:#26A5E4,stroke:#1d8bc0,color:#fff
    classDef gcp fill:#4285F4,stroke:#1a56c2,color:#fff
    classDef ai fill:#8E75B2,stroke:#6b5689,color:#fff
    classDef pw fill:#2EAD33,stroke:#1f7a22,color:#fff
    classDef gcs fill:#F9AB00,stroke:#c28700,color:#1a1a1a
    classDef out fill:#2a2a2a,stroke:#888,color:#fff,stroke-dasharray:4 2
    classDef ig fill:#E4405F,stroke:#b0304a,color:#fff

    class A user
    class B tg
    class C gcp
    class D ai
    class E pw
    class F gcs
    class G out
    class H ig
```

> 실선 = 자동 실행 · 점선 = 사용자가 `📤` 버튼 눌러야 발동

### 시간 순서

```mermaid
sequenceDiagram
    participant U as 👤 사용자
    participant T as 📨 Telegram
    participant B as ☁️ 백엔드<br/>(Cloud Run)
    participant I as 📸 Instagram

    U->>T: 1️⃣ "더닝-크루거 효과"
    T->>B: 2️⃣ POST /tg (webhook)
    B-->>T: 3️⃣ 200 OK (즉시)
    T-->>U: 4️⃣ "⏳ 생성 중..."

    Note over B: 🧠 Gemini → 카드 8장 JSON
    Note over B: 🖼 Playwright → 1080×1350 PNG × 8
    Note over B: 📦 GCS 업로드 → public URLs

    B->>T: 5️⃣ sendMediaGroup (앨범)
    T-->>U: 6️⃣ 앨범 + [🔁 다시 만들기 · 📤 인스타 아카이브]

    Note over U,I: ── IG엔 아직 아무것도 안 올라감 ──

    U->>T: 7️⃣ 📤 아카이브 버튼
    T->>B: 8️⃣ callback_query
    B->>I: 9️⃣ 3단계 캐러셀 발행
    I-->>B: 🔟 media_id
    B-->>U: ✅ 완료 메시지
```

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
- **HTML5 + CSS3** · 카드 15종은 [`templates/01–15.html`](templates/) 순수 HTML
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

## 💸 비용 구조

개인 프로젝트라 **사실상 0원**. 모든 구성요소가 각자 무료 티어에 걸리거나 요청이 없으면 0으로 수렴함.

### 생성 1회 (개념 → 카드 8장 앨범) 당 대략

| 단계 | 과금 방식 | 대략 비용 | 비고 |
|---|---|---:|---|
| 📨 Telegram Bot API | 무료 | ― | 웹훅/미디어 그룹 전송 무료 |
| ☁️ Cloud Run | 2 vCPU × ~90s + 2 GiB 메모리 사용 시간 | ≈ 0원 | **월 1,000회까진 무료 티어 안** |
| 🧠 Gemini 3 Flash | Google AI Studio 무료 티어 (하루 약 20회 한도) | ≈ 0원 | 개인 용도(하루 1–2회)면 **항상 무료 범위** |
| 🎨 Playwright | Cloud Run 안에서 실행 | ― | 별도 과금 없음 (Cloud Run 비용에 포함) |
| 📦 Cloud Storage | PUT 8회 · 2.4 MB 저장 (7일 TTL) · IG egress | < 0.1원 | 7일 후 자동 삭제로 저장 비용 거의 0 |
| 🔐 Secret Manager | 시크릿 접근 ops | ― | 월 10k 접근 무료 티어 안 |
| 📸 Instagram Graph API | 무료 | ― | Business 계정 rate limit 안 |
| **합계** | | **≈ 0원** | |

> 💡 Gemini 무료 티어 초과 시(유료 결제 전환) 입력 $0.075 / 출력 $0.30 per 1M tokens로 과금 전환. 요청당 ~2원 수준.

### 고정비 (idle 시 0원에 가까움)

| 항목 | 월 비용 | 설명 |
|---|---:|---|
| Cloud Run | **0원** | 요청 없으면 인스턴스 0개 → 안 돌면 과금 없음 |
| Cloud Storage (GCS) | **< 10원** | 7일 TTL로 버킷 거의 비어 있음 |
| Artifact Registry (Docker 이미지) | ≈ 50–100원 | Cloud Build가 쌓아둔 이미지 1–2 GB 상시 저장 |
| Secret Manager (5개 시크릿) | **0원** | 시크릿 활성 버전 6개 무료 |

### 비용 포인트

- **Gemini 무료 티어** — Google AI Studio 기준 하루 약 20회 무료 (모델별 상이). 혼자 모르는 개념 정리할 때 하루 몇 번 쓰는 용도면 **절대 안 넘음**. 넘어도 요청당 2원 수준
- **`--no-cpu-throttling` 필수 트레이드오프** — 응답 반환 후에도 CPU가 돌아야 백그라운드 파이프라인이 살아남음. 응답 후 ~90초간 CPU 과금 지속. 이걸 빼면 파이프라인 자체가 죽음 → **필수**
- **Cloud Run 무료 티어** — 월 180k vCPU-sec · 360k GiB-sec · 2M 요청. 요청당 ~360 vCPU-sec 쓰니 **월 500회까진 확실히 무료**
- **실질 월 비용** — 하루 1–2회 사용 시 **사실상 0원**. Artifact Registry Docker 이미지 저장만 월 50–100원 정도 고정으로 나옴

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
3. 봇과 대화 시작 → 개념 메시지 보내기 → 1–2분 후 카드뉴스 앨범 도착 → `📤 인스타 아카이브` 버튼으로 발행
