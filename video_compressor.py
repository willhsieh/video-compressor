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

# On Windows, ffmpeg/ffprobe are console programs, so every subprocess call
# would flash a console window over the GUI unless CREATE_NO_WINDOW is set.
# The attribute only exists on Windows; 0 is a no-op elsewhere.
SUBPROCESS_FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

# Audio is always re-encoded at this bitrate
AUDIO_BITRATE_KBPS = 128


def calculate_video_bitrate(max_size_mb, duration_seconds, source_bitrate_k=None,
                            audio_bitrate_k=AUDIO_BITRATE_KBPS):
    """Target video bitrate in kbps so video + audio fit within max_size_mb.

    Returns None if the budget can't even hold the audio. Capped at the
    source video bitrate when known — encoding above the source bitrate
    only pads the file without adding quality.
    """
    # 5% safety margin so the output never exceeds the user's limit
    target_size_bits = max_size_mb * 0.95 * 8 * 1024 * 1024
    audio_size_bits = audio_bitrate_k * 1024 * duration_seconds
    video_size_bits = target_size_bits - audio_size_bits

    if video_size_bits <= 0:
        return None

    bitrate_k = int(video_size_bits / duration_seconds / 1024)
    if source_bitrate_k is not None and bitrate_k > source_bitrate_k:
        bitrate_k = source_bitrate_k
    return max(1, bitrate_k)


class VideoCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Compressor")
        self.root.geometry("650x920")
        self.root.resizable(False, False)
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.max_size_mb = tk.StringVar(value="10")
        self.start_time = tk.StringVar(value="00:00:00")
        self.end_time = tk.StringVar(value="")
        self.use_gpu = tk.BooleanVar(value=False)
        self.processing = False
        self.gpu_available = False
        self.video_duration = 0
        self.thumbnails = []
        self.timeline_loaded = False
        
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
        
        # Video preview frame
        self.preview_frame = tk.Frame(self.root)
        self.preview_frame.pack(fill="x", padx=20, pady=10)
        
        self.preview_label_text = tk.Label(self.preview_frame, text="Video Preview:", font=("Arial", 10))
        self.preview_label_text.pack(anchor="w")
        
        self.preview_canvas = tk.Canvas(self.preview_frame, width=320, height=180, bg="#1a1a1a", highlightthickness=1, highlightbackground="#555")
        self.preview_canvas.pack(pady=5)
        
        self.preview_time_label = tk.Label(self.preview_frame, text="", font=("Arial", 9), fg="#888")
        self.preview_time_label.pack()
        
        self.preview_photo = None  # Keep reference to prevent garbage collection
        self.current_video_path = None
        self.scrub_job = None  # For debouncing scrub updates
        
        # Timeline frame for video trimming
        self.timeline_frame = tk.Frame(self.root)
        self.timeline_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(self.timeline_frame, text="Video Timeline (drag handles to trim):", font=("Arial", 10)).pack(anchor="w")
        
        # Timeline canvas
        self.timeline_canvas = tk.Canvas(self.timeline_frame, height=70, bg="#2a2a2a", highlightthickness=1, highlightbackground="#555")
        self.timeline_canvas.pack(fill="x", pady=5)
        
        # Timeline placeholder text
        self.timeline_placeholder = self.timeline_canvas.create_text(
            300, 35, text="Load a video to see timeline", fill="#888", font=("Arial", 10)
        )
        
        # Timeline variables
        self.timeline_width = 0
        self.handle_left_x = 0
        self.handle_right_x = 0
        self.dragging_handle = None
        self.handle_width = 12
        
        # Bind canvas events
        self.timeline_canvas.bind("<Configure>", self.on_timeline_configure)
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self.on_timeline_release)
        
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
        
        # Button frame for compress and reset buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        # Compress button
        self.compress_btn = tk.Button(button_frame, text="Compress Video", command=self.start_compression,
                                       bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                                       padx=20, pady=10)
        self.compress_btn.pack(side="left", padx=5)
        
        # Reset button (initially hidden)
        self.reset_btn = tk.Button(button_frame, text="Reset", command=self.reset_form,
                                    bg="#2196F3", fg="white", font=("Arial", 12, "bold"),
                                    padx=20, pady=10)
        # Don't pack initially - will be shown after compression completes
        
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
                # Load video timeline
                self.current_video_path = file_path
                self.load_video_timeline(file_path)
                # Show reset button
                self.reset_btn.pack(side="left", padx=5)
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
            # Load video timeline
            self.current_video_path = filename
            self.load_video_timeline(filename)
            # Show reset button
            self.reset_btn.pack(side="left", padx=5)
    
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
            
            # Calculate target bitrate from the size budget, capped at the
            # source bitrate so short clips trimmed from large files aren't
            # padded up to the size limit
            audio_bitrate = AUDIO_BITRATE_KBPS
            source_bitrate_k = self.get_video_bitrate(input_path)
            target_video_bitrate_k = calculate_video_bitrate(
                max_size_mb, target_duration, source_bitrate_k, audio_bitrate)

            if target_video_bitrate_k is None:
                self.show_error("Target file size is too small for the specified duration.")
                return
            
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
                universal_newlines=True,
                creationflags=SUBPROCESS_FLAGS
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
                universal_newlines=True,
                creationflags=SUBPROCESS_FLAGS
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
        
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
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
        
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
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
    
    def get_video_bitrate(self, video_path):
        """Get the source video bitrate in kbps using ffprobe, or None if unknown.

        Prefers the video stream's own bitrate; some containers (e.g. mkv)
        don't store per-stream bitrates, so fall back to the container-level
        bitrate. That includes audio so it reads slightly high, but the cap
        only needs to be the right order of magnitude.
        """
        ffprobe_path = get_ffmpeg_path('ffprobe')
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=bit_rate:format=bit_rate',
            '-of', 'json',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)

        if result.returncode != 0:
            return None

        try:
            data = json.loads(result.stdout)
        except ValueError:
            return None

        streams = data.get('streams') or [{}]
        for rate in (streams[0].get('bit_rate'), data.get('format', {}).get('bit_rate')):
            try:
                return max(1, int(int(rate) / 1024))
            except (TypeError, ValueError):
                continue
        return None

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
        
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=SUBPROCESS_FLAGS)
        
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
    
    def reset_form(self):
        """Reset the form to compress another video."""
        self.input_file.set("")
        self.output_file.set("")
        self.start_time.set("00:00:00")
        self.end_time.set("")
        self.progress_label.config(text="")
        # Hide reset button until next compression
        self.reset_btn.pack_forget()
        # Reset timeline
        self.timeline_loaded = False
        self.video_duration = 0
        self.thumbnails = []
        self.current_video_path = None
        self.timeline_canvas.delete("all")
        self.timeline_placeholder = self.timeline_canvas.create_text(
            self.timeline_width // 2 if self.timeline_width > 0 else 300, 35,
            text="Load a video to see timeline", fill="#888", font=("Arial", 10)
        )
        # Reset preview
        self.preview_canvas.delete("all")
        self.preview_time_label.config(text="")
        self.preview_photo = None
    
    def on_timeline_configure(self, event):
        """Handle timeline canvas resize."""
        self.timeline_width = event.width
        if self.timeline_loaded:
            self.draw_timeline()
        else:
            # Update placeholder position
            self.timeline_canvas.coords(self.timeline_placeholder, event.width // 2, 35)
    
    def on_timeline_click(self, event):
        """Handle click on timeline to start dragging a handle."""
        if not self.timeline_loaded:
            return
        
        x = event.x
        # Check if clicking on left handle
        if abs(x - self.handle_left_x) < self.handle_width:
            self.dragging_handle = "left"
        # Check if clicking on right handle
        elif abs(x - self.handle_right_x) < self.handle_width:
            self.dragging_handle = "right"
        else:
            self.dragging_handle = None
    
    def on_timeline_drag(self, event):
        """Handle dragging of timeline handles."""
        if not self.timeline_loaded or not self.dragging_handle:
            return
        
        x = max(self.handle_width, min(event.x, self.timeline_width - self.handle_width))
        
        if self.dragging_handle == "left":
            # Don't let left handle go past right handle
            if x < self.handle_right_x - self.handle_width * 2:
                self.handle_left_x = x
        elif self.dragging_handle == "right":
            # Don't let right handle go past left handle
            if x > self.handle_left_x + self.handle_width * 2:
                self.handle_right_x = x
        
        self.draw_timeline()
        self.update_time_from_handles()
        
        # Scrub video preview to current handle position
        self.scrub_to_handle_position()
    
    def on_timeline_release(self, event):
        """Handle release of timeline handle."""
        self.dragging_handle = None
    
    def scrub_to_handle_position(self):
        """Update video preview to show frame at current handle position."""
        if not self.current_video_path or not self.dragging_handle:
            return
        
        # Calculate timestamp based on which handle is being dragged
        usable_width = self.timeline_width - self.handle_width * 2
        if usable_width <= 0:
            return
        
        if self.dragging_handle == "left":
            ratio = (self.handle_left_x - self.handle_width) / usable_width
        else:
            ratio = (self.handle_right_x - self.handle_width) / usable_width
        
        timestamp = max(0, min(ratio * self.video_duration, self.video_duration))
        
        # Debounce: cancel previous job if still pending
        if self.scrub_job:
            self.root.after_cancel(self.scrub_job)
        
        # Schedule frame extraction with small delay for smoother dragging
        self.scrub_job = self.root.after(50, lambda: self._extract_and_show_frame(timestamp))
    
    def _extract_and_show_frame(self, timestamp):
        """Extract a frame at the given timestamp and display it."""
        if not self.current_video_path:
            return
        
        # Run in background thread to avoid UI lag
        thread = threading.Thread(target=self._do_frame_extraction, args=(timestamp,))
        thread.daemon = True
        thread.start()
    
    def _do_frame_extraction(self, timestamp):
        """Actually extract the frame (runs in background thread)."""
        try:
            import tempfile
            
            # Create temp file for the frame
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            ffmpeg_path = get_ffmpeg_path('ffmpeg')
            cmd = [
                ffmpeg_path, '-y',
                '-ss', str(timestamp),
                '-i', self.current_video_path,
                '-vframes', '1',
                '-vf', 'scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2',
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=5, creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode == 0 and os.path.exists(temp_path):
                # Update UI on main thread
                self.root.after(0, lambda: self._display_preview_frame(temp_path, timestamp))
            else:
                # Clean up on failure
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error extracting frame: {e}")
    
    def _display_preview_frame(self, frame_path, timestamp):
        """Display the extracted frame in the preview canvas."""
        try:
            from PIL import Image, ImageTk
            
            if os.path.exists(frame_path):
                img = Image.open(frame_path)
                self.preview_photo = ImageTk.PhotoImage(img)
                
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(160, 90, image=self.preview_photo, anchor="center")
                
                # Update time label
                self.preview_time_label.config(text=f"Time: {self.format_time(timestamp)}")
                
                # Clean up temp file
                try:
                    os.unlink(frame_path)
                except:
                    pass
        except ImportError:
            # PIL not available
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(160, 90, text=f"Frame at {self.format_time(timestamp)}", fill="#888")
            self.preview_time_label.config(text=f"Time: {self.format_time(timestamp)} (Install Pillow for preview)")
        except Exception as e:
            print(f"Error displaying frame: {e}")
    
    def update_time_from_handles(self):
        """Update start/end time fields based on handle positions."""
        if not self.timeline_loaded or self.video_duration <= 0:
            return
        
        usable_width = self.timeline_width - self.handle_width * 2
        
        # Calculate time from handle positions
        left_ratio = (self.handle_left_x - self.handle_width) / usable_width
        right_ratio = (self.handle_right_x - self.handle_width) / usable_width
        
        start_seconds = max(0, left_ratio * self.video_duration)
        end_seconds = min(self.video_duration, right_ratio * self.video_duration)
        
        # Format as HH:MM:SS
        self.start_time.set(self.format_time(start_seconds))
        self.end_time.set(self.format_time(end_seconds))
    
    def format_time(self, seconds):
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def load_video_timeline(self, video_path):
        """Load video and generate timeline thumbnails."""
        try:
            # Get video duration
            self.video_duration = self.get_video_duration(video_path)
            
            # Generate thumbnails in background thread
            thread = threading.Thread(target=self._generate_thumbnails, args=(video_path,))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Error loading timeline: {e}")
    
    def _generate_thumbnails(self, video_path):
        """Generate thumbnail images from video (runs in background thread)."""
        try:
            import tempfile
            
            # Create temp directory for thumbnails
            temp_dir = tempfile.mkdtemp()
            
            # Generate ~10 thumbnails evenly spaced
            num_thumbnails = 10
            interval = self.video_duration / num_thumbnails
            
            ffmpeg_path = get_ffmpeg_path('ffmpeg')
            thumbnails = []
            
            for i in range(num_thumbnails):
                timestamp = i * interval
                output_path = os.path.join(temp_dir, f"thumb_{i}.png")
                
                cmd = [
                    ffmpeg_path, '-y',
                    '-ss', str(timestamp),
                    '-i', video_path,
                    '-vframes', '1',
                    '-vf', 'scale=60:40',
                    output_path
                ]
                
                subprocess.run(cmd, capture_output=True, timeout=10, creationflags=SUBPROCESS_FLAGS)
                
                if os.path.exists(output_path):
                    thumbnails.append(output_path)
            
            self.thumbnails = thumbnails
            self.timeline_loaded = True
            
            # Initialize handle positions
            self.handle_left_x = self.handle_width
            self.handle_right_x = self.timeline_width - self.handle_width if self.timeline_width > 0 else 580
            
            # Update UI on main thread
            self.root.after(0, self.draw_timeline)
            
        except Exception as e:
            print(f"Error generating thumbnails: {e}")
    
    def draw_timeline(self):
        """Draw the timeline with thumbnails and handles."""
        if not self.timeline_loaded:
            return
        
        self.timeline_canvas.delete("all")
        
        canvas_width = self.timeline_width if self.timeline_width > 0 else 580
        canvas_height = 70
        
        # Draw thumbnails
        if self.thumbnails:
            try:
                from PIL import Image, ImageTk
                
                thumb_width = (canvas_width - self.handle_width * 2) // len(self.thumbnails)
                
                # Store photo references to prevent garbage collection
                if not hasattr(self, 'photo_refs'):
                    self.photo_refs = []
                self.photo_refs.clear()
                
                for i, thumb_path in enumerate(self.thumbnails):
                    if os.path.exists(thumb_path):
                        img = Image.open(thumb_path)
                        img = img.resize((thumb_width, 50), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        self.photo_refs.append(photo)
                        
                        x = self.handle_width + i * thumb_width
                        self.timeline_canvas.create_image(x, 10, image=photo, anchor="nw")
            except ImportError:
                # PIL not available, draw placeholder rectangles
                thumb_width = (canvas_width - self.handle_width * 2) // 10
                for i in range(10):
                    x = self.handle_width + i * thumb_width
                    color = "#444" if i % 2 == 0 else "#555"
                    self.timeline_canvas.create_rectangle(x, 10, x + thumb_width, 60, fill=color, outline="")
        
        # Draw selected region overlay (dimmed outside selection)
        self.timeline_canvas.create_rectangle(
            0, 0, self.handle_left_x, canvas_height,
            fill="#000", stipple="gray50", outline=""
        )
        self.timeline_canvas.create_rectangle(
            self.handle_right_x, 0, canvas_width, canvas_height,
            fill="#000", stipple="gray50", outline=""
        )
        
        # Draw selection border (yellow like QuickTime)
        self.timeline_canvas.create_rectangle(
            self.handle_left_x, 2, self.handle_right_x, canvas_height - 2,
            outline="#FFD700", width=3
        )
        
        # Draw left handle
        self.timeline_canvas.create_rectangle(
            self.handle_left_x - self.handle_width // 2, 0,
            self.handle_left_x + self.handle_width // 2, canvas_height,
            fill="#FFD700", outline="#FFA500"
        )
        self.timeline_canvas.create_line(
            self.handle_left_x, 15, self.handle_left_x, canvas_height - 15,
            fill="#000", width=2
        )
        
        # Draw right handle
        self.timeline_canvas.create_rectangle(
            self.handle_right_x - self.handle_width // 2, 0,
            self.handle_right_x + self.handle_width // 2, canvas_height,
            fill="#FFD700", outline="#FFA500"
        )
        self.timeline_canvas.create_line(
            self.handle_right_x, 15, self.handle_right_x, canvas_height - 15,
            fill="#000", width=2
        )
    
    def check_gpu_availability(self):
        """Check if NVIDIA GPU with NVENC is available."""
        try:
            ffmpeg_path = get_ffmpeg_path('ffmpeg')
            
            # Check if h264_nvenc encoder is available
            result = subprocess.run(
                [ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            if 'h264_nvenc' in result.stdout:
                # NVENC encoder is available in FFmpeg
                # Try a quick test to see if GPU is actually accessible
                test_result = subprocess.run(
                    [ffmpeg_path, '-f', 'lavfi', '-i', 'nullsrc=s=256x256:d=1',
                     '-c:v', 'h264_nvenc', '-f', 'null', '-'],
                    capture_output=True,
                    timeout=10,
                    creationflags=SUBPROCESS_FLAGS
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
        subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True, creationflags=SUBPROCESS_FLAGS)
        subprocess.run([ffprobe_path, '-version'], capture_output=True, check=True, creationflags=SUBPROCESS_FLAGS)
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
