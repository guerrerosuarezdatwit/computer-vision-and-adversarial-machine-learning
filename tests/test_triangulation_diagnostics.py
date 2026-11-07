"""Synthetic geometry checks: a perfect reprojection can still have weak depth."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.triangulation_diagnostics import (
    pair_metrics, classify, statistics, export_diagnostics,
)


class GeometryDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.K = np.array([[800., 0, 450], [0, 800, 300], [0, 0, 1]])
        self.a = (np.eye(3), np.zeros((3, 1)))
        self.b = (np.eye(3), np.array([[-1.], [0], [0]]))

    def project(self, points, pose):
        R, t = pose
        h = (points @ R.T + t.reshape(3)) @ self.K.T
        with np.errstate(divide='ignore', invalid='ignore'):
            return h[:, :2] / h[:, 2:3]

    def rows(self, X, scale=1.):
        poses = [(R, t*scale) for R, t in (self.a, self.b)]
        X = np.array(X, dtype=float).reshape(-1, 3)*scale
        metrics = pair_metrics(X, *(self.project(X, p) for p in poses), *poses, self.K)
        rows = []
        for i, point in enumerate(X):
            r = dict(point_id=i, origin='Seed 03-04', x=point[0], y=point[1], z=point[2],
                     view_a=3, view_b=4, associated_observations=2,
                     associated_max_error_px=0., associated_min_depth=point[2])
            r.update({k: float(v[i]) for k, v in metrics.items()})
            r['depth_baselines'] = r['max_depth']/scale
            rows.append(r)
        return rows

    def test_perfect_reprojection_does_not_imply_good_geometry(self):
        rows = self.rows([[.5, 0, 4], [.5, 0, 10000]])
        self.assertLess(max(r['max_error_px'] for r in rows), 1e-9)
        mask, reasons = classify(rows)
        self.assertEqual(mask.tolist(), [True, False])
        self.assertIn('angle', reasons[1])
        self.assertIn('depth', reasons[1])
        self.assertNotIn('reprojection', reasons[1])

    def test_scale_invariance(self):
        X = [[.5, 0, 4], [.5, 0, 10000]]
        a, b = self.rows(X), self.rows(X, scale=17.)
        np.testing.assert_array_equal(classify(a)[0], classify(b)[0])
        for field in ['effective_angle_deg', 'depth_baselines', 'max_error_px']:
            np.testing.assert_allclose([r[field] for r in a], [r[field] for r in b], atol=1e-10)

    def test_cheirality_and_undefined_rays(self):
        rows = self.rows([[.5, 0, -4], [0, 0, 0]])
        mask, reasons = classify(rows)
        self.assertFalse(mask.any())
        self.assertIn('cheirality', reasons[0])
        self.assertIn('nonfinite', reasons[1])

    def test_depth_uses_camera_frame(self):
        R = np.array([[0., 0, 1], [0, 1, 0], [-1, 0, 0]])
        pose = (R, np.array([[0], [0], [10.]]))
        X = np.array([[1., 0, 4]])
        metrics = pair_metrics(X, self.project(X, self.a), self.project(X, pose), self.a, pose, self.K)
        self.assertEqual(metrics['depth_a'][0], 4.)
        self.assertEqual(metrics['depth_b'][0], 9.)

    def test_association_errors_are_optional_and_separate(self):
        rows = self.rows([[.5, 0, 4]])
        rows[0]['associated_max_error_px'] = 30.
        self.assertTrue(classify(rows)[0][0])
        mask, why = classify(rows, check_associations=True)
        self.assertFalse(mask[0])
        self.assertEqual(why[0], ['associations'])

    def test_boundaries_and_empty_subsets(self):
        rows = self.rows([[.5, 0, 4]])
        self.assertTrue(classify(rows, min_angle=rows[0]['effective_angle_deg'],
                                 max_error=rows[0]['max_error_px'], max_depth_baselines=4.)[0][0])
        self.assertEqual(statistics(rows, [False])['count'], 0)
        self.assertIsNone(statistics([])['max_depth'])
        self.assertEqual(classify([])[0].size, 0)
        with self.assertRaises(ValueError): classify(rows, min_angle=-1)

    def test_offline_export_with_nonfinite_point(self):
        rows = self.rows([[.5, 0, 4], [0, 0, 0]])
        with tempfile.TemporaryDirectory() as folder:
            path, summary = export_diagnostics(rows, {3: self.a, 4: self.b}, folder)
            html = path.read_text()
            self.assertEqual(summary['before']['count'], 2)
            self.assertEqual(summary['after']['count'], 1)
            self.assertIn('plotly.js', html)
            self.assertNotIn('__ROWS__', html)
            self.assertNotIn('__THRESHOLDS__', html)
            self.assertTrue((Path(folder)/'points.csv').exists())
            self.assertTrue((Path(folder)/'summary.json').exists())


if __name__ == '__main__':
    unittest.main()
