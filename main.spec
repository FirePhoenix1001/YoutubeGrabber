# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 取得目前目錄
project_dir = os.path.abspath(os.getcwd())

# 找出 customtkinter 的路徑 (用於打包其資源檔)
# 這裡嘗試從 site-packages 中找出
try:
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    ctk_data = (ctk_path, 'customtkinter')
except ImportError:
    ctk_data = None

# 找出 opencc 的路徑
try:
    import opencc
    opencc_path = os.path.dirname(opencc.__file__)
    opencc_data = (opencc_path, 'opencc')
except ImportError:
    opencc_data = None

datas = [
    ('sunflower.ico', '.'),
    ('tools', 'tools'),
]

if ctk_data:
    datas.append(ctk_data)
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
        'customtkinter',
        'yt_dlp',
        'PIL.ImageResampling' # customtkinter 可能需要
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='sunflower.ico',
)
