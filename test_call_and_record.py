import serial
import time
import sys
import re
import os
import subprocess
from pathlib import Path
from datetime import datetime

# ---------- CONFIG ----------
SERIAL_PORT = "COM37"      # Test trên com 37
BAUDRATE = 921600
PHONE = "0379543103"     
# Tạo tên file unique với timestamp để tránh ghi đè
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REMOTE_FILENAME = "record.amr"  # Tên file đơn giản
LOCAL_FILENAME = f"{PHONE}_{TIMESTAMP}.amr"   # Tên file local đầy đủ
FORMAT = 13               # format từ AT+QAUDRD=? (giá trị 13 theo phản hồi của bạn)
CHUNK = 65536  # 64KB chunk - cân bằng tốc độ và ổn định
# ---------------------------

def open_serial(port, baud):
    s = serial.Serial(port, baud, timeout=5)  # Tăng timeout cho baudrate cao
    time.sleep(0.5)  # Đợi lâu hơn
    s.reset_input_buffer()
    s.reset_output_buffer()
    return s

def send_at(ser, cmd, timeout=3, binary_mode=False):
    ser.write((cmd + "\r\n").encode())
    deadline = time.time() + timeout
    resp = b""
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            resp += chunk
            # Với binary mode, không dừng khi gặp OK/ERROR
            if not binary_mode and (b"\r\nOK\r\n" in resp or b"\r\nERROR\r\n" in resp):
                break
        else:
            time.sleep(0.03)  # Giảm từ 0.05 xuống 0.03
    
    if binary_mode:
        return resp  # Trả về raw bytes
    else:
        return resp.decode(errors="ignore")

def read_exact(ser, length, timeout=5):
    """Đọc đúng length byte trong khoảng timeout"""
    deadline = time.time() + timeout
    data = b""
    while len(data) < length and time.time() < deadline:
        chunk = ser.read(length - len(data))
        if chunk:
            data += chunk
        else:
            time.sleep(0.001)  # Ngủ rất ngắn
    return data

def expect_ok(resp):
    return "\r\nOK\r\n" in resp

#  cấu hình lại baudrate của EC20
def set_ec20_baudrate(com_port):
    ser = serial.Serial(com_port, 115200, timeout=1)
    cmds = ["AT+IPR=921600\r\n", "AT&W\r\n", "AT+CFUN=1,1\r\n"]
    for cmd in cmds:
        ser.write(cmd.encode())
        time.sleep(0.5)
        print(ser.read(128).decode(errors="ignore"))
    ser.close()
    print(f"Đã set {com_port} sang 921600, hãy mở lại COM với baudrate 921600.")


def check_call_status(ser):
    """Kiểm tra trạng thái cuộc gọi"""
    resp = send_at(ser, "AT+CPAS", timeout=2)
    if "4" in resp:  # 4 = call in progress
        return True
    elif "0" in resp:  # 0 = ready
        return False
    else:
        print(f"Trạng thái cuộc gọi không rõ: {resp}")
        return False

def wait_for_call_established(ser, max_wait=10):
    """Đợi cuộc gọi được thiết lập"""
    print("Đang đợi cuộc gọi được thiết lập...")
    for i in range(max_wait):
        if check_call_status(ser):
            print(f"Cuộc gọi đã được thiết lập sau {i+1} giây")
            return True
        time.sleep(1)
    print("Cuộc gọi không được thiết lập trong thời gian cho phép")
    return False

def try_parse_qfopen(resp):
    m = re.search(r"\+QFOPEN:\s*(\d+)", resp)
    if m:
        return int(m.group(1))
    return None

def list_files_on_module(ser):
    """Liệt kê các file trên module"""
    print("Liệt kê file trên module...")
    resp = send_at(ser, 'AT+QFLST="*"', timeout=5)
    print("Danh sách file:", resp)
    return resp

def delete_old_record_files(ser):
    """Xóa các file record cũ trên module"""
    print("Xóa các file record cũ...")
    resp = send_at(ser, 'AT+QFLST="record_*"', timeout=5)
    print("Files cũ:", resp)
    
    # Tìm và xóa các file record cũ
    lines = resp.split('\n')
    for line in lines:
        if 'record_' in line and '.amr' in line:
            # Extract filename from line like: +QFLST: "record_20241201_143022.amr",239084
            match = re.search(r'\+QFLST:\s*"([^"]+)"', line)
            if match:
                filename = match.group(1)
                print(f"Xóa file cũ: {filename}")
                del_resp = send_at(ser, f'AT+QFDEL="{filename}"', timeout=3)
                print(f"Kết quả xóa: {del_resp}")

def download_file_via_qfread(ser, remote_name, local_path):
    # Kiểm tra và lấy file size
    resp = send_at(ser, f'AT+QFLST="{remote_name}"', timeout=3)
    if "ERROR" in resp:
        return False
    
    # Lấy file size từ response
    file_size = 0
    size_match = re.search(r'\+QFLST:\s*"[^"]+",(\d+)', resp)
    if size_match:
        file_size = int(size_match.group(1))
        print(f"File size: {file_size} bytes")

    resp = send_at(ser, f'AT+QFOPEN="{remote_name}",0', timeout=3)
    fd = try_parse_qfopen(resp)
    if fd is None:
        return False

    total_bytes = 0
    
    try:
        with open(local_path, "wb") as f:
            chunk_count = 0
            while True:
                chunk_count += 1
                
                # Tính chunk size cho lần đọc này
                remaining = file_size - total_bytes
                current_chunk = min(CHUNK, remaining)
                
                # Gửi lệnh QFREAD và đọc toàn bộ response
                ser.write(f"AT+QFREAD={fd},{current_chunk}\r\n".encode())
                
                # Đọc toàn bộ response (bao gồm CONNECT và binary data)
                response = b""
                start_time = time.time()
                while time.time() - start_time < 5:  # Timeout 5 giây để tăng tốc
                    if ser.in_waiting > 0:
                        response += ser.read(ser.in_waiting)
                        # Kiểm tra xem đã có đủ dữ liệu chưa (có CONNECT và OK)
                        if b"CONNECT" in response and b"\r\nOK\r\n" in response:
                            break
                    else:
                        time.sleep(0.005)  # Giảm sleep time để tăng tốc
                
                # Parse length từ response
                response_str = response.decode(errors="ignore")
                m = re.search(r"CONNECT\s+(\d+)", response_str)
                if m:
                    length = int(m.group(1))
                    percentage = (total_bytes / file_size * 100) if file_size > 0 else 0
                    print(f"Chunk {chunk_count}: {length} bytes ({total_bytes}/{file_size}, {percentage:.1f}%)")
                    
                    # Tìm vị trí binary data
                    connect_pos = response.find(b"CONNECT")
                    if connect_pos != -1:
                        line_end = response.find(b"\r\n", connect_pos)
                        if line_end != -1:
                            data_start = line_end + 2
                            ok_pos = response.find(b"\r\nOK\r\n")
                            if ok_pos != -1:
                                data_end = ok_pos
                                binary_data = response[data_start:data_end]
                                f.write(binary_data[:length])
                                total_bytes += min(length, len(binary_data))
                            else:
                                break
                        else:
                            break
                    else:
                        break
                else:
                    print(f"Không tìm thấy CONNECT trong response: {response_str[:200]}...")
                    break
                
                if length == 0:
                    print("Đã đọc hết file")
                    break
                
                if length < CHUNK:
                    print("Đã đọc hết file (length < CHUNK)")
                    break

    except Exception as e:
        return False
    finally:
        send_at(ser, f"AT+QFCLOSE={fd}", timeout=2)
    
    return total_bytes > 0

# Removed AMR to WAV conversion functions - not needed for streamlined workflow

def main():
    try:
        ser = open_serial(SERIAL_PORT, BAUDRATE)
    except Exception as e:
        print("Không thể mở cổng serial:", e)
        sys.exit(1)

    print("=== GSM RECORDING TOOL ===")
    print(f"Gọi tới: {PHONE}")
    print(f"File sẽ lưu: {LOCAL_FILENAME}")
    # cấu hình lại baudrate của EC20
    # set_ec20_baudrate(SERIAL_PORT)

    # Gọi điện và đợi 1 giây
    print("Đang gọi...")
    call_resp = send_at(ser, f"ATD{PHONE};", timeout=5)
    if "ERROR" in call_resp:
        print("❌ Lỗi khi gọi điện")
        ser.close()
        return
    
    print("✅ Đã gọi, đợi cuộc gọi được thiết lập...")
    time.sleep(1.5)  # Giảm từ 2s xuống 1.5s
    
    # Kiểm tra trạng thái cuộc gọi
    call_status = send_at(ser, "AT+CPAS", timeout=2)
    print(f"Trạng thái cuộc gọi: {call_status}")
    
    # Xóa file cũ nếu có
    print("Xóa file cũ...")
    send_at(ser, f'AT+QFDEL="{REMOTE_FILENAME}"', timeout=2)
    
    # Bắt đầu ghi âm với format 13 (đã test thành công)
    print("🎤 Bắt đầu ghi âm (15 giây)...")
    cmd_start = f'AT+QAUDRD=1,"{REMOTE_FILENAME}",{FORMAT},1'  # Format 13
    record_resp = send_at(ser, cmd_start, timeout=3)
    print(f"Response ghi âm: {record_resp}")
    
    if "ERROR" in record_resp or "CME ERROR" in record_resp:
        print("❌ Không thể bắt đầu ghi âm. Kết thúc.")
        ser.close()
        return
    
    # Ghi âm 15 giây (không hiển thị progress để tăng tốc)
    print("Đang ghi âm 15 giây...")
    time.sleep(15)
    
    # Dừng ghi âm
    print("⏹️  Dừng ghi âm...")
    cmd_stop = f'AT+QAUDRD=0,"{REMOTE_FILENAME}",{FORMAT},1'  # Format 13
    stop_resp = send_at(ser, cmd_stop, timeout=2)
    print(f"Response dừng ghi âm: {stop_resp}")
    
    # Đợi module lưu file hoàn toàn (giảm từ 1s xuống 0.5s)
    print("⏳ Đợi module lưu file...")
    time.sleep(0.5)
    
    # Ngắt cuộc gọi bằng ATH
    print("📞 Ngắt cuộc gọi...")
    send_at(ser, "ATH", timeout=2)
    
    # Tải file
    print("💾 Đang tải file...")
    local_path = os.path.join(os.path.dirname(__file__), LOCAL_FILENAME)
    ok = download_file_via_qfread(ser, REMOTE_FILENAME, local_path)
    
    if ok:
        print(f"✅ Hoàn tất: {LOCAL_FILENAME}")
    else:
        print("❌ Không tải được file")

    ser.close()
    print("🏁 Kết thúc!")

if __name__ == "__main__":
    main()