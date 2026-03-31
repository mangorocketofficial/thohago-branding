# `shorts_beat_sheet.json` 스키마 명세

## 1. 목적

`shorts_beat_sheet.json`은 블로그에서 추출한 `story map`을 바탕으로, 실제 숏츠/릴스/쇼츠 영상을 편집하기 전에 필요한 **편집 기획 레이어**를 담는 JSON이다.

이 파일은 다음 질문에 답해야 한다.

- 이번 영상은 몇 초짜리로 만들 것인가?
- 어떤 감정 곡선으로 갈 것인가?
- 어떤 비트를 어떤 순서로 배치할 것인가?
- 각 비트에 몇 초를 쓸 것인가?
- 각 비트에서 어떤 종류의 소스를 우선 사용할 것인가?
- 각 비트에서 어떤 메시지를 전달해야 하는가?

즉, `shorts_beat_sheet.json`은 렌더링 명세가 아니라 **숏폼 영상의 설계도**다.

---

## 2. 상위 구조

```json
{
  "version": "1.0",
  "source": {},
  "duration": {},
  "editorial": {},
  "selection_rules": {},
  "beats": [],
  "script_budget": {},
  "validation": {}
}
```

---

## 3. 최상위 필드 정의

### 3.1 `version`

- 타입: `string`
- 필수 여부: 필수
- 설명: beat sheet 포맷 버전
- 예시: `"1.0"`

### 3.2 `source`

- 타입: `object`
- 필수 여부: 필수
- 설명: 어떤 블로그/story map/asset set을 바탕으로 생성되었는지 기록

### 3.3 `duration`

- 타입: `object`
- 필수 여부: 필수
- 설명: 총 길이와 길이 구간, 비트별 시간 배분 정보를 담음

### 3.4 `editorial`

- 타입: `object`
- 필수 여부: 필수
- 설명: 이번 영상의 편집 톤, 감정, 패턴, 훅 전략을 담음

### 3.5 `selection_rules`

- 타입: `object`
- 필수 여부: 필수
- 설명: 컷/사진/영상 선택 시 우선순위를 정의

### 3.6 `beats`

- 타입: `array<object>`
- 필수 여부: 필수
- 설명: 실제 숏츠를 구성하는 비트 목록

### 3.7 `script_budget`

- 타입: `object`
- 필수 여부: 필수
- 설명: 전체 및 비트별 자막/내레이션 예산

### 3.8 `validation`

- 타입: `object`
- 필수 여부: 필수
- 설명: 생성 후 검증에 사용할 규칙

---

## 4. `source` 스키마

```json
{
  "shop_id": "sisun8082",
  "session_id": "2026_03_27",
  "blog_story_map_id": "story_map_001",
  "main_angle": "필리핀 관광객 5명이 한국 오기 전부터 예약한 헤드스파 경험",
  "asset_counts": {
    "photos": 5,
    "videos": 2
  }
}
```

### 필드 설명

- `shop_id`: 샵 식별자
- `session_id`: 세션 식별자
- `blog_story_map_id`: 연결된 story map id
- `main_angle`: 블로그/세션의 핵심 angle
- `asset_counts`: 입력 소스 개수

---

## 5. `duration` 스키마

```json
{
  "available_video_sec": 20.0,
  "available_photo_sec_min": 7.5,
  "available_photo_sec_max": 12.5,
  "estimated_total_sec": 27.5,
  "target_output_sec": 23.0,
  "duration_band": "standard"
}
```

### 필드 설명

- `available_video_sec`
  - 원본 영상 클립 길이 총합
- `available_photo_sec_min`
  - 사진을 최소 홀드 시간으로 썼을 때 확보 가능한 길이
- `available_photo_sec_max`
  - 사진을 최대 홀드 시간으로 썼을 때 확보 가능한 길이
- `estimated_total_sec`
  - 이론상 사용 가능 총 길이
- `target_output_sec`
  - 실제 목표 출력 길이
- `duration_band`
  - 허용값:
    - `short`
    - `standard`
    - `extended`

### 권장 규칙

- `short`: 12~18초
- `standard`: 18~26초
- `extended`: 26~35초

---

## 6. `editorial` 스키마

```json
{
  "editorial_pattern": "tourist_reaction",
  "primary_emotion": "curiosity",
  "secondary_emotion": "delight",
  "hook_type": "angle_hook",
  "pace_curve": "fast_open_slow_finish",
  "caption_density": "low",
  "visual_style": "quiet_premium"
}
```

### 필드 설명

#### `editorial_pattern`

허용값 예시:

- `tourist_reaction`
- `group_visit_story`
- `first_time_kbeauty`
- `before_after_relief`
- `quiet_luxury_spa`
- `specialized_treatment`
- `local_hidden_gem`

#### `primary_emotion`

허용값 예시:

- `curiosity`
- `delight`
- `calm`
- `surprise`
- `trust`
- `premium`

#### `secondary_emotion`

선택 필드. 없을 수도 있다.

#### `hook_type`

허용값 예시:

- `angle_hook`
- `question_hook`
- `contrast_hook`
- `reaction_hook`
- `proof_hook`

#### `pace_curve`

허용값 예시:

- `fast_open_slow_finish`
- `steady`
- `slow_burn`
- `fast_all_the_way`

#### `caption_density`

- `low`
- `medium`
- `high`

#### `visual_style`

- `quiet_premium`
- `bright_social`
- `proof_driven`
- `emotional_soft`

---

## 7. `selection_rules` 스키마

```json
{
  "prefer_video_for": ["hook", "proof"],
  "prefer_photo_for": ["setup", "cta"],
  "max_photo_hold_sec": 2.5,
  "min_photo_hold_sec": 1.2,
  "max_single_clip_sec": 4.0,
  "allow_clip_trim": true,
  "allow_photo_repeat": false,
  "reaction_priority_order": [
    "customer_face",
    "customer_quote",
    "device_usage",
    "space_ambience"
  ]
}
```

### 필드 설명

- `prefer_video_for`
  - 특정 비트에서는 영상 우선
- `prefer_photo_for`
  - 특정 비트에서는 사진 우선
- `max_photo_hold_sec`
  - 사진 한 장 최대 유지 시간
- `min_photo_hold_sec`
  - 사진 한 장 최소 유지 시간
- `max_single_clip_sec`
  - 한 클립을 너무 길게 쓰지 않기 위한 제한
- `allow_clip_trim`
  - 원본 영상을 잘라서 사용할 수 있는지
- `allow_photo_repeat`
  - 사진 반복 사용 허용 여부
- `reaction_priority_order`
  - 반응 비트에서 어떤 증거를 우선할지

---

## 8. `beats` 스키마

핵심 필드다. 각 beat는 실제 영상의 하나의 기능 단위다.

```json
[
  {
    "beat_id": "b01",
    "name": "hook",
    "goal": "낯선 맥락으로 시선 붙잡기",
    "story_unit_ids": ["arrival_context"],
    "duration_sec": 3.0,
    "asset_preference": "video_first",
    "asset_selection_rule": "가장 강한 시각적 surprise 장면",
    "message_focus": "필리핀 관광객 5명이 한국 오기 전부터 예약",
    "caption_mode": "on_screen_hook",
    "voiceover_mode": "optional",
    "transition_in": "hard_cut",
    "transition_out": "soft_push"
  }
]
```

### 필드 정의

#### `beat_id`

- 타입: `string`
- 예시: `"b01"`

#### `name`

허용값:

- `hook`
- `setup`
- `contrast`
- `proof`
- `reaction`
- `cta`

#### `goal`

- 타입: `string`
- 설명: 이 비트가 해야 하는 기능

#### `story_unit_ids`

- 타입: `array<string>`
- 설명: 어떤 blog story unit를 압축한 비트인지

#### `duration_sec`

- 타입: `number`
- 설명: 해당 비트 길이

#### `asset_preference`

허용값:

- `video_first`
- `photo_first`
- `hybrid`

#### `asset_selection_rule`

- 타입: `string`
- 설명: 컷 선택 규칙

#### `message_focus`

- 타입: `string`
- 설명: 이 비트가 전달할 핵심 메시지

#### `caption_mode`

허용값:

- `none`
- `on_screen_hook`
- `supporting_text`
- `quote_text`
- `cta_text`

#### `voiceover_mode`

허용값:

- `none`
- `optional`
- `required`

#### `transition_in`

허용값 예시:

- `hard_cut`
- `fade`
- `soft_push`
- `zoom_cross`

#### `transition_out`

같은 방식으로 정의

---

## 9. `script_budget` 스키마

```json
{
  "total_caption_chars_max": 90,
  "total_voiceover_chars_max": 120,
  "per_beat": {
    "hook": {
      "caption_chars_max": 18,
      "voiceover_chars_max": 20
    },
    "setup": {
      "caption_chars_max": 24,
      "voiceover_chars_max": 28
    },
    "proof": {
      "caption_chars_max": 32,
      "voiceover_chars_max": 36
    },
    "reaction": {
      "caption_chars_max": 24,
      "voiceover_chars_max": 28
    },
    "cta": {
      "caption_chars_max": 18,
      "voiceover_chars_max": 20
    }
  }
}
```

### 역할

스크립트 생성 모델이 자유롭게 너무 길게 쓰지 못하게 제어한다.

---

## 10. `validation` 스키마

```json
{
  "required_beats": ["hook", "proof", "cta"],
  "max_total_duration_delta_sec": 1.0,
  "min_visual_evidence_count": 3,
  "forbid_duplicate_message_focus": true,
  "forbid_same_story_unit_back_to_back": true,
  "hook_must_use_strongest_angle": true
}
```

### 역할

생성된 beat sheet가 실제로 usable한지 검증하는 기준이다.

---

## 11. 완성 예시

```json
{
  "version": "1.0",
  "source": {
    "shop_id": "sisun8082",
    "session_id": "2026_03_27",
    "blog_story_map_id": "story_map_001",
    "main_angle": "필리핀 관광객 5명이 한국 오기 전부터 예약한 헤드스파 경험",
    "asset_counts": {
      "photos": 5,
      "videos": 2
    }
  },
  "duration": {
    "available_video_sec": 20.0,
    "available_photo_sec_min": 7.5,
    "available_photo_sec_max": 12.5,
    "estimated_total_sec": 27.5,
    "target_output_sec": 23.0,
    "duration_band": "standard"
  },
  "editorial": {
    "editorial_pattern": "tourist_reaction",
    "primary_emotion": "curiosity",
    "secondary_emotion": "delight",
    "hook_type": "angle_hook",
    "pace_curve": "fast_open_slow_finish",
    "caption_density": "low",
    "visual_style": "quiet_premium"
  },
  "selection_rules": {
    "prefer_video_for": ["hook", "proof"],
    "prefer_photo_for": ["setup", "cta"],
    "max_photo_hold_sec": 2.5,
    "min_photo_hold_sec": 1.2,
    "max_single_clip_sec": 4.0,
    "allow_clip_trim": true,
    "allow_photo_repeat": false,
    "reaction_priority_order": [
      "customer_face",
      "customer_quote",
      "device_usage",
      "space_ambience"
    ]
  },
  "beats": [
    {
      "beat_id": "b01",
      "name": "hook",
      "goal": "강한 방문 맥락으로 스크롤 정지",
      "story_unit_ids": ["arrival_context"],
      "duration_sec": 3.0,
      "asset_preference": "video_first",
      "asset_selection_rule": "가장 낯선 장면 또는 집단 방문을 보여주는 장면",
      "message_focus": "필리핀 관광객 5명이 한국 오기 전부터 예약했다",
      "caption_mode": "on_screen_hook",
      "voiceover_mode": "optional",
      "transition_in": "hard_cut",
      "transition_out": "soft_push"
    },
    {
      "beat_id": "b02",
      "name": "setup",
      "goal": "왜 이 경험이 특별한지 설명",
      "story_unit_ids": ["arrival_context", "shop_choice"],
      "duration_sec": 4.0,
      "asset_preference": "photo_first",
      "asset_selection_rule": "맥락이 잘 보이는 사진",
      "message_focus": "관광 동선 안에서 헤드스파를 선택한 이유",
      "caption_mode": "supporting_text",
      "voiceover_mode": "optional",
      "transition_in": "soft_push",
      "transition_out": "fade"
    },
    {
      "beat_id": "b03",
      "name": "proof",
      "goal": "기술과 차별점 증명",
      "story_unit_ids": ["treatment_proof"],
      "duration_sec": 6.0,
      "asset_preference": "hybrid",
      "asset_selection_rule": "LED, 진단 장비, 실제 관리 과정이 보이는 장면",
      "message_focus": "스팀캡, LED, 두피 진단 같은 한국식 관리 증거",
      "caption_mode": "supporting_text",
      "voiceover_mode": "required",
      "transition_in": "fade",
      "transition_out": "hard_cut"
    },
    {
      "beat_id": "b04",
      "name": "reaction",
      "goal": "감정 피크 전달",
      "story_unit_ids": ["reaction_peak"],
      "duration_sec": 6.0,
      "asset_preference": "video_first",
      "asset_selection_rule": "표정, 반응, 후기와 연결되는 장면",
      "message_focus": "K-뷰티 최고라는 반응",
      "caption_mode": "quote_text",
      "voiceover_mode": "optional",
      "transition_in": "hard_cut",
      "transition_out": "soft_push"
    },
    {
      "beat_id": "b05",
      "name": "cta",
      "goal": "부드럽게 마무리",
      "story_unit_ids": ["closing"],
      "duration_sec": 4.0,
      "asset_preference": "photo_first",
      "asset_selection_rule": "공간/결과/브랜드가 잘 보이는 장면",
      "message_focus": "서면 오면 쉬어가기 좋은 헤드스파",
      "caption_mode": "cta_text",
      "voiceover_mode": "optional",
      "transition_in": "soft_push",
      "transition_out": "fade"
    }
  ],
  "script_budget": {
    "total_caption_chars_max": 90,
    "total_voiceover_chars_max": 120,
    "per_beat": {
      "hook": { "caption_chars_max": 18, "voiceover_chars_max": 20 },
      "setup": { "caption_chars_max": 24, "voiceover_chars_max": 28 },
      "proof": { "caption_chars_max": 32, "voiceover_chars_max": 36 },
      "reaction": { "caption_chars_max": 24, "voiceover_chars_max": 28 },
      "cta": { "caption_chars_max": 18, "voiceover_chars_max": 20 }
    }
  },
  "validation": {
    "required_beats": ["hook", "proof", "cta"],
    "max_total_duration_delta_sec": 1.0,
    "min_visual_evidence_count": 3,
    "forbid_duplicate_message_focus": true,
    "forbid_same_story_unit_back_to_back": true,
    "hook_must_use_strongest_angle": true
  }
}
```

---

## 12. 생성 규칙 요약

`shorts_beat_sheet.json` 생성 시 시스템은 다음 규칙을 따라야 한다.

1. 블로그를 먼저 읽고 `story map`을 만든다
2. 사용 가능한 총 길이를 계산한다
3. `duration_band`를 선택한다
4. 해당 길이 구간에 맞는 기본 beat 구조를 고른다
5. 각 beat에 story unit를 매핑한다
6. 각 beat에 시간과 script budget을 할당한다
7. 최종 검증 규칙을 통과하는지 검사한다

---

## 13. 구현 시 주의점

- beat 수는 많을수록 좋은 것이 아니다
- 짧은 영상일수록 message_focus는 더 강하게 압축되어야 한다
- `hook`과 `reaction`은 절대 약하면 안 된다
- `proof`가 없는 숏츠는 예쁘기만 하고 신뢰감이 없다
- `cta`는 판매 문구보다 경험 마무리로 다루는 것이 자연스럽다
- 사진 기반 숏츠에서는 `photo hold duration`과 `caption density`가 지나치게 높아지지 않도록 제어해야 한다

---

## 14. 결론

`shorts_beat_sheet.json`은 영상 렌더링 이전 단계에서

- 감정 곡선
- 비트 구조
- 메시지 압축
- 길이 제약

을 통제하는 핵심 파일이다.

이 스키마가 잘 정의되어야 이후의 `shorts_render_spec.json`도 안정적으로 생성할 수 있다.
