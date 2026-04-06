from __future__ import annotations

import asyncio
import json

from thohago.web.repositories import SessionRepository


class SessionEventBus:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository
        self._queues: dict[str, list[asyncio.Queue[dict]]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        self._queues.setdefault(session_id, []).append(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue[dict]) -> None:
        queues = self._queues.get(session_id)
        if not queues:
            return
        try:
            queues.remove(queue)
        except ValueError:
            return
        if not queues:
            self._queues.pop(session_id, None)

    def publish(self, session_id: str, event_type: str, data: dict) -> int:
        record = self.repository.insert_session_event(
            session_id=session_id,
            event_type=event_type,
            data=data,
        )
        event = {
            "id": record.id,
            "type": record.event_type,
            "data": json.loads(record.data_json),
        }
        for queue in list(self._queues.get(session_id, [])):
            queue.put_nowait(event)
        return record.id
