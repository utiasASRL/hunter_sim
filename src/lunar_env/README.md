# Lunar world generator

`world_generator.py` creates a deterministic Gazebo SDF world from a lunar
elevation GeoTIFF. The source raster is replaceable: its dimensions,
resolution, CRS, nodata mask, and valid extent are inspected at runtime.

The generator writes:

- `world.sdf`, `terrain_model.sdf`, and `rocks_model.sdf`;
- higher-resolution `terrain_visual.obj`;
- lower-triangle-count but aligned `terrain_collision.obj`;
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
crop_size_m: 1000
terrain_resolution_m: 1
crater_min_diameter_m: 5
crater_max_diameter_m: 20
crater_max_count: 5000
rock_min_diameter_m: 0.1
rock_max_diameter_m: 2
rock_abundance_per_100m2: 0.234
rock_sfd_exponent: 2.11
rock_shape_segments: 8
rock_shape_rings: 3
rock_shape_irregularity: 0.12
rock_embed_depth_m: 0.02
rock_crater_probability: 0.65
rock_crater_radius_factor: 2
rock_crater_rim_width_factor: 0.25
rock_collision_cutoff_m: 0.1
visual_resolution_m: 2
collision_resolution_m: 2
terrain_reference_z_m: 0
```

`terrain_reference_z_m` is the desired height of the terrain directly under
the world origin. With the default value of `0`, the generated surface at
`x=0, y=0` is at `z=0`; the terrain, craters, and rocks are shifted together.

`crater_max_count` is a safety/performance cap, not a density setting. For the
default 1 km² crop and 5--20 m diameter range, the NASA cumulative SFD predicts
approximately 2,959 craters. The default cap of 5,000 does not truncate that
distribution; reduce it only when performance is more important than the
specified abundance.

Rock diameters use the truncated cumulative law `N(>=D) proportional to
D^-rock_sfd_exponent`, rather than a log-uniform distribution. With the
default 0.1--2 m range and exponent 2.11, approximately 0.6% of generated
rocks are at least 1 m; this is why small rocks dominate numerically. The
default Surveyor I abundance (`rock_abundance_per_100m2: 0.234`) extrapolated
down to 0.1 m predicts about 302,000 rocks per km2, so `rock_max_count: 2500`
intentionally caps the generated
sample for Gazebo performance. The manifest records the uncapped expected
count as `expected_rocks_before_cap`.

Rocks are represented by low-poly, irregular rounded boulders rather than
sharp-pointed octahedra. Increase `rock_shape_segments` or
`rock_shape_rings` for rounder silhouettes, or increase
`rock_shape_irregularity` for less uniform shapes.

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

The source raster is first upsampled to `terrain_resolution_m` (1 m by default)
before smoothing and procedural crater relief are applied. The visual and
collision meshes are then sampled from that terrain grid at
`visual_resolution_m` and `collision_resolution_m`, respectively. This keeps
the higher-resolution smoothing and feature placement separate from exported
mesh cost. Collision rocks are
low-poly shapes, rather than the visual mesh detail, and every rock at or above
`rock_collision_cutoff_m` participates in LiDAR collision. The default cutoff
is the 0.1 m minimum, so no generated rock is omitted from LiDAR by default.
