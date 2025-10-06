"""
GSM Instance - Quản lý từng thực thể GSM độc lập
Mỗi instance có kết nối riêng, baudrate riêng, và xử lý riêng
"""

import serial
import time
import logging
import threading
import os
import re
import subprocess
from typing import Dict, List, Optional, Callable
from pathlib import Path
from datetime import datetime

# Import cho STT và phân loại
import torch
import librosa
import soundfile as sf
from pydub import AudioSegment

from string_detection import keyword_in_text, labels
from model_manager import model_manager

# Cấu hình logging - ghi ra file
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

class GSMInstance:
    """Quản lý một thực thể GSM với đầy đủ chức năng"""

    def __init__(self, port: str, log_callback: Optional[Callable] = None):
        self.port = port
        self.log_callback = log_callback
        self.serial_connection = None
        self.is_connected = False

        # Thông tin cơ bản
        self.signal_strength = "Không xác định"
        self.network_operator = "Không xác định"
        self.phone_number = "Không xác định"
        self.balance = "Không xác định"

        # Quản lý baudrate
        self.default_baudrate = 115200
        self.working_baudrate = 921600
        self.current_baudrate = self.default_baudrate

        # Quản lý cuộc gọi
        self.phone_queue = []
        self.call_count = 0
        self.max_calls_before_reset = 100
        self.status = "idle"  # idle, calling, resetting, error
        self.results = []

        # Threading
        self.processing_thread = None
        self.stop_flag = False

        # Logging riêng cho instance này
        self.logger = logging.getLogger(f"GSMInstance_{port}")
        log_file = os.path.join(log_dir, f"gsm_{port}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
    def log(self, message: str):
        """Gửi log message"""
        # Log vào file
        self.logger.info(message)

        # Gửi lên GUI nếu có callback
        if self.log_callback:
            self.log_callback(f"[{self.port}] {message}")
    
    def connect(self, baudrate: int = None) -> bool:
        """Kết nối với baudrate cụ thể"""
        if baudrate is None:
            baudrate = self.current_baudrate
            
        try:
            # Đóng kết nối cũ nếu có
            self.disconnect()
            
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=baudrate,
                timeout=5,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            self.is_connected = True
            self.current_baudrate = baudrate
            self.log(f"✅ Kết nối thành công với baudrate {baudrate}")
            return True
            
        except Exception as e:
            self.log(f"❌ Lỗi kết nối: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Ngắt kết nối"""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
            except:
                pass
        self.is_connected = False
    
    def send_command(self, command: str, wait_time: float = 1.0) -> str:
        """Gửi lệnh AT và nhận phản hồi"""
        if not self.is_connected:
            return "ERROR: Not connected"
        
        try:
            # Xóa buffer
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Gửi lệnh
            if command:
                self.serial_connection.write((command + '\r\n').encode())
                time.sleep(wait_time)
            
            # Đọc phản hồi
            response = ""
            start_time = time.time()
            timeout = wait_time + 2
            
            while time.time() - start_time < timeout:
                if self.serial_connection.in_waiting:
                    chunk = self.serial_connection.read(
                        self.serial_connection.in_waiting
                    ).decode('utf-8', errors='ignore')
                    response += chunk
                time.sleep(0.1)
            
            return response.strip()
            
        except Exception as e:
            self.log(f"❌ Lỗi gửi lệnh {command}: {e}")
            return f"ERROR: {str(e)}"
    
    def get_basic_info(self) -> Dict[str, str]:
        """Lấy thông tin cơ bản: tín hiệu, nhà mạng, số điện thoại, số dư"""
        try:
            self.log("📋 Đang lấy thông tin cơ bản...")
            
            # Lấy tín hiệu sóng
            signal_response = self.send_command("AT+CSQ")
            if "+CSQ" in signal_response:
                try:
                    parts = signal_response.split("+CSQ: ")[1].split(",")
                    rssi = int(parts[0])
                    if rssi != 99:
                        self.signal_strength = f"{rssi}/31"
                    else:
                        self.signal_strength = "Không xác định"
                except:
                    self.signal_strength = "Không xác định"
            
            # Lấy nhà mạng
            operator_response = self.send_command("AT+COPS?")
            if "+COPS" in operator_response:
                try:
                    start = operator_response.find('"')
                    end = operator_response.rfind('"')
                    if start != -1 and end != -1:
                        operator = operator_response[start+1:end].strip()
                        if ' ' in operator:
                            operator = operator.split()[0]
                        self.network_operator = operator
                except:
                    self.network_operator = "Không xác định"
            
            # Lấy số điện thoại và số dư qua USSD
            ussd_command = "*101#"  # Mặc định
            if "Vietnamobile" in self.network_operator:
                ussd_command = "*102#"
            
            ussd_response = self.send_command(f'AT+CUSD=1,"{ussd_command}",15', wait_time=3.0)
            
            # Parse USSD response
            import re
            phone_match = re.search(r'\+84\d{9,10}', ussd_response)
            if phone_match:
                self.phone_number = phone_match.group(0)
            
            balance_match = re.search(r'TKC\s+(\d+)\s+d', ussd_response)
            if balance_match:
                balance_amount = balance_match.group(1)
                self.balance = f"{balance_amount} VND"
            
            self.log(f"📊 Thông tin: {self.phone_number} - {self.balance} - {self.network_operator}")
            
            return {
                "signal": self.signal_strength,
                "network_operator": self.network_operator,
                "phone_number": self.phone_number,
                "balance": self.balance
            }
            
        except Exception as e:
            self.log(f"❌ Lỗi lấy thông tin cơ bản: {e}")
            return {
                "signal": "Lỗi",
                "network_operator": "Lỗi",
                "phone_number": "Lỗi",
                "balance": "Lỗi"
            }
    
    def reset_baudrate(self, new_baudrate: int) -> bool:
        """Reset baudrate: đóng → kết nối 115200 → reset → kết nối new_baudrate"""
        try:
            self.status = "resetting"
            self.log(f"🔄 Đang reset baudrate từ {self.current_baudrate} → {new_baudrate}")
            
            # Bước 1: Đóng kết nối hiện tại
            self.disconnect()
            time.sleep(0.5)
            
            # Bước 2: Kết nối với baudrate mặc định
            if not self.connect(self.default_baudrate):
                self.log("❌ Không thể kết nối với baudrate mặc định")
                return False
            
            # Bước 3: Reset baudrate
            reset_response = self.send_command(f"AT+IPR={new_baudrate}", wait_time=2.0)
            if "ERROR" in reset_response:
                self.log("❌ Lỗi reset baudrate")
                return False
            
            # Bước 4: Đóng và kết nối lại với baudrate mới
            self.disconnect()
            time.sleep(0.5)
            
            if not self.connect(new_baudrate):
                self.log("❌ Không thể kết nối với baudrate mới")
                return False
            
            self.log(f"✅ Reset baudrate thành công: {new_baudrate}")
            self.status = "idle"
            return True
            
        except Exception as e:
            self.log(f"❌ Lỗi reset baudrate: {e}")
            self.status = "error"
            return False
    
    def make_call_and_classify(self, phone_number: str) -> Dict:
        """Gọi số và phân loại kết quả"""
        try:
            self.status = "calling"
            self.log(f"📞 Đang gọi {phone_number}...")
            
            # Thực hiện cuộc gọi
            call_response = self.send_command(f"ATD{phone_number};", wait_time=1.5)
            if "ERROR" in call_response:
                self.log(f"❌ Không thể gọi {phone_number}")
                return {
                    "phone_number": phone_number,
                    "result": "can_not_connect",
                    "reason": "Không thể kết nối"
                }
            
            # Chờ 1.5 giây sau khi gọi
            time.sleep(1.5)
            
            # Bắt đầu ghi âm
            self.log(f"🎙️ Bắt đầu ghi âm {phone_number}...")
            record_filename = f"record_{self.port}_{int(time.time())}.amr"
            record_response = self.send_command(f'AT+QAUDRD=1,"{record_filename}",13,1', wait_time=1.0)
            
            if "ERROR" in record_response:
                self.log(f"❌ Không thể bắt đầu ghi âm cho {phone_number}")
                self.send_command("ATH", wait_time=1.0)
                return {
                    "phone_number": phone_number,
                    "result": "lỗi",
                    "reason": "Không thể ghi âm"
                }
            
            # Ghi âm 15 giây và check AT+CLCC mỗi 0.5 giây
            found_colp = False
            recording_duration = 15  # giây
            check_interval = 0.5  # giây
            checks = int(recording_duration / check_interval)
            
            for i in range(checks):
                # Check AT+CLCC
                clcc_response = self.send_command("AT+CLCC", wait_time=0.3)
                
                # Kiểm tra có +COLP trong response
                if "+COLP" in clcc_response:
                    self.log(f"✅ Phát hiện +COLP cho {phone_number} - Người nhấc máy!")
                    found_colp = True
                    
                    # Dừng ghi âm ngay
                    self.send_command(f'AT+QAUDRD=0,"{record_filename}",13,1', wait_time=1.0)
                    
                    # Ngắt cuộc gọi
                    self.send_command("ATH", wait_time=1.0)
                    
                    # Xóa file ghi âm vì không cần
                    self.send_command(f'AT+QFDEL="{record_filename}"', wait_time=1.0)
                    
                    return {
                        "phone_number": phone_number,
                        "result": "hoạt động",
                        "reason": "Có người nhấc máy (+COLP detected)"
                    }
                
                # Đợi trước khi check tiếp
                time.sleep(check_interval)
            
            # Sau 15 giây không có +COLP
            self.log(f"⏱️ Hết thời gian ghi âm cho {phone_number} - Không phát hiện +COLP")
            
            # Dừng ghi âm
            stop_response = self.send_command(f'AT+QAUDRD=0,"{record_filename}",13,1', wait_time=1.0)
            
            # Ngắt cuộc gọi
            self.send_command("ATH", wait_time=1.0)
            
            # Tải file ghi âm, STT và phân loại
            self.log(f"📥 Đang tải file {record_filename} để phân tích...")
            
            # Tạo tên file local
            timestamp = int(time.time())
            local_amr = f"{phone_number}_{self.port}_{timestamp}.amr"
            local_wav = f"{phone_number}_{self.port}_{timestamp}.wav"
            
            # Tải file từ module về máy tính
            if not self._download_file_via_qfread(record_filename, local_amr):
                self.log(f"❌ Không thể tải file {record_filename}")
                return {
                    "phone_number": phone_number,
                    "result": "lỗi",
                    "reason": "Không thể tải file ghi âm"
                }

            # Kiểm tra file AMR có hợp lệ không (file size > 0)
            if not os.path.exists(local_amr):
                self.log(f"❌ File {local_amr} không tồn tại")
                return {
                    "phone_number": phone_number,
                    "result": "lỗi",
                    "reason": "File ghi âm không tồn tại"
                }

            file_size = os.path.getsize(local_amr)
            if file_size == 0:
                self.log(f"❌ File {local_amr} có kích thước 0 bytes")
                # Xóa file lỗi
                try:
                    os.remove(local_amr)
                except:
                    pass
                return {
                    "phone_number": phone_number,
                    "result": "lỗi",
                    "reason": "File ghi âm rỗng (0 bytes)"
                }

            self.log(f"✅ File AMR hợp lệ: {file_size} bytes")

            # Convert AMR sang WAV
            if not self._convert_to_wav(local_amr, local_wav):
                self.log(f"❌ Không thể convert file âm thanh")
                return {
                    "phone_number": phone_number,
                    "result": "lỗi",
                    "reason": "Không thể convert file âm thanh"
                }
            
            # Speech-to-text
            transcribed_text = self._transcribe_audio(local_wav)
            if not transcribed_text:
                self.log(f"❌ Không thể thực hiện STT")
                return {
                    "phone_number": phone_number,
                    "result": "lỗi",
                    "reason": "Không thể thực hiện STT"
                }
            
            # Phân loại kết quả
            classification_result = self._classify_result(transcribed_text)
            
            # Dọn dẹp file tạm
            try:
                if os.path.exists(local_amr):
                    os.remove(local_amr)
                if os.path.exists(local_wav):
                    os.remove(local_wav)
                self.log(f"🗑️ Đã dọn dẹp file tạm")
            except:
                pass
            
            # Xóa file trên module
            self.send_command(f'AT+QFDEL="{record_filename}"', wait_time=1.0)
            
            return {
                "phone_number": phone_number,
                "result": classification_result,
                "reason": f"STT: {transcribed_text[:50]}..." if len(transcribed_text) > 50 else f"STT: {transcribed_text}",
                "transcribed_text": transcribed_text
            }
                
        except Exception as e:
            self.log(f"❌ Lỗi khi gọi {phone_number}: {e}")
            # Đảm bảo ngắt cuộc gọi nếu có lỗi
            try:
                self.send_command("ATH", wait_time=1.0)
            except:
                pass
            
            return {
                "phone_number": phone_number,
                "result": "lỗi",
                "reason": f"Lỗi: {e}"
            }
        finally:
            self.status = "idle"
    
    def set_phone_queue(self, phone_numbers: List[str]):
        """Thiết lập danh sách số điện thoại cần gọi"""
        self.phone_queue = phone_numbers.copy()
        self.call_count = 0
        self.results = []
        self.log(f"📋 Đã nhận {len(phone_numbers)} số điện thoại")
    
    def start_processing(self):
        """Bắt đầu xử lý danh sách số điện thoại"""
        if not self.phone_queue:
            self.log("⚠️ Không có số điện thoại để xử lý")
            return
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.log("⚠️ Đang xử lý rồi")
            return
        
        self.stop_flag = False
        self.processing_thread = threading.Thread(target=self._process_phones, daemon=True)
        self.processing_thread.start()
    
    def _process_phones(self):
        """Xử lý danh sách số điện thoại trong thread riêng"""
        try:
            self.log(f"🚀 Bắt đầu xử lý {len(self.phone_queue)} số điện thoại")
            self.log(f"ℹ️ Đang sử dụng baudrate {self.current_baudrate} cho việc gọi")
            
            for phone_number in self.phone_queue:
                if self.stop_flag:
                    self.log("🛑 Dừng xử lý theo yêu cầu")
                    break
                
                # Gọi và phân loại
                result = self.make_call_and_classify(phone_number)
                self.results.append(result)
                self.call_count += 1
                
                self.log(f"📊 [{self.call_count}/{len(self.phone_queue)}] {phone_number}: {result['result']}")
                
                # Reset sau 100 cuộc gọi
                if self.call_count % self.max_calls_before_reset == 0:
                    self.log(f"🔄 Đã gọi {self.call_count} số, đang reset...")
                    self._reset_and_continue()
                
                # Nghỉ giữa các cuộc gọi
                time.sleep(2)
            
            self.log(f"✅ Hoàn thành xử lý {len(self.results)} số điện thoại")
            
        except Exception as e:
            self.log(f"❌ Lỗi trong quá trình xử lý: {e}")
        finally:
            self.status = "idle"
    
    def _reset_and_continue(self):
        """Reset module và tiếp tục với baudrate mặc định"""
        try:
            # Reset về baudrate mặc định
            if not self.reset_baudrate(self.default_baudrate):
                self.log("❌ Không thể reset về baudrate mặc định")
                return
            
            # Load lại số dư với baudrate mặc định
            self.log("💰 Đang load lại số dư...")
            ussd_command = "*101#"  # Mặc định
            if "Vietnamobile" in self.network_operator:
                ussd_command = "*102#"
            
            balance_response = self.send_command(f'AT+CUSD=1,"{ussd_command}",15', wait_time=3.0)
            
            # Parse số dư mới
            import re
            balance_match = re.search(r'TKC\s+(\d+)\s+d', balance_response)
            if balance_match:
                balance_amount = balance_match.group(1)
                self.balance = f"{balance_amount} VND"
                self.log(f"💰 Số dư mới: {self.balance}")
            else:
                self.log("⚠️ Không thể lấy số dư mới")
            
            # Nghỉ ngơi 30 giây
            self.log("😴 Nghỉ ngơi 30 giây...")
            time.sleep(30)
            
            # Reset về baudrate làm việc
            if not self.reset_baudrate(self.working_baudrate):
                self.log("❌ Không thể reset về baudrate làm việc")
                return
            
        except Exception as e:
            self.log(f"❌ Lỗi trong quá trình reset: {e}")
    
    def stop_processing(self):
        """Dừng xử lý"""
        self.stop_flag = True
        self.status = "idle"
        self.log("🛑 Đã yêu cầu dừng xử lý")
    
    def get_results(self) -> List[Dict]:
        """Lấy kết quả xử lý"""
        return self.results.copy()
    
    def get_status(self) -> Dict:
        """Lấy trạng thái hiện tại"""
        return {
            "port": self.port,
            "status": self.status,
            "call_count": self.call_count,
            "queue_remaining": len(self.phone_queue) - self.call_count,
            "results_count": len(self.results),
            "current_baudrate": self.current_baudrate,
            "is_connected": self.is_connected,
            "signal": self.signal_strength,
            "network_operator": self.network_operator,
            "phone_number": self.phone_number,
            "balance": self.balance
        }
    
    def final_reset_and_close(self):
        """Reset cuối cùng trước khi thoát chương trình"""
        try:
            self.log("🔄 Đang gửi lệnh reset cuối cùng...")
            
            # Đảm bảo kết nối với baudrate mặc định trước khi reset
            if self.current_baudrate != self.default_baudrate:
                if not self.connect(self.default_baudrate):
                    self.log("❌ Không thể kết nối để reset cuối cùng")
                    return False
            
            # Gửi lệnh reset
            response = self.send_command("AT+CFUN=1,1", wait_time=1.0)
            
            if "OK" in response:
                self.log("✅ Reset cuối cùng thành công")
                return True
            else:
                self.log("❌ Reset cuối cùng thất bại")
                return False
                
        except Exception as e:
            self.log(f"❌ Lỗi reset cuối cùng: {e}")
            return False
        finally:
            # Luôn đóng kết nối
            self.disconnect()
    
    def _load_stt_model(self):
        """
        Lazy load STT model từ ModelManager (shared model)
        KHÔNG CẦN NỮA - đã được thay thế bởi model_manager
        """
        pass
    
    def _try_parse_qfopen(self, resp):
        """Parse file descriptor từ QFOPEN response"""
        m = re.search(r"\+QFOPEN:\s*(\d+)", resp)
        if m:
            return int(m.group(1))
        return None
    
    def _download_file_via_qfread(self, remote_name, local_path):
        """Tải file từ GSM module về máy tính"""
        try:
            self.log(f"📥 Đang tải file {remote_name}...")
            
            # Kiểm tra file size
            resp = self.send_command(f'AT+QFLST="{remote_name}"', wait_time=3.0)
            if "ERROR" in resp:
                self.log(f"❌ File {remote_name} không tồn tại")
                return False
            
            # Lấy file size
            file_size = 0
            size_match = re.search(r'\+QFLST:\s*"[^"]+",(\d+)', resp)
            if size_match:
                file_size = int(size_match.group(1))
                self.log(f"📊 File size: {file_size} bytes")
            
            # Mở file để đọc
            resp = self.send_command(f'AT+QFOPEN="{remote_name}",0', wait_time=3.0)
            fd = self._try_parse_qfopen(resp)
            if fd is None:
                self.log(f"❌ Không thể mở file {remote_name}")
                return False
            
            total_bytes = 0
            chunk_size = 65536  # 64KB
            
            try:
                with open(local_path, "wb") as f:
                    while True:
                        remaining = file_size - total_bytes
                        current_chunk = min(chunk_size, remaining)
                        
                        if current_chunk <= 0:
                            break
                        
                        # Gửi lệnh QFREAD
                        self.serial_connection.write(f"AT+QFREAD={fd},{current_chunk}\r\n".encode())
                        
                        # Đọc response
                        response = b""
                        start_time = time.time()
                        while time.time() - start_time < 5:
                            if self.serial_connection.in_waiting > 0:
                                response += self.serial_connection.read(self.serial_connection.in_waiting)
                                if b"CONNECT" in response and b"\r\nOK\r\n" in response:
                                    break
                            else:
                                time.sleep(0.005)
                        
                        # Parse binary data
                        response_str = response.decode(errors="ignore")
                        m = re.search(r"CONNECT\s+(\d+)", response_str)
                        if m:
                            length = int(m.group(1))
                            if length == 0:
                                break
                            
                            # Extract binary data
                            connect_pos = response.find(b"CONNECT")
                            if connect_pos != -1:
                                line_end = response.find(b"\r\n", connect_pos)
                                if line_end != -1:
                                    data_start = line_end + 2
                                    ok_pos = response.find(b"\r\nOK\r\n")
                                    if ok_pos != -1:
                                        binary_data = response[data_start:ok_pos]
                                        f.write(binary_data[:length])
                                        total_bytes += min(length, len(binary_data))
                            
                            if length < chunk_size:
                                break
                        else:
                            break
                            
            except Exception as e:
                self.log(f"❌ Lỗi khi tải file: {e}")
                return False
            finally:
                # Đóng file descriptor
                self.send_command(f"AT+QFCLOSE={fd}", wait_time=2.0)
            
            self.log(f"✅ Tải file thành công: {total_bytes} bytes")
            return total_bytes > 0
            
        except Exception as e:
            self.log(f"❌ Lỗi tải file: {e}")
            return False
    
    def _convert_to_wav(self, amr_file, wav_file):
        """Convert AMR sang WAV 16kHz mono"""
        try:
            self.log(f"🔄 Đang convert {amr_file} -> {wav_file}")
            audio = AudioSegment.from_file(amr_file)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(wav_file, format="wav")
            self.log(f"✅ Convert thành công")
            return True
        except Exception as e:
            self.log(f"❌ Lỗi convert: {e}")
            return False
    
    def _transcribe_audio(self, wav_file):
        """Speech-to-text sử dụng Wav2Vec2 từ ModelPool (pool of models)"""
        try:
            self.log("🎤 Đang thực hiện speech-to-text...")

            # Lấy model từ ModelPool (blocking nếu pool đầy)
            processor, model, device = model_manager.get_model()

            try:
                # Load audio
                speech, rate = librosa.load(wav_file, sr=16000)
                input_values = processor(speech, return_tensors="pt", sampling_rate=16000).input_values.to(device)

                # Transcribe
                with torch.no_grad():
                    logits = model(input_values).logits

                predicted_ids = torch.argmax(logits, dim=-1)
                transcription = processor.batch_decode(predicted_ids)

                result = transcription[0]
                self.log(f"📝 STT result: {result}")
                return result

            finally:
                # QUAN TRỌNG: Trả model về pool sau khi dùng xong
                model_manager.release_model(model)

        except Exception as e:
            self.log(f"❌ Lỗi STT: {e}")
            return ""
    
    def _classify_result(self, text):
        """Phân loại kết quả dựa trên text"""
        try:
            self.log("🔍 Đang phân loại kết quả...")
            result_index = keyword_in_text(text)
            result_label = labels[result_index]
            self.log(f"📊 Kết quả phân loại: {result_label}")
            return result_label
        except Exception as e:
            self.log(f"❌ Lỗi phân loại: {e}")
            return "incorrect"
