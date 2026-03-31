# Source-First 숏폼 영상 생성 파이프라인

## 1. 개요

소스(사진/영상)와 인터뷰 전사를 기반으로 **하나의 서사 스크립트를 먼저 작성**하고, 스크립트 길이에 맞춰 미디어를 배치하는 파이프라인이다.

핵심 원칙:
- **스크립트가 먼저, 미디어가 따라간다** — TTS 자연 속도를 절대 변경하지 않는다
- **서사는 하나의 흐름** — beat 구조를 AI에게 알려주지 않는다
- **AI가 문장별로 소스를 직접 매칭** — 별도 allocation 단계 불필요

---

## 2. 전체 흐름

```
소스 확인 (사진 + 영상 + 인터뷰 전사)
        |
        v
Phase 1: Claude가 자유 서사 작성 + 문장별 소스 매칭
        |
        v
Phase 2: Google Cloud TTS 생성 (1.1x, 자연 속도)
        |
        v
Phase 3: TTS 길이 기준으로 타임라인 자동 생성
        |
        v
Phase 4: 클립 세그먼트 렌더 (Ken Burns / crop reframe)
        |
        v
Phase 5: 텍스트 오버레이 + 자막 합성
        |
        v
Phase 6: 보이스오버 믹싱 → 최종 MP4 출력
```

---

## 3. Phase 1: 서사 스크립트 생성

### 입력

| 입력 | 설명 |
|------|------|
| `media_preflight.json` | 사진별 scene, details, mood 분석 |
| `interview_transcripts.md` | 인터뷰 전사 전문 |
| 영상 메타데이터 | 영상별 길이, 가로/세로 방향 |

### AI 프롬프트 설계

Claude에게 **주는 것**:
- 각 사진의 장면 설명 (예: "photo_01: 듀얼 샴푸대 동시 시술, 은박 스팀캡, 몽환적 휴식")
- 각 영상의 메타 (예: "video_01: 13.3초, 세로 영상")
- 인터뷰 전사 전문
- 배경 정보 (샵 이름, 위치, 상황)

Claude에게 **주지 않는 것**:
- beat 구조 (hook/setup/proof/reaction/cta)
- 비트별 메시지
- 문장 수 강제

### 프롬프트 핵심 지침

```
하나의 이야기를 쓰세요. 누군가에게 "이런 일이 있었어"라고
자연스럽게 말해주는 것처럼요.

- 전체 5~6문장 (절대 7문장 이상 쓰지 마세요)
- 각 문장은 20~35자 이내로 짧게
- 인터뷰에서 나온 실제 표현을 살리세요
- 마지막 문장은 샵 이름을 포함한 클로징
- 편안한 해요체
- 전체 소리내어 읽었을 때 20~25초 분량
- 각 문장마다 화면에 보여줄 소스를 지정해주세요
```

### 출력

`narrative_script.json`:

```json
{
  "full_narrative": "전체 이야기 (하나의 연결된 텍스트)",
  "sentences": [
    {
      "index": 1,
      "text": "필리핀 관광객 5명이 한국 오기 전부터 예약하고 서면까지 왔어요.",
      "sources": ["video_02"],
      "overlay_text": "사전예약"
    }
  ]
}
```

### 모델

- `claude-sonnet-4-20250514` (max_tokens: 2000)
- API 키: `.env`의 `CLAUDE_API_KEY` 또는 `ANTHROPIC_API_KEY`

---

## 4. Phase 2: TTS 생성

### 설정

| 항목 | 값 |
|------|-----|
| 엔진 | Google Cloud Text-to-Speech |
| 인증 | Application Default Credentials (ADC) |
| 음성 | `ko-KR-Chirp3-HD-Achernar` (한국어 여성, HD) |
| 속도 | `1.1x` (자연스럽되 약간 빠르게) |
| 출력 형식 | MP3 → WAV 변환 (44100Hz, 모노) |

### 처리 과정

1. `narrative_script.json`의 각 sentence.text를 TTS로 변환
2. MP3로 생성 → ffmpeg로 WAV 변환
3. 각 문장의 **실제 TTS 길이를 측정** — 이 길이가 해당 문장의 영상 길이가 됨

### 핵심 규칙

**TTS 속도를 사후에 절대 변경하지 않는다.** atempo, 시간 압축/확장 없음.
미디어가 TTS 길이에 맞춰야지, TTS가 미디어에 맞춰서는 안 된다.

---

## 5. Phase 3: 타임라인 생성

### 규칙

1. 문장 순서대로 타임라인을 구성
2. 각 문장의 TTS 길이 = 해당 구간의 영상 길이
3. 문장에 소스가 2개면, TTS 길이를 균등 분할
4. 절대 시간축은 문장들을 순서대로 이어붙여 계산

### 예시

```
문장 1 (5.23초): video_02 → 0.0~5.23초
문장 2 (3.65초): photo_01 → 5.23~8.88초
문장 3 (4.34초): photo_01 + photo_04 → 8.88~11.05 / 11.05~13.22초
...
```

### 영상 길이 부족 시

TTS 합계 > 클립 합계인 경우, 마지막 프레임을 freeze (`tpad=stop_mode=clone`)로 연장.

---

## 6. Phase 4: 클립 세그먼트 렌더

### 사진 처리 (Ken Burns)

```
ffmpeg -loop 1 -i {photo}
  -vf "scale=8000:-1,
       zoompan=z='{scale_from}+({scale_to}-{scale_from})*on/{frames}'
       :x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'
       :d={frames}:s=1080x1920:fps=30,
       setsar=1,
       eq=saturation=1.1:brightness=0.03,
       colorbalance=rs=0.04:gs=0.01:bs=-0.03:rm=0.03:gm=0.0:bm=-0.02,
       vignette=PI/4"
  -t {duration} -c:v libx264 -preset fast -crf 18
```

- 기본 줌: 1.0 → 1.06 (서서히 확대)
- Warm 컬러 그레이딩: 채도 1.1, 밝기 +0.03, red 강조
- 비네팅: PI/4 (가장자리 자연스럽게 어두워짐)

### 영상 처리

**가로 영상** (horizontal_to_vertical):
```
scale=-1:1920, crop=1080:1920:(iw-1080)/2:0
```
센터 크롭으로 세로 변환.

**세로 영상** (native_vertical):
```
scale=1080:1920:force_original_aspect_ratio=decrease,
pad=1080:1920:(ow-iw)/2:(oh-ih)/2
```
비율 유지 + 패딩.

### 공통 설정

| 항목 | 값 |
|------|-----|
| 해상도 | 1080x1920 (9:16) |
| FPS | 30 |
| 코덱 | H.264 (libx264) |
| 프리셋 | fast |
| 품질 | CRF 18 |

### 화면 전환

- **하드컷** (기본값) — 클립 간 전환 효과 없음
- 크로스페이드/디졸브/페이드 인·아웃은 사용하지 않음 (깜빡임 방지)

### 비주얼 효과 (사진 클립 기본 적용)

| 효과 | 값 | 목적 |
|------|-----|------|
| Warm 컬러 그레이딩 | saturation=1.1, brightness=+0.03, red 강조 | 따뜻한 분위기 통일 |
| 비네팅 | vignette=PI/4 | 시선 중앙 집중 |

영상 클립에는 컬러 그레이딩/비네팅을 적용하지 않음 (원본 유지).

---

## 7. Phase 5: 오버레이 합성

### 텍스트 오버레이 (PIL 3-레이어 렌더링)

| 항목 | 값 |
|------|-----|
| 폰트 | Cafe24Dangdanghae-v2.0.ttf |
| 색상 | `#FFEE59` (노란색) |
| 크기 | hook: **100px** / cta: **80px** / supporting: **72px** |
| 위치 | 첫 문장: center / 나머지: bottom_center |

3-레이어 구조:
1. **소프트 쉐도우**: 검정 텍스트를 (x+2, y+4) 오프셋 후 GaussianBlur(radius=8) — 깊이감
2. **컬러 글로우**: #FFEE59 텍스트(alpha 100)를 GaussianBlur(radius=12) — 발광 효과
3. **크리스프 본문**: 2px 검정 아웃라인(alpha 160) + #FFEE59 본문(alpha 255)

### 자막 (PIL로 PNG 생성)

| 항목 | 값 |
|------|-----|
| 폰트 | Cafe24Ohsquare-v2.0.ttf |
| 색상 | 흰색 |
| 배경 | 반투명 검정 (alpha 160) |
| 크기 | 44px |
| 위치 | 하단 12% 영역 |
| 줄바꿈 | 화면 폭 - 120px 기준 자동 줄바꿈 |

### 합성 방식

ffmpeg `overlay` 필터로 각 PNG를 `enable='between(t,start,end)'`로 타이밍 적용.

---

## 8. Phase 6: 보이스오버 믹싱

1. TTS 합계 길이의 무음 베이스 트랙 생성 (44100Hz, 모노)
2. 각 문장의 WAV를 `adelay`로 정확한 시작 시점에 배치
3. `amix`로 합성 (normalize=0, 원본 볼륨 유지)
4. 최종 비디오 + 오디오 머징 (video copy, audio AAC 192k)

---

## 9. 실행 방법

### 새로 생성 (스크립트 + 렌더)

```bash
python render_from_spec.py
```

### 소스 배치만 변경 후 재렌더 (스크립트 유지)

```bash
# 1. narrative_script.json에서 sources만 수정
# 2. 재렌더
python render_from_spec.py --rerender
```

`--rerender`는 Phase 1(Claude 호출)을 건너뛰고 기존 `narrative_script.json`을 재사용한다.

---

## 10. 입출력 파일 정리

### 입력

| 파일 | 역할 |
|------|------|
| `media_preflight.json` | 사진/영상 장면 분석 |
| `interview_transcripts.md` | 인터뷰 전사 원문 |
| `images/*.jpg` | 사진 소스 (photo_01~05) |
| `video/*.mp4` | 영상 소스 (video_01~02) |

### 중간 산출물

| 파일 | 역할 |
|------|------|
| `narrative_script.json` | AI 생성 서사 + 문장별 소스 매칭 |
| `generated_render_spec.json` | 자동 생성된 타임라인/오버레이/자막 스펙 |
| `voice/s01~s06.wav` | 문장별 TTS 음성 |
| `segments/c01~c08.mp4` | 개별 클립 세그먼트 |
| `overlay_pngs/*.png` | 텍스트 오버레이 이미지 |
| `subtitles/*.png` | 자막 이미지 |

### 최종 출력

| 파일 | 역할 |
|------|------|
| `shorts_render.mp4` | 최종 렌더 영상 (1080x1920, 약 25초) |

---

## 11. 의존성

| 패키지/도구 | 용도 |
|-------------|------|
| `ffmpeg` / `ffprobe` | 영상/오디오 처리 |
| `google-cloud-texttospeech` | TTS 생성 |
| `anthropic` | Claude API (스크립트 생성) |
| `Pillow` (PIL) | 한글 텍스트 PNG 렌더링 |
| `python-dotenv` | 환경변수 로드 |

### 환경 설정

```bash
# Google Cloud ADC 인증
gcloud auth application-default login

# .env 파일에 필요한 키
CLAUDE_API_KEY=sk-ant-...
```

---

## 12. 스탠다드 비주얼 디폴트 요약

| 카테고리 | 항목 | 기본값 |
|----------|------|--------|
| **영상 포맷** | 해상도 | 1080x1920 (9:16) |
| | FPS | 30 |
| | 코덱 | H.264, CRF 18 |
| **사진 모션** | Ken Burns | 1.0 → 1.06 (서서히 확대) |
| **사진 보정** | 컬러 그레이딩 | warm tone (saturation 1.1, brightness +0.03, red 강조) |
| | 비네팅 | PI/4 |
| **영상 보정** | 없음 | 원본 유지 |
| **화면 전환** | 하드컷 | 전환 효과 없음 |
| **페이드** | 없음 | fade in/out 사용 안 함 |
| **오버레이 폰트** | Cafe24Dangdanghae | hook 100px, cta 80px, supporting 72px |
| **오버레이 색상** | #FFEE59 | 3레이어 (쉐도우 + 글로우 + 본문) |
| **자막 폰트** | Cafe24Ohsquare | 44px 흰색, 반투명 검정 배경 |
| **TTS** | Google Cloud | ko-KR-Chirp3-HD-Achernar, 1.1x |
| **BGM** | 없음 | 추후 추가 예정 |

---

## 13. 설계 원칙 요약

1. **서사 우선**: beat 구조가 아닌 자유로운 이야기에서 출발
2. **자연 음성**: TTS 속도를 사후 조정하지 않음 — 미디어가 음성에 맞춤
3. **소스 기반**: AI가 사진/영상을 직접 보고 문장에 매칭
4. **분리된 관심사**: 스크립트 생성 → TTS → 타임라인 → 렌더가 독립적으로 동작
5. **재렌더 가능**: 소스 배치만 바꿔서 Claude 호출 없이 재렌더 가능
6. **깔끔한 전환**: 화면 전환 효과/페이드 없이 하드컷 — 깜빡임 방지
