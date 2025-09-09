#!/usr/bin/env python3
"""
Script kiểm tra dependencies trước khi build
"""

import sys
import importlib

def check_dependency(module_name: str, display_name: str = None) -> bool:
    """Kiểm tra một dependency"""
    if display_name is None:
        display_name = module_name
    
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✓ {display_name}: {version}")
        return True
    except ImportError:
        print(f"✗ {display_name}: CHƯA CÀI ĐẶT")
        return False

def main():
    """Kiểm tra tất cả dependencies"""
    print("=" * 50)
    print("   KIỂM TRA DEPENDENCIES CHO BUILD")
    print("=" * 50)
    print()
    
    dependencies = [
        ("serial", "pyserial"),
        ("numpy", "numpy"),
        ("openpyxl", "openpyxl"),
        ("scipy", "scipy"),
        ("scipy.signal", "scipy.signal"),
        ("pyaudio", "pyaudio"),
        ("librosa", "librosa (Professional MFCC)"),
        ("fastdtw", "fastdtw (DTW distance)"),
        ("tkinter", "tkinter"),
        ("threading", "threading"),
        ("queue", "queue"),
        ("logging", "logging"),
        ("datetime", "datetime"),
        ("time", "time"),
        ("os", "os"),
        ("typing", "typing")
    ]
    
    all_ok = True
    
    for module_name, display_name in dependencies:
        if not check_dependency(module_name, display_name):
            all_ok = False
    
    print()
    print("=" * 50)
    
    if all_ok:
        print("✅ TẤT CẢ DEPENDENCIES ĐÃ SẴN SÀNG!")
        print("🚀 Có thể chạy: python build.py")
    else:
        print("❌ CÒN THIẾU DEPENDENCIES!")
        print("📦 Chạy: pip install -r requirements.txt")
        print("💡 Lưu ý: librosa + fastdtw cần để dùng Professional MFCC")
        print("💡 PyAudio có thể cần cài thủ công trên Windows")
    
    print("=" * 50)
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
