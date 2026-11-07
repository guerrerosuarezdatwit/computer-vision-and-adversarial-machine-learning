"""Backend policy tests using a fake torch module; no torch/GPU is required."""
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.device_selection import select_device


class DeviceSelectionTests(unittest.TestCase):
    def choose(self, preferred="auto", cuda=False, mps=False, missing_mps=False):
        fake = SimpleNamespace(device=lambda name: name,
                               cuda=SimpleNamespace(is_available=lambda: cuda),
                               backends=SimpleNamespace() if missing_mps else
                               SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)))
        with patch.dict(sys.modules, {"torch": fake}):
            return select_device(preferred)

    def test_auto_prioritizes_cuda(self):
        self.assertEqual(self.choose(cuda=True, mps=True), "cuda")

    def test_auto_uses_mps_when_cuda_is_absent(self):
        self.assertEqual(self.choose(mps=True), "mps")

    def test_auto_falls_back_to_cpu(self):
        self.assertEqual(self.choose(), "cpu")
        self.assertEqual(self.choose(missing_mps=True), "cpu")

    def test_explicit_cpu_overrides_available_accelerators(self):
        self.assertEqual(self.choose("cpu", cuda=True, mps=True), "cpu")

    def test_explicit_accelerators_do_not_silently_fall_back(self):
        for backend in ["cuda", "mps"]:
            with self.subTest(backend=backend), self.assertRaises(RuntimeError):
                self.choose(backend)

    def test_explicit_accelerator_can_be_selected(self):
        self.assertEqual(self.choose("cuda", cuda=True), "cuda")
        self.assertEqual(self.choose("mps", mps=True), "mps")

    def test_invalid_selection_is_rejected(self):
        with self.assertRaises(ValueError):
            select_device("gpu")


if __name__ == "__main__":
    unittest.main()
