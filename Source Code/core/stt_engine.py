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

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import asyncio
import tempfile
import re
import time
import threading
import numpy as np
import speech_recognition as sr
from collections import deque
from typing import Optional, Tuple

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

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
    except Exception:
        HAS_FASTER_WHISPER = False
        return False


DOMAIN_PROMPT = (
    "JARVIS AI assistant voice commands: "
    "Hey Jarvis, Hi Jarvis, Hello Jarvis, Okay Jarvis, "
    "open Spotify, open YouTube, open Brave, open Chrome, open Edge, open Firefox, "
    "open Notepad, open Calculator, open Discord, open Steam, open VS Code, "
    "open File Explorer, open Task Manager, open Settings, open Control Panel, "
    "open Paint, open Word, open Excel, open PowerPoint, open Teams, "
    "play music on Spotify, pause Spotify, skip song, "
    "search Google, search YouTube, "
    "turn on living room light, turn off bedroom light, set brightness to 50 percent, "
    "set temperature to 24 degrees, movie night mode, goodnight Jarvis, "
    "lock my PC, take a screenshot, system status, what time is it."
)

WHISPER_HALLUCINATIONS = {
    "you", "thank you", "thanks", "bye", "subtitles",
    "thank you for watching", "thank you.", "thanks.", "bye.",
    ".", "..", "...", "hmm", "hmm.", "um", "uh",
    "okay", "okay.", "ok", "alright", "sure",
    "subtitles by", "captions by", "amara.org",
}


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

        candidates.sort(key=lambda x: x[0], reverse=True)

        existing_indices = {c[1] for c in candidates}
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and idx not in existing_indices:
                candidates.append((0, idx, dev))

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


class STTEngine:
    """
    Studio-Grade Local Speech-to-Text Engine.

    Features:
    - Auto-probing hardware microphone discovery with native rate & channel support
    - Pre-roll Ring Buffer (~192ms) preventing syllable clipping
    - DC Offset Removal + High-Pass Filter (eliminates mic hum / room rumble)
    - Dynamic Software AGC (Automatic Gain Control) for quiet-voice clarity
    - High-Speed Cloud & Studio STT with local Whisper fallback
    """

    def __init__(self, model_size: str = "tiny", wake_words: Optional[list] = None):
        self.wake_words = [w.lower() for w in (wake_words or ["jarvis", "hey jarvis", "hi jarvis", "stark"])]
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 150
        self.recognizer.dynamic_energy_threshold = True

        self.input_device_index, self.device_sample_rate, self.device_channels, self.device_name = discover_working_microphone()
        self.model_size = model_size
        self.whisper_model = None
        self.vad_model = None

        if os.environ.get("ENABLE_LOCAL_WHISPER", "0") == "1" and _try_load_whisper_modules():
            try:
                self.whisper_model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                print(f"[STT Engine]: Faster-Whisper '{self.model_size}' initialized.")
            except Exception as ex:
                print(f"[STT Notice: Using Google STT Engine ({ex})]")
                self.whisper_model = None
        else:
            print("[STT Engine]: High-Speed Cloud & Studio STT Engine initialized (Sub-200ms, zero memory load).")

<<<<<<< HEAD
    def record_mic_audio(self, duration: float = 4.0, target_sr: int = 16000) -> Optional[sr.AudioData]:
=======
    # ------------------------------------------------------------------
    # Model initialisation
    # ------------------------------------------------------------------

    def _init_whisper_model(self):
        """Initialises WhisperModel with CUDA float16 acceleration and CPU int8 fallback."""
        if not HAS_FASTER_WHISPER:
            return None

        # Attempt CUDA GPU offloading
        has_cuda = (
            hasattr(ctranslate2, "get_cuda_device_count")
            and ctranslate2.get_cuda_device_count() > 0
        )
        if has_cuda:
            try:
                print(f"[STT Engine]: Initialising Whisper '{self.model_size}' on CUDA (float16)...")
                model = WhisperModel(self.model_size, device="cuda", compute_type="float16")
                # Warm-up inference to verify cuBLAS loads cleanly
                dummy = np.zeros(8000, dtype=np.float32)
                list(model.transcribe(dummy)[0])
                print("[STT Engine]: [+] GPU acceleration active!")
                return model
            except Exception as err:
                print(f"[STT Engine]: CUDA init failed ({err}) - falling back to CPU int8.")

        # CPU int8 fallback
        try:
            print(f"[STT Engine]: Initialising Whisper '{self.model_size}' on CPU (int8)...")
            model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            print("[STT Engine]: [+] CPU int8 Whisper model ready.")
            return model
        except Exception as ex:
            print(f"[STT Error: Whisper init deferred ({ex}).]")
            return None

    # ------------------------------------------------------------------
    # Audio capture
    # ------------------------------------------------------------------

    def record_mic_audio(self, duration: float = 4.0) -> Optional[sr.AudioData]:
>>>>>>> c1804ac35a4ec2029e52139fcf0e8a37385eb156
        """
        Studio-grade microphone capture with:
          1. Streaming from verified hardware device at its native sample rate and channels.
          2. Fast software mono downmixing and linear interpolation resampling to 16,000 Hz.
          3. Pre-Roll Ring Buffer (~192 ms) to catch onset consonants.
          4. DC Offset Removal & High-Pass Filter (~80 Hz cutoff).
          5. Trailing Silence Cut (~224 ms) after speech.
          6. Dynamic AGC normalising quiet speech to optimal volume.
        """
        dev_idx = self.input_device_index
        native_sr = self.device_sample_rate or 16000
        native_ch = self.device_channels or 1

        target_block_size = 512  # ~32ms at 16kHz
        native_block_size = int(target_block_size * (native_sr / target_sr))
        max_frames = int((duration * target_sr) / target_block_size)
        max_silence_frames = 7   # ~224ms trailing silence cutoff
        pre_roll_limit = 6       # ~192ms pre-speech ring buffer

        if HAS_SOUNDDEVICE and dev_idx is not None:
            try:
                captured_blocks = []
                lock = threading.Lock()

                def _stream_callback(indata, frames, time_info, status):
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

                        # 2. High-Pass Filter (alpha ≈ 0.94 -> ~80 Hz cutoff at 16 kHz)
                        filtered = np.empty_like(flat)
                        for i in range(len(flat)):
                            hp_prev_out = 0.94 * (hp_prev_out + flat[i] - hp_prev_in)
                            hp_prev_in = flat[i]
                            filtered[i] = hp_prev_out

                        # Always maintain pre-roll ring buffer
                        if not speech_detected:
                            pre_roll_buffer.append(filtered)
                            if len(pre_roll_buffer) > pre_roll_limit:
                                pre_roll_buffer.pop(0)

                        # 3. Speech Activity Check
                        is_voice = False
                        if self.vad_model:
                            try:
                                prob = float(self.vad_model(filtered)[0])
                                is_voice = prob > 0.35
                            except Exception:
                                is_voice = np.max(np.abs(filtered)) > 0.012
                        else:
                            is_voice = np.max(np.abs(filtered)) > 0.012

                        if is_voice:
                            if not speech_detected:
                                speech_detected = True
                                processed_frames.extend(pre_roll_buffer)
                            processed_frames.append(filtered)
                            silent_frames = 0
                        elif speech_detected:
                            processed_frames.append(filtered)
                            silent_frames += 1
                            if silent_frames >= max_silence_frames:
                                break

                if not processed_frames:
                    return None

                raw_audio = np.concatenate(processed_frames)
                max_val = float(np.max(np.abs(raw_audio)))

                if max_val < 0.002:
                    return None

                # 4. Dynamic AGC
                gain = min(28500.0 / (max_val + 1e-5), 32000.0)
                normalized = (raw_audio * gain).clip(-32767, 32767).astype(np.int16)
                return sr.AudioData(normalized.tobytes(), target_sr, 2)

            except Exception as e:
                print(f"[STT SoundDevice Error: {e}]")

        # Fallback - SpeechRecognition built-in microphone
        try:
            with sr.Microphone(sample_rate=target_sr) as source:
                return self.recognizer.listen(source, timeout=2.0, phrase_time_limit=duration)
        except Exception:
            pass

        return None

    async def listen_raw_audio(self, timeout: float = 2.0, phrase_time_limit: float = 4.0) -> Optional[sr.AudioData]:
        """Asynchronously records raw audio from the hardware microphone."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.record_mic_audio, phrase_time_limit)

    def transcribe_audio(self, audio: sr.AudioData) -> str:
        """Transcribes recorded AudioData using domain-prompt-conditioned STT."""
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
                    beam_size=2,
                    language="en",
                    initial_prompt=DOMAIN_PROMPT,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=200),
                )
                text = " ".join([seg.text for seg in segments]).strip()

                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

                return text

            except Exception as e:
                self.whisper_model = None
                print(f"[Whisper STT Notice (Switched to Google STT): {e}]")

        # Google STT fallback
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""
        except Exception:
            return ""

    async def listen_command(self, timeout: float = 3.0, phrase_time_limit: float = 5.0) -> str:
        """Capture and transcribe a single user command."""
        audio = await self.listen_raw_audio(timeout=timeout, phrase_time_limit=phrase_time_limit)
        if audio:
            return self.transcribe_audio(audio)
        return ""

    async def detect_wake_word(self, timeout: float = 2.0) -> bool:
        """Listens for wake word only; returns True when detected."""
        _, text = await self.detect_wake_word_or_command(timeout=timeout)
        return bool(text) or False

    async def detect_wake_word_or_command(self, timeout: float = 2.0) -> Tuple[bool, str]:
        """
        Captures microphone audio, transcribes it, filters hallucinations,
        and returns (wake_detected, command_text).
        """
        audio = await self.listen_raw_audio(timeout=timeout, phrase_time_limit=4.0)
        if not audio:
            return False, ""

        transcription = self.transcribe_audio(audio).strip()
        if not transcription or len(transcription) < 2:
            return False, ""

        trans_lower = transcription.lower().strip(".,!? ")

        # Filter common Whisper hallucination artifacts
        if trans_lower in WHISPER_HALLUCINATIONS:
            return False, ""

        # Wake word detected
        if any(w in trans_lower for w in self.wake_words):
            clean_cmd = re.sub(
                r'^(?:hey\s+|hi\s+|hello\s+|okay\s+|ok\s+)?jarvis\s*,?\s*',
                '', trans_lower, flags=re.IGNORECASE
            ).strip()
            return True, clean_cmd

        return False, ""

