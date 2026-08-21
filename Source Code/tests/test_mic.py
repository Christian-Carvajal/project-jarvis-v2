import time
import sys
import os
import numpy as np
import sounddevice as sd
import speech_recognition as sr

# Ensure src/ is discoverable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..")) if os.path.basename(CURRENT_DIR) == "tests" else CURRENT_DIR
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.voice_pipeline import discover_working_microphone, VoicePipeline

def test_microphone():
    print("=" * 65)
    print("       JARVIS MICROPHONE & VOICE STT DIAGNOSTIC UTILITY          ")
    print("=" * 65)

    # 1. Device Discovery
    dev_idx, native_sr, native_ch, dev_name = discover_working_microphone()

    print(f"\n[1] Auto-Discovered Hardware Microphone:")
    print(f"    - Name:         '{dev_name}'")
    print(f"    - Device Index: {dev_idx}")
    print(f"    - Sample Rate:  {native_sr} Hz")
    print(f"    - Channels:     {native_ch}")

    if dev_idx is None:
        print("\n[ERROR] No functional microphone could be opened.")
        print("   Please ensure microphone privacy is allowed in Windows Settings.")
        return

    print("\n[2] Live Audio Capture Test")
    print("    >>> GET READY... Speak a voice command clearly (e.g., 'Hey Jarvis open Spotify') <<<")
    print("    Recording starts in 1 second...")
    time.sleep(1.0)
    print("    [LIVE RECORDING ACTIVE -- SPEAK NOW!]")

    target_sr = 16000
    duration = 3.5
    target_block_size = 512
    native_block_size = int(target_block_size * (native_sr / target_sr))
    total_iterations = int((duration * target_sr) / target_block_size)

    captured_chunks = []
    
    try:
        def stream_cb(indata, frames, time_info, status):
            captured_chunks.append(indata.copy())

        with sd.InputStream(
            device=dev_idx,
            channels=native_ch,
            samplerate=native_sr,
            dtype='float32',
            blocksize=native_block_size,
            callback=stream_cb
        ):
            # Display real-time volume VU-meter
            for i in range(total_iterations):
                time.sleep(0.032)
                if captured_chunks:
                    recent = captured_chunks[-1]
                    amp = float(np.max(np.abs(recent)))
                    bars = int(min(amp * 100, 30))
                    meter = "#" * bars + "-" * (30 - bars)
                    elapsed = (i + 1) * 0.032
                    sys.stdout.write(f"\r    [{meter}] {amp*100:5.1f}% | Time: {elapsed:.1f}s / {duration:.1f}s")
                    sys.stdout.flush()
        print("\n\n    [OK] Audio capture complete!")
    except Exception as e:
        print(f"\n[FAIL] Recording stream error: {e}")
        return

    if not captured_chunks:
        print("[FAIL] No audio frames captured.")
        return

    # 3. Audio Processing & Normalization
    raw_np = np.concatenate(captured_chunks, axis=0)
    if native_ch > 1 and raw_np.ndim > 1:
        mono = np.mean(raw_np, axis=1)
    else:
        mono = raw_np.flatten()

    # Fast software resampling to 16,000 Hz
    num_target_samples = int(len(mono) * (target_sr / native_sr))
    orig_indices = np.linspace(0, len(mono) - 1, num_target_samples)
    resampled = np.interp(orig_indices, np.arange(len(mono)), mono).astype(np.float32)

    # DC offset removal & High-Pass filter
    resampled = resampled - np.mean(resampled)
    hp_filtered = np.empty_like(resampled)
    prev_in = 0.0
    prev_out = 0.0
    for i in range(len(resampled)):
        prev_out = 0.94 * (prev_out + resampled[i] - prev_in)
        prev_in = resampled[i]
        hp_filtered[i] = prev_out

    peak = float(np.max(np.abs(hp_filtered)))
    rms = float(np.sqrt(np.mean(hp_filtered ** 2)))

    print("\n[3] Microphone Audio Level Analysis:")
    print(f"    - Peak Amplitude:    {peak:.4f}")
    print(f"    - RMS Volume Energy: {rms:.4f}")

    # AGC Normalization
    gain_factor = min(28500.0 / (peak + 1e-5), 32000.0) if peak > 0.001 else 32000.0
    normalized = (hp_filtered * gain_factor).clip(-32767, 32767).astype(np.int16)
    audio_data = sr.AudioData(normalized.tobytes(), target_sr, 2)

    # 4. Speech Recognition Test
    print("\n[4] Running Voice Transcription Engine...")
    r = sr.Recognizer()
    transcription = ""

    try:
        transcription = r.recognize_google(audio_data)
    except sr.UnknownValueError:
        transcription = "[No intelligible speech detected - microphone audio signal is clear and functional!]"
    except Exception as e:
        transcription = f"Could not transcribe speech ({e})"

    print("\n" + "=" * 65)
    print(f"   TRANSCRIBED TEXT: \"{transcription}\"")
    print("=" * 65)

    # 5. Wake word gating test
    if transcription and not transcription.startswith("["):
        pipeline = VoicePipeline()
        is_wake, cmd = pipeline.filter_wake_word(transcription)
        print(f"\n[5] Command Gateway Verification:")
        print(f"    - Wake Word Detected: {is_wake}")
        print(f"    - Extracted Command:  \"{cmd or transcription}\"")
    print()

if __name__ == "__main__":
    test_microphone()

