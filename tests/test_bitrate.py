"""Tests for the size-budget bitrate calculation and the source-bitrate cap.

Regression for: trimming a short clip out of a large file produced an output
padded up to the size limit (e.g. 1s trimmed from a 100s/100MB source with a
25MB limit came out ~25MB instead of ~1MB), because the target bitrate was
computed purely as budget/duration with no regard for the source bitrate.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from video_compressor import VideoCompressorGUI, calculate_video_bitrate

FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class TestCalculateVideoBitrate(unittest.TestCase):
    def test_scales_bitrate_to_fit_size_budget(self):
        # 25MB budget over 100s: (25 * 0.95 MB in bits - audio) / 100s = 1817 kbps
        self.assertEqual(calculate_video_bitrate(25, 100, source_bitrate_k=8000), 1817)

    def test_caps_bitrate_at_source_bitrate(self):
        # The reported bug: a 1s clip from an ~8000kbps source with a 25MB
        # budget must encode at the source's 8000kbps (~1MB output), not at
        # budget/duration = 194432kbps (~25MB output).
        self.assertEqual(calculate_video_bitrate(25, 1.0, source_bitrate_k=8000), 8000)

    def test_no_cap_when_source_bitrate_unknown(self):
        self.assertEqual(calculate_video_bitrate(25, 1.0, source_bitrate_k=None), 194432)

    def test_returns_none_when_audio_alone_exceeds_budget(self):
        self.assertIsNone(calculate_video_bitrate(0.1, 100))


@unittest.skipUnless(FFMPEG_AVAILABLE, "ffmpeg/ffprobe not on PATH")
class TestGetVideoBitrate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.mp4 = str(Path(cls.tmp.name) / "sample.mp4")
        cls.mkv = str(Path(cls.tmp.name) / "sample.mkv")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "testsrc=duration=2:size=320x240:rate=30",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", cls.mp4],
            check=True, capture_output=True)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", cls.mp4, "-c", "copy", cls.mkv],
            check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_reads_stream_bitrate_from_mp4(self):
        rate = VideoCompressorGUI.get_video_bitrate(None, self.mp4)
        self.assertIsNotNone(rate)
        self.assertGreater(rate, 0)

    def test_falls_back_to_container_bitrate_for_mkv(self):
        # mkv doesn't store per-stream bitrates, so the container-level
        # bitrate must be used instead of returning None
        rate = VideoCompressorGUI.get_video_bitrate(None, self.mkv)
        self.assertIsNotNone(rate)
        self.assertGreater(rate, 0)

    def test_returns_none_for_missing_file(self):
        missing = str(Path(self.tmp.name) / "does-not-exist.mp4")
        self.assertIsNone(VideoCompressorGUI.get_video_bitrate(None, missing))


if __name__ == "__main__":
    unittest.main()
