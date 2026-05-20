from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    location: str
    swiggy_token: str | None
    vosk_model: str | None
    confirm_before_cart: bool
    gemini_api_key: str | None


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        location=os.getenv("VOICECART_LOCATION", ""),
        swiggy_token=os.getenv("SWIGGY_MCP_TOKEN") or None,
        vosk_model=os.getenv("VOICECART_VOSK_MODEL") or None,
        confirm_before_cart=os.getenv("VOICECART_CONFIRM_BEFORE_CART", "true").lower()
        in {"1", "true", "yes"},
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
    )
