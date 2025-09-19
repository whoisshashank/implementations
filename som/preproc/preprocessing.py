import os
import subprocess
import tyro
from dataclasses import dataclass

@dataclass
class PreprocessConfig:
    video_path: str
    output_dir: str
    height: int = 540
    gpu: int = 0
    skip_time: int = 1

def main(cfg: PreprocessConfig):
    # Create directory structure
    os.makedirs(cfg.output_dir, exist_ok=True)
    images_dir = os.path.join(cfg.output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # 1. Extract frames
    print("Extracting frames...")
    subprocess.run([
        "python", "extract_frames.py",
        "--video-paths", cfg.video_path,
        "--output-root", images_dir,
        "--height", str(cfg.height),
        "--skip-time", str(cfg.skip_time)
    ], check=True)

    # 2. Run the main preprocessing
    print("Running preprocessing pipeline...")
    subprocess.run([
        "python", "process_custom.py",
        "--img-dirs", cfg.output_dir,
        "--gpus", str(cfg.gpu)
    ], check=True)

if __name__ == "__main__":
    tyro.cli(main)