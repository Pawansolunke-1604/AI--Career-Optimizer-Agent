from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings


def _build(model_name: str) -> ChatGoogleGenerativeAI:
    s = get_settings()
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=s.google_api_key,
        temperature=s.temperature,
        max_retries=1,
        timeout=45,
    )


def get_llm() -> ChatGoogleGenerativeAI:
    return _build(get_settings().model_name)


def get_structured_llm(schema):
    """Structured-output model with an automatic fallback if the main model is overloaded."""
    s = get_settings()
    primary = _build(s.model_name).with_structured_output(schema)
    if s.fallback_model_name:
        fallback = _build(s.fallback_model_name).with_structured_output(schema)
        return primary.with_fallbacks([fallback])
    return primary


def get_agent_model() -> ChatGoogleGenerativeAI:
    """Main chat model for the agent (it needs tool calling, so no structured-output wrapper)."""
    return _build(get_settings().model_name)


def get_agent_fallback_model() -> ChatGoogleGenerativeAI | None:
    name = get_settings().fallback_model_name
    return _build(name) if name else None