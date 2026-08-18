import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr

try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

def test_microphone():
    print("=" * 60)
    print("      JARVIS MICROPHONE & VOICE STT DIAGNOSTIC UTILITY     ")
    print("=" * 60)

    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    default_input = sd.query_devices(kind='input')

    print(f"\n[1] Detected {len(input_devices)} Audio Input Device(s):")
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            is_default = " (DEFAULT)" if dev['name'] == default_input['name'] else ""
            print(f"    - Index {idx}: {dev['name']}{is_default}")

    print(f"\n[2] Active Recording Device: '{default_input['name']}'")
    print("\n[3] Testing Microphone Input (Speak into your mic for 4 seconds)...")

    sample_rate = 16000
    duration = 4.0
    print("\n>>> RECORDING STARTED NOW - SPEAK CLEARLY NOW <<<")

    for i in range(4, 0, -1):
        print(f"Countdown: {i}...")
        time.sleep(1.0)

    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()

    audio_flat = recording.flatten()
    rms = float(np.sqrt(np.mean(audio_flat.astype(np.float32) ** 2)))
    max_amp = float(np.max(np.abs(audio_flat)))

    print("\n[4] Microphone Audio Level Analysis:")
    print(f"    - RMS Volume Energy: {rms:.2f}")
    print(f"    - Peak Amplitude:    {max_amp:.2f}")

    bars = int(min(rms / 10.0, 30))
    meter = "█" * bars + "░" * (30 - bars)
    print(f"    - Volume Meter:      [{meter}]")

    if max_amp < 100:
        print("\n❌ WARNING: Extremely low or zero audio signal detected!")
        print("   Possible causes: Microphone hardware is muted, Windows mic privacy permission disabled, or wrong input device selected.")
    else:
        print("\n✅ Audio signal successfully captured from microphone!")

    print("\n[5] Testing Voice-to-Text Transcription...")
    raw_bytes = recording.tobytes()
    audio_data = sr.AudioData(raw_bytes, sample_rate, 2)

    transcription = ""
    if HAS_WHISPER:
        try:
            print("   Running local Whisper AI model...")
            whisper = WhisperModel("tiny", device="cpu", compute_type="int8")
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                fp.write(audio_data.get_wav_data())
                tmp = fp.name
            segments, _ = whisper.transcribe(tmp, beam_size=1)
            transcription = " ".join([s.text for s in segments]).strip()
            try:
                os.remove(tmp)
            except Exception:
                pass
        except Exception as e:
            print(f"   Whisper Notice: {e}")

    if not transcription:
        try:
            print("   Running Google Speech Recognition fallback...")
            r = sr.Recognizer()
            transcription = r.recognize_google(audio_data)
        except Exception as e:
            transcription = f"Could not transcribe speech ({e})"

    print(f"\n=======================================================")
    print(f"   RESULTS - TRANSCRIBED TEXT: \"{transcription}\"")
    print(f"=======================================================\n")

if __name__ == "__main__":
    test_microphone()
