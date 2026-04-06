from __future__ import annotations

import argparse
from pathlib import Path

from thohago.bot import start_bot
from thohago.config import load_config
from thohago.pipeline import Phase1ReplayPipeline
from thohago.registry import load_shop_registry
from thohago.sync_client import list_sessions as sync_list_sessions
from thohago.sync_client import pull_session as sync_pull_session
from thohago.sync_client import push_session as sync_push_session
from thohago.web.config import build_web_config
from thohago.web.database import initialize_database
from thohago.web.repositories import SessionRepository
from thohago.web.services.sessions import SessionService
from thohago.web.services.stt_verification import verify_live_groq_stt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thohago")
    subparsers = parser.add_subparsers(dest="command", required=True)

    replay_parser = subparsers.add_parser("replay", help="Run the replayable Phase 1 pipeline")
    replay_parser.add_argument("--shop-id", required=True)
    replay_parser.add_argument("--session-key", required=True)
    replay_parser.add_argument("--artifact-root", default=None)

    bot_parser = subparsers.add_parser("bot", help="Start the Telegram bot scaffold")
    bot_parser.add_argument("--dry-run", action="store_true")

    web_parser = subparsers.add_parser("web", help="Web runtime utilities")
    web_subparsers = web_parser.add_subparsers(dest="web_command", required=True)

    web_init_db_parser = web_subparsers.add_parser("init-db", help="Initialize the web SQLite database")
    web_init_db_parser.add_argument("--db-path", default=None)

    web_create_session_parser = web_subparsers.add_parser(
        "create-session",
        help="Create a customer web session for an existing shop",
    )
    web_create_session_parser.add_argument("--shop-id", required=True)
    web_create_session_parser.add_argument("--session-key", default=None)

    web_verify_stt_parser = web_subparsers.add_parser(
        "verify-groq-stt",
        help="Run a live Groq STT verification against a sample audio file",
    )
    web_verify_stt_parser.add_argument("--audio-path", required=True)

    sync_parser = subparsers.add_parser("sync", help="Sync API client utilities")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command", required=True)

    sync_list_parser = sync_subparsers.add_parser("list", help="List sessions from the sync API")
    sync_list_parser.add_argument("--base-url", default=None)
    sync_list_parser.add_argument("--token", default=None)
    sync_list_parser.add_argument("--stage", default="awaiting_production")

    sync_pull_parser = sync_subparsers.add_parser("pull", help="Download and extract a session from the sync API")
    sync_pull_parser.add_argument("--base-url", default=None)
    sync_pull_parser.add_argument("--token", default=None)
    sync_pull_parser.add_argument("--session-id", required=True)
    sync_pull_parser.add_argument("--output-dir", default="client")

    sync_push_parser = sync_subparsers.add_parser("push", help="Upload preview artifacts to the sync API")
    sync_push_parser.add_argument("--base-url", default=None)
    sync_push_parser.add_argument("--token", default=None)
    sync_push_parser.add_argument("--session-id", required=True)
    sync_push_parser.add_argument("--source-dir", required=True)
    sync_push_parser.add_argument("--manifest", required=True)

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

    if args.command == "web":
        web_config = build_web_config(config)
        database_path = Path(args.db_path).resolve() if getattr(args, "db_path", None) else web_config.database_path

        if args.web_command == "init-db":
            initialize_database(database_path)
            print(f"web_database={database_path}")
            return 0

        if args.web_command == "create-session":
            shops = load_shop_registry(config.shops_file)
            initialize_database(database_path)
            repository = SessionRepository(database_path)
            service = SessionService(config=config, web_config=web_config, shops=shops, repository=repository)
            created = service.create_session(shop_id=args.shop_id, session_key=args.session_key)
            print(f"shop_id={created.session.shop_id}")
            print(f"session_id={created.session.id}")
            print(f"session_key={created.session.session_key}")
            print(f"customer_token={created.session.customer_token}")
            print(f"customer_url={created.customer_url}")
            print(f"artifact_dir={created.artifacts.artifact_dir}")
            print(f"session_metadata={created.metadata_path}")
            return 0

        if args.web_command == "verify-groq-stt":
            result = verify_live_groq_stt(
                config=config,
                audio_path=Path(args.audio_path).resolve(),
            )
            print(f"audio_path={result.audio_path}")
            print(f"transcript_length={len(result.transcript_text)}")
            print(f"transcript_excerpt={result.transcript_text[:120]}")
            print(f"provider_model={result.metadata.get('model', config.groq_stt_model)}")
            return 0

    if args.command == "sync":
        web_config = build_web_config(config)
        base_url = (args.base_url or web_config.base_url).rstrip("/")
        token = args.token or web_config.sync_api_token

        if args.sync_command == "list":
            payload = sync_list_sessions(base_url=base_url, token=token, stage=args.stage)
            print(f"count={len(payload.get('sessions', []))}")
            for index, session in enumerate(payload.get("sessions", []), start=1):
                print(
                    "session_{index}={session_id}|{shop_id}|{stage}|{customer_url}".format(
                        index=index,
                        session_id=session["session_id"],
                        shop_id=session["shop_id"],
                        stage=session["stage"],
                        customer_url=session["customer_url"],
                    )
                )
            return 0

        if args.sync_command == "pull":
            zip_path, extract_dir = sync_pull_session(
                base_url=base_url,
                token=token,
                session_id=args.session_id,
                output_dir=Path(args.output_dir).resolve(),
            )
            print(f"session_id={args.session_id}")
            print(f"downloaded_zip={zip_path}")
            print(f"extract_dir={extract_dir}")
            return 0

        if args.sync_command == "push":
            payload = sync_push_session(
                base_url=base_url,
                token=token,
                session_id=args.session_id,
                source_dir=Path(args.source_dir).resolve(),
                manifest_path=Path(args.manifest).resolve(),
            )
            print(f"session_id={payload['session_id']}")
            print(f"stage={payload['stage']}")
            print(f"preview_url={payload['preview_url']}")
            print(f"manifest_path={payload['manifest_path']}")
            return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
