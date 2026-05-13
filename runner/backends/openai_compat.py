"""
OpenAI-Compatible Backend — универсальный вызов любого OpenAI-совместимого API.
Поддерживает: OpenAI, Together AI, Novita, DeepSeek, Groq, SambaNova, OpenRouter и т.д.
"""
import json
import requests

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "novita": "deepseek/deepseek-v4-flash",
    "sambanova": "Meta-Llama-3.3-70B-Instruct",
    "groq": "llama-3.3-70b-versatile",
    "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "openrouter": "openai/gpt-4o-mini",
}

BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "novita": "https://api.novita.ai/v3/openai",
    "sambanova": "https://api.sambanova.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


def analyze(prompt: str, system_prompt: str = "", model: str = None,
            api_key: str = None, base_url: str = None, provider: str = "mistral",
            max_tokens: int = 4096, temperature: float = 0.7) -> dict:
    """
    Универсальный вызов LLM через OpenAI-совместимый API.

    Параметры:
        provider: 'mistral' | 'openai' | 'deepseek' | 'novita' | 'sambanova' | 'groq' | 'together' | 'openrouter' | 'custom'
        api_key: ключ API (обязателен для всех кроме mistral)
        base_url: кастомный URL для provider='custom'
        model: модель (автоподбор если не указан)
    """
    # Mistral — отдельный API (не OpenAI-совместимый)
    if provider == "mistral":
        return _call_mistral(prompt, system_prompt, model or "mistral-small-latest", api_key, max_tokens, temperature)

    # OpenAI-совместимые провайдеры
    if provider == "custom":
        if not base_url:
            return {"error": "Для custom провайдера укажите base_url", "raw_response": ""}
    else:
        base_url = BASE_URLS.get(provider)
        if not base_url:
            return {"error": f"Неизвестный провайдер: {provider}. Доступны: {list(BASE_URLS.keys())}", "raw_response": ""}

    if not api_key:
        return {"error": f"Требуется api_key для провайдера {provider}", "raw_response": ""}

    model = model or DEFAULT_MODELS.get(provider, "gpt-4o-mini")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=120,
        )

        if resp.status_code == 401:
            return {"error": "Неверный API ключ", "raw_response": ""}
        if resp.status_code == 402 or resp.status_code == 403:
            body = resp.json()
            return {"error": f"Недостаточно баланса: {body.get('error',{}).get('message','')}", "raw_response": ""}
        if resp.status_code == 429:
            return {"error": "Превышен лимит запросов (rate limit)", "raw_response": ""}

        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return {"raw_response": content, "tokens_used": tokens, "model": model, "provider": provider}
    except requests.exceptions.Timeout:
        return {"error": f"Таймаут {provider} (>120s)", "raw_response": ""}
    except Exception as e:
        return {"error": f"Ошибка {provider}: {e}", "raw_response": ""}


def _call_mistral(prompt: str, system_prompt: str, model: str, api_key: str,
                  max_tokens: int, temperature: float) -> dict:
    """Вызов Mistral API"""
    url = "https://api.mistral.ai/v1/chat/completions"
    if not api_key:
        return {"error": "Нет MISTRAL_API_KEY", "raw_response": ""}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return {"raw_response": content, "tokens_used": tokens, "model": model, "provider": "mistral"}
    except Exception as e:
        return {"error": f"Mistral error: {e}", "raw_response": ""}
