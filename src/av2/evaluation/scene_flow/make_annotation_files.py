"""Utility program for producing minimnal annotation files used for evaluation on the val and test splits."""

import argparse
from pathlib import Path
from typing import Final, Tuple

import click
import numpy as np
import pandas as pd
from av2.evaluation.scene_flow.utils import (get_eval_point_mask,
                                             get_eval_subset)
from av2.torch.data_loaders.scene_flow import SceneFlowDataloader
from av2.utils.typing import NDArrayBool, NDArrayFloat, NDArrayInt
from rich.progress import track

CLOSE_DISTANCE_THRESHOLD: Final = 35


def write_annotation(
    category_indices: NDArrayInt,
    is_close: NDArrayBool,
    is_dynamic: NDArrayBool,
    is_valid: NDArrayBool,
    flow: NDArrayFloat,
    sweep_uuid: Tuple[str, int],
    output_dir: Path,
) -> None:
    """Write an annotation file.

    Args:
        category_indices: Category label indices.
        is_close: Close (inside 70m box) labels.
        is_dynamic: Dynamic labels.
        is_valid: Valid flow labels.
        flow: Flow labels.
        sweep_uuid: Log and timestamp of the sweep.
        output_dir: Top level directory to store the output in.
    """
    output = pd.DataFrame(
        {
            "category_indices": category_indices.astype(np.uint8),
            "is_close": is_close.astype(bool),
            "is_dynamic": is_dynamic.astype(bool),
            "is_valid": is_valid.astype(bool),
            "flow_tx_m": flow[:, 0].astype(np.float16),
            "flow_ty_m": flow[:, 1].astype(np.float16),
            "flow_tz_m": flow[:, 2].astype(np.float16),
        }
    )

    log_id, timestamp_ns = sweep_uuid

    output_subdir = output_dir / log_id
    output_subdir.mkdir(exist_ok=True)
    output_file = output_subdir / f"{timestamp_ns}.feather"
    output.to_feather(output_file)


@click.command()
@click.argument("output_dir", type=str)
@click.argument("data_dir", type=str)
@click.option(
    "--name",
    type=str,
    help="the data should be located in <data_dir>/<name>/sensor/<split>",
    default="av2",
)
@click.option(
    "--split",
    help="the data should be located in <data_dir>/<name>/sensor/<split>",
    default="val",
    type=click.Choice(["test", "val"]),
)
def make_annotation_files(output_dir: str, data_dir: str, name: str, split: str):
    """Create annotation files for running the evaluation."""
    data_loader = SceneFlowDataloader(data_dir, name, "val")

    output_root = Path(output_dir)
    output_root.mkdir(exist_ok=True)

    eval_inds = get_eval_subset(data_loader)
    for i in track(eval_inds):
        datum = data_loader[i]
        if datum[3] is None:
            raise ValueError("Missing flow annotations!")

        mask = get_eval_point_mask(datum[0].sweep_uuid, split=split)

        flow = datum[3].flow[mask].numpy().astype(np.float16)
        is_valid = datum[3].is_valid[mask].numpy().astype(bool)
        category_indices = datum[3].category_indices[mask].numpy().astype(np.uint8)
        is_dynamic = datum[3].is_dynamic[mask].numpy().astype(bool)

        pc = datum[0].lidar.as_tensor()[mask, :3].numpy()
        is_close = np.logical_and.reduce(
            np.abs(pc[:, :2]) <= CLOSE_DISTANCE_THRESHOLD, axis=1
        ).astype(bool)

        write_annotation(
            category_indices,
            is_close,
            is_dynamic,
            is_valid,
            flow,
            datum[0].sweep_uuid,
            output_root,
        )


if __name__ == "__main__":
    make_annotation_files()
