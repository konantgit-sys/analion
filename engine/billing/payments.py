"""
Payments — платёжные интеграции Analion.
Поддерживает: Telegram Stars, заглушка для Stripe/ЮKassa.
"""
import os
import json
import sqlite3
from datetime import datetime, date
from typing import Optional, Dict
from .plans import PLANS, Plan

DB_PATH = os.environ.get(
    "ANALION_DB_ENGINE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "analion.db"),
)


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_invoice(session_id: str, plan_id: str, amount_stars: int) -> Optional[Dict]:
    """
    Создаёт счёт на оплату (Telegram Stars).
    Возвращает invoice_id для передачи в Telegram API.
    """
    plan = PLANS.get(plan_id)
    if not plan:
        return None

    conn = _get_db()
    cursor = conn.execute(
        "INSERT INTO invoices (session_id, amount_rub, amount_stars, plan_id, status) VALUES (?, ?, ?, ?, 'pending')",
        (session_id, plan.price_rub, amount_stars, plan_id),
    )
    invoice_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": invoice_id,
        "session_id": session_id,
        "plan_id": plan_id,
        "amount_stars": amount_stars,
        "amount_rub": plan.price_rub,
        "status": "pending",
    }


def confirm_payment(invoice_id: int, telegram_payment_id: str = "") -> bool:
    """Подтверждает оплату и активирует подписку."""
    conn = _get_db()
    row = conn.execute(
        "SELECT session_id, plan_id FROM invoices WHERE id=? AND status='pending'",
        (invoice_id,),
    ).fetchone()
    if not row:
        conn.close()
        return False

    session_id = row["session_id"]
    plan_id = row["plan_id"]
    now = datetime.now().isoformat()

    # Обновляем инвойс
    conn.execute(
        "UPDATE invoices SET status='paid', paid_at=?, telegram_payment_id=? WHERE id=?",
        (now, telegram_payment_id, invoice_id),
    )
    # Активируем подписку (на 30 дней)
    from datetime import timedelta
    expires = (datetime.now() + timedelta(days=30)).isoformat()
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


def get_invoice(invoice_id: int) -> Optional[Dict]:
    """Статус счёта."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_invoices(session_id: str, limit: int = 10) -> list:
    """История платежей пользователя."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM invoices WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_stars_invoice_link(invoice_id: int, plan: Plan, session_id: str) -> str:
    """
    Генерирует ссылку на оплату Telegram Stars.
    Формат: https://t.me/send?start=analion_sub_{invoice_id}
    Для продакшена — интеграция с @BotFather и Telegram Payments API.
    """
    return f"https://t.me/analion_bot?start=pay_{invoice_id}"
