"""Validate the real Experiment 02 recording; no experiments are rerun here."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

from src.canonical_reconstruction import sha256
from src.track_verification import compare_variants, load_frozen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/experiments/02_track_verification/v1"
RECORDING = OUTPUT / "track_verification.rrd"


@unittest.skipUnless(importlib.util.find_spec("rerun") and RECORDING.exists(), "Generate the private Experiment 02 RRD with SDK 0.42.0.")
class TrackRecordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_frozen(ROOT / "results/canonical_reconstruction/v1")
        cls.report, cls.decisions = compare_variants(cls.data)

    def test_actual_serialized_decisions_images_coordinates_and_geometry(self):
        from src.rerun_track_experiment import validate_track_recording
        result = validate_track_recording(RECORDING, self.data, self.report, self.decisions, ROOT)
        self.assertEqual(result["serialized_association_decisions"], 170)
        self.assertEqual(result["original_point_ids"], 386)

    def test_layout_has_baseline_policy_and_variant_navigation(self):
        from rerun.chunk import RrdReader
        reader = RrdReader(RECORDING)
        text = "\n".join(c.format(trim_metadata_keys=False) for c in reader.stream(store=reader.blueprints()[0]))
        for label in ["gate_variant", "baseline", "policy", "Camera 06", "All 34 proposal decisions"]:
            self.assertIn(label, text)

    def test_saved_reports_match_the_recording_and_frozen_payload(self):
        metadata = json.loads((OUTPUT / "validation.json").read_text())
        self.assertEqual(sha256(RECORDING), metadata["recording_sha256"])
        self.assertEqual(json.loads((OUTPUT / "comparison.json").read_text()), self.report)
        for name, h in metadata["canonical_files_sha256"].items():
            self.assertEqual(sha256(self.data["folder"] / name), h)
        for name, h in metadata["source_files_sha256"].items():
            self.assertEqual(sha256(ROOT / name), h)

    def test_cli_refuses_to_overwrite_existing_experiment(self):
        before = sha256(RECORDING)
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/run_track_verification_experiment.py")],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Output already exists", result.stderr)
        self.assertEqual(sha256(RECORDING), before)


if __name__ == "__main__":
    unittest.main()
