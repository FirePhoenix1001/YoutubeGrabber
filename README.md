# 🌻 Youtube 擷取工具 - 向日葵網頁版

這是一個基於 **Eel + HTML5 + CSS3 + JavaScript (ES6)** 混合架構打造的輕量化、現代化 YouTube 影音擷取與處理工具。

## 🌟 核心功能
1. **YouTube 影音下載**：支援「僅影像」、「僅聲音（轉 MP3）」與「影音合併（高清推薦）」，對接最新的 `yt-dlp` 下載串流。
2. **本地媒體剪輯**：藉由前端 `ffmpeg.wasm`-like 操作，傳送至後端直接利用 `ffmpeg` 進行快速、無損（`-c copy`）剪切與封裝。
3. **語音辨識 (Whisper)**：使用優化版 `faster-whisper` 模型（預設採用 `large-v3`），將本地音訊/影片轉換為帶有時間戳記的逐字稿，並內建 `OpenCC` 自動轉換為台灣繁體中文。

---

## 🛠️ 技術架構
- **前端 (Frontend)**：HTML5、CSS3 (自訂圓角、流光進度條、微動畫與向日葵配色)、Vanilla JavaScript (ES6)。
- **後端 (Backend)**：Python 3、Eel (基於 Bottle Web 伺服器與 WebSocket 雙向 RPC 通訊)。
- **外部依賴**：`yt-dlp`、`ffmpeg`、`ffprobe`。

---

## 🚀 開發者設置指南 (Development Setup)

如果您想在本地端運行或修改原始碼，請依照以下步驟：

1. **複製專案**：
   ```bash
   git clone https://github.com/FirePhoenix1001/YoutubeGrabber.git
   cd YoutubeGrabber
   ```

2. **安裝依賴套件**：
   ```bash
   pip install -r requirements.txt
   ```

3. **啟動程式**：
   ```bash
   python src/main.py
   ```
   > **💡 關鍵變更**：本專案已改為**自動更新機制**。您不需要手動下載 `ffmpeg.exe`、`ffprobe.exe` 或 `yt-dlp.exe`。程式啟動時會自動檢查本地 `tools/` 資料夾，連網下載最新版二進位檔案，若離線則會降級使用本地快取。

---

## 📦 打包發行 (Build Single EXE)

本專案已完成 PyInstaller 打包設定優化。若要將本專案打包為單一的 `.exe` 獨立執行檔，請執行：

```bash
pyinstaller main.spec --clean
```

### 優化說明
- **網頁資源嵌入**：`web/` 前端靜態資源會自動被打包入 `.exe` 內，啟動時會解壓至臨時目錄。
- **體積大幅精簡**：`tools/` 資料夾（高達 150MB+）**不進行靜態打包**。打包後的 `.exe` 體積僅數十 MB。當使用者首次執行生成的 `.exe` 時，程式會自動下載並常駐 `tools/` 於執行檔同級目錄下，兼顧體積與自動更新。