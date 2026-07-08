# Quick Build Instructions

## macOS Build

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up FFmpeg (Optional - for bundling)
```bash
# Install FFmpeg via Homebrew
brew install ffmpeg

# Create ffmpeg folder and copy binaries
mkdir -p ffmpeg
cp $(which ffmpeg) ffmpeg/
cp $(which ffprobe) ffmpeg/
```

### Step 3: Build
```bash
pyinstaller build_mac.spec --clean
```

The app bundle will be at `dist/VideoCompressor.app`.

---

## Windows Build

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

### Windows:
```cmd
build.bat
```
When prompted about missing FFmpeg, choose to continue.

### macOS:
```bash
# Don't copy ffmpeg binaries, just build
pyinstaller build_mac.spec --clean
```

Users will need to install FFmpeg separately (`brew install ffmpeg`).

---

## Distribution

### If FFmpeg is Bundled:
✅ Just distribute the single executable/app bundle  
✅ No installation needed for users  
✅ Completely self-contained (includes Pillow for video preview)

### If FFmpeg is Not Bundled:
⚠️ Users need to install FFmpeg separately  
⚠️ Windows: Include `ffmpeg.exe` and `ffprobe.exe` alongside the executable  
⚠️ macOS: Users run `brew install ffmpeg`

---

## Dependencies Bundled in Executable

- **Pillow** - Video preview and timeline thumbnails
- **tkinterdnd2** - Drag-and-drop support
- **FFmpeg** (optional) - Video processing

---

## File Size Comparison

### Windows:
- **Without FFmpeg**: ~15-25 MB
- **With FFmpeg bundled**: ~90-100 MB

### macOS:
- **Without FFmpeg**: ~20-30 MB
- **With FFmpeg bundled**: ~80-90 MB

The bundled version is larger but provides a much better user experience.

---

## Troubleshooting

### "Python not found"
Install Python 3.7+ from https://www.python.org/ or `brew install python`

### "pyinstaller not found" 
Run: `pip install -r requirements.txt`

### "No module named tkinter" (macOS)
```bash
brew install python-tk
```

### FFmpeg download fails (Windows)
Manually download from: https://www.gyan.dev/ffmpeg/builds/  
Extract and place `ffmpeg.exe` and `ffprobe.exe` in the `ffmpeg` folder

### Build fails
```bash
# Windows
pyinstaller build_windows.spec --clean

# macOS
pyinstaller build_mac.spec --clean
```

### "IndexError: tuple index out of range" during build
Your Python is exactly 3.10.0, which has a bytecode bug that crashes
PyInstaller's module scanning (PyInstaller issue #6301). Install Python
3.10.11 or newer — any version except 3.10.0 works — and build again.

### Pillow import errors
```bash
pip install --upgrade Pillow
```
