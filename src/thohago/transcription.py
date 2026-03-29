from __future__ import annotations

import json
from pathlib import Path

from thohago.heuristics import normalize_whitespace


class SidecarTranscriptProvider:
    """Replay transcriber that reads already-prepared transcript sidecars."""

    def load_transcript(self, transcript_path: Path) -> str:
        json_sidecar = transcript_path.with_suffix(".json")
        if json_sidecar.exists():
            payload = json.loads(json_sidecar.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("text"), str):
                return normalize_whitespace(payload["text"])
        return normalize_whitespace(transcript_path.read_text(encoding="utf-8"))
