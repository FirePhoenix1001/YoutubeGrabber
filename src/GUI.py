import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import subprocess
import threading
import youtubeDownload
import mediaCut

# ==========================================
#           🎨 主題與字體設定
# ==========================================
THEME = {
    "bg_color": "#ECE2C4",      # 背景色：奶油米白 (讓介面看起來很溫暖)
    "yellow": "#FFC107",        # 向日葵黃 (主按鈕)
    "yellow_dark": "#FFA000",   # 深黃色 (按鈕懸停)
    "brown": "#5D4037",         # 深褐色 (次要按鈕)
    "brown_dark": "#3E2723",    # 更深的褐色 (懸停)
    "text_on_yellow": "#3E2723",# 黃按鈕上的字 (深褐)
    "text_white": "#CDCDCD",    # 褐按鈕上的字 (白)
    "frame_bg": "#FFF3D0",      # 分區塊的背景 (純白，讓區塊分明)
}

# ★ 新增：字體設定 (這裡可以隨意更改)
# 如果您的電腦有安裝 "源柔哥特" 或 "圓體"，改這裡會變得超級可愛！
FONTS = {
    "main": ("Microsoft JhengHei UI", 12),          # 一般文字
    "bold": ("Microsoft JhengHei UI", 13, "bold"),  # 標題與按鈕
    "log":  ("Consolas", 10),                       # 日誌區 (等寬字體)
    "time": ("Arial", 14, "bold")                   # 時間輸入框 (數字用 Arial 比較清楚)
}

# ==========================================
#           日誌重導向工具
# ==========================================
class PrintLogger:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, text):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def flush(self):
        pass

# ==========================================
#           核心路徑設定
# ==========================================
def get_tool_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

FFMPEG_PATH = get_tool_path('ffmpeg.exe')
FFPROBE_PATH = get_tool_path('ffprobe.exe')

def get_video_duration(file_path):
    try:
        command = [
            FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        duration_sec = float(result.stdout.strip())
        m, s = divmod(duration_sec, 60)
        h, m = divmod(m, 60)
        return int(h), int(m), int(s)
    except:
        return 0, 0, 10

# ==========================================
#               主程式 App
# ==========================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Youtube 擷取工具 - 向日葵特別版 🌻")
        self.geometry("620x580") # 稍微加寬一點點，因為正黑體比較寬
        self.minsize(600, 450)
        
        ctk.set_appearance_mode("Light") 
        self.configure(fg_color=THEME["bg_color"])

        # ★★★ 新增：設定視窗 Icon ★★★
        # 使用 get_tool_path 確保打包後也能找到
        icon_path = get_tool_path("sunflower.ico")
        
        # 加一個檢查，避免檔案不見時程式閃退
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        else:
            print(f"警告: 找不到 Icon 檔案 ({icon_path})")
        # ★★★ 結束新增 ★★★

        self.selected_file_path = ""
        self.last_output_path = ""
        self.create_widgets()
        
        self.logger = PrintLogger(self.log_box)
        sys.stdout = self.logger
        sys.stderr = self.logger
        
        print("--- 向日葵系統初始化完成 🌻 ---")
        # print("已套用字體：微軟正黑體 (Microsoft JhengHei UI)")

    def create_widgets(self):
        # 1. 上半部：分頁功能區
        self.tabview = ctk.CTkTabview(self, height=300, 
                                      fg_color=THEME["frame_bg"],
                                      text_color=THEME["brown"],
                                      segmented_button_fg_color=THEME["frame_bg"],
                                      segmented_button_selected_color=THEME["yellow"],
                                      segmented_button_selected_hover_color=THEME["yellow_dark"],
                                      segmented_button_unselected_hover_color="#EEE")
        self.tabview.pack(fill="x", padx=20, pady=10)
        
        # ★ 套用字體到分頁按鈕 (可惜 CTkTabview 的字體設定比較隱晦，這裡主要設定內容)
        # 我們直接設定內部的 Font
        self.tabview._segmented_button.configure(font=FONTS["bold"])

        self.tab_down = self.tabview.add("下載 YouTube")
        self.tab_cut = self.tabview.add("本地剪輯")

        self.setup_download_tab()
        self.setup_cut_tab()

        # 2. 中間：進度條區
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(self.progress_frame, text="執行進度:", text_color=THEME["brown"], font=FONTS["bold"]).pack(side="left", padx=5)
        
        self.progressbar = ctk.CTkProgressBar(self.progress_frame, orientation="horizontal", 
                                              progress_color=THEME["yellow"],
                                              fg_color="#E0E0E0")
        self.progressbar.pack(side="left", fill="x", expand=True, padx=10)
        self.progressbar.set(0)

        # 3. 下半部：日誌區
        self.log_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        log_header = ctk.CTkFrame(self.log_frame, height=30, fg_color="transparent")
        log_header.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(log_header, text="系統日誌 (Log)", font=FONTS["bold"], text_color=THEME["brown"]).pack(side="left", padx=5)
        
        ctk.CTkButton(log_header, text="🗑 清空日誌", width=80, height=24, font=FONTS["main"],
                      fg_color=THEME["brown"], hover_color=THEME["brown_dark"], text_color=THEME["text_white"],
                      command=self.clear_log).pack(side="right", padx=5)

        # ★ 日誌區使用 Log 字體 (Consolas)
        self.log_box = ctk.CTkTextbox(self.log_frame, state="disabled", font=FONTS["log"],
                                      fg_color="white", text_color="black")
        self.log_box.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_download_tab(self):
        frame = self.tab_down
        
        # ★ 輸入框字體
        self.entry_url = ctk.CTkEntry(frame, placeholder_text="在此貼上影片網址...", width=400, font=FONTS["main"],
                                      fg_color="white", text_color="black", placeholder_text_color="gray")
        self.entry_url.pack(pady=10)

        self.download_mode_var = ctk.StringVar(value="3")
        radio_frame = ctk.CTkFrame(frame, fg_color="transparent")
        radio_frame.pack(pady=5)
        
        radio_style = {"fg_color": THEME["yellow"], "hover_color": THEME["yellow_dark"], "text_color": THEME["brown"], "font": FONTS["main"]}
        ctk.CTkRadioButton(radio_frame, text="僅影像", variable=self.download_mode_var, value="1", **radio_style).pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="僅聲音", variable=self.download_mode_var, value="2", **radio_style).pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="合併 (推薦)", variable=self.download_mode_var, value="3", **radio_style).pack(side="left", padx=10)

        # ★ 按鈕字體
        ctk.CTkButton(frame, text="開始下載", command=self.start_download_thread, height=40, font=FONTS["bold"],
                      fg_color=THEME["yellow"], hover_color=THEME["yellow_dark"], 
                      text_color=THEME["text_on_yellow"]).pack(pady=10)
        
        ctk.CTkButton(frame, text="📂 開啟程式資料夾", width=140, command=self.open_app_folder, font=FONTS["main"],
                      fg_color=THEME["brown"], hover_color=THEME["brown_dark"], text_color=THEME["text_white"]).pack(pady=5)

    def setup_cut_tab(self):
        frame = self.tab_cut
        
        file_frame = ctk.CTkFrame(frame, fg_color="transparent")
        file_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(file_frame, text="📂 選擇影片...", width=120, command=self.on_select_file_click, font=FONTS["main"],
                      fg_color=THEME["brown"], hover_color=THEME["brown_dark"], text_color=THEME["text_white"]).pack(side="left", padx=10, pady=10)
        
        self.lbl_filename = ctk.CTkLabel(file_frame, text="尚未選擇", text_color=THEME["yellow_dark"], anchor="w", font=FONTS["main"])
        self.lbl_filename.pack(side="left", padx=10, fill="x", expand=True)

        self.btn_play_system = ctk.CTkButton(frame, text="▶ 系統預覽 (查看時間)", command=self.open_in_system_player, state="disabled",
                                             fg_color=THEME["brown"], hover_color=THEME["brown_dark"], text_color=THEME["text_white"], font=FONTS["main"])
        self.btn_play_system.pack(fill="x", padx=20, pady=5)

        # 時間輸入區
        time_container = ctk.CTkFrame(frame, fg_color="transparent")
        time_container.pack(pady=10)

        label_style = {"text_color": THEME["brown"], "font": FONTS["bold"]}
        ctk.CTkLabel(time_container, text="開始", **label_style).grid(row=0, column=0, padx=5)
        self.frame_start = ctk.CTkFrame(time_container, fg_color="transparent")
        self.frame_start.grid(row=1, column=0, padx=5)
        self.start_h = self.create_time_entry(self.frame_start, "00")
        self.create_colon(self.frame_start)
        self.start_m = self.create_time_entry(self.frame_start, "00")
        self.create_colon(self.frame_start)
        self.start_s = self.create_time_entry(self.frame_start, "00")

        ctk.CTkLabel(time_container, text="結束", **label_style).grid(row=0, column=1, padx=5)
        self.frame_end = ctk.CTkFrame(time_container, fg_color="transparent")
        self.frame_end.grid(row=1, column=1, padx=5)
        self.end_h = self.create_time_entry(self.frame_end, "00")
        self.create_colon(self.frame_end)
        self.end_m = self.create_time_entry(self.frame_end, "00")
        self.create_colon(self.frame_end)
        self.end_s = self.create_time_entry(self.frame_end, "00")

        ctk.CTkButton(frame, text="✂️ 執行剪輯", command=self.on_cut_click, height=40, font=FONTS["bold"],
                      fg_color=THEME["yellow"], hover_color=THEME["yellow_dark"],
                      text_color=THEME["text_on_yellow"]).pack(fill="x", padx=20, pady=10)

        res_frame = ctk.CTkFrame(frame, fg_color="transparent")
        res_frame.pack(fill="x", padx=20)
        
        self.btn_open_folder = ctk.CTkButton(res_frame, text="開啟位置", state="disabled", width=100, command=self.open_result_folder,
                                             fg_color=THEME["brown"], hover_color=THEME["brown_dark"], text_color=THEME["text_white"], font=FONTS["main"])
        self.btn_open_folder.pack(side="left", padx=2)
        
        self.btn_preview_result = ctk.CTkButton(res_frame, text="播放結果", state="disabled", width=100, command=self.play_cut_result,
                                                fg_color=THEME["yellow"], hover_color=THEME["yellow_dark"], text_color=THEME["text_on_yellow"], font=FONTS["main"])
        self.btn_preview_result.pack(side="right", padx=2)

    def create_time_entry(self, parent, default_val):
        # ★ 時間輸入框使用 Time 字體 (Arial Bold)
        entry = ctk.CTkEntry(parent, width=35, justify="center", fg_color="white", text_color="black", font=FONTS["time"])
        entry.insert(0, default_val)
        entry.pack(side="left", padx=1)
        entry.bind("<FocusOut>", self.format_time_input)
        entry.bind("<Return>", self.format_time_input)
        return entry

    def create_colon(self, parent):
        ctk.CTkLabel(parent, text=":", font=FONTS["time"], text_color=THEME["brown"]).pack(side="left")

    def format_time_input(self, event):
        entry = event.widget
        val = entry.get().strip()
        if val.isdigit():
            formatted = f"{int(val):02d}"
            entry.delete(0, "end")
            entry.insert(0, formatted)
        elif val == "":
            entry.delete(0, "end")
            entry.insert(0, "00")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def start_download_thread(self):
        url = self.entry_url.get()
        if not url: return
        self.progressbar.set(0)
        print(f"準備下載: {url}")
        threading.Thread(target=self.run_download, args=(url,), daemon=True).start()

    def run_download(self, url):
        mode = self.download_mode_var.get()
        try:
            youtubeDownload.download_video(url, mode, progress_callback=self.update_progress)
            self.progressbar.set(1)
            print("下載任務結束。")
            messagebox.showinfo("成功", "下載完成！")
        except Exception as e:
            print(f"錯誤: {e}")
            messagebox.showerror("錯誤", str(e))

    def update_progress(self, val):
        self.progressbar.set(val)

    def on_cut_click(self):
        if not self.selected_file_path: return
        start = self.get_time_string(self.start_h, self.start_m, self.start_s)
        end = self.get_time_string(self.end_h, self.end_m, self.end_s)
        
        print(f"開始剪輯: {start} -> {end}")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()
        self.after(100, lambda: self.run_cut(start, end))

    def run_cut(self, start, end):
        success, result = mediaCut.cut_video(self.selected_file_path, start, end)
        self.progressbar.stop()
        self.progressbar.configure(mode="determinate")
        self.progressbar.set(1)
        
        if success:
            print(f"剪輯成功: {result}")
            self.last_output_path = result
            self.btn_open_folder.configure(state="normal")
            self.btn_preview_result.configure(state="normal")
            messagebox.showinfo("成功", "剪輯完成！")
        else:
            print(f"剪輯失敗: {result}")
            messagebox.showerror("失敗", result)

    def open_app_folder(self):
        os.startfile(os.path.normpath(os.getcwd()))
        
    def open_in_system_player(self):
        if self.selected_file_path: os.startfile(self.selected_file_path)

    def open_result_folder(self):
        if self.last_output_path: subprocess.run(['explorer', '/select,', os.path.normpath(self.last_output_path)])

    def play_cut_result(self):
        if self.last_output_path: os.startfile(self.last_output_path)

    def on_select_file_click(self):
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mkv *.webm *.mov *.avi *.mp3")])
        if path:
            self.selected_file_path = path
            self.lbl_filename.configure(text=os.path.basename(path), text_color=THEME["yellow_dark"])
            self.btn_play_system.configure(state="normal")
            self.btn_open_folder.configure(state="disabled")
            self.btn_preview_result.configure(state="disabled")
            
            h, m, s = get_video_duration(path)
            
            self.set_time_inputs(self.start_h, self.start_m, self.start_s, 0, 0, 0)
            
            self.set_time_inputs(self.end_h, self.end_m, self.end_s, h, m, s)
            print(f"已載入影片，長度: {h}:{m}:{s}")

    def set_time_inputs(self, eh, em, es, h, m, s):
        eh.delete(0, "end"); eh.insert(0, f"{h:02d}")
        em.delete(0, "end"); em.insert(0, f"{m:02d}")
        es.delete(0, "end"); es.insert(0, f"{s:02d}")

    def get_time_string(self, h, m, s):
        return f"{int(h.get() or 0):02d}:{int(m.get() or 0):02d}:{int(s.get() or 0):02d}"

if __name__ == "__main__":
    app = App()
    app.mainloop()