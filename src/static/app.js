/**
 * YoutubeGrabber - Sunflower Studio JS Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // Dynamic API Base URL for GitHub Pages support
    const API_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.hostname === '::1') ? '' : 'http://localhost:8000';

    // DOM Elements - Navigation & Theme
    const tabs = document.querySelectorAll('.nav-tab');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const openWorkspaceBtn = document.getElementById('open-workspace-btn');
    const dependencyBanner = document.getElementById('dependency-banner');
    const installToolsBtn = document.getElementById('install-tools-btn');
    const connectionBanner = document.getElementById('connection-banner');
    const cleanEnvBtn = document.getElementById('clean-env-btn');

    // DOM Elements - YouTube Tab
    const downloadUrl = document.getElementById('download-url');
    const startDownloadBtn = document.getElementById('start-download-btn');

    // DOM Elements - Cut Tab
    const cutFilePath = document.getElementById('cut-file-path');
    const startH = document.getElementById('start-h');
    const startM = document.getElementById('start-m');
    const startS = document.getElementById('start-s');
    const endH = document.getElementById('end-h');
    const endM = document.getElementById('end-m');
    const endS = document.getElementById('end-s');
    const startCutBtn = document.getElementById('start-cut-btn');

    // DOM Elements - Transcribe Tab
    const transcribeFilePath = document.getElementById('transcribe-file-path');
    const whisperModelSelect = document.getElementById('whisper-model-select');
    const showTimestampsCheck = document.getElementById('show-timestamps-check');
    const startTranscribeBtn = document.getElementById('start-transcribe-btn');

    // DOM Elements - File Manager Tab
    const filesListBody = document.getElementById('files-list-body');

    // DOM Elements - Progress HUD
    const progressContainer = document.getElementById('progress-container');
    const progressTaskName = document.getElementById('progress-task-name');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressBarFill = document.getElementById('progress-bar-fill');

    // DOM Elements - Terminal Console
    const terminalConsole = document.getElementById('terminal-console');
    const clearLogsBtn = document.getElementById('clear-logs-btn');

    // Active State
    let taskCheckInterval = null;

    /* ===================================================
       1. Navigation Tabs & Theme Toggle
       =================================================== */

    // Tab switcher
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const targetPane = document.getElementById(tab.dataset.tab);
            targetPane.classList.add('active');

            // Fetch files list if switching to File Manager
            if (tab.dataset.tab === 'tab-files') {
                loadFiles();
            }
        });
    });

    // Theme Switcher (Dark / Light)
    themeToggleBtn.addEventListener('click', () => {
        const isDark = document.body.classList.contains('theme-dark');
        if (isDark) {
            document.body.classList.remove('theme-dark');
            document.body.classList.add('theme-light');
            themeToggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i> <span>淺色模式</span>';
            localStorage.setItem('sunflower-theme', 'light');
        } else {
            document.body.classList.remove('theme-light');
            document.body.classList.add('theme-dark');
            themeToggleBtn.innerHTML = '<i class="fa-solid fa-moon"></i> <span>深色模式</span>';
            localStorage.setItem('sunflower-theme', 'dark');
        }
    });

    // Read stored theme preference
    const storedTheme = localStorage.getItem('sunflower-theme');
    if (storedTheme === 'light') {
        document.body.classList.remove('theme-dark');
        document.body.classList.add('theme-light');
        themeToggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i> <span>淺色模式</span>';
    }

    // Open workspace folder
    openWorkspaceBtn.addEventListener('click', () => {
        fetch(API_BASE + '/api/open-folder', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (!data.success) showToast("無法開啟程式資料夾：" + data.message, "error");
            });
    });

    // Tool dependency checks and management
    function checkTools() {
        checkToolsWithStatus(null);
    }

    function checkToolsWithStatus(statusData) {
        fetch(API_BASE + '/api/check-tools')
            .then(res => res.json())
            .then(data => {
                if (data.installed) {
                    dependencyBanner.classList.add('hide');
                } else {
                    // 偵測是否已經在背景下載部署中，若在下載中則不需要提醒
                    if (statusData && statusData.active && statusData.type === 'install') {
                        dependencyBanner.classList.add('hide');
                    } else {
                        // 只有當後端已連線時才顯示缺少組件
                        if (isBackendConnected) {
                            dependencyBanner.classList.remove('hide');
                        } else {
                            dependencyBanner.classList.add('hide');
                        }
                    }
                }
            })
            .catch(err => {
                console.error("Error checking tools:", err);
                dependencyBanner.classList.add('hide');
            });
    }

    // Check on page load
    checkTools();

    installToolsBtn.addEventListener('click', () => {
        installToolsBtn.disabled = true;
        installToolsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 下載安裝中...';
        
        fetch(API_BASE + '/api/install-tools', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast("自動下載已啟動", "success");
                } else {
                    showToast(data.message, "error");
                    installToolsBtn.disabled = false;
                    installToolsBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> 一鍵自動安裝';
                }
            })
            .catch(err => {
                showToast("連線後端失敗", "error");
                installToolsBtn.disabled = false;
                installToolsBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> 一鍵自動安裝';
            });
    });

    cleanEnvBtn.addEventListener('click', () => {
        if (confirm("⚠️ 警告：確認要清空本機下載的核心組件嗎？")) {
            fetch(API_BASE + '/api/clean-environment', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        showToast(data.message, "success");
                        // 重新檢查組件狀態以自動顯現缺少工具的黃色 Alert Banner
                        checkTools();
                    } else {
                        showToast("啟動清理失敗：" + data.message, "error");
                    }
                })
                .catch(err => showToast("連線後端失敗", "error"));
        }
    });

    /* ===================================================
       2. Real-time Logging (SSE Server-Sent Events)
       =================================================== */
    
    // Connection status tracking
    let isBackendConnected = false;
    const connectionDot = document.getElementById('connection-dot');

    // 啟動時預設啟動一個 2 秒的連線超時計時器。若 2 秒內未成功與後端連線，即顯示「未連線至背景伺服器」警告
    let disconnectTimeout = setTimeout(() => {
        if (connectionDot) {
            connectionDot.className = 'connection-dot disconnected';
            connectionDot.title = '與後端服務中斷連線...';
        }
        if (connectionBanner) {
            connectionBanner.classList.remove('hide');
        }
        if (dependencyBanner) {
            dependencyBanner.classList.add('hide');
        }
        appendTerminalLog("[SYSTEM] 警告：與背景伺服器失去連線！請確認本地執行檔是否已啟動。");
    }, 2000);

    function setConnectionStatus(connected) {
        if (connected) {
            if (!isBackendConnected) {
                isBackendConnected = true;
                // 自動重新獲取組件狀態與檔案清單，恢復連接
                checkTools();
                loadFiles();
                appendTerminalLog("[SYSTEM] 成功連接至向日葵本地伺服器！🌻");
            }
            isBackendConnected = true;
            if (disconnectTimeout) {
                clearTimeout(disconnectTimeout);
                disconnectTimeout = null;
            }
            if (connectionDot) {
                connectionDot.className = 'connection-dot connected';
                connectionDot.title = '後端服務已連線 🌻';
            }
            if (connectionBanner) {
                connectionBanner.classList.add('hide');
            }
        } else {
            if (isBackendConnected) {
                isBackendConnected = false;
                if (!disconnectTimeout) {
                    disconnectTimeout = setTimeout(() => {
                        if (connectionDot) {
                            connectionDot.className = 'connection-dot disconnected';
                            connectionDot.title = '與後端服務中斷連線...';
                        }
                        if (connectionBanner) {
                            connectionBanner.classList.remove('hide');
                        }
                        if (dependencyBanner) {
                            dependencyBanner.classList.add('hide');
                        }
                        appendTerminalLog("[SYSTEM] 警告：與背景伺服器失去連線！請確認本地執行檔是否已啟動。");
                    }, 2000);
                }
            }
        }
    }

    // Connect to Server-Sent Event log stream
    let eventSource = null;

    function connectSSE() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource(API_BASE + '/api/stream-logs');

        eventSource.onopen = () => {
            setConnectionStatus(true);
        };

        eventSource.onmessage = (event) => {
            const logLineText = event.data;

            // Mark connected on receiving messages
            setConnectionStatus(true);

            // Filter out system connection banner message to avoid spamming the log list
            if (logLineText.includes('成功連接至向日葵日誌串流服務')) {
                return;
            }

            // Check if log contains progress indicators: [PROGRESS] 45
            if (logLineText.startsWith('[PROGRESS]')) {
                const percent = parseInt(logLineText.replace('[PROGRESS]', '').trim());
                updateProgressHUD(percent);
                return;
            }

            // Print to log screen
            appendTerminalLog(logLineText);
        };

        eventSource.onerror = (err) => {
            console.error("SSE connection error:", err);
            setConnectionStatus(false);
        };
    }

    connectSSE();

    function appendTerminalLog(text) {
        if (!text || text.trim() === '') return;
        
        const line = document.createElement('div');
        line.className = 'log-line';
        
        // Add styling for special messages
        if (text.includes('[SYSTEM]')) {
            line.classList.add('system-line');
        } else if (text.includes('核心報錯:') || text.includes('失敗') || text.includes('錯誤:')) {
            line.classList.add('core-err-line');
        }
        
        line.textContent = text;
        terminalConsole.appendChild(line);
        
        // Scroll terminal to bottom
        terminalConsole.scrollTop = terminalConsole.scrollHeight;
    }

    clearLogsBtn.addEventListener('click', () => {
        terminalConsole.innerHTML = '<div class="log-line system-line">[SYSTEM] 終端機日誌已清除。</div>';
    });

    /* ===================================================
       3. Progress HUD Actions
       =================================================== */

    function updateProgressHUD(percent) {
        progressContainer.classList.remove('hide');
        progressPercentage.textContent = `${percent}%`;
        progressBarFill.style.width = `${percent}%`;

        // Auto hide progress HUD when completed
        if (percent >= 100) {
            setTimeout(() => {
                progressContainer.classList.add('hide');
                progressBarFill.style.width = `0%`;
                // Reload files automatically if tab is active
                loadFiles();
            }, 3000);
        }
    }

    // Active State for installation tracking
    let wasInstalling = false;

    // Periodic task status poller
    function startStatusPoller() {
        if (taskCheckInterval) clearInterval(taskCheckInterval);
        
        let toolCheckCounter = 0;
        
        taskCheckInterval = setInterval(() => {
            fetch(API_BASE + '/api/status')
                .then(res => res.json())
                .then(data => {
                    setConnectionStatus(true);
                    
                    // 每隔 3 秒自動同步一次組件安裝狀態，若工具齊全或已在下載則收回異常提示
                    toolCheckCounter++;
                    if (toolCheckCounter >= 3) {
                        toolCheckCounter = 0;
                        checkToolsWithStatus(data);
                    }

                    const buttons = [startDownloadBtn, startCutBtn, startTranscribeBtn];
                    
                    if (data.active) {
                        // Disable buttons
                        buttons.forEach(btn => btn.disabled = true);
                        progressContainer.classList.remove('hide');
                        
                        let prefix = "正在執行任務...";
                        if (data.type === 'download') prefix = "📥 正在下載 YouTube 媒體...";
                        if (data.type === 'cut') prefix = "✂️ 正在進行視訊剪輯...";
                        if (data.type === 'transcribe') prefix = "🎤 AI 語音辨識中，請稍候...";
                        if (data.type === 'install') {
                            prefix = "🌻 正在下載安裝必要核心組件...";
                            wasInstalling = true;
                            installToolsBtn.disabled = true;
                            installToolsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 下載安裝中...';
                        }
                        
                        progressTaskName.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${prefix}`;
                    } else {
                        // Enable buttons
                        buttons.forEach(btn => btn.disabled = false);
                        
                        // If installation has finished, refresh UI
                        if (wasInstalling) {
                            wasInstalling = false;
                            installToolsBtn.disabled = false;
                            installToolsBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> 一鍵自動安裝';
                            checkTools();
                        }
                    }
                })
                .catch(err => {
                    setConnectionStatus(false);
                });
        }, 1000);
    }
    
    startStatusPoller();

    /* ===================================================
       4. Forms Action Trigger (Fetch REST API)
       =================================================== */

    // YouTube Downloader
    startDownloadBtn.addEventListener('click', () => {
        const url = downloadUrl.value.trim();
        const mode = document.querySelector('input[name="download-mode"]:checked').value;

        if (!url) {
            showToast("請輸入 YouTube 網址！", "warning");
            return;
        }

        startDownloadBtn.disabled = true;
        fetch(API_BASE + '/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, mode })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast("下載任務已送出", "success");
            } else {
                showToast(data.message, "error");
                startDownloadBtn.disabled = false;
            }
        })
        .catch(err => {
            showToast("伺服器連線失敗", "error");
            startDownloadBtn.disabled = false;
        });
    });

    // Local Media Cut
    startCutBtn.addEventListener('click', () => {
        const input_path = cutFilePath.value.trim();
        if (!input_path) {
            showToast("請輸入本地檔案路徑或從檔案管理選擇！", "warning");
            return;
        }

        const start_time = getFormattedTime(startH, startM, startS);
        const end_time = getFormattedTime(endH, endM, endS);

        startCutBtn.disabled = true;
        fetch(API_BASE + '/api/cut', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input_path, start_time, end_time })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast("剪輯任務已送出", "success");
            } else {
                showToast(data.message, "error");
                startCutBtn.disabled = false;
            }
        })
        .catch(err => {
            showToast("伺服器連線失敗", "error");
            startCutBtn.disabled = false;
        });
    });

    // Voice Transcriber (Whisper)
    startTranscribeBtn.addEventListener('click', () => {
        const input_path = transcribeFilePath.value.trim();
        if (!input_path) {
            showToast("請輸入本機檔案路徑或從檔案管理選擇！", "warning");
            return;
        }

        const model_size = whisperModelSelect.value;
        const show_timestamps = showTimestampsCheck.checked;

        startTranscribeBtn.disabled = true;
        fetch(API_BASE + '/api/transcribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input_path, model_size, show_timestamps })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast("語音辨識任務已送出", "success");
            } else {
                showToast(data.message, "error");
                startTranscribeBtn.disabled = false;
            }
        })
        .catch(err => {
            showToast("伺服器連線失敗", "error");
            startTranscribeBtn.disabled = false;
        });
    });

    function getFormattedTime(hEl, mEl, sEl) {
        const h = String(parseInt(hEl.value || 0)).padStart(2, '0');
        const m = String(parseInt(mEl.value || 0)).padStart(2, '0');
        const s = String(parseInt(sEl.value || 0)).padStart(2, '0');
        return `${h}:${m}:${s}`;
    }

    /* ===================================================
       5. File Manager Functions
       =================================================== */

    function loadFiles() {
        filesListBody.innerHTML = '<tr><td colspan="4" class="empty-message"><i class="fa-solid fa-circle-notch fa-spin"></i> 載入檔案清單中...</td></tr>';
        
        fetch(API_BASE + '/api/files')
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    filesListBody.innerHTML = `<tr><td colspan="4" class="empty-message text-danger">讀取失敗：${data.message}</td></tr>`;
                    return;
                }

                if (data.files.length === 0) {
                    filesListBody.innerHTML = '<tr><td colspan="4" class="empty-message">目前目錄下尚無下載或編輯後的檔案。</td></tr>';
                    return;
                }

                filesListBody.innerHTML = '';
                data.files.forEach(file => {
                    const row = document.createElement('tr');
                    
                    // Determine file icon
                    let icon = '<i class="fa-solid fa-file"></i>';
                    const nameLower = file.name.toLowerCase();
                    if (nameLower.endsWith('.mp4') || nameLower.endsWith('.mkv') || nameLower.endsWith('.webm') || nameLower.endsWith('.mov') || nameLower.endsWith('.avi')) {
                        icon = '<i class="fa-solid fa-file-video text-warning" style="color: #ffb300;"></i>';
                    } else if (nameLower.endsWith('.mp3') || nameLower.endsWith('.wav') || nameLower.endsWith('.m4a')) {
                        icon = '<i class="fa-solid fa-file-audio text-info" style="color: #2196f3;"></i>';
                    } else if (nameLower.endsWith('.txt')) {
                        icon = '<i class="fa-solid fa-file-lines text-success" style="color: #8bc34a;"></i>';
                    }

                    // Determine file type category label
                    let fileType = '一般檔案';
                    if (nameLower.endsWith('.txt')) fileType = '辨識結果 (.txt)';
                    else if (nameLower.includes('_cut')) fileType = '編輯後檔案';
                    else if (nameLower.includes('_audio') || nameLower.endsWith('.mp3')) fileType = '擷取音訊';
                    else if (nameLower.includes('_video') || nameLower.endsWith('.mp4')) fileType = '擷取影片';

                    row.innerHTML = `
                        <td>${icon} <span class="file-name-span" title="${file.name}">${file.name}</span></td>
                        <td>${file.size_mb} MB</td>
                        <td>${fileType}</td>
                        <td class="action-row">
                            <button class="table-btn btn-play" onclick="openFileLocally('${file.path.replace(/\\/g, '\\\\')}')">
                                <i class="fa-solid fa-desktop"></i> 電腦開啟
                            </button>
                            ${!nameLower.endsWith('.txt') ? `
                                <button class="table-btn btn-cut" onclick="sendToCutter('${file.path.replace(/\\/g, '\\\\')}')">
                                    <i class="fa-solid fa-scissors"></i> 剪輯
                                </button>
                                <button class="table-btn btn-ocr" onclick="sendToTranscribe('${file.path.replace(/\\/g, '\\\\')}')">
                                    <i class="fa-solid fa-microphone-lines"></i> 辨識
                                </button>
                            ` : ''}
                            <button class="table-btn btn-delete" onclick="deleteFileLocally('${file.path.replace(/\\/g, '\\\\')}', '${file.name}')">
                                <i class="fa-solid fa-trash-can"></i> 刪除
                            </button>
                        </td>
                    `;
                    filesListBody.appendChild(row);
                });
            })
            .catch(err => {
                filesListBody.innerHTML = '<tr><td colspan="4" class="empty-message text-danger">伺服器連線失敗。</td></tr>';
            });
    }

    // Expose helpers globally so they can be triggered from onclick attributes in dynamically generated HTML
    window.openFileLocally = function(path) {
        fetch(API_BASE + '/api/open-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        })
        .then(res => res.json())
        .then(data => {
            if (!data.success) showToast("無法開啟檔案：" + data.message, "error");
        });
    };

    window.sendToCutter = function(path) {
        cutFilePath.value = path;
        // Reset times
        startH.value = 0; startM.value = 0; startS.value = 0;
        endH.value = 0; endM.value = 0; endS.value = 10;
        
        // Switch tab
        tabs.forEach(t => t.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));
        
        const cutTabBtn = Array.from(tabs).find(t => t.dataset.tab === 'tab-cut');
        cutTabBtn.classList.add('active');
        document.getElementById('tab-cut').classList.add('active');
        
        showToast("已載入檔案路徑", "success");
    };

    window.sendToTranscribe = function(path) {
        transcribeFilePath.value = path;
        
        // Switch tab
        tabs.forEach(t => t.classList.remove('active'));
        tabPanes.forEach(p => p.classList.remove('active'));
        
        const transcribeTabBtn = Array.from(tabs).find(t => t.dataset.tab === 'tab-transcribe');
        transcribeTabBtn.classList.add('active');
        document.getElementById('tab-transcribe').classList.add('active');
        
        showToast("已載入檔案路徑", "success");
    };

    window.deleteFileLocally = function(path, filename) {
        if (confirm(`確定要永久刪除此檔案嗎？\n檔名: ${filename}`)) {
            fetch(API_BASE + '/api/delete-file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast("檔案已刪除", "success");
                    loadFiles();
                } else {
                    showToast("刪除失敗：" + data.message, "error");
                }
            });
        }
    };

    /* ===================================================
       6. Toast Notification Helper
       =================================================== */

    function showToast(message, type = 'success', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `custom-toast toast-${type}`;
        
        let iconClass = 'fa-check-circle';
        if (type === 'warning') iconClass = 'fa-exclamation-circle';
        if (type === 'error') iconClass = 'fa-times-circle';
        
        toast.innerHTML = `
            <i class="fa-solid ${iconClass}"></i>
            <span>${message}</span>
        `;
        
        if (!document.getElementById('toast-style-tag')) {
            const style = document.createElement('style');
            style.id = 'toast-style-tag';
            style.innerHTML = `
                .custom-toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: rgba(26, 22, 20, 0.95);
                    backdrop-filter: blur(8px);
                    border: 1px solid var(--border-color-active);
                    color: #fff;
                    padding: 14px 24px;
                    border-radius: 12px;
                    z-index: 99999;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                    transform: translateY(-20px);
                    opacity: 0;
                    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                }
                .custom-toast.show {
                    transform: translateY(0);
                    opacity: 1;
                }
                .toast-success i { color: #8bc34a; }
                .toast-warning i { color: #ffb300; }
                .toast-error i { color: #ef5350; }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 50);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, duration);
    }

    /* ===================================================
       7. Native File Selector & Drag-and-Drop
       =================================================== */

    // Select File natively via Python Tkinter dialog
    function setupFileBrowser(btnId, targetInputId) {
        const btn = document.getElementById(btnId);
        const input = document.getElementById(targetInputId);
        if (!btn || !input) return;

        btn.addEventListener('click', () => {
            btn.disabled = true;
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

            fetch(API_BASE + '/api/select-file', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.path) {
                        input.value = data.path;
                        showToast("已選取本機檔案", "success");
                    }
                    btn.disabled = false;
                    btn.innerHTML = originalHTML;
                })
                .catch(err => {
                    console.error("Error selecting file:", err);
                    showToast("連線伺服器選取檔案失敗。", "error");
                    btn.disabled = false;
                    btn.innerHTML = originalHTML;
                });
        });
    }

    // Drag and drop handler to resolve absolute path if file exists in workspace
    function setupDragAndDrop(inputEl) {
        if (!inputEl) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            inputEl.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            inputEl.addEventListener(eventName, () => {
                inputEl.style.borderColor = 'var(--accent-sunflower)';
                inputEl.style.boxShadow = '0 0 0 3px var(--accent-shadow)';
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            inputEl.addEventListener(eventName, () => {
                inputEl.style.borderColor = '';
                inputEl.style.boxShadow = '';
            }, false);
        });

        inputEl.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files && files.length > 0) {
                const file = files[0];
                
                // 優先比對檔案管理清單以獲取完整絕對路徑
                fetch(API_BASE + '/api/files')
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            const matched = data.files.find(f => f.name === file.name);
                            if (matched) {
                                inputEl.value = matched.path;
                                showToast("已自動對接檔案路徑 🌻", "success");
                            } else {
                                showToast(`無法取得「${file.name}」的絕對路徑。建議點擊「瀏覽檔案」選取，或直接放入程式資料夾中。`, "warning", 6000);
                                inputEl.value = file.name;
                            }
                        } else {
                            inputEl.value = file.name;
                        }
                    })
                    .catch(() => {
                        inputEl.value = file.name;
                    });
            }
        });
    }

    setupFileBrowser('browse-cut-btn', 'cut-file-path');
    setupFileBrowser('browse-transcribe-btn', 'transcribe-file-path');

    setupDragAndDrop(cutFilePath);
    setupDragAndDrop(transcribeFilePath);
});
