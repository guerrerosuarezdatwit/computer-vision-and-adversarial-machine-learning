"""Replay notebook 13 without writing historical files; export or validate a version.

Run with .venv/bin/python scripts/export_canonical_reconstruction.py --output
results/canonical_reconstruction/v1. Existing output directories are never reused.
No model inference, dependency installation, or SfM algorithm changes are made.
"""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.canonical_reconstruction import capture_propagation, export_canonical, sha256, validate_export


def protected_fingerprints():
    """Snapshot all pre-existing experiment assets/results, excluding new exports."""
    return {str(p.relative_to(ROOT)): sha256(p)
            for folder in ("notebooks", "data", "assets", "results")
            for p in sorted((ROOT / folder).rglob("*"))
            if p.is_file() and "canonical_reconstruction" not in p.parts
            and p.name != ".DS_Store" and "__pycache__" not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/canonical_reconstruction/v1"))
    parser.add_argument("--validate-only", type=Path, help="Check an existing export without running SfM or writing files.")
    args = parser.parse_args()
    if args.validate_only is not None:
        print(json.dumps(validate_export(args.validate_only.resolve(), ROOT), indent=2))
        return
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        parser.error("Use the existing project .venv/bin/python to reproduce the historical map.")
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists. Choose a fresh version directory; nothing was overwritten.")
    # Plotting is suppressed, but all historical numerical cells run in order,
    # including RANSAC calls that influence the original random-number sequence.
    os.environ["MPLBACKEND"] = "Agg"
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "adversarial-vision-matplotlib"))
    import matplotlib.pyplot as plt
    import plotly.basedatatypes
    notebook_path = ROOT / "results/triangulation_diagnostics/original_13_multiview_3d_reconstruction.ipynb"
    original = json.loads(notebook_path.read_text())
    current = json.loads((ROOT / "notebooks/13_multiview_3d_reconstruction.ipynb").read_text())
    if current["cells"][:len(original["cells"])] != original["cells"]:
        raise ValueError("Historical notebook cells differ from their preserved reference.")
    checksums = protected_fingerprints()
    recorded = json.loads((notebook_path.parent / "image_sha256.json").read_text())
    if len(recorded) != 12 or any(sha256(ROOT / p) != digest for p, digest in recorded.items()):
        raise ValueError("Original image manifest differs; export aborted.")
    cwd = Path.cwd()
    old_show, old_plt_show = plotly.basedatatypes.BaseFigure.show, plt.show
    plotly.basedatatypes.BaseFigure.show = lambda *a, **kw: None
    plt.show = lambda *a, **kw: plt.close("all")
    namespace, propagation = {"__name__": "__main__"}, []
    try:
        os.chdir(ROOT / "notebooks")
        for i, cell in enumerate(original["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            if source.lstrip().startswith("%pip"):
                print(f"Skipped historical dependency-installation cell {i}.", flush=True)
                continue
            if i in (47, 48):
                a, b, stage = (3, 4, 3) if i == 47 else (4, 5, 4)
                propagation.extend(capture_propagation(namespace, a, b, stage))
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, f"historical-cell-{i}", "exec"), namespace)
        print(f"Reproduced {len(namespace['global_points'])} original point IDs; exporting.", flush=True)
        with contextlib.redirect_stdout(io.StringIO()) as report:
            export_canonical(namespace, propagation, ROOT, output, checksums)
        if protected_fingerprints() != checksums:
            raise RuntimeError("A protected historical file changed during export.")
        print(report.getvalue(), end="")
        print("Verified: all protected notebooks, photographs, model weights and historical results are unchanged.")
    finally:
        os.chdir(cwd)
        plotly.basedatatypes.BaseFigure.show, plt.show = old_show, old_plt_show
        plt.close("all")


if __name__ == "__main__":
    main()
