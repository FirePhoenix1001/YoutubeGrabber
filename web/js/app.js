// web/js/app.js

const BACKEND_URL = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", () => {
    // ==========================================
    //            分頁切換邏輯
    // ==========================================
    const tabLinks = document.querySelectorAll(".tab-link");
    const tabContents = document.querySelectorAll(".tab-content");
    const globalProgress = document.getElementById("global-progress");

    tabLinks.forEach(link => {
        link.addEventListener("click", () => {
            const targetTab = link.getAttribute("data-tab");
            tabLinks.forEach(l => l.classList.remove("active"));
            link.classList.add("active");

            tabContents.forEach(content => {
                content.classList.remove("active");
                if (content.id === targetTab) {
                    content.classList.add("active");
                }
            });
            globalProgress.classList.add("hidden");
        });
    });

    // ==========================================
    //            全域進度條控制
    // ==========================================
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressPercent = document.getElementById("progress-percent");
    const progressStatus = document.getElementById("progress-status");
    const progressSpeed = document.getElementById("progress-speed");
    const progressEta = document.getElementById("progress-eta");

    function showProgress(status, percent = 0, speed = "進行中", eta = "請稍候...") {
        globalProgress.classList.remove("hidden");
        progressStatus.textContent = status;
        progressBarFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        progressSpeed.textContent = `狀態: ${speed}`;
        progressEta.textContent = eta;
    }

    function hideProgress() {
        globalProgress.classList.add("hidden");
    }

    // ==========================================
    //       🌻 新增：自主心跳偵測與狀態控制
    // ==========================================
    const statusLamp = document.getElementById("status-lamp");
    const statusText = document.getElementById("status-text");
    const startupOverlay = document.getElementById("startup-overlay");
    const overlayStatus = document.getElementById("overlay-status");
    const overlayProgressBar = document.getElementById("overlay-progress-bar");
    const overlayPercent = document.getElementById("overlay-percent");

    let isBackendOnline = false;

    // 控制全網頁控制項啟用與否
    function setAllControlsDisabled(disabled) {
        document.querySelectorAll("input, button, select").forEach(el => {
            // 例外：選取檔案或 status 燈號不在此限
            if (el.id !== "status-lamp") {
                el.disabled = disabled;
            }
        });
        
        // 額外美化選卡 opacity
        document.querySelectorAll(".mode-card").forEach(c => {
            c.style.opacity = disabled ? "0.6" : "1";
        });
    }

    // 動態更新連線燈號與 Startup Loading 遮罩
    function updateConnectionStatus(status, progress = 0, error = "") {
        statusLamp.className = "lamp"; // 清除舊 class
        
        if (status === "offline") {
            isBackendOnline = false;
            statusLamp.classList.add("offline");
            statusText.textContent = "服務離線 🔴";
            setAllControlsDisabled(true);
            startupOverlay.classList.add("hidden");
            showProgress("⚠️ 後端運算服務尚未啟動，請先執行 Python 程式。", 0, "斷線", "無法下載");
        } 
        else if (status === "checking") {
            isBackendOnline = true;
            statusLamp.classList.add("updating");
            statusText.textContent = "準備中 🟡";
            setAllControlsDisabled(true);
            startupOverlay.classList.remove("hidden");
            overlayStatus.textContent = "正在檢查本地相依二進位工具...";
            overlayProgressBar.style.width = "0%";
            overlayPercent.textContent = "0%";
            hideProgress();
        } 
        else if (status === "updating") {
            isBackendOnline = true;
            statusLamp.classList.add("updating");
            statusText.textContent = "更新中 🟡";
            setAllControlsDisabled(true);
            startupOverlay.classList.remove("hidden");
            overlayStatus.textContent = "正在下載核心組件 (ffmpeg / yt-dlp)...";
            overlayProgressBar.style.width = `${progress}%`;
            overlayPercent.textContent = `${progress}%`;
            hideProgress();
        } 
        else if (status === "ready") {
            // 就緒正常狀態
            if (!isBackendOnline) {
                // 從 Offline 轉為 Online 時，解鎖控制項
                setAllControlsDisabled(false);
                hideProgress();
                // 恢復分頁啟用狀態
                updateTabButtonsState();
            }
            isBackendOnline = true;
            statusLamp.classList.add("online");
            statusText.textContent = "連線就緒 🟢";
            startupOverlay.classList.add("hidden");
        } 
        else if (status === "error") {
            isBackendOnline = true;
            statusLamp.classList.add("offline");
            statusText.textContent = "工具錯誤 ❌";
            setAllControlsDisabled(true);
            startupOverlay.classList.remove("hidden");
            overlayStatus.textContent = `核心工具配置出錯: ${error}`;
            overlayProgressBar.style.width = "0%";
            overlayPercent.textContent = "ERROR";
            hideProgress();
        }
    }

    // 當系統解鎖時，確認哪些次要按鈕該維持 disabled
    function updateTabButtonsState() {
        // 如果沒有選擇檔案，本地剪輯與語音辨識的按鈕應為禁用
        if (!selectedCutPath) {
            document.getElementById("cut-preview-btn").disabled = true;
            document.getElementById("cut-execute-btn").disabled = true;
        }
        if (!lastCutOutputPath) {
            document.getElementById("cut-open-folder-btn").disabled = true;
            document.getElementById("cut-play-result-btn").disabled = true;
        }
        if (!selectedTranscribePath) {
            document.getElementById("transcribe-execute-btn").disabled = true;
        }
        if (!lastTxtOutputPath) {
            document.getElementById("transcribe-open-result-btn").disabled = true;
        }
    }

    // 發起自主心跳偵測
    async function checkHeartbeat() {
        try {
            const response = await fetch(`${BACKEND_URL}/api/status`, { mode: 'cors' });
            if (response.ok) {
                const data = await response.json();
                updateConnectionStatus(data.status, data.progress, data.error);
            } else {
                updateConnectionStatus("offline");
            }
        } catch (err) {
            updateConnectionStatus("offline");
        }
        // 每 2 秒偵測一次
        setTimeout(checkHeartbeat, 2000);
    }

    // 啟動心跳檢查
    checkHeartbeat();


    // ==========================================
    //          分頁一：下載 YouTube
    // ==========================================
    const urlInput = document.getElementById("youtube-url");
    const downloadBtn = document.getElementById("download-btn");
    const btnText = downloadBtn.querySelector(".btn-text");
    const btnLoader = downloadBtn.querySelector(".btn-loader");

    function setDownloadFormDisabled(disabled) {
        urlInput.disabled = disabled;
        downloadBtn.disabled = disabled;
        document.getElementsByName("download-mode").forEach(r => {
            r.disabled = disabled;
            r.closest(".mode-card").style.opacity = disabled ? "0.6" : "1";
        });
    }

    downloadBtn.addEventListener("click", async () => {
        const url = urlInput.value.trim();
        if (!url) {
            alert("請貼上 YouTube 影片網址！");
            return;
        }

        let mode = "3";
        document.getElementsByName("download-mode").forEach(r => {
            if (r.checked) mode = r.value;
        });

        setDownloadFormDisabled(true);
        btnText.textContent = "任務啟動中...";
        btnLoader.classList.remove("hidden");
        
        showProgress("正在向後端 API 請求下載...", 0, "傳送中", "請稍候...");

        try {
            const res = await fetch(`${BACKEND_URL}/api/download`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url, mode }),
                mode: 'cors'
            });
            const data = await res.json();
            
            if (data.success) {
                // 成功啟動後端下載，開始監聽 SSE (Server-Sent Events) 進度條
                listenProgressStream("download");
            } else {
                alert("❌ " + data.message);
                setDownloadFormDisabled(false);
                btnText.textContent = "開始下載";
                btnLoader.classList.add("hidden");
                hideProgress();
            }
        } catch (e) {
            alert("❌ 網路請求失敗，請確認 Python 後端是否運作正常。");
            setDownloadFormDisabled(false);
            btnText.textContent = "開始下載";
            btnLoader.classList.add("hidden");
            hideProgress();
        }
    });

    // 監聽 SSE 串流以取得實時進度
    function listenProgressStream(taskType) {
        const eventSource = new EventSource(`${BACKEND_URL}/api/progress/${taskType}`);
        
        eventSource.onmessage = (event) => {
            const percent = parseFloat(event.data);
            
            if (percent < 0) {
                // 失敗訊號 (-1.0)
                eventSource.close();
                if (taskType === "download") {
                    onDownloadFinished(false, "下載失敗，詳情請查看 Python 主控台。");
                } else if (taskType === "transcribe") {
                    onTranscribeFinished(false, "語音辨識失敗，詳情請查看 Python 主控台。");
                }
            } 
            else if (percent >= 1.0) {
                // 成功完成 (1.0)
                eventSource.close();
                if (taskType === "download") {
                    onDownloadFinished(true, "下載任務已成功完成！");
                } else if (taskType === "transcribe") {
                    onTranscribeFinished(true, "語音辨識已完成！");
                }
            } 
            else {
                // 更新進度
                const percentage = Math.round(percent * 100);
                if (taskType === "download") {
                    showProgress(
                        percentage < 100 ? "影片檔案下載中..." : "下載完成！正在使用 FFmpeg 進行合併或轉碼...",
                        percentage,
                        percentage < 100 ? "下載中" : "合併中",
                        `${percentage}%`
                    );
                } else if (taskType === "transcribe") {
                    showProgress(
                        "語音轉文字辨識中，並將簡體中文轉換為繁體中文...",
                        percentage,
                        "辨識中",
                        `進度: ${percentage}%`
                    );
                }
            }
        };

        eventSource.onerror = () => {
            // 連線斷開
            eventSource.close();
        };
    }

    function onDownloadFinished(success, msg) {
        setDownloadFormDisabled(false);
        btnText.textContent = "開始下載";
        btnLoader.classList.add("hidden");
        hideProgress();
        alert(success ? "🌻 " + msg : "❌ " + msg);
    }


    // ==========================================
    //          分頁二：本地影片剪輯
    // ==========================================
    const cutFileBtn = document.getElementById("cut-file-btn");
    const cutFilename = document.getElementById("cut-filename");
    const cutPreviewBtn = document.getElementById("cut-preview-btn");
    const cutExecuteBtn = document.getElementById("cut-execute-btn");
    const cutOpenFolderBtn = document.getElementById("cut-open-folder-btn");
    const cutPlayResultBtn = document.getElementById("cut-play-result-btn");

    const timeInputs = [
        "start-h", "start-m", "start-s",
        "end-h", "end-m", "end-s"
    ];

    let selectedCutPath = "";
    let lastCutOutputPath = "";

    // 時間輸入框自動補零
    timeInputs.forEach(id => {
        const input = document.getElementById(id);
        input.addEventListener("focus", () => input.select());
        input.addEventListener("blur", () => {
            let val = input.value.trim();
            if (val && !isNaN(val)) {
                input.value = String(parseInt(val, 10)).padStart(2, '0');
            } else {
                input.value = "00";
            }
        });
        input.addEventListener("keyup", (e) => {
            if (e.key === "Enter") input.blur();
        });
    });

    // 選擇剪輯檔案
    cutFileBtn.addEventListener("click", async () => {
        try {
            const res = await fetch(`${BACKEND_URL}/api/select-file`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tab_type: "cut" }),
                mode: 'cors'
            });
            const data = await res.json();
            
            if (data.success && data.file) {
                selectedCutPath = data.file.path;
                cutFilename.textContent = data.file.name;
                cutPreviewBtn.disabled = false;
                cutExecuteBtn.disabled = false;
                cutOpenFolderBtn.disabled = true;
                cutPlayResultBtn.disabled = true;

                // 獲取影片長度
                const durRes = await fetch(`${BACKEND_URL}/api/media-duration`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file_path: selectedCutPath }),
                    mode: 'cors'
                });
                const durData = await durRes.json();
                
                if (durData.success) {
                    document.getElementById("start-h").value = "00";
                    document.getElementById("start-m").value = "00";
                    document.getElementById("start-s").value = "00";

                    document.getElementById("end-h").value = String(durData.duration.h).padStart(2, '0');
                    document.getElementById("end-m").value = String(durData.duration.m).padStart(2, '0');
                    document.getElementById("end-s").value = String(durData.duration.s).padStart(2, '0');
                }
            }
        } catch (e) {
            alert("❌ 選取檔案失敗，請確認後端是否連線。");
        }
    });

    // 系統預覽
    cutPreviewBtn.addEventListener("click", async () => {
        if (!selectedCutPath) return;
        await fetch(`${BACKEND_URL}/api/play-file`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_path: selectedCutPath }),
            mode: 'cors'
        });
    });

    // 取得時間字串 (HH:MM:SS)
    function getTimeString(prefix) {
        const h = document.getElementById(`${prefix}-h`).value;
        const m = document.getElementById(`${prefix}-m`).value;
        const s = document.getElementById(`${prefix}-s`).value;
        return `${h}:${m}:${s}`;
    }

    // 執行剪輯
    cutExecuteBtn.addEventListener("click", async () => {
        if (!selectedCutPath) return;
        const startTime = getTimeString("start");
        const endTime = getTimeString("end");

        cutExecuteBtn.disabled = true;
        showProgress("正在使用 FFmpeg 快速剪輯檔案中...", 50, "剪輯中", "請稍候...");

        try {
            const res = await fetch(`${BACKEND_URL}/api/video-cut`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ file_path: selectedCutPath, start_time: startTime, end_time: endTime }),
                mode: 'cors'
            });
            const data = await res.json();
            
            cutExecuteBtn.disabled = false;
            hideProgress();
            
            if (data.success) {
                lastCutOutputPath = data.result_path;
                cutOpenFolderBtn.disabled = false;
                cutPlayResultBtn.disabled = false;
                alert("🌻 影片剪輯完成！");
            } else {
                alert("❌ 剪輯失敗！\n\n" + data.message);
            }
        } catch (e) {
            cutExecuteBtn.disabled = false;
            hideProgress();
            alert("❌ 剪輯請求失敗。");
        }
    });

    // 開啟資料夾
    cutOpenFolderBtn.addEventListener("click", async () => {
        if (!lastCutOutputPath) return;
        await fetch(`${BACKEND_URL}/api/open-folder`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_path: lastCutOutputPath }),
            mode: 'cors'
        });
    });

    // 播放結果
    cutPlayResultBtn.addEventListener("click", async () => {
        if (!lastCutOutputPath) return;
        await fetch(`${BACKEND_URL}/api/play-file`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_path: lastCutOutputPath }),
            mode: 'cors'
        });
    });


    // ==========================================
    //          分頁三：語音辨識 (Whisper)
    // ==========================================
    const transcribeFileBtn = document.getElementById("transcribe-file-btn");
    const transcribeFilename = document.getElementById("transcribe-filename");
    const modelSelect = document.getElementById("model-select");
    const showTimestampsCb = document.getElementById("show-timestamps");
    const transcribeExecuteBtn = document.getElementById("transcribe-execute-btn");
    const transcribeOpenResultBtn = document.getElementById("transcribe-open-result-btn");

    let selectedTranscribePath = "";
    let lastTxtOutputPath = "";

    function setTranscribeFormDisabled(disabled) {
        transcribeFileBtn.disabled = disabled;
        modelSelect.disabled = disabled;
        showTimestampsCb.disabled = disabled;
        transcribeExecuteBtn.disabled = disabled;
    }

    // 選擇辨識檔案
    transcribeFileBtn.addEventListener("click", async () => {
        try {
            const res = await fetch(`${BACKEND_URL}/api/select-file`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tab_type: "transcribe" }),
                mode: 'cors'
            });
            const data = await res.json();
            
            if (data.success && data.file) {
                selectedTranscribePath = data.file.path;
                transcribeFilename.textContent = data.file.name;
                transcribeExecuteBtn.disabled = false;
                transcribeOpenResultBtn.disabled = true;
            }
        } catch (e) {
            alert("❌ 選取檔案失敗。");
        }
    });

    // 執行語音辨識
    transcribeExecuteBtn.addEventListener("click", async () => {
        if (!selectedTranscribePath) return;
        const modelSize = modelSelect.value;
        const showTimestamps = showTimestampsCb.checked;

        setTranscribeFormDisabled(true);
        showProgress("正在初始化 Whisper 模型...", 0, "載入中", "請稍候...");

        try {
            const res = await fetch(`${BACKEND_URL}/api/transcribe`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ file_path: selectedTranscribePath, model_size: modelSize, show_timestamps: showTimestamps }),
                mode: 'cors'
            });
            const data = await res.json();
            
            if (data.success) {
                // 開始監聽 SSE 進度串流
                listenProgressStream("transcribe");
            } else {
                alert("❌ " + data.message);
                setTranscribeFormDisabled(false);
                hideProgress();
            }
        } catch (e) {
            alert("❌ 語音辨識請求失敗。");
            setTranscribeFormDisabled(false);
            hideProgress();
        }
    });

    function onTranscribeFinished(success, output_path_or_err) {
        setTranscribeFormDisabled(false);
        hideProgress();

        if (success) {
            // output_path_or_err 在這裡是由 API 後續的 check_and_update 來知道的。
            // 由於非同步執行，我們可以直接在本地推導出 txt 路徑，或透過回傳取得。
            // 因為後端 output_path 定義為 檔案名稱_辨識結果.txt，前端也可以本地生成它。
            const dotIndex = selectedTranscribePath.lastIndexOf('.');
            lastTxtOutputPath = selectedTranscribePath.substring(0, dotIndex) + "_辨識結果.txt";
            
            transcribeOpenResultBtn.disabled = false;
            alert("🌻 語音辨識完成！產出結果已轉換為繁體中文字幕。");
        } else {
            alert("❌ 語音辨識失敗！\n\n" + output_path_or_err);
        }
    }

    // 打開辨識結果 txt
    transcribeOpenResultBtn.addEventListener("click", async () => {
        if (!lastTxtOutputPath) return;
        await fetch(`${BACKEND_URL}/api/play-file`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_path: lastTxtOutputPath }),
            mode: 'cors'
        });
    });
});
