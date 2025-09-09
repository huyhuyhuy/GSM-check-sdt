#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test file để chuyển đổi file WAV thành text sử dụng Wav2Vec2 Base Vietnamese-250h
Mô hình: "nguyenvulebinh/wav2vec2-base-vietnamese-250h"

Cài đặt dependencies:
pip install transformers torch torchaudio librosa soundfile
pip install accelerate (để tăng tốc GPU)
"""

import os
import sys
import time
import json
import wave
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings("ignore")

# ==============================================================================
# IMPORTS VÀ KIỂM TRA DEPENDENCIES
# ==============================================================================

def check_dependencies():
    """Kiểm tra và cài đặt dependencies cần thiết"""
    required_packages = [
        "transformers",
        "torch", 
        "torchaudio",
        "librosa",
        "soundfile"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: Đã cài đặt")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}: Chưa cài đặt")
    
    if missing_packages:
        print(f"\n🚨 Cần cài đặt các package sau:")
        print(f"pip install {' '.join(missing_packages)}")
        print(f"pip install accelerate  # Để tăng tốc GPU")
        return False
    
    return True

# ==============================================================================
# WAV2VEC2 VIETNAMESE MODEL
# ==============================================================================

class Wav2Vec2VietnameseSTT:
    """
    Lớp xử lý Speech-to-Text sử dụng Wav2Vec2 Base Vietnamese-250h
    """
    
    def __init__(self, model_name: str = "nguyenvulebinh/wav2vec2-base-vietnamese-250h"):
        """
        Khởi tạo mô hình Wav2Vec2 Vietnamese
        
        Args:
            model_name: Tên mô hình từ Hugging Face
        """
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = None
        self.is_loaded = False
        
        print(f"🚀 Khởi tạo Wav2Vec2 Vietnamese STT...")
        print(f"📦 Model: {model_name}")
        
        # Kiểm tra GPU
        self._setup_device()
        
        # Load mô hình
        self._load_model()
    
    def _setup_device(self):
        """Thiết lập device (GPU/CPU)"""
        try:
            import torch
            if torch.cuda.is_available():
                self.device = "cuda"
                print(f"🎮 GPU detected: {torch.cuda.get_device_name(0)}")
                print(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            else:
                self.device = "cpu"
                print("💻 Sử dụng CPU")
        except ImportError:
            self.device = "cpu"
            print("💻 Sử dụng CPU (torch chưa cài đặt)")
    
    def _load_model(self):
        """Load mô hình và processor"""
        try:
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            
            print("📥 Đang tải mô hình Wav2Vec2 Vietnamese...")
            start_time = time.time()
            
            # Load processor
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_name)
            print("✅ Đã tải processor")
            
            # Load model
            self.model = Wav2Vec2ForCTC.from_pretrained(self.model_name)
            self.model.to(self.device)
            print("✅ Đã tải model")
            
            # Set model to evaluation mode
            self.model.eval()
            
            load_time = time.time() - start_time
            print(f"⏱️ Thời gian tải mô hình: {load_time:.2f}s")
            
            self.is_loaded = True
            
        except Exception as e:
            print(f"❌ Lỗi khi tải mô hình: {str(e)}")
            self.is_loaded = False
    
    def preprocess_audio(self, wav_file_path: str) -> Optional[np.ndarray]:
        """
        Tiền xử lý file WAV để phù hợp với mô hình
        
        Args:
            wav_file_path: Đường dẫn file WAV
            
        Returns:
            Audio array đã được xử lý
        """
        try:
            print(f"🔧 Đang tiền xử lý audio: {wav_file_path}")
            
            # Đọc file WAV
            with wave.open(wav_file_path, 'rb') as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                
                print(f"📊 Audio info: {channels} channels, {sample_width*8} bit, {sample_rate} Hz, {n_frames} frames")
                
                # Đọc raw audio data
                raw_audio = wf.readframes(n_frames)
            
            # Chuyển đổi bytes thành numpy array
            if sample_width == 2:  # 16-bit
                audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
            elif sample_width == 4:  # 32-bit
                audio = np.frombuffer(raw_audio, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:  # 8-bit
                audio = np.frombuffer(raw_audio, dtype=np.uint8).astype(np.float32) / 128.0
            
            # Chuyển stereo thành mono nếu cần
            if channels == 2:
                audio = audio.reshape(-1, 2).mean(axis=1)
                print("🔄 Chuyển stereo → mono")
            
            # Resample về 16kHz nếu cần (Wav2Vec2 yêu cầu 16kHz)
            if sample_rate != 16000:
                print(f"🔄 Resample: {sample_rate} Hz → 16000 Hz")
                import librosa
                audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=16000)
            
            # Normalize audio
            max_amp = np.max(np.abs(audio))
            if max_amp > 0:
                audio = audio / max_amp
            
            print(f"✅ Audio đã xử lý: {len(audio)} samples, {len(audio)/16000:.2f}s")
            print(f"🔍 Audio range: {audio.min():.6f} to {audio.max():.6f}")
            
            return audio
            
        except Exception as e:
            print(f"❌ Lỗi khi tiền xử lý audio: {str(e)}")
            return None
    
    def transcribe(self, wav_file_path: str) -> Dict:
        """
        Chuyển đổi file WAV thành text
        
        Args:
            wav_file_path: Đường dẫn file WAV
            
        Returns:
            Dict chứa kết quả transcription
        """
        if not self.is_loaded:
            return {
                "success": False,
                "error": "Mô hình chưa được tải",
                "text": None
            }
        
        if not os.path.exists(wav_file_path):
            return {
                "success": False,
                "error": f"File không tồn tại: {wav_file_path}",
                "text": None
            }
        
        try:
            start_time = time.time()
            
            # Tiền xử lý audio
            audio = self.preprocess_audio(wav_file_path)
            if audio is None:
                return {
                    "success": False,
                    "error": "Không thể tiền xử lý audio",
                    "text": None
                }
            
            # Chuyển đổi audio thành input format cho mô hình
            print("🎙️ Đang nhận diện với Wav2Vec2 Vietnamese...")
            
            # Sử dụng processor để chuẩn bị input
            inputs = self.processor(
                audio, 
                sampling_rate=16000, 
                return_tensors="pt", 
                padding=True
            )
            
            # Di chuyển input về device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Debug: In ra keys của inputs
            print(f"🔍 Input keys: {list(inputs.keys())}")
            
            # Inference - xử lý input format đúng cách
            with torch.no_grad():
                # Kiểm tra key đúng cho input
                if 'input_values' in inputs:
                    input_key = 'input_values'
                elif 'input_features' in inputs:
                    input_key = 'input_features'
                else:
                    # In ra tất cả keys để debug
                    print(f"🔍 Tất cả input keys: {list(inputs.keys())}")
                    # Sử dụng key đầu tiên
                    input_key = list(inputs.keys())[0]
                    print(f"🔍 Sử dụng key: {input_key}")
                
                logits = self.model(inputs[input_key]).logits
                
                # Decode logits thành text
                predicted_ids = torch.argmax(logits, dim=-1)
                transcription = self.processor.batch_decode(predicted_ids)
            
            processing_time = time.time() - start_time
            
            # Lấy text từ batch
            text = transcription[0] if transcription else ""
            
            print(f"✅ Transcription hoàn thành trong {processing_time:.2f}s")
            
            return {
                "success": True,
                "text": text.strip(),
                "processing_time": processing_time,
                "model_name": self.model_name,
                "device": self.device,
                "audio_duration": len(audio) / 16000,
                "confidence": None  # Wav2Vec2 không trả về confidence score
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi transcription: {str(e)}",
                "text": None
            }

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def analyze_audio_file(wav_file_path: str) -> Dict:
    """
    Phân tích thông tin file audio
    """
    try:
        with wave.open(wav_file_path, 'rb') as wf:
            info = {
                "file_path": wav_file_path,
                "file_size_mb": os.path.getsize(wav_file_path) / (1024 * 1024),
                "channels": wf.getnchannels(),
                "sample_width_bits": wf.getsampwidth() * 8,
                "sample_rate": wf.getframerate(),
                "duration_seconds": wf.getnframes() / wf.getframerate(),
                "total_frames": wf.getnframes()
            }
        return info
    except Exception as e:
        return {
            "file_path": wav_file_path,
            "error": str(e)
        }

def save_results(results: Dict, output_file: str):
    """
    Lưu kết quả vào file JSON
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu kết quả vào: {output_file}")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {str(e)}")

def print_results_summary(results: Dict):
    """
    In tóm tắt kết quả
    """
    print("\n" + "=" * 80)
    print("📋 TÓM TẮT KẾT QUẢ WAV2VEC2 VIETNAMESE STT")
    print("=" * 80)
    
    if results.get("success"):
        print(f"✅ Trạng thái: Thành công")
        print(f"📝 Text: {results.get('text', 'N/A')}")
        print(f"⏱️ Thời gian xử lý: {results.get('processing_time', 0):.2f}s")
        print(f"🎵 Thời lượng audio: {results.get('audio_duration', 0):.2f}s")
        print(f"🤖 Model: {results.get('model_name', 'N/A')}")
        print(f"💻 Device: {results.get('device', 'N/A')}")
    else:
        print(f"❌ Trạng thái: Thất bại")
        print(f"🚨 Lỗi: {results.get('error', 'N/A')}")
    
    print("=" * 80)

# ==============================================================================
# MAIN TEST FUNCTION
# ==============================================================================

def test_wav2vec2_vietnamese(wav_file_path: str, 
                             output_file: Optional[str] = None,
                             save_audio_info: bool = True) -> Dict:
    """
    Hàm chính để test Wav2Vec2 Vietnamese STT
    
    Args:
        wav_file_path: Đường dẫn file WAV
        output_file: File output JSON (tùy chọn)
        save_audio_info: Có lưu thông tin audio không
        
    Returns:
        Dict chứa kết quả STT
    """
    
    print("🎵 BẮT ĐẦU TEST WAV2VEC2 VIETNAMESE STT")
    print(f"📁 File: {wav_file_path}")
    print("=" * 80)
    
    # Kiểm tra dependencies
    if not check_dependencies():
        return {
            "success": False,
            "error": "Thiếu dependencies cần thiết"
        }
    
    # Kiểm tra file tồn tại
    if not os.path.exists(wav_file_path):
        return {
            "success": False,
            "error": f"File không tồn tại: {wav_file_path}"
        }
    
    # Kiểm tra định dạng file
    if not wav_file_path.lower().endswith('.wav'):
        return {
            "success": False,
            "error": "File phải có định dạng .wav"
        }
    
    try:
        # Phân tích file audio
        audio_info = None
        if save_audio_info:
            print("\n📊 PHÂN TÍCH FILE AUDIO:")
            audio_info = analyze_audio_file(wav_file_path)
            for key, value in audio_info.items():
                if key != "file_path":
                    print(f"   {key}: {value}")
        
        # Khởi tạo Wav2Vec2 Vietnamese STT
        print("\n🚀 KHỞI TẠO MÔ HÌNH:")
        stt_model = Wav2Vec2VietnameseSTT()
        
        if not stt_model.is_loaded:
            return {
                "success": False,
                "error": "Không thể tải mô hình Wav2Vec2 Vietnamese"
            }
        
        # Thực hiện transcription
        print("\n🎙️ THỰC HIỆN TRANSCRIPTION:")
        results = stt_model.transcribe(wav_file_path)
        
        # Thêm thông tin bổ sung
        results["input_file"] = wav_file_path
        results["audio_info"] = audio_info
        results["test_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # In kết quả
        print_results_summary(results)
        
        # Lưu kết quả nếu có yêu cầu
        if output_file:
            save_results(results, output_file)
        
        return results
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Lỗi không xác định: {str(e)}",
            "input_file": wav_file_path
        }
        print(f"❌ Lỗi: {str(e)}")
        return error_result

# ==============================================================================
# COMMAND LINE INTERFACE
# ==============================================================================

def main():
    """
    Command line interface để test Wav2Vec2 Vietnamese STT
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Wav2Vec2 Vietnamese Speech-to-Text với file WAV"
    )
    parser.add_argument("wav_file", help="Đường dẫn file WAV")
    parser.add_argument("--output", "-o", help="File output JSON (tùy chọn)")
    parser.add_argument("--no-audio-info", action="store_true", 
                       help="Không lưu thông tin audio")
    
    args = parser.parse_args()
    
    # Test Wav2Vec2 Vietnamese STT
    result = test_wav2vec2_vietnamese(
        args.wav_file,
        output_file=args.output,
        save_audio_info=not args.no_audio_info
    )
    
    # In kết quả chi tiết nếu không có output file
    if not args.output:
        print("\n📄 KẾT QUẢ CHI TIẾT:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

# ==============================================================================
# DEMO VÀ TEST
# ==============================================================================

def demo_with_sample_files():
    """
    Demo với các file WAV có sẵn trong dự án
    """
    print("🎬 DEMO WAV2VEC2 VIETNAMESE STT")
    print("=" * 80)
    
    # Tìm các file WAV trong dự án
    wav_files = []
    for ext in ['*.wav', '*.WAV']:
        wav_files.extend(Path('.').glob(ext))
    
    if not wav_files:
        print("❌ Không tìm thấy file WAV nào trong thư mục hiện tại")
        return
    
    print(f"📁 Tìm thấy {len(wav_files)} file WAV:")
    for i, wav_file in enumerate(wav_files, 1):
        print(f"   {i}. {wav_file}")
    
    # Test với file đầu tiên
    if wav_files:
        first_file = str(wav_files[0])
        print(f"\n🧪 Test với file: {first_file}")
        
        result = test_wav2vec2_vietnamese(first_file)
        
        if result.get("success"):
            print(f"\n🎉 Demo thành công!")
            print(f"📝 Text: {result.get('text')}")
        else:
            print(f"\n❌ Demo thất bại: {result.get('error')}")

if __name__ == "__main__":
    # Import torch ở đây để tránh lỗi khi chạy
    try:
        import torch
    except ImportError:
        print("❌ Cần cài đặt PyTorch: pip install torch torchaudio")
        sys.exit(1)
    
    # Test với command line arguments
    if len(sys.argv) > 1:
        main()
    else:
        # Demo mode
        print("🔧 DEMO MODE - Chạy trực tiếp")
        print("Để sử dụng command line:")
        print("python test_wav2vec2_vietnamese.py <file_wav> [--output <output.json>]")
        print("\nVí dụ:")
        print("python test_wav2vec2_vietnamese.py audio.wav")
        print("python test_wav2vec2_vietnamese.py audio.wav --output result.json")
        print("python test_wav2vec2_vietnamese.py audio.wav --no-audio-info")
        
        print("\n" + "=" * 80)
        
        # Chạy demo
        demo_with_sample_files()
