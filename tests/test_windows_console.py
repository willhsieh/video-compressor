"""Guards against the Windows console-flicker bug.

The main exe is built windowed (console=False in build_windows.spec), but on
Windows every ffmpeg/ffprobe child process opens its own console window unless
the call passes creationflags=subprocess.CREATE_NO_WINDOW. These tests enforce
that invariant without needing a Windows machine.
"""
import ast
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_DIR / "video_compressor.py"

sys.path.insert(0, str(PROJECT_DIR))

try:
    import tkinter  # noqa: F401
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


def subprocess_calls(tree):
    """Yield every ast.Call node that invokes subprocess.run/Popen/etc."""
    spawning = {"run", "Popen", "call", "check_call", "check_output"}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr in spawning
        ):
            yield node


class TestNoConsoleFlicker(unittest.TestCase):
    def test_every_subprocess_call_hides_console_window(self):
        tree = ast.parse(SOURCE.read_text())
        calls = list(subprocess_calls(tree))
        self.assertGreater(len(calls), 0, "expected subprocess calls in video_compressor.py")

        missing = [
            node.lineno
            for node in calls
            if not any(kw.arg == "creationflags" for kw in node.keywords)
        ]
        self.assertEqual(
            missing,
            [],
            f"subprocess calls at lines {missing} of video_compressor.py do not pass "
            "creationflags=SUBPROCESS_FLAGS — each one flashes a console window on Windows",
        )

    @unittest.skipUnless(TKINTER_AVAILABLE, "tkinter not available in this Python")
    def test_subprocess_flags_constant_matches_platform(self):
        import video_compressor

        if sys.platform == "win32":
            self.assertEqual(video_compressor.SUBPROCESS_FLAGS, subprocess.CREATE_NO_WINDOW)
        else:
            self.assertEqual(video_compressor.SUBPROCESS_FLAGS, 0)


if __name__ == "__main__":
    unittest.main()
