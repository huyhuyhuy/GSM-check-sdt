# Wav2Vec2 Vietnamese STT Installer Script
# Chạy với PowerShell: .\install_and_run_wav2vec2.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   WAV2VEC2 VIETNAMESE STT INSTALLER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🚀 Đang cài đặt dependencies..." -ForegroundColor Green
Write-Host ""

# Kiểm tra Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python đã được cài đặt: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python chưa được cài đặt hoặc không có trong PATH" -ForegroundColor Red
    Write-Host "Vui lòng cài đặt Python 3.8+ trước" -ForegroundColor Yellow
    Read-Host "Nhấn Enter để thoát"
    exit 1
}

# Kiểm tra pip
try {
    $pipVersion = python -m pip --version 2>&1
    Write-Host "✅ pip đã sẵn sàng: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ pip chưa được cài đặt" -ForegroundColor Red
    Write-Host "Đang cài đặt pip..." -ForegroundColor Yellow
    
    try {
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
        python get-pip.py
        Remove-Item "get-pip.py"
        Write-Host "✅ pip đã được cài đặt" -ForegroundColor Green
    } catch {
        Write-Host "❌ Không thể cài đặt pip" -ForegroundColor Red
        Read-Host "Nhấn Enter để thoát"
        exit 1
    }
}

Write-Host ""
Write-Host "📦 Đang cài đặt các package cần thiết..." -ForegroundColor Green
Write-Host ""

# Cài đặt dependencies
$packages = @(
    @{name="PyTorch"; cmd="torch torchaudio transformers"},
    @{name="Audio Processing"; cmd="librosa soundfile numpy scipy"},
    @{name="Accelerate"; cmd="accelerate"}
)

foreach ($package in $packages) {
    Write-Host "🔧 Cài đặt $($package.name)..." -ForegroundColor Yellow
    try {
        python -m pip install $package.cmd
        Write-Host "✅ $($package.name) đã được cài đặt" -ForegroundColor Green
    } catch {
        Write-Host "❌ Lỗi khi cài đặt $($package.name)" -ForegroundColor Red
        Read-Host "Nhấn Enter để thoát"
        exit 1
    }
}

Write-Host ""
Write-Host "✅ Tất cả dependencies đã được cài đặt!" -ForegroundColor Green
Write-Host ""

Write-Host "🎬 Bắt đầu demo Wav2Vec2 Vietnamese STT..." -ForegroundColor Cyan
Write-Host ""

# Chạy demo
try {
    python test_wav2vec2_vietnamese.py
} catch {
    Write-Host "❌ Lỗi khi chạy demo" -ForegroundColor Red
    Write-Host "Bạn có thể chạy thủ công:" -ForegroundColor Yellow
    Write-Host "python test_wav2vec2_vietnamese.py" -ForegroundColor White
}

Write-Host ""
Write-Host "🎉 Demo hoàn thành!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Để sử dụng với file WAV cụ thể:" -ForegroundColor Cyan
Write-Host "   python test_wav2vec2_vietnamese.py your_audio.wav" -ForegroundColor White
Write-Host ""
Write-Host "💡 Để lưu kết quả:" -ForegroundColor Cyan
Write-Host "   python test_wav2vec2_vietnamese.py your_audio.wav --output result.json" -ForegroundColor White
Write-Host ""

Read-Host "Nhấn Enter để thoát"
