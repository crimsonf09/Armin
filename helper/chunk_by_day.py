"""Chunk extracted chat JSON into per-day folders (day starts at 5 AM)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


DAY_CUTOFF_HOUR = 5


def parse_message_timestamp(timestamp: str) -> datetime:
    normalized = timestamp.replace("\u202f", " ").replace("\xa0", " ").strip()
    return datetime.strptime(normalized, "%b %d, %Y, %I:%M %p")


def logical_day(message_time: datetime, cutoff_hour: int = DAY_CUTOFF_HOUR) -> date:
    return (message_time - timedelta(hours=cutoff_hour)).date()


def day_label(day: date) -> str:
    return f"{day.year % 100:02d}/{day.month}/{day.day}"


def day_folder_name(day: date) -> str:
    # Filesystem-safe folder name (slashes would create nested subfolders).
    return day_label(day).replace("/", "-")


def chunk_messages_by_day(
    data: dict,
    output_root: Path,
    cutoff_hour: int = DAY_CUTOFF_HOUR,
) -> list[Path]:
    grouped: dict[date, list[dict]] = defaultdict(list)

    for message in data["messages"]:
        parsed = parse_message_timestamp(message["timestamp"])
        day = logical_day(parsed, cutoff_hour=cutoff_hour)
        grouped[day].append(
            {
                **message,
                "parsed_timestamp": parsed.isoformat(),
            }
        )

    written: list[Path] = []
    for day in sorted(grouped):
        messages = sorted(grouped[day], key=lambda item: item["parsed_timestamp"])
        folder_name = day_folder_name(day)
        output_path = output_root / folder_name / "raw_chat.json"

        payload = {
            "date": day_label(day),
            "day_starts_at": f"{day.isoformat()} {cutoff_hour:02d}:00:00",
            "source_file": data.get("source_file"),
            "thread_title": data.get("thread_title"),
            "participants": data.get("participants", []),
            "message_count": len(messages),
            "messages": messages,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(output_path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk chat JSON into daily folders (5 AM cutoff)")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "message_1.json",
        help="Path to extracted chat JSON",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "chats",
        help="Root folder for day folders like 26-6-28/raw_chat.json",
    )
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    written = chunk_messages_by_day(data, args.output_root)
    print(f"Wrote {len(written)} day folders under {args.output_root}")


if __name__ == "__main__":
    main()
