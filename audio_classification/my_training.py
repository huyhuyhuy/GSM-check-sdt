import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import resample_poly
from pathlib import Path
import sounddevice as sd

BASE_PATH = Path(__file__).parent
DATASET_PATH = BASE_PATH / "dataset/vietel"
VALIDATE_PATH = BASE_PATH / "dataset/vietel/validate"
MODEL_PATH = BASE_PATH / "audio_classification.keras"

labels = [
    "alive",
    "can_not_connect",
    "incorrect",
    "unknown",
]
num_classes = len(labels)

# =========================
# Load YAMNet backbone
# =========================
yamnet_model_handle = "https://tfhub.dev/google/yamnet/1"
yamnet_model = hub.load(yamnet_model_handle)


# =========================
# Audio utils + augmentation
# =========================
def load_wav(filename: str):
    # audio, sr = librosa.load(
    #     filename,
    #     # mono=True,
    #     # sr=16000,
    # )
    audio, sr = sf.read(filename)
    if audio.ndim > 1:  # stereo -> mono
        # audio = np.sum(audio, axis=1)
        audio = audio[:, 0] + audio[:, 1] + audio[:, 1]

    # resample về 16kHz, nhưng giữ nguyên tốc độ/nội dung
    if sr != 16000:
        audio = resample_poly(audio, 16000, sr)
    return audio.astype(np.float32)


def add_white_noise(audio, noise_factor=0.005):
    noise = np.random.randn(len(audio))
    return (audio + noise_factor * noise).astype(np.float32)


def shift_audio(audio, shift_max=2000):
    shift = np.random.randint(-shift_max, shift_max)
    return np.roll(audio, shift).astype(np.float32)


def stretch_audio(audio, rate=1.1):
    """Time-stretch waveform using librosa (via STFT)."""
    # STFT
    stft = librosa.stft(audio)
    # Stretch
    stft_stretch = librosa.phase_vocoder(stft, rate=rate)
    # Inverse STFT
    stretched = librosa.istft(stft_stretch)
    return stretched.astype(np.float32)


def removeFirst(
    audio,
    seconds,
    sr=16000,
):
    if isinstance(audio, np.ndarray):
        start_sample = int(seconds * sr)
        if start_sample >= len(audio):
            return np.array([], dtype=audio.dtype)  # all removed
        return audio[start_sample:]
    else:
        raise TypeError("audio must be a numpy array")


def audio_to_embedding(audio):
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
# Build dataset (clone + noise)
# =========================
def build_dataset(base_path, labels):
    all_embeddings, all_labels = [], []
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            # listen(audio)
            # input()
            # always keep original
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

            # clone 1: add white noise
            # maximum 0.1
            noise = add_white_noise(
                audio,
                noise_factor=0.05,
            )
            all_embeddings.append(audio_to_embedding(noise))
            # listen(noise)
            # input()
            all_labels.append(idx)

            # clone 2: shift
            shift_noise = shift_audio(
                audio,
            )
            all_embeddings.append(audio_to_embedding(shift_noise))
            # listen(shift_noise)
            # input()
            all_labels.append(idx)

            # clone 3: stretch
            # max rate 1.5
            stretch = stretch_audio(
                audio,
                rate=1.5,
            )
            all_embeddings.append(audio_to_embedding(stretch))
            # listen(stretch)
            # input()
            all_labels.append(idx)

    # Remove first 1s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = removeFirst(
                audio,
                seconds=1,
            )
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

            stretch = stretch_audio(
                removed,
                rate=1.3,
            )
            all_embeddings.append(audio_to_embedding(stretch))
            # listen(stretch)
            # input()
            all_labels.append(idx)

    X = tf.stack(all_embeddings)
    y = tf.convert_to_tensor(all_labels, dtype=tf.int32)
    return tf.data.Dataset.from_tensor_slices((X, y))


# =========================
# Build validation dataset (no augmentation)
# =========================
def build_validation_dataset(
    base_path,
    labels,
):
    all_embeddings, all_labels = [], []
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            # listen(audio)
            # input()
            # always keep original
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

            # clone 1: add white noise
            # maximum 0.1
            noise = add_white_noise(
                audio,
                noise_factor=0.1,
            )
            all_embeddings.append(audio_to_embedding(noise))
            # listen(noise)
            # input()
            all_labels.append(idx)

            # clone 2: shift
            shift_noise = shift_audio(
                audio,
            )
            all_embeddings.append(audio_to_embedding(shift_noise))
            # listen(shift_noise)
            # input()
            all_labels.append(idx)

            # clone 3: stretch
            # max rate 1.5

            stretch = stretch_audio(
                audio,
                rate=1.5,
            )
            all_embeddings.append(audio_to_embedding(stretch))
            # listen(stretch)
            # input()
            all_labels.append(idx)

    # Remove first 1s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            print(f"canhd label: {label}\nfile: {f}")
            audio = load_wav(str(f))
            removed = removeFirst(
                audio,
                seconds=6,
            )
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    X = tf.stack(all_embeddings)
    y = tf.convert_to_tensor(all_labels, dtype=tf.int32)
    return tf.data.Dataset.from_tensor_slices((X, y))


# =========================
# Build train/val datasets
# =========================
train_ds = (
    build_dataset(
        DATASET_PATH,
        labels,
    )
    .batch(32)
    .prefetch(tf.data.AUTOTUNE)
)
val_ds = (
    build_validation_dataset(
        VALIDATE_PATH,
        labels,
    )
    .batch(32)
    .prefetch(tf.data.AUTOTUNE)
)

# =========================
# Build classifier
# =========================
classifier = tf.keras.Sequential(
    [
        tf.keras.layers.Input(shape=(1024,)),
        tf.keras.layers.Dense(512, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ]
)

classifier.compile(
    optimizer=tf.keras.optimizers.Adam(1e-4),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

# =========================
# Train
# =========================
history = classifier.fit(train_ds, validation_data=val_ds, epochs=30)

# =========================
# Save model
# =========================
classifier.save(MODEL_PATH)
print(f"✅ Model saved to {MODEL_PATH}")
