#!/usr/bin/env python3
"""
Build script để tạo file exe từ GSM Classification System
Sử dụng PyInstaller để đóng gói ứng dụng
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Kiểm tra PyInstaller đã được cài đặt chưa"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("❌ PyInstaller chưa được cài đặt")
        print("🔧 Đang cài đặt PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ Đã cài đặt PyInstaller thành công")
            return True
        except subprocess.CalledProcessError:
            print("❌ Không thể cài đặt PyInstaller")
            return False

def create_spec_file():
    """Tạo file .spec cho PyInstaller"""
    
    # Kiểm tra và tạo danh sách datas
    datas_list = []
    if os.path.exists('icon.ico'):
        datas_list.append("('icon.ico', '.')")
        print("✅ Tìm thấy icon.ico - sẽ đóng gói vào exe")
    else:
        print("⚠️ Không tìm thấy icon.ico - bỏ qua")
    
    if os.path.exists('icon.png'):
        datas_list.append("('icon.png', '.')")
        print("✅ Tìm thấy icon.png - sẽ đóng gói vào exe")
    
    datas_str = "[" + ", ".join(datas_list) + "]" if datas_list else "[]"
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Danh sách các file dữ liệu cần đóng gói
datas = {datas_str}

# Danh sách các thư viện cần ẩn import
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.scrolledtext',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'threading',
    'queue',
    'time',
    'logging',
    'pathlib',
    'datetime',
    'os',
    'sys',
    'json',
    'pandas',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils.dataframe',
    'numpy',
    'librosa',
    'soundfile',
    'pydub',
    'torch',
    'transformers',
    'transformers.models.wav2vec2',
    'transformers.models.wav2vec2.modeling_wav2vec2',
    'transformers.models.wav2vec2.tokenization_wav2vec2',
    'transformers.models.wav2vec2.processing_wav2vec2',
    'transformers.tokenization_utils',
    'transformers.models.wav2vec2.configuration_wav2vec2',
    'transformers.models.wav2vec2.feature_extraction_wav2vec2',
    'transformers.models.wav2vec2.processing_wav2vec2',
    'scipy',
    'scipy.signal',
    'scipy.io',
    'scipy.io.wavfile',
]

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GSM_Classification_System',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Ẩn console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,  # Sử dụng icon nếu có
)"""
    
    with open('GSM_Classification.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ Đã tạo file GSM_Classification.spec")

def build_executable():
    """Build file exe từ spec file"""
    print("🔨 Bắt đầu build file exe...")
    
    try:
        # Xóa thư mục build và dist cũ nếu có
        if os.path.exists('build'):
            shutil.rmtree('build')
            print("🗑️ Đã xóa thư mục build cũ")
        
        if os.path.exists('dist'):
            shutil.rmtree('dist')
            print("🗑️ Đã xóa thư mục dist cũ")
        
        # Chạy PyInstaller
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "GSM_Classification.spec"]
        print(f"🚀 Chạy lệnh: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Build thành công!")
            
            # Kiểm tra file exe đã được tạo
            exe_path = Path("dist/GSM_Classification_System.exe")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📁 File exe: {exe_path.absolute()}")
                print(f"📏 Kích thước: {size_mb:.1f} MB")
                return True
            else:
                print("❌ File exe không được tạo")
                return False
        else:
            print("❌ Build thất bại!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi build: {e}")
        return False

def create_portable_package():
    """Tạo package portable với các file cần thiết"""
    print("📦 Tạo package portable...")
    
    try:
        # Tạo thư mục portable
        portable_dir = Path("GSM_Classification_Portable")
        if portable_dir.exists():
            shutil.rmtree(portable_dir)
        portable_dir.mkdir()
        
        # Copy file exe
        exe_src = Path("dist/GSM_Classification_System.exe")
        exe_dst = portable_dir / "GSM_Classification_System.exe"
        if exe_src.exists():
            shutil.copy2(exe_src, exe_dst)
            print(f"✅ Đã copy file exe")
        
        # Copy README
        readme_src = Path("README.md")
        readme_dst = portable_dir / "README.md"
        if readme_src.exists():
            shutil.copy2(readme_src, readme_dst)
            print(f"✅ Đã copy README")
        
        # Tạo file mẫu danh sách số điện thoại
        sample_file = portable_dir / "sample_phone_list.txt"
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write("""0987654321
0987654322
0987654323
0987654324
0987654325
""")
        print(f"✅ Đã tạo file mẫu danh sách số điện thoại")
        
        # Tạo file hướng dẫn sử dụng
        guide_file = portable_dir / "HUONG_DAN_SU_DUNG.txt"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write("""HƯỚNG DẪN SỬ DỤNG GSM CLASSIFICATION SYSTEM
===============================================

1. CHUẨN BỊ:
   - Kết nối modem GSM với máy tính qua USB
   - Đảm bảo driver đã được cài đặt
   - Chuẩn bị file danh sách số điện thoại (.txt)

2. SỬ DỤNG:
   - Chạy file: GSM_Classification_System.exe
   - Chọn file danh sách số điện thoại
   - Click "Bắt Đầu" để bắt đầu xử lý
   - Theo dõi log trong cửa sổ
   - Click "Xuất Kết Quả" để lưu file Excel

3. FILE DANH SÁCH SỐ ĐIỆN THOẠI:
   - Mỗi số điện thoại trên một dòng
   - Chỉ chứa số, không có ký tự đặc biệt
   - Xem file mẫu: sample_phone_list.txt

4. KẾT QUẢ:
   - File Excel với các sheet phân loại
   - Thống kê tổng hợp và chi tiết
   - File audio được lưu trong thư mục

5. LƯU Ý:
   - Đảm bảo SIM có tiền để gọi điện
   - Kiểm tra tín hiệu mạng tốt
   - Không tắt chương trình khi đang xử lý

Hỗ trợ: Xem file README.md để biết thêm chi tiết
""")
        print(f"✅ Đã tạo file hướng dẫn")
        
        print(f"📁 Package portable: {portable_dir.absolute()}")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi tạo package portable: {e}")
        return False

def main():
    """Hàm main để build"""
    print("🚀 GSM Classification System - Build Script")
    print("=" * 50)
    
    # Kiểm tra PyInstaller
    if not check_pyinstaller():
        return False
    
    # Tạo spec file
    create_spec_file()
    
    # Build executable
    if not build_executable():
        return False
    
    # Tạo package portable
    if not create_portable_package():
        return False
    
    print("\n" + "=" * 50)
    print("🎉 BUILD THÀNH CÔNG!")
    print("\n📁 Các file đã tạo:")
    print("  - dist/GSM_Classification_System.exe (File exe chính)")
    print("  - GSM_Classification_Portable/ (Package portable)")
    
    print("\n🚀 Để sử dụng:")
    print("  1. Copy thư mục GSM_Classification_Portable")
    print("  2. Chạy GSM_Classification_System.exe")
    print("  3. Làm theo hướng dẫn trong HUONG_DAN_SU_DUNG.txt")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Hoàn thành build thành công!")
        else:
            print("\n❌ Build thất bại!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Build bị hủy bởi người dùng")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Lỗi không mong muốn: {e}")
        sys.exit(1)
