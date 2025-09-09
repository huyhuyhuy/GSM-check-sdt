# GSM Phone Number Checker - Enhanced with ESP32 Audio Analysis

Tool kiểm tra số điện thoại sử dụng GSM 32 cổng với chip XR21V1414, tích hợp ESP32 để phân tích âm thanh và AT+CLCC để tối ưu chi phí.

## Tính năng mới

- **ESP32 Audio Analysis**: Phân tích tín hiệu âm thanh từ GSM modem
- **AT+CLCC Polling**: Detect người nhấc máy ngay lập tức để tiết kiệm chi phí
- **ADC Pattern Recognition**: Phân loại âm thanh (RINGTONE, VOICE_MACHINE, BLOCKED)
- **Real-time Plotting**: Vẽ đồ thị ADC waveform và histogram
- **Enhanced GUI**: Giao diện cải tiến với thông tin ESP32 status

## Tính năng cơ bản

- Hỗ trợ tối đa 32 cổng GSM đồng thời
- Giao diện đơn giản, dễ sử dụng
- Tự động quét và khởi tạo các cổng COM
- Xử lý đa luồng để tối ưu hiệu năng
- Xuất kết quả ra 2 file riêng biệt
- Log chi tiết quá trình thực hiện

## Yêu cầu hệ thống

- Windows 10/11
- Python 3.7+
- Thiết bị GSM 32 cổng với chip XR21V1414
- ESP32 với code audio analyzer
- Driver cho thiết bị GSM
- Kết nối phần cứng: GSM Audio → MAX9814 → CD74HC4067 → ESP32

## Cài đặt

### Cách 1: Chạy từ source code
1. Clone hoặc tải về project
2. Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```
3. Chạy chương trình:
```bash
python main_enhanced.py
```

### Cách 2: Build thành file exe (Khuyến nghị)
1. Chạy lệnh:
```bash
python build.py
```
2. File exe sẽ được tạo trong thư mục `dist/`

## Sử dụng

1. Kết nối thiết bị GSM 32 cổng và ESP32 vào máy tính
2. Chạy chương trình:
   - **File exe**: Double-click `GSM_Phone_Checker.exe`
   - **Source code**: `python main_enhanced.py`

3. Trong giao diện:
   - Nhấn "Nhập File" để chọn file danh sách số điện thoại
   - Nhấn "Bắt Đầu" để bắt đầu kiểm tra
   - Theo dõi tiến độ trong ô log
   - Nhấn "Vẽ Đồ Thị ADC" để xem phân tích âm thanh
   - Nhấn "Xuất Kết Quả" để lưu kết quả

## Logic phân loại mới

### 1. HOẠT ĐỘNG (Active):
- **GSM Response**: CONNECT, BUSY, NO ANSWER, RINGING
- **AT+CLCC**: status=0 (người nhấc máy)
- **ADC Pattern**: RINGTONE (khi GSM không xác định)

### 2. KHÔNG HOẠT ĐỘNG (Inactive):
- **GSM Response**: ERROR, NO DIALTONE, +CME, NO CARRIER
- **ADC Pattern**: VOICE_MACHINE, BLOCKED (khi GSM không xác định)

### Ưu tiên kết quả:
1. **AT+CLCC status=0** → HOẠT ĐỘNG (ngắt ngay)
2. **GSM Response** → Phân loại theo keywords
3. **ADC Pattern** → Fallback khi GSM không xác định

## Cấu trúc file

### Source code:
- `main_enhanced.py`: Giao diện chính với ESP32 support
- `gsm_manager_enhanced.py`: Quản lý GSM với AT+CLCC và ESP32
- `esp32_audio_analyzer.py`: Phân tích âm thanh từ ESP32
- `file_manager.py`: Đọc và ghi file
- `requirements.txt`: Danh sách thư viện cần thiết

### Build tools:
- `build.py`: Script build file exe (chạy trực tiếp: `python build.py`)
- `install.bat`: Script cài đặt (được tạo sau khi build)
- `README_EXE.txt`: Hướng dẫn cho người dùng exe

## Định dạng file đầu vào

File txt chứa danh sách số điện thoại, mỗi số một dòng:
```
0123456789
0987654321
0123456780
...
```

## Kết quả xuất

Tool sẽ tạo 2 file trong thư mục `results/`:
- `active_numbers_YYYYMMDD_HHMMSS.txt`: Các số còn hoạt động
- `inactive_numbers_YYYYMMDD_HHMMSS.txt`: Các số không liên lạc được

## Lưu ý

- Đảm bảo thiết bị GSM đã được cài đặt driver đúng cách
- Kiểm tra tín hiệu mạng trước khi sử dụng
- Có thể mất phí cuộc gọi khi check số điện thoại
- Tool sẽ tự động hủy cuộc gọi sau khi kiểm tra
- ESP32 phải được nạp code audio analyzer trước khi sử dụng

## Troubleshooting

1. **Không tìm thấy cổng COM**: Kiểm tra driver và kết nối thiết bị
2. **Lỗi kết nối GSM**: Kiểm tra SIM card và tín hiệu mạng
3. **ESP32 không kết nối**: Kiểm tra cổng COM và code Arduino
4. **Hiệu năng chậm**: Đảm bảo tất cả 32 cổng đều hoạt động
5. **ADC data không chính xác**: Kiểm tra kết nối phần cứng và threshold

## Phiên bản

- Version: 2.0 (Enhanced with ESP32)
- Ngày phát hành: 2024
- Tính năng mới: ESP32 Audio Analysis, AT+CLCC Polling, Real-time Plotting 