# src/updater.py
import os
import sys
import json
import urllib.request
import zipfile
import shutil
import tempfile

# =====================================================================
#             🌻 解決 PyInstaller console=False 時 sys.stdout 為 None 的問題
# =====================================================================
class DummyWriter:
    def write(self, *args, **kwargs):
        pass
    def flush(self, *args, **kwargs):
        pass

if sys.stdout is None:
    sys.stdout = DummyWriter()
if sys.stderr is None:
    sys.stderr = DummyWriter()

# =====================================================================
#             🌻 用以追蹤更新進度與狀態的全域變數
# =====================================================================
current_status = "idle"       # "idle", "checking", "updating", "ready", "error"
current_progress = 0          # 0 - 100 之間
current_error = ""            # 錯誤訊息

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_PATH = get_base_path()
TOOLS_DIR = os.path.join(BASE_PATH, "tools")
VERSION_FILE = os.path.join(TOOLS_DIR, "version.json")

YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_VER_URL = "https://www.gyan.dev/ffmpeg/builds/release-version"
YT_DLP_API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"

def read_local_versions():
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[更新器] 讀取本地版本檔失敗，將重置版本資訊。錯誤: {e}")
    return {"yt-dlp": "", "ffmpeg": ""}

def write_local_versions(versions):
    try:
        with open(VERSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(versions, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[更新器] 寫入本地版本檔失敗: {e}")

def get_latest_versions_online():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    latest = {"yt-dlp": None, "ffmpeg": None}

    try:
        req = urllib.request.Request(YT_DLP_API_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            latest["yt-dlp"] = data.get("tag_name", "").strip()
    except Exception as e:
        print(f"[更新器] 無法獲取遠端 yt-dlp 版本: {e}")

    try:
        req = urllib.request.Request(FFMPEG_VER_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            latest["ffmpeg"] = response.read().decode('utf-8').strip()
    except Exception as e:
        print(f"[更新器] 無法獲取遠端 ffmpeg 版本: {e}")

    return latest

def download_file(url, dest_path, label="下載中"):
    global current_progress
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=60) as response:
        total_size = int(response.info().get('Content-Length', 0))
        bytes_so_far = 0
        chunk_size = 1024 * 128
        
        with open(dest_path, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                bytes_so_far += len(chunk)
                if total_size > 0:
                    percent = (bytes_so_far / total_size) * 100
                    current_progress = int(percent)
                    bar_length = 30
                    filled_length = int(bar_length * bytes_so_far // total_size)
                    bar = '=' * filled_length + '-' * (bar_length - filled_length)
                    sys.stdout.write(f"\r{label}: [{bar}] {percent:.1f}% ({bytes_so_far // 1024} KB / {total_size // 1024} KB)")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r{label}: 已下載 {bytes_so_far // 1024} KB")
                    sys.stdout.flush()
        print()

def extract_ffmpeg_from_zip(zip_path):
    print("[更新器] 正在解壓縮 ffmpeg & ffprobe...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.namelist():
            filename = os.path.basename(member)
            if filename in ['ffmpeg.exe', 'ffprobe.exe']:
                if 'bin/' in member:
                    target_path = os.path.join(TOOLS_DIR, filename)
                    if os.path.exists(target_path):
                        try:
                            os.remove(target_path)
                        except Exception as e:
                            print(f"[更新器] 無法移除舊的 {filename}，可能程式正在佔用中: {e}")
                            raise e
                    
                    with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    print(f"[更新器] 已成功解壓並安裝: {filename}")

def check_and_update_tools():
    """主進入點：檢查並更新 tools 外部工具"""
    global current_status, current_progress, current_error
    current_status = "checking"
    current_progress = 0
    current_error = ""

    print("=" * 50)
    print(f"[更新器] 開始檢查外部相依工具...")
    print(f"[更新器] 目標目錄: {TOOLS_DIR}")
    print("=" * 50)
    
    os.makedirs(TOOLS_DIR, exist_ok=True)
    
    local_versions = read_local_versions()
    yt_dlp_path = os.path.join(TOOLS_DIR, "yt-dlp.exe")
    ffmpeg_path = os.path.join(TOOLS_DIR, "ffmpeg.exe")
    ffprobe_path = os.path.join(TOOLS_DIR, "ffprobe.exe")
    
    has_yt_dlp = os.path.exists(yt_dlp_path)
    has_ffmpeg = os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path)
    
    print("[更新器] 正在連網檢查最新版本...")
    online_versions = get_latest_versions_online()
    
    is_offline = (online_versions["yt-dlp"] is None) or (online_versions["ffmpeg"] is None)
    if is_offline:
        print("[更新器] [警告] 無法連接更新伺服器，將切換為「離線模式」。")
        if has_yt_dlp and has_ffmpeg:
            print("[更新器] 本地工具完整，將直接啟動程式。")
            current_status = "ready"
            return True
        else:
            missing = []
            if not has_yt_dlp: missing.append("yt-dlp.exe")
            if not has_ffmpeg: missing.append("ffmpeg.exe/ffprobe.exe")
            err_msg = f"缺少必要工具 {missing} 且無法連網下載！"
            print(f"[更新器] [錯誤] 嚴重錯誤：{err_msg}")
            current_status = "error"
            current_error = err_msg
            return False

    current_status = "updating"

    # 3. 處理 yt-dlp 更新與下載
    need_yt_dlp = not has_yt_dlp or (local_versions.get("yt-dlp") != online_versions["yt-dlp"])
    if need_yt_dlp:
        print(f"[更新器] 發現 yt-dlp 新版本: {online_versions['yt-dlp']} (本地: {local_versions.get('yt-dlp') or '無'})")
        try:
            temp_file = tempfile.mktemp(dir=TOOLS_DIR)
            download_file(YT_DLP_URL, temp_file, label="下載 yt-dlp.exe")
            
            if os.path.exists(yt_dlp_path):
                os.remove(yt_dlp_path)
            os.rename(temp_file, yt_dlp_path)
            
            local_versions["yt-dlp"] = online_versions["yt-dlp"]
            write_local_versions(local_versions)
            print("[更新器] yt-dlp.exe 更新成功！")
        except Exception as e:
            err_msg = f"下載 yt-dlp.exe 失敗: {e}"
            print(f"[更新器] [錯誤] {err_msg}")
            if not has_yt_dlp:
                current_status = "error"
                current_error = err_msg
                return False
    else:
        print(f"[更新器] yt-dlp.exe 已是最新版本 ({local_versions.get('yt-dlp')})")

    # 4. 處理 ffmpeg/ffprobe 更新與下載
    need_ffmpeg = not has_ffmpeg or (local_versions.get("ffmpeg") != online_versions["ffmpeg"])
    if need_ffmpeg:
        print(f"[更新器] 發現 ffmpeg 新版本: {online_versions['ffmpeg']} (本地: {local_versions.get('ffmpeg') or '無'})")
        temp_zip = os.path.join(TOOLS_DIR, "ffmpeg_temp.zip")
        try:
            download_file(FFMPEG_URL, temp_zip, label="下載 ffmpeg-release.zip")
            extract_ffmpeg_from_zip(temp_zip)
            
            local_versions["ffmpeg"] = online_versions["ffmpeg"]
            write_local_versions(local_versions)
            print("[更新器] ffmpeg & ffprobe 更新成功！")
        except Exception as e:
            err_msg = f"下載或解壓 ffmpeg 失敗: {e}"
            print(f"[更新器] [錯誤] {err_msg}")
            if not has_ffmpeg:
                current_status = "error"
                current_error = err_msg
                return False
        finally:
            if os.path.exists(temp_zip):
                try:
                    os.remove(temp_zip)
                except:
                    pass
    else:
        print(f"[更新器] ffmpeg & ffprobe 已是最新版本 ({local_versions.get('ffmpeg')})")

    print("[更新器] [成功] 所有外部相依工具準備就緒！")
    current_status = "ready"
    return True

if __name__ == "__main__":
    success = check_and_update_tools()
    if success:
        print("\n[測試結果] 成功：工具已就緒。")
    else:
        print("\n[測試結果] 失敗：缺少必要工具且無法下載。")
