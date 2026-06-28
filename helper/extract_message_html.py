"""Extract Instagram message export HTML into JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup


def extract_thread_title(soup: BeautifulSoup) -> str:
    title_el = soup.select_one("div._a70e")
    if title_el:
        return title_el.get_text(strip=True)
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""


def extract_message_content(content_el) -> tuple[str, list[str], list[str]]:
    reactions = [li.get_text(strip=True) for li in content_el.select("ul._a6-q li")]

    links: list[str] = []
    for anchor in content_el.select("a[href]"):
        href = anchor["href"].strip()
        if href and href not in links:
            links.append(href)

    content_copy = BeautifulSoup(str(content_el), "html.parser")
    for ul in content_copy.select("ul._a6-q"):
        ul.decompose()

    text_parts: list[str] = []
    for div in content_copy.find_all("div"):
        if div.find("div") or div.find("a"):
            continue
        text = div.get_text(strip=True)
        if text and text not in text_parts:
            text_parts.append(text)

    return "\n".join(text_parts), links, reactions


def extract_messages(html_path: Path) -> dict:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    thread_title = extract_thread_title(soup)

    messages: list[dict] = []
    for block in soup.select("div.pam._3-95._2ph-._a6-g"):
        sender_el = block.select_one("div._3-95._2pim._a6-h._a6-i")
        content_el = block.select_one("div._3-95._a6-p")
        timestamp_el = block.select_one("div._3-94._a6-o")

        if not sender_el or not content_el or not timestamp_el:
            continue

        content, links, reactions = extract_message_content(content_el)
        messages.append(
            {
                "sender": sender_el.get_text(strip=True),
                "timestamp": timestamp_el.get_text(strip=True),
                "content": content,
                "links": links,
                "reactions": reactions,
            }
        )

    participants = sorted({message["sender"] for message in messages})

    return {
        "source_file": html_path.name,
        "thread_title": thread_title,
        "participants": participants,
        "message_count": len(messages),
        "messages": messages,
    }


def write_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Instagram message HTML to JSON")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "message_1.html",
        help="Path to the HTML export file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to the output JSON file (defaults to <input>.json)",
    )
    args = parser.parse_args()

    output_path = args.output or args.input.with_suffix(".json")
    data = extract_messages(args.input)
    write_json(data, output_path)
    print(f"Wrote {data['message_count']} messages to {output_path}")


if __name__ == "__main__":
    main()
