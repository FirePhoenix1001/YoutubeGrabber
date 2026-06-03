using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Reflection;
using System.Windows.Forms;
using System.Drawing;
using System.Net;
using System.Collections.Generic;

namespace SunflowerLauncher
{
    static class Program
    {
        public static Process pythonProcess;
        public static NotifyIcon trayIcon;
        public static SplashForm splashForm;
        public static bool isExiting = false;
        public static bool hasShownReadyNotification = false;

        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // 1. 單一執行實例檢查與釋放 Port 8000
            KillOtherInstances();
            KillPort8000Process();

            // 2. 解壓內嵌 Python 腳本與靜態網頁資源至 %TEMP%\SunflowerWebStudio
            string tempDir = Path.Combine(Path.GetTempPath(), "SunflowerWebStudio");
            try
            {
                ExtractEmbeddedResources(tempDir);
            }
            catch (Exception ex)
            {
                MessageBox.Show("解壓內建資源失敗: " + ex.Message, "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // 3. 建立啟動日誌控制台 (預設隱藏狀態，但建立視窗代碼以利跨執行緒日誌讀取)
            splashForm = new SplashForm();
            IntPtr forceHandle = splashForm.Handle;

            // 4. 啟動 Python 背景後端伺服器 (設定 Working Directory 為啟動器所在目錄，確保下載路徑可攜)
            pythonProcess = new Process();
            pythonProcess.StartInfo.FileName = "python.exe";
            pythonProcess.StartInfo.Arguments = "\"" + Path.Combine(tempDir, "main.py") + "\"";
            pythonProcess.StartInfo.WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory;
            pythonProcess.StartInfo.UseShellExecute = false;
            pythonProcess.StartInfo.CreateNoWindow = true;
            pythonProcess.StartInfo.RedirectStandardOutput = true;
            pythonProcess.StartInfo.RedirectStandardError = true;

            pythonProcess.OutputDataReceived += (s, e) => {
                if (e.Data != null)
                {
                    splashForm.AppendLog(e.Data);
                }
            };
            pythonProcess.ErrorDataReceived += (s, e) => {
                if (e.Data != null)
                {
                    splashForm.AppendLog(e.Data);
                }
            };

            pythonProcess.EnableRaisingEvents = true;
            pythonProcess.Exited += (s, e) => {
                if (!isExiting)
                {
                    MessageBox.Show("Python 背景伺服器已異常終止！請確認 Python 環境與依賴庫安裝狀態。", "伺服器終止", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    CleanExit();
                }
            };

            try
            {
                pythonProcess.Start();
                pythonProcess.BeginOutputReadLine();
                pythonProcess.BeginErrorReadLine();
            }
            catch (System.ComponentModel.Win32Exception)
            {
                MessageBox.Show("找不到 Python 環境！\n請先安裝 Python，並確認已將其加入 Windows 的環境變數 (Path)。\n\n官方下載網站: https://www.python.org/", "啟動錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // 5. 設定系統工作列常駐圖示
            SetupTrayIcon();
            trayIcon.Visible = true;

            // 6. 啟動背景檢測執行緒，確認 Port 8000 響應
            StartServerCheckTimer();

            // 7. 開始訊息循環 (僅作背景連線，不彈出 Form)
            Application.Run();
        }

        private static void KillOtherInstances()
        {
            try
            {
                Process current = Process.GetCurrentProcess();
                string currentName = current.ProcessName;
                int currentId = current.Id;
                foreach (Process p in Process.GetProcessesByName(currentName))
                {
                    if (p.Id != currentId)
                    {
                        try
                        {
                            p.Kill();
                            p.WaitForExit(2000);
                        }
                        catch { }
                    }
                }
            }
            catch { }
        }

        private static void KillPort8000Process()
        {
            try
            {
                Process p = new Process();
                p.StartInfo.FileName = "cmd.exe";
                p.StartInfo.Arguments = "/c netstat -ano | findstr :8000";
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.RedirectStandardOutput = true;
                p.StartInfo.CreateNoWindow = true;
                p.Start();
                string output = p.StandardOutput.ReadToEnd();
                p.WaitForExit();

                string[] lines = output.Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
                foreach (string line in lines)
                {
                    if (line.Contains("LISTENING") || line.Contains("127.0.0.1:8000"))
                    {
                        string[] tokens = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                        if (tokens.Length > 0)
                        {
                            string pidStr = tokens[tokens.Length - 1].Trim();
                            int pid;
                            if (int.TryParse(pidStr, out pid))
                            {
                                if (pid > 0 && pid != Process.GetCurrentProcess().Id)
                                {
                                    try
                                    {
                                        Process target = Process.GetProcessById(pid);
                                        target.Kill();
                                        target.WaitForExit(1500);
                                    }
                                    catch { }
                                }
                            }
                        }
                    }
                }
            }
            catch { }
        }

        private static void ExtractEmbeddedResources(string targetDir)
        {
            if (!Directory.Exists(targetDir))
            {
                Directory.CreateDirectory(targetDir);
            }
            string staticDir = Path.Combine(targetDir, "static");
            if (!Directory.Exists(staticDir))
            {
                Directory.CreateDirectory(staticDir);
            }

            Assembly assembly = Assembly.GetExecutingAssembly();
            Dictionary<string, string> resourceMap = new Dictionary<string, string>
            {
                { "main.py", Path.Combine(targetDir, "main.py") },
                { "audioProcessor.py", Path.Combine(targetDir, "audioProcessor.py") },
                { "mediaCut.py", Path.Combine(targetDir, "mediaCut.py") },
                { "youtubeDownload.py", Path.Combine(targetDir, "youtubeDownload.py") },
                { "static.index.html", Path.Combine(staticDir, "index.html") },
                { "static.style.css", Path.Combine(staticDir, "style.css") },
                { "static.app.js", Path.Combine(staticDir, "app.js") }
            };

            foreach (KeyValuePair<string, string> pair in resourceMap)
            {
                string resourceName = pair.Key;
                string destPath = pair.Value;
                string actualResourceName = null;

                foreach (string name in assembly.GetManifestResourceNames())
                {
                    if (name.EndsWith(resourceName, StringComparison.OrdinalIgnoreCase))
                    {
                        actualResourceName = name;
                        break;
                    }
                }

                if (actualResourceName == null)
                {
                    throw new FileNotFoundException("找不到內嵌資源: " + resourceName);
                }

                using (Stream stream = assembly.GetManifestResourceStream(actualResourceName))
                {
                    if (stream != null)
                    {
                        using (FileStream fs = new FileStream(destPath, FileMode.Create, FileAccess.Write))
                        {
                            byte[] buffer = new byte[8192];
                            int read;
                            while ((read = stream.Read(buffer, 0, buffer.Length)) > 0)
                            {
                                fs.Write(buffer, 0, read);
                            }
                        }
                    }
                }
            }
        }

        private static void SetupTrayIcon()
        {
            trayIcon = new NotifyIcon();
            trayIcon.Text = "YoutubeGrabber";
            trayIcon.Icon = CreateSunflowerIcon();

            ContextMenu contextMenu = new ContextMenu();
            contextMenu.MenuItems.Add("開啟網頁端", (s, e) => OpenWebStudio());
            contextMenu.MenuItems.Add("顯示日誌控制台", (s, e) => ShowConsole());
            contextMenu.MenuItems.Add("-");
            contextMenu.MenuItems.Add("結束程式", (s, e) => CleanExit());

            trayIcon.ContextMenu = contextMenu;
            trayIcon.DoubleClick += (s, e) => OpenWebStudio();
        }

        private static void OpenWebStudio()
        {
            try
            {
                Process.Start("https://FirePhoenix1001.github.io/WedTest/");
            }
            catch (Exception ex)
            {
                MessageBox.Show("無法開啟網頁端: " + ex.Message, "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void ShowConsole()
        {
            if (splashForm != null)
            {
                splashForm.Show();
                splashForm.WindowState = FormWindowState.Normal;
                splashForm.Activate();
            }
        }

        private static void StartServerCheckTimer()
        {
            Thread checkThread = new Thread(() => {
                while (!isExiting)
                {
                    if (IsServerResponding())
                    {
                        if (trayIcon != null && !hasShownReadyNotification)
                        {
                            trayIcon.ShowBalloonTip(3000, "YoutubeGrabber", "背景伺服器已就緒！🌻", ToolTipIcon.Info);
                            hasShownReadyNotification = true;
                        }
                        break;
                    }
                    Thread.Sleep(500);
                }
            });
            checkThread.IsBackground = true;
            checkThread.Start();
        }

        private static bool IsServerResponding()
        {
            try
            {
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create("http://127.0.0.1:8000/api/status");
                req.Timeout = 1000;
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                {
                    return resp.StatusCode == HttpStatusCode.OK;
                }
            }
            catch { }
            return false;
        }

        private static Icon CreateSunflowerIcon()
        {
            try
            {
                using (Bitmap bmp = new Bitmap(16, 16))
                {
                    using (Graphics g = Graphics.FromImage(bmp))
                    {
                        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
                        g.Clear(Color.Transparent);

                        // 繪製綠色葉柄
                        g.FillRectangle(Brushes.ForestGreen, 7, 8, 2, 8);

                        // 繪製黃色向日葵花瓣
                        int cx = 8;
                        int cy = 6;
                        int r = 4;
                        for (int angle = 0; angle < 360; angle += 45)
                        {
                            double rad = angle * Math.PI / 180.0;
                            int px = (int)(cx + r * Math.Cos(rad));
                            int py = (int)(cy + r * Math.Sin(rad));
                            g.FillEllipse(Brushes.Gold, px - 2, py - 2, 4, 4);
                        }

                        // 繪製棕色花蕊中心
                        g.FillEllipse(Brushes.SaddleBrown, cx - 2, cy - 2, 4, 4);
                    }
                    return Icon.FromHandle(bmp.GetHicon());
                }
            }
            catch
            {
                return SystemIcons.Application;
            }
        }

        public static void CleanExit()
        {
            isExiting = true;

            if (trayIcon != null)
            {
                trayIcon.Visible = false;
                trayIcon.Dispose();
            }

            if (pythonProcess != null && !pythonProcess.HasExited)
            {
                try
                {
                    pythonProcess.Kill();
                    pythonProcess.WaitForExit(1000);
                }
                catch { }
            }

            KillPort8000Process();
            Application.Exit();
        }
    }

    public class SplashForm : Form
    {
        // 視窗無邊框拖曳 API
        public const int WM_NCLBUTTONDOWN = 0xA1;
        public const int HT_CAPTION = 0x2;

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        public static extern int SendMessage(IntPtr hWnd, int Msg, int wParam, int lParam);
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        public static extern bool ReleaseCapture();

        private Label lblTitle;
        private Label lblSubtitle;
        private Label lblStatus;
        private Label lblMin;
        private Label lblClose;
        private Label lblProgressPct;
        private Panel pnlProgressBg;
        private Panel pnlProgressFill;
        private TextBox txtLogs;
        private Panel pnlLogBorder;

        public SplashForm()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Size = new Size(550, 380);
            this.FormBorderStyle = FormBorderStyle.None;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(18, 18, 24);
            this.Text = "Sunflower Web Studio - Launcher Console";
            this.ShowInTaskbar = true;

            this.MouseDown += Form_MouseDown;

            this.Paint += (s, e) => {
                using (Pen pen = new Pen(Color.FromArgb(63, 63, 70), 1))
                {
                    e.Graphics.DrawRectangle(pen, 0, 0, this.Width - 1, this.Height - 1);
                }
            };

            // 1. 標題與副標題
            lblTitle = new Label();
            lblTitle.Text = "SUNFLOWER";
            lblTitle.Font = new Font("Segoe UI", 18, FontStyle.Bold);
            lblTitle.ForeColor = Color.Gold;
            lblTitle.Location = new Point(20, 15);
            lblTitle.AutoSize = true;
            lblTitle.MouseDown += Form_MouseDown;
            this.Controls.Add(lblTitle);

            lblSubtitle = new Label();
            lblSubtitle.Text = "PORTABLE WEB STUDIO - LOG CONSOLE";
            lblSubtitle.Font = new Font("Segoe UI", 8, FontStyle.Regular);
            lblSubtitle.ForeColor = Color.FromArgb(161, 161, 170);
            lblSubtitle.Location = new Point(24, 48);
            lblSubtitle.AutoSize = true;
            lblSubtitle.MouseDown += Form_MouseDown;
            this.Controls.Add(lblSubtitle);

            // 2. 最小化與隱藏按鈕
            lblMin = new Label();
            lblMin.Text = "—";
            lblMin.Font = new Font("Segoe UI", 10, FontStyle.Bold);
            lblMin.ForeColor = Color.FromArgb(113, 113, 122);
            lblMin.Location = new Point(490, 15);
            lblMin.Size = new Size(20, 20);
            lblMin.TextAlign = ContentAlignment.MiddleCenter;
            lblMin.Cursor = Cursors.Hand;
            lblMin.Click += (s, e) => this.WindowState = FormWindowState.Minimized;
            lblMin.MouseEnter += (s, e) => lblMin.ForeColor = Color.White;
            lblMin.MouseLeave += (s, e) => lblMin.ForeColor = Color.FromArgb(113, 113, 122);
            this.Controls.Add(lblMin);

            lblClose = new Label();
            lblClose.Text = "×";
            lblClose.Font = new Font("Segoe UI", 14, FontStyle.Bold);
            lblClose.ForeColor = Color.FromArgb(113, 113, 122);
            lblClose.Location = new Point(515, 12);
            lblClose.Size = new Size(20, 20);
            lblClose.TextAlign = ContentAlignment.MiddleCenter;
            lblClose.Cursor = Cursors.Hand;
            lblClose.Click += (s, e) => {
                this.Hide();
            };
            lblClose.MouseEnter += (s, e) => lblClose.ForeColor = Color.FromArgb(239, 68, 68);
            lblClose.MouseLeave += (s, e) => lblClose.ForeColor = Color.FromArgb(113, 113, 122);
            this.Controls.Add(lblClose);

            // 3. 日誌框架
            pnlLogBorder = new Panel();
            pnlLogBorder.Location = new Point(20, 85);
            pnlLogBorder.Size = new Size(510, 215);
            pnlLogBorder.BackColor = Color.FromArgb(39, 39, 42);
            pnlLogBorder.Padding = new Padding(1);
            this.Controls.Add(pnlLogBorder);

            txtLogs = new TextBox();
            txtLogs.Multiline = true;
            txtLogs.ReadOnly = true;
            txtLogs.ScrollBars = ScrollBars.Vertical;
            txtLogs.BackColor = Color.FromArgb(9, 9, 11);
            txtLogs.ForeColor = Color.FromArgb(228, 228, 231);
            txtLogs.Font = new Font("Consolas", 9, FontStyle.Regular);
            txtLogs.BorderStyle = BorderStyle.None;
            txtLogs.Dock = DockStyle.Fill;
            pnlLogBorder.Controls.Add(txtLogs);

            // 4. 進度狀態與百分比 Label
            lblStatus = new Label();
            lblStatus.Text = "伺服器運行中...";
            lblStatus.Font = new Font("Segoe UI", 9, FontStyle.Regular);
            lblStatus.ForeColor = Color.FromArgb(212, 212, 216);
            lblStatus.Location = new Point(20, 312);
            lblStatus.Size = new Size(350, 20);
            this.Controls.Add(lblStatus);

            lblProgressPct = new Label();
            lblProgressPct.Text = "100%";
            lblProgressPct.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            lblProgressPct.ForeColor = Color.Gold;
            lblProgressPct.Location = new Point(490, 312);
            lblProgressPct.Size = new Size(40, 20);
            lblProgressPct.TextAlign = ContentAlignment.TopRight;
            this.Controls.Add(lblProgressPct);

            // 5. 自訂進度條
            pnlProgressBg = new Panel();
            pnlProgressBg.Location = new Point(20, 335);
            pnlProgressBg.Size = new Size(510, 8);
            pnlProgressBg.BackColor = Color.FromArgb(39, 39, 42);
            this.Controls.Add(pnlProgressBg);

            pnlProgressFill = new Panel();
            pnlProgressFill.Location = new Point(0, 0);
            pnlProgressFill.Size = new Size(510, 8); // 預設拉滿
            pnlProgressFill.BackColor = Color.Gold;
            pnlProgressBg.Controls.Add(pnlProgressFill);

            this.FormClosing += (s, e) => {
                if (e.CloseReason == CloseReason.UserClosing)
                {
                    e.Cancel = true;
                    this.Hide();
                }
            };
        }

        private void Form_MouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                ReleaseCapture();
                SendMessage(Handle, WM_NCLBUTTONDOWN, HT_CAPTION, 0);
            }
        }

        public void AppendLog(string text)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new Action<string>(AppendLog), text);
                return;
            }

            if (text.Contains("[PROGRESS]"))
            {
                try
                {
                    string pctStr = text.Replace("[PROGRESS]", "").Trim();
                    int val;
                    if (int.TryParse(pctStr, out val))
                    {
                        UpdateProgress(val);
                    }
                }
                catch { }
                return;
            }

            string cleanText = text.Trim();
            if (cleanText.StartsWith("[SYSTEM]"))
            {
                lblStatus.Text = cleanText.Replace("[SYSTEM]", "").Trim();
            }

            txtLogs.AppendText(text + Environment.NewLine);
            txtLogs.SelectionStart = txtLogs.TextLength;
            txtLogs.ScrollToCaret();
        }

        private void UpdateProgress(int percentage)
        {
            if (percentage < 0) percentage = 0;
            if (percentage > 100) percentage = 100;

            lblProgressPct.Text = percentage + "%";
            int fillWidth = (int)((pnlProgressBg.Width * percentage) / 100.0);
            pnlProgressFill.Width = fillWidth;
        }
    }
}
