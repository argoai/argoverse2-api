//! # augmentations
//!
//! Geometric augmentations.

use std::ops::MulAssign;

use itertools::Itertools;
use ndarray::{concatenate, s, Axis};
use polars::{
    lazy::dsl::{col, cols, GetOutput},
    prelude::{DataFrame, DataType, Float32Type, IntoLazy},
    series::Series,
};
use rand_distr::{Bernoulli, Distribution, Uniform};

use crate::{
    io::ndarray_from_frame,
    share::{data_frame_to_ndarray_f32, ndarray_to_expr_vec},
};

use super::{
    polytope::{compute_interior_points_mask, cuboids_to_polygons},
    so3::{
        reflect_orientation_x, reflect_orientation_y, reflect_translation_x, reflect_translation_y,
    },
};

/// Sample a scene reflection.
/// This reflects both a point cloud and cuboids across the x-axis.
pub fn sample_scene_reflection_x(
    lidar: DataFrame,
    cuboids: DataFrame,
    p: f64,
) -> (DataFrame, DataFrame) {
    let distribution = Bernoulli::new(p).unwrap();
    let is_augmented = distribution.sample(&mut rand::thread_rng());
    if is_augmented {
        let augmented_lidar = lidar
            .lazy()
            .with_column(col("y").map(
                move |x| {
                    Ok(Some(
                        x.f32()
                            .unwrap()
                            .into_no_null_iter()
                            .map(|y| -y)
                            .collect::<Series>(),
                    ))
                },
                GetOutput::from_type(DataType::Float32),
            ))
            .collect()
            .unwrap();

        let translation_column_names = vec!["tx_m", "ty_m", "tz_m"];
        let txyz_m = data_frame_to_ndarray_f32(cuboids.clone(), translation_column_names.clone());
        let augmentation_translation = reflect_translation_x(&txyz_m.view());

        let orientation_column_names = vec!["qw", "qx", "qy", "qz"];
        let quat_wxyz =
            data_frame_to_ndarray_f32(cuboids.clone(), orientation_column_names.clone());
        let augmented_orientation = reflect_orientation_x(&quat_wxyz.view());
        let augmented_poses =
            concatenate![Axis(1), augmentation_translation, augmented_orientation];

        let column_names = translation_column_names
            .into_iter()
            .chain(orientation_column_names)
            .collect_vec();
        let series_vec = ndarray_to_expr_vec(augmented_poses, column_names);
        let augmented_cuboids = cuboids.lazy().with_columns(series_vec).collect().unwrap();
        (augmented_lidar, augmented_cuboids)
    } else {
        (lidar, cuboids)
    }
}

/// Sample a scene reflection.
/// This reflects both a point cloud and cuboids across the y-axis.
pub fn sample_scene_reflection_y(
    lidar: DataFrame,
    cuboids: DataFrame,
    p: f64,
) -> (DataFrame, DataFrame) {
    let distribution: Bernoulli = Bernoulli::new(p).unwrap();
    let is_augmented = distribution.sample(&mut rand::thread_rng());
    if is_augmented {
        let augmented_lidar = lidar
            .lazy()
            .with_column(col("x").map(
                move |x| {
                    Ok(Some(
                        x.f32()
                            .unwrap()
                            .into_no_null_iter()
                            .map(|x| -x)
                            .collect::<Series>(),
                    ))
                },
                GetOutput::from_type(DataType::Float32),
            ))
            .collect()
            .unwrap();

        let translation_column_names = vec!["tx_m", "ty_m", "tz_m"];
        let txyz_m = data_frame_to_ndarray_f32(cuboids.clone(), translation_column_names.clone());
        let augmentation_translation = reflect_translation_y(&txyz_m.view());

        let orientation_column_names = vec!["qw", "qx", "qy", "qz"];
        let quat_wxyz =
            data_frame_to_ndarray_f32(cuboids.clone(), orientation_column_names.clone());
        let augmented_orientation = reflect_orientation_y(&quat_wxyz.view());
        let augmented_poses =
            concatenate![Axis(1), augmentation_translation, augmented_orientation];

        let column_names = translation_column_names
            .into_iter()
            .chain(orientation_column_names)
            .collect_vec();
        let series_vec = ndarray_to_expr_vec(augmented_poses, column_names);
        let augmented_cuboids = cuboids.lazy().with_columns(series_vec).collect().unwrap();
        (augmented_lidar, augmented_cuboids)
    } else {
        (lidar, cuboids)
    }
}

/// Sample a scene with random object scaling.
pub fn sample_random_object_scale(
    lidar: DataFrame,
    cuboids: DataFrame,
    low_inclusive: f64,
    high_inclusive: f64,
) -> (DataFrame, DataFrame) {
    let mut points = ndarray_from_frame(&lidar, cols(["x", "y", "z"]));
    let distribution = Uniform::new_inclusive(low_inclusive, high_inclusive);

    let mut cuboids_ndarray = cuboids.to_ndarray::<Float32Type>().unwrap();
    let cuboid_vertices = cuboids_to_polygons(&cuboids_ndarray.view());
    let interior_points_mask =
        compute_interior_points_mask(&points.view(), &cuboid_vertices.view());
    for m in interior_points_mask.outer_iter() {
        let scale_factor = distribution.sample(&mut rand::thread_rng()) as f32;
        let indices = m
            .iter()
            .enumerate()
            .filter_map(|(i, x)| match *x {
                true => Some(i),
                _ => None,
            })
            .collect_vec();
        let mut interior_points = points.select(Axis(0), &indices);
        interior_points *= scale_factor;

        for index in indices {
            points
                .slice_mut(s![index, ..])
                .assign(&interior_points.slice(s![index, ..]));
        }

        cuboids_ndarray
            .slice_mut(s![.., 3..6])
            .par_mapv_inplace(|x| x * scale_factor);
    }

    let lidar_column_names = vec!["x", "y", "z"];
    let series_vec = ndarray_to_expr_vec(points, lidar_column_names);
    let augmented_lidar = lidar.lazy().with_columns(series_vec).collect().unwrap();

    let cuboid_column_names = vec!["length_m", "width_m", "height_m"];
    let series_vec = ndarray_to_expr_vec(cuboids_ndarray, cuboid_column_names);
    let augmented_cuboids = cuboids.lazy().with_columns(series_vec).collect().unwrap();
    (augmented_lidar, augmented_cuboids)
}
