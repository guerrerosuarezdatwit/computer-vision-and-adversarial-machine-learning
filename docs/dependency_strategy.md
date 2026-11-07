# Dependency strategy: shared code, platform-specific runtimes

Reviewed **2026-11-07**. No packages were installed, upgraded or downloaded in this
task. Metadata/wheel availability is evidence of an install option, not proof of
a resolved environment, working driver, supported operation or reproducible result.

## Three distinct baselines

| Stack | Mac | Windows | Status |
| --- | --- | --- | --- |
| Historical research | `.venv`, Python 3.10.5, torch 2.13.0, torchvision 0.28.0, NumPy 1.26.4 | No historical Windows baseline exists. | Preserve the Mac environment unchanged. |
| New notebook development | Candidate Python 3.12 ARM64, normal macOS torch wheel with MPS runtime check. | Candidate Python 3.12 x86-64, CUDA 12.6 torch wheel with NVIDIA driver/runtime check. | New recipes are not install-tested. |
| Visualization | Existing Python 3.12.13, Rerun 0.42.0, NumPy 2.5.4. | Candidate Python 3.12 x86-64, same Rerun runtime pins. | Mac recording/readback verified; Windows untested. |

The same Python *minor* version is a useful candidate for new development, not
a requirement to replace a validated historical stack. Pin each machine's exact
patch/build after it has actually been provisioned and tested. A virtual environment
is machine-local; Git synchronizes its instructions and source, never its directory.

### Checks actually executed in this follow-up

Seven device-policy unit tests passed without GPU dependencies. In the existing
Mac environment, torch 2.13.0 imported successfully, a tiny explicit-CPU tensor
operation passed, and canonical payload validation retained 386 IDs, four cameras,
897 evidence rows and 364 distinct positions. The automated execution context
reported `mps.is_built() == True` but `mps.is_available() == False`; no MPS operation
was claimed or forced. Check explicit MPS availability from the Mac's normal
terminal/Jupyter context before recording a GPU baseline. CUDA execution, Windows
setup and both fresh candidate installs remain untested.

## Shared and platform-specific dependencies

- `requirements-notebooks.observed.txt` describes the preserved Mac stack. It is
  not a portable lockfile and must not be installed unchanged as the Windows plan.
- `requirements/notebooks-shared.candidate.txt` contains direct numerical,
  perception and notebook package pins, excluding explicit torch/torchvision and
  CUDA-index choices. It is derived from the Mac record and still needs a complete
  solve on both new platforms. Ultralytics and other packages can still constrain
  torch transitively; inspect the resolved versions rather than bypassing them.
- Install a matched torch/torchvision pair from its platform-specific source first.
  The candidate pair is 2.13.0 / 0.28.0. Windows uses the documented CUDA 12.6 index;
  macOS uses the documented macOS wheel command. Avoid a global pip index change
  and do not put a CUDA-only index in shared requirements.
- `requirements-rerun.txt` remains the pinned visualization runtime. Rerun's
  NumPy >=2 requirement is kept apart from the historical/candidate notebook
  NumPy 1.26.4 stack. It requires no PyTorch or model weights.
- No full CUDA toolkit or compiler stack is prescribed for the current pure
  wheel-based notebook prototype. Native/custom extensions in future methods
  require a new, versioned compatibility assessment.

## Compatibility evidence checked

| Component | Verified from official metadata/docs | Still unverified |
| --- | --- | --- |
| torch 2.13.0 / torchvision 0.28.0 | Official matched commands for macOS and Windows CUDA 12.6; CPython 3.12 target wheels. | Fresh install, target driver, CUDA execution and MPS operation coverage. |
| torch Mac wheel | CPython 3.12 ARM64 wheel tag requires macOS 14+. | MPS runtime requirements/availability on any other Mac/OS. |
| Notebook NumPy 1.26.4 | CPython 3.12 platform distributions listed. | Full candidate environment solve and interaction with application packages. |
| Rerun 0.42.0 | Python >=3.11, macOS ARM64 and Windows x86-64 cp311-abi3 wheels. | Full Windows dependency resolution and Viewer rendering. |
| NumPy 2.5.4 / PyArrow 26.0.1 | CPython 3.12 Windows x86-64 distributions listed. | Full Windows runtime behavior. |

The rolling PyTorch start page contains a mixture of current and older selector
text. Version-specific commands, wheel tags and local package metadata were used
instead of inferring compatibility from a displayed "latest" label. Do not infer
that an NVIDIA GPU alone establishes which CUDA wheel or driver works.

## Reproducibility after the target-machine checks

1. Record the Python patch, architecture, OS, device, torch build suffix and
   runtime. On Windows record NVIDIA driver, GPU name and `torch.version.cuda`.
2. Run `pip check`, a tiny explicit-device tensor test, payload validation, and
   appropriate artifact tests. Check a model-free baseline before model downloads.
3. Capture a separate resolved snapshot for each tested stack: Mac notebook,
   Windows CUDA notebook, and visualization. A future hash-locked format should
   record platform/build tags and approved package sources, not only version names.
4. For an audit snapshot, `python -m pip freeze` is useful, but inspect it before
   committing: local paths, editable installs, credential URLs and platform CUDA
   packages must not become a universal requirements file.
5. Commit a new validated lock/snapshot alongside its evidence in a future task;
   retain the historical observed record. Do not overwrite a frozen export's
   environment metadata to match a different machine.

Compare geometry using documented numerical tolerances and scientific metrics.
MPS/CUDA/CPU kernels, RANSAC/library versions and nondeterminism can affect results.
A different floating-point trajectory is not automatically a bug, and a matching
point count is not proof of matching reconstruction. Exporters must keep refusing
to substitute a changed reconstruction for the canonical reference silently.

## Sources

- [PyTorch versioned installation commands](https://pytorch.org/get-started/previous-versions/)
- [CUDA 12.6 torch distributions](https://download.pytorch.org/whl/cu126/torch/)
- [torch 2.13.0 metadata](https://pypi.org/project/torch/2.13.0/)
- [torchvision 0.28.0 metadata](https://pypi.org/project/torchvision/0.28.0/)
- [MPS runtime availability checks](https://docs.pytorch.org/docs/stable/notes/mps.html)
- [NumPy 1.26.4](https://pypi.org/project/numpy/1.26.4/)
- [Rerun 0.42.0](https://pypi.org/project/rerun-sdk/0.42.0/)
- [Visualization NumPy](https://pypi.org/project/numpy/2.5.4/) and [PyArrow](https://pypi.org/project/pyarrow/26.0.1/)
