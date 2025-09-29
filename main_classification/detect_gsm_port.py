"""
Quét tất cả COM ports, mở ở baudrate 115200, gửi "AT" và nếu nhận được "OK" -> đánh dấu là modem.
"""

import time
import json
from serial import Serial, SerialException
from serial.tools import list_ports

CMD = "AT\r"
OPEN_TIMEOUT = 1.0   # timeout khi mở cổng
REPLY_WAIT = 1.0     # thời gian chờ đọc reply (s)

def list_com_ports():
    return [p.device for p in list_ports.comports()]

def probe_port(port):
    """Mở port với baud 115200, gửi AT, đọc phản hồi trong REPLY_WAIT giây."""
    try:
        ser = Serial(port=port, baudrate=115200, timeout=0.1, write_timeout=0.5)
    except SerialException as e:
        return {"port": port, "ok": False, "reason": f"cannot open: {e}"}
    except Exception as e:
        return {"port": port, "ok": False, "reason": f"open error: {e}"}

    try:
        # flush input/output, một vài thiết bị cần thời gian để ổn định
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.05)

        ser.write(CMD.encode())
        ser.flush()

        # đọc trong khoảng REPLY_WAIT giây
        end = time.time() + REPLY_WAIT
        collected = b""
        while time.time() < end:
            try:
                n = ser.in_waiting
            except Exception:
                n = 0
            if n:
                collected += ser.read(n)
            else:
                time.sleep(0.05)

        text = collected.decode(errors="ignore").strip()
        ser.close()

        # tìm "OK" trong reply (không phân biệt hoa thường)
        if "ok" in text.lower():
            return {"port": port, "ok": True, "reply": text}
        else:
            return {"port": port, "ok": False, "reply": text or "<no reply>"}
    except Exception as e:
        try:
            ser.close()
        except Exception:
            pass
        return {"port": port, "ok": False, "reason": f"probe error: {e}"}


#!/usr/bin/env python3
"""
detect_gsm_extended.py

Quét cổng COM (baud 115200). Nếu port trả lời "OK" với lệnh AT thì coi là modem.
Sau đó lấy thêm thông tin:
 - Tín hiệu mạng (AT+CSQ)
 - Số điện thoại của SIM (AT+CNUM)
 - Số tiền tài khoản (thử nghĩa vụ USSD bằng AT+CUSD)

Usage:
    pip install pyserial
    python detect_gsm_extended.py
"""

BAUD = 115200
AT_CMD = "AT\r"
OPEN_TIMEOUT = 1.0
REPLY_WAIT = 1.0    # base wait for simple AT replies
LONG_WAIT = 5.0     # wait for USSD reply (USSD có thể mất vài giây)

# Danh sách mã USSD thử (thông dụng ở VN nhưng không chắc chắn với mọi nhà mạng)
USSD_CODES = ["*101#", "*101*1#", "*123#", "*100#"]

def list_com_ports():
    return [p.device for p in list_ports.comports()]

def read_all(ser, wait_time):
    """Đọc dữ liệu trong wait_time giây (polling)"""
    end = time.time() + wait_time
    collected = b""
    while time.time() < end:
        try:
            n = ser.in_waiting
        except Exception:
            n = 0
        if n:
            try:
                collected += ser.read(n)
            except Exception:
                pass
        else:
            time.sleep(0.05)
    try:
        return collected.decode(errors="ignore").strip()
    except Exception:
        return str(collected)

def send_at_and_read(ser, cmd, wait=REPLY_WAIT):
    """Gửi một lệnh AT (chuỗi đã kèm CR nếu cần) và đọc trả lời"""
    if not cmd.endswith("\r"):
        cmd = cmd + "\r"
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass
    ser.write(cmd.encode(errors="ignore"))
    ser.flush()
    return read_all(ser, wait)

def probe_port_simple(port):
    """Mở port ở BAUD, gửi AT, nếu reply chứa OK -> valid"""
    try:
        ser = Serial(port=port, baudrate=BAUD, timeout=0.1, write_timeout=0.5)
    except SerialException as e:
        return {"port": port, "ok": False, "reason": f"open error: {e}"}
    except Exception as e:
        return {"port": port, "ok": False, "reason": f"open unknown error: {e}"}

    try:
        time.sleep(0.05)
        reply = send_at_and_read(ser, "AT", wait=REPLY_WAIT)
        ser.close()
    except Exception as e:
        try:
            ser.close()
        except Exception:
            pass
        return {"port": port, "ok": False, "reason": f"probe error: {e}"}

    if "ok" in reply.lower():
        return {"port": port, "ok": True, "reply": reply}
    else:
        return {"port": port, "ok": False, "reply": reply or "<no reply>"}

# ---------------- khi xác định được cổng COM GSM thì sử dụng các hàm sau để lấy thêm thông tin ----------------

def get_signal_info(ser):
    """
    Gửi AT+CSQ và parse +CSQ: <rssi>,<ber>
    rssi: 0..31, 99 = not known or not detectable
    dBm ≈ -113 + 2*rssi  (khoảng)
    """
    resp = send_at_and_read(ser, "AT+CSQ", wait=REPLY_WAIT)
    # tìm +CSQ: line
    for line in resp.splitlines():
        line = line.strip()
        if line.upper().startswith("+CSQ"):
            # +CSQ: <rssi>,<ber>
            try:
                parts = line.split(":")[1].strip().split(",")
                rssi = int(parts[0])
                ber = int(parts[1]) if len(parts) > 1 else None
                if rssi == 99:
                    return {"raw": line, "rssi": None, "ber": ber, "dbm": None, "note": "unknown"}
                dbm = -113 + 2 * rssi
                return {"raw": line, "rssi": rssi, "ber": ber, "dbm": dbm}
            except Exception:
                return {"raw": line, "parse_error": True}
    # fallback: trả về toàn bộ response
    return {"raw": resp}

def get_phone_number(ser):
    """
    Thử AT+CNUM để lấy MSISDN (tùy SIM/nhà mạng).
    Format: +CNUM: "NAME","<number>",<type>,<speed>,<service>
    Nếu không có -> trả None
    """
    resp = send_at_and_read(ser, "AT+CNUM", wait=REPLY_WAIT)
    # tìm +CNUM
    for line in resp.splitlines():
        line = line.strip()
        if line.upper().startswith("+CNUM"):
            # try parse number in quotes
            try:
                # ví dụ: +CNUM: "","0123456789",145,7,4
                after = line.split(":",1)[1]
                # lấy tất cả các chuỗi trong dấu ngoặc kép
                quotes = []
                cur = ""
                inq = False
                for ch in after:
                    if ch == '"':
                        inq = not inq
                        if not inq:
                            quotes.append(cur)
                            cur = ""
                    elif inq:
                        cur += ch
                # số thường nằm ở quotes[1] theo format trên
                number = None
                if len(quotes) >= 2 and quotes[1].strip():
                    number = quotes[1].strip()
                else:
                    # fallback: thử tách bằng dấu phẩy, phần thứ 1/2 có vẻ là số không trong quotes
                    parts = [p.strip().strip('"') for p in after.split(",")]
                    if parts:
                        # tìm phần nào có nhiều chữ số
                        for p in parts:
                            if any(ch.isdigit() for ch in p) and len([c for c in p if c.isdigit()]) >= 6:
                                number = p
                                break
                return {"raw": line, "number": number}
            except Exception:
                return {"raw": line, "parse_error": True}
    # nếu không có +CNUM, trả về response để debug
    return {"raw": resp, "number": None}

def try_ussd_for_balance(ser, codes=USSD_CODES):
    """
    Thử các mã USSD trong danh sách; trả về nội dung trả về đầu tiên của +CUSD.
    Cách gửi: AT+CUSD=1,"<code>",15
    Lưu ý: sau lệnh này modem sẽ trả +CUSD: ... (cần đợi lâu hơn)
    """
    # Bật chế độ USSD result format (1) nếu cần
    # Một số modem yêu cầu AT+CUSD=1 để kích hoạt
    send_at_and_read(ser, "AT+CUSD=1", wait=0.6)

    for code in codes:
        # gửi và chờ lâu hơn vì USSD có thể mất thời gian
        cmd = f'AT+CUSD=1,"{code}",15'
        resp = send_at_and_read(ser, cmd, wait=LONG_WAIT)
        # đôi khi modem trả ngay "OK" và sau vài giây trả +CUSD,...
        # chờ thêm 1-2s để xem có +CUSD xuất hiện không
        more = read_all(ser, 2.0)
        if more:
            resp = (resp + "\n" + more).strip()

        # tìm +CUSD:
        for line in resp.splitlines():
            l = line.strip()
            if l.upper().startswith("+CUSD"):
                # +CUSD: 0,"<text>",15
                # extract quoted text
                # nếu trả về chuỗi hex (kiểu "00..."), modem có thể trả UCS2 -> cần decode; 
                # ở đây ta lấy raw text trong quotes nếu có, hoặc toàn dòng
                try:
                    # tìm phần trong quotes
                    start = l.find('"')
                    end = l.rfind('"')
                    if start != -1 and end != -1 and end > start:
                        content = l[start+1:end]
                    else:
                        # fallback: lấy phần sau : và loại status
                        parts = l.split(":",1)
                        content = parts[1].strip() if len(parts) > 1 else l
                    return {"ussd_code": code, "raw": l, "content": content}
                except Exception:
                    return {"ussd_code": code, "raw": l, "content": None}
        # Nếu không thấy +CUSD nhưng có text khác (tạm chấp nhận)
        if resp and "OK" not in resp.upper():
            # treat as potential result
            return {"ussd_code": code, "raw": resp, "content": resp}
    return {"ussd_code": None, "raw": None, "content": None}

def main():
    ports = list_com_ports()
    if not ports:
        print("[INFO] Không tìm thấy cổng COM/TTY nào.")
        return

    print(f"[INFO] Found ports: {ports}")
    results = []
    
    # Buoc 1: Quet tat ca ports de tim GSM
    print("\n=== BUOC 1: QUET CONG GSM ===")
    for p in ports:
        res = probe_port_simple(p)
        results.append(res)
        if res.get("ok"):
            print(f"[FOUND] {p} => replies: {res.get('reply')}")
        else:
            r = res.get("reply") or res.get("reason")
            print(f"[SKIP ] {p} => {r}")

    # Buoc 2: Thu thap thong tin chi tiet tu cac GSM ports
    found = [r for r in results if r.get("ok")]
    if found:
        print("\n=== BUOC 2: THU THAP THONG TIN CHI TIET ===")
        for f in found:
            port = f['port']
            print(f"\n--- Thong tin chi tiet {port} ---")
            
            try:
                ser = Serial(port=port, baudrate=BAUD, timeout=0.1, write_timeout=0.5)
                time.sleep(0.1)
                
                # Lay thong tin tin hieu
                signal_info = get_signal_info(ser)
                print(f"Tin hieu: {signal_info}")
                
                # Lay so dien thoai
                phone_info = get_phone_number(ser)
                print(f"So dien thoai: {phone_info}")
                
                # Thu USSD de lay so du
                balance_info = try_ussd_for_balance(ser)
                print(f"So du: {balance_info}")
                
                ser.close()
                
            except Exception as e:
                print(f"Loi khi lay thong tin {port}: {e}")
    else:
        print("\n[INFO] Khong tim thay port tra loi 'OK'. Kiem tra driver/permission/thiet bi.")

if __name__ == "__main__":
    main()
