# Design Decisions

만드는 동안 선택의 기로가 여러 번 있었다. 각각의 결정과 **이유**, 그리고 **뭘 포기했는가**를 기록.

---

## 1. 왜 서버리스(Cloud Run)인가 — VM도 Lambda도 아닌

- **VM(항상 실행)**: 하루에 몇 번 쓰는 개인 툴에 유휴 비용 내기 싫음.
- **AWS Lambda / GCF 2nd gen**: 이미지 크기 제한(250MB 언팩)이 빡셈. Playwright + Chromium + Noto CJK + Python 얹으면 넘김.
- **Cloud Run**: 컨테이너 그대로 올리고, 요청 없을 땐 0개 인스턴스. Playwright 공식 이미지 쓸 수 있음. 스케일 0 → N 자동.

**트레이드오프**: 콜드스타트 3~5초. Telegram 봇이 `⏳ 생성 중...`으로 먼저 답하니 체감 X.

---

## 2. 왜 Fire-and-forget 패턴인가

전체 파이프라인(Gemini → Playwright → GCS → Telegram 전송)은 **60~120초** 걸린다. Telegram webhook은 응답을 빨리 안 돌려주면 재시도를 해버린다 → 동기로 돌리면 같은 작업이 두세 번 트리거됨.

### 구현
1. `/tg` 웹훅 수신 → 즉시 `200 OK` 반환
2. `asyncio.create_task(...)`로 파이프라인을 백그라운드로 띄움
3. 완료되면 `sendMediaGroup`로 Telegram 채팅에 결과 푸시

```python
asyncio.create_task(_do_telegram_publish(chat_id, concept))
return {"ok": True}
```

**함정**: Cloud Run이 응답 반환 후 CPU를 스로틀링하면 백그라운드 태스크가 멈춘다. 반드시 `--no-cpu-throttling` 플래그 켜야 함.

### 사용자 알림
백그라운드 진행 중에는 `sendChatAction("upload_photo")`을 4초마다 갱신해서 채팅 상단에 "사진 업로드 중..." 인디케이터를 띄운다 — 사용자가 "응답 안 옴?"으로 오해하지 않도록.

---

## 3. 왜 Gemini 3 Flash인가 — Claude / GPT-4 아닌

- **가격**: Flash는 입력 $0.075/M, 출력 $0.30/M. 카드 하나당 0.1센트 수준.
- **structured output**: `response_schema`로 JSON 강제 가능. 실패율 낮음.
- **속도**: 8장 카드 생성 15~25초. 파이프라인 전체 중 가장 짧음.
- **품질**: 카드뉴스 요약 용도엔 Flash로 충분. 차이는 미미.

**포기한 것**: 더 깊은 추론. 하지만 카드뉴스는 본질적으로 **요약 + 포맷팅** 작업이라서 문제 없음.

---

## 4. 왜 Playwright로 HTML→PNG인가 — Pillow/Canvas API 아닌

### Pillow로 직접 그리기
- 한글 폰트(Pretendard), 커닝, 자동 줄바꿈 전부 수동 계산
- 디자인 바꿀 때마다 파이썬 코드 수정
- **폐기**

### HTML `<canvas>` API
- 브라우저에서만 돌아감. 서버에서 렌더하려면 어차피 Playwright 필요
- **폐기**

### Playwright + HTML 템플릿 (선택)
- 디자이너 친화적: CSS로 디자인 수정
- `index.html`에서 **실시간 브라우저 프리뷰 == 서버 렌더 결과** 1:1 보장
- 웹폰트, SVG, flexbox 모든 게 공짜

**트레이드오프**: Chromium 무거움 → 2Gi 메모리 필요. 하지만 개인 용도라 허용 가능.

---

## 5. 왜 GCS를 경유하는가 — IG에 바이트 직접 못 보냄

Instagram Graph API의 스펙:
- `image_url` 파라미터만 받음 (바이트 업로드 X)
- 리다이렉트 따라가지 않음
- 확장자 기반 타입 추론 (`.png`, `.jpg`만 허용)

### 시도한 것들
- `picsum.photos`로 테스트 → IG 에러 코드 9004 (리다이렉트)
- 시그니처드 URL → 복잡하고 IG가 싫어하는 쿼리 파라미터

### 최종
- **GCS 공개 버킷**: `allUsers:objectViewer`로 공개
- **파일명 `.png`**: `{uuid}.png`
- **Content-Type `image/png`**: 업로드 시 명시
- **Lifecycle 7일 삭제**: 원본이 IG에 박히면 끝, GCS는 임시 저장소

---

## 6. 왜 concurrency=1 + max-instances=3인가

### concurrency=1 (인스턴스당 동시 요청 1개만)
Playwright는 Chromium을 프로세스로 띄운다.
한 인스턴스에서 동시에 2개 파이프라인이 돌면:
- Chromium 2개 = 메모리 2배 = 2Gi로 부족
- OOM으로 둘 다 죽음

### max-instances=3
개인 인스타 + 개인 봇이라 동시 요청이 이론상 1~2개.
3이면 여유 있고, 비용 폭주 방어도 됨.

---

## 7. 왜 Secrets Manager인가 — .env 커밋 X

- `gemini-key`, `ig-token`, `ig-user-id`, `api-secret`, `tg-token` 전부 Secret Manager
- Cloud Run `--set-secrets`로 배포 시 주입
- 로컬 개발용 `.env`는 `.gitignore`로 막고, `.env.example`만 커밋

**IG long-lived token은 60일마다 만료** → Secret Manager 값만 바꾸고 재배포하면 끝. 코드 변경 없음.

---

## 8. 왜 Telegram secret_token만으로 인증하는가

Telegram의 `setWebhook`은 임의 값을 `secret_token`으로 받아두면, 모든 webhook 요청에 `X-Telegram-Bot-Api-Secret-Token` 헤더로 같이 보내준다.

- 개인 툴이라 OAuth / JWT 같은 풀스케일 인증은 오버킬
- `API_SECRET` 시크릿 하나를 webhook secret_token으로 재사용 → 봇 외 누가 `/tg`를 때려도 401
- 노출되면 Secret Manager 값 회전 + `setWebhook` 한 번 더 호출하면 끝

---

## 9. 카드 14종 + 8장 고정의 이유

### 왜 14개 템플릿?
개요 / 비유 / 단계 / 타임라인 / 비교 / 장단점 / 스펙트럼 / 실생활사례 / 통계숫자 / 결정트리 / 체크리스트 / FAQ / 한줄요약 + 예비 1개.
모든 "개념 설명"은 이 14개 조합으로 표현 가능하다고 판단. 더 늘리면 LLM이 선택을 헤맴.

### 왜 정확히 8장?
- IG 캐러셀 최대 10장
- 1장(개요) + 1장(한줄요약) 고정 → 중간 6장
- 8장이 **스크롤 피로도 vs 정보량**의 스윗스팟
- LLM에게 "정확히 8장"으로 강제 → 길이 결정 부담 제거
