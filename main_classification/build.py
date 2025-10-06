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
        print(f"[OK] PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("[ERROR] PyInstaller chua duoc cai dat")
        print("[INFO] Dang cai dat PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] Da cai dat PyInstaller thanh cong")
            return True
        except subprocess.CalledProcessError:
            print("[ERROR] Khong the cai dat PyInstaller")
            return False

def create_spec_file():
    """Tạo file .spec cho PyInstaller"""
    
    # Kiểm tra và tạo danh sách datas
    datas_list = []
    if os.path.exists('icon.ico'):
        datas_list.append("('icon.ico', '.')")
        print("[OK] Tim thay icon.ico - se dong goi vao exe")
    else:
        print("[WARNING] Khong tim thay icon.ico - bo qua")
    
    if os.path.exists('icon.png'):
        datas_list.append("('icon.png', '.')")
        print("[OK] Tim thay icon.png - se dong goi vao exe")
    
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
    # GSM detection và string detection
    'detect_gsm_port',
    'string_detection',
    'gsm_instance',
    'controller',
    'export_excel',
    # Concurrent processing
    'concurrent.futures',
    'concurrent.futures.thread',
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

# Fix Python DLL issue
pyi_splash = None

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
    upx=False,  # Tắt UPX để tránh DLL issues
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
    
    print("[OK] Da tao file GSM_Classification.spec")

def build_executable():
    """Build file exe từ spec file"""
    print("[INFO] Bat dau build file exe...")
    
    try:
        # Xóa thư mục build và dist cũ nếu có
        if os.path.exists('build'):
            shutil.rmtree('build')
            print("[INFO] Da xoa thu muc build cu")
        
        if os.path.exists('dist'):
            shutil.rmtree('dist')
            print("[INFO] Da xoa thu muc dist cu")
        
        # Thử build với spec file trước
        try:
            cmd = [
                sys.executable, "-m", "PyInstaller", 
                "--clean",
                "--onefile",
                "--noconsole",
                "--noupx",
                "GSM_Classification.spec"
            ]
            print(f"[INFO] Chay lenh: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return check_exe_result()
            else:
                print("[WARNING] Build voi spec file that bai, thu cach khac...")
                print("STDERR:", result.stderr)
                
        except Exception as e:
            print(f"[WARNING] Loi khi build voi spec: {e}")
        
        # Fallback: Build trực tiếp không dùng spec file
        print("[INFO] Thu build truc tiep...")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--noconsole", 
            "--noupx",
            "--name", "GSM_Classification_System",
            "--hidden-import", "tkinter",
            "--hidden-import", "tkinter.ttk",
            "--hidden-import", "serial",
            "--hidden-import", "transformers",
            "--hidden-import", "torch",
            "--hidden-import", "librosa",
            "--hidden-import", "pydub",
            "--hidden-import", "string_detection",
            "--hidden-import", "detect_gsm_port",
            "--hidden-import", "gsm_instance",
            "--hidden-import", "controller",
            "--hidden-import", "export_excel",
            "main_gui.py"
        ]
        
        if os.path.exists('icon.ico'):
            cmd.extend(["--icon", "icon.ico"])
        
        print(f"[INFO] Chay lenh: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return check_exe_result()
        else:
            print("[ERROR] Build that bai!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"[ERROR] Loi khi build: {e}")
        return False

def check_exe_result():
    """Kiểm tra kết quả build exe"""
    exe_path = Path("dist/GSM_Classification_System.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("[OK] Build thanh cong!")
        print(f"[INFO] File exe: {exe_path.absolute()}")
        print(f"[INFO] Kich thuoc: {size_mb:.1f} MB")
        return True
    else:
        print("[ERROR] File exe khong duoc tao")
        return False

def create_portable_package():
    """Tạo package portable với các file cần thiết"""
    print("[INFO] Tao package portable...")
    
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
            print(f"[OK] Da copy file exe")
        
        # Copy README
        readme_src = Path("README.md")
        readme_dst = portable_dir / "README.md"
        if readme_src.exists():
            shutil.copy2(readme_src, readme_dst)
            print(f"[OK] Da copy README")
        
        # Tạo file mẫu danh sách số điện thoại
        sample_file = portable_dir / "sample_phone_list.txt"
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write("""0987654321
0987654322
0987654323
0987654324
0987654325
""")
        print(f"[OK] Da tao file mau danh sach so dien thoai")
        
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
        print(f"[OK] Da tao file huong dan")
        
        print(f"[INFO] Package portable: {portable_dir.absolute()}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Loi khi tao package portable: {e}")
        return False

def main():
    """Hàm main để build"""
    print("GSM Classification System - Build Script")
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
    print("\n[INFO] Cac file da tao:")
    print("  - dist/GSM_Classification_System.exe (File exe chính)")
    print("  - GSM_Classification_Portable/ (Package portable)")
    
    print("\n[INFO] De su dung:")
    print("  1. Copy thư mục GSM_Classification_Portable")
    print("  2. Chạy GSM_Classification_System.exe")
    print("  3. Làm theo hướng dẫn trong HUONG_DAN_SU_DUNG.txt")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n[SUCCESS] Hoan thanh build thanh cong!")
        else:
            print("\n[ERROR] Build that bai!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[WARNING] Build bi huy boi nguoi dung")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Loi khong mong muon: {e}")
        sys.exit(1)
