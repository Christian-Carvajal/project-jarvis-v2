import asyncio
import tempfile
import os
import time
import numpy as np
from typing import Optional, Callable, Tuple

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

from core.stt_engine import STTEngine
from core.tts_engine import TTSEngine

class AudioEngine:
    """Unified Duplex Audio Engine managing SoundDevice Streams, Acoustic Isolation Guard, Instant Post-TTS Buffer Flushing, and Visualizer Decibels."""

    def __init__(self, stt_engine: STTEngine, tts_engine: TTSEngine):
        self.stt = stt_engine
        self.tts = tts_engine

        self.duplex_state = "LISTENING"  # LISTENING, PROCESSING, EXECUTING, SPEAKING, COOLDOWN
        self.is_speaking_tts = False
        self.is_listening_mic = False
        self.last_speech_time = 0.0
        self.cooldown_duration = 0.15  # 150ms post-TTS safety cooldown

        self.audio_level = 0.0  # Decibel audio level callback for UI visualizer
        self.audio_level_callback: Optional[Callable[[float], None]] = None

        self._tts_stream: Optional[sd.OutputStream] = None
        self._interrupt_event = asyncio.Event()

    def set_audio_level_callback(self, callback: Callable[[float], None]):
        """Sets UI callback for live decibel energy level updates."""
        self.audio_level_callback = callback

    def _emit_audio_level(self, level: float):
        self.audio_level = level
        if self.audio_level_callback:
            try:
                self.audio_level_callback(level)
            except Exception:
                pass

    def interrupt_speech(self):
        """HALT / OVERRIDE & Barge-In: Flushes active speech playback and resets status to LISTENING."""
        self._interrupt_event.set()
        self.is_speaking_tts = False
        self.duplex_state = "LISTENING"
        if hasattr(self, 'tts') and self.tts:
            if hasattr(self.tts, 'stop_speech'):
                self.tts.stop_speech()
            elif hasattr(self.tts, 'stop_playback'):
                self.tts.stop_playback()
        self._emit_audio_level(0.0)

    def flush_microphone_buffer(self):
        """Flushes residual sounddevice input buffer to prevent self-transcription echo."""
        if HAS_SOUNDDEVICE and self.stt.input_device_index is not None:
            try:
                # Read and discard a 100ms audio block from stream
                with sd.InputStream(
                    samplerate=16000,
                    channels=1,
                    dtype='float32',
                    blocksize=1600,
                    device=self.stt.input_device_index
                ) as stream:
                    stream.read(1600)
            except Exception:
                pass

    async def speak_text_async(self, text: str) -> bool:
        """Synthesizes TTS speech using sounddevice output streaming with instant post-speech release."""
        if not text:
            return False

        self._interrupt_event.clear()
        self.is_speaking_tts = True
        self.duplex_state = "SPEAKING"

        try:
            # Await async TTS streaming coroutine safely. Release immediately post-audio playback.
            await self.tts.speak_stream(text)
        except Exception as e:
            print(f"[AudioEngine Speak Exception: {e}]")
        finally:
            self.is_speaking_tts = False
            self.duplex_state = "LISTENING"
            self.last_speech_time = time.time()
            self._emit_audio_level(0.0)

            # Instant Post-TTS State Release: Flush audio input buffer and enforce 150ms cooldown
            self.flush_microphone_buffer()
            await asyncio.sleep(self.cooldown_duration)

        return not self._interrupt_event.is_set()

    async def listen_for_command(self) -> Tuple[bool, str]:
        """Listens for user speech with multi-layer self-feedback isolation and VAD silence validation."""
        # 1. State Machine Guard: Refuse mic capture while JARVIS is speaking
        if self.is_speaking_tts or self.duplex_state in ["SPEAKING", "COOLDOWN"]:
            return False, ""

        if time.time() - self.last_speech_time < self.cooldown_duration:
            return False, ""

        self.is_listening_mic = True
        try:
            detected, spoken_text = await self.stt.detect_wake_word_or_command(timeout=1.5)
            if detected and not self.is_speaking_tts and self.duplex_state == "LISTENING":
                self._emit_audio_level(0.8)
                return True, spoken_text
        except Exception as e:
            print(f"[AudioEngine Listen Exception: {e}]")
        finally:
            self.is_listening_mic = False

        return False, ""
