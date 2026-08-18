import asyncio
import tempfile
import os
import re
import numpy as np
import speech_recognition as sr
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


def find_best_hardware_microphone() -> Optional[int]:
    """Scans Windows audio devices and selects the active physical hardware microphone, bypassing muted virtual webcams."""
    if not HAS_SOUNDDEVICE:
        return None

    try:
        devices = sd.query_devices()
        avoid_keywords = ['iriun', 'stereo mix', 'virtual', 'mapper', 'camo']
        preferred_keywords = ['realtek', 'intel', 'array', 'nvidia broadcast', 'microphone']

        # 1. Look for physical hardware mic array
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_lower = dev['name'].lower()
                if any(avoid in name_lower for avoid in avoid_keywords):
                    continue
                if any(pref in name_lower for pref in preferred_keywords):
                    print(f"[STT Mic Auto-Select]: Found hardware microphone '{dev['name']}' at Index {idx}.")
                    return idx

        # 2. Fallback to first non-virtual input device
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name_lower = dev['name'].lower()
                if not any(avoid in name_lower for avoid in avoid_keywords):
                    print(f"[STT Mic Auto-Select]: Selected input device '{dev['name']}' at Index {idx}.")
                    return idx
    except Exception as e:
        print(f"[STT Mic Selection Notice: {e}]")

    return None


class STTEngine:
    """High-Precision Local Speech-to-Text Engine with CUDA Hardware Acceleration and Silero VAD Auto-Slicing."""

    def __init__(self, model_size: str = "base", wake_words: Optional[list[str]] = None):
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
            except Exception as e:
                print(f"[STT Warning: Silero VAD model load notice ({e})]")

    def _init_whisper_model(self):
        """Initializes WhisperModel with CUDA float16 acceleration and CPU int8 fallback."""
        if not HAS_FASTER_WHISPER:
            return None

        # 1. Try CUDA GPU offloading with immediate runtime verification
        has_cuda = hasattr(ctranslate2, "get_cuda_device_count") and ctranslate2.get_cuda_device_count() > 0
        if has_cuda:
            try:
                print(f"[STT Engine]: Initializing Faster-Whisper '{self.model_size}' on CUDA (float16)...")
                test_model = WhisperModel(self.model_size, device="cuda", compute_type="float16")
                # Run 0.5s dummy inference to verify cublas64_12.dll loads cleanly
                dummy_audio = np.zeros(8000, dtype=np.float32)
                list(test_model.transcribe(dummy_audio)[0])
                print("[STT Engine]: GPU Acceleration successfully active!")
                return test_model
            except Exception as err:
                print(f"[STT Engine Warning]: CUDA init failed ({err}). Defaulting to CPU int8.")

        # 2. Fallback to CPU int8 if CUDA is unavailable or missing DLLs
        try:
            print(f"[STT Engine]: Initializing Faster-Whisper '{self.model_size}' on CPU (int8)...")
            return WhisperModel(self.model_size, device="cpu", compute_type="int8")
        except Exception as ex:
            print(f"[STT Error: Faster-Whisper initialization deferred ({ex}).]")
            return None

    def record_mic_audio(self, duration: float = 3.5) -> Optional[sr.AudioData]:
        """Captures hardware microphone audio with frame-by-frame Silero VAD streaming and 300ms trailing silence auto-slicing."""
        sample_rate = 16000
        block_size = 512  # ~32ms per audio frame

        if HAS_SOUNDDEVICE:
            try:
                audio_frames = []
                speech_detected = False
                silent_frames = 0
                max_frames = int((duration * sample_rate) / block_size)
                max_silence_frames = 10  # 10 * 32ms = ~320ms trailing silence threshold

                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype='float32',
                    blocksize=block_size,
                    device=self.input_device_index
                ) as stream:
                    for _ in range(max_frames):
                        frame, overflow = stream.read(block_size)
                        flat_frame = frame.flatten()
                        audio_frames.append(flat_frame)

                        if self.vad_model:
                            try:
                                prob = float(self.vad_model(flat_frame)[0])
                                if prob > 0.4:
                                    speech_detected = True
                                    silent_frames = 0
                                elif speech_detected:
                                    silent_frames += 1
                                    if silent_frames >= max_silence_frames:
                                        # Auto-slice audio capture immediately upon trailing silence
                                        break
                            except Exception:
                                pass

                if not audio_frames:
                    return None

                raw_audio = np.concatenate(audio_frames)
                max_val = np.max(np.abs(raw_audio))

                if max_val < 0.005:  # Muted hardware mic
                    return None

                # Normalize gain to prevents distortion/whispering errors
                normalized_audio = (raw_audio / (max_val + 1e-5) * 30000.0).astype(np.int16)
                raw_bytes = normalized_audio.tobytes()
                return sr.AudioData(raw_bytes, sample_rate, 2)

            except Exception as e:
                print(f"[sounddevice VAD Streaming Error: {e}]")

        # Fallback to SpeechRecognition Microphone if sounddevice stream fails
        try:
            with sr.Microphone() as source:
                return self.recognizer.listen(source, timeout=2.0, phrase_time_limit=duration)
        except Exception:
            pass

        return None

    async def listen_raw_audio(self, timeout: float = 2.0, phrase_time_limit: float = 3.5) -> Optional[sr.AudioData]:
        """Asynchronously records raw audio from the selected hardware microphone."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.record_mic_audio, phrase_time_limit)

    def transcribe_audio(self, audio: sr.AudioData) -> str:
        """Transcribes recorded AudioData using domain-prompt-conditioned Whisper AI."""
        if not audio:
            return ""

        if self.whisper_model:
            try:
                wav_bytes = audio.get_wav_data()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    temp_wav = fp.name
                    fp.write(wav_bytes)

                # Domain initial prompt conditions Whisper to accurately decode PC automation words
                domain_prompt = "JARVIS AI commands: play music on spotify, play fein on spotify, play highest in the room, play youtube, search google, open brave, close spotify, system status."

                segments, _ = self.whisper_model.transcribe(
                    temp_wav,
                    beam_size=5,
                    language="en",
                    initial_prompt=domain_prompt,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=250)
                )
                text = " ".join([segment.text for segment in segments]).strip()

                try:
                    os.remove(temp_wav)
                except Exception:
                    pass

                return text
            except Exception as e:
                print(f"[Whisper STT Error: {e}]")

        try:
            return self.recognizer.recognize_google(audio)
        except Exception:
            return ""

    async def listen_command(self, timeout: float = 3.0, phrase_time_limit: float = 4.0) -> str:
        """Capture and transcribe user command."""
        audio = await self.listen_raw_audio(timeout=timeout, phrase_time_limit=phrase_time_limit)
        if audio:
            return self.transcribe_audio(audio)
        return ""

    async def detect_wake_word_or_command(self, timeout: float = 2.0) -> Tuple[bool, str]:
        """Captures microphone audio and transcribes spoken text."""
        audio = await self.listen_raw_audio(timeout=timeout, phrase_time_limit=3.5)
        if not audio:
            return False, ""

        transcription = self.transcribe_audio(audio).strip()
        if not transcription or len(transcription) < 2:
            return False, ""

        trans_lower = transcription.lower()

        # Filter out common single hallucinated Whisper artifacts like "you", "thanks", "bye"
        if trans_lower in ["you", "thank you", "thanks", "bye", "subtitles", "thankyou"]:
            return False, ""

        # 1. Wake word detected
        if any(w in trans_lower for w in self.wake_words):
            clean_cmd = re.sub(r'^(?:hey\s+)?jarvis\s*,?\s*', '', trans_lower, flags=re.IGNORECASE).strip()
            return True, clean_cmd

        # 2. Strict Gating: No wake word detected -> discard completely!
        return False, ""
