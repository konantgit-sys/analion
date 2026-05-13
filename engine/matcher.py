"""
Matcher — подбор методологий под проблему пользователя.
Keyword-based scoring, без внешних зависимостей.
"""
import os
import json
import re
from typing import Optional

SITE_DIR = os.environ.get("ANALION_PROMPTS_DIR", os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.environ.get("ANALION_DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
META_PATH = os.path.join(DATA_DIR, "frameworks_meta.json")

# Стоп-слова
STOP_WORDS = set("""
это что такой такая такие так как и в на с о об по из у за для к от до про без
через под над перед при между после около против внутри вокруг вне вместо
вроде наподобие словно будто точно также ещё уже очень совсем почти достаточно
весь вся все всем всего всех ещё же ли бы ни не или но а да ибо если
когда где куда откуда зачем почему как какой какая какое какие чей чья чье чьи
тот та то те этого этому этим этих этого этому этим этих
""".split())


def tokenize(text: str) -> list[str]:
    """Токенизация: слова 3+ буквы, нижний регистр, без стоп-слов."""
    words = re.findall(r'[а-яёa-z]{3,}', text.lower())
    return [w for w in words if w not in STOP_WORDS]


def load_frameworks() -> list[dict]:
    """Загружает метаданные методологий."""
    if not os.path.exists(META_PATH):
        return []
    with open(META_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _get_full_text(framework_id: str) -> str:
    """Читает полный TXT методологии для расширенного поиска."""
    fpath = os.path.join(SITE_DIR, f"{framework_id}.txt")
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def match(problem: str, top_n: int = 5) -> list[dict]:
    """
    Подбирает методологии под проблему.
    Сравнивает токены проблемы с:
      - полным текстом TXT
      - keywords из метаданных
      - названием методологии
    """
    tokens = set(tokenize(problem))
    if not tokens:
        return []

    frameworks = load_frameworks()
    fw_map = {fw["id"]: fw for fw in frameworks}
    scored = []

    for fw in frameworks:
        fid = fw["id"]
        full_text = _get_full_text(fid)
        fw_tokens = set(tokenize(full_text))

        # Считаем совпадения
        matched = tokens & fw_tokens
        # Частичные совпадения для длинных токенов (>5 букв)
        partial = set()
        for t in tokens:
            if len(t) <= 5:
                continue
            for ft in fw_tokens:
                if len(ft) > 5 and (t in ft or ft in t):
                    partial.add(t)
                    break

        all_matched = matched | partial
        score = len(all_matched) / max(len(tokens), 1)
        matched_list = sorted(all_matched)[:5]

        if score > 0:
            scored.append({
                "id": fid,
                "name": fw["name"],
                "category": fw.get("category", "unknown"),
                "score": round(score * 100, 1),
                "match_count": len(all_matched),
                "matched_terms": matched_list,
            })

    scored.sort(key=lambda x: (-x["score"], -x["match_count"]))
    # Добавляем reason только для топ-N
    for s in scored[:top_n]:
        s["reason"] = _generate_reason(s["name"], s.get("category", ""), s["matched_terms"])
    return scored[:top_n]


def _generate_reason(name: str, category: str, matched_terms: list[str]) -> str:
    cat_labels = {
        "engineering": "инженерный анализ",
        "strategic": "стратегический анализ",
        "management": "управленческий анализ",
        "risk": "анализ рисков",
        "decision": "принятие решений",
        "analytical": "системный анализ",
    }
    cat = cat_labels.get(category, "анализ")
    if matched_terms:
        terms = ", ".join(matched_terms[:3])
        return f"Метод «{name}» ({cat}). Совпадение: {terms}"
    return f"Метод «{name}» ({cat})"
