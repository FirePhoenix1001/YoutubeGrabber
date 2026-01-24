import os
import sys
import subprocess

# 1. 為了讓剪輯功能也能獨立運作，我們同樣需要這個路徑偵測函式
def get_ffmpeg_path():
    """
    智慧判斷 FFmpeg 路徑：
    1. 打包後 (exe)：會去暫存資料夾 sys._MEIPASS 找
    2. 開發中 (py) ：會去目前的檔案資料夾找
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_path, 'ffmpeg.exe')

# 定義 FFmpeg 路徑
FFMPEG_PATH = get_ffmpeg_path()

def cut_video(input_path, start_time, end_time):
    """
    執行影片剪輯的核心函式
    :param input_path: 來源檔案路徑 (絕對路徑)
    :param start_time: 開始時間 (字串 "HH:MM:SS")
    :param end_time:   結束時間 (字串 "HH:MM:SS")
    :return: (bool 成功與否, string 訊息)
    """
    
    # 檢查 FFmpeg 是否存在
    if not os.path.exists(FFMPEG_PATH):
        return False, "找不到 ffmpeg.exe，請確認檔案位置。"

    # 檢查來源檔案是否存在
    if not os.path.exists(input_path):
        return False, f"找不到來源檔案: {input_path}"

    # 產生輸出檔名：在原檔名後面加上 "_cut"
    # 例如: C:/Video/test.mp4 -> C:/Video/test_cut.mp4
    file_dir, file_name = os.path.split(input_path)
    name, ext = os.path.splitext(file_name)
    output_filename = f"{name}_cut{ext}"
    output_path = os.path.join(file_dir, output_filename)

    # 組合 FFmpeg 指令
    # -ss: 開始時間
    # -to: 結束時間
    # -c copy: 關鍵參數！直接複製資料流，不重新編碼 (速度極快)
    # -y: 若輸出檔案已存在，直接覆蓋不詢問
    command = [
        FFMPEG_PATH, 
        "-i", input_path,
        "-ss", start_time,
        "-to", end_time,
        "-c", "copy",
        output_path,
        "-y"
    ]

    try:
        # ... (前面的 subprocess 指令不用動) ...
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        # ★ 修改這裡：成功時，直接回傳「輸出路徑 (output_path)」
        return True, output_path 

    except subprocess.CalledProcessError as e:
        return False, f"剪輯失敗 (FFmpeg Error): {e.stderr}"
    except Exception as e:
        return False, f"發生未預期的錯誤: {str(e)}"
    
# ==========================================
#        單元測試區 (Unit Test)
#  這段只有在直接執行此檔案時才會跑，被匯入時不會跑
# ==========================================
if __name__ == "__main__":
    print("--- 開始測試剪輯功能 ---")
    print(f"使用的 FFmpeg 路徑: {FFMPEG_PATH}")
    
    # 您可以在這裡填入一個真實的檔案路徑來測試
    # 注意：Windows 路徑若有反斜線 \ 請改用雙斜線 \\ 或斜線 /
    test_file = input("請輸入要測試的影片路徑 (例如 C:/Downloads/video.mp4): ")
    
    # 去除路徑可能包含的引號 (有些使用者會用複製路徑的方式)
    test_file = test_file.strip('"')

    if test_file:
        success, msg = cut_video(test_file, "00:00:00", "00:00:10")
        print(msg)
    else:
        print("未輸入路徑，跳過測試。")