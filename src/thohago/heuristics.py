from __future__ import annotations

import re
from collections import Counter


PRIORITY_ORDER = [
    "differentiator",
    "entry_channel",
    "customer_reaction",
    "location_advantage",
]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z가-힣0-9\-]{2,}", text)
    counts = Counter(token for token in tokens if token not in {"그리고", "이렇게", "정말", "오늘", "이번", "그런", "사진"})
    return [token for token, _ in counts.most_common(8)]


def detect_elements(text: str) -> list[str]:
    normalized = normalize_whitespace(text)
    detected: list[str] = []
    if any(keyword in normalized for keyword in ("예약", "리뷰", "SNS", "소개", "입소문", "관광", "찾아")):
        detected.append("entry_channel")
    if any(keyword in normalized for keyword in ("맞춤", "추천", "진단", "차별", "특별", "코스", "전문")):
        detected.append("differentiator")
    if any(keyword in normalized for keyword in ("좋", "만족", "놀라", "감동", "반응", "시원", "힐링")):
        detected.append("customer_reaction")
    if any(keyword in normalized for keyword in ("위치", "서면", "거리", "접근", "동선", "관광코스")):
        detected.append("location_advantage")
    return detected


def detect_main_angle(text: str) -> str:
    normalized = normalize_whitespace(text)
    if any(keyword in normalized for keyword in ("필리핀", "외국", "관광", "관광객")):
        return "외국인 관광객이 한국 방문 전에 미리 예약하는 경험"
    if "리뷰" in normalized or "입소문" in normalized:
        return "리뷰와 입소문으로 이어지는 방문 경험"
    if any(keyword in normalized for keyword in ("맞춤", "진단", "코스")):
        return "두피 진단 기반 맞춤 케어 경험"
    return "고객이 매장에서 겪은 인상적인 경험"


def choose_missing_elements(covered_elements: list[str]) -> list[str]:
    return [element for element in PRIORITY_ORDER if element not in covered_elements]


def choose_question_strategy(turn_index: int, covered_elements: list[str], specificity_score: float) -> str:
    missing = choose_missing_elements(covered_elements)
    if turn_index == 2 and specificity_score < 0.45:
        return "scene_probe"
    if not missing:
        return "scene_probe"
    if missing[0] == "customer_reaction":
        return "reaction_probe"
    if missing[0] == "differentiator":
        return "differentiator_probe"
    if missing[0] == "entry_channel":
        return "entry_channel_probe"
    return "location_probe"


def score_specificity(text: str) -> float:
    length_score = min(len(normalize_whitespace(text)) / 120.0, 1.0)
    keyword_score = min(len(extract_keywords(text)) / 6.0, 1.0)
    return round((length_score * 0.6) + (keyword_score * 0.4), 2)
