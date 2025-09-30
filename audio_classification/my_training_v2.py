import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import resample_poly
from pathlib import Path
import sounddevice as sd
from pydub import AudioSegment
import io


BASE_PATH = Path(__file__).parent
DATASET_PATH = BASE_PATH / "dataset_v2/vietel"
VALIDATE_PATH = BASE_PATH / "dataset_v2/validate"
MODEL_PATH = BASE_PATH / "audio_classification_v2.keras"

# ffmpeg_path = r"D:\ffmpeg-2025-09-25-git-9970dc32bf-full_build\bin\ffmpeg.exe"
# ffprobe_path = r"D:\ffmpeg-2025-09-25-git-9970dc32bf-full_build\bin\ffprobe.exe"
# AudioSegment.converter = ffmpeg_path
# AudioSegment.ffprobe = ffprobe_path

labels = [
    "alive",  # ringback tone
    "alive1",  # waiting sounds
    "alive2",  # leave message
    "be_blocked",
    # "be_blocked_and_incorrect",
    "can_not_connect",
    # "has_no_money",
    # "incorrect",
    # "unknown",
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
def load_wav(filename: str, target_sample_rate=16000):

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


def add_white_noise(audio, noise_factor=0.005):
    noise = np.random.randn(len(audio))
    return (audio + noise_factor * noise).astype(np.float32)


def stretch_audio(audio, rate=1.1):
    """Time-stretch waveform using librosa (via STFT)."""
    # STFT
    stft = librosa.stft(audio)
    # Stretch
    stft_stretch = librosa.phase_vocoder(stft, rate=rate)
    # Inverse STFT
    stretched = librosa.istft(stft_stretch)
    return stretched.astype(np.float32)


def add_pink_noise(audio, amount=0.005):
    n = len(audio)
    uneven = n % 2
    X = np.random.randn(n // 2 + 1 + uneven) + 1j * np.random.randn(n // 2 + 1 + uneven)
    S = np.sqrt(np.arange(len(X)) + 1.0)  # 1/f
    y = (np.fft.irfft(X / S)).real
    if uneven:
        y = y[:-1]
    y = y / np.max(np.abs(y))  # chuẩn hóa
    augmented = audio + amount * y[: len(audio)]
    return augmented.astype(np.float32)


def time_mask(audio, sr, mask_duration=0.2):
    augmented = audio.copy()
    mask_len = int(mask_duration * sr)
    start = np.random.randint(0, len(audio) - mask_len)
    augmented[start : start + mask_len] = 0
    return augmented.astype(np.float32)


def add_random_volume(
    audio,
    sr=16000,
    chunk_duration=1.0,
    prob=0.3,
    min_gain=0.5,
    max_gain=1.5,
):
    audio = audio.copy()
    chunk_size = int(sr * chunk_duration)
    n_chunks = int(np.ceil(len(audio) / chunk_size))

    for i in range(n_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, len(audio))

        if np.random.rand() < prob:
            gain = np.random.uniform(min_gain, max_gain)
            audio[start:end] *= gain

    return audio.astype(np.float32)


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


def audio_to_embedding(audio):
    scores, embeddings, spectrogram = yamnet_model(audio)
    emb = tf.reduce_mean(embeddings, axis=0)
    return emb


# =========================
# Build dataset (clone + noise)
# =========================
training_count = 0


def build_dataset(base_path, labels):
    global training_count
    all_embeddings, all_labels = [], []

    # original
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            # listen(audio)
            # input()
            # always keep original
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # add white noise only noise_factor=0.01
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            # if idx != labels.index("unknown"):
            audio = add_white_noise(
                audio,
                noise_factor=0.01,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # add random volume
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            noise = add_random_volume(audio)
            # listen(noise)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(noise))
            all_labels.append(idx)

    # stretch rate=1.2
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            stretch = stretch_audio(
                audio,
                rate=1.2,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(stretch))
            all_labels.append(idx)

    # add white noise noise_factor=0.02
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            # if idx != labels.index("unknown"):
            audio = add_white_noise(
                audio,
                noise_factor=0.02,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # stretch rate=0.8,
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = stretch_audio(
                audio,
                rate=0.8,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Stretch 0.9 and add white noise 0.01
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = stretch_audio(
                audio,
                rate=0.9,
            )
            # if idx != labels.index("unknown"):
            removed = add_white_noise(
                removed,
                noise_factor=0.01,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # pink noise 0.03
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            # if idx != labels.index("unknown"):
            audio = add_pink_noise(
                audio,
                amount=0.3,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # Time mask 1s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            if idx != labels.index("alive1"):
                audio = time_mask(
                    audio,
                    sr=16000,
                    mask_duration=1,
                )
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # Time mask 0.3s 4 times
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            if idx != labels.index("alive1"):
                audio = time_mask(
                    audio,
                    sr=16000,
                    mask_duration=0.3,
                )
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)
            if idx != labels.index("alive1"):
                audio = time_mask(
                    audio,
                    sr=16000,
                    mask_duration=0.3,
                )
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)
            if idx != labels.index("alive1"):
                audio = time_mask(
                    audio,
                    sr=16000,
                    mask_duration=0.3,
                )
            # listen(removed)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # Time mask 0.5s 4 times and add random volume
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_random_volume(
                audio,
            )
            if idx != labels.index("alive1"):
                removed = time_mask(
                    removed,
                    sr=16000,
                    mask_duration=0.5,
                )
                removed = time_mask(
                    removed,
                    sr=16000,
                    mask_duration=0.5,
                )
                removed = time_mask(
                    removed,
                    sr=16000,
                    mask_duration=0.5,
                )
                removed = time_mask(
                    removed,
                    sr=16000,
                    mask_duration=0.5,
                )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # add random volume and pink noise 0.03
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            noise = add_random_volume(audio)
            # if idx != labels.index("unknown"):
            noise = add_pink_noise(
                noise,
                amount=0.3,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(noise))
            all_labels.append(idx)

    X = tf.stack(all_embeddings)
    y = tf.convert_to_tensor(all_labels, dtype=tf.int32)
    return tf.data.Dataset.from_tensor_slices((X, y))


# =========================
# Build validation dataset (no augmentation)
# =========================
valiadtion_count = 0


def build_validation_dataset(
    base_path,
    labels,
):
    global valiadtion_count
    all_embeddings, all_labels = [], []

    # original
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # add white noise
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            # if idx != labels.index("unknown"):
            audio = add_white_noise(
                audio,
                noise_factor=0.05,
            )
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

    # add random volume
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_random_volume(audio)
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Time mask 0.1s 4 times
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.amr"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            if idx != labels.index("alive1"):
                audio = time_mask(
                    audio,
                    sr=16000,
                    mask_duration=0.1,
                )
                audio = time_mask(
                    audio,
                    sr=16000,
                    mask_duration=0.1,
                )
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)
            if idx != labels.index("alive1"):
                audio = time_mask(
                    audio,
                    sr=16000,
                    mask_duration=0.1,
                )
            # listen(removed)
            # input()
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(audio))
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
print(f"canhdt training count: {training_count}")
print(f"canhdt validation count: {valiadtion_count}")
# =========================
# Build classifier
# =========================
reload = False

if reload and MODEL_PATH.exists():
    print(f"🔹 Loading model from {MODEL_PATH}")
    classifier = tf.keras.models.load_model(MODEL_PATH)
else:
    print("🔹 Building new model...")
    classifier = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(1024,)),
            tf.keras.layers.Dense(1024, activation="relu"),
            tf.keras.layers.Dense(512, activation="relu"),
            tf.keras.layers.Dense(256, activation="relu"),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dense(64, activation="relu"),
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
# canhdt training_count: 2220
# canhdt valiadtion_count: 310
history = classifier.fit(
    train_ds,
    validation_data=val_ds,
    epochs=30,
    # steps_per_epoch=70,
    # validation_steps=8,
)

# =========================
# Save model
# =========================
classifier.save(MODEL_PATH)
print(f"✅ Model saved to {MODEL_PATH}")
