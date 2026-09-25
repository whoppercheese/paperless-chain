#requirements:
#httpx==0.27.2

import json
import os
import re

import httpx


def _chat_timeout() -> httpx.Timeout:
    seconds = float(os.environ.get("LLM_CHAT_TIMEOUT", "600"))
    return httpx.Timeout(connect=30.0, read=seconds, write=30.0, pool=30.0)


def _embed_timeout() -> httpx.Timeout:
    seconds = float(os.environ.get("LLM_EMBED_TIMEOUT", "300"))
    return httpx.Timeout(connect=30.0, read=seconds, write=30.0, pool=30.0)


def _log_llm_request(model: str, system: str, user: str, temperature: float) -> None:
    print("=== Paperless-chAIn LLM Request ===")
    print(f"model: {model}")
    print(f"temperature: {temperature}")
    print("--- system ---")
    print(system)
    print("--- user ---")
    print(user)


def _log_llm_response(raw_response: str, parsed: dict | None = None) -> None:
    print("=== Paperless-chAIn LLM Response (raw) ===")
    print(raw_response)
    if parsed is not None:
        print("=== Paperless-chAIn LLM Response (parsed) ===")
        print(json.dumps(parsed, ensure_ascii=False, indent=2))


def chat_json(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0,
    format_schema: dict | None = None,
) -> dict:
    url = os.environ["LLM_URL"].rstrip("/")
    model = model or os.environ.get("LLM_MODEL", "qwen3")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": format_schema or "json",
        "think": False,
        "options": {"temperature": temperature},
    }
    _log_llm_request(model, system, user, temperature)
    with httpx.Client(timeout=_chat_timeout()) as client:
        response = client.post(f"{url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    text = ((data.get("message") or {}).get("content") or "").strip()
    try:
        parsed = json.loads(text)
        _log_llm_response(text, parsed)
        return parsed
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            _log_llm_response(text, parsed)
            return parsed
        _log_llm_response(text)
        raise ValueError(f"Could not parse JSON from model response: {text[:500]}")


def chat(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0,
) -> str:
    url = os.environ["LLM_URL"].rstrip("/")
    model = model or os.environ.get("LLM_MODEL", "qwen3")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": temperature},
    }
    _log_llm_request(model, system, user, temperature)
    with httpx.Client(timeout=_chat_timeout()) as client:
        response = client.post(f"{url}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    text = ((data.get("message") or {}).get("content") or "").strip()
    _log_llm_response(text)
    return text


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    if not texts:
        return []
    url = os.environ["LLM_URL"].rstrip("/")
    model = model or os.environ.get("LLM_EMBED_MODEL", "bge-m3")
    with httpx.Client(timeout=_embed_timeout()) as client:
        r = client.post(f"{url}/api/embed", json={"model": model, "input": texts})
        r.raise_for_status()
        data = r.json()
    return data.get("embeddings") or [data["embedding"]]
