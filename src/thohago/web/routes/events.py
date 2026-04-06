from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from thohago.web.dependencies import get_runtime, get_session_or_404
from thohago.web.repositories import SessionRecord
from thohago.web.runtime import WebRuntime


router = APIRouter()


@router.get("/s/{customer_token}/events")
async def session_events(
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    runtime: WebRuntime = Depends(get_runtime),
    session: SessionRecord = Depends(get_session_or_404),
) -> StreamingResponse:
    queue = runtime.event_bus.subscribe(session.id)
    replay_after_id = _parse_last_event_id(last_event_id) if last_event_id else None

    async def event_stream():
        replayed_max_id = replay_after_id or 0
        try:
            if replay_after_id is not None:
                replay_events = runtime.session_repository.list_session_events_after(session.id, replay_after_id)
                for replay_event in replay_events:
                    replayed_max_id = max(replayed_max_id, replay_event.id)
                    yield _format_sse(
                        replay_event.id,
                        replay_event.event_type,
                        json.loads(replay_event.data_json),
                    )
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    if event["id"] <= replayed_max_id:
                        continue
                    replayed_max_id = event["id"]
                    yield _format_sse(event["id"], event["type"], event["data"])
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            runtime.event_bus.unsubscribe(session.id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _format_sse(event_id: int, event_type: str, data: dict) -> str:
    return f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _parse_last_event_id(value: str | None) -> int:
    if not value:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        return 0
