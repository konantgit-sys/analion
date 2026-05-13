"""
Backend stubs — заглушки для внешних API.
Активируются автоматически при наличии ключа в переменных окружения.
"""
import os
import time
import requests


def _check_env(var_name: str) -> str:
    """Проверяет наличие ключа в окружении."""
    return os.environ.get(var_name, "").strip()


# ---------- OpenAI ----------
OPENAI_KEY = _check_env("ANALION_OPENAI_KEY")
OPENAI_URL = os.environ.get("ANALION_OPENAI_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_MODEL = os.environ.get("ANALION_OPENAI_MODEL", "gpt-4o-mini")


def openai_analyze(prompt: str, model: str = None, max_tokens: int = 4000) -> dict:
    if not OPENAI_KEY:
        return {"error": "no_key", "raw_response": None, "tokens_used": 0, "time_ms": 0, "backend": "openai"}

    start = time.time()
    try:
        r = requests.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={"model": model or OPENAI_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": max_tokens},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "error": None,
            "raw_response": data["choices"][0]["message"]["content"],
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
            "time_ms": int((time.time() - start) * 1000),
            "backend": "openai",
        }
    except Exception as e:
        return {"error": str(e), "raw_response": None, "tokens_used": 0, "time_ms": int((time.time() - start) * 1000), "backend": "openai"}


# ---------- DeepSeek ----------
DEEPSEEK_KEY = _check_env("ANALION_DEEPSEEK_KEY")
DEEPSEEK_MODEL = os.environ.get("ANALION_DEEPSEEK_MODEL", "deepseek-chat")


def deepseek_analyze(prompt: str, model: str = None, max_tokens: int = 4000) -> dict:
    if not DEEPSEEK_KEY:
        return {"error": "no_key", "raw_response": None, "tokens_used": 0, "time_ms": 0, "backend": "deepseek"}

    start = time.time()
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": model or DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": max_tokens},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "error": None,
            "raw_response": data["choices"][0]["message"]["content"],
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
            "time_ms": int((time.time() - start) * 1000),
            "backend": "deepseek",
        }
    except Exception as e:
        return {"error": str(e), "raw_response": None, "tokens_used": 0, "time_ms": int((time.time() - start) * 1000), "backend": "deepseek"}


# ---------- Gemini ----------
GEMINI_KEY = _check_env("ANALION_GEMINI_KEY")
GEMINI_MODEL = os.environ.get("ANALION_GEMINI_MODEL", "gemini-2.0-flash")


def gemini_analyze(prompt: str, model: str = None, max_tokens: int = 4000) -> dict:
    if not GEMINI_KEY:
        return {"error": "no_key", "raw_response": None, "tokens_used": 0, "time_ms": 0, "backend": "gemini"}

    start = time.time()
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model or GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
        r = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": max_tokens}},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return {
            "error": None,
            "raw_response": content,
            "tokens_used": data.get("usageMetadata", {}).get("totalTokenCount", 0),
            "time_ms": int((time.time() - start) * 1000),
            "backend": "gemini",
        }
    except Exception as e:
        return {"error": str(e), "raw_response": None, "tokens_used": 0, "time_ms": int((time.time() - start) * 1000), "backend": "gemini"}


# ---------- Local ----------
LOCAL_MODEL_PATH = os.environ.get("ANALION_LOCAL_MODEL", "")
LOCAL_MODEL = None
LOCAL_TOKENIZER = None


def local_analyze(prompt: str, model: str = None, max_tokens: int = 4000) -> dict:
    global LOCAL_MODEL, LOCAL_TOKENIZER

    if not LOCAL_MODEL_PATH:
        return {"error": "no_model", "raw_response": None, "tokens_used": 0, "time_ms": 0, "backend": "local"}

    start = time.time()
    try:
        # Lazy load
        if LOCAL_MODEL is None:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            LOCAL_TOKENIZER = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH, trust_remote_code=True)
            LOCAL_MODEL = AutoModelForCausalLM.from_pretrained(LOCAL_MODEL_PATH, trust_remote_code=True, torch_dtype="auto", device_map="cpu")

        messages = [{"role": "user", "content": prompt}]
        text = LOCAL_TOKENIZER.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = LOCAL_TOKENIZER([text], return_tensors="pt")
        with torch.no_grad():
            outputs = LOCAL_MODEL.generate(**inputs, max_new_tokens=max_tokens, temperature=0.7, do_sample=True, pad_token_id=LOCAL_TOKENIZER.eos_token_id)
        response = LOCAL_TOKENIZER.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)

        return {
            "error": None,
            "raw_response": response,
            "tokens_used": 0,  # не считаем для локальной
            "time_ms": int((time.time() - start) * 1000),
            "backend": "local",
        }
    except Exception as e:
        return {"error": str(e), "raw_response": None, "tokens_used": 0, "time_ms": int((time.time() - start) * 1000), "backend": "local"}
