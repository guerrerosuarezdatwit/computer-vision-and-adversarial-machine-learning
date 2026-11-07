# Windows x86-64 setup: RTX 4060 / CUDA

Status: **2026-11-07 — ALL Windows installation, GPU and Viewer steps are untested
on the target ASUS ROG Strix G17.** Official wheel availability and install
commands were checked, but that is not a successful machine-level installation.
No dependencies were installed in this task.

## 1. Clone only after the private repository exists

Use 64-bit Windows, Git for Windows, VS Code, and an authorized CPython 3.12 x64
installation. Check the installed Python patch and architecture; Mac 3.12.13 is
an observed baseline, not a claim that an identical Windows installer is available.
Obtain tools from [Git for Windows](https://gitforwindows.org/),
[Python's Windows downloads](https://www.python.org/downloads/windows/), and
[VS Code](https://code.visualstudio.com/). GPU driver provisioning should use the
appropriate ASUS/NVIDIA source; it is not performed by the Python commands here.
Replace `OWNER` after the reviewed private repository has been populated:

```powershell
git clone https://github.com/OWNER/adversarial-vision.git
Set-Location adversarial-vision
py -3.12 -c "import platform, sys; print(sys.version); print(platform.machine())"
```

Use Git Credential Manager/browser authentication or a device-specific SSH key.
Never put a token in the clone URL or copy Mac credential files onto Windows.
Do not clone over another working copy. Do not copy `.venv` or `.venv-rerun` from
macOS: interpreters, native wheels, executables and paths are platform-specific.

Commands below use PowerShell and explicit interpreter paths. Activation is not
required, so there is no need to relax PowerShell execution policy. Examples use
single command lines rather than Bash backslash continuations.

## 2. Check the NVIDIA driver

```powershell
nvidia-smi
```

Confirm the actual GPU and driver reported by the machine. The `CUDA Version`
shown there is driver capability, not proof that a CUDA-enabled torch wheel is
installed. The driver must support the selected CUDA 12.6 runtime. If the check
fails, stop the GPU setup and resolve the driver/build combination; do not assume
an installed CUDA toolkit will fix a CPU torch wheel. Do not install a guessed
second toolkit as part of this recipe. Custom CUDA extensions may need separate
compiler/toolkit requirements in later VGGT or Gaussian Splatting work.

## 3. Candidate CUDA notebook environment

Create `.venv-notebooks` only when it does not exist:

```powershell
py -3.12 -m venv .venv-notebooks
.\.venv-notebooks\Scripts\python.exe -m pip install torch==2.13.0 torchvision==0.28.0 --index-url https://download.pytorch.org/whl/cu126
.\.venv-notebooks\Scripts\python.exe -m pip install -r requirements/notebooks-shared.candidate.txt
.\.venv-notebooks\Scripts\python.exe -m pip check
```

This pair/index is an official Windows install option, and the official CUDA
index lists `torch-2.13.0+cu126-cp312-cp312-win_amd64.whl`. The plain PyPI Windows
wheel does not by itself establish that the intended CUDA build was installed;
use the explicit CUDA index for the torch pair and verify the result afterwards.

The shared file excludes explicit torch and torchvision pins and uses the
observed numerical/application package versions as a **candidate**. Packages
such as Ultralytics have transitive torch dependencies, so check the final pair
and backend after the shared install. Do not use the entire historical Mac
requirements file unchanged or use `--no-deps` to hide conflicts.

Official references: [versioned PyTorch commands](https://pytorch.org/get-started/previous-versions/),
[CUDA 12.6 torch wheel index](https://download.pytorch.org/whl/cu126/torch/),
[torchvision 0.28.0 wheels](https://pypi.org/project/torchvision/0.28.0/).
No CUDA download or install command was executed in this milestone.

## 4. Verify the backend with a tiny tensor

```powershell
.\.venv-notebooks\Scripts\python.exe -B -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable')"
.\.venv-notebooks\Scripts\python.exe -B -c "import torch; from src.device_selection import select_device; d=select_device('cuda'); print(d); print(torch.arange(4, device=d).cpu())"
```

Expected intent is a CUDA-enabled build, `is_available()` true, the target NVIDIA
GPU and a successful small tensor operation. These results have **not** been
observed here. Explicit `cuda` selection fails if unavailable; auto selection can
fall back to CPU and must not be mistaken for a successful GPU check.

For an intentional CPU-only baseline, create a different new environment and use
the official CPU index for the same torch pair; do not replace the CUDA environment
silently. Select `select_device('cpu')` and record that decision. The optional helper
is not wired into historical notebooks, some of which contain Mac-oriented choices.
Running them unchanged may select CPU even when CUDA exists, or fail later.

## 5. Independent Rerun visualization environment

```powershell
py -3.12 -m venv .venv-rerun
.\.venv-rerun\Scripts\python.exe -m pip install -r requirements-rerun.txt
.\.venv-rerun\Scripts\python.exe -m pip check
.\.venv-rerun\Scripts\python.exe -B -c "import rerun, numpy, pyarrow; print(rerun.__version__, numpy.__version__, pyarrow.__version__)"
```

Rerun 0.42.0 publishes a Windows x86-64 `cp311-abi3` wheel, usable with the selected
CPython 3.12 ABI. CPython 3.12 Windows wheels were also checked for NumPy 2.5.4 and
PyArrow 26.0.1. Full dependency resolution, runtime and rendering are still untested
on Windows. Do not merge this NumPy 2 stack into the notebook NumPy 1.26.4 stack.

References: [Rerun wheels](https://pypi.org/project/rerun-sdk/0.42.0/),
[NumPy wheels](https://pypi.org/project/numpy/2.5.4/),
[PyArrow wheels](https://pypi.org/project/pyarrow/26.0.1/).

## 6. VS Code and Jupyter

Open the cloned folder in VS Code. Use the Microsoft Python and Jupyter extensions.
Select `.venv-notebooks\Scripts\python.exe` with **Python: Select Interpreter**,
then choose that same environment with the notebook **Select Kernel** menu.
For visualization scripts select `.venv-rerun\Scripts\python.exe` instead.
Do not reuse a Mac kernelspec pointing to a `/Users/...` interpreter.

```powershell
.\.venv-notebooks\Scripts\python.exe -m jupyter lab --notebook-dir=notebooks
```

Avoid changing historical notebooks solely to save machine-specific kernel paths.
Their `../assets` / `../data` references require a working directory compatible
with `notebooks/`. Keep workspace/editor settings local. The
[VS Code notebook guide](https://code.visualstudio.com/docs/datascience/jupyter-notebooks)
documents kernel selection; [Python environments](https://code.visualstudio.com/docs/python/environments)
documents interpreter selection.

## 7. Validate the source-only checkout

These checks require no photographs, CUDA, model weights or RRD:

```powershell
.\.venv-rerun\Scripts\python.exe -B -m unittest discover -s tests -p test_device_selection.py -v
.\.venv-rerun\Scripts\python.exe -B -c "from src.canonical_reconstruction import validate_export; print(validate_export('results/canonical_reconstruction/v1'))"
```

The device tests use fake backends and do not import real torch. The canonical
check verifies payload hashes, shapes, poses and associations inside the frozen
export. `.gitattributes` prevents Windows checkout from rewriting those payloads'
line endings. A hash failure requires investigation, not regenerating manifests
or changing the canonical files to make the test pass.

## 8. Provision local artifacts, generate and view Rerun

Git intentionally omits `data/`, `assets/`, model weights, the frozen notebook
backup and `.rrd` files. Privately transfer only owner-approved files from the Mac,
keeping the original relative paths. Preserve source bytes; do not resize images.
Full image validation needs all twelve `data/view_*.jpg` files, even though four
photos are embedded in the recording. Model weights are not needed for Rerun.

After the approved data transfer:

```powershell
.\.venv-rerun\Scripts\python.exe -B scripts/export_canonical_reconstruction.py --validate-only results/canonical_reconstruction/v1
.\.venv-rerun\Scripts\python.exe -B scripts/export_rerun_reconstruction.py --output results/rerun_reconstruction/v2-windows
.\.venv-rerun\Scripts\rerun.exe --bind 127.0.0.1 results/rerun_reconstruction/v2-windows/deku_reconstruction.rrd
```

Select timeline `stage`, then stage 4. Never overwrite canonical v1 or a previous
recording version. The exporter verifies serialized data and does not run SfM.
If the approved original v1 recording was transferred too, its readback tests are:

```powershell
.\.venv-rerun\Scripts\python.exe -B -m unittest discover -s tests -p test_rerun_reconstruction.py -v
```

Those tests target v1, not the newly generated v2 directory. Full historical
notebook tests are not a green cross-platform acceptance suite. Canonical
regeneration itself enforces the original `.venv` path and historical input
reference; this milestone does not port that generator or change its guards.

Record the exact Python patch, torch local build suffix, `torch.version.cuda`,
driver, GPU, package versions, test results and commit when the Windows setup is
eventually validated. See [dependency_strategy.md](dependency_strategy.md).
