"""Lightweight artifact and corruption tests; never rerun SfM or model inference.

The versioned v1 export is the test fixture. Negative tests edit private temporary
copies and refresh their checksums to test semantic validation, not only hashes.
"""
import collections
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from src.canonical_reconstruction import FILES, read_csv, sha256, validate_export, write_json


ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "results/canonical_reconstruction/v1"


class CanonicalReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (EXPORT / "manifest.json").exists():
            raise unittest.SkipTest("Generate the canonical v1 export first; no reconstruction is run by tests.")
        cls.manifest = json.loads((EXPORT / "manifest.json").read_text())
        cls.cameras = json.loads((EXPORT / "cameras.json").read_text())["cameras"]
        cls.observations = read_csv(EXPORT / "observations.csv")
        cls.metrics = read_csv(EXPORT / "metrics.csv")

    def private_copy(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        folder = Path(temporary.name)
        for name in (*FILES, "manifest.json"):
            shutil.copyfile(EXPORT / name, folder / name)
        return folder

    def refresh_hash(self, folder, filename):
        manifest = json.loads((folder / "manifest.json").read_text())
        manifest["artifacts"][filename] = dict(sha256=sha256(folder / filename), bytes=(folder / filename).stat().st_size)
        write_json(folder / "manifest.json", manifest)

    def write_rows(self, path, rows):
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_independent_validation(self):
        self.assertEqual(validate_export(EXPORT, ROOT), dict(
            points=386, cameras=4, observations=897, final_associations=892,
            diagnostic_accepted=376, unique_positions=364))

    def test_ids_colors_and_chronological_stages(self):
        with np.load(EXPORT / "points.npz", allow_pickle=False) as points:
            np.testing.assert_array_equal(points["point_ids"], np.arange(386))
            self.assertEqual(points["xyz"].shape, (386, 3))
            self.assertEqual(points["xyz"].dtype, np.float32)
            self.assertEqual(points["rgb"].shape, (386, 3))
            self.assertEqual(points["rgb"].dtype, np.uint8)
            self.assertEqual(len(np.unique(points["xyz"], axis=0)), 364)
            np.testing.assert_array_equal(points["stage"], [0] * 188 + [3] * 113 + [4] * 85)
        self.assertEqual([s["point_count"] for s in self.manifest["stages"]], [188, 188, 188, 301, 386])

    def test_camera_direction_centers_and_resize(self):
        # A nontrivial camera-space point must map back to the same camera point.
        local = np.array([.2, -.4, 5.])
        for camera in self.cameras:
            R = np.array(camera["R_world_to_camera"])
            t = np.array(camera["t_world_to_camera"])
            C = np.array(camera["center_world"])
            world = R.T @ local + C
            np.testing.assert_allclose(R @ world + t, local, atol=1e-12)
            np.testing.assert_allclose(R @ C + t, 0, atol=1e-12)
            world_h = np.r_[world, 1.]
            np.testing.assert_allclose(np.array(camera["T_world_to_camera"]) @ world_h, np.r_[local, 1.], atol=1e-12)
            np.testing.assert_allclose(camera["K_sift"], [[810, 0, 450], [0, 810, 600], [0, 0, 1]])
            np.testing.assert_allclose(camera["K_original"], [[1036.8, 0, 576], [0, 1036.8, 768], [0, 0, 1]])
            self.assertEqual(camera["original_size"], dict(width=1152, height=1536))
            self.assertEqual(camera["sift_size"], dict(width=900, height=1200))
        self.assertEqual([c["camera_id"] for c in self.cameras], [3, 4, 5, 6])

    def test_observation_provenance_and_overwritten_evidence(self):
        counts = collections.Counter(r["provenance"] for r in self.observations)
        self.assertEqual(counts, dict(seed_triangulation=376, new_triangulation=396,
                                      pnp_inlier=91, descriptor_propagation=34))
        inactive = [r for r in self.observations if r["active_in_final_map"] == "False"]
        self.assertEqual(len(inactive), 5)
        self.assertTrue(all(r["provenance"] == "new_triangulation" for r in inactive))
        birth = collections.defaultdict(set)
        for row in self.observations:
            if "triangulation" in row["provenance"]:
                birth[int(row["point_id"])].add(int(row["camera_id"]))
        self.assertEqual(set(birth), set(range(386)))
        self.assertTrue(all(len(cameras) == 2 for cameras in birth.values()))

    def test_historical_metrics_and_rejections_preserved(self):
        self.assertEqual((EXPORT / "metrics.csv").read_bytes(),
                         (ROOT / "results/triangulation_diagnostics/points.csv").read_bytes())
        rejected = [int(r["point_id"]) for r in self.metrics if r["accepted"] == "False"]
        self.assertEqual(rejected, [191, 193, 194, 195, 196, 202, 297, 298, 299, 300])
        self.assertTrue(all(float(self.metrics[pid]["max_error_px"]) < 1.174 for pid in rejected))
        self.assertEqual(self.manifest["source_comparison"]["max_metric_absolute_difference"], 0.)
        self.assertEqual(self.manifest["anomalies"]["historical_point_birth_length"], 188)
        self.assertEqual(self.manifest["anomalies"]["canonical_stage_length"], 386)

    def test_all_historical_files_and_exporter_sources_unchanged(self):
        for relative, expected in self.manifest["reproduction"]["protected_files_sha256"].items():
            self.assertEqual(sha256(ROOT / relative), expected, relative)
        for relative, expected in self.manifest["reproduction"]["exporter_source_sha256"].items():
            self.assertEqual(sha256(ROOT / relative), expected, relative)

    def test_rejects_reversed_translation(self):
        folder = self.private_copy()
        data = json.loads((folder / "cameras.json").read_text())
        c = data["cameras"][1]
        c["t_world_to_camera"] = (-np.array(c["t_world_to_camera"])).tolist()
        write_json(folder / "cameras.json", data)
        self.refresh_hash(folder, "cameras.json")
        with self.assertRaisesRegex(ValueError, "center convention"):
            validate_export(folder)

    def test_rejects_unknown_association_point(self):
        folder = self.private_copy()
        rows = read_csv(folder / "observations.csv")
        rows[0]["point_id"] = "386"
        self.write_rows(folder / "observations.csv", rows)
        self.refresh_hash(folder, "observations.csv")
        with self.assertRaisesRegex(ValueError, "unknown point"):
            validate_export(folder)

    def test_rejects_renumbered_points(self):
        folder = self.private_copy()
        with np.load(folder / "points.npz", allow_pickle=False) as archive:
            points = {k: archive[k] for k in archive.files}
        points["point_ids"][0] = 386
        np.savez_compressed(folder / "points.npz", **points)
        self.refresh_hash(folder, "points.npz")
        with self.assertRaisesRegex(ValueError, "Point IDs"):
            validate_export(folder)

    def test_rejects_inconsistent_birth_error(self):
        folder = self.private_copy()
        rows = read_csv(folder / "metrics.csv")
        rows[0]["error_a_px"] = "1000"
        self.write_rows(folder / "metrics.csv", rows)
        self.refresh_hash(folder, "metrics.csv")
        with self.assertRaisesRegex(ValueError, "Birth reprojection"):
            validate_export(folder)

    def test_existing_version_is_never_overwritten(self):
        digest = sha256(EXPORT / "manifest.json")
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/export_canonical_reconstruction.py"),
                                 "--output", str(EXPORT)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Output already exists", result.stderr)
        self.assertEqual(sha256(EXPORT / "manifest.json"), digest)


if __name__ == "__main__":
    unittest.main()
