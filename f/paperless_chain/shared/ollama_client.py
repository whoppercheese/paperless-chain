#requirements:
#httpx==0.27.2

import json
import os
import re

import httpx


def _chat_timeout() -> httpx.Timeout:
    seconds = float(os.environ.get("OLLAMA_CHAT_TIMEOUT", "600"))
    return httpx.Timeout(connect=30.0, read=seconds, write=30.0, pool=30.0)


def _embed_timeout() -> httpx.Timeout:
    seconds = float(os.environ.get("OLLAMA_EMBED_TIMEOUT", "300"))
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
    temperature: float = 0.2,
    format_schema: dict | None = None,
) -> dict:
    url = os.environ["OLLAMA_URL"].rstrip("/")
    model = os.environ.get("OLLAMA_LLM_MODEL", "qwen3")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "format": format_schema or "json",
        "options": {"temperature": temperature},
    }
    _log_llm_request(model, system, user, temperature)
    content = ""
    with httpx.Client(timeout=_chat_timeout()) as client:
        with client.stream("POST", f"{url}/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                message = chunk.get("message") or {}
                if message.get("content"):
                    content += message["content"]
                if chunk.get("done"):
                    break

    text = content.strip()
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


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    url = os.environ["OLLAMA_URL"].rstrip("/")
    model = os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3")
    with httpx.Client(timeout=_embed_timeout()) as client:
        r = client.post(f"{url}/api/embed", json={"model": model, "input": texts})
        r.raise_for_status()
        data = r.json()
    return data.get("embeddings") or [data["embedding"]]
