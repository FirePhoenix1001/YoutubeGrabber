using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;

namespace IconGenerator
{
    class CreateIcon
    {
        static void Main()
        {
            int size = 256;
            using (Bitmap bmp = new Bitmap(size, size))
            {
                using (Graphics g = Graphics.FromImage(bmp))
                {
                    g.SmoothingMode = SmoothingMode.AntiAlias;
                    g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    g.Clear(Color.Transparent);

                    // 繪製黃色向日葵花瓣 (環繞中心)
                    int cx = size / 2;
                    int cy = size / 2;
                    int petalCount = 12;
                    int rx = 100; // 花瓣橫徑
                    int ry = 30;  // 花瓣縱徑

                    g.TranslateTransform(cx, cy);

                    for (int i = 0; i < petalCount; i++)
                    {
                        g.RotateTransform(360f / petalCount);
                        // 外層深金黃花瓣
                        using (Brush petalBrush = new SolidBrush(Color.FromArgb(255, 179, 0)))
                        {
                            g.FillEllipse(petalBrush, 20, -ry, rx, ry * 2);
                        }
                        // 內層亮黃花瓣增加層次感
                        using (Brush lightPetalBrush = new SolidBrush(Color.FromArgb(255, 235, 59)))
                        {
                            g.FillEllipse(lightPetalBrush, 35, -ry + 8, rx - 20, (ry - 8) * 2);
                        }
                    }

                    g.ResetTransform();

                    // 繪製深棕色花蕊中心
                    using (Brush centerBrush = new SolidBrush(Color.FromArgb(93, 64, 55)))
                    {
                        g.FillEllipse(centerBrush, cx - 55, cy - 55, 110, 110);
                    }

                    // 繪製格線網狀紋路 (使向日葵花蕊更精緻擬真)
                    using (Pen centerPen = new Pen(Color.FromArgb(62, 39, 35), 3))
                    {
                        for (int offset = -40; offset <= 40; offset += 15)
                        {
                            g.DrawLine(centerPen, cx - 45, cy + offset, cx + 45, cy + offset);
                            g.DrawLine(centerPen, cx + offset, cy - 45, cx + offset, cy + 45);
                        }
                    }
                }

                // 儲存為 PNG
                bmp.Save("src/icon.png", System.Drawing.Imaging.ImageFormat.Png);
            }

            // 將 PNG 包裝寫入符合 Windows 標準的 ICO 二進位檔
            byte[] pngBytes = File.ReadAllBytes("src/icon.png");
            using (FileStream fs = new FileStream("src/icon.ico", FileMode.Create))
            {
                // ICO 標頭 (6 bytes)
                fs.WriteByte(0); fs.WriteByte(0); // 保留
                fs.WriteByte(1); fs.WriteByte(0); // 類型: 1 (Icon)
                fs.WriteByte(1); fs.WriteByte(0); // 圖片個數: 1

                // 圖片目錄進入點 (16 bytes)
                fs.WriteByte(0); // 寬度 256 (0 代表 256)
                fs.WriteByte(0); // 高度 256 (0 代表 256)
                fs.WriteByte(0); // 調色盤 (無)
                fs.WriteByte(0); // 保留
                fs.WriteByte(1); fs.WriteByte(0); // 色彩平面 (1)
                fs.WriteByte(32); fs.WriteByte(0); // 每像素位元數 (32)

                // 圖片數據大小 (4 bytes)
                int len = pngBytes.Length;
                fs.WriteByte((byte)(len & 0xFF));
                fs.WriteByte((byte)((len >> 8) & 0xFF));
                fs.WriteByte((byte)((len >> 16) & 0xFF));
                fs.WriteByte((byte)((len >> 24) & 0xFF));

                // 數據偏移位置 (4 bytes, 標頭 6 + 目錄 16 = 22)
                fs.WriteByte(22); fs.WriteByte(0); fs.WriteByte(0); fs.WriteByte(0);

                // 寫入實際 PNG 數據
                fs.Write(pngBytes, 0, len);
            }

            // 刪除暫存 PNG
            File.Delete("src/icon.png");
        }
    }
}
