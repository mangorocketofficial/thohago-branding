"""Generate Threads post (3-part chain) from blog content.

Structure: Main post (hook) → Reply 1 (story + quotes) → Reply 2 (CTA)
Input: Blog HTML or narrative script + interview transcripts
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass

PROJ_ROOT = Path(__file__).resolve().parents[3]
INTERVIEW_PATH = PROJ_ROOT / "client" / "sisun8082" / "2026_03_27" / "interview" / "interview_transcripts.md"
BLOG_PATH = PROJ_ROOT / "client" / "sisun8082" / "2026_03_27" / "blog_preview" / "blog_content.html"
OUT_DIR = Path(__file__).resolve().parent / "thread_output"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    load_dotenv(PROJ_ROOT / ".env")
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or anthropic is None:
        print("CLAUDE_API_KEY required")
        return 1

    interview_text = INTERVIEW_PATH.read_text(encoding="utf-8") if INTERVIEW_PATH.exists() else ""
    blog_text = BLOG_PATH.read_text(encoding="utf-8") if BLOG_PATH.exists() else ""

    prompt = f"""당신은 쓰레드(Threads) 콘텐츠 작가입니다.

아래 블로그 글과 인터뷰 원문을 바탕으로, 쓰레드 3단 포스트를 만들어주세요.

## 블로그 원문
{blog_text}

## 인터뷰 원문 (샵 원장님 대화)
{interview_text}

## 샵 정보
- 이름: 시선을 즐기다
- 위치: 부산 서면 점포카페거리

## 쓰레드 3단 구조

1. **메인 포스트** (훅)
   - 스크롤을 멈추게 하는 핵심 에피소드
   - 호기심을 유발해서 댓글을 열어보게
   - 2~3줄 이내

2. **댓글 1** (스토리 + 인용)
   - 에피소드 전개 + 인터뷰 실제 멘트 인용
   - 읽는 사람이 "와 진짜?" 하고 느끼는 부분
   - 3~4줄 이내

3. **댓글 2** (CTA)
   - 샵 이름, 위치 자연스럽게 포함
   - 부드러운 마무리 (판매 느낌 아닌, 경험 공유 느낌)
   - 해시태그 2~3개
   - 2~3줄 이내

## 작성 지침

- 화자는 브랜드/샵 시점
- 캐주얼하고 친근한 톤 (쓰레드 특성)
- 이모지 적절히 활용 (과하지 않게)
- 각 파트가 독립적으로도 읽히지만, 이어서 읽으면 하나의 이야기

## 출력 형식 (JSON만)

```json
{{
  "main_post": "메인 포스트 텍스트",
  "reply_1": "댓글 1 텍스트",
  "reply_2": "댓글 2 텍스트"
}}
```

JSON만 출력하세요."""

    print("Generating thread via Claude...")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if "```" in text:
        lines = text.split("\n")
        clean = []
        inside = False
        for line in lines:
            if line.strip().startswith("```"):
                inside = not inside
                continue
            if inside:
                clean.append(line)
        text = "\n".join(clean).strip()

    result = json.loads(text)

    # Save JSON
    json_path = OUT_DIR / "thread_content.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save as plain text (copy-paste ready)
    txt_path = OUT_DIR / "thread_posts.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 50 + "\n")
        f.write("[메인 포스트]\n")
        f.write("=" * 50 + "\n")
        f.write(result["main_post"] + "\n\n")
        f.write("=" * 50 + "\n")
        f.write("[댓글 1]\n")
        f.write("=" * 50 + "\n")
        f.write(result["reply_1"] + "\n\n")
        f.write("=" * 50 + "\n")
        f.write("[댓글 2]\n")
        f.write("=" * 50 + "\n")
        f.write(result["reply_2"] + "\n")

    print(f"\nSaved: {json_path}")
    print(f"Saved: {txt_path}")

    print("\n" + "=" * 50)
    print("[메인 포스트]")
    print("=" * 50)
    print(result["main_post"])
    print("\n" + "=" * 50)
    print("[댓글 1]")
    print("=" * 50)
    print(result["reply_1"])
    print("\n" + "=" * 50)
    print("[댓글 2]")
    print("=" * 50)
    print(result["reply_2"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
