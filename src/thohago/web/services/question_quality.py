from __future__ import annotations

import re
from collections import Counter

OWNER_ANCHOR_MARKERS = (
    "사장님",
    "보시기",
    "보신",
    "기억",
    "느끼신",
    "생각",
    "신경",
    "고객 반응",
    "표정",
    "대화",
    "행동",
)

CUSTOMER_INNER_STATE_PATTERNS = (
    r"(고객|손님).*(느낌|기분|마음|생각|만족|감정)",
    r"(느낌|기분|마음|생각|만족|감정).*(고객|손님)",
)

SERVICE_RECIPIENT_PATTERNS = (
    "마사지되는 순간",
    "시술을 받",
    "케어를 받",
    "관리받",
    "헤드 스파를 받",
    "장비에 의해",
    "누워 계실 때",
    "안대를 하고",
)


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

    if _targets_unobservable_customer_inner_state(normalized):
        return True

    if _implies_owner_is_service_recipient(normalized):
        return True

    return False


def _targets_unobservable_customer_inner_state(normalized: str) -> bool:
    return any(re.search(pattern, normalized) for pattern in CUSTOMER_INNER_STATE_PATTERNS)


def _implies_owner_is_service_recipient(normalized: str) -> bool:
    if any(marker in normalized for marker in OWNER_ANCHOR_MARKERS):
        return False
    if any(pattern in normalized for pattern in SERVICE_RECIPIENT_PATTERNS):
        if any(ending in normalized for ending in ("어떤 느낌이셨나요", "어떠셨나요", "편안하셨나요", "만족하셨나요")):
            return True
    return False
