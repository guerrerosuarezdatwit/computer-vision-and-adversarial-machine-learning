"""Read back the actual RRD with the pinned SDK; no SfM, models, or GUI needed."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np

from src.canonical_reconstruction import sha256
from src.rerun_reconstruction import (
    POINT_PATHS, SDK_VERSION, load_reconstruction, point_attributes,
    read_recording, stage_masks, validate_recording,
)

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "results/canonical_reconstruction/v1"
OUTPUT = ROOT / "results/rerun_reconstruction/v1"
RECORDING = OUTPUT / "deku_reconstruction.rrd"


@unittest.skipUnless(importlib.util.find_spec("rerun"), "Use the separate .venv-rerun environment.")
class RerunReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import rerun as rr
        if rr.__version__ != SDK_VERSION or not RECORDING.exists():
            raise unittest.SkipTest("Generate the v1 recording with the pinned SDK first.")
        cls.data = load_reconstruction(CANONICAL, ROOT)
        cls.rows = read_recording(RECORDING)
        cls.report = json.loads((OUTPUT / "validation.json").read_text())

    def test_actual_recording_validation(self):
        result = validate_recording(RECORDING, self.data)
        self.assertEqual(result["final_point_ids"], 386)
        self.assertEqual(result["unique_positions"], 364)
        self.assertEqual(result["embedded_original_images"], 4)
        self.assertEqual(result["all_observations_logged"], 897)
        self.assertEqual([r["rgb"] for r in result["stages"]], [188, 188, 188, 301, 386])
        self.assertEqual([r["accepted"] for r in result["stages"]], [188, 188, 188, 291, 376])
        self.assertEqual([r["rejected"] for r in result["stages"]], [0, 0, 0, 10, 10])

    def test_diagnostics_are_from_recorded_thresholds(self):
        thresholds = self.data["manifest"]["diagnostic_thresholds"]
        self.assertEqual(thresholds, dict(min_angle=2., max_error=3., max_depth_baselines=10., check_associations=False))
        rejected = self.data["arrays"]["point_ids"][stage_masks(self.data, 4)["rejected"]]
        self.assertEqual(rejected.tolist(), self.data["manifest"]["anomalies"]["diagnostic_rejected_point_ids"])
        for pid in rejected:
            # All diagnostic rejections still have small birth reprojection error.
            self.assertLess(float(self.data["metrics"][pid]["max_error_px"]), 1.174)

    def test_all_original_ids_and_metric_values_survive_serialization(self):
        final = next(r for r in self.rows[POINT_PATHS["rgb"]] if r.get("stage") == 4)
        expected = point_attributes(self.data, np.arange(386))
        for field, values in expected.items():
            if values.dtype.kind == "f":
                np.testing.assert_array_equal(final[field], values)
            else:
                self.assertEqual(final[field], values.tolist(), field)
        self.assertEqual(final["Points3D:labels"], [f"ID {pid}" for pid in range(386)])
        self.assertIn("195,196", final["duplicate_ids"])

    def test_camera_timing_rdf_and_original_resolution(self):
        for camera in self.data["cameras"]:
            path = f"/world/cameras/view_{camera['camera_id']:02d}"
            poses = [r for r in self.rows[path] if r.get("Transform3D:mat3x3") is not None]
            self.assertEqual(len(poses), 1)
            self.assertEqual(poses[0]["stage"], camera["registration_stage"])
            pinhole = next(r for r in self.rows[path + "/image"] if r.get("Pinhole:resolution") is not None)
            self.assertEqual(pinhole["Pinhole:resolution"], [[1152., 1536.]])
            self.assertIsNotNone(pinhole["Pinhole:camera_xyz"])

    def test_observations_and_known_bad_associations_remain_identifiable(self):
        seen, high = set(), set()
        for camera in self.data["cameras"]:
            path = f"/world/cameras/view_{camera['camera_id']:02d}/image/evidence/observed"
            final = next(r for r in self.rows[path] if r.get("stage") == 4 and r.get("point_id") is not None)
            for oid, pid, active, error in zip(final["observation_id"], final["point_id"],
                                              final["active_in_final_map"], final["error_sift_px"]):
                seen.add(oid)
                if active and error > 3:
                    high.add(pid)
        self.assertEqual(seen, set(range(897)))
        self.assertEqual(sorted(high), [62, 140, 161, 162, 192, 232, 295])

    def test_layout_contains_spatial_image_metrics_and_stage_views(self):
        from rerun.chunk import RrdReader
        reader = RrdReader(RECORDING)
        text = "\n".join(c.format(trim_metadata_keys=False) for c in reader.stream(store=reader.blueprints()[0]))
        for label in ["Original RGB", "Diagnostic layers", "View 03", "View 04", "View 05", "View 06", "stage"]:
            self.assertIn(label, text)

    def test_canonical_and_original_images_still_match_report(self):
        for name, expected in self.report["canonical_files_sha256"].items():
            self.assertEqual(sha256(CANONICAL / name), expected)
        for name, expected in self.report["images_sha256"].items():
            self.assertEqual(sha256(ROOT / name), expected)
        self.assertEqual(sha256(RECORDING), self.report["recording_sha256"])

    def test_refuses_to_overwrite_recording_version(self):
        before = sha256(RECORDING)
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/export_rerun_reconstruction.py"),
                                 "--output", str(OUTPUT)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Output already exists", result.stderr)
        self.assertEqual(before, sha256(RECORDING))


if __name__ == "__main__":
    unittest.main()
