"""Coordinate/provenance checks and readback of the actual private v0.2 RRD."""
from collections import Counter
import copy
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np

from src.canonical_reconstruction import read_csv, validate_export
from src.rerun_inspection import (
    SELECTED, TIMELINE, inspection_text, observation_records, validate_inspection,
)
from src.rerun_reconstruction import read_recording

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "results/canonical_reconstruction/v1"
RECORDING = ROOT / "results/rerun_reconstruction/v2/deku_inspection.rrd"


def portable_data():
    import json
    validate_export(CANONICAL)  # Numeric tests require no photos or Rerun.
    with np.load(CANONICAL / "points.npz", allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    metrics = read_csv(CANONICAL / "metrics.csv")
    return dict(root=ROOT, folder=CANONICAL, arrays=arrays, metrics=metrics,
                accepted=np.array([r["accepted"] == "True" for r in metrics]),
                manifest=json.loads((CANONICAL / "manifest.json").read_text()),
                cameras=json.loads((CANONICAL / "cameras.json").read_text())["cameras"],
                observations=read_csv(CANONICAL / "observations.csv"))


class ObservationGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = portable_data()
        cls.records = observation_records(cls.data)

    def test_every_residual_uses_actual_observed_pixels(self):
        for r in self.records:
            c = next(c for c in self.data["cameras"] if c["camera_id"] == r["camera_id"])
            camera_xyz = np.array(c["R_world_to_camera"]) @ self.data["arrays"]["xyz"][r["point_id"]] + c["t_world_to_camera"]
            homogeneous = np.array(c["K_original"]) @ camera_xyz
            predicted = homogeneous[:2] / homogeneous[2]
            np.testing.assert_allclose(predicted, r["projected"], rtol=0, atol=1e-10)
            np.testing.assert_allclose(np.linalg.norm(predicted-r["observed"]), r["error_original_px"], atol=1e-9)
            np.testing.assert_allclose(r["error_sift_px"], r["error_original_px"] * .78125, atol=1e-9)
            self.assertEqual(c["original_size"], dict(width=1152, height=1536))
            np.testing.assert_allclose(np.diag([.78125, .78125, 1]) @ c["K_original"], c["K_sift"])

    def test_verified_low_residual_example_and_missing_evidence(self):
        r = self.records[0]
        self.assertEqual((r["point_id"], r["camera_id"], r["observation_id"]), (0, 3, 0))
        self.assertEqual(r["status"], "active_consistent")
        self.assertAlmostEqual(r["error_sift_px"], .28908621235741355)
        self.assertEqual({r["camera_id"] for r in self.records if r["point_id"] == 0}, {3, 4})
        self.assertIn("missing evidence", inspection_text(self.data, self.records, 0))

    def test_problematic_propagation_and_pnp_are_both_flagged(self):
        worst = self.records[782]
        self.assertEqual((worst["point_id"], worst["camera_id"], worst["keypoint_id"]), (162, 6, 0))
        self.assertEqual(worst["provenance"], "descriptor_propagation")
        self.assertEqual(worst["status"], "active_inconsistent")
        self.assertAlmostEqual(worst["error_sift_px"], 540.9044871112978)
        self.assertAlmostEqual(worst["error_original_px"], 692.3577435024612)
        pnp = self.records[460]
        self.assertEqual(pnp["provenance"], "pnp_inlier")
        self.assertEqual(pnp["status"], "active_inconsistent")
        self.assertEqual(Counter(r["status"] for r in self.records),
                         dict(active_consistent=884, active_inconsistent=8, inactive_consistent=5))

    def test_overwritten_rows_retain_both_historical_and_replacement_ids(self):
        inactive = [r for r in self.records if not r["active_in_final_map"]]
        self.assertEqual([(r["point_id"], r["overwritten_by_point_id"]) for r in inactive],
                         [(188, 189), (203, 205), (204, 206), (280, 281), (294, 295)])
        self.assertTrue(all(r["consistent_3px"] for r in inactive))
        self.assertIn("inactive_consistent", inspection_text(self.data, self.records, 188))

    def test_duplicate_xyz_is_not_point_identity(self):
        np.testing.assert_array_equal(self.data["arrays"]["xyz"][195], self.data["arrays"]["xyz"][196])
        a, b = ([r for r in self.records if r["point_id"] == pid] for pid in [195, 196])
        self.assertNotEqual({r["observation_id"] for r in a}, {r["observation_id"] for r in b})
        self.assertNotEqual({r["keypoint_id"] for r in a}, {r["keypoint_id"] for r in b})
        self.assertEqual(len(np.unique(self.data["arrays"]["xyz"], axis=0)), 364)

    def test_corrupted_observation_cannot_reuse_a_stored_error(self):
        data = copy.deepcopy(self.data)
        row = data["observations"][0]
        row["u_original"] = str(float(row["u_original"]) + 100)
        row["u_sift"] = str(float(row["u_sift"]) + 78.125)
        with self.assertRaisesRegex(ValueError, "Recorded residual mismatch"):
            observation_records(data)


@unittest.skipUnless(importlib.util.find_spec("rerun") and RECORDING.exists(),
                     "Generate v0.2 with the pinned SDK and private local photographs.")
class InspectionRecordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = portable_data()
        cls.rows = read_recording(RECORDING)

    def test_complete_serialized_geometry_observations_and_camera_validation(self):
        report = validate_inspection(RECORDING, self.data)
        self.assertEqual(report["point_ids"], 386)
        self.assertEqual(report["observation_rows"], 897)
        self.assertEqual(report["unique_positions"], 364)
        self.assertEqual(report["overwritten_observations"], 5)
        self.assertGreater(report["missing_point_camera_pairs"], 0)

    def test_missing_views_are_cleared_at_each_inspected_id(self):
        for cid in [5, 6]:
            base = f"/world/cameras/view_{cid:02d}/image/inspection"
            self.assertTrue(any(r.get(TIMELINE) == 0 and r.get("Clear:is_recursive") == [True]
                                for r in self.rows[base]))
            self.assertFalse(any(r.get(TIMELINE) == 0 for r in self.rows[base + "/observed"]))

    def test_duplicate_positions_have_separate_serialized_inspection_steps(self):
        for pid in [195, 196]:
            r = next(r for r in self.rows[SELECTED] if r.get(TIMELINE) == pid)
            self.assertEqual(r["point_id"], [pid])
            self.assertEqual(r["duplicate_ids"], ["195,196"])

    def test_blueprint_has_four_image_views_raw_metadata_and_id_timeline(self):
        from rerun.chunk import RrdReader
        reader = RrdReader(RECORDING)
        text = "\n".join(c.format(trim_metadata_keys=False) for c in reader.stream(store=reader.blueprints()[0]))
        for label in ["View 03", "View 04", "View 05", "View 06", TIMELINE,
                      "Selected observation metadata", "RGB reconstruction"]:
            self.assertIn(label, text)

    def test_cli_refuses_to_overwrite_an_existing_version(self):
        from src.canonical_reconstruction import sha256
        before = sha256(RECORDING)
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/export_rerun_inspection.py")],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Output already exists", result.stderr)
        self.assertEqual(sha256(RECORDING), before)


if __name__ == "__main__":
    unittest.main()
