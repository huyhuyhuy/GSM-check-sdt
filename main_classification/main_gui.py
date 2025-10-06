import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import json
import os
from controller import GSMController

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
        try:
            # Thử load icon từ đường dẫn tương đối
            icon_path = "icon.ico"
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                # Nếu không tìm thấy, thử từ thư mục của script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(script_dir, "icon.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                else:
                    # Nếu vẫn không tìm thấy, bỏ qua (không crash)
                    print("⚠️ Không tìm thấy file icon.ico - bỏ qua thiết lập icon")
        except Exception as e:
            # Bỏ qua lỗi icon để không crash ứng dụng
            print(f"⚠️ Không thể thiết lập icon: {e}")
        
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
        # mỗi hàng sẽ chia thành 6 cột: stt, số cổng GSM, trạng thái sim, nhà mạng, số điện thoại trên cổng đó, số tiền còn lại của sim đó
        self.gsm_list = ttk.Treeview(tree_frame, columns=("stt", "COM", "sim status", "network operator", "phone number", "remaining balance"), show="headings")
        
        # Thiết lập header với style đẹp hơn
        self.gsm_list.heading("stt", text="STT", anchor="center")
        self.gsm_list.heading("COM", text="Cổng GSM", anchor="center")
        self.gsm_list.heading("sim status", text="Tín Hiệu Sóng", anchor="center")
        self.gsm_list.heading("network operator", text="Nhà Mạng", anchor="center")
        self.gsm_list.heading("phone number", text="Số Điện Thoại", anchor="center")
        self.gsm_list.heading("remaining balance", text="Số Dư Còn Lại", anchor="center")
        
        # Thiết lập độ rộng cột tự động fit
        self.gsm_list.column("stt", width=60, minwidth=60, anchor="center")
        self.gsm_list.column("COM", width=100, minwidth=100, anchor="center")
        self.gsm_list.column("sim status", width=120, minwidth=120, anchor="center")
        self.gsm_list.column("network operator", width=120, minwidth=120, anchor="center")
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
        self.controller = GSMController()
        self.controller.set_log_callback(self.add_log)
        self.phone_file_path = None

        # Hiện loading dialog và khởi tạo hệ thống trong background
        self.show_loading_and_initialize()
    
    def show_loading_and_initialize(self):
        """Hiện loading dialog và khởi tạo hệ thống trong background"""
        # Tạo loading dialog
        loading_dialog = tk.Toplevel(self.root)
        loading_dialog.title("Đang khởi tạo...")
        loading_dialog.geometry("400x150")
        loading_dialog.resizable(False, False)

        # Center dialog
        loading_dialog.transient(self.root)
        loading_dialog.grab_set()

        # Frame chứa nội dung
        frame = ttk.Frame(loading_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Label thông báo
        label = ttk.Label(frame,
                         text="🔍 Đang quét và khởi tạo các cổng GSM...\nVui lòng đợi...",
                         font=('Arial', 11),
                         justify=tk.CENTER)
        label.pack(pady=10)

        # Progress bar
        progress = ttk.Progressbar(frame, mode='indeterminate', length=300)
        progress.pack(pady=10)
        progress.start(10)

        # Status label
        status_label = ttk.Label(frame,
                                text="Đang quét cổng COM...",
                                font=('Arial', 9),
                                foreground='#666')
        status_label.pack(pady=5)

        def update_status(message):
            """Cập nhật status label"""
            status_label.config(text=message)

        def init_thread():
            """Thread khởi tạo hệ thống"""
            try:
                # Quét các cổng GSM
                self.root.after(0, lambda: update_status("🔍 Đang quét cổng COM..."))
                self.add_log("🔍 Quét các cổng GSM...")
                gsm_ports = self.controller.scan_gsm_ports()

                if gsm_ports:
                    # Hiển thị kết quả quét
                    self.root.after(0, lambda: update_status(f"✅ Tìm thấy {len(gsm_ports)} cổng GSM"))
                    self.display_gsm_ports(gsm_ports)
                    self.add_log(f"✅ Tìm thấy {len(gsm_ports)} cổng GSM")

                    # GSM instances đã được tạo trong scan_gsm_ports
                    self.add_log("✅ GSM instances đã sẵn sàng!")
                else:
                    self.add_log("⚠️ Không tìm thấy cổng GSM nào")
                    # Hiển thị thông báo
                    self.display_no_gsm_found()

            except Exception as e:
                self.add_log(f"❌ Lỗi khởi tạo: {e}")
                import traceback
                self.add_log(traceback.format_exc())

            finally:
                # Đóng loading dialog
                self.root.after(100, loading_dialog.destroy)

        # Bắt đầu thread khởi tạo
        threading.Thread(target=init_thread, daemon=True).start()

    def initialize_system(self):
        """Khởi tạo hệ thống (deprecated - dùng show_loading_and_initialize thay thế)"""
        self.show_loading_and_initialize()
    
    def display_gsm_ports(self, gsm_ports):
        """Hiển thị danh sách cổng GSM trong Treeview (sắp xếp theo cổng COM tăng dần)"""
        # Xóa dữ liệu cũ
        for item in self.gsm_list.get_children():
            self.gsm_list.delete(item)

        # Sắp xếp theo cổng COM tăng dần (COM3, COM36, COM37, COM39, ...)
        def extract_com_number(gsm_info):
            """Trích xuất số từ cổng COM để sắp xếp"""
            port = gsm_info["port"]
            try:
                # Lấy số từ "COM37" -> 37
                return int(port.replace("COM", ""))
            except:
                return 999  # Nếu không parse được, đẩy xuống cuối

        sorted_gsm_ports = sorted(gsm_ports, key=extract_com_number)

        # Thêm dữ liệu mới (đã sắp xếp)
        for i, gsm_info in enumerate(sorted_gsm_ports, 1):
            data = (
                str(i),
                gsm_info["port"],
                gsm_info["signal"],  # Thay vì status, dùng signal
                gsm_info.get("network_operator", "Không xác định"),
                gsm_info["phone_number"],
                gsm_info["balance"]
            )

            # Xác định tag dựa trên số thứ tự (0-based)
            tag = "even" if i % 2 == 0 else "odd"
            self.gsm_list.insert("", "end", values=data, tags=(tag,))
    
    def display_no_gsm_found(self):
        """Hiển thị thông báo khi không tìm thấy GSM"""
        # Xóa dữ liệu cũ
        for item in self.gsm_list.get_children():
            self.gsm_list.delete(item)
        
        # Thêm thông báo với đủ 6 cột
        self.gsm_list.insert("", "end", values=(
            "1", "Không tìm thấy", "N/A", "N/A", "N/A", "N/A"
        ))
    
    def select_file(self):
        """Chọn file danh sách số điện thoại"""
        file_path = filedialog.askopenfilename(
            title="Chọn file danh sách số điện thoại",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            self.phone_file_path = file_path
            self.add_log(f"📁 Đã chọn file: {os.path.basename(file_path)}")
            
            # Tải danh sách số điện thoại
            if self.controller.load_phone_list(file_path):
                self.add_log("✅ Đã tải danh sách số điện thoại thành công!")
            else:
                self.add_log("❌ Không thể tải danh sách số điện thoại")
                messagebox.showerror("Lỗi", "Không thể tải file danh sách số điện thoại")
    
    def start_processing(self):
        """Bắt đầu quá trình xử lý"""
        if not self.phone_file_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file danh sách số điện thoại trước!")
            return
        
        if not self.controller.gsm_instances:
            messagebox.showerror("Lỗi", "Không có thiết bị GSM nào được kết nối!")
            return
        
        # Xóa kết quả cũ
        self.controller.clear_results()
        
        # Cập nhật trạng thái nút
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Bắt đầu xử lý
        self.controller.start_processing()
        self.add_log("🚀 Bắt đầu xử lý số điện thoại...")
    
    def stop_processing(self):
        """Dừng quá trình xử lý"""
        self.controller.stop_processing()
        
        # Cập nhật trạng thái nút
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
        self.add_log("🛑 Đã dừng xử lý")
    
    def export_results(self):
        """Xuất kết quả ra file Excel"""
        if not any(self.controller.results.values()):
            messagebox.showwarning("Cảnh báo", "Không có kết quả nào để xuất!")
            return
        
        # Chọn nơi lưu file
        file_path = filedialog.asksaveasfilename(
            title="Lưu kết quả Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if file_path:
            if self.controller.export_results(file_path):
                self.add_log(f"✅ Đã xuất kết quả ra: {os.path.basename(file_path)}")
                messagebox.showinfo("Thành công", f"Đã xuất kết quả ra file:\n{file_path}")
            else:
                self.add_log("❌ Không thể xuất kết quả")
                messagebox.showerror("Lỗi", "Không thể xuất kết quả ra file Excel")
    
    def add_log(self, message: str):
        """Thêm log vào text area"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
    
    def on_closing(self):
        """Xử lý khi đóng ứng dụng với shutdown dialog"""
        # Hỏi xác nhận trước khi thoát
        if messagebox.askyesno("Xác nhận thoát",
                               "Bạn có chắc chắn muốn thoát?\n\n"
                               "Hệ thống sẽ dừng xử lý và reset tất cả GSM instances."):
            self.show_shutdown_dialog()

    def show_shutdown_dialog(self):
        """Hiện shutdown dialog và thực hiện cleanup"""
        # Tạo shutdown dialog
        shutdown_dialog = tk.Toplevel(self.root)
        shutdown_dialog.title("Đang thoát...")
        shutdown_dialog.geometry("400x150")
        shutdown_dialog.resizable(False, False)

        # Center dialog
        shutdown_dialog.transient(self.root)
        shutdown_dialog.grab_set()

        # Frame chứa nội dung
        frame = ttk.Frame(shutdown_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Label thông báo
        label = ttk.Label(frame,
                         text="🔄 Đang dừng và reset các GSM instances...\nVui lòng đợi...",
                         font=('Arial', 11),
                         justify=tk.CENTER)
        label.pack(pady=10)

        # Progress bar
        progress = ttk.Progressbar(frame, mode='indeterminate', length=300)
        progress.pack(pady=10)
        progress.start(10)

        # Status label
        status_label = ttk.Label(frame,
                                text="Đang dừng xử lý...",
                                font=('Arial', 9),
                                foreground='#666')
        status_label.pack(pady=5)

        def update_status(message):
            """Cập nhật status label"""
            try:
                status_label.config(text=message)
            except:
                pass  # Dialog có thể đã bị đóng

        def shutdown_thread():
            """Thread thực hiện shutdown"""
            try:
                # Bước 1: Dừng xử lý nếu đang chạy
                if self.controller.is_running:
                    self.root.after(0, lambda: update_status("🛑 Đang dừng xử lý..."))
                    self.add_log("🛑 Đang dừng xử lý...")
                    self.controller.stop_processing()
                    self.add_log("✅ Đã dừng xử lý")

                # Bước 2: Reset cuối cùng tất cả GSM instances (song song)
                num_instances = len(self.controller.gsm_instances)
                if num_instances > 0:
                    self.root.after(0, lambda: update_status(f"🔄 Đang reset {num_instances} GSM instances..."))
                    self.add_log(f"🔄 Đang reset cuối cùng {num_instances} GSM instances...")
                    self.controller.final_reset_all_instances()
                    self.add_log("✅ Đã reset tất cả GSM instances")

                # Bước 3: Hoàn thành
                self.root.after(0, lambda: update_status("✅ Hoàn thành!"))
                self.add_log("✅ Đóng chương trình thành công!")

            except Exception as e:
                self.add_log(f"❌ Lỗi khi đóng chương trình: {e}")
                import traceback
                self.add_log(traceback.format_exc())

            finally:
                # Đóng shutdown dialog và main window
                self.root.after(500, shutdown_dialog.destroy)
                self.root.after(600, self.root.destroy)

        # Bắt đầu thread shutdown
        threading.Thread(target=shutdown_thread, daemon=True).start()

def main():
    root = tk.Tk()
    app = AudioClassificationGUI(root)
    
    # Xử lý đóng ứng dụng
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()
