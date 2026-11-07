# Deku canonical reconstruction export — v1

This is a portable snapshot of the existing notebook 13 experiment. No SfM
algorithm changes, point filtering, duplicate merging, image edits, or Rerun
installation were performed. All 386 original point IDs are retained, including
the 10 IDs rejected by the existing diagnostic settings.

## Files and schema

| File | Contents |
| --- | --- |
| `manifest.json` | Schema version, environment, stages, coordinate conventions, image and artifact hashes, comparison with historical diagnostics, anomalies, and limitations. |
| `points.npz` | `point_ids`: int64 `(386,)`, equal to original map row indices 0–385. `xyz`: original float32 `(386,3)` world positions. `rgb`: uint8 `(386,3)` in RGB order. `stage`: int64 `(386,)`, the point's creation stage. All arrays load with `allow_pickle=False`. |
| `cameras.json` | Four registered cameras, numbered 3–6; original zero-based image indices; image paths relative to the repository root; original/SIFT dimensions; intrinsics at both resolutions; world-to-camera R/t and homogeneous transforms in both directions. |
| `observations.csv` | 897 evidence rows linking points, cameras and keypoints, with source pixels, reprojections, depths, errors, stages, provenance and final-map membership. |
| `metrics.csv` | Byte-for-byte copy of the historical triangulation diagnostic CSV, after comparison against reproduced variables. Contains one row per original point ID, birth-pair metrics, final-association aggregates, diagnostic acceptance and rejection reasons. |

CSV booleans are the literal strings `True` and `False`. Empty source-camera and
source-keypoint fields mean not applicable. Coordinates are numeric pixel values,
errors are Euclidean pixel distances, angles are degrees, and 3D lengths use the
arbitrary monocular scale. Arrays and CSV rows must be joined by `point_id`, never
by the current visible point index after filtering.

`schema_version = 1.0.0` describes the format. The output directory version
identifies the particular exported experiment; it is not a new reconstruction.
The four payload checksums are in the manifest. The manifest is intentionally not
self-hashed. Image files remain in `data/`; copy that directory alongside the
export or resolve its repository-relative paths when transferring the snapshot.

## Camera and pixel conventions

The exact historical convention is:

```text
X_camera = R_world_to_camera @ X_world + t_world_to_camera
C_world = -R_world_to_camera.T @ t_world_to_camera
X_world = R_world_to_camera.T @ X_camera + C_world
```

`T_world_to_camera` and `T_camera_to_world` are 4×4 homogeneous transforms for
column vectors `[X,Y,Z,1]`. The world frame is the original View 03 camera frame.
Camera axes are right-handed RDF: X right, Y down, Z forward. The seed baseline
between Views 03 and 04 is one arbitrary unit, not one meter.

All twelve original photographs decode to 1152×1536 (width×height). SIFT used
900×1200, with `cv2.resize` default `INTER_LINEAR`. Both scale factors are 0.78125.
The approximate shared intrinsics at the SIFT resolution are:

```text
K_sift = [[810, 0, 450], [0, 810, 600], [0, 0, 1]]
K_original = [[1036.8, 0, 576], [0, 1036.8, 768], [0, 0, 1]]
```

`K_sift = diag(scale_x, scale_y, 1) @ K_original`. Observed and projected pixel
coordinates use `(u,v) = (column,row)` from the top-left corner. Original pixels
are derived by dividing SIFT coordinates by the scale factors. This is the
conventional linear scaling of the existing approximate camera model; no new
calibration or half-pixel correction has been introduced. Original photos are
neither rewritten nor undistorted. Raw historical colors are exactly recovered
by `rgb.astype(float64) / 255`; the conversion to uint8 lost no source values.

## Reconstruction chronology

| Stage | Event | Point IDs available | Registered cameras |
| --- | --- | ---: | --- |
| 0 | Seed triangulation, Views 03–04 | 188 | 3, 4 |
| 1 | PnP registration, View 05 | 188 | 3, 4, 5 |
| 2 | PnP registration, View 06 | 188 | 3, 4, 5, 6 |
| 3 | Map expansion, Views 04–05 | 301 | 3, 4, 5, 6 |
| 4 | Map expansion, Views 05–06 | 386 | 3, 4, 5, 6 |

Point birth stages are therefore 0, 3 and 4. Camera registration happens before
the two expansions in the actual historical notebook. These stages preserve that
chronology rather than inventing an interleaved registration/expansion loop.

## Observation provenance

- `seed_triangulation`: 376 rows, the two original observations of 188 seed IDs.
- `new_triangulation`: 396 rows, the two birth observations of 198 added IDs.
- `pnp_inlier`: 91 retained associations from the original PnP dictionaries
  (70 for View 05 and 21 for View 06).
- `descriptor_propagation`: 34 insertions captured by replaying the original
  propagation rule on copies immediately before the unchanged expansion calls.

The evidence union has 897 rows. Exactly 892 correspond to the final dictionaries.
Five birth associations were overwritten by historical many-to-one assignments;
their rows are retained with `active_in_final_map=False`. Do not use those five
rows when reproducing final-dictionary aggregate metrics. A row's provenance
describes how it entered the experiment, not whether its physical match is correct.

`source_camera_id` / `source_keypoint_id` identify the source of propagation.
`source_evidence` explains where each row was recovered. `geometrically_consistent_3px`
is only a post-hoc check: positive camera depth and error ≤3 px. It does not alter
the source inliers or the original map. PnP records cover retained dictionaries,
not discarded RANSAC hypotheses or a complete correspondence history.

## Verified preservation and anomalies

- Replayed XYZ and historical diagnostic XYZ match exactly; maximum difference
  across reproduced historical diagnostic values is **0.0**.
- Original normalized colors survive an exact RGB uint8 round trip.
- Camera centers match the historical variables and transforms are mutual inverses.
- All pre-existing notebooks, images, model weights and results were hashed before
  and after replay and remained unchanged; hashes are recorded in the manifest.
- 386 IDs occupy **364 distinct XYZ positions**: 21 duplicate groups, 22 extra IDs.
  Full duplicate membership is recorded; no ID was removed or merged.
- Existing diagnostic acceptance is **376/386** under 2°, 3 px and 10-baseline
  thresholds. The 10 rejected IDs remain in `points.npz` and `metrics.csv`.
- Seven point IDs have final-association errors above 3 px: 62, 140, 161, 162,
  192, 232 and 295. The maximum is approximately **540.904 px**.
- Historical `point_birth` has only 188 entries, while `global_points` has 386.
  The canonical `stage` array is derived from actual seed/expansion ID lists;
  the historical variable is left untouched and its short length is recorded.
- The 107 expansion candidates originally rejected before map insertion did not
  receive original map IDs. They are not the 10 post-hoc diagnostic rejections,
  and are not silently added as new canonical map points.

K is approximate, distortion is omitted, bundle adjustment is absent, and eight
images remain unregistered. Duplicate samples and inconsistent propagated matches
are evidence to investigate. Low reprojection error does not establish reliable
3D depth. The export reports existing results; it does not repair the algorithm
or establish ground truth. The historical notebook did not explicitly set an RNG
seed; its numerical call order was retained. Reproduction on another dependency
stack must pass the historical comparison rather than silently substitute a map.

## Reproduction and independent validation

From the repository root, using the existing project environment:

```bash
# Validate this snapshot only: no SfM, model inference, or file writes.
.venv/bin/python -B scripts/export_canonical_reconstruction.py \
  --validate-only results/canonical_reconstruction/v1

# Reproduce using a NEW version directory. Existing versions are never overwritten.
.venv/bin/python -B scripts/export_canonical_reconstruction.py \
  --output results/canonical_reconstruction/v2

# Lightweight Python tests; canonical tests do not execute the reconstruction.
.venv/bin/python -B -m unittest discover -s tests -v
```

The exporter executes preserved numerical notebook cells in their original order,
skips the historical `%pip` cell, suppresses displays and invokes no learned model.
It never executes the notebook's appended export cells or the older diagnostic
runner, both of which would write historical outputs. It aborts if the map differs
from historical diagnostics, and refuses an existing output directory. A failed
export can leave a partial new directory; successful validation is required before
treating a new version as complete.

The independent `validate_export` function uses NumPy and the standard library;
Pillow is used only when validating referenced image dimensions. It needs no kernel,
OpenCV, Plotly, PyTorch or Rerun. It verifies checksums, array schemas, camera inverses,
image scales, point references, observation reprojections, birth-pair metrics and
final-association aggregates. Tests also corrupt private temporary copies to check
that reversed translations, renumbered points and inconsistent observations fail.

## Exact next steps for the first Rerun recording (not implemented)

1. Create a separate visualization environment after approval and pin a Rerun SDK
   compatible with that environment; leave the historical environment unchanged.
2. Read these artifacts directly with `np.load(..., allow_pickle=False)`, JSON and
   CSV. No reconstruction or feature extraction is needed.
3. Open a `RecordingStream`, call `save` for a new `.rrd`, and log the coordinate
   convention. Use a sequence timeline with stages 0–4 as documented above.
4. At each stage, log the points whose birth stage is available, with original RGB
   and explicit original IDs. Log accepted and rejected subsets on separate paths.
5. Log each available camera's `T_camera_to_world`, `Pinhole` and referenced image.
   Pair full-resolution photos with `K_original`, or 900×1200 images with `K_sift`.
6. Log observed pixels, projected pixels, residual segments and per-point metrics.
   Keep provenance and inactive historical evidence distinguishable. Stage-time
   membership is not the same as final-map activity; this export does not claim a
   complete history of every intermediate dictionary overwrite.
7. Add a 3D/image/metrics blueprint and visually verify camera orientation, point
   reprojections, counts, duplicate preservation and the known high-error cases.

No Rerun package or `.rrd` is included in this milestone.
