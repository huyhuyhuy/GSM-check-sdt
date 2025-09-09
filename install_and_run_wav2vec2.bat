@echo off
chcp 65001 >nul
echo ========================================
echo    WAV2VEC2 VIETNAMESE STT INSTALLER
echo ========================================
echo.

echo 🚀 Đang cài đặt dependencies...
echo.

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python chưa được cài đặt hoặc không có trong PATH
    echo Vui lòng cài đặt Python 3.8+ trước
    pause
    exit /b 1
)

echo ✅ Python đã được cài đặt
python --version

REM Kiểm tra pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip chưa được cài đặt
    echo Đang cài đặt pip...
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
    del get-pip.py
)

echo ✅ pip đã sẵn sàng
python -m pip --version

echo.
echo 📦 Đang cài đặt các package cần thiết...
echo.

REM Cài đặt dependencies sử dụng python -m pip
echo 🔧 Cài đặt PyTorch...
python -m pip install torch torchaudio transformers
if errorlevel 1 (
    echo ❌ Lỗi khi cài đặt PyTorch
    pause
    exit /b 1
)

echo 🔧 Cài đặt audio processing libraries...
python -m pip install librosa soundfile numpy scipy
if errorlevel 1 (
    echo ❌ Lỗi khi cài đặt audio processing libraries
    pause
    exit /b 1
)

echo 🔧 Cài đặt accelerate...
python -m pip install accelerate
if errorlevel 1 (
    echo ❌ Lỗi khi cài đặt accelerate
    pause
    exit /b 1
)

echo.
echo ✅ Tất cả dependencies đã được cài đặt!
echo.

echo 🎬 Bắt đầu demo Wav2Vec2 Vietnamese STT...
echo.

REM Chạy demo
python test_wav2vec2_vietnamese.py

echo.
echo 🎉 Demo hoàn thành!
echo.
echo 💡 Để sử dụng với file WAV cụ thể:
echo    python test_wav2vec2_vietnamese.py your_audio.wav
echo.
echo 💡 Để lưu kết quả:
echo    python test_wav2vec2_vietnamese.py your_audio.wav --output result.json
echo.

pause
