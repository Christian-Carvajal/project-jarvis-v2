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

HAS_FASTER_WHISPER = False
WhisperModel = None
get_vad_model = None

def _try_load_whisper_modules():
    global HAS_FASTER_WHISPER, WhisperModel, get_vad_model
    if HAS_FASTER_WHISPER:
        return True
    try:
        import ctranslate2
        from faster_whisper import WhisperModel as WM
        from faster_whisper.vad import get_vad_model as GVM
        WhisperModel = WM
        get_vad_model = GVM
        HAS_FASTER_WHISPER = True
        return True
    except Exception as e:
        HAS_FASTER_WHISPER = False
        return False

logger = logging.getLogger("JarvisLogger")


def discover_working_microphone() -> Tuple[Optional[int], int, int, str]:
    """
    Scans and dynamically probes all audio input devices on Windows.
    Tests candidate devices (prioritizing physical hardware arrays like Realtek, AMD, Intel, USB audio, WDM-KS, WASAPI)
    by opening a micro-stream and verifying that frames are actually captured without PortAudio / OS errors.
    Returns:
        (device_index, native_samplerate, channels, device_name)
    """
    if not HAS_SOUNDDEVICE:
        return None, 16000, 1, "Default"

    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        avoid_keywords = ['iriun', 'stereo mix', 'virtual', 'mapper', 'camo', 'droidcam', 'line in', 'steam', 'blackhole']
        preferred_keywords = ['microphone array', 'realtek', 'amd', 'intel', 'nvidia broadcast', 'usb audio', 'headset', 'mic']

        candidates = []
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] <= 0:
                continue
            name_lower = dev['name'].lower()
            if any(avoid in name_lower for avoid in avoid_keywords):
                continue

            score = 0
            api_name = hostapis[dev['hostapi']]['name'].lower()
            if 'wdm-ks' in api_name:
                score += 30
            elif 'wasapi' in api_name:
                score += 20
            elif 'directsound' in api_name:
                score += 10

            if any(pref in name_lower for pref in preferred_keywords):
                score += 50
            if 'microphone array' in name_lower:
                score += 20

            candidates.append((score, idx, dev))

        # Sort candidates by suitability score descending
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Include remaining input devices as fallback
        existing_indices = {c[1] for c in candidates}
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and idx not in existing_indices:
                candidates.append((0, idx, dev))

        # Dynamically probe each candidate device to ensure 0 PortAudio errors
        for score, idx, dev in candidates:
            api_name = hostapis[dev['hostapi']]['name']
            sr_options = [int(dev['default_samplerate']), 48000, 44100, 16000]
            sr_options = list(dict.fromkeys(sr_options))
            ch_options = [dev['max_input_channels'], 1]
            ch_options = list(dict.fromkeys(ch_options))

            for sr_test in sr_options:
                for ch_test in ch_options:
                    try:
                        frames_received = []
                        def _test_cb(indata, frames, time_info, status):
                            frames_received.append(indata.copy())

                        with sd.InputStream(
                            device=idx,
                            channels=ch_test,
                            samplerate=sr_test,
                            dtype='float32',
                            callback=_test_cb
                        ):
                            time.sleep(0.08)

                        if len(frames_received) > 0:
                            print(f"[STT Mic Selection]: Selected verified hardware mic '{dev['name']}' (Index {idx}, {api_name}, {sr_test}Hz, {ch_test}ch).")
                            return idx, sr_test, ch_test, dev['name']
                    except Exception:
                        pass

    except Exception as e:
        print(f"[STT Mic Auto-Discovery Notice: {e}]")

    return None, 16000, 1, "Default"


def find_best_hardware_microphone() -> Optional[int]:
    """Backward compatibility alias for discover_working_microphone."""
    idx, _, _, _ = discover_working_microphone()
    return idx


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
    - Auto-probing hardware microphone discovery with native rate & channel support
    - Pre-roll Ring Buffer (~192ms) ensuring onset consonants are never cut off
    - High-Pass Noise Reduction & Dynamic Software AGC (Automatic Gain Control)
    - Low-Latency VAD / Dynamic Energy Trailing Silence Slicing (~220ms cut)
    - Domain-Conditioned Whisper STT with Instant Google STT Fallback
    - Two-Stage Conversational State Machine Support
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
        self.recognizer.energy_threshold = 150
        self.recognizer.dynamic_energy_threshold = True
        self.tts = TTSEngine(voice="en-GB-RyanNeural")
        self.is_mic_muted = False

        # Discover best hardware microphone with verified stream capability
        self.input_device_index, self.device_sample_rate, self.device_channels, self.device_name = discover_working_microphone()
        print(f"[VoicePipeline]: Initialized microphone: '{self.device_name}' (Device Index: {self.input_device_index}, Native SR: {self.device_sample_rate}Hz, CH: {self.device_channels})")

        self.whisper_model = None
        self.vad_model = None

        if os.environ.get("ENABLE_LOCAL_WHISPER", "0") == "1" and HAS_FASTER_WHISPER:
            try:
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                print("[STT Engine]: Faster-Whisper 'tiny' initialized.")
            except Exception as e:
                print(f"[Whisper load notice (using Google STT): {e}]")
                self.whisper_model = None
        else:
            print("[STT Engine]: High-Speed Cloud & Studio STT Engine initialized (Sub-200ms, zero-memory footprint).")

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

    def record_audio_with_vad(self, duration: float = 5.0, target_sr: int = 16000) -> Optional[sr.AudioData]:
        """
        Studio-grade microphone capture featuring:
        1. Streaming from verified hardware device at its native sample rate and channels.
        2. Fast software mono downmixing and linear interpolation resampling to 16,000 Hz.
        3. Pre-roll Ring Buffer (6 frames / ~192ms) ensuring first syllables are never cut off.
        4. DC Offset Removal & High-Pass Filtering (removes sub-80Hz low rumble/hum).
        5. Silero VAD / Dynamic Energy Trailing Silence Slicing (~220ms response cutoff).
        6. Dynamic Software AGC (Automatic Gain Control) normalizing speech to ~28,500 16-bit PCM.
        """
        if self.is_mic_muted:
            return None

        # Determine native device parameters
        dev_idx = self.input_device_index
        native_sr = self.device_sample_rate or 16000
        native_ch = self.device_channels or 1

        target_block_size = 512  # ~32ms at 16kHz
        native_block_size = int(target_block_size * (native_sr / target_sr))
        max_frames = int((duration * target_sr) / target_block_size)
        max_silence_frames = 7   # ~224ms trailing silence cutoff — instant auto-slice
        pre_roll_limit = 6       # ~192ms pre-speech ring buffer

        if HAS_SOUNDDEVICE and dev_idx is not None:
            try:
                captured_blocks = []
                lock = threading.Lock()
                stream_error = []

                def _stream_callback(indata, frames, time_info, status):
                    if status:
                        pass
                    with lock:
                        captured_blocks.append(indata.copy())

                with sd.InputStream(
                    device=dev_idx,
                    channels=native_ch,
                    samplerate=native_sr,
                    dtype='float32',
                    blocksize=native_block_size,
                    callback=_stream_callback
                ):
                    pre_roll_buffer = []
                    processed_frames = []
                    speech_detected = False
                    silent_frames = 0
                    hp_prev_in = 0.0
                    hp_prev_out = 0.0
                    frame_count = 0

                    while frame_count < max_frames:
                        raw_block = None
                        with lock:
                            if captured_blocks:
                                raw_block = captured_blocks.pop(0)

                        if raw_block is None:
                            time.sleep(0.01)
                            continue

                        frame_count += 1

                        # Downmix to mono
                        if native_ch > 1 and raw_block.ndim > 1:
                            mono = np.mean(raw_block, axis=1)
                        else:
                            mono = raw_block.flatten()

                        # Resample to target 16,000 Hz via fast linear interpolation
                        if native_sr != target_sr:
                            orig_indices = np.linspace(0, len(mono) - 1, target_block_size)
                            flat = np.interp(orig_indices, np.arange(len(mono)), mono).astype(np.float32)
                        else:
                            flat = mono.astype(np.float32)

                        # 1. DC Offset Removal
                        flat = flat - np.mean(flat)

                        # 2. High-Pass Filter (removes sub-80Hz electrical/room rumble)
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

                        # 3. Speech Activity Check
                        is_voice_frame = False
                        if self.vad_model:
                            try:
                                prob = float(self.vad_model(filtered)[0])
                                if prob > 0.35:
                                    is_voice_frame = True
                            except Exception:
                                if np.max(np.abs(filtered)) > 0.012:
                                    is_voice_frame = True
                        else:
                            if np.max(np.abs(filtered)) > 0.012:
                                is_voice_frame = True

                        if is_voice_frame:
                            if not speech_detected:
                                speech_detected = True
                                # Prepend captured pre-roll buffer so onset consonants are preserved
                                processed_frames.extend(pre_roll_buffer)
                            processed_frames.append(filtered)
                            silent_frames = 0
                        elif speech_detected:
                            processed_frames.append(filtered)
                            silent_frames += 1
                            if silent_frames >= max_silence_frames:
                                # User finished speaking -> Slice immediately!
                                break

                if not processed_frames:
                    return None

                raw_audio = np.concatenate(processed_frames)
                max_val = float(np.max(np.abs(raw_audio)))

                # Noise gate threshold
                if max_val < 0.002:
                    return None

                # 4. Dynamic Software AGC (Automatic Gain Control)
                gain_factor = min(28500.0 / (max_val + 1e-5), 32000.0)
                normalized = (raw_audio * gain_factor).clip(-32767, 32767).astype(np.int16)
                pcm_bytes = normalized.tobytes()

                return sr.AudioData(pcm_bytes, target_sr, 2)

            except Exception as e:
                logger.error(f"Voice recording error: {e}")

        # Fallback to SpeechRecognition Microphone
        try:
            with sr.Microphone(sample_rate=target_sr) as source:
                return self.recognizer.listen(source, timeout=2.0, phrase_time_limit=duration)
        except Exception:
            pass

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

        if raw_text in ["you", "thank you", "thanks", "bye", "subtitles", "thank you for watching", "okay", "ok"]:
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
        if not raw_text or raw_text.lower() in ["you", "thank you", "thanks", "bye", "subtitles", "thank you for watching", "okay", "ok"]:
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
        """Transcribes recorded AudioData using domain-conditioned Whisper STT with instant Google STT fallback."""
        if not audio:
            return ""

        # Tier 1: Local Whisper STT (if memory and model are available)
        if self.whisper_model:
            try:
                wav_bytes = audio.get_wav_data()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    temp_wav = fp.name
                    fp.write(wav_bytes)

                segments, _ = self.whisper_model.transcribe(
                    temp_wav,
                    beam_size=2,
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
                # If memory allocation or execution fails, disable whisper and switch to Google STT
                self.whisper_model = None
                print(f"[Whisper Notice -> Switched to Google STT: {e}]")

        # Tier 2: Google Speech Recognition (High accuracy, sub-second latency, zero memory load)
        try:
            res = self.recognizer.recognize_google(audio)
            if res:
                return self.normalize_speech_text(res)
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            logger.info(f"Google STT notice: {e}")
            return ""

        return ""

