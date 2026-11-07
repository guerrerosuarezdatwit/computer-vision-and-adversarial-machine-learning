# Two-computer development workflow

The intended remote is a **private** GitHub repository. No Git initialization,
staging, commit, remote creation or push is authorized by the current task.
The Git commands below are a future workflow, gated by review of
[github_publication_checklist.md](github_publication_checklist.md).

## What synchronizes

| Use Git after review | Keep local / transfer separately when approved |
| --- | --- |
| Source, tests, documentation, requirements and reviewed notebooks. | `.venv`, `.venv-notebooks`, `.venv-rerun`, editor settings and caches. |
| Canonical v1 arrays, camera/observation/metric files and manifest. | Original photos/assets, private datasets and model weights. |
| Selected validation and environment records. | RRD/RBL recordings, raw videos, temporary runs and unreviewed figures. |

`.gitignore` is conservative even for the private remote. Private visibility is
an access-control choice, not permission to upload secrets or every raw dataset.
Rerun recordings and notebook outputs can contain photographs even when `data/`
is ignored. See the existing [privacy and size review](RELEASE_REVIEW.md).

## Environment discipline

Use [setup_macos.md](setup_macos.md) on the M1 Pro and
[setup_windows.md](setup_windows.md) on the RTX 4060 computer. Recreate native
environments; never sync them through Git, cloud folders, ZIP copies or a drive.
Use explicit interpreter paths to avoid installing into the wrong environment.
Do not import the optional device helper into historical notebooks as an automatic
refactor. Use it in new experiments and log the selected backend explicitly.

Rerun is a separate viewer/export environment. On both machines a source-only
checkout can validate the canonical payload without source images. Full RRD
generation requires the privately provisioned images with matching hashes.
Do not assume the historical canonical-regeneration script is Windows-ready:
it deliberately enforces the historical `.venv` path and source reference.

## Prevent line-ending corruption

`.gitattributes` checks out source/documentation as LF where specified and marks
notebooks and `results/` as `-text`, preserving their actual bytes. Canonical
`metrics.csv` contains historical line endings protected by manifest hashes.
Do not run a formatter, line-ending converter, JSON pretty-printer or automatic
notebook-output cleaner over frozen scientific references.

After Git initialization has been approved, inspect the real checkout attributes:

```bash
git check-attr text eol -- results/canonical_reconstruction/v1/metrics.csv notebooks/13_multiview_3d_reconstruction.ipynb src/rerun_reconstruction.py
```

Expected intent is `text: unset` for the frozen CSV/notebook and `text: set`,
`eol: lf` for Python. Source-only payload validation on Windows is the next
end-to-end check of this policy. No `git add --renormalize` is prescribed.

## Start a work session (only after the reviewed remote exists)

On either computer, first check for local edits:

```bash
git status --short
git switch main
git pull --ff-only origin main
git switch -c research/describe-the-change
```

If the working tree has edits, resolve their ownership and preserve them before
switching/pulling. Do not discard notebook changes or use destructive resets to
force synchronization. Never work concurrently on the same notebook from both
machines without an agreed ownership plan. Keep one active machine per change
when possible, with separate branches for independent work.

## End a work session

Run the relevant lightweight checks with the correct local interpreter, then
inspect exact paths. These are future examples, not commands run in this task:

```bash
git diff --stat
git diff -- src/device_selection.py tests/test_device_selection.py
git add -- src/device_selection.py tests/test_device_selection.py
git diff --cached --stat
git diff --cached
git status --short
```

Review notebook renders and media manually when they are included; a text diff
does not reveal every embedded output. Once the specific commit/push is approved,
the usual branch publication is:

```bash
git commit -m "Describe the reviewed change"
git push -u origin research/describe-the-change
```

Open a private pull request, review, and merge. On the other computer, return to
main with a clean tree and use `git pull --ff-only`. Fetch updates rather than
copying the entire Mac working directory over the Windows checkout.

If divergence prevents a fast-forward, stop and inspect; do not force-push or
reset another machine's work. Notebook conflicts require a deliberate source/
output review, not blindly selecting one entire JSON side. Keep uncommitted
backups outside the tracked tree when investigating a conflict.

## Dataset and artifact transfer

Use a separately approved private transfer method for originals or model files.
Keep paths such as `data/view_03.jpg` identical, but never copy a private key or
the virtual environment. Run the canonical full image/hash validation after
transfer. No remote dataset host, URL or transfer has been configured by this task.

Write new research runs to distinct directories such as `v2-macos` and
`v2-windows`; record the source commit, platform and environment with the results.
Ignored outputs are not backed up by Git. Maintain a separate backup of research
history and locally held assets. Preserve canonical v1 rather than editing it
to accommodate differences in a new run.

## Tests and evidence

- Device-policy unit tests need no torch/GPU; actual accelerator smoke checks are
  separate and do not establish model compatibility.
- Canonical payload validation needs NumPy, not photographs. Full validation
  checks all twelve originals.
- Rerun tests need the local v1 recording/photos and its SDK; eight passed in
  milestone 2. Windows results must be recorded separately when actually observed.
- The historical full suite has a known snapshot checksum failure. Preserve that
  finding; do not delete a test, rewrite a notebook, or update frozen hashes merely
  to claim that a cross-platform suite is green.

The long-term lab can add VGGT, Gaussian Splatting and adversarial 3D experiments
as separately versioned integrations with their own hardware/license assessments.
None of those methods is installed or implemented by this workflow task.
