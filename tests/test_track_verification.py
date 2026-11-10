"""Numeric-only Experiment 02 tests; no photographs, SfM or SDK required."""
import copy
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

import numpy as np

from src.track_verification import compare_variants, load_frozen, recorded_candidates, verify_associations

ROOT = Path(__file__).resolve().parents[1]


class FrozenComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_frozen(ROOT / "results/canonical_reconstruction/v1")
        cls.report, cls.decisions = compare_variants(cls.data)

    def test_baseline_preserves_every_recorded_propagation_and_its_ids(self):
        proposals = recorded_candidates(self.data)
        baseline = [r for r in self.decisions if r["variant"] == "baseline"]
        self.assertEqual(len(baseline), 34)
        self.assertTrue(all(r["accepted"] for r in baseline))
        for a, b in zip(proposals, baseline):
            for k, value in a.items():
                self.assertEqual(b[k], value)

    def test_threshold_counts_and_fixed_geometry_coverage(self):
        self.assertEqual([r["accepted"] for r in self.report["variants"]], [34, 9, 23, 27, 28])
        self.assertEqual([r["rejected"] for r in self.report["variants"]], [0, 25, 11, 7, 6])
        self.assertEqual([r["retained_final_coverage"]["associations"] for r in self.report["variants"]],
                         [892, 867, 881, 885, 886])
        self.assertEqual([r["retained_final_coverage"]["points_with_at_least_three_cameras"] for r in self.report["variants"]],
                         [100, 79, 92, 96, 97])
        for r in self.report["variants"]:
            self.assertEqual(r["retained_final_coverage"]["point_ids"], 386)
            self.assertEqual(r["retained_final_coverage"]["camera_ids"], [3, 4, 5, 6])
            self.assertEqual(r["downstream_triangulation"], "not rerun")

    def test_actual_pixels_reproduce_residuals_in_sift_coordinates(self):
        for r in self.decisions:
            c = next(c for c in self.data["cameras"] if c["camera_id"] == r["camera_id"])
            xyz = self.data["arrays"]["xyz"][r["point_id"]]
            camera = np.array(c["R_world_to_camera"]) @ xyz + c["t_world_to_camera"]
            h = np.array(c["K_sift"]) @ camera
            np.testing.assert_allclose(r["projected_sift"], h[:2] / h[2], rtol=0, atol=1e-10)
            self.assertAlmostEqual(r["error_sift_px"], np.linalg.norm(h[:2] / h[2] - r["observed_sift"]))

    def test_failure_and_low_error_example_have_different_policy_outcomes(self):
        for r in self.decisions:
            if r["observation_id"] == 782:
                self.assertEqual((r["point_id"], r["camera_id"]), (162, 6))
                self.assertAlmostEqual(r["error_sift_px"], 540.9044871112978)
                self.assertEqual(r["accepted"], r["variant"] == "baseline")
            if r["observation_id"] == 810:
                self.assertEqual(r["point_id"], 278)
                self.assertTrue(r["accepted"])
                self.assertAlmostEqual(r["error_sift_px"], .3541865909793897)

    def test_pnp_threshold_difference_and_overwrites_are_not_called_propagation(self):
        self.assertEqual(self.report["unaffected_nonpropagation_over_3px_observation_ids"], [460])
        self.assertEqual(self.report["canonical_inactive_rows"], 5)
        self.assertNotIn(460, {r["observation_id"] for r in self.decisions})
        self.assertEqual(self.report["candidate_conflicting_target_keys"], 0)
        self.assertEqual(self.report["duplicate_xyz_groups"], 21)
        self.assertEqual(self.report["unique_xyz_positions"], 364)

    def test_numeric_cli_does_not_need_sdk_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "run"
            command = [sys.executable, "-B", str(ROOT / "scripts/run_track_verification_experiment.py"),
                       "--no-rerun", "--output", str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertFalse((output / "track_verification.rrd").exists())
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})


class InsertionGateTests(unittest.TestCase):
    def setUp(self):
        self.xyz = np.array([[0., 0., 1.], [0., 0., 1.]])
        self.cameras = [dict(camera_id=6, R_world_to_camera=np.eye(3), t_world_to_camera=np.zeros(3), K_sift=np.eye(3))]

    def candidate(self, pid=0, kp=10, pixel=(0., 0.), oid=1):
        return dict(point_id=pid, camera_id=6, keypoint_id=kp, observed_sift=list(pixel), observation_id=oid)

    def verify(self, rows, **kw):
        return verify_associations(rows, self.xyz, self.cameras, **kw)

    def test_boundary_is_inclusive_and_a_stricter_gate_rejects(self):
        row = self.candidate(pixel=(1., 0.))
        self.assertTrue(self.verify([row], threshold=1)[0]["accepted"])
        self.assertFalse(self.verify([row], threshold=.999)[0]["accepted"])

    def test_depth_and_nonfinite_geometry_are_checked_even_with_zero_residual(self):
        for z in [-1., 0., np.nan, np.inf]:
            self.xyz[0, 2] = z
            result = self.verify([self.candidate()], threshold=5)[0]
            self.assertFalse(result["accepted"])
            self.assertTrue("nonpositive_depth" in result["rejection_reasons"] or "nonfinite_geometry" in result["rejection_reasons"])
        self.xyz[0, 2] = -1.
        self.assertTrue(self.verify([self.candidate()], threshold=None)[0]["accepted"])

    def test_nonfinite_observation_is_rejected(self):
        self.assertIn("nonfinite_geometry", self.verify([self.candidate(pixel=(np.nan, 0))], threshold=3)[0]["rejection_reasons"])

    def test_existing_identity_is_not_overwritten_and_identical_identity_can_reuse(self):
        existing = {(6, 10): 0}
        self.assertEqual(self.verify([self.candidate()], existing=existing, threshold=3)[0]["action"], "reuse")
        conflict = self.verify([self.candidate(pid=1)], existing=existing, threshold=3)[0]
        self.assertIn("existing_keypoint_conflict", conflict["rejection_reasons"])
        self.assertEqual(existing, {(6, 10): 0})

    def test_ambiguous_unmapped_target_rejects_all_ids_independent_of_order(self):
        candidates = [self.candidate(pid=0), self.candidate(pid=1, oid=2)]
        for order in [candidates, candidates[::-1]]:
            result = self.verify(order, threshold=3)
            self.assertTrue(all(not r["accepted"] and "ambiguous_candidate_ids" in r["rejection_reasons"] for r in result))

    def test_duplicate_proposal_does_not_add_another_association(self):
        r = self.candidate()
        result = self.verify([r, dict(r)], threshold=3)
        self.assertTrue(result[0]["accepted"])
        self.assertIn("duplicate_candidate", result[1]["rejection_reasons"])

    def test_duplicate_xyz_is_not_merged_and_inputs_are_not_modified(self):
        candidates = [self.candidate(pid=0), self.candidate(pid=1, kp=11, oid=2)]
        before = copy.deepcopy(candidates)
        results = self.verify(candidates, threshold=3)
        self.assertEqual([r["point_id"] for r in results if r["accepted"]], [0, 1])
        self.assertEqual(candidates, before)

    def test_invalid_reference_and_threshold_are_rejected(self):
        self.assertIn("unknown_reference", self.verify([self.candidate(pid=1000)], threshold=3)[0]["rejection_reasons"])
        for threshold in [-1, np.nan, np.inf]:
            with self.assertRaises(ValueError):
                self.verify([self.candidate()], threshold=threshold)


if __name__ == "__main__":
    unittest.main()
