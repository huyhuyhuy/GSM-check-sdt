import serial
import time
import threading
from typing import List, Dict, Callable
from queue import Queue
import logging
from esp32_audio_analyzer import ESP32AudioAnalyzer
from check_vina_mobi_vietnam import ultra_fast_check_vina_mobi_vietnamobile
from check_viettel import viettel_combined_check

class GSMDevice:
    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.is_connected = False
        self.is_busy = False
        self.log_callback = None
        self.audio_analyzer = None  # ESP32 audio analyzer
        self.audio_channel = 0  # Channel cho audio analysis
        
    def set_log_callback(self, callback: Callable):
        """Thiết lập callback để ghi log"""
        self.log_callback = callback
    
    def set_audio_analyzer(self, analyzer: ESP32AudioAnalyzer, channel: int = 0):
        """Thiết lập ESP32 audio analyzer"""
        self.audio_analyzer = analyzer
        self.audio_channel = channel
    
    def log(self, message: str):
        """Ghi log"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(f"[{self.port}] {message}")
        
    def connect(self) -> bool:
        """Kết nối đến cổng GSM"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.is_connected = True
            return True
        except Exception as e:
            logging.error(f"Lỗi kết nối cổng {self.port}: {str(e)}")
            return False
    
    def disconnect(self):
        """Ngắt kết nối"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
    
    def send_command_quick(self, command: str, wait_time: float = 0.5) -> str:
        """Gửi lệnh AT nhanh cho việc scan port"""
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
            
            # Đọc phản hồi nhanh
            response = ""
            if self.serial_connection.in_waiting:
                response = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
            
            return response.strip()
        except Exception as e:
            return f"ERROR: {str(e)}"

    def send_command(self, command: str, wait_time: float = 1.0) -> str:
        """Gửi lệnh AT và nhận phản hồi"""
        if not self.is_connected:
            return "ERROR: Not connected"
        
        try:
            # Xóa buffer trước khi gửi lệnh
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Gửi lệnh (chỉ khi có command)
            if command:
                self.serial_connection.write((command + '\r\n').encode())
                time.sleep(wait_time)
            
            # Đọc phản hồi
            response = ""
            start_time = time.time()
            timeout = wait_time + 2  # Thêm 2 giây buffer
            
            while time.time() - start_time < timeout:
                if self.serial_connection.in_waiting:
                    chunk = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                    response += chunk
                time.sleep(0.1)
            
            return response.strip()
        except Exception as e:
            logging.error(f"Lỗi gửi lệnh trên cổng {self.port}: {str(e)}")
            return f"ERROR: {str(e)}"
    
    def refresh_modem(self):
        """Refresh modem về trạng thái sạch"""
        try:
            self.log(f"Đang refresh modem {self.port}...")
            
            # Hủy tất cả cuộc gọi
            self.send_command("AT+CHUP")
            time.sleep(2)
            
            # Reset modem
            self.send_command("ATZ")
            time.sleep(2)
            self.send_command("AT&F")
            time.sleep(2)
            
            # Cấu hình AT+COLP=1 (chỉ cần 1 lần)
            self.send_command("AT+COLP=1")
            # cấu hình AT+CMEE=2
            self.send_command("AT+CMEE=2")
            # cấu hình ATV1
            self.send_command("ATV1")
            time.sleep(1)
            # Lưu cấu hình sau khi thiết lập
            self.send_command("AT&W")

            time.sleep(1)
            
            # Kiểm tra modem sẵn sàng
            response = self.send_command("AT")
            if "OK" in response:
                self.log(f"Modem {self.port} đã được refresh và cấu hình thành công")
                return True
            else:
                self.log(f"Modem {self.port} không phản hồi sau khi refresh")
                return False
        except Exception as e:
            self.log(f"Lỗi refresh modem {self.port}: {str(e)}")
            return False

    def parse_clcc_status(self, clcc_response: str) -> int:
        """Parse status từ response AT+CLCC"""
        try:
            # Tìm dòng +CLCC: trong response
            lines = clcc_response.split('\n')
            for line in lines:
                if '+CLCC:' in line:
                    # Parse format: +CLCC: <idx>,<dir>,<status>,<mode>,<mpty>,"<number>",<type>
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        status = int(parts[2])  # Lấy status (phần tử thứ 3)
                        return status
            return -1  # Không tìm thấy status
        except Exception as e:
            self.log(f"Lỗi parse CLCC response: {str(e)}")
            return -1

    def check_phone_number(self, phone_number: str) -> str:
        """Check một số điện thoại và trả về kết quả: HOẠT ĐỘNG, THUÊ BAO, SỐ KHÔNG ĐÚNG"""
        # Sử dụng logic tối ưu mới
        return self.check_phone_number_optimized(phone_number)

    def detect_carrier(self, phone_number: str) -> str:
        """Phát hiện nhà mạng dựa trên đầu số"""
        prefix = phone_number[:3]
        # nếu số không hợp lệ dài quá 10 ký tự cũng return luôn
        if len(phone_number) > 10:
            return 'UNKNOWN'
        # VIETTEL
        if prefix in ['086', '096', '097', '098', '032', '033', '034', '035', '036', '037', '038', '039']:
            return 'VIETTEL'
        # MOBIFONE
        elif prefix in ['089', '090', '093', '070', '079', '077', '076', '078', '087']:
            return 'MOBIFONE'
        # VINA
        elif prefix in ['088', '091', '094', '083', '084', '085', '081', '082']:
            return 'VINA'
        # VIETNAMOBILE
        elif prefix in ['092', '056', '058', '059', '099']:
            return 'VIETNAMOBILE'
        else:
            return 'UNKNOWN'

    def check_phone_number_optimized(self, phone_number: str) -> str:
        """Check số điện thoại với logic tối ưu theo nhà mạng và trả về kết quả string"""
        if not self.is_connected:
            return "THUÊ BAO"

        try:
            # Phát hiện nhà mạng trước
            carrier = self.detect_carrier(phone_number)
            # self.log(f"Số {phone_number}: Nhà mạng {carrier}")
            
            # Gọi hàm tương ứng với nhà mạng
            if carrier in ['VINA', 'MOBIFONE', 'VIETNAMOBILE']:
                result = ultra_fast_check_vina_mobi_vietnamobile(self, phone_number, self.log)
                return result
            elif carrier == 'VIETTEL':
                result = viettel_combined_check(self, phone_number, self.log)
                return result
            else:
                # UNKNOWN hoặc nhà mạng khác → Mặc định THUÊ BAO
                # self.log(f"Số {phone_number}: Nhà mạng {carrier} → THUÊ BAO")
                return "THUÊ BAO"
            
        except Exception as e:
            self.log(f"Lỗi check optimized {phone_number}: {str(e)}")
            # Fallback mặc định
            return "HOẠT ĐỘNG"


class GSMManager:
    def __init__(self, port_prefix: str = "COM", start_port: int = 35, end_port: int = 66, esp32_port: str = "COM67"):
        self.port_prefix = port_prefix
        self.start_port = start_port
        self.end_port = end_port
        self.devices: Dict[str, GSMDevice] = {}
        self.available_ports = []
        self.task_queue = Queue()
        self.results = {}
        self.is_running = False
        self.log_callback: Callable = None
        
        # ESP32 Audio Analyzer
        self.esp32_analyzer = ESP32AudioAnalyzer(esp32_port)
        self.esp32_connected = False
        self.adc_data_callback = None  # Callback để nhận ADC data
        
        # Multi-channel support
        self.total_channels = 32
        self.channel_mapping = {}  # Map device port to channel number
        
    def scan_ports(self) -> List[str]:
        """Quét tất cả cổng COM có sẵn từ start_port đến end_port"""
        available_ports = []
        self.log(f"Quét cổng COM từ {self.start_port} đến {self.end_port}")
        
        for i in range(self.start_port, self.end_port + 1):
            port_name = f"{self.port_prefix}{i}"
            try:
                # Thử kết nối với timeout ngắn để scan nhanh
                test_serial = serial.Serial(port_name, 115200, timeout=0.5)
                test_serial.close()
                available_ports.append(port_name)
                self.log(f"Tìm thấy cổng: {port_name}")
            except:
                continue
        
        self.available_ports = available_ports
        return available_ports
    
    def initialize_devices(self) -> bool:
        """Khởi tạo tất cả thiết bị GSM và ESP32"""
        # Khởi tạo ESP32 Audio Analyzer
        self.log("Đang khởi tạo ESP32 Multi-Channel Audio Analyzer...")
        if self.esp32_analyzer.connect():
            self.esp32_connected = True
            self.esp32_analyzer.set_log_callback(self.log_callback)
            if self.adc_data_callback:
                self.esp32_analyzer.set_adc_data_callback(self.adc_data_callback)
            self.log("ESP32 Multi-Channel Audio Analyzer đã sẵn sàng")
            
            # Test kết nối ESP32 (tạm thời bỏ qua)
            # if self.esp32_analyzer.test_connection():
            #     self.log("ESP32 connection test thành công")
            # else:
            #     self.log("ESP32 connection test thất bại")
            # self.log("ESP32 connection test tạm thời bỏ qua")
        else:
            self.log("Không thể kết nối ESP32 Audio Analyzer - sẽ sử dụng chế độ phân tích GSM thông thường")
        
        if not self.available_ports:
            self.scan_ports()
        
        if not self.available_ports:
            self.log("Không tìm thấy cổng COM nào!")
            return False
        
        self.log(f"Đang khởi tạo {len(self.available_ports)} thiết bị GSM...")
        
        for i, port in enumerate(self.available_ports):
            device = GSMDevice(port)
            device.set_log_callback(self.log_callback)  # Truyền callback log
            
            # Gán ESP32 analyzer cho device nếu có
            if self.esp32_connected:
                # Map device port to channel number (0-31)
                channel = i % self.total_channels
                device.set_audio_analyzer(self.esp32_analyzer, channel=channel)
                self.channel_mapping[port] = channel
                self.log(f"Device {port} mapped to channel {channel}")
            
            if device.connect():
                # Kiểm tra thiết bị có phải GSM không với timeout ngắn
                response = device.send_command_quick("AT")
                if "OK" in response:
                    self.devices[port] = device
                    self.log(f"Thiết bị {port} đã sẵn sàng")
                    # Cấu hình modem một lần sau khi xác nhận là GSM
                    # if device.refresh_modem():
                    #     self.log(f"Đã cấu hình modem {port}")
                    # else:
                    #     self.log(f"Không thể cấu hình modem {port}")
                else:
                    device.disconnect()
                    self.log(f"Thiết bị {port} không phải GSM modem")
            else:
                self.log(f"Không thể kết nối thiết bị {port}")
        
        self.log(f"Đã khởi tạo thành công {len(self.devices)} thiết bị GSM")

        # Override mapping: Chỉ định 2 thiết bị đầu cho audio channels 1 và 2
        # để phù hợp với firmware chỉ stream 2 kênh
        if self.esp32_connected and len(self.devices) > 0:
            try:
                selected_ports = [p for p in self.available_ports if p in self.devices][:2]
                for idx, port in enumerate(selected_ports):
                    new_channel = 1 + idx  # channels 1 và 2
                    device = self.devices[port]
                    device.set_audio_analyzer(self.esp32_analyzer, channel=new_channel)
                    self.channel_mapping[port] = new_channel
                    self.log(f"Override: Device {port} remapped to channel {new_channel}")
            except Exception as e:
                self.log(f"Không thể override audio channels: {str(e)}")
        return len(self.devices) > 0
    
    def set_log_callback(self, callback: Callable):
        """Thiết lập callback để ghi log"""
        self.log_callback = callback
    
    def set_adc_data_callback(self, callback: Callable):
        """Thiết lập callback để nhận ADC data"""
        self.adc_data_callback = callback
        if self.esp32_analyzer:
            self.esp32_analyzer.set_adc_data_callback(callback)
    
    def log(self, message: str):
        """Ghi log"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def start_checking(self, phone_numbers: List[str], result_callback: Callable, batch_size: int = 100):
        """Bắt đầu check danh sách số điện thoại với batch processing"""
        if not self.devices:
            self.log("Chưa có thiết bị GSM nào được khởi tạo!")
            return
        
        self.is_running = True
        self.results = {}
        self.total_numbers = len(phone_numbers)
        self.processed_numbers = 0
        
        # Phân chia số điện thoại theo yêu cầu:
        # - Chia 2 nhóm: VIETTEL và nhóm còn lại
        # - 2 cổng đầu nhận toàn bộ số VIETTEL (chia đều giữa 2 cổng)
        # - Các cổng còn lại nhận toàn bộ số nhóm khác (chia đều giữa các cổng còn lại)

        # Sắp xếp thiết bị theo thứ tự cổng tăng dần (COMxx)
        def _port_index(port: str) -> int:
            try:
                if port.startswith(self.port_prefix):
                    return int(port[len(self.port_prefix):])
            except Exception:
                pass
            return 0

        devices_sorted = sorted(self.devices.values(), key=lambda d: _port_index(d.port))
        num_devices = len(devices_sorted)

        # REMOVED: Trường hợp đặc biệt bỏ phân loại
        # OLD LOGIC: if num_devices <= 2 → chia đều (WRONG!)
        # NEW LOGIC: Luôn áp dụng COM38 exclusive cho Viettel

        # Helper detect nhà mạng (độc lập thiết bị)
        def _detect_carrier(number: str) -> str:
            prefix = number[:3]
            if len(number) > 10:
                return 'UNKNOWN'
            if prefix in ['086', '096', '097', '098', '032', '033', '034', '035', '036', '037', '038', '039']:
                return 'VIETTEL'
            if prefix in ['089', '090', '093', '070', '079', '077', '076', '078', '087']:
                return 'MOBIFONE'
            if prefix in ['088', '091', '094', '083', '084', '085', '081', '082']:
                return 'VINA'
            if prefix in ['092', '056', '058', '059', '099']:
                return 'VIETNAMOBILE'
            return 'UNKNOWN'

        viettel_numbers = []
        other_numbers = []
        for pn in phone_numbers:
            carrier = _detect_carrier(pn)
            if carrier == 'VIETTEL':
                viettel_numbers.append(pn)
            else:
                other_numbers.append(pn)

        device_tasks = {}
        # Nếu không có số VIETTEL → chia đều tất cả số cho tất cả thiết bị
        if len(viettel_numbers) == 0:
            for i, pn in enumerate(phone_numbers):
                dev = devices_sorted[i % num_devices]
                device_tasks.setdefault(dev.port, []).append(pn)
        else:
            # LOGIC MỚI: Phân số VIETTEL chỉ cho COM38
            viettel_device = None
            for dev in devices_sorted:
                if dev.port == "COM38":
                    viettel_device = dev
                    break
            
            if viettel_device and len(viettel_numbers) > 0:
                # Tất cả số VIETTEL dành cho COM38 
                # CRITICAL: Chỉ COM38 xử lý Viettel (sequential) để tránh PyAudio conflict
                device_tasks.setdefault(viettel_device.port, []).extend(viettel_numbers)
                self.log(f"Phân {len(viettel_numbers)} số VIETTEL cho {viettel_device.port} (sequential processing)")
            else:
                if len(viettel_numbers) > 0:
                    self.log(f"⚠️ Không tìm thấy COM38 cho {len(viettel_numbers)} số VIETTEL!")
                    # Fallback: phân cho thiết bị đầu tiên nếu không có COM38
                    if devices_sorted:
                        device_tasks.setdefault(devices_sorted[0].port, []).extend(viettel_numbers)
                        self.log(f"Fallback: Phân số VIETTEL cho {devices_sorted[0].port}")

            # Phân số còn lại (VINA/MOBI/VIETNAMOBILE) cho TẤT CẢ cổng TRỪ COM38
            non_viettel_devices = [dev for dev in devices_sorted if dev.port != "COM38"]
            if non_viettel_devices and len(other_numbers) > 0:
                for i, pn in enumerate(other_numbers):
                    dev = non_viettel_devices[i % len(non_viettel_devices)]
                    device_tasks.setdefault(dev.port, []).append(pn)
                self.log(f"Phân {len(other_numbers)} số khác cho {len(non_viettel_devices)} cổng (trừ COM38)")
            elif len(other_numbers) > 0:
                # Fallback nếu không có cổng nào khác
                for i, pn in enumerate(other_numbers):
                    dev = devices_sorted[i % len(devices_sorted)]
                    device_tasks.setdefault(dev.port, []).append(pn)
                self.log(f"Fallback: Phân {len(other_numbers)} số khác cho tất cả cổng")

        # self.log(f"Phân chia {len(phone_numbers)} số (VIETTEL={len(viettel_numbers)}, KHÁC={len(other_numbers)}) cho {num_devices} thiết bị:")
        for dev in devices_sorted:
            cnt = len(device_tasks.get(dev.port, []))
            self.log(f"  - {dev.port}: {cnt} số")
        
        # Khởi động worker threads
        threads = []
        for device in devices_sorted:
            if device.port in device_tasks:
                thread = threading.Thread(target=self._device_worker_thread, args=(device, result_callback, device_tasks[device.port]))
                thread.daemon = True
                thread.start()
                threads.append(thread)
        
        # Thread theo dõi tiến độ
        monitor_thread = threading.Thread(target=self._monitor_progress, args=(len(phone_numbers),))
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def _device_worker_thread(self, device: GSMDevice, result_callback: Callable, phone_numbers: List[str]):
        """Worker thread xử lý check số điện thoại cho một device"""
        # self.log(f"Device {device.port} bắt đầu xử lý {len(phone_numbers)} số")
        
        for i, phone_number in enumerate(phone_numbers):
            if not self.is_running:
                break
            
            try:
                device.is_busy = True
                self.log(f"Đang check số {phone_number} ...")
                
                # Check số điện thoại
                result_type = device.check_phone_number(phone_number)
                self.results[phone_number] = result_type
                self.processed_numbers += 1
                
                # Gọi callback với kết quả
                result_callback(phone_number, result_type)
                
                device.is_busy = False
                
                # Nghỉ giữa các cuộc gọi để tránh spam
                time.sleep(1)
                
            except Exception as e:
                self.log(f"Lỗi check số {phone_number} trên {device.port}: {str(e)}")
                device.is_busy = False
                self.processed_numbers += 1
                result_callback(phone_number, "THUÊ BAO")  # Fallback
        # self.log(f"Device {device.port} hoàn thành xử lý {len(phone_numbers)} số")
    
    def _monitor_progress(self, total_numbers: int):
        """Theo dõi tiến độ check"""
        while self.is_running:
            checked = self.processed_numbers
            if checked >= total_numbers:
                self.is_running = False
                # self.log("Hoàn thành check tất cả số điện thoại!")
                break
            time.sleep(1)
    
    # def start_multi_channel_audio_analysis(self, channels: List[int]) -> dict:
    #     """Bắt đầu phân tích âm thanh cho nhiều channels cùng lúc"""
    #     if not self.esp32_connected:
    #         self.log("ESP32 chưa kết nối!")
    #         return {ch: "ERROR" for ch in channels}
        
    #     try:
    #         self.log(f"Bắt đầu multi-channel audio analysis cho channels: {channels}")
    #         results = self.esp32_analyzer.analyze_audio_pattern_multi_channel(channels)
    #         self.log(f"Kết quả multi-channel analysis: {results}")
    #         return results
    #     except Exception as e:
    #         self.log(f"Lỗi multi-channel audio analysis: {str(e)}")
    #         return {ch: "ERROR" for ch in channels}
    
    def get_device_channels(self) -> List[int]:
        """Lấy danh sách channels của các device đang hoạt động"""
        channels = []
        for port, device in self.devices.items():
            if port in self.channel_mapping:
                channels.append(self.channel_mapping[port])
        return channels
    
    def stop_checking(self):
        """Dừng quá trình check"""
        self.is_running = False
    
    def get_progress(self) -> tuple:
        """Trả về tiến độ hiện tại với 3 loại kết quả"""
        checked = len(self.results)
        hoat_dong = sum(1 for result in self.results.values() if result == "HOẠT ĐỘNG")
        thue_bao = sum(1 for result in self.results.values() if result == "THUÊ BAO")
        so_khong_dung = sum(1 for result in self.results.values() if result == "SỐ KHÔNG ĐÚNG")
        return checked, hoat_dong, thue_bao, so_khong_dung
    
    def cleanup(self):
        """Dọn dẹp tài nguyên"""
        self.stop_checking()
        for device in self.devices.values():
            device.disconnect()
        self.devices.clear()
        
        # Disconnect ESP32
        if self.esp32_connected:
            self.esp32_analyzer.disconnect()
            self.esp32_connected = False 