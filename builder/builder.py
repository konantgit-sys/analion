"""
Prompt Builder — загружает шаблон и вставляет проблему пользователя.
"""
import os
import re

PROMPTS_DIR = os.environ.get("ANALION_PROMPTS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts"))

SYSTEM_PREFIX = """Ты — эксперт по системному анализу и принятию решений. 
Твоя задача — применить указанный метод анализа к проблеме пользователя.

## Проблема для анализа
{problem}

## Контекст
{context}

## Твоя задача
Используй метод **{framework_name}** для анализа этой проблемы.
Следуй алгоритму ниже шаг за шагом. Не пропускай шаги.
"""

OUTPUT_SUFFIX = """
## Формат ответа
1. **Краткий вывод** (2-3 предложения) — суть анализа
2. **Пошаговый разбор** — каждый шаг метода
3. **Итоговые рекомендации** — что делать
4. Отвечай на русском языке. Будь конкретен, используй данные из проблемы пользователя.
"""


def load_template(framework_id: str) -> str:
    """Загружает .txt шаблон для указанной системы."""
    path = os.path.join(PROMPTS_DIR, f"{framework_id}.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Template not found: {framework_id}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_framework_name(framework_id: str) -> str:
    """Извлекает название системы из первой строки шаблона."""
    template = load_template(framework_id)
    first_line = template.strip().split("\n")[0]
    # "# FMEA — Failure Mode and Effects Analysis (Анализ видов и последствий отказов)"
    name = first_line.replace("#", "").strip()
    return name


def build_prompt(framework_id: str, problem: str, context: str = "") -> str:
    """Собирает финальный промпт для отправки в LLM."""
    template = load_template(framework_id)
    framework_name = get_framework_name(framework_id)
    context = context or "Не предоставлен"

    prefix = SYSTEM_PREFIX.format(problem=problem, context=context, framework_name=framework_name)

    return prefix + "\n---\n\n" + template + "\n---\n" + OUTPUT_SUFFIX


if __name__ == "__main__":
    # Тест
    prompt = build_prompt("20_PARETO", "Падают продажи интернет-магазина", "B2C, электроника")
    print(prompt[:500])
    print(f"\n... (всего {len(prompt)} символов)")
