"""
Framework Selector — подбирает 2-3 системы анализа под проблему.
"""
import json
import os
import re
from collections import Counter

INDEX_PATH = os.environ.get("ANALION_INDEX_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "selector", "keywords_index.json"))
PROMPTS_DIR = os.environ.get("ANALION_PROMPTS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts"))

# Ручной индекс ключевых слов для каждой системы
# Ключи: id системы, значения: {keywords: [...], category: str, priority: int}
FRAMEWORK_KEYWORDS = {
    "01_TRIZ": {"keywords": ["противоречие", "изобретательск", "техническ", "идеальный", "система"], "category": "engineering", "priority": 3},
    "02_MORPHOLOGICAL": {"keywords": ["морфологическ", "матрица", "комбинаци", "вариант", "параметр", "перебор"], "category": "engineering", "priority": 2},
    "03_TOC": {"keywords": ["ограничение", "бутылочное горлышко", "узкое место", "пропускная", "goldratt", "барабан"], "category": "business", "priority": 4},
    "04_FIRST_PRINCIPLES": {"keywords": ["первопринцип", "фундаментальн", "разобрать", "базовый", "аксиома", "first principle"], "category": "strategic", "priority": 3},
    "05_ARIZ_85B": {"keywords": ["ариз", "изобретательск", "алгоритм", "вещество", "поле", "ресурс"], "category": "engineering", "priority": 3},
    "06_SYSTEMS_THINKING": {"keywords": ["системн", "обратная связь", "петля", "эмерджент", "целое", "взаимосвяз"], "category": "strategic", "priority": 4},
    "07_CYNEFIN": {"keywords": ["cynefin", "сложность", "домен", "простой", "запутанный", "сложный", "хаотичный", "хаос"], "category": "strategic", "priority": 4},
    "08_DESIGN_THINKING": {"keywords": ["дизайн-мышление", "эмпатия", "прототип", "пользовател", "клиент", "дизайн"], "category": "creative", "priority": 3},
    "09_KEPNER_TREGOE": {"keywords": ["кернер", "трего", "корневая причина", "отклонение", "решение", "оценка риск"], "category": "business", "priority": 2},
    "10_DMAIC": {"keywords": ["dmaic", "six sigma", "сигма", "процесс", "измер", "улучшен", "контроль", "качество"], "category": "business", "priority": 3},
    "11_SCAMPER": {"keywords": ["scamper", "замени", "скомбинируй", "адаптируй", "модифицируй", "творческ", "мозговой штурм"], "category": "creative", "priority": 2},
    "12_FIVE_WHYS_ISHIKAWA": {"keywords": ["почему", "5 why", "исикава", "рыбья кость", "причина", "корневой"], "category": "strategic", "priority": 3},
    "13_DELPHI": {"keywords": ["дельфи", "эксперт", "опрос", "консенсус", "прогноз", "аноним"], "category": "strategic", "priority": 2},
    "14_SYNECTICS": {"keywords": ["синектика", "аналогия", "метафора", "творческ", "необычный", "фантазия"], "category": "creative", "priority": 2},
    "15_OODA": {"keywords": ["ooda", "наблюдай", "ориентируйся", "решай", "действуй", "бойд", "цикл", "быстро"], "category": "strategic", "priority": 3},
    "16_FMEA": {"keywords": ["fmea", "отказ", "надёжность", "риск", "severity", "rpn", "отказывать", "поломка", "авария"], "category": "engineering", "priority": 4},
    "17_FTA": {"keywords": ["fault tree", "дерево отказов", "логическ", "and-or", "вероятность отказа", "minimal cut"], "category": "engineering", "priority": 3},
    "18_PDCA": {"keywords": ["pdca", "деминг", "plan-do-check", "непрерывное улучшение", "качество", "цикл улучшения", "kaizen"], "category": "business", "priority": 3},
    "19_MCKINSEY_7S": {"keywords": ["mckinsey", "7s", "организаци", "структура", "стратегия", "ценности", "персонал", "навыки"], "category": "business", "priority": 3},
    "20_PARETO": {"keywords": ["парето", "80/20", "80 на 20", "приоритет", "vital few", "немногие", "большинство проблем", "диаграмма", "продаж", "падение", "снижение", "проблем"], "category": "business", "priority": 4},
    "21_SIX_HATS": {"keywords": ["шляп", "де боно", "параллельное мышление", "режим мышления", "роль", "фасилитатор"], "category": "creative", "priority": 3},
    "22_LATERAL_THINKING": {"keywords": ["латеральн", "обходное", "нестандартн", "провокация", "random word", "инверсия", "креатив"], "category": "creative", "priority": 3},
    "23_WARDLEY": {"keywords": ["wardley", "уордли", "карта", "эволюция", "commodity", "ценности", "стратегия", "позиционирование", "технологии"], "category": "strategic", "priority": 4},
    "24_SWOT": {"keywords": ["swot", "tows", "сильные", "слабые", "возможности", "угрозы", "стратегия", "рынок"], "category": "strategic", "priority": 2},
    "25_PESTLE": {"keywords": ["pestle", "pest", "макросреда", "политическ", "экономическ", "социальн", "технологическ", "legal", "экологическ"], "category": "strategic", "priority": 2},
    "26_GAME_THEORY": {"keywords": ["игр", "нэш", "payoff", "стратегия", "игрок", "равновесие", "матрица выигрыша", "дилемма"], "category": "strategic", "priority": 4},
    "27_KANO": {"keywords": ["кано", "kano", "фича", "продукт", "пользовател", "удовлетворённость", "must-be", "attractive", "восторг"], "category": "business", "priority": 3},
}


def build_index():
    """Сохраняет индекс в JSON файл."""
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(FRAMEWORK_KEYWORDS, f, ensure_ascii=False, indent=2)
    print(f"Index saved: {INDEX_PATH} ({len(FRAMEWORK_KEYWORDS)} frameworks)")


def load_index():
    """Загружает индекс из JSON файла."""
    if not os.path.exists(INDEX_PATH):
        build_index()
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def select_frameworks(problem: str, top_n: int = 3) -> list:
    """
    Подбирает top_n систем анализа под проблему.
    
    Возвращает: [{"framework_id": "...", "name": "...", "reason": "...", "score": 0.0}, ...]
    """
    index = load_index()
    problem_lower = problem.lower()
    
    scores = {}
    for fid, data in index.items():
        score = 0
        matched_keywords = []
        for kw in data["keywords"]:
            if kw.lower() in problem_lower:
                score += data.get("priority", 1)
                matched_keywords.append(kw)
        
        if score > 0:
            scores[fid] = {"score": score, "matched": matched_keywords, "priority": data["priority"]}
    
    # Sort by score desc
    ranked = sorted(scores.items(), key=lambda x: (-x[1]["score"], -x[1]["priority"]))
    
    # If not enough keyword matches, add high-priority defaults
    if len(ranked) < top_n:
        # Add highest priority frameworks not yet matched
        all_by_priority = sorted(index.items(), key=lambda x: -x[1]["priority"])
        for fid, data in all_by_priority:
            if fid not in scores:
                ranked.append((fid, {"score": 0, "matched": ["default"], "priority": data["priority"]}))
            if len(ranked) >= top_n:
                break
    
    # Take top_n
    results = []
    for fid, info in ranked[:top_n]:
        # Read name from template
        try:
            with open(os.path.join(PROMPTS_DIR, f"{fid}.txt"), "r") as f:
                first_line = f.readline().strip().replace("#", "").strip()
            name = first_line.split("—")[0].strip() if "—" in first_line else first_line[:60]
        except:
            name = fid
        
        reason = "Ключевые слова: " + ", ".join(info["matched"]) if info["matched"] else "Высокоприоритетная система"
        results.append({
            "framework_id": fid,
            "name": name,
            "reason": reason,
            "score": info["score"],
            "category": index[fid]["category"]
        })
    
    return results


if __name__ == "__main__":
    build_index()
    
    tests = [
        "Падают продажи интернет-магазина электроники",
        "Как улучшить качество производства на фабрике",
        "Нужно придумать новый продукт",
        "Рынок нестабилен, конкуренты агрессивны, что делать",
        "Система даёт сбои, нужно найти причину отказов",
    ]
    
    for t in tests:
        print(f"\nПроблема: {t}")
        results = select_frameworks(t, top_n=3)
        for r in results:
            print(f"  {r['framework_id']} | {r['name']} | score={r['score']} | {r['reason']}")
