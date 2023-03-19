"""Example of rust-backed, torch dataloader."""

import logging
from pathlib import Path
from typing import Final

from kornia.geometry.linalg import transform_points
from tqdm import tqdm

from av2.torch.data_loaders.detection import DetectionDataLoader
from av2.torch.structures.cuboids import CuboidMode

logger = logging.getLogger(__name__)

HOME_DIR: Final = Path.home()


def main(
    root_dir: Path = HOME_DIR / "data" / "datasets",
    dataset_name: str = "av2",
    split_name: str = "val",
    num_accumulated_sweeps: int = 1,
    max_iterations: int = 1000,
) -> None:
    """Iterate over the detection data-loader.

    Dataset should live at ~/data/datasets/{dataset_name}/{split_name}.

    Args:
        root_dir: Root directory to the datasets.
        dataset_name: Name of the dataset (e.g., "av2").
        split_name: Name of the split (e.g., "val").
        num_accumulated_sweeps: Number of sweeps to accumulate.
        max_iterations: Maximum number of iterations for the data-loader example.
    """
    logger.info("Starting detection data-loader example ...")
    data_loader = DetectionDataLoader(root_dir, dataset_name, split_name, num_accumulated_sweeps=num_accumulated_sweeps)
    for i, sweep in enumerate(tqdm(data_loader)):
        # 4x4 matrix representing the SE(3) transformation to city from ego-vehicle coordinates.
        city_SE3_ego_4x4 = sweep.city_SE3_ego.matrix()

        # Lidar (x,y,z) in meters and intensity (i).
        lidar_xyzi_ego = sweep.lidar.as_tensor()

        # Transform the points to city coordinates.
        lidar_xyz_city = transform_points(city_SE3_ego_4x4, lidar_xyzi_ego[:, :3])

        # Cuboids might not be available (e.g., using the "test" split).
        if sweep.cuboids is not None:
            # Annotations in (x,y,z,l,w,h,yaw) format.
            cuboids = sweep.cuboids.as_tensor()

            # Annotations in (x,y,z,l,w,h,qw,qx,qy,qz) format.
            # Full 3-DOF rotation.
            cuboids_qwxyz = sweep.cuboids.as_tensor(cuboid_mode=CuboidMode.XYZLWH_QWXYZ)

        if i >= max_iterations:
            logger.info(f"Reached max iterations of {max_iterations}!")
            break

    logger.info("Example complete!")


if __name__ == "__main__":
    main()
