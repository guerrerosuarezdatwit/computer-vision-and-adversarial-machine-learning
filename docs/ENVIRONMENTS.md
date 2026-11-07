# Environments, setup and verification

Run commands from the repository root. Keep the notebook and visualization
environments separate; never install the Rerun requirements into `.venv`.
No packages were installed or upgraded in milestone 3.

The **2026-11-07 cross-platform follow-up** adds [macOS](setup_macos.md) and
[Windows](setup_windows.md) recipes, [dependency strategy](dependency_strategy.md),
and a [private Git workflow](development_workflow.md). The observed records below
remain the historical Mac evidence; do not reuse the entire Mac environment on
Windows. New notebook development proposes a separate Python 3.12 candidate and
a platform-specific torch install. Those fresh setups remain untested.

## Verification levels

| Level | Verified status | What it does not establish |
| --- | --- | --- |
| Existing canonical payload | Validated again in milestone 3. | Full notebook execution, image rights or metric 3D accuracy. |
| Existing canonical + local images | Validated again with the existing notebook environment. | A fresh installation or all 12 registered poses. |
| Existing RRD readback | Validated again in milestone 3 with the visualization SDK. | Independent on-screen QA or live threshold recomputation. |
| Rerun setup | Separate environment installed successfully in milestone 2; exact versions recorded. | Portability to every OS or Python version. |
| Fresh setup from pinned files | Instructions prepared; not reinstalled or tested in milestone 3. | Clean-machine reproducibility. |
| Complete notebook curriculum | Not validated; known failures remain. | Do not advertise Restart Kernel / Run All for all notebooks. |

## Notebook environment

The existing `.venv` uses CPython **3.10.5** on macOS ARM64. Observed direct
dependencies are in [requirements-notebooks.observed.txt](../requirements-notebooks.observed.txt).
This is a descriptive snapshot, not a full transitive lockfile. Some notebooks
download weights on first use and depend on files that are not distributed yet.

### Existing local environment

```bash
.venv/bin/python --version
.venv/bin/python -m pip check
.venv/bin/python -m jupyter lab
```

Select the notebook environment's kernel and use each notebook's working-directory
assumptions (usually `notebooks/`). Missing `frog.jpg` and `penguin.jpeg`, stateful
cells, device mismatches, coordinate issues and API/preprocessing concerns still
prevent treating the whole curriculum as a reproducible package.

### Proposed clean setup — NOT VALIDATED

Do not replace the preserved `.venv` to test a recipe. A future validation should
use a disposable environment and the same Python baseline:

```bash
python3.10 -m venv .venv-notebooks-validation
.venv-notebooks-validation/bin/python -m pip install \
  -r requirements-notebooks.observed.txt
```

Confirm Python reports 3.10.5, then validate actual wheel compatibility,
transitive versions, downloads and datasets. Accelerator availability and CPU/MPS/
CUDA behavior need separate checks. Do not add a successful-setup claim until
this exercise has been completed. No full notebook lockfile is supplied yet.

## Visualization environment

The existing `.venv-rerun` uses CPython **3.12.13** on macOS ARM64 with:

| Dependency | Pinned version |
| --- | --- |
| rerun-sdk | 0.42.0 |
| numpy | 2.5.4 |
| pillow | 13.0.0 |
| pyarrow | 26.0.1 |
| attrs | 26.1.0 |
| psutil | 7.2.2 |
| typing_extensions | 4.16.0 |

[requirements-rerun.txt](../requirements-rerun.txt) pins these runtime versions.
The milestone-2 [environment record](../results/rerun_reconstruction/v1/environment.txt)
also records Python and bootstrap pip. Rerun 0.42.0 requires Python >=3.11;
the project uses the verified 3.12.13 baseline rather than upgrading notebooks.
See the [SDK package metadata](https://pypi.org/project/rerun-sdk/0.42.0/).

### Fresh visualization setup recipe

Only run environment creation when the target directory does not exist:

```bash
python3.12 --version
python3.12 -m venv .venv-rerun
.venv-rerun/bin/python -m pip install -r requirements-rerun.txt
.venv-rerun/bin/python -m pip check
```

Use Python 3.12.13 for the recorded baseline. The existing environment and export
were verified; installing this pinned file again on a fresh machine remains a
separate portability check. No PyTorch, OpenCV, model download or notebook
execution is required for the Rerun exporter.

## Validation, tests and regeneration

### Payload-only validation: usable without original photos

```bash
.venv-rerun/bin/python -B -c "from src.canonical_reconstruction import validate_export; print(validate_export('results/canonical_reconstruction/v1'))"
```

This validates checksums, schemas, poses, scaling, associations and metric
consistency inside the export. Image hashes/dimensions are checked only when
the optional repository root is supplied to `validate_export`.

### Full local validation: requires original photographs

```bash
.venv/bin/python -B scripts/export_canonical_reconstruction.py \
  --validate-only results/canonical_reconstruction/v1

.venv-rerun/bin/python -B scripts/export_rerun_reconstruction.py \
  --validate-only results/rerun_reconstruction/v1/deku_reconstruction.rrd

.venv-rerun/bin/python -B -m unittest discover -s tests \
  -p 'test_rerun_reconstruction.py' -v
```

Rerun tests require the locally ignored recording and source images. Milestone 2
recorded eight passes; this milestone revalidated the existing RRD without claiming
a new full-suite run. The original Python suite previously recorded 17 passes,
one historical-file checksum failure and eight SDK-specific skips. The earlier
reference included a different notebook 12 hash, a 66-cell notebook 13, and the
now-absent `image_processing.ipynb`. Canonical v1 retains that history unchanged.

`tests/test_triangulation_dashboard.mjs` additionally needs Node.js, which was
not available in the terminal PATH at the last check. No Node dependency was
installed. Its earlier validation used a JavaScript runtime and DOM/Plotly test
doubles, not browser rendering.

### Generate another RRD: requires approved/local source photos

```bash
.venv-rerun/bin/python -B scripts/export_rerun_reconstruction.py \
  --output results/rerun_reconstruction/v2
```

Use a fresh version directory; exporters refuse existing versions. Canonical
regeneration additionally requires the ignored frozen notebook backup and original
notebook dependencies, and repeats the classical pipeline. It is not needed for
viewing the existing RRD or checking the canonical numerical payload.

The current 61-cell notebook 13 lacks the previously appended diagnostics section.
`scripts/run_triangulation_diagnostics.py` expects variables created by that
section and is not a verified regeneration route in its current state. Do not
rewrite notebooks or frozen artifacts simply to hide that dependency.

## Data, weights and publication prerequisites

No public dataset URL or automated weight-download script is supplied. Original
photos and educational assets are excluded pending ownership, privacy and license
review. The current RRD embeds four of those photos. Existing `sam_b.pt` and
`yolo11n.pt` copies remain local and ignored. Torchvision/Hugging Face models may
also exist outside the repository in user caches; those caches are not a dataset
or a reproducible model manifest.

Before a clean-checkout reproduction claim, document authorized image sources,
exact model/checkpoint identities, licenses, hashes, availability and the intended
download method. Existing local files are not evidence of permission to redistribute.
