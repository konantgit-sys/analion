"""
Adapter Manager — выбирает доступный LLM-бэкенд и вызывает его.
С авто-фоллбэком: если один бэкенд упал → пробуем следующий.

Приоритет (авто-выбор):
  1. mistral    — Mistral API (стабильный, 2 ключа с ротацией)
  2. sambanova  — SambaNova Cloud (Llama-4-Maverick, быстрый, но бывают лимиты)
  3. v2bot      — внутренняя делегация V2Bot (заглушка)
"""
import os
from runner.backends.v2bot import analyze as v2bot_analyze
from runner.backends.sambanova import analyze as sambanova_analyze
from runner.backends.mistral import analyze as mistral_analyze
from runner.backends.stubs import (
    openai_analyze,
    deepseek_analyze,
    gemini_analyze,
    local_analyze,
)
from runner.backends.template import analyze as template_analyze

FALLBACK_PRIORITY = ["template", "sambanova", "mistral", "v2bot", "openai", "deepseek", "gemini", "local"]

BACKEND_FUNCTIONS = {
    "mistral": mistral_analyze,
    "sambanova": sambanova_analyze,
    "v2bot": v2bot_analyze,
    "template": template_analyze,
    "openai": openai_analyze,
    "deepseek": deepseek_analyze,
    "gemini": gemini_analyze,
    "local": local_analyze,
}


def _detect_available():
    available = ["template", "mistral", "sambanova", "v2bot"]
    if os.environ.get("ANALION_OPENAI_KEY"):
        available.append("openai")
    if os.environ.get("ANALION_DEEPSEEK_KEY"):
        available.append("deepseek")
    if os.environ.get("ANALION_GEMINI_KEY"):
        available.append("gemini")
    if os.environ.get("ANALION_LOCAL_MODEL"):
        available.append("local")
    return available


def get_available_backends() -> list:
    return _detect_available()


def get_active_backend() -> str:
    forced = os.environ.get("ANALION_BACKEND", "").strip()
    if forced:
        return forced
    return _detect_available()[0]


def _call_func(func, prompt, model, max_tokens):
    """Безопасный вызов функции бэкенда — подбирает аргументы по сигнатуре."""
    import inspect
    sig = inspect.signature(func)
    kwargs = {}
    if 'model' in sig.parameters:
        kwargs['model'] = model
    if 'max_tokens' in sig.parameters:
        kwargs['max_tokens'] = max_tokens
    return func(prompt, **kwargs)


def run(prompt: str, backend: str = None, model: str = None, max_tokens: int = 4000) -> dict:
    """Прогоняет промпт через бэкенд с авто-фоллбэком."""
    if backend:
        # Пользователь явно выбрал — пробуем только его
        func = BACKEND_FUNCTIONS.get(backend)
        if func is None:
            return {"error": f"Unknown backend: {backend}", "raw_response": None,
                    "tokens_used": 0, "time_ms": 0, "backend": backend}
        result = _call_func(func, prompt, model, max_tokens)
        result["backend"] = backend
        return result

    # Используем активный бэкенд из окружения
    forced = os.environ.get("ANALION_BACKEND", "").strip()
    if forced:
        func = BACKEND_FUNCTIONS.get(forced)
        if func is None:
            return {"error": f"Unknown backend: {forced}", "raw_response": None,
                    "tokens_used": 0, "time_ms": 0, "backend": forced}
        result = _call_func(func, prompt, model, max_tokens)
        if result.get("error") is None and result.get("raw_response"):
            result["backend"] = forced
            return result

    # Авто-выбор с фоллбэком
    last_error = None
    for be in FALLBACK_PRIORITY:
        if be not in _detect_available():
            continue
        func = BACKEND_FUNCTIONS.get(be)
        if func is None:
            continue
        result = _call_func(func, prompt, model, max_tokens)
        if result.get("error") is None and result.get("raw_response"):
            result["backend"] = be
            return result
        last_error = result.get("error", "unknown")

    return {
        "error": f"All backends failed. Last: {last_error}",
        "raw_response": None,
        "tokens_used": 0,
        "time_ms": 0,
        "backend": "none",
    }
