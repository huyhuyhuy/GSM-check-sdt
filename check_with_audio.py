import pyaudio
import wave
import time
import numpy as np
from datetime import datetime
import os

# MFCC imports
try:
    import librosa
    import librosa.feature
    from scipy.signal import butter, filtfilt
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("⚠️ librosa không có sẵn. Cài đặt bằng: pip install librosa")

try:
    from fastdtw import fastdtw
    from scipy.spatial.distance import euclidean
    DTW_AVAILABLE = True
except ImportError:
    DTW_AVAILABLE = False

def record_audio():
    """
    Thu âm 20 giây từ cổng line-in và lưu thành file WAV
    """
    # Thiết lập các thông số thu âm
    CHUNK = 1024  # Kích thước buffer
    FORMAT = pyaudio.paInt16  # 16-bit audio
    CHANNELS = 2  # Stereo
    RATE = 44100  # Sample rate 44.1kHz
    RECORD_SECONDS = 20  # Thu âm 20 giây
    
    # Tạo tên file với timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    WAVE_OUTPUT_FILENAME = f"recorded_audio_{timestamp}.wav"
    
    # Khởi tạo PyAudio
    p = pyaudio.PyAudio()
    
    try:
        print("Bắt đầu thu âm...")
        print("Đang thu âm trong 20 giây...")
        
        # Mở stream để thu âm
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        frames = []
        
        # Thu âm trong 20 giây
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)
            
            # Hiển thị tiến trình
            if i % (int(RATE / CHUNK)) == 0:
                remaining = RECORD_SECONDS - (i // int(RATE / CHUNK))
                print(f"Còn lại: {remaining} giây...")
        
        print("Hoàn thành thu âm!")
        
        # Đóng stream
        stream.stop_stream()
        stream.close()
        
        # Lưu file WAV
        print(f"Đang lưu file: {WAVE_OUTPUT_FILENAME}")
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"File âm thanh đã được lưu: {WAVE_OUTPUT_FILENAME}")
        
    except Exception as e:
        print(f"Lỗi khi thu âm: {e}")
        print("Kiểm tra:")
        print("1. Microphone/Line-in có được kết nối không?")
        print("2. Có cài đặt pyaudio không? (pip install pyaudio)")
        
    finally:
        # Đóng PyAudio
        p.terminate()

def read_wav_file(filename):
    """
    Đọc file WAV và trả về dữ liệu âm thanh
    """
    try:
        with wave.open(filename, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16)
            
            # Nếu là stereo, chuyển thành mono bằng cách lấy trung bình
            if wf.getnchannels() == 2:
                audio_data = audio_data.reshape(-1, 2)
                audio_data = np.mean(audio_data, axis=1)
            
            return audio_data, wf.getframerate()
    except Exception as e:
        print(f"Lỗi đọc file {filename}: {e}")
        return None, None

def resample_and_normalize_audio(audio_data, current_rate, target_rate=44100):
    """
    Resample và normalize audio data
    """
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Simple resampling (linear interpolation)
    if current_rate != target_rate:
        duration = len(audio_data) / current_rate
        new_length = int(duration * target_rate)
        audio_data = np.interp(
            np.linspace(0, len(audio_data), new_length),
            np.arange(len(audio_data)),
            audio_data
        )
    
    # Convert to float and normalize
    audio_data = audio_data.astype(np.float64)
    audio_data = audio_data - np.mean(audio_data)  # Remove DC offset
    
    # Normalize volume
    if np.std(audio_data) > 0:
        audio_data = audio_data / np.std(audio_data)
    
    return audio_data, target_rate

def extract_noise_profile(audio_data, sample_rate, noise_duration=2.0):
    """
    Extract noise profile từ đoạn đầu file (chỉ có "eee...eee")
    """
    noise_samples = int(noise_duration * sample_rate)
    if len(audio_data) < noise_samples:
        noise_samples = len(audio_data) // 2
    
    noise_segment = audio_data[:noise_samples]
    
    # Tính power spectrum của noise
    noise_stft = librosa.stft(noise_segment, n_fft=2048, hop_length=512)
    noise_magnitude = np.abs(noise_stft)
    noise_power = noise_magnitude ** 2
    
    # Average power spectrum (noise profile)
    noise_profile = np.mean(noise_power, axis=1)
    
    print(f"   🔧 Noise profile extracted từ {noise_duration}s đầu ({noise_samples} samples)")
    return noise_profile

def spectral_subtraction(audio_data, noise_profile, sample_rate, alpha=2.0, beta=0.01):
    """
    Spectral subtraction sử dụng noise profile ước tính
    """
    try:
        # STFT of input signal
        stft = librosa.stft(audio_data, n_fft=2048, hop_length=512)
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        power = magnitude ** 2
        
        # Expand noise profile to match STFT frames
        noise_power_expanded = noise_profile[:, np.newaxis]
        
        # Spectral subtraction
        clean_power = power - alpha * noise_power_expanded
        
        # Ensure non-negative power với floor (beta * original power)
        floor = beta * power
        clean_power = np.maximum(clean_power, floor)
        
        # Reconstruct magnitude và combine với original phase
        clean_magnitude = np.sqrt(clean_power)
        clean_stft = clean_magnitude * np.exp(1j * phase)
        
        # ISTFT to get clean audio
        clean_audio = librosa.istft(clean_stft, hop_length=512)
        
        print(f"   🔧 Spectral subtraction applied (α={alpha}, β={beta})")
        return clean_audio
        
    except Exception as e:
        print(f"   ⚠️ Spectral subtraction failed: {e}")
        return audio_data

def bandpass_filter_speech(audio_data, sample_rate, low_freq=100, high_freq=3800):
    """
    Bandpass filter để chỉ giữ speech frequency range
    """
    try:
        # Thiết kế bandpass filter cho speech (100-3800Hz)
        nyquist = sample_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        # Butterworth bandpass filter
        b, a = butter(4, [low, high], btype='band')
        filtered_audio = filtfilt(b, a, audio_data)
        
        print(f"   🔧 Bandpass filter: {low_freq}-{high_freq}Hz (speech range)")
        
        return filtered_audio
        
    except Exception as e:
        print(f"   ⚠️ Bandpass filter failed: {e}, sử dụng audio gốc")
        return audio_data

def professional_preprocessing(audio_data, sample_rate, target_sr=16000, 
                              noise_duration=2.0, apply_noise_reduction=True):
    """
    Professional preprocessing pipeline theo đúng chuẩn speech processing
    """
    processed_audio = audio_data.copy()
    
    # 1. Resample về 16kHz (optimal cho speech)
    if sample_rate != target_sr:
        processed_audio = librosa.resample(processed_audio, orig_sr=sample_rate, target_sr=target_sr)
        print(f"   🔧 Resampled: {sample_rate}Hz → {target_sr}Hz")
        sample_rate = target_sr
    
    # 2. Amplitude normalization
    if np.max(np.abs(processed_audio)) > 0:
        processed_audio = processed_audio / np.max(np.abs(processed_audio))
    
    # 3. Pre-emphasis filter (0.97) - quan trọng cho speech
    processed_audio = librosa.effects.preemphasis(processed_audio, coef=0.97)
    print(f"   🔧 Pre-emphasis applied (coef=0.97)")
    
    if apply_noise_reduction:
        # 4. Extract noise profile từ đoạn đầu
        noise_profile = extract_noise_profile(processed_audio, sample_rate, noise_duration)
        
        # 5. Spectral subtraction
        processed_audio = spectral_subtraction(processed_audio, noise_profile, sample_rate)
        
        # 6. Bandpass filter 100-3800Hz (optimal cho speech)
        processed_audio = bandpass_filter_speech(processed_audio, sample_rate, 
                                               low_freq=100, high_freq=3800)
    
    return processed_audio, sample_rate

def professional_mfcc_extraction(audio_data, sample_rate, apply_noise_reduction=True):
    """
    Professional MFCC extraction theo chuẩn công nghiệp
    - 20 MFCC coefficients
    - 25ms frame, 10ms hop
    - Delta + Delta-Delta features  
    - CMVN normalization
    """
    if not LIBROSA_AVAILABLE:
        raise ImportError("librosa is required for professional MFCC extraction")
    
    try:
        # 1. Professional preprocessing
        processed_audio, final_sr = professional_preprocessing(
            audio_data, sample_rate, apply_noise_reduction=apply_noise_reduction
        )
        
        # 2. Optimal MFCC parameters cho speech
        frame_length = int(0.025 * final_sr)  # 25ms frame
        hop_length = int(0.01 * final_sr)     # 10ms hop
        n_mfcc = 20                           # 20 coefficients
        
        print(f"   📊 MFCC params: {n_mfcc} coeffs, {frame_length} frame, {hop_length} hop")
        
        # 3. Extract MFCC features
        mfcc = librosa.feature.mfcc(
            y=processed_audio.astype(np.float32),
            sr=final_sr,
            n_mfcc=n_mfcc,
            n_fft=frame_length * 2,  # Thường gấp đôi frame length
            hop_length=hop_length,
            window='hamming',
            center=True
        )
        
        # 4. Delta features (tốc độ thay đổi)
        delta_mfcc = librosa.feature.delta(mfcc, order=1)
        
        # 5. Delta-Delta features (gia tốc)
        delta2_mfcc = librosa.feature.delta(mfcc, order=2)
        
        # 6. Combine all features
        all_features = np.vstack([mfcc, delta_mfcc, delta2_mfcc])  # Shape: (60, time_frames)
        
        # 7. CMVN normalization (cực kỳ quan trọng cho noise robustness!)
        # Cepstral Mean and Variance Normalization
        mean_norm = np.mean(all_features, axis=1, keepdims=True)
        std_norm = np.std(all_features, axis=1, keepdims=True) + 1e-8  # Tránh division by zero
        
        cmvn_features = (all_features - mean_norm) / std_norm
        
        # 8. Transpose để có shape (time_frames, feature_dims)
        final_features = cmvn_features.T
        
        print(f"   📊 Professional MFCC shape: {final_features.shape}")
        print(f"       ├─ MFCC: {n_mfcc} coeffs")
        print(f"       ├─ Delta: {n_mfcc} coeffs") 
        print(f"       ├─ Delta²: {n_mfcc} coeffs")
        print(f"       └─ CMVN normalized: ✅")
        
        return final_features
        
    except Exception as e:
        print(f"   ❌ Professional MFCC extraction failed: {e}")
        return None

def compute_dtw_distance(mfcc1, mfcc2):
    """
    Tính khoảng cách DTW giữa 2 chuỗi MFCC
    """
    if not DTW_AVAILABLE:
        # Fallback: sử dụng Euclidean distance đơn giản
        min_len = min(len(mfcc1), len(mfcc2))
        mfcc1_crop = mfcc1[:min_len]
        mfcc2_crop = mfcc2[:min_len]
        
        distances = [euclidean(f1, f2) for f1, f2 in zip(mfcc1_crop, mfcc2_crop)]
        return np.mean(distances)
    
    try:
        # Sử dụng FastDTW với euclidean distance
        distance, path = fastdtw(mfcc1, mfcc2, dist=euclidean)
        
        # Normalize distance bởi chiều dài chuỗi
        normalized_distance = distance / len(path)
        
        return normalized_distance
        
    except Exception as e:
        print(f"Lỗi khi tính DTW: {e}")
        # Fallback
        min_len = min(len(mfcc1), len(mfcc2))
        mfcc1_crop = mfcc1[:min_len]
        mfcc2_crop = mfcc2[:min_len]
        distances = [euclidean(f1, f2) for f1, f2 in zip(mfcc1_crop, mfcc2_crop)]
        return np.mean(distances)

def mfcc_sliding_window_match(template_3s, check_file_audio, sample_rate, distance_threshold=15.0, use_enhanced=True):
    """
    Trượt cửa sổ 3s template (MFCC) qua file check để tìm match tốt nhất
    Sử dụng Professional MFCC + DTW distance với noise reduction
    """
    if not LIBROSA_AVAILABLE:
        print("❌ Cần cài đặt librosa để sử dụng MFCC!")
        return float('inf'), 0
    
    window_size = len(template_3s)  # 3s template
    step_size = sample_rate // 10  # 0.1s step
    
    best_distance = float('inf')
    best_position = 0
    total_comparisons = 0
    valid_comparisons = 0
    
    method_name = "Professional MFCC Pipeline"
    print(f"🎵 {method_name} Sliding Window (3s template)...")
    print(f"   Template length: {len(template_3s)} samples")
    print(f"   Check file length: {len(check_file_audio)} samples")
    print(f"   Distance threshold: {distance_threshold}")
    
    # Extract MFCC cho template
    print(f"   🔧 Extracting {method_name} cho template...")
    
    template_mfcc = professional_mfcc_extraction(template_3s, sample_rate, apply_noise_reduction=True)
    
    if template_mfcc is None:
        print("   ❌ Không thể extract MFCC cho template!")
        return float('inf'), 0
    
    print(f"   📊 Template MFCC shape: {template_mfcc.shape}")
    
    # Scan với sliding window
    for i in range(0, len(check_file_audio) - window_size + 1, step_size):
        total_comparisons += 1
        
        # Lấy đoạn 3s từ file check
        check_segment = check_file_audio[i:i+window_size]
        
        # Skip nếu segment quá yên tĩnh
        segment_rms = np.sqrt(np.mean(check_segment**2))
        if segment_rms < 0.1:  # Threshold cho normalized data
            continue
        
        # Extract MFCC cho segment
        check_mfcc = professional_mfcc_extraction(check_segment, sample_rate, apply_noise_reduction=True)
        
        if check_mfcc is None:
            continue
            
        valid_comparisons += 1
        
        # Tính DTW distance
        try:
            dtw_distance = compute_dtw_distance(template_mfcc, check_mfcc)
            
            if dtw_distance < best_distance:
                best_distance = dtw_distance
                best_position = i / sample_rate
                
                if dtw_distance < distance_threshold * 1.5:  # Show progress
                    print(f"   📈 Good match: DTW={dtw_distance:.2f} at {best_position:.1f}s")
                
        except Exception as e:
            print(f"   ⚠️ Error at position {i/sample_rate:.1f}s: {e}")
            continue
    
    print(f"   ✅ Scan complete. Best DTW distance: {best_distance:.2f} at {best_position:.1f}s")
    print(f"   📊 Stats: {total_comparisons} total, {valid_comparisons} valid")
    
    return best_distance, best_position

def find_best_template_mfcc_match_enhanced(check_file, distance_threshold=15.0, skip_seconds=0):
    """
    Streamlined version - auto sử dụng Professional MFCC pipeline
    Chỉ check 2 templates chính: THUE BAO và SO KHONG DUNG
    """
    if not LIBROSA_AVAILABLE:
        print("❌ Cần cài đặt librosa để sử dụng MFCC!")
        print("   Chạy: pip install librosa")
        return None
    
    print(f"\n🎵 TÌM TEMPLATE KHỚP NHẤT (Professional MFCC + DTW)")
    print("🔧 Professional Pipeline: 16kHz+Pre-emphasis+Noise profile+CMVN")
    print(f"File cần check: {check_file}")
    print("="*60)
    
    # Chỉ check 2 templates chính
    templates = {
        "THUE BAO": "template_thue_bao_ok.wav",
        "SO KHONG DUNG": "template_so_khong_dung_ok.wav"
    }
    
    print(f"📋 Templates: {', '.join(templates.keys())}")
    
    # Đọc file cần check
    check_audio, check_rate = read_wav_file(check_file)
    if check_audio is None:
        print(f"❌ Không thể đọc file: {check_file}")
        return None
    
    print(f"📂 File check: {len(check_audio)} samples, {check_rate}Hz")
    
    # Chuẩn bị file check
    check_audio_norm, target_rate = resample_and_normalize_audio(check_audio, check_rate)
    
    # Skip N giây đầu nếu được yêu cầu
    if skip_seconds > 0:
        skip_samples = int(skip_seconds * target_rate)
        if skip_samples < len(check_audio_norm):
            check_audio_norm = check_audio_norm[skip_samples:]
            print(f"   ✂️ Đã bỏ qua {skip_seconds}s đầu ({skip_samples} samples)")
            print(f"   Sau skip: {len(check_audio_norm)} samples, {target_rate}Hz")
        else:
            print(f"   ⚠️ Không thể skip {skip_seconds}s - file quá ngắn!")
    else:
        print(f"   Sau normalize: {len(check_audio_norm)} samples, {target_rate}Hz")
    
    results = {}
    
    # Kiểm tra từng template 
    for template_name, template_file in templates.items():
        if not os.path.exists(template_file):
            print(f"\n⚠️ Không tìm thấy: {template_file}")
            continue
            
        print(f"\n🎵 KIỂM TRA TEMPLATE: {template_name}")
        print("-" * 40)
        
        # Đọc template
        template_audio, template_rate = read_wav_file(template_file)
        if template_audio is None:
            print(f"❌ Không thể đọc template: {template_file}")
            continue
        
        print(f"📂 Template: {len(template_audio)} samples, {template_rate}Hz")
        
        # Chuẩn bị template (resample + normalize)
        template_norm, _ = resample_and_normalize_audio(template_audio, template_rate, target_rate)
        
        # DEBUG: Template stats
        orig_rms = np.sqrt(np.mean(template_norm**2))
        print(f"   📊 Template RMS sau normalize: {orig_rms:.3f}")
        
        # Lấy 3s đầu template
        window_3s = target_rate * 3
        template_3s = template_norm[:min(window_3s, len(template_norm))]
        
        actual_duration = len(template_3s) / target_rate
        print(f"   ✂️ Sử dụng {actual_duration:.1f}s đầu template ({len(template_3s)} samples)")
        
        # MFCC sliding window match
        distance, position = mfcc_sliding_window_match(
            template_3s, check_audio_norm, target_rate, distance_threshold, use_enhanced=True
        )
        
        # Convert distance to similarity score với adaptive scaling
        if distance == float('inf'):
            similarity_score = 0.0
        else:
            # Adaptive scaling dựa trên enhanced features
            if distance < 8.0:      # Excellent match
                similarity_score = 0.95 + (8.0 - distance) * 0.005  # 0.95-1.0
            elif distance < 15.0:   # Good match  
                similarity_score = 0.8 + (15.0 - distance) * 0.015 / 7.0  # 0.8-0.95
            elif distance < 25.0:   # Fair match
                similarity_score = 0.5 + (25.0 - distance) * 0.3 / 10.0   # 0.5-0.8
            else:                   # Poor match
                similarity_score = max(0, 0.5 - (distance - 25.0) * 0.02)  # 0-0.5
        
        results[template_name] = {
            'distance': distance,
            'similarity': similarity_score,
            'position': position,
        }
        
        print(f"   🎯 Kết quả: DTW distance={distance:.2f}, similarity={similarity_score:.3f} (tại {position:.1f}s)")
    
    # Tổng kết kết quả
    print("\n" + "="*60)
    print(f"📊 TỔNG KẾT KẾT QUẢ (Professional MFCC + DTW):")
    print("="*60)
    
    if not results:
        print("❌ Không có template nào được xử lý thành công")
        return None
    
    # Sắp xếp theo distance (thấp nhất = tốt nhất)
    sorted_results = sorted(results.items(), key=lambda x: x[1]['distance'])
    
    for i, (name, data) in enumerate(sorted_results):
        icon = "🥇" if i == 0 else "🥈"
        distance = data['distance']
        similarity = data['similarity']
        if distance == float('inf'):
            print(f"{icon} {name}: DTW=∞ (không tính được)")
        else:
            print(f"{icon} {name}: DTW={distance:.2f} Sim={similarity:.3f} (tại {data['position']:.1f}s)")
    
    # Xác định kết quả cuối cùng
    best_template, best_data = sorted_results[0]
    best_distance = best_data['distance']
    best_similarity = best_data['similarity']
    
    print(f"\n🎯 TEMPLATE KHỚP NHẤT: {best_template}")
    print(f"📈 DTW Distance: {best_distance:.2f}")
    print(f"📈 Similarity Score: {best_similarity:.3f} ({best_similarity*100:.1f}%)")
    print(f"📍 Vị trí khớp: {best_data['position']:.1f}s")
    
    # Logic: DTW > 9.3 thì trả về HOAT DONG
    dtw_threshold = 9.3
    
    # Đánh giá độ tin cậy
    if best_distance == float('inf'):
        print(f"❌ KHÔNG THỂ TÍNH TOÁN - Lỗi MFCC extraction")
        final_result = "ERROR - MFCC_FAILED"
    elif best_distance <= dtw_threshold:
        print(f"✅ KẾT QUẢ TIN CẬY (DTW ≤ {dtw_threshold})")
        final_result = best_template
    else:
        print(f"⚠️ DTW > {dtw_threshold} → PHÂN LOẠI LÀ HOẠT ĐỘNG")
        final_result = "HOAT DONG"
    
    print("="*60)
    print(f"\n🎯 KẾT QUẢ CUỐI CÙNG: {final_result}")
    return final_result

def main_menu():
    """
    Menu chính - Chỉ Option 1 và 7
    """
    # Kiểm tra template files
    templates = [
        "template_thue_bao_ok.wav",
        "template_so_khong_dung_ok.wav"
    ]
    
    print("=== THU ÂM VÀ SO SÁNH ÂM THANH ===")
    print("1. Thu âm mới")
    print("7. 🎵 Tìm template khớp nhất (Professional MFCC + DTW)")
    print("0. Thoát")
    
    choice = input("\nChọn chức năng (1, 7, 0): ").strip()
    
    if choice == "1":
        record_audio()
        
    elif choice == "7":
        # Kiểm tra template files
        missing_templates = [t for t in templates if not os.path.exists(t)]
        if missing_templates:
            print("⚠️ Thiếu các template files:")
            for template in missing_templates:
                print(f"   - {template}")
            print("Vui lòng đảm bảo có đủ 2 template files!")
            return
        
        # Kiểm tra dependencies
        if not LIBROSA_AVAILABLE:
            print("❌ Thiếu thư viện librosa!")
            print("   Cài đặt bằng: pip install librosa")
            return
        
        if not DTW_AVAILABLE:
            print("⚠️ Thiếu thư viện fastdtw (sẽ dùng fallback method)")
            print("   Để có hiệu suất tốt nhất, cài đặt: pip install fastdtw")
        
        print("🎵 TÌM TEMPLATE KHỚP NHẤT (Professional MFCC + DTW)")
        print("Phương pháp: Professional speech processing pipeline + DTW distance")
        print("📋 Template files:")
        print("   - THUE BAO: template_thue_bao_ok.wav")
        print("   - SO KHONG DUNG: template_so_khong_dung_ok.wav") 
        print("\n🔧 PROFESSIONAL PIPELINE (tự động):")
        print("   ✅ Resample 16kHz + Pre-emphasis (0.97)")
        print("   ✅ Noise profile estimation từ đoạn đầu")
        print("   ✅ Spectral subtraction + Bandpass 100-3800Hz")
        print("   ✅ 20 MFCC + Delta + Delta² (60 features)")
        print("   ✅ CMVN normalization (noise robust)")
        print("   ✅ DTW matching với optimal parameters")
        print("   ✅ Frame 25ms, Hop 10ms (chuẩn speech)")
        
        # Nhập tên file cần kiểm tra
        input_filename = input("\nNhập tên file âm thanh cần check (VD: recorded_audio.wav): ").strip()
        
        # Kiểm tra file tồn tại
        if not os.path.exists(input_filename):
            print(f"❌ Không tìm thấy file: {input_filename}")
            print("Vui lòng kiểm tra lại tên file và đường dẫn!")
            return
        
        print(f"✅ Tìm thấy file: {input_filename}")
        
        # Hiển thị thông tin file
        try:
            audio_data, sample_rate = read_wav_file(input_filename)
            if audio_data is not None:
                duration = len(audio_data) / sample_rate
                rms_value = np.sqrt(np.mean(audio_data**2))
                print(f"📊 Thông tin file:")
                print(f"   - Độ dài: {duration:.1f} giây")
                print(f"   - Sample rate: {sample_rate} Hz")
                print(f"   - RMS: {rms_value:.1f}")
        except:
            pass
        
        print(f"\n🚀 Bắt đầu Professional MFCC + DTW analysis...")
        
        input("\nNhấn Enter để bắt đầu analysis...")
        
        # Tìm template khớp nhất với MFCC + DTW
        result = find_best_template_mfcc_match_enhanced(input_filename)
        
        if result:
            print(f"\n🎯 KẾT QUẢ CUỐI CÙNG: {result}")
        else:
            print(f"\n❌ Không thể xử lý file hoặc thiếu thư viện cần thiết")
            
    elif choice == "0":
        print("Tạm biệt!")
        return
    else:
        print("Lựa chọn không hợp lệ!")
    
    # Quay lại menu
    input("\nNhấn Enter để tiếp tục...")
    main_menu()

if __name__ == "__main__":
    main_menu()
