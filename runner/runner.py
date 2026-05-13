"""
Analysis Runner — прогоняет промпт через доступный LLM-бэкенд.
"""
import time
from runner.adapter import run as adapter_run, get_active_backend, get_available_backends


def run_analysis(prompt: str, backend: str = None, model: str = None, max_tokens: int = 4000) -> dict:
    """
    Отправляет промпт в LLM через адаптер и возвращает структурированный результат.
    """
    result = adapter_run(prompt, backend=backend, model=model, max_tokens=max_tokens)

    if result.get("error"):
        return {
            "error": result["error"],
            "raw_response": None,
            "tokens_used": 0,
            "time_ms": result.get("time_ms", 0),
            "backend": result.get("backend", "unknown"),
        }

    return {
        "error": None,
        "raw_response": result["raw_response"],
        "tokens_used": result.get("tokens_used", 0),
        "time_ms": result.get("time_ms", 0),
        "backend": result.get("backend", "v2bot"),
        "model": model or "auto",
    }


def parse_analysis(raw_response: str) -> dict:
    """Парсит ответ LLM в структурированный вид."""
    if not raw_response:
        return {"summary": "", "steps": [], "recommendations": []}

    lines = raw_response.split("\n")
    sections = {"summary": [], "steps": [], "recommendations": []}
    current_section = "summary"

    for line in lines:
        line_lower = line.strip().lower()
        if any(kw in line_lower for kw in ["краткий вывод", "вывод:", "**краткий", "**вывод"]):
            current_section = "summary"
            continue
        elif any(kw in line_lower for kw in ["пошаговый разбор", "шаг", "**шаг", "анализ:"]):
            current_section = "steps"
            continue
        elif any(kw in line_lower for kw in ["рекомендаци", "итогов", "**рекомендаци", "что делать"]):
            current_section = "recommendations"
            continue

        if line.strip():
            sections[current_section].append(line.strip())

    return {
        "summary": "\n".join(sections["summary"]) if sections["summary"] else raw_response[:500],
        "steps": sections["steps"],
        "recommendations": sections["recommendations"],
    }


def get_status() -> dict:
    """Возвращает статус всех бэкендов."""
    return {
        "active": get_active_backend(),
        "available": get_available_backends(),
    }
