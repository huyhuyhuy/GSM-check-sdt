#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thu âm tự động từ jack 3.5mm khi gọi điện thoại qua GSM
- Luôn nghe audio từ jack 3.5mm
- Đọc danh sách số từ list_viettel.txt
- Gọi số qua GSM cổng COM132
- Thu âm 15 giây và lưu file
"""

import pyaudio
import wave
import serial
import time
import threading
import queue
from datetime import datetime
import os
import sys

class AudioRecorder:
    """Class để thu âm liên tục từ jack 3.5mm"""
    
    def __init__(self, sample_rate=44100, channels=2, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16
        
        self.pyaudio_instance = None
        self.stream = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.recording_thread = None
        
    def start_continuous_recording(self):
        """Bắt đầu thu âm liên tục"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Kiểm tra audio device
            if self.pyaudio_instance.get_device_count() == 0:
                print("❌ Không tìm thấy audio device!")
                return False
            
            print("🎤 Khởi tạo audio stream...")
            self.stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_callback
            )
            
            self.is_recording = True
            self.recording_thread = threading.Thread(target=self._recording_worker, daemon=True)
            self.recording_thread.start()
            
            print("✅ Đã bắt đầu thu âm liên tục từ jack 3.5mm")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khởi tạo audio: {e}")
            return False
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback cho audio stream"""
        if self.is_recording:
            self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def _recording_worker(self):
        """Worker thread để xử lý audio data"""
        while self.is_recording:
            try:
                # Lấy data từ queue và xử lý
                if not self.audio_queue.empty():
                    data = self.audio_queue.get_nowait()
                    # Có thể xử lý real-time ở đây nếu cần
                else:
                    time.sleep(0.01)  # Tránh CPU cao
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                print(f"⚠️ Lỗi trong recording worker: {e}")
    
    def save_recording(self, filename, duration_seconds=15):
        """Lưu đoạn thu âm với thời gian chỉ định"""
        print(f"🎵 Bắt đầu lưu thu âm {duration_seconds}s...")
        
        frames = []
        start_time = time.time()
        
        # Thu thập frames trong thời gian chỉ định
        while time.time() - start_time < duration_seconds:
            try:
                if not self.audio_queue.empty():
                    data = self.audio_queue.get_nowait()
                    frames.append(data)
                else:
                    time.sleep(0.01)
            except queue.Empty:
                time.sleep(0.01)
        
        # Lưu file WAV
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            
            print(f"✅ Đã lưu file: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi lưu file {filename}: {e}")
            return False
    
    def stop_recording(self):
        """Dừng thu âm"""
        self.is_recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        print("🛑 Đã dừng thu âm")

class GSMController:
    """Class để điều khiển GSM qua cổng COM132"""
    
    def __init__(self, port="COM132", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_connected = False
    
    def connect(self):
        """Kết nối đến GSM"""
        try:
            print(f"📡 Đang kết nối GSM cổng {self.port}...")
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=5,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Test kết nối
            time.sleep(1)
            self.send_command("AT", 1.0)
            
            self.is_connected = True
            print(f"✅ Đã kết nối GSM cổng {self.port}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi kết nối GSM: {e}")
            return False
    
    def send_command(self, command, wait_time=1.0):
        """Gửi lệnh AT"""
        if not self.is_connected:
            return "ERROR: Not connected"
        
        try:
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            if command:
                self.serial_connection.write((command + '\r\n').encode())
                time.sleep(wait_time)
            
            response = ""
            if self.serial_connection.in_waiting:
                response = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
            
            return response.strip()
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def make_call(self, phone_number):
        """Gọi số điện thoại"""
        if not self.is_connected:
            return False
        
        try:
            print(f"📞 Đang gọi số: {phone_number}")
            
            # Gửi lệnh gọi
            response = self.send_command(f"ATD{phone_number};", 0.5)
            print(f"📡 Response: {response}")
            
            return True
            
        except Exception as e:
            print(f"❌ Lỗi gọi số {phone_number}: {e}")
            return False
    
    def hangup_call(self):
        """Cúp máy"""
        if not self.is_connected:
            return False
        
        try:
            print("📞 Đang cúp máy...")
            response = self.send_command("ATH", 1.0)
            print(f"📡 Hangup response: {response}")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi cúp máy: {e}")
            return False
    
    def disconnect(self):
        """Ngắt kết nối"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
        print("📡 Đã ngắt kết nối GSM")

def load_phone_numbers(filename="list_viettel.txt"):
    """Đọc danh sách số điện thoại từ file"""
    phone_numbers = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    phone_numbers.append(line)
        
        print(f"📋 Đã đọc {len(phone_numbers)} số điện thoại từ {filename}")
        return phone_numbers
        
    except Exception as e:
        print(f"❌ Lỗi đọc file {filename}: {e}")
        return []

def main():
    """Hàm chính"""
    print("🎵 THU ÂM TỰ ĐỘNG TỪ JACK 3.5MM")
    print("=" * 50)
    
    # Khởi tạo audio recorder
    audio_recorder = AudioRecorder()
    
    # Bắt đầu thu âm liên tục
    if not audio_recorder.start_continuous_recording():
        print("❌ Không thể khởi tạo audio recorder!")
        return
    
    # Khởi tạo GSM controller
    gsm = GSMController(port="COM132")
    
    # Kết nối GSM
    if not gsm.connect():
        print("❌ Không thể kết nối GSM!")
        audio_recorder.stop_recording()
        return
    
    # Đọc danh sách số điện thoại
    phone_numbers = load_phone_numbers("list_viettel.txt")
    if not phone_numbers:
        print("❌ Không có số điện thoại nào để gọi!")
        gsm.disconnect()
        audio_recorder.stop_recording()
        return
    
    print(f"\n🚀 Bắt đầu gọi {len(phone_numbers)} số điện thoại...")
    print("=" * 50)
    
    # Xử lý từng số điện thoại
    for i, phone_number in enumerate(phone_numbers, 1):
        print(f"\n📞 [{i}/{len(phone_numbers)}] Xử lý số: {phone_number}")
        
        try:
            # Gọi số
            if gsm.make_call(phone_number):
                print("⏱️ Chờ 0.5s trước khi bắt đầu thu âm...")
                time.sleep(0.5)
                
                # Tạo tên file với timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{phone_number}_{timestamp}.wav"
                
                # Thu âm 15 giây
                print(f"🎵 Thu âm 15 giây...")
                if audio_recorder.save_recording(filename, duration_seconds=15):
                    print(f"✅ Đã lưu: {filename}")
                else:
                    print(f"❌ Lỗi lưu file: {filename}")
                
                # Cúp máy
                gsm.hangup_call()
                
                # Nghỉ 2 giây trước khi gọi số tiếp theo
                print("⏱️ Nghỉ 2s trước khi gọi số tiếp theo...")
                time.sleep(2)
            
            else:
                print(f"❌ Không thể gọi số {phone_number}")
        
        except KeyboardInterrupt:
            print("\n🛑 Người dùng dừng chương trình!")
            break
        except Exception as e:
            print(f"❌ Lỗi xử lý số {phone_number}: {e}")
            continue
    
    # Kết thúc
    print("\n🏁 Hoàn thành tất cả cuộc gọi!")
    gsm.disconnect()
    audio_recorder.stop_recording()
    print("👋 Tạm biệt!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Chương trình bị dừng bởi người dùng!")
    except Exception as e:
        print(f"❌ Lỗi không mong muốn: {e}")
    finally:
        print("🧹 Đang dọn dẹp...")
        sys.exit(0)
