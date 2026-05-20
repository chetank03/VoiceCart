from __future__ import annotations

import io
import sys
import threading
import wave
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import sounddevice as sd
from google import genai
from google.genai import types


SAMPLE_RATE = 16000


class Listener(Protocol):
    def listen(self) -> str:
        ...


class Speaker(Protocol):
    def say(self, text: str) -> None:
        ...


@dataclass
class TextListener:
    prompt: str = "What groceries do you want? "

    def listen(self) -> str:
        return input(self.prompt).strip()


class ConsoleSpeaker:
    def say(self, text: str) -> None:
        _print_text(text)


class PyttsxSpeaker:
    def __init__(self) -> None:
        import pyttsx3

        self._engine = pyttsx3.init()

    def say(self, text: str) -> None:
        _print_text(text)
        self._engine.say(text)
        self._engine.runAndWait()


class GeminiVoiceListener:
    """Records from microphone until Enter is pressed, then transcribes via Gemini."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def listen(self) -> str:
        input("Press Enter to start recording...")
        print("Recording — speak now. Press Enter again to stop.")

        frames: list[np.ndarray] = []
        stop_event = threading.Event()

        def _audio_callback(indata, frame_count, time_info, status) -> None:
            frames.append(indata.copy())

        def _wait_for_enter() -> None:
            input()
            stop_event.set()

        stopper = threading.Thread(target=_wait_for_enter, daemon=True)
        stopper.start()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=_audio_callback,
        ):
            stop_event.wait()

        print("Processing...")
        audio = np.concatenate(frames, axis=0)
        wav_bytes = _to_wav(audio)
        return _transcribe(wav_bytes, self._api_key)


def _to_wav(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def _transcribe(wav_bytes: bytes, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            types.Part(inline_data=types.Blob(mime_type="audio/wav", data=wav_bytes)),
            types.Part(text=(
                "Transcribe this audio exactly as spoken. "
                "The speaker may be in English, Telugu script, or mixed Telugu-English. "
                "Return only the transcribed text, nothing else."
            )),
        ],
    )
    return response.text.strip()


def build_listener(mode: str, api_key: str | None = None) -> Listener:
    if mode == "voice":
        if not api_key:
            raise ValueError("Voice mode needs GEMINI_API_KEY.")
        return GeminiVoiceListener(api_key)
    return TextListener()


def build_speaker(use_tts: bool) -> Speaker:
    if use_tts:
        return PyttsxSpeaker()
    return ConsoleSpeaker()


def _print_text(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            print(text)
            return
        print(text.encode("ascii", errors="replace").decode("ascii"))
