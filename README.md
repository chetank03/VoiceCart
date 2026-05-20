# VoiceCart

Raspberry Pi bilingual voice assistant starter for building a grocery cart on Swiggy Instamart through a Swiggy MCP server.

This project listens for English, Telugu, or mixed Telugu-English grocery requests, extracts a shopping list, normalizes common Telugu grocery names into search terms, and sends the cart-building task to a Swiggy MCP adapter. It intentionally keeps final checkout/payment behind explicit human confirmation.

## What It Can Do

- Take voice or typed grocery requests.
- Parse English, Telugu script, and common Telugu-English grocery phrases.
- Normalize common grocery words such as `పాలు`, `biyyam`, and `perugu`.
- Speak status updates on the Raspberry Pi.
- Build a dry-run cart plan before any live Swiggy MCP action.
- Keep the Swiggy integration isolated in `src/voicecart/swiggy_mcp.py`.

## What It Will Not Do

- Bypass login, OTP, CAPTCHA, location prompts, or payment confirmation.
- Place orders automatically without human review.
- Guess your final product choices when multiple close matches exist.

## Hardware

Recommended:

- Raspberry Pi 4 or 5
- USB microphone or ReSpeaker-style mic HAT
- Speaker or 3.5mm/audio HAT output
- Stable Wi-Fi

## Setup On Raspberry Pi OS

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip espeak-ng portaudio19-dev

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[voice,test]"
```

For offline speech recognition, download a Vosk model, for example `vosk-model-small-en-in-0.4`, and set:

```bash
cp .env.example .env
VOICECART_VOSK_MODEL=/home/pi/models/vosk-model-small-en-in-0.4
```

## First Run

Start in typed mode while developing:

```bash
voicecart --input text --dry-run
```

Example request:

```text
Add two packets of milk, 1 kg atta, tomatoes, and six bananas
```

Telugu examples:

```text
రెండు ప్యాకెట్లు పాలు, ఒక కిలో బియ్యం
paalu two packets and perugu one packet add cheyyi
```

When parsing looks good, run the Swiggy MCP dry run:

```bash
voicecart --input text --use-mcp --dry-run
```

After the real Swiggy MCP tool names and schema are connected in `src/voicecart/swiggy_mcp.py`, live cart changes can use:

```bash
voicecart --input voice --use-mcp --no-dry-run
```

## Environment

See `.env.example`.

## Development

```bash
pip install -e ".[test]"
pytest
```

## Notes

## Swiggy MCP Contract Needed

To finish the live integration, connect the actual MCP tools in `src/voicecart/swiggy_mcp.py`. Ideally the MCP exposes tools like:

- `search_products(query, location)`
- `add_to_cart(product_id, quantity)`
- `view_cart()`
- `remove_from_cart(cart_item_id)`
- `checkout_summary()`

Final checkout should still require a separate explicit confirmation.
