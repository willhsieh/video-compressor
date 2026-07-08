"""CI smoke test: launch the real GUI on a Windows runner, open a generated
sample video (the code path that flashed console windows), screenshot the app,
and screen-record the whole session so any console flicker is caught on video.

Usage: python ci/smoke_test.py [screenshot.png] [recording.mp4]

Exits nonzero if the app fails to construct, the video fails to load, or the
screenshot was not written, so the workflow fails visibly instead of shipping
a broken exe.
"""
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import video_compressor
from video_compressor import SUBPROCESS_FLAGS

LOAD_VIDEO_DELAY_MS = 1500
CAPTURE_DELAY_MS = 10000
# Failsafe: a stuck mainloop (e.g. an unexpected modal dialog) must not hang
# the CI job until the 6-hour timeout.
HARD_KILL_SECONDS = 120


def make_sample_video(path):
    """Generate a tiny 2s test video so the timeline/probe code paths run."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=15",
         "-pix_fmt", "yuv420p", str(path)],
        capture_output=True, timeout=60, check=True, creationflags=SUBPROCESS_FLAGS,
    )


def start_screen_recording(path):
    """Record the runner's desktop; the recorder itself runs windowless so the
    only console windows in the footage would come from the app under test."""
    return subprocess.Popen(
        ["ffmpeg", "-y", "-f", "gdigrab", "-framerate", "15", "-t", "60", "-i", "desktop",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
         str(path)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=SUBPROCESS_FLAGS,
    )


def stop_screen_recording(recorder):
    try:
        recorder.stdin.write(b"q")  # graceful stop so the mp4 gets finalized
        recorder.stdin.flush()
        recorder.wait(timeout=20)
    except Exception:
        recorder.terminate()


def check_initial_state(app):
    """Assert the app booted into the expected state on a GPU-less CI runner.

    Raises AssertionError (fails the job) if an invariant is violated.
    """
    gpu_text = app.gpu_status_label.cget("text")
    assert "GPU" in gpu_text, f"unexpected GPU status label: {gpu_text!r}"
    assert not app.gpu_available, "CI runner has no NVIDIA GPU; gpu_available must be False"
    assert str(app.compress_btn.cget("state")) == "normal", "Compress button should start enabled"


def check_video_loaded(app):
    """Assert the sample video was probed and its timeline rendered."""
    assert app.video_duration > 0, "ffprobe duration probe did not run"
    assert app.timeline_loaded, "timeline thumbnails were not generated in time"


def main():
    screenshot_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("smoke-screenshot.png")
    recording_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("smoke-recording.mp4")

    killer = threading.Timer(HARD_KILL_SECONDS, lambda: os._exit(2))
    killer.daemon = True
    killer.start()

    ffmpeg_available = shutil.which("ffmpeg") is not None
    sample_path = PROJECT_DIR / "ci" / "sample.mp4"
    if ffmpeg_available:
        make_sample_video(sample_path)

    recorder = None
    if ffmpeg_available and sys.platform == "win32":
        recorder = start_screen_recording(recording_path)

    if video_compressor.DRAG_DROP_AVAILABLE:
        root = video_compressor.TkinterDnD.Tk()
    else:
        import tkinter as tk
        root = tk.Tk()

    app = video_compressor.VideoCompressorGUI(root)
    failures = []

    def load_sample_video():
        app.input_file.set(str(sample_path))
        app.current_video_path = str(sample_path)
        app.load_video_timeline(str(sample_path))

    def capture_and_quit():
        try:
            check_initial_state(app)
            if ffmpeg_available:
                check_video_loaded(app)
            from PIL import ImageGrab
            ImageGrab.grab().save(screenshot_path)
        except Exception as e:
            failures.append(e)
        finally:
            root.destroy()

    if ffmpeg_available:
        root.after(LOAD_VIDEO_DELAY_MS, load_sample_video)
    root.after(CAPTURE_DELAY_MS, capture_and_quit)
    root.mainloop()

    if recorder is not None:
        stop_screen_recording(recorder)

    if failures:
        print(f"SMOKE TEST FAILED: {failures[0]}", file=sys.stderr)
        sys.exit(1)
    if not screenshot_path.exists():
        print("SMOKE TEST FAILED: screenshot was not written", file=sys.stderr)
        sys.exit(1)
    print(f"Smoke test passed; screenshot saved to {screenshot_path}")
    if recorder is not None and recording_path.exists():
        print(f"Screen recording saved to {recording_path}")


if __name__ == "__main__":
    main()
