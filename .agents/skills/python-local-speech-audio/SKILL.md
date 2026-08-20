---
name: python-local-speech-audio
description: >-
  Architectural patterns and procedures for 100% offline local speech recognition (STT),
  acoustic wake-word gating, voice activity detection (Silero VAD), SoundDevice streaming,
  and offline text-to-speech synthesis (TTS) using Python, faster-whisper, and Pygame/pyttsx3/Edge-TTS.
  Use when designing voice assistants, real-time microphone stream buffering, audio processing,
  wake word detection, or offline speech pipelines.
license: Apache-2.0
metadata:
  version: v1
  publisher: antigravity-community
---

# Local Python Speech & Voice Pipeline Skill

This skill provides production patterns for low-latency, fully offline speech-to-text (STT), voice activity detection (VAD), wake-word gating, and text-to-speech (TTS) in Python.

---

## 1. High-Performance Audio Pipeline Architecture

```text
Microphone (SoundDevice) -> 16kHz Mono Float32 -> Ring Buffer
                                                     │
                                                     ▼
                                          Silero VAD (Speech/Silence)
                                                     │
                                                     ▼
                                          faster-whisper (STT Engine)
                                                     │
                                                     ▼
                                      Acoustic Wake Word Filter
                                                     │
                                                     ▼
                                        LLM Core / Action Dispatch
                                                     │
                                                     ▼
                                         Edge-TTS / pyttsx3 / Pygame
```

---

## 2. Voice Activity Detection & Stream Buffering

```python
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

class OfflineSTTEngine:
    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.sample_rate = 16000

    def transcribe_audio_array(self, audio_data: np.ndarray) -> str:
        segments, _ = self.model.transcribe(
            audio_data,
            beam_size=5,
            language="en",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        return " ".join([seg.text.strip() for seg in segments]).strip()
```

---

## 3. Two-Stage Wake-Word Acoustic Gating

```python
from typing import Tuple

class WakeWordFilter:
    WAKE_KEYWORDS = ["hey jarvis", "hi jarvis", "hello jarvis", "jarvis"]

    @classmethod
    def filter_utterance(cls, raw_transcript: str) -> Tuple[bool, str]:
        text = raw_transcript.lower().strip()
        cleaned = "".join([c for c in text if c.isalnum() or c.isspace()]).strip()

        for wake in cls.WAKE_KEYWORDS:
            if cleaned == wake:
                return True, ""
            if cleaned.startswith(wake + " "):
                cmd = cleaned[len(wake):].strip()
                return True, cmd
            if wake in cleaned:
                parts = cleaned.split(wake, 1)
                cmd = parts[1].strip()
                return True, cmd

        return False, ""
```
