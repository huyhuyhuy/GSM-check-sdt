import tensorflow as tf
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from pathlib import Path
from transformers import TFWav2Vec2Model

# =========================
# Config
# =========================
BASE_PATH = Path(__file__).parent
MODEL_PATH = BASE_PATH / "audio_classification_wav2vec2.keras"
TEST_PATH = BASE_PATH / "dataset/testing"

labels = [
    "alive",
    "alive1",  # waiting sounds
    "alive2",  # leave message
    "be_blocked",
    "can_not_connect",
    "has_no_money",
    "incorrect",
    "unknown",
]

MAX_LEN = 16000 * 14  # 14s


# =========================
# Audio utils
# =========================
def load_wav(filename: str):
    audio, sr = sf.read(filename)
    if audio.ndim > 1:  # convert stereo -> mono
        audio = audio[:, 0] + audio[:, 1] + audio[:, 1]
    if sr != 16000:
        audio = resample_poly(audio, 16000, sr)
    return audio.astype(np.float32)


def pad_audio(audio, max_len=MAX_LEN):
    if len(audio) >= max_len:
        return audio[:max_len]
    else:
        return np.pad(audio, (0, max_len - len(audio)), mode="constant")


# =========================
# Load model
# =========================
print(f"🔹 Loading model from {MODEL_PATH} ...")
model = tf.keras.models.load_model(
    MODEL_PATH,
    custom_objects={"TFWav2Vec2Model": TFWav2Vec2Model},
)
print("✅ Model loaded successfully!")


# =========================
# Run testing
# =========================
def predict_audio(file_path):
    audio = load_wav(file_path)
    audio = pad_audio(audio)
    audio = np.expand_dims(audio, axis=0)  # (1, seq_len)
    preds = model.predict(audio)
    pred_id = np.argmax(preds, axis=1)[0]
    pred_label = labels[pred_id]
    return pred_label, preds[0][pred_id]


print(f"\n🔹 Testing on folder: {TEST_PATH}")
for wav_file in TEST_PATH.glob("*.wav"):
    label, conf = predict_audio(str(wav_file))
    print(f"{wav_file.name:30s} -> {label} ({conf:.2f})")
