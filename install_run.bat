@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ========================================
echo    GSM Phone Checker - Auto Setup
echo ========================================
echo.

REM Kiểm tra Python
echo 🔍 Kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python không được tìm thấy!
    echo.
    echo 💡 Vui lòng cài đặt Python 3.8+ từ python.org trước
    echo    - Tải về: https://www.python.org/downloads/
    echo    - Chọn "Add Python to PATH" khi cài đặt
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% OK
echo.

REM Tạo virtual environment
echo 📦 Tạo môi trường ảo Python...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Lỗi tạo virtual environment!
        pause
        exit /b 1
    )
    echo ✅ Tạo venv thành công
) else (
    echo ✅ Virtual environment đã có sẵn
)

REM Activate virtual environment
echo 🔄 Kích hoạt môi trường ảo...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Lỗi kích hoạt virtual environment!
    pause
    exit /b 1
)
echo ✅ Đã kích hoạt venv

REM Upgrade pip
echo 📈 Nâng cấp pip...
python -m pip install --upgrade pip >nul 2>&1

REM Cài đặt PyAudio trước (Windows fix)
echo 🔊 Cài đặt PyAudio...
python -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    echo   - Thử cài từ wheel...
    python -m pip install pyaudio --only-binary=all >nul 2>&1
    if errorlevel 1 (
        echo   - Thử pipwin...
        python -m pip install pipwin >nul 2>&1
        python -m pipwin install pyaudio >nul 2>&1
        if errorlevel 1 (
            echo ❌ Không thể cài PyAudio!
            echo 💡 Thử tải wheel từ: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
            pause
            exit /b 1
        )
    )
    echo ✅ PyAudio cài thành công
) else (
    echo ✅ PyAudio đã có sẵn
)

REM Cài đặt requirements
echo 📦 Cài đặt thư viện cần thiết...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt --upgrade >nul 2>&1
    if errorlevel 1 (
        echo ❌ Lỗi cài requirements!
        echo 🔧 Thử cài từng package...
        
        REM Cài từng package quan trọng
        python -m pip install pyserial numpy openpyxl scipy matplotlib pyaudio >nul 2>&1
        echo 🎵 Cài librosa và fastdtw cho Professional MFCC...
        python -m pip install librosa fastdtw >nul 2>&1
        if errorlevel 1 (
            echo ❌ Lỗi cài packages cơ bản!
            pause
            exit /b 1
        )
    )
    echo ✅ Thư viện đã cài xong
) else (
    echo ⚠️ Không có requirements.txt, cài basic packages...
    python -m pip install pyserial numpy openpyxl scipy matplotlib pyaudio librosa fastdtw >nul 2>&1
)

REM Kiểm tra template files
echo 📋 Kiểm tra template files...
set MISSING_TEMPLATES=0
if not exist "template_de_lai_loi_nhan_ok.wav" (
    echo ⚠️ Thiếu: template_de_lai_loi_nhan_ok.wav
    set MISSING_TEMPLATES=1
)
if not exist "template_so_khong_dung_ok.wav" (
    echo ⚠️ Thiếu: template_so_khong_dung_ok.wav
    set MISSING_TEMPLATES=1
)
if not exist "template_thue_bao_ok.wav" (
    echo ⚠️ Thiếu: template_thue_bao_ok.wav
    set MISSING_TEMPLATES=1
)

if !MISSING_TEMPLATES! equ 1 (
    echo.
    echo ⚠️ CẢNH BÁO: Thiếu template files!
    echo    Professional MFCC chỉ cần: template_thue_bao_ok.wav và template_so_khong_dung_ok.wav
    echo    Vui lòng copy đầy đủ các file .wav
    echo.
) else (
    echo ✅ Template files OK - Professional MFCC ready
)

REM Kiểm tra file chính
echo 📋 Kiểm tra file chương trình...
if not exist "main_enhanced.py" (
    echo ❌ Thiếu file main_enhanced.py!
    echo 💡 Vui lòng copy đầy đủ source code
    pause
    exit /b 1
)
echo ✅ File chương trình OK

echo.
echo ========================================
echo         THIẾT LẬP HOÀN TẤT! 🎉
echo ========================================
echo.

REM Hỏi người dùng muốn làm gì
echo Bạn muốn:
echo [1] Chạy chương trình ngay
echo [2] Build file EXE
echo [3] Thoát
echo.
set /p choice="Chọn (1/2/3): "

if "!choice!"=="1" (
    echo.
    echo 🚀 Đang khởi động chương trình...
    echo ⚠️ Đảm bảo thiết bị GSM đã kết nối!
    echo.
    python main_enhanced.py
    if errorlevel 1 (
        echo.
        echo ❌ Chương trình gặp lỗi!
        pause
    )
) else if "!choice!"=="2" (
    if exist "build.py" (
        echo.
        echo 🏗️ Đang build file EXE...
        python build.py
        if errorlevel 1 (
            echo ❌ Build thất bại!
        ) else (
            echo.
            echo ✅ Build thành công!
            echo 📁 File EXE: dist\GSM_Phone_Checker.exe
        )
        pause
    ) else (
        echo ❌ Không tìm thấy build.py!
        pause
    )
) else (
    echo.
    echo 📝 Để chạy lại sau:
    echo    1. Mở Command Prompt
    echo    2. Đi tới thư mục này
    echo    3. Chạy: venv\Scripts\activate.bat
    echo    4. Chạy: python main_enhanced.py
    echo.
)

echo.
echo ========================================
echo           HOÀN THÀNH!
echo ========================================
pause
