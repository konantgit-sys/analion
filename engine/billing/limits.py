"""
Limits — проверка квот и трекинг использования.
Привязан к БД Analion (таблица usage_log).
"""
import sqlite3
import os
from datetime import datetime, date
from typing import Optional, Tuple
from .plans import get_plan, get_default_plan

DB_PATH = os.environ.get(
    "ANALION_DB_ENGINE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "analion.db"),
)


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_limits_table():
    """Создаёт таблицы если нет."""
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            plan_id TEXT NOT NULL DEFAULT 'free',
            telegram_id INTEGER DEFAULT 0,
            stripe_id TEXT DEFAULT '',
            expires_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            date TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        DROP INDEX IF EXISTS idx_usage_session_date
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_session_date
        ON usage_log(session_id, date)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            amount_rub INTEGER,
            amount_stars INTEGER,
            plan_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            telegram_payment_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            paid_at TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def get_plan_for_session(session_id: str) -> str:
    """Возвращает plan_id для сессии. Если нет — создаёт free."""
    conn = _get_db()
    row = conn.execute(
        "SELECT plan_id FROM subscriptions WHERE session_id=?", (session_id,)
    ).fetchone()
    if row:
        plan_id = row["plan_id"]
        conn.close()
        return plan_id
    # Создаём бесплатную подписку
    conn.execute(
        "INSERT OR IGNORE INTO subscriptions (session_id, plan_id) VALUES (?, 'free')",
        (session_id,),
    )
    conn.commit()
    conn.close()
    return "free"


def get_daily_usage(session_id: str, endpoint: str = "analyze") -> int:
    """Сколько раз вызывал эндпоинт сегодня."""
    today = date.today().isoformat()
    conn = _get_db()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE session_id=? AND date=? AND endpoint=?",
        (session_id, today, endpoint),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def log_usage(session_id: str, endpoint: str = "analyze", tokens: int = 0):
    """Записывает факт использования."""
    today = date.today().isoformat()
    conn = _get_db()
    conn.execute(
        "INSERT INTO usage_log (session_id, date, endpoint, tokens_used) VALUES (?, ?, ?, ?)",
        (session_id, today, endpoint, tokens),
    )
    conn.commit()
    conn.close()


def check_analyze_limit(session_id: str, plan_id: str = None) -> Tuple[bool, int, int]:
    """
    Проверяет можно ли сделать анализ.
    Возвращает: (разрешено, использовано, лимит)
    """
    if plan_id is None:
        plan_id = get_plan_for_session(session_id)

    plan = get_plan(plan_id) or get_default_plan()
    used = get_daily_usage(session_id, "analyze")

    if used >= plan.analyses_per_day:
        return False, used, plan.analyses_per_day

    return True, used, plan.analyses_per_day


def get_usage_stats(session_id: str) -> dict:
    """Статистика использования за сегодня и всё время."""
    today = date.today().isoformat()
    conn = _get_db()
    # Сегодня
    today_row = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(tokens_used),0) as tokens "
        "FROM usage_log WHERE session_id=? AND date=?",
        (session_id, today),
    ).fetchone()
    # Всё время
    total_row = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(tokens_used),0) as tokens "
        "FROM usage_log WHERE session_id=?",
        (session_id,),
    ).fetchone()
    conn.close()
    return {
        "today_requests": today_row["cnt"] if today_row else 0,
        "today_tokens": today_row["tokens"] if today_row else 0,
        "total_requests": total_row["cnt"] if total_row else 0,
        "total_tokens": total_row["tokens"] if total_row else 0,
    }


# Инициализация при импорте
_init_limits_table()
