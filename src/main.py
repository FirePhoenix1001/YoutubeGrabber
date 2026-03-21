# src/main.py
import multiprocessing
import sys
from GUI import App

if __name__ == "__main__":
    # 打包後的穩定性修正，防止在 Windows 多執行緒/程序出現重複啟動問題
    multiprocessing.freeze_support()
    
    app = App()
    app.mainloop()
