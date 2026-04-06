from __future__ import annotations

from pathlib import Path

from thohago.config import AppConfig
from thohago.groq_live import GroqApiClient, GroqTranscriptionProvider
from thohago.models import TranscriptProviderResult


class StubTranscriptionProvider:
    def transcribe_audio(self, audio_path: Path, language: str = "ko") -> TranscriptProviderResult:
        return TranscriptProviderResult(
            text=f"[stub transcript] {audio_path.stem}",
            metadata={"provider": "stub", "language": language},
        )


def resolve_transcriber(config: AppConfig):
    mode = config.web_stt_mode.lower()
    if mode == "groq":
        if not config.groq_api_key:
            raise RuntimeError("THOHAGO_WEB_STT_MODE=groq requires GROQ_API_KEY.")
        return GroqTranscriptionProvider(GroqApiClient(config.groq_api_key), config.groq_stt_model)
    if mode == "auto" and config.groq_api_key:
        return GroqTranscriptionProvider(GroqApiClient(config.groq_api_key), config.groq_stt_model)
    return StubTranscriptionProvider()
