"""
Template Backend — генерация ответа по шаблону методологии.
Без API, без ключей, без сети. Работает всегда.
Читает TXT методологии, вставляет проблему пользователя,
генерирует структурированный ответ.
"""
import os
import time
import re

def _get_prompts_dir():
    """Ленивое определение директории промптов — на момент вызова, не импорта."""
    d = os.environ.get("ANALION_PROMPTS_DIR")
    if d and os.path.isdir(d):
        return d
    # Fallback: 3 уровня вверх от этого файла → корень проекта
    fallback = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if os.path.isdir(fallback):
        return fallback
    return os.getcwd()


def analyze(prompt: str, system_prompt: str = "") -> dict:
    """Быстрый шаблонный анализ без ML."""
    start = time.time()

    # Если system_prompt передан — это ID методологии
    fw_id = (system_prompt or "").strip()
    
    if not fw_id:
        # Ищем ID в промпте
        for line in prompt.split('\n'):
            line = line.strip()
            if re.match(r'^\d{2}_[A-Z_]+', line):
                fw_id = line.strip()
                break

    if not fw_id:
        m = re.search(r'(\d{2}_[A-Z_]+)', prompt)
        if m:
            fw_id = m.group(1)

    # Загружаем TXT методологии
    template_text = ""
    if fw_id:
        fw_path = os.path.join(_get_prompts_dir(), f"{fw_id}.txt")
        if os.path.exists(fw_path):
            with open(fw_path, 'r', encoding='utf-8') as f:
                template_text = f.read()

    # Извлекаем название
    name = fw_id
    if template_text:
        m = re.search(r'^# (.+)', template_text, re.MULTILINE)
        if m:
            name = m.group(1).strip()

    # Извлекаем описание метода
    description = ""
    if template_text:
        lines = template_text.split('\n')
        capture = False
        for line in lines:
            if line.strip().startswith('## ') and not description:
                capture = True
                continue
            if capture and line.strip().startswith('## '):
                break
            if capture and line.strip() and not line.startswith('#') and not line.startswith('*'):
                description += ' ' + line.strip()
        description = description.strip()[:300]

    # Извлекаем шаги
    steps_raw = []
    if template_text:
        in_alg = False
        for line in lines:
            if 'Алгоритм' in line and line.startswith('##'):
                in_alg = True
                continue
            if in_alg:
                if line.startswith('## '):
                    break
                m = re.match(r'\d\.?\s*(.+?)(?::\s*|$)', line.strip())
                if m:
                    steps_raw.append(m.group(1).strip())

    # Извлекаем кейсы
    cases = ""
    if template_text:
        m = re.search(r'(?:Известные кейсы|Известные примеры|Кейсы|Примеры применения)[^\n]*\n(.+?)(?:\n##|\Z)', template_text, re.DOTALL)
        if m:
            cases = m.group(1).strip()[:200]

    # Извлекаем проблему
    problem = ""
    m = re.search(r'## Проблема для анализа\n(.+?)(?:\n##|\Z)', prompt, re.DOTALL)
    if m:
        problem = m.group(1).strip()

    # Генерируем ответ
    if not template_text:
        raw = f"""# Анализ методом {name}

**Метод:** {name}

## Краткий вывод
Метод {name} — мощный инструмент для анализа проблем. Рекомендуется изучить полное описание методологии в каталоге Analion.

## Пошаговый разбор
1. Ознакомьтесь с полным описанием методологии на витрине Analion
2. Определите применимость к вашей задаче
3. Следуйте алгоритму из описания

## Итоговые рекомендации
— Изучите методологию {name} в каталоге: https://konantgit-sys.github.io/analion/
— Попробуйте применить к вашей конкретной ситуации
"""
    else:
        steps_text = ""
        if steps_raw:
            steps_text = '\n'.join([f"{i+1}. {s}" for i, s in enumerate(steps_raw[:5])])
        else:
            steps_text = "1. Примените шаги из полного описания методологии"

        raw = f"""# Анализ методом {name}

**Метод:** {name}

## Краткий вывод
{description[:250]}

**Применимо к проблеме:** {problem[:100] if problem else 'Общий анализ'}

## Пошаговый разбор
{steps_text}

## Контекст метода
{name} — это {'инженерный' if 'ARIZ' in fw_id or 'TRIZ' in fw_id or 'FMEA' in fw_id else 'стратегический' if 'SWOT' in fw_id or 'PESTLE' in fw_id else 'управленческий' if 'PDCA' in fw_id or 'OKR' in fw_id else 'аналитический'} метод, разработанный для {'решения изобретательских задач' if 'TRIZ' in fw_id else 'стратегического анализа' if 'SWOT' in fw_id else 'управления качеством' if 'PDCA' in fw_id else 'системного анализа'}.

## Итоговые рекомендации
— Изучите полное описание методологии в каталоге Analion
— Примените к вашей конкретной ситуации
— Комбинируйте с другими методологиями для более глубокого анализа
"""

    elapsed = int((time.time() - start) * 1000)

    return {
        "error": None,
        "raw_response": raw,
        "tokens_used": len(raw) // 4 if raw else 0,
        "time_ms": elapsed,
        "backend": "template",
    }
