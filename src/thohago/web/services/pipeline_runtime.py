from __future__ import annotations

from collections.abc import Iterable

from thohago.anthropic_live import AnthropicApiClient, AnthropicMultimodalInterviewEngine
from thohago.config import AppConfig
from thohago.gemini_live import GeminiApiClient, GeminiMultimodalInterviewEngine
from thohago.groq_live import GroqApiClient, GroqMultimodalInterviewEngine
from thohago.heuristics import extract_keywords
from thohago.interview_engine import HeuristicMultimodalInterviewEngine
from thohago.models import PlannerOutput
from thohago.openai_live import OpenAIChatCompletionsClient, OpenAIMultimodalInterviewEngine
from thohago.pipeline import Phase1ReplayPipeline


class OrderedFallbackInterviewEngine:
    def __init__(self, engines: Iterable[object]) -> None:
        self.engines = list(engines)

    def build_preflight(self, shop, photos, videos):
        return self._first_success("build_preflight", shop, photos, videos)

    def plan_turn1(self, preflight: dict):
        return self._first_success("plan_turn1", preflight)

    def plan_turn(self, turn_index: int, transcripts: list[str], preflight: dict):
        return self._first_success("plan_turn", turn_index, transcripts, preflight)

    def build_turn_question_artifact(self, planner: PlannerOutput) -> dict:
        payload = planner.to_dict()
        payload["keywords"] = extract_keywords(planner.main_angle)
        return payload

    def _first_success(self, method_name: str, *args):
        last_error: Exception | None = None
        for engine in self.engines:
            try:
                method = getattr(engine, method_name)
                return method(*args)
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"No interview engines configured for method: {method_name}")


def resolve_engine(config: AppConfig):
    selected = _normalize_engine_name(config.default_interview_engine)
    if selected == "auto":
        return _resolve_auto_engine(config)
    if selected == "gemini":
        if not config.gemini_api_key:
            raise RuntimeError("THOHAGO_DEFAULT_INTERVIEW_ENGINE=gemini requires GEMINI_API_KEY or GOOGLE_API_KEY.")
        return GeminiMultimodalInterviewEngine(
            GeminiApiClient(config.gemini_api_key, config.gemini_model),
        )
    if selected == "claude":
        if not config.anthropic_api_key:
            raise RuntimeError("THOHAGO_DEFAULT_INTERVIEW_ENGINE=claude requires CLAUDE_API_KEY or ANTHROPIC_API_KEY.")
        return AnthropicMultimodalInterviewEngine(
            AnthropicApiClient(config.anthropic_api_key, config.anthropic_model),
        )
    if selected == "groq":
        if not config.groq_api_key:
            raise RuntimeError("THOHAGO_DEFAULT_INTERVIEW_ENGINE=groq requires GROQ_API_KEY.")
        return GroqMultimodalInterviewEngine(
            GroqApiClient(config.groq_api_key),
            config.groq_vision_model,
        )
    if selected == "openai":
        if not config.openai_api_key:
            raise RuntimeError("THOHAGO_DEFAULT_INTERVIEW_ENGINE=openai requires OPENAI_API_KEY or GPT_API_KEY.")
        return OpenAIMultimodalInterviewEngine(
            OpenAIChatCompletionsClient(config.openai_api_key, config.openai_model),
        )
    if selected == "heuristic":
        return HeuristicMultimodalInterviewEngine()
    raise RuntimeError(f"Unsupported THOHAGO_DEFAULT_INTERVIEW_ENGINE value: {config.default_interview_engine}")


def resolve_pipeline(config: AppConfig):
    engine = resolve_engine(config)
    return Phase1ReplayPipeline(engine=engine), engine


def _resolve_auto_engine(config: AppConfig):
    engines: list[object] = []
    if config.gemini_api_key:
        engines.append(
            GeminiMultimodalInterviewEngine(
                GeminiApiClient(config.gemini_api_key, config.gemini_model),
            )
        )
    if config.groq_api_key:
        engines.append(
            GroqMultimodalInterviewEngine(
                GroqApiClient(config.groq_api_key),
                config.groq_vision_model,
            )
        )
    if not engines:
        return HeuristicMultimodalInterviewEngine()
    if len(engines) == 1:
        return engines[0]
    return OrderedFallbackInterviewEngine(engines)


def _normalize_engine_name(raw_value: str | None) -> str:
    value = (raw_value or "auto").strip().lower()
    aliases = {
        "gemini": "gemini",
        "google": "gemini",
        "anthropic": "claude",
        "claude": "claude",
        "groq": "groq",
        "openai": "openai",
        "gpt": "openai",
        "heuristic": "heuristic",
        "auto": "auto",
    }
    return aliases.get(value, value)
