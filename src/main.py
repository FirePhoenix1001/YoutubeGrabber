# src/web_server.py
import os
import sys
import queue
import threading
import subprocess
import zipfile
import tempfile
import urllib.request
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# Add parent directory to path so imports work correctly when executing web_server.py directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import youtubeDownload
import mediaCut
from audioProcessor import AudioProcessor

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Global Thread-Safe Queue for logs and progress streaming
log_queue = queue.Queue()
original_stdout = sys.stdout
original_stderr = sys.stderr

# Custom Logger to intercept stdout/stderr prints
class QueueLogger:
    def __init__(self, q, stream):
        self.q = q
        self.stream = stream

    def write(self, text):
        if text:
            # If text is bytes, decode it to string for queue
            if isinstance(text, bytes):
                try:
                    text = text.decode(getattr(self.stream, 'encoding', 'utf-8') or 'utf-8', errors='replace')
                except Exception:
                    text = str(text)

            # 阻擋 Werkzeug 的 HTTP 連線存取日誌、Flask 啟動日誌及重複的 poller 輪詢
            if "127.0.0.1 - - [" in text:
                return
            if "Serving Flask app" in text or "Debug mode:" in text or "WARNING: This is a development server" in text or "Press CTRL+C to quit" in text or "Running on http://" in text:
                return
            if "GET /api/status" in text or "GET /api/files" in text:
                return

            # Put string log into the queue
            self.q.put(text)

            # Write to the original terminal stream safely
            try:
                self.stream.write(text)
            except UnicodeEncodeError:
                encoding = getattr(self.stream, 'encoding', 'utf-8') or 'utf-8'
                clean_text = text.encode(encoding, errors='replace').decode(encoding)
                try:
                    self.stream.write(clean_text)
                except Exception:
                    pass
            except TypeError:
                try:
                    encoding = getattr(self.stream, 'encoding', 'utf-8') or 'utf-8'
                    self.stream.write(text.encode(encoding, errors='replace'))
                except Exception:
                    pass
            except Exception:
                pass

    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass

# Redirect standard outputs to our QueueLogger
sys.stdout = QueueLogger(log_queue, original_stdout)
sys.stderr = QueueLogger(log_queue, original_stderr)

# Global states
running_task = {
    "active": False,
    "type": None,  # "download", "cut", "transcribe"
    "progress": 0.0
}
audio_processor = None

def progress_callback(val):
    """Sends progress markers directly into the log stream"""
    running_task["progress"] = val
    log_queue.put(f"[PROGRESS] {int(val * 100)}\n")

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/status')
def get_status():
    return jsonify(running_task)

@app.route('/api/stream-logs')
def stream_logs():
    def event_generator():
        yield "data: [SYSTEM] 成功連接至向日葵日誌串流服務... 🌻\n\n"
        while True:
            try:
                # Wait for logs for up to 1 second
                log_msg = log_queue.get(timeout=1.0)
                yield f"data: {log_msg}\n\n"
            except queue.Empty:
                # Send empty ping to keep client connection alive
                yield ": ping\n\n"
    return Response(event_generator(), mimetype='text/event-stream')

@app.route('/api/download', methods=['POST'])
def start_download():
    if running_task["active"]:
        return jsonify({"success": False, "message": "目前有其他任務正在執行中，請稍候。"}), 400

    data = request.json or {}
    url = data.get("url")
    mode = data.get("mode", "3") # Default mode 3 (Merged)

    if not url:
        return jsonify({"success": False, "message": "請輸入影片網址！"}), 400

    def download_thread_func():
        try:
            running_task["active"] = True
            running_task["type"] = "download"
            running_task["progress"] = 0.0
            print(f"\n[SYSTEM] 下載任務開始...")
            print(f"網址: {url}")
            
            youtubeDownload.download_video(url, mode, progress_callback=progress_callback)
            
            running_task["progress"] = 1.0
            print(f"[SYSTEM] 下載成功！")
        except Exception as e:
            print(f"[SYSTEM] 下載失敗: {str(e)}")
        finally:
            running_task["active"] = False
            running_task["type"] = None

    threading.Thread(target=download_thread_func, daemon=True).start()
    return jsonify({"success": True, "message": "下載任務已啟動。"})

@app.route('/api/cut', methods=['POST'])
def start_cut():
    if running_task["active"]:
        return jsonify({"success": False, "message": "目前有其他任務正在執行中，請稍候。"}), 400

    data = request.json or {}
    input_path = data.get("input_path")
    start_time = data.get("start_time", "00:00:00")
    end_time = data.get("end_time", "00:00:10")

    if not input_path or not os.path.exists(input_path):
        return jsonify({"success": False, "message": "找不到指定的來源檔案！"}), 400

    def cut_thread_func():
        try:
            running_task["active"] = True
            running_task["type"] = "cut"
            running_task["progress"] = 0.0
            print(f"\n[SYSTEM] 剪輯任務開始...")
            print(f"檔案: {os.path.basename(input_path)}")
            
            # Start progress simulation
            progress_callback(0.2)
            success, result = mediaCut.cut_video(input_path, start_time, end_time)
            
            if success:
                progress_callback(1.0)
                print(f"[SYSTEM] 剪輯成功！輸出: {result}")
            else:
                progress_callback(0.0)
                print(f"[SYSTEM] 剪輯失敗: {result}")
        except Exception as e:
            progress_callback(0.0)
            print(f"--- 剪輯發生異常錯誤: {str(e)} ---")
        finally:
            running_task["active"] = False
            running_task["type"] = None

    threading.Thread(target=cut_thread_func, daemon=True).start()
    return jsonify({"success": True, "message": "剪輯任務已啟動。"})

@app.route('/api/transcribe', methods=['POST'])
def start_transcribe():
    if running_task["active"]:
        return jsonify({"success": False, "message": "目前有其他任務正在執行中，請稍候。"}), 400

    data = request.json or {}
    input_path = data.get("input_path")
    model_size = data.get("model_size", "large-v3")
    show_timestamps = data.get("show_timestamps", True)

    if not input_path or not os.path.exists(input_path):
        return jsonify({"success": False, "message": "找不到指定的音訊/影片檔案！"}), 400

    def transcribe_thread_func():
        global audio_processor
        try:
            running_task["active"] = True
            running_task["type"] = "transcribe"
            running_task["progress"] = 0.0
            print(f"\n[SYSTEM] 語音辨識任務開始...")
            print(f"檔案: {os.path.basename(input_path)}")
            
            # Load or switch Whisper model
            if audio_processor is None or audio_processor.model_size != model_size:
                print(f"[SYSTEM] 正在載入 Whisper ({model_size}) 模型...")
                audio_processor = AudioProcessor(model_size=model_size)
            
            output_path = os.path.splitext(input_path)[0] + "_辨識結果.txt"
            
            audio_processor.transcribe(
                input_path,
                output_file=output_path,
                progress_callback=progress_callback,
                show_timestamps=show_timestamps
            )
            
            progress_callback(1.0)
            print(f"[SYSTEM] 辨識成功！儲存於: {output_path}")
        except Exception as e:
            progress_callback(0.0)
            print(f"[SYSTEM] 辨識失敗: {str(e)}")
        finally:
            running_task["active"] = False
            running_task["type"] = None

    threading.Thread(target=transcribe_thread_func, daemon=True).start()
    return jsonify({"success": True, "message": "語音辨識任務已啟動。"})

@app.route('/api/files', methods=['GET'])
def list_files():
    # List files in the project root directory
    base_dir = os.getcwd()
    allowed_extensions = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.mp3', '.wav', '.m4a', '.txt'}
    
    files_list = []
    try:
        for file in os.listdir(base_dir):
            file_path = os.path.join(base_dir, file)
            if os.path.isfile(file_path):
                name, ext = os.path.splitext(file)
                if ext.lower() in allowed_extensions:
                    stat = os.stat(file_path)
                    files_list.append({
                        "name": file,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "mtime": stat.st_mtime,
                        "path": os.path.abspath(file_path)
                    })
        # Sort by modification time (newest first)
        files_list.sort(key=lambda x: x["mtime"], reverse=True)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": True, "files": files_list})

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    try:
        # Open working dir
        base_dir = os.getcwd()
        os.startfile(os.path.normpath(base_dir))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/open-file', methods=['POST'])
def open_file():
    data = request.json or {}
    file_path = data.get("path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "message": "找不到該檔案！"}), 400
    try:
        os.startfile(file_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    data = request.json or {}
    file_path = data.get("path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "message": "找不到該檔案！"}), 400
    try:
        os.remove(file_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/select-file', methods=['POST'])
def select_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        file_path = ""
        def run_dialog():
            nonlocal file_path
            try:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                file_path = filedialog.askopenfilename(
                    title="選擇媒體檔案",
                    filetypes=[("媒體與影音檔案", "*.mp4;*.mkv;*.webm;*.mov;*.avi;*.mp3;*.wav;*.m4a;*.*")]
                )
                root.destroy()
            except Exception as ex:
                print(f"[SYSTEM] 開啟本機檔案選取視窗失敗: {str(ex)}")

        t = threading.Thread(target=run_dialog)
        t.start()
        t.join()
        
        return jsonify({"success": True, "path": file_path})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def get_tool_path(filename):
    base_dir = os.getcwd()
    search_paths = [
        base_dir,
        os.path.join(base_dir, "tools"),
        os.path.join(base_dir, "src"),
        # Also fall back to the temp extracted folder where main.py actually is
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    ]
    for d in search_paths:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return path
    return os.path.join(base_dir, "tools", filename)

@app.route('/api/check-tools', methods=['GET'])
def check_tools():
    base_dir = os.getcwd()
    search_paths = [
        base_dir,
        os.path.join(base_dir, "tools"),
        os.path.join(base_dir, "src"),
        # Also fall back to the temp extracted folder where main.py actually is
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    ]
    ffmpeg_exists = False
    ffprobe_exists = False
    ytdlp_exists = False
    
    for d in search_paths:
        if os.path.exists(os.path.join(d, "ffmpeg.exe")):
            ffmpeg_exists = True
        if os.path.exists(os.path.join(d, "ffprobe.exe")):
            ffprobe_exists = True
        if os.path.exists(os.path.join(d, "yt-dlp.exe")):
            ytdlp_exists = True
            
    return jsonify({
        "ffmpeg": ffmpeg_exists,
        "ffprobe": ffprobe_exists,
        "ytdlp": ytdlp_exists,
        "installed": ffmpeg_exists and ffprobe_exists and ytdlp_exists
    })

@app.route('/api/install-tools', methods=['POST'])
def install_tools():
    if running_task["active"]:
        return jsonify({"success": False, "message": "目前有其他任務正在執行中，請稍候。"}), 400
        
    def install_thread_func():
        try:
            running_task["active"] = True
            running_task["type"] = "install"
            running_task["progress"] = 0.0
            print("\n[SYSTEM] 開始下載必要核心組件...")
            
            base_dir = os.getcwd()
            tools_dir = os.path.join(base_dir, "tools")
            if not os.path.exists(tools_dir):
                os.makedirs(tools_dir)
                
            urls = {
                "ffmpeg": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v6.1/ffmpeg-6.1-win-64.zip",
                "ffprobe": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v6.1/ffprobe-6.1-win-64.zip",
                "yt-dlp": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            }
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            total_steps = len(urls)
            for idx, (name, url) in enumerate(urls.items()):
                step_progress_start = idx / total_steps
                progress_callback(step_progress_start + 0.05)
                
                if name == "yt-dlp":
                    dest_exe = os.path.join(tools_dir, "yt-dlp.exe")
                    if os.path.exists(dest_exe):
                        continue
                    print("[SYSTEM] 下載 yt-dlp.exe...")
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req) as response:
                        with open(dest_exe, "wb") as f:
                            f.write(response.read())
                    print("[SYSTEM] yt-dlp 安裝完成")
                else:
                    dest_exe = os.path.join(tools_dir, f"{name}.exe")
                    if os.path.exists(dest_exe):
                        continue
                        
                    print(f"[SYSTEM] 下載 {name}.exe...")
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req) as response:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                            tmp_file.write(response.read())
                            tmp_path = tmp_file.name
                    
                    progress_callback(step_progress_start + 0.2)
                    print(f"[SYSTEM] 安裝 {name}.exe...")
                    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                        zip_ref.extract(f"{name}.exe", tools_dir)
                        
                    os.remove(tmp_path)
                    print(f"[SYSTEM] {name} 安裝完成")
                
            progress_callback(1.0)
            print("[SYSTEM] 所有組件安裝完成！")
            
            # 下載完後背景觸發一次更新以防萬一
            threading.Thread(target=check_and_update_dependencies, daemon=True).start()
        except Exception as e:
            progress_callback(0.0)
            print(f"--- 下載安裝失敗: {str(e)} ---")
        finally:
            running_task["active"] = False
            running_task["type"] = None
            
    threading.Thread(target=install_thread_func, daemon=True).start()
    return jsonify({"success": True, "message": "安裝任務已在背景啟動。"})

@app.route('/api/clean-environment', methods=['POST'])
def clean_environment():
    if running_task["active"]:
        return jsonify({"success": False, "message": "目前有其他任務正在執行中，無法清空環境。"}), 400
        
    try:
        base_dir = os.getcwd()
        tools_dir = os.path.join(base_dir, "tools")
        
        # 僅刪除本機下載的核心組件資料夾
        import shutil
        if os.path.exists(tools_dir):
            shutil.rmtree(tools_dir, ignore_errors=True)
            
        # 移除解壓卸載 flag
        flag_path = os.path.join(base_dir, "uninstall.flag")
        if os.path.exists(flag_path):
            os.remove(flag_path)
            
        print("[SYSTEM] 已清空本機核心組件 (tools/ 資料夾已刪除)")
        return jsonify({
            "success": True, 
            "message": "本機核心組件已清空"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"清理失敗: {str(e)}"}), 500

def check_and_update_dependencies():
    """在背景執行 yt-dlp.exe 自我升級指令"""
    ytdlp_path = get_tool_path('yt-dlp.exe')
    if not os.path.exists(ytdlp_path):
        return
        
    print("[SYSTEM] 檢查 yt-dlp 更新...")
    try:
        res = subprocess.run(
            [ytdlp_path, "--update"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if res.returncode == 0:
            out_str = res.stdout.strip()
            print("[SYSTEM] yt-dlp 已是最新版" if "latest" in out_str or "up to date" in out_str else "[SYSTEM] yt-dlp 更新完成")
        else:
            print(f"[SYSTEM] yt-dlp 更新錯誤: {res.returncode}")
    except Exception as e:
        print(f"[SYSTEM] yt-dlp 背景更新失敗: {str(e)}")

def auto_install_tools_if_missing():
    """在背景自動檢查並安裝 FFmpeg/FFprobe/yt-dlp.exe，若缺失則自動下載"""
    base_dir = os.getcwd()
    search_paths = [
        base_dir,
        os.path.join(base_dir, "tools"),
        os.path.join(base_dir, "src"),
        # Also fall back to the temp extracted folder where main.py actually is
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    ]
    ffmpeg_exists = False
    ffprobe_exists = False
    ytdlp_exists = False
    
    for d in search_paths:
        if os.path.exists(os.path.join(d, "ffmpeg.exe")):
            ffmpeg_exists = True
        if os.path.exists(os.path.join(d, "ffprobe.exe")):
            ffprobe_exists = True
        if os.path.exists(os.path.join(d, "yt-dlp.exe")):
            ytdlp_exists = True
            
    if not (ffmpeg_exists and ffprobe_exists and ytdlp_exists):
        print("[SYSTEM] 偵測到缺少組件，啟動背景下載...")
        try:
            # 優先檢測網路連線狀態
            try:
                urllib.request.urlopen("https://github.com", timeout=3)
            except Exception:
                print("[SYSTEM] 警告：無法連線至網際網路 (GitHub)！請檢查網路設定，否則無法自動下載必要核心組件。")
                
            tools_dir = os.path.join(base_dir, "tools")
            if not os.path.exists(tools_dir):
                os.makedirs(tools_dir)
                
            urls = {
                "ffmpeg": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v6.1/ffmpeg-6.1-win-64.zip",
                "ffprobe": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v6.1/ffprobe-6.1-win-64.zip",
                "yt-dlp": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            }
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            for name, url in urls.items():
                if name == "yt-dlp":
                    dest_exe = os.path.join(tools_dir, "yt-dlp.exe")
                    if os.path.exists(dest_exe):
                        continue
                    print("[SYSTEM] 背景下載 yt-dlp.exe...")
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req) as response:
                        with open(dest_exe, "wb") as f:
                            f.write(response.read())
                    print("[SYSTEM] 背景部署 yt-dlp 完成")
                else:
                    dest_exe = os.path.join(tools_dir, f"{name}.exe")
                    if os.path.exists(dest_exe):
                        continue
                    
                    print(f"[SYSTEM] 背景下載 {name}.exe...")
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req) as response:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                            tmp_file.write(response.read())
                            tmp_path = tmp_file.name
                            
                    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                        zip_ref.extract(f"{name}.exe", tools_dir)
                    os.remove(tmp_path)
                    print(f"[SYSTEM] 背景部署 {name} 完成")
            print("[SYSTEM] 背景組件下載完成")
            
            # 下載完成後立即順便背景執行一次更新
            threading.Thread(target=check_and_update_dependencies, daemon=True).start()
        except Exception as e:
            print(f"[SYSTEM] 背景自動安裝核心組件失敗: {str(e)}")

def open_browser():
    """自動開啟瀏覽器對接網頁端"""
    import webbrowser
    import time
    time.sleep(1.5)
    try:
        webbrowser.open("https://FirePhoenix1001.github.io/WedTest/")
    except Exception as e:
        print(f"[SYSTEM] 無法自動開啟瀏覽器: {str(e)}")

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

    # 啟動背景更新與部署線程
    threading.Thread(target=check_and_update_dependencies, daemon=True).start()
    threading.Thread(target=open_browser, daemon=True).start()

    # Make sure we run on 8000
    app.run(host='127.0.0.1', port=8000, debug=False, threaded=True)
