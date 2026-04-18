import os
from faster_whisper import WhisperModel
from opencc import OpenCC

class AudioProcessor:
    def __init__(self, model_size="large-v3", device="cpu", compute_type="int8"):
        """
        初始化語音處理器
        :param model_size: 模型大小 (預設為 large-v3)
        :param device: 執行設備 (cpu, cuda)
        :param compute_type: 計算類型 (int8, float16 等)
        """
        self.cc = OpenCC('s2twp')  # 簡體轉台灣繁體
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def load_model(self):
        """延遲載入模型，避免啟動程式時耗時過久"""
        if self.model is None:
            print(f"正在初始化 Whisper 模型 ({self.model_size})... 這可能需要一些時間。")
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            print("模型初始化完成！")

    def transcribe(self, input_file, output_file=None, progress_callback=None, show_timestamps=True):
        """
        開始辨識語音並轉換為繁體中文
        :param input_file: 輸入音訊路徑
        :param output_file: 輸出文字檔路徑 (選填)
        :param progress_callback: 進度回調函數 (接收 0~1 的浮點數)
        :param show_timestamps: 是否顯示時間戳記 (預設 True)
        :return: (辨識文字列表, info)
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"找不到輸入檔案: {input_file}")

        self.load_model()
        
        print(f"開始辨識語音: {os.path.basename(input_file)}")
        segments, info = self.model.transcribe(
            input_file,
            beam_size=5,
            language="zh"
        )

        total_duration = info.duration
        print(f"偵測到語言: {info.language} (信心值: {info.language_probability:.2f})")
        print(f"音訊時長: {total_duration:.2f} 秒")
        print("-" * 30)

        results = []
        
        # 如果有指定輸出檔案，開啟它
        f = None
        if output_file:
            f = open(output_file, "w", encoding="utf-8")
            f.write(f"來源檔案: {os.path.basename(input_file)}\n")
            f.write(f"偵測語言: {info.language} (信心值: {info.language_probability:.2f})\n")
            f.write("-" * 30 + "\n")

        try:
            for segment in segments:
                # 簡轉繁
                traditional_text = self.cc.convert(segment.text).strip()
                
                if show_timestamps:
                    line = f"[{segment.start:.2f}s -> {segment.end:.2f}s] {traditional_text}"
                else:
                    line = traditional_text
                
                results.append(line)
                
                # 同時輸出到終端機
                print(line)
                
                # 寫入檔案
                if f:
                    f.write(line + "\n")
                
                # 回傳進度
                if progress_callback and total_duration > 0:
                    current_progress = min(segment.end / total_duration, 1.0)
                    progress_callback(current_progress)

            if f:
                print(f"\n--- 辨識完成！結果已儲存至 {output_file} ---")
            else:
                print("\n--- 辨識完成！ ---")

        finally:
            if f:
                f.close()
        
        return results, info

# 提供一個簡單的測試介面
if __name__ == "__main__":
    processor = AudioProcessor()
    # 測試程式 (需確認 test.mp3 存在)
    if os.path.exists("test.mp3"):
        processor.transcribe("test.mp3", "output.txt")
    else:
        print("測試失敗: 找不到 test.mp3")