import yt_dlp
import os
import sys

def get_tool_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

FFMPEG_PATH = get_tool_path('ffmpeg.exe')

def download_video(url, mode, progress_callback=None):
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            p_str = d.get('_percent_str', '0%').replace('%', '')
            try:
                progress = float(p_str) / 100
                if progress_callback:
                    progress_callback(progress)
            except:
                pass
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback(1.0)
            print(f"\n下載完成: {d.get('filename', 'unknown')}")

    # 基礎設定
    ydl_opts = {
        "ffmpeg_location": ffmpeg_dir,
        "ignoreerrors": True,
        "progress_hooks": [progress_hook],
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        # ★ 新增：強制覆蓋同名檔案 (避免因為檔案已存在而跳過)
        "overwrites": True, 
    }

    # ★ 根據模式設定「檔名」與「格式」
    if mode == "1": # 僅影像
        # 檔名加上 _video
        ydl_opts["outtmpl"] = "./%(title)s_video.%(ext)s"
        ydl_opts["format"] = "bestvideo"
        
    elif mode == "2": # 僅聲音
        # 檔名加上 _audio
        ydl_opts["outtmpl"] = "./%(title)s_audio.%(ext)s"
        ydl_opts["format"] = "bestaudio/best"
        # ★ 特效藥：針對聲音模式，強制轉檔為 mp3
        ydl_opts["postprocessors"] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        
    elif mode == "3": # 合併
        # 維持原檔名，最乾淨
        ydl_opts["outtmpl"] = "./%(title)s.%(ext)s"
        ydl_opts["format"] = "bestvideo+bestaudio/best"
    
    print(f"正在連線並解析影片資訊... (模式: {mode})")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])