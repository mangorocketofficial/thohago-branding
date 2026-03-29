from __future__ import annotations

import argparse
from pathlib import Path

from thohago.bot import start_bot
from thohago.config import load_config
from thohago.pipeline import Phase1ReplayPipeline
from thohago.registry import load_shop_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thohago")
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay_parser = subparsers.add_parser("replay", help="Run the replayable Phase 1 pipeline")
    replay_parser.add_argument("--shop-id", required=True)
    replay_parser.add_argument("--session-key", required=True)
    replay_parser.add_argument("--artifact-root", default=None)

    bot_parser = subparsers.add_parser("bot", help="Start the Telegram bot scaffold")
    bot_parser.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "replay":
        shops = load_shop_registry(config.shops_file)
        shop = shops[args.shop_id]
        artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else config.artifact_root
        result = Phase1ReplayPipeline().run(artifact_root=artifact_root, shop=shop, session_key=args.session_key)
        print(f"artifact_dir={result.artifacts.artifact_dir}")
        print(f"media_preflight={result.media_preflight_path}")
        print(f"turn2_planner={result.turn2_planner_path}")
        print(f"turn3_planner={result.turn3_planner_path}")
        print(f"content_bundle={result.content_bundle_path}")
        print(f"blog_article={result.blog_article_path}")
        print(f"publish_result={result.publish_result_path}")
        return 0

    if args.command == "bot":
        if args.dry_run:
            shops = load_shop_registry(config.shops_file)
            print(f"loaded_shops={len(shops)}")
            for shop in shops.values():
                print(f"{shop.shop_id} -> chat_ids={shop.telegram_chat_ids} invite_tokens={shop.invite_tokens}")
            return 0
        return start_bot()

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
