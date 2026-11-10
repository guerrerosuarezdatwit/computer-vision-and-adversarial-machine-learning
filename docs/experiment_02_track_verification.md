# Experiment 02: geometric verification of feature-track propagation

## Research question and scope

Does a reprojection gate remove implausible propagated 2D-3D associations while
retaining useful evidence coverage? This first experiment is a **controlled,
propagation-only diagnostic on frozen final poses and 34 recorded proposals**.
It is not an end-to-end SfM result, a ground-truth accuracy evaluation, or a
measurement of improved downstream camera localization or triangulation.

All 386 canonical point IDs, 364 distinct XYZ positions, four camera poses,
photographs and previous recordings remain unchanged. Only experimental decisions
about retaining observation evidence differ. The experiment outputs a new RRD;
rejected evidence stays visible and is never removed from canonical files.

## Verified historical control flow

Cell numbers below are **zero-based indices** in the preserved notebook
`notebooks/13_multiview_3d_reconstruction.ipynb` (61 cells).

| Location | Association creation and checks | Reuse / overwrite behavior |
| --- | --- | --- |
| 18-19 | Seed Views 03-04: Lowe ratio `<0.75`, Essential RANSAC at 1 px, pose mask, finite triangulated XYZ and positive depth in both cameras. | Seed matches define point IDs. Seed geometry has no newly added filter. |
| 29 | `view04_to_3d` maps surviving seed target keypoints to seed point IDs. Descriptor matches 04->05 provide the 3D-2D candidates for PnP. | Dictionary comprehension can collapse repeated target keys; no explicit conflict resolution policy. |
| 30, 34-36 | View 05 uses `solvePnPRansac`, EPNP, 500 iterations, 4 px threshold, confidence 0.999; retained inliers become `view05_to_3d`. | Current-view keypoint dictionary retains one ID per key; overwritten/discarded PnP candidates are not fully exported. |
| 37-38 | View 06 registration follows the same descriptor/PnP pattern from the View 05 seed map. | PnP uses already registered seed associations, before either map expansion. |
| 45 | `view_maps` copies seed and retained PnP dictionaries for Views 03-06; `global_points` starts at 188. | No geometric revalidation of these dictionaries here. |
| 46, propagation loop | `expand_map` recomputes ratio-tested matches. If only one endpoint has a 3D identity, it assigns that ID to the other endpoint. | **No depth, finite-projection, reprojection, mutual-match or source-track consistency check.** It does not overwrite an already mapped target. If both endpoints are mapped, they are left alone even when IDs disagree. Mutations can affect later matches within the same loop. |
| 46, new-point branch | After propagation, matches with both endpoints unmapped are triangulated. Checks: finite XYZ, positive depth in both cameras, and strict `<3` px reprojection error in each image. | `new_matches` is built before any new points are inserted. Many-to-one target matches can both survive, append distinct points, then overwrite the same target key during insertion. No uniqueness gate or point merge exists. |
| 47-48 | Expand 04-05, then 05-06; maps and global points from the first expansion feed the second. | Stage-3 propagation can affect stage-4 source availability, candidate classification, new-point counts and new ID assignment. |

There is **no later PnP call after these propagation loops** in the existing
notebook. The gate proposed here cannot retroactively improve the already computed
View 05/06 PnP estimates. Propagated identities are, however, reused within map
expansion and by the next expansion. A future registration step could consume them.

Distinct mechanisms must remain separate:

- Observation 782 (point 162, View 06) is an unchecked descriptor propagation,
  with 540.904487 SIFT px residual.
- Observation 460 (point 62, View 06) is retained PnP evidence at 3.462302 px.
  It exceeds the diagnostic 3 px criterion but is within the original PnP 4 px
  threshold. This alone is **not evidence that PnP failed or the match is wrong**.
- Five inactive birth observations at View 05 retain overwritten triangulation
  evidence. Their point IDs are 188, 203, 204, 280, 294; their final replacement
  IDs are 189, 205, 206, 281, 295 respectively. Propagation did not directly
  overwrite these already mapped targets; new-point insertion did.

## Experimental design and gate

`src/track_verification.py` loads the numerical payload without photographs or
Rerun. It takes the 34 `descriptor_propagation` evidence rows as a fixed proposal
universe. All 34 are active in the canonical final map. There are 2 stage-3 and
32 stage-4 events; targets span Views 04, 05 and 06 and 32 original point IDs.
Other active evidence (858 associations) is held fixed in every variant.

For target camera coordinates and actual observed SIFT pixels:

```text
X_camera = R_world_to_camera @ X_world + t_world_to_camera
p = K_sift @ X_camera
predicted = p[:2] / p[2]
error = norm(predicted - observed_sift)
gate = finite(X_world, observed_sift, predicted, depth, error)
       and depth > 0 and error <= threshold
```

Thresholds are inclusive: 1, 2, 3 and 5 SIFT-image pixels. The no-gate baseline
does not check geometry, preserving the historical behavior for these proposals.
All real proposals have finite geometry and positive depth; reprojection error
is the only geometric rejection reason observed in this experiment. The target
is checked; source availability and source quality are not replayed or inferred.

The reusable gate returns decisions without modifying points, camera parameters,
candidate inputs or caller maps. Its explicit insertion policy is:

- Existing camera/keypoint identities win; a conflicting new ID is rejected.
- Several new IDs competing for an unmapped target keypoint are all rejected as
  ambiguous, independent of ordering. Geometry is not used to guess identity.
- An exact repeated camera/keypoint/point proposal is rejected after its first
  occurrence. An existing identical association can be reused without insertion.
- Distinct keypoints for the same point in one camera remain allowed and counted.
  Distinct IDs at identical XYZ positions remain separate.

The same identity policy is used by every variant; it changes none of the 34
real proposals. There are **zero duplicate target keys, zero conflicting target
IDs and zero conflicts with the fixed associations** in this proposal universe.
This does not establish that the unexported descriptor matches were conflict-free.
The canonical cloud has 21 duplicate XYZ groups, all retained.

## Results: frozen-pose comparison

Every row evaluates the same 34 proposals. Error summaries below describe only
the kept propagated associations, in **SIFT pixels**.

| Variant | Proposed | Kept | Rejected | Mean | Median | P95 | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No gate | 34 | 34 | 0 | 35.364659 | 1.461491 | 233.105360 | 540.904487 |
| <=1 px | 34 | 9 | 25 | 0.728316 | 0.835573 | 0.978370 | 0.996254 |
| <=2 px | 34 | 23 | 11 | 1.196175 | 1.214615 | 1.920785 | 1.947198 |
| <=3 px | 34 | 27 | 7 | 1.353530 | 1.375302 | 2.295646 | 2.366591 |
| <=5 px | 34 | 28 | 6 | 1.418899 | 1.395549 | 2.350913 | 3.183862 |

The proposed distribution is identical across rows. Full min/median/mean/P95/max
distributions for proposed, kept and rejected subsets are in `comparison.json`.

Coverage below combines kept proposals with fixed active non-propagation evidence.
It describes **retained evidence on an unchanged map**, not recovered map quality.
All rows retain 386 point IDs and cameras 03-06; 381 points have evidence in at
least two distinct cameras, unchanged across these variants. Five points already
lacked two active-camera observations in the baseline after historical overwrites.

| Variant | Kept proposal point IDs | Kept proposal cameras | Total active associations | Points with >=3 cameras | Active residuals >3 px |
| --- | ---: | --- | ---: | ---: | ---: |
| No gate | 32 | 04,05,06 | 892 | 100 | 8 |
| <=1 px | 9 | 06 | 867 | 79 | 1 |
| <=2 px | 22 | 05,06 | 881 | 92 | 1 |
| <=3 px | 26 | 05,06 | 885 | 96 | 1 |
| <=5 px | 27 | 05,06 | 886 | 97 | 2 |

The final baseline has two point/camera pairs with multiple keypoints; at 1, 2,
3, 5 px the retained counts of such pairs are 0, 1, 1, 1. These are not conflicting
camera/keypoint identities and are not silently deduplicated. All five inactive
rows remain historical evidence and are excluded from the active-coverage count.

At 3 px the gate rejects seven propagation rows, including the documented severe
case, and keeps all 27 propagation rows consistent with that reference criterion.
At 1 px it additionally rejects 18 proposals with errors <=3 px; at 2 px it rejects
four such proposals. They might be useful, but there is no ground truth proving
their identity. At 5 px, observation 811 (point 295, View 06, 3.183862 px) remains.
Observation 460 is outside propagation and remains in every variant.

Removing high residuals with a residual threshold necessarily lowers the retained
residual distribution. This is a filter sanity check and a coverage tradeoff,
not independent evidence of more accurate geometry or descriptor identities.

## Interactive recording and verified examples

Outputs are local and ignored under `results/experiments/02_track_verification/v1/`:

```text
comparison.json          complete numerical report and limitations
comparison.csv           compact threshold table
decisions.csv            170 decisions, preserving canonical observation/point IDs
track_verification.rrd   private Rerun recording with four original photographs
validation.json          recording checksums, numerical-source hashes and SDK versions
```

The recording keeps the full RGB map, shows green/red 3D proposal markers, and
opens a camera comparison layout. Choose `gate_variant` sequence values:

```text
0 = no gate     1 = 1 px     2 = 2 px     3 = 3 px     4 = 5 px
```

The camera tabs contain the cyan baseline on the left and kept green / rejected
red evidence on the right. Small orange points are actual camera projections;
segments join the observed and predicted locations. Labels are available in the
Selection panel; explicit `point_id` / `observation_id` fields are authoritative,
not subset instance indices. All 34 decisions, residuals and rejection reasons
appear in the metadata tab. Clicking does not synchronize different entities.
No pixel coordinates or point positions are clamped, corrected or merged.

| Example | Expected comparison |
| --- | --- |
| Point 162 / View 06 / obs 782 | 540.904487 SIFT px; kept by baseline, rejected by all four gates. Observed original pixel is near (15.301,743.130), while its prediction is near (589.416,1130.108). |
| Point 278 / View 06 / obs 810 | 0.354187 SIFT px; kept by every variant. This is a low-residual consistency example, not verified ground truth. |

Images use original 1152x1536 coordinates; K_sift and observed SIFT pixels use
900x1200. Per-axis scaling is 0.78125, so displayed residual lengths are 1.28
times their SIFT-pixel magnitudes. Original camera-to-world transforms, RDF axes,
image bytes and scaled pinhole intrinsics are preserved.

Actual RRD readback verifies the RGB cloud, camera transforms and image bytes,
all 170 serialized policy decisions, 2D observations/projections/residual segments,
original IDs, 3D decision positions and metadata. Per-variant recursive clears
prevent stale accepted/rejected markers. Blueprint content is tested. The project
owner subsequently reported completing visual inspection on macOS; this is manual
evidence, separate from automated readback. Windows rendering and interaction
remain untested.

## Reproduction and validation

Use the existing separate visualization environment; no new dependencies:

```bash
.venv-rerun/bin/python -B scripts/run_track_verification_experiment.py
.venv-rerun/bin/rerun --bind 127.0.0.1 \
  results/experiments/02_track_verification/v1/track_verification.rrd
.venv-rerun/bin/python -B -m unittest discover -s tests -p 'test_*track*.py' -v
```

Existing output directories are refused. For a repeat use a fresh version path
with `--output`. Numerical-only reproduction needs just NumPy, not photos/Rerun:

```bash
.venv/bin/python -B scripts/run_track_verification_experiment.py \
  --no-rerun --output results/experiments/02_track_verification/numeric_repeat_01
.venv/bin/python -B -m unittest discover -s tests -p test_track_verification.py -v
```

The 18 experiment tests cover known residuals and coverage, finite/depth gates,
inclusive boundaries, ambiguous IDs, existing-map conflicts, duplicate proposals,
duplicate XYZ identities, immutability, overwrite refusal and actual RRD readback.
These tests are separate from the known historical full-suite checksum failures.

### Windows PowerShell (installation and runtime not yet validated)

Use the dedicated Windows environment described in [setup_windows.md](setup_windows.md),
not a copied Mac environment. From the updated checkout's project root:

```powershell
.\.venv-rerun\Scripts\python.exe -B -m unittest discover -s tests -p test_track_verification.py -v
.\.venv-rerun\Scripts\python.exe -B scripts/run_track_verification_experiment.py --no-rerun --output results/experiments/02_track_verification/windows_numeric_01
```

These numerical operations need no photographs, model weights, CUDA or notebooks.
The new CLI modules establish the repository import path using `Path(__file__)`.
The `src` directory uses Python namespace-package imports; no editable install or
new packaging dependency is required. Run test discovery from the repository root.

After privately provisioning all twelve owner-approved original photographs under
their existing relative paths, the existing SDK can generate a new local recording:

```powershell
.\.venv-rerun\Scripts\python.exe -B scripts/run_track_verification_experiment.py --output results/experiments/02_track_verification/windows_rrd_01
.\.venv-rerun\Scripts\rerun.exe --bind 127.0.0.1 results/experiments/02_track_verification/windows_rrd_01/track_verification.rrd
```

Generation performs RRD readback validation. Choose fresh directories; all these
outputs remain ignored by Git. `test_rerun_track_experiment.py` uses the exact local
fixture `results/experiments/02_track_verification/v1/track_verification.rrd` and
skips when it is absent. It does not automatically target `windows_rrd_01`.
The source-hash comparison in that test records exporter provenance; an LF/CRLF
conversion or local source edit can make it fail even when numerical validation
succeeds. Source files use LF via `.gitattributes`; frozen payloads use `-text`.
The saved comparison report is also compared exactly with a recomputation; these
tests have not established numerical equality across Mac and Windows CPUs.
Record any mismatch rather than rewriting historical validation reports.

### Known historical test status

The existing notebook-environment canonical suite has a known provenance-check
failure: notebooks 12 and 13 differ from the manifest's historical checksums, and
the referenced `notebooks/image_processing.ipynb` is absent. The test stops at its
first mismatch (notebook 12). This is separate from successful canonical payload
validation and from these new experiment tests. The references remain frozen.
The excluded notebook history and private inputs are not prerequisites for the
portable numerical tests. Missing recordings produce skips, not evidence that
recording generation or Viewer behavior passed on Windows.

The macOS synchronization review passed all 11 v0.2 tests, all 18 Experiment 02
tests, and the eight existing v0.1 Rerun regression tests. The existing canonical
suite passed 10 of 11 tests, with the historical checksum failure described above.
A temporary source-only copy (first-commit files plus this proposal, with no
photographs, notebooks, environments or RRDs copied) loaded all new modules and
both guarded CLIs, validated the canonical payload, and ran the 29 new tests:
20 passed and nine private-recording tests were skipped. The interpreter and
installed dependencies were reused from the local Mac environment. This is
source-only validation on macOS, not an actual Windows installation or checkout.

## End-to-end status and next experiment

**No PnP or triangulation was rerun; no end-to-end A/B result is claimed.** The
existing canonical reproduction runner requires complete notebook-cell equality
with its backup. That guard currently fails: sources match but saved cell state
and outputs differ. The notebook has no explicit RNG seeding, and deterministic
replay has not been demonstrated here. We did not relax its guard, normalize
historical notebooks, or execute the older diagnostic runner that writes them.
This is not a claim that safe replay is impossible; it remains unverified.

The canonical exporter sorts events after capture, so observation IDs do not
encode within-stage match order. Point 161 illustrates a cross-stage dependency:
obs 581 creates a View 05 association in stage 3, used as source by obs 781 in
stage 4. Point 261 illustrates a same-stage dependency: obs 804 propagates from
View 05 keypoint 853 to View 06 keypoint 1048, then obs 695 propagates back to a
different View 05 keypoint 862. Sorted observation IDs reverse that causal order.
This experiment deliberately does not simulate source-availability cascades.

The recommended next experiment is an **expansion replay from a frozen checkpoint
immediately before cell 46**, keeping PnP poses fixed initially:

1. Export SIFT keypoints/descriptors, seed XYZ/RGB, all four registered poses and
   the pre-expansion maps. Preserve match iteration order and source dependencies.
2. Run the unmodified expansion twice, requiring agreement with the canonical
   386-point baseline and birth observations before evaluating variants.
3. Apply no gate versus a 3 px gate at insertion, before each subsequent map
   operation. Keep 2 px as a stricter ablation; the current evidence does not
   establish that any threshold is optimal.
4. Track new-point correspondence by birth camera/keypoint pairs, not new array
   indices or equal XYZ, because rejected propagations can change triangulation
   candidates and new ID assignment. Record all conflicts and rejected matches.
5. Measure downstream triangulation counts, track lengths, multi-view residuals
   and degenerate geometry. Evaluate PnP only after adding a genuine later camera
   registration stage that actually consumes the modified map.

Approximate intrinsics, absent distortion correction/bundle adjustment, incomplete
track history, a single scene and no ground truth limit the conclusions. A gate
can reject correctly identified features when geometry/calibration is inaccurate,
or accept a wrong identity near its predicted projection. Threshold selection on
these same final poses is not an independent generalization evaluation.
