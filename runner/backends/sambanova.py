"""
SambaNova Cloud LLM Backend
Uses Llama-4-Maverick-17B-128E-Instruct
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("SAMBANOVA_API_KEY", "")
API_URL = "https://api.sambanova.ai/v1/chat/completions"
MODEL = "Llama-4-Maverick-17B-128E-Instruct"

def analyze(prompt: str, system_prompt: str = "") -> dict:
    """Send prompt to SambaNova and return response."""
    if not API_KEY:
        return {"error": "SAMBANOVA_API_KEY not set in .env", "raw_response": ""}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
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
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return {"raw_response": content, "tokens_used": tokens, "model": MODEL}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}
