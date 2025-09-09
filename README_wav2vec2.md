# Wav2Vec2 Vietnamese Speech-to-Text

File test để chuyển đổi file WAV thành văn bản sử dụng mô hình **Wav2Vec2 Base Vietnamese-250h** từ Hugging Face.

## 🚀 Tính năng

- **Mô hình chuyên biệt**: Sử dụng mô hình được huấn luyện đặc biệt cho tiếng Việt
- **Xử lý audio thông minh**: Tự động chuyển đổi format, resample, normalize
- **Hỗ trợ GPU/CPU**: Tự động phát hiện và sử dụng GPU nếu có
- **Command line interface**: Dễ dàng sử dụng từ terminal
- **Demo mode**: Chạy trực tiếp để test với file có sẵn

## 📦 Cài đặt Dependencies

```bash
# Cài đặt tất cả dependencies
pip install -r requirements_wav2vec2.txt

# Hoặc cài đặt từng package
pip install torch torchaudio transformers
pip install librosa soundfile numpy scipy
pip install accelerate
```

## 🎯 Cách sử dụng

### 1. Chạy Demo (Không cần tham số)

```bash
python test_wav2vec2_vietnamese.py
```

Script sẽ tự động tìm file WAV trong thư mục hiện tại và chạy test.

### 2. Test với file WAV cụ thể

```bash
# Test cơ bản
python test_wav2vec2_vietnamese.py audio.wav

# Lưu kết quả vào file JSON
python test_wav2vec2_vietnamese.py audio.wav --output result.json

# Không lưu thông tin audio
python test_wav2vec2_vietnamese.py audio.wav --no-audio-info
```

### 3. Sử dụng trong code Python

```python
from test_wav2vec2_vietnamese import test_wav2vec2_vietnamese

# Test với file WAV
result = test_wav2vec2_vietnamese("audio.wav")

if result["success"]:
    print(f"Text: {result['text']}")
    print(f"Thời gian xử lý: {result['processing_time']:.2f}s")
else:
    print(f"Lỗi: {result['error']}")
```

## 🔧 Tham số Command Line

| Tham số | Mô tả | Ví dụ |
|---------|-------|-------|
| `wav_file` | Đường dẫn file WAV (bắt buộc) | `audio.wav` |
| `--output, -o` | File output JSON (tùy chọn) | `--output result.json` |
| `--no-audio-info` | Không lưu thông tin audio | `--no-audio-info` |

## 📊 Kết quả

Script trả về dictionary với các thông tin:

```python
{
    "success": True,
    "text": "Văn bản được nhận diện",
    "processing_time": 2.45,
    "model_name": "nguyenvulebinh/wav2vec2-base-vietnamese-250h",
    "device": "cuda",  # hoặc "cpu"
    "audio_duration": 5.23,
    "input_file": "audio.wav",
    "audio_info": {
        "file_size_mb": 0.85,
        "channels": 1,
        "sample_width_bits": 16,
        "sample_rate": 16000,
        "duration_seconds": 5.23
    },
    "test_timestamp": "2025-01-08 15:30:45"
}
```

## 🎵 Yêu cầu file Audio

- **Định dạng**: WAV
- **Sample rate**: Tự động resample về 16kHz
- **Channels**: Hỗ trợ mono và stereo (tự động chuyển về mono)
- **Bit depth**: Hỗ trợ 8-bit, 16-bit, 32-bit

## ⚡ Hiệu suất

- **Lần đầu chạy**: Cần tải mô hình (~500MB) - có thể mất 1-2 phút
- **Lần sau**: Chỉ cần load mô hình từ cache - nhanh hơn nhiều
- **GPU**: Tăng tốc đáng kể so với CPU
- **Memory**: Cần ít nhất 2GB RAM

## 🐛 Xử lý lỗi thường gặp

### 1. Lỗi "CUDA out of memory"
```bash
# Giảm batch size hoặc sử dụng CPU
export CUDA_VISIBLE_DEVICES=""
python test_wav2vec2_vietnamese.py audio.wav
```

### 2. Lỗi "Model not found"
```bash
# Kiểm tra kết nối internet
# Mô hình sẽ được tải tự động từ Hugging Face
```

### 3. Lỗi "Audio file corrupted"
```bash
# Kiểm tra file WAV có hợp lệ không
# Thử với file WAV khác
```

## 🔍 So sánh với các phương pháp khác

| Phương pháp | Độ chính xác | Tốc độ | Yêu cầu internet | Hỗ trợ tiếng Việt |
|-------------|--------------|--------|------------------|-------------------|
| **Wav2Vec2 Vietnamese** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ⭐⭐⭐⭐⭐ |
| Google Speech Recognition | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐ |
| OpenAI Whisper | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ⭐⭐⭐⭐ |
| Azure Speech | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐ |

## 📝 Ghi chú

- Mô hình được huấn luyện trên 250 giờ audio tiếng Việt
- Phù hợp nhất cho giọng nói tiếng Việt chuẩn
- Có thể xử lý được các accent và phương ngữ khác nhau
- Kết quả tốt nhất với audio chất lượng cao, ít nhiễu

## 🤝 Đóng góp

Nếu bạn muốn cải thiện script này, hãy:
1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push và tạo Pull Request

## 📄 License

Script này sử dụng mô hình Wav2Vec2 Vietnamese từ Hugging Face với license tương ứng.
