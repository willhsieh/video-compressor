# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Look for FFmpeg binaries in a 'ffmpeg' subdirectory
ffmpeg_dir = os.path.join(os.getcwd(), 'ffmpeg')
binaries = []

if os.path.exists(ffmpeg_dir):
    ffmpeg_exe = os.path.join(ffmpeg_dir, 'ffmpeg')
    ffprobe_exe = os.path.join(ffmpeg_dir, 'ffprobe')
    
    if os.path.exists(ffmpeg_exe):
        binaries.append((ffmpeg_exe, '.'))
    if os.path.exists(ffprobe_exe):
        binaries.append((ffprobe_exe, '.'))

# Collect tkinterdnd2 data files and DLLs
datas = []
try:
    tkdnd_datas = collect_data_files('tkinterdnd2')
    datas.extend(tkdnd_datas)
    tkdnd_binaries = collect_dynamic_libs('tkinterdnd2')
    binaries.extend(tkdnd_binaries)
except Exception as e:
    print(f"Note: tkinterdnd2 not found - drag-and-drop will not be available ({e})")

# Collect Pillow data files
try:
    pillow_datas = collect_data_files('PIL')
    datas.extend(pillow_datas)
    pillow_binaries = collect_dynamic_libs('PIL')
    binaries.extend(pillow_binaries)
except Exception as e:
    print(f"Note: Pillow collection issue ({e})")

a = Analysis(
    ['video_compressor.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['tkinterdnd2', 'PIL', 'PIL.Image', 'PIL.ImageTk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='VideoCompressor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # Required for Mac
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)

# Create .app bundle for Mac
app = BUNDLE(
    exe,
    name='VideoCompressor.app',
    icon=None,
    bundle_identifier='com.videocompressor.app',
    info_plist={
        'CFBundleName': 'Video Compressor',
        'CFBundleDisplayName': 'Video Compressor',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
)
