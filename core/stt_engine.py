import asyncio
import tempfile
import os
import re
import numpy as np
import speech_recognition as sr
from collections import deque
from typing import Optional, Tuple

try:
    import ctranslate2
    from faster_whisper import WhisperModel
    from faster_whisper.vad import get_vad_model
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


# ---------------------------------------------------------------------------
# Whisper domain prompt — conditions the model to accurately decode PC
# automation commands, app names, and smart home vocabulary.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Whisper hallucination artifacts — common false-positive outputs to discard.
# ---------------------------------------------------------------------------
WHISPER_HALLUCINATIONS = {
    "you", "thank you", "thanks", "bye", "subtitles",
    "thank you for watching", "thank you.", "thanks.", "bye.",
    ".", "..", "...", "hmm", "hmm.", "um", "uh",
    "okay", "okay.", "ok", "alright", "sure",
    "subtitles by", "captions by", "amara.org",
}


def find_best_hardware_microphone() -> Optional[int]:
    """
    Scans Windows audio input devices and selects the highest-quality
    physical hardware microphone, bypassing virtual loopbacks and webcam audio.
    Priority: Windows default device → named hardware array → first valid device.
    """
    if not HAS_SOUNDDEVICE:
        return None

    try:
        devices = sd.query_devices()
        avoid_keywords = [
            'iriun', 'stereo mix', 'virtual', 'mapper', 'camo',
            'droidcam', 'line in', 'steam', 'soundflower', 'blackhole'
        ]
        preferred_keywords = [
            'microphone array', 'realtek', 'amd audio', 'intel',
            'nvidia broadcast', 'usb audio', 'headset', 'mic', 'audio input'
        ]

        # 1. Prefer the Windows-default input device if it is a real mic
        try:
            default_in = sd.default.device[0]
            if default_in is not None and 0 <= default_in < len(devices):
                dev = devices[default_in]
                if dev['max_input_channels'] > 0:
                    name_lower = dev['name'].lower()
                    if not any(avoid in name_lower for avoid in avoid_keywords):
                        print(f"[STT Mic]: Using Windows default mic '{dev['name']}' (Index {default_in}).")
                        return default_in
        except Exception:
            pass

        # 2. Prefer named hardware arrays
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_lower = dev['name'].lower()
                if any(avoid in name_lower for avoid in avoid_keywords):
                    continue
                if any(pref in name_lower for pref in preferred_keywords):
                    print(f"[STT Mic]: Selected hardware mic '{dev['name']}' (Index {idx}).")
                    return idx

        # 3. First valid non-virtual input device
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_lower = dev['name'].lower()
                if not any(avoid in name_lower for avoid in avoid_keywords):
                    print(f"[STT Mic]: Fallback mic '{dev['name']}' (Index {idx}).")
                    return idx

    except Exception as e:
        print(f"[STT Mic Notice: {e}]")

    return None


class STTEngine:
    """
    Studio-Grade Local Speech-to-Text Engine.

    Features:
    - Faster-Whisper 'small' model for high-accuracy command transcription
    - CUDA float16 acceleration with CPU int8 fallback
    - Silero VAD auto-slicing with tight trailing silence (~224 ms)
    - Pre-Roll Ring Buffer (5 frames / ~160 ms) — no clipped onset consonants
    - DC Offset Removal + High-Pass Filter (eliminates mic hum / room rumble)
    - Dynamic Software AGC (Automatic Gain Control) for quiet-voice clarity
    - Multi-phrase hallucination filter to block Whisper artifacts
    """

    def __init__(self, model_size: str = "small", wake_words: Optional[list] = None):
        self.wake_words = [w.lower() for w in (wake_words or ["jarvis", "hey jarvis", "stark"])]
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 100
        self.recognizer.dynamic_energy_threshold = True

        self.input_device_index = find_best_hardware_microphone()
        self.model_size = model_size

        self.whisper_model = self._init_whisper_model()
        self.vad_model = None

        if HAS_FASTER_WHISPER:
            try:
                self.vad_model = get_vad_model()
                print("[STT Engine]: Silero VAD loaded.")
            except Exception as e:
                print(f"[STT Warning: Silero VAD load notice ({e})]")

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
                print("[STT Engine]: ✅ GPU acceleration active!")
                return model
            except Exception as err:
                print(f"[STT Engine]: CUDA init failed ({err}) — falling back to CPU int8.")

        # CPU int8 fallback
        try:
            print(f"[STT Engine]: Initialising Whisper '{self.model_size}' on CPU (int8)...")
            model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            print("[STT Engine]: ✅ CPU int8 Whisper model ready.")
            return model
        except Exception as ex:
            print(f"[STT Error: Whisper init deferred ({ex}).]")
            return None

    # ------------------------------------------------------------------
    # Audio capture
    # ------------------------------------------------------------------

    def record_mic_audio(self, duration: float = 4.0) -> Optional[sr.AudioData]:
        """
        Studio-grade microphone capture with:
          1. Pre-Roll Ring Buffer  — 5 frames (~160 ms) to catch onset consonants
          2. DC Offset Removal     — eliminates low-frequency electrical bias
          3. High-Pass Filter      — removes sub-80 Hz room rumble / hum
          4. Silero VAD            — frame-level speech probability gating (0.50 threshold)
          5. Trailing Silence Cut  — 7 frames (~224 ms) after last voice frame
          6. Dynamic AGC           — normalises quiet speech to optimal Whisper levels
        """
        sample_rate = 16000
        block_size = 512          # ~32 ms per frame at 16 kHz
        max_frames = int((duration * sample_rate) / block_size)
        max_silence_frames = 7    # ~224 ms trailing silence before auto-slice
        pre_roll_limit = 5        # ~160 ms pre-speech ring buffer

        if HAS_SOUNDDEVICE:
            try:
                pre_roll: deque = deque(maxlen=pre_roll_limit)
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

                        # 2. High-Pass Filter (alpha ≈ 0.94 → ~80 Hz cutoff at 16 kHz)
                        filtered = np.empty_like(flat)
                        for i in range(len(flat)):
                            hp_prev_out = 0.94 * (hp_prev_out + flat[i] - hp_prev_in)
                            hp_prev_in = flat[i]
                            filtered[i] = hp_prev_out

                        # Always maintain pre-roll ring buffer
                        pre_roll.append(filtered.copy())

                        # 3. Silero VAD speech detection
                        is_voice = False
                        if self.vad_model:
                            try:
                                prob = float(self.vad_model(filtered)[0])
                                is_voice = prob > 0.50   # tighter threshold vs. 0.40
                            except Exception:
                                is_voice = np.max(np.abs(filtered)) > 0.015
                        else:
                            is_voice = np.max(np.abs(filtered)) > 0.015

                        if is_voice:
                            if not speech_detected:
                                speech_detected = True
                                # Prepend ring buffer so onset syllables are preserved
                                audio_frames.extend(list(pre_roll))
                            audio_frames.append(filtered)
                            silent_frames = 0
                        elif speech_detected:
                            audio_frames.append(filtered)
                            silent_frames += 1
                            if silent_frames >= max_silence_frames:
                                break   # Auto-slice immediately after trailing silence

                if not audio_frames:
                    return None

                raw_audio = np.concatenate(audio_frames)
                max_val = np.max(np.abs(raw_audio))

                if max_val < 0.003:   # Noise gate — discard near-silent captures
                    return None

                # 4. Dynamic AGC — boost quiet speech without clipping
                gain = min(28500.0 / (max_val + 1e-5), 32000.0)
                normalized = (raw_audio * gain).clip(-32767, 32767).astype(np.int16)
                return sr.AudioData(normalized.tobytes(), sample_rate, 2)

            except Exception as e:
                print(f"[STT SoundDevice Error: {e}]")

        # Fallback — SpeechRecognition built-in microphone
        try:
            with sr.Microphone() as source:
                return self.recognizer.listen(source, timeout=2.0, phrase_time_limit=duration)
        except Exception:
            pass

        return None

    async def listen_raw_audio(self, timeout: float = 2.0, phrase_time_limit: float = 4.0) -> Optional[sr.AudioData]:
        """Asynchronously records raw audio from the hardware microphone."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.record_mic_audio, phrase_time_limit)

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def transcribe_audio(self, audio: sr.AudioData) -> str:
        """Transcribes recorded AudioData using domain-prompt-conditioned Whisper STT."""
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
                    beam_size=5,
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
                print(f"[Whisper STT Error: {e}]")

        # Google STT fallback
        try:
            return self.recognizer.recognize_google(audio)
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # High-level listen methods
    # ------------------------------------------------------------------

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

        Single-phrase mode: the engine captures one complete utterance
        (terminated by ~224 ms of silence) and returns immediately.
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

        # No wake word — strict gating
        return False, ""
