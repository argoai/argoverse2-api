"""Unit tests for Pytorch Detection Dataset module."""

from pathlib import Path
from typing import Final

from av2.torch.dataloaders.detection import DetectionDataloader

TEST_DATA_DIR: Final = Path(__file__).parent.parent.parent.resolve() / "test_data" / "sensor_dataset_logs"


def test_build_data_loader() -> None:
    """Test building the Pytorch Detection DataLoader."""
    root_dir = TEST_DATA_DIR
    dataset_name = "av2"
    split_name = "val"
    data_loader = DetectionDataloader(root_dir=root_dir, dataset_name=dataset_name, split_name=split_name)
    for datum in data_loader:
        assert datum is not None
