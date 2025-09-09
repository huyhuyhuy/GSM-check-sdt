import serial
import time
import threading
from typing import Callable, Optional, List
import logging

class ESP32AudioAnalyzer:
    def __init__(self, port: str = "COM67", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        self.log_callback = None
        self.adc_data_callback = None
        self.binary_mode = True  # Mặc định bật binary mode
        
        # Multi-channel support
        self.total_channels = 32
        self.max_active_channels = 32  # Tăng lên 32 channels để phù hợp với ESP32
        self.active_channels = []
        self.buffer_size = 50  # Giảm xuống 50 samples để phù hợp với ESP32 buffer
        self.streaming = False
        self.adc_buffer = {}  # Store ADC values for each channel
        
    def set_log_callback(self, callback: Callable):
        """Thiết lập callback để ghi log"""
        self.log_callback = callback
    
    def set_adc_data_callback(self, callback: Callable):
        """Thiết lập callback để gửi ADC data"""
        self.adc_data_callback = callback
    
    def log(self, message: str):
        """Ghi log"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[ESP32] {message}")
    
    def connect(self) -> bool:
        """Kết nối đến ESP32 (tối ưu cho ESP32 mới)"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=250000,
                timeout=1
            )
            self.connected = True
            self.log(f"ESP32 Multi-Channel Audio Analyzer connected on {self.port} at 250000 bps")
            
            # Tự động bật binary mode
            if self.binary_mode:
                self.set_binary_mode(True)
            
            return True
        except Exception as e:
            self.log(f"Failed to connect ESP32 on {self.port}: {str(e)}")
            return False
    
    def disconnect(self):
        """Ngắt kết nối ESP32"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
        self.log("ESP32 Audio Analyzer disconnected")
    
    def read_audio_level(self, channel: int = 0) -> int:
        """Đọc mức âm thanh từ kênh cụ thể (tối ưu cho ESP32 mới)"""
        if not self.connected:
            return -1
        
        try:
            # Gửi lệnh đọc
            command = f"read {channel}\n"
            self.serial.write(command.encode())
            
            # Đọc phản hồi
            start_time = time.time()
            while time.time() - start_time < 3:  # Giảm timeout xuống 3 giây
                if self.serial.in_waiting:
                    try:
                        line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    except UnicodeDecodeError:
                        continue
                    if line.startswith(f"CH{channel}:"):  # Sửa format để phù hợp với ESP32
                        # Parse: "CH0: 1942"
                        try:
                            value = int(line.split(":")[1].strip())
                            return value
                        except (ValueError, IndexError):
                            self.log(f"Error parsing audio level: {line}")
                            return -1
                time.sleep(0.05)  # Giảm sleep time
            
            self.log(f"Timeout reading audio level from channel {channel}")
            return -1
            
        except Exception as e:
            self.log(f"Error reading audio level from channel {channel}: {str(e)}")
            return -1
    
    def start_multi_channel_streaming(self, channels: List[int]) -> bool:
        """Bắt đầu streaming nhiều channels cùng lúc"""
        if not self.connected:
            return False
        
        # Giới hạn số channels active
        if len(channels) > self.max_active_channels:
            self.log(f"⚠️ Giới hạn {self.max_active_channels} channels, chỉ sử dụng {channels[:self.max_active_channels]}")
            channels = channels[:self.max_active_channels]
        
        try:
            # Clear buffer cho tất cả channels
            for channel in channels:
                self.adc_buffer[channel] = []
            
            self.active_channels = channels
            self.streaming = True
            
            # Gửi lệnh bắt đầu multi-channel streaming
            channels_str = ",".join(map(str, channels))
            command = f"start_multi {channels_str}\n"
            # self.log(f"Bắt đầu multi-channel streaming: {channels_str}")
            self.serial.write(command.encode())
            
            # Đọc confirmation
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith("MULTI_STREAM_START:"):
                        channel_count = int(line.split(":")[1])
                        # self.log(f"Multi-channel streaming started for {channel_count} channels")
                        return True
                time.sleep(0.1)
            
            self.log(f"Timeout starting multi-channel stream")
            return False
            
        except Exception as e:
            # self.log(f"Error starting multi-channel stream: {str(e)}")
            return False
    
    def start_streaming(self, channel: int = 0) -> bool:
        """Bắt đầu streaming ADC values từ kênh cụ thể (legacy method)"""
        if not self.connected:
            return False
        
        try:
            # Clear buffer
            self.adc_buffer[channel] = []
            self.streaming = True
            self.active_channels = [channel]
            
            # Gửi lệnh bắt đầu streaming
            command = f"start_stream {channel}\n"
            self.log(f"Bắt đầu streaming channel {channel}")
            self.serial.write(command.encode())
            
            # Đọc confirmation
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line == "STREAM_START":
                        return True
                time.sleep(0.1)
            
            self.log(f"Timeout starting stream for channel {channel}")
            return False
            
        except Exception as e:
            self.log(f"Error starting stream for channel {channel}: {str(e)}")
            return False
    
    def stop_streaming(self) -> bool:
        """Dừng streaming"""
        if not self.connected:
            return False
        
        try:
            self.streaming = False
            command = "stop_stream\n"
            self.serial.write(command.encode())
            
            # Đọc confirmation
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line == "STREAM_STOP":
                        self.log("Streaming stopped")
                        return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            self.log(f"Error stopping stream: {str(e)}")
            return False
    
    def set_binary_mode(self, enabled: bool) -> bool:
        """Switch giữa binary và text mode"""
        if not self.connected:
            return False
        
        try:
            if enabled:
                command = "binary_on\n"
                # self.log("Switching to binary mode...")
            else:
                command = "binary_off\n"
                # self.log("Switching to text mode...")
            
            self.serial.write(command.encode())
            
            # Đọc confirmation
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line in ["BINARY_MODE_ON", "TEXT_MODE_ON"]:
                        self.binary_mode = enabled
                        self.log(f"Mode switched: {line}")
                        return True
            
            return False
        except Exception as e:
            self.log(f"Error switching mode: {str(e)}")
            return False

    def read_batch_adc_data(self, batch_size: int = 800) -> List[tuple]:
        """Đọc nhiều ADC samples cùng lúc (batch reading tối ưu cho ESP32)"""
        if not self.connected or not self.binary_mode:
            return []
        
        try:
            # Đọc tất cả data có sẵn
            available_bytes = self.serial.in_waiting
            if available_bytes < 3:  # Cần ít nhất 1 mẫu (3 bytes)
                return []
            
            # Tính số mẫu có thể đọc (giới hạn batch_size)
            max_samples = min(available_bytes // 3, batch_size)
            if max_samples == 0:
                return []
            
            # Đọc tất cả bytes cùng lúc
            total_bytes = max_samples * 3
            raw_data = self.serial.read(total_bytes)
            
            # Parse thành các mẫu
            samples = []
            for i in range(0, len(raw_data), 3):
                if i + 2 < len(raw_data):
                    channel = raw_data[i]
                    value = (raw_data[i+1] << 8) | raw_data[i+2]
                    samples.append((channel, value))
            
            return samples
            
        except Exception as e:
            self.log(f"Error reading batch data: {str(e)}")
            return []

    def read_binary_adc_data(self, timeout: float = 0.05) -> Optional[tuple]:
        """Đọc binary ADC data từ ESP32 (tối ưu cho ESP32 mới)"""
        if not self.connected or not self.binary_mode:
            return None
        
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.serial.in_waiting >= 3:  # Cần 3 bytes: [channel][value_high][value_low]
                    # Đọc 3 bytes binary data
                    channel_byte = self.serial.read(1)
                    value_high_byte = self.serial.read(1)
                    value_low_byte = self.serial.read(1)
                    
                    if len(channel_byte) == 1 and len(value_high_byte) == 1 and len(value_low_byte) == 1:
                        channel = channel_byte[0]
                        value = (value_high_byte[0] << 8) | value_low_byte[0]
                        return (channel, value)
            
            return None
        except Exception as e:
            self.log(f"Error reading binary data: {str(e)}")
            return None

    def read_adc_stream(self, timeout: float = 0.05) -> Optional[tuple]:
        """Đọc ADC value từ stream (hỗ trợ cả text và binary)"""
        if not self.connected or not self.streaming:
            return None
        
        # Nếu binary mode, sử dụng binary parser
        if self.binary_mode:
            return self.read_binary_adc_data(timeout)
        
        # Text mode (legacy)
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.serial.in_waiting:
                    try:
                        line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    except UnicodeDecodeError:
                        continue
                    
                    if line.startswith("CH") and ":" in line:
                        try:
                            parts = line.split(":")
                            channel = int(parts[0][2:])  # Bỏ "CH"
                            value = int(parts[1])
                            return (channel, value)
                        except (ValueError, IndexError):
                            continue
            
            return None
        except Exception as e:
            self.log(f"Error reading ADC stream: {str(e)}")
            return None
    
    # ====== PHƯƠNG PHÁP CŨ: THU 12 GIÂY ADC → PHÂN TÍCH VÙNG DÀY ĐẶC ======
    def collect_adc_samples(self, channel: int, duration: float = 12.0) -> List[int]:
        """Thu thập ADC cho 1 kênh trong duration giây (phương pháp cũ)."""
        if not self.connected:
            return []
        if not self.start_streaming(channel):
            return []
        try:
            self.adc_buffer[channel] = []
            start_time = time.time()
            while time.time() - start_time < duration:
                result = self.read_adc_stream(timeout=0.01)
                if result:
                    ch, adc_value = result
                    if ch == channel:
                        self.adc_buffer[channel].append(adc_value)
            return self.adc_buffer[channel]
        finally:
            self.stop_streaming()

    def collect_adc_samples_multi_channel(self, channels: List[int], duration: float = 12.0) -> dict:
        """Thu thập ADC đồng thời cho tối đa 2 kênh trong duration giây, ưu tiên binary + batch read để đủ mẫu."""
        if not self.connected:
            return {ch: [] for ch in channels}
        channels = channels[:2]
        if not self.start_multi_channel_streaming(channels):
            return {ch: [] for ch in channels}
        try:
            # Dùng buffer tạm cục bộ thay vì self.adc_buffer để tránh side effects
            buffers = {ch: [] for ch in channels}
            start_time = time.time()
            # cố gắng dùng binary mode để đọc batch
            self.set_binary_mode(True)
            while time.time() - start_time < duration:
                # Ưu tiên batch read nếu có sẵn dữ liệu (tăng batch-size)
                batch = self.read_batch_adc_data(batch_size=1200)
                if batch:
                    for ch, adc_value in batch:
                        if ch in buffers:
                            buffers[ch].append(adc_value)
                    continue
                # fallback đọc đơn lẻ
                result = self.read_adc_stream(timeout=0.001)
                if result:
                    ch, adc_value = result
                    if ch in buffers:
                        buffers[ch].append(adc_value)
            return buffers
        finally:
            self.stop_streaming()

    def _find_rectangular_regions(self, samples: list) -> dict:
        """Tìm các vùng dày đặc với thuật toán fuzzy rectangles (phương pháp cũ)."""
        threshold = 2700
        sample_rate = 1000  # 1000 samples per second
        min_ms = 300        # thời gian tối thiểu của 1 vùng
        max_gap = 12        # số nhiễu cho phép

        min_samples = int((min_ms / 1000) * sample_rate)
        regions = []

        start = None
        below_count = 0

        for i, val in enumerate(samples):
            if val >= threshold:
                if start is None:
                    start = i
                below_count = 0
            else:
                if start is not None:
                    below_count += 1
                    if below_count > max_gap:
                        end = i - below_count
                        if end - start >= min_samples:
                            regions.append({
                                'start': start,
                                'end': end,
                                'duration': end - start,
                                'start_time': start * 0.001,
                                'end_time': end * 0.001
                            })
                        start = None
                        below_count = 0

        if start is not None:
            end = len(samples)
            if end - start >= min_samples:
                regions.append({
                    'start': start,
                    'end': end,
                    'duration': end - start,
                    'start_time': start * 0.001,
                    'end_time': end * 0.001
                })

        # self.log(f"Tìm thấy {len(regions)} vùng dày đặc:")
        # for i, region in enumerate(regions):
        #     self.log(f"Vùng {i+1}: {region['start_time']:.1f}s - {region['end_time']:.1f}s (duration: {region['duration']*0.001:.1f}s)")

        return self._analyze_rectangular_pattern(regions)

    def analyze_buffered_channel(self, channel: int) -> str:
        """Phân tích self.adc_buffer[channel] và trả về pattern: RINGTONE/BLOCKED/VOICE_MACHINE/SILENCE."""
        if channel not in self.adc_buffer or len(self.adc_buffer[channel]) == 0:
            return "SILENCE"
        samples = self.adc_buffer[channel]
        return self._find_rectangular_regions(samples)["pattern"]

    def detect_pattern_by_stream(self, channel: int, duration: float = 12.0) -> str:
        """Tiện ích: Thu 12s rồi phân tích, trả về pattern (phương pháp cũ)."""
        samples = self.collect_adc_samples(channel, duration=duration)
        if not samples:
            return "SILENCE"
        return self._find_rectangular_regions(samples)["pattern"]

    # def collect_adc_samples_multi_channel_optimized(self, channels: List[int], max_wait_time: float = 25.0) -> bool:
    #     """Thu thập ADC với batch reading (tối ưu hóa cho ESP32 mới)"""
    #     if not self.start_multi_channel_streaming(channels):
    #         return False
        
    #     try:
    #         self.log(f"=== BẮT ĐẦU THU THẬP ADC (BATCH READING) CHO {len(channels)} CHANNELS ===")
    #         self.log(f"Channels: {channels}")
    #         self.log(f"Logic: Clear buffer → Batch reading → Thu đủ 12,000 samples")
            
    #         # Phase 1: Clear buffer nhanh với batch reading
    #         self.log("🧹 Clear buffer với batch reading...")
    #         clear_start = time.time()
    #         while time.time() - clear_start < 1.0:  # Tăng lên 1s để clear buffer tốt hơn
    #             batch = self.read_batch_adc_data(batch_size=100)  # Giảm xuống 100 mẫu/lần
    #             if not batch:
    #                 break
    #             time.sleep(0.01)
            
    #         self.log("✅ Đã clear buffer xong")
            
    #         # Phase 2: Thu thập với batch reading
    #         target_samples = 5000  # Giảm xuống 5000 samples để phù hợp với ESP32 (20s × 250Hz)
    #         self.log(f"📊 Bắt đầu batch reading cho đến khi đủ {target_samples:,} samples...")
    #         collection_start = time.time()
            
    #         # Khởi tạo buffer cho tất cả channels
    #         for channel in channels:
    #             self.adc_buffer[channel] = []
            
    #         sample_count = {ch: 0 for ch in channels}
    #         all_channels_complete = False
            
    #         # Debug counters
    #         batch_count = 0
    #         total_samples_read = 0
            
    #         while time.time() - collection_start < max_wait_time and not all_channels_complete:
    #             # Đọc batch nhỏ để tối ưu với ESP32
    #             batch = self.read_batch_adc_data(batch_size=50)  # 50 mẫu/lần
    #             batch_count += 1
                
    #             if batch:
    #                 total_samples_read += len(batch)
    #                 for ch, adc_value in batch:
    #                     if ch in channels:
    #                         self.adc_buffer[ch].append(adc_value)
    #                         sample_count[ch] += 1
                            
    #                         # Progress check mỗi 500 mẫu
    #                         if sample_count[ch] % 500 == 0:
    #                             elapsed = time.time() - collection_start
    #                             rate = sample_count[ch] / elapsed if elapsed > 0 else 0
    #                             remaining_samples = target_samples - sample_count[ch]
    #                             estimated_time = remaining_samples / rate if rate > 0 else 0
    #                             self.log(f"Channel {ch}: {sample_count[ch]:,} mẫu ({elapsed:.1f}s) - Tốc độ: {rate:.0f} mẫu/s - Còn lại: {remaining_samples:,} mẫu (~{estimated_time:.1f}s)")
                            
    #                         # Kiểm tra đủ samples
    #                         if sample_count[ch] >= target_samples:
    #                             self.log(f"✅ Channel {ch}: Đã thu đủ {sample_count[ch]:,} samples")
                
    #             # In debug mỗi 50 batch
    #             if batch_count % 50 == 0:
    #                 elapsed = time.time() - collection_start
    #                 avg_batch_size = total_samples_read / batch_count if batch_count > 0 else 0
    #                 self.log(f"📊 Debug: {batch_count} batches, {total_samples_read:,} samples, avg batch: {avg_batch_size:.1f} - {elapsed:.1f}s elapsed")
                
    #             # Kiểm tra tất cả channels đã đủ chưa
    #             all_channels_complete = all(sample_count[ch] >= target_samples for ch in channels)
            
    #         collection_time = time.time() - collection_start
    #         self.log(f"✅ Thu thập xong sau {collection_time:.1f}s:")
    #         for ch in channels:
    #             self.log(f"   Channel {ch}: {len(self.adc_buffer[ch]):,} mẫu")
            
    #         # Thống kê hiệu suất batch reading
    #         avg_rate = sum(len(self.adc_buffer[ch]) for ch in channels) / collection_time if collection_time > 0 else 0
    #         self.log(f"📊 THỐNG KÊ BATCH READING:")
    #         self.log(f"   Tổng thời gian: {collection_time:.1f}s")
    #         self.log(f"   Tổng batches: {batch_count}")
    #         self.log(f"   Tổng samples đọc: {total_samples_read:,}")
    #         self.log(f"   Tốc độ trung bình: {avg_rate:.0f} mẫu/s")
    #         self.log(f"   Avg batch size: {total_samples_read/batch_count:.1f}" if batch_count > 0 else "   Avg batch size: 0")
            
    #         # Xuất ADC samples ra file check.txt (chỉ channel đầu tiên)
    #         if channels and len(self.adc_buffer[channels[0]]) > 0:
    #             try:
    #                 with open('check.txt', 'w') as f:
    #                     for adc_value in self.adc_buffer[channels[0]]:
    #                         f.write(f"{adc_value}\n")
    #                 print(f"📄 Đã xuất {len(self.adc_buffer[channels[0]]):,} mẫu ADC (channel {channels[0]}) ra file check.txt")
    #             except Exception as e:
    #                 print(f"❌ Lỗi khi xuất file check.txt: {str(e)}")
            
    #         self.stop_streaming()
            
    #         # Phase 3: Phân tích cho từng channel
    #         results = {}
    #         for channel in channels:
    #             if len(self.adc_buffer[channel]) > 0:
    #                 self.log(f"🔍 PHÂN TÍCH CHANNEL {channel}...")
    #                 pattern = self._analyze_samples(channel)
    #                 results[channel] = pattern
    #                 self.log(f"   Channel {channel}: {pattern}")
    #             else:
    #                 self.log(f"❌ Channel {channel}: Không thu được mẫu!")
    #                 results[channel] = "NO_DATA"
            
    #         # Gọi callback để gửi ADC data nếu có
    #         if self.adc_data_callback and channels and len(self.adc_buffer[channels[0]]) > 0:
    #             # Tạo timestamps cho samples (channel đầu tiên)
    #             timestamps = [i * 0.001 for i in range(len(self.adc_buffer[channels[0]]))]
    #             self.adc_data_callback(self.adc_buffer[channels[0]], timestamps)
            
    #         return True
            
    #     except Exception as e:
    #         self.log(f"Error collecting ADC samples: {str(e)}")
    #         self.stop_streaming()
    #         return False

    # def collect_adc_samples_multi_channel(self, channels: List[int], max_wait_time: float = 25.0) -> bool:
    #     """Thu thập ADC samples cho nhiều channels cùng lúc (tối ưu cho ESP32 mới)"""
    #     if not self.start_multi_channel_streaming(channels):
    #         return False
        
    #     try:
    #         self.log(f"=== BẮT ĐẦU THU THẬP ADC CHO {len(channels)} CHANNELS ===")
    #         self.log(f"Channels: {channels}")
    #         self.log(f"Logic: Clear buffer → Thu đủ 5,000 samples → Phân tích sau")
            
    #         # Phase 1: Clear buffer (không chờ)
    #         self.log("🧹 Clear buffer...")
    #         clear_start = time.time()
    #         while time.time() - clear_start < 1.0:  # Tăng lên 1s để clear buffer tốt hơn
    #             result = self.read_adc_stream(timeout=0.001)  # Giảm timeout xuống 1ms
    #             if result:
    #                 ch, adc_value = result
    #                 if ch in channels:
    #                     # Chỉ đọc để clear buffer, không lưu
    #                     pass
    #             time.sleep(0.01)
            
    #         self.log("✅ Đã clear buffer xong")
            
    #         # Phase 2: Thu thập cho đến khi đủ 5,000 samples
    #         target_samples = 5000  # Mục tiêu 5,000 samples (20s × 250Hz)
    #         self.log(f"📊 Bắt đầu thu thập ADC cho đến khi đủ {target_samples:,} samples...")
    #         collection_start = time.time()
            
    #         # Khởi tạo buffer cho tất cả channels
    #         for channel in channels:
    #             self.adc_buffer[channel] = []
            
    #         sample_count = {ch: 0 for ch in channels}
    #         all_channels_complete = False
            
    #         while time.time() - collection_start < max_wait_time and not all_channels_complete:
    #             # Đọc liên tục không timeout để tăng tốc độ
    #             result = self.read_adc_stream(timeout=0.001)  # Giảm timeout xuống 1ms
    #             if result:
    #                 ch, adc_value = result
    #                 if ch in channels:
    #                     self.adc_buffer[ch].append(adc_value)
    #                     sample_count[ch] += 1
                        
    #                     # In progress mỗi 100 mẫu
    #                     if sample_count[ch] % 100 == 0:
    #                         elapsed = time.time() - collection_start
    #                         self.log(f"Channel {ch}: {sample_count[ch]:,} mẫu ({elapsed:.1f}s)")
                        
    #                     # Kiểm tra xem đã đủ samples chưa
    #                     if sample_count[ch] >= target_samples:
    #                         self.log(f"✅ Channel {ch}: Đã thu đủ {sample_count[ch]:,} samples")
                
    #             # Kiểm tra xem tất cả channels đã đủ chưa
    #             all_channels_complete = all(sample_count[ch] >= target_samples for ch in channels)
            
    #         collection_time = time.time() - collection_start
    #         self.log(f"✅ Thu thập xong sau {collection_time:.1f}s:")
    #         for ch in channels:
    #             self.log(f"   Channel {ch}: {len(self.adc_buffer[ch]):,} mẫu")
            
    #         # Xuất ADC samples ra file check.txt (chỉ channel đầu tiên)
    #         if channels and len(self.adc_buffer[channels[0]]) > 0:
    #             try:
    #                 with open('check.txt', 'w') as f:
    #                     for adc_value in self.adc_buffer[channels[0]]:
    #                         f.write(f"{adc_value}\n")
    #                 print(f"📄 Đã xuất {len(self.adc_buffer[channels[0]]):,} mẫu ADC (channel {channels[0]}) ra file check.txt")
    #             except Exception as e:
    #                 print(f"❌ Lỗi khi xuất file check.txt: {str(e)}")
            
    #         self.stop_streaming()
            
    #         # Phase 3: Phân tích cho từng channel
    #         results = {}
    #         for channel in channels:
    #             if len(self.adc_buffer[channel]) > 0:
    #                 self.log(f"🔍 PHÂN TÍCH CHANNEL {channel}...")
    #                 pattern = self._analyze_samples(channel)
    #                 results[channel] = pattern
    #                 self.log(f"   Channel {channel}: {pattern}")
    #             else:
    #                 self.log(f"❌ Channel {channel}: Không thu được mẫu!")
    #                 results[channel] = "NO_DATA"
            
    #         # Gọi callback để gửi ADC data nếu có
    #         if self.adc_data_callback and channels and len(self.adc_buffer[channels[0]]) > 0:
    #             # Tạo timestamps cho samples (channel đầu tiên)
    #             timestamps = [i * 0.001 for i in range(len(self.adc_buffer[channels[0]]))]
    #             self.adc_data_callback(self.adc_buffer[channels[0]], timestamps)
            
    #         return True
            
    #     except Exception as e:
    #         self.log(f"Error collecting ADC samples: {str(e)}")
    #         self.stop_streaming()
    #         return False

    # def collect_adc_samples_with_detection(self, channel: int, max_wait_time: float = 25.0) -> bool:
    #     """Thu thập ADC samples với logic mới: batch reading (legacy method)"""
    #     return self.collect_adc_samples_multi_channel_optimized([channel], max_wait_time)

    # def collect_adc_samples(self, channel: int, duration: float = 20.0) -> bool:
    #     """Thu thập ADC samples trong thời gian cụ thể (tối ưu cho ESP32 mới)"""
    #     if not self.start_streaming(channel):
    #         return False
        
    #     try:
    #         start_time = time.time()
    #         self.adc_buffer[channel] = []
    #         sample_count = 0
            
    #         print(f"\n=== BẮT ĐẦU THU THẬP ADC CHANNEL {channel} ===")
            
    #         while time.time() - start_time < duration:
    #             result = self.read_adc_stream(timeout=0.05)  # Giảm timeout xuống 0.05s
    #             if result:
    #                 ch, adc_value = result
    #                 if ch == channel:
    #                     self.adc_buffer[channel].append(adc_value)
    #                     sample_count += 1
                        
    #                     # In ra TẤT CẢ mẫu để debug
    #                     print(f"Sample {sample_count}: ADC={adc_value}")
                        
    #                     # Limit buffer size
    #                     if len(self.adc_buffer[channel]) > self.buffer_size:
    #                         self.adc_buffer[channel] = self.adc_buffer[channel][-self.buffer_size:]
            
    #         self.stop_streaming()
            
    #         # In thống kê chi tiết
    #         if len(self.adc_buffer[channel]) > 0:
    #             samples = self.adc_buffer[channel]
    #             min_val = min(samples)
    #             max_val = max(samples)
    #             avg_val = sum(samples) / len(samples)
                
    #             print(f"\n=== THỐNG KÊ ADC CHANNEL {channel} ===")
    #             print(f"Tổng số mẫu: {len(samples)}")
    #             print(f"Min ADC: {min_val}")
    #             print(f"Max ADC: {max_val}")
    #             print(f"Avg ADC: {avg_val:.2f}")
    #             print(f"Amplitude: {max_val - min_val}")
            
    #         self.log(f"Collected {len(self.adc_buffer[channel])} samples for channel {channel}")
    #         return len(self.adc_buffer[channel]) > 0
            
    #     except Exception as e:
    #         self.log(f"Error collecting ADC samples: {str(e)}")
    #         self.stop_streaming()
    #         return False
    
    # def analyze_audio_pattern(self, channel: int = 0) -> str:
    #     """(Không dùng) Cơ chế ESP tự phát hiện - đã bỏ, dùng PC streaming thay thế."""
    #     return "UNSUPPORTED"

    # def analyze_audio_pattern_multi_channel(self, channels: List[int]) -> dict:
    #     """Phân tích pattern âm thanh cho nhiều channels cùng lúc (ESP32 mới)"""
    #     if not self.connected:
    #         return {ch: "ERROR" for ch in channels}
        
    #     # Sequential analysis cho từng channel (ESP32 chỉ hỗ trợ 1 channel tại 1 thời điểm)
    #     results = {}
    #     for channel in channels:
    #         self.log(f"Analyzing channel {channel}...")
    #         results[channel] = self.analyze_audio_pattern(channel)
    #         time.sleep(0.5)  # Delay giữa các channels
        
    #     return results

    # def _check_voice_pattern(self, regions: list, samples: list) -> Optional[str]:
    #     """Kiểm tra pattern lời thoại trước khi post-processing"""
    #     if len(regions) < 3:  # Cần ít nhất 3 vùng để là lời thoại
    #         return None
        
    #     print(f"     Kiểm tra {len(regions)} vùng cho pattern lời thoại...")
        
    #     # Tính khoảng cách giữa các vùng
    #     gaps = []
    #     for i in range(len(regions) - 1):
    #         gap = regions[i+1]['start'] - regions[i]['end']
    #         gaps.append(gap)
        
    #     if len(gaps) < 2:
    #         return None
        
    #     avg_gap = sum(gaps) / len(gaps)
    #     avg_duration = sum(r['duration'] for r in regions) / len(regions)
        
    #     print(f"     Khoảng cách trung bình: {avg_gap*0.001:.1f}s")
    #     print(f"     Thời lượng trung bình: {avg_duration*0.001:.1f}s")
        
    #     # Điều kiện cho lời thoại:
    #     # - Nhiều vùng nhỏ (≥3 vùng)
    #     # - Vùng ngắn (≤1.5s mỗi vùng)
    #     # - Khoảng cách ngắn (≤2s giữa các vùng)
    #     # - Khoảng cách đều đặn (độ lệch chuẩn ≤500ms)
    #     if (len(regions) >= 3 and
    #         avg_duration <= 1500 and      # Vùng ngắn ≤1.5s
    #         avg_gap <= 2000):             # Khoảng cách ngắn ≤2s
            
    #         # Tính độ lệch chuẩn của khoảng cách
    #         import statistics
    #         gap_std = statistics.stdev(gaps)
    #         print(f"     Độ lệch chuẩn khoảng cách: {gap_std*0.001:.1f}s")
            
    #         if gap_std <= 500:  # Khoảng cách đều đặn ≤500ms variation
    #             print(f"     ✅ Phát hiện pattern lời thoại: {len(regions)} vùng nhỏ, khoảng cách đều")
    #             return "VOICE_MACHINE"
        
    #     return None

    def _post_process_regions(self, regions: list, samples: list) -> list:
        """Post-processing: làm sạch và merge vùng dày đặc"""
        if len(regions) == 0:
            return regions
        
        print(f"     Vùng ban đầu: {len(regions)}")
        
        # 1. Loại bỏ vùng nhiễu ngắn (<800ms)
        filtered_regions = []
        for region in regions:
            if region['duration'] >= 800:  # Tối thiểu 800ms
                filtered_regions.append(region)
            else:
                print(f"     Loại bỏ vùng ngắn: {region['start_time']:.1f}s - {region['end_time']:.1f}s ({region['duration']*0.001:.1f}s)")
        
        print(f"     Sau lọc vùng ngắn: {len(filtered_regions)}")
        
        if len(filtered_regions) == 0:
            return filtered_regions
        
        # 2. Merge vùng gần nhau (<1s)
        merged_regions = []
        current_region = filtered_regions[0].copy()
        
        for i in range(1, len(filtered_regions)):
            gap = filtered_regions[i]['start'] - current_region['end']
            
            if gap <= 1000:  # Gap ≤ 1s thì merge
                print(f"     Merge vùng: {current_region['start_time']:.1f}s - {filtered_regions[i]['end_time']:.1f}s (gap: {gap*0.001:.1f}s)")
                current_region['end'] = filtered_regions[i]['end']
                current_region['duration'] = current_region['end'] - current_region['start']
                current_region['end_time'] = current_region['end'] * 0.001
                # Recalculate avg_amplitude
                current_region['avg_amplitude'] = sum(samples[current_region['start']:current_region['end']]) / current_region['duration']
            else:
                # Gap > 1s, tách riêng
                merged_regions.append(current_region)
                current_region = filtered_regions[i].copy()
        
        # Thêm vùng cuối
        merged_regions.append(current_region)
        
        print(f"     Sau merge: {len(merged_regions)}")
        
        # 3. Tách vùng dài (>2.5s) thành vùng nhỏ hơn
        final_regions = []
        for region in merged_regions:
            if region['duration'] > 2500:  # > 2.5s
                print(f"     Tách vùng dài: {region['start_time']:.1f}s - {region['end_time']:.1f}s ({region['duration']*0.001:.1f}s)")
                
                # Tìm điểm có amplitude thấp nhất trong vùng để tách
                region_samples = samples[region['start']:region['end']]
                min_amplitude_idx = region_samples.index(min(region_samples))
                split_point = region['start'] + min_amplitude_idx
                
                # Tách thành 2 vùng
                region1 = {
                    'start': region['start'],
                    'end': split_point,
                    'duration': split_point - region['start'],
                    'start_time': region['start'] * 0.001,
                    'end_time': split_point * 0.001,
                    'avg_amplitude': sum(samples[region['start']:split_point]) / (split_point - region['start'])
                }
                
                region2 = {
                    'start': split_point,
                    'end': region['end'],
                    'duration': region['end'] - split_point,
                    'start_time': split_point * 0.001,
                    'end_time': region['end'] * 0.001,
                    'avg_amplitude': sum(samples[split_point:region['end']]) / (region['end'] - split_point)
                }
                
                if region1['duration'] >= 800:
                    final_regions.append(region1)
                if region2['duration'] >= 800:
                    final_regions.append(region2)
            else:
                final_regions.append(region)
        
        print(f"     Vùng cuối cùng: {len(final_regions)}")
        return final_regions

    # def _find_rectangular_regions(self, samples: list) -> dict:
    #     """Tìm các vùng dày đặc với thuật toán fuzzy rectangles"""
        
    #     # print(f"   🔍 TÌM VÙNG DÀY ĐẶC (FUZZY RECTANGLES)...")
        
    #     threshold = 2700
    #     sample_rate = 1000  # 1000 samples per second
    #     min_ms = 300  # thời gian tối thiểu của 1 vùng
    #     max_gap = 12  # số nhiễu cho phép
        
    #     min_samples = int((min_ms / 1000) * sample_rate)
    #     regions = []
        
    #     start = None
    #     below_count = 0
        
    #     for i, val in enumerate(samples):
    #         if val >= threshold:
    #             if start is None:
    #                 start = i
    #             below_count = 0
    #         else:
    #             if start is not None:
    #                 below_count += 1
    #                 if below_count > max_gap:
    #                     end = i - below_count
    #                     if end - start >= min_samples:
    #                         regions.append({
    #                             'start': start,
    #                             'end': end,
    #                             'duration': end - start,
    #                             'start_time': start * 0.001,
    #                             'end_time': end * 0.001
    #                         })
    #                     start = None
    #                     below_count = 0
        
    #     # Xử lý vùng cuối cùng
    #     if start is not None:
    #         end = len(samples)
    #         if end - start >= min_samples:
    #             regions.append({
    #                 'start': start,
    #                 'end': end,
    #                 'duration': end - start,
    #                 'start_time': start * 0.001,
    #                 'end_time': end * 0.001
    #             })
        
    #     self.log(f"Tìm thấy {len(regions)} vùng dày đặc:")
    #     for i, region in enumerate(regions):
    #         self.log(f"Vùng {i+1}: {region['start_time']:.1f}s - {region['end_time']:.1f}s (duration: {region['duration']*0.001:.1f}s)")
        
    #     return self._analyze_rectangular_pattern(regions)

    def _analyze_rectangular_pattern(self, regions: list) -> dict:
        """Phân tích pattern dựa trên các vùng dày đặc"""
        if len(regions) == 0:
            # self.log(f"✅ Không tìm thấy vùng dày đặc → SILENCE")
            return {
                "regions": [],
                "pattern": "SILENCE",
                "region_count": 0
            }
        
        # print(f"   🔍 PHÂN TÍCH {len(regions)} VÙNG DÀY ĐẶC...")
        
        # Khởi tạo pattern với giá trị mặc định
        pattern = "RINGTONE"
        
        # Phân loại dựa trên số lượng và đặc điểm vùng
        if len(regions) == 1:
            # Kiểm tra thời lượng vùng
            duration = regions[0]['duration'] * 0.001  # Chuyển sang giây
            if duration > 3.5:  # > 3.5 giây
                print(f"   ✅ Vùng dài ({duration:.1f}s) → BLOCKED")
                pattern = "BLOCKED"
            else:
                pattern = "RINGTONE"
                
        elif len(regions) >= 2:
            # Tính khoảng cách giữa các vùng
            gaps = []
            for i in range(len(regions) - 1):
                gap = (regions[i+1]['start'] - regions[i]['end']) * 0.001  # Chuyển sang giây
                gaps.append(gap)
            
            avg_gap = sum(gaps) / len(gaps)
            avg_duration = sum(r['duration'] * 0.001 for r in regions) / len(regions)
            
            # self.log(f"Khoảng cách trung bình: {avg_gap:.1f}s")
            # self.log(f"Thời lượng trung bình: {avg_duration:.1f}s")
            
            # Điều kiện cho chuông "tu...tu"
            if (avg_duration <= 2.0 and  # Mỗi vùng ≤ 2s
                4.0 <= avg_gap <= 6.0):   # Khoảng cách 4-6s
                self.log(f"✅ Pattern chuông → RINGTONE")
                pattern = "RINGTONE"
            # điều kiện là voice_machine, giọng máy thuê bao quý khách vừa gọi. có từ 4 vùng trở lên, mỗi vùng ngắn từ 0.3s- 1s,
            #  khoảng cách đều đặn trung bình <= 1,2s
            elif len(regions) >= 4 and 0.3 <= avg_duration <= 1 and avg_gap <= 1.2:
                self.log(f"✅ Pattern lời thoại → VOICE_MACHINE")
                pattern = "VOICE_MACHINE"
            # điều kiện số bị chặn "tu..." <0.8-1 giây> <nghỉ 0.3-1 giây> "quý khách vui lòng đề lại lời nhắn...." 
            elif len(regions) >= 3 and 0.8 <= avg_duration <= 1 and 0.3 <= avg_gap <= 1:
                self.log(f"✅ Pattern đã chặn → BLOCKED")
                pattern = "BLOCKED"
            #còn lại có thể là nhạc chuông, bài hát... nhiều vùng mỗi vùng dài ngắn không đều và khoảng cách cũng không đều.
            else:
                self.log(f"✅ Pattern chuông → RINGTONE")
                pattern = "RINGTONE"
        
        return {
            "regions": regions,
            "pattern": pattern,
            "region_count": len(regions)
        }

    # def _analyze_samples(self, channel: int) -> str:
    #     """Phân tích ADC samples"""
    #     if channel not in self.adc_buffer or len(self.adc_buffer[channel]) == 0:
    #         return "ERROR"
        
    #     samples = self.adc_buffer[channel]
        
    #     # Tính toán thống kê
    #     min_val = min(samples)
    #     max_val = max(samples)
    #     amplitude = max_val - min_val
        
    #     # Tính frequency (zero crossings)
    #     zero_crossings = 0
    #     middle_value = 2048  # ADC middle value
        
    #     for i in range(1, len(samples)):
    #         if ((samples[i-1] < middle_value and samples[i] >= middle_value) or 
    #             (samples[i-1] >= middle_value and samples[i] < middle_value)):
    #             zero_crossings += 1
        
    #     frequency = (zero_crossings * 1000) / (2.0 * len(samples))  # Hz
        
    #     # Tính silence ratio
    #     silence_count = sum(1 for s in samples if abs(s - middle_value) < 500)
    #     silence_ratio = silence_count / len(samples)
        
    #     # Debug info
    #     self.log(f"Channel {channel} - Amp:{amplitude} Freq:{frequency:.2f} Silence:{silence_ratio:.2f}")
        
    #     # Sử dụng thuật toán mới: tìm vùng hình chữ nhật
    #     rectangular_analysis = self._find_rectangular_regions(samples)
        
    #     # Trả về kết quả từ phân tích vùng hình chữ nhật
    #     return rectangular_analysis["pattern"]
        
    #     # # Sử dụng thuật toán cũ: tìm vùng dày đặc (đã comment)
    #     # dense_analysis = self._find_dense_regions(samples)
    #     # return dense_analysis["pattern"]
    
    # def test_connection(self) -> bool:
    #     """(Không dùng) Test detection mode - đã bỏ."""
    #     return False
    
    def get_status(self) -> dict:
        """Lấy trạng thái ESP32 (ESP32 mới)"""
        return {
            "connected": self.connected,
            "port": self.port,
            "baudrate": self.baudrate,
            "streaming": self.streaming,
            "total_channels": self.total_channels,
            "active_channels": self.active_channels,
            "max_active_channels": self.max_active_channels,
            "binary_mode": self.binary_mode,
            "buffer_size": self.buffer_size,
            "system_type": "ESP32_Streamer_2ch",
            "detection_time": None,
            "supported_results": []
        }
    
    # def check_detection_status(self) -> dict:
    #     """(Không dùng) Detection status - đã bỏ."""
    #     return {"error": "unsupported"}
    
    # def stop_detection(self) -> bool:
    #     """(Không dùng) Dừng detection - đã bỏ."""
    #     return False
    
    # def cancel_detection(self, channel: int = None) -> bool:
    #     """(Không dùng) Hủy detection - đã bỏ."""
    #     return False

    def quick_adc_test(self, channel: int = 0, num_samples: int = 500):
        """Đọc nhanh num_samples giá trị ADC và in ra terminal (tối ưu cho ESP32 mới)"""
        if not self.connected:
            print("ESP32 chưa kết nối!")
            return
        if not self.start_streaming(channel):
            print("Không thể bắt đầu streaming!")
            return
        print(f"=== QUICK ADC TEST: Đọc {num_samples} mẫu từ channel {channel} ===")
        samples = []
        for i in range(num_samples):
            result = self.read_adc_stream(timeout=0.05)  # Giảm timeout xuống 0.05s
            if result:
                ch, adc_value = result
                if ch == channel:
                    samples.append(adc_value)
                    print(f"Sample {i+1}: ADC={adc_value}")
        self.stop_streaming()
        if samples:
            print(f"Min: {min(samples)}, Max: {max(samples)}, Avg: {sum(samples)/len(samples):.2f}")
            # print(f"20 mẫu đầu: {samples[:20]}")
            # print(f"20 mẫu cuối: {samples[-20:]}")
        else:
            print("Không thu được mẫu ADC nào!")
    
    # def test_detection_parameters(self, channel: int = 0, max_wait_time: float = 15.0):
    #     """(Không dùng) Test tham số detection - đã bỏ."""
    #     return
    
    # def check_channel_and_wait_result(self, channel: int) -> str:
    #     """(Không dùng) Chế độ ESP tự detect - đã bỏ."""
    #     return "ERROR"