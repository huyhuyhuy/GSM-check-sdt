#!/usr/bin/env python3
"""
Batch Vietnamese speech-to-text using OpenAI Whisper API.
Reads all WAV files from folder and prints transcripts.
"""

import os
from pathlib import Path
import soundfile as sf
from openai import OpenAI

# === Hardcoded paths ===
BASE_PATH = Path(__file__).parent
WAV_FOLDER = BASE_PATH / "dataset/prepare_dataset"

# Init client
client = OpenAI(api_key="")


def transcribe_file_api(wav_path: Path, language="vi"):
    """Send audio file to Whisper API and return transcript"""
    with open(wav_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",  # or "whisper-1"
            file=f,
            language=language,
        )
    return transcript.text


if __name__ == "__main__":
    for fname in os.listdir(WAV_FOLDER):
        if fname.lower().endswith(".wav"):
            fpath = WAV_FOLDER / fname
            try:
                transcript = transcribe_file_api(fpath, language="vi")
                print(f"[{fname}] {transcript}")
            except Exception as e:
                print(f"[{fname}] ❌ Error: {e}")
