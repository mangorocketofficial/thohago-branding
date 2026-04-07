from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if (
            len(value) >= 2
            and value.startswith(('"', "'"))
            and value.endswith(('"', "'"))
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

    from sidecar.dispatcher import (
        publish_instagram_carousel,
        publish_instagram_reels,
        publish_naver_blog,
        publish_threads,
    )

    load_env_file(repo_root / ".env")

    fixture_root = repo_root / "client" / "sisun8082" / "2026_03_27" / "images"
    image_paths = [
        fixture_root / "KakaoTalk_20260327_121540482.jpg",
        fixture_root / "KakaoTalk_20260327_121540482_01.jpg",
    ]
    existing_images = [str(path) for path in image_paths if path.exists()]

    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "instagram_carousel_live": publish_instagram_carousel(
            {
                "project_id": "phase9-live-check",
                "execution_mode": "live",
                "caption": "Phase 9 live execution verification",
                "image_paths": existing_images,
                "graph_meta_access_token": os.environ.get("GRAPH_META_ACCESS_TOKEN", ""),
                "instagram_business_account_id": os.environ.get(
                    "INSTAGRAM_BUSINESS_ACCOUNT_ID", ""
                ),
                "facebook_page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),
                "instagram_graph_version": os.environ.get(
                    "INSTAGRAM_GRAPH_VERSION", "v23.0"
                ),
            }
        ),
        "threads_live": publish_threads(
            {
                "project_id": "phase9-live-check",
                "execution_mode": "live",
                "text": "Phase 9 live execution verification",
                "image_paths": existing_images[:1],
                "threads_access_token": os.environ.get("THREADS_ACCESS_TOKEN", ""),
                "threads_user_id": os.environ.get("THREADS_USER_ID", ""),
                "facebook_page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),
                "instagram_graph_version": os.environ.get(
                    "INSTAGRAM_GRAPH_VERSION", "v23.0"
                ),
            }
        ),
        "naver_live": publish_naver_blog(
            {
                "project_id": "phase9-live-check",
                "execution_mode": "live",
                "naver_live_note": "manual desktop note",
            }
        ),
        "instagram_reels_live": publish_instagram_reels(
            {
                "project_id": "phase9-live-check",
                "execution_mode": "live",
                "video_path": None,
            }
        ),
    }

    output_dir = repo_root / "apps" / "desktop" / ".thohago-desktop"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = [
        output_dir / "phase9-live-execution-report.json",
        output_dir / "phase10-live-execution-report.json",
    ]
    for output_path in output_paths:
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        name: {
            "status": result.get("status"),
            "message": result.get("message"),
        }
        for name, result in report.items()
        if isinstance(result, dict) and "status" in result
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(output_paths[-1])


if __name__ == "__main__":
    main()
