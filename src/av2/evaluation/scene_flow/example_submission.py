"""An example showing how to output flow predictions in the format required for submission."""

import argparse
from pathlib import Path

import numpy as np
from kornia.geometry.linalg import transform_points
from rich.progress import track

from av2.evaluation.scene_flow.utils import get_eval_point_mask, get_eval_subset, write_output_file
from av2.torch.data_loaders.scene_flow import SceneFlowDataloader

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="example_submission",
        description="example program demonstrating how to use the API "
        "to output the correct files for submission to the leaderboard",
    )
    parser.add_argument("output_root", type=str, help="path/to/output/")
    parser.add_argument("data_root", type=str, help="root/path/to/data")
    parser.add_argument(
        "--name",
        type=str,
        default="av2",
        help="the data should be located in <data_root>/<name>/sensor/<split> (default: av2)",
    )

    args = parser.parse_args()

    dl = SceneFlowDataloader(args.data_root, args.name, "test")

    output_root = Path(args.output_root)
    output_root.mkdir(exist_ok=True)

    eval_inds = get_eval_subset(dl)
    for i in track(eval_inds, description="Generating outputs..."):
        sweep_0, sweep_1, ego_motion, flow = dl[i]
        mask = get_eval_point_mask(sweep_0.sweep_uuid)

        pc1 = sweep_0.lidar.as_tensor()[mask, :3]
        pc1_rigid = transform_points(ego_motion.matrix(), pc1[None])[0]
        rigid_flow = (pc1_rigid - pc1).detach().numpy()
        dynamic = np.zeros(len(rigid_flow), dtype=bool)

        write_output_file(rigid_flow, dynamic, sweep_0.sweep_uuid, output_root)