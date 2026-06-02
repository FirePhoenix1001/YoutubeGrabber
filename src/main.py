# src/main.py
import os
import sys
import threading
import subprocess
import queue
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from tkinter import Tk, filedialog
import updater
import youtubeDownload
import mediaCut
from audioProcessor import AudioProcessor

# 初始化 Flask App
app = Flask(__name__)
# 啟用全域 CORS，允許本地前端 (file://, localhost) 發送請求
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 全域語音處理器實例
audio_processor = AudioProcessor()

# 定義 ffprobe 路徑
FFPROBE_PATH = os.path.join(updater.TOOLS_DIR, 'ffprobe.exe')

# 用於存放非同步任務進度推播的 Queue 字典
progress_queues = {
    "download": queue.Queue(),
    "transcribe": queue.Queue()
}

def clean_queue(q):
    """清空 Queue 中的所有舊數據"""
    while not q.empty():
        try:
            q.get_nowait()
        except queue.Empty:
            break

# =====================================================================
#             🌻 核心：心跳與組件下載進度 API
# =====================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """
    心跳偵測與組件下載狀態查詢接口。
    回傳值:
      status: "checking" (檢查中), "updating" (下載更新中), "ready" (就緒), "error" (出錯)
      progress: 0 到 100 之間
      error: 錯誤說明字串
    """
    return jsonify({
        "status": updater.current_status,
        "progress": updater.current_progress,
        "error": updater.current_error
    })

# =====================================================================
#             🌻 進度推播 API (Server-Sent Events)
# =====================================================================

@app.route('/api/progress/<task_type>', methods=['GET'])
def get_progress_stream(task_type):
    """
    以 Server-Sent Events (SSE) 單向串流推送即時進度。
    task_type: 'download' 或 'transcribe'
    """
    if task_type not in progress_queues:
        return jsonify({"error": "無效的任務類型"}), 400

    def event_generator():
        q = progress_queues[task_type]
        clean_queue(q) # 開始新任務前先清空
        
        while True:
            # 阻塞等待新的進度百分比 (0.0 到 1.0)
            percent = q.get()
            yield f"data: {percent}\n\n"
            
            # 若為 1.0 (完成) 或小於 0 (例如 -1 代表失敗)，則結束 SSE 連線
            if percent >= 1.0 or percent < 0:
                break
                
    return Response(event_generator(), mimetype="text/event-stream")

# =====================================================================
#             🌻 功能 API：下載、選檔、剪輯、辨識、系統操作
# =====================================================================

@app.route('/api/download', methods=['POST'])
def handle_download():
    """YouTube 下載 API"""
    data = request.json or {}
    url = data.get('url', '').strip()
    mode = data.get('mode', '3')
    
    if not url:
        return jsonify({"success": False, "message": "影片網址為空"}), 400

    def run():
        try:
            def local_callback(percent):
                progress_queues["download"].put(percent)
            
            # 執行下載
            youtubeDownload.download_video(url, mode, progress_callback=local_callback)
            progress_queues["download"].put(1.0) # 下載完成
        except Exception as e:
            print(f"[下載 API] 出錯: {e}")
            progress_queues["download"].put(-1.0) # 下載失敗

    # 在背景執行緒中處理，避免阻塞 HTTP 請求
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"success": True, "message": "下載任務已在背景啟動"})

@app.route('/api/select-file', methods=['POST'])
def handle_select_file():
    """原生檔案選擇器 filedialog 橋接 API"""
    data = request.json or {}
    tab_type = data.get('tab_type', 'cut')
    
    try:
        if tab_type == 'cut':
            file_types = [("影片與音訊檔案", "*.mp4 *.mkv *.webm *.mov *.avi *.mp3")]
        else:
            file_types = [("影音媒體檔案", "*.mp3 *.wav *.m4a *.mp4 *.mkv *.webm *.mov *.avi")]
        
        # 使用 Tkinter filedialog 選擇本地檔案
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(filetypes=file_types)
        root.destroy()
        
        if file_path:
            normalized_path = os.path.normpath(file_path).replace('\\', '/')
            file_name = os.path.basename(normalized_path)
            return jsonify({
                "success": True, 
                "file": {"path": normalized_path, "name": file_name}
            })
        return jsonify({"success": True, "file": None})
    except Exception as e:
        print(f"[選檔 API] 出錯: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/media-duration', methods=['POST'])
def handle_media_duration():
    """解析影音長度 API"""
    data = request.json or {}
    file_path = data.get('file_path', '')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "message": "檔案不存在"}), 400
        
    try:
        command = [
            FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        duration_sec = float(result.stdout.strip())
        
        m, s = divmod(duration_sec, 60)
        h, m = divmod(m, 60)
        return jsonify({
            "success": True, 
            "duration": {"h": int(h), "m": int(m), "s": int(s)}
        })
    except Exception as e:
        print(f"[時長 API] 出錯: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/video-cut', methods=['POST'])
def handle_video_cut():
    """本地影片剪切 API"""
    data = request.json or {}
    file_path = data.get('file_path', '')
    start_time = data.get('start_time', '00:00:00')
    end_time = data.get('end_time', '00:00:10')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "message": "檔案不存在"}), 400

    try:
        success, result_path = mediaCut.cut_video(file_path, start_time, end_time)
        return jsonify({"success": success, "result_path": result_path if success else "", "message": "剪輯成功" if success else result_path})
    except Exception as e:
        print(f"[剪切 API] 出錯: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/transcribe', methods=['POST'])
def handle_transcribe():
    """語音辨識 Whisper API"""
    data = request.json or {}
    file_path = data.get('file_path', '')
    model_size = data.get('model_size', 'large-v3')
    show_timestamps = data.get('show_timestamps', True)
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "message": "檔案不存在"}), 400

    def run():
        try:
            output_path = os.path.splitext(file_path)[0] + "_辨識結果.txt"
            audio_processor.model_size = model_size
            
            def local_callback(percent):
                progress_queues["transcribe"].put(percent)
                
            audio_processor.transcribe(
                file_path,
                output_file=output_path,
                progress_callback=local_callback,
                show_timestamps=show_timestamps
            )
            progress_queues["transcribe"].put(1.0) # 辨識完成
        except Exception as e:
            print(f"[辨識 API] 出錯: {e}")
            progress_queues["transcribe"].put(-1.0) # 辨識失敗

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"success": True, "message": "語音辨識任務已在背景啟動"})

@app.route('/api/open-folder', methods=['POST'])
def handle_open_folder():
    """檔案總管開啟 API"""
    data = request.json or {}
    file_path = data.get('file_path', '')
    if file_path and os.path.exists(file_path):
        normalized_path = os.path.normpath(file_path)
        subprocess.run(['explorer', '/select,', normalized_path])
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "檔案路徑不存在"}), 400

@app.route('/api/play-file', methods=['POST'])
def handle_play_file():
    """系統預設播放器開啟 API"""
    data = request.json or {}
    file_path = data.get('file_path', '')
    if file_path and os.path.exists(file_path):
        normalized_path = os.path.normpath(file_path)
        os.startfile(normalized_path)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "檔案路徑不存在"}), 400

# =====================================================================
#             🌻 新增：網頁自動引導啟動
# =====================================================================
import time
import webbrowser

def open_browser_guide():
    """等待 Flask 服務啟動後，以系統預設瀏覽器開啟本地的 web/index.html 檔案"""
    time.sleep(1.5) # 稍微延遲以確保 Flask 已經在 Port 5000 監聽
    try:
        # 獲取與程式同級目錄下的 web/index.html 路徑
        base_dir = updater.get_base_path()
        index_path = os.path.abspath(os.path.join(base_dir, "web", "index.html"))
        if os.path.exists(index_path):
            print(f"[主程式] [引導啟動] 正在利用預設瀏覽器開啟網頁: {index_path}")
            os.startfile(index_path)
        else:
            print(f"[主程式] [引導啟動] [錯誤] 找不到網頁檔案: {index_path}")
    except Exception as e:
        print(f"[主程式] [引導啟動] [錯誤] 開啟瀏覽器失敗: {e}")

# =====================================================================

def main():
    print("=" * 50)
    print("[主程式] 啟動 Flask 後端服務 (Port 5000)...")
    print("=" * 50)

    # 1. 於背景執行緒啟動工具自動檢查與下載，使 Flask 能秒開，前端網頁得以立刻連線
    threading.Thread(target=updater.check_and_update_tools, daemon=True).start()

    # 2. 啟動瀏覽器引導開啟執行緒
    threading.Thread(target=open_browser_guide, daemon=True).start()

    # 3. 啟動 Flask 服務 (綁定 localhost 的 5000 埠口)
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
    except (SystemExit, KeyboardInterrupt):
        print("[主程式] 服務已正常關閉。")
    except Exception as e:
        print(f"[主程式] [錯誤] 啟動 Flask 失敗: {e}")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
