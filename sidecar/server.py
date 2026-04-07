from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from sidecar.dispatcher import build_dispatcher


def _write_message(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _write_error(request_id: str | int | None, message: str, code: int = -32000) -> None:
    _write_message(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }
    )


def main() -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()

    dispatcher = build_dispatcher(project_root=args.project_root)
    print("desktop sidecar booted", file=sys.stderr, flush=True)

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            _write_error(None, f"invalid JSON: {exc.msg}", code=-32700)
            continue

        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if message.get("jsonrpc") != "2.0" or not method:
            _write_error(request_id, "invalid JSON-RPC request", code=-32600)
            continue

        try:
            result = dispatcher.handle(method, params)
            _write_message(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }
            )
        except KeyError as exc:
            _write_error(request_id, str(exc), code=-32601)
        except Exception as exc:  # pragma: no cover - defensive server boundary
            print(f"sidecar internal error: {exc}", file=sys.stderr, flush=True)
            _write_error(request_id, f"internal error: {exc}", code=-32603)

        if dispatcher.shutdown_requested:
            break

    print("desktop sidecar stopped", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
