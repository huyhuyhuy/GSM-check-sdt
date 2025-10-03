import serial
import time

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

    # gửi lệnh AT tới GSM để check tình trạng cuộc gọi (AT+CLCC)
    def get_call_status(self):
        return self.send_command("AT+CLCC")
