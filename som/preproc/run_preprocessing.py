import os
import subprocess
import sys
from dataclasses import dataclass
import tyro
import shutil

@dataclass
class PreprocessConfig:
    video_path: str
    output_dir: str
    height: int = 540
    gpu: int = 0
    skip_time: int = 1

def check_ffmpeg():
    if not shutil.which('ffmpeg'):
        print("FFmpeg not found! Please install FFmpeg first:")
        print("1. Download from: https://github.com/BtbN/FFmpeg-Builds/releases")
        print("2. Extract to C:\\ffmpeg")
        print("3. Add C:\\ffmpeg\\bin to system PATH")
        sys.exit(1)

def main(cfg: PreprocessConfig):
    # Check FFmpeg installation
    check_ffmpeg()

    # Create directory structure
    os.makedirs(cfg.output_dir, exist_ok=True)
    images_dir = os.path.join(cfg.output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    print(f"Processing video: {cfg.video_path}")
    print(f"Output directory: {cfg.output_dir}")

    try:
        # Extract frames
        print("Extracting frames...")
        result = subprocess.run([
            "python", "extract_frames.py",
            "--video-paths", cfg.video_path,
            "--output-root", images_dir,
            "--height", str(cfg.height),
            "--skip-time", str(cfg.skip_time)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Error extracting frames:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)

        # Run preprocessing only if frame extraction succeeded
        print("Running preprocessing pipeline...")
        result = subprocess.run([
            "python", "process_custom.py",
            "--img-dirs", images_dir,
            "--gpus", str(cfg.gpu)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Error in preprocessing:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    tyro.cli(main)