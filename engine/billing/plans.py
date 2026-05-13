"""
Plans — тарифы и лимиты Analion.
Определяет что доступно на каждом уровне подписки.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Plan:
    id: str
    name: str
    price_rub: int          # цена в рублях/мес
    price_stars: int        # цена в Telegram Stars
    analyses_per_day: int   # AI-анализов в день
    max_tokens: int         # макс токенов на анализ
    deep_analyze: bool      # F9 доступен
    brainstorm: bool        # F13 доступен
    file_analyze: bool      # F14 доступен
    pdf_export: bool        # F5 доступен
    custom_backends: bool   # свои ключи
    history_days: int       # хранение истории
    price_monthly_rub: int = 0
    price_yearly_rub: int = 0


# Определение тарифов
PLANS: Dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Бесплатный",
        price_rub=0,
        price_stars=0,
        analyses_per_day=3,
        max_tokens=2048,
        deep_analyze=False,
        brainstorm=False,
        file_analyze=False,
        pdf_export=False,
        custom_backends=False,
        history_days=7,
    ),
    "starter": Plan(
        id="starter",
        name="Starter",
        price_rub=499,
        price_stars=50,
        analyses_per_day=20,
        max_tokens=8192,
        deep_analyze=True,
        brainstorm=True,
        file_analyze=True,
        pdf_export=True,
        custom_backends=False,
        history_days=30,
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_rub=1490,
        price_stars=150,
        analyses_per_day=100,
        max_tokens=16384,
        deep_analyze=True,
        brainstorm=True,
        file_analyze=True,
        pdf_export=True,
        custom_backends=True,
        history_days=365,
    ),
    "unlimited": Plan(
        id="unlimited",
        name="Unlimited",
        price_rub=4990,
        price_stars=500,
        analyses_per_day=9999,
        max_tokens=32768,
        deep_analyze=True,
        brainstorm=True,
        file_analyze=True,
        pdf_export=True,
        custom_backends=True,
        history_days=3650,
    ),
}


def get_plan(plan_id: str) -> Optional[Plan]:
    return PLANS.get(plan_id)


def get_default_plan() -> Plan:
    return PLANS["free"]


def list_plans() -> Dict[str, Plan]:
    return PLANS
