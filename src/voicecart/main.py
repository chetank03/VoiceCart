from __future__ import annotations

import argparse
import asyncio

from voicecart.config import load_settings
from voicecart.nlu import VoiceCartError, parse_grocery_request
from voicecart.swiggy_mcp import SwiggyMcpClient
from voicecart.voice import build_listener, build_speaker


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceCart grocery assistant")
    parser.add_argument("--input", choices=["text", "voice"], default="text")
    parser.add_argument("--use-mcp", action="store_true", help="Build the cart through Swiggy MCP")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.add_argument("--tts", action="store_true", help="Speak responses with local TTS")
    args = parser.parse_args()

    settings = load_settings()
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not set. Add it to your .env file.")

    listener = build_listener(args.input, api_key=settings.gemini_api_key)
    speaker = build_speaker(args.tts)

    speaker.say("VoiceCart is ready. English and Telugu are supported.")
    try:
        text = listener.listen()
        request = parse_grocery_request(text, api_key=settings.gemini_api_key)
    except VoiceCartError as e:
        speaker.say(str(e))
        return

    if not request.items:
        speaker.say("I could not find any groceries in that request.")
        return

    speaker.say(_localized_found_message(request.language, request.summary()))

    if settings.confirm_before_cart and not _confirm(_localized_confirm_prompt(request.language)):
        speaker.say(_localized_stop_message(request.language))
        return

    if args.use_mcp:
        client = SwiggyMcpClient(dry_run=args.dry_run)
        results = asyncio.run(client.build_cart(request.items))
        for result in results:
            speaker.say(f"{result.item.name}: {result.status}. {result.detail}")
    else:
        speaker.say("MCP cart building is off. Run again with --use-mcp to build the cart.")


def _confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in {"y", "yes", "అవును", "ha", "haa"}


def _localized_found_message(language: str, summary: str) -> str:
    if language in {"te", "mixed"}:
        return f"I found these items: {summary}. ఇవి సరేనా?"
    return f"I found: {summary}"


def _localized_confirm_prompt(language: str) -> str:
    if language in {"te", "mixed"}:
        return "Swiggy Instamart cart build cheyyala?"
    return "Build this Swiggy Instamart cart?"


def _localized_stop_message(language: str) -> str:
    if language in {"te", "mixed"}:
        return "Okay, ikkade stop chestanu."
    return "Okay, I will stop here."


if __name__ == "__main__":
    main()
