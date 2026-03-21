import os
import sys
import yt_dlp

def get_tool_path(filename):
    """
    採用 BASE_PATH 邏輯：檢查順序為 根目錄 -> tools 資料夾
    """
    IS_BUNDLE = hasattr(sys, '_MEIPASS')
    BASE_PATH = sys._MEIPASS if IS_BUNDLE else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 檢查位置清單
    search_paths = [
        BASE_PATH,
        os.path.join(BASE_PATH, "tools"),
        os.path.join(BASE_PATH, "src")
    ]
    
    for d in search_paths:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return path
    return os.path.join(BASE_PATH, filename)

FFMPEG_PATH = get_tool_path('ffmpeg.exe')

# ★ 新增：建立一個安靜的 Logger，防止系統訊息亂噴
class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): 
        print(f"核心報錯: {msg}") # 只留錯誤訊息

def download_video(url, mode, progress_callback=None):
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            try:
                p_str = d.get('_percent_str', '0%').replace('%', '')
                if progress_callback:
                    progress_callback(float(p_str) / 100)
            except:
                pass
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback(1.0)
            print(f"\n檔案處理中: {d.get('filename', 'unknown')}")

    # ★ 這裡這兩行能大幅降低 403 報錯率
    ydl_opts = {
        "ffmpeg_location": ffmpeg_dir,
        "progress_hooks": [progress_hook],
        "logger": MyLogger(),           # ★ 套用安靜 Logger
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "referer": "https://www.youtube.com/",
        "remote_components": ["ejs:github"], # 實現核心腳本自動更新
        "extractor_args": {
            "youtube": {
                "player_client": ["default", "-android_sdkless"]
            }
        },
        "overwrites": True, 
    }

    if mode == "1": # 僅影像
        ydl_opts["outtmpl"] = "./%(title)s_video.%(ext)s"
        ydl_opts["format"] = "bestvideo"
    elif mode == "2": # 僅聲音
        ydl_opts["outtmpl"] = "./%(title)s_audio.%(ext)s"
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif mode == "3": # 合併
        ydl_opts["outtmpl"] = "./%(title)s.%(ext)s"
        ydl_opts["format"] = "bestvideo+bestaudio/best"
    
    print(f"解析連結中 (自動核心腳本模式: 開啟)...")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            print(f"下載失敗: {e}")
            raise e
