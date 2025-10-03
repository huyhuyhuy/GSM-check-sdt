import os
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from vosk import Model, KaldiRecognizer, SetLogLevel
import json
from pathlib import Path
import sounddevice as sd
import io
from pydub import AudioSegment


SetLogLevel(-1)  # reduce VOSK logging

# === Hardcoded paths ===
BASE_PATH = Path(__file__).parent
WAV_FOLDER = BASE_PATH / "dataset/vina"
# MODEL_PATH = BASE_PATH / "vosk-model-small-vn-0.4"
MODEL_PATH = BASE_PATH / "vosk-model-vn-0.4"


def listen(audio):
    """Play audio in normal Python (terminal)"""
    # if isinstance(audio, tf.Tensor):
    #     audio = audio.numpy()
    print("▶️ playing audio...")
    sd.play(
        audio,
        16000,
    )
    sd.wait()  # block cho tới khi play xong
    print("✅ done")


def load_wav(filename: str, target_sample_rate=16000):

    # v2
    audio_segment = AudioSegment.from_file(filename)
    audio_segment = audio_segment.set_channels(1).set_frame_rate(target_sample_rate)
    wav_io = io.BytesIO()
    audio_segment.export(wav_io, format="wav")
    wav_io.seek(0)
    audio, sr = sf.read(wav_io)
    if audio.ndim > 1:  # stereo -> mono
        audio = audio[:, 0]
    if sr != 16000:
        audio = resample_poly(audio, 16000, sr)

    # listen(audio)
    # input()
    return audio.astype(np.float32)


def load_wav_resample(path, target_sr=16000):
    data = load_wav(path)
    # listen(data)
    # input()
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    return pcm, target_sr


def transcribe_file(model, wav_path):
    pcm, sr = load_wav_resample(wav_path, target_sr=16000)
    rec = KaldiRecognizer(model, sr)
    rec.SetWords(False)

    pcm_bytes = pcm.tobytes()
    pos, chunk_size = 0, 4000
    texts = []

    while pos < len(pcm_bytes):
        end = pos + chunk_size
        if rec.AcceptWaveform(pcm_bytes[pos:end]):
            res = json.loads(rec.Result())
            if res.get("text"):
                texts.append(res["text"])
        pos = end

    final_res = json.loads(rec.FinalResult())
    if final_res.get("text"):
        texts.append(final_res["text"])
    return " ".join(texts).strip()


if __name__ == "__main__":
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"VOSK model not found at {MODEL_PATH}")

    print("canhdt start")
    model = Model(str(MODEL_PATH))

    for fname in os.listdir(WAV_FOLDER):
        if fname.lower().endswith(".amr"):
            fpath = os.path.join(WAV_FOLDER, fname)
            transcript = transcribe_file(model, fpath)
            print(f"[{fname}] {transcript}")
