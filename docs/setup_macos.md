# macOS ARM64 setup: M1 Pro / MPS

Status: **2026-11-07**. Existing Mac artifacts and environments have been exercised;
the fresh notebook recipe below is a **candidate, not install-tested**. No packages
were installed or upgraded while preparing this guide. Windows is documented
separately in [setup_windows.md](setup_windows.md).

## 1. Obtain the source after the private-repository review

No repository or remote has been created yet. Only after the owner has created
and populated the approved private repository, replace `OWNER` and run:

```bash
git clone https://github.com/OWNER/adversarial-vision.git
cd adversarial-vision
```

On the existing Mac, open the current project directory instead of cloning over it.
Use native ARM64 Python, not an x86-64 interpreter running under Rosetta:

```bash
python3.12 -c "import platform, sys; print(sys.version); print(platform.machine())"
```

Run the remaining commands from the directory containing the root README.
Do not copy environments from another computer. Originals, datasets, weights and
recordings excluded by `.gitignore` will not arrive through `git clone`.

## 2. Keep the historical notebook environment

The existing `.venv` is CPython 3.10.5 with torch 2.13.0, torchvision 0.28.0 and
NumPy 1.26.4. It is the observed historical stack, not a universal installation
recipe. Keep it intact; do not upgrade it for this workflow.

```bash
.venv/bin/python --version
.venv/bin/python -m pip check
```

The direct-dependency record is
[requirements-notebooks.observed.txt](../requirements-notebooks.observed.txt).
Historical notebooks still contain execution-order, asset and preprocessing issues.

## 3. Candidate environment for new notebook development

Use a new `.venv-notebooks`, only if that directory does not already exist.
CPython 3.12 is the proposed shared minor version for new Mac/Windows development;
it does not redefine the historical Python 3.10.5 baseline. The existing Mac
visualization interpreter is 3.12.13. Record the exact patch actually used.

```bash
python3.12 -m venv .venv-notebooks
.venv-notebooks/bin/python -m pip install torch==2.13.0 torchvision==0.28.0
.venv-notebooks/bin/python -m pip install -r requirements/notebooks-shared.candidate.txt
.venv-notebooks/bin/python -m pip check
```

The first install is the documented macOS torch/torchvision pair. MPS does not
use a CUDA wheel. The second file deliberately omits explicit torch pins and CUDA
indexes, although packages such as Ultralytics depend on torch transitively.
After resolving it, verify that the intended torch/torchvision pair remains.
Do not use `--no-deps` to conceal dependency conflicts.

Official metadata lists a CPython 3.12 macOS 14+ ARM64 wheel for torch 2.13.0;
runtime MPS availability must still be checked. The new environment, complete
shared dependency solve and all notebook executions remain untested here.
See [official versioned install commands](https://pytorch.org/get-started/previous-versions/)
and [torch wheel metadata](https://pypi.org/project/torch/2.13.0/).

## 4. Verify device selection without model downloads

```bash
.venv-notebooks/bin/python -B -c "import torch; from src.device_selection import select_device; d=select_device(); print(torch.__version__, d); print(torch.arange(4, device=d).cpu())"
.venv-notebooks/bin/python -B -c "from src.device_selection import select_device; print(select_device('mps'))"
```

The optional helper selects CUDA → MPS → CPU for `auto`. An explicit unavailable
MPS request raises an error instead of silently changing the experiment to CPU.
MPS availability depends on the OS, build and execution context. If it is absent,
inspect `torch.backends.mps.is_built()` and `is_available()` and run an explicit CPU
baseline. Do not globally enable fallback and call that a pure MPS experiment.
The [PyTorch MPS guide](https://docs.pytorch.org/docs/stable/notes/mps.html) documents
these availability checks.

The helper is not imported by or substituted into any historical notebook.
For new code, put model parameters, inputs, labels and normalization tensors on
the selected device. Record the chosen backend; MPS and CUDA results need not
match bit-for-bit, especially for iterative adversarial optimization.

## 5. Separate Rerun environment

The existing `.venv-rerun` uses Python 3.12.13, Rerun 0.42.0 and NumPy 2.5.4.
Keep it separate from NumPy 1.26.4 in notebook development. Fresh setup is only
for a new directory and was not repeated in this milestone:

```bash
python3.12 -m venv .venv-rerun
.venv-rerun/bin/python -m pip install -r requirements-rerun.txt
.venv-rerun/bin/python -m pip check
```

Open an existing local recording:

```bash
.venv-rerun/bin/rerun --bind 127.0.0.1 results/rerun_reconstruction/v1/deku_reconstruction.rrd
```

Select `stage` and move to 4. The file is ignored by Git and embeds photographs;
transfer it privately only after the data plan is approved. No torch is needed
to export or inspect the Rerun recording.

## 6. VS Code and Jupyter

Open the project folder in VS Code and use the Microsoft Python and Jupyter
extensions. Run **Python: Select Interpreter** and choose either the historical
`.venv/bin/python` or the candidate `.venv-notebooks/bin/python`, deliberately.
Then choose the same environment through the notebook's **Select Kernel** menu.
Use `.venv-rerun/bin/python` for visualization scripts, not historical notebooks.
Workspace/editor settings remain local and ignored.

```bash
.venv-notebooks/bin/python -m jupyter lab --notebook-dir=notebooks
```

VS Code's notebook working directory must resolve `../assets` and `../data` as
the historical notebooks expect. For new experiments use explicit `Path`-based
project paths, and keep notebook sources/outputs unchanged when merely selecting
interpreters. See the official [interpreter](https://code.visualstudio.com/docs/python/environments)
and [notebook/kernel](https://code.visualstudio.com/docs/datascience/jupyter-notebooks) guides.

## 7. Lightweight checks and new recordings

These checks do not run SfM or learned models:

```bash
.venv-rerun/bin/python -B -m unittest discover -s tests -p 'test_device_selection.py' -v
.venv-rerun/bin/python -B -c "from src.canonical_reconstruction import validate_export; print(validate_export('results/canonical_reconstruction/v1'))"
```

The first uses fake backends and requires no torch. The second validates frozen
numerical payloads without requiring source photographs.

Once all twelve original photos have been provisioned locally with matching
hashes, generate to a fresh directory (never overwrite canonical v1):

```bash
.venv-rerun/bin/python -B scripts/export_rerun_reconstruction.py --output results/rerun_reconstruction/v2-macos
.venv-rerun/bin/python -B -m unittest discover -s tests -p 'test_rerun_reconstruction.py' -v
```

The Rerun tests target the existing v1 fixture and require its local RRD and
photos; generating v2 does not retarget those tests automatically. Full historical
test discovery includes a known checksum failure; do not report it as a green
portable suite. Canonical regeneration remains tied to the historical `.venv`
and ignored frozen notebook backup. See [dependency strategy](dependency_strategy.md)
and [development workflow](development_workflow.md).
