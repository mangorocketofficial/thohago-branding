# Thohago Branding Runbook

전체 콘텐츠 생성 워크플로우. 텔레그램 인터뷰부터 모든 플랫폼 발행까지.

---

## 전체 흐름도

```
Phase 0: 클라이언트 온보딩
    ↓
Phase 1: 텔레그램 인터뷰 (자동)
    ↓
Phase 2: 블로그 생성 + 고객 승인
    ↓
Phase 3: 숏폼 영상 생성 (릴스)
    ↓
Phase 4: 인스타그램 캐러셀 생성
    ↓
Phase 5: 쓰레드 생성
    ↓
Phase 6: 발행 (네이버, 인스타, 쓰레드)
```

---

## Phase 0: 클라이언트 온보딩

### 목적
새 클라이언트(샵)를 시스템에 등록한다.

### 실행

1. `config/shops.example.json`에 샵 정보 추가:
```json
{
  "shop_id": "new_shop",
  "display_name": "샵 이름",
  "invite_tokens": ["new_shop-start"],
  "telegram_chat_ids": [],
  "publish": { "provider": "mock_naver", "targets": ["naver_blog"] },
  "media_hints": ["주요 장면 힌트1", "장면 힌트2"]
}
```

2. 텔레그램에서 고객이 `/start new_shop-start` 입력 → 자동 바인딩

### 출력
- 샵 레지스트리에 등록 완료
- 텔레그램 chat_id와 shop_id 매핑

### 다음 단계 조건
- 고객이 텔레그램 봇에 접속 완료

---

## Phase 1: 텔레그램 인터뷰

### 목적
고객으로부터 사진/영상 + 3턴 인터뷰를 수집한다.

### 상태: ✅ 자동화 완료

### 실행

봇 시작:
```bash
python -m thohago bot
```

고객 측 흐름:
```
/begin                → 세션 생성
사진/영상 업로드       → 미디어 수집
/interview            → 인터뷰 시작
  Q1 (preflight 기반 동적 질문) → 답변
  Q2 (AI 생성 후속 질문)        → 답변
  Q3 (AI 생성 후속 질문)        → 답변
                      → 자동 완료
```

### 봇 명령어

| 명령어 | 기능 |
|--------|------|
| `/start <token>` | 샵 바인딩 |
| `/begin` | 새 세션 시작 |
| `/interview` | 미디어 분석 + 인터뷰 시작 |
| `/status` | 현재 상태 확인 |
| `/reset` | 세션 초기화 |

### 출력

```
runs/{shop_id}/{session_key}/
├── raw/                    # 원본 사진/영상
├── transcripts/            # 턴별 전사
├── generated/
│   ├── media_preflight.json
│   ├── content_bundle.json
│   └── naver_blog_article.md
├── planners/               # 턴별 질문 생성 로직
├── published/
├── chat_log.jsonl
└── session_metadata.json
```

### 다음 단계 조건
- `session_metadata.json`의 stage가 `completed`

### 참고 문서
- Q1 동적 생성: `src/thohago/interview_engine.py` → `plan_turn1()`
- 3단 fallback: Anthropic → OpenAI → Heuristic

---

## Phase 2: 블로그 생성 + 고객 승인

### 목적
인터뷰 + 사진을 기반으로 블로그 글을 AI로 작성하고, 고객 승인을 받는다.

### 상태: 🔄 재설계 필요

### 현재 문제
- `content.py`가 AI 프롬프트 없이 템플릿 조립만 함
- 블로그 품질이 낮음 (전사 붙여넣기, 기계적 구조)

### 개선 방향
1. Claude가 자유 서사로 블로그 작성 (숏폼과 같은 원칙)
2. 네이버 스타일 HTML로 출력 (볼드, 색상, 사진 인라인)
3. GitHub Pages에 미리보기 HTML 배포
4. 텔레그램으로 미리보기 링크 전송 → 고객 승인

### 블로그 작성 원칙
- 정보는 최대한 많이 제공, 글쓰기는 Claude에게 자유롭게
- 실제 경험 중심 서사
- 인터뷰 멘트 인용 활용
- 사진 적절한 위치 배치
- 볼드, 텍스트 색상 활용

### 승인 흐름
```
Claude가 블로그 HTML 생성
    → GitHub Pages에 push
    → 텔레그램에 미리보기 링크 전송
    → 고객 확인 → 승인/수정 요청
    → 승인 시 → Phase 6에서 네이버 발행
```

### 입력
- `content_bundle.json`
- `interview_transcripts` (3턴)
- `media_preflight.json`
- 샵 정보

### 출력
- 블로그 HTML 파일
- GitHub Pages 미리보기 URL
- 고객 승인 상태

### 다음 단계 조건
- 고객 승인 완료

---

## Phase 3: 숏폼 영상 생성

### 목적
블로그 서사를 기반으로 인스타 릴스 / 숏폼 영상을 생성한다.

### 상태: ✅ 파이프라인 완성 (수동 실행)

### 실행

```bash
cd client/{shop_id}/{date}/shorts_pipeline_test

# 1. 새로 생성 (서사 + TTS + 렌더)
python render_from_spec.py

# 2. 스티커 생성 (선택)
python generate_stickers.py

# 3. 소스 배치 변경 후 재렌더
python render_from_spec.py --rerender
```

### 파이프라인 (Source-First)

```
Phase 1: Claude가 자유 서사 작성 + 문장별 소스 매칭
Phase 2: Google Cloud TTS 생성 (1.1x 속도)
Phase 3: TTS 길이 기준 타임라인 자동 생성
Phase 4: 클립 세그먼트 렌더 (Ken Burns + warm grading)
Phase 5: 텍스트 오버레이 + 자막 + 스티커 합성
Phase 6: 보이스오버 믹싱 → 최종 MP4
```

### 수동 조정 가능 항목
- `narrative_script.json` → 스크립트 텍스트, 소스 매칭 수정
- `sticker_plan.json` → 이모지 종류, 좌표, 크기 수정
- `--rerender`로 Claude 호출 없이 재렌더

### 비주얼 디폴트

| 항목 | 값 |
|------|-----|
| 해상도 | 1080x1920 (9:16) |
| 사진 보정 | warm grading + 비네팅 |
| 오버레이 | Cafe24Dangdanghae, #FFEE59, 3-layer 글로우 |
| 자막 | Cafe24Ohsquare, 44px, 반투명 배경 |
| 화면 전환 | 하드컷 (효과 없음) |
| TTS | Google Cloud ko-KR-Chirp3-HD-Achernar, 1.1x |

### 출력
- `render_output/shorts_render.mp4`
- `render_output/narrative_script.json`
- `render_output/generated_render_spec.json`

### 다음 단계 조건
- 영상 품질 확인 완료

### 참고 문서
- `docs/shorts_source_first_pipeline.md`

---

## Phase 4: 인스타그램 캐러셀 생성

### 목적
사진 기반 인스타그램 피드용 캐러셀 (5장 슬라이드)을 생성한다.

### 상태: ⚙️ 스크립트 존재 (스펙 수동 작성)

### 실행

```bash
cd client/{shop_id}/{date}/images
python render_instagram_carousel.py
```

### 실행

```bash
cd client/{shop_id}/{date}

# 1. Claude가 캐러셀 서사 + 슬라이드별 사진/텍스트 매칭 → 스펙 자동 생성
python generate_carousel.py

# 2. 기존 렌더러로 슬라이드 렌더
cd images
python render_instagram_carousel.py
```

### 파이프라인 (Source-First)

```
Phase 1: Claude가 사진 + 인터뷰를 보고 5장 서사 기획
         → 슬라이드별 사진/headline/subheadline 매칭
         → instagram_carousel_edit_spec.json 자동 생성
Phase 2: PIL로 각 슬라이드 렌더 (사진 크롭 + 텍스트 오버레이)
```

### 디자인 디폴트

| 항목 | 값 |
|------|-----|
| 해상도 | 1080x1350 (4:5) |
| 헤드라인 폰트 | Cafe24Moyamoya (cover) / Cafe24Ohsquare (나머지) |
| 강조 색상 | #FFEE59 |
| 패널 배경 | rgba(5,17,34,0.72) |

### 출력
- `carousel_output/slide_*.jpg` (1080x1350, 4:5)
- `carousel_output/caption.txt`
- `carousel_output/hashtags.txt`
- `carousel_output/carousel_manifest.json`

### 다음 단계 조건
- 캐러셀 이미지 확인 완료

---

## Phase 5: 쓰레드 생성

### 목적
블로그 서사를 쓰레드 3단 체인(메인 + 댓글 2개)으로 압축한다.

### 상태: ✅ 파이프라인 완성 (수동 실행)

### 구조

```
[메인 포스트] 훅 — 핵심 에피소드로 호기심 유발
    ↓
[댓글 1] 스토리 + 인용 — 실제 반응/경험 전개
    ↓
[댓글 2] CTA — 샵 정보 + 마무리 + 해시태그
```

### 실행

```bash
cd client/{shop_id}/{date}
python generate_thread.py
```

### 입력
- `blog_preview/blog_content.html` (블로그 HTML)
- `interview/interview_transcripts.md` (인터뷰 전사)

### 출력
- `thread_output/thread_content.json` — 구조화된 데이터
- `thread_output/thread_posts.txt` — 복사해서 바로 올릴 수 있는 텍스트

### 톤/스타일
- 브랜드 시점, 캐주얼 대화체
- 인터뷰 실제 멘트 인용
- 이모지 적절히 (과하지 않게)
- 해시태그 2~3개

### 다음 단계 조건
- 쓰레드 텍스트 확인 완료

---

## Phase 6: 발행

### 목적
생성된 콘텐츠를 각 플랫폼에 발행한다.

### 상태: ❌ API 연결 미완료

### 발행 대상

| 플랫폼 | 콘텐츠 | 상태 |
|--------|--------|------|
| 네이버 블로그 | 블로그 HTML | 🔄 파이프라인 준비 (API 키 미연결) |
| 인스타그램 피드 | 캐러셀 5장 + 캡션 | ❌ 미구현 |
| 인스타그램 릴스 | 숏폼 영상 | ❌ 미구현 |
| 쓰레드 | 텍스트 콘텐츠 | ❌ 미구현 |

### 발행 순서 (계획)
```
1. 네이버 블로그 발행 (고객 승인 후)
2. 인스타그램 릴스 업로드
3. 인스타그램 피드 캐러셀 업로드
4. 쓰레드 텍스트 발행
```

---

## 환경 설정

### 필수 환경변수 (.env)

```
# 텔레그램
TELEGRAM_BOT_TOKEN=<bot_token>

# 샵 설정
THOHAGO_SHOPS_FILE=config/shops.example.json
THOHAGO_ARTIFACT_ROOT=runs

# AI API 키
CLAUDE_API_KEY=<anthropic_api_key>
GROQ_API_KEY=<groq_api_key>
OPENAI_API_KEY=<openai_api_key>

# Google Cloud TTS
# ADC 인증: gcloud auth application-default login
```

### 의존성 설치

```bash
pip install -e .
# 추가: google-cloud-texttospeech, anthropic, Pillow, python-dotenv
# 시스템: ffmpeg, ffprobe
```

### 테스트

```bash
python -m pytest tests/ -v
```

---

## 트러블슈팅

### TTS 인증 실패
```bash
gcloud auth application-default login
gcloud config set project <project_id>
```

### 텔레그램 봇 시작 실패
- `.env`의 `TELEGRAM_BOT_TOKEN` 확인
- `python -m thohago bot --dry-run`으로 설정 확인

### 숏폼 렌더 실패
- ffmpeg 설치 확인: `ffmpeg -version`
- 폰트 경로 확인: `assets/font/` 하위
- 사진/영상 경로 확인: `client/{shop_id}/{date}/images/`, `video/`

### Claude API 실패
- `.env`의 `CLAUDE_API_KEY` 확인
- fallback 체인: Anthropic → OpenAI → Heuristic 자동 전환

---

## 부록: 파일 구조

```
Thohago_branding/
├── Runbook.md                          # 이 문서
├── .env                                # 환경변수 (커밋 금지)
├── config/
│   └── shops.example.json              # 샵 레지스트리
├── src/thohago/                        # 핵심 패키지
│   ├── bot.py                          # 텔레그램 봇
│   ├── pipeline.py                     # 리플레이 파이프라인
│   ├── content.py                      # 블로그 생성 (개선 필요)
│   ├── interview_engine.py             # 인터뷰 엔진
│   ├── anthropic_live.py / openai_live.py / groq_live.py
│   └── ...
├── client/{shop_id}/{date}/            # 클라이언트별 소스/산출물
│   ├── images/                         # 사진 + 캐러셀 렌더
│   ├── video/                          # 영상 + 릴스 렌더
│   ├── interview/                      # 인터뷰 전사
│   └── shorts_pipeline_test/           # 숏폼 파이프라인
├── runs/{shop_id}/                     # 세션별 산출물
├── assets/font/                        # Cafe24 폰트
├── docs/                               # 스키마/설계 문서
└── tests/                              # 테스트
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-03-29 | Q1 동적 생성 구현 |
| 2026-03-29 | Source-First 숏폼 파이프라인 구현 |
| 2026-03-29 | 영상 효과 (warm grading, 글로우 텍스트, 스티커) |
| 2026-03-29 | Google Cloud TTS 전환 (1.1x) |
| 2026-03-29 | 블로그 AI 생성 + GitHub Pages 승인 흐름 설계 |
| 2026-03-29 | Runbook 초판 작성 |
| 2026-03-30 | 캐러셀 Source-First 파이프라인 구현 (generate_carousel.py) |
| 2026-03-30 | 쓰레드 3단 체인 생성 구현 (generate_thread.py) |
| 2026-03-30 | Phase 5(쓰레드) 추가, Phase 번호 재정렬 |
