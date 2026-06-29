"""Split daily chat messages into enriched topic chunks using Gemini."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SCORE_KEYS = ("valence", "arousal", "stress", "engagement", "impact")


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


def is_included_message(message: dict) -> bool:
    content = message.get("content", "").strip()
    links = message.get("links") or []
    return bool(content or links)


def indexed_message_map(messages: list[dict]) -> dict[int, dict]:
    mapping: dict[int, dict] = {}
    for index, message in enumerate(messages, start=1):
        if is_included_message(message):
            mapping[index] = message
    return mapping


def format_messages_for_prompt(messages: list[dict]) -> str:
    lines: list[str] = []
    for index, message in indexed_message_map(messages).items():
        content = message.get("content", "").strip()
        links = message.get("links") or []
        suffix = f" [links: {', '.join(links)}]" if links else ""
        lines.append(f"[{index}] {message['sender']} ({message['timestamp']}): {content}{suffix}")
    return "\n".join(lines)


def iso_date_from_raw(raw_data: dict) -> str:
    day_starts_at = raw_data.get("day_starts_at", "")
    if day_starts_at:
        return day_starts_at.split(" ", 1)[0]
    date_label = raw_data.get("date", "")
    if date_label:
        parts = date_label.split("/")
        if len(parts) == 3:
            year, month, day = parts
            full_year = 2000 + int(year) if len(year) == 2 else int(year)
            return f"{full_year:04d}-{int(month):02d}-{int(day):02d}"
    raise ValueError("Could not derive ISO date from raw chat data")


def validate_topic_scores(scores: dict) -> dict[str, float]:
    if not isinstance(scores, dict):
        raise ValueError("topic_scores must be an object")

    validated: dict[str, float] = {}
    for key in SCORE_KEYS:
        if key not in scores:
            raise ValueError(f"topic_scores missing required key: {key}")
        value = float(scores[key])
        validated[key] = max(0.0, min(1.0, value))
    return validated


def build_topic_prompt(chat_text: str, date_label: str) -> str:
    return f"""Split this day's chat into topic-based chunks.

Rules:
- Group related messages about the same topic into one chunk.
- Use the message numbers shown in brackets (e.g. [1], [2]) as message_indices.
- Every numbered message must appear in exactly one topic.
- Keep topic_summary and keywords in the original language of the chat.
- topic_scores must be numbers between 0 and 1:
  - valence: positive vs negative emotional tone
  - arousal: energy or excitement level
  - stress: tension, worry, or pressure
  - engagement: how actively the participants interact
  - impact: emotional significance of the topic
- Return valid JSON only in this exact shape:
{{
  "topics": [
    {{
      "topic_summary": "short summary",
      "topic_scores": {{
        "valence": 0.0,
        "arousal": 0.0,
        "stress": 0.0,
        "engagement": 0.0,
        "impact": 0.0
      }},
      "keywords": ["keyword1", "keyword2"],
      "message_indices": [1, 2, 3]
    }}
  ]
}}
- If all messages belong to one topic, return one item in topics.
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


def call_gemini_topics(prompt: str, api_key: str, model: str) -> list[dict]:
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
    topics = parsed.get("topics")
    if not isinstance(topics, list) or not topics:
        raise RuntimeError('Gemini JSON must contain a non-empty "topics" array')

    return topics


def build_chunk_objects(raw_data: dict, topics: list[dict], day_folder: str) -> list[dict]:
    messages = raw_data.get("messages", [])
    index_map = indexed_message_map(messages)
    valid_indices = set(index_map)
    used_indices: set[int] = set()
    iso_date = iso_date_from_raw(raw_data)

    chunks: list[dict] = []
    for topic in topics:
        indices = topic.get("message_indices")
        if not isinstance(indices, list) or not indices:
            raise ValueError(f"{day_folder}: each topic must include message_indices")

        normalized_indices: list[int] = []
        for raw_index in indices:
            index = int(raw_index)
            if index not in valid_indices:
                raise ValueError(f"{day_folder}: invalid message index {index}")
            if index in used_indices:
                raise ValueError(f"{day_folder}: message index {index} assigned to multiple topics")
            used_indices.add(index)
            normalized_indices.append(index)

        keywords = topic.get("keywords")
        if not isinstance(keywords, list):
            raise ValueError(f"{day_folder}: keywords must be an array")

        chunks.append(
            {
                "date": iso_date,
                "topic_summary": str(topic.get("topic_summary", "")).strip(),
                "topic_scores": validate_topic_scores(topic.get("topic_scores", {})),
                "keywords": [str(keyword).strip() for keyword in keywords if str(keyword).strip()],
                "messages": [index_map[index] for index in normalized_indices],
            }
        )

    missing = valid_indices - used_indices
    if missing:
        raise ValueError(f"{day_folder}: unassigned message indices: {sorted(missing)}")

    return chunks


def clear_stale_chunk_files(day_folder: Path) -> None:
    for path in day_folder.glob("chunk*.json"):
        path.unlink()


def write_chunk_files(day_folder: Path, chunks: list[dict]) -> list[Path]:
    clear_stale_chunk_files(day_folder)
    written: list[Path] = []
    for index, chunk in enumerate(chunks, start=1):
        output_path = day_folder / f"chunk_{index}.json"
        output_path.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(output_path)
    return written


def split_day_by_topic(
    raw_chat_path: Path,
    env_path: Path | None = None,
) -> list[Path]:
    raw_chat_path = raw_chat_path.resolve()
    day_folder = raw_chat_path.parent
    raw_data = json.loads(raw_chat_path.read_text(encoding="utf-8"))
    chat_text = format_messages_for_prompt(raw_data.get("messages", []))

    if not chat_text.strip():
        clear_stale_chunk_files(day_folder)
        return []

    api_key, model = load_gemini_config(env_path)
    prompt = build_topic_prompt(chat_text, raw_data.get("date", day_folder.name))
    topics = call_gemini_topics(prompt, api_key, model)
    chunks = build_chunk_objects(raw_data, topics, day_folder.name)
    return write_chunk_files(day_folder, chunks)


def split_all_days(chats_root: Path, env_path: Path | None = None) -> list[Path]:
    written: list[Path] = []
    for raw_chat_path in sorted(chats_root.glob("*/raw_chat.json")):
        written.extend(split_day_by_topic(raw_chat_path, env_path=env_path))
    return written
