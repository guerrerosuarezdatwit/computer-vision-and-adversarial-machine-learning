# Deku Rerun proof of concept — v1

## Deliverables

- `deku_reconstruction.rrd`: self-contained recording, approximately 3.8 MiB,
  including all 386 original point IDs and the four original registered-camera JPEGs.
- `validation.json`: source hashes, versions, serialized-data readback results,
  test results, observed preservation discrepancies, and scientific limitations.
- `environment.txt`: exact Python, bootstrap pip and runtime package versions.
- `src/rerun_reconstruction.py`: reusable canonical-to-Rerun exporter and validator.
- `scripts/export_rerun_reconstruction.py`: generation and readback command.
- `requirements-rerun.txt`: pinned direct and transitive runtime dependencies.

The recording was generated directly from all five artifacts in
`results/canonical_reconstruction/v1/`. No notebook, SfM reconstruction, SIFT,
PnP, or learned model was executed. No model weights were downloaded. The source
canonical files and all twelve original photographs remain unchanged.

## Environment

The dedicated `.venv-rerun` uses **CPython 3.12.13**, **Rerun SDK 0.42.0**,
**NumPy 2.5.4**, **Pillow 13.0.0** and **PyArrow 26.0.1** on macOS ARM64.
All runtime dependency versions are pinned in the root requirements file.
The notebook `.venv` was not changed: all 55,009 original file sizes and
modification timestamps match the pre-task inventory.

To recreate the separate environment on this machine, using the existing Python
3.12 installation (verify `python3.12 --version` reports 3.12.13):

```bash
python3.12 -m venv .venv-rerun
.venv-rerun/bin/python -m pip install -r requirements-rerun.txt
```

Do not run the installation command with the notebook environment's Python.
On another platform, package wheel availability must be checked separately;
this recording can still be opened in a matching Rerun Viewer without Python.

## Open the recording

From the repository root:

```bash
.venv-rerun/bin/rerun --bind 127.0.0.1 \
  results/rerun_reconstruction/v1/deku_reconstruction.rrd
```

Choose the `stage` timeline and move to **4** for the complete map. Stages 0–2
have 188 points, stage 3 has 301 and stage 4 has 386. The time panel is included
and paused by default. A previously saved Viewer layout can override the default
blueprint; select the recording's default blueprint if needed.

The layout contains:

- A large 3D tab for original RGB and a second 3D tab for green accepted / red
  rejected layers. Layers are separated to avoid rendering duplicate copies of
  the same points over one another in the default view.
- Four camera-image tabs, Views 03–06. View 04 is selected initially because it
  exists from stage 0 and participates in initialization and the first expansion.
- A stage summary/scientific-notes panel and a point-metrics table tab.
- An expanded stage timeline. Open the Selection panel after clicking a point
  to inspect its original `point_id`, angle, errors, rejection reasons and
  `duplicate_ids`. Labels are recorded but not all drawn over the scene.

Cyan pixels are original observations; orange pixels and segments show
reprojections and residuals. Final active propagated associations above 3 SIFT
pixels are marked red. All evidence rows, including five overwritten birth
associations, retain IDs, provenance and final-map activity metadata. These
overlays are hidden in 3D to keep the cloud and camera frustums readable.

Duplicate positions remain distinct point instances. Overlapping instances can
be difficult to pick spatially; the metrics table contains separate entities
for every original point ID. Its rows are birth events across the recording;
they should not be interpreted as a live current-stage count.

## Reproduce and validate

Existing version directories are never overwritten. Choose a new directory:

```bash
.venv-rerun/bin/python -B scripts/export_rerun_reconstruction.py \
  --canonical results/canonical_reconstruction/v1 \
  --output results/rerun_reconstruction/v2

# Read back this existing recording without modifying any artifact.
.venv-rerun/bin/python -B scripts/export_rerun_reconstruction.py \
  --validate-only results/rerun_reconstruction/v1/deku_reconstruction.rrd

# SDK readback tests: no model inference, SfM, or GUI.
.venv-rerun/bin/python -B -m unittest discover -s tests \
  -p 'test_rerun_reconstruction.py' -v

# Official native file-format verification.
.venv-rerun/bin/rerun rrd verify \
  results/rerun_reconstruction/v1/deku_reconstruction.rrd
```

Viewer UI execution is not required for export or numerical validation. New
exports write an initial numerical validation report; the additional test and
UI-attempt notes in this v1 report describe this delivery's verification session.
RRD internal row IDs, timestamps and generated blueprint view IDs may differ on
reproduction even when the scientific content is identical.

## Validation results

The installed SDK's actual constructors and signatures were inspected before
implementation. A small save/readback probe preceded the full recording.
The tests read serialized Arrow batches with `rerun.chunk.RrdReader`, rather
than only checking the Python arrays supplied to the logger.

| Stage | Point IDs | Accepted | Rejected | Cameras |
| --- | ---: | ---: | ---: | --- |
| 0 | 188 | 188 | 0 | 03, 04 |
| 1 | 188 | 188 | 0 | 03, 04, 05 |
| 2 | 188 | 188 | 0 | 03, 04, 05, 06 |
| 3 | 301 | 291 | 10 | 03, 04, 05, 06 |
| 4 | 386 | 376 | 10 | 03, 04, 05, 06 |

- **8/8 Rerun tests passed.** XYZ and RGB survive serialization exactly.
- All 386 original IDs and all 364 distinct XYZ positions remain identifiable.
- All four JPEG byte streams match the source photographs exactly.
- All 897 available observation evidence rows are logged.
- Camera creation stages, camera-to-world direction and intrinsics were checked.
- Serialized float32 camera transforms reproduce canonical projections within
  **0.001 original-resolution pixels**. Geometry is not re-estimated or optimized.
- The classification is recomputed from the recorded diagnostic thresholds and
  checked against CSV decisions: angle ≥2°, birth-pair error ≤3 SIFT px,
  depth ≤10 baselines, association filtering disabled.
- The native verifier reported **1 file verified without error**.
- `pip check` reported no broken requirements in the visualization environment.

### Camera convention and resolution

Canonical poses use `X_camera = R @ X_world + t`. The Rerun camera entity receives
the inverse transform: rotation `R.T`, translation `C = -R.T @ t`, with explicit
`TransformRelation.ParentFromChild`. Both world and camera use right-handed RDF
(X right, Y down, Z forward). No arbitrary visual rotation is applied to the map.

The original 1152×1536 JPEGs are logged without resizing. `Pinhole` therefore
uses `K_original`: focal lengths 1036.8 and principal point (576,768). SIFT used
900×1200, scale 0.78125, with focal lengths 810 and principal point (450,600).
Observed and projected overlays are converted to original pixel coordinates;
error metrics retain their original SIFT-pixel units. No recalibration,
undistortion, or new half-pixel convention is introduced.

### Preservation discrepancies observed during this task

The eight new Rerun tests pass. The historical notebook-environment regression
run had **17 passes, 1 failure and 8 skips** (the new SDK-specific tests correctly
skip in the original environment without Rerun).

The failure is the earlier canonical test comparing every historical file to
its milestone-1 checksum: `notebooks/12_epipolar_geometry.ipynb` already differed
from that checksum at the start of milestone 2. `image_processing.ipynb` from
the earlier reference was also already absent. These pre-existing differences
were not repaired or hidden.

During the task, the checksum of notebook 13 changed relative to the pre-task
inventory. It now has 61 cells; those 61 historical cells still match the preserved
reference. The Rerun exporter and tests contain no notebook-writing operation;
the origin of the observed change is not established. No notebook was reverted.
The before/after hashes are included in `validation.json`.

Canonical v1 and all twelve photographs did not change, and neither did the
original `.venv` file inventory. This recording depends on canonical v1 rather
than the notebook's current editable state.

## What remains incomplete

**Visual inspection is pending.** Native app launch through the computer-use
bridge timed out twice, and the browser access host was unavailable. The RRD
and blueprint were checked structurally and numerically; no claim is made that
the layout has been visually reviewed on screen. Run the open command above to
inspect the scene interactively.

This is a visualization of existing reconstruction results, not evidence that
the SfM reconstruction is correct. Intrinsics are approximate, distortion is
omitted, bundle adjustment is absent, scale is arbitrary, and eight images have
no poses. Low reprojection error does not establish reliable depth.

All known high-error final associations remain documented: point IDs 62, 140,
161, 162, 192, 232 and 295, with a maximum around 540.904 SIFT px. Birth-pair
diagnostic acceptance is intentionally distinct from those association errors.
Evidence appears from its creation stage, but final-map activity is only known
for the final snapshot, not a complete intermediate track history.

The first Research Lab additions should be visual QA, synchronized ID-based
2D/3D selection, a current-stage metrics table, explicit camera/observation
selection, and live threshold controls that generate new diagnostic results.
No such controls, reconstruction changes, model inference, web hosting, or
publication are part of this milestone.

## API references checked

- [Rerun SDK 0.42.0 and Python/platform requirements](https://pypi.org/project/rerun-sdk/0.42.0/)
- [RecordingStream save and RrdReader](https://rerun.io/docs/concepts/logging-and-ingestion/rrd-format)
- [Pinhole and image projection](https://rerun.io/docs/reference/types/archetypes/pinhole)
- [Transform3D](https://rerun.io/docs/reference/types/archetypes/transform3d)
- [DataframeView](https://rerun.io/docs/reference/types/views/dataframe_view)
