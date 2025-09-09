#!/usr/bin/env python3
"""
Debug script để test logic Viettel với error handling
"""

import logging
import sys
from check_viettel import viettel_combined_check

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MockDevice:
    """Mock GSM device để test"""
    def __init__(self, port="COM38"):
        self.port = port
        self.is_connected = True
        self.serial_connection = None
        self.timeout = 5
        
    def send_command_quick(self, command, wait_time=0.5):
        """Mock GSM response"""
        if command == "AT":
            return "OK"
        elif command == "ATH":
            return "OK"
        elif command.startswith("ATD"):
            return "OK"
        elif command == "AT+CLCC":
            # Simulate different responses
            return ""  # No active call
        return ""

def test_viettel_numbers():
    """Test với các số Viettel"""
    test_numbers = [
        "0961234567",  # Viettel
        "0321234567",  # Viettel
        "0871234567",  # Invalid
    ]
    
    device = MockDevice()
    
    def log_callback(message):
        print(f"[DEBUG] {message}")
    
    print("=" * 50)
    print("    DEBUG VIETTEL LOGIC")
    print("=" * 50)
    print()
    
    for i, number in enumerate(test_numbers, 1):
        print(f"🔍 Test {i}: {number}")
        try:
            result = viettel_combined_check(device, number, log_callback)
            print(f"✅ Kết quả: {result}")
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}")
            import traceback
            traceback.print_exc()
        print("-" * 30)

def check_audio_availability():
    """Kiểm tra audio có sẵn không"""
    print("🔊 Kiểm tra audio availability...")
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        print(f"✅ Audio devices: {device_count}")
        
        # List audio devices
        for i in range(device_count):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  📷 Input device {i}: {info['name']}")
        
        p.terminate()
        return True
        
    except Exception as e:
        print(f"❌ Audio lỗi: {str(e)}")
        return False

def check_templates():
    """Kiểm tra template files"""
    print("📋 Kiểm tra template files...")
    templates = [
        "template_de_lai_loi_nhan_ok.wav",
        "template_so_khong_dung_ok.wav", 
        "template_thue_bao_ok.wav"
    ]
    
    all_ok = True
    for template in templates:
        import os
        if os.path.exists(template):
            size = os.path.getsize(template)
            print(f"✅ {template} ({size} bytes)")
        else:
            print(f"❌ {template} - THIẾU")
            all_ok = False
    
    return all_ok

def main():
    """Main debug function"""
    print("🚀 VIETTEL DEBUG TOOL")
    print()
    
    # Check prerequisites
    audio_ok = check_audio_availability()
    templates_ok = check_templates()
    
    print()
    if not audio_ok:
        print("⚠️ Cảnh báo: Audio không sẵn sàng - sẽ fallback")
    if not templates_ok:
        print("⚠️ Cảnh báo: Thiếu templates - sẽ fallback")
    
    print()
    
    # Test logic
    test_viettel_numbers()
    
    print()
    print("🎯 DEBUG HOÀN THÀNH!")
    print()
    print("💡 Lưu ý:")
    print("- Nếu có lỗi PyAudio → kiểm tra audio device")
    print("- Nếu có lỗi template → copy đủ .wav files")
    print("- Logic sẽ fallback thành HOẠT ĐỘNG khi có lỗi")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Thoát debug tool")
    except Exception as e:
        print(f"\n💥 Lỗi không mong đợi: {str(e)}")
        import traceback
        traceback.print_exc()
