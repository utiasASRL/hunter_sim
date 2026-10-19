"""Generate deterministic, compact Gazebo worlds for lunar-terrain experiments.

The generator intentionally writes ordinary OBJ/MTL and SDF files rather than
depending on a mesh-processing framework.  All stochastic choices use the
single NumPy generator seeded by ``--seed``.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

try:
    import rasterio
except ImportError as exc:  # pragma: no cover - exercised in minimal installs
    raise SystemExit(
        "world_generator.py requires rasterio and numpy. "
        "Install the generator requirements first."
    ) from exc

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "world_generator.py requires PyYAML for configuration files."
    ) from exc


CRATER_DIAMETERS_M = np.array(
    [10, 12.6, 15.8, 20, 25.1, 31.6, 39.8, 50.1, 63.1, 79.4,
     100, 126, 158, 200, 251, 316, 398, 501, 631, 794],
    dtype=float,
)
CRATER_DENSITY_PER_KM2 = np.array(
    [794, 501, 316, 200, 126, 79.4, 50.1, 31.6, 20, 12.6,
     7.94, 5.01, 3.16, 1.72, 0.773, 0.339, 0.146, 0.0617,
     0.026, 0.011],
    dtype=float,
)


@dataclass
class LightingConfig:
    azimuth_deg: float = 35.0
    elevation_deg: float = 8.0
    intensity: float = 1.0
    ambient: float = 0.035


@dataclass
class Config:
    input_tif: str
    output_dir: str
    seed: int = 0
    crop_size_m: float = 1000.0
    terrain_resolution_m: float = 1.0
    visual_resolution_m: float = 2.0
    collision_resolution_m: float = 2.0
    smoothing_radius_m: float = 5.0
    terrain_reference_z_m: float = 0.0
    crater_min_diameter_m: float = 5.0
    crater_max_diameter_m: float = 20.0
    crater_density_scale: float = 1.0
    crater_max_count: int = 5000
    rock_min_diameter_m: float = 0.1
    rock_max_diameter_m: float = 2.0
    rock_abundance_per_100m2: float = 0.234
    rock_density_scale: float = 1.0
    rock_max_count: int = 2500
    rock_sfd_exponent: float = 2.11
    rock_collision_cutoff_m: float = 0.1
    rock_height_ratio_mean: float = 0.60
    rock_height_ratio_std: float = 0.28
    rock_shape_segments: int = 8
    rock_shape_rings: int = 3
    rock_shape_irregularity: float = 0.12
    rock_embed_depth_m: float = 0.02
    rock_crater_probability: float = 0.65
    rock_crater_radius_factor: float = 2.0
    rock_crater_rim_width_factor: float = 0.25
    terrain_texture_strength: float = 0.18
    terrain_texture_scale_m: float = 35.0
    lighting: LightingConfig = field(default_factory=LightingConfig)


def _config_from_mapping(values: dict[str, Any]) -> Config:
    values = dict(values)
    lighting = LightingConfig(**values.pop("lighting", {}))
    return Config(lighting=lighting, **values)


def load_config(path: Path, cli: dict[str, Any]) -> Config:
    data: dict[str, Any] = {}
    if path:
        with path.open(encoding="utf-8") as stream:
            loaded = yaml.safe_load(stream) or {}
        if not isinstance(loaded, dict):
            raise ValueError("configuration root must be a mapping")
        data.update(loaded)
    data.update({key: value for key, value in cli.items() if value is not None})
    return _config_from_mapping(data)


def _validate_config(config: Config) -> None:
    if config.crop_size_m <= 0:
        raise ValueError("crop_size_m must be positive")
    if config.visual_resolution_m <= 0:
        raise ValueError("visual_resolution_m must be positive")
    if config.terrain_resolution_m <= 0:
        raise ValueError("terrain_resolution_m must be positive")
    if config.terrain_resolution_m > config.visual_resolution_m:
        raise ValueError("terrain resolution cannot be coarser than visual resolution")
    if not 0 < config.collision_resolution_m:
        raise ValueError("collision_resolution_m must be positive")
    if config.collision_resolution_m < config.visual_resolution_m:
        raise ValueError("collision resolution cannot be finer than visual resolution")
    if config.crater_max_count <= 0:
        raise ValueError("crater_max_count must be positive")
    if not 0 < config.crater_min_diameter_m <= config.crater_max_diameter_m:
        raise ValueError("invalid crater diameter range")
    if not 0 < config.rock_min_diameter_m <= config.rock_max_diameter_m:
        raise ValueError("invalid rock diameter range")
    if config.rock_abundance_per_100m2 < 0:
        raise ValueError("rock_abundance_per_100m2 cannot be negative")
    if config.rock_collision_cutoff_m < config.rock_min_diameter_m:
        raise ValueError("rock_collision_cutoff_m cannot be below rock_min_diameter_m")
    if config.rock_collision_cutoff_m > config.rock_max_diameter_m:
        raise ValueError("rock_collision_cutoff_m cannot exceed rock_max_diameter_m")
    if config.rock_shape_segments < 6 or config.rock_shape_rings < 2:
        raise ValueError("rock_shape_segments must be at least 6 and rock_shape_rings at least 2")
    if not 0 <= config.rock_shape_irregularity < 0.5:
        raise ValueError("rock_shape_irregularity must be in [0, 0.5)")
    if config.rock_embed_depth_m < 0:
        raise ValueError("rock_embed_depth_m cannot be negative")
    if not 0 <= config.rock_crater_probability <= 1:
        raise ValueError("rock_crater_probability must be between 0 and 1")
    if config.rock_crater_radius_factor <= 0:
        raise ValueError("rock_crater_radius_factor must be positive")
    if config.rock_crater_rim_width_factor <= 0:
        raise ValueError("rock_crater_rim_width_factor must be positive")


def _smooth(image: np.ndarray, radius_pixels: int) -> np.ndarray:
    if radius_pixels <= 0:
        return image
    size = radius_pixels * 2 + 1
    kernel = np.ones(size, dtype=float) / size
    padded = np.pad(image, ((0, 0), (radius_pixels, radius_pixels)), mode="edge")
    horizontal = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), 1, padded)
    padded = np.pad(horizontal, ((radius_pixels, radius_pixels), (0, 0)), mode="edge")
    return np.apply_along_axis(lambda col: np.convolve(col, kernel, mode="valid"), 0, padded)


def _resample(image: np.ndarray, rows: int, cols: int) -> np.ndarray:
    source_y = np.linspace(0.0, 1.0, image.shape[0])
    source_x = np.linspace(0.0, 1.0, image.shape[1])
    target_y = np.linspace(0.0, 1.0, rows)
    target_x = np.linspace(0.0, 1.0, cols)
    horizontal = np.vstack([np.interp(target_x, source_x, row) for row in image])
    return np.vstack([np.interp(target_y, source_y, horizontal[:, col]) for col in range(cols)]).T


def _cumulative_density(diameter_m: float) -> float:
    log_d = np.log(CRATER_DIAMETERS_M)
    log_n = np.log(CRATER_DENSITY_PER_KM2)
    if diameter_m < CRATER_DIAMETERS_M[0]:
        slope = (log_n[1] - log_n[0]) / (log_d[1] - log_d[0])
        return float(np.exp(log_n[0] + slope * (np.log(diameter_m) - log_d[0])))
    if diameter_m > CRATER_DIAMETERS_M[-1]:
        slope = (log_n[-1] - log_n[-2]) / (log_d[-1] - log_d[-2])
        return float(np.exp(log_n[-1] + slope * (np.log(diameter_m) - log_d[-1])))
    return float(np.exp(np.interp(np.log(diameter_m), log_d, log_n)))


def read_crop(config: Config, rng: np.random.Generator) -> tuple[np.ndarray, dict[str, Any]]:
    with rasterio.open(config.input_tif) as source:
        if source.count < 1:
            raise ValueError("input GeoTIFF has no raster bands")
        band = source.read(1, masked=True).astype(np.float64)
        if band.mask.all():
            raise ValueError("input GeoTIFF contains no valid elevation samples")
        nodata = source.nodata
        valid_rows, valid_cols = np.where(~band.mask)
        row_min, row_max = int(valid_rows.min()), int(valid_rows.max())
        col_min, col_max = int(valid_cols.min()), int(valid_cols.max())
        pixel_x, pixel_y = abs(source.transform.a), abs(source.transform.e)
        height_pixels = max(2, int(round(config.crop_size_m / pixel_y)))
        width_pixels = max(2, int(round(config.crop_size_m / pixel_x)))
        if height_pixels > row_max - row_min + 1 or width_pixels > col_max - col_min + 1:
            raise ValueError(
                f"crop_size_m={config.crop_size_m} exceeds valid raster extent "
                f"{(col_max - col_min + 1) * pixel_x:.1f} x {(row_max - row_min + 1) * pixel_y:.1f} m"
            )
        row0 = int(rng.integers(row_min, row_max - height_pixels + 2))
        col0 = int(rng.integers(col_min, col_max - width_pixels + 2))
        crop = band[row0:row0 + height_pixels, col0:col0 + width_pixels].filled(np.nan)
        if np.isnan(crop).any():
            raise ValueError("selected crop includes nodata; use a valid contiguous source raster")
        crop_origin = source.transform * (col0, row0)
        metadata = {
            "source": str(Path(config.input_tif).resolve()),
            "source_shape": [source.height, source.width],
            "source_resolution_m": [pixel_x, pixel_y],
            "source_nodata": nodata,
            "source_crs": str(source.crs) if source.crs else None,
            "crop_window_pixels": [row0, col0, height_pixels, width_pixels],
            "crop_origin_source": [float(crop_origin[0]), float(crop_origin[1])],
            "elevation_min_source_m": float(np.min(crop)),
            "elevation_max_source_m": float(np.max(crop)),
            "terrain_reference_z_m": config.terrain_reference_z_m,
        }
    return crop, metadata


def _sample_crater_diameters(
    rng: np.random.Generator,
    count: int,
    minimum: float,
    maximum: float,
) -> np.ndarray:
    """Sample diameters whose cumulative distribution follows the crater SFD."""
    minimum_density = _cumulative_density(minimum)
    maximum_density = _cumulative_density(maximum)
    target_density = minimum_density - rng.random(count) * (
        minimum_density - maximum_density
    )
    log_diameters = np.log(CRATER_DIAMETERS_M)
    log_densities = np.log(CRATER_DENSITY_PER_KM2)
    target_log_density = np.log(target_density)
    density_axis = log_densities[::-1]
    diameter_axis = log_diameters[::-1]
    sampled_log_diameter = np.interp(
        target_log_density, density_axis, diameter_axis
    )
    low = target_log_density < density_axis[0]
    high = target_log_density > density_axis[-1]
    low_slope = (diameter_axis[1] - diameter_axis[0]) / (density_axis[1] - density_axis[0])
    high_slope = (diameter_axis[-1] - diameter_axis[-2]) / (
        density_axis[-1] - density_axis[-2]
    )
    sampled_log_diameter[low] = diameter_axis[0] + low_slope * (
        target_log_density[low] - density_axis[0]
    )
    sampled_log_diameter[high] = diameter_axis[-1] + high_slope * (
        target_log_density[high] - density_axis[-1]
    )
    return np.exp(sampled_log_diameter)


def sample_craters(config: Config, rng: np.random.Generator) -> list[dict[str, float]]:
    area_km2 = (config.crop_size_m / 1000.0) ** 2
    density_min = _cumulative_density(config.crater_min_diameter_m)
    density_max = _cumulative_density(config.crater_max_diameter_m)
    expected = max(0.0, (density_min - density_max) * area_km2 * config.crater_density_scale)
    count = min(config.crater_max_count, int(rng.poisson(expected)))
    morphologies = (
        ("freshest", 0.005, 0.16),
        ("fresh", 0.025, 0.14),
        ("moderate", 0.17, 0.115),
        ("degraded", 0.30, 0.085),
        ("very_degraded", 0.50, 0.045),
    )
    probabilities = np.array([item[1] for item in morphologies])
    probabilities /= probabilities.sum()
    result: list[dict[str, float]] = []
    diameters = _sample_crater_diameters(
        rng,
        count,
        config.crater_min_diameter_m,
        config.crater_max_diameter_m,
    )
    for diameter in diameters:
        diameter = float(diameter)
        morphology_index = int(rng.choice(len(morphologies), p=probabilities))
        morphology, _, depth_ratio = morphologies[morphology_index]
        result.append({
            "x": float(rng.uniform(-config.crop_size_m / 2, config.crop_size_m / 2)),
            "y": float(rng.uniform(-config.crop_size_m / 2, config.crop_size_m / 2)),
            "diameter": diameter,
            "depth": diameter * float(rng.uniform(depth_ratio * 0.8, depth_ratio * 1.2)),
            "morphology": morphology,
        })
    return result


def _expected_rock_count(config: Config, area_m2: float) -> float:
    # Surveyor I SLS-DSNE abundance: 0.234 rocks >= 1 m / 100 m².
    abundance = (
        config.rock_abundance_per_100m2
        * area_m2
        / 100.0
        * config.rock_density_scale
    )
    exponent = config.rock_sfd_exponent
    expected_count = abundance * (
        config.rock_min_diameter_m ** (-exponent)
        - config.rock_max_diameter_m ** (-exponent)
    )
    return max(0.0, expected_count)


def _rock_count(config: Config, area_m2: float) -> int:
    return min(config.rock_max_count, int(_expected_rock_count(config, area_m2)))


def _sample_rock_diameters(
    config: Config, count: int, rng: np.random.Generator
) -> np.ndarray:
    """Sample the truncated cumulative rock SFD, N(>=D) proportional to D^-q."""
    exponent = config.rock_sfd_exponent
    minimum_power = config.rock_min_diameter_m ** (-exponent)
    maximum_power = config.rock_max_diameter_m ** (-exponent)
    target = minimum_power - rng.random(count) * (minimum_power - maximum_power)
    return target ** (-1.0 / exponent)


def sample_rocks(config: Config, craters: list[dict[str, float]], rng: np.random.Generator) -> list[dict[str, float]]:
    count = _rock_count(config, config.crop_size_m ** 2)
    rocks: list[dict[str, float]] = []
    diameters = _sample_rock_diameters(config, count, rng)
    crater_weights = None
    if craters:
        influence_radii = np.array(
            [
                crater["diameter"] * config.rock_crater_radius_factor / 2.0
                for crater in craters
            ]
        )
        crater_weights = influence_radii**2
        crater_weights /= crater_weights.sum()
    for diameter in diameters:
        if craters and rng.random() < config.rock_crater_probability:
            crater = craters[int(rng.choice(len(craters), p=crater_weights))]
            influence_radius = (
                crater["diameter"] * config.rock_crater_radius_factor / 2.0
            )
            rim_radius = crater["diameter"] / 2.0
            rim_width = influence_radius * config.rock_crater_rim_width_factor
            radial_distance = float(rng.normal(rim_radius, rim_width))
            for _ in range(8):
                if 0.0 <= radial_distance <= influence_radius:
                    break
                radial_distance = float(rng.normal(rim_radius, rim_width))
            radial_distance = float(np.clip(radial_distance, 0.0, influence_radius))
            angle = float(rng.uniform(0.0, 2.0 * math.pi))
            x = crater["x"] + radial_distance * math.cos(angle)
            y = crater["y"] + radial_distance * math.sin(angle)
        else:
            x = float(rng.uniform(-config.crop_size_m / 2, config.crop_size_m / 2))
            y = float(rng.uniform(-config.crop_size_m / 2, config.crop_size_m / 2))
        margin = diameter / 2
        x = float(np.clip(x, -config.crop_size_m / 2 + margin, config.crop_size_m / 2 - margin))
        y = float(np.clip(y, -config.crop_size_m / 2 + margin, config.crop_size_m / 2 - margin))
        diameter = float(diameter)
        ratio = float(np.clip(rng.normal(config.rock_height_ratio_mean, config.rock_height_ratio_std), 0.1, 
                              3 * config.rock_height_ratio_std))
        rocks.append({
            "x": x, "y": y, "diameter": diameter, "height": diameter * ratio,
            "yaw": float(rng.uniform(0, 2 * math.pi)),
        })
    return rocks


def apply_craters(
    elevation: np.ndarray, config: Config, craters: list[dict[str, float]]
) -> np.ndarray:
    result = elevation.copy()
    half = config.crop_size_m / 2
    rows, cols = result.shape
    x = np.linspace(-half, half, cols)
    y = np.linspace(-half, half, rows)
    xx, yy = np.meshgrid(x, y)
    for crater in craters:
        radius = crater["diameter"] / 2
        distance = np.hypot(xx - crater["x"], yy - crater["y"])
        inside = distance <= radius
        profile = np.zeros_like(result)
        profile[inside] = -crater["depth"] * (1 - (distance[inside] / radius) ** 2)
        rim_peak_radius_factor = 1.05
        rim_half_width_factor = 0.20
        rim_height_factor = 0.20
        rim_inner_radius_factor = rim_peak_radius_factor - rim_half_width_factor
        rim_outer_radius_factor = rim_peak_radius_factor + rim_half_width_factor
        rim = (distance > radius * rim_inner_radius_factor) & (
            distance <= radius * rim_outer_radius_factor
        )
        profile[rim] += crater["depth"] * rim_height_factor * (
            1
            - np.abs(distance[rim] / radius - rim_peak_radius_factor)
            / rim_half_width_factor
        )
        result += profile
    return result


def _mesh_grid(
    elevation: np.ndarray, resolution: float, config: Config
) -> tuple[np.ndarray, np.ndarray]:
    stride = max(1, int(round(resolution / config.terrain_resolution_m)))
    sampled = elevation[::stride, ::stride]
    if sampled[-1, -1] != elevation[-1, -1]:
        sampled = np.pad(sampled, ((0, 1), (0, 1)), mode="edge")
    rows, cols = sampled.shape
    half = config.crop_size_m / 2
    xs = np.linspace(-half, half, cols)
    ys = np.linspace(-half, half, rows)
    xx, yy = np.meshgrid(xs, ys, indexing="xy")
    vertices = np.column_stack((xx.reshape(-1), yy.reshape(-1), sampled.reshape(-1)))
    faces: list[tuple[int, int, int]] = []
    for row in range(rows - 1):
        for col in range(cols - 1):
            a = row * cols + col + 1
            b = a + 1
            c = a + cols
            d = c + 1
            faces.extend(((a, b, d), (a, d, c)))
    return vertices, np.asarray(faces, dtype=int)


def _material_indices(vertices: np.ndarray, faces: np.ndarray, config: Config) -> np.ndarray:
    if not len(faces):
        return np.zeros(0, dtype=int)
    centers = vertices[faces - 1].mean(axis=1)
    texture = (
        np.sin(centers[:, 0] / config.terrain_texture_scale_m)
        + 0.55 * np.cos(centers[:, 1] / (config.terrain_texture_scale_m * 1.7))
        + 0.25 * np.sin((centers[:, 0] + centers[:, 1]) / (config.terrain_texture_scale_m * 0.37))
    )
    scaled = texture * config.terrain_texture_strength
    return np.clip(np.floor((scaled + 1.0) * 2.0), 0, 3).astype(int)


def _write_obj(
    path: Path,
    vertices: np.ndarray,
    faces: np.ndarray,
    material_indices: np.ndarray | None = None,
) -> None:
    material_indices = (
        np.zeros(len(faces), dtype=int) if material_indices is None else material_indices
    )
    normals = np.zeros_like(vertices, dtype=float)
    if len(faces):
        face_vertices = vertices[faces - 1]
        face_normals = np.cross(
            face_vertices[:, 1] - face_vertices[:, 0],
            face_vertices[:, 2] - face_vertices[:, 0],
        )
        lengths = np.linalg.norm(face_normals, axis=1)
        valid = lengths > np.finfo(float).eps
        face_normals[valid] /= lengths[valid, None]
        for corner in range(3):
            np.add.at(normals, faces[:, corner] - 1, face_normals)
        normal_lengths = np.linalg.norm(normals, axis=1)
        valid = normal_lengths > np.finfo(float).eps
        normals[valid] /= normal_lengths[valid, None]
        normals[~valid] = (0.0, 0.0, 1.0)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(f"mtllib {path.with_suffix('.mtl').name}\n")
        for x, y, z in vertices:
            stream.write(f"v {x:.5f} {y:.5f} {z:.5f}\n")
        for nx, ny, nz in normals:
            stream.write(f"vn {nx:.7f} {ny:.7f} {nz:.7f}\n")
        for index, (a, b, c) in enumerate(faces):
            stream.write(f"usemtl lunar_surface_{material_indices[index]}\n")
            stream.write(f"f {a}//{a} {b}//{b} {c}//{c}\n")
    colors = (0.34, 0.39, 0.44, 0.50)
    path.with_suffix(".mtl").write_text(
        "".join(
            f"newmtl lunar_surface_{index}\nKd {color} {color} {color}\n"
            "roughness 1.0\n\n"
            for index, color in enumerate(colors)
        ),
        encoding="utf-8",
    )


def _rock_mesh(rocks: list[dict[str, float]], terrain: np.ndarray, config: Config) -> tuple[np.ndarray, np.ndarray]:
    def terrain_height(x: float, y: float) -> float:
        col = (x + config.crop_size_m / 2) / config.crop_size_m * (terrain.shape[1] - 1)
        row = (y + config.crop_size_m / 2) / config.crop_size_m * (terrain.shape[0] - 1)
        col0 = int(np.clip(math.floor(col), 0, terrain.shape[1] - 1))
        row0 = int(np.clip(math.floor(row), 0, terrain.shape[0] - 1))
        col1 = min(col0 + 1, terrain.shape[1] - 1)
        row1 = min(row0 + 1, terrain.shape[0] - 1)
        fx = col - col0
        fy = row - row0
        return float(
            (1 - fy) * ((1 - fx) * terrain[row0, col0] + fx * terrain[row0, col1])
            + fy * ((1 - fx) * terrain[row1, col0] + fx * terrain[row1, col1])
        )

    vertices: list[list[float]] = []
    faces: list[tuple[int, int, int]] = []
    for rock in rocks:
        if rock["diameter"] < config.rock_collision_cutoff_m:
            continue
        radius = rock["diameter"] / 2
        height = rock["height"]
        base_z = terrain_height(rock["x"], rock["y"])
        start = len(vertices) + 1
        segments = config.rock_shape_segments
        rings = config.rock_shape_rings
        yaw = rock["yaw"]
        ring_count = rings + 1
        for ring in range(ring_count):
            fraction = ring / rings
            radial_factor = 0.35 + 0.65 * math.sin(math.pi * fraction) ** 0.55
            z = base_z + height * fraction
            for segment in range(segments):
                angle = yaw + 2 * math.pi * segment / segments
                irregularity = 1.0 + config.rock_shape_irregularity * math.sin(
                    3 * angle + 1.7 * fraction
                )
                r = radius * radial_factor * irregularity
                vertex_x = rock["x"] + r * math.cos(angle)
                vertex_y = rock["y"] + r * math.sin(angle)
                if ring == 0:
                    z = terrain_height(vertex_x, vertex_y) - config.rock_embed_depth_m
                vertices.append([vertex_x, vertex_y, z])
        for ring in range(rings):
            for segment in range(segments):
                a = start + ring * segments + segment
                b = start + ring * segments + (segment + 1) % segments
                c = start + (ring + 1) * segments + segment
                d = start + (ring + 1) * segments + (segment + 1) % segments
                faces.extend(((a, b, d), (a, d, c)))
        bottom = start
        for segment in range(1, segments - 1):
            faces.append((bottom, bottom + segment + 1, bottom + segment))
        top_center = len(vertices) + 1
        vertices.append([rock["x"], rock["y"], base_z + height])
        top = start + rings * segments
        for segment in range(segments):
            faces.append((top + segment, top + (segment + 1) % segments, top_center))
    return np.asarray(vertices), np.asarray(faces, dtype=int)


def _write_sdf(output: Path, config: Config) -> None:
    output_uri = output.resolve().as_uri()
    light = config.lighting
    azimuth = math.radians(light.azimuth_deg)
    elevation = math.radians(light.elevation_deg)
    direction = (
        math.cos(elevation) * math.cos(azimuth),
        math.cos(elevation) * math.sin(azimuth),
        -math.sin(elevation),
    )
    world = f"""<?xml version="1.0"?>
<sdf version="1.7">
  <world name="generated_lunar_world">
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
    <gravity>0 0 -1.62</gravity>
    <scene><ambient>{light.ambient} {light.ambient} {light.ambient} 1</ambient><background>0.01 0.01 0.01 1</background><shadows>true</shadows></scene>
    <light name="low_angle_sun" type="directional">
      <cast_shadows>true</cast_shadows><diffuse>{light.intensity} {light.intensity} {light.intensity} 1</diffuse>
      <specular>0 0 0 1</specular><direction>{direction[0]} {direction[1]} {direction[2]}</direction>
    </light>
    <include><uri>{output_uri}/terrain_model.sdf</uri></include>
    <include><uri>{output_uri}/rocks_model.sdf</uri></include>
  </world>
</sdf>
"""
    (output / "world.sdf").write_text(world, encoding="utf-8")
    terrain_model = """<?xml version="1.0"?><sdf version="1.7"><model name="terrain"><static>true</static><link name="terrain"><visual name="visual"><geometry><mesh><uri>file://{}/terrain_visual.obj</uri></mesh></geometry></visual><collision name="collision"><geometry><mesh><uri>file://{}/terrain_collision.obj</uri></mesh></geometry></collision></link></model></sdf>""".format(output.resolve(), output.resolve())
    rocks_model = """<?xml version="1.0"?><sdf version="1.7"><model name="rocks"><static>true</static><link name="rocks"><visual name="visual"><geometry><mesh><uri>file://{}/rocks.obj</uri></mesh></geometry></visual><collision name="collision"><geometry><mesh><uri>file://{}/rocks.obj</uri></mesh></geometry></collision></link></model></sdf>""".format(output.resolve(), output.resolve())
    (output / "terrain_model.sdf").write_text(terrain_model, encoding="utf-8")
    (output / "rocks_model.sdf").write_text(rocks_model, encoding="utf-8")


def generate(config: Config) -> dict[str, Any]:
    _validate_config(config)
    rng = np.random.default_rng(config.seed)
    output = Path(config.output_dir)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    elevation, source_metadata = read_crop(config, rng)
    target_size = max(2, int(round(config.crop_size_m / config.terrain_resolution_m))) + 1
    elevation = _resample(elevation, target_size, target_size)
    smoothing_radius_pixels = int(
        round(config.smoothing_radius_m / config.terrain_resolution_m)
    )
    elevation = _smooth(elevation, smoothing_radius_pixels)
    craters = sample_craters(config, rng)
    elevation = apply_craters(elevation, config, craters)
    center_row = (elevation.shape[0] - 1) // 2
    center_col = (elevation.shape[1] - 1) // 2
    elevation += config.terrain_reference_z_m - elevation[center_row, center_col]
    rocks = sample_rocks(config, craters, rng)
    visual_vertices, visual_faces = _mesh_grid(elevation, config.visual_resolution_m, config)
    collision_vertices, collision_faces = _mesh_grid(elevation, config.collision_resolution_m, config)
    _write_obj(
        output / "terrain_visual.obj", visual_vertices, visual_faces,
        _material_indices(visual_vertices, visual_faces, config),
    )
    _write_obj(
        output / "terrain_collision.obj", collision_vertices, collision_faces,
        _material_indices(collision_vertices, collision_faces, config),
    )
    rock_vertices, rock_faces = _rock_mesh(rocks, elevation, config)
    if len(rock_vertices):
        _write_obj(output / "rocks.obj", rock_vertices, rock_faces)
    else:
        _write_obj(
            output / "rocks.obj", np.zeros((0, 3)), np.zeros((0, 3), dtype=int)
        )
    _write_sdf(output, config)
    manifest = {
        "generator": "lunar_world_generator",
        "seed": config.seed,
        "config": asdict(config),
        "source": source_metadata,
        "counts": {
            "craters": len(craters),
            "rocks": len(rocks),
            "expected_rocks_before_cap": _expected_rock_count(
                config, config.crop_size_m ** 2
            ),
            "lidar_collision_rocks": int(len(rock_vertices) / (
                config.rock_shape_segments * (config.rock_shape_rings + 1) + 1
            )),
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--input-tif")
    parser.add_argument("--output-dir")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--crop-size-m", type=float)
    parser.add_argument("--terrain-resolution-m", type=float)
    parser.add_argument("--visual-resolution-m", type=float)
    parser.add_argument("--collision-resolution-m", type=float)
    parser.add_argument("--smoothing-radius-m", type=float)
    parser.add_argument("--terrain-reference-z-m", type=float)
    parser.add_argument("--crater-min-diameter-m", type=float)
    parser.add_argument("--crater-max-diameter-m", type=float)
    parser.add_argument("--rock-min-diameter-m", type=float)
    parser.add_argument("--rock-max-diameter-m", type=float)
    parser.add_argument("--rock-abundance-per-100m2", type=float)
    parser.add_argument("--rock-sfd-exponent", type=float)
    parser.add_argument("--rock-shape-segments", type=int)
    parser.add_argument("--rock-shape-rings", type=int)
    parser.add_argument("--rock-shape-irregularity", type=float)
    parser.add_argument("--rock-embed-depth-m", type=float)
    parser.add_argument("--rock-crater-probability", type=float)
    parser.add_argument("--rock-crater-radius-factor", type=float)
    parser.add_argument("--rock-crater-rim-width-factor", type=float)
    parser.add_argument("--rock-collision-cutoff-m", type=float)
    return parser


def main() -> None:
    args = vars(_parser().parse_args())
    config_path = args.pop("config")
    config = load_config(config_path, args)
    if not config.input_tif or not config.output_dir:
        raise SystemExit("--input-tif and --output-dir are required, directly or in --config")
    manifest = generate(config)
    print(json.dumps({"output_dir": config.output_dir, "counts": manifest["counts"]}, indent=2))


if __name__ == "__main__":
    main()