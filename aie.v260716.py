#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
알파카 이미지 편집기 (Alpaca Image Editor)

이미지 병합/뒤집기/회전/크기 조정/ICO 변환 기능을 제공하는 Tkinter 기반 GUI 프로그램.

필요 패키지:
    pip install Pillow
    pip install tkinterdnd2      (드래그 앤 드롭 기능, 필수)
    pip install sv-ttk           (현대적인 라이트 테마, 선택 - 없어도 기본 테마로 동작)
"""

import tkinter as tk
import os
import sys

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    tkdnd_path = os.path.join(base_path, 'tkinterdnd2', 'tkdnd')
    os.environ['TKDND_LIBRARY'] = tkdnd_path

from tkinter import filedialog, messagebox, ttk, colorchooser, Toplevel
from PIL import Image, ImageOps, ImageTk
import webbrowser
# tkinterdnd2 라이브러리 임포트 시도
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    messagebox.showerror("라이브러리 오류", "tkinterdnd2 라이브러리를 찾을 수 없습니다.\n'pip install tkinterdnd2' 명령으로 설치해주세요.")
    exit()

# 현대적인 라이트 테마 (Sun Valley) - 설치되어 있지 않으면 기본 테마로 자동 대체
try:
    import sv_ttk
    SV_TTK_AVAILABLE = True
except ImportError:
    SV_TTK_AVAILABLE = False

# ============================================================================
# "ICO 파일 변환" 기능에서 사용하는 상수 (ico_converter.py 이식)
# ============================================================================
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ICO_LARGEST_SIZE = ICO_SIZES[-1]
ICO_SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp")

# ============================================================================
# 앱 전체가 공통으로 사용하는 색상 팔레트 (Sun Valley 라이트 테마와 어울리도록 구성)
# ============================================================================
APP_BG = "#fafafa"
APP_CARD = "#ffffff"
APP_BORDER = "#e5e5e5"
APP_BORDER_ACTIVE = "#005fb8"
APP_ACCENT = "#005fb8"
APP_ACCENT_HOVER = "#0258a8"
APP_ACCENT_DISABLED = "#a9c9e8"
APP_TEXT = "#1a1a1a"
APP_SUBTEXT = "#666666"
APP_SUCCESS = "#0f7b3f"
APP_WARN = "#b45f06"
APP_ERROR = "#c0392b"

# 좌측 기능 선택 내비게이션에서 각 모드를 나타내는 아이콘
NAV_ICONS = {
    "2_horiz": "↔️", "2_vert": "↕️", "3_horiz": "↔️", "3_vert": "↕️",
    "4_grid": "▦", "flip_image": "🔃", "rotate_image": "🔄",
    "resize_image": "📐", "crop_image": "✂️", "ico_convert": "🪟",
}


class ImageEditorApp:
    def __init__(self, master):
        self.master = master
        master.title("알파카 이미지 편집기 (Alpaca Image Editor)")
        # 아이콘 설정 (오류 발생 시 무시)
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aie.ico")
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
            else:
                print(f"아이콘 파일을 찾을 수 없습니다: {icon_path}")
        except Exception as e:
            print(f"아이콘 로드 실패: {e}")
            pass

        master.geometry("1000x780")
        master.minsize(900, 700)
        master.resizable(True, True)

        self.feature_options_list = [
            ("2개 이미지 병합 (가로)", "2_horiz"),
            ("2개 이미지 병합 (세로)", "2_vert"),
            ("3개 이미지 병합 (가로)", "3_horiz"),
            ("3개 이미지 병합 (세로)", "3_vert"),
            ("4개 이미지 병합 (2x2)", "4_grid"),
            ("이미지 뒤집기", "flip_image"),
            ("이미지 회전하기", "rotate_image"),
            ("이미지 크기 조정", "resize_image"),
            ("이미지 자르기", "crop_image"),
            ("ICO 파일 변환", "ico_convert")
        ]
        self.active_mode_value = self.feature_options_list[0][1] 
        self.current_gap_color = tk.StringVar(value="#FFFFFF")
        self.current_border_color = tk.StringVar(value="#000000") 

        # 이미지 경로 엔트리/버튼/레이블 리스트 (동적 생성을 위해 초기화)
        self.image_paths_entries = []
        self.browse_buttons = []
        self.image_labels = []

        # 특정 모드를 위한 위젯 (재사용을 위해 변수 선언)
        self.single_image_entry = None
        self.flip_options_combobox = None
        self.rotate_options_combobox = None

        master.configure(bg=APP_BG)
        style = ttk.Style()
        if SV_TTK_AVAILABLE:
            try:
                sv_ttk.set_theme("light")
            except Exception:
                style.theme_use('clam')
                self._apply_fallback_style(style)
        else:
            style.theme_use('clam')
            self._apply_fallback_style(style)

        self.master.option_add('*TCombobox*Listbox.background', 'white')
        self.master.option_add('*TCombobox*Listbox.font', ('Helvetica', 10))
        self.master.option_add('*TCombobox*Listbox.selectBackground', APP_ACCENT)
        self.master.option_add('*TCombobox*Listbox.selectForeground', 'white')

        top_frame = ttk.Frame(master, padding=10)
        top_frame.pack(expand=True, fill=tk.BOTH)

        left_menu_frame = ttk.LabelFrame(top_frame, text="기능 선택", padding=10)
        left_menu_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.right_options_frame = ttk.LabelFrame(top_frame, text="옵션 설정", padding=10)
        self.right_options_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        bottom_frame = ttk.Frame(master, padding="10 0 10 10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self._build_nav_sidebar(left_menu_frame)

        button_sub_frame = ttk.Frame(bottom_frame)
        button_sub_frame.pack(pady=(0,10))

        # 하단 실행 버튼들은 ttk.Button 대신 tk.Button을 사용합니다.
        # sv_ttk는 버튼을 스프라이트 이미지로 그리기 때문에, 색상을 직접 지정하는
        # 커스텀 ttk 스타일(Custom/Preview/Exit.TButton)을 얹으면 Windows 환경에서
        # 배경/글자가 제대로 그려지지 않고 흰 버튼으로만 보이는 문제가 있었습니다.
        # tk.Button은 테마 엔진을 거치지 않고 지정한 색을 그대로 그리므로 이 문제가 없습니다.
        btn_font = ('Helvetica', 10, 'bold')

        self.preview_btn = tk.Button(button_sub_frame, text="미리보기", command=self.show_preview,
                                      bg=APP_SUCCESS, fg="white", activebackground="#0b5c30",
                                      activeforeground="white", font=btn_font, relief="flat",
                                      cursor="hand2", padx=14, pady=6, borderwidth=0)
        self.preview_btn.pack(side=tk.LEFT, padx=5)

        self.action_btn = tk.Button(button_sub_frame, text="실행", command=self.process_action,
                                     bg=APP_ACCENT, fg="white", activebackground=APP_ACCENT_HOVER,
                                     activeforeground="white", font=btn_font, relief="flat",
                                     cursor="hand2", padx=14, pady=6, borderwidth=0)
        self.action_btn.pack(side=tk.LEFT, padx=5)

        self.exit_btn = tk.Button(button_sub_frame, text="종료", command=master.quit,
                                   bg=APP_ERROR, fg="white", activebackground="#a5322a",
                                   activeforeground="white", font=btn_font, relief="flat",
                                   cursor="hand2", padx=14, pady=6, borderwidth=0)
        self.exit_btn.pack(side=tk.LEFT, padx=5)

        self.footer_text = "제작: 알파카100 (https://alpaca100.tistory.com/)"
        self.footer_url = "https://alpaca100.tistory.com/"
        self.footer_label = tk.Label(bottom_frame, text=self.footer_text, bg=APP_BG,
                                      fg=APP_ACCENT, cursor="hand2", font=('Helvetica', 9))
        self.footer_label.pack(pady=(5,0))
        self.footer_label.bind("<Button-1>", lambda e: self.open_link(self.footer_url))

        self.update_options_ui()

    @staticmethod
    def _apply_fallback_style(style):
        """sv_ttk가 설치되어 있지 않을 때 사용하는 대체 스타일 (기존 'clam' 테마 기반)."""
        style.configure("TButton", padding=6, relief="groove", font=('Helvetica', 10))
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TEntry", padding=5, font=('Helvetica', 10))
        style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))
        style.configure("TCombobox", padding=5, font=('Helvetica', 10))
        style.map("TCombobox",
                  fieldbackground=[("readonly", "white")],
                  selectbackground=[("readonly", "white")],
                  selectforeground=[("readonly", "black")])

    # ========================================================================
    # 좌측 "기능 선택" 내비게이션 (필 모양 아이콘 리스트)
    # ========================================================================
    def _build_nav_sidebar(self, parent):
        self.nav_items = []
        nav_container = tk.Frame(parent, bg=APP_BG)
        nav_container.pack(fill="both", expand=True)

        for label_text, mode_value in self.feature_options_list:
            self._create_nav_row(nav_container, label_text, mode_value)

    def _create_nav_row(self, parent, label_text, mode_value):
        icon = NAV_ICONS.get(mode_value, "•")
        row_h = 38
        canvas = tk.Canvas(parent, height=row_h, width=200, bg=APP_BG,
                            highlightthickness=0, cursor="hand2")
        canvas.pack(fill="x", pady=2)

        def redraw(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            if w < 10:
                w = 200
            selected = (self.active_mode_value == mode_value)
            if selected:
                self._draw_rounded_rect(canvas, 2, 2, w - 2, row_h - 2, radius=10,
                                         fill=APP_ACCENT, outline="")
                fg = "#ffffff"
            else:
                fg = APP_TEXT
            canvas.create_text(14, row_h // 2, text=icon, anchor="w",
                                font=("Segoe UI Emoji", 12))
            canvas.create_text(40, row_h // 2, text=label_text, anchor="w",
                                font=("Helvetica", 10), fill=fg)

        canvas.bind("<Configure>", redraw)
        canvas.bind("<Button-1>", lambda e: self._on_nav_click(mode_value))
        self.nav_items.append(redraw)

    @staticmethod
    def _draw_rounded_rect(canvas, x1, y1, x2, y2, radius=10, **kwargs):
        points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
                  x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
                  x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _on_nav_click(self, mode_value):
        if mode_value == self.active_mode_value:
            return
        self.active_mode_value = mode_value
        self._refresh_nav_selection()
        self.update_options_ui()

    def _refresh_nav_selection(self):
        for redraw in self.nav_items:
            redraw()

    def validate_combobox(self, event):
        """콤보박스에서 포커스가 벗어날 때 값이 비었는지 확인하고 복원합니다."""
        widget = event.widget
        try:
            if not widget.get():
                if widget == self.flip_options_combobox:
                    widget.set("좌우 뒤집기")
                elif widget == self.rotate_options_combobox:
                    widget.set("시계 방향으로 90°")
        except tk.TclError:
            pass

    def update_options_ui(self):
        for widget in self.right_options_frame.winfo_children():
            widget.destroy()
        
        self.image_paths_entries.clear(); self.browse_buttons.clear(); self.image_labels.clear()

        mode = self.active_mode_value

        if mode in ["2_horiz", "2_vert", "3_horiz", "3_vert", "4_grid"]:
            num_images = 2 if mode in ["2_horiz", "2_vert"] else \
                         3 if mode in ["3_horiz", "3_vert"] else \
                         4 if mode == "4_grid" else 0

            container = tk.Frame(self.right_options_frame, bg=APP_BG)
            container.pack(fill="both", expand=True)

            self._ui_section(container, "이미지 선택")
            card = self._ui_card(container)
            card.grid_columnconfigure(1, weight=1)

            for i in range(num_images):
                label = tk.Label(card, text=f"이미지 {i+1}:", bg=APP_CARD, fg=APP_TEXT,
                                  font=("Helvetica", 10), width=8, anchor="w")
                label.grid(row=i, column=0, sticky="w", pady=4)
                self.image_labels.append(label)

                entry = tk.Entry(card, font=("Courier", 9), bg="#F5F7FA", relief="flat",
                                  fg=APP_TEXT, state="readonly")
                entry.grid(row=i, column=1, sticky="ew", padx=8, ipady=5)
                self.image_paths_entries.append(entry)
                entry.drop_target_register(DND_FILES)
                entry.dnd_bind('<<Drop>>', lambda event, e=entry: self.handle_drop(event, e))

                button = tk.Button(card, text="찾아보기", command=lambda e=entry: self.browse_file(e),
                                    bg=APP_ACCENT, fg="white", font=("Helvetica", 9, "bold"),
                                    relief="flat", cursor="hand2", padx=10)
                button.grid(row=i, column=2, padx=(0, 2))
                self.browse_buttons.append(button)

            self._create_merge_options_widgets(container)

        elif mode == "flip_image":
            container = tk.Frame(self.right_options_frame, bg=APP_BG)
            container.pack(fill="both", expand=True)
            self._build_single_image_section(container, "대상 이미지")

            self._ui_section(container, "뒤집기 옵션")
            card = self._ui_card(container)
            self.flip_options_combobox = ttk.Combobox(
                card, values=["좌우 뒤집기", "상하 뒤집기", "상하/좌우 뒤집기"],
                state="readonly", font=('Helvetica', 10), width=22)
            self.flip_options_combobox.set("좌우 뒤집기")
            self.flip_options_combobox.pack(anchor="w")
            self.flip_options_combobox.bind("<FocusOut>", self.validate_combobox)

        elif mode == "rotate_image":
            container = tk.Frame(self.right_options_frame, bg=APP_BG)
            container.pack(fill="both", expand=True)
            self._build_single_image_section(container, "대상 이미지")

            self._ui_section(container, "회전 각도")
            card = self._ui_card(container)
            self.rotate_options_combobox = ttk.Combobox(
                card, values=["시계 방향으로 90°", "시계 방향으로 180°", "시계 방향으로 270°"],
                state="readonly", font=('Helvetica', 10), width=22)
            self.rotate_options_combobox.set("시계 방향으로 90°")
            self.rotate_options_combobox.pack(anchor="w")
            self.rotate_options_combobox.bind("<FocusOut>", self.validate_combobox)

        elif mode == "resize_image":
            self._build_resize_ui(self.right_options_frame)

        elif mode == "crop_image":
            self._build_crop_ui(self.right_options_frame)

        elif mode == "ico_convert":
            self._build_ico_ui(self.right_options_frame)

    # ========================================================================
    # 모든 옵션 패널이 공유하는 카드 스타일 UI 헬퍼
    # ========================================================================
    def _ui_section(self, parent, text):
        tk.Label(parent, text=text, bg=APP_BG, fg=APP_TEXT, font=("Helvetica", 10, "bold"),
                 anchor="w").pack(fill="x", pady=(8, 2))

    def _ui_card(self, parent, fill="x", expand=False):
        frm = tk.Frame(parent, bg=APP_CARD, highlightthickness=1, highlightbackground=APP_BORDER)
        frm.pack(fill=fill, expand=expand, pady=1, ipady=8, ipadx=10)
        return frm

    def _build_single_image_section(self, container, title):
        self._ui_section(container, title)
        card = self._ui_card(container)
        row = tk.Frame(card, bg=APP_CARD)
        row.pack(fill="x")
        self.single_image_entry = tk.Entry(row, font=("Courier", 9), bg="#F5F7FA", relief="flat",
                                            fg=APP_TEXT, state="readonly", width=44)
        self.single_image_entry.pack(side="left", ipady=5, padx=(0, 8))
        self.single_image_entry.drop_target_register(DND_FILES)
        self.single_image_entry.dnd_bind(
            '<<Drop>>', lambda event, e=self.single_image_entry: self.handle_drop(event, e))
        tk.Button(row, text="찾아보기", command=lambda: self.browse_file(self.single_image_entry),
                  bg=APP_ACCENT, fg="white", font=("Helvetica", 9, "bold"), relief="flat",
                  cursor="hand2", padx=10).pack(side="left")

    # ========================================================================
    # "이미지 크기 조정" 기능 (image_resizer.py 이식)
    # ========================================================================
    def _build_resize_ui(self, parent):
        self.resize_image_path = tk.StringVar()
        self.resize_output_name = tk.StringVar()
        self.resize_mode = tk.StringVar(value="percent")
        self.resize_percent = tk.DoubleVar(value=50.0)
        self.resize_custom_w = tk.IntVar(value=0)
        self.resize_custom_h = tk.IntVar(value=0)
        self.resize_keep_ratio = tk.BooleanVar(value=True)
        self.resize_quality = tk.IntVar(value=85)
        self._resize_orig_w = 0
        self._resize_orig_h = 0
        self._resize_preview_img = None

        f_label = ("Helvetica", 10)
        f_small = ("Helvetica", 9)
        f_bold = ("Helvetica", 10, "bold")
        f_title = ("Helvetica", 13, "bold")
        f_btn = ("Helvetica", 11, "bold")
        f_mono = ("Courier", 9)

        container = tk.Frame(parent, bg=APP_BG)
        container.pack(fill="both", expand=True)

        def section(text):
            tk.Label(container, text=text, bg=APP_BG, fg=APP_TEXT,
                     font=f_bold, anchor="w").pack(fill="x", pady=(8, 2))

        def card(fill="x"):
            frm = tk.Frame(container, bg=APP_CARD, highlightthickness=1,
                            highlightbackground=APP_BORDER)
            frm.pack(fill=fill, pady=1, ipady=6, ipadx=10)
            return frm

        # ── 이미지 선택 ──
        section("이미지 선택")
        frm_path = card()
        self.resize_ent_path = tk.Entry(frm_path, textvariable=self.resize_image_path,
                                         font=f_mono, bg="#F0F2F8", relief="flat",
                                         fg=APP_TEXT, width=46)
        self.resize_ent_path.pack(side="left", ipady=6, ipadx=6, padx=(0, 8))
        tk.Button(frm_path, text="찾아보기…", command=self._resize_browse,
                  bg=APP_ACCENT, fg="white", font=f_btn, relief="flat",
                  cursor="hand2", padx=10).pack(side="left")
        self.resize_ent_path.drop_target_register(DND_FILES)
        self.resize_ent_path.dnd_bind("<<Drop>>", self._resize_on_drop)

        tk.Label(container, text="파일을 끌어다 놓거나 찾아보기 버튼을 클릭하세요",
                 bg=APP_BG, fg=APP_SUBTEXT, font=f_small).pack(anchor="w")

        # ── 원본 이미지 정보 ──
        section("원본 이미지 정보")
        frm_info = card(fill="both")
        left_info = tk.Frame(frm_info, bg=APP_CARD)
        left_info.pack(side="left", fill="both", expand=True)
        self.resize_lbl_info = tk.Label(left_info, text="이미지를 선택하면 정보가 표시됩니다.",
                                         bg=APP_CARD, fg=APP_SUBTEXT, font=f_label,
                                         justify="left", anchor="w")
        self.resize_lbl_info.pack(anchor="w", pady=4)

        self.resize_canvas_prev = tk.Canvas(frm_info, width=100, height=70, bg="#EAECF2",
                                             relief="flat", highlightthickness=1,
                                             highlightbackground=APP_BORDER)
        self.resize_canvas_prev.pack(side="right", padx=(8, 0))
        self.resize_canvas_prev.create_text(50, 35, text="미리보기", fill=APP_SUBTEXT,
                                             font=f_small, tags="hint")

        # ── 변환 옵션 ──
        section("변환 옵션")
        frm_opt = card(fill="both")

        frm_radio = tk.Frame(frm_opt, bg=APP_CARD)
        frm_radio.pack(anchor="w", pady=(0, 6))
        tk.Radiobutton(frm_radio, text="비율로 축소", variable=self.resize_mode,
                        value="percent", command=self._resize_on_mode_change,
                        bg=APP_CARD, font=f_label, fg=APP_TEXT,
                        activebackground=APP_CARD).pack(side="left", padx=(0, 16))
        tk.Radiobutton(frm_radio, text="크기 직접 입력 (px)", variable=self.resize_mode,
                        value="custom", command=self._resize_on_mode_change,
                        bg=APP_CARD, font=f_label, fg=APP_TEXT,
                        activebackground=APP_CARD).pack(side="left")

        # "비율로 축소" 옵션 (슬라이더 + 직접 입력 텍스트 상자)
        self.resize_frm_percent = tk.Frame(frm_opt, bg=APP_CARD)
        tk.Label(self.resize_frm_percent, text="축소 비율:", bg=APP_CARD, font=f_label,
                  fg=APP_TEXT, width=9, anchor="w").pack(side="left")
        self.resize_slider = ttk.Scale(self.resize_frm_percent, from_=1, to=100,
                                        variable=self.resize_percent, orient="horizontal",
                                        length=220, command=self._resize_on_percent_slide)
        self.resize_slider.pack(side="left", padx=8)
        self.resize_pct_entry_var = tk.StringVar(value="50")
        self.resize_ent_pct = tk.Entry(self.resize_frm_percent, textvariable=self.resize_pct_entry_var,
                                        width=4, font=f_label, bg="#F0F2F8", relief="flat",
                                        justify="center")
        self.resize_ent_pct.pack(side="left", ipady=3)
        self.resize_ent_pct.bind("<Return>", self._resize_on_pct_entry_commit)
        self.resize_ent_pct.bind("<FocusOut>", self._resize_on_pct_entry_commit)
        tk.Label(self.resize_frm_percent, text="%", bg=APP_CARD, font=f_label,
                  fg=APP_TEXT).pack(side="left", padx=(2, 8))
        self.resize_lbl_pct_size = tk.Label(self.resize_frm_percent, text="", bg=APP_CARD,
                                             fg=APP_SUBTEXT, font=f_small)
        self.resize_lbl_pct_size.pack(side="left", padx=8)

        # "비율로 축소"가 선택되었을 때만 보이는 빠른 선택 버튼
        self.resize_frm_quick = tk.Frame(frm_opt, bg=APP_CARD)
        tk.Label(self.resize_frm_quick, text="빠른 선택:", bg=APP_CARD, fg=APP_SUBTEXT, font=f_small,
                  width=9, anchor="w").pack(side="left")
        for pct in (25, 50, 75):
            tk.Button(self.resize_frm_quick, text=f"{pct}%", command=lambda p=pct: self._resize_set_percent(p),
                      bg=APP_BORDER, fg=APP_TEXT, font=f_small, relief="flat",
                      cursor="hand2", padx=8, pady=2).pack(side="left", padx=2)

        # "크기 직접 입력" 옵션
        self.resize_frm_custom = tk.Frame(frm_opt, bg=APP_CARD)
        tk.Label(self.resize_frm_custom, text="너비(W):", bg=APP_CARD, font=f_label,
                  fg=APP_TEXT, width=8, anchor="w").grid(row=0, column=0, sticky="w")
        self.resize_ent_w = tk.Entry(self.resize_frm_custom, textvariable=self.resize_custom_w,
                                      width=7, font=f_label, bg="#F0F2F8", relief="flat")
        self.resize_ent_w.grid(row=0, column=1, padx=(0, 4))
        self.resize_ent_w.bind("<FocusOut>", self._resize_on_custom_w_change)
        tk.Label(self.resize_frm_custom, text="px", bg=APP_CARD, font=f_small,
                  fg=APP_SUBTEXT).grid(row=0, column=2, padx=(0, 14))
        tk.Label(self.resize_frm_custom, text="높이(H):", bg=APP_CARD, font=f_label,
                  fg=APP_TEXT, width=8, anchor="w").grid(row=0, column=3)
        self.resize_ent_h = tk.Entry(self.resize_frm_custom, textvariable=self.resize_custom_h,
                                      width=7, font=f_label, bg="#F0F2F8", relief="flat")
        self.resize_ent_h.grid(row=0, column=4, padx=(0, 4))
        self.resize_ent_h.bind("<FocusOut>", self._resize_on_custom_h_change)
        tk.Label(self.resize_frm_custom, text="px", bg=APP_CARD, font=f_small,
                  fg=APP_SUBTEXT).grid(row=0, column=5)
        tk.Checkbutton(self.resize_frm_custom, text="비율 유지", variable=self.resize_keep_ratio,
                        bg=APP_CARD, font=f_small, fg=APP_TEXT,
                        activebackground=APP_CARD).grid(row=0, column=6, padx=(14, 0))

        # ── 저장 품질 (비율/직접입력 선택과 무관하게 항상 표시) ──
        section("저장 품질")
        frm_quality = card()
        tk.Label(frm_quality, text="저장 품질:", bg=APP_CARD, font=f_label, fg=APP_TEXT,
                  width=9, anchor="w").pack(side="left")
        self.resize_slider_q = ttk.Scale(frm_quality, from_=10, to=100, variable=self.resize_quality,
                                          orient="horizontal", length=200,
                                          command=self._resize_on_quality_slide)
        self.resize_slider_q.pack(side="left", padx=8)
        self.resize_quality_entry_var = tk.StringVar(value="85")
        self.resize_ent_quality = tk.Entry(frm_quality, textvariable=self.resize_quality_entry_var,
                                            width=4, font=f_label, bg="#F0F2F8", relief="flat",
                                            justify="center")
        self.resize_ent_quality.pack(side="left", ipady=3)
        self.resize_ent_quality.bind("<Return>", self._resize_on_quality_entry_commit)
        self.resize_ent_quality.bind("<FocusOut>", self._resize_on_quality_entry_commit)
        tk.Label(frm_quality, text="%", bg=APP_CARD, font=f_label,
                  fg=APP_TEXT).pack(side="left", padx=(2, 8))
        tk.Label(frm_quality, text="(JPEG/WEBP에만 적용)", bg=APP_CARD, fg=APP_SUBTEXT,
                  font=f_small).pack(side="left")

        # ── 상태 안내 (저장은 하단 공용 '미리보기'/'실행' 버튼 사용) ──
        bottom_row = tk.Frame(container, bg=APP_BG)
        bottom_row.pack(fill="x", pady=(10, 0))
        self.resize_lbl_status = tk.Label(
            bottom_row,
            text="  하단의 '미리보기' 또는 '실행' 버튼으로 결과를 확인하고 저장하세요.",
            bg=APP_BG, fg=APP_SUBTEXT, font=f_small, anchor="w", justify="left"
        )
        self.resize_lbl_status.pack(side="left", fill="x", expand=True)

        self._resize_on_mode_change()

    def _resize_browse(self):
        path = filedialog.askopenfilename(
            title="이미지 선택",
            filetypes=[("이미지 파일", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff"),
                       ("모든 파일", "*.*")]
        )
        if path:
            self._resize_load_image(path)

    def _resize_on_drop(self, event):
        try:
            paths = self.master.splitlist(event.data)
        except Exception:
            paths = [event.data]
        if paths:
            self._resize_load_image(paths[0])

    def _resize_load_image(self, path):
        if not os.path.isfile(path):
            self._resize_set_status("파일을 찾을 수 없습니다.", APP_ERROR)
            return
        try:
            img = Image.open(path)
            self._resize_orig_w, self._resize_orig_h = img.size
            size_kb = os.path.getsize(path) / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"

            self.resize_image_path.set(path)
            self.resize_custom_w.set(self._resize_orig_w)
            self.resize_custom_h.set(self._resize_orig_h)

            base = os.path.splitext(os.path.basename(path))[0]
            self.resize_output_name.set(f"{base}_resized")

            self.resize_lbl_info.config(
                text=(f"크기: {self._resize_orig_w} × {self._resize_orig_h} px\n"
                      f"파일 크기: {size_str}    형식: {img.format or '알 수 없음'}    "
                      f"모드: {img.mode}"),
                fg=APP_TEXT
            )

            thumb = img.copy()
            thumb.thumbnail((100, 70))
            self._resize_preview_img = ImageTk.PhotoImage(thumb)
            self.resize_canvas_prev.delete("all")
            self.resize_canvas_prev.create_image(50, 35, image=self._resize_preview_img)

            self._resize_update_percent_size_label()
            self._resize_set_status(f"이미지 로드 완료: {os.path.basename(path)}", APP_SUCCESS)
        except Exception as e:
            self._resize_set_status(f"이미지 열기 실패: {e}", APP_ERROR)

    def _resize_on_mode_change(self):
        # 세 프레임을 모두 떼어낸 뒤 필요한 것만 순서대로 다시 배치합니다.
        # (떼어냈다가 하나만 다시 pack()하면 형제 위젯들보다 맨 아래로 밀려나는
        #  문제가 있었기 때문에, 매번 전체를 정해진 순서로 재배치합니다.)
        self.resize_frm_percent.pack_forget()
        self.resize_frm_quick.pack_forget()
        self.resize_frm_custom.pack_forget()

        if self.resize_mode.get() == "percent":
            self.resize_frm_percent.pack(fill="x", pady=(0, 4))
            self.resize_frm_quick.pack(anchor="w", pady=(0, 4))
        else:
            self.resize_frm_custom.pack(anchor="w", pady=(0, 4))

    def _resize_on_percent_slide(self, _=None):
        pct = int(self.resize_percent.get())
        self.resize_pct_entry_var.set(str(pct))
        self._resize_update_percent_size_label()

    def _resize_on_pct_entry_commit(self, event=None):
        try:
            val = float(self.resize_pct_entry_var.get())
        except ValueError:
            val = self.resize_percent.get()
        val = max(1, min(100, val))
        self.resize_percent.set(val)
        self.resize_pct_entry_var.set(str(int(val)))
        self._resize_update_percent_size_label()

    def _resize_update_percent_size_label(self):
        if self._resize_orig_w and self._resize_orig_h:
            pct = self.resize_percent.get() / 100
            nw = int(self._resize_orig_w * pct)
            nh = int(self._resize_orig_h * pct)
            self.resize_lbl_pct_size.config(text=f"→ {nw} × {nh} px")
        else:
            self.resize_lbl_pct_size.config(text="")

    def _resize_set_percent(self, pct):
        self.resize_percent.set(pct)
        self._resize_on_percent_slide()

    def _resize_on_quality_slide(self, _=None):
        self.resize_quality_entry_var.set(str(int(self.resize_quality.get())))

    def _resize_on_quality_entry_commit(self, event=None):
        try:
            val = int(float(self.resize_quality_entry_var.get()))
        except ValueError:
            val = int(self.resize_quality.get())
        val = max(10, min(100, val))
        self.resize_quality.set(val)
        self.resize_quality_entry_var.set(str(val))

    def _resize_on_custom_w_change(self, _=None):
        if self.resize_keep_ratio.get() and self._resize_orig_w and self._resize_orig_h:
            try:
                nw = self.resize_custom_w.get()
                nh = int(nw * self._resize_orig_h / self._resize_orig_w)
                self.resize_custom_h.set(nh)
            except Exception:
                pass

    def _resize_on_custom_h_change(self, _=None):
        if self.resize_keep_ratio.get() and self._resize_orig_w and self._resize_orig_h:
            try:
                nh = self.resize_custom_h.get()
                nw = int(nh * self._resize_orig_w / self._resize_orig_h)
                self.resize_custom_w.set(nw)
            except Exception:
                pass

    def _resize_guess_ext(self):
        """저장 대화상자의 기본 확장자를 원본 파일 확장자로 추정합니다."""
        path = self.resize_image_path.get().strip() if hasattr(self, "resize_image_path") else ""
        ext = os.path.splitext(path)[1].lower() if path else ""
        return ext if ext else ".jpg"

    def _resize_save_with_format(self, image, output_path):
        """저장 경로의 확장자에 맞춰 포맷별 저장 옵션(품질 등)을 적용해 저장합니다."""
        ext = os.path.splitext(output_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(output_path, format="JPEG",
                       quality=int(self.resize_quality.get()), optimize=True)
        elif ext == ".webp":
            image.save(output_path, format="WEBP", quality=int(self.resize_quality.get()))
        elif ext == ".png":
            image.save(output_path, format="PNG", optimize=True)
        else:
            image.save(output_path)

    def _resize_set_status(self, msg, color=APP_SUBTEXT):
        self.resize_lbl_status.config(text=f"  {msg}", fg=color)

    # ========================================================================
    # "이미지 자르기" 기능 (모서리 8방향 핸들 드래그 방식)
    # ========================================================================
    CROP_CANVAS_W = 560
    CROP_CANVAS_H = 360
    CROP_HANDLE_SIZE = 9
    CROP_MIN_SIZE = 16  # 캔버스 좌표 기준 최소 크롭 크기(px)

    def _build_crop_ui(self, parent):
        self.crop_image_path = tk.StringVar()
        self.crop_pil_image = None
        self.crop_orig_w = 0
        self.crop_orig_h = 0
        self.crop_scale = 1.0
        self.crop_img_x0 = 0
        self.crop_img_y0 = 0
        self.crop_disp_w = 0
        self.crop_disp_h = 0
        self.crop_rect = [0, 0, 0, 0]
        self.crop_photo = None
        self._crop_drag_handle = None
        self._crop_drag_start = None
        self._crop_drag_rect0 = None

        f_label = ("Helvetica", 10)
        f_small = ("Helvetica", 9)
        f_bold = ("Helvetica", 10, "bold")
        f_btn = ("Helvetica", 11, "bold")
        f_mono = ("Courier", 9)

        container = tk.Frame(parent, bg=APP_BG)
        container.pack(fill="both", expand=True)

        def section(text):
            tk.Label(container, text=text, bg=APP_BG, fg=APP_TEXT, font=f_bold,
                     anchor="w").pack(fill="x", pady=(6, 2))

        def card(fill="x", expand=False):
            frm = tk.Frame(container, bg=APP_CARD, highlightthickness=1, highlightbackground=APP_BORDER)
            frm.pack(fill=fill, expand=expand, pady=1, ipady=6, ipadx=10)
            return frm

        # ── 이미지 선택 ──
        section("이미지 선택")
        frm_path = card()
        self.crop_ent_path = tk.Entry(frm_path, textvariable=self.crop_image_path, font=f_mono,
                                       bg="#F0F2F8", relief="flat", fg=APP_TEXT, width=46)
        self.crop_ent_path.pack(side="left", ipady=6, ipadx=6, padx=(0, 8))
        tk.Button(frm_path, text="찾아보기…", command=self._crop_browse, bg=APP_ACCENT, fg="white",
                  font=f_btn, relief="flat", cursor="hand2", padx=10).pack(side="left")
        self.crop_ent_path.drop_target_register(DND_FILES)
        self.crop_ent_path.dnd_bind("<<Drop>>", self._crop_on_drop)

        tk.Label(container, text="파일을 끌어다 놓거나 찾아보기 버튼을 클릭하세요",
                 bg=APP_BG, fg=APP_SUBTEXT, font=f_small).pack(anchor="w")

        # ── 자를 영역 선택 (캔버스 + 8방향 핸들) ──
        section("자를 영역 선택 (모서리/변의 파란 점을 드래그하세요)")
        frm_canvas = card()
        self.crop_canvas = tk.Canvas(frm_canvas, width=self.CROP_CANVAS_W, height=self.CROP_CANVAS_H,
                                      bg="#EAECF2", highlightthickness=0, cursor="crosshair")
        self.crop_canvas.pack()
        self.crop_canvas.bind("<B1-Motion>", self._crop_on_drag)
        self.crop_canvas.bind("<ButtonRelease-1>", self._crop_on_release)
        self._crop_draw_placeholder()

        info_row = tk.Frame(container, bg=APP_BG)
        info_row.pack(fill="x", pady=(6, 0))
        self.crop_lbl_info = tk.Label(info_row, text="이미지를 선택하면 잘라낼 영역을 지정할 수 있습니다.",
                                       bg=APP_BG, fg=APP_SUBTEXT, font=f_small, anchor="w")
        self.crop_lbl_info.pack(side="left")
        tk.Button(info_row, text="영역 초기화", command=self._crop_reset, bg=APP_BORDER, fg=APP_TEXT,
                  font=f_small, relief="flat", cursor="hand2", padx=10).pack(side="right")

        # ── 상태 안내 (저장은 하단 공용 '미리보기'/'실행' 버튼 사용) ──
        bottom_row = tk.Frame(container, bg=APP_BG)
        bottom_row.pack(fill="x", pady=(8, 0))
        self.crop_lbl_status = tk.Label(
            bottom_row,
            text="  하단의 '미리보기' 또는 '실행' 버튼으로 결과를 확인하고 저장하세요.",
            bg=APP_BG, fg=APP_SUBTEXT, font=f_small, anchor="w", justify="left"
        )
        self.crop_lbl_status.pack(side="left", fill="x", expand=True)

    def _crop_draw_placeholder(self):
        self.crop_canvas.delete("all")
        self.crop_canvas.create_text(
            self.CROP_CANVAS_W // 2, self.CROP_CANVAS_H // 2,
            text="이미지를 선택하세요", fill=APP_SUBTEXT, font=("Helvetica", 10)
        )

    def _crop_browse(self):
        path = filedialog.askopenfilename(
            title="이미지 선택",
            filetypes=[("이미지 파일", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff"),
                       ("모든 파일", "*.*")]
        )
        if path:
            self._crop_load_image(path)

    def _crop_on_drop(self, event):
        try:
            paths = self.master.splitlist(event.data)
        except Exception:
            paths = [event.data]
        if paths:
            self._crop_load_image(paths[0])

    def _crop_load_image(self, path):
        if not os.path.isfile(path):
            self.crop_lbl_status.config(text="  파일을 찾을 수 없습니다.", fg=APP_ERROR)
            return
        try:
            img = Image.open(path)
            img.load()
        except Exception as e:
            self.crop_lbl_status.config(text=f"  이미지 열기 실패: {e}", fg=APP_ERROR)
            return

        self.crop_image_path.set(path)
        self.crop_pil_image = img
        self.crop_orig_w, self.crop_orig_h = img.size

        # 캔버스 안에 맞도록 축소 비율 계산 (확대는 하지 않음)
        max_w, max_h = self.CROP_CANVAS_W - 20, self.CROP_CANVAS_H - 20
        scale = min(max_w / self.crop_orig_w, max_h / self.crop_orig_h, 1.0)
        self.crop_scale = scale
        self.crop_disp_w = max(1, int(self.crop_orig_w * scale))
        self.crop_disp_h = max(1, int(self.crop_orig_h * scale))
        self.crop_img_x0 = (self.CROP_CANVAS_W - self.crop_disp_w) // 2
        self.crop_img_y0 = (self.CROP_CANVAS_H - self.crop_disp_h) // 2

        disp_img = img.copy()
        if disp_img.mode not in ("RGB", "RGBA"):
            disp_img = disp_img.convert("RGBA")
        disp_img.thumbnail((self.crop_disp_w, self.crop_disp_h), Image.Resampling.LANCZOS)
        self.crop_photo = ImageTk.PhotoImage(disp_img)

        # 잘라낼 영역을 이미지 전체로 초기화
        self.crop_rect = [self.crop_img_x0, self.crop_img_y0,
                           self.crop_img_x0 + self.crop_disp_w, self.crop_img_y0 + self.crop_disp_h]

        self._crop_redraw()
        self.crop_lbl_status.config(text=f"  이미지 로드 완료: {os.path.basename(path)}", fg=APP_SUCCESS)

    def _crop_reset(self):
        if not self.crop_pil_image:
            return
        self.crop_rect = [self.crop_img_x0, self.crop_img_y0,
                           self.crop_img_x0 + self.crop_disp_w, self.crop_img_y0 + self.crop_disp_h]
        self._crop_redraw()

    def _crop_redraw(self):
        c = self.crop_canvas
        c.delete("all")
        if not self.crop_pil_image:
            self._crop_draw_placeholder()
            return

        c.create_image(self.crop_img_x0, self.crop_img_y0, anchor="nw", image=self.crop_photo)

        x1, y1, x2, y2 = self.crop_rect
        ix1, iy1 = self.crop_img_x0, self.crop_img_y0
        ix2, iy2 = self.crop_img_x0 + self.crop_disp_w, self.crop_img_y0 + self.crop_disp_h

        # 잘려나갈(제외되는) 바깥 영역을 어둡게 표시
        dim_kwargs = dict(fill="black", stipple="gray50", outline="")
        if y1 > iy1:
            c.create_rectangle(ix1, iy1, ix2, y1, **dim_kwargs)
        if y2 < iy2:
            c.create_rectangle(ix1, y2, ix2, iy2, **dim_kwargs)
        if x1 > ix1:
            c.create_rectangle(ix1, y1, x1, y2, **dim_kwargs)
        if x2 < ix2:
            c.create_rectangle(x2, y1, ix2, y2, **dim_kwargs)

        # 크롭 영역 (내부를 옅게 채워서 어디를 클릭해도 이동 드래그가 되도록 함)
        rect_id = c.create_rectangle(x1, y1, x2, y2, outline=APP_ACCENT, width=2,
                                      fill=APP_ACCENT, stipple="gray12", tags="crop_rect")
        c.tag_bind(rect_id, "<ButtonPress-1>", self._crop_on_rect_press)

        # 8방향 핸들 (모서리 4개 + 변 중앙 4개)
        hs = self.CROP_HANDLE_SIZE
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        handle_positions = {
            "tl": (x1, y1), "t": (mx, y1), "tr": (x2, y1),
            "l": (x1, my), "r": (x2, my),
            "bl": (x1, y2), "b": (mx, y2), "br": (x2, y2),
        }
        cursor_map = {
            "tl": "size_nw_se", "br": "size_nw_se", "tr": "size_ne_sw", "bl": "size_ne_sw",
            "t": "size_ns", "b": "size_ns", "l": "size_we", "r": "size_we",
        }
        for name, (hx, hy) in handle_positions.items():
            hid = c.create_rectangle(hx - hs / 2, hy - hs / 2, hx + hs / 2, hy + hs / 2,
                                      fill=APP_ACCENT, outline="white", width=1)
            cur = cursor_map[name]
            c.tag_bind(hid, "<ButtonPress-1>", lambda e, n=name: self._crop_on_handle_press(e, n))
            c.tag_bind(hid, "<Enter>", lambda e, cu=cur: self.crop_canvas.config(cursor=cu))
            c.tag_bind(hid, "<Leave>", lambda e: self.crop_canvas.config(cursor="crosshair"))

        self._crop_update_info_label()

    def _crop_update_info_label(self):
        x1, y1, x2, y2 = self._crop_get_original_coords()
        w, h = max(0, x2 - x1), max(0, y2 - y1)
        self.crop_lbl_info.config(
            text=f"잘라낼 영역: {w} × {h} px  (원본 {self.crop_orig_w} × {self.crop_orig_h} px 중)",
            fg=APP_TEXT
        )

    def _crop_on_handle_press(self, event, handle_name):
        self._crop_drag_handle = handle_name
        self._crop_drag_start = (event.x, event.y)
        self._crop_drag_rect0 = list(self.crop_rect)

    def _crop_on_rect_press(self, event):
        self._crop_drag_handle = "move"
        self._crop_drag_start = (event.x, event.y)
        self._crop_drag_rect0 = list(self.crop_rect)

    def _crop_on_drag(self, event):
        if not self._crop_drag_handle or not self.crop_pil_image:
            return
        if self._crop_drag_handle == "move":
            self._crop_do_move_drag(event)
        else:
            self._crop_do_handle_drag(event)

    def _crop_on_release(self, event):
        self._crop_drag_handle = None
        self._crop_drag_start = None
        self._crop_drag_rect0 = None

    def _crop_do_handle_drag(self, event):
        ix1, iy1 = self.crop_img_x0, self.crop_img_y0
        ix2, iy2 = self.crop_img_x0 + self.crop_disp_w, self.crop_img_y0 + self.crop_disp_h
        min_size = self.CROP_MIN_SIZE

        x = max(ix1, min(ix2, event.x))
        y = max(iy1, min(iy2, event.y))

        x1, y1, x2, y2 = self.crop_rect
        h = self._crop_drag_handle

        if "l" in h:
            x1 = min(x, x2 - min_size)
        if "r" in h:
            x2 = max(x, x1 + min_size)
        if "t" in h:
            y1 = min(y, y2 - min_size)
        if "b" in h:
            y2 = max(y, y1 + min_size)

        self.crop_rect = [x1, y1, x2, y2]
        self._crop_redraw()

    def _crop_do_move_drag(self, event):
        if not self._crop_drag_rect0 or not self._crop_drag_start:
            return
        ix1, iy1 = self.crop_img_x0, self.crop_img_y0
        ix2, iy2 = self.crop_img_x0 + self.crop_disp_w, self.crop_img_y0 + self.crop_disp_h

        dx = event.x - self._crop_drag_start[0]
        dy = event.y - self._crop_drag_start[1]
        x1, y1, x2, y2 = self._crop_drag_rect0
        w, h = x2 - x1, y2 - y1

        nx1 = max(ix1, min(x1 + dx, ix2 - w))
        ny1 = max(iy1, min(y1 + dy, iy2 - h))

        self.crop_rect = [nx1, ny1, nx1 + w, ny1 + h]
        self._crop_redraw()

    def _crop_get_original_coords(self):
        """캔버스 좌표계의 크롭 영역을 원본 이미지 픽셀 좌표로 변환합니다."""
        if not self.crop_pil_image or self.crop_scale <= 0:
            return 0, 0, 0, 0
        x1, y1, x2, y2 = self.crop_rect
        ox1 = round((x1 - self.crop_img_x0) / self.crop_scale)
        oy1 = round((y1 - self.crop_img_y0) / self.crop_scale)
        ox2 = round((x2 - self.crop_img_x0) / self.crop_scale)
        oy2 = round((y2 - self.crop_img_y0) / self.crop_scale)
        ox1 = max(0, min(ox1, self.crop_orig_w))
        oy1 = max(0, min(oy1, self.crop_orig_h))
        ox2 = max(0, min(ox2, self.crop_orig_w))
        oy2 = max(0, min(oy2, self.crop_orig_h))
        return ox1, oy1, ox2, oy2

    def _crop_guess_ext(self):
        path = self.crop_image_path.get().strip() if hasattr(self, "crop_image_path") else ""
        ext = os.path.splitext(path)[1].lower() if path else ""
        return ext if ext else ".png"

    def _crop_save_with_format(self, image, output_path):
        ext = os.path.splitext(output_path)[1].lower()
        if ext in (".jpg", ".jpeg") and image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(output_path)

    # ========================================================================
    # "ICO 파일 변환" 기능 (ico_converter.py 이식)
    # ========================================================================
    def _build_ico_ui(self, parent):
        self.ico_image_path = None
        self.ico_pil_image = None
        self.ico_output_path = None
        self.ico_preview_photo = None

        f_body = ("Helvetica", 10)
        f_bold = ("Helvetica", 11, "bold")
        f_small = ("Helvetica", 9)
        f_button = ("Helvetica", 11, "bold")

        container = tk.Frame(parent, bg=APP_BG)
        container.pack(fill="both", expand=True)

        self.ico_drop_frame = tk.Frame(container, bg=APP_CARD, highlightthickness=2,
                                        highlightbackground=APP_BORDER,
                                        highlightcolor=APP_BORDER, bd=0)
        self.ico_drop_frame.pack(fill="x", pady=(4, 0))

        inner = tk.Frame(self.ico_drop_frame, bg=APP_CARD)
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        self.ico_preview_canvas = tk.Canvas(inner, width=120, height=120, bg=APP_CARD,
                                             highlightthickness=1, highlightbackground=APP_BORDER)
        self.ico_preview_canvas.pack(pady=(0, 10))
        self._ico_draw_placeholder()

        self.ico_drop_label = tk.Label(inner, text="이미지를 끌어다 놓거나 버튼을 클릭하세요",
                                        font=f_body, bg=APP_CARD, fg=APP_SUBTEXT)
        self.ico_drop_label.pack(pady=(0, 10))

        self.ico_select_btn = tk.Button(
            inner, text="이미지 선택", font=f_button, bg=APP_ACCENT, fg="white",
            activebackground=APP_ACCENT_HOVER, activeforeground="white", relief="flat",
            bd=0, padx=20, pady=8, cursor="hand2", command=self._ico_select_file
        )
        self.ico_select_btn.pack()

        self.ico_drop_frame.drop_target_register(DND_FILES)
        self.ico_drop_frame.dnd_bind("<<Drop>>", self._ico_on_drop)
        self.ico_drop_frame.dnd_bind("<<DropEnter>>", self._ico_on_drop_enter)
        self.ico_drop_frame.dnd_bind("<<DropLeave>>", self._ico_on_drop_leave)

        info = tk.Frame(container, bg=APP_BG)
        info.pack(fill="x", pady=(12, 0))

        self.ico_name_label = tk.Label(info, text="선택된 파일 없음", font=f_bold,
                                        bg=APP_BG, fg=APP_TEXT, anchor="w")
        self.ico_name_label.pack(fill="x")

        self.ico_meta_label = tk.Label(info, text="", font=f_small, bg=APP_BG,
                                        fg=APP_SUBTEXT, anchor="w")
        self.ico_meta_label.pack(fill="x", pady=(3, 0))

        sizes_txt = "포함 해상도: " + ", ".join(f"{w}×{h}" for w, h in ICO_SIZES)
        tk.Label(container, text=sizes_txt, font=f_small, bg=APP_BG, fg=APP_SUBTEXT,
                 anchor="w").pack(fill="x", pady=(10, 0))

        self.ico_status_label = tk.Label(
            container,
            text="  하단의 '미리보기' 또는 '실행' 버튼으로 ICO 파일을 저장하세요.",
            font=f_small, bg=APP_BG, fg=APP_SUBTEXT, anchor="w", justify="left",
            wraplength=460
        )
        self.ico_status_label.pack(fill="x", pady=(10, 0))

    def _ico_draw_placeholder(self):
        self.ico_preview_canvas.delete("all")
        self.ico_preview_canvas.create_text(60, 60, text="미리보기", font=("Helvetica", 9),
                                             fill=APP_SUBTEXT)

    def _ico_on_drop_enter(self, event):
        self.ico_drop_frame.config(highlightbackground=APP_BORDER_ACTIVE,
                                    highlightcolor=APP_BORDER_ACTIVE)

    def _ico_on_drop_leave(self, event):
        self.ico_drop_frame.config(highlightbackground=APP_BORDER, highlightcolor=APP_BORDER)

    def _ico_on_drop(self, event):
        self._ico_on_drop_leave(event)
        try:
            paths = self.master.splitlist(event.data)
        except Exception:
            paths = [event.data]
        if not paths:
            return
        path = paths[0]
        if path.lower().endswith(ICO_SUPPORTED_EXTS):
            self._ico_load_image(path)
        else:
            messagebox.showwarning(
                "지원하지 않는 파일",
                "이미지 파일만 지원합니다.\n(PNG, JPG, BMP, GIF, TIFF, WEBP)"
            )

    def _ico_select_file(self):
        filetypes = [
            ("이미지 파일", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp"),
            ("PNG 파일", "*.png"),
            ("JPEG 파일", "*.jpg *.jpeg"),
            ("모든 파일", "*.*"),
        ]
        path = filedialog.askopenfilename(title="이미지 선택", filetypes=filetypes)
        if path:
            self._ico_load_image(path)

    def _ico_load_image(self, path):
        try:
            img = Image.open(path)
            img.load()
        except Exception as e:
            messagebox.showerror("이미지 열기 실패", f"이미지를 여는 중 오류가 발생했습니다.\n\n{e}")
            return

        self.ico_image_path = path
        self.ico_pil_image = img

        base, _ext = os.path.splitext(path)
        self.ico_output_path = base + ".ico"

        self._ico_refresh_info()
        self._ico_refresh_preview()

    def _ico_refresh_info(self):
        name = os.path.basename(self.ico_image_path)
        w, h = self.ico_pil_image.size
        transparent = self._ico_has_transparency(self.ico_pil_image)

        self.ico_name_label.config(text=name)
        self.ico_meta_label.config(
            text=f"원본 크기 {w}×{h}px    투명 배경 {'있음' if transparent else '없음'}"
        )

        if max(w, h) < ICO_LARGEST_SIZE[0]:
            self.ico_status_label.config(
                text=(f"⚠ 원본이 {ICO_LARGEST_SIZE[0]}×{ICO_LARGEST_SIZE[1]}px보다 작아 확대되며, "
                      "큰 아이콘에서는 다소 흐리게 보일 수 있어요."),
                fg=APP_WARN
            )
        else:
            self.ico_status_label.config(
                text="  하단의 '미리보기' 또는 '실행' 버튼으로 ICO 파일을 저장하세요.",
                fg=APP_SUBTEXT
            )

    @staticmethod
    def _ico_has_transparency(img):
        if img.mode in ("RGBA", "LA"):
            return img.getchannel("A").getextrema()[0] < 255
        if img.mode == "P" and "transparency" in img.info:
            return True
        return False

    def _ico_refresh_preview(self):
        thumb = self.ico_pil_image.copy()
        thumb.thumbnail((110, 110), Image.Resampling.LANCZOS)
        if thumb.mode != "RGBA":
            thumb = thumb.convert("RGBA")

        checker = self._ico_checker_bg(thumb.size)
        composed = Image.alpha_composite(checker, thumb)

        self.ico_preview_photo = ImageTk.PhotoImage(composed)
        self.ico_preview_canvas.delete("all")
        self.ico_preview_canvas.create_image(60, 60, image=self.ico_preview_photo)

    @staticmethod
    def _ico_checker_bg(size, cell=8):
        """투명 영역을 시각적으로 보여주기 위한 체크무늬 배경 생성."""
        w, h = size
        bg = Image.new("RGBA", (w, h), (255, 255, 255, 255))
        light, dark = (255, 255, 255, 255), (222, 222, 224, 255)
        for y in range(0, h, cell):
            for x in range(0, w, cell):
                color = dark if ((x // cell) + (y // cell)) % 2 == 0 else light
                bw, bh = min(cell, w - x), min(cell, h - y)
                bg.paste(Image.new("RGBA", (bw, bh), color), (x, y))
        return bg

    @staticmethod
    def _ico_fit_to_square(img, size):
        """비율을 유지한 채 정사각형 캔버스 중앙에 배치하고 남는 영역은 투명 처리."""
        img = img.convert("RGBA")
        w, h = img.size
        scale = min(size[0] / w, size[1] / h)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        offset = ((size[0] - nw) // 2, (size[1] - nh) // 2)
        canvas.paste(resized, offset, resized)
        return canvas

    def _create_merge_options_widgets(self, container):
        """병합 모드에 필요한 여백/테두리 옵션 위젯들을 카드 스타일로 생성합니다."""
        self._ui_section(container, "여백 및 테두리 설정")
        card = self._ui_card(container)

        tk.Label(card, text="여백 크기 (px):", bg=APP_CARD, fg=APP_TEXT, font=("Helvetica", 10),
                 anchor="w", width=18).grid(row=0, column=0, sticky="w", pady=4)
        self.gap_spinbox = tk.Spinbox(card, from_=0, to=100, width=7, increment=1,
                                       font=('Helvetica', 10), relief="flat", bg="#F5F7FA")
        self.gap_spinbox.delete(0, "end"); self.gap_spinbox.insert(0, "10")
        self.gap_spinbox.grid(row=0, column=1, sticky="w", pady=4)

        tk.Label(card, text="여백 색상:", bg=APP_CARD, fg=APP_TEXT, font=("Helvetica", 10),
                 anchor="w", width=18).grid(row=1, column=0, sticky="w", pady=4)
        self.gap_color_preview = self._create_color_picker(card, 1, self.current_gap_color)

        tk.Label(card, text="테두리 굵기 (px):", bg=APP_CARD, fg=APP_TEXT, font=("Helvetica", 10),
                 anchor="w", width=18).grid(row=2, column=0, sticky="w", pady=(14, 4))
        self.border_spinbox = tk.Spinbox(card, from_=0, to=50, width=7, increment=1,
                                          font=('Helvetica', 10), relief="flat", bg="#F5F7FA")
        self.border_spinbox.delete(0, "end"); self.border_spinbox.insert(0, "0")
        self.border_spinbox.grid(row=2, column=1, sticky="w", pady=(14, 4))

        tk.Label(card, text="테두리 색상:", bg=APP_CARD, fg=APP_TEXT, font=("Helvetica", 10),
                 anchor="w", width=18).grid(row=3, column=0, sticky="w", pady=4)
        self.border_color_preview = self._create_color_picker(card, 3, self.current_border_color)

    def _create_color_picker(self, card, row, color_variable):
        """카드 내 지정된 행에 색상 선택 위젯(견본+16진값+색상표 버튼)을 가로로 배치합니다."""
        row_frame = tk.Frame(card, bg=APP_CARD)
        row_frame.grid(row=row, column=1, sticky="w", pady=4)

        preview_label = tk.Label(row_frame, text="  ", bg=color_variable.get(),
                                  relief="solid", width=3, borderwidth=1)
        preview_label.pack(side="left")

        hex_entry = tk.Entry(row_frame, textvariable=color_variable, width=10,
                              font=('Helvetica', 10), relief="flat", bg="#F5F7FA")
        hex_entry.pack(side="left", padx=8, ipady=3)

        choose_button = tk.Button(row_frame, text="색상표...", bg=APP_BORDER, fg=APP_TEXT,
                                   font=('Helvetica', 9), relief="flat", cursor="hand2", padx=8,
                                   command=lambda: self._choose_color(color_variable, preview_label))
        choose_button.pack(side="left")

        hex_entry.bind("<FocusOut>", lambda event, var=color_variable, pl=preview_label: self._update_preview_from_entry(var, pl))
        return preview_label

    def _update_preview_from_entry(self, color_variable, preview_label):
        """Entry의 값으로 색상 미리보기를 업데이트합니다."""
        color_code = color_variable.get()
        try:
            preview_label.config(bg=color_code)
        except tk.TclError:
            pass 

    def _choose_color(self, color_variable, preview_label):
        """색상 선택 대화상자를 열고 선택된 색상으로 변수와 미리보기를 업데이트합니다."""
        chosen_color = colorchooser.askcolor(title="색상 선택", initialcolor=color_variable.get())
        if chosen_color and chosen_color[1]:
            color_variable.set(chosen_color[1])
            preview_label.config(bg=chosen_color[1])

    def handle_drop(self, event, entry_widget):
        try:
            filepaths = self.master.splitlist(event.data)
            if filepaths:
                entry_widget.config(state="normal")
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, filepaths[0])
                entry_widget.config(state="readonly")
        except Exception as e:
            messagebox.showerror("드롭 처리 오류", f"파일 드롭 처리 중 오류 발생: {e}")

    def browse_file(self, entry_widget):
        file_path = filedialog.askopenfilename(title="이미지 파일 선택", filetypes=[("이미지 파일", "*.jpg *.jpeg *.png *.bmp *.gif"), ("모든 파일", "*.*")])
        if file_path:
            entry_widget.config(state="normal"); entry_widget.delete(0, tk.END); entry_widget.insert(0, file_path); entry_widget.config(state="readonly")

    def open_link(self, url):
        try: webbrowser.open_new_tab(url)
        except Exception as e: messagebox.showerror("오류", f"링크를 여는 중 오류가 발생했습니다: {e}")

    def _validate_color(self, color_code, default_color):
        """색상 코드의 유효성을 검사하고, 유효하지 않으면 기본값을 반환합니다."""
        try:
            Image.new('RGB', (1,1), color_code)
            return color_code
        except ValueError:
            messagebox.showwarning("색상 오류", f"잘못된 색상 코드 '{color_code}'입니다.\n기본값 '{default_color}'로 대체합니다.")
            return default_color
    
    def _load_multiple_images(self, num_expected):
        images, image_paths = [], [entry.get() for entry in self.image_paths_entries]
        if len(image_paths) != num_expected: return None
        for i, path in enumerate(image_paths):
            if not path:
                messagebox.showwarning("경고", f"{num_expected}개의 이미지를 모두 선택해주세요 (이미지 {i+1} 누락)."); return None
            try:
                img = Image.open(path)
                if img.mode == 'RGBA': img = img.convert('RGB')
                images.append(img)
            except Exception as e:
                messagebox.showerror("오류", f"이미지 로드/처리 중 오류 ({path}): {e}"); return None
        return images

    def _load_single_image(self, entry_widget):
        path = entry_widget.get()
        if not path:
            messagebox.showwarning("경고", "처리할 이미지를 선택해주세요."); return None
        try:
            img = Image.open(path)
            if img.mode == 'RGBA': img = img.convert('RGB')
            return img
        except FileNotFoundError:
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다: {path}"); return None
        except Exception as e:
            messagebox.showerror("오류", f"이미지 로드 중 오류 ({path}): {e}"); return None

    def _generate_processed_image(self):
        """현재 설정에 따라 처리된 이미지를 생성합니다."""
        mode = self.active_mode_value
        processed_image = None

        if mode in ["2_horiz", "2_vert", "3_horiz", "3_vert", "4_grid"]:
            try:
                gap = int(self.gap_spinbox.get())
                border_width = int(self.border_spinbox.get())
                if gap < 0 or border_width < 0:
                    messagebox.showerror("입력 오류", "여백과 테두리 굵기는 0 이상이어야 합니다.")
                    return None
            except ValueError:
                messagebox.showerror("입력 오류", "여백과 테두리 굵기는 숫자여야 합니다.")
                return None

            gap_color = self._validate_color(self.current_gap_color.get(), "#FFFFFF")
            border_color = self._validate_color(self.current_border_color.get(), "#000000")
            
            self.current_gap_color.set(gap_color); self.current_border_color.set(border_color)
            self._update_preview_from_entry(self.current_gap_color, self.gap_color_preview)
            self._update_preview_from_entry(self.current_border_color, self.border_color_preview)

            num_images = 2 if mode in ["2_horiz", "2_vert"] else 3 if mode in ["3_horiz", "3_vert"] else 4 if mode == "4_grid" else 0
            images = self._load_multiple_images(num_images)
            if not images: return None

            if mode in ["2_horiz", "3_horiz"]: processed_image = self.merge_horizontal(images, gap, gap_color)
            elif mode in ["2_vert", "3_vert"]: processed_image = self.merge_vertical(images, gap, gap_color)
            elif mode == "4_grid": processed_image = self.merge_4_grid(images, gap, gap_color)
            
            if processed_image and border_width > 0:
                processed_image = ImageOps.expand(processed_image, border=border_width, fill=border_color)

        elif mode == "flip_image":
            image = self._load_single_image(self.single_image_entry)
            if not image: return None
            
            flip_option_text = self.flip_options_combobox.get()
            if flip_option_text == "좌우 뒤집기":
                processed_image = image.transpose(Image.FLIP_LEFT_RIGHT)
            elif flip_option_text == "상하 뒤집기":
                processed_image = image.transpose(Image.FLIP_TOP_BOTTOM)
            elif flip_option_text == "상하/좌우 뒤집기":
                processed_image = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
            else:
                messagebox.showerror("오류", "유효한 뒤집기 옵션을 선택해주세요.")
                return None

        elif mode == "rotate_image":
            image = self._load_single_image(self.single_image_entry)
            if not image: return None
            
            rotate_option_text = self.rotate_options_combobox.get()
            if rotate_option_text == "시계 방향으로 90°":
                processed_image = image.transpose(Image.ROTATE_270)
            elif rotate_option_text == "시계 방향으로 180°":
                processed_image = image.transpose(Image.ROTATE_180)
            elif rotate_option_text == "시계 방향으로 270°":
                processed_image = image.transpose(Image.ROTATE_90)
            else:
                messagebox.showerror("오류", "유효한 회전 옵션을 선택해주세요.")
                return None

        elif mode == "resize_image":
            path = self.resize_image_path.get().strip() if hasattr(self, "resize_image_path") else ""
            if not path or not os.path.isfile(path):
                messagebox.showwarning("경고", "크기를 조정할 이미지를 먼저 선택해주세요.")
                return None
            try:
                img = Image.open(path)
            except Exception as e:
                messagebox.showerror("오류", f"이미지 로드 중 오류가 발생했습니다: {e}")
                return None

            orig_w, orig_h = img.size
            if self.resize_mode.get() == "percent":
                pct = self.resize_percent.get() / 100
                new_w = max(1, int(orig_w * pct))
                new_h = max(1, int(orig_h * pct))
            else:
                new_w = max(1, self.resize_custom_w.get())
                new_h = max(1, self.resize_custom_h.get())

            processed_image = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        elif mode == "crop_image":
            if not getattr(self, "crop_pil_image", None):
                messagebox.showwarning("경고", "자를 이미지를 먼저 선택해주세요.")
                return None
            x1, y1, x2, y2 = self._crop_get_original_coords()
            if (x2 - x1) < 1 or (y2 - y1) < 1:
                messagebox.showwarning("경고", "잘라낼 영역이 너무 작습니다.")
                return None
            processed_image = self.crop_pil_image.crop((x1, y1, x2, y2))

        elif mode == "ico_convert":
            if not getattr(self, "ico_pil_image", None):
                messagebox.showwarning("경고", "ICO로 변환할 이미지를 먼저 선택해주세요.")
                return None
            processed_image = self._ico_fit_to_square(self.ico_pil_image, ICO_LARGEST_SIZE)

        return processed_image

    def show_preview(self):
        """미리보기 창을 표시합니다."""
        processed_image = self._generate_processed_image()
        if not processed_image:
            return
        
        # 미리보기 창 생성
        preview_window = Toplevel(self.master)
        preview_window.title("미리보기")
        preview_window.geometry("800x600")
        
        # 이미지를 화면 크기에 맞게 조정
        max_width, max_height = 780, 550
        img_width, img_height = processed_image.size
        
        # 비율 유지하면서 크기 조정
        ratio = min(max_width / img_width, max_height / img_height)
        if ratio < 1:  # 이미지가 창보다 클 경우만 축소
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            display_image = processed_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            display_image = processed_image
        
        # Tkinter에서 표시할 수 있도록 변환
        photo = ImageTk.PhotoImage(display_image)
        
        # 스크롤 가능한 캔버스 생성
        canvas_frame = ttk.Frame(preview_window)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg='gray')
        scrollbar_y = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 이미지를 캔버스에 추가
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.config(scrollregion=canvas.bbox(tk.ALL))
        
        # 이미지 정보 표시
        info_text = f"원본 크기: {img_width} x {img_height} 픽셀"
        if ratio < 1:
            info_text += f" | 미리보기: {display_image.size[0]} x {display_image.size[1]} 픽셀 ({int(ratio*100)}%)"
        
        info_label = ttk.Label(preview_window, text=info_text, font=('Helvetica', 9))
        info_label.pack(pady=(0, 10))
        
        # 닫기 버튼
        close_btn = ttk.Button(preview_window, text="닫기", command=preview_window.destroy)
        close_btn.pack(pady=(0, 10))
        
        # 닫기 버튼에 포커스 설정
        close_btn.focus_set()
        
        # 이미지 참조 유지 (가비지 컬렉션 방지)
        preview_window.photo = photo

    def process_action(self):
        mode = self.active_mode_value
        save_kwargs = {}
        dialog_kwargs = {"title": "결과 이미지 저장 위치 선택"}

        if mode == "ico_convert":
            dialog_kwargs["defaultextension"] = ".ico"
            dialog_kwargs["filetypes"] = [("ICO 파일", "*.ico")]
            if getattr(self, "ico_output_path", None):
                dialog_kwargs["initialfile"] = os.path.basename(self.ico_output_path)
                dialog_kwargs["initialdir"] = os.path.dirname(self.ico_output_path)
            save_kwargs = {"format": "ICO", "sizes": ICO_SIZES}

        elif mode == "resize_image":
            dialog_kwargs["defaultextension"] = self._resize_guess_ext()
            dialog_kwargs["filetypes"] = [
                ("JPEG 파일", "*.jpg *.jpeg"), ("PNG 파일", "*.png"),
                ("WEBP 파일", "*.webp"), ("BMP 파일", "*.bmp"), ("모든 파일", "*.*")
            ]
            src_path = self.resize_image_path.get().strip() if hasattr(self, "resize_image_path") else ""
            if src_path:
                out_name = self.resize_output_name.get().strip() or "resized"
                dialog_kwargs["initialfile"] = out_name + self._resize_guess_ext()
                dialog_kwargs["initialdir"] = os.path.dirname(src_path)

        elif mode == "crop_image":
            dialog_kwargs["defaultextension"] = self._crop_guess_ext()
            dialog_kwargs["filetypes"] = [
                ("PNG 파일", "*.png"), ("JPEG 파일", "*.jpg *.jpeg"),
                ("WEBP 파일", "*.webp"), ("BMP 파일", "*.bmp"), ("모든 파일", "*.*")
            ]
            src_path = self.crop_image_path.get().strip() if hasattr(self, "crop_image_path") else ""
            if src_path:
                base = os.path.splitext(os.path.basename(src_path))[0]
                dialog_kwargs["initialfile"] = f"{base}_cropped{self._crop_guess_ext()}"
                dialog_kwargs["initialdir"] = os.path.dirname(src_path)

        else:
            dialog_kwargs["defaultextension"] = ".png"
            dialog_kwargs["filetypes"] = [("PNG 파일", "*.png"), ("JPEG 파일", "*.jpg")]

        output_path = filedialog.asksaveasfilename(**dialog_kwargs)
        if not output_path:
            return

        processed_image = self._generate_processed_image()

        if processed_image:
            try:
                if mode == "resize_image":
                    self._resize_save_with_format(processed_image, output_path)
                elif mode == "crop_image":
                    self._crop_save_with_format(processed_image, output_path)
                else:
                    processed_image.save(output_path, **save_kwargs)
                messagebox.showinfo("성공", f"작업이 성공적으로 완료되어 저장되었습니다:\n{output_path}")
            except Exception as e:
                messagebox.showerror("저장 오류", f"이미지 저장 중 오류 발생: {e}")

    def merge_horizontal(self, images, gap, gap_color):
        min_height = min(img.height for img in images)
        resized_images = [img if img.height == min_height else img.resize((int(img.width * min_height / img.height), min_height), Image.Resampling.LANCZOS) for img in images]
        total_width = sum(img.width for img in resized_images) + gap * (len(resized_images) - 1)
        dst = Image.new('RGB', (total_width, min_height), gap_color)
        current_x = 0
        for img in resized_images:
            dst.paste(img, (current_x, 0)); current_x += img.width + gap
        return dst

    def merge_vertical(self, images, gap, gap_color):
        min_width = min(img.width for img in images)
        resized_images = [img if img.width == min_width else img.resize((min_width, int(img.height * min_width / img.width)), Image.Resampling.LANCZOS) for img in images]
        total_height = sum(img.height for img in resized_images) + gap * (len(resized_images) - 1)
        dst = Image.new('RGB', (min_width, total_height), gap_color)
        current_y = 0
        for img in resized_images:
            dst.paste(img, (0, current_y)); current_y += img.height + gap
        return dst

    def merge_4_grid(self, images, gap, gap_color):
        h1 = min(images[0].height, images[1].height)
        img0_r = images[0].resize((int(images[0].width * h1 / images[0].height), h1), Image.Resampling.LANCZOS)
        img1_r = images[1].resize((int(images[1].width * h1 / images[1].height), h1), Image.Resampling.LANCZOS)
        h2 = min(images[2].height, images[3].height)
        img2_r = images[2].resize((int(images[2].width * h2 / images[2].height), h2), Image.Resampling.LANCZOS)
        img3_r = images[3].resize((int(images[3].width * h2 / images[3].height), h2), Image.Resampling.LANCZOS)
        w_col1 = max(img0_r.width, img2_r.width); w_col2 = max(img1_r.width, img3_r.width)
        total_width = w_col1 + w_col2 + gap; total_height = h1 + h2 + gap
        dst = Image.new('RGB', (total_width, total_height), gap_color)
        dst.paste(img0_r, (0, 0)); dst.paste(img1_r, (w_col1 + gap, 0))
        dst.paste(img2_r, (0, h1 + gap)); dst.paste(img3_r, (w_col1 + gap, h1 + gap))
        return dst

if __name__ == "__main__":
    if 'TkinterDnD' in globals():
        root = TkinterDnD.Tk()
        app = ImageEditorApp(root)
        root.mainloop()