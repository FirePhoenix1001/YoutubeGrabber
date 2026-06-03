import os
import sys
import subprocess

def get_tool_path(filename):
    """
    採用 BASE_PATH 邏輯：檢查順序為 根目錄 -> tools 資料夾 -> src -> CWD -> CWD/tools
    """
    IS_BUNDLE = hasattr(sys, '_MEIPASS')
    BASE_PATH = sys._MEIPASS if IS_BUNDLE else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 檢查位置清單
    search_paths = [
        BASE_PATH,
        os.path.join(BASE_PATH, "tools"),
        os.path.join(BASE_PATH, "src"),
        os.getcwd(),
        os.path.join(os.getcwd(), "tools")
    ]
    
    for d in search_paths:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return path
    return os.path.join(BASE_PATH, filename)

def download_video(url, mode, progress_callback=None):
    ffmpeg_path = get_tool_path('ffmpeg.exe')
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    ytdlp_path = get_tool_path('yt-dlp.exe')
    
    if not os.path.exists(ytdlp_path):
        raise FileNotFoundError(f"找不到 yt-dlp.exe，請確認元件安裝狀態。")

    # 輸出檔名格式 (直接輸出在當前工作目錄)
    if mode == "1": # 僅影像
        outtmpl = "./%(title)s_video.%(ext)s"
        fmt = "bestvideo"
    elif mode == "2": # 僅聲音
        outtmpl = "./%(title)s_audio.%(ext)s"
        fmt = "bestaudio/best"
    elif mode == "3": # 合併
        outtmpl = "./%(title)s.%(ext)s"
        fmt = "bestvideo+bestaudio/best"
        
    cmd = [
        ytdlp_path,
        url,
        "-o", outtmpl,
        "-f", fmt,
        "--ffmpeg-location", ffmpeg_dir,
        "--no-playlist",
        "--progress",
        "--no-check-certificate",
        "--referer", "https://www.youtube.com/",
        "--extractor-args", "youtube:player_client=default,-android_sdkless"
    ]
    
    # 支援自動動態解密腳本載入
    cmd.extend(["--remote-components", "ejs:github"])
    
    if mode == "2":
        cmd.extend([
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "192K"
        ])
        
    print(f"正在分析連結並啟動 yt-dlp 核心引擎... 📥")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore',
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        for line in proc.stdout:
            line_str = line.strip()
            if not line_str:
                continue
                
            # 處理下載百分比
            if "[download]" in line_str:
                # 典型進度：[download]  12.5% of 100.00MiB...
                try:
                    parts = line_str.split()
                    for p in parts:
                        if "%" in p:
                            pct_val = float(p.replace("%", "").strip())
                            if progress_callback:
                                progress_callback(pct_val / 100)
                            break
                except:
                    pass
            else:
                # 其他輸出直接串流列印至 UI 日誌框
                print(line_str)
                
        proc.wait()
        if proc.returncode != 0:
            raise Exception(f"yt-dlp 下載失敗，錯誤碼: {proc.returncode}")
            
    except Exception as e:
        print(f"下載任務發生異常: {str(e)}")
        raise e
