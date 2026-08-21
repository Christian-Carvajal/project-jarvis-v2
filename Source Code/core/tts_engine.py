import asyncio
import os
import re
import tempfile
from typing import AsyncGenerator, Union
import edge_tts
import pyttsx3

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


class TTSEngine:
    """Hybrid low-latency Text-to-Speech Engine with decoupled async speech queue and SoundDevice/Pygame HALT controls."""

    def __init__(self, voice: str = "en-GB-RyanNeural"):
        self.voice = voice
        self.speech_queue = asyncio.Queue()
        self.is_processing = False
        self.is_speaking = False
        self._worker_task = None

        if HAS_PYGAME and not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                pass
        self._init_fallback_engine()

    def start_worker(self):
        """Start isolated background audio consumer thread."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._process_speech_queue())

    async def _process_speech_queue(self):
        while True:
            text = await self.speech_queue.get()
            if text is None:  # Shutdown signal
                break
            try:
                await self.speak_text(text)
            except Exception as e:
                print(f"[TTS Worker Error: {e}]")
            finally:
                self.speech_queue.task_done()

    def _init_fallback_engine(self):
        try:
            self.fallback_engine = pyttsx3.init()
            self.fallback_engine.setProperty('rate', 180)
        except Exception:
            self.fallback_engine = None

    def stop_playback(self):
        """Halts active audio output stream and clears TTS playback queue."""
        self.is_speaking = False
        self.is_processing = False
        self.stop_audio()
        if HAS_SOUNDDEVICE:
            try:
                sd.stop()
            except Exception:
                pass

    def stop_speech(self):
        """Alias wrapper for audio engine HALT interrupt calls."""
        self.stop_playback()

    def stop_audio(self):
        """Stop any active audio playback immediately."""
        try:
            if HAS_PYGAME and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass

    async def speak_text(self, text: str):
        """Synthesize and play a full string of text asynchronously."""
        if not text.strip():
            return

        self.is_speaking = True
        played_successfully = False
        if HAS_PYGAME:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    temp_path = fp.name

                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(temp_path)

                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and self.is_speaking:
                    await asyncio.sleep(0.05)

                pygame.mixer.music.unload()
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                played_successfully = True
            except Exception as e:
                print(f"\n[Edge-TTS Notice: {e}]")

        if not played_successfully and self.fallback_engine and self.is_speaking:
            try:
                self.fallback_engine.say(text)
                self.fallback_engine.runAndWait()
            except Exception as e:
                print(f"\n[TTS Fallback Error: {e}]")

        self.is_speaking = False

    async def speak_stream(self, text_or_stream: Union[str, AsyncGenerator[str, None]]):
        """Streams text or async token generator to speech output."""
        if isinstance(text_or_stream, str):
            await self.speak_text(text_or_stream)
            return

        self.start_worker()
        sentence_buffer = ""
        delimiters = (".", "!", "?", "\n", ";", ":")

        async for token in text_or_stream:
            sentence_buffer += token

            if any(sentence_buffer.endswith(d) for d in delimiters) or len(sentence_buffer) > 100:
                clean_text = re.sub(r'<[^>]+>', '', sentence_buffer).strip()
                if clean_text:
                    await self.speech_queue.put(clean_text)
                sentence_buffer = ""

        if sentence_buffer.strip():
            clean_text = re.sub(r'<[^>]+>', '', sentence_buffer).strip()
            if clean_text:
                await self.speech_queue.put(clean_text)
