import customtkinter as ctk
import threading
import time
import os
import json
import requests
import random
import base64

from tkinter import messagebox, filedialog, BooleanVar
from PIL import Image, ImageOps

from seleniumbase import Driver
from selenium.webdriver.common.by import By  # để sẵn nếu sau này cần

# ================= CONFIG =================
TARGET_URL = "https://labs.google/fx/vi/tools/flow"
COOKIES_FILE = "profile_cookies.json"
DEFAULT_OUTPUT_FOLDER = "Output_Images"

if not os.path.exists(DEFAULT_OUTPUT_FOLDER):
    os.makedirs(DEFAULT_OUTPUT_FOLDER)

try:
    from config import MANUAL_AUTH, PROJECT_ID
except ImportError:
    MANUAL_AUTH = ""
    PROJECT_ID = ""

MODEL_MAP = {
    "Nano Banana Pro": "GEM_PIX_2",
    "Nano Banana": "GEM_PIX",
    "Imagen 4": "IMAGEN_3_5",
}

RATIO_MAP = {
    "Khổ ngang (16:9)": "IMAGE_ASPECT_RATIO_LANDSCAPE",
    "Khổ dọc (9:16)": "IMAGE_ASPECT_RATIO_PORTRAIT",
}

STYLE_MAP = {
    "Không áp dụng": "",
    "Điện ảnh (Cinematic)": (
        "Cinematic photography style, detailed, high dynamic range, "
        "soft lighting, rich colors, filmic look."
    ),
    "Truyện tranh": (
        "Comic book style illustration, bold outlines, flat shading, "
        "vibrant colors, dynamic composition."
    ),
    "Minh họa fantasy": (
        "Fantasy illustration style, epic, dramatic lighting, "
        "high detail, magical atmosphere."
    ),
    "Phong cách anime": (
        "Anime style illustration, clean lines, expressive eyes, "
        "smooth shading, vibrant colors."
    ),
}

# ================ THEME SETTINGS =================
APP_BG = "#0f172a"
CARD_BG = "#111827"
SUBTLE_BG = "#1f2937"
BORDER_COLOR = "#1f2937"
PRIMARY_COLOR = "#2563eb"
SUCCESS_COLOR = "#22c55e"
WARNING_COLOR = "#f59e0b"
ERROR_COLOR = "#ef4444"
TEXT_MUTED = "#9ca3af"
FONT_BASE = ("Inter", 12)

# ================= ROW WIDGET =================


class StatusRow(ctk.CTkFrame):
    """
    Một dòng trong bảng kết quả.
    Thay đổi: Thêm màu nền xen kẽ (zebra striping) để dễ nhìn.
    """
    def __init__(self, parent, index, prompt_text, app_ref):
        # MÀU NỀN XEN KẼ: Dòng chẵn màu tối hơn chút, dòng lẻ trong suốt
        bg_color = SUBTLE_BG if index % 2 == 0 else CARD_BG
        super().__init__(
            parent,
            fg_color=bg_color,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        self.index = index
        self.prompt_text = prompt_text
        self.app = app_ref

        self.thumb_image = None
        self.current_image_path = None
        self.is_error = False
        self.selected_var = BooleanVar(value=False)

        # Cấu hình grid layout cho dòng này
        self.grid_columnconfigure(0, weight=0, minsize=30)  # Checkbox
        self.grid_columnconfigure(1, weight=0, minsize=40)  # STT
        self.grid_columnconfigure(2, weight=0, minsize=100) # Trạng thái
        self.grid_columnconfigure(3, weight=1)              # Prompt (giãn tối đa)
        self.grid_columnconfigure(4, weight=0, minsize=180) # Tiến độ/Kết quả

        # ----- Cột 0: checkbox -----
        self.chk_select = ctk.CTkCheckBox(
            self, text="", width=20, variable=self.selected_var
        )
        self.chk_select.grid(row=0, column=0, padx=(8, 4), pady=8, sticky="w")

        # ----- Cột 1: STT -----
        self.lbl_stt = ctk.CTkLabel(
            self, text=f"{index:03d}", width=30, font=("Inter", 12, "bold"), text_color=TEXT_MUTED
        )
        self.lbl_stt.grid(row=0, column=1, padx=4, pady=8, sticky="w")

        # ----- Cột 2: Trạng thái -----
        self.lbl_status = ctk.CTkLabel(
            self, text="Sẵn sàng", text_color=TEXT_MUTED, width=90, anchor="w", font=FONT_BASE
        )
        self.lbl_status.grid(row=0, column=2, padx=4, pady=8, sticky="w")

        # ----- Cột 3: Prompt + nút Sửa -----
        prompt_frame = ctk.CTkFrame(self, fg_color="transparent")
        prompt_frame.grid(row=0, column=3, padx=4, pady=8, sticky="ew")
        prompt_frame.grid_columnconfigure(0, weight=1)

        short = prompt_text if len(prompt_text) <= 60 else prompt_text[:60] + "..."
        self.lbl_prompt = ctk.CTkLabel(
            prompt_frame, text=short, anchor="w", justify="left", font=FONT_BASE
        )
        self.lbl_prompt.grid(row=0, column=0, sticky="ew")

        self.btn_edit = ctk.CTkButton(
            prompt_frame, text="✏", width=28, height=28,
            command=self.on_edit_clicked, fg_color=PRIMARY_COLOR, hover_color="#1d4ed8"
        )
        self.btn_edit.grid(row=0, column=1, padx=(4, 0))

        # ----- Cột 4: Tiến độ / Kết quả -----
        # Container cho progress bar
        self.progress_container = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_container.grid(row=0, column=4, padx=(4, 8), pady=8, sticky="e")
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_container, width=120, height=10, fg_color=CARD_BG, progress_color=PRIMARY_COLOR
        )
        self.progress_bar.grid(row=0, column=0, padx=(0, 4))
        self.progress_bar.set(0)
        self.lbl_percent = ctk.CTkLabel(self.progress_container, text="0%", width=30, font=FONT_BASE)
        self.lbl_percent.grid(row=0, column=1)

        # Container cho kết quả (thumbnail)
        self.result_container = ctk.CTkFrame(self, fg_color="transparent")
        self.thumb_label = ctk.CTkLabel(
            self.result_container, text="", width=140, height=78, fg_color=CARD_BG
        )  # Tỷ lệ 16:9 nhỏ
        self.thumb_label.grid(row=0, column=0, padx=(0, 4))
        
        self.btn_regen_small = ctk.CTkButton(
            self.result_container, text="↻", width=26, height=26,
            command=self.on_regen_clicked, fg_color=PRIMARY_COLOR, hover_color="#1d4ed8"
        )
        self.btn_regen_small.grid(row=0, column=1)

        # Ẩn ban đầu
        self.progress_container.grid_remove()
        self.result_container.grid_remove()

    # ... (GIỮ NGUYÊN CÁC HÀM start_render, update_progress, finish_success... BÊN DƯỚI) ...
    # ... (Chỉ cần đảm bảo copy lại các hàm tiện ích đó vào trong class này) ...

    # ----- Tiện ích -----
    def is_selected(self) -> bool:
        return bool(self.selected_var.get())

    def set_selected(self, value: bool):
        self.selected_var.set(value)

    # ----- API cho App -----
    def set_status(self, text, color="white"):
        self.lbl_status.configure(text=text, text_color=color)

    def start_render(self, round_no=1):
        self.is_error = False
        self.set_status(f"Đang render (v{round_no})...", "#e67e22")
        self.current_image_path = None

        # hiển thị mode progress
        self.result_container.grid_remove()
        self.thumb_label.configure(image=None, text="")
        self.progress_container.grid(row=0, column=4, padx=6, pady=(4, 0), sticky="e")

        self.progress_bar.set(0.1)
        self.lbl_percent.configure(text="10%")

    def update_progress(self, p: float):
        p = max(0.0, min(1.0, p))
        self.progress_bar.set(p)
        self.lbl_percent.configure(text=f"{int(p * 100)}%")

    def finish_success(self, image_path):
        self.is_error = False
        self.set_status("Hoàn thành", "#2ecc71")

        # chuẩn bị thumbnail 16:9
        self.current_image_path = image_path
        try:
            img = Image.open(image_path)
            img = ImageOps.fit(img, (160, 90), Image.LANCZOS)
            self.thumb_image = ctk.CTkImage(img, size=(160, 90))
            self.thumb_label.configure(image=self.thumb_image, text="")
            self.thumb_label.bind("<Button-1>", lambda e: self.open_full_image())
        except Exception:
            self.thumb_label.configure(text="Xem ảnh lỗi", image=None)

        # chuyển sang mode result (thumbnail + regen nhỏ)
        self.progress_container.grid_remove()
        self.result_container.grid(row=0, column=4, padx=6, pady=(4, 0), sticky="e")

    def finish_error(self, msg="Lỗi"):
        self.is_error = True
        self.set_status(msg, "#e74c3c")

        self.current_image_path = self.current_image_path or None
        self.thumb_label.configure(text="Lỗi", image=None)
        self.thumb_label.unbind("<Button-1>")

        self.progress_container.grid_remove()
        self.result_container.grid(row=0, column=4, padx=6, pady=(4, 0), sticky="e")

    def open_full_image(self):
        if not self.current_image_path:
            return
        top = ctk.CTkToplevel(self)
        top.title(f"Xem ảnh #{self.index:03d}")
        try:
            img = Image.open(self.current_image_path)
            w, h = img.size
            max_w, max_h = 900, 900
            scale = min(max_w / w, max_h / h, 1.0)
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size)
            big = ctk.CTkImage(img, size=new_size)
            lbl = ctk.CTkLabel(top, image=big, text="")
            lbl.image = big
            lbl.pack(padx=10, pady=10)
        except Exception as e:
            ctk.CTkLabel(top, text=f"Lỗi mở ảnh: {e}").pack(padx=10, pady=10)

    def on_edit_clicked(self):
        top = ctk.CTkToplevel(self)
        top.title(f"Sửa prompt #{self.index:03d}")

        txt = ctk.CTkTextbox(top, width=520, height=180)
        txt.pack(padx=10, pady=10)
        txt.insert("1.0", self.prompt_text)

        def save():
            new_p = txt.get("1.0", "end").strip()
            if new_p:
                self.prompt_text = new_p
                short = new_p if len(new_p) <= 80 else new_p[:80] + "..."
                self.lbl_prompt.configure(text=short)
            top.destroy()

        ctk.CTkButton(top, text="Lưu", command=save).pack(pady=(0, 10))

    def on_regen_clicked(self):
        # regen 1 dòng (ghi đè ảnh nếu có)
        if self.app:
            self.app.regenerate_single(self.index, self.prompt_text)


# ================= MAIN APP =================


class AutoGenApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Flow Labs API Pure (V18.1 - UI Revamp)")
        self.geometry("1350x800")
        # KHÔNG cho kéo nhỏ hơn kích thước này
        self.minsize(1200, 720)
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color=APP_BG)

        self.session = requests.Session()
        self.cookies_loaded = False
        self.project_id = None
        self.tool_name = "PINHOLE"
        self.is_running = False
        self.rows = {}
        self.output_folder = DEFAULT_OUTPUT_FOLDER

        self.setup_ui()
        self.load_cookies_to_session()

    # ---------- UI ----------
    def setup_ui(self):
        # 3 cột: trái (prompt + cài đặt), giữa (nhân vật gốc), phải (kết quả)
        self.grid_columnconfigure(0, weight=2, minsize=380)
        self.grid_columnconfigure(1, weight=1, minsize=260)
        self.grid_columnconfigure(2, weight=3, minsize=520)
        self.grid_rowconfigure(0, weight=1)

        # ===== LEFT PANEL =====
        left = ctk.CTkScrollableFrame(self, fg_color=APP_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        left.grid_columnconfigure(0, weight=1)

        # --- Prompts tạo ảnh ---
        group_prompts = ctk.CTkFrame(
            left,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        group_prompts.grid(row=0, column=0, sticky="nsew", padx=4, pady=(0, 10))
        group_prompts.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            group_prompts, text="Prompts tạo ảnh", font=("Inter", 14, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        hint = "TỐI ĐA 300 PROMPTS, cứ XUỐNG DÒNG là 1 prompt mới..."
        self.txt_prompts = ctk.CTkTextbox(
            group_prompts, height=260, font=FONT_BASE, fg_color=SUBTLE_BG
        )
        self.txt_prompts.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.txt_prompts.insert("1.0", hint)

        # --- Cài đặt ---
        group_settings = ctk.CTkFrame(
            left,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        group_settings.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 10))
        group_settings.grid_columnconfigure(0, weight=1)
        group_settings.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            group_settings, text="Cài đặt", font=("Inter", 14, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 8))

        # Phong cách
        ctk.CTkLabel(
            group_settings, text="Phong cách:", anchor="w", font=FONT_BASE
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(2, 0))
        self.combo_style = ctk.CTkComboBox(
            group_settings, values=list(STYLE_MAP.keys()), width=200
        )
        self.combo_style.set("Điện ảnh (Cinematic)")
        self.combo_style.grid(row=2, column=0, sticky="we", padx=12, pady=(0, 8))

        # Tỷ lệ
        ctk.CTkLabel(
            group_settings, text="Tỷ lệ ảnh:", anchor="w", font=FONT_BASE
        ).grid(row=1, column=1, sticky="w", padx=12, pady=(2, 0))
        self.combo_ratio = ctk.CTkComboBox(
            group_settings, values=list(RATIO_MAP.keys()), width=200
        )
        self.combo_ratio.set("Khổ ngang (16:9)")
        self.combo_ratio.grid(row=2, column=1, sticky="we", padx=12, pady=(0, 8))

        # Nơi lưu
        ctk.CTkLabel(
            group_settings, text="Thư mục lưu ảnh:", anchor="w", font=FONT_BASE
        ).grid(row=3, column=0, sticky="w", padx=12, pady=(2, 0))
        folder_frame = ctk.CTkFrame(group_settings, fg_color="transparent")
        folder_frame.grid(
            row=4, column=0, columnspan=2, sticky="we", padx=12, pady=(0, 8)
        )
        folder_frame.grid_columnconfigure(0, weight=1)

        self.lbl_folder = ctk.CTkLabel(
            folder_frame, text=self.output_folder, anchor="w", font=FONT_BASE
        )
        self.lbl_folder.grid(row=0, column=0, sticky="we")

        ctk.CTkButton(
            folder_frame,
            text="Chọn nơi lưu",
            width=140,
            fg_color=PRIMARY_COLOR,
            hover_color="#1d4ed8",
            command=self.choose_output_folder,
        ).grid(row=0, column=1, padx=(8, 0))

        # Model
        ctk.CTkLabel(
            group_settings, text="Model:", anchor="w", font=FONT_BASE
        ).grid(row=5, column=0, sticky="w", padx=12, pady=(2, 0))
        self.combo_model = ctk.CTkComboBox(
            group_settings, values=list(MODEL_MAP.keys()), width=200
        )
        self.combo_model.set("Nano Banana Pro")
        self.combo_model.grid(row=6, column=0, sticky="we", padx=12, pady=(0, 8))

        # Trạng thái cookie (hiện ở góc)
        self.lbl_auth_status = ctk.CTkLabel(
            group_settings, text="Cookie: Chưa có", text_color=TEXT_MUTED, font=FONT_BASE
        )
        self.lbl_auth_status.grid(row=6, column=1, sticky="e", padx=12, pady=(0, 8))

        # --- Điều khiển + Log ---
        group_control = ctk.CTkFrame(
            left,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        group_control.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 4))
        group_control.grid_columnconfigure(0, weight=1)
        group_control.grid_rowconfigure(1, weight=1)

        # nút login
        self.btn_login = ctk.CTkButton(
            group_control,
            text="Đăng nhập & Lấy Cookie",
            height=36,
            fg_color=WARNING_COLOR,
            hover_color="#d97706",
            command=self.manual_login,
        )
        self.btn_login.grid(row=0, column=0, sticky="we", padx=8, pady=(6, 4))

        # nút bắt đầu
        self.btn_start = ctk.CTkButton(
            group_control,
            text="🚀 Bắt đầu tạo ảnh",
            height=40,
            fg_color=SUCCESS_COLOR,
            hover_color="#16a34a",
            state="disabled",
            command=self.start_batch,
        )
        self.btn_start.grid(row=0, column=1, sticky="we", padx=8, pady=(6, 4))

        # log
        ctk.CTkLabel(
            group_control, text="LOG HỆ THỐNG:", anchor="w", font=FONT_BASE
        ).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8
        )
        self.txt_log = ctk.CTkTextbox(
            group_control, height=120, font=("Consolas", 10), fg_color=SUBTLE_BG
        )
        self.txt_log.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=(2, 8))

        # ===== MIDDLE PANEL: Nhân vật gốc =====
        middle = ctk.CTkScrollableFrame(self, fg_color=APP_BG)
        middle.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=12)
        middle.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            middle, text="Nhân vật gốc", font=("Inter", 14, "bold")
        ).grid(row=0, column=0, padx=4, pady=(0, 8), sticky="w")

        # dùng ScrollableFrame để chứa 10 slot xếp 2 cột cho gọn
        slots_frame = ctk.CTkFrame(
            middle,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        slots_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        slots_frame.grid_columnconfigure((0, 1), weight=1)

        for i in range(10):
            row = i // 2
            col = i % 2
            slot = ctk.CTkFrame(
                slots_frame,
                fg_color=SUBTLE_BG,
                corner_radius=10,
                border_width=1,
                border_color=BORDER_COLOR,
            )
            slot.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            slot.grid_columnconfigure(0, weight=1)

            btn = ctk.CTkButton(
                slot,
                text=f"Chọn ảnh/bối cảnh #{i+1}",
                height=36,
                fg_color=PRIMARY_COLOR,
                hover_color="#1d4ed8",
            )
            btn.grid(row=0, column=0, sticky="we", padx=8, pady=(8, 4))

            entry = ctk.CTkEntry(
                slot,
                placeholder_text="Tên nhân vật / bối cảnh...",
                font=FONT_BASE,
            )
            entry.grid(row=1, column=0, sticky="we", padx=8, pady=(0, 8))

        # ===== RIGHT PANEL: Kết quả tạo ảnh =====
        right = ctk.CTkFrame(
            self,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        right.grid(row=0, column=2, sticky="nsew", padx=(0, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        # thanh tiêu đề + nút chức năng
        title_bar = ctk.CTkFrame(right, fg_color="transparent")
        title_bar.grid(row=0, column=0, sticky="we", padx=12, pady=(12, 6))
        title_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_bar,
            text="Kết quả tạo ảnh (Click thumbnail để zoom)",
            font=("Inter", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")

        # nút góc phải
        btn_bar = ctk.CTkFrame(title_bar, fg_color="transparent")
        btn_bar.grid(row=0, column=1, sticky="e")

        self.btn_regen_selected = ctk.CTkButton(
            btn_bar,
            text="Tạo lại ảnh",
            height=32,
            fg_color=PRIMARY_COLOR,
            hover_color="#1d4ed8",
            state="disabled",
            command=self.regenerate_selected,
        )
        self.btn_regen_selected.grid(row=0, column=0, padx=(0, 6))

        self.btn_regen_failed = ctk.CTkButton(
            btn_bar,
            text="Tạo lại ảnh lỗi",
            height=32,
            fg_color=WARNING_COLOR,
            hover_color="#d97706",
            state="disabled",
            command=self.regenerate_failed,
        )
        self.btn_regen_failed.grid(row=0, column=1, padx=(0, 6))

        self.btn_delete_rows = ctk.CTkButton(
            btn_bar,
            text="Xóa",
            height=32,
            fg_color=ERROR_COLOR,
            hover_color="#dc2626",
            state="disabled",
            command=self.delete_selected_rows,
        )
        self.btn_delete_rows.grid(row=0, column=2)

        # header bảng
        self.header_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.header_frame.grid(row=1, column=0, sticky="we", padx=12, pady=(0, 4))

        self.build_header_row()

        # separator dưới header (line đậm hơn)
        self.header_separator = ctk.CTkFrame(right, height=1, fg_color=BORDER_COLOR)
        self.header_separator.grid(row=2, column=0, sticky="we", padx=12, pady=(0, 6))

        # danh sách dòng
        self.right_list = ctk.CTkScrollableFrame(right, fg_color=SUBTLE_BG)
        self.right_list.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def build_header_row(self):
        header = self.header_frame

        ctk.CTkLabel(header, text="", width=30).grid(row=0, column=0, padx=(4, 4))
        ctk.CTkLabel(
            header, text="STT", width=40, anchor="w", font=("Inter", 12, "bold")
        ).grid(row=0, column=1, padx=2, sticky="w")

        ctk.CTkLabel(
            header, text="Trạng thái", width=120, anchor="w", font=("Inter", 12, "bold")
        ).grid(row=0, column=2, padx=2, sticky="w")

        ctk.CTkLabel(
            header,
            text="Prompt",
            anchor="w",
            font=("Inter", 12, "bold"),
        ).grid(row=0, column=3, padx=2, sticky="w")

        ctk.CTkLabel(
            header,
            text="Tiến độ",
            anchor="w",
            font=("Inter", 12, "bold"),
        ).grid(row=0, column=4, padx=6, sticky="e")

    # ---------- LOG ----------
    def log(self, msg):
        print(msg)
        try:
            self.txt_log.insert("end", msg + "\n")
            self.txt_log.see("end")
        except Exception:
            pass

    # ---------- AUTH ----------
    def manual_login(self):
        threading.Thread(target=self._login_thread, daemon=True).start()

    def _login_thread(self):
        self.log("🚀 Đang khởi động trình duyệt (Chế độ Native CDP)...")
        
        try:
            import undetected_chromedriver as uc
            import json
            import time
            
            # 1. Cấu hình Chrome đọc log mạng
            options = uc.ChromeOptions()
            options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
            
            # 2. Mở trình duyệt
            driver = uc.Chrome(options=options, headless=False)
            
            self.log("🌍 Đang vào Labs Google...")
            driver.get(TARGET_URL)
            
            # --- SỬA ĐỔI: LOGIC CHỜ THÔNG MINH ---
            # Thay vì check URL ngay, ta chờ 5 giây để xem nó có redirect không
            time.sleep(5) 
            
            found_token = None
            
            # Thử quét nhanh 1 vòng xem có token luôn không (nếu cookie cũ còn sống)
            self.log("dang quét sơ bộ...")
            logs = driver.get_log("performance")
            found_token = self._scan_logs_for_token(logs)

            # Nếu CHƯA có token, bắt buộc hiện bảng thông báo để người dùng thao tác
            if not found_token:
                self.log("⚠️ Chưa thấy token tự động. Đang chờ người dùng thao tác...")
                
                # Bảng này sẽ BLOCK code lại, trình duyệt sẽ không tắt cho đến khi bạn bấm OK
                messagebox.showinfo(
                    "Yêu cầu thủ công", 
                    "1. Hãy đăng nhập Google trên cửa sổ Chrome vừa mở.\n"
                    "2. Chờ trang Flow Labs tải xong giao diện (hiện ô nhập prompt).\n"
                    "3. SAU KHI TẢI XONG HẾT thì mới bấm OK ở đây."
                )
                
                # Sau khi bấm OK, quét lại lần nữa
                self.log("🔄 Đang quét lại log sau khi người dùng bấm OK...")
                logs = driver.get_log("performance")
                found_token = self._scan_logs_for_token(logs)

            # --- LƯU COOKIE ---
            self.log("🍪 Đang lưu Cookie...")
            try:
                cookies = driver.get_cookies()
                with open(COOKIES_FILE, "w") as f:
                    json.dump(cookies, f)
            except Exception as e:
                self.log(f"Lỗi lưu cookie: {e}")

            driver.quit()

            # --- KẾT QUẢ ---
            if found_token:
                self.log(f"✅ BẮT ĐƯỢC TOKEN: {found_token[:20]}...")
                with open("token.txt", "w") as f:
                    f.write(found_token)
                
                self.manual_auth_token = found_token
                self.load_cookies_to_session() # Update UI
            else:
                self.log("❌ Vẫn không tìm thấy Token! Hãy thử F5 trang web rồi bấm Login lại.")

        except Exception as e:
            self.log(f"❌ Lỗi: {e}")
            try:
                driver.quit()
            except:
                pass

    # Hàm phụ trợ để quét log cho gọn
    def _scan_logs_for_token(self, logs):
        import json
        for entry in logs:
            try:
                obj = json.loads(entry.get("message"))
                message = obj.get("message")
                method = message.get("method")
                if method == "Network.requestWillBeSent":
                    params = message.get("params")
                    request = params.get("request")
                    url = request.get("url")
                    if "googleapis.com" in url or "labs.google" in url:
                        headers = request.get("headers")
                        auth = headers.get("Authorization")
                        if auth and "Bearer" in auth:
                            return auth
            except:
                continue
        return None

    def load_cookies_to_session(self):
        # 1. Nạp Cookie (Code cũ giữ nguyên)
        if not os.path.exists(COOKIES_FILE):
            return
        try:
            with open(COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            self.session = requests.Session()
            for c in cookies:
                self.session.cookies.set(c["name"], c["value"], domain=c["domain"])

            # Setup Header giả lập Chrome
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Origin": "https://labs.google",
                "Referer": "https://labs.google/fx/vi/tools/flow",
            })
            
            self.cookies_loaded = True
        except Exception as e:
            self.log(f"Lỗi nạp cookie: {e}")

        # 2. NẠP TOKEN TỪ FILE (PHẦN MỚI THÊM VÀO) ---
        self.manual_auth_token = ""
        if os.path.exists("token.txt"):
            try:
                with open("token.txt", "r") as f:
                    self.manual_auth_token = f.read().strip()
                self.log(f"Đã nạp Token từ file token.txt: {self.manual_auth_token[:15]}...")
            except Exception as e:
                self.log(f"Lỗi đọc token.txt: {e}")
        # ---------------------------------------------

        # 3. Cập nhật trạng thái UI
        if self.cookies_loaded and self.manual_auth_token:
            self.lbl_auth_status.configure(text="Auth: Full (OK)", text_color=SUCCESS_COLOR)  # Xanh lá
            self.btn_start.configure(state="normal", fg_color=SUCCESS_COLOR)
        elif self.cookies_loaded:
            self.lbl_auth_status.configure(text="Auth: Thiếu Token", text_color=WARNING_COLOR)  # Vàng
        else:
            self.lbl_auth_status.configure(text="Chưa có gì", text_color="gray")

    # ---------- Thư mục lưu ----------
    def choose_output_folder(self):
        path = filedialog.askdirectory()
        if not path:
            return
        self.output_folder = path
        self.lbl_folder.configure(text=path)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        self.log(f"Đã chọn thư mục lưu: {path}")

    # ---------- UI HELPERS (chạy trên main thread) ----------
    def ui_start_render(self, row, round_no):
        self.after(0, lambda: row.start_render(round_no))

    def ui_update_progress(self, row, p):
        self.after(0, lambda: row.update_progress(p))

    def ui_finish_success(self, row, path):
        def fn():
            row.update_progress(1.0)
            row.finish_success(path)

        self.after(0, fn)

    def ui_finish_error(self, row, msg):
        self.after(0, lambda: row.finish_error(msg))

    # ---------- AUTH HEADER GOOGLEAPIS ----------
    def build_googleapis_auth_headers(self):
        headers = {}
        
        # 1. Ưu tiên số 1: Dùng Token động vừa bắt được
        if hasattr(self, 'manual_auth_token') and self.manual_auth_token:
            headers["Authorization"] = self.manual_auth_token
            # self.log("Dùng Token Bearer động.")
            return headers
            
        # 2. Ưu tiên số 2: Tìm trong file token.txt (phòng khi biến bị reset)
        if os.path.exists("token.txt"):
            with open("token.txt", "r") as f:
                token = f.read().strip()
            if token:
                headers["Authorization"] = token
                return headers

        # 3. Ưu tiên cuối: Dùng Config cứng (Code cũ)
        if MANUAL_AUTH and str(MANUAL_AUTH).strip():
            headers["Authorization"] = MANUAL_AUTH.strip()
            self.log("Dùng Authorization từ Config cũ.")
            return headers
            
        # Nếu chạy đến đây là Lỗi
        self.log("CẢNH BÁO: Không tìm thấy bất kỳ Token nào để gửi request!")
        return headers

    # ---------- UTILS ----------
    @staticmethod
    def _collect_encoded_images(obj, out_list):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "encodedImage" and isinstance(v, str):
                    out_list.append(v)
                else:
                    AutoGenApp._collect_encoded_images(v, out_list)
        elif isinstance(obj, list):
            for item in obj:
                AutoGenApp._collect_encoded_images(item, out_list)

    # ---------- START BATCH ----------
    def start_batch(self):
        if self.is_running:
            return
        raw_text = self.txt_prompts.get("1.0", "end")
        prompts = [p.strip() for p in raw_text.split("\n") if p.strip()]
        if not prompts:
            messagebox.showwarning("Thiếu prompt", "Bạn chưa nhập prompt nào.")
            return

        # xóa dòng cũ
        for w in self.right_list.winfo_children():
            w.destroy()
        self.rows = {}

        # tạo row mới
        jobs = []
        for i, p in enumerate(prompts):
            idx = i + 1
            row = StatusRow(self.right_list, idx, p, app_ref=self)
            row.grid(row=i, column=0, sticky="we", padx=2, pady=0)
            self.rows[idx] = row
            jobs.append((idx, p))

        self.btn_regen_selected.configure(state="normal")
        self.btn_regen_failed.configure(state="normal")
        self.btn_delete_rows.configure(state="normal")

        threading.Thread(
            target=self.run_jobs, args=(jobs, False), daemon=True
        ).start()

    # ---------- GỬI 1 PROMPT ----------
    def _generate_once(self, idx: int, prompt: str, round_no: int, overwrite_existing: bool) -> bool:
        row = self.rows.get(idx)
        if not row:
            return False

        self.ui_start_render(row, round_no)

        self.project_id = PROJECT_ID
        if not self.project_id:
            self.ui_finish_error(row, "Thiếu PROJECT_ID")
            self.log("PROJECT_ID trống trong config.py")
            return False

        gen_url = (
            f"https://aisandbox-pa.googleapis.com/v1/projects/"
            f"{self.project_id}/flowMedia:batchGenerateImages"
        )

        client_session = f";{int(time.time() * 1000)}"

        # model & aspect ratio từ combobox
        model_name = MODEL_MAP.get(self.combo_model.get(), "GEM_PIX")
        aspect_ratio = RATIO_MAP.get(
            self.combo_ratio.get(), "IMAGE_ASPECT_RATIO_LANDSCAPE"
        )

        # phong cách
        style_key = self.combo_style.get()
        style_text = STYLE_MAP.get(style_key, "").strip()
        final_prompt = f"{style_text}. {prompt}" if style_text else prompt

        payload = {
            "requests": [
                {
                    "clientContext": {"sessionId": client_session},
                    "seed": random.randint(100000, 999999),
                    "imageModelName": model_name,
                    "imageAspectRatio": aspect_ratio,
                    "prompt": final_prompt,
                    "imageInputs": [],
                }
            ]
        }

        try:
            custom_headers = {
                "Content-Type": "text/plain;charset=UTF-8",
                "User-Agent": self.session.headers.get("User-Agent", ""),
                "Referer": "https://labs.google/",
            }
            custom_headers.update(self.build_googleapis_auth_headers())

            resp = self.session.post(gen_url, json=payload, headers=custom_headers)

            if resp.status_code == 200:
                body = resp.text
                self.log(f"P{idx} (v{round_no}): body (rút gọn):")
                self.log(body[:300])

                try:
                    data = resp.json()
                except Exception as e:
                    self.ui_finish_error(row, "JSON lỗi")
                    self.log(f"P{idx}: Lỗi parse JSON (v{round_no}): {e}")
                    return False

                encoded_list = []
                self._collect_encoded_images(data, encoded_list)
                if not encoded_list:
                    self.ui_finish_error(row, "Không thấy encodedImage")
                    self.log(
                        f"P{idx}: 200 OK nhưng không có encodedImage (v{round_no})."
                    )
                    return False

                encoded = encoded_list[0]
                try:
                    img_data = base64.b64decode(encoded)
                except Exception as e:
                    self.ui_finish_error(row, "Lỗi decode base64")
                    self.log(f"P{idx}: Lỗi decode base64 (v{round_no}): {e}")
                    return False

                # xác định đường dẫn lưu (có thể ghi đè)
                save_path = None
                if overwrite_existing and row.current_image_path:
                    save_path = row.current_image_path

                if not save_path:
                    p_short = prompt[:15].strip().replace(" ", "_")
                    fname = f"{idx:03d}_{p_short}_{int(time.time())}.png"
                    save_path = os.path.join(self.output_folder, fname)

                try:
                    with open(save_path, "wb") as f:
                        f.write(img_data)
                    self.ui_finish_success(row, save_path)
                    self.log(
                        f"P{idx}: OK (v{round_no}) - đã lưu {os.path.basename(save_path)}"
                    )
                    return True
                except Exception as e:
                    self.ui_finish_error(row, "Lỗi ghi file")
                    self.log(f"P{idx}: Lỗi ghi file (v{round_no}): {e}")
                    return False

            elif resp.status_code == 429:
                self.ui_finish_error(row, "429 (Rate limit)")
                self.log(
                    f"P{idx}: Rate limit 429 (v{round_no}), chờ 2s rồi chuyển prompt."
                )
                time.sleep(2.0)
                return False

            else:
                self.ui_finish_error(row, f"Lỗi API {resp.status_code}")
                self.log(
                    f"P{idx}: Lỗi API {resp.status_code} (v{round_no}): {resp.text[:200]}"
                )
                return False

        except Exception as e:
            self.ui_finish_error(row, "Exception")
            self.log(f"P{idx}: Exception (v{round_no}): {e}")
            return False

    # ---------- WORKFLOW 3 VÒNG ----------
    def run_jobs(self, jobs, overwrite_existing: bool):
        self.is_running = True

        # disable nút
        self.btn_start.configure(state="disabled")
        self.btn_regen_selected.configure(state="disabled")
        self.btn_regen_failed.configure(state="disabled")
        self.btn_delete_rows.configure(state="disabled")

        MAX_ROUNDS = 3
        SLEEP_BETWEEN_PROMPTS = 0.3

        pending = list(jobs)
        for round_no in range(1, MAX_ROUNDS + 1):
            if not pending or not self.is_running:
                break
            self.log(f"=== VÒNG {round_no}: xử lý {len(pending)} prompt ===")
            new_pending = []
            for idx, prompt in pending:
                if not self.is_running:
                    break
                ok = self._generate_once(idx, prompt, round_no, overwrite_existing)
                if not ok:
                    new_pending.append((idx, prompt))
                time.sleep(SLEEP_BETWEEN_PROMPTS)
            pending = new_pending

        if pending:
            self.log(
                f"--- CÒN {len(pending)} PROMPT LỖI SAU {MAX_ROUNDS} VÒNG. ĐÃ ĐÁNH DẤU LỖI CUỐI CÙNG ---"
            )
            for idx, prompt in pending:
                row = self.rows.get(idx)
                if row:
                    self.ui_finish_error(row, "Lỗi sau 3 lần")

            try:
                self.txt_prompts.delete("1.0", "end")
                self.txt_prompts.insert("1.0", "\n".join(p for _, p in pending))
            except Exception:
                pass

            try:
                with open(
                    "failed_prompts_after_3_rounds.txt", "w", encoding="utf-8"
                ) as f:
                    for _, p in pending:
                        f.write(p + "\n")
                self.log(
                    "Đã lưu danh sách prompt lỗi cuối vào failed_prompts_after_3_rounds.txt"
                )
            except Exception as e:
                self.log(f"Lỗi khi lưu failed_prompts_after_3_rounds.txt: {e}")
        else:
            self.log(f"Tất cả prompt đã xong trong <= {MAX_ROUNDS} vòng.")

        self.is_running = False

        # enable lại nút
        if self.cookies_loaded:
            self.btn_start.configure(state="normal", fg_color="#27ae60")
        else:
            self.btn_start.configure(state="disabled")

        if self.rows:
            self.btn_regen_selected.configure(state="normal")
            self.btn_regen_failed.configure(state="normal")
            self.btn_delete_rows.configure(state="normal")
        else:
            self.btn_regen_selected.configure(state="disabled")
            self.btn_regen_failed.configure(state="disabled")
            self.btn_delete_rows.configure(state="disabled")

        self.log("--- HOÀN TẤT ---")

    # ---------- TẠO LẠI 1 DÒNG ----------
    def regenerate_single(self, index, prompt):
        if self.is_running:
            self.log("Đang chạy batch, không thể Tạo lại từng dòng.")
            return

        def worker():
            MAX_ROUNDS = 3
            for round_no in range(1, MAX_ROUNDS + 1):
                ok = self._generate_once(index, prompt, round_no, True)
                if ok:
                    break
                time.sleep(0.5)

        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_regen_selected.configure(state="disabled")
        self.btn_regen_failed.configure(state="disabled")
        self.btn_delete_rows.configure(state="disabled")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        def wait_done():
            t.join()
            self.is_running = False
            if self.cookies_loaded:
                self.btn_start.configure(state="normal", fg_color="#27ae60")
            self.btn_regen_selected.configure(state="normal")
            self.btn_regen_failed.configure(state="normal")
            self.btn_delete_rows.configure(state="normal")

        threading.Thread(target=wait_done, daemon=True).start()

    # ---------- TẠO LẠI ẢNH ĐƯỢC CHỌN (GHI ĐÈ) ----------
    def regenerate_selected(self):
        if self.is_running:
            self.log("Đang chạy batch, không thể Tạo lại ảnh.")
            return

        jobs = []
        for idx, row in self.rows.items():
            if row.is_selected():
                jobs.append((idx, row.prompt_text))

        if not jobs:
            messagebox.showinfo("Chú ý", "Bạn chưa chọn ảnh nào để tạo lại.")
            return

        if not messagebox.askyesno(
            "Xác nhận",
            "Tạo lại các ảnh đã chọn?\nẢnh mới sẽ ghi đè lên file cũ (nếu có).",
        ):
            return

        threading.Thread(
            target=self.run_jobs, args=(jobs, True), daemon=True
        ).start()

    # ---------- TẠO LẠI ẢNH LỖI ----------
    def regenerate_failed(self):
        if self.is_running:
            self.log("Đang chạy batch, không thể Tạo lại ảnh lỗi.")
            return
        if not self.rows:
            return

        jobs = []
        for idx, row in self.rows.items():
            if row.is_error:
                jobs.append((idx, row.prompt_text))

        if not jobs:
            self.log("Không có dòng nào lỗi để tạo lại.")
            messagebox.showinfo("Thông báo", "Không có ảnh nào đang ở trạng thái lỗi.")
            return

        threading.Thread(
            target=self.run_jobs, args=(jobs, True), daemon=True
        ).start()

    # ---------- XÓA DÒNG ĐƯỢC CHỌN (không xóa file) ----------
    def delete_selected_rows(self):
        if self.is_running:
            self.log("Đang chạy batch, không thể Xóa.")
            return

        selected_indices = [idx for idx, r in self.rows.items() if r.is_selected()]
        if not selected_indices:
            messagebox.showinfo("Thông báo", "Bạn chưa chọn dòng nào để xóa.")
            return

        if not messagebox.askyesno(
            "Xác nhận", f"Xóa {len(selected_indices)} dòng khỏi bảng? (Không xóa file)"
        ):
            return

        for idx in selected_indices:
            row = self.rows.pop(idx, None)
            if row is not None:
                row.destroy()

        if not self.rows:
            self.btn_regen_selected.configure(state="disabled")
            self.btn_regen_failed.configure(state="disabled")
            self.btn_delete_rows.configure(state="disabled")

        self.log(f"Đã xóa {len(selected_indices)} dòng khỏi bảng.")


# ---------- MAIN ----------
if __name__ == "__main__":
    app = AutoGenApp()
    app.mainloop()
