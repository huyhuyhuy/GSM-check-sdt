#  cấu hình lại baudrate của EC20 từ 115200 sang 921600
import serial
import time

def set_ec20_baudrate(com_port):
    ser = serial.Serial(com_port, 115200, timeout=1)
    cmds = ["AT+IPR=921600\r\n", "AT&W\r\n", "AT+CFUN=1,1\r\n"]
    for cmd in cmds:
        ser.write(cmd.encode())
        time.sleep(0.5)
        print(ser.read(128).decode(errors="ignore"))
    ser.close()
    print(f"Đã set {com_port} sang 921600, hãy mở lại COM với baudrate 921600.")

if __name__ == "__main__":
    set_ec20_baudrate("COM37")