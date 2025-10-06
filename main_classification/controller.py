"""
GSM Controller - Điều phối toàn bộ hệ thống GSM
Quản lý nhiều GSM instances, phân phối số điện thoại, và tổng hợp kết quả
"""

import threading
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path
import os
from datetime import datetime

from gsm_instance import GSMInstance
from detect_gsm_port import scan_gsm_ports_parallel
from string_detection import keyword_in_text, labels
from spk_to_text_wav2 import convert_to_wav, transcribe_wav2vec2
from export_excel import export_results_to_excel

# Cấu hình logging - ghi ra file
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"gsm_controller_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # Vẫn in ra console
    ]
)
logger = logging.getLogger(__name__)

class GSMController:
    """Controller chính điều phối toàn bộ hệ thống GSM"""
    
    def __init__(self, max_ports: int = 32):
        self.max_ports = max_ports
        self.gsm_instances: Dict[str, GSMInstance] = {}
        self.gsm_ports_list: List[str] = []  # Lưu danh sách cổng GSM
        self.phone_list: List[str] = []  # Danh sách số điện thoại
        self.results: Dict[str, List[Dict]] = {
            "hoạt động": [],
            "leave_message": [],
            "be_blocked": [],
            "can_not_connect": [],
            "incorrect": [],
            "ringback_tone": [],
            "waiting_tone": [],
            "mute": [],
            "lỗi": []  # Thêm cột cho các số bị lỗi
        }
        self.is_running = False
        self.is_stopping = False
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
        """Quét và phát hiện các cổng GSM với đa luồng"""
        self.log("🔍 Bắt đầu quét các cổng GSM...")
        
        # Sử dụng đa luồng để quét cổng
        gsm_port_list = scan_gsm_ports_parallel(max_workers=10, log_callback=self.log)
        
        # Lưu danh sách cổng để reset khi đóng
        self.gsm_ports_list = gsm_port_list.copy()
        
        gsm_ports = []
        
        # Tạo GSM instances cho từng cổng
        for port in gsm_port_list:
            try:
                self.log(f"📋 [{port}] Đang tạo GSM instance...")
                
                # Tạo GSM instance
                gsm_instance = GSMInstance(port, self.log)
                
                # Kết nối và lấy thông tin cơ bản
                if gsm_instance.connect():
                    gsm_info = gsm_instance.get_basic_info()
                    gsm_info["port"] = port
                    gsm_info["status"] = "Active"
                    gsm_ports.append(gsm_info)
                    
                    # Reset baudrate lên 921600 ngay sau khi lấy thông tin cơ bản
                    self.log(f"🔄 [{port}] Đang reset baudrate lên 921600...")
                    if gsm_instance.reset_baudrate(921600):
                        self.log(f"✅ [{port}] Reset baudrate thành công")
                    else:
                        self.log(f"❌ [{port}] Reset baudrate thất bại")
                    
                    # Lưu instance
                    self.gsm_instances[port] = gsm_instance
                    
                    self.log(f"✅ [{port}] GSM instance đã sẵn sàng")
                else:
                    self.log(f"❌ [{port}] Không thể kết nối GSM instance")
                
                # Đợi một chút giữa các cổng để tránh xung đột
                time.sleep(0.5)
                
                if len(gsm_ports) >= self.max_ports:
                    break
                    
            except Exception as e:
                self.log(f"❌ Lỗi khi tạo GSM instance {port}: {e}")
                # Đợi một chút ngay cả khi có lỗi
                time.sleep(0.5)
        
        self.log(f"🎯 Tạo thành công {len(gsm_ports)} GSM instances")
        return gsm_ports
    
    def load_phone_list(self, file_path: str) -> bool:
        """Tải danh sách số điện thoại từ file"""
        try:
            if not os.path.exists(file_path):
                self.log(f"❌ File không tồn tại: {file_path}")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            self.phone_list = []
            for line in lines:
                phone = line.strip()
                # Validate số điện thoại: phải bắt đầu bằng 0 và có 10-11 chữ số
                if phone and phone.startswith('0') and phone.isdigit() and len(phone) in [10, 11]:
                    # Lấy nguyên số từ danh sách, không chuyển đổi
                    self.phone_list.append(phone)
                elif phone:
                    self.log(f"⚠️ Bỏ qua số không hợp lệ: {phone}")

            self.log(f"📋 Đã tải {len(self.phone_list)} số điện thoại hợp lệ từ file")
            return True

        except Exception as e:
            self.log(f"❌ Lỗi khi tải file: {e}")
            return False
    
    def distribute_phone_numbers(self):
        """Phân phối số điện thoại cho các GSM instances"""
        if not self.phone_list:
            self.log("❌ Không có danh sách số điện thoại")
            return False
        
        if not self.gsm_instances:
            self.log("❌ Không có GSM instances")
            return False
        
        # Chia đều số điện thoại cho các instances
        instances = list(self.gsm_instances.values())
        phones_per_instance = len(self.phone_list) // len(instances)
        remainder = len(self.phone_list) % len(instances)
        
        start_idx = 0
        for i, instance in enumerate(instances):
            # Tính số lượng số cho instance này
            count = phones_per_instance
            if i < remainder:  # Phân phối số dư cho các instance đầu
                count += 1
            
            # Lấy danh sách số cho instance này
            end_idx = start_idx + count
            instance_phones = self.phone_list[start_idx:end_idx]
            
            # Thiết lập danh sách số cho instance
            instance.set_phone_queue(instance_phones)
            
            self.log(f"📋 [{instance.port}] Nhận {len(instance_phones)} số điện thoại")
            start_idx = end_idx
        
        self.log(f"✅ Đã phân phối {len(self.phone_list)} số điện thoại cho {len(instances)} instances")
        return True
    
    def start_processing(self):
        """Bắt đầu xử lý trên tất cả GSM instances"""
        if not self.gsm_instances:
            self.log("❌ Không có GSM instances để xử lý")
            return False
        
        if self.is_running:
            self.log("⚠️ Đang xử lý rồi")
            return False
        
        # Phân phối số điện thoại
        if not self.distribute_phone_numbers():
            return False
        
        # Xóa kết quả cũ
        self.clear_results()
        
        # Bắt đầu xử lý trên tất cả instances
        self.is_running = True
        self.is_stopping = False
        
        self.log("🚀 Bắt đầu xử lý trên tất cả GSM instances...")
        self.log("ℹ️ Các instances đã ở baudrate 921600, sẵn sàng gọi và ghi âm")
        
        # Khởi động tất cả instances
        for instance in self.gsm_instances.values():
            instance.start_processing()
        
        return True
    
    def stop_processing(self):
        """Dừng xử lý trên tất cả GSM instances"""
        if not self.is_running:
            return
        
        self.log("🛑 Đang dừng xử lý...")
        self.is_stopping = True
        
        # Dừng tất cả instances
        for instance in self.gsm_instances.values():
            instance.stop_processing()
        
        self.is_running = False
        self.log("✅ Đã dừng xử lý")
    
    def collect_results(self):
        """Thu thập kết quả từ tất cả GSM instances"""
        self.log("📊 Đang thu thập kết quả...")
        
        # Xóa kết quả cũ
        self.clear_results()
        
        # Thu thập kết quả từ tất cả instances
        total_results = 0
        processed_phones = set()  # Tập hợp các số đã được xử lý
        
        for instance in self.gsm_instances.values():
            instance_results = instance.get_results()
            total_results += len(instance_results)
            
            # Phân loại kết quả
            for result in instance_results:
                category = result.get("result", "incorrect")
                phone_number = result.get("phone_number", "")
                processed_phones.add(phone_number)
                
                if category in self.results:
                    self.results[category].append(result)
                else:
                    self.results["lỗi"].append(result)
        
        # Thêm các số chưa được xử lý vào cột lỗi
        if self.phone_list:
            for phone in self.phone_list:
                if phone not in processed_phones:
                    self.results["lỗi"].append({
                        "phone_number": phone,
                        "result": "lỗi",
                        "reason": "Chưa được xử lý"
                    })
                    self.log(f"⚠️ Số {phone} chưa được xử lý")
        
        total_with_unprocessed = total_results + len(self.results["lỗi"])
        self.log(f"📊 Đã thu thập {total_results} kết quả + {len(self.results['lỗi'])} số chưa xử lý = {total_with_unprocessed} tổng cộng")
        
        # Log thống kê
        for category, results in self.results.items():
            if results:
                self.log(f"📈 {category}: {len(results)} kết quả")
    
    def get_processing_status(self) -> Dict:
        """Lấy trạng thái xử lý của tất cả instances"""
        status = {
            "is_running": self.is_running,
            "total_instances": len(self.gsm_instances),
            "active_instances": 0,
            "total_calls": 0,
            "total_results": 0,
            "instances": {}
        }
        
        for port, instance in self.gsm_instances.items():
            instance_status = instance.get_status()
            status["instances"][port] = instance_status
            
            if instance_status["status"] in ["calling", "idle"]:
                status["active_instances"] += 1
            
            status["total_calls"] += instance_status["call_count"]
            status["total_results"] += instance_status["results_count"]
        
        return status
    
    def clear_results(self):
        """Xóa tất cả kết quả"""
        for category in self.results:
            self.results[category] = []
        
        # Xóa kết quả trong tất cả instances
        for instance in self.gsm_instances.values():
            instance.results = []
    
    def export_results(self, output_path: str = None) -> bool:
        """Xuất kết quả ra file Excel"""
        try:
            # Thu thập kết quả trước khi xuất
            self.collect_results()

            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"gsm_results_{timestamp}.xlsx"

            # Xuất ra Excel với định dạng dict đúng
            success = export_results_to_excel(self.results, output_path)

            if success:
                self.log(f"✅ Đã xuất kết quả ra file: {output_path}")
                return True
            else:
                self.log("❌ Không thể xuất kết quả")
                return False

        except Exception as e:
            self.log(f"❌ Lỗi khi xuất kết quả: {e}")
            return False
    
    def reset_all_gsm_instances(self):
        """Reset tất cả GSM instances về baudrate mặc định"""
        if not self.gsm_instances:
            self.log("⚠️ Không có GSM instances để reset")
            return
        
        self.log(f"🔄 Đang reset {len(self.gsm_instances)} GSM instances...")
        
        reset_count = 0
        for port, instance in self.gsm_instances.items():
            try:
                self.log(f"🔄 [{port}] Đang reset instance...")
                
                # Reset về baudrate mặc định
                if instance.reset_baudrate(instance.default_baudrate):
                    self.log(f"✅ [{port}] Reset thành công")
                    reset_count += 1
                else:
                    self.log(f"❌ [{port}] Reset thất bại")
                    
            except Exception as e:
                self.log(f"❌ [{port}] Lỗi khi reset: {e}")
        
        self.log(f"🎯 Đã reset thành công {reset_count}/{len(self.gsm_instances)} instances")
    
    def final_reset_all_instances(self):
        """Reset cuối cùng tất cả GSM instances trước khi thoát"""
        if not self.gsm_instances:
            self.log("⚠️ Không có GSM instances để reset cuối cùng")
            return
        
        self.log(f"🔄 Đang reset cuối cùng {len(self.gsm_instances)} GSM instances...")
        
        reset_count = 0
        for port, instance in self.gsm_instances.items():
            try:
                self.log(f"🔄 [{port}] Đang reset cuối cùng...")
                
                # Gửi lệnh AT+CFUN=1,1 và đóng kết nối
                if instance.final_reset_and_close():
                    self.log(f"✅ [{port}] Reset cuối cùng thành công")
                    reset_count += 1
                else:
                    self.log(f"❌ [{port}] Reset cuối cùng thất bại")
                    
            except Exception as e:
                self.log(f"❌ [{port}] Lỗi khi reset cuối cùng: {e}")
        
        self.log(f"🎯 Đã reset cuối cùng thành công {reset_count}/{len(self.gsm_instances)} instances")
    
    def disconnect_all(self):
        """Ngắt kết nối tất cả GSM instances"""
        for port, instance in self.gsm_instances.items():
            try:
                instance.disconnect()
                self.log(f"🔌 Đã ngắt kết nối {port}")
            except Exception as e:
                self.log(f"❌ Lỗi khi ngắt kết nối {port}: {e}")
        
        self.gsm_instances.clear()
    
    def get_gsm_instances_info(self) -> List[Dict]:
        """Lấy thông tin tất cả GSM instances cho GUI"""
        instances_info = []
        for port, instance in self.gsm_instances.items():
            info = instance.get_status()
            instances_info.append({
                "port": port,
                "signal": info["signal"],
                "network_operator": info["network_operator"],
                "phone_number": info["phone_number"],
                "balance": info["balance"],
                "status": info["status"],
                "call_count": info["call_count"],
                "queue_remaining": info["queue_remaining"]
            })
        return instances_info