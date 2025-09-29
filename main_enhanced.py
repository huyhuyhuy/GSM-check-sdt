import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import json
import os
# from gsm_manager_enhanced import GSMManager
# from file_manager import FileManager

class PhoneCheckerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GSM Phone Number Checker - Enhanced with ESP32 Multi-Channel Audio Analysis")
        self.root.geometry("800x1000")
        self.root.resizable(True, True)
        
        # Load config
        self.config = self.load_config()
        
        # Khởi tạo các manager
        gsm_start = self.config.get("gsm_port_start", 35)
        gsm_end = gsm_start + 31
        esp_port = self.config.get("esp_port", "COM67")
        
        self.gsm_manager = GSMManager(start_port=gsm_start, end_port=gsm_end, esp32_port=esp_port)
        self.file_manager = FileManager()
        
        # Thiết lập callback cho log
        self.gsm_manager.set_log_callback(self.add_log)
        
        # Biến trạng thái
        self.is_checking = False
        self.selected_file = ""
        
        self.setup_ui()
        self.setup_styles()
    
    def load_config(self):
        """Load config từ file config.json"""
        config_file = "config.json"
        default_config = {
            "gsm_port_start": 35,
            "esp_port": "COM67"
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config
            else:
                # Tạo file config mặc định
                self.save_config(default_config)
                return default_config
        except Exception as e:
            print(f"Lỗi load config: {e}")
            return default_config
    
    def save_config(self, config):
        """Save config vào file config.json"""
        try:
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi save config: {e}")
    
    def save_config_ui(self):
        """Save config từ UI và restart GSM manager"""
        try:
            # Lấy giá trị từ UI
            gsm_port_start = int(self.gsm_port_start_var.get())
            esp_port = self.esp_port_var.get()
            
            # Validate
            if gsm_port_start < 1 or gsm_port_start > 100:
                messagebox.showerror("Lỗi", "GSM Port Start phải từ 1-100")
                return
            
            if not esp_port.startswith("COM"):
                messagebox.showerror("Lỗi", "ESP Port phải bắt đầu bằng COM")
                return
            
            # Tạo config mới
            new_config = {
                "gsm_port_start": gsm_port_start,
                "esp_port": esp_port
            }
            
            # Save config
            self.save_config(new_config)
            self.config = new_config
            
            # Restart GSM manager với config mới
            gsm_end = gsm_port_start + 31
            self.gsm_manager.cleanup()
            self.gsm_manager = GSMManager(start_port=gsm_port_start, end_port=gsm_end, esp32_port=esp_port)
            self.gsm_manager.set_log_callback(self.add_log)

            
            # Khởi tạo lại
            self.initialize_gsm()
            
            messagebox.showinfo("Thành công", f"Đã lưu config:\nGSM Port Start: {gsm_port_start}\nESP Port: {esp_port}")
            
        except ValueError:
            messagebox.showerror("Lỗi", "GSM Port Start phải là số nguyên")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi save config: {str(e)}")
        
    def setup_styles(self):
        """Thiết lập style cho giao diện"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Style cho buttons - nhỏ gọn hơn
        style.configure('Action.TButton', 
                       font=('Arial', 8, 'bold'),
                       padding=5)
        
        # Style cho labels
        style.configure('Title.TLabel',
                       font=('Arial', 12, 'bold'),
                       foreground='#2c3e50')
        
        style.configure('Info.TLabel',
                       font=('Arial', 9),
                       foreground='#34495e')
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Frame chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Cấu hình grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.columnconfigure(3, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Frame cho buttons - 4 nút xếp 1 hàng
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=0, column=0, columnspan=4, pady=(0, 5))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)
        
        # Nút chọn file
        self.select_file_btn = ttk.Button(button_frame, 
                                         text="Nhập File", 
                                         command=self.select_file,
                                         style='Action.TButton',
                                         width=12)
        self.select_file_btn.grid(row=0, column=0, padx=(0, 3))
        
        # Nút bắt đầu
        self.start_btn = ttk.Button(button_frame, 
                                   text="Bắt Đầu", 
                                   command=self.start_checking,
                                   style='Action.TButton',
                                   width=12)
        self.start_btn.grid(row=0, column=1, padx=(0, 3))
        
        # Nút dừng
        self.stop_btn = ttk.Button(button_frame, 
                                  text="Dừng", 
                                  command=self.stop_checking,
                                  state='disabled',
                                  style='Action.TButton',
                                  width=12)
        self.stop_btn.grid(row=0, column=2, padx=(0, 3))
        
        # Nút xuất kết quả
        self.export_btn = ttk.Button(button_frame, 
                                    text="Xuất Kết Quả", 
                                    command=self.export_results,
                                    style='Action.TButton',
                                    width=12)
        self.export_btn.grid(row=0, column=3, padx=(0, 3))
        
        # Frame cho config
        config_frame = ttk.LabelFrame(main_frame, text="Cấu Hình Hệ Thống", padding="5")
        config_frame.grid(row=1, column=0, columnspan=4, pady=(0, 5), sticky=(tk.W, tk.E))
        
        # GSM Port Start
        ttk.Label(config_frame, text="GSM Port Start:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.gsm_port_start_var = tk.StringVar(value=str(self.config.get("gsm_port_start", 35)))
        self.gsm_port_start_entry = ttk.Entry(config_frame, textvariable=self.gsm_port_start_var, width=10)
        self.gsm_port_start_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # ESP Port
        ttk.Label(config_frame, text="ESP Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.esp_port_var = tk.StringVar(value=self.config.get("esp_port", "COM67"))
        self.esp_port_entry = ttk.Entry(config_frame, textvariable=self.esp_port_var, width=10)
        self.esp_port_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Nút Save
        self.save_config_btn = ttk.Button(config_frame, 
                                         text="Save", 
                                         command=self.save_config_ui,
                                         style='Action.TButton',
                                         width=8)
        self.save_config_btn.grid(row=0, column=4, sticky=tk.W)
        
        # Frame cho thông tin hệ thống
        info_frame = ttk.LabelFrame(main_frame, text="Thông Tin Hệ Thống", padding="5")
        info_frame.grid(row=2, column=0, columnspan=4, pady=(0, 5), sticky=(tk.W, tk.E))
        
        # Thông tin ESP32
        self.esp32_status_label = ttk.Label(info_frame, text="ESP32: Đang khởi tạo...", style='Info.TLabel')
        self.esp32_status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Thông tin GSM
        self.gsm_status_label = ttk.Label(info_frame, text="GSM: Đang khởi tạo...", style='Info.TLabel')
        self.gsm_status_label.grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # Thông tin channels
        self.channels_status_label = ttk.Label(info_frame, text="Channels: 0/32", style='Info.TLabel')
        self.channels_status_label.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        

        
        # Frame cho log
        log_frame = ttk.LabelFrame(main_frame, text="Log Quá Trình", padding="10")
        log_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Text area cho log
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Khởi tạo GSM devices
        self.initialize_gsm()
    
    def initialize_gsm(self):
        """Khởi tạo GSM devices"""
        def init_thread():
            self.add_log("Đang khởi tạo hệ thống...")
            success = self.gsm_manager.initialize_devices()
            if success:
                self.add_log("Khởi tạo hệ thống thành công!")
                self.update_status_labels()
            else:
                self.add_log("Khởi tạo hệ thống thất bại!")
                self.update_status_labels()
        
        threading.Thread(target=init_thread, daemon=True).start()
    
    def update_status_labels(self):
        """Cập nhật thông tin trạng thái"""
        # Cập nhật ESP32 status
        esp32_status = self.gsm_manager.esp32_analyzer.get_status()
        if esp32_status["connected"]:
            self.esp32_status_label.config(text=f"ESP32: Kết nối ({esp32_status['port']})", foreground="green")
        else:
            self.esp32_status_label.config(text="ESP32: Không kết nối", foreground="red")
        
        # Cập nhật GSM status
        gsm_count = len(self.gsm_manager.devices)
        if gsm_count > 0:
            self.gsm_status_label.config(text=f"GSM: {gsm_count} thiết bị", foreground="green")
        else:
            self.gsm_status_label.config(text="GSM: Không có thiết bị", foreground="red")
        
        # Cập nhật channels status
        active_channels = self.gsm_manager.get_device_channels()
        self.channels_status_label.config(text=f"Channels: {len(active_channels)}/32", foreground="blue")
    
    def select_file(self):
        """Chọn file danh sách số điện thoại"""
        file_path = filedialog.askopenfilename(
            title="Chọn file danh sách số điện thoại",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                phone_numbers = self.file_manager.load_phone_numbers(file_path)
                self.selected_file = file_path
                self.add_log(f"Đã tải {len(phone_numbers)} số điện thoại từ file: {file_path}")
                # test esp32 sau khi chọn file
                # self.gsm_manager.esp32_analyzer.quick_adc_test(channel=0, num_samples=1000)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file: {str(e)}")
    
    def start_checking(self):
        """Bắt đầu quá trình check"""
        if not self.selected_file:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file danh sách trước!")
            return
        
        if not self.gsm_manager.devices:
            messagebox.showerror("Lỗi", "Chưa có thiết bị GSM nào được khởi tạo!")
            return
        
        self.is_checking = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.select_file_btn.config(state='disabled')
        
        # Reset kết quả
        self.file_manager.reset_results()

        # clear log
        self.log_text.delete("1.0", tk.END)

        # Bắt đầu check trong thread riêng
        def check_thread():
            self.gsm_manager.start_checking(
                self.file_manager.phone_numbers,
                self.on_result_received
            )
        
        threading.Thread(target=check_thread, daemon=True).start()
        
        # Bắt đầu cập nhật progress
        self.update_progress()
    
    def stop_checking(self):
        """Dừng quá trình check"""
        self.gsm_manager.stop_checking()
        self.is_checking = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.select_file_btn.config(state='normal')
        self.add_log("Đã dừng quá trình check")
    
    def on_result_received(self, phone_number: str, result_type: str):
        """Callback khi nhận được kết quả check với 3 loại: HOẠT ĐỘNG, THUÊ BAO, SỐ KHÔNG ĐÚNG"""
        self.file_manager.add_result(phone_number, result_type)
        
        # Hiển thị tiến độ trong log
        checked, total, percentage = self.file_manager.get_progress()
        self.add_log(f"[{checked}/{total}] Số {phone_number}: {result_type}")
    
    def update_progress(self):
        """Cập nhật tiến độ"""
        if self.is_checking:
            checked, total, percentage = self.file_manager.get_progress()
            
            # Kiểm tra hoàn thành
            if checked >= total and total > 0:
                # Thêm delay để đảm bảo ADC analysis hoàn thành
                self.add_log("Đang chờ ADC analysis hoàn thành...")
                self.root.after(2000, self._finalize_completion)  # Chờ 2 giây
                return
            
            # Cập nhật tiếp sau 100ms
            self.root.after(100, self.update_progress)
    
    def _finalize_completion(self):
        """Hoàn thành quá trình check sau khi ADC analysis xong"""
        self.is_checking = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.select_file_btn.config(state='normal')
        self.add_log("✅ Hoàn thành check tất cả số điện thoại!")
        messagebox.showinfo("Thành công", "Đã hoàn thành check tất cả số điện thoại!")
    

    

    
    def export_results(self):
        """Xuất kết quả ra file Excel với 3 loại: HOẠT ĐỘNG, THUÊ BAO, SỐ KHÔNG ĐÚNG"""
        if not self.file_manager.hoat_dong and not self.file_manager.thue_bao and not self.file_manager.so_khong_dung:
            messagebox.showwarning("Cảnh báo", "Chưa có kết quả để xuất!")
            return
        
        try:
            excel_file = self.file_manager.save_results()
            hoat_dong_count = len(self.file_manager.hoat_dong)
            thue_bao_count = len(self.file_manager.thue_bao)
            so_khong_dung_count = len(self.file_manager.so_khong_dung)
            
            self.add_log(f"Đã xuất kết quả thành công!")
            self.add_log(f"- File Excel: {excel_file}")
            self.add_log(f"- Số HOẠT ĐỘNG: {hoat_dong_count}")
            self.add_log(f"- Số THUÊ BAO: {thue_bao_count}")
            self.add_log(f"- Số SỐ KHÔNG ĐÚNG: {so_khong_dung_count}")
            
            messagebox.showinfo("Thành công", f"Đã xuất kết quả thành công!\n\nFile Excel: {excel_file}\nSố HOẠT ĐỘNG: {hoat_dong_count}\nSố THUÊ BAO: {thue_bao_count}\nSố SỐ KHÔNG ĐÚNG: {so_khong_dung_count}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất kết quả: {str(e)}")
    
    def add_log(self, message: str):
        """Thêm log vào text area"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # Giới hạn số dòng log để tránh memory leak
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:
            self.log_text.delete("1.0", "500.0")
    

    

    
    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        if self.is_checking:
            if messagebox.askokcancel("Xác nhận", "Đang trong quá trình check. Bạn có muốn thoát?"):
                self.gsm_manager.cleanup()
                self.root.destroy()
        else:
            self.gsm_manager.cleanup()
            self.root.destroy()

def main():
    root = tk.Tk()
    app = PhoneCheckerGUI(root)
    
    # Xử lý đóng ứng dụng
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main() 