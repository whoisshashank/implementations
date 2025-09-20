import os
import sys
import subprocess
import shutil
from dataclasses import dataclass
import tyro

@dataclass
class PreprocessConfig:
    video_path: str
    output_dir: str
    height: int = 540
    gpu: int = 0
    skip_time: int = 1

def get_ffmpeg_path():
    return r"C:\ffmpeg\bin\ffmpeg.exe"

def check_ffmpeg():
    ffmpeg_path = get_ffmpeg_path()
    if not os.path.exists(ffmpeg_path):
        print("FFmpeg not found! Please install FFmpeg first:")
        print("1. Download from: https://github.com/BtbN/FFmpeg-Builds/releases")
        print("2. Extract to C:\\ffmpeg")
        print("3. Add C:\\ffmpeg\\bin to system PATH")
        sys.exit(1)
    return ffmpeg_path

def main(cfg: PreprocessConfig):
    try:
        # Check FFmpeg installation and get path
        ffmpeg_path = check_ffmpeg()

        # Create directory structure
        os.makedirs(cfg.output_dir, exist_ok=True)
        images_dir = os.path.join(cfg.output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        print(f"Processing video: {cfg.video_path}")
        print(f"Output directory: {cfg.output_dir}")
        print(f"Using FFmpeg from: {ffmpeg_path}")

        # Set FFmpeg path in environment
        os.environ["FFMPEG_BINARY"] = ffmpeg_path
        
        # Extract frames
        print("Extracting frames...")
        result = subprocess.run([
            "python", "extract_frames.py",
            "--video-paths", cfg.video_path,
            "--output-root", images_dir,
            "--height", str(cfg.height),
            "--skip-time", str(cfg.skip_time)
        ], capture_output=True, text=True, env=dict(os.environ))
        
        if result.returncode != 0:
            print("Error extracting frames:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"Error running extraction command: {e}", file=sys.stderr)
        print(f"Command output: {e.output}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: Required file or directory not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        print("Cleanup and finalizing processing...")
        print("Processing completed.")

if __name__ == "__main__":
    tyro.cli(main)