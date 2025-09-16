from pathlib import Path

BASE_PATH = Path(__file__).parent
DATASET_PATH = BASE_PATH / "dataset/vietel"
VALIDATE_PATH = BASE_PATH / "dataset/validate"
training_count = 0
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


def build_dataset(base_path, labels):
    global training_count
    # all_embeddings, all_labels = [], []

    # original
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            continue
        for f in files:
            # audio = load_wav(str(f))
            # listen(audio)
            # input()
            # always keep original
            training_count += 1
            # all_embeddings.append(audio_to_embedding(audio))
            # all_labels.append(idx)

            # clone 2: shift
            # shift_noise = shift_audio(
            #     audio,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(shift_noise))
            # listen(shift_noise)
            # input()
            # all_labels.append(idx)

            # clone 3: stretch
            # max rate 1.5
            # stretch = stretch_audio(
            #     audio,
            #     rate=1.5,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(stretch))
            # # listen(stretch)
            # # input()
            # all_labels.append(idx)

    # add white noise only
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            continue
        for f in files:
            # audio = load_wav(str(f))
            # noise = add_white_noise(
            #     audio,
            #     noise_factor=0.05,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(noise))
            # all_labels.append(idx)

    # Remove first 3s and stretch rate=1.3
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = removeFirst(
            #     audio,
            #     seconds=3,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

            # stretch = stretch_audio(
            #     removed,
            #     rate=1.3,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(stretch))
            # # listen(stretch)
            # # input()
            # all_labels.append(idx)

    # Remove first 1s and add white noise noise_factor=0.02
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = removeFirst(
            #     audio,
            #     seconds=1,
            # )
            # removed = add_white_noise(
            #     removed,
            #     noise_factor=0.02,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # Remove first 7s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = removeFirst(
            #     audio,
            #     seconds=7,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # Remove first 4s and stretch rate=0.9,
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = removeFirst(
            #     audio,
            #     seconds=7,
            # )
            # removed = stretch_audio(
            #     removed,
            #     rate=1.2,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # Stretch 0.8
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = stretch_audio(
            #     audio,
            #     rate=0.8,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # Stretch 0.9 and add white noise 0.01
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = stretch_audio(
            #     audio,
            #     rate=0.9,
            # )
            # removed = add_white_noise(
            #     removed,
            #     noise_factor=0.01,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # pink noise 0.03
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = add_pink_noise(
            #     audio,
            #     amount=0.3,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # Time mask 0.5s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = time_mask(
            #     audio,
            #     sr=16000,
            #     mask_duration=0.5,
            # )
            # listen(removed)
            # input()
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # Reverb decay=10 and remove first 2s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = add_reverb(
            #     audio,
            #     sr=16000,
            #     decay=10,
            # )
            # removed = removeFirst(removed, seconds=2)
            # listen(removed)
            # input()
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

        # Time mask 0.5s

    # Time mask 0.5s again
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = time_mask(
            #     audio,
            #     sr=16000,
            #     mask_duration=0.5,
            # )
            # listen(removed)
            # input()
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

        # Time mask 0.5s again

    # Time mask 0.2s 4 times
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = time_mask(
            #     audio,
            #     sr=16000,
            #     mask_duration=0.2,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)
            # removed = time_mask(
            #     removed,
            #     sr=16000,
            #     mask_duration=0.25,
            # )
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)
            # removed = time_mask(
            #     removed,
            #     sr=16000,
            #     mask_duration=0.25,
            # )
            # listen(removed)
            # input()
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

        # Time mask 0.5s

    # Time mask 0.5s 4 times and remove 2s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = removeFirst(
            #     audio,
            #     seconds=2,
            # )
            # removed = time_mask(
            #     removed,
            #     sr=16000,
            #     mask_duration=0.5,
            # )
            # listen(removed)
            # input()
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

        # Time mask 0.5s 4 times and remove 2s

    # Time mask 0.5s and add reverb 2
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = add_reverb(
            #     audio,
            #     sr=16000,
            #     decay=2,
            # )
            # removed = time_mask(
            #     removed,
            #     sr=16000,
            #     mask_duration=0.5,
            # )
            # listen(removed)
            # input()
            training_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    print(f"canhdt training_count: {training_count}")


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
            # audio = load_wav(str(f))
            valiadtion_count += 1
            # all_embeddings.append(audio_to_embedding(audio))
            # all_labels.append(idx)

            # clone 2: shift
            # shift_noise = shift_audio(
            #     audio,
            # )
            valiadtion_count += 1
            # all_embeddings.append(audio_to_embedding(shift_noise))
            # all_labels.append(idx)

            # clone 3: stretch
            # max rate 1.5
            # stretch = stretch_audio(
            #     audio,
            #     rate=1.5,
            # )
            valiadtion_count += 1
            # all_embeddings.append(audio_to_embedding(stretch))
            # all_labels.append(idx)

    # add white noise
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # noise = add_white_noise(
            #     audio,
            #     noise_factor=0.1,
            # )
            valiadtion_count += 1
            # all_embeddings.append(audio_to_embedding(noise))
            # all_labels.append(idx)

    # Remove first 5s
    for idx, label in enumerate(labels):
        folder = base_path / label
        files = list(folder.glob("*.wav"))
        if not files:
            print(f"[WARN] No files found in {folder}")
            continue
        for f in files:
            # audio = load_wav(str(f))
            # removed = removeFirst(
            #     audio,
            #     seconds=5,
            # )
            valiadtion_count += 1
            # all_embeddings.append(audio_to_embedding(removed))
            # all_labels.append(idx)

    # X = tf.stack(all_embeddings)
    # y = tf.convert_to_tensor(all_labels, dtype=tf.int32)
    # return tf.data.Dataset.from_tensor_slices((X, y))
    print(f"canhdt valiadtion_count: {valiadtion_count}")


build_dataset(DATASET_PATH, labels)
build_validation_dataset(VALIDATE_PATH, labels)
