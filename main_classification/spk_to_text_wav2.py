# pip install vosk pydub torch transformers datasets soundfile librosa
# pip install git+https://github.com/openai/whisper.git


import os
import sys
import subprocess
from pathlib import Path
import time

import torch
import librosa
import soundfile as sf
from pydub import AudioSegment

from vosk import Model, KaldiRecognizer
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor


# -------------------- CONFIG --------------------
INPUT_FILE = "input.amr"   # file .amr hoặc .amr đầu vào
TEMP_WAV = "temp.wav"      # file wav tạm sau khi convert
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# -------------------- UTILS --------------------
def convert_to_wav(in_file, out_file):
    """Convert input audio (.amr/.amr) sang wav 16kHz mono"""
    audio = AudioSegment.from_file(in_file)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(out_file, format="wav")
    print(f"[INFO] Converted {in_file} -> {out_file}")


# --------------------  Wav2Vec2 --------------------
def transcribe_wav2vec2(wav_file):
    print("\n[Running Wav2Vec2]...")
    model_id = "nguyenvulebinh/wav2vec2-base-vietnamese-250h"
    processor = Wav2Vec2Processor.from_pretrained(model_id)
    model = Wav2Vec2ForCTC.from_pretrained(model_id).to(DEVICE)

    speech, rate = librosa.load(wav_file, sr=16000)
    input_values = processor(speech, return_tensors="pt", sampling_rate=16000).input_values.to(DEVICE)

    with torch.no_grad():
        logits = model(input_values).logits

    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.batch_decode(predicted_ids)
    return transcription[0]

# -------------------- MAIN --------------------
def main():
    # Danh sách 6 file .amr cần xử lý
    amr_files = [
        "input_khong_dung.amr",
        "input_loi_nhan.amr", 
        "input_nhac_cho.amr",
        "input_tam_khoa.amr",
        "input_thue_bao.amr",
        "input_tu_tu.amr"
    ]
    
    print(f"🎵 Sẽ xử lý {len(amr_files)} file:")
    for i, file in enumerate(amr_files, 1):
        print(f"  {i}. {file}")
    
    for i, file in enumerate(amr_files, 1):
        print(f"\n{'='*60}")
        print(f"🎵 [{i}/{len(amr_files)}] Xử lý file: {file}")
        print(f"{'='*60}")
        
        # Kiểm tra file có tồn tại không
        if not os.path.exists(file):
            print(f"❌ File {file} không tồn tại. Bỏ qua.")
            continue
            
        INPUT_FILE = file
        
        # Convert sang wav chuẩn
        start_time = time.time()
        convert_to_wav(INPUT_FILE, TEMP_WAV)
        end_time = time.time()
        print(f"Thời gian convert sang wav: {end_time - start_time:.2f}s")

        start_time = time.time()
        w2v_text = transcribe_wav2vec2(TEMP_WAV)
        print(">> Wav2Vec2:", w2v_text)
        end_time = time.time()
        print(f"Thời gian xử lý Wav2Vec2: {end_time - start_time:.2f}s")

    
    print(f"\n{'='*60}")
    print("🏁 Hoàn tất xử lý tất cả file!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
