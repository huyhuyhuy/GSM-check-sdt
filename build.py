#!/usr/bin/env python3
"""
Build script để tạo file exe độc lập cho GSM Phone Number Checker
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def ensure_pyinstaller() -> bool:
    """Đảm bảo PyInstaller đã có; nếu chưa thì tự cài đặt với version phù hợp."""
    try:
        import PyInstaller  # type: ignore
        print(f"✓ PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        # Detect Python version và chọn PyInstaller version phù hợp
        python_version = sys.version_info
        print(f"🐍 Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version >= (3, 13):
            # Python 3.13+ cần PyInstaller 6.10.0+
            pyinstaller_version = "6.15.0"
            print(f"✗ PyInstaller chưa có. Đang cài đặt pyinstaller=={pyinstaller_version} (cho Python 3.13+)...")
        elif python_version >= (3, 12):
            # Python 3.12 dùng 6.3.0+
            pyinstaller_version = "6.8.0"
            print(f"✗ PyInstaller chưa có. Đang cài đặt pyinstaller=={pyinstaller_version} (cho Python 3.12)...")
        else:
            # Python < 3.12 dùng 6.3.0
            pyinstaller_version = "6.3.0"
            print(f"✗ PyInstaller chưa có. Đang cài đặt pyinstaller=={pyinstaller_version}...")
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", f"pyinstaller=={pyinstaller_version}"], check=True)
            import PyInstaller  # type: ignore
            print(f"✓ Đã cài PyInstaller version: {PyInstaller.__version__}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Lỗi cài PyInstaller {pyinstaller_version}: {e}")
            # Fallback: thử latest version
            print("🔄 Thử cài latest version...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
                import PyInstaller  # type: ignore
                print(f"✓ Đã cài PyInstaller latest version: {PyInstaller.__version__}")
                return True
            except subprocess.CalledProcessError as e2:
                print(f"✗ Lỗi cài PyInstaller latest: {e2}")
                return False


def install_pyaudio() -> bool:
    """Cài đặt PyAudio với xử lý đặc biệt cho Windows"""
    try:
        import pyaudio
        print("✓ PyAudio đã có sẵn")
        return True
    except ImportError:
        print("📦 Đang cài đặt PyAudio...")
        try:
            # Thử cài PyAudio bằng pip (thường work trên Windows với wheel)
            subprocess.run([sys.executable, "-m", "pip", "install", "pyaudio"], check=True)
            print("✓ Cài đặt PyAudio thành công")
            return True
        except subprocess.CalledProcessError:
            print("⚠️ Lỗi cài PyAudio bằng pip. Thử pipwin...")
            try:
                # Fallback: Sử dụng pipwin cho Windows
                subprocess.run([sys.executable, "-m", "pip", "install", "pipwin"], check=True)
                subprocess.run([sys.executable, "-m", "pipwin", "install", "pyaudio"], check=True)
                print("✓ Cài đặt PyAudio thành công qua pipwin")
                return True
            except subprocess.CalledProcessError as e:
                print(f"✗ Lỗi cài PyAudio: {e}")
                print("💡 Thủ công: Tải wheel từ https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio")
                return False


def install_requirements() -> bool:
    """Cài đặt requirements nếu có file requirements.txt (tùy chọn)."""
    req_path = "requirements.txt"
    if not os.path.exists(req_path):
        print("(Bỏ qua) Không có requirements.txt")
        return True
    
    # Cài PyAudio riêng trước
    if not install_pyaudio():
        return False
    
    print("📦 Đang cài đặt thư viện từ requirements.txt...")
    try:
        # Cài các packages khác (trừ PyAudio vì đã cài riêng)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path, "--ignore-installed", "pyaudio"], check=True)
        print("✓ Cài đặt requirements hoàn tất")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Lỗi cài requirements: {e}")
        return False

def clean_build_dirs():
    """Dọn dẹp thư mục build cũ"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Đang xóa thư mục {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Xóa file .spec cũ
    spec_file = "gsm_checker.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Đã xóa file {spec_file}")

def build_exe():
    """Build file exe"""
    print("🚀 Bắt đầu build file exe...")
    
    # Lệnh PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # Tạo 1 file exe duy nhất
        "--windowed",                   # Không hiển thị console window
        "--name=GSM_Phone_Checker",     # Tên file exe
        "--icon=icon.ico",              # Icon (nếu có)
        "--add-data=README.md;.",       # Thêm file README
        "--add-data=template_de_lai_loi_nhan_ok.wav;.", # Template audio files
        "--add-data=template_so_khong_dung_ok.wav;.",
        "--add-data=template_thue_bao_ok.wav;.",
        "--hidden-import=serial",       # Import thư viện serial
        "--hidden-import=serial.tools", # Import tools của serial
        "--hidden-import=tkinter",      # Import tkinter
        "--hidden-import=tkinter.ttk",  # Import ttk
        "--hidden-import=tkinter.filedialog", # Import filedialog
        "--hidden-import=tkinter.messagebox", # Import messagebox
        "--hidden-import=tkinter.scrolledtext", # Import scrolledtext
        "--hidden-import=threading",    # Import threading
        "--hidden-import=queue",        # Import queue
        "--hidden-import=logging",      # Import logging
        "--hidden-import=datetime",     # Import datetime
        "--hidden-import=time",         # Import time
        "--hidden-import=os",           # Import os
        "--hidden-import=typing",       # Import typing
        "--hidden-import=matplotlib",   # Import matplotlib cho plotting
        "--hidden-import=matplotlib.pyplot", # Import pyplot
        "--hidden-import=numpy",        # Import numpy
        "--hidden-import=scipy",        # Import scipy
        "--hidden-import=scipy.signal", # Import scipy.signal cho correlation
        "--hidden-import=pyaudio",      # Import pyaudio cho audio recording
        "--clean",                      # Dọn dẹp cache
        "--noconfirm",                  # Không hỏi xác nhận
        "main_enhanced.py"              # File chính (đã thay đổi)
    ]
    
    # Xóa icon nếu không có file icon
    if not os.path.exists("icon.ico"):
        cmd.remove("--icon=icon.ico")
        print("⚠️  Không tìm thấy file icon.ico, sẽ sử dụng icon mặc định")
    
    # Xóa README nếu không có
    if not os.path.exists("README.md"):
        cmd.remove("--add-data=README.md;.")
        print("⚠️  Không tìm thấy file README.md")
    
    # Kiểm tra template files
    template_files = [
        "template_de_lai_loi_nhan_ok.wav",
        "template_so_khong_dung_ok.wav", 
        "template_thue_bao_ok.wav"
    ]
    
    for template_file in template_files:
        if not os.path.exists(template_file):
            data_arg = f"--add-data={template_file};."
            if data_arg in cmd:
                cmd.remove(data_arg)
            print(f"⚠️  Không tìm thấy {template_file} - Viettel audio analysis sẽ không hoạt động")
        else:
            print(f"✓ Tìm thấy template: {template_file}")
    
    try:
        # Chạy lệnh build
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Build thành công!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Lỗi build: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def create_installer_script():
    """Tạo script cài đặt đơn giản"""
    installer_content = """@echo off
echo ========================================
echo    GSM Phone Number Checker Installer
echo ========================================
echo.
echo Dang cai dat ung dung...

REM Tao thu muc cai dat
if not exist "C:\\GSM_Checker" mkdir "C:\\GSM_Checker"

REM Copy file exe
copy "dist\\GSM_Phone_Checker.exe" "C:\\GSM_Checker\\"

REM Tao shortcut tren Desktop
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%USERPROFILE%\\Desktop\\GSM Phone Checker.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "C:\\GSM_Checker\\GSM_Phone_Checker.exe" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "C:\\GSM_Checker" >> CreateShortcut.vbs
echo oLink.Description = "GSM Phone Number Checker" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo.
echo ========================================
echo    Cai dat hoan thanh!
echo ========================================
echo.
echo Ung dung da duoc cai dat tai: C:\\GSM_Checker\\
echo Shortcut da duoc tao tren Desktop
echo.
pause
"""
    
    with open("install.bat", "w", encoding="utf-8") as f:
        f.write(installer_content)
    print("✓ Đã tạo file install.bat")

def create_readme_exe():
    """Tạo file README cho người dùng exe"""
    readme_content = """# GSM Phone Number Checker - Phiên bản EXE

## Cách sử dụng:

### 1. Chạy ứng dụng:
- Double-click vào file `GSM_Phone_Checker.exe`
- Hoặc chạy từ Command Prompt: `GSM_Phone_Checker.exe`

### 2. Chuẩn bị:
- Kết nối thiết bị GSM 32 cổng vào máy tính
- Chuẩn bị file txt chứa danh sách số điện thoại (mỗi số một dòng)

### 3. Sử dụng:
1. Nhấn "Nhập File" để chọn file danh sách số điện thoại
2. Nhấn "Bắt Đầu" để bắt đầu kiểm tra
3. Theo dõi tiến độ trong khung log
4. Nhấn "Xuất Kết Quả" để lưu kết quả

### 4. Kết quả:
- File kết quả sẽ được lưu trong thư mục `results/`
- `active_numbers_YYYYMMDD_HHMMSS.txt`: Các số còn hoạt động
- `inactive_numbers_YYYYMMDD_HHMMSS.txt`: Các số không hoạt động

## Lưu ý:
- Đảm bảo thiết bị GSM đã được cài đặt driver
- Có thể mất phí cuộc gọi khi kiểm tra số điện thoại
- Tool sẽ tự động hủy cuộc gọi sau khi kiểm tra

## Hỗ trợ:
Nếu gặp lỗi, vui lòng kiểm tra:
1. Thiết bị GSM đã được kết nối đúng cách
2. Driver đã được cài đặt
3. File danh sách số điện thoại đúng định dạng

---
Phiên bản: 1.0
Ngày phát hành: 2024
"""
    
    with open("README_EXE.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("✓ Đã tạo file README_EXE.txt")

def main():
    """Hàm chính"""
    print("=" * 50)
    print("    GSM Phone Number Checker - Build Tool")
    print("=" * 50)
    print()
    
    # Kiểm tra PyInstaller
    if not ensure_pyinstaller():
        return False
    
    # Skip install requirements nếu PyAudio đã có
    try:
        import pyaudio
        print("✓ PyAudio đã có - Skip install requirements")
    except ImportError:
        # Cài requirements nếu PyAudio chưa có
        if not install_requirements():
            return False

    # Dọn dẹp thư mục build cũ
    clean_build_dirs()
    
    # Build exe
    if not build_exe():
        return False
    
    # Tạo file hỗ trợ
    create_installer_script()
    create_readme_exe()
    
    print()
    print("=" * 50)
    print("    BUILD HOÀN THÀNH!")
    print("=" * 50)
    print()
    print("📁 File exe: dist/GSM_Phone_Checker.exe")
    print("📁 Script cài đặt: install.bat")
    print("📁 Hướng dẫn: README_EXE.txt")
    print()
    print("🎯 Để phân phối:")
    print("1. Copy file dist/GSM_Phone_Checker.exe")
    print("2. Copy file README_EXE.txt")
    print("3. Copy file install.bat (tùy chọn)")
    print()
    print("✅ Người dùng chỉ cần chạy file exe, không cần cài thêm gì!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 