from __future__ import annotations

import json
import re

from google import genai
from google.genai import errors as genai_errors

from voicecart.models import GroceryItem, GroceryRequest


_PROMPT = """\
Extract all grocery items from the text below. The text may be in English, \
Telugu script, or mixed Telugu-English (Tenglish / code-switched speech).

Return ONLY valid JSON — no markdown fences, no explanation — in this exact shape:
{{
  "language": "<en|te|mixed>",
  "items": [
    {{"name": "<normalized English grocery name>", "quantity":  "<number as string>", "unit": "<kg|g|packet|packets|piece|pieces|litre|litres|dozen|  or empty string>"}}
  ]
}}

Rules:
- Translate Telugu or Tenglish item names to common English grocery names (e.g. పాలు → milk, perugu → curd, biyyam → rice).
- If no quantity is mentioned, use "1" and leave unit as an empty string.
- Strip filler words like "add cheyyi", "kavali", "add", "please", "order", "get".
- "language" should be "te" if the text is mostly Telugu script, "mixed" if it mixes scripts or uses Tenglish, "en" otherwise.

Text: {text}
"""


class VoiceCartError(Exception):
    pass


def parse_grocery_request(text: str, api_key: str) -> GroceryRequest:
    if not text.strip():
        raise VoiceCartError("No speech detected. Please try again.")

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=_PROMPT.format(text=text),
        )
    except genai_errors.ClientError as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise VoiceCartError("Gemini API quota exceeded. Please wait a moment and try again.") from e
        if "401" in str(e) or "API_KEY" in str(e):
            raise VoiceCartError("Invalid Gemini API key. Check your .env file.") from e
        raise VoiceCartError(f"Gemini API error: {e}") from e
    except Exception as e:
        raise VoiceCartError(f"Could not reach Gemini. Check your internet connection. ({e})") from e

    try:
        data = json.loads(_strip_fences(response.text))
    except (json.JSONDecodeError, AttributeError):
        raise VoiceCartError("Could not understand the response from Gemini. Please try again.")

    items = tuple(
        GroceryItem(
            name=entry["name"],
            original_name=None,
            quantity=f"{entry['quantity']} {entry.get('unit', '')}".strip(),
        )
        for entry in data.get("items", [])
        if entry.get("name")
    )
    return GroceryRequest(raw_text=text, items=items, language=data.get("language", "en"))


def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    return match.group(1) if match else text.strip()
