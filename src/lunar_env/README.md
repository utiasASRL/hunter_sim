# Lunar world generator

`world_generator.py` creates a deterministic Gazebo SDF world from a lunar
elevation GeoTIFF. The source raster is replaceable: its dimensions,
resolution, CRS, nodata mask, and valid extent are inspected at runtime.

The generator writes:

- `world.sdf`, `terrain_model.sdf`, and `rocks_model.sdf`;
- shared `terrain.obj` used for both visual and collision geometry;
- `rocks.obj`, used for both visual and collision geometry so rocks appear in
  Gazebo LiDAR scans;
- `manifest.json`, including the resolved configuration, source metadata, seed,
  crop, and generated feature counts.

## Dependencies

The Docker image installs the small runtime set:

```text
python3-numpy
python3-rasterio
python3-yaml
```

No mesh-processing framework is required.

## Usage

```bash
python3 world_generator.py \
  --input-tif Site06_final_adj_5mpp_surf.tif \
  --output-dir /tmp/lunar_world_42 \
  --seed 42
```

All arbitrary choices are configurable. A YAML file can provide a complete
experiment configuration, and command-line values override it:

```yaml
input_tif: /data/site.tif
output_dir: /tmp/lunar_world
seed: 42
crop_size_m: 500
terrain_resolution_m: 0.5
crater_min_diameter_m: 0.5
crater_max_diameter_m: 20
limit_crater_diameter_to_source_resolution: true
crater_max_count: 5000
rock_min_diameter_m: 0.1
rock_max_diameter_m: 2
rock_abundance_per_100m2: 0.014
rock_max_count: 80000
rock_sfd_exponent: 2.11
rock_small_shape_segments: 6
rock_large_shape_segments: 12
rock_small_shape_rings: 2
rock_large_shape_rings: 4
rock_detail_transition_diameter_m: 1
rock_shape_irregularity: 0.12
rock_embed_depth_m: 0.02
rock_crater_probability: 0.65
rock_crater_radius_factor: 2
rock_crater_rim_width_factor: 0.25
rock_collision_cutoff_m: 0.1
terrain_reference_z_m: 0
terrain_material_base: 0.94
rock_material_base: 0.28
material_color_step: 0.04
terrain_texture_size: 2048
terrain_texture_tile_size_m: 8
terrain_texture_base: 0.72
terrain_texture_contrast: 0.14
```

`terrain_reference_z_m` is the desired height of the terrain directly under
the world origin. With the default value of `0`, the generated surface at
`x=0, y=0` is at `z=0`; the terrain, craters, and rocks are shifted together.

`crater_max_count` is a safety/performance cap, not a density setting. The
crater cumulative SFD is extrapolated below the smallest tabulated SLS-DSNE
diameter, so the default range includes craters down to 0.5 m. The cap is
important at these sizes because the extrapolated population can be very large.
The default 0.5 m terrain mesh is only just fine enough to sample a 0.5 m crater
and will not faithfully represent its rim; decrease `terrain_resolution_m` if
sub-metre crater geometry is required.

`limit_crater_diameter_to_source_resolution: true` prevents procedural
craters larger than the finer source DEM pixel dimension. For example, a DEM
with 5 m pixels will generate no procedural craters above 5 m; larger features
are assumed to already be represented by the source elevation data. This is
enabled by default. The same option is available on the command line as
`--limit-crater-diameter-to-source-resolution`. If this limit is at or below
`crater_min_diameter_m`, no procedural craters are added.

Rock diameters use the truncated cumulative law `N(>=D) proportional to
D^-rock_sfd_exponent`, rather than a log-uniform distribution. With the
default 0.1--2 m range and exponent 2.11, approximately 0.6% of generated
rocks are at least 1 m; this is why small rocks dominate numerically. The
default least-dense SLS-DSNE abundance
(`rock_abundance_per_100m2: 0.014`) extrapolated down to 0.1 m predicts about
18,000 rocks per km2, or approximately 4,500 rocks in the default 500 m × 500 m
crop. The `rock_max_count: 80000` setting is a permanent safety cap and does
not truncate the default sample; the manifest records the uncapped expected
count as `expected_rocks_before_cap`.

The 80,000-rock setting remains available for larger crops or increased
abundance scales. With the default rounded-rock geometry it can produce
millions of vertices and triangles, so generation and Gazebo loading may be
slow or memory-intensive.

The terrain uses a deterministic seamless multi-scale lunar-regolith tile.
`terrain_texture_tile_size_m` controls how many meters the tile covers; the
texture repeats across the crop, but periodic noise and multiple spatial scales
avoid hard seams and obvious regular bands. The tile uses isotropic randomized
frequency content rather than separate horizontal and vertical waves, avoiding
the checkerboard/grid appearance while retaining fine-grained noise. With the
default 8 m tile and 2048-pixel texture, each texture pixel represents about
3.9 mm. `terrain_texture_size` controls the tile resolution.
`terrain_texture_base` controls the average regolith
brightness, while `terrain_texture_contrast` controls the variation around that
brightness. The terrain and rocks use separate
grayscale material palettes. The default
terrain palette is bright (`terrain_material_base: 0.94`) and the rock palette
is darker (`rock_material_base: 0.28`). `material_color_step` controls the
variation among the four generated shades.

Rocks are represented by low-poly, irregular rounded boulders rather than
sharp-pointed octahedra. Rocks at the minimum diameter use
`rock_small_shape_segments` and `rock_small_shape_rings`; detail increases
linearly with diameter until `rock_detail_transition_diameter_m`, where the
large-rock segment and ring settings are reached. This keeps the many small
rocks inexpensive while preserving smoother silhouettes for larger rocks.
Increase `rock_shape_irregularity` for less uniform shapes.

Rock footprints are bilinearly conformed to the terrain mesh and are embedded
by `rock_embed_depth_m` (2 cm by default) to prevent visible gaps on slopes.
Rock centers are also constrained inside the generated terrain boundary.
`rock_crater_probability` controls the fraction of rocks initially sampled
near craters; `0` makes all rocks uniform and `1` makes all rocks
crater-associated when craters are present. The default `0.65` is a tunable
heuristic, not a measured NASA probability.

Crater-associated rocks select craters with probability proportional to the
area of their influence regions, so larger craters attract more rocks. Their
angle around the selected crater is uniform, while radial distance is sampled
from a rim-centered normal distribution. `rock_crater_radius_factor` controls
the outer influence radius relative to crater diameter, and
`rock_crater_rim_width_factor` controls the radial spread around the rim.

The generated `world.sdf` can be tested directly:

```bash
gz sim -s -r -v 3 /tmp/lunar_world_42/world.sdf
```

Use `-s` for server-only mode when testing from a headless container. To open
the GUI from a Docker container, the container must have access to the host X
server. The container needs the X11 socket and a matching Xauthority file, for
example:

```bash
XAUTH=/tmp/.docker.xauth
touch "$XAUTH"
xauth nlist "$DISPLAY" | sed 's/^..../ffff/' | xauth -f "$XAUTH" nmerge -

docker run ... \
  -e DISPLAY="$DISPLAY" \
  -e XAUTHORITY=/tmp/.docker.xauth \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$XAUTH":/tmp/.docker.xauth:rw \
  ...
```

If the GUI is not needed, use `gz sim -s` rather than `gz sim`; this avoids
Qt/X11 errors such as `Authorization required` and `could not connect to
display`.

The source raster is first upsampled to `terrain_resolution_m` before smoothing
and procedural crater relief are applied. A single `terrain.obj` mesh is then
used for both Gazebo visual and collision geometry, so the robot sees exactly
the same terrain heightmap that LiDAR and collision queries use. Collision rocks are
low-poly shapes, rather than the visual mesh detail, and every rock at or above
`rock_collision_cutoff_m` participates in LiDAR collision. The default cutoff
is the 0.1 m minimum, so no generated rock is omitted from LiDAR by default.
