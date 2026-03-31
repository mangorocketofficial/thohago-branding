# `blog_story_map.json` 스키마 명세

## 1. 목적

`blog_story_map.json`은 블로그 본문과 원본 세션 맥락을 구조화한 파일이다.

이 파일은 다음 질문에 답해야 한다.

- 이번 세션의 핵심 angle은 무엇인가?
- 블로그 안에서 어떤 장면/정보 단위가 중요한가?
- 각 장면은 어떤 역할을 하는가?
- 어떤 사진과 영상이 어떤 story unit에 대응하는가?
- 숏츠로 압축할 때 무엇을 남기고 무엇을 버려야 하는가?

즉, `blog_story_map.json`은

- 블로그 본문
- 인터뷰 전사
- 사진/영상 의미

를 편집 가능한 story unit 단위로 정리하는 **의미 구조 레이어**다.

---

## 2. 상위 구조

```json
{
  "version": "1.0",
  "source": {},
  "summary": {},
  "story_units": [],
  "compression_hints": {},
  "validation": {}
}
```

---

## 3. 최상위 필드 정의

### 3.1 `version`

- 타입: `string`
- 필수 여부: 필수
- 예시: `"1.0"`

### 3.2 `source`

- 타입: `object`
- 필수 여부: 필수
- 설명: 어떤 세션, 어떤 블로그, 어떤 인터뷰와 연결되는지 기록

### 3.3 `summary`

- 타입: `object`
- 필수 여부: 필수
- 설명: 전체 세션의 angle, 톤, 구조를 요약

### 3.4 `story_units`

- 타입: `array<object>`
- 필수 여부: 필수
- 설명: 블로그를 구성하는 핵심 의미 단위

### 3.5 `compression_hints`

- 타입: `object`
- 필수 여부: 필수
- 설명: 숏츠로 압축할 때 어떤 unit를 우선할지, 무엇을 버릴 수 있는지 힌트 제공

### 3.6 `validation`

- 타입: `object`
- 필수 여부: 필수
- 설명: story map 품질 검증 규칙

---

## 4. `source` 스키마

```json
{
  "shop_id": "sisun8082",
  "session_id": "2026_03_27",
  "content_bundle_id": "bundle_001",
  "blog_article_path": "generated/naver_blog_article.md",
  "photo_count": 5,
  "video_count": 2
}
```

### 필드 설명

- `shop_id`: 샵 식별자
- `session_id`: 세션 식별자
- `content_bundle_id`: 참조하는 content bundle id
- `blog_article_path`: 블로그 원문 경로 또는 id
- `photo_count`: 사진 수
- `video_count`: 영상 수

---

## 5. `summary` 스키마

```json
{
  "main_angle": "필리핀 관광객 5명이 한국 오기 전부터 예약한 헤드스파 경험",
  "main_angle_strength": 0.93,
  "primary_story_type": "tourist_group_experience",
  "dominant_emotion": "curiosity",
  "secondary_emotion": "delight",
  "blog_structure_mode": "narrative_flow",
  "compression_recommendation": "reaction_led"
}
```

### 필드 설명

#### `main_angle`

- 타입: `string`
- 설명: 세션의 핵심 마케팅 angle

#### `main_angle_strength`

- 타입: `number`
- 범위: `0.0 ~ 1.0`
- 설명: angle의 선명도

#### `primary_story_type`

허용값 예시:

- `tourist_group_experience`
- `first_time_visit`
- `specialized_treatment`
- `reaction_story`
- `local_convenience_story`
- `quiet_luxury_story`

#### `dominant_emotion`

허용값 예시:

- `curiosity`
- `delight`
- `trust`
- `calm`
- `surprise`
- `premium`

#### `secondary_emotion`

- 선택 필드

#### `blog_structure_mode`

허용값:

- `narrative_flow`
- `key_moments`
- `proof_points`

#### `compression_recommendation`

숏츠로 압축할 때 추천되는 방향

예:

- `reaction_led`
- `proof_first`
- `tourist_hook`
- `quiet_luxury`

---

## 6. `story_units` 스키마

이 배열이 핵심이다.

각 story unit은 블로그 안의 의미 단위를 표현한다.

### 예시

```json
[
  {
    "unit_id": "u01",
    "type": "context",
    "title": "한국 오기 전 미리 예약한 단체 고객",
    "summary": "필리핀 관광객 5명이 한국 오기 전에 예약했다",
    "importance": 0.94,
    "emotion_weight": 0.78,
    "compression_priority": 0.96,
    "blog_section_order": 1,
    "photo_ids": ["photo_1"],
    "video_ids": [],
    "content_roles": ["hook", "setup"],
    "proof_strength": "medium",
    "quote_candidates": [
      "필리핀 관광객 5명이 한국 오기 전부터 예약"
    ]
  }
]
```

### 필드 정의

#### `unit_id`

- 타입: `string`
- 예시: `"u01"`

#### `type`

허용값:

- `context`
- `arrival`
- `setup`
- `proof`
- `reaction`
- `differentiator`
- `location`
- `closing`
- `cta`

#### `title`

- 타입: `string`
- 설명: 사람이 읽기 쉬운 짧은 제목

#### `summary`

- 타입: `string`
- 설명: story unit의 핵심 의미

#### `importance`

- 타입: `number`
- 범위: `0.0 ~ 1.0`
- 설명: 블로그 전체에서의 중요도

#### `emotion_weight`

- 타입: `number`
- 범위: `0.0 ~ 1.0`
- 설명: 감정 곡선에서의 강도

#### `compression_priority`

- 타입: `number`
- 범위: `0.0 ~ 1.0`
- 설명: 숏츠로 압축할 때 우선 유지해야 하는 정도

#### `blog_section_order`

- 타입: `integer`
- 설명: 블로그 상 등장 순서

#### `photo_ids`

- 타입: `array<string>`
- 설명: 이 unit에 연결된 사진

#### `video_ids`

- 타입: `array<string>`
- 설명: 이 unit에 연결된 영상

#### `content_roles`

허용값 예시:

- `hook`
- `setup`
- `proof`
- `reaction`
- `cta`

하나의 unit가 여러 역할을 가질 수 있다.

#### `proof_strength`

허용값:

- `low`
- `medium`
- `high`

#### `quote_candidates`

- 타입: `array<string>`
- 설명: 자막/내레이션/후기 포인트로 바로 쓸 수 있는 문장 후보

---

## 7. `compression_hints` 스키마

```json
{
  "must_keep_unit_ids": ["u01", "u03", "u05"],
  "optional_unit_ids": ["u02", "u04"],
  "drop_first_unit_ids": ["u06"],
  "best_hook_unit_id": "u01",
  "best_reaction_unit_id": "u05",
  "best_proof_unit_id": "u03",
  "recommended_editorial_patterns": [
    "tourist_reaction",
    "group_visit_story"
  ]
}
```

### 역할

story map이 이미 숏츠 압축 방향까지 일부 제안하는 레이어다.

### 필드 설명

- `must_keep_unit_ids`
  - 어떤 길이에서도 가급적 유지할 unit
- `optional_unit_ids`
  - 길이 여유가 있을 때만 포함할 unit
- `drop_first_unit_ids`
  - 가장 먼저 버려도 되는 unit
- `best_hook_unit_id`
  - Hook로 가장 강한 unit
- `best_reaction_unit_id`
  - 감정 피크로 가장 강한 unit
- `best_proof_unit_id`
  - 장비/과정/증거로 강한 unit
- `recommended_editorial_patterns`
  - beat sheet 생성 시 추천 패턴

---

## 8. `validation` 스키마

```json
{
  "min_story_unit_count": 3,
  "require_main_angle": true,
  "require_hook_candidate": true,
  "require_proof_candidate": true,
  "require_reaction_candidate": true,
  "forbid_empty_summary": true
}
```

### 역할

story map 자체가 너무 빈약하거나 압축 불가능한 상태가 아닌지 점검

---

## 9. 완성 예시

```json
{
  "version": "1.0",
  "source": {
    "shop_id": "sisun8082",
    "session_id": "2026_03_27",
    "content_bundle_id": "bundle_001",
    "blog_article_path": "generated/naver_blog_article.md",
    "photo_count": 5,
    "video_count": 2
  },
  "summary": {
    "main_angle": "필리핀 관광객 5명이 한국 오기 전부터 예약한 헤드스파 경험",
    "main_angle_strength": 0.93,
    "primary_story_type": "tourist_group_experience",
    "dominant_emotion": "curiosity",
    "secondary_emotion": "delight",
    "blog_structure_mode": "narrative_flow",
    "compression_recommendation": "tourist_hook"
  },
  "story_units": [
    {
      "unit_id": "u01",
      "type": "context",
      "title": "한국 오기 전 예약한 5인 단체",
      "summary": "필리핀 관광객 5명이 한국 방문 전에 미리 예약했다",
      "importance": 0.94,
      "emotion_weight": 0.78,
      "compression_priority": 0.96,
      "blog_section_order": 1,
      "photo_ids": ["photo_1"],
      "video_ids": [],
      "content_roles": ["hook", "setup"],
      "proof_strength": "medium",
      "quote_candidates": [
        "필리핀 손님 5명이 한국 오기 전부터 예약했다"
      ]
    },
    {
      "unit_id": "u02",
      "type": "proof",
      "title": "두피 진단과 LED 관리",
      "summary": "스팀캡, LED, 두피 진단 장비가 시술의 증거로 제시된다",
      "importance": 0.91,
      "emotion_weight": 0.62,
      "compression_priority": 0.94,
      "blog_section_order": 2,
      "photo_ids": ["photo_2", "photo_4"],
      "video_ids": ["video_1"],
      "content_roles": ["proof"],
      "proof_strength": "high",
      "quote_candidates": [
        "한국식 관리 장비가 확실히 보인다"
      ]
    },
    {
      "unit_id": "u03",
      "type": "reaction",
      "title": "K-뷰티 최고라는 반응",
      "summary": "고객들이 K-뷰티와 한국 기술력에 강한 만족 반응을 보였다",
      "importance": 0.97,
      "emotion_weight": 0.95,
      "compression_priority": 0.98,
      "blog_section_order": 3,
      "photo_ids": ["photo_3", "photo_5"],
      "video_ids": [],
      "content_roles": ["reaction"],
      "proof_strength": "medium",
      "quote_candidates": [
        "K-뷰티 최고예요",
        "너무 시원하고 만족스러워요"
      ]
    },
    {
      "unit_id": "u04",
      "type": "location",
      "title": "서면 관광 동선 안의 위치 장점",
      "summary": "서면 핫플레이스 동선 안에 있어 관광 코스 중 들르기 좋다",
      "importance": 0.74,
      "emotion_weight": 0.31,
      "compression_priority": 0.62,
      "blog_section_order": 4,
      "photo_ids": [],
      "video_ids": [],
      "content_roles": ["setup", "cta"],
      "proof_strength": "low",
      "quote_candidates": [
        "서면 관광 코스 안에서 쉬어가기 좋다"
      ]
    }
  ],
  "compression_hints": {
    "must_keep_unit_ids": ["u01", "u02", "u03"],
    "optional_unit_ids": ["u04"],
    "drop_first_unit_ids": [],
    "best_hook_unit_id": "u01",
    "best_reaction_unit_id": "u03",
    "best_proof_unit_id": "u02",
    "recommended_editorial_patterns": [
      "tourist_reaction",
      "group_visit_story"
    ]
  },
  "validation": {
    "min_story_unit_count": 3,
    "require_main_angle": true,
    "require_hook_candidate": true,
    "require_proof_candidate": true,
    "require_reaction_candidate": true,
    "forbid_empty_summary": true
  }
}
```

---

## 10. 생성 규칙 요약

`blog_story_map.json` 생성 시 시스템은 아래 순서를 따라야 한다.

1. 블로그 본문을 읽는다
2. 인터뷰 전사와 사진/영상 context를 연결한다
3. 블로그를 3~7개의 story unit으로 분해한다
4. 각 unit에 중요도/감정/압축 우선순위를 부여한다
5. 숏츠용 hook/proof/reaction 후보를 선택한다
6. compression hints를 생성한다

---

## 11. 구현 시 주의점

- story unit 수가 너무 많으면 beat sheet 생성이 흔들린다
- 너무 큰 문단 단위가 아니라, 실제로 편집 가능한 의미 단위로 나눠야 한다
- `main_angle`는 추상 명사형이 아니라 실제 마케팅 hook이 되도록 써야 한다
- `compression_priority`는 블로그 중요도와 같지 않을 수 있다
  - 블로그에서는 중요하지만 숏츠에서는 버릴 unit도 있다
- `quote_candidates`는 가능한 한 실제 인터뷰 표현을 살려야 한다

---

## 12. 결론

`blog_story_map.json`은 블로그를 영상 기획 가능한 구조로 바꾸는 첫 번째 단계다.

정리하면:

- `blog_story_map.json`은 의미 구조
- `shorts_beat_sheet.json`은 편집 구조
- `shorts_render_spec.json`은 실행 구조

이며, 세 단계가 연결되어야 숏츠 영상 생성 로직이 완성된다.
