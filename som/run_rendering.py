import os
import time
from dataclasses import dataclass

import torch
import tyro
from loguru import logger as guru

from flow3d.renderer import Renderer

import yaml

torch.set_float32_matmul_precision("high")


@dataclass
class RenderConfig:
    work_dir: str
    port: int = 8890


def main(cfg: RenderConfig):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ckpt_path = f"{cfg.work_dir}/checkpoints/last.ckpt"
    assert os.path.exists(ckpt_path)

    train_cfg_path = f"{cfg.work_dir}/cfg.yaml"
    with open(train_cfg_path, "r") as file:
        train_cfg = yaml.safe_load(file)

    renderer = Renderer.init_from_checkpoint(
        ckpt_path,
        device,
        use_2dgs=train_cfg["use_2dgs"],
        work_dir=cfg.work_dir,
        port=cfg.port,
    )

    guru.info(f"Starting rendering from {renderer.global_step=}")
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    main(tyro.cli(RenderConfig))
