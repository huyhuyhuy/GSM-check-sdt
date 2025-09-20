"""
Batch Vietnamese speech-to-text using OpenAI Whisper (local).
Transcribes all WAV files in a given folder and prints results.
"""

import os
from pathlib import Path
import whisper
import shutil
import sounddevice as sd
import soundfile as sf
from scipy.signal import resample_poly
import numpy as np
import torch
import tensorflow as tf

# === Hardcoded paths ===
BASE_PATH = Path(__file__).parent
WAV_FOLDER = BASE_PATH / "dataset/prepare_dataset"

# Load Whisper model (choose: tiny, base, small, medium, large)
model = whisper.load_model("large")


def listen(audio):
    """Play audio in normal Python (terminal)"""
    if isinstance(audio, tf.Tensor):
        audio = audio.numpy()
    print("▶️ playing audio...")
    sd.play(
        audio,
        16000,
    )
    sd.wait()  # block cho tới khi play xong
    print("✅ done")


def load_wav(filename: str):
    audio, sr = sf.read(filename)
    if audio.ndim > 1:  # stereo -> mono
        audio = audio[:, 0]
    if sr != 16000:
        audio = resample_poly(audio, 16000, sr)
    return audio.astype(np.float32)


# def transcribe_file(wav_path: Path, language="vi"):
#     """Transcribe file using Whisper local"""
#     result = model.transcribe(str(wav_path), language=language)
#     return result["text"]


if __name__ == "__main__":
    for fname in os.listdir(WAV_FOLDER):
        if fname.lower().endswith(".wav"):
            fpath = WAV_FOLDER / fname
            try:
                audio = load_wav(str(fpath))

                audio_tensor = torch.from_numpy(audio)
                print(audio_tensor.shape)
                result = model.transcribe(audio_tensor, language="vi", fp16=False)
                print(f'canhdt [{fname}] content: {result["text"]}')
            except Exception as e:
                print(f"❌ Error: {e}")
