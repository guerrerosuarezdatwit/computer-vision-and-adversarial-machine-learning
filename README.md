# Adversarial Vision

**An educational Computer Vision and Adversarial Machine Learning project evolving
into an Interactive 3D Reconstruction Research Lab.**

The project investigates how visual predictions and reconstructed geometry fail,
how to measure those failures, and how to preserve experiments so they can be
inspected independently. Its current research-engineering focus is a sparse
multi-view reconstruction of a Deku figurine, exported into a portable format
and explored with a Rerun proof of concept.

## Current status

| Component | Evidence and scope |
| --- | --- |
| Educational notebooks 01–13 | Preserved locally; excluded from the initial source-only selection pending individual privacy review. The entire curriculum is **not** certified reproducible. |
| Canonical reconstruction v1 | Validated snapshot with 386 original point IDs, four registered cameras, RGB, observations, provenance and geometric metrics. |
| Rerun prototype v1 | Recording with exact source XYZ/RGB, original camera images, diagnostic layers and a five-stage timeline; eight SDK readback tests passed in milestone 2. |
| Visual experience | Working prototype reported by the project owner; automated on-screen review was unavailable during milestone 2. |
| GitHub foundation | The first local foundation commit exists and an `origin` remote is configured. The next implementation changes are under review; no Windows runtime certification, CI badge or release is implied. |

The project owner reports an existing **private** GitHub repository for sharing
development between an M1 Pro Mac (MPS) and a Windows RTX 4060 computer (CUDA).
The second-commit staging proposal covers Research Lab v0.2 and Experiment 02;
staging, committing and pushing remain separate approval steps. Local review
does not independently verify GitHub visibility or remote branch contents. See
the [private-repository checklist](docs/github_publication_checklist.md).

Start with [macOS setup](docs/setup_macos.md), [Windows setup](docs/setup_windows.md),
[the two-computer workflow](docs/development_workflow.md), and
[dependency strategy](docs/dependency_strategy.md). Existing
[environment evidence](docs/ENVIRONMENTS.md), the
[public-release checklist](docs/PUBLICATION_CHECKLIST.md), and the
[privacy/large-file review](docs/RELEASE_REVIEW.md) remain available.

Fresh installation recipes are explicitly untested. The optional
`src.device_selection.select_device` helper is for new experiments only; historical
notebooks keep their original device choices and behavior.

## Technical scope

- **Adversarial ML:** FGSM, untargeted and targeted PGD, cross-model
  transferability, adversarial patches, Expectation Over Transformation and CLIP.
- **Visual perception:** object detection, occlusion sensitivity, semantic and
  instance segmentation, promptable segmentation, and relative monocular depth.
- **Classical 3D vision:** camera geometry, SIFT, geometric matching, Fundamental
  and Essential matrices, pose recovery, triangulation, PnP and sparse map expansion.
- **Research engineering:** explicit coordinate conventions, immutable versioned
  snapshots, association provenance, anomaly reporting, tests and Rerun export.

## Notebook curriculum

These learning experiments are preserved in the original local workspace and
are intentionally absent from the initial source-only selection. The identifiers
below describe that local curriculum; they are not download links. Each notebook
requires individual privacy and embedded-output review before inclusion. Status
reflects code inspection and recorded evidence, not a clean-kernel reproduction.

| Notebook | Topic | Current qualification |
| --- | --- | --- |
| 01 | FGSM | Missing image references and saved CPU/MPS errors. |
| 02 | PGD, targeted attacks, quantization | Developed experiment; fresh end-to-end execution still unverified. |
| 03 | Transferability across CNNs and ViT | Variable use before definition in cell order. |
| 04 | Patches and EOT | Developed single-image study with paired comparisons; broader generalization untested. |
| 05 | CLIP and embedding-space attacks | Missing variable definitions and an indentation issue. |
| 06 | YOLO, occlusion and localized attacks | RGB/BGR consistency in attack evaluation needs correction. |
| 07 | Semantic, instance and promptable segmentation | Exploratory execution order and image/prompt coordinate consistency need review. |
| 08 | Relative depth with object-level analysis | Relative predictions, not metric depth or ground-truth validation. |
| 09 | Camera and stereo geometry | Synthetic teaching examples; not a noisy-data benchmark. |
| 10 | Synthetic point clouds | Known-geometry reconstruction example. |
| 11 | SIFT and homography verification | Synthetic transformed-image experiment. |
| 12 | Two-view reconstruction | Essential/pose-mask continuity needs review; file differs from milestone-1 checksum. |
| 13 | Multi-view sparse reconstruction | Four-camera experiment; canonical snapshot is the portable reference. |

Notebook 13 currently has 61 historical cells. The standalone Plotly diagnostics
and their Python module remain available, but the previously appended diagnostic
section is absent. The older diagnostic runner depends on that section and is
not presented as a working regeneration command for the current notebook.

## Featured experiment: investigating a sparse 3D reconstruction

Twelve original photographs were analyzed. Views 03–04 initialize the map;
Views 05 and 06 are localized with PnP, followed by two map expansions.

| Finding | Preserved result |
| --- | ---: |
| Original point IDs | 386 |
| Distinct XYZ positions | 364 |
| Registered cameras | 4 of 12 |
| Accepted / rejected under the recorded diagnostic policy | 376 / 10 |
| Observation evidence rows / final associations | 897 / 892 |
| Points with a final association above 3 SIFT pixels | 7 |

The ten diagnostic rejections have birth-pair reprojection errors below 1.174 px.
They demonstrate why a small image-space error can coexist with weak depth
geometry. Duplicate positions, overwritten associations and high-error propagated
matches are retained as evidence rather than silently repaired.

The recorded exploratory policy requires positive depth, effective triangulation
angle at least 2°, maximum birth-pair error at most 3 SIFT pixels, and depth at
most 10 birth-pair baselines. Association filtering is disabled in that policy.
These thresholds define an investigation, not ground truth or calibrated uncertainty.

The Rerun timeline preserves the actual notebook chronology:

```text
stage 0: seed 03–04          188 IDs, 2 cameras
stage 1: register View 05   188 IDs, 3 cameras
stage 2: register View 06   188 IDs, 4 cameras
stage 3: expand 04–05       301 IDs, 4 cameras
stage 4: expand 05–06       386 IDs, 4 cameras
```

Read the [portfolio case study](docs/PORTFOLIO.md),
[canonical schema](results/canonical_reconstruction/v1/README.md), and
[Rerun reproduction guide](results/rerun_reconstruction/v1/README.md).

The [Research Lab v0.2 inspection guide](docs/rerun_inspection_v02.md) describes
the new ID-indexed 2D/3D recording, observed-versus-projected markers, final-map
association status, verified residual examples and interaction limitations.
Its private generated recording is separate from the preserved v0.1 artifact.
The [Experiment 02 report](docs/experiment_02_track_verification.md) compares
propagation verification thresholds on frozen final poses. The owner reports
visual inspection of both developments on macOS; Windows runtime/rendering and
controlled incremental SfM replay remain future validation work.

## Explore the local Rerun prototype

Run commands **from the project root**, the directory containing this README.
The following macOS command assumes the dedicated environment and local recording
already exist:

```bash
.venv-rerun/bin/rerun --bind 127.0.0.1 \
  results/rerun_reconstruction/v1/deku_reconstruction.rrd
```

Windows PowerShell, after a separate local installation and approved artifact transfer:

```powershell
.\.venv-rerun\Scripts\rerun.exe --bind 127.0.0.1 results/rerun_reconstruction/v1/deku_reconstruction.rrd
```

Choose `stage` and move to 4. The layout contains original-RGB and diagnostic
3D tabs, four camera-image tabs, a timeline, scientific notes and a metrics table.
No reconstruction or model inference is needed to open the recording.

The `.rrd` embeds original photographs and is intentionally ignored by Git pending
release review. It will not be present in a source-only checkout. The original
photographs, image assets and model weights are also kept local by default.
No public download is claimed to exist yet.

For a payload-only numerical check that does not require source photographs,
use an environment with NumPy (such as the existing visualization environment):

```bash
.venv-rerun/bin/python -B -c "from src.canonical_reconstruction import validate_export; print(validate_export('results/canonical_reconstruction/v1'))"
```

This checks the canonical payload, not external-image availability or a fresh
notebook run. [Environment documentation](docs/ENVIRONMENTS.md) separates these
verification levels and gives setup/export commands with their prerequisites.

### Portable validation versus historical reproduction

The source-only selection includes the canonical payload and its validator.
With NumPy installed, the command above checks payload SHA-256 hashes, point IDs,
camera transformations, recorded image-size/intrinsics scaling, associations and
cross-file metrics without photographs, notebooks, PyTorch or Rerun. The preserved
reference contains 386 points, 364 unique positions, four cameras, 897 observation
rows, 892 final associations and 376 diagnostically accepted points. Validation
checks internal consistency; it does not establish geometric accuracy or verify
the dimensions/content of photographs that are absent.

Historical checks have different prerequisites and known failures:

- In the existing notebook environment, the first-commit review ran 11 canonical
  tests: 10 passed and the historical-file checksum test failed. Notebooks 12 and
  13 differ from their frozen manifest references, and the referenced
  `notebooks/image_processing.ipynb` is absent. Those provenance references remain
  unchanged; the canonical payload hashes still validate.
- A source-only copy cannot run the full historical suite unchanged. Image-aware
  validation needs local photographs; the provenance test needs excluded historical
  files. The overwrite-protection test also expects the original project `.venv`
  and fails at that environment guard in a copy without it.
- Regenerating SfM and exporting image-bearing Rerun recordings require private
  local inputs and their documented environments. They are separate from portable
  payload validation and are not claimed to work from a source-only checkout.

Do not interpret a historical-suite failure as payload corruption, or a successful
payload check as a successful notebook reproduction. Neither notebooks nor frozen
research artifacts have been rewritten to make these checks pass.

## Repository layout

```text
notebooks/    preserved locally; excluded pending individual review
src/          canonical export, diagnostics and Rerun helpers
scripts/      export and validation entry points
tests/        geometry, canonical and Rerun readback tests
docs/         setup, release review, checklist and portfolio case study
data/         original multiview photographs (local; ignored)
assets/       educational image assets (local; ignored)
results/      local experiment history plus selected reference artifacts
```

## Scientific and reproducibility limitations

The reconstruction uses approximate shared intrinsics, omits lens distortion
and bundle adjustment, and has arbitrary monocular scale. Eight images have no
estimated pose. A visualization does not establish that recovered geometry is
correct. Most adversarial experiments use a single image; transform success rates
on that image do not measure generalization across images.

There are two deliberately separate environment roles: notebooks and visualization.
The preserved Mac notebook baseline is Python 3.10.5 with NumPy 1.26.4; visualization
uses Python 3.12.13 with Rerun 0.42.0 and NumPy 2.5.4. New notebook development has
a proposed Python 3.12 candidate with a platform-specific torch installation;
the existing Mac `.venv` is not upgraded or copied to Windows. Windows CUDA and
Rerun runtime validation remain pending. The notebook dependency files are observed
or candidate direct pins, not validated portable lockfiles.
The historical full test suite is not completely green; its checksum failure is
documented rather than hidden. See [environment and test status](docs/ENVIRONMENTS.md).

## Direction and release status

Next research steps are synchronized point-ID inspection, configurable geometric
diagnostics, better track validation and broader camera registration. VGGT,
3D Gaussian Splatting and adversarial 3D experiments are future work, not current
implemented results.

Code-license selection, image provenance/permissions and notebook-output privacy
review remain open. No project-wide license or third-party redistribution rights
are implied. See [the private first-commit gates](docs/github_publication_checklist.md)
and the separate [public-release gates](docs/PUBLICATION_CHECKLIST.md).
