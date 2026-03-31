# `shorts_render_spec.json` 스키마 명세

## 1. 목적

`shorts_render_spec.json`은 `shorts_beat_sheet.json`을 실제 렌더링 가능한 수준으로 변환한 실행 명세다.

이 파일은 다음 질문에 답해야 한다.

- 어떤 사진/영상을 어떤 순서로 쓸 것인가?
- 각 컷은 몇 초 동안 유지되는가?
- 사진에는 어떤 Ken Burns 모션을 줄 것인가?
- 자막과 텍스트는 언제, 어디에, 어떤 스타일로 넣을 것인가?
- 배경음악과 내레이션은 어떻게 배치할 것인가?
- 최종 출력 포맷은 무엇인가?

즉, `shorts_render_spec.json`은 편집 기획 파일이 아니라 **렌더링 실행 파일**이다.

---

## 2. 상위 구조

```json
{
  "version": "1.0",
  "source": {},
  "timeline": [],
  "text_overlays": [],
  "voiceover": {},
  "audio": {},
  "visual_effects": {},
  "export": {},
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
- 설명: 이 render spec이 어떤 beat sheet와 어떤 세션에서 파생되었는지 기록

### 3.3 `timeline`

- 타입: `array<object>`
- 필수 여부: 필수
- 설명: 실제 컷 배치와 시간축을 정의

### 3.4 `text_overlays`

- 타입: `array<object>`
- 필수 여부: 선택
- 설명: on-screen text, quote, CTA 등의 자막/텍스트 오버레이

### 3.5 `voiceover`

- 타입: `object`
- 필수 여부: 선택
- 설명: TTS 또는 녹음 기반 내레이션 구조

### 3.6 `audio`

- 타입: `object`
- 필수 여부: 필수
- 설명: BGM, 원본 오디오, 믹싱 정책

### 3.7 `visual_effects`

- 타입: `object`
- 필수 여부: 선택
- 설명: 전반적인 색감, 전환, 룩앤필 정책

### 3.8 `export`

- 타입: `object`
- 필수 여부: 필수
- 설명: 최종 렌더링 포맷

### 3.9 `validation`

- 타입: `object`
- 필수 여부: 필수
- 설명: 렌더링 전후 검증 규칙

---

## 4. `source` 스키마

```json
{
  "shop_id": "sisun8082",
  "session_id": "2026_03_27",
  "story_map_id": "story_map_001",
  "beat_sheet_id": "beat_sheet_001",
  "target_duration_sec": 23.0
}
```

### 필드 설명

- `shop_id`: 샵 식별자
- `session_id`: 세션 식별자
- `story_map_id`: 참조하는 story map id
- `beat_sheet_id`: 참조하는 beat sheet id
- `target_duration_sec`: 목표 출력 길이

---

## 5. `timeline` 스키마

`timeline`은 실제 컷 단위 실행 계획이다.

### 예시

```json
[
  {
    "clip_id": "c01",
    "beat_id": "b01",
    "asset_type": "video",
    "asset_id": "video_01",
    "source_path": "assets/raw/video_01.mp4",
    "start_sec": 0.0,
    "end_sec": 2.8,
    "duration_sec": 2.8,
    "trim": {
      "source_in_sec": 1.2,
      "source_out_sec": 4.0
    },
    "motion": {
      "type": "none"
    },
    "transition_in": "hard_cut",
    "transition_out": "soft_push",
    "caption_ids": ["t01"]
  }
]
```

### 필드 설명

#### `clip_id`

- 타입: `string`
- 컷 식별자

#### `beat_id`

- 타입: `string`
- 어떤 beat에 속하는지

#### `asset_type`

허용값:

- `video`
- `photo`
- `generated_background`

#### `asset_id`

- 타입: `string`
- 소스 식별자

#### `source_path`

- 타입: `string`
- 실제 파일 경로

#### `start_sec`

- 타입: `number`
- 타임라인 상 시작 시간

#### `end_sec`

- 타입: `number`
- 타임라인 상 종료 시간

#### `duration_sec`

- 타입: `number`
- 컷 길이

#### `trim`

영상인 경우:

```json
{
  "source_in_sec": 1.2,
  "source_out_sec": 4.0
}
```

사진인 경우:

```json
{
  "source_in_sec": null,
  "source_out_sec": null
}
```

#### `motion`

사진 기반 컷에서 중요하다.

예:

```json
{
  "type": "ken_burns",
  "preset": "slow_push_in",
  "anchor": "center",
  "scale_from": 1.0,
  "scale_to": 1.08
}
```

허용값 예시:

- `none`
- `ken_burns`
- `static_hold`
- `subtle_pan`

#### `transition_in`, `transition_out`

허용값 예시:

- `hard_cut`
- `fade`
- `soft_push`
- `zoom_cross`
- `dip_to_black`

#### `caption_ids`

- 타입: `array<string>`
- 이 컷에 연결된 텍스트 오버레이 id 목록

---

## 6. `text_overlays` 스키마

### 예시

```json
[
  {
    "text_id": "t01",
    "kind": "hook",
    "text": "한국 오기 전부터 왜 예약했을까?",
    "start_sec": 0.0,
    "end_sec": 2.4,
    "position": "center",
    "style_preset": "hook_bold",
    "animation_in": "fade_up",
    "animation_out": "fade_out"
  }
]
```

### 필드 설명

#### `kind`

허용값:

- `hook`
- `supporting`
- `quote`
- `cta`
- `label`

#### `position`

허용값 예시:

- `top_left`
- `top_center`
- `center`
- `bottom_left`
- `bottom_center`

#### `style_preset`

허용값 예시:

- `hook_bold`
- `quote_soft`
- `cta_clean`
- `label_minimal`

#### `animation_in`, `animation_out`

허용값 예시:

- `none`
- `fade_up`
- `fade_in`
- `slide_up`
- `typewriter`

---

## 7. `voiceover` 스키마

### 예시

```json
{
  "mode": "tts",
  "script_blocks": [
    {
      "beat_id": "b01",
      "text": "필리핀 손님 다섯 분이 한국 오기 전부터 예약했어요.",
      "start_sec": 0.0,
      "end_sec": 2.8,
      "tone": "curious_warm"
    }
  ],
  "subtitle_mode": "burned_in",
  "subtitle_style": "clean_bottom"
}
```

### 필드 설명

#### `mode`

허용값:

- `none`
- `tts`
- `recorded_voice`

#### `script_blocks`

- beat 단위 또는 컷 단위로 voiceover 텍스트를 담는다

#### `subtitle_mode`

- `none`
- `burned_in`
- `external_srt`

#### `subtitle_style`

- `clean_bottom`
- `center_dynamic`
- `minimal`

---

## 8. `audio` 스키마

### 예시

```json
{
  "bgm": {
    "mode": "library",
    "mood": "lofi_warm",
    "volume": 0.45,
    "duck_under_voiceover": true
  },
  "original_audio": {
    "use": false,
    "volume": 0.0
  },
  "mixing": {
    "normalize_output": true,
    "peak_db": -1.0
  }
}
```

### 필드 설명

#### `bgm.mode`

- `none`
- `library`
- `uploaded`

#### `bgm.mood`

예시:

- `lofi_warm`
- `quiet_premium`
- `bright_clean`
- `emotional_soft`

#### `duck_under_voiceover`

- `true`면 voiceover 구간에서 음악 볼륨 자동 감소

#### `original_audio.use`

- 영상 원본 소리를 쓸지 여부

---

## 9. `visual_effects` 스키마

### 예시

```json
{
  "color_grade": {
    "preset": "warm_soft",
    "intensity": 0.6
  },
  "vignette": {
    "enabled": true,
    "intensity": 0.15
  },
  "safe_zone": {
    "top_pct": 15,
    "bottom_pct": 20,
    "side_pct": 8
  }
}
```

### 설명

- 전체 영상에 걸친 룩을 관리
- 자막/오버레이가 플랫폼 UI와 겹치지 않도록 safe zone 규칙 포함

---

## 10. `export` 스키마

### 예시

```json
{
  "aspect_ratio": "9:16",
  "resolution": {
    "width": 1080,
    "height": 1920
  },
  "fps": 30,
  "codec": "h264",
  "video_bitrate": "8M",
  "audio_codec": "aac",
  "audio_bitrate": "192k",
  "container": "mp4"
}
```

### 설명

- 플랫폼 업로드용 포맷 정의

---

## 11. `validation` 스키마

### 예시

```json
{
  "max_duration_delta_sec": 0.5,
  "require_hook_in_first_sec": true,
  "max_text_chars_per_screen": 22,
  "require_cta_in_last_sec": true,
  "allow_empty_voiceover": true,
  "require_min_clip_count": 4
}
```

### 설명

- 렌더링 전후 QA 규칙
- 시간 오차, 자막 길이, 훅 위치, CTA 위치 등을 검증

---

## 12. 완성 예시

```json
{
  "version": "1.0",
  "source": {
    "shop_id": "sisun8082",
    "session_id": "2026_03_27",
    "story_map_id": "story_map_001",
    "beat_sheet_id": "beat_sheet_001",
    "target_duration_sec": 23.0
  },
  "timeline": [
    {
      "clip_id": "c01",
      "beat_id": "b01",
      "asset_type": "video",
      "asset_id": "video_01",
      "source_path": "assets/raw/video_01.mp4",
      "start_sec": 0.0,
      "end_sec": 2.8,
      "duration_sec": 2.8,
      "trim": { "source_in_sec": 1.2, "source_out_sec": 4.0 },
      "motion": { "type": "none" },
      "transition_in": "hard_cut",
      "transition_out": "soft_push",
      "caption_ids": ["t01"]
    },
    {
      "clip_id": "c02",
      "beat_id": "b02",
      "asset_type": "photo",
      "asset_id": "photo_02",
      "source_path": "assets/raw/photo_02.jpg",
      "start_sec": 2.8,
      "end_sec": 6.2,
      "duration_sec": 3.4,
      "trim": { "source_in_sec": null, "source_out_sec": null },
      "motion": {
        "type": "ken_burns",
        "preset": "slow_push_in",
        "anchor": "center",
        "scale_from": 1.0,
        "scale_to": 1.08
      },
      "transition_in": "soft_push",
      "transition_out": "fade",
      "caption_ids": ["t02"]
    }
  ],
  "text_overlays": [
    {
      "text_id": "t01",
      "kind": "hook",
      "text": "한국 오기 전부터 왜 예약했을까?",
      "start_sec": 0.0,
      "end_sec": 2.4,
      "position": "center",
      "style_preset": "hook_bold",
      "animation_in": "fade_up",
      "animation_out": "fade_out"
    }
  ],
  "voiceover": {
    "mode": "tts",
    "script_blocks": [
      {
        "beat_id": "b01",
        "text": "필리핀 손님 다섯 분이 한국 오기 전부터 예약했어요.",
        "start_sec": 0.0,
        "end_sec": 2.8,
        "tone": "curious_warm"
      }
    ],
    "subtitle_mode": "burned_in",
    "subtitle_style": "clean_bottom"
  },
  "audio": {
    "bgm": {
      "mode": "library",
      "mood": "lofi_warm",
      "volume": 0.45,
      "duck_under_voiceover": true
    },
    "original_audio": {
      "use": false,
      "volume": 0.0
    },
    "mixing": {
      "normalize_output": true,
      "peak_db": -1.0
    }
  },
  "visual_effects": {
    "color_grade": {
      "preset": "warm_soft",
      "intensity": 0.6
    },
    "vignette": {
      "enabled": true,
      "intensity": 0.15
    },
    "safe_zone": {
      "top_pct": 15,
      "bottom_pct": 20,
      "side_pct": 8
    }
  },
  "export": {
    "aspect_ratio": "9:16",
    "resolution": {
      "width": 1080,
      "height": 1920
    },
    "fps": 30,
    "codec": "h264",
    "video_bitrate": "8M",
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "container": "mp4"
  },
  "validation": {
    "max_duration_delta_sec": 0.5,
    "require_hook_in_first_sec": true,
    "max_text_chars_per_screen": 22,
    "require_cta_in_last_sec": true,
    "allow_empty_voiceover": true,
    "require_min_clip_count": 4
  }
}
```

---

## 13. 생성 규칙 요약

`shorts_render_spec.json` 생성 시 시스템은 아래 순서를 따라야 한다.

1. `shorts_beat_sheet.json`을 읽는다
2. 각 beat에 맞는 실제 소스를 선택한다
3. 컷 순서와 타이밍을 계산한다
4. 자막과 voiceover를 beat별로 배치한다
5. audio, transition, motion을 결정한다
6. export와 validation을 채운다

---

## 14. 구현 시 주의점

- `timeline.duration_sec` 총합은 `target_duration_sec`와 크게 어긋나면 안 된다
- 같은 컷을 반복할 경우 `allow_photo_repeat` 또는 별도 규칙이 있어야 한다
- 텍스트가 너무 많으면 숏폼 리듬이 무너진다
- `hook`는 0~2초 구간에 반드시 들어가야 한다
- `proof` 없는 영상은 감성적이어도 설득력이 약하다
- `reaction` 없는 영상은 기억에 남지 않는다

---

## 15. 결론

`shorts_render_spec.json`은 실제 편집 엔진이 이해할 수 있는 최종 실행 명세다.

정리하면:

- `story map`은 의미 구조
- `beat sheet`는 편집 구조
- `render spec`은 실행 구조

이며, 이 3단계가 분리되어야 숏츠 영상 생성이 반복 가능하고 안정적으로 운영될 수 있다.
