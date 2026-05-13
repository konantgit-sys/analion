"""
Subscriptions — управление подписками пользователей.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict
from .plans import get_plan, get_default_plan

DB_PATH = os.environ.get(
    "ANALION_DB_ENGINE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "analion.db"),
)


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_subscription(session_id: str) -> Dict:
    """Возвращает полную информацию о подписке."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE session_id=?", (session_id,)
    ).fetchone()
    conn.close()

    if not row:
        return {
            "session_id": session_id,
            "plan_id": "free",
            "plan_name": get_default_plan().name,
            "expires_at": "",
            "is_active": True,
        }

    sub = dict(row)
    plan = get_plan(sub["plan_id"]) or get_default_plan()
    sub["plan_name"] = plan.name
    # Проверка истекла ли
    if sub.get("expires_at"):
        try:
            expires = datetime.fromisoformat(sub["expires_at"])
            sub["is_active"] = expires > datetime.now()
        except Exception:
            sub["is_active"] = True
    else:
        sub["is_active"] = True

    return sub


def set_plan(session_id: str, plan_id: str, duration_days: int = 30) -> bool:
    """Устанавливает или меняет план подписки."""
    plan = get_plan(plan_id)
    if not plan:
        return False

    from datetime import timedelta
    expires = (datetime.now() + timedelta(days=duration_days)).isoformat()
    now = datetime.now().isoformat()

    conn = _get_db()
    conn.execute("""
        INSERT INTO subscriptions (session_id, plan_id, expires_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            plan_id=excluded.plan_id,
            expires_at=excluded.expires_at,
            updated_at=excluded.updated_at
    """, (session_id, plan_id, expires, now))
    conn.commit()
    conn.close()
    return True


def upgrade_from_free(session_id: str, plan_id: str) -> Dict:
    """
    Апгрейд с бесплатного на платный тариф.
    """
    current = get_subscription(session_id)
    if current["plan_id"] != "free" and current.get("is_active"):
        return {"ok": False, "error": "У вас уже активна платная подписка"}

    ok = set_plan(session_id, plan_id)
    if not ok:
        return {"ok": False, "error": "Неверный тариф"}

    plan = get_plan(plan_id)
    return {
        "ok": True,
        "session_id": session_id,
        "plan_id": plan_id,
        "plan_name": plan.name if plan else plan_id,
        "message": f"Подписка {plan.name if plan else plan_id} активирована",
    }
