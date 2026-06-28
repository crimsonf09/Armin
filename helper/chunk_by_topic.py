"""Split daily chat messages into topic chunks using Gemini."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def load_gemini_config(env_path: Path | None = None) -> tuple[str, str]:
    if env_path and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return api_key, model


def format_messages_for_prompt(messages: list[dict]) -> str:
    lines: list[str] = []
    for index, message in enumerate(messages, start=1):
        content = message.get("content", "").strip()
        links = message.get("links") or []
        if not content and not links:
            continue
        suffix = f" [links: {', '.join(links)}]" if links else ""
        lines.append(f"[{index}] {message['sender']} ({message['timestamp']}): {content}{suffix}")
    return "\n".join(lines)


def build_topic_prompt(chat_text: str, date_label: str) -> str:
    return f"""Split this day's chat into topic-based chunks.

Rules:
- Group related messages about the same topic into one chunk.
- Each chunk must contain the original chat text for that topic using lines like "Sender: message".
- Keep the original language.
- Return valid JSON only in this exact shape:
{{"chunks": ["chunk text 1", "chunk text 2"]}}
- If all messages belong to one topic, return one chunk in the array.
- Do not wrap the JSON in markdown fences.

Date: {date_label}

Messages:
{chat_text}
"""


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def call_gemini_json(prompt: str, api_key: str, model: str) -> dict:
    url = GEMINI_API_URL.format(model=model)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, params={"key": api_key}, json=payload)
        if response.is_error:
            raise RuntimeError(f"Gemini request failed ({response.status_code}): {response.text}")

        data = response.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")

    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part.get("text"), str)).strip()
    if not text:
        raise RuntimeError("Gemini returned empty text")

    parsed = _extract_json(text)
    chunks = parsed.get("chunks")
    if not isinstance(chunks, list):
        raise RuntimeError('Gemini JSON must contain a "chunks" array')

    return {"chunks": [str(chunk).strip() for chunk in chunks if str(chunk).strip()]}


def split_day_by_topic(
    raw_chat_path: Path,
    output_path: Path | None = None,
    env_path: Path | None = None,
) -> Path:
    raw_chat_path = raw_chat_path.resolve()
    raw_data = json.loads(raw_chat_path.read_text(encoding="utf-8"))
    chat_text = format_messages_for_prompt(raw_data.get("messages", []))
    if not chat_text.strip():
        result = {"chunks": []}
    else:
        api_key, model = load_gemini_config(env_path)
        prompt = build_topic_prompt(chat_text, raw_data.get("date", raw_chat_path.parent.name))
        result = call_gemini_json(prompt, api_key, model)

    target = output_path or raw_chat_path.parent / "chunk.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def split_all_days(chats_root: Path, env_path: Path | None = None) -> list[Path]:
    written: list[Path] = []
    for raw_chat_path in sorted(chats_root.glob("*/raw_chat.json")):
        written.append(split_day_by_topic(raw_chat_path, env_path=env_path))
    return written
