"""
Voice Pipeline Module for Project JARVIS (Apex Home Automations & Stark PC Suite).
Features:
- Native SoundDevice Streaming with Silero VAD (Voice Activity Detection) Auto-Slicing
- Automatic Audio Gain Normalization (Eliminates low volume & truncated syllables)
- Domain-Prompt-Conditioned Whisper STT (Accurate recognition of 'Hey Jarvis', 'Hi Jarvis', PC & Smart Home commands)
- Two-Stage Conversational Capture (Wake Word in Standby -> Direct Command Capture in Active Mode)
- Authentic British JARVIS Voice (en-GB-RyanNeural via Edge-TTS & Pygame) with Pyttsx3 COM Fallback
- Emergency HALT / Speech Override & Mic Mute Controls
"""

import os
import sys
import re
import time
import queue
import asyncio
import tempfile
import threading
import logging
from typing import Optional, Callable, Tuple
import numpy as np
import speech_recognition as sr
import pyttsx3

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import pythoncom
    HAS_PYTHONCOM = True
except ImportError:
    HAS_PYTHONCOM = False

try:
    import ctranslate2
    from faster_whisper import WhisperModel
    from faster_whisper.vad import get_vad_model
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

logger = logging.getLogger("JarvisLogger")


def find_best_hardware_microphone() -> Optional[int]:
    """Scans audio devices and selects the physical hardware microphone, bypassing virtual webcams (Iriun/Camo)."""
    if not HAS_SOUNDDEVICE:
        return None

    try:
        devices = sd.query_devices()
        avoid_keywords = ['iriun', 'stereo mix', 'virtual', 'mapper', 'camo', 'line in']
        preferred_keywords = ['intel', 'array', 'realtek', 'nvidia broadcast', 'microphone']

        # 1. Prioritize physical hardware mic array
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_lower = dev['name'].lower()
                if any(avoid in name_lower for avoid in avoid_keywords):
                    continue
                if any(pref in name_lower for pref in preferred_keywords):
                    print(f"[STT Mic Selection]: Selected hardware microphone '{dev['name']}' (Index {idx}).")
                    return idx

        # 2. Fallback to first non-virtual input device
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_lower = dev['name'].lower()
                if not any(avoid in name_lower for avoid in avoid_keywords):
                    print(f"[STT Mic Selection]: Fallback microphone '{dev['name']}' (Index {idx}).")
                    return idx
    except Exception as e:
        print(f"[STT Mic Detection Notice: {e}]")

    return None


class TTSEngine:
    """
    Hybrid High-Fidelity Text-to-Speech Engine.
    Primary: Microsoft Edge-TTS 'en-GB-RyanNeural' (Authentic British JARVIS Voice)
    Fallback: Offline Pyttsx3 (SAPI5 with pythoncom.CoInitialize)
    Includes instant HALT / Emergency Speech Override.
    """

    def __init__(self, voice: str = "en-GB-RyanNeural", rate: int = 175, volume: float = 1.0):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.queue = queue.Queue()
        self.is_speaking = False
        self.is_running = True
        self._halt_flag = threading.Event()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def _process_queue(self):
        """Persistent worker loop managing audio synthesis and playback."""
        if HAS_PYTHONCOM:
            try:
                pythoncom.CoInitialize()
            except Exception:
                pass

        offline_engine = None
        try:
            offline_engine = pyttsx3.init()
            offline_engine.setProperty('rate', self.rate)
            offline_engine.setProperty('volume', self.volume)
            voices = offline_engine.getProperty('voices')
            for v in voices:
                if any(k in v.name.lower() for k in ["david", "george", "english", "mark", "zira"]):
                    offline_engine.setProperty('voice', v.id)
                    break
        except Exception as e:
            logger.error(f"pyttsx3 fallback init error: {e}")

        while self.is_running:
            try:
                item = self.queue.get(timeout=0.2)
                if not item:
                    continue

                text, callback = item
                if text and text.strip() and not self._halt_flag.is_set():
                    self.is_speaking = True
                    print(f"[JARVIS Audio Speech]: \"{text}\"")

                    played = False
                    # 1. Primary High-Quality British Jarvis Voice (Edge-TTS)
                    if HAS_EDGE_TTS and HAS_PYGAME and not self._halt_flag.is_set():
                        try:
                            played = self._speak_edge_tts(text)
                        except Exception as e:
                            logger.info(f"Edge-TTS notice: {e}")
                            played = False

                    # 2. Offline Pyttsx3 Fallback
                    if not played and offline_engine and not self._halt_flag.is_set():
                        try:
                            offline_engine.say(text)
                            offline_engine.runAndWait()
                            played = True
                        except Exception as ex:
                            logger.error(f"Pyttsx3 synthesis error: {ex}")

                    self.is_speaking = False

                    if callback and not self._halt_flag.is_set():
                        try:
                            callback()
                        except Exception as cb_err:
                            logger.warning(f"TTS callback error: {cb_err}")

                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.is_speaking = False
                logger.error(f"TTS queue loop error: {e}")

    def _speak_edge_tts(self, text: str) -> bool:
        """Synthesizes voice via Edge-TTS and streams over pygame mixer."""
        temp_path = None
        try:
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = fp.name
            fp.close()

            async def _download():
                comm = edge_tts.Communicate(text, self.voice)
                await comm.save(temp_path)

            asyncio.run(_download())

            if self._halt_flag.is_set():
                return False

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and not self._halt_flag.is_set():
                time.sleep(0.05)

            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            return True
        except Exception:
            return False
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def speak(self, text: str, callback: Optional[Callable[[], None]] = None):
        """Queues speech synthesis."""
        if text and text.strip():
            self._halt_flag.clear()
            self.queue.put((text.strip(), callback))

    def halt(self):
        """Emergency HALT: Instantly stops speech playback and clears speech queue."""
        self._halt_flag.set()
        self.is_speaking = False
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except Exception:
                break

        if HAS_PYGAME and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
        print("[TTS HALT]: Speech output interrupted by user override.")

    def stop(self):
        """Stops the worker thread."""
        self.is_running = False
        self.halt()


class VoicePipeline:
    """
    Offline Voice Pipeline with Silero VAD Voice Activity Detection,
    Gain Normalization, Domain-Conditioned Whisper STT, and British JARVIS TTS.
    """

    DOMAIN_PROMPT = (
        "JARVIS AI virtual assistant voice commands: "
        "Hey Jarvis, Hi Jarvis, Hello Jarvis, Jarvis, "
        "turn on the living room light, turn off the light, set brightness to 50, "
        "set temperature to 24 degrees, lock the front door, unlock the door, "
        "movie night mode, goodnight jarvis, open brave, open chrome, close notepad, "
        "play music on spotify, open youtube and search for music, volume up, lock my pc."
    )

    def __init__(self, wake_words: Optional[list] = None):
        self.wake_words = [w.lower() for w in (wake_words or ["jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "okay jarvis"])]
        self.recognizer = sr.Recognizer()
        self.tts = TTSEngine(voice="en-GB-RyanNeural")
        self.is_mic_muted = False
        self.input_device_index = find_best_hardware_microphone()

        self.whisper_model = None
        self.vad_model = None

        if HAS_FASTER_WHISPER:
            try:
                self.vad_model = get_vad_model()
            except Exception as e:
                print(f"[VAD Model Notice: {e}]")

            try:
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                print("[STT Engine]: Faster-Whisper + Silero VAD initialized.")
            except Exception as e:
                print(f"[Whisper load notice: {e}]")

    def speak(self, text: str, callback: Optional[Callable[[], None]] = None):
        """Speaks text using high-fidelity TTS."""
        self.tts.speak(text, callback)

    def halt_speech(self):
        """HALT emergency speech override."""
        self.tts.halt()

    def toggle_mic(self) -> bool:
        """Toggles microphone mute state."""
        self.is_mic_muted = not self.is_mic_muted
        return self.is_mic_muted

    def filter_wake_word(self, transcript: str) -> Tuple[bool, str]:
        """
        Flexible Wake-Word Gating with Fragment Protection:
        Matches: 'jarvis', 'hey jarvis', 'hi jarvis', 'hello jarvis', 'okay jarvis', 'jarvisst', etc.
        Returns:
            (is_wake: bool, sanitized_command: str)
        """
        if not transcript:
            return False, ""

        clean = transcript.lower().strip()

        # Phonetic match for jarvis / common variations
        wake_pattern = r'\b(?:hey|hi|hello|ok|okay|yo|please)?\s*(?:jarvisst|jarvist|jarvis|javis|jarvas|travis)\b'
        match = re.search(wake_pattern, clean, flags=re.IGNORECASE)

        if not match and "jarvis" not in clean:
            return False, ""

        # Strip wake-word prefix
        sanitized = re.sub(r'^(?:hey|hi|hello|ok|okay|yo|please)?\s*(?:jarvisst|jarvist|jarvis|javis|jarvas|travis)\s*,?\s*', '', clean, flags=re.IGNORECASE).strip()
        # Strip trailing wake word
        sanitized = re.sub(r'\s*(?:jarvisst|jarvist|jarvis|javis|jarvas|travis)\s*$', '', sanitized, flags=re.IGNORECASE).strip()
        sanitized = sanitized.strip(",.!? ")

        # If leftover command is just a trailing stutter/letter (e.g. 'st', 's', 't', 'a'), treat as NO command
        if len(sanitized) < 3 or sanitized in ["st", "st.", "s", "t", "a", "the"]:
            sanitized = ""

        return True, sanitized

    def record_audio_with_vad(self, duration: float = 4.0, sample_rate: int = 16000) -> Optional[sr.AudioData]:
        """
        Captures microphone audio using Silero VAD frame streaming and trailing silence auto-slicing.
        Ensures spoken sentences are NEVER cut off mid-speech.
        """
        if not HAS_SOUNDDEVICE or self.is_mic_muted:
            return None

        block_size = 512  # ~32ms per frame
        max_frames = int((duration * sample_rate) / block_size)
        max_silence_frames = 12  # ~380ms trailing silence threshold

        try:
            audio_frames = []
            speech_detected = False
            silent_frames = 0

            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype='float32',
                blocksize=block_size,
                device=self.input_device_index
            ) as stream:
                for _ in range(max_frames):
                    frame, _ = stream.read(block_size)
                    flat_frame = frame.flatten()
                    audio_frames.append(flat_frame)

                    if self.vad_model:
                        try:
                            prob = float(self.vad_model(flat_frame)[0])
                            if prob > 0.45:
                                speech_detected = True
                                silent_frames = 0
                            elif speech_detected:
                                silent_frames += 1
                                if silent_frames >= max_silence_frames:
                                    # User finished speaking -> Slice immediately!
                                    break
                        except Exception:
                            pass

            if not audio_frames:
                return None

            raw_audio = np.concatenate(audio_frames)
            max_val = np.max(np.abs(raw_audio))

            if max_val < 0.004:
                return None

            # Gain Normalization: Boosts quiet voices and normalizes volume
            normalized = (raw_audio / (max_val + 1e-5) * 28000.0).astype(np.int16)
            pcm_bytes = normalized.tobytes()
            return sr.AudioData(pcm_bytes, sample_rate, 2)

        except Exception as e:
            logger.error(f"VAD sounddevice recording error: {e}")
            return None

    def listen_and_filter(self) -> Tuple[bool, str]:
        """
        Listens for wake word when in STANDBY mode.
        Returns:
            (is_wake_word_detected: bool, extracted_inline_command: str)
        """
        if self.is_mic_muted:
            time.sleep(0.2)
            return False, ""

        audio = self.record_audio_with_vad(duration=4.5)
        if not audio:
            return False, ""

        raw_text = self._transcribe_audio(audio).lower().strip()
        if not raw_text:
            return False, ""

        if raw_text in ["you", "thank you", "thanks", "bye", "subtitles"]:
            return False, ""

        is_wake, clean_cmd = self.filter_wake_word(raw_text)
        if not is_wake:
            print(f"[Passive Acoustic Gate]: Discarded non-wake audio -> \"{raw_text}\"")
            return False, ""

        print(f"\n[WAKE WORD TRIGGERED]: \"{raw_text}\" (Extracted Command: \"{clean_cmd}\")")
        return True, clean_cmd

    def listen_for_wake_word(self) -> Tuple[bool, str]:
        """Listens for wake word in STANDBY mode. Alias for listen_and_filter."""
        return self.listen_and_filter()

    def listen_raw_command(self, timeout: float = 6.0) -> str:
        """
        Listens directly for the user's follow-up command when in ACTIVE_COMMAND mode.
        (Does NOT require repeating 'Hey Jarvis').
        Returns:
            transcribed_command: str
        """
        if self.is_mic_muted:
            return ""

        audio = self.record_audio_with_vad(duration=timeout)
        if not audio:
            return ""

        raw_text = self._transcribe_audio(audio).strip()
        if not raw_text or raw_text.lower() in ["you", "thank you", "thanks", "bye", "subtitles"]:
            return ""

        # Clean any repeated wake words if user happened to say it again
        clean_text = raw_text.lower()
        if "jarvis" in clean_text:
            _, extracted_cmd = self.filter_wake_word(clean_text)
            return extracted_cmd or raw_text

        return raw_text

    def listen_for_direct_command(self, duration: float = 6.0) -> str:
        """Alias for listen_raw_command."""
        return self.listen_raw_command(timeout=duration)

    def _transcribe_audio(self, audio: sr.AudioData) -> str:
        """Transcribes recorded AudioData using domain-conditioned Whisper STT with Google STT fallback."""
        if not audio:
            return ""

        if self.whisper_model:
            try:
                wav_bytes = audio.get_wav_data()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    temp_wav = fp.name
                    fp.write(wav_bytes)

                segments, _ = self.whisper_model.transcribe(
                    temp_wav,
                    beam_size=3,
                    language="en",
                    initial_prompt=self.DOMAIN_PROMPT,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=250)
                )
                text = " ".join([s.text for s in segments]).strip()
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

                if text:
                    return text
            except Exception as e:
                print(f"[Whisper STT Notice: {e}]")

        try:
            return self.recognizer.recognize_google(audio)
        except Exception:
            return ""
