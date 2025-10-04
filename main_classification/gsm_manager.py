import serial
import time
import logging

class GSMDevice:
    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.is_connected = False

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
            return f"ERROR: {str(e)}"

    # gửi lệnh AT tới GSM để check tình trạng sóng (AT+CSQ)
    def get_signal_info(self):
        return self.send_command("AT+CSQ")

    # gửi lệnh AT tới GSM để check số điện thoại (AT+CNUM)
    def get_phone_number(self):
        return self.send_command("AT+CNUM")

    # gửi lệnh AT tới GSM để check số dư còn lại của sim (AT+CUSD=1,"*101#",15)
    def get_balance(self):
        return self.send_command("AT+CUSD=1,\"*101#\",15")
    
    def check_call_status(self):
        """Kiểm tra trạng thái cuộc gọi hiện tại"""
        response = self.send_command("AT+CPAS", wait_time=1.0)
        if "4" in response:  # 4 = call in progress
            return True
        elif "0" in response:  # 0 = ready
            return False
        else:
            return False
    
    def check_picked_up(self):
        """Kiểm tra xem có người nhấc máy không bằng AT+CLCC"""
        response = self.send_command("AT+CLCC", wait_time=0.5)
        # Tìm các dấu hiệu người nhấc máy
        if "+COLP" in response or "CONNECT" in response:
            return True
        return False
    
    def make_call(self, phone_number: str):
        """Thực hiện cuộc gọi"""
        response = self.send_command(f"ATD{phone_number};", wait_time=3.0)
        return "ERROR" not in response
    
    def hang_up(self):
        """Ngắt cuộc gọi"""
        response = self.send_command("ATH", wait_time=2.0)
        return "OK" in response
    
    def start_recording(self, filename: str = "record.amr"):
        """Bắt đầu ghi âm"""
        response = self.send_command(f'AT+QAUDRD=1,"{filename}",13,1', wait_time=3.0)
        return "ERROR" not in response
    
    def stop_recording(self, filename: str = "record.amr"):
        """Dừng ghi âm"""
        response = self.send_command(f'AT+QAUDRD=0,"{filename}",13,1', wait_time=2.0)
        return "ERROR" not in response
    
    def delete_file(self, filename: str):
        """Xóa file trên module"""
        response = self.send_command(f'AT+QFDEL="{filename}"', wait_time=1.0)
        return "OK" in response
    
    def get_signal_strength(self):
        """Lấy thông tin tín hiệu"""
        response = self.send_command("AT+CSQ", wait_time=1.0)
        return response
    
    def get_network_info(self):
        """Lấy thông tin mạng"""
        response = self.send_command("AT+COPS?", wait_time=2.0)
        return response
    
    def get_registration_status(self):
        """Kiểm tra trạng thái đăng ký mạng"""
        response = self.send_command("AT+CREG?", wait_time=2.0)
        return response
    
    def reset_module(self):
        """Reset module"""
        try:
            response = self.send_command("AT+CFUN=1,1", wait_time=5.0)
            return "OK" in response
        except Exception as e:
            logging.error(f"Lỗi khi reset module: {e}")
            return False
