from __future__ import annotations

import re
from collections import Counter


def question_title_for_turn(turn_index: int) -> str:
    return {
        1: "첫번째 질문",
        2: "두번째 질문",
        3: "세번째 질문",
    }.get(turn_index, "질문")


def question_looks_invalid(text: str) -> bool:
    normalized = " ".join(text.split())
    if not normalized or len(normalized) < 8:
        return True
    if not re.search(r"[가-힣]", normalized):
        return True
    if normalized.endswith("입니다") or normalized.endswith("니다"):
        return True

    tokens = re.findall(r"[가-힣A-Za-z0-9]+", normalized)
    if tokens:
        ratio = len(set(tokens)) / len(tokens)
        if ratio < 0.55:
            return True
        counts = Counter(tokens)
        if any(len(token) >= 3 and count >= 3 for token, count in counts.items()):
            return True

    if not any(marker in normalized for marker in ("?", "요", "까요", "어떤", "어땠", "있다면", "느꼈", "들려")):
        return True

    return False
