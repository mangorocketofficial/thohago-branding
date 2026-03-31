from __future__ import annotations

import json
from pathlib import Path

from thohago.models import PublishConfig, SampleSession, ShopConfig


def load_shop_registry(registry_path: Path) -> dict[str, ShopConfig]:
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    root = registry_path.parent.parent.resolve()
    shops: dict[str, ShopConfig] = {}
    for raw_shop in payload.get("shops", []):
        sample_sessions: dict[str, SampleSession] = {}
        for key, raw_session in raw_shop.get("sample_sessions", {}).items():
            base_dir = (root / raw_session["base_dir"]).resolve()
            sample_sessions[key] = SampleSession(
                key=key,
                base_dir=base_dir,
                image_dir=(base_dir / raw_session["image_dir"]).resolve(),
                video_dir=(base_dir / raw_session["video_dir"]).resolve(),
                interview_dir=(base_dir / raw_session["interview_dir"]).resolve(),
                turn_transcript_files=[
                    (root / relative_path).resolve() for relative_path in raw_session["turn_transcript_files"]
                ],
            )

        shops[raw_shop["shop_id"]] = ShopConfig(
            shop_id=raw_shop["shop_id"],
            display_name=raw_shop["display_name"],
            invite_tokens=list(raw_shop.get("invite_tokens", [])),
            telegram_chat_ids=[str(chat_id) for chat_id in raw_shop.get("telegram_chat_ids", [])],
            publish=PublishConfig(
                provider=raw_shop.get("publish", {}).get("provider", "mock_naver"),
                targets=list(raw_shop.get("publish", {}).get("targets", ["naver_blog"])),
            ),
            media_hints=list(raw_shop.get("media_hints", [])),
            profile=dict(raw_shop.get("profile", {})),
            sample_sessions=sample_sessions,
        )
    return shops


def resolve_shop_by_chat_id(shops: dict[str, ShopConfig], chat_id: str) -> ShopConfig:
    for shop in shops.values():
        if chat_id in shop.telegram_chat_ids:
            return shop
    raise KeyError(f"No registered shop for chat id {chat_id}")


def resolve_shop_by_invite_token(shops: dict[str, ShopConfig], invite_token: str) -> ShopConfig:
    for shop in shops.values():
        if invite_token in shop.invite_tokens:
            return shop
    raise KeyError(f"No registered shop for invite token {invite_token}")
