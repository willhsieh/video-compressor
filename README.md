# Video Compressor

A simple GUI application for compressing video files to a specified maximum file size with support for trimming and combining multiple audio tracks.

## Features

- **Simple GUI** - Easy-to-use interface built with tkinter
- **Drag-and-Drop Support** - Simply drag video files into the window to select them
- **Target File Size** - Compress videos to meet a specific maximum file size
- **Video Trimming** - Set start and end timestamps to compress only a portion of the video
- **Audio Track Merging** - Automatically combines multiple audio tracks into a single track
- **Smart Compression** - Calculates optimal bitrate to achieve target file size
- **FPS Preservation** - Automatically detects and preserves the original video framerate
- **GPU Acceleration** - Optional NVIDIA NVENC support for 5-10x faster encoding
- **Automatic Fallback** - Gracefully falls back to CPU if GPU encoding fails
- **Self-Contained Executable** - Option to bundle FFmpeg, making the executable fully standalone

## Requirements

### Runtime Requirements
- **FFmpeg** (if not bundled) - Required for video processing
  - Download from: https://ffmpeg.org/download.html
  - Both `ffmpeg.exe` and `ffprobe.exe` must be in your system PATH or in the same directory as the executable
  - **Note**: If you bundle FFmpeg during the build process, users won't need to install anything!

### Development Requirements (for building from source)
- **Python 3.7+**
- **PyInstaller** (see `requirements.txt`)

## Usage

### Running the Executable

1. Download or build the `VideoCompressor.exe` file
2. Ensure FFmpeg is installed and accessible
3. Double-click `VideoCompressor.exe` to launch the application
4. Fill in the required fields:
   - **Input Video**: Drag-and-drop a video file or click Browse to select one
   - **Output Video**: Choose where to save the compressed video
   - **Max File Size (MB)**: Enter the target maximum file size in megabytes
   - **Start Time**: Starting timestamp (format: HH:MM:SS or seconds, default: 00:00:00)
   - **End Time**: Ending timestamp (format: HH:MM:SS or seconds, leave empty for full video)
   - **Use GPU Acceleration**: Check this box to use NVIDIA GPU encoding (if available)
5. Click "Compress Video" to start the process

### Running from Source

```bash
python video_compressor.py
```

## Building the Windows Executable

### Prerequisites
1. Install Python 3.7 or higher

### Build Steps

#### Option 1: Build with Bundled FFmpeg (Recommended - Fully Standalone)

This creates a single executable that includes FFmpeg, requiring no additional installation from users.

1. **Download FFmpeg binaries automatically:**
   ```cmd
   python download_ffmpeg.py
   ```
   
   Or **manually**:
   - Download from: https://www.gyan.dev/ffmpeg/builds/ (get "ffmpeg-release-essentials.zip")
   - Extract the zip
   - Create a folder named `ffmpeg` in the project directory
   - Copy `ffmpeg.exe` and `ffprobe.exe` from the `bin` folder to the `ffmpeg` folder

2. **Build the executable:**
   ```cmd
   build.bat
   ```
   
3. The standalone executable will be in the `dist` folder

#### Option 2: Build without Bundled FFmpeg

This creates a smaller executable, but users must install FFmpeg separately.

1. Run the build script:
   ```cmd
   build.bat
   ```
   
2. When prompted that FFmpeg is not found, choose to continue

3. The executable will be in the `dist` folder

#### Option 3: Manual Build

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Set up FFmpeg binaries in `ffmpeg` folder

3. Build the executable:
   ```bash
   pyinstaller build_windows.spec --clean
   ```

4. Find the executable in the `dist` folder

### Distributing the Executable

**If you bundled FFmpeg:**
- Simply distribute `VideoCompressor.exe` from the `dist` folder
- The executable is fully self-contained and ready to use!
- No additional installation required from users

**If you didn't bundle FFmpeg:**
- Distribute `VideoCompressor.exe` from the `dist` folder
- Include `ffmpeg.exe` and `ffprobe.exe` in the same directory, OR
- Instruct users to install FFmpeg and add it to their PATH

**Optional:**
- Create an installer using tools like Inno Setup or NSIS for a more professional distribution

## How It Works

1. **Input Validation**: Checks that all inputs are valid and the input file exists
2. **Video Analysis**: Uses ffprobe to determine:
   - Video duration
   - Original framerate (FPS)
3. **Bitrate Calculation**: Calculates the optimal video bitrate to achieve the target file size:
   - Formula: `target_bitrate = (target_size_bits - audio_size_bits) / duration`
   - Reserves 128 kbps for audio
4. **GPU Detection**: Checks if NVIDIA GPU with NVENC support is available
5. **Video Processing**: Uses ffmpeg to:
   - Trim the video based on start/end timestamps
   - Compress with the calculated bitrate
   - **Preserve the original framerate** using the detected FPS
   - Combine audio tracks using the `amix` filter
   - Encode with H.264 using either:
     - **NVENC (GPU)**: h264_nvenc codec for fast encoding
     - **x264 (CPU)**: libx264 codec for compatibility
   - Convert audio to AAC codec
6. **Automatic Fallback**: If GPU encoding fails, automatically retries with CPU
7. **Output**: Saves the compressed video to the specified location

## Supported Video Formats

### Input Formats
- MP4, AVI, MKV, MOV, FLV, WMV, WEBM, and more

### Output Format
- MP4 (H.264 video + AAC audio)

## Tips

- **File Size**: The output file size may not exactly match the target due to encoding overhead, but it will be close
- **Quality**: Larger target sizes will result in better video quality
- **Duration**: Shorter videos can achieve higher quality at the same file size
- **Timestamps**: Use format HH:MM:SS (e.g., 00:01:30) or just seconds (e.g., 90)
- **Audio**: If your video has multiple audio tracks, they will be automatically mixed into stereo
- **Framerate**: The original video's FPS is automatically preserved in the output
- **GPU Encoding**: Enabled by default if NVIDIA GPU detected; 5-10x faster than CPU
- **Automatic Fallback**: If GPU encoding fails, the app automatically retries with CPU encoding

## GPU Acceleration

### Requirements
- **NVIDIA GPU** with NVENC support (GTX 600 series or newer, most modern NVIDIA GPUs)
- **Updated GPU drivers**
- **FFmpeg with NVENC support** (included in most builds)

### Performance
- **GPU Encoding**: 5-10x faster than CPU, minimal CPU usage
- **CPU Encoding**: Slower but works on any system
- The application automatically detects GPU availability on startup

### How It Works
1. On startup, the app tests if NVENC encoding is available
2. If available, the "Use GPU Acceleration" checkbox is enabled and checked by default
3. If not available (no NVIDIA GPU or driver issues), the checkbox is disabled
4. If GPU encoding fails during compression, it automatically falls back to CPU encoding

### Encoding Quality
- Both GPU and CPU encoding produce similar quality at the same bitrate
- GPU uses NVENC preset "p4" (balanced speed/quality)
- CPU uses x264 preset "medium"

## Troubleshooting

### GPU Encoding Issues
- **"No NVIDIA GPU detected"**: You don't have an NVIDIA GPU or drivers aren't installed
- **GPU encoding fails**: The app will automatically retry with CPU encoding
- **Drivers**: Ensure you have the latest NVIDIA drivers installed
- **NVENC unavailable**: Older GPUs (pre-GTX 600) don't support NVENC

### "FFmpeg Not Found" Error
- **If using the bundled executable**: This shouldn't happen - FFmpeg should be included
- **If FFmpeg is not bundled**: 
  - Download FFmpeg from https://ffmpeg.org/download.html
  - Add FFmpeg to your system PATH, or
  - Place `ffmpeg.exe` and `ffprobe.exe` in the same directory as `VideoCompressor.exe`

### Output File Too Large or Too Small
- The bitrate calculation is an estimate
- Try adjusting the target file size
- Video content complexity affects compression efficiency

### Encoding Errors
- Ensure the input video file is not corrupted
- Check that you have write permissions for the output directory
- Verify that the start and end timestamps are valid

## Technical Details

- **GUI Framework**: tkinter (built into Python)
- **Drag-and-Drop**: tkinterdnd2 (bundled in executable)
- **Video Processing**: FFmpeg
- **Video Codecs**: 
  - **GPU**: H.264 (h264_nvenc) with NVENC preset p4
  - **CPU**: H.264 (libx264) with preset medium
- **Audio Codec**: AAC
- **Audio Bitrate**: 128 kbps
- **GPU Detection**: Automatic on startup with test encoding
- **Fallback**: Automatic CPU encoding if GPU fails

## License

This project is provided as-is for educational and personal use.

## Credits

- Built with Python and tkinter
- Video processing powered by FFmpeg
- Packaged with PyInstaller
