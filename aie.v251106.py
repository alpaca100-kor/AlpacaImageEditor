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

        master.geometry("800x600")
        master.resizable(False, False)

        self.merge_options_list = [
            ("2개 이미지 병합 (가로)", "2_horiz"),
            ("2개 이미지 병합 (세로)", "2_vert"),
            ("3개 이미지 병합 (가로)", "3_horiz"),
            ("3개 이미지 병합 (세로)", "3_vert"),
            ("4개 이미지 병합 (2x2)", "4_grid"),
            ("이미지 뒤집기", "flip_image"),
            ("이미지 회전하기", "rotate_image")
        ]
        self.active_mode_value = self.merge_options_list[0][1] 
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

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="groove", font=('Helvetica', 10))
        style.configure("TLabel", padding=5, font=('Helvetica', 10))
        style.configure("TEntry", padding=5, font=('Helvetica', 10))
        style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))
        style.configure("Listbox", font=('Helvetica', 10))
        style.configure("TCombobox", padding=5, font=('Helvetica', 10))

        style.map("TCombobox", 
                  fieldbackground=[("readonly", "white")],
                  selectbackground=[("readonly", "white")],
                  selectforeground=[("readonly", "black")]
                 )
        self.master.option_add('*TCombobox*Listbox.background', 'white')
        self.master.option_add('*TCombobox*Listbox.font', ('Helvetica', 10))
        self.master.option_add('*TCombobox*Listbox.selectBackground', '#0078D7')
        self.master.option_add('*TCombobox*Listbox.selectForeground', 'white')

        style.configure("Custom.TButton", 
                        background="#00008B",
                        foreground="white",
                        font=('Helvetica', 10, 'bold'),
                        padding=6,
                        relief="groove")
        
        style.map("Custom.TButton",
                  background=[('active', '#0000CD'), ('!disabled', '#00008B')],
                  foreground=[('!disabled', 'white')])

        # 미리보기 버튼 스타일 추가 (진한 초록색)
        style.configure("Preview.TButton", 
                        background="#2E7D32",  # 진한 초록색
                        foreground="white",
                        font=('Helvetica', 10, 'bold'),
                        padding=6,
                        relief="groove")
        
        style.map("Preview.TButton",
                  background=[('active', '#1B5E20'), ('!disabled', '#2E7D32')],
                  foreground=[('!disabled', 'white')])
        
        # 종료 버튼 스타일 추가 (진한 빨간색)
        style.configure("Exit.TButton", 
                        background="#C62828",  # 진한 빨간색
                        foreground="white",
                        font=('Helvetica', 10, 'bold'),
                        padding=6,
                        relief="groove")
        
        style.map("Exit.TButton",
                  background=[('active', '#B71C1C'), ('!disabled', '#C62828')],
                  foreground=[('!disabled', 'white')])

        top_frame = ttk.Frame(master, padding=10)
        top_frame.pack(expand=True, fill=tk.BOTH)

        left_menu_frame = ttk.LabelFrame(top_frame, text="기능 선택", padding=10)
        left_menu_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.right_options_frame = ttk.LabelFrame(top_frame, text="옵션 설정", padding=10)
        self.right_options_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        bottom_frame = ttk.Frame(master, padding="10 0 10 10")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.mode_listbox = tk.Listbox(left_menu_frame, exportselection=False, 
                                       height=len(self.merge_options_list), 
                                       font=('Helvetica', 10), relief="groove", borderwidth=2)
        for item_text, _ in self.merge_options_list:
            self.mode_listbox.insert(tk.END, item_text)
        self.mode_listbox.select_set(0) 
        self.mode_listbox.pack(anchor=tk.NW, pady=3, fill=tk.X)
        self.mode_listbox.bind("<<ListboxSelect>>", self.on_mode_select)

        button_sub_frame = ttk.Frame(bottom_frame)
        button_sub_frame.pack(pady=(0,10))

        # 미리보기 버튼 추가
        self.preview_btn = ttk.Button(button_sub_frame, text="미리보기", command=self.show_preview, style="Preview.TButton")
        self.preview_btn.pack(side=tk.LEFT, padx=5)

        self.action_btn = ttk.Button(button_sub_frame, text="실행", command=self.process_action, style="Custom.TButton")
        self.action_btn.pack(side=tk.LEFT, padx=5)

        self.exit_btn = ttk.Button(button_sub_frame, text="종료", command=master.quit, style="Exit.TButton")
        self.exit_btn.pack(side=tk.LEFT, padx=5)

        self.footer_text = "제작: 알파카100 (https://alpaca100.tistory.com/)"
        self.footer_url = "https://alpaca100.tistory.com/"
        self.footer_label = tk.Label(bottom_frame, text=self.footer_text, fg="blue", cursor="hand2", font=('Helvetica', 9))
        self.footer_label.pack(pady=(5,0))
        self.footer_label.bind("<Button-1>", lambda e: self.open_link(self.footer_url))

        self.update_options_ui()

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

    def on_mode_select(self, event=None):
        selection_indices = self.mode_listbox.curselection()
        if selection_indices:
            selected_index = selection_indices[0]
            _, self.active_mode_value = self.merge_options_list[selected_index]
            self.update_options_ui()

    def update_options_ui(self):
        for widget in self.right_options_frame.winfo_children():
            widget.destroy()
        
        self.image_paths_entries.clear(); self.browse_buttons.clear(); self.image_labels.clear()

        mode = self.active_mode_value
        current_row = 0

        if mode in ["2_horiz", "2_vert", "3_horiz", "3_vert", "4_grid"]:
            num_images = 2 if mode in ["2_horiz", "2_vert"] else \
                         3 if mode in ["3_horiz", "3_vert"] else \
                         4 if mode == "4_grid" else 0

            for i in range(num_images):
                label = ttk.Label(self.right_options_frame, text=f"이미지 {i+1}:")
                label.grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=5)
                self.image_labels.append(label)

                entry = ttk.Entry(self.right_options_frame, width=60, state="readonly")
                entry.grid(row=current_row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
                self.image_paths_entries.append(entry)
                entry.drop_target_register(DND_FILES)
                entry.dnd_bind('<<Drop>>', lambda event, e=entry: self.handle_drop(event, e))

                button = ttk.Button(self.right_options_frame, text="찾아보기", command=lambda e=entry: self.browse_file(e))
                button.grid(row=current_row, column=3, padx=5, pady=5)
                self.browse_buttons.append(button)
                current_row += 1
            
            self._create_merge_options_widgets(current_row)

        elif mode == "flip_image":
            ttk.Label(self.right_options_frame, text="대상 이미지:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=5)
            self.single_image_entry = ttk.Entry(self.right_options_frame, width=60, state="readonly")
            self.single_image_entry.grid(row=current_row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
            self.single_image_entry.drop_target_register(DND_FILES)
            self.single_image_entry.dnd_bind('<<Drop>>', lambda event, e=self.single_image_entry: self.handle_drop(event, e))
            ttk.Button(self.right_options_frame, text="찾아보기", command=lambda: self.browse_file(self.single_image_entry)).grid(row=current_row, column=3, padx=5, pady=5)
            current_row += 1

            ttk.Label(self.right_options_frame, text="뒤집기 옵션:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=5)
            self.flip_options_combobox = ttk.Combobox(self.right_options_frame, 
                                                      values=["좌우 뒤집기", "상하 뒤집기", "상하/좌우 뒤집기"],
                                                      state="readonly", font=('Helvetica', 10))
            self.flip_options_combobox.set("좌우 뒤집기")
            self.flip_options_combobox.grid(row=current_row, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
            self.flip_options_combobox.bind("<FocusOut>", self.validate_combobox)
            current_row += 1

        elif mode == "rotate_image":
            ttk.Label(self.right_options_frame, text="대상 이미지:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=5)
            self.single_image_entry = ttk.Entry(self.right_options_frame, width=60, state="readonly")
            self.single_image_entry.grid(row=current_row, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
            self.single_image_entry.drop_target_register(DND_FILES)
            self.single_image_entry.dnd_bind('<<Drop>>', lambda event, e=self.single_image_entry: self.handle_drop(event, e))
            ttk.Button(self.right_options_frame, text="찾아보기", command=lambda: self.browse_file(self.single_image_entry)).grid(row=current_row, column=3, padx=5, pady=5)
            current_row += 1

            ttk.Label(self.right_options_frame, text="회전 각도:").grid(row=current_row, column=0, sticky=tk.W, padx=5, pady=5)
            self.rotate_options_combobox = ttk.Combobox(self.right_options_frame, 
                                                       values=["시계 방향으로 90°", "시계 방향으로 180°", "시계 방향으로 270°"],
                                                       state="readonly", font=('Helvetica', 10))
            self.rotate_options_combobox.set("시계 방향으로 90°")
            self.rotate_options_combobox.grid(row=current_row, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
            self.rotate_options_combobox.bind("<FocusOut>", self.validate_combobox)
            current_row += 1

        self.right_options_frame.columnconfigure(1, weight=1)

    def _create_merge_options_widgets(self, start_row):
        """병합 모드에 필요한 옵션 위젯들을 생성합니다."""
        ttk.Label(self.right_options_frame, text="여백 크기 (px):").grid(row=start_row, column=0, sticky=tk.W, padx=5, pady=(10,5))
        self.gap_spinbox = tk.Spinbox(self.right_options_frame, from_=0, to=100, width=7, increment=1, font=('Helvetica', 10))
        self.gap_spinbox.delete(0,"end"); self.gap_spinbox.insert(0,"10")
        self.gap_spinbox.grid(row=start_row, column=1, sticky=tk.W, padx=5, pady=(10,5))
        
        ttk.Label(self.right_options_frame, text="여백 색상:").grid(row=start_row + 1, column=0, sticky=tk.W, padx=5, pady=5)
        self.gap_color_preview = self._create_color_picker(start_row + 1, self.current_gap_color)
        
        ttk.Label(self.right_options_frame, text="최종 이미지 테두리 굵기 (px):").grid(row=start_row + 2, column=0, sticky=tk.W, padx=5, pady=(10,5))
        self.border_spinbox = tk.Spinbox(self.right_options_frame, from_=0, to=50, width=7, increment=1, font=('Helvetica', 10))
        self.border_spinbox.delete(0,"end"); self.border_spinbox.insert(0,"0")
        self.border_spinbox.grid(row=start_row + 2, column=1, sticky=tk.W, padx=5, pady=(10,5))

        ttk.Label(self.right_options_frame, text="최종 이미지 테두리 색상:").grid(row=start_row + 3, column=0, sticky=tk.W, padx=5, pady=5)
        self.border_color_preview = self._create_color_picker(start_row + 3, self.current_border_color)

    def _create_color_picker(self, row, color_variable):
        """지정된 행에 색상 선택 위젯 세트를 생성하고 미리보기 레이블을 반환합니다."""
        preview_label = tk.Label(self.right_options_frame, text="    ", bg=color_variable.get(), relief="sunken", width=4, borderwidth=2)
        preview_label.grid(row=row, column=1, sticky=tk.W, padx=(5,0), pady=5)
        
        hex_entry = ttk.Entry(self.right_options_frame, textvariable=color_variable, width=10, font=('Helvetica', 10))
        hex_entry.grid(row=row, column=1, sticky=tk.W, padx=(50,5), pady=5)
        
        choose_button = ttk.Button(self.right_options_frame, text="색상표...", command=lambda: self._choose_color(color_variable, preview_label))
        choose_button.grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)

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
        output_path = filedialog.asksaveasfilename(title="결과 이미지 저장 위치 선택", defaultextension=".png", filetypes=[("PNG 파일", "*.png"), ("JPEG 파일", "*.jpg")])
        if not output_path: return

        processed_image = self._generate_processed_image()
        
        if processed_image:
            try:
                processed_image.save(output_path)
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