@echo off
echo ========================================
echo   GSM CHECKER - PACK FOR TRANSFER
echo   Professional MFCC + DTW Version
echo ========================================
echo.

REM Tạo thư mục đích
set PACK_DIR=GSM_Checker_Portable
if exist "%PACK_DIR%" (
    echo Xóa thư mục cũ...
    rmdir /s /q "%PACK_DIR%"
)
mkdir "%PACK_DIR%"

echo 📦 Đang copy files cần thiết...

REM Copy files chính (bắt buộc)
echo   - Files chương trình chính...
copy "install_run.bat" "%PACK_DIR%\" >nul
copy "main_enhanced.py" "%PACK_DIR%\" >nul  
copy "gsm_manager_enhanced.py" "%PACK_DIR%\" >nul
copy "check_viettel.py" "%PACK_DIR%\" >nul
copy "check_vina_mobi_vietnam.py" "%PACK_DIR%\" >nul
copy "file_manager.py" "%PACK_DIR%\" >nul
copy "requirements.txt" "%PACK_DIR%\" >nul
copy "config.json" "%PACK_DIR%\" >nul

REM Copy files tùy chọn (chỉ nếu có)
echo   - Files tùy chọn...
if exist "esp32_audio_analyzer.py" (
    copy "esp32_audio_analyzer.py" "%PACK_DIR%\" >nul
    echo     ✅ esp32_audio_analyzer.py (ESP32 support)
)

REM Copy audio templates (Professional MFCC chỉ cần 2 files chính)
echo   - Audio template files...
if exist "template_de_lai_loi_nhan_ok.wav" (
    copy "template_de_lai_loi_nhan_ok.wav" "%PACK_DIR%\" >nul
    echo     ✅ template_de_lai_loi_nhan_ok.wav (OPTIONAL - không dùng trong Professional MFCC)
) else (
    echo     ⚠️ template_de_lai_loi_nhan_ok.wav (OPTIONAL - không ảnh hưởng Professional MFCC)
)

if exist "template_so_khong_dung_ok.wav" (
    copy "template_so_khong_dung_ok.wav" "%PACK_DIR%\" >nul  
    echo     ✅ template_so_khong_dung_ok.wav (PRIMARY - bắt buộc cho Professional MFCC)
) else (
    echo     ❌ THIẾU: template_so_khong_dung_ok.wav (PRIMARY - BẮT BUỘC!)
)

if exist "template_thue_bao_ok.wav" (
    copy "template_thue_bao_ok.wav" "%PACK_DIR%\" >nul
    echo     ✅ template_thue_bao_ok.wav (PRIMARY - bắt buộc cho Professional MFCC)
) else (
    echo     ❌ THIẾU: template_thue_bao_ok.wav (PRIMARY - BẮT BUỘC!)
)

REM Copy files tùy chọn
echo   - Files tùy chọn...
if exist "build.py" copy "build.py" "%PACK_DIR%\" >nul
if exist "check_dependencies.py" copy "check_dependencies.py" "%PACK_DIR%\" >nul
if exist "README.md" copy "README.md" "%PACK_DIR%\" >nul
if exist "README_PROFESSIONAL_MFCC.md" copy "README_PROFESSIONAL_MFCC.md" "%PACK_DIR%\" >nul
if exist "icon.ico" copy "icon.ico" "%PACK_DIR%\" >nul
if exist "COPY_FILES_LIST.txt" copy "COPY_FILES_LIST.txt" "%PACK_DIR%\" >nul

REM Copy sample data files
echo   - Sample files...
if exist "listsdt.txt" copy "listsdt.txt" "%PACK_DIR%\" >nul
if exist "test_sdt.txt" copy "test_sdt.txt" "%PACK_DIR%\" >nul

REM Tạo README cho portable
echo   - Tạo hướng dẫn...
echo GSM Phone Checker - Professional MFCC + DTW Version > "%PACK_DIR%\README_PORTABLE.txt"
echo. >> "%PACK_DIR%\README_PORTABLE.txt"
echo 🎯 TÍNH NĂNG MỚI: >> "%PACK_DIR%\README_PORTABLE.txt"
echo - Professional MFCC + DTW Analysis >> "%PACK_DIR%\README_PORTABLE.txt"
echo - Advanced Signal Processing >> "%PACK_DIR%\README_PORTABLE.txt"
echo - 20 MFCC Coefficients + Delta features >> "%PACK_DIR%\README_PORTABLE.txt"
echo - CMVN Normalization (chống nhiễu) >> "%PACK_DIR%\README_PORTABLE.txt"
echo - DTW Distance với threshold 9.3 >> "%PACK_DIR%\README_PORTABLE.txt"
echo. >> "%PACK_DIR%\README_PORTABLE.txt"
echo HƯỚNG DẪN SỬ DỤNG: >> "%PACK_DIR%\README_PORTABLE.txt"
echo 1. Copy toàn bộ thư mục này sang máy đích >> "%PACK_DIR%\README_PORTABLE.txt"
echo 2. Double-click vào install_run.bat >> "%PACK_DIR%\README_PORTABLE.txt"
echo 3. Chọn [1] để chạy chương trình >> "%PACK_DIR%\README_PORTABLE.txt"
echo 4. Hoặc chọn [2] để build file EXE >> "%PACK_DIR%\README_PORTABLE.txt"
echo. >> "%PACK_DIR%\README_PORTABLE.txt"
echo YÊU CẦU: >> "%PACK_DIR%\README_PORTABLE.txt"
echo - Windows 10/11 >> "%PACK_DIR%\README_PORTABLE.txt"
echo - Python 3.8+ (script sẽ hướng dẫn cài) >> "%PACK_DIR%\README_PORTABLE.txt"
echo - Internet để tải thư viện (bao gồm librosa + fastdtw) >> "%PACK_DIR%\README_PORTABLE.txt"
echo - Thiết bị GSM 32 cổng >> "%PACK_DIR%\README_PORTABLE.txt"
echo. >> "%PACK_DIR%\README_PORTABLE.txt"
echo 🎵 AUDIO TEMPLATES CẦN THIẾT: >> "%PACK_DIR%\README_PORTABLE.txt"
echo - template_thue_bao_ok.wav (PRIMARY) >> "%PACK_DIR%\README_PORTABLE.txt"
echo - template_so_khong_dung_ok.wav (PRIMARY) >> "%PACK_DIR%\README_PORTABLE.txt"
echo. >> "%PACK_DIR%\README_PORTABLE.txt"
echo 📖 Chi tiết: Xem README_PROFESSIONAL_MFCC.md >> "%PACK_DIR%\README_PORTABLE.txt"

REM Kiểm tra validation template files
echo   - Kiểm tra template validation...
set PRIMARY_TEMPLATES_OK=1
if not exist "%PACK_DIR%\template_thue_bao_ok.wav" set PRIMARY_TEMPLATES_OK=0
if not exist "%PACK_DIR%\template_so_khong_dung_ok.wav" set PRIMARY_TEMPLATES_OK=0

echo.
if !PRIMARY_TEMPLATES_OK! equ 1 (
    echo ✅ VALIDATION: Primary templates OK - Professional MFCC sẵn sàng!
) else (
    echo ❌ VALIDATION: Thiếu primary templates - Professional MFCC sẽ không hoạt động!
    echo    Cần copy: template_thue_bao_ok.wav và template_so_khong_dung_ok.wav
)

echo.
echo ========================================
echo     PACK HOÀN THÀNH! 📦
echo   Professional MFCC + DTW Version
echo ========================================
echo.
echo 📁 Thư mục: %PACK_DIR%\
echo 📋 Chứa tất cả files cần thiết (với librosa + fastdtw)
echo 🎵 Professional MFCC pipeline integrated
echo.
echo 🚀 CÁCH CHUYỂN SANG MÁY KHÁC:
echo   1. Copy toàn bộ thư mục "%PACK_DIR%"
echo   2. Trên máy đích: Double-click install_run.bat
echo   3. Script sẽ tự cài librosa + fastdtw
echo   4. Chọn [1] để chạy hoặc [2] để build EXE
echo.

REM Hỏi có muốn nén không
set /p compress="Có muốn nén thành file ZIP? (y/n): "
if /i "%compress%"=="y" (
    if exist "%PACK_DIR%.zip" del "%PACK_DIR%.zip"
    echo 📦 Đang nén...
    powershell -command "Compress-Archive -Path '%PACK_DIR%' -DestinationPath '%PACK_DIR%.zip'" >nul 2>&1
    if exist "%PACK_DIR%.zip" (
        echo ✅ Đã tạo file: %PACK_DIR%.zip
        echo 📤 Có thể gửi file ZIP này sang máy khác
    ) else (
        echo ❌ Lỗi tạo file ZIP
    )
)

echo.
pause
