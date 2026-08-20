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
import warnings

# Suppress HuggingFace Hub unauthenticated / symlink warnings on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")
warnings.filterwarnings("ignore", message=".*cache-system uses symlinks.*")

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
    """
    Scans audio input devices on Windows and automatically selects the highest-quality
    physical hardware microphone array, bypassing virtual loopbacks and webcam audio.
    """
    if not HAS_SOUNDDEVICE:
        return None

    try:
        devices = sd.query_devices()
        avoid_keywords = ['iriun', 'stereo mix', 'virtual', 'mapper', 'camo', 'droidcam', 'line in', 'steam']
        preferred_keywords = ['microphone array', 'realtek', 'amd audio', 'intel', 'nvidia broadcast', 'usb audio', 'headset', 'mic']

        # 1. Check Windows default input device first
        try:
            default_in = sd.default.device[0]
            if default_in is not None and default_in >= 0 and default_in < len(devices):
                dev = devices[default_in]
                if dev['max_input_channels'] > 0:
                    name_lower = dev['name'].lower()
                    if not any(avoid in name_lower for avoid in avoid_keywords):
                        print(f"[STT Mic Selection]: Using Windows Default Hardware Microphone '{dev['name']}' (Index {default_in}).")
                        return default_in
        except Exception:
            pass

        # 2. Prioritize dedicated hardware microphone array
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_lower = dev['name'].lower()
                if any(avoid in name_lower for avoid in avoid_keywords):
                    continue
                if any(pref in name_lower for pref in preferred_keywords):
                    print(f"[STT Mic Selection]: Selected hardware microphone '{dev['name']}' (Index {idx}).")
                    return idx

        # 3. Fallback to first non-virtual input device
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
                time.sleep(0.04)

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
    Studio-Grade Voice Pipeline:
    - High-Pass Noise Reduction & Dynamic Software AGC (Automatic Gain Control)
    - Pre-Roll Ring Buffer (Ensures zero truncated onset syllables)
    - Low-Latency Silero VAD Speech Slicing (~250ms trailing silence cut)
    - Domain-Conditioned Whisper STT (Snappy command & application recognition)
    - Single-Turn Immediate Response Dispatching
    - Authentic British JARVIS Voice (Edge-TTS en-GB-RyanNeural)
    """

    DOMAIN_PROMPT = (
        "JARVIS virtual assistant voice commands: "
        "Hey Jarvis, Hi Jarvis, Hello Jarvis, Jarvis, "
        "open Spotify, play music on Spotify, open YouTube and search, "
        "open Chrome, open Brave, open Edge, open Firefox, "
        "open Notepad, open Calculator, open VS Code, open Discord, "
        "open Steam, open File Explorer, open Task Manager, open Settings, "
        "open Control Panel, open Paint, open Word, open Excel, open Teams, "
        "open PowerPoint, open Outlook, open Telegram, open WhatsApp, "
        "turn on living room light, turn off bedroom light, set brightness to 50 percent, "
        "set temperature to 24 degrees, movie night mode, goodnight Jarvis, "
        "lock my PC, take a screenshot, system status, what time is it, "
        "pause music, skip song, volume up, volume down, mute."
    )

    PHONETIC_CORRECTIONS = {
        # Spotify
        "spotty": "spotify",
        "spot if i": "spotify",
        "spotifi": "spotify",
        "spottily": "spotify",
        "sportify": "spotify",
        "spotify app": "spotify",
        # YouTube
        "you tube": "youtube",
        "u tube": "youtube",
        "youtube app": "youtube",
        # Notepad
        "note pad": "notepad",
        "not pad": "notepad",
        "notepad app": "notepad",
        # Calculator
        "calc": "calculator",
        "calculator app": "calculator",
        # Browsers
        "brave browser": "brave",
        "google chrome": "chrome",
        "chrome browser": "chrome",
        "ms edge": "edge",
        "microsoft edge": "edge",
        # VS Code
        "vs code": "vs code",
        "visual studio code": "vs code",
        "vs code app": "vs code",
        "vscode": "vs code",
        # Discord
        "disk cord": "discord",
        "dis cord": "discord",
        "discord app": "discord",
        # Steam
        "steam app": "steam",
        # File Explorer
        "file explore": "file explorer",
        "files explorer": "file explorer",
        "explorer": "file explorer",
        # Task Manager
        "task manage": "task manager",
        # Teams
        "microsoft teams": "teams",
        "team's": "teams",
        # Paint
        "ms paint": "paint",
        # Settings
        "setting": "settings",
        "system settings": "settings",
        # Volume
        "volume up": "volume up",
        "volume down": "volume down",
        "turn up volume": "volume up",
        "turn down volume": "volume down",
    }

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
                self.whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
                print("[STT Engine]: Faster-Whisper 'small' + Silero VAD initialized.")
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

    def normalize_speech_text(self, text: str) -> str:
        """Normalizes common speech phonetic misrecognitions for commands and applications."""
        if not text:
            return ""
        clean = text.strip()
        clean_lower = clean.lower()

        for phonetic, target in self.PHONETIC_CORRECTIONS.items():
            if phonetic in clean_lower:
                clean_lower = clean_lower.replace(phonetic, target)

        return clean_lower

    def filter_wake_word(self, transcript: str) -> Tuple[bool, str]:
        """
        Flexible Wake-Word Gating with Fragment Protection:
        Matches: 'jarvis', 'hey jarvis', 'hi jarvis', 'hello jarvis', 'okay jarvis', 'jarvisst', etc.
        Returns:
            (is_wake: bool, sanitized_command: str)
        """
        if not transcript:
            return False, ""

        clean = self.normalize_speech_text(transcript)

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

    def record_audio_with_vad(self, duration: float = 5.0, sample_rate: int = 16000) -> Optional[sr.AudioData]:
        """
        Studio-grade microphone capture featuring:
        1. Pre-roll Ring Buffer (6 frames / ~192ms) ensuring first syllables are never cut off.
        2. DC Offset Removal & High-Pass Filtering (removes sub-80Hz low rumble/hum).
        3. Dynamic Software AGC (Automatic Gain Control) normalizing speech to ~28,500 16-bit PCM.
        4. Low-Latency Silero VAD Trailing Silence Slicing (~250ms response cutoff).
        """
        if not HAS_SOUNDDEVICE or self.is_mic_muted:
            return None

        block_size = 512  # ~32ms per frame at 16kHz
        max_frames = int((duration * sample_rate) / block_size)
        max_silence_frames = 6   # ~192ms trailing silence cutoff — snappier auto-slice
        pre_roll_limit = 6       # ~192ms pre-speech ring buffer

        try:
            pre_roll_buffer = []
            audio_frames = []
            speech_detected = False
            silent_frames = 0
            hp_prev_in = 0.0
            hp_prev_out = 0.0

            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype='float32',
                blocksize=block_size,
                device=self.input_device_index
            ) as stream:
                for _ in range(max_frames):
                    frame, _ = stream.read(block_size)
                    flat = frame.flatten()

                    # 1. DC Offset Removal
                    flat = flat - np.mean(flat)

                    # 2. Simple High-Pass Filter (removes sub-80Hz electrical/room rumble)
                    filtered = np.empty_like(flat)
                    for i in range(len(flat)):
                        hp_prev_out = 0.94 * (hp_prev_out + flat[i] - hp_prev_in)
                        hp_prev_in = flat[i]
                        filtered[i] = hp_prev_out

                    # Maintain Pre-Roll Ring Buffer
                    if not speech_detected:
                        pre_roll_buffer.append(filtered)
                        if len(pre_roll_buffer) > pre_roll_limit:
                            pre_roll_buffer.pop(0)

                    # 3. Silero VAD Speech Activity Check
                    is_voice_frame = False
                    if self.vad_model:
                        try:
                            prob = float(self.vad_model(filtered)[0])
                            if prob > 0.38:
                                is_voice_frame = True
                        except Exception:
                            # Energy fallback
                            if np.max(np.abs(filtered)) > 0.015:
                                is_voice_frame = True
                    else:
                        if np.max(np.abs(filtered)) > 0.015:
                            is_voice_frame = True

                    if is_voice_frame:
                        if not speech_detected:
                            speech_detected = True
                            # Prepend captured pre-roll buffer to preserve onset consonants!
                            audio_frames.extend(pre_roll_buffer)
                        audio_frames.append(filtered)
                        silent_frames = 0
                    elif speech_detected:
                        audio_frames.append(filtered)
                        silent_frames += 1
                        if silent_frames >= max_silence_frames:
                            # User finished speaking -> Slice immediately!
                            break

            if not audio_frames:
                return None

            raw_audio = np.concatenate(audio_frames)
            max_val = np.max(np.abs(raw_audio))

            # Faint noise gate threshold
            if max_val < 0.003:
                return None

            # 4. Dynamic Software AGC (Automatic Gain Control)
            # Boosts quiet speech to optimal Whisper volume (~28,500 in 16-bit PCM) without distortion
            gain_factor = min(28500.0 / (max_val + 1e-5), 32000.0)
            normalized = (raw_audio * gain_factor).clip(-32767, 32767).astype(np.int16)
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

        audio = self.record_audio_with_vad(duration=5.0)
        if not audio:
            return False, ""

        raw_text = self._transcribe_audio(audio).lower().strip()
        if not raw_text:
            return False, ""

        if raw_text in ["you", "thank you", "thanks", "bye", "subtitles", "thank you for watching"]:
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
        Listens directly for the user's follow-up or manual voice trigger command.
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
        if not raw_text or raw_text.lower() in ["you", "thank you", "thanks", "bye", "subtitles", "thank you for watching"]:
            return ""

        clean_text = self.normalize_speech_text(raw_text)
        if "jarvis" in clean_text:
            _, extracted_cmd = self.filter_wake_word(clean_text)
            return extracted_cmd or clean_text

        return clean_text

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
                    vad_parameters=dict(min_silence_duration_ms=200)
                )
                text = " ".join([s.text for s in segments]).strip()
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

                if text:
                    return self.normalize_speech_text(text)
            except Exception as e:
                print(f"[Whisper STT Notice: {e}]")

        try:
            res = self.recognizer.recognize_google(audio)
            return self.normalize_speech_text(res)
        except Exception:
            return ""

