import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from pathlib import Path
import sounddevice as sd
import io
from pydub import AudioSegment

# =========================
# Config
# =========================
BASE_PATH = Path(__file__).parent
# TEST_PATH = BASE_PATH / "dataset/testing"
# TEST_PATH = BASE_PATH / "dataset/prepare_dataset"
TEST_PATH = BASE_PATH / "dataset_v2/validate/incorrect"
# TEST_PATH = BASE_PATH / "dataset/vietel/unknown"

FORCE_LABEL = 5
MODEL_PATH = BASE_PATH / "audio_classification_v2.keras"
# MODEL_PATH = BASE_PATH / "audio_classification_wav2vec2.keras"

labels = [
    "alive",  # ringback tone
    "alive1",  # waiting sounds
    "alive2",  # leave message
    # "alive3",  # leave message - busy
    "be_blocked",
    # "be_blocked_and_incorrect",  # merged class with the same vocal
    "can_not_connect",
    # "has_no_money",
    "incorrect",
    # "unknown",
]
num_classes = len(labels)

# =========================
# Load pretrained models
# =========================
print("🔹 Loading YAMNet backbone...")
yamnet_model_handle = "https://tfhub.dev/google/yamnet/1"
yamnet_model = hub.load(yamnet_model_handle)

print("🔹 Loading trained classifier...")
classifier = tf.keras.models.load_model(MODEL_PATH, compile=False)


# =========================
# Audio utils
# =========================
def load_wav(filename: str):

    # v2

    # audio, sr = sf.read(filename)
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

    # v1
    # # audio, sr = librosa.load(
    # #     filename,
    # #     # mono=True,
    # #     # sr=16000,
    # # )
    # audio, sr = sf.read(filename)
    # if audio.ndim > 1:  # stereo -> mono
    #     # audio = np.mean(audio, axis=1)
    #     audio = audio[:, 0]
    #     # audio = audio[:, 0] + audio[:, 1]
    #     # audio = audio[:, 1]
    #     # audio = audio[:, 0]

    # # resample về 16kHz, nhưng giữ nguyên tốc độ/nội dung
    # if sr != 16000:
    #     audio = resample_poly(audio, 16000, sr)
    # return audio.astype(np.float32)


def audio_to_embedding(audio):
    """Convert waveform -> YAMNet embedding"""
    scores, embeddings, spectrogram = yamnet_model(audio)
    emb = tf.reduce_mean(embeddings, axis=0)
    return emb


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


# =========================
# Run inference on testing folder
# =========================
print("🔹 Running inference on testing dataset...")

files = list(TEST_PATH.glob("*.amr"))
if not files:
    print(f"[WARN] No .wav files found in {TEST_PATH}")
else:
    for f in files:
        audio = load_wav(str(f))
        # listen(audio)
        # input()
        emb = audio_to_embedding(audio)
        emb = tf.expand_dims(emb, 0)  # batch size 1

        preds = classifier.predict(emb, verbose=0)
        pred_idx = int(np.argmax(preds[0]))
        pred_label = labels[pred_idx]
        confidence = float(preds[0][pred_idx])

        print(f"🎧 File: {f.name}")
        if FORCE_LABEL != None and FORCE_LABEL != pred_idx:
            print(f"❌   → Predicted: {pred_label} ({confidence:.2%})\n")
        elif confidence < 0.95:
            # warning icon
            print(f"⚠️   → Predicted: {pred_label} ({confidence:.2%})\n")
        else:
            print(f"   → Predicted: {pred_label} ({confidence:.2%})\n")
