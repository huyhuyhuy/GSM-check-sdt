import threading
import time
import queue
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import os
from datetime import datetime

from gsm_manager import GSMDevice
from detect_gsm_port import probe_port_simple, get_signal_info, get_phone_number, try_ussd_for_balance
from string_detection import keyword_in_text, labels
from spk_to_text_wav2 import convert_to_wav, transcribe_wav2vec2
from export_excel import export_results_to_excel

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GSMController:
    """Controller chính điều phối toàn bộ hệ thống GSM"""
    
    def __init__(self, max_ports: int = 32):
        self.max_ports = max_ports
        self.gsm_devices: Dict[str, GSMDevice] = {}
        self.phone_queue = queue.Queue()
        self.results: Dict[str, List[Dict]] = {
            "hoạt động": [],
            "leave_message": [],
            "be_blocked": [],
            "can_not_connect": [],
            "incorrect": [],
            "ringback_tone": [],
            "waiting_tone": [],
            "mute": []
        }
        self.is_running = False
        self.is_stopping = False
        self.call_threads: List[threading.Thread] = []
        self.log_callback = None
        
    def set_log_callback(self, callback):
        """Thiết lập callback để gửi log lên GUI"""
        self.log_callback = callback
    
    def log(self, message: str):
        """Gửi log message"""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)
    
    def scan_gsm_ports(self) -> List[Dict]:
        """Quét và phát hiện các cổng GSM"""
        self.log("🔍 Bắt đầu quét các cổng GSM...")
        
        # Import từ detect_gsm_port
        from serial.tools import list_ports
        
        ports = [p.device for p in list_ports.comports()]
        gsm_ports = []
        
        for port in ports:
            try:
                result = probe_port_simple(port)
                if result.get("ok"):
                    self.log(f"✅ Tìm thấy GSM tại {port}")
                    
                    # Lấy thông tin chi tiết
                    gsm_info = self._get_detailed_gsm_info(port)
                    gsm_info["port"] = port
                    gsm_info["status"] = "Active"
                    gsm_ports.append(gsm_info)
                    
                    if len(gsm_ports) >= self.max_ports:
                        break
                        
            except Exception as e:
                self.log(f"❌ Lỗi khi quét {port}: {e}")
        
        self.log(f"🎯 Tìm thấy {len(gsm_ports)} cổng GSM")
        return gsm_ports
    
    def _get_detailed_gsm_info(self, port: str) -> Dict:
        """Lấy thông tin chi tiết của một cổng GSM"""
        try:
            from serial import Serial
            
            ser = Serial(port=port, baudrate=115200, timeout=0.1, write_timeout=0.5)
            time.sleep(0.1)
            
            # Lấy thông tin tín hiệu
            signal_info = get_signal_info(ser)
            signal_str = "Không xác định"
            if "rssi" in signal_info and signal_info["rssi"] is not None:
                signal_str = f"{signal_info['rssi']}/31 ({signal_info.get('dbm', 'N/A')} dBm)"
            
            # Lấy số điện thoại
            phone_info = get_phone_number(ser)
            phone_number = phone_info.get("number", "Không xác định")
            
            # Lấy số dư
            balance_info = try_ussd_for_balance(ser)
            balance = "Không xác định"
            if balance_info.get("content"):
                balance = balance_info["content"]
            
            ser.close()
            
            return {
                "signal": signal_str,
                "phone_number": phone_number,
                "balance": balance
            }
            
        except Exception as e:
            self.log(f"❌ Lỗi khi lấy thông tin {port}: {e}")
            return {
                "signal": "Lỗi",
                "phone_number": "Lỗi", 
                "balance": "Lỗi"
            }
    
    def load_phone_list(self, file_path: str) -> bool:
        """Tải danh sách số điện thoại từ file"""
        try:
            if not os.path.exists(file_path):
                self.log(f"❌ File {file_path} không tồn tại")
                return False
            
            phones = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    phone = line.strip()
                    if phone and phone.isdigit():
                        phones.append(phone)
            
            # Thêm vào queue
            for phone in phones:
                self.phone_queue.put(phone)
            
            self.log(f"✅ Đã tải {len(phones)} số điện thoại từ {file_path}")
            return True
            
        except Exception as e:
            self.log(f"❌ Lỗi khi tải file: {e}")
            return False
    
    def initialize_gsm_devices(self, gsm_ports: List[Dict]) -> bool:
        """Khởi tạo các thiết bị GSM"""
        self.log("🔧 Khởi tạo các thiết bị GSM...")
        
        for i, gsm_info in enumerate(gsm_ports):
            port = gsm_info["port"]
            try:
                # Tạo GSM device
                gsm_device = GSMDevice(port, baudrate=115200)
                
                # Kết nối
                if gsm_device.connect():
                    # Reset baudrate lên 921600
                    if self._reset_baudrate(gsm_device):
                        self.gsm_devices[port] = gsm_device
                        self.log(f"✅ Khởi tạo thành công {port}")
                    else:
                        self.log(f"❌ Không thể reset baudrate cho {port}")
                        gsm_device.disconnect()
                else:
                    self.log(f"❌ Không thể kết nối đến {port}")
                    
            except Exception as e:
                self.log(f"❌ Lỗi khi khởi tạo {port}: {e}")
        
        self.log(f"🎯 Khởi tạo thành công {len(self.gsm_devices)} thiết bị GSM")
        return len(self.gsm_devices) > 0
    
    def _reset_baudrate(self, gsm_device: GSMDevice) -> bool:
        """Reset baudrate từ 115200 lên 921600"""
        try:
            # Gửi lệnh reset baudrate
            response = gsm_device.send_command("AT+IPR=921600", wait_time=2.0)
            if "OK" in response:
                response = gsm_device.send_command("AT&W", wait_time=2.0)
                if "OK" in response:
                    gsm_device.disconnect()
                    time.sleep(1)
                    
                    # Kết nối lại với baudrate mới
                    gsm_device.baudrate = 921600
                    return gsm_device.connect()
            return False
            
        except Exception as e:
            self.log(f"❌ Lỗi khi reset baudrate: {e}")
            return False
    
    def start_processing(self):
        """Bắt đầu xử lý đa luồng"""
        if self.is_running:
            self.log("⚠️ Hệ thống đang chạy")
            return
        
        if not self.gsm_devices:
            self.log("❌ Không có thiết bị GSM nào được khởi tạo")
            return
        
        if self.phone_queue.empty():
            self.log("❌ Không có số điện thoại nào để gọi")
            return
        
        self.is_running = True
        self.is_stopping = False
        
        self.log("🚀 Bắt đầu xử lý đa luồng...")
        
        # Tạo thread cho mỗi GSM device
        for port, gsm_device in self.gsm_devices.items():
            thread = threading.Thread(
                target=self._process_calls_worker,
                args=(port, gsm_device),
                daemon=True
            )
            thread.start()
            self.call_threads.append(thread)
        
        self.log(f"🎯 Đã khởi động {len(self.call_threads)} luồng xử lý")
    
    def _process_calls_worker(self, port: str, gsm_device: GSMDevice):
        """Worker thread xử lý cuộc gọi cho một GSM device"""
        self.log(f"🔄 Luồng {port} bắt đầu hoạt động")
        
        while self.is_running and not self.is_stopping:
            try:
                # Lấy số điện thoại từ queue (blocking với timeout)
                try:
                    phone = self.phone_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                if phone is None:  # Signal để dừng
                    break
                
                # Xử lý cuộc gọi
                result = self._process_single_call(port, gsm_device, phone)
                
                # Lưu kết quả
                self._save_result(result)
                
                # Mark task done
                self.phone_queue.task_done()
                
                # Nghỉ giữa các cuộc gọi
                time.sleep(2)
                
            except Exception as e:
                self.log(f"❌ Lỗi trong luồng {port}: {e}")
                time.sleep(5)  # Nghỉ lâu hơn khi có lỗi
        
        self.log(f"🏁 Luồng {port} kết thúc")
    
    def _process_single_call(self, port: str, gsm_device: GSMDevice, phone: str) -> Dict:
        """Xử lý một cuộc gọi đơn lẻ"""
        self.log(f"📞 [{port}] Gọi tới {phone}")
        
        call_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"{phone}_{call_timestamp}.amr"
        
        try:
            # 1. Gọi điện
            call_response = gsm_device.send_command(f"ATD{phone};", wait_time=3.0)
            if "ERROR" in call_response:
                return {
                    "port": port,
                    "phone": phone,
                    "status": "can_not_connect",
                    "timestamp": call_timestamp,
                    "file": None,
                    "transcription": None,
                    "error": "Không thể gọi điện"
                }
            
            time.sleep(1.5)  # Đợi cuộc gọi được thiết lập
            
            # 2. Xóa file cũ nếu có
            gsm_device.send_command('AT+QFDEL="record.amr"', wait_time=1.0)
            
            # 3. Bắt đầu ghi âm
            record_response = gsm_device.send_command('AT+QAUDRD=1,"record.amr",13,1', wait_time=3.0)
            if "ERROR" in record_response:
                gsm_device.send_command("ATH", wait_time=1.0)  # Ngắt cuộc gọi
                return {
                    "port": port,
                    "phone": phone,
                    "status": "can_not_connect",
                    "timestamp": call_timestamp,
                    "file": None,
                    "transcription": None,
                    "error": "Không thể ghi âm"
                }
            
            # 4. Ghi âm 15 giây và check CLCC
            start_time = time.time()
            picked_up = False
            
            while time.time() - start_time < 15:
                # Check CLCC để xem có nhấc máy không
                clcc_response = gsm_device.send_command("AT+CLCC", wait_time=0.5)
                if "+COLP" in clcc_response or "CONNECT" in clcc_response:
                    picked_up = True
                    self.log(f"📞 [{port}] {phone} đã nhấc máy - dừng ghi âm")
                    break
                
                time.sleep(0.5)  # Check mỗi 0.5 giây
            
            # 5. Dừng ghi âm
            gsm_device.send_command('AT+QAUDRD=0,"record.amr",13,1', wait_time=2.0)
            time.sleep(0.5)  # Đợi module lưu file
            
            # 6. Ngắt cuộc gọi
            gsm_device.send_command("ATH", wait_time=2.0)
            
            # 7. Nếu đã nhấc máy, không cần phân tích audio
            if picked_up:
                return {
                    "port": port,
                    "phone": phone,
                    "status": "hoạt động",
                    "timestamp": call_timestamp,
                    "file": None,
                    "transcription": "Người nghe đã nhấc máy",
                    "error": None
                }
            
            # 8. Tải file audio về
            local_path = os.path.join(os.path.dirname(__file__), local_filename)
            if self._download_audio_file(gsm_device, "record.amr", local_path):
                
                # 9. Speech-to-text và phân loại
                transcription, classification = self._analyze_audio(local_path)
                
                return {
                    "port": port,
                    "phone": phone,
                    "status": classification,
                    "timestamp": call_timestamp,
                    "file": local_filename,
                    "transcription": transcription,
                    "error": None
                }
            else:
                return {
                    "port": port,
                    "phone": phone,
                    "status": "can_not_connect",
                    "timestamp": call_timestamp,
                    "file": None,
                    "transcription": None,
                    "error": "Không thể tải file audio"
                }
                
        except Exception as e:
            self.log(f"❌ Lỗi khi xử lý cuộc gọi {phone} trên {port}: {e}")
            return {
                "port": port,
                "phone": phone,
                "status": "can_not_connect",
                "timestamp": call_timestamp,
                "file": None,
                "transcription": None,
                "error": str(e)
            }
    
    def _download_audio_file(self, gsm_device: GSMDevice, remote_filename: str, local_path: str) -> bool:
        """Tải file audio từ GSM về máy tính"""
        try:
            # Import từ call_and_record
            from call_and_record import download_file_via_qfread
            
            return download_file_via_qfread(gsm_device.serial_connection, remote_filename, local_path)
            
        except Exception as e:
            self.log(f"❌ Lỗi khi tải file audio: {e}")
            return False
    
    def _analyze_audio(self, audio_path: str) -> Tuple[str, str]:
        """Phân tích audio: speech-to-text và phân loại"""
        try:
            # Convert AMR to WAV
            temp_wav = "temp.wav"
            convert_to_wav(audio_path, temp_wav)
            
            # Speech-to-text
            transcription = transcribe_wav2vec2(temp_wav)
            
            # Phân loại dựa trên từ khóa
            classification_index = keyword_in_text(transcription)
            classification = labels[classification_index]
            
            # Cleanup temp file
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            
            return transcription, classification
            
        except Exception as e:
            self.log(f"❌ Lỗi khi phân tích audio: {e}")
            return "", "mute"
    
    def _save_result(self, result: Dict):
        """Lưu kết quả vào dictionary"""
        status = result["status"]
        if status in self.results:
            self.results[status].append(result)
        else:
            # Nếu không tìm thấy category, thêm vào "mute"
            self.results["mute"].append(result)
        
        self.log(f"📊 [{result['port']}] {result['phone']} → {status}")
    
    def stop_processing(self):
        """Dừng xử lý"""
        if not self.is_running:
            return
        
        self.log("🛑 Đang dừng hệ thống...")
        self.is_stopping = True
        
        # Đợi tất cả thread kết thúc
        for thread in self.call_threads:
            thread.join(timeout=5)
        
        self.call_threads.clear()
        self.is_running = False
        self.is_stopping = False
        
        self.log("✅ Đã dừng hệ thống")
    
    def get_results(self) -> Dict[str, List[Dict]]:
        """Lấy kết quả"""
        return self.results
    
    def clear_results(self):
        """Xóa kết quả"""
        for key in self.results:
            self.results[key].clear()
    
    def export_results(self, output_path: str = None) -> bool:
        """Xuất kết quả ra file Excel"""
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"gsm_results_{timestamp}.xlsx"
            
            return export_results_to_excel(self.results, output_path)
            
        except Exception as e:
            self.log(f"❌ Lỗi khi xuất kết quả: {e}")
            return False
    
    def disconnect_all(self):
        """Ngắt kết nối tất cả GSM devices"""
        for port, gsm_device in self.gsm_devices.items():
            try:
                gsm_device.disconnect()
                self.log(f"🔌 Đã ngắt kết nối {port}")
            except Exception as e:
                self.log(f"❌ Lỗi khi ngắt kết nối {port}: {e}")
        
        self.gsm_devices.clear()
