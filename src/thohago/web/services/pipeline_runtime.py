from __future__ import annotations

from thohago.anthropic_live import AnthropicApiClient, AnthropicMultimodalInterviewEngine
from thohago.config import AppConfig
from thohago.groq_live import GroqApiClient, GroqMultimodalInterviewEngine
from thohago.interview_engine import HeuristicMultimodalInterviewEngine
from thohago.openai_live import OpenAIChatCompletionsClient, OpenAIMultimodalInterviewEngine
from thohago.pipeline import Phase1ReplayPipeline


def resolve_engine(config: AppConfig):
    selected = _normalize_engine_name(config.default_interview_engine)
    if selected == "auto":
        return _resolve_auto_engine(config)
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
    if config.anthropic_api_key:
        return AnthropicMultimodalInterviewEngine(
            AnthropicApiClient(config.anthropic_api_key, config.anthropic_model),
        )
    if config.groq_api_key:
        return GroqMultimodalInterviewEngine(
            GroqApiClient(config.groq_api_key),
            config.groq_vision_model,
        )
    if config.openai_api_key:
        return OpenAIMultimodalInterviewEngine(
            OpenAIChatCompletionsClient(config.openai_api_key, config.openai_model),
        )
    return HeuristicMultimodalInterviewEngine()


def _normalize_engine_name(raw_value: str | None) -> str:
    value = (raw_value or "auto").strip().lower()
    aliases = {
        "anthropic": "claude",
        "claude": "claude",
        "groq": "groq",
        "openai": "openai",
        "gpt": "openai",
        "heuristic": "heuristic",
        "auto": "auto",
    }
    return aliases.get(value, value)
