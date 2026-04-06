from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from thohago.config import AppConfig
from thohago.groq_live import GroqApiClient, GroqTranscriptionProvider


class LiveGroqSttVerificationError(RuntimeError):
    pass


@dataclass(slots=True)
class LiveGroqSttVerificationResult:
    audio_path: Path
    transcript_text: str
    metadata: dict


def verify_live_groq_stt(*, config: AppConfig, audio_path: Path) -> LiveGroqSttVerificationResult:
    if not audio_path.exists():
        raise LiveGroqSttVerificationError(f"Audio sample not found: {audio_path}")
    if not config.groq_api_key:
        raise LiveGroqSttVerificationError("GROQ_API_KEY is not configured.")

    provider = GroqTranscriptionProvider(GroqApiClient(config.groq_api_key), config.groq_stt_model)
    result = provider.transcribe_audio(audio_path, language="ko")
    transcript_text = result.text.strip()
    if not transcript_text:
        raise LiveGroqSttVerificationError("Groq STT returned an empty transcript.")
    return LiveGroqSttVerificationResult(
        audio_path=audio_path,
        transcript_text=transcript_text,
        metadata=result.metadata,
    )
