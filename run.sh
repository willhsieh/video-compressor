#!/bin/bash
# Simple script to run the video compressor application

echo "Starting Video Compressor..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: FFmpeg is not installed"
    echo "Please install FFmpeg to use this application"
    echo "Visit: https://ffmpeg.org/download.html"
    echo ""
fi

# Run the application
python3 video_compressor.py
