from __future__ import annotations

import json
import queue
import sys
from dataclasses import dataclass
from typing import Protocol


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


class VoskListener:
    def __init__(self, model_path: str, sample_rate: int = 16000) -> None:
        import sounddevice as sd
        from vosk import KaldiRecognizer, Model

        self._sd = sd
        self._sample_rate = sample_rate
        self._recognizer = KaldiRecognizer(Model(model_path), sample_rate)
        self._audio_queue: queue.Queue[bytes] = queue.Queue()

    def listen(self) -> str:
        def callback(indata, frames, time, status) -> None:  # noqa: ANN001
            if status:
                print(status, file=sys.stderr)
            self._audio_queue.put(bytes(indata))

        with self._sd.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            print("Listening. Speak your grocery list.")
            while True:
                data = self._audio_queue.get()
                if self._recognizer.AcceptWaveform(data):
                    result = json.loads(self._recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        return text


def build_listener(mode: str, vosk_model: str | None) -> Listener:
    if mode == "voice":
        if not vosk_model:
            raise ValueError("Voice mode needs VOICECART_VOSK_MODEL or --vosk-model.")
        return VoskListener(vosk_model)
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
