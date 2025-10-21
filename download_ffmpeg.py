"""
Helper script to download and extract FFmpeg binaries for Windows.
Run this before building the executable to bundle FFmpeg.
"""

import os
import sys
import urllib.request
import zipfile
import shutil


FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
DOWNLOAD_PATH = "ffmpeg-release-essentials.zip"
EXTRACT_PATH = "ffmpeg_temp"
TARGET_DIR = "ffmpeg"


def download_ffmpeg():
    """Download FFmpeg essentials build."""
    print("Downloading FFmpeg from gyan.dev...")
    print(f"URL: {FFMPEG_URL}")
    print()
    
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size)
        bar_length = 40
        filled = int(bar_length * percent / 100)
        bar = '=' * filled + '-' * (bar_length - filled)
        sys.stdout.write(f'\r[{bar}] {percent:.1f}%')
        sys.stdout.flush()
    
    urllib.request.urlretrieve(FFMPEG_URL, DOWNLOAD_PATH, reporthook=progress_hook)
    print("\n\nDownload complete!")


def extract_ffmpeg():
    """Extract FFmpeg binaries from the downloaded zip."""
    print("\nExtracting FFmpeg...")
    
    # Create temporary extraction directory
    os.makedirs(EXTRACT_PATH, exist_ok=True)
    
    with zipfile.ZipFile(DOWNLOAD_PATH, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_PATH)
    
    # Find the bin folder (it's nested in a versioned folder)
    bin_folder = None
    for root, dirs, files in os.walk(EXTRACT_PATH):
        if 'bin' in dirs:
            bin_folder = os.path.join(root, 'bin')
            break
    
    if not bin_folder:
        raise Exception("Could not find bin folder in FFmpeg archive")
    
    # Create target directory
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # Copy ffmpeg.exe and ffprobe.exe
    ffmpeg_exe = os.path.join(bin_folder, 'ffmpeg.exe')
    ffprobe_exe = os.path.join(bin_folder, 'ffprobe.exe')
    
    if os.path.exists(ffmpeg_exe):
        shutil.copy2(ffmpeg_exe, os.path.join(TARGET_DIR, 'ffmpeg.exe'))
        print(f"✓ Copied ffmpeg.exe to {TARGET_DIR}/")
    else:
        print("✗ Warning: ffmpeg.exe not found")
    
    if os.path.exists(ffprobe_exe):
        shutil.copy2(ffprobe_exe, os.path.join(TARGET_DIR, 'ffprobe.exe'))
        print(f"✓ Copied ffprobe.exe to {TARGET_DIR}/")
    else:
        print("✗ Warning: ffprobe.exe not found")


def cleanup():
    """Clean up temporary files."""
    print("\nCleaning up temporary files...")
    
    if os.path.exists(DOWNLOAD_PATH):
        os.remove(DOWNLOAD_PATH)
        print(f"✓ Removed {DOWNLOAD_PATH}")
    
    if os.path.exists(EXTRACT_PATH):
        shutil.rmtree(EXTRACT_PATH)
        print(f"✓ Removed {EXTRACT_PATH}/")


def main():
    print("=" * 60)
    print("FFmpeg Downloader for Video Compressor")
    print("=" * 60)
    print()
    
    # Check if FFmpeg already exists
    if os.path.exists(os.path.join(TARGET_DIR, 'ffmpeg.exe')) and \
       os.path.exists(os.path.join(TARGET_DIR, 'ffprobe.exe')):
        print(f"FFmpeg binaries already exist in '{TARGET_DIR}' folder.")
        response = input("Do you want to re-download? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted.")
            return
    
    try:
        # Download
        download_ffmpeg()
        
        # Extract
        extract_ffmpeg()
        
        # Cleanup
        cleanup()
        
        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"FFmpeg binaries are ready in the '{TARGET_DIR}' folder.")
        print("You can now run build.bat to create the executable with")
        print("FFmpeg bundled inside.")
        print()
        
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nIf automatic download fails, please manually:")
        print(f"1. Download FFmpeg from: {FFMPEG_URL}")
        print("2. Extract the zip file")
        print(f"3. Copy ffmpeg.exe and ffprobe.exe to '{TARGET_DIR}' folder")
        sys.exit(1)


if __name__ == "__main__":
    main()
