"""Run Experiment 02 without changing historical SfM or reconstruction artifacts."""
import argparse
import csv
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.canonical_reconstruction import sha256, write_json
from src.track_verification import compare_variants, load_frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=ROOT / "results/canonical_reconstruction/v1")
    parser.add_argument("--output", type=Path, default=ROOT / "results/experiments/02_track_verification/v1")
    parser.add_argument("--no-rerun", action="store_true", help="Numeric-only; no SDK or photographs needed.")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; use a fresh version directory.")
    data = load_frozen(args.canonical)
    before = {p.name: sha256(p) for p in data["folder"].iterdir() if p.is_file()}
    report, decisions = compare_variants(data)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "comparison.json", report)
    with (args.output / "decisions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(decisions[0]))
        writer.writeheader()
        for row in decisions:
            writer.writerow({k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()})
    with (args.output / "comparison.csv").open("w", newline="") as f:
        fields = ["variant", "threshold_sift_px", "proposed", "accepted", "rejected", "mean_kept_sift_px",
                  "median_kept_sift_px", "p95_kept_sift_px", "max_kept_sift_px", "retained_active_associations",
                  "retained_points", "retained_cameras", "tracks_at_least_3_cameras", "active_errors_over_3px"]
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for row in report["variants"]:
            e, c = row["accepted_errors"], row["retained_final_coverage"]
            writer.writerow(dict(variant=row["variant"], threshold_sift_px=row["threshold_sift_px"],
                                 proposed=row["proposed"], accepted=row["accepted"], rejected=row["rejected"],
                                 mean_kept_sift_px=e["mean"], median_kept_sift_px=e["median"],
                                 p95_kept_sift_px=e["p95"], max_kept_sift_px=e["max"],
                                 retained_active_associations=c["associations"], retained_points=c["point_ids"],
                                 retained_cameras=len(c["camera_ids"]), tracks_at_least_3_cameras=c["points_with_at_least_three_cameras"],
                                 active_errors_over_3px=row["retained_active_over_3px"]))
    validation = dict(mode=report["mode"], canonical_files_sha256=before,
                      python=platform.python_version(), numpy=importlib.metadata.version("numpy"),
                      downstream_pnp="not rerun", downstream_triangulation="not rerun")
    if not args.no_rerun:
        from src.rerun_track_experiment import export_track_recording
        import rerun as rr
        path = args.output / "track_verification.rrd"
        validation["rerun"] = export_track_recording(data, report, decisions, path, ROOT)
        validation.update(rerun_sdk=rr.__version__, recording_sha256=sha256(path), recording_bytes=path.stat().st_size)
    validation["canonical_unchanged"] = before == {p.name: sha256(p) for p in data["folder"].iterdir() if p.is_file()}
    assert validation["canonical_unchanged"]
    validation["source_files_sha256"] = {name: sha256(ROOT / name) for name in
        ["src/track_verification.py", "src/rerun_track_experiment.py", "src/rerun_reconstruction.py",
         "scripts/run_track_verification_experiment.py"]}
    write_json(args.output / "validation.json", validation)
    print((args.output / "comparison.csv").read_text())
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
