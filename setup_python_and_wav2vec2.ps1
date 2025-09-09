# Setup Python và Wav2Vec2 Vietnamese STT từ đầu
# Chạy với PowerShell: .\setup_python_and_wav2vec2.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   SETUP PYTHON + WAV2VEC2 VIETNAMESE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🚀 Bắt đầu cài đặt Python và Wav2Vec2 Vietnamese STT..." -ForegroundColor Green
Write-Host ""

# Kiểm tra Python
Write-Host "🔍 Kiểm tra Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python đã được cài đặt: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python chưa được cài đặt" -ForegroundColor Red
    Write-Host ""
    Write-Host "📥 Hướng dẫn cài đặt Python:" -ForegroundColor Cyan
    Write-Host "1. Truy cập: https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "2. Tải Python 3.11 hoặc 3.12" -ForegroundColor White
    Write-Host "3. Khi cài đặt, NHỚ TICK 'Add Python to PATH'" -ForegroundColor Yellow
    Write-Host "4. Chọn 'Install Now'" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Hoặc cài từ Microsoft Store: tìm 'Python 3.11'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "⏳ Sau khi cài đặt Python xong, hãy chạy lại script này" -ForegroundColor Yellow
    Read-Host "Nhấn Enter để thoát"
    exit 1
}

# Kiểm tra phiên bản Python
$pythonVersionText = python --version 2>&1
if ($pythonVersionText -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
        Write-Host "❌ Python phiên bản quá cũ: $pythonVersionText" -ForegroundColor Red
        Write-Host "Cần Python 3.8+ để chạy Wav2Vec2" -ForegroundColor Yellow
        Read-Host "Nhấn Enter để thoát"
        exit 1
    }
    
    Write-Host "✅ Python phiên bản phù hợp: $pythonVersionText" -ForegroundColor Green
} else {
    Write-Host "⚠️ Không thể xác định phiên bản Python" -ForegroundColor Yellow
}

# Kiểm tra pip
Write-Host ""
Write-Host "🔍 Kiểm tra pip..." -ForegroundColor Yellow
try {
    $pipVersion = python -m pip --version 2>&1
    Write-Host "✅ pip đã sẵn sàng: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ pip chưa được cài đặt" -ForegroundColor Red
    Write-Host "Đang cài đặt pip..." -ForegroundColor Yellow
    
    try {
        Write-Host "📥 Tải get-pip.py..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
        
        Write-Host "🔧 Cài đặt pip..." -ForegroundColor Cyan
        python get-pip.py
        
        Write-Host "🧹 Dọn dẹp..." -ForegroundColor Cyan
        Remove-Item "get-pip.py"
        
        Write-Host "✅ pip đã được cài đặt" -ForegroundColor Green
    } catch {
        Write-Host "❌ Không thể cài đặt pip" -ForegroundColor Red
        Write-Host "Lỗi: $($_.Exception.Message)" -ForegroundColor Red
        Read-Host "Nhấn Enter để thoát"
        exit 1
    }
}

Write-Host ""
Write-Host "📦 Bắt đầu cài đặt các package cần thiết..." -ForegroundColor Green
Write-Host ""

# Cài đặt dependencies theo thứ tự
$packages = @(
    @{name="NumPy (cơ bản)"; cmd="numpy"},
    @{name="PyTorch (ML framework)"; cmd="torch torchaudio --index-url https://download.pytorch.org/whl/cpu"},
    @{name="Transformers (Hugging Face)"; cmd="transformers"},
    @{name="Audio Processing"; cmd="librosa soundfile scipy"},
    @{name="Accelerate (tối ưu)"; cmd="accelerate"}
)

foreach ($package in $packages) {
    Write-Host "🔧 Cài đặt $($package.name)..." -ForegroundColor Yellow
    try {
        $startTime = Get-Date
        python -m pip install $package.cmd --quiet
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        Write-Host "✅ $($package.name) đã được cài đặt trong $([math]::Round($duration, 1))s" -ForegroundColor Green
    } catch {
        Write-Host "❌ Lỗi khi cài đặt $($package.name)" -ForegroundColor Red
        Write-Host "Lỗi: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Thử cài đặt thủ công:" -ForegroundColor Cyan
        Write-Host "python -m pip install $($package.cmd)" -ForegroundColor White
        Read-Host "Nhấn Enter để thoát"
        exit 1
    }
}

Write-Host ""
Write-Host "✅ Tất cả dependencies đã được cài đặt thành công!" -ForegroundColor Green
Write-Host ""

# Kiểm tra file test có tồn tại không
if (-not (Test-Path "test_wav2vec2_vietnamese.py")) {
    Write-Host "❌ Không tìm thấy file test_wav2vec2_vietnamese.py" -ForegroundColor Red
    Write-Host "Vui lòng đảm bảo bạn đang chạy script này trong thư mục dự án" -ForegroundColor Yellow
    Read-Host "Nhấn Enter để thoát"
    exit 1
}

Write-Host "🎬 Bắt đầu demo Wav2Vec2 Vietnamese STT..." -ForegroundColor Cyan
Write-Host ""

# Chạy demo
try {
    Write-Host "🚀 Khởi chạy Python script..." -ForegroundColor Green
    python test_wav2vec2_vietnamese.py
} catch {
    Write-Host "❌ Lỗi khi chạy demo" -ForegroundColor Red
    Write-Host "Lỗi: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Bạn có thể chạy thủ công:" -ForegroundColor Cyan
    Write-Host "python test_wav2vec2_vietnamese.py" -ForegroundColor White
}

Write-Host ""
Write-Host "🎉 Setup hoàn thành!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Để sử dụng với file WAV cụ thể:" -ForegroundColor Cyan
Write-Host "   python test_wav2vec2_vietnamese.py your_audio.wav" -ForegroundColor White
Write-Host ""
Write-Host "💡 Để lưu kết quả:" -ForegroundColor Cyan
Write-Host "   python test_wav2vec2_vietnamese.py your_audio.wav --output result.json" -ForegroundColor White
Write-Host ""
Write-Host "📚 Tài liệu tham khảo:" -ForegroundColor Cyan
Write-Host "   - README_wav2vec2.md" -ForegroundColor White
Write-Host "   - requirements_wav2vec2.txt" -ForegroundColor White
Write-Host ""

Read-Host "Nhấn Enter để thoát"
