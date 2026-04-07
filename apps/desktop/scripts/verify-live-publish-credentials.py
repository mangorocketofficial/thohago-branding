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
        validate_instagram_publish,
        validate_naver_publish,
        validate_threads_publish,
    )

    load_env_file(repo_root / ".env")

    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "instagram": validate_instagram_publish(
            {
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
        "threads": validate_threads_publish(
            {
                "threads_access_token": os.environ.get("THREADS_ACCESS_TOKEN", ""),
                "threads_user_id": os.environ.get("THREADS_USER_ID", ""),
                "facebook_page_id": os.environ.get("FACEBOOK_PAGE_ID", ""),
                "instagram_graph_version": os.environ.get(
                    "INSTAGRAM_GRAPH_VERSION", "v23.0"
                ),
            }
        ),
        "naver": validate_naver_publish(
            {"naver_live_note": "manual desktop note"}
        ),
    }

    output_path = (
        repo_root / "apps" / "desktop" / ".thohago-desktop" / "phase8-live-validation-report.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        provider: {
            "status": result.get("status"),
            "message": result.get("message"),
        }
        for provider, result in report.items()
        if isinstance(result, dict) and "status" in result
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(output_path)


if __name__ == "__main__":
    main()
