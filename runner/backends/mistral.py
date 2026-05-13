"""
Mistral AI LLM Backend
Uses mistral-large-latest with 2-key rotation
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-large-latest"

def analyze(prompt: str, system_prompt: str = "") -> dict:
    """Send prompt to Mistral and return response."""
    keys = [
        os.environ.get("MISTRAL_API_KEY", ""),
        os.environ.get("MISTRAL_API_KEY_2", ""),
    ]
    keys = [k for k in keys if k]

    if not keys:
        return {"error": "No MISTRAL_API_KEY set in .env", "raw_response": ""}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Try each key
    for key in keys:
        try:
            resp = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                },
                timeout=60,
            )
            if resp.status_code == 429:
                continue  # Rate limit, try next key
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return {"raw_response": content, "tokens_used": tokens, "model": MODEL}
        except Exception as e:
            if key == keys[-1]:
                return {"error": str(e), "raw_response": ""}
            continue

    return {"error": "All Mistral keys exhausted", "raw_response": ""}
