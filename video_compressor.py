import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import json
import threading
import re
import sys

# Try to import tkinterdnd2 for drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False


class VideoCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Compressor")
        self.root.geometry("600x570")
        self.root.resizable(False, False)
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.max_size_mb = tk.StringVar(value="25")
        self.start_time = tk.StringVar(value="00:00:00")
        self.end_time = tk.StringVar(value="")
        self.use_gpu = tk.BooleanVar(value=False)
        self.processing = False
        self.gpu_available = False
        
        self.setup_ui()
        self.setup_drag_drop()
        self.check_gpu_availability()
        
    def setup_ui(self):
        # Title
        title_label = tk.Label(self.root, text="Video Compressor", font=("Arial", 18, "bold"))
        title_label.pack(pady=10)
        
        # Input file selection
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(input_frame, text="Input Video:", font=("Arial", 10)).pack(anchor="w")
        
        input_entry_frame = tk.Frame(input_frame)
        input_entry_frame.pack(fill="x", pady=5)
        
        self.input_entry = tk.Entry(input_entry_frame, textvariable=self.input_file, width=50)
        self.input_entry.pack(side="left", fill="x", expand=True)
        tk.Button(input_entry_frame, text="Browse", command=self.browse_input).pack(side="left", padx=5)
        
        # Output file selection
        output_frame = tk.Frame(self.root)
        output_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(output_frame, text="Output Video:", font=("Arial", 10)).pack(anchor="w")
        
        output_entry_frame = tk.Frame(output_frame)
        output_entry_frame.pack(fill="x", pady=5)
        
        tk.Entry(output_entry_frame, textvariable=self.output_file, width=50).pack(side="left", fill="x", expand=True)
        tk.Button(output_entry_frame, text="Browse", command=self.browse_output).pack(side="left", padx=5)
        
        # Max file size
        size_frame = tk.Frame(self.root)
        size_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(size_frame, text="Max File Size (MB):", font=("Arial", 10)).pack(anchor="w")
        tk.Entry(size_frame, textvariable=self.max_size_mb, width=20).pack(anchor="w", pady=5)
        
        # Start timestamp
        start_frame = tk.Frame(self.root)
        start_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(start_frame, text="Start Time (HH:MM:SS or seconds):", font=("Arial", 10)).pack(anchor="w")
        tk.Entry(start_frame, textvariable=self.start_time, width=20).pack(anchor="w", pady=5)
        
        # End timestamp
        end_frame = tk.Frame(self.root)
        end_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(end_frame, text="End Time (HH:MM:SS or seconds, leave empty for end):", font=("Arial", 10)).pack(anchor="w")
        tk.Entry(end_frame, textvariable=self.end_time, width=20).pack(anchor="w", pady=5)
        
        # GPU acceleration checkbox
        gpu_frame = tk.Frame(self.root)
        gpu_frame.pack(fill="x", padx=20, pady=5)
        
        self.gpu_checkbox = tk.Checkbutton(
            gpu_frame,
            text="Use GPU Acceleration (NVIDIA NVENC)",
            variable=self.use_gpu,
            font=("Arial", 10)
        )
        self.gpu_checkbox.pack(anchor="w")
        
        self.gpu_status_label = tk.Label(gpu_frame, text="Checking GPU...", font=("Arial", 8), fg="gray")
        self.gpu_status_label.pack(anchor="w", padx=20)
        
        # Progress bar
        self.progress_frame = tk.Frame(self.root)
        self.progress_frame.pack(fill="x", padx=20, pady=10)
        
        self.progress_label = tk.Label(self.progress_frame, text="", font=("Arial", 9))
        self.progress_label.pack(anchor="w")
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", pady=5)
        
        # Compress button
        self.compress_btn = tk.Button(self.root, text="Compress Video", command=self.start_compression,
                                       bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                                       padx=20, pady=10)
        self.compress_btn.pack(pady=20)
        
    def setup_drag_drop(self):
        """Setup drag-and-drop functionality for input files."""
        if DRAG_DROP_AVAILABLE:
            # Register the input entry as a drop target
            self.input_entry.drop_target_register(DND_FILES)
            self.input_entry.dnd_bind('<<Drop>>', self.on_drop)
            
            # Also register the whole window as a drop target
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_drop)
        else:
            # Fallback: Use Windows-specific drag-and-drop
            try:
                self.root.tk.eval('catch {tk_setPalette background}')
                self.root.drop_target_register('DND_Files')
                self.root.dnd_bind('<<Drop>>', self.on_drop)
            except:
                pass  # Drag-and-drop not available
    
    def on_drop(self, event):
        """Handle dropped files."""
        try:
            # Get the dropped file path
            files = event.data
            
            # Handle different formats
            if isinstance(files, str):
                # Remove curly braces and quotes that tkinterdnd2 may add
                files = files.strip('{}').strip()
                # Split multiple files (take only the first one)
                file_list = files.split('} {')
                file_path = file_list[0].strip('"').strip()
            else:
                file_path = str(files)
            
            # Validate it's a file
            if os.path.isfile(file_path):
                self.input_file.set(file_path)
                # Auto-suggest output filename
                if not self.output_file.get():
                    base, ext = os.path.splitext(file_path)
                    self.output_file.set(f"{base}_compressed{ext}")
                return 'break'
        except Exception as e:
            print(f"Error handling drop: {e}")
        return 'break'
    
    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Input Video",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            # Auto-suggest output filename
            if not self.output_file.get():
                base, ext = os.path.splitext(filename)
                self.output_file.set(f"{base}_compressed{ext}")
    
    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save Output Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
    
    def validate_inputs(self):
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input video file.")
            return False
        
        if not os.path.exists(self.input_file.get()):
            messagebox.showerror("Error", "Input file does not exist.")
            return False
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Please specify an output file.")
            return False
        
        try:
            max_size = float(self.max_size_mb.get())
            if max_size <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Max file size must be a positive number.")
            return False
        
        return True
    
    def start_compression(self):
        if not self.validate_inputs():
            return
        
        if self.processing:
            messagebox.showwarning("Warning", "Processing already in progress.")
            return
        
        self.processing = True
        self.compress_btn.config(state="disabled")
        self.progress_label.config(text="Processing video...")
        self.progress_bar.start()
        
        # Run compression in a separate thread
        thread = threading.Thread(target=self.compress_video)
        thread.daemon = True
        thread.start()
    
    def compress_video(self):
        try:
            input_path = self.input_file.get()
            output_path = self.output_file.get()
            max_size_mb = float(self.max_size_mb.get())
            start_time = self.start_time.get()
            end_time = self.end_time.get()
            
            # Get video duration, FPS, and audio track count
            duration = self.get_video_duration(input_path)
            fps = self.get_video_fps(input_path)
            audio_track_count = self.get_audio_track_count(input_path)
            
            # Calculate target duration based on timestamps
            start_seconds = self.parse_time(start_time)
            if end_time:
                end_seconds = self.parse_time(end_time)
            else:
                end_seconds = duration
            
            target_duration = end_seconds - start_seconds
            
            if target_duration <= 0:
                self.show_error("Invalid time range. End time must be greater than start time.")
                return
            
            # Calculate target bitrate (in bits per second)
            # Formula: (target_size_in_bits) / duration_in_seconds
            # Reserve some space for audio (128 kbps) and overhead
            target_size_bits = max_size_mb * 8 * 1024 * 1024  # Convert MB to bits
            audio_bitrate = 128  # kbps
            audio_size_bits = audio_bitrate * 1024 * target_duration
            video_size_bits = target_size_bits - audio_size_bits
            
            if video_size_bits <= 0:
                self.show_error("Target file size is too small for the specified duration.")
                return
            
            target_video_bitrate = int(video_size_bits / target_duration)  # bits per second
            target_video_bitrate_k = int(target_video_bitrate / 1024)  # Convert to kbps
            
            # Determine if we should use GPU
            use_gpu_encoding = self.use_gpu.get() and self.gpu_available
            
            # Build ffmpeg command
            ffmpeg_path = get_ffmpeg_path('ffmpeg')
            cmd = [ffmpeg_path, '-y']
            
            # Add hardware acceleration input if using GPU
            if use_gpu_encoding:
                cmd.extend(['-hwaccel', 'cuda'])
            
            cmd.extend(['-i', input_path])
            
            # Add start time
            if start_time and start_time != "00:00:00":
                cmd.extend(['-ss', start_time])
            
            # Add end time (as duration from start)
            if end_time:
                cmd.extend(['-t', str(target_duration)])
            
            # Build audio filter based on number of tracks
            audio_filter = self.build_audio_filter(audio_track_count)
            if audio_filter:
                cmd.extend([
                    '-filter_complex', audio_filter,
                    '-map', '0:v:0',  # Map video
                    '-map', '[aout]',  # Map filtered audio output
                ])
            else:
                # Single audio track - use default mapping
                pass
            
            # Ensure stereo output
            cmd.extend(['-ac', '2'])
            
            # Choose codec based on GPU availability and user preference
            if use_gpu_encoding:
                cmd.extend([
                    '-c:v', 'h264_nvenc',  # NVIDIA GPU codec
                    '-b:v', f'{target_video_bitrate_k}k',  # Video bitrate
                    '-maxrate', f'{target_video_bitrate_k}k',
                    '-bufsize', f'{target_video_bitrate_k * 2}k',
                    '-preset', 'p4',  # NVENC preset (p1=fastest, p7=slowest/best quality)
                    '-rc', 'vbr',  # Variable bitrate mode
                ])
            else:
                cmd.extend([
                    '-c:v', 'libx264',  # CPU codec
                    '-b:v', f'{target_video_bitrate_k}k',  # Video bitrate
                    '-maxrate', f'{target_video_bitrate_k}k',
                    '-bufsize', f'{target_video_bitrate_k * 2}k',
                    '-preset', 'medium',  # CPU encoding preset
                ])
            
            cmd.extend([
                '-r', str(fps),  # Preserve original FPS
                '-c:a', 'aac',  # Audio codec
                '-b:a', f'{audio_bitrate}k',  # Audio bitrate
                '-movflags', '+faststart',  # Web optimization
                output_path
            ])
            
            # Run ffmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                # If GPU encoding failed, try falling back to CPU
                if use_gpu_encoding:
                    self.root.after(0, lambda: self.progress_label.config(text="GPU encoding failed, retrying with CPU..."))
                    return self.compress_video_cpu_fallback(input_path, output_path, max_size_mb, 
                                                            start_time, end_time, fps, 
                                                            target_duration, target_video_bitrate_k, audio_bitrate,
                                                            audio_track_count)
                else:
                    self.show_error(f"FFmpeg error:\n{stderr}")
                    return
            
            # Check output file size
            output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            
            encoding_method = "GPU (NVENC)" if use_gpu_encoding else "CPU (x264)"
            self.show_success(f"Video compressed successfully!\n\n"
                             f"Encoding method: {encoding_method}\n"
                             f"Output size: {output_size_mb:.2f} MB\n"
                             f"Target size: {max_size_mb} MB\n"
                             f"Saved to: {output_path}")
            
        except Exception as e:
            self.show_error(f"An error occurred:\n{str(e)}")
        
        finally:
            self.root.after(0, self.reset_ui)
    
    def compress_video_cpu_fallback(self, input_path, output_path, max_size_mb, 
                                     start_time, end_time, fps, target_duration, 
                                     target_video_bitrate_k, audio_bitrate, audio_track_count):
        """Fallback to CPU encoding if GPU encoding fails."""
        try:
            ffmpeg_path = get_ffmpeg_path('ffmpeg')
            cmd = [ffmpeg_path, '-y', '-i', input_path]
            
            # Add start time
            if start_time and start_time != "00:00:00":
                cmd.extend(['-ss', start_time])
            
            # Add end time (as duration from start)
            if end_time:
                cmd.extend(['-t', str(target_duration)])
            
            # Build audio filter based on number of tracks
            audio_filter = self.build_audio_filter(audio_track_count)
            if audio_filter:
                cmd.extend([
                    '-filter_complex', audio_filter,
                    '-map', '0:v:0',  # Map video
                    '-map', '[aout]',  # Map filtered audio output
                ])
            
            # Use CPU encoding
            cmd.extend([
                '-ac', '2',
                '-c:v', 'libx264',
                '-b:v', f'{target_video_bitrate_k}k',
                '-maxrate', f'{target_video_bitrate_k}k',
                '-bufsize', f'{target_video_bitrate_k * 2}k',
                '-preset', 'medium',
                '-r', str(fps),
                '-c:a', 'aac',
                '-b:a', f'{audio_bitrate}k',
                '-movflags', '+faststart',
                output_path
            ])
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.show_error(f"CPU fallback encoding also failed:\n{stderr}")
                return
            
            output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            
            self.show_success(f"Video compressed successfully!\n\n"
                             f"Encoding method: CPU (x264) - GPU fallback\n"
                             f"Output size: {output_size_mb:.2f} MB\n"
                             f"Target size: {max_size_mb} MB\n"
                             f"Saved to: {output_path}")
        
        except Exception as e:
            self.show_error(f"Fallback encoding error:\n{str(e)}")
    
    def get_video_duration(self, video_path):
        """Get video duration in seconds using ffprobe."""
        ffprobe_path = get_ffmpeg_path('ffprobe')
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception("Could not read video duration")
        
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    
    def get_video_fps(self, video_path):
        """Get video FPS using ffprobe."""
        ffprobe_path = get_ffmpeg_path('ffprobe')
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception("Could not read video FPS")
        
        data = json.loads(result.stdout)
        fps_str = data['streams'][0]['r_frame_rate']
        
        # Parse fraction (e.g., "30000/1001" or "30/1")
        if '/' in fps_str:
            num, denom = fps_str.split('/')
            fps = float(num) / float(denom)
        else:
            fps = float(fps_str)
        
        return fps
    
    def get_audio_track_count(self, video_path):
        """Get the number of audio tracks using ffprobe."""
        ffprobe_path = get_ffmpeg_path('ffprobe')
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=index',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return 1  # Default to 1 if we can't detect
        
        try:
            data = json.loads(result.stdout)
            audio_streams = data.get('streams', [])
            count = len(audio_streams)
            return max(1, count)  # At least 1
        except:
            return 1
    
    def build_audio_filter(self, audio_track_count):
        """Build the audio filter complex string based on number of tracks."""
        if audio_track_count == 1:
            # Single audio track - just convert to stereo
            return None  # No filter needed, use default mapping
        else:
            # Multiple audio tracks - mix them together
            # Build input labels: [0:a:0][0:a:1][0:a:2]...
            inputs = ''.join([f'[0:a:{i}]' for i in range(audio_track_count)])
            return f'{inputs}amix=inputs={audio_track_count}:duration=first:dropout_transition=2[aout]'
    
    def parse_time(self, time_str):
        """Parse time string to seconds. Accepts HH:MM:SS or seconds."""
        if not time_str or time_str == "00:00:00":
            return 0
        
        # Check if it's just a number (seconds)
        try:
            return float(time_str)
        except ValueError:
            pass
        
        # Parse HH:MM:SS format
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            return float(parts[0])
    
    def show_error(self, message):
        self.root.after(0, lambda: messagebox.showerror("Error", message))
    
    def show_success(self, message):
        self.root.after(0, lambda: messagebox.showinfo("Success", message))
    
    def reset_ui(self):
        self.processing = False
        self.compress_btn.config(state="normal")
        self.progress_label.config(text="")
        self.progress_bar.stop()
    
    def check_gpu_availability(self):
        """Check if NVIDIA GPU with NVENC is available."""
        try:
            ffmpeg_path = get_ffmpeg_path('ffmpeg')
            
            # Check if h264_nvenc encoder is available
            result = subprocess.run(
                [ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'h264_nvenc' in result.stdout:
                # NVENC encoder is available in FFmpeg
                # Try a quick test to see if GPU is actually accessible
                test_result = subprocess.run(
                    [ffmpeg_path, '-f', 'lavfi', '-i', 'nullsrc=s=256x256:d=1', 
                     '-c:v', 'h264_nvenc', '-f', 'null', '-'],
                    capture_output=True,
                    timeout=10
                )
                
                if test_result.returncode == 0:
                    self.gpu_available = True
                    self.gpu_status_label.config(text="✓ GPU available", fg="green")
                    self.use_gpu.set(True)  # Enable by default if available
                    return
            
            # GPU not available
            self.gpu_available = False
            self.gpu_checkbox.config(state="disabled")
            self.gpu_status_label.config(text="✗ No NVIDIA GPU detected", fg="red")
            
        except Exception as e:
            self.gpu_available = False
            self.gpu_checkbox.config(state="disabled")
            self.gpu_status_label.config(text="✗ GPU check failed", fg="red")


def get_ffmpeg_path(executable_name):
    """Get the path to ffmpeg or ffprobe executable.
    
    Checks in order:
    1. Bundled with the executable (for PyInstaller)
    2. In the same directory as the script/executable
    3. In system PATH
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = sys._MEIPASS
        bundled_path = os.path.join(bundle_dir, f'{executable_name}.exe')
        if os.path.exists(bundled_path):
            return bundled_path
    
    # Check in same directory as script/executable
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    local_path = os.path.join(app_dir, f'{executable_name}.exe')
    if os.path.exists(local_path):
        return local_path
    
    # Fall back to system PATH
    return executable_name


def check_ffmpeg():
    """Check if ffmpeg and ffprobe are available."""
    try:
        ffmpeg_path = get_ffmpeg_path('ffmpeg')
        ffprobe_path = get_ffmpeg_path('ffprobe')
        subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True)
        subprocess.run([ffprobe_path, '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    if not check_ffmpeg():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "FFmpeg Not Found",
            "FFmpeg is required but not found in your system.\n\n"
            "Please download FFmpeg from https://ffmpeg.org/download.html\n"
            "and add it to your system PATH."
        )
        return
    
    # Use TkinterDnD if available for drag-and-drop support
    if DRAG_DROP_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = VideoCompressorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
