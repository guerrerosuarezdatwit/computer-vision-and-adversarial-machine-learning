# Portfolio case study: diagnosing a sparse 3D reconstruction

## Project summary

Adversarial Vision combines a Computer Vision and Adversarial ML learning
curriculum with an emerging research-engineering workflow. Its current featured
experiment reconstructs a Deku figurine from a small photo sequence, preserves
the result in a documented canonical format, and exports it to Rerun for inspection.

The work emphasizes measurable failure analysis: a visually plausible point cloud
and a low reprojection error do not establish accurate geometry.

## Engineering work demonstrated

- Connected SIFT matching, Essential Matrix pose recovery, triangulation and PnP
  into an inspectable sparse reconstruction experiment.
- Preserved original IDs, RGB, coordinate conventions, reconstruction chronology
  and 2D observation provenance in versioned numerical artifacts.
- Compared triangulation angle, camera depth and reprojection error without
  silently deleting duplicates or rejected points.
- Built a separate, pinned Rerun visualization stack reading canonical artifacts
  directly, with camera-image views, diagnostic layers, timeline and metrics.
- Verified the serialized recording's point IDs, exact XYZ/RGB, original JPEG
  bytes, camera conventions and projection consistency through SDK readback tests.

## Evidence and findings

| Evidence | Result |
| --- | ---: |
| Original photographs analyzed | 12 |
| Registered cameras | 4 |
| Original point IDs / distinct XYZ positions | 386 / 364 |
| Diagnostic accepted / rejected IDs | 376 / 10 |
| Available observation evidence / final associations | 897 / 892 |
| Final associations above 3 SIFT px, measured by affected point IDs | 7 |
| Rerun SDK readback tests in milestone 2 | 8 passed |

The 10 diagnostic rejections have birth-pair errors below 1.174 pixels, despite
their problematic depth/angle behavior under the exploratory policy. Two have
an effective triangulation angle around 1.708 degrees. Separately, some propagated
associations have errors up to approximately 540.904 SIFT pixels. Keeping birth
geometry and later association quality distinct prevents a misleading single
"reconstruction quality" number.

The source's `point_birth` metadata had 188 entries for a 386-ID map. The canonical
export derives stages from actual insertion-ID lists and records that discrepancy,
while retaining five birth observations overwritten by final dictionaries.

## Concise portfolio description

> Developed a sparse multi-view reconstruction diagnostic prototype combining
> classical Computer Vision, provenance-preserving canonical exports and Rerun.
> Preserved 386 original point IDs across five reconstruction stages, identified
> duplicate positions and inconsistent associations, and validated serialized
> geometry, colors and camera projections with eight SDK readback tests.

This describes an educational research prototype, not a published benchmark,
production deployment, novel SfM algorithm or completed research paper.

## Presentation plan

After privacy and rights clearance, a short demonstration should show camera
registration/map growth, RGB versus accepted/rejected geometry, and an individual
point with small reprojection error but weak triangulation geometry. A second
figure should explain a high-error propagated association and its provenance.

Numerical diagnostic plots and the connectivity heatmap are stronger evidence
than an unannotated point-cloud screenshot. Raw workspace photos and a full desktop
recording require review before public use. No video or new portfolio figure has
been generated in milestone 3.

## Scientific boundaries and next work

Intrinsics are approximate; there is no bundle adjustment, modeled lens distortion,
metric scale or ground-truth 3D accuracy measurement. Eight views remain
unregistered. Filters are exploratory and fixed in the current Rerun recording.
Most adversarial notebooks are single-image experiments and do not support broad
robustness claims. Full-curriculum reproducibility is still work in progress.

Next work should improve synchronized ID-based inspection, track validation,
camera coverage, fresh-environment reproduction and controlled evaluation. VGGT,
3D Gaussian Splatting and adversarial 3D experiments remain future directions.

References: [canonical schema](../results/canonical_reconstruction/v1/README.md),
[Rerun evidence](../results/rerun_reconstruction/v1/validation.json),
[environments](ENVIRONMENTS.md), and [release review](RELEASE_REVIEW.md).
