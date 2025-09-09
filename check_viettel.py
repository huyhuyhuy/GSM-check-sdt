import time
import os
import threading
from typing import Callable
import pyaudio
import wave
import numpy as np
from datetime import datetime
from scipy.signal import correlate

# Professional MFCC imports
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

# Global audio lock để tránh conflict PyAudio
# _AUDIO_LOCK = threading.Lock()
# _AUDIO_IN_USE = False


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


def parse_clcc_status(clcc_response: str) -> int:
    """Parse status từ response AT+CLCC"""
    try:
        lines = clcc_response.split('\n')
        for line in lines:
            if '+CLCC:' in line:
                parts = line.strip().split(',')
                if len(parts) >= 3:
                    status = int(parts[2])
                    return status
        return -1
    except Exception:
        return -1


# ==============================================================================
# LOGIC CŨ - ĐÃ COMMENT
# Thuật toán song song GSM + ESP32 phức tạp, thay thế bằng audio analysis đơn giản
# ==============================================================================
def viettel_combined_check_OLD(device, phone_number: str, log_callback: Callable = None) -> str:
    """
    [COMMENTED OUT - LOGIC CŨ]
    Chạy song song 2 luồng:
    - GSM (KẾT QUẢ 1): tìm HOẠT ĐỘNG dựa vào CLCC 0/3, +COLP:, BUSY/RING/RINGING/CONNECT.
    - ESP (KẾT QUẢ 2): chờ 2s sau ATD rồi thu 12s ADC kênh 1,2; phân tích vùng dày đặc.

    Quy tắc quyết định cuối:
    - Nếu KẾT QUẢ 1 = HOẠT ĐỘNG → kết quả cuối = HOẠT ĐỘNG (nhưng vẫi đợi ESP xong để an toàn).
    - Ngược lại → kết quả cuối theo KẾT QUẢ 2.
    
    THAY THẾ BẰNG: viettel_audio_check() - sử dụng template matching
    """

    """
    # COMMENTED OUT - TOÀN BỘ LOGIC CŨ
    def log(message: str):
        if log_callback:
            log_callback(message)
        else:
            print(f"[{phone_number}] {message}")

    try:
        # Đảm bảo modem sẵn sàng
        ready_response = device.send_command_quick("AT")
        if "OK" not in ready_response:
            log("Modem không sẵn sàng")
            try:
                device.send_command_quick("ATH")
            except Exception:
                pass
            return "THUÊ BAO"

        device.send_command_quick("ATH")
        time.sleep(1)

        # Gửi lệnh gọi
        call_command = f"ATD{phone_number};"
        log("Gửi lệnh gọi...")
        device.serial_connection.reset_input_buffer()
        device.serial_connection.reset_output_buffer()
        device.serial_connection.write((call_command + "\r\n").encode())
        time.sleep(1)  # Chờ 1s để cuộc gọi ổn định

        # Bắt đầu 2 luồng song song
        # log("Bắt đầu GSM và ESP threads...")

        gsm_done = threading.Event()
        esp_done = threading.Event()
        gsm_result = {}
        esp_result = {}

        # GSM thread: xác định KẾT QUẢ 1
        def gsm_thread_func():
            try:
                start_time = time.time()
                timeout = 15.0

                clcc_statuses = []
                gsm_responses = []
                active_detected = False
                ath_sent_immediately = False

                while time.time() - start_time < timeout and not gsm_done.is_set():
                    clcc_response = device.send_command_quick("AT+CLCC", 0.5)
                    if "+CLCC:" in clcc_response:
                        status = parse_clcc_status(clcc_response)
                        clcc_statuses.append(status)
                        log(f"ESP Status: {status}")
                        if status in [0, 3]:
                            active_detected = True
                            gsm_result['final'] = 'HOẠT ĐỘNG'
                            # Nếu status==0 (đã nhấc máy) → cúp ngay để tránh tốn phí
                            if status == 0 and not ath_sent_immediately:
                                try:
                                    device.send_command_quick("ATH")
                                    ath_sent_immediately = True
                                    # log("GSM Thread - Phát hiện CLCC=0 → gửi ATH ngay")
                                except Exception:
                                    pass
                            # log("GSM Thread - KẾT QUẢ 1 = HOẠT ĐỘNG")
                            gsm_done.set()
                            return

                    try:
                        time.sleep(0.5)
                        if device.serial_connection.in_waiting > 0:
                            chunk = device.serial_connection.read(device.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                            if chunk.strip():
                                gsm_responses.append(chunk)
                                log(f"GSM Thread - Response: '{chunk.strip()}'")
                                up = chunk.upper()
                                if ("+COLP:" in up or "BUSY" in up or "RINGING" in up or
                                    "RING" in up or "CONNECT" in up):
                                    active_detected = True
                                    gsm_result['final'] = 'HOẠT ĐỘNG'
                                    # Nếu là COLP/CONNECT (đã nhấc máy) → cúp ngay để tránh tốn phí
                                    if (("+COLP:" in up or "CONNECT" in up) and not ath_sent_immediately):
                                        try:
                                            device.send_command_quick("ATH")
                                            ath_sent_immediately = True
                                            # log("GSM Thread - Phát hiện COLP/CONNECT → gửi ATH ngay")
                                        except Exception:
                                            pass
                                    # log("GSM Thread - KẾT QUẢ 1 = HOẠT ĐỘNG (keyword)")
                                    gsm_done.set()
                                    return
                        else:
                            if time.time() - start_time > 5.0:
                                # log(f"GSM Thread - Debug: in_waiting={device.serial_connection.in_waiting}")
                                try:
                                    device.serial_connection.timeout = 0.1
                                    test_read = device.serial_connection.read(100)
                                    if test_read:
                                        test_text = test_read.decode('utf-8', errors='ignore')
                                        # log(f"GSM Thread - Debug: Found data: '{test_text.strip()}'")
                                        gsm_responses.append(test_text)
                                    device.serial_connection.timeout = device.timeout
                                except Exception as e:
                                    log(f"GSM Thread - Debug read e: {str(e)}")
                    except Exception as e:
                        log(f"GSM Thread - Lỗi đọc response: {str(e)}")

                gsm_text = " ".join(gsm_responses).upper()
                gsm_result['clcc_statuses'] = clcc_statuses
                gsm_result['gsm_text'] = gsm_text
                if not active_detected:
                    unique_status = set(clcc_statuses)
                    if unique_status and unique_status.issubset({2, 6}):
                        gsm_result['final'] = 'THUÊ BAO'
                        # log("GSM Thread - KẾT QUẢ 1 = THUÊ BAO (chỉ 2/6)")
                    else:
                        gsm_result['final'] = 'THUÊ BAO'
                log(f"GSM Thread - Total responses: {len(gsm_responses)}")
                if gsm_responses:
                    log(f"GSM Thread - Last response: '{gsm_responses[-1].strip()}'")
            except Exception as e:
                log(f"GSM Thread - Lỗi: {str(e)}")
                gsm_result['error'] = str(e)
            finally:
                gsm_done.set()

        # ESP thread: thu 12s ADC kênh 1,2 sau khi chờ 2s
        def esp_thread_func():
            try:
                if device.audio_analyzer:
                    log(f"ESP Thread - Thu ADC, lưu file và phân tích")
                    timestamp_str = time.strftime("%H_%M_%S")
                    output_dir = "adc_logs"
                    os.makedirs(output_dir, exist_ok=True)

                    # log("ESP Thread - Chờ 2s sau ATD trước khi bắt đầu thu ADC...")
                    time.sleep(2.0)

                    samples_map = device.audio_analyzer.collect_adc_samples_multi_channel([1, 2], duration=12.0)

                    # for ch, samples in samples_map.items():
                    #     try:
                    #         file_path = os.path.join(output_dir, f"ADC_channel{ch}_{timestamp_str}.txt")
                    #         with open(file_path, 'w', encoding='utf-8') as f:
                    #             for val in samples:
                    #                 f.write(f"{val}\n")
                    #         log(f"ESP Thread - Đã lưu {len(samples)} mẫu: {file_path}")
                    #     except Exception as e:
                    #         log(f"ESP Thread - Lỗi lưu file channel {ch}: {str(e)}")

                    device_channel = getattr(device, 'audio_channel', 1)
                    if device_channel not in [1, 2]:
                        device_channel = 1
                    device_samples = samples_map.get(device_channel, [])
                    if device_samples:
                        analysis = device.audio_analyzer._find_rectangular_regions(device_samples)
                        pattern = analysis.get('pattern', 'SILENCE')
                    else:
                        pattern = 'SILENCE'
                    esp_result['pattern'] = pattern
                    # log(f"ESP Thread - Pattern (channel {device_channel}): {pattern}")
                else:
                    # log("ESP Thread - Không có audio analyzer")
                    esp_result['pattern'] = 'SILENCE'
            except Exception as e:
                log(f"ESP Thread - Lỗi: {str(e)}")
                esp_result['pattern'] = 'SILENCE'
            finally:
                esp_done.set()

        # Khởi động threads
        gsm_thread = threading.Thread(target=gsm_thread_func)
        esp_thread = threading.Thread(target=esp_thread_func)
        gsm_thread.start()
        esp_thread.start()

        # Chờ GSM xong để lấy KẾT QUẢ 1, nhưng KHÔNG trả về sớm
        gsm_thread.join(timeout=15.0)
        gsm_final = gsm_result.get('final', 'THUÊ BAO')
        # log(f"KẾT QUẢ 1 (GSM): {gsm_final}")

        # Luôn chờ ESP hoàn thành để tránh xung đột lệnh ở lần gọi tiếp theo
        esp_thread.join(timeout=15.0)
        pattern = esp_result.get('pattern', 'SILENCE')
        # log(f"KẾT QUẢ 2 (ESP): {pattern}")

        # Quy tắc quyết định cuối cùng
        if gsm_final == 'HOẠT ĐỘNG':
            final_result = 'HOẠT ĐỘNG'
        else:
            if pattern == 'RINGTONE':
                final_result = 'HOẠT ĐỘNG'
            elif pattern == 'BLOCKED':
                final_result = 'SỐ KHÔNG ĐÚNG'
            else:
                final_result = 'THUÊ BAO'

        # Dừng cuộc gọi
        device.send_command_quick("ATH")
        time.sleep(1)
        return final_result

    except Exception as e:
        log(f"Lỗi check Viettel: {str(e)}")
        try:
            device.send_command_quick("ATH")
        except Exception:
            pass
        return "THUÊ BAO"
    """
    # KẾT THÚC COMMENT - LOGIC CŨ ĐÃ ĐƯỢC COMMENT TOÀN BỘ
    pass  # Placeholder cho function cũ


def viettel_combined_check(device, phone_number: str, log_callback: Callable = None) -> str:
    """
    LOGIC MỚI - Đơn giản hóa cho số Viettel:
    1. GSM gửi lệnh gọi (ATD)
    2. Thu âm audio và phân tích bằng template matching
    3. Trả về: SO KHONG DUNG, THUE BAO, hoặc HOAT DONG
    
    Chỉ dành cho cổng COM38 (cổng cố định xử lý Viettel)
    """
    return viettel_audio_check(device, phone_number, log_callback)


def analyze_audio_with_templates(wave_filename: str, log_callback: Callable) -> str:
    """
    Phân tích audio file với Professional MFCC + DTW (Option 7 style)
    Chỉ sử dụng 2 templates chính: THUE BAO và SO KHONG DUNG
    Trả về: SO KHONG DUNG, THUE BAO, hoặc HOAT DONG
    """
    if not LIBROSA_AVAILABLE:
        if log_callback:
            log_callback("❌ Cần cài đặt librosa để sử dụng Professional MFCC!")
        return "HOAT DONG"
    
    # Chỉ check 2 templates chính (như Option 7)
    templates = {
        "THUE BAO": "template_thue_bao_ok.wav",
        "SO KHONG DUNG": "template_so_khong_dung_ok.wav"
    }
    
    def log(message: str):
        if log_callback:
            log_callback(message)
    
    try:
        log("🎵 PROFESSIONAL MFCC + DTW ANALYSIS")
        log("🔧 Professional Pipeline: 16kHz+Pre-emphasis+Noise profile+CMVN")
        
        # Đọc file cần check
        check_audio, check_rate = read_wav_file(wave_filename)
        if check_audio is None:
            log(f"❌ Không thể đọc file: {wave_filename}")
            return "HOAT DONG"
        
        log(f"📂 File check: {len(check_audio)} samples, {check_rate}Hz")
        
        # Chuẩn bị file check
        check_audio_norm, target_rate = resample_and_normalize_audio(check_audio, check_rate)
        log(f"   Sau normalize: {len(check_audio_norm)} samples, {target_rate}Hz")
        
        results = {}
        
        # Kiểm tra từng template 
        for template_name, template_file in templates.items():
            if not os.path.exists(template_file):
                log(f"⚠️ Không tìm thấy: {template_file}")
                continue
                
            log(f"🎵 KIỂM TRA TEMPLATE: {template_name}")
            
            # Đọc template
            template_audio, template_rate = read_wav_file(template_file)
            if template_audio is None:
                log(f"❌ Không thể đọc template: {template_file}")
                continue
            
            # Chuẩn bị template (resample + normalize)
            template_norm, _ = resample_and_normalize_audio(template_audio, template_rate, target_rate)
            
            # Lấy 3s đầu template
            window_3s = target_rate * 3
            template_3s = template_norm[:min(window_3s, len(template_norm))]
            
            actual_duration = len(template_3s) / target_rate
            log(f"   ✂️ Sử dụng {actual_duration:.1f}s đầu template ({len(template_3s)} samples)")
            
            # MFCC sliding window match
            distance, position = mfcc_sliding_window_match(
                template_3s, check_audio_norm, target_rate, distance_threshold=15.0
            )
            
            # Convert distance to similarity score với adaptive scaling
            if distance == float('inf'):
                similarity_score = 0.0
            else:
                # Adaptive scaling dựa trên enhanced features (giống Option 7)
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
            
            log(f"   🎯 Kết quả: DTW distance={distance:.2f}, similarity={similarity_score:.3f} (tại {position:.1f}s)")
        
        # Tổng kết kết quả (giống Option 7)
        if not results:
            log("❌ Không có template nào được xử lý thành công")
            return "HOAT DONG"
        
        # Sắp xếp theo distance (thấp nhất = tốt nhất)
        sorted_results = sorted(results.items(), key=lambda x: x[1]['distance'])
        
        for i, (name, data) in enumerate(sorted_results):
            icon = "🥇" if i == 0 else "🥈"
            distance = data['distance']
            similarity = data['similarity']
            if distance == float('inf'):
                log(f"{icon} {name}: DTW=∞ (không tính được)")
            else:
                log(f"{icon} {name}: DTW={distance:.2f} Sim={similarity:.3f} (tại {data['position']:.1f}s)")
        
        # Xác định kết quả cuối cùng (Logic Option 7)
        best_template, best_data = sorted_results[0]
        best_distance = best_data['distance']
        
        # DTW threshold và logic như Option 7
        dtw_threshold = 9.3
        
        if best_distance == float('inf'):
            log(f"❌ KHÔNG THỂ TÍNH TOÁN - Lỗi MFCC extraction")
            final_result = "HOAT DONG"
        elif best_distance <= dtw_threshold:
            log(f"✅ KẾT QUẢ TIN CẬY (DTW ≤ {dtw_threshold})")
            final_result = best_template
        else:
            log(f"⚠️ DTW > {dtw_threshold} → PHÂN LOẠI LÀ HOẠT ĐỘNG")
            final_result = "HOAT DONG"
        
        log(f"🎯 KẾT QUẢ CUỐI CÙNG: {final_result}")
        return final_result
            
    except Exception as e:
        log(f"Lỗi phân tích audio: {str(e)}")
        return "HOAT DONG"


def viettel_audio_check(device, phone_number: str, log_callback: Callable = None) -> str:
    """
    Check số Viettel bằng cách:
    1. Gửi lệnh gọi ATD
    2. Monitor GSM response song song với thu âm
    3. Dừng sớm nếu CLCC=0 hoặc +COLP (người nhấc máy) → HOẠT ĐỘNG
    4. Nếu không, phân tích audio với templates
    5. Luôn gửi ATH để tiết kiệm phí
    
    CRITICAL: Chỉ 1 số Viettel được xử lý tại 1 thời điểm để tránh PyAudio conflict
    """
    # Imports đã được đưa lên đầu file
    
    def log(message: str):
        if log_callback:
            log_callback(message)
        else:
            print(f"[{phone_number}] {message}")
    
    try:
        # Đảm bảo modem sẵn sàng
        ready_response = device.send_command_quick("AT")
        if "OK" not in ready_response:
            log("Modem không sẵn sàng")
            return "THUE BAO"
        
        # Cleanup trước khi gọi
        device.send_command_quick("ATH")
        time.sleep(1)
        
        # Bắt đầu cuộc gọi
        call_command = f"ATD{phone_number};"
        log(f"Bắt đầu gọi {phone_number}...")
        device.serial_connection.reset_input_buffer()
        device.serial_connection.reset_output_buffer()
        device.serial_connection.write((call_command + "\r\n").encode())
        
        # Chờ 1 giây để cuộc gọi khởi tạo
        time.sleep(1)
        
        # Sử dụng dual-threading với khả năng dừng sớm
        log("Bắt đầu dual-threading: GSM monitoring + Audio recording...")
        result = gsm_monitor_with_audio_recording(device, phone_number, log)
        
        # Luôn dừng cuộc gọi
        try:
            device.send_command_quick("ATH")
            time.sleep(0.5)
        except:
            pass
        
        return result
            
    except Exception as e:
        log(f"Lỗi check Viettel: {str(e)}")
        try:
            device.send_command_quick("ATH")
            time.sleep(0.5)
        except:
            pass
        return "THUÊ BAO"


def gsm_monitor_with_audio_recording(device, phone_number: str, log_callback: Callable) -> str:
    """
    Chạy song song 2 luồng:
    1. GSM Thread: Monitor CLCC status và response → Dừng sớm nếu có người nhấc máy
    2. Audio Thread: Thu âm và phân tích templates (BỎ LOCK - thu âm trực tiếp)
    
    Ưu tiên: GSM detection → Early stop → Audio analysis → Fallback
    """
    import threading
    
    def log(message: str):
        if log_callback:
            log_callback(message)
    
    # Shared variables
    gsm_done = threading.Event()
    audio_done = threading.Event()
    should_stop_audio = threading.Event()  # Signal để dừng audio sớm
    
    gsm_result = {'status': None, 'early_stop': False}
    audio_result = {'pattern': None}
    
    def gsm_monitoring_thread():
        """
        Monitor GSM responses trong 20 giây
        Dừng sớm nếu phát hiện CLCC=0 hoặc +COLP (người nhấc máy)
        → Signal audio thread dừng và trả về HOẠT ĐỘNG ngay lập tức
        """
        try:
            start_time = time.time()
            timeout = 20.0  # Tối đa 20 giây
            
            while time.time() - start_time < timeout and not gsm_done.is_set():
                # Check CLCC status
                clcc_response = device.send_command_quick("AT+CLCC", 0.3)
                if "+CLCC:" in clcc_response:
                    status = parse_clcc_status(clcc_response)
                    if status == 0:  # Người nhấc máy
                        log(f"🎯 CLCC=0 - Người nhấc máy! → HOẠT ĐỘNG")
                        gsm_result['status'] = 'HOẠT ĐỘNG'
                        gsm_result['early_stop'] = True
                        # Dừng cuộc gọi ngay
                        device.send_command_quick("ATH")
                        # Signal audio thread dừng
                        should_stop_audio.set()
                        gsm_done.set()
                        return
                
                # Check serial response
                try:
                    if device.serial_connection.in_waiting > 0:
                        chunk = device.serial_connection.read(device.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                        if chunk.strip():
                            chunk_upper = chunk.upper()
                            log(f"GSM Response: '{chunk.strip()}'")
                            
                            # Check for +COLP (người nhấc máy)
                            if "+COLP:" in chunk_upper:
                                log(f"🎯 +COLP detected - Người nhấc máy! → HOẠT ĐỘNG")
                                gsm_result['status'] = 'HOẠT ĐỘNG'
                                gsm_result['early_stop'] = True
                                # Dừng cuộc gọi ngay
                                device.send_command_quick("ATH")
                                # Signal audio thread dừng
                                should_stop_audio.set()
                                gsm_done.set()
                                return
                            
                            # Check for other activity indicators
                            if any(keyword in chunk_upper for keyword in ["CONNECT", "BUSY", "RINGING"]):
                                log(f"GSM Activity: {chunk.strip()}")
                                # Không dừng sớm, để audio analysis quyết định
                
                except Exception as e:
                    log(f"GSM monitoring error: {str(e)}")
                
                time.sleep(0.5)  # Check mỗi 0.5 giây
            
            log("GSM monitoring hoàn thành (timeout)")
            gsm_done.set()
            
        except Exception as e:
            log(f"GSM monitoring thread error: {str(e)}")
            gsm_done.set()
    
    def audio_recording_thread():
        """
        Thu âm và phân tích audio templates
        Có thể bị dừng sớm bởi GSM thread khi phát hiện người nhấc máy
        BỎ LOCK - thu âm trực tiếp
        """
        # Bỏ lock - thu âm trực tiếp
        log("Bắt đầu thu âm...")
        
        # Thiết lập thu âm
        CHUNK = 1024
        FORMAT = pyaudio.paInt16  
        CHANNELS = 2
        RATE = 44100
        RECORD_SECONDS = 20
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wave_filename = f"viettel_audio_{phone_number}_{timestamp}.wav"
        
        p = pyaudio.PyAudio()
        
        # Kiểm tra audio device có sẵn không
        if p.get_device_count() == 0:
            log("Không tìm thấy audio device!")
            p.terminate()
            audio_result['pattern'] = 'NO_AUDIO_DEVICE'
            audio_done.set()
            return
        
        try:
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                           input=True, frames_per_buffer=CHUNK)
        except Exception as audio_error:
            log(f"Lỗi mở audio stream: {str(audio_error)}")
            p.terminate()
            audio_result['pattern'] = 'NO_AUDIO_DEVICE'
            audio_done.set()
            return
        
        frames = []
        total_chunks = int(RATE / CHUNK * RECORD_SECONDS)
        
        for i in range(total_chunks):
            # Check nếu GSM thread yêu cầu dừng
            if should_stop_audio.is_set():
                log("Audio recording dừng sớm (GSM detected)")
                break
            
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except Exception as read_error:
                log(f"Lỗi đọc audio chunk {i}: {str(read_error)}")
                # Tiếp tục thay vì crash
                continue
            
            # Log progress mỗi 2 giây
            if i % (int(RATE / CHUNK * 2)) == 0:
                elapsed = i // int(RATE / CHUNK)
                log(f"Thu âm: {elapsed}s/{RECORD_SECONDS}s")
        
        # Cleanup audio stream safely
        try:
            stream.stop_stream()
            stream.close()
        except Exception as cleanup_error:
            log(f"Lỗi cleanup audio stream: {str(cleanup_error)}")
        
        # Nếu bị dừng sớm, vẫn lưu file để kiểm tra
        if should_stop_audio.is_set():
            if frames:  # Có data thu được
                try:
                    log("Lưu audio dừng sớm...")
                    wf = wave.open(wave_filename, 'wb')
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(p.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    log(f"💾 Đã lưu audio (early stop): {wave_filename}")
                except Exception as early_save_error:
                    log(f"Lỗi lưu audio early stop: {str(early_save_error)}")
            
            p.terminate()
            audio_result['pattern'] = 'EARLY_STOP'
            audio_done.set()
            return
        
        # Lưu và phân tích audio
        if frames:
            try:
                log("Lưu và phân tích audio...")
                wf = wave.open(wave_filename, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                # Phân tích templates
                pattern = analyze_audio_with_templates(wave_filename, log)
                audio_result['pattern'] = pattern
                
                # Lưu file để user kiểm tra
                log(f"💾 Đã lưu audio: {wave_filename}")
                
            except Exception as file_error:
                log(f"Lỗi lưu/phân tích audio: {str(file_error)}")
                audio_result['pattern'] = 'FILE_ERROR'
            
            # GIỮ LẠI FILE để user kiểm tra (không xóa nữa)
            # try:
            #     if os.path.exists(wave_filename):
            #         os.remove(wave_filename)
            # except Exception as delete_error:
            #     log(f"Lỗi xóa file tạm: {str(delete_error)}")
        else:
            audio_result['pattern'] = 'NO_AUDIO'
        
        p.terminate()
        log("Audio recording hoàn thành")
        audio_done.set()
        
        # Không cần cleanup lock nữa
    
    # Khởi động 2 threads
    gsm_thread = threading.Thread(target=gsm_monitoring_thread)
    audio_thread = threading.Thread(target=audio_recording_thread)
    
    gsm_thread.start()
    audio_thread.start()
    
    # Chờ cả 2 threads hoàn thành (timeout 25s)
    gsm_thread.join(timeout=25)
    audio_thread.join(timeout=25)
    
    # Quyết định kết quả cuối cùng
    if gsm_result.get('early_stop', False):
        # GSM đã phát hiện người nhấc máy → Ưu tiên cao nhất
        log(f"🎯 Kết quả: {gsm_result['status']} (Early detection)")
        return gsm_result['status']
    
    # Fallback theo audio analysis
    pattern = audio_result.get('pattern', 'ERROR')
    
    if pattern == 'SO KHONG DUNG':
        return "SỐ KHÔNG ĐÚNG"
    elif pattern == 'THUE BAO':
        return "THUÊ BAO"
    elif pattern in ['DE LAI LOI NHAN', 'HOAT DONG', 'EARLY_STOP', 'NO_AUDIO']:
        return "HOẠT ĐỘNG"  # Đính chính: "để lại lời nhắn" → HOẠT ĐỘNG
    elif pattern in ['NO_AUDIO_DEVICE', 'AUDIO_ERROR', 'FILE_ERROR', 'AUDIO_BUSY', 'AUDIO_TIMEOUT']:
        log(f"Audio lỗi ({pattern}) → Fallback HOẠT ĐỘNG")
        return "HOẠT ĐỘNG"  # Fallback khi audio bị lỗi hoặc busy
    else:
        return "THUÊ BAO"  # Default fallback


def analyze_audio_with_templates(wave_filename: str, log_callback: Callable) -> str:
    """
    Phân tích audio file với 3 templates
    Trả về: SO KHONG DUNG, THUE BAO, DE LAI LOI NHAN, hoặc HOAT DONG
    """
    templates = {
        "SO KHONG DUNG": "template_so_khong_dung_ok.wav",
        "THUE BAO": "template_thue_bao_ok.wav",
        "DE LAI LOI NHAN": "template_de_lai_loi_nhan_ok.wav"
    }
    
    def log(message: str):
        if log_callback:
            log_callback(message)
    
    try:
        results = {}
        
        for label, template_file in templates.items():
            if not os.path.exists(template_file):
                log(f"Không tìm thấy template: {template_file}")
                continue
            
            # So sánh bằng correlation
            is_match = compare_audio_files_simple(template_file, wave_filename, threshold=0.3)
            results[label] = is_match
            
            if is_match:
                log(f"✅ Khớp với template: {label}")
        
        # Logic phân loại
        matched_templates = [label for label, is_match in results.items() if is_match]
        
        if len(matched_templates) == 0:
            return "HOAT DONG"  # Không khớp template nào
        elif "SO KHONG DUNG" in matched_templates:
            return "SO KHONG DUNG"  # Ưu tiên cao nhất
        elif "THUE BAO" in matched_templates:
            return "THUE BAO"
        elif "DE LAI LOI NHAN" in matched_templates:
            return "HOAT DONG"  # Đính chính: "để lại lời nhắn" → HOẠT ĐỘNG
        else:
            return "HOAT DONG"  # Fallback
            
    except Exception as e:
        log(f"Lỗi phân tích audio: {str(e)}")
        return "HOAT DONG"


def record_and_analyze_audio(phone_number: str, log_callback: Callable) -> str:
    """
    Thu âm và phân tích với Professional MFCC + DTW (Option 7)
    Trả về: SO KHONG DUNG, THUE BAO, hoặc HOAT DONG
    """
    def log(message: str):
        if log_callback:
            log_callback(message)
    
    try:
        # Thiết lập thu âm
        CHUNK = 1024
        FORMAT = pyaudio.paInt16  
        CHANNELS = 2
        RATE = 44100
        RECORD_SECONDS = 20
        
        # Tạo tên file với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wave_filename = f"viettel_audio_{phone_number}_{timestamp}.wav"
        
        # Bỏ lock - thu âm trực tiếp
        log("Bắt đầu thu âm trực tiếp...")
        
        p = pyaudio.PyAudio()
        
        stream = p.open(format=FORMAT,
                       channels=CHANNELS, 
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        log("Đang thu âm...")
        frames = []
        
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        # Lưu file WAV
        wf = wave.open(wave_filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        p.terminate()
        
        log("Hoàn thành thu âm, bắt đầu phân tích Professional MFCC + DTW...")
        
        # Phân tích với Professional MFCC + DTW (Option 7 style)
        result = analyze_audio_with_templates(wave_filename, log_callback)
        
        log(f"💾 Đã lưu audio: {wave_filename}")
        
        return result
            
    except Exception as e:
        log(f"Lỗi thu âm và phân tích: {str(e)}")
        return "HOAT DONG"  # Conservative fallback


def compare_audio_files_simple(file1: str, file2: str, threshold: float = 0.3) -> bool:
    """
    So sánh 2 file âm thanh đơn giản, trả về True nếu giống nhau
    Sử dụng thuật toán correlation cơ bản
    """
    try:
        # Đọc file WAV
        def read_wav_file(filename):
            with wave.open(filename, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16)
                # Chuyển stereo thành mono
                if wf.getnchannels() == 2:
                    audio_data = audio_data.reshape(-1, 2)
                    audio_data = np.mean(audio_data, axis=1)
                return audio_data, wf.getframerate()
        
        audio1, rate1 = read_wav_file(file1)
        audio2, rate2 = read_wav_file(file2)
        
        if audio1 is None or audio2 is None or rate1 != rate2:
            return False
        
        # Chuẩn hóa
        audio1 = audio1.astype(np.float64) - np.mean(audio1)
        audio2 = audio2.astype(np.float64) - np.mean(audio2)
        
        if np.std(audio1) > 0:
            audio1 = audio1 / np.std(audio1)
        if np.std(audio2) > 0:
            audio2 = audio2 / np.std(audio2)
        
        # So sánh đoạn 5 giây đầu để tăng tốc
        segment_length = min(rate1 * 5, len(audio1), len(audio2))
        seg1 = audio1[:segment_length]
        seg2 = audio2[:segment_length]
        
        # Cross-correlation
        correlation_full = correlate(seg1, seg2, mode='full')
        max_corr = np.max(np.abs(correlation_full)) / len(seg1)
        
        # Direct correlation
        min_length = min(len(audio1), len(audio2))
        direct_corr = np.corrcoef(audio1[:min_length], audio2[:min_length])[0, 1]
        if np.isnan(direct_corr):
            direct_corr = 0
        
        # Điểm số tổng hợp
        final_score = (max_corr * 0.6 + abs(direct_corr) * 0.4)
        
        return final_score >= threshold
        
    except Exception:
        return False


