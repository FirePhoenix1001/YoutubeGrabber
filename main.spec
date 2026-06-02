# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 取得目前目錄
project_dir = os.path.abspath(os.getcwd())

# 找出 opencc 的路徑 (用於簡繁轉換資源)
try:
    import opencc
    opencc_path = os.path.dirname(opencc.__file__)
    opencc_data = (opencc_path, 'opencc')
except ImportError:
    opencc_data = None

# 定義要打包的資源
# 1. 為了實現「極致前後端分離」，web 前端目錄不打包進 exe。使用者可直接開啟外部的 web/index.html
# 2. tools 資料夾改為動態下載，因此亦不進行靜態打包
datas = [
    ('sunflower.ico', '.'),
]

if opencc_data:
    datas.append(opencc_data)

a = Analysis(
    ['src/main.py'],
    pathex=[os.path.join(project_dir, 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'faster_whisper',
        'opencc',
        'yt_dlp',
        'flask',
        'flask_cors'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['customtkinter', 'PIL', 'eel', 'bottle', 'gevent'], # 排除未使用的 Eel、Tkinter 桌面與圖片套件以極致優化體積
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YoutubeGrabber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # 打包發行版本隱藏後台主控台視窗 (Eel 被 Flask 取代，網頁將自動彈出)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='sunflower.ico',
)
