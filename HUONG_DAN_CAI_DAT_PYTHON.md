# 🐍 HƯỚNG DẪN CÀI ĐẶT PYTHON TRÊN WINDOWS 11

## 🚀 **Bước 1: Tải Python**

### **Cách 1: Từ trang chủ Python (Khuyến nghị)**
1. **Truy cập**: https://www.python.org/downloads/
2. **Tải phiên bản**: Python 3.11 hoặc Python 3.12 (phiên bản mới nhất)
3. **File tải**: `python-3.11.x-amd64.exe` hoặc `python-3.12.x-amd64.exe`

### **Cách 2: Từ Microsoft Store**
1. Mở **Microsoft Store**
2. Tìm kiếm: `Python 3.11` hoặc `Python 3.12`
3. Chọn **Install** hoặc **Get**

## 🔧 **Bước 2: Cài đặt Python**

### **QUAN TRỌNG: Tick vào "Add Python to PATH"**

![Python Install](https://docs.python.org/3/_images/win_installer.png)

1. **Chạy file installer** đã tải về
2. **Tick vào ô "Add Python.exe to PATH"** ⭐
3. Chọn **"Install Now"**
4. Đợi cài đặt hoàn tất
5. Chọn **"Close"**

## ✅ **Bước 3: Kiểm tra cài đặt**

### **Mở PowerShell hoặc Command Prompt mới**

```bash
# Kiểm tra Python
python --version
# Kết quả mong đợi: Python 3.11.x hoặc Python 3.12.x

# Kiểm tra pip
python -m pip --version
# Kết quả mong đợi: pip x.x.x from ... (python 3.x)
```

## 🎯 **Bước 4: Chạy script cài đặt Wav2Vec2**

Sau khi Python đã cài đặt thành công:

```powershell
# Mở PowerShell với quyền Administrator
# Chạy script setup:
.\setup_python_and_wav2vec2.ps1
```

## 🐛 **Xử lý lỗi thường gặp**

### **Lỗi 1: "Python was not found"**
```bash
# Nguyên nhân: Python không có trong PATH
# Giải pháp: Cài đặt lại Python và TICK "Add Python to PATH"
```

### **Lỗi 2: "pip is not recognized"**
```bash
# Giải pháp: Sử dụng python -m pip
python -m pip install package_name
```

### **Lỗi 3: "Permission denied"**
```bash
# Giải pháp: Chạy PowerShell với quyền Administrator
# Hoặc sử dụng:
python -m pip install --user package_name
```

## 📋 **Kiểm tra hệ thống**

### **Yêu cầu tối thiểu:**
- **Windows**: Windows 10/11 (64-bit)
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB+)
- **Dung lượng ổ cứng**: 2GB trống
- **Python**: 3.8+ (khuyến nghị 3.11+)

### **Kiểm tra Windows:**
```bash
# Kiểm tra phiên bản Windows
winver

# Kiểm tra kiến trúc (64-bit)
systeminfo | findstr "System Type"
```

## 🔍 **Kiểm tra Python đã cài đặt**

### **Cách 1: Command Line**
```bash
python --version
python -c "import sys; print(sys.executable)"
```

### **Cách 2: Windows Settings**
1. Mở **Settings** → **Apps** → **Apps & features**
2. Tìm kiếm: `Python`
3. Kiểm tra phiên bản đã cài đặt

### **Cách 3: File Explorer**
```bash
# Kiểm tra thư mục cài đặt
C:\Users\[Username]\AppData\Local\Programs\Python\
C:\Program Files\Python3x\
C:\Python3x\
```

## 📚 **Tài liệu tham khảo**

- **Python Official**: https://www.python.org/
- **Python Downloads**: https://www.python.org/downloads/
- **Python Documentation**: https://docs.python.org/
- **pip Documentation**: https://pip.pypa.io/

## 🆘 **Hỗ trợ**

Nếu gặp vấn đề:

1. **Kiểm tra lỗi**: Copy toàn bộ thông báo lỗi
2. **Kiểm tra Python**: `python --version`
3. **Kiểm tra PATH**: `echo $env:PATH` (PowerShell)
4. **Restart**: Khởi động lại máy tính sau khi cài Python

## 🎉 **Sau khi cài đặt thành công**

Python sẽ có thể chạy từ bất kỳ thư mục nào:
```bash
# Test Python
python -c "print('Hello, Python!')"

# Test pip
python -m pip list

# Cài đặt package
python -m pip install requests
```

---

**Lưu ý**: Luôn tick vào "Add Python to PATH" khi cài đặt để tránh lỗi "Python was not found"!
