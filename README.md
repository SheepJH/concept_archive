# concept-archive

> 개념 하나를 던지면, 인스타그램에 카드뉴스 8장이 자동으로 올라간다.

iOS 단축어에 "양자역학"이라고 입력하면, 약 90초 뒤
[@what_is_this.zip](https://instagram.com/what_is_this.zip) 피드에 8장짜리 캐러셀이 올라온다.

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

```mermaid
flowchart LR
    A["📱<br/>iOS Shortcut"]:::client
    B["☁️<br/>Cloud Run<br/>FastAPI"]:::infra
    C["🧠<br/>Gemini 3 Flash"]:::gen
    D["🖼<br/>Playwright<br/>Chromium"]:::infra
    E["📦<br/>Cloud Storage"]:::infra
    F["📸<br/>Instagram<br/>Graph API"]:::ext

    A -->|"① POST /publish"| B
    B -.->|"200 OK (즉시)"| A
    B -->|"② 8장 생성"| C
    C -->|"③ HTML→PNG"| D
    D -->|"④ 업로드"| E
    E -->|"⑤ 캐러셀 발행"| F
    F -.->|"media_id"| A

    classDef client fill:#0066FF,stroke:#0044cc,color:#fff,stroke-width:2px
    classDef gen fill:#FFF4E0,stroke:#E8A63B,color:#6B4A10,stroke-width:1.5px
    classDef infra fill:#F5F5F5,stroke:#BBB,color:#222,stroke-width:1.5px
    classDef ext fill:#FFE6EE,stroke:#D94C7A,color:#6B1733,stroke-width:1.5px

    linkStyle 0,2,3,4,5 stroke:#0066FF,stroke-width:2px
    linkStyle 1,6 stroke:#999,stroke-dasharray:5 5
```

> **①** 폰에서 POST → **즉시 200 OK 반환** (fire-and-forget)<br>
> **② → ⑤** 백그라운드에서 `Gemini 생성 → Playwright 렌더 → GCS 업로드 → IG 발행`<br>
> 약 **90초 뒤** `media_id`와 함께 IG 피드에 캐러셀 등장 → iOS가 알림 표시

**색상 범례** · 🟦 진입점(iOS) · ⬜ GCP 인프라(Cloud Run·Playwright·GCS) · 🟨 LLM(Gemini) · 🟥 외부 API(Instagram)

---

## 🧱 기술 스택

| 레이어 | 사용 기술 |
|---|---|
| **런타임** | Python 3.13 · Docker (`mcr.microsoft.com/playwright/python:v1.48.0-jammy`) |
| **백엔드** | FastAPI 0.115 · Uvicorn 0.32 · Pydantic 2.9 · httpx 0.27 |
| **LLM** | Google Gemini 3 Flash (`google-genai` SDK) · structured output |
| **렌더링** | Playwright 1.48 (Chromium) · HTML5 · CSS3 |
| **프론트 (프리뷰)** | Vanilla JS · Pretendard · Inter (CDN) |
| **인프라** | Google Cloud Run · Cloud Storage · Secret Manager · Cloud Build |
| **외부 API** | Instagram Graph API v21.0 (Business 계정) |
| **클라이언트** | iOS Shortcuts |
| **CI / 배포** | `gcloud run deploy --source .` (Cloud Build 자동) |

---

## 📁 폴더 구조

```
concept-archive/
├── index.html              # 브라우저 프리뷰 (디자인 확인용)
├── shared/styles.css       # 디자인 토큰 + 공통 레이아웃
├── templates/              # 카드 15종 HTML (01-overview ~ 15-oneline)
├── backend/
│   ├── main.py             # FastAPI + fire-and-forget 디스패처
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

Secret Manager에 `gemini-key`, `ig-token`, `ig-user-id`, `api-secret` 4개를 넣고:

```bash
gcloud run deploy card-news \
  --source . --region asia-northeast3 \
  --memory 2Gi --cpu 2 \
  --max-instances 3 --concurrency 1 \
  --no-cpu-throttling \
  --set-secrets GEMINI_KEY=gemini-key:latest,IG_TOKEN=ig-token:latest,IG_USER_ID=ig-user-id:latest,API_SECRET=api-secret:latest \
  --set-env-vars GCS_BUCKET=your-bucket-name \
  --allow-unauthenticated
```

### iOS 단축어

1. **URL 콘텐츠 가져오기**: POST `https://<CLOUD_RUN_URL>/publish`, 헤더 `Authorization: Bearer <API_SECRET>`, 본문 `{"concept": "매번 묻기"}`
2. **알림 보기** — 응답 변수 표시
