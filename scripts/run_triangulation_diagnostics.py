"""Replay original notebook in the project venv and execute only appended diagnostics.

Historical outputs are preserved. No package installs, image writes or new poses
from modified algorithms. Run from any working directory.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    raise RuntimeError("Use the project .venv/bin/python.")
os.environ["MPLBACKEND"] = "Agg"
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "adversarial-vision-matplotlib"))
import matplotlib.pyplot as plt
import nbformat
import plotly.basedatatypes


def main():
    original_cwd = Path.cwd()
    original_show = plotly.basedatatypes.BaseFigure.show
    original_plt_show = plt.show
    plt.show = lambda *a, **kw: plt.close("all")
    plotly.basedatatypes.BaseFigure.show = lambda *a, **kw: None
    notebook_path = ROOT / "notebooks/13_multiview_3d_reconstruction.ipynb"
    original_path = ROOT / "results/triangulation_diagnostics/original_13_multiview_3d_reconstruction.ipynb"
    original = json.loads(original_path.read_text())
    notebook = nbformat.read(notebook_path, as_version=4)
    original_cells = json.loads(notebook_path.read_text())["cells"][:len(original["cells"])]
    assert original_cells == original["cells"], "Historical experiment cells changed."
    images = sorted((ROOT / "data").glob("view_*.jpg"))
    checksums = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in images}
    saved_checksums = json.loads((original_path.parent / "image_sha256.json").read_text())
    assert checksums == saved_checksums and len(images) == 12, "Original images differ."
    namespace = {"__name__": "__main__"}
    try:
        os.chdir(ROOT / "notebooks")
        for i, cell in enumerate(original["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            if source.lstrip().startswith("%pip"):
                print(f"Skipping historical installation cell {i}; dependencies already available.", flush=True)
                continue
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, f"original-cell-{i}", "exec"), namespace)
        print(f"Original map reproduced: {len(namespace['global_points'])} points", flush=True)
        for i in range(len(original["cells"]), len(notebook.cells)):
            cell = notebook.cells[i]
            if cell.cell_type != "code":
                continue
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile(cell.source, f"diagnostic-cell-{i}", "exec"), namespace)
            cell.execution_count = i + 1
            cell.outputs = [nbformat.v4.new_output("stream", name="stdout", text=output.getvalue())] if output.getvalue() else []
            if "from IPython.display import IFrame" in cell.source:
                frame = namespace["IFrame"](src=namespace["diagnostic_html_relative"].as_posix(), width="100%", height=1350)
                cell.outputs = [nbformat.v4.new_output("display_data", data={"text/html": frame._repr_html_(), "text/plain": "Interactive triangulation diagnostics"})]
            print(output.getvalue(), end="", flush=True)
        assert namespace["view_maps"] == namespace["diagnostic_maps_before"]
        assert namespace["np"].array_equal(namespace["global_points"], namespace["diagnostic_points_before"])
        # Python reference classifications for the standalone JavaScript controls.
        cases = []
        for thresholds in [
            dict(min_angle=2., max_error=3., max_depth_baselines=10., check_associations=False),
            dict(min_angle=0., max_error=100., max_depth_baselines=1e9, check_associations=False),
            dict(min_angle=2., max_error=100., max_depth_baselines=1e9, check_associations=False),
            dict(min_angle=0., max_error=.1, max_depth_baselines=1e9, check_associations=False),
            dict(min_angle=90., max_error=0., max_depth_baselines=.1, check_associations=False),
            dict(min_angle=2., max_error=3., max_depth_baselines=10., check_associations=True),
        ]:
            mask, _ = namespace["td"].classify(namespace["diagnostic_rows"], **thresholds)
            cases.append(dict(thresholds=thresholds, accepted_ids=namespace["np"].flatnonzero(mask).tolist()))
        (original_path.parent / "control_cases.json").write_text(json.dumps(cases, indent=2)+'\n')
        assert json.loads(nbformat.writes(notebook))["cells"][:len(original["cells"])] == original["cells"]
        nbformat.validate(notebook)
        nbformat.write(notebook, notebook_path)
        print("Verified: historical cells, map, associations and 12 original images preserved.")
    finally:
        os.chdir(original_cwd)
        plotly.basedatatypes.BaseFigure.show = original_show
        plt.show = original_plt_show
        plt.close("all")
    assert checksums == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in images}


if __name__ == "__main__":
    main()
