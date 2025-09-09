#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test file để chuyển đổi file WAV thành text sử dụng Speech-to-Text (STT)
Phương pháp: Speech-to-Text (STT) - Chính xác nhất

Cài đặt dependencies:
pip install SpeechRecognition pydub openai-whisper
pip install azure-cognitiveservices-speech (nếu dùng Azure)
"""

import os
import sys
import time
import wave
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# ==============================================================================
# PHƯƠNG PHÁP 1: GOOGLE SPEECH RECOGNITION (MIỄN PHÍ)
# ==============================================================================

def google_speech_to_text(wav_file_path: str, language: str = "vi-VN") -> Dict:
    """
    Chuyển đổi WAV thành text sử dụng Google Speech Recognition
    Miễn phí, chính xác cao, cần internet
    """
    try:
        import speech_recognition as sr
        
        # Khởi tạo recognizer
        recognizer = sr.Recognizer()
        
        # Đọc file WAV
        with sr.AudioFile(wav_file_path) as source:
            print(f"🎵 Đang đọc file: {wav_file_path}")
            
            # Điều chỉnh noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Thu audio
            audio = recognizer.record(source)
            
            print("🔍 Đang nhận diện với Google Speech Recognition...")
            
            # Nhận diện speech
            text = recognizer.recognize_google(
                audio, 
                language=language,
                show_all=False  # Chỉ lấy kết quả tốt nhất
            )
            
            return {
                "method": "Google Speech Recognition",
                "success": True,
                "text": text,
                "confidence": None,  # Google không trả về confidence
                "language": language,
                "processing_time": None
            }
            
    except sr.UnknownValueError:
        return {
            "method": "Google Speech Recognition",
            "success": False,
            "error": "Không thể nhận diện được speech",
            "text": None,
            "confidence": None,
            "language": language
        }
    except sr.RequestError as e:
        return {
            "method": "Google Speech Recognition",
            "success": False,
            "error": f"Lỗi kết nối Google: {str(e)}",
            "text": None,
            "confidence": None,
            "language": language
        }
    except Exception as e:
        return {
            "method": "Google Speech Recognition",
            "success": False,
            "error": f"Lỗi không xác định: {str(e)}",
            "text": None,
            "confidence": None,
            "language": language
        }

# ==============================================================================
# PHƯƠNG PHÁP 2: OPENAI WHISPER (CHÍNH XÁC NHẤT)
# ==============================================================================
import whisper
import wave
import numpy as np
import resampy
def whisper_speech_to_text(wav_file_path: str, model_size: str = "small") -> Dict:
    try:

        wav_path = Path(wav_file_path).resolve()
        print(f"🎵 Đang tải Whisper model: {model_size}")
        print(f"📁 File path: {wav_path}")
        print(f"📁 File exists: {wav_path.exists()}")
        print(f" Current directory: {Path.cwd()}")

        if not wav_path.exists():
            return {
                "method": f"OpenAI Whisper ({model_size})",
                "success": False,
                "error": f"File không tồn tại: {wav_path}",
                "text": None,
                "confidence": None,
                "language": "vi"
            }

        # Đọc WAV
        print("📖 Đang đọc file WAV...")
        with wave.open(str(wav_path), 'rb') as wf:
            ch      = wf.getnchannels()
            sw      = wf.getsampwidth()
            sr      = wf.getframerate()
            n_fr    = wf.getnframes()
            print(f"📊 Audio info: {ch} channels, {sw*8} bit, {sr} Hz, {n_fr} frames")
            raw = wf.readframes(n_fr)

        # bytes → float32 array in [-1,1]
        if sw == 2:
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)/32768.0
        elif sw == 4:
            audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32)/2147483648.0
        else:
            audio = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)/128.0

        if ch == 2:
            audio = audio.reshape(-1,2).mean(axis=1)
            print("🔄 Chuyển stereo → mono")

        print(f"✅ Đã đọc audio: {len(audio)} samples, {len(audio)/sr:.2f}s")

        # Resample về 16k
        print("🔄 Đang resample về 16 kHz...")
        if sr != 16000:
            audio = resampy.resample(audio, sr, 16000)
            print(f"✅ Đã resample: {sr} -> 16000 Hz")
        else:
            print("✅ File đã 16 kHz")

        # Cast & normalize
        print("🔧 Đang cast và normalize audio...")
        audio = audio.astype(np.float32)
        max_amp = np.max(np.abs(audio))
        if max_amp > 0:
            audio /= max_amp
        print(f"🔍 Audio range: {audio.min():.6f} to {audio.max():.6f}")

        # Transcribe
        start = time.time()
        model = whisper.load_model("medium")
        print("🎙️ Đang nhận diện với Whisper...")
        result = model.transcribe(
            audio,
            language="vi",
            task="transcribe",
            verbose=False,
            no_speech_threshold=0.7,
            logprob_threshold=-1.0
        )
        print("✅ Whisper xử lý thành công!")

        return {
            "method": f"OpenAI Whisper ({model_size})",
            "success": True,
            "text": result["text"].strip(),
            "confidence": result.get("avg_logprob"),
            "language": result.get("language", "vi"),
            "processing_time": time.time() - start,
            "segments": result.get("segments", [])
        }

    except Exception as e:
        return {
            "method": f"OpenAI Whisper ({model_size})",
            "success": False,
            "error": f"Lỗi tổng quát: {e}",
            "text": None,
            "confidence": None,
            "language": "vi"
        }


# ==============================================================================
# PHƯƠNG PHÁP 3: AZURE SPEECH SERVICES (CHUYÊN NGHIỆP)
# ==============================================================================

def azure_speech_to_text(wav_file_path: str, subscription_key: str, region: str) -> Dict:
    """
    Chuyển đổi WAV thành text sử dụng Azure Speech Services
    Chuyên nghiệp, chính xác cao, có confidence score
    """
    try:
        import azure.cognitiveservices.speech as speechsdk
        
        # Cấu hình Azure Speech
        speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key, 
            region=region
        )
        speech_config.speech_recognition_language = "vi-VN"
        
        # Tạo audio config
        audio_config = speechsdk.AudioConfig(filename=wav_file_path)
        
        # Tạo speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, 
            audio_config=audio_config
        )
        
        print("🔍 Đang nhận diện với Azure Speech Services...")
        start_time = time.time()
        
        # Nhận diện speech
        result = speech_recognizer.recognize_once()
        
        processing_time = time.time() - start_time
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return {
                "method": "Azure Speech Services",
                "success": True,
                "text": result.text,
                "confidence": None,  # Azure không trả về confidence trực tiếp
                "language": "vi-VN",
                "processing_time": processing_time,
                "reason": str(result.reason)
            }
        else:
            return {
                "method": "Azure Speech Services",
                "success": False,
                "error": f"Không nhận diện được: {result.reason}",
                "text": None,
                "confidence": None,
                "language": "vi-VN"
            }
            
    except Exception as e:
        return {
            "method": "Azure Speech Services",
            "success": False,
            "error": f"Lỗi Azure: {str(e)}",
            "text": None,
            "confidence": None,
            "language": "vi-VN"
        }

# ==============================================================================
# PHƯƠNG PHÁP 4: HYBRID APPROACH - KẾT HỢP NHIỀU PHƯƠNG PHÁP
# ==============================================================================

def hybrid_speech_to_text(wav_file_path: str, 
                          use_google: bool = True,
                          use_whisper: bool = True,
                          use_azure: bool = False,
                          azure_key: str = "",
                          azure_region: str = "") -> Dict:
    """
    Kết hợp nhiều phương pháp STT để tăng độ chính xác
    """
    results = {}
    
    print("🚀 Bắt đầu Hybrid Speech-to-Text Analysis...")
    print("=" * 60)
    
    # 1. Google Speech Recognition
    if use_google:
        print("\n📱 Phương pháp 1: Google Speech Recognition")
        results['google'] = google_speech_to_text(wav_file_path)
        if results['google']['success']:
            print(f"✅ Kết quả: {results['google']['text']}")
        else:
            print(f"❌ Lỗi: {results['google']['error']}")
    
    # 2. OpenAI Whisper
    if use_whisper:
        print("\n🤖 Phương pháp 2: OpenAI Whisper")
        results['whisper'] = whisper_speech_to_text(wav_file_path, "small")
        if results['whisper']['success']:
            print(f"✅ Kết quả: {results['whisper']['text']}")
            print(f"⏱️ Thời gian xử lý: {results['whisper']['processing_time']:.2f}s")
        else:
            print(f"❌ Lỗi: {results['whisper']['error']}")
    
    # 3. Azure Speech Services
    if use_azure and azure_key and azure_region:
        print("\n☁️ Phương pháp 3: Azure Speech Services")
        results['azure'] = azure_speech_to_text(wav_file_path, azure_key, azure_region)
        if results['azure']['success']:
            print(f"✅ Kết quả: {results['azure']['text']}")
            print(f"⏱️ Thời gian xử lý: {results['azure']['processing_time']:.2f}s")
        else:
            print(f"❌ Lỗi: {results['azure']['error']}")
    
    # 4. Phân tích và quyết định kết quả cuối cùng
    print("\n" + "=" * 60)
    print("🎯 PHÂN TÍCH KẾT QUẢ CUỐI CÙNG")
    print("=" * 60)
    
    final_result = analyze_hybrid_results(results)
    
    return {
        "individual_results": results,
        "final_result": final_result,
        "summary": create_summary(results)
    }

def analyze_hybrid_results(results: Dict) -> Dict:
    """
    Phân tích kết quả từ nhiều phương pháp và đưa ra quyết định cuối cùng
    """
    successful_results = {}
    
    # Lọc các kết quả thành công
    for method, result in results.items():
        if result.get('success', False) and result.get('text'):
            successful_results[method] = result
    
    if not successful_results:
        return {
            "success": False,
            "error": "Không có phương pháp nào thành công",
            "text": None,
            "confidence": 0.0,
            "recommended_method": None
        }
    
    # Nếu chỉ có 1 kết quả thành công
    if len(successful_results) == 1:
        method, result = list(successful_results.items())[0]
        return {
            "success": True,
            "text": result['text'],
            "confidence": 0.8,  # Confidence cao vì chỉ có 1 kết quả
            "recommended_method": method,
            "single_result": True
        }
    
    # Nếu có nhiều kết quả thành công - so sánh và chọn tốt nhất
    print(f"📊 So sánh {len(successful_results)} phương pháp thành công:")
    
    best_result = None
    best_score = 0
    
    for method, result in successful_results.items():
        score = calculate_result_score(result)
        print(f"   {method}: {score:.2f} điểm")
        
        if score > best_score:
            best_score = score
            best_result = result
    
    # Kiểm tra độ tương đồng giữa các kết quả
    similarity_score = calculate_similarity_score(successful_results)
    
    return {
        "success": True,
        "text": best_result['text'],
        "confidence": min(0.95, best_score / 100),  # Normalize confidence
        "recommended_method": best_result['method'],
        "similarity_score": similarity_score,
        "all_texts": [r['text'] for r in successful_results.values()],
        "single_result": False
    }

def calculate_result_score(result: Dict) -> float:
    """
    Tính điểm cho kết quả dựa trên nhiều tiêu chí
    """
    score = 0
    
    # Điểm cơ bản
    score += 50
    
    # Điểm cho confidence (nếu có)
    if result.get('confidence') is not None:
        if result['confidence'] > 0.8:
            score += 20
        elif result['confidence'] > 0.6:
            score += 15
        elif result['confidence'] > 0.4:
            score += 10
    
    # Điểm cho processing time (nhanh hơn = tốt hơn)
    if result.get('processing_time'):
        if result['processing_time'] < 2.0:
            score += 15
        elif result['processing_time'] < 5.0:
            score += 10
        elif result['processing_time'] < 10.0:
            score += 5
    
    # Điểm cho method (Whisper thường chính xác nhất)
    if "Whisper" in result.get('method', ''):
        score += 10
    elif "Azure" in result.get('method', ''):
        score += 8
    elif "Google" in result.get('method', ''):
        score += 5
    
    return score

def calculate_similarity_score(results: Dict) -> float:
    """
    Tính độ tương đồng giữa các kết quả text
    """
    texts = [r['text'] for r in results.values()]
    
    if len(texts) < 2:
        return 1.0
    
    # So sánh từng cặp text
    total_similarity = 0
    comparisons = 0
    
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            similarity = text_similarity(texts[i], texts[j])
            total_similarity += similarity
            comparisons += 1
    
    return total_similarity / comparisons if comparisons > 0 else 0.0

def text_similarity(text1: str, text2: str) -> float:
    """
    Tính độ tương đồng giữa 2 text (đơn giản)
    """
    # Chuẩn hóa text
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    if text1 == text2:
        return 1.0
    
    # Tách thành từ
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def create_summary(results: Dict) -> str:
    """
    Tạo tóm tắt kết quả
    """
    successful_count = sum(1 for r in results.values() if r.get('success', False))
    total_count = len(results)
    
    summary = f"""
📋 TÓM TẮT KẾT QUẢ:
   • Tổng phương pháp: {total_count}
   • Thành công: {successful_count}
   • Tỷ lệ thành công: {(successful_count/total_count)*100:.1f}%
"""
    
    for method, result in results.items():
        status = "✅" if result.get('success', False) else "❌"
        text_preview = result.get('text', '')[:50] + "..." if result.get('text') else "N/A"
        summary += f"   • {method}: {status} {text_preview}\n"
    
    return summary

# ==============================================================================
# MAIN FUNCTION - TEST STT
# ==============================================================================

def test_speech_to_text(wav_file_path: str, 
                        method: str = "hybrid",
                        azure_key: str = "",
                        azure_region: str = "") -> Dict:
    """
    Hàm chính để test Speech-to-Text
    
    Args:
        wav_file_path: Đường dẫn file WAV
        method: "google", "whisper", "azure", "hybrid"
        azure_key: Azure subscription key (nếu dùng Azure)
        azure_region: Azure region (nếu dùng Azure)
    
    Returns:
        Dict chứa kết quả STT
    """
    
    # Kiểm tra file tồn tại
    if not os.path.exists(wav_file_path):
        return {
            "error": f"File không tồn tại: {wav_file_path}",
            "success": False
        }
    
    # Kiểm tra định dạng file
    if not wav_file_path.lower().endswith('.wav'):
        return {
            "error": "File phải có định dạng .wav",
            "success": False
        }
    
    print(f"🎵 BẮT ĐẦU TEST SPEECH-TO-TEXT")
    print(f"📁 File: {wav_file_path}")
    print(f"🔧 Phương pháp: {method}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        if method == "google":
            result = google_speech_to_text(wav_file_path)
        elif method == "whisper":
            result = whisper_speech_to_text(wav_file_path)
        elif method == "azure":
            if not azure_key or not azure_region:
                return {
                    "error": "Cần Azure key và region để sử dụng Azure Speech",
                    "success": False
                }
            result = azure_speech_to_text(wav_file_path, azure_key, azure_region)
        elif method == "hybrid":
            result = hybrid_speech_to_text(
                wav_file_path,
                use_google=True,
                use_whisper=True,
                use_azure=bool(azure_key and azure_region),
                azure_key=azure_key,
                azure_region=azure_region
            )
        else:
            return {
                "error": f"Phương pháp không hợp lệ: {method}",
                "success": False
            }
        
        total_time = time.time() - start_time
        
        # Thêm thông tin tổng quan
        if isinstance(result, dict) and 'final_result' in result:
            # Hybrid result
            result['total_processing_time'] = total_time
            result['input_file'] = wav_file_path
        else:
            # Single method result
            result['total_processing_time'] = total_time
            result['input_file'] = wav_file_path
        
        print(f"\n⏱️ Tổng thời gian xử lý: {total_time:.2f}s")
        print("🎉 HOÀN THÀNH TEST STT!")
        
        return result
        
    except Exception as e:
        return {
            "error": f"Lỗi không xác định: {str(e)}",
            "success": False,
            "input_file": wav_file_path
        }

# ==============================================================================
# COMMAND LINE INTERFACE
# ==============================================================================

def main():
    """
    Command line interface để test STT
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Speech-to-Text với file WAV")
    parser.add_argument("wav_file", help="Đường dẫn file WAV")
    parser.add_argument("--method", choices=["google", "whisper", "azure", "hybrid"], 
                       default="hybrid", help="Phương pháp STT")
    parser.add_argument("--azure-key", help="Azure subscription key")
    parser.add_argument("--azure-region", help="Azure region")
    parser.add_argument("--output", help="File output JSON (tùy chọn)")
    
    args = parser.parse_args()
    
    # Test STT
    result = test_speech_to_text(
        args.wav_file,
        method=args.method,
        azure_key=args.azure_key or "",
        azure_region=args.azure_region or ""
    )
    
    # In kết quả
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Đã lưu kết quả vào: {args.output}")
    else:
        print("\n📄 KẾT QUẢ CHI TIẾT:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # Test với file cụ thể nếu chạy trực tiếp
    if len(sys.argv) == 1:
        print("🔧 TEST MODE - Chạy trực tiếp")
        print("Để sử dụng command line:")
        print("python test_stt_audio.py <file_wav> --method <method>")
        print("\nVí dụ:")
        print("python test_stt_audio.py audio.wav --method hybrid")
        print("python test_stt_audio.py audio.wav --method whisper")
        print("python test_stt_audio.py audio.wav --method google")
    else:
        main()
