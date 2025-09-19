import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import resample_poly
import scipy.signal
from pathlib import Path
import sounddevice as sd


BASE_PATH = Path(__file__).parent
DATASET_PATH = BASE_PATH / "dataset/vietel"
VALIDATE_PATH = BASE_PATH / "dataset/validate"
MODEL_PATH = BASE_PATH / "audio_classification.keras"

labels = [
    "alive",  # ringback tone
    "alive1",  # waiting sounds
    "alive2",  # leave message
    # "alive3",  # leave message - busy
    # "be_blocked",
    "be_blocked_and_incorrect",
    "can_not_connect",
    "has_no_money",
    # "incorrect",
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
    audio, sr = sf.read(filename)
    if audio.ndim > 1:  # stereo -> mono
        audio = audio[:, 0]

    # resample
    if sr != 16000:
        audio = resample_poly(audio, 16000, sr)
    return audio.astype(np.float32)


def add_white_noise(audio, noise_factor=0.005):
    noise = np.random.randn(len(audio))
    return (audio + noise_factor * noise).astype(np.float32)


# def shift_audio(audio, shift_max=2000):
#     shift = np.random.randint(-shift_max, shift_max)
#     return np.roll(audio, shift).astype(np.float32)


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


def removeFirst(
    audio,
    seconds,
    sr=16000,
):
    if not isinstance(audio, np.ndarray):
        raise TypeError("audio must be a numpy array")

    start_sample = int(seconds * sr)
    total_len = len(audio)

    if start_sample >= total_len:
        return np.zeros_like(audio)

    # Lấy phần còn lại
    trimmed = audio[start_sample:]

    # Bổ sung silence (0.0) cho đủ độ dài ban đầu
    padding = np.zeros(total_len - len(trimmed), dtype=audio.dtype)

    return np.concatenate([trimmed, padding])


def audio_to_embedding(audio):
    scores, embeddings, spectrogram = yamnet_model(audio)
    emb = tf.reduce_mean(embeddings, axis=0)
    return emb


def time_mask(audio, sr, mask_duration=0.2):
    augmented = audio.copy()
    mask_len = int(mask_duration * sr)
    start = np.random.randint(0, len(audio) - mask_len)
    augmented[start : start + mask_len] = 0
    return augmented.astype(np.float32)


def add_reverb(audio, sr, decay=0.3):
    ir_len = int(sr * 0.03)  # 30ms
    impulse = np.zeros(ir_len)
    impulse[0] = 1.0
    impulse += decay * np.random.randn(ir_len)
    reverb = scipy.signal.fftconvolve(audio, impulse)[: len(audio)]
    reverb = reverb / np.max(np.abs(reverb))
    return reverb.astype(np.float32)


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
        files = list(folder.glob("*.wav"))
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

            # max rate 1.2
            stretch = stretch_audio(
                audio,
                rate=1.2,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(stretch))
            # listen(stretch)
            # input()
            all_labels.append(idx)

    # add white noise only
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            noise = add_white_noise(
                audio,
                noise_factor=0.05,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(noise))
            all_labels.append(idx)

    # add random volume
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
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

    # Remove first 3s and stretch rate=1.3
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
                seconds=3,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

            stretch = stretch_audio(
                removed,
                rate=1.3,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(stretch))
            # listen(stretch)
            # input()
            all_labels.append(idx)

    # Remove first 1s and add white noise noise_factor=0.02
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
            removed = add_white_noise(
                removed,
                noise_factor=0.02,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Remove first 1s and stretch rate=0.9,
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
            removed = stretch_audio(
                removed,
                rate=1.2,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Stretch 0.8
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
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
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = stretch_audio(
                audio,
                rate=0.9,
            )
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
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_pink_noise(
                audio,
                amount=0.3,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Time mask 0.5s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = time_mask(
                audio,
                sr=16000,
                mask_duration=0.5,
            )
            # listen(removed)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Reverb decay=10 and remove first 2s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_reverb(
                audio,
                sr=16000,
                decay=10,
            )
            removed = removeFirst(removed, seconds=2)
            # listen(removed)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

        # Time mask 0.5s

    # Time mask 0.5s again
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = time_mask(
                audio,
                sr=16000,
                mask_duration=0.5,
            )
            # listen(removed)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

        # Time mask 0.5s again

    # Time mask 0.2s 4 times
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = time_mask(
                audio,
                sr=16000,
                mask_duration=0.2,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)
            removed = time_mask(
                removed,
                sr=16000,
                mask_duration=0.25,
            )
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)
            removed = time_mask(
                removed,
                sr=16000,
                mask_duration=0.25,
            )
            # listen(removed)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Time mask 0.2s 4 times and remove 2s
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
                seconds=2,
            )
            removed = time_mask(
                removed,
                sr=16000,
                mask_duration=0.2,
            )
            # listen(removed)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

        # Time mask 0.5s 4 times and remove 2s

    # Time mask 0.2s and add reverb 2
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_reverb(
                audio,
                sr=16000,
                decay=2,
            )
            removed = time_mask(
                removed,
                sr=16000,
                mask_duration=0.2,
            )
            # listen(removed)
            # input()
            training_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # add random volume and pink noise 0.03
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            noise = add_random_volume(audio)
            noise = add_pink_noise(
                noise,
                amount=0.3,
            )
            # listen(noise)
            # input()
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
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(audio))
            all_labels.append(idx)

            # clone 3: stretch
            # max rate 1.3
            stretch = stretch_audio(
                audio,
                rate=1.3,
            )
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(stretch))
            all_labels.append(idx)

    # # add white noise
    # for idx, label in enumerate(labels):
    #     folder = base_path / label
    #     files = list(folder.glob("*.wav"))
    #     if not files:
    #         print(f"[WARN] No files found in {folder}")
    #         continue
    #     for f in files:
    #         audio = load_wav(str(f))
    #         noise = add_white_noise(
    #             audio,
    #             noise_factor=0.1,
    #         )
    #         valiadtion_count += 1
    #         all_embeddings.append(audio_to_embedding(noise))
    #         all_labels.append(idx)

    # Remove first 3s add random volume
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
                seconds=3,
            )
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)
            removed = add_random_volume(removed)
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)

    # Time mask 0.3s 4 times
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = time_mask(
                audio,
                sr=16000,
                mask_duration=0.3,
            )
            # valiadtion_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)
            removed = time_mask(
                removed,
                sr=16000,
                mask_duration=0.3,
            )
            valiadtion_count += 1
            all_embeddings.append(audio_to_embedding(removed))
            all_labels.append(idx)
            removed = time_mask(
                removed,
                sr=16000,
                mask_duration=0.3,
            )
            # listen(removed)
            # input()
            valiadtion_count += 1
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
print(f"canhdt training count: {training_count}")
print(f"canhdt validation count: {valiadtion_count}")
# =========================
# Build classifier
# =========================

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
