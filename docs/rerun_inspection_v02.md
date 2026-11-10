# Research Lab v0.2: observation inspection

This is an ID-indexed inspection of the **final canonical snapshot**, using the
existing macOS Python 3.12.13 / Rerun 0.42.0 environment. It neither reruns SfM nor
changes camera poses, point geometry, the canonical export, or the v0.1 recording.
No packages were installed. Generated recordings embed private photographs and
remain ignored by Git, including their generated validation reports.

## Reproduce on macOS

From the project root, with the existing `.venv-rerun` environment and local
original photographs available:

```bash
.venv-rerun/bin/python -B scripts/export_rerun_inspection.py
.venv-rerun/bin/rerun --bind 127.0.0.1 \
  results/rerun_reconstruction/v2/deku_inspection.rrd
```

The exporter refuses an existing output directory. For another run use a fresh
directory, for example `--output results/rerun_reconstruction/v2_repeat_01`.
It writes `deku_inspection.rrd` and `validation.json`; neither is staged or tracked.
The original v0.1 artifact remains at `results/rerun_reconstruction/v1/`.

```bash
.venv-rerun/bin/python -B scripts/export_rerun_inspection.py \
  --validate-only results/rerun_reconstruction/v2/deku_inspection.rrd
.venv-rerun/bin/python -B -m unittest discover -s tests -p 'test_rerun*.py' -v
```

Numeric-only tests also run without Rerun or photographs in an environment with
NumPy: `python -B -m unittest discover -s tests -p test_rerun_inspection.py -k ObservationGeometryTests`.
RRD readback tests require the private recording, the pinned SDK and four local
registered-camera images. These checks do not certify the historical notebook
suite or a clean cross-platform installation.

## Inspect a known ID

1. Select the `inspect_point_id` timeline and pause playback.
2. Set its current sequence value to an integer canonical ID from 0 through 385.
   This index represents point identity, **not time or reconstruction stage**.
3. The left view retains the full RGB cloud and highlights the inspected point in
   yellow. The four right image views show only that ID's recorded observations,
   projected positions and residual segments.
4. Read the coverage/residual table below the images. The metadata tab exposes
   observation IDs, original image keypoint IDs, activity, provenance, depth,
   creation stage, consistency and final replacement IDs.
5. Click or hover a displayed instance for Rerun's usual inspection details. Read
   the explicit `point_id` and `observation_id` fields; rendered instance indices
   are not canonical IDs. Clicking does **not** change `inspect_point_id`.

Observed markers are large and labeled; projections are smaller and orange.
Observed-marker and residual colors distinguish:

| Status | Color | Meaning |
| --- | --- | --- |
| `active_consistent` | Cyan | Active in the final map, positive depth and error <=3 SIFT px. |
| `active_inconsistent` | Red | Active in the final map but fails that geometric criterion. |
| `inactive_consistent` | Purple | Historical evidence retained after its camera/keypoint mapping was overwritten. |
| `inactive_inconsistent` | Pink | Inactive evidence that also fails consistency; no such rows in this snapshot. |

An empty camera view means **no exported observation for this ID/camera**. It does
not prove occlusion, invisibility or a failed descriptor match. The exporter clears
all overlay children at each ID to prevent markers from a previous ID remaining.
Predictions outside the image are retained, not clamped; pan/zoom may be necessary.
All 12 original photographs remain local; four are embedded because only Views
03-06 have registered cameras. The new recording does not replay reconstruction
stages: the unchanged v0.1 recording remains the stage-based view.

## Data and coordinate conventions

| Canonical file | Available data used here |
| --- | --- |
| `points.npz` | 386 original integer IDs, float32 XYZ, uint8 RGB, birth stage. |
| `cameras.json` | Views 03-06, world-to-camera and inverse poses, both intrinsic matrices, image paths, dimensions and resize factors. |
| `observations.csv` | 897 evidence rows with point/camera/keypoint IDs, observed pixels at both resolutions, provenance, creation stage, final activity and recorded projections/errors. |
| `metrics.csv` | Point-level triangulation angle, depth/baseline, birth residual, association diagnostics, acceptance and rejection reasons. |
| `manifest.json` | Hashes, fixed diagnostic policy, duplicate groups and limitations. |

Projection uses `X_camera = R @ X_world + t`, followed by homogeneous division of
`K @ X_camera`. Camera poses logged to Rerun use the inverse transform, with RDF
axes (+X right, +Y down, +Z forward). No poses are fitted or adjusted.

For each observation the exporter computes:

```text
predicted_sift = project(XYZ, R, t, K_sift)
error_sift_px = norm(predicted_sift - actual_observed_sift)
predicted_original = project(XYZ, R, t, K_original)
error_original_px = norm(predicted_original - actual_observed_original)
```

SIFT uses 900x1200 pixels; original photographs use 1152x1536. The per-axis factor
from original to SIFT is 0.78125, so original-pixel residual magnitudes are 1.28
times the SIFT magnitudes here. Both are exposed; the 3-pixel criterion is always
in SIFT coordinates. Recomputed values are checked against canonical evidence.
The convention is the historical linear pixel scaling, without a newly introduced
half-pixel offset, undistortion or recalibration.

Point-level triangulation acceptance and observation consistency are independent:
an accepted point can have an incorrect propagated association, while a rejected
far point can have a small reprojection error. A low residual is not ground truth.

## Verified examples and counts

| Inspect ID | Evidence | Result |
| --- | --- | --- |
| 0 | Observation 0, View 03, seed keypoint 222 | Active consistent; 0.289086 SIFT px / 0.370030 original px. View 04 has a second consistent seed observation; Views 05/06 have no exported evidence. This is a consistency example, not externally verified ground truth. |
| 162 | Observation 782, View 06, propagated keypoint 0 | Active inconsistent; 540.904487 SIFT px / 692.357744 original px. The bad correspondence is preserved. |
| 62 | Observation 460, View 06, PnP inlier | Active inconsistent under 3 px; 3.462302 SIFT px. Provenance does not certify geometric consistency. |
| 188 | Observation 582, View 05 | Inactive consistent evidence, overwritten by point ID 189 at the same camera/keypoint. |
| 195 and 196 | Separate IDs and distinct observation/keypoint IDs | Identical XYZ positions remain separately inspectable; neither is merged. |

The serialized recording preserves 386 IDs / 364 unique positions, 897 evidence
rows, four original photographs and four camera models. It contains 884 active
consistent rows, 8 active inconsistent rows (7 propagated, 1 PnP) and 5 inactive
consistent rows. There are 649 missing point/camera pairs across the four cameras.
Some point/camera pairs have multiple evidence rows; row count is not pair count.
Final activity and overwrites are known; the full intermediate track history,
discarded matches, unregistered-view observations and ground truth are unavailable.

## Supported interaction and validation limits

The installed 0.42.0 SDK was inspected for `Points2D`, `Points3D`, explicit custom
components, static camera logging, recursive `Clear`, `TimePanel`, four image
views and `RawDataView`. The CLI also reports version 0.42.0. Actual RRD readback
checks IDs, exact XYZ/RGB, selected-point metadata, camera transforms, original
JPEG bytes, intrinsics, overlay coordinates, all observation metadata, duplicate
identity, blueprint content and missing-view clears. Overlay serialization is
float32, so its coordinate tolerance is 1e-4 original pixels.

Matching labels, `keypoint_ids`, or equal XYZ positions do not establish a join
between different Viewer entities. This exporter provides **timeline-coordinated
inspection**, not demonstrated click-to-select synchronization. Rerun documents
selection callbacks for [web/Jupyter integrations](https://rerun.io/docs/howto/visualization/callbacks);
the installed `rerun.notebook.Viewer.on_event` exposes `SelectionChangeEvent`.
A live application could map an observed instance to its explicit canonical ID
and update the time controller, but that bridge is not part of a standalone RRD.

The project owner subsequently reported completing visual inspection on macOS.
That is manual, owner-reported evidence; automated validation covers serialized
data and blueprint content, and the earlier automated file-opening attempt stalled
in its dialog. Windows rendering and interaction are **not verified**. No
synchronized click-selection claim is made. See also the official
[Viewer interaction overview](https://rerun.io/docs/reference/viewer/overview) and
[0.42 release notes](https://rerun.io/docs/changelog/changeset-0-42).

## Windows synchronization and validation (untested on Windows)

Follow [Windows environment setup](setup_windows.md) for a separate local
`.venv-rerun`; never copy the Mac virtual environment. After an explicitly
approved commit/push and updating the Windows checkout, open PowerShell at the
project root. Imports use the existing `src` namespace; each CLI resolves the
repository root from its own file. No CUDA or notebook environment is needed.

Numeric tests need only the committed source and canonical payload:

```powershell
.\.venv-rerun\Scripts\python.exe -B -m unittest discover -s tests -p test_rerun_inspection.py -k ObservationGeometryTests -v
.\.venv-rerun\Scripts\python.exe -B -c "from src.canonical_reconstruction import validate_export; print(validate_export('results/canonical_reconstruction/v1'))"
```

A clone does not contain photographs or recordings. Full image-aware validation
requires all twelve owner-approved original `data/view_*.jpg` files, although four
are embedded in the RRD. Provision these privately with the original relative
paths and bytes; never add them to Git. To regenerate after provisioning:

```powershell
.\.venv-rerun\Scripts\python.exe -B scripts/export_rerun_inspection.py --output results/rerun_reconstruction/v2_windows_01
.\.venv-rerun\Scripts\rerun.exe --bind 127.0.0.1 results/rerun_reconstruction/v2_windows_01/deku_inspection.rrd
.\.venv-rerun\Scripts\python.exe -B scripts/export_rerun_inspection.py --validate-only results/rerun_reconstruction/v2_windows_01/deku_inspection.rrd
```

Use a fresh output directory. Recording tests target the exact private fixture
`results/rerun_reconstruction/v2/deku_inspection.rrd`; they intentionally skip when
it is absent, and do not automatically discover `v2_windows_01`. The explicit
`--validate-only` command checks the newly generated path. Some Rerun regression
tests target the separate v0.1 fixture. A skip is not successful Viewer validation.

The macOS test results do not certify Windows installation, image decoding,
rendering or selection behavior. Preserve canonical hashes and CRLF data; never
regenerate historical manifests to conceal checkout or provenance failures.
