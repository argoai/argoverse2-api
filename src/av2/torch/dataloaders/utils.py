"""Pytorch dataloader utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from functools import cached_property
from typing import Final, List, Optional, Tuple

import pandas as pd
import torch
from torch import Tensor

import av2._r as rust
from av2.geometry.geometry import quat_to_mat
from av2.utils.typing import NDArrayFloat

DEFAULT_ANNOTATIONS_TENSOR_FIELDS: Final = (
    "tx_m",
    "ty_m",
    "tz_m",
    "length_m",
    "width_m",
    "height_m",
    "qw",
    "qx",
    "qy",
    "qz",
)
DEFAULT_LIDAR_TENSOR_FIELDS: Final = ("x", "y", "z")
QUAT_WXYZ_FIELDS: Final = ("qw", "qx", "qy", "qz")
TRANSLATION_FIELDS: Final = ("tx_m", "ty_m", "tz_m")


@unique
class OrientationMode(str, Enum):
    """Orientation (pose) modes for the ground truth annotations."""

    QUATERNION_WXYZ = "QUATERNION_WXYZ"
    YAW = "YAW"


@dataclass(frozen=True)
class Annotations:
    """Dataclass for ground truth annotations.

    Args:
        dataframe: Dataframe containing the annotations and their attributes.
    """

    dataframe: pd.DataFrame

    @property
    def category_names(self) -> List[str]:
        """Return the category names."""
        category_names: List[str] = self.dataframe["category"].to_list()
        return category_names

    @property
    def track_uuids(self) -> List[str]:
        """Return the unique track identifiers."""
        category_names: List[str] = self.dataframe["track_uuid"].to_list()
        return category_names

    def as_tensor(
        self,
        field_ordering: Tuple[str, ...] = DEFAULT_ANNOTATIONS_TENSOR_FIELDS,
        dtype: torch.dtype = torch.float32,
    ) -> Tensor:
        """Return the annotations as a tensor.

        Args:
            field_ordering: Feature ordering for the tensor.
            dtype: Target datatype for casting.

        Returns:
            (N,K) tensor where N is the number of annotations and K
                is the number of annotation fields.
        """
        dataframe_npy = self.dataframe.loc[:, list(field_ordering)].to_numpy()
        return torch.as_tensor(dataframe_npy, dtype=dtype)


@dataclass(frozen=True)
class Lidar:
    """Dataclass for lidar sweeps.

    Args:
        dataframe: Dataframe containing the lidar and its attributes.
    """

    dataframe: pd.DataFrame

    def as_tensor(
        self, field_ordering: Tuple[str, ...] = DEFAULT_LIDAR_TENSOR_FIELDS, dtype: torch.dtype = torch.float32
    ) -> Tensor:
        """Return the lidar sweep as a tensor.

        Args:
            field_ordering: Feature ordering for the tensor.
            dtype: Target datatype for casting.

        Returns:
            (N,K) tensor where N is the number of lidar points and K
                is the number of features.
        """
        dataframe_npy = self.dataframe.loc[:, list(field_ordering)].to_numpy()
        return torch.as_tensor(dataframe_npy, dtype=dtype)


@dataclass(frozen=True)
class Sweep:
    """Stores the annotations and lidar for one sweep.

    Args:
        annotations: Annotations parameterization.
        city_pose: Rigid transformation describing the city pose of the ego-vehicle.
        lidar: Lidar parameters.
        sweep_uuid: Log id and nanosecond timestamp (unique identifier).
    """

    annotations: Optional[Annotations]
    city_pose: Pose
    lidar: Lidar
    sweep_uuid: Tuple[str, int]

    @classmethod
    def from_rust(cls, sweep: rust.Sweep) -> Sweep:
        """Build a sweep from the Rust backend."""
        annotations = Annotations(dataframe=sweep.annotations.to_pandas())
        city_pose = Pose(dataframe=sweep.city_pose.to_pandas())
        lidar = Lidar(dataframe=sweep.lidar.to_pandas())
        return cls(annotations=annotations, city_pose=city_pose, lidar=lidar, sweep_uuid=sweep.sweep_uuid)


@dataclass(frozen=True)
class Pose:
    """Pose class for rigid transformations."""

    dataframe: pd.DataFrame

    @cached_property
    def Rt(self) -> Tuple[Tensor, Tensor]:
        """Return a (3,3) rotation matrix and a (3,) translation vector."""
        quat_wxyz: NDArrayFloat = self.dataframe[QUAT_WXYZ_FIELDS].to_numpy()
        translation: NDArrayFloat = self.dataframe[TRANSLATION_FIELDS].to_numpy()

        rotation = quat_to_mat(quat_wxyz)
        return torch.as_tensor(rotation, dtype=torch.float32), torch.as_tensor(translation, dtype=torch.float32)
