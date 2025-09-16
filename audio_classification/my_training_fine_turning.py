import tensorflow as tf
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import resample_poly
import scipy.signal
from pathlib import Path
import sounddevice as sd
from transformers import TFWav2Vec2Model

BASE_PATH = Path(__file__).parent
DATASET_PATH = BASE_PATH / "dataset/vietel"
VALIDATE_PATH = BASE_PATH / "dataset/validate"
MODEL_PATH = BASE_PATH / "audio_classification_wav2vec2.keras"

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
num_classes = len(labels)

MAX_LEN = 16000 * 14  # 10s

# =========================
# Load Hugging Face backbone
# =========================
pretrained_name = "facebook/wav2vec2-base"
wav2vec2 = TFWav2Vec2Model.from_pretrained(
    pretrained_name, from_pt=True, trainable=False
)

for layer in wav2vec2.wav2vec2.encoder.layer[:-4]:
    layer.trainable = False


# =========================
# Audio utils
# =========================
def load_wav(filename: str):
    audio, sr = sf.read(filename)
    if audio.ndim > 1:
        audio = audio[:, 0] + audio[:, 1] + audio[:, 1]
    if sr != 16000:
        audio = resample_poly(audio, 16000, sr)

    # target_len = MAX_LEN
    # cur_len = len(audio)
    # if cur_len != target_len:
    #     print(f"canhdt cur_len: {cur_len}, target_len: {target_len}")
    #     audio = resample_poly(audio, target_len, cur_len)

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
    if isinstance(audio, np.ndarray):
        start_sample = int(seconds * sr)
        if start_sample >= len(audio):
            return np.array([], dtype=audio.dtype)  # all removed
        return audio[start_sample:]
    else:
        raise TypeError("audio must be a numpy array")


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


def pad_audio(audio, max_len=MAX_LEN):
    if len(audio) >= max_len:
        return audio[:max_len]
    else:
        return np.pad(audio, (0, max_len - len(audio)), mode="constant")


def generator_dataset(base_path=DATASET_PATH, labels=labels):
    global training_count
    # original
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            training_count += 1
            yield pad_audio(audio, max_len=MAX_LEN), idx

            shift_noise = shift_audio(audio)
            training_count += 1
            yield pad_audio(shift_noise, max_len=MAX_LEN), idx

            stretch = stretch_audio(audio, rate=1.5)
            training_count += 1
            yield pad_audio(stretch, max_len=MAX_LEN), idx
    print("canhdt end first loop")
    # add white noise only
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            continue
        for f in files:
            audio = load_wav(str(f))
            noise = add_white_noise(audio, noise_factor=0.05)
            training_count += 1
            yield pad_audio(noise, max_len=MAX_LEN), idx

    # Remove first 3s and stretch rate=1.3
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = removeFirst(audio, seconds=3)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

            stretch = stretch_audio(removed, rate=1.3)
            training_count += 1
            yield pad_audio(stretch, max_len=MAX_LEN), idx

    # Remove first 1s and add white noise noise_factor=0.02
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = removeFirst(audio, seconds=1)
            removed = add_white_noise(removed, noise_factor=0.02)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Remove first 7s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = removeFirst(audio, seconds=7)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Remove first 4s and stretch rate=0.9,
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = removeFirst(audio, seconds=7)
            removed = stretch_audio(removed, rate=1.2)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Stretch 0.8
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = stretch_audio(audio, rate=0.8)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Stretch 0.9 and add white noise 0.01
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = stretch_audio(audio, rate=0.9)
            removed = add_white_noise(removed, noise_factor=0.01)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # pink noise 0.03
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_pink_noise(audio, amount=0.3)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Time mask 0.5s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = time_mask(audio, sr=16000, mask_duration=0.5)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Reverb decay=10 and remove first 2s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_reverb(audio, sr=16000, decay=10)
            removed = removeFirst(removed, seconds=2)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Time mask 0.5s again
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = time_mask(audio, sr=16000, mask_duration=0.5)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Time mask 0.2s 4 times
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = time_mask(audio, sr=16000, mask_duration=0.2)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

            removed = time_mask(removed, sr=16000, mask_duration=0.25)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

            removed = time_mask(removed, sr=16000, mask_duration=0.25)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Time mask 0.5s 4 times and remove 2s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = removeFirst(audio, seconds=2)
            removed = time_mask(removed, sr=16000, mask_duration=0.5)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx

    # Time mask 0.5s and add reverb 2
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = add_reverb(audio, sr=16000, decay=2)
            removed = time_mask(removed, sr=16000, mask_duration=0.5)
            training_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx


def build_dataset(base_path, labels):
    global training_count
    output_signature = (
        tf.TensorSpec(shape=(MAX_LEN,), dtype=tf.float32),
        tf.TensorSpec(shape=(), dtype=tf.int32),
    )
    return tf.data.Dataset.from_generator(
        generator_dataset, output_signature=output_signature
    )


valiadtion_count = 0


def generator(base_path=VALIDATE_PATH, labels=labels):
    global valiadtion_count
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
            yield pad_audio(audio, max_len=MAX_LEN), idx

            shift_noise = shift_audio(audio)
            valiadtion_count += 1
            yield pad_audio(shift_noise, max_len=MAX_LEN), idx

            stretch = stretch_audio(audio, rate=1.5)
            valiadtion_count += 1
            yield pad_audio(stretch, max_len=MAX_LEN), idx

    # add white noise
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            noise = add_white_noise(audio, noise_factor=0.1)
            valiadtion_count += 1
            yield pad_audio(noise, max_len=MAX_LEN), idx

    # Remove first 5s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            audio = load_wav(str(f))
            removed = removeFirst(audio, seconds=5)
            valiadtion_count += 1
            yield pad_audio(removed, max_len=MAX_LEN), idx


def build_validation_dataset(base_path, labels):
    global valiadtion_count

    output_signature = (
        tf.TensorSpec(shape=(MAX_LEN,), dtype=tf.float32),
        tf.TensorSpec(shape=(), dtype=tf.int32),
    )
    return tf.data.Dataset.from_generator(generator, output_signature=output_signature)


train_ds = (
    build_dataset(DATASET_PATH, labels)
    .batch(2)
    .prefetch(
        tf.data.AUTOTUNE,
    )
)
val_ds = (
    build_validation_dataset(VALIDATE_PATH, labels)
    .batch(2)
    .prefetch(
        tf.data.AUTOTUNE,
    )
)


# =========================
# Build model (Wav2Vec2 + classifier)
# =========================
def pad_waveform(batch_waveforms, max_len=MAX_LEN):
    return tf.keras.preprocessing.sequence.pad_sequences(
        batch_waveforms,
        maxlen=max_len,
        dtype="float32",
        padding="post",
        truncating="post",
    )


inputs = tf.keras.layers.Input(
    shape=(None,),
    dtype=tf.float32,
    name="waveform",
)
# Hugging Face model expects shape: (batch, seq_len)
x = tf.expand_dims(inputs, axis=0) if len(inputs.shape) == 1 else inputs
features = wav2vec2(x).last_hidden_state  # (batch, seq_len, hidden_size)
x = tf.reduce_mean(features, axis=1)  # mean pooling

x = tf.keras.layers.Dense(512, activation="relu")(x)
x = tf.keras.layers.Dense(128, activation="relu")(x)
x = tf.keras.layers.Dropout(0.3)(x)
outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

model = tf.keras.Model(inputs=inputs, outputs=outputs)

model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-5),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

model.summary()

# =========================
# Train
# =========================
history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=10,
)

# =========================
# Save
# =========================
print(f"canhdt training count: {training_count}")
print(f"canhdt validation count: {valiadtion_count}")
model.save(MODEL_PATH)
print(f"✅ Model saved to {MODEL_PATH}")
