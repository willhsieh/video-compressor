@echo off
echo ========================================
echo Video Compressor Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check for FFmpeg binaries
if not exist "ffmpeg\ffmpeg.exe" (
    echo.
    echo WARNING: FFmpeg binaries not found in 'ffmpeg' folder!
    echo.
    echo To bundle FFmpeg with your executable, please:
    echo 1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
    echo    (Get the "ffmpeg-release-essentials.zip")
    echo 2. Extract the zip file
    echo 3. Create a folder named 'ffmpeg' in this directory
    echo 4. Copy ffmpeg.exe and ffprobe.exe from the 'bin' folder to 'ffmpeg' folder
    echo.
    echo You can continue building without FFmpeg, but users will need to install it separately.
    echo.
    choice /C YN /M "Continue without bundling FFmpeg"
    if errorlevel 2 exit /b 1
) else (
    echo Found FFmpeg binaries - will bundle with executable
)

REM Install requirements
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM Build executable
echo.
echo Building executable...
pyinstaller build_windows.spec --clean
if errorlevel 1 (
    echo Error: Failed to build executable
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD COMPLETE!
echo ========================================
echo Executable location: dist\VideoCompressor.exe
echo.
if exist "ffmpeg\ffmpeg.exe" (
    echo FFmpeg has been bundled with the executable.
    echo The executable is fully self-contained!
) else (
    echo NOTE: FFmpeg was not bundled.
    echo Users will need to install FFmpeg separately.
)
echo.
pause
