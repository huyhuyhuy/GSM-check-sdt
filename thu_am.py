#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thu âm tự động từ jack 3.5mm khi gọi điện thoại qua GSM
- Luôn nghe audio từ jack 3.5mm
- Đọc danh sách số từ list_viettel.txt
- Gọi số qua GSM cổng COM38
- Thu âm 15 giây và lưu file
"""

import pyaudio
import wave
import serial
import time
import threading
from datetime import datetime
import os
import sys

class AudioRecorder:
    """Class để thu âm từ jack 3.5mm khi cần thiết"""
    
    def __init__(self, sample_rate=44100, channels=2, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16
        
        self.pyaudio_instance = None
        self.is_initialized = False
        
    def initialize(self):
        """Khởi tạo PyAudio"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Kiểm tra audio device
            if self.pyaudio_instance.get_device_count() == 0:
                print("❌ Không tìm thấy audio device!")
                return False
            
            print("🎤 Khởi tạo audio system...")
            self.is_initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khởi tạo audio: {e}")
            return False
    
    def record_audio(self, filename, duration_seconds=15):
        """Thu âm trực tiếp với thời gian chỉ định"""
        if not self.is_initialized:
            print("❌ Audio chưa được khởi tạo!")
            return False
        
        print(f"🎵 Bắt đầu thu âm {duration_seconds}s...")
        
        try:
            # Mở stream để thu âm
            stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            frames = []
            total_chunks = int(self.sample_rate / self.chunk_size * duration_seconds)
            
            # Thu âm từng chunk
            for i in range(total_chunks):
                data = stream.read(self.chunk_size)
                frames.append(data)
                
                # Hiển thị tiến trình
                if i % (total_chunks // 10) == 0:
                    progress = (i / total_chunks) * 100
                    print(f"   📊 Tiến trình: {progress:.0f}%")
            
            # Đóng stream
            stream.stop_stream()
            stream.close()
            
            # Lưu file WAV
            print(f"💾 Đang lưu file: {filename}")
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
            
            print(f"✅ Đã lưu file: {filename} ({duration_seconds}s)")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi thu âm: {e}")
            return False
    
    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        print("🛑 Đã dọn dẹp audio system")

class GSMController:
    """Class để điều khiển GSM qua cổng COM38"""
    
    def __init__(self, port="COM38", baudrate=115200):
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
    
    # Khởi tạo audio system
    if not audio_recorder.initialize():
        print("❌ Không thể khởi tạo audio system!")
        return
    
    # Khởi tạo GSM controller
    gsm = GSMController(port="COM38")
    
    # Kết nối GSM
    if not gsm.connect():
        print("❌ Không thể kết nối GSM!")
        audio_recorder.cleanup()
        return
    
    # Đọc danh sách số điện thoại
    phone_numbers = load_phone_numbers("list_viettel.txt")
    if not phone_numbers:
        print("❌ Không có số điện thoại nào để gọi!")
        gsm.disconnect()
        audio_recorder.cleanup()
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
                
                # Thu âm 15 giây trực tiếp
                if audio_recorder.record_audio(filename, duration_seconds=15):
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
    audio_recorder.cleanup()
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
