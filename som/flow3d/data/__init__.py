from dataclasses import asdict, replace

from torch.utils.data import Dataset

from .base_dataset import BaseDataset
from .casual_dataset import CasualDataset, CustomDataConfig, DavisDataConfig
from .iphone_dataset import (
    iPhoneDataConfig,
    iPhoneDataset,
    iPhoneDatasetKeypointView,
    iPhoneDatasetVideoView,
)
from .nvidia_dataset import NvidiaDataset, NvidiaDataConfig, NvidiaDatasetVideoView


def get_train_val_datasets(
    data_cfg: iPhoneDataConfig | DavisDataConfig | CustomDataConfig | NvidiaDataConfig, load_val: bool
) -> tuple[BaseDataset, Dataset | None, Dataset | None, Dataset | None]:
    train_video_view = None
    val_img_dataset = None
    val_kpt_dataset = None
    if isinstance(data_cfg, iPhoneDataConfig):
        train_dataset = iPhoneDataset(**asdict(data_cfg))
        train_video_view = iPhoneDatasetVideoView(train_dataset)
        if load_val:
            val_img_dataset = (
                iPhoneDataset(
                    **asdict(replace(data_cfg, split="val", load_from_cache=True))
                )
                if train_dataset.has_validation
                else None
            )
            val_kpt_dataset = iPhoneDatasetKeypointView(train_dataset)
    elif isinstance(data_cfg, DavisDataConfig) or isinstance(
        data_cfg, CustomDataConfig
    ):
        train_dataset = CasualDataset(**asdict(data_cfg))
    elif isinstance(data_cfg, NvidiaDataConfig):
        train_dataset = NvidiaDataset(**asdict(data_cfg))
        train_video_view = NvidiaDatasetVideoView(train_dataset)
        if load_val:
            val_img_dataset = (
                NvidiaDataset(
                    **asdict(replace(data_cfg, split="val", load_from_cache=True))
                )
                if train_dataset.has_validation
                else None
            )
    else:
        raise ValueError(f"Unknown data config: {data_cfg}")
    return train_dataset, train_video_view, val_img_dataset, val_kpt_dataset
