## 🛠️ 開發者設置指南 (Development Setup)

如果您想修改原始碼或在本地運行，請依照以下步驟：

1. **複製專案**：`git clone https://github.com/FirePhoenix1001/YoutubeGrabber.git`
2. **安裝依賴**：`pip install -r requirements.txt`
3. **配置 FFmpeg (關鍵步驟)**：
   * 本專案依賴 FFmpeg 進行媒體處理。
   * 請自行[下載](https://www.gyan.dev/ffmpeg/builds/) `ffmpeg.exe` 及 `ffprobe.exe`。
   * 將它們放入專案根目錄中的tools裡。
4. **執行程式**：`python src/main.py`
5. **打包指令**：`pyinstaller main.spec --clean`