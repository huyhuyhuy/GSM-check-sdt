import time
import threading
from typing import Callable



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
    except Exception as e:
        return -1

def ultra_fast_check_vina_mobi_vietnamobile(device, phone_number: str, log_callback: Callable = None) -> str:
    """
    Check nhanh cho 3 nhà mạng dễ: Vina, Mobifone, Vietnamobile
    Logic: Chờ status 3 (ALERTING) tối đa 10 giây
    Trả về: HOẠT ĐỘNG, THUÊ BAO, SỐ KHÔNG ĐÚNG
    """
    def log(message: str):
        if log_callback:
            log_callback(message)
        else:
            print(f"[{phone_number}] {message}")
    
    # Logic này chỉ được gọi cho Vina, Mobifone, Vietnamobile
    # Không cần kiểm tra carrier nữa vì đã được kiểm tra ở gsm_manager_enhanced.py
    # log(f"Áp dụng logic nhanh cho Vina/Mobifone/Vietnamobile")

    
    try:
        # Đảm bảo modem sẵn sàng
        ready_response = device.send_command_quick("AT")
        if "OK" not in ready_response:
            log(f"Modem không sẵn sàng")
            try:
                device.send_command_quick("ATH")
            except:
                pass
            return "THUÊ BAO"

        device.send_command_quick("ATH")
        time.sleep(1)

        # Gửi lệnh gọi
        call_command = f'ATD{phone_number};'
        log(f"Gửi lệnh gọi...")
        device.serial_connection.reset_input_buffer()
        device.serial_connection.reset_output_buffer()
        device.serial_connection.write((call_command + '\r\n').encode())
        time.sleep(1)

        # Chờ status 3 (ALERTING) - tối đa 10 giây
        start_time = time.time()
        timeout = 10.0
        status_2_time = None  # Thời điểm phát hiện status 2
        
        # log(f"Bắt đầu chờ status 3 (ALERTING) tối đa {timeout} giây...")
        log(f"ESP Thread - Thu ADC, lưu file và phân tích")

        # trường hợp khi có CLCC status 2 sau đó 1 đến 3 giây thấy CLCC staus = 6 luôn đó là không tín hiệu -> return thuê bao
        while time.time() - start_time < timeout:
            clcc_response = device.send_command_quick("AT+CLCC", 0.5)
            
            if "+CLCC:" in clcc_response:
                status = parse_clcc_status(clcc_response)
                log(f"ESP Status: {status}")
                
                if status == 0:  # Nhấc máy
                    log(f"Phát hiện nhấc máy → HOẠT ĐỘNG")
                    device.send_command_quick("ATH")
                    return "HOẠT ĐỘNG"
                elif status == 2:  # Đang kết nối
                    if status_2_time is None:
                        status_2_time = time.time()
                        # log(f"Phát hiện status 2 (đang kết nối)")
                elif status == 3:  # ALERTING (đổ chuông)
                    log(f"Phát hiện đổ chuông → HOẠT ĐỘNG")
                    device.send_command_quick("ATH")
                    return "HOẠT ĐỘNG"
                elif status == 6:  # Gác máy/từ chối sớm
                    # Kiểm tra tình huống status 2 → status 6 trong 1-3 giây
                    if status_2_time is not None:
                        time_diff = time.time() - status_2_time
                        if 1.0 <= time_diff <= 3.0:
                            # log(f"Status 2 → Status 6 trong {time_diff:.1f}s → THUÊ BAO")
                            device.send_command_quick("ATH")
                            return "THUÊ BAO"
                    
                    log(f"Phát hiện gác máy/từ chối sớm → HOẠT ĐỘNG")
                    device.send_command_quick("ATH")
                    return "HOẠT ĐỘNG"
            
            time.sleep(0.5)  # Poll mỗi 500ms
        
        # Sau 10 giây không có status 3 → THUÊ BAO
        # log(f"Không phát hiện status 3 sau {timeout} giây → THUÊ BAO")
        device.send_command_quick("ATH")
        return "THUÊ BAO"
        
    except Exception as e:
        log(f"Lỗi check nhanh: {str(e)}")
        try:
            device.send_command_quick("ATH")
        except:
            pass
        return "HOẠT ĐỘNG"  # Fallback mặc định HOẠT ĐỘNG