"""
V2Bot backend — внутренний бэкенд Аналиона.
Анализ выполняется через агента V2Bot (delegate_to_researcher).
Движок возвращает промпты; агент выполняет анализ.
"""
import time


def analyze(prompt: str, model: str = None, max_tokens: int = 4000) -> dict:
    """
    V2Bot backend: возвращает статус 'delegated'.
    Фактический анализ выполняется агентом V2Bot через delegate_to_researcher.
    """
    return {
        "error": None,
        "raw_response": "__ANALION_DELEGATED__",
        "tokens_used": 0,
        "time_ms": 0,
        "backend": "v2bot",
        "model": model or "v2bot-agent",
        "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
    }
