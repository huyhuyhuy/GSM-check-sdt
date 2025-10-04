# GSM Phone Number Classification System

Hệ thống phân loại số điện thoại tự động sử dụng thiết bị GSM với khả năng xử lý đa luồng cho 32 cổng SIM.

## 🎯 Tính năng chính

- **Quét tự động**: Tự động phát hiện và kết nối đến 32 cổng GSM
- **Gọi đồng thời**: Xử lý đa luồng cho nhiều cuộc gọi cùng lúc
- **Ghi âm thông minh**: Ghi âm 15 giây và phát hiện người nhấc máy
- **Phân loại tự động**: Sử dụng AI để phân loại 7 loại số điện thoại
- **Xuất Excel**: Báo cáo chi tiết với biểu đồ và thống kê

## 📋 Phân loại số điện thoại

1. **Hoạt động** - Người nghe đã nhấc máy
2. **Để lại lời nhắn** - Hộp thư thoại
3. **Bị chặn** - Thuê bao tạm khóa
4. **Không liên lạc được** - Thuê bao tạm thời không liên lạc được
5. **Số không đúng** - Số điện thoại không tồn tại
6. **Nhạc chờ** - Tiếng tút chuông
7. **Im lặng** - Không có âm thanh hoặc không xác định

## 🛠️ Cài đặt

### 1. Cài đặt Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Cài đặt thêm (nếu cần)

```bash
# Cho speech-to-text
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Cho audio processing
pip install ffmpeg-python
```

### 3. Chuẩn bị thiết bị

- Kết nối modem GSM với máy tính qua USB
- Đảm bảo driver đã được cài đặt
- Kiểm tra các cổng COM được nhận diện

## 🚀 Sử dụng

### 1. Chạy hệ thống

```bash
python main_gui.py
```

### 2. Chuẩn bị file số điện thoại

Tạo file text (ví dụ: `list_sdt.txt`) với mỗi số điện thoại trên một dòng:

```
0987654321
0987654322
0987654323
0987654324
0987654325
```

### 3. Quy trình sử dụng

1. **Khởi động**: Hệ thống tự động quét và hiển thị các cổng GSM
2. **Chọn file**: Click "Nhập File" để chọn file danh sách số điện thoại
3. **Bắt đầu**: Click "Bắt Đầu" để bắt đầu xử lý
4. **Theo dõi**: Xem log real-time trong cửa sổ log
5. **Dừng**: Click "Dừng" nếu cần dừng giữa chừng
6. **Xuất kết quả**: Click "Xuất Kết Quả" để lưu file Excel

## 📊 Kết quả

File Excel xuất ra sẽ bao gồm:

- **Sheet Tổng Hợp**: Thống kê tổng quan với biểu đồ
- **Sheet chi tiết**: Dữ liệu chi tiết cho từng loại phân loại
- **Thông tin**: Cổng GSM, số điện thoại, thời gian, file audio, nội dung

## 🔧 Cấu hình

### Baudrate
- **Mặc định**: 115200 (khi khởi động)
- **Tự động**: Tăng lên 921600 khi xử lý

### Timeout
- **Ghi âm**: 15 giây
- **Check CLCC**: Mỗi 0.5 giây
- **Kết nối**: 5 giây

### Đa luồng
- **Tối đa**: 32 cổng GSM đồng thời
- **Nghỉ giữa cuộc gọi**: 2 giây
- **Reset module**: Sau mỗi 100 cuộc gọi

## 🧪 Test hệ thống

```bash
python test_system.py
```

Script test sẽ kiểm tra:
- Import các module
- Chức năng controller
- String detection
- Export Excel
- GSM Manager
- Tạo dữ liệu test

## 📁 Cấu trúc project

```
main_classification/
├── main_gui.py              # Giao diện chính
├── controller.py            # Controller điều phối hệ thống
├── gsm_manager.py          # Quản lý kết nối GSM
├── detect_gsm_port.py      # Phát hiện cổng GSM
├── call_and_record.py      # Gọi điện và ghi âm
├── string_detection.py     # Phân loại từ khóa
├── spk_to_text_wav2.py     # Speech-to-text
├── export_excel.py         # Xuất kết quả Excel
├── test_system.py          # Test hệ thống
├── requirements.txt        # Dependencies
└── README.md              # Hướng dẫn này
```

## ⚠️ Lưu ý quan trọng

1. **Thiết bị GSM**: Đảm bảo modem GSM tương thích với lệnh AT
2. **SIM Card**: Cần có SIM có tiền để thực hiện cuộc gọi
3. **Mạng**: Đảm bảo thiết bị có tín hiệu mạng tốt
4. **Driver**: Cài đặt driver cho modem GSM
5. **Quyền**: Một số hệ thống cần quyền admin để truy cập cổng COM

## 🐛 Troubleshooting

### Lỗi "Không tìm thấy cổng GSM"
- Kiểm tra kết nối USB
- Cài đặt lại driver
- Thử cổng COM khác

### Lỗi "Không thể gọi điện"
- Kiểm tra SIM có tiền
- Kiểm tra tín hiệu mạng
- Kiểm tra số điện thoại có đúng format

### Lỗi "Không thể ghi âm"
- Kiểm tra module hỗ trợ AT+QAUDRD
- Kiểm tra baudrate
- Thử reset module

### Lỗi Speech-to-text
- Cài đặt torch với CUDA support
- Kiểm tra file audio có tồn tại
- Kiểm tra định dạng AMR

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Chạy `test_system.py` để kiểm tra
2. Xem log trong giao diện
3. Kiểm tra file `note.txt` để biết thêm chi tiết kỹ thuật

---

**Phát triển bởi**: GSM Classification Team  
**Phiên bản**: 1.0.0  
**Ngày**: 2024
