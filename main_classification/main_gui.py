import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import json
import os

class AudioClassificationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Phone Number Classification System")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Thiết lập icon cho ứng dụng
        self.set_app_icon()
        
        self.setup_ui()
        self.setup_styles()
    
    def set_app_icon(self):
        """Thiết lập icon cho ứng dụng"""
        self.root.iconbitmap("icon.ico")
        
    def setup_styles(self):
        """Thiết lập style cho giao diện"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Style cho buttons - tương đồng với header
        style.configure('Action.TButton', 
                       background='#1976D2',      # Nền xanh đậm như header
                       foreground='white',        # Chữ trắng
                       font=('Arial', 9, 'bold'), # Font giống header
                       padding=(10, 5),           # Padding rộng hơn
                       relief='flat',             # Không viền nổi
                       borderwidth=0)             # Không viền
        
        # Style cho button khi hover
        style.map('Action.TButton',
                 background=[('active', '#1565C0'),    # Xanh đậm hơn khi hover
                            ('pressed', '#0D47A1')])  # Xanh rất đậm khi click
        
        # Style cho labels
        style.configure('Title.TLabel',
                       font=('Arial', 12, 'bold'),
                       foreground='#2c3e50')
        
        style.configure('Info.TLabel',
                       font=('Arial', 9),
                       foreground='#34495e')
        
        # Style cho Treeview header - nền xanh đậm, chữ trắng, in đậm
        style.configure('Treeview.Heading',
                       background='#1976D2',  # Xanh đậm
                       foreground='white',     # Chữ trắng
                       font=('Arial', 9, 'bold'),
                       relief='flat')
        
        # Style cho Treeview cells
        style.configure('Treeview',
                       background='white',
                       foreground='black',
                       font=('Arial', 9),
                       rowheight=25)
    
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
        main_frame.rowconfigure(2, weight=1)  # Treeview frame chiếm 1/4
        main_frame.rowconfigure(3, weight=3)  # Log frame chiếm 3/4
        
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
                                   command=self.start_processing,
                                   style='Action.TButton',
                                   width=12)
        self.start_btn.grid(row=0, column=1, padx=(0, 3))
        
        # Nút dừng
        self.stop_btn = ttk.Button(button_frame, 
                                  text="Dừng", 
                                  command=self.stop_processing,
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
        
        # Frame cho Treeview GSM
        tree_frame = ttk.LabelFrame(main_frame, text="Danh Sách GSM", padding="5")
        tree_frame.grid(row=2, column=0, columnspan=4, pady=(0, 5), sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # tạo 1 vùng chứa list các đối tượng là các cổng GSM quét được
        # mỗi hàng sẽ chia thành 5 cột: stt, số cổng GSM, trạng thái sim, số điện thoại trên cổng đó, số tiền còn lại của sim đó
        self.gsm_list = ttk.Treeview(tree_frame, columns=("stt", "COM", "sim status", "phone number", "remaining balance"), show="headings")
        
        # Thiết lập header với style đẹp hơn
        self.gsm_list.heading("stt", text="STT", anchor="center")
        self.gsm_list.heading("COM", text="Cổng GSM", anchor="center")
        self.gsm_list.heading("sim status", text="Trạng Thái SIM", anchor="center")
        self.gsm_list.heading("phone number", text="Số Điện Thoại", anchor="center")
        self.gsm_list.heading("remaining balance", text="Số Dư Còn Lại", anchor="center")
        
        # Thiết lập độ rộng cột tự động fit
        self.gsm_list.column("stt", width=60, minwidth=60, anchor="center")
        self.gsm_list.column("COM", width=100, minwidth=100, anchor="center")
        self.gsm_list.column("sim status", width=120, minwidth=120, anchor="center")
        self.gsm_list.column("phone number", width=150, minwidth=150, anchor="center")
        self.gsm_list.column("remaining balance", width=140, minwidth=140, anchor="center")
        
        # Thiết lập màu sắc cho các hàng
        self.gsm_list.tag_configure("even", background="#E3F2FD")  # Xanh dương nhạt
        self.gsm_list.tag_configure("odd", background="white")     # Trắng
        
        self.gsm_list.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Frame cho log
        log_frame = ttk.LabelFrame(main_frame, text="Log Quá Trình", padding="10")
        log_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Text area cho log
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Khởi tạo
        self.initialize_system()
    
    def initialize_system(self):
        """Khởi tạo hệ thống"""
        def init_thread():
            self.add_log("Đang khởi tạo hệ thống...")
            # Simulate initialization
            time.sleep(1)
            self.add_log("Khởi tạo hệ thống thành công!")
            # Thêm fake data vào Treeview
            self.add_fake_data()
        
        threading.Thread(target=init_thread, daemon=True).start()
    
    def add_fake_data(self):
        """Thêm dữ liệu giả vào Treeview"""
        fake_data = [
            ("1", "COM37", "Active", "0987654321", "50,000 VND"),
            ("2", "COM38", "Active", "0987654322", "45,000 VND"),
            ("3", "COM39", "Inactive", "0987654323", "0 VND"),
            ("4", "COM40", "Active", "0987654324", "75,000 VND"),
            ("5", "COM41", "Active", "0987654325", "30,000 VND"),
            ("6", "COM42", "Inactive", "0987654326", "0 VND"),
            ("7", "COM43", "Active", "0987654327", "60,000 VND"),
            ("8", "COM44", "Active", "0987654328", "25,000 VND"),
            ("9", "COM45", "Active", "0987654329", "80,000 VND"),
            ("10", "COM46", "Inactive", "0987654330", "0 VND"),
            ("11", "COM47", "Active", "0987654321", "50,000 VND"),
            ("12", "COM48", "Active", "0987654322", "45,000 VND"),
            ("13", "COM49", "Inactive", "0987654323", "0 VND"),
            ("14", "COM50", "Active", "0987654324", "75,000 VND"),
            ("15", "COM51", "Active", "0987654325", "30,000 VND"),
            ("16", "COM52", "Inactive", "0987654326", "0 VND"),
            ("17", "COM53", "Active", "0987654327", "60,000 VND"),
            ("18", "COM54", "Active", "0987654328", "25,000 VND"),
            ("19", "COM55", "Active", "0987654329", "80,000 VND"),
            ("20", "COM56", "Inactive", "0987654330", "0 VND")
        ]
        
        for i, data in enumerate(fake_data):
            # Xác định tag dựa trên số thứ tự (0-based)
            tag = "even" if i % 2 == 0 else "odd"
            self.gsm_list.insert("", "end", values=data, tags=(tag,))
        
        self.add_log(f"Đã thêm {len(fake_data)} dòng dữ liệu GSM vào bảng")
    
    def select_file(self):
        """Chọn file danh sách số điện thoại"""
       
    
    def start_processing(self):
        """Bắt đầu quá trình xử lý"""
    
    def stop_processing(self):
        """Dừng quá trình xử lý"""
    
    def _finalize_completion(self):
        """Hoàn thành quá trình xử lý"""
    
    def export_results(self):
        """Xuất kết quả ra file Excel"""
    
    def add_log(self, message: str):
        """Thêm log vào text area"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
    
    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        self.root.destroy()

def main():
    root = tk.Tk()
    app = AudioClassificationGUI(root)
    
    # Xử lý đóng ứng dụng
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()
