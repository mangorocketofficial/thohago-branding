from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from thohago.cli import main
from thohago.config import load_config
from thohago.models import TranscriptProviderResult
from thohago.web.services.stt_verification import LiveGroqSttVerificationError, verify_live_groq_stt


class WebPhase7Tests(unittest.TestCase):
    def test_verify_live_groq_stt_fails_clearly_when_key_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.m4a"
            audio_path.write_bytes(b"fake-audio")
            with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
                config = load_config()
                with self.assertRaises(LiveGroqSttVerificationError) as ctx:
                    verify_live_groq_stt(config=config, audio_path=audio_path)
            self.assertIn("GROQ_API_KEY", str(ctx.exception))

    def test_cli_verify_groq_stt_prints_result_with_mocked_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.m4a"
            audio_path.write_bytes(b"fake-audio")

            class FakeProvider:
                def __init__(self, client, model):
                    self.model = model

                def transcribe_audio(self, audio_path: Path, language: str = "ko"):
                    return TranscriptProviderResult(
                        text="테스트 전사 결과입니다.",
                        metadata={"model": "fake-whisper"},
                    )

            with patch("thohago.web.services.stt_verification.GroqTranscriptionProvider", FakeProvider):
                with patch.dict(os.environ, {"GROQ_API_KEY": "fake-key"}, clear=False):
                    stdout = io.StringIO()
                    with redirect_stdout(stdout):
                        exit_code = main(["web", "verify-groq-stt", "--audio-path", str(audio_path)])
            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            self.assertIn("audio_path=", output)
            self.assertIn("transcript_length=", output)
            self.assertIn("provider_model=fake-whisper", output)


if __name__ == "__main__":
    unittest.main()
