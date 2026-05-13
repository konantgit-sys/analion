"""
Analion Engine — FastAPI ядро.
"""
import sys
import os
import json
import uuid
import sqlite3
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env from project root
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

# Default environment for server mode
if not os.environ.get("ANALION_PROMPTS_DIR"):
    os.environ["ANALION_PROMPTS_DIR"] = os.path.dirname(os.path.dirname(__file__))
if not os.environ.get("ANALION_BACKEND"):
    os.environ["ANALION_BACKEND"] = "template"

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from selector.selector import select_frameworks
from builder.builder import build_prompt
from runner.runner import run_analysis, parse_analysis, get_status

app = FastAPI(title="Analion Engine", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Database init ----
DB_PATH = os.environ.get("ANALION_DB_ENGINE_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "analion.db"))
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            page TEXT,
            referer TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            country TEXT,
            session_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS beta_signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            name TEXT,
            use_case TEXT,
            source TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            item TEXT,
            amount_rub REAL,
            notes TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            problem TEXT,
            frameworks TEXT,
            analyses TEXT,
            backend TEXT,
            total_tokens INTEGER DEFAULT 0,
            total_time_ms INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            provider TEXT NOT NULL,
            api_key TEXT NOT NULL,
            base_url TEXT DEFAULT '',
            model TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            last_used TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


init_db()


# ---- Models ----
class AnalyzeRequest(BaseModel):
    problem: str
    context: str = ""
    frameworks: list[str] = []
    backend: str = ""       # template | mistral | openai | deepseek | ... или custom
    api_key: str = ""       # свой ключ (для custom/своих провайдеров)
    base_url: str = ""      # свой URL (для custom)
    model: str = ""         # модель (автоподбор если пусто)
    session_id: str = ""    # для лимитов и подписок


class AnalyzeResponse(BaseModel):
    request_id: str
    problem: str
    frameworks_selected: list[dict]
    analyses: list[dict]
    total_tokens: int
    total_time_ms: int


class VisitorRequest(BaseModel):
    page: str = "/"
    referer: str = ""


class SignupRequest(BaseModel):
    email: str
    name: str = ""
    use_case: str = ""
    source: str = ""


# ---- Static files (опционально) ----
STATIC_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "static"
if STATIC_DIR.exists() and any(STATIC_DIR.iterdir()):
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return {
        "engine": "Analion v0.2.0",
        "status": "running",
        "endpoints": {
            "health": "/api/v1/health",
            "status": "/api/v1/status",
            "frameworks": "/api/v1/frameworks",
            "framework": "/api/v1/frameworks/{id}",
            "analyze": "/api/v1/analyze",
            "docs": "/docs",
        },
    }


# ---- API Endpoints ----
@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.2.0", "timestamp": datetime.now().isoformat()}


@app.get("/api/v1/status")
async def status():
    return {
        "engine": "Analion v0.2.0",
        "domain": "analion.v2.site",
        "backends": get_status(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/frameworks")
async def list_frameworks():
    # Сканируем реальные TXT файлы
    prompts_dir = os.environ.get("ANALION_PROMPTS_DIR", os.path.dirname(os.path.dirname(__file__)))
    frameworks = []
    if os.path.isdir(prompts_dir):
        for fname in sorted(os.listdir(prompts_dir)):
            if re.match(r'^\d{2}_[A-Z_]+\.txt$', fname):
                fid = fname.replace('.txt', '')
                name = fid
                # Читаем заголовок
                fpath = os.path.join(prompts_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('# '):
                        name = first_line[2:].strip()
                frameworks.append({"id": fid, "name": name})
    return {"total": len(frameworks), "frameworks": frameworks}


@app.get("/api/v1/frameworks/{framework_id}")
async def get_framework(framework_id: str):
    try:
        from builder.builder import load_template, get_framework_name
        name = get_framework_name(framework_id)
        template = load_template(framework_id)
        prompt = build_prompt(framework_id, "[проблема]", "[контекст]")
        return {"id": framework_id, "name": name, "template": template, "example_prompt": prompt}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Framework {framework_id} not found")


@app.post("/api/v1/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    request_id = str(uuid.uuid4())[:8]

    # Проверка лимитов для всех AI-анализов и подписок
    sid = req.session_id or request.client.host if request.client else "unknown"
    from engine.billing.limits import check_analyze_limit, log_usage, get_plan_for_session
    plan_id = get_plan_for_session(sid)
    allowed, used, limit = check_analyze_limit(sid, plan_id)
    if not allowed:
        return {
            "error": "daily_limit_reached",
            "message": f"Лимит {limit} анализов в день исчерпан. Апгрейдните тариф: /api/v1/plans",
            "plan_id": plan_id,
            "used_today": used,
            "daily_limit": limit,
        }

    if req.frameworks:
        selected = [{"framework_id": fid, "name": fid, "reason": "выбрано пользователем", "score": 0} for fid in req.frameworks]
    else:
        selected = select_frameworks(req.problem, top_n=3)

    analyses = []
    total_tokens = 0
    total_time = 0

    for fw in selected:
        fid = fw["framework_id"]
        prompt = build_prompt(fid, req.problem, req.context)

        # Мульти-провайдер: выбор нейронки
        backend_mode = req.backend or ""

        if backend_mode == "template":
            from runner.backends.template import analyze as template_analyze
            result = template_analyze(prompt, system_prompt=fid)
        elif backend_mode and req.api_key:
            # Пользовательский ключ — любой OpenAI-совместимый
            from runner.backends.openai_compat import analyze as oai
            result = oai(prompt, system_prompt=fid, provider=backend_mode,
                         api_key=req.api_key, base_url=req.base_url,
                         model=req.model or None)
        elif backend_mode and backend_mode != "mistral":
            # Попробовать системный ключ (кроме mistral — у него свои ключи)
            from runner.backends.openai_compat import analyze as oai
            result = oai(prompt, system_prompt=fid, provider=backend_mode,
                         api_key="", model=req.model or None)
        else:
            # Системный бэкенд (Mistral или template из .env)
            result = run_analysis(prompt, backend=req.backend if req.backend else None)

        if result.get("error"):
            # Fallback на template при ошибке
            from runner.backends.template import analyze as template_analyze
            result = template_analyze(prompt, system_prompt=fid)
        
        if result.get("error"):
            analyses.append({"framework_id": fid, "name": fw.get("name", fid), "error": result["error"], "summary": "", "steps": [], "recommendations": []})
            continue

        parsed = parse_analysis(result["raw_response"])

        analyses.append({
            "framework_id": fid, "name": fw.get("name", fid), "error": None,
            "summary": parsed["summary"], "steps": parsed["steps"],
            "recommendations": parsed["recommendations"],
            "raw_response": result["raw_response"],
            "tokens_used": result.get("tokens_used", 0),
            "time_ms": result.get("time_ms", 0),
            "backend": result.get("backend", result.get("provider", backend_mode or "system")),
            "model": result.get("model", req.model or ""),
        })

        total_tokens += result.get("tokens_used", 0)
        total_time += result.get("time_ms", 0)

    # Логируем использование для лимитов
    if sid and sid != "unknown":
        from engine.billing.limits import log_usage
        log_usage(sid, "analyze", total_tokens)

    response = {
        "request_id": request_id, "problem": req.problem,
        "frameworks_selected": selected, "analyses": analyses,
        "total_tokens": total_tokens, "total_time_ms": total_time,
    }

    # Сохраняем в историю
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO analysis_history (request_id, problem, frameworks, analyses, backend, total_tokens, total_time_ms) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (request_id, req.problem, json.dumps([f["framework_id"] for f in selected], ensure_ascii=False),
             json.dumps(analyses, ensure_ascii=False), result.get("backend", "template"),
             total_tokens, total_time),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # история не критична

    return response


class MatcherRequest(BaseModel):
    problem: str
    top_n: int = 5


@app.post("/api/v1/matcher")
async def matcher(req: MatcherRequest):
    from engine.matcher import match
    results = match(req.problem, top_n=req.top_n)
    return {
        "problem": req.problem,
        "total": len(results),
        "matches": results,
    }


@app.get("/api/v1/examples")
async def list_examples():
    ex_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "examples.json")
    if not os.path.exists(ex_path):
        return {"total": 0, "examples": []}
    with open(ex_path, "r", encoding="utf-8") as f:
        examples = json.load(f)
    return {"total": len(examples), "examples": examples}


@app.get("/api/v1/examples/{example_id}")
async def get_example(example_id: str):
    ex_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "examples.json")
    if not os.path.exists(ex_path):
        raise HTTPException(status_code=404, detail="No examples")
    with open(ex_path, "r", encoding="utf-8") as f:
        examples = json.load(f)
    for ex in examples:
        if ex["id"] == example_id:
            return ex
    raise HTTPException(status_code=404, detail=f"Example {example_id} not found")


@app.get("/api/v1/graph")
async def get_graph():
    g_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "graph.json")
    if not os.path.exists(g_path):
        return {"nodes": [], "edges": []}
    with open(g_path, "r", encoding="utf-8") as f:
        return json.load(f)


class CompareRequest(BaseModel):
    frameworks: list[str]


@app.post("/api/v1/compare")
async def compare(req: CompareRequest):
    metrics_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "frameworks_metrics.json")
    if not os.path.exists(metrics_path):
        return {"error": "No metrics data"}
    with open(metrics_path, "r", encoding="utf-8") as f:
        all_metrics = json.load(f)
    
    # Also load names
    meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "frameworks_meta.json")
    names = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            for fw in json.load(f):
                names[fw["id"]] = fw["name"]
    
    results = []
    for fid in req.frameworks:
        meta = all_metrics.get(fid, {})
        results.append({
            "id": fid,
            "name": names.get(fid, fid),
            "difficulty": meta.get("difficulty", "?"),
            "time_hours": meta.get("time_hours", "?"),
            "data_needed": meta.get("data_needed", "?"),
            "result_type": meta.get("result_type", "?"),
            "group": meta.get("group", "?"),
        })
    
    return {"frameworks": results, "total": len(results)}


class ReportRequest(BaseModel):
    problem: str
    framework_id: str
    context: str = ""


class ProblemScoreRequest(BaseModel):
    problem: str


class BrainstormRequest(BaseModel):
    problem: str
    framework_id: str = "01_TRIZ"
    context: str = ""


class AnalyzeFileRequest(BaseModel):
    problem: str = ""
    framework_id: str
    text: str = ""
    file_url: str = ""
    context: str = ""


@app.post("/api/v1/report")
async def generate_report(req: ReportRequest):
    """Генерирует PDF-отчёт по анализу."""
    from runner.backends.template import analyze as template_analyze
    from builder.builder import build_prompt, load_template

    prompt = build_prompt(req.framework_id, req.problem, req.context)
    result = template_analyze(prompt, system_prompt=req.framework_id)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    raw = result.get("raw_response", "Нет данных")

    # Генерируем PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"report_{req.framework_id}_{uuid.uuid4().hex[:8]}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Title2", parent=styles["Heading1"], fontSize=16, spaceAfter=12))
    styles.add(ParagraphStyle("Body2", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6))

    elements = []
    elements.append(Paragraph(f"Analion — {req.framework_id}", styles["Title2"]))
    elements.append(Paragraph(f"Проблема: {req.problem}", styles["Body2"]))
    elements.append(Spacer(1, 10*mm))

    for line in raw.split('\n'):
        if line.strip().startswith('# '):
            elements.append(Paragraph(line.strip('# ').strip(), styles["Heading2"]))
        elif line.strip().startswith('## '):
            elements.append(Paragraph(line.strip('# ').strip(), styles["Heading2"]))
        elif line.strip().startswith(('— ', '- ', '* ')):
            elements.append(Paragraph(f'• {line.strip()[2:]}', styles["Body2"]))
        elif line.strip():
            elements.append(Paragraph(line.strip(), styles["Body2"]))

    doc.build(elements)

    return {"status": "ok", "report_url": f"/api/v1/report/download/{os.path.basename(pdf_path)}", "file": pdf_path}


@app.get("/api/v1/report/download/{filename}")
async def download_report(filename: str):
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)


@app.get("/api/v1/examples/{example_id}")
async def get_example(example_id: str):
    ex_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "examples.json")
    if not os.path.exists(ex_path):
        raise HTTPException(status_code=404, detail="No examples")
    with open(ex_path, "r", encoding="utf-8") as f:
        examples = json.load(f)
    for ex in examples:
        if ex["id"] == example_id:
            return ex
    raise HTTPException(status_code=404, detail=f"Example {example_id} not found")


# ==================== Фаза 2: LLM-интеграции ====================

@app.get("/api/v1/history")
async def get_history(limit: int = 20):
    """F8: История анализов"""
    conn = get_db()
    rows = conn.execute(
        "SELECT request_id, problem, frameworks, backend, total_tokens, total_time_ms, timestamp "
        "FROM analysis_history ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {
        "total": len(rows),
        "history": [dict(r) for r in rows],
    }


@app.get("/api/v1/frameworks/{framework_id}/checklist")
async def get_checklist(framework_id: str):
    """F11: Чек-лист по методологии — шаги из TXT"""
    prompts_dir = os.environ.get("ANALION_PROMPTS_DIR", os.path.dirname(os.path.dirname(__file__)))
    fpath = os.path.join(prompts_dir, f"{framework_id}.txt")
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Framework {framework_id} not found")
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()

    name = framework_id
    m = re.search(r'^# (.+)', text, re.MULTILINE)
    if m:
        name = m.group(1).strip()

    # Извлекаем шаги
    steps = []
    lines = text.split('\n')
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
                steps.append(m.group(1).strip())
            elif line.strip() and not line.startswith('*') and not line.startswith('—'):
                # Ненумерованный шаг
                steps.append(line.strip())

    # Извлекаем категории/разделы
    sections = []
    for line in lines:
        if line.startswith('## '):
            sections.append(line.strip('# ').strip())

    return {
        "id": framework_id,
        "name": name,
        "steps": steps[:10],
        "sections": sections,
        "total_steps": len(steps),
    }


@app.post("/api/v1/problem-score")
async def problem_score(req: "ProblemScoreRequest"):
    """F12: Оценка сложности проблемы (keyword heuristics)"""
    from engine.matcher import tokenize

    text = req.problem.lower()
    tokens = tokenize(text)

    # Эвристики сложности
    score = 5  # базовое
    reasons = []

    # Факторы сложности
    complexity_signals = {
        'сложн': 1, 'запутан': 1, 'много': 1, 'комплекс': 1, 'систем': 1,
        'интеграци': 1, 'масштаб': 1, 'глобальн': 1, 'мног': 1,
        'распределён': 1, 'гетероген': 1, 'неопределён': 1,
    }
    urgency_signals = {
        'срочн': 1, 'горящ': 1, 'критич': 1, 'авария': 1, 'срыв': 1,
        'дедлайн': 1, 'падение': 1, 'вчера': 1, 'стоп': 1, 'блокиру': 1,
    }
    uncertainty_signals = {
        'непонятн': 1, 'неизвестн': 1, 'впервые': 1, 'нет данных': 1,
        'сомнени': 1, 'риск': 1, 'вероятн': 1,
    }

    for t in tokens:
        for signal in complexity_signals:
            if signal in t:
                score += 1
                if signal not in [r.split(':')[0] for r in reasons]:
                    reasons.append(f"сложность:{signal}")
                break
        for signal in urgency_signals:
            if signal in t:
                score += 1
                if f"срочность:{signal}" not in reasons:
                    reasons.append(f"срочность:{signal}")
                break
        for signal in uncertainty_signals:
            if signal in t:
                score += 1
                if f"неопределённость:{signal}" not in reasons:
                    reasons.append(f"неопределённость:{signal}")
                break

    score = min(score, 10)

    return {
        "problem": req.problem,
        "score": score,
        "level": "высокая" if score >= 8 else "средняя" if score >= 5 else "низкая",
        "factors": reasons[:5],
    }


@app.post("/api/v1/brainstorm")
async def brainstorm(req: "BrainstormRequest"):
    """F13: Генерация гипотез (template-based)"""
    from runner.backends.template import analyze as template_analyze

    # Собираем промпт с инструкцией на генерацию гипотез
    prompt = f"""# Генерация гипотез методом {req.framework_id}
    
## Проблема для анализа
{req.problem}

## Контекст
{req.context or 'Не предоставлен'}

## Твоя задача
Примени метод **{req.framework_id}** для генерации 5-10 гипотез/идей по решению проблемы.

## Формат ответа
1. **Краткая сводка** (1 предложение)
2. **Гипотезы:**
   - Гипотеза 1: [описание]
   - Гипотеза 2: [описание]
   ...
3. **Рекомендация:** какая гипотеза самая перспективная и почему
"""

    result = template_analyze(prompt, system_prompt=req.framework_id)
    raw = result.get("raw_response", "Ошибка генерации")

    # Парсим гипотезы
    hypotheses = []
    for line in raw.split('\n'):
        line_s = line.strip()
        m = re.match(r'[-*\d]+\.?\s*(?:Гипотеза\s*\d+[:\s]*)?(.+)', line_s)
        if m and line_s.startswith(('-', '*', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'Гипотеза')):
            hypotheses.append(m.group(1))

    return {
        "problem": req.problem,
        "framework_id": req.framework_id,
        "raw": raw,
        "hypotheses": hypotheses[:10],
        "token_estimate": result.get("tokens_used", 0),
    }


@app.post("/api/v1/analyze-file")
async def analyze_file(req: "AnalyzeFileRequest"):
    """F14: Анализ текста из файла (или прямого текста)"""
    from runner.backends.template import analyze as template_analyze
    from builder.builder import build_prompt

    # Читаем текст
    text = req.text or ""
    if req.file_url:
        try:
            import urllib.request
            with urllib.request.urlopen(req.file_url, timeout=30) as resp:
                text = resp.read().decode('utf-8')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Не удалось загрузить файл: {e}")

    if not text.strip():
        # Если текста нет, используем problem как есть
        text = req.problem

    prompt = build_prompt(req.framework_id, text, req.context or "")
    result = template_analyze(prompt, system_prompt=req.framework_id)

    from runner.runner import parse_analysis
    parsed = parse_analysis(result.get("raw_response", ""))

    return {
        "framework_id": req.framework_id,
        "text_length": len(text),
        "summary": parsed["summary"],
        "steps": parsed["steps"],
        "recommendations": parsed["recommendations"],
        "time_ms": result.get("time_ms", 0),
    }


class DeepAnalyzeRequest(BaseModel):
    problem: str
    top_n: int = 3
    context: str = ""


@app.post("/api/v1/deep-analyze")
async def deep_analyze(req: DeepAnalyzeRequest):
    """F9: Глубокий анализ — матчер + анализ каждым методом + синтез"""
    from engine.matcher import match
    from runner.backends.template import analyze as template_analyze
    from builder.builder import build_prompt
    from runner.runner import parse_analysis

    # 1. Матчер
    matched = match(req.problem, top_n=req.top_n)
    if not matched:
        return {"error": "Не удалось подобрать методологии", "problem": req.problem}

    analyses = []
    for m in matched:
        fid = m["id"]
        prompt = build_prompt(fid, req.problem, req.context)
        result = template_analyze(prompt, system_prompt=fid)
        parsed = parse_analysis(result.get("raw_response", ""))
        analyses.append({
            "framework_id": fid,
            "name": m["name"],
            "score": m["score"],
            "summary": parsed["summary"],
            "steps": parsed["steps"],
            "recommendations": parsed["recommendations"],
            "time_ms": result.get("time_ms", 0),
        })

    # 2. Синтез (общий вывод из всех)
    synthesis = "Сводный анализ по методологиям:\n"
    for a in analyses:
        synthesis += f"\n• {a['name']} (совпадение {a['score']}%): {a['summary'][:150]}"

    return {
        "problem": req.problem,
        "total_frameworks": len(analyses),
        "analyses": analyses,
        "synthesis": synthesis,
    }


class SummarizeRequest(BaseModel):
    text: str
    framework_id: str = ""
    max_length: int = 3


class BackendConnectRequest(BaseModel):
    provider: str = "mistral"  # mistral | openai | deepseek | novita | sambanova | groq | together | custom
    api_key: str
    base_url: str = ""  # для custom провайдера
    model: str = ""
    label: str = ""


class BackendTestRequest(BaseModel):
    provider: str
    api_key: str
    base_url: str = ""
    model: str = ""


# ==================== Провайдеры / Ключи пользователей ====================

PROVIDERS_INFO = {
    "mistral": {"name": "Mistral AI", "models": ["mistral-small-latest", "mistral-large-latest"], "docs": "https://console.mistral.ai/"},
    "openai":  {"name": "OpenAI", "models": ["gpt-4o-mini", "gpt-4o"], "docs": "https://platform.openai.com/api-keys"},
    "deepseek": {"name": "DeepSeek", "models": ["deepseek-chat"], "docs": "https://platform.deepseek.com/api_keys"},
    "novita":  {"name": "Novita AI", "models": ["deepseek/deepseek-v4-flash", "moonshotai/kimi-k2.6"], "docs": "https://novita.ai/settings/key-management"},
    "groq":    {"name": "Groq", "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"], "docs": "https://console.groq.com/keys"},
    "together": {"name": "Together AI", "models": ["meta-llama/Llama-3.3-70B-Instruct-Turbo"], "docs": "https://api.together.xyz/settings/api-keys"},
    "sambanova": {"name": "SambaNova", "models": ["Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3.1"], "docs": "https://cloud.sambanova.ai/"},
    "openrouter": {"name": "OpenRouter", "models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet"], "docs": "https://openrouter.ai/keys"},
    "custom": {"name": "Кастомный", "models": ["любая"], "docs": "—"},
}


@app.get("/api/v1/providers")
async def list_providers():
    """Список всех доступных провайдеров для подключения"""
    return {
        "providers": {k: {"name": v["name"], "models": v["models"], "docs": v["docs"]}
                      for k, v in PROVIDERS_INFO.items()}
    }


@app.post("/api/v1/backends/test")
async def test_backend(req: BackendTestRequest):
    """Проверка ключа провайдера — тестовый запрос"""
    from runner.backends.openai_compat import analyze as oai

    # Берём ключ: переданный или из окружения
    api_key = req.api_key

    result = oai("Ответь одним словом: привет", provider=req.provider,
                 api_key=api_key, base_url=req.base_url,
                 model=req.model or None, max_tokens=10)

    return {
        "provider": req.provider,
        "ok": result.get("error") is None,
        "response": (result.get("raw_response") or "")[:100],
        "error": result.get("error"),
        "model_used": result.get("model"),
    }


@app.get("/api/v1/backends")
async def list_backends(session_id: str = "default"):
    """Список сохранённых ключей пользователя"""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, provider, model, base_url, is_active, created_at, last_used "
        "FROM user_keys WHERE session_id=? ORDER BY created_at DESC", (session_id,)
    ).fetchall()
    conn.close()
    return {"keys": [dict(r) for r in rows]}


@app.post("/api/v1/backends")
async def connect_backend(req: BackendConnectRequest, session_id: str = "default"):
    """Подключить свой API ключ"""
    result = "saved"

    # Сначала тестируем
    from runner.backends.openai_compat import analyze as oai
    test = oai("Ответь OK если ты работаешь", provider=req.provider,
               api_key=req.api_key, base_url=req.base_url,
               model=req.model or None, max_tokens=10)

    if test.get("error"):
        return {"ok": False, "error": f"Ключ не прошёл проверку: {test['error']}"}

    # Сохраняем
    conn = get_db()
    conn.execute(
        "INSERT INTO user_keys (session_id, provider, api_key, base_url, model) VALUES (?, ?, ?, ?, ?)",
        (session_id, req.provider, req.api_key, req.base_url, req.model),
    )
    conn.commit()
    key_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    return {
        "ok": True,
        "key_id": key_id,
        "provider": req.provider,
        "model_used": test.get("model", req.model),
        "message": f"✅ {req.provider} подключён! Используйте backend={req.provider} в запросах.",
    }


@app.delete("/api/v1/backends/{key_id}")
async def delete_backend(key_id: int, session_id: str = "default"):
    """Удалить ключ"""
    conn = get_db()
    conn.execute("DELETE FROM user_keys WHERE id=? AND session_id=?", (key_id, session_id))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---- Visitor tracking ----


@app.post("/api/v1/summarize")
async def summarize(req: SummarizeRequest):
    """F10: Резюме анализа — сокращает текст до N предложений"""
    from runner.backends.template import analyze as template_analyze

    if not req.framework_id:
        # Extractive summary — первые N предложений без загрузки LLM
        sentences = re.split(r'(?<=[.!?])\s+', req.text[:3000])
        summary_sentences = sentences[:min(req.max_length, len(sentences))]
        raw_summary = ' '.join(summary_sentences)
        result = {"raw_response": raw_summary, "tokens_used": 0, "time_ms": 0}
    else:
        # Summary in context of a methodology
        prompt = f"""Примени метод {req.framework_id} для выделения ключевых выводов из текста.
Сократи до {req.max_length} предложений.

{req.text[:3000]}

Формат:
1. [ключевой вывод]
2. [ключевой вывод]
..."""
        result = template_analyze(prompt, system_prompt=req.framework_id)

    return {
        "original_length": len(req.text),
        "summary": result.get("raw_response", ""),
        "time_ms": result.get("time_ms", 0),
    }


# ---- Visitor tracking ----
@app.post("/api/v1/visitor")
async def track_visitor(req: VisitorRequest):
    """Записывает посещение."""
    conn = get_db()
    session_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO visitors (ip, user_agent, page, referer, session_id) VALUES (?, ?, ?, ?, ?)",
        ("unknown", "unknown", req.page, req.referer, session_id),
    )
    conn.commit()
    total = conn.execute("SELECT COUNT(DISTINCT session_id) FROM visitors").fetchone()[0]
    today = conn.execute("SELECT COUNT(DISTINCT session_id) FROM visitors WHERE date(timestamp) = date('now')").fetchone()[0]
    conn.close()
    return {"session_id": session_id, "total_visitors": total, "today_visitors": today}


@app.get("/api/v1/visitors")
async def get_visitors():
    """Статистика посетителей."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    unique = conn.execute("SELECT COUNT(DISTINCT session_id) FROM visitors").fetchone()[0]
    today = conn.execute("SELECT COUNT(*) FROM visitors WHERE date(timestamp) = date('now')").fetchone()[0]
    pages = conn.execute("SELECT page, COUNT(*) as c FROM visitors GROUP BY page ORDER BY c DESC LIMIT 10").fetchall()
    conn.close()
    return {
        "total_hits": total, "unique_visitors": unique, "today_hits": today,
        "top_pages": [{"page": r["page"], "hits": r["c"]} for r in pages],
    }


# ---- Beta signups ----
@app.post("/api/v1/signup")
async def signup(req: SignupRequest):
    """Регистрация бета-тестера."""
    conn = get_db()
    conn.execute(
        "INSERT INTO beta_signups (email, name, use_case, source) VALUES (?, ?, ?, ?)",
        (req.email, req.name, req.use_case, req.source),
    )
    total = conn.execute("SELECT COUNT(*) FROM beta_signups").fetchone()[0]
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Спасибо! Вы в списке бета-тестеров.", "total_signups": total}


@app.get("/api/v1/signups")
async def get_signups():
    """Список бета-тестеров (только количество)."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM beta_signups").fetchone()[0]
    today = conn.execute("SELECT COUNT(*) FROM beta_signups WHERE date(timestamp) = date('now')").fetchone()[0]
    conn.close()
    return {"total": total, "today": today}


# ---- Costs ----
@app.get("/api/v1/costs")
async def get_costs():
    """Возвращает учёт затрат."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM costs ORDER BY timestamp DESC").fetchall()
    total = conn.execute("SELECT SUM(amount_rub) FROM costs").fetchone()[0] or 0
    conn.close()
    return {
        "total_rub": total,
        "items": [dict(r) for r in rows],
    }


# ==================== Модуль монетизации ====================


def _get_session(request, x_session_id: str = "") -> str:
    """Определяет session_id: заголовок или IP."""
    if x_session_id:
        return x_session_id
    client = request.client
    return f"ip_{client.host}" if client else "unknown"


@app.get("/api/v1/plans")
async def list_plans():
    """Список тарифов с ценами и лимитами"""
    from engine.billing.plans import list_plans, Plan
    plans = list_plans()
    return {
        "plans": {
            pid: {
                "id": p.id,
                "name": p.name,
                "price_rub": p.price_rub,
                "price_stars": p.price_stars,
                "analyses_per_day": p.analyses_per_day,
                "max_tokens": p.max_tokens,
                "features": {
                    "deep_analyze": p.deep_analyze,
                    "brainstorm": p.brainstorm,
                    "file_analyze": p.file_analyze,
                    "pdf_export": p.pdf_export,
                    "custom_backends": p.custom_backends,
                    "history_days": p.history_days,
                }
            }
            for pid, p in plans.items()
        }
    }


@app.get("/api/v1/my/status")
async def my_status(request: Request, x_session_id: str = Header(default="")):
    """Моя подписка + статистика использования"""
    from engine.billing.limits import get_plan_for_session, check_analyze_limit, get_usage_stats
    from engine.billing.subscriptions import get_subscription

    sid = _get_session(request, x_session_id)

    plan_id = get_plan_for_session(sid)
    sub = get_subscription(sid)
    allowed, used, limit = check_analyze_limit(sid, plan_id)
    stats = get_usage_stats(sid)

    return {
        "session_id": sid,
        "plan_id": plan_id,
        "plan_name": sub.get("plan_name", plan_id),
        "is_active": sub.get("is_active", True),
        "expires_at": sub.get("expires_at", ""),
        "limits": {
            "analyses_today": used,
            "analyses_limit": limit,
            "can_analyze": allowed,
        },
        "usage": stats,
    }


@app.get("/api/v1/my/usage")
async def my_usage(request: Request, x_session_id: str = Header(default="")):
    """Детальная статистика использования"""
    from engine.billing.limits import get_usage_stats
    sid = _get_session(request, x_session_id)
    return get_usage_stats(sid)


@app.get("/api/v1/my/invoices")
async def my_invoices(request: Request, x_session_id: str = Header(default="")):
    """История платежей"""
    from engine.billing.payments import get_user_invoices
    sid = _get_session(request, x_session_id)
    return {"invoices": get_user_invoices(sid)}


@app.post("/api/v1/my/upgrade")
async def upgrade_plan(
    plan_id: str,
    request: Request,
    x_session_id: str = Header(default=""),
):
    """Апгрейд подписки (заглушка — создаёт инвойс)"""
    from engine.billing.subscriptions import upgrade_from_free
    from engine.billing.payments import create_invoice
    from engine.billing.plans import PLANS

    sid = _get_session(request, x_session_id)
    plan = PLANS.get(plan_id)

    if not plan:
        return {"ok": False, "error": f"Тариф {plan_id} не найден"}

    # Создаём счёт
    invoice = create_invoice(sid, plan_id, plan.price_stars)
    if not invoice:
        return {"ok": False, "error": "Не удалось создать счёт"}

    return {
        "ok": True,
        "message": f"Счёт на {plan.name} создан",
        "invoice": invoice,
        "pay_url": f"https://t.me/analion_bot?start=pay_{invoice['id']}",
        "note": "После оплаты через Telegram Stars подписка активируется автоматически",
    }


@app.post("/api/v1/webhook/payment")
async def payment_webhook(data: dict):
    """Вебхук от Telegram Payments / ЮKassa."""
    from engine.billing.payments import confirm_payment

    invoice_id = data.get("invoice_id") or data.get("payload", {}).get("invoice_id")
    payment_id = data.get("payment_id", "")

    if not invoice_id:
        return {"ok": False, "error": "No invoice_id"}

    ok = confirm_payment(int(invoice_id), payment_id)
    return {"ok": ok}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8101)
