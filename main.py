diff --git a/main.py b/main.py
index b03217225615c1173491b4ac55f2a9178260b6b4..686bf9288a39ef8c59a71dc57272294bd32a087f 100644
--- a/main.py
+++ b/main.py
@@ -1,228 +1,274 @@
-import customtkinter as ctk
-import threading
-import time
-import os
-import json
-import requests
-import random
-import base64
-
-from tkinter import messagebox, filedialog, BooleanVar
-from PIL import Image, ImageOps
-
-from seleniumbase import Driver
-from selenium.webdriver.common.by import By  # để sẵn nếu sau này cần
+import customtkinter as ctk
+import threading
+import time
+import os
+import json
+import requests
+import random
+import base64
+
+from tkinter import messagebox, filedialog, BooleanVar
+from PIL import Image, ImageOps
+
+from seleniumbase import Driver
+from selenium.webdriver.common.by import By  # để sẵn nếu sau này cần
 
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
 
-MODEL_MAP = {
-    "Nano Banana Pro": "GEM_PIX_2",
-    "Nano Banana": "GEM_PIX",
-    "Imagen 4": "IMAGEN_3_5",
-}
+MODEL_MAP = {
+    "Nano Banana Pro": "GEM_PIX_2",
+    "Nano Banana": "GEM_PIX",
+    "Imagen 4": "IMAGEN_3_5",
+}
 
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
-    "Phong cách anime": (
-        "Anime style illustration, clean lines, expressive eyes, "
-        "smooth shading, vibrant colors."
-    ),
-}
+    "Phong cách anime": (
+        "Anime style illustration, clean lines, expressive eyes, "
+        "smooth shading, vibrant colors."
+    ),
+}
+
+# ================ THEME SETTINGS =================
+APP_BG = "#0f172a"
+CARD_BG = "#111827"
+SUBTLE_BG = "#1f2937"
+BORDER_COLOR = "#1f2937"
+PRIMARY_COLOR = "#2563eb"
+SUCCESS_COLOR = "#22c55e"
+WARNING_COLOR = "#eab308"
+ERROR_COLOR = "#ef4444"
+TEXT_MUTED = "#9ca3af"
+FONT_BASE = ("Inter", 12)
 
 # ================= ROW WIDGET =================
 
 
-class StatusRow(ctk.CTkFrame):
+class StatusRow(ctk.CTkFrame):
     """
     Một dòng trong bảng kết quả.
     Thay đổi: Thêm màu nền xen kẽ (zebra striping) để dễ nhìn.
     """
     def __init__(self, parent, index, prompt_text, app_ref):
         # MÀU NỀN XEN KẼ: Dòng chẵn màu tối hơn chút, dòng lẻ trong suốt
-        bg_color = "#2b2b2b" if index % 2 == 0 else "transparent"
-        super().__init__(parent, fg_color=bg_color, corner_radius=6)
+        bg_color = SUBTLE_BG if index % 2 == 0 else CARD_BG
+        super().__init__(
+            parent,
+            fg_color=bg_color,
+            corner_radius=10,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
 
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
-        self.lbl_stt = ctk.CTkLabel(
-            self, text=f"{index:03d}", width=30, font=("Arial", 12, "bold")
-        )
+        self.lbl_stt = ctk.CTkLabel(
+            self,
+            text=f"{index:03d}",
+            width=30,
+            font=("Inter", 12, "bold"),
+            text_color=TEXT_MUTED,
+        )
         self.lbl_stt.grid(row=0, column=1, padx=4, pady=8, sticky="w")
 
         # ----- Cột 2: Trạng thái -----
-        self.lbl_status = ctk.CTkLabel(
-            self, text="Sẵn sàng", text_color="gray", width=90, anchor="w"
-        )
+        self.lbl_status = ctk.CTkLabel(
+            self,
+            text="Sẵn sàng",
+            text_color=TEXT_MUTED,
+            width=90,
+            anchor="w",
+            font=FONT_BASE,
+        )
         self.lbl_status.grid(row=0, column=2, padx=4, pady=8, sticky="w")
 
         # ----- Cột 3: Prompt + nút Sửa -----
         prompt_frame = ctk.CTkFrame(self, fg_color="transparent")
         prompt_frame.grid(row=0, column=3, padx=4, pady=8, sticky="ew")
         prompt_frame.grid_columnconfigure(0, weight=1)
 
         short = prompt_text if len(prompt_text) <= 60 else prompt_text[:60] + "..."
-        self.lbl_prompt = ctk.CTkLabel(
-            prompt_frame, text=short, anchor="w", justify="left"
-        )
+        self.lbl_prompt = ctk.CTkLabel(
+            prompt_frame,
+            text=short,
+            anchor="w",
+            justify="left",
+            font=FONT_BASE,
+        )
         self.lbl_prompt.grid(row=0, column=0, sticky="ew")
 
         self.btn_edit = ctk.CTkButton(
             prompt_frame, text="✏", width=24, height=24,
             command=self.on_edit_clicked, fg_color="#3b82f6", hover_color="#2563eb"
         )
         self.btn_edit.grid(row=0, column=1, padx=(4, 0))
 
         # ----- Cột 4: Tiến độ / Kết quả -----
         # Container cho progress bar
         self.progress_container = ctk.CTkFrame(self, fg_color="transparent")
         self.progress_container.grid(row=0, column=4, padx=(4, 8), pady=8, sticky="e")
-        self.progress_bar = ctk.CTkProgressBar(self.progress_container, width=100, height=10)
+        self.progress_bar = ctk.CTkProgressBar(
+            self.progress_container, width=120, height=10, fg_color=BORDER_COLOR
+        )
         self.progress_bar.grid(row=0, column=0, padx=(0, 4))
         self.progress_bar.set(0)
-        self.lbl_percent = ctk.CTkLabel(self.progress_container, text="0%", width=30, font=("Arial", 11))
+        self.lbl_percent = ctk.CTkLabel(
+            self.progress_container,
+            text="0%",
+            width=34,
+            font=("Inter", 11, "bold"),
+            text_color=TEXT_MUTED,
+        )
         self.lbl_percent.grid(row=0, column=1)
 
         # Container cho kết quả (thumbnail)
         self.result_container = ctk.CTkFrame(self, fg_color="transparent")
-        self.thumb_label = ctk.CTkLabel(self.result_container, text="", width=120, height=67) # Tỷ lệ 16:9 nhỏ
+        self.thumb_label = ctk.CTkLabel(
+            self.result_container,
+            text="",
+            width=120,
+            height=67,
+            fg_color=SUBTLE_BG,
+            corner_radius=6,
+        )  # Tỷ lệ 16:9 nhỏ
         self.thumb_label.grid(row=0, column=0, padx=(0, 4))
         
         self.btn_regen_small = ctk.CTkButton(
             self.result_container, text="↻", width=24, height=24,
             command=self.on_regen_clicked, fg_color="#4b5563", hover_color="#6b7280"
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
-    def set_status(self, text, color="white"):
-        self.lbl_status.configure(text=text, text_color=color)
+    def set_status(self, text, color="white"):
+        self.lbl_status.configure(text=text, text_color=color)
 
     def start_render(self, round_no=1):
         self.is_error = False
-        self.set_status(f"Đang render (v{round_no})...", "#e67e22")
+        self.set_status(f"Đang render (v{round_no})...", WARNING_COLOR)
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
-        self.set_status("Hoàn thành", "#2ecc71")
+        self.set_status("Hoàn thành", SUCCESS_COLOR)
 
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
 
-    def finish_error(self, msg="Lỗi"):
-        self.is_error = True
-        self.set_status(msg, "#e74c3c")
+    def finish_error(self, msg="Lỗi"):
+        self.is_error = True
+        self.set_status(msg, ERROR_COLOR)
 
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
@@ -233,326 +279,428 @@ class StatusRow(ctk.CTkFrame):
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
 
 
-class AutoGenApp(ctk.CTk):
-    def __init__(self):
-        super().__init__()
-        self.title("Flow Labs API Pure (V18.1 - UI Revamp)")
-        self.geometry("1350x800")
-        # KHÔNG cho kéo nhỏ hơn kích thước này
-        self.minsize(1200, 720)
-        ctk.set_appearance_mode("Dark")
-
-        self.session = requests.Session()
-        self.cookies_loaded = False
-        self.project_id = None
-        self.tool_name = "PINHOLE"
+class AutoGenApp(ctk.CTk):
+    def __init__(self):
+        super().__init__()
+        self.title("Flow Labs API Pure (V18.1 - UI Revamp)")
+        self.geometry("1350x800")
+        # KHÔNG cho kéo nhỏ hơn kích thước này
+        self.minsize(1200, 720)
+        ctk.set_appearance_mode("Dark")
+        ctk.set_default_color_theme("dark-blue")
+        self.configure(fg_color=APP_BG)
+
+        self.session = requests.Session()
+        self.cookies_loaded = False
+        self.project_id = None
+        self.tool_name = "PINHOLE"
         self.is_running = False
         self.rows = {}
         self.output_folder = DEFAULT_OUTPUT_FOLDER
 
         self.setup_ui()
         self.load_cookies_to_session()
 
     # ---------- UI ----------
     def setup_ui(self):
         # 3 cột: trái (prompt + cài đặt), giữa (nhân vật gốc), phải (kết quả)
         self.grid_columnconfigure(0, weight=2, minsize=380)
         self.grid_columnconfigure(1, weight=1, minsize=220)
         self.grid_columnconfigure(2, weight=3, minsize=500)
         self.grid_rowconfigure(0, weight=1)
 
         # ===== LEFT PANEL =====
-        left = ctk.CTkFrame(self)
-        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
-        left.grid_rowconfigure(0, weight=3)
-        left.grid_rowconfigure(1, weight=2)
-        left.grid_rowconfigure(2, weight=1)
-
-        # --- Prompts tạo ảnh ---
-        group_prompts = ctk.CTkFrame(left)
-        group_prompts.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
-
-        ctk.CTkLabel(
-            group_prompts, text="Prompts tạo ảnh", font=("Arial", 13, "bold")
-        ).pack(anchor="w", padx=8, pady=(6, 2))
-
-        hint = "TỐI ĐA 300 PROMPTS, cứ XUỐNG DÒNG là 1 prompt mới..."
-        self.txt_prompts = ctk.CTkTextbox(group_prompts, height=260)
-        self.txt_prompts.pack(fill="both", expand=True, padx=8, pady=(0, 8))
-        self.txt_prompts.insert("1.0", hint)
+        left = ctk.CTkFrame(self, fg_color=APP_BG)
+        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
+        left.grid_rowconfigure(0, weight=3)
+        left.grid_rowconfigure(1, weight=2)
+        left.grid_rowconfigure(2, weight=1)
+
+        # --- Prompts tạo ảnh ---
+        group_prompts = ctk.CTkFrame(
+            left,
+            fg_color=CARD_BG,
+            corner_radius=14,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
+        group_prompts.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
+
+        ctk.CTkLabel(
+            group_prompts,
+            text="Prompts tạo ảnh",
+            font=("Inter", 14, "bold"),
+        ).pack(anchor="w", padx=10, pady=(10, 4))
+
+        hint = "TỐI ĐA 300 PROMPTS, cứ XUỐNG DÒNG là 1 prompt mới..."
+        self.txt_prompts = ctk.CTkTextbox(
+            group_prompts,
+            height=260,
+            fg_color=SUBTLE_BG,
+            border_width=1,
+            border_color=BORDER_COLOR,
+            font=FONT_BASE,
+        )
+        self.txt_prompts.pack(fill="both", expand=True, padx=10, pady=(0, 10))
+        self.txt_prompts.insert("1.0", hint)
 
         # --- Cài đặt ---
-        group_settings = ctk.CTkFrame(left)
-        group_settings.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
-        group_settings.grid_columnconfigure(0, weight=1)
-        group_settings.grid_columnconfigure(1, weight=1)
-
-        ctk.CTkLabel(
-            group_settings, text="Cài đặt", font=("Arial", 13, "bold")
-        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 4))
+        group_settings = ctk.CTkFrame(
+            left,
+            fg_color=CARD_BG,
+            corner_radius=14,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
+        group_settings.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
+        group_settings.grid_columnconfigure(0, weight=1)
+        group_settings.grid_columnconfigure(1, weight=1)
+
+        ctk.CTkLabel(
+            group_settings, text="Cài đặt", font=("Inter", 14, "bold")
+        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 6))
 
         # Phong cách
-        ctk.CTkLabel(group_settings, text="Phong cách:", anchor="w").grid(
-            row=1, column=0, sticky="w", padx=8, pady=(2, 0)
-        )
-        self.combo_style = ctk.CTkComboBox(
-            group_settings, values=list(STYLE_MAP.keys()), width=200
-        )
-        self.combo_style.set("Điện ảnh (Cinematic)")
-        self.combo_style.grid(row=2, column=0, sticky="we", padx=8, pady=(0, 6))
+        ctk.CTkLabel(
+            group_settings, text="Phong cách:", anchor="w", text_color=TEXT_MUTED
+        ).grid(
+            row=1, column=0, sticky="w", padx=10, pady=(2, 0)
+        )
+        self.combo_style = ctk.CTkComboBox(
+            group_settings, values=list(STYLE_MAP.keys()), width=200, font=FONT_BASE
+        )
+        self.combo_style.set("Điện ảnh (Cinematic)")
+        self.combo_style.grid(row=2, column=0, sticky="we", padx=10, pady=(0, 8))
 
         # Tỷ lệ
-        ctk.CTkLabel(group_settings, text="Tỷ lệ ảnh:", anchor="w").grid(
-            row=1, column=1, sticky="w", padx=8, pady=(2, 0)
-        )
-        self.combo_ratio = ctk.CTkComboBox(
-            group_settings, values=list(RATIO_MAP.keys()), width=200
-        )
-        self.combo_ratio.set("Khổ ngang (16:9)")
-        self.combo_ratio.grid(row=2, column=1, sticky="we", padx=8, pady=(0, 6))
+        ctk.CTkLabel(
+            group_settings, text="Tỷ lệ ảnh:", anchor="w", text_color=TEXT_MUTED
+        ).grid(
+            row=1, column=1, sticky="w", padx=10, pady=(2, 0)
+        )
+        self.combo_ratio = ctk.CTkComboBox(
+            group_settings, values=list(RATIO_MAP.keys()), width=200, font=FONT_BASE
+        )
+        self.combo_ratio.set("Khổ ngang (16:9)")
+        self.combo_ratio.grid(row=2, column=1, sticky="we", padx=10, pady=(0, 8))
 
         # Nơi lưu
-        ctk.CTkLabel(group_settings, text="Thư mục lưu ảnh:", anchor="w").grid(
-            row=3, column=0, sticky="w", padx=8, pady=(2, 0)
-        )
-        folder_frame = ctk.CTkFrame(group_settings, fg_color="transparent")
-        folder_frame.grid(
-            row=4, column=0, columnspan=2, sticky="we", padx=8, pady=(0, 6)
-        )
+        ctk.CTkLabel(
+            group_settings, text="Thư mục lưu ảnh:", anchor="w", text_color=TEXT_MUTED
+        ).grid(
+            row=3, column=0, sticky="w", padx=10, pady=(2, 0)
+        )
+        folder_frame = ctk.CTkFrame(group_settings, fg_color="transparent")
+        folder_frame.grid(
+            row=4, column=0, columnspan=2, sticky="we", padx=8, pady=(0, 6)
+        )
         folder_frame.grid_columnconfigure(0, weight=1)
 
-        self.lbl_folder = ctk.CTkLabel(
-            folder_frame, text=self.output_folder, anchor="w"
-        )
-        self.lbl_folder.grid(row=0, column=0, sticky="we")
+        self.lbl_folder = ctk.CTkLabel(
+            folder_frame, text=self.output_folder, anchor="w", font=FONT_BASE
+        )
+        self.lbl_folder.grid(row=0, column=0, sticky="we", padx=(2, 0))
 
         ctk.CTkButton(
             folder_frame,
-            text="Chọn nơi lưu",
-            width=140,
-            command=self.choose_output_folder,
-        ).grid(row=0, column=1, padx=(6, 0))
+            text="Chọn nơi lưu",
+            width=140,
+            fg_color=PRIMARY_COLOR,
+            hover_color="#1d4ed8",
+            command=self.choose_output_folder,
+        ).grid(row=0, column=1, padx=(6, 0))
 
         # Model
-        ctk.CTkLabel(group_settings, text="Model:", anchor="w").grid(
-            row=5, column=0, sticky="w", padx=8, pady=(2, 0)
-        )
-        self.combo_model = ctk.CTkComboBox(
-            group_settings, values=list(MODEL_MAP.keys()), width=200
-        )
-        self.combo_model.set("Nano Banana Pro")
-        self.combo_model.grid(row=6, column=0, sticky="we", padx=8, pady=(0, 6))
-
-        # Trạng thái cookie (hiện ở góc)
-        self.lbl_auth_status = ctk.CTkLabel(
-            group_settings, text="Cookie: Chưa có", text_color="gray"
-        )
-        self.lbl_auth_status.grid(row=6, column=1, sticky="e", padx=8, pady=(0, 6))
+        ctk.CTkLabel(
+            group_settings, text="Model:", anchor="w", text_color=TEXT_MUTED
+        ).grid(
+            row=5, column=0, sticky="w", padx=10, pady=(2, 0)
+        )
+        self.combo_model = ctk.CTkComboBox(
+            group_settings, values=list(MODEL_MAP.keys()), width=200, font=FONT_BASE
+        )
+        self.combo_model.set("Nano Banana Pro")
+        self.combo_model.grid(row=6, column=0, sticky="we", padx=10, pady=(0, 8))
+
+        # Trạng thái cookie (hiện ở góc)
+        self.lbl_auth_status = ctk.CTkLabel(
+            group_settings,
+            text="Cookie: Chưa có",
+            text_color=TEXT_MUTED,
+            font=FONT_BASE,
+        )
+        self.lbl_auth_status.grid(row=6, column=1, sticky="e", padx=10, pady=(0, 8))
 
         # --- Điều khiển + Log ---
-        group_control = ctk.CTkFrame(left)
-        group_control.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
-        group_control.grid_columnconfigure(0, weight=1)
-        group_control.grid_rowconfigure(1, weight=1)
-
-        # nút login
-        self.btn_login = ctk.CTkButton(
-            group_control,
-            text="Đăng nhập & Lấy Cookie",
-            height=36,
-            fg_color="#d35400",
-            hover_color="#e67e22",
-            command=self.manual_login,
-        )
-        self.btn_login.grid(row=0, column=0, sticky="we", padx=8, pady=(6, 4))
+        group_control = ctk.CTkFrame(
+            left,
+            fg_color=CARD_BG,
+            corner_radius=14,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
+        group_control.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
+        group_control.grid_columnconfigure(0, weight=1)
+        group_control.grid_rowconfigure(1, weight=1)
+
+        # nút login
+        self.btn_login = ctk.CTkButton(
+            group_control,
+            text="Đăng nhập & Lấy Cookie",
+            height=36,
+            fg_color="#f59e0b",
+            hover_color="#d97706",
+            command=self.manual_login,
+        )
+        self.btn_login.grid(row=0, column=0, sticky="we", padx=10, pady=(10, 4))
 
         # nút bắt đầu
         self.btn_start = ctk.CTkButton(
             group_control,
-            text="🚀 Bắt đầu tạo ảnh",
-            height=40,
-            fg_color="#27ae60",
-            hover_color="#1e8449",
-            state="disabled",
-            command=self.start_batch,
-        )
-        self.btn_start.grid(row=0, column=1, sticky="we", padx=8, pady=(6, 4))
+            text="🚀 Bắt đầu tạo ảnh",
+            height=40,
+            fg_color="#27ae60",
+            hover_color="#1e8449",
+            state="disabled",
+            command=self.start_batch,
+        )
+        self.btn_start.grid(row=0, column=1, sticky="we", padx=10, pady=(10, 4))
 
         # log
-        ctk.CTkLabel(group_control, text="LOG HỆ THỐNG:", anchor="w").grid(
-            row=1, column=0, columnspan=2, sticky="w", padx=8
-        )
-        self.txt_log = ctk.CTkTextbox(group_control, height=120, font=("Consolas", 9))
-        self.txt_log.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=8, pady=(2, 8))
+        ctk.CTkLabel(
+            group_control,
+            text="LOG HỆ THỐNG:",
+            anchor="w",
+            font=("Inter", 12, "bold"),
+        ).grid(
+            row=1, column=0, columnspan=2, sticky="w", padx=10
+        )
+        self.txt_log = ctk.CTkTextbox(
+            group_control,
+            height=120,
+            font=("Consolas", 10),
+            fg_color=SUBTLE_BG,
+            border_width=1,
+            border_color=BORDER_COLOR,
+            text_color="#e5e7eb",
+        )
+        self.txt_log.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=(2, 10))
 
         # ===== MIDDLE PANEL: Nhân vật gốc =====
-        middle = ctk.CTkFrame(self)
-        middle.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
-        middle.grid_rowconfigure(1, weight=1)
-
-        ctk.CTkLabel(
-            middle, text="Nhân vật gốc", font=("Arial", 13, "bold")
-        ).grid(row=0, column=0, padx=8, pady=(6, 4), sticky="w")
+        middle = ctk.CTkFrame(
+            self,
+            fg_color=CARD_BG,
+            corner_radius=14,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
+        middle.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
+        middle.grid_rowconfigure(1, weight=1)
+
+        ctk.CTkLabel(
+            middle, text="Nhân vật gốc", font=("Inter", 14, "bold")
+        ).grid(row=0, column=0, padx=10, pady=(10, 4), sticky="w")
 
         # dùng ScrollableFrame để chứa 10 slot
-        slots_frame = ctk.CTkScrollableFrame(middle)
-        slots_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
-        slots_frame.grid_columnconfigure(0, weight=1)
+        slots_frame = ctk.CTkScrollableFrame(
+            middle,
+            fg_color=SUBTLE_BG,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
+        slots_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
+        slots_frame.grid_columnconfigure(0, weight=1)
 
         for i in range(10):
-            slot = ctk.CTkFrame(slots_frame)
-            slot.grid(row=i, column=0, sticky="we", pady=4)
-            slot.grid_columnconfigure(0, weight=1)
-
-            btn = ctk.CTkButton(
-                slot,
-                text=f"Click để chọn ảnh nhân vật/bối cảnh #{i+1}",
-                height=36,
-                fg_color="#444444",
-                hover_color="#555555",
-            )
-            btn.grid(row=0, column=0, sticky="we", padx=4, pady=(4, 2))
-
-            entry = ctk.CTkEntry(slot, placeholder_text="Tên nhân vật / bối cảnh...")
-            entry.grid(row=1, column=0, sticky="we", padx=4, pady=(0, 4))
+            slot = ctk.CTkFrame(slots_frame, fg_color=CARD_BG, corner_radius=10)
+            slot.grid(row=i, column=0, sticky="we", pady=6, padx=4)
+            slot.grid_columnconfigure(0, weight=1)
+
+            btn = ctk.CTkButton(
+                slot,
+                text=f"Click để chọn ảnh nhân vật/bối cảnh #{i+1}",
+                height=36,
+                fg_color=PRIMARY_COLOR,
+                hover_color="#1d4ed8",
+            )
+            btn.grid(row=0, column=0, sticky="we", padx=6, pady=(6, 4))
+
+            entry = ctk.CTkEntry(
+                slot,
+                placeholder_text="Tên nhân vật / bối cảnh...",
+                font=FONT_BASE,
+                fg_color=SUBTLE_BG,
+                border_color=BORDER_COLOR,
+            )
+            entry.grid(row=1, column=0, sticky="we", padx=6, pady=(0, 6))
 
         # ===== RIGHT PANEL: Kết quả tạo ảnh =====
-        right = ctk.CTkFrame(self)
-        right.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)
-        right.grid_columnconfigure(0, weight=1)
-        right.grid_rowconfigure(2, weight=1)
+        right = ctk.CTkFrame(
+            self,
+            fg_color=CARD_BG,
+            corner_radius=14,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
+        right.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)
+        right.grid_columnconfigure(0, weight=1)
+        right.grid_rowconfigure(2, weight=1)
 
         # thanh tiêu đề + nút chức năng
-        title_bar = ctk.CTkFrame(right, fg_color="transparent")
-        title_bar.grid(row=0, column=0, sticky="we", padx=8, pady=(6, 4))
-        title_bar.grid_columnconfigure(0, weight=1)
-
-        ctk.CTkLabel(
-            title_bar,
-            text="Kết quả tạo ảnh (Click thumbnail để zoom)",
-            font=("Arial", 13, "bold"),
-        ).grid(row=0, column=0, sticky="w")
+        title_bar = ctk.CTkFrame(right, fg_color="transparent")
+        title_bar.grid(row=0, column=0, sticky="we", padx=12, pady=(10, 6))
+        title_bar.grid_columnconfigure(0, weight=1)
+
+        ctk.CTkLabel(
+            title_bar,
+            text="Kết quả tạo ảnh (Click thumbnail để zoom)",
+            font=("Inter", 14, "bold"),
+        ).grid(row=0, column=0, sticky="w")
 
         # nút góc phải
         btn_bar = ctk.CTkFrame(title_bar, fg_color="transparent")
         btn_bar.grid(row=0, column=1, sticky="e")
 
         self.btn_regen_selected = ctk.CTkButton(
             btn_bar,
             text="Tạo lại ảnh",
-            height=32,
-            fg_color="#2980b9",
-            hover_color="#1f6391",
-            state="disabled",
-            command=self.regenerate_selected,
-        )
-        self.btn_regen_selected.grid(row=0, column=0, padx=(0, 4))
+            height=32,
+            fg_color=PRIMARY_COLOR,
+            hover_color="#1d4ed8",
+            state="disabled",
+            command=self.regenerate_selected,
+        )
+        self.btn_regen_selected.grid(row=0, column=0, padx=(0, 4))
 
         self.btn_regen_failed = ctk.CTkButton(
             btn_bar,
             text="Tạo lại ảnh lỗi",
-            height=32,
-            fg_color="#d35400",
-            hover_color="#e67e22",
-            state="disabled",
-            command=self.regenerate_failed,
-        )
-        self.btn_regen_failed.grid(row=0, column=1, padx=(0, 4))
+            height=32,
+            fg_color="#f59e0b",
+            hover_color="#d97706",
+            state="disabled",
+            command=self.regenerate_failed,
+        )
+        self.btn_regen_failed.grid(row=0, column=1, padx=(0, 4))
 
         self.btn_delete_rows = ctk.CTkButton(
             btn_bar,
             text="Xóa",
-            height=32,
-            fg_color="#c0392b",
-            hover_color="#e74c3c",
-            state="disabled",
-            command=self.delete_selected_rows,
-        )
-        self.btn_delete_rows.grid(row=0, column=2)
-
-        # header bảng
-        self.header_frame = ctk.CTkFrame(right, fg_color="transparent")
-        self.header_frame.grid(row=1, column=0, sticky="we", padx=8, pady=(0, 2))
+            height=32,
+            fg_color="#ef4444",
+            hover_color="#dc2626",
+            state="disabled",
+            command=self.delete_selected_rows,
+        )
+        self.btn_delete_rows.grid(row=0, column=2)
+
+        # header bảng
+        self.header_frame = ctk.CTkFrame(
+            right,
+            fg_color=SUBTLE_BG,
+            corner_radius=10,
+            border_width=1,
+            border_color=BORDER_COLOR,
+        )
+        self.header_frame.grid(row=1, column=0, sticky="we", padx=12, pady=(0, 4))
 
         self.build_header_row()
 
         # separator dưới header (line đậm hơn)
-        self.header_separator = ctk.CTkFrame(right, height=1, fg_color="#404040")
-        self.header_separator.grid(row=2, column=0, sticky="we", padx=8, pady=(0, 2))
-
-        # danh sách dòng
-        self.right_list = ctk.CTkScrollableFrame(right)
-        self.right_list.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
+        self.header_separator = ctk.CTkFrame(right, height=1, fg_color=BORDER_COLOR)
+        self.header_separator.grid(row=2, column=0, sticky="we", padx=12, pady=(0, 2))
+
+        # danh sách dòng
+        self.right_list = ctk.CTkScrollableFrame(
+            right,
+            fg_color=CARD_BG,
+            border_width=0,
+        )
+        self.right_list.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
 
     def build_header_row(self):
         header = self.header_frame
 
-        ctk.CTkLabel(header, text="", width=30).grid(row=0, column=0, padx=(4, 4))
-        ctk.CTkLabel(
-            header, text="STT", width=40, anchor="w", font=("Arial", 12, "bold")
-        ).grid(row=0, column=1, padx=2, sticky="w")
-
-        ctk.CTkLabel(
-            header, text="Trạng thái", width=120, anchor="w", font=("Arial", 12, "bold")
-        ).grid(row=0, column=2, padx=2, sticky="w")
-
-        ctk.CTkLabel(
-            header,
-            text="Prompt",
-            anchor="w",
-            font=("Arial", 12, "bold"),
-        ).grid(row=0, column=3, padx=2, sticky="w")
-
-        ctk.CTkLabel(
-            header,
-            text="Tiến độ",
-            anchor="w",
-            font=("Arial", 12, "bold"),
-        ).grid(row=0, column=4, padx=6, sticky="e")
+        ctk.CTkLabel(header, text="", width=30, fg_color="transparent").grid(
+            row=0, column=0, padx=(10, 6)
+        )
+        ctk.CTkLabel(
+            header,
+            text="STT",
+            width=40,
+            anchor="w",
+            font=("Inter", 12, "bold"),
+            text_color="#e5e7eb",
+        ).grid(row=0, column=1, padx=6, sticky="w")
+
+        ctk.CTkLabel(
+            header,
+            text="Trạng thái",
+            width=120,
+            anchor="w",
+            font=("Inter", 12, "bold"),
+            text_color="#e5e7eb",
+        ).grid(row=0, column=2, padx=6, sticky="w")
+
+        ctk.CTkLabel(
+            header,
+            text="Prompt",
+            anchor="w",
+            font=("Inter", 12, "bold"),
+            text_color="#e5e7eb",
+        ).grid(row=0, column=3, padx=6, sticky="w")
+
+        ctk.CTkLabel(
+            header,
+            text="Tiến độ",
+            anchor="w",
+            font=("Inter", 12, "bold"),
+            text_color="#e5e7eb",
+        ).grid(row=0, column=4, padx=10, sticky="e")
 
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
@@ -655,57 +803,57 @@ class AutoGenApp(ctk.CTk):
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
-        if self.cookies_loaded and self.manual_auth_token:
-            self.lbl_auth_status.configure(text="Auth: Full (OK)", text_color="#2ecc71") # Xanh lá
-            self.btn_start.configure(state="normal", fg_color="#27ae60")
-        elif self.cookies_loaded:
-            self.lbl_auth_status.configure(text="Auth: Thiếu Token", text_color="#f39c12") # Vàng
-        else:
-            self.lbl_auth_status.configure(text="Chưa có gì", text_color="gray")
+        if self.cookies_loaded and self.manual_auth_token:
+            self.lbl_auth_status.configure(text="Auth: Full (OK)", text_color=SUCCESS_COLOR) # Xanh lá
+            self.btn_start.configure(state="normal", fg_color=SUCCESS_COLOR)
+        elif self.cookies_loaded:
+            self.lbl_auth_status.configure(text="Auth: Thiếu Token", text_color=WARNING_COLOR) # Vàng
+        else:
+            self.lbl_auth_status.configure(text="Chưa có gì", text_color=TEXT_MUTED)
 
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
