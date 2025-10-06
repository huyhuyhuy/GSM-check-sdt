# 🚀 Quick Start Guide

## 📋 Yêu cầu hệ thống

- Python 3.8+
- Windows (đã test trên Windows)
- 32 cổng GSM modem (hoặc ít hơn)
- SIM cards có tiền

## 🛠️ Cài đặt

### 1. Clone repository
```bash
cd d:\DEV_TOOL\GSM_check_sdt\main_classification
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Cài đặt PyTorch với CUDA (nếu có GPU)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Hoặc CPU only:
```bash
pip install torch torchvision torchaudio
```

## 🎯 Sử dụng

### 1. Chuẩn bị file danh sách số điện thoại

Tạo file `list_sdt.txt` với mỗi số trên một dòng:

```
0987654321
0387654322
0587654323
0787654324
0987654325
```

**Lưu ý**: 
- Số phải bắt đầu bằng 0
- Độ dài 10-11 chữ số
- Chỉ chứa chữ số (không có ký tự đặc biệt)

### 2. Chạy chương trình

```bash
python main_gui.py
```

### 3. Quy trình sử dụng

1. **Khởi động**: Hệ thống tự động quét các cổng GSM
   - Hiển thị danh sách cổng GSM trong bảng
   - Mỗi cổng có: STT, Cổng, Tín hiệu, Nhà mạng, SĐT, Số dư

2. **Chọn file**: Click "Nhập File" → chọn file `list_sdt.txt`

3. **Bắt đầu**: Click "Bắt Đầu"
   - Hệ thống tự động chia số điện thoại cho các cổng GSM
   - Mỗi cổng xử lý độc lập trong thread riêng

4. **Theo dõi**: Xem log real-time trong cửa sổ log

5. **Dừng** (nếu cần): Click "Dừng"

6. **Xuất kết quả**: Click "Xuất Kết Quả" → chọn nơi lưu file Excel

## 📊 Kết quả

File Excel sẽ có:

### Sheet "Tổng Hợp"
- Thống kê tổng quan
- Số lượng từng loại
- Tỷ lệ phần trăm

### Sheet chi tiết cho từng loại
- Hoạt động
- Leave Message
- Be Blocked
- Can Not Connect
- Incorrect
- Ringback Tone
- Waiting Tone
- Mute
- Lỗi

## 🔍 Phân loại số điện thoại

1. **Hoạt động**: Người nghe đã nhấc máy (+COLP detected)
2. **Leave Message**: Hộp thư thoại
3. **Be Blocked**: Thuê bao tạm khóa
4. **Can Not Connect**: Không liên lạc được
5. **Incorrect**: Số không đúng
6. **Ringback Tone**: Tiếng tút chuông
7. **Waiting Tone**: Nhạc chờ
8. **Mute**: Im lặng
9. **Lỗi**: Các số bị lỗi trong quá trình xử lý

## 📝 Logs

Tất cả logs được lưu trong thư mục `logs/`:

```
logs/
├── gsm_controller_YYYYMMDD_HHMMSS.log    # Log chính
├── gsm_COM37_YYYYMMDD_HHMMSS.log         # Log từng cổng
├── gsm_COM38_YYYYMMDD_HHMMSS.log
├── detect_gsm_YYYYMMDD_HHMMSS.log        # Log quét cổng
└── export_excel_YYYYMMDD_HHMMSS.log      # Log xuất Excel
```

### Xem logs:
```bash
# Xem log controller
type logs\gsm_controller_*.log

# Xem log cổng cụ thể
type logs\gsm_COM37_*.log

# Xem log mới nhất
dir logs /od /b | findstr gsm_controller
```

## 🧪 Test hệ thống

### Test ModelManager:
```bash
python test_model_manager.py
```

Kết quả mong đợi:
```
=== Test 1: Singleton Pattern ===
✅ ModelManager là singleton

=== Test 2: Lazy Loading ===
✅ Model chưa được load (lazy loading)
📥 Đang load model lần đầu...
✅ Load model thành công trong X.XXs
✅ Model đã được load
📥 Đang load model lần 2 (cached)...
✅ Load model cached trong 0.0001s
✅ Processor và Model là cùng instance (cached)
⚡ Tốc độ tăng: XXXXx nhanh hơn

=== Test 3: Thread Safety ===
🚀 Tạo 10 threads đồng thời...
✅ Tất cả 10 threads đều nhận cùng 1 model instance
✅ Thread-safe hoạt động đúng

=== Test 4: Memory Usage ===
📊 Memory trước khi load: XX.XX MB
📊 Memory sau khi load: XX.XX MB
📊 Memory sử dụng cho model: XX.XX MB
💰 Tiết kiệm với 32 instances: XXXX.XX MB (~X.XX GB)

🎉 TẤT CẢ TESTS ĐỀU PASS!
```

## ⚙️ Cấu hình

### Baudrate
- **Khởi tạo**: 115200 (quét cổng, lấy thông tin)
- **Xử lý**: 921600 (gọi điện, ghi âm, tải file)

### Timeout
- **Gọi điện**: 1.5 giây
- **Ghi âm**: 15 giây
- **Check CLCC**: 0.5 giây/lần (0.3s timeout)

### Reset
- **Sau mỗi 100 cuộc gọi**: Reset module, load lại số dư
- **Nghỉ ngơi**: 30 giây sau reset
- **Reset cuối**: AT+CFUN=1,1 khi thoát chương trình

## 🐛 Troubleshooting

### Lỗi "Không tìm thấy cổng GSM"
```
❌ Không tìm thấy cổng COM nào
```

**Giải pháp**:
1. Kiểm tra kết nối USB
2. Cài đặt driver cho modem GSM
3. Kiểm tra Device Manager → Ports (COM & LPT)

### Lỗi "Không thể gọi điện"
```
❌ Không thể gọi 0987654321
```

**Giải pháp**:
1. Kiểm tra SIM có tiền
2. Kiểm tra tín hiệu mạng (AT+CSQ)
3. Kiểm tra số điện thoại đúng format

### Lỗi "File ghi âm rỗng"
```
❌ File ghi âm rỗng (0 bytes)
```

**Giải pháp**:
1. Kiểm tra module hỗ trợ AT+QAUDRD
2. Kiểm tra baudrate = 921600
3. Thử reset module

### Lỗi "Không thể load model"
```
❌ Failed to load model
```

**Giải pháp**:
1. Kiểm tra kết nối internet (lần đầu cần download model)
2. Cài đặt lại transformers: `pip install --upgrade transformers`
3. Kiểm tra PyTorch: `python -c "import torch; print(torch.__version__)"`

## 💡 Tips

### 1. Tăng tốc độ xử lý
- Sử dụng GPU nếu có (CUDA)
- Tăng số lượng cổng GSM
- Giảm thời gian ghi âm (nếu không cần STT chi tiết)

### 2. Tiết kiệm RAM
- ModelManager đã tự động tiết kiệm RAM
- Đóng các ứng dụng không cần thiết
- Sử dụng CPU nếu GPU không đủ VRAM

### 3. Debug
- Xem logs trong thư mục `logs/`
- Sử dụng `test_model_manager.py` để test
- Kiểm tra từng cổng GSM riêng lẻ

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Xem file `FIXES_SUMMARY.md` để biết các fix đã thực hiện
2. Xem file `CHANGELOG.md` để biết lịch sử thay đổi
3. Kiểm tra logs trong thư mục `logs/`
4. Chạy `test_model_manager.py` để test hệ thống

---

**Chúc bạn sử dụng thành công!** 🎉

