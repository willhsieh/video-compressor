# Quick Build Instructions

## For a Fully Standalone Executable (Recommended)

### Step 1: Download FFmpeg
```cmd
python download_ffmpeg.py
```

This automatically downloads and sets up FFmpeg binaries in the `ffmpeg` folder.

### Step 2: Build
```cmd
build.bat
```

The executable in `dist/VideoCompressor.exe` will be fully self-contained with FFmpeg bundled inside.

---

## For a Smaller Executable (Users Need FFmpeg)

### Just Run:
```cmd
build.bat
```

When prompted about missing FFmpeg, choose to continue. Users will need to install FFmpeg separately.

---

## Distribution

### If FFmpeg is Bundled:
✅ Just distribute the single `VideoCompressor.exe` file  
✅ No installation needed for users  
✅ Completely self-contained  

### If FFmpeg is Not Bundled:
⚠️ Users need to install FFmpeg separately, OR  
⚠️ Include `ffmpeg.exe` and `ffprobe.exe` alongside `VideoCompressor.exe`

---

## File Size Comparison

- **Without FFmpeg**: ~12-18 MB (includes drag-and-drop support)
- **With FFmpeg bundled**: ~85-95 MB

The bundled version is larger but provides a much better user experience since no additional installation is required.

---

## Troubleshooting

### "Python not found"
Install Python 3.7+ from https://www.python.org/

### "pyinstaller not found" 
Run: `pip install -r requirements.txt`

### FFmpeg download fails
Manually download from: https://www.gyan.dev/ffmpeg/builds/  
Extract and place `ffmpeg.exe` and `ffprobe.exe` in the `ffmpeg` folder

### Build fails
Try: `pyinstaller build_windows.spec --clean`
