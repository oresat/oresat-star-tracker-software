"""Tests for the in-process LOST `_lost_core` extension (optional build)."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import oresat_star_tracker._lost_core as _lost_core
except ImportError:
    _lost_core = None  # type: ignore[assignment, misc]

from oresat_star_tracker.lost.wrapper import database


@unittest.skipUnless(_lost_core is not None, "_lost_core not importable")
class TestLostNative(unittest.TestCase):
    test_root = Path(__file__).resolve().parent
    proj_root = test_root.parent
    images_root = test_root / "images"
    db_path = proj_root / "oresat_star_tracker" / "lost" / "data" / "py-database.dat"

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["ORESAT_LOST_DATABASE"] = str(cls.db_path.resolve())

    def test_estimate_golden_quaternion(self) -> None:
        if not self.db_path.is_file():
            database()

        img_path = self.images_root / "img_7660.png"
        gray = np.ascontiguousarray(
            np.asarray(Image.open(str(img_path)).convert("L"), dtype=np.uint8)
        )
        q = _lost_core.estimate(gray)
        self.assertEqual(q.shape, (4,))
        self.assertTrue(np.all(np.isfinite(q)), q)

        self.assertAlmostEqual(float(q[0]), 0.00786371, places=4)
        self.assertAlmostEqual(float(q[1]), 0.5304, places=4)
        self.assertAlmostEqual(float(q[2]), -0.0768838, places=4)
        self.assertAlmostEqual(float(q[3]), 0.844218, places=4)


if __name__ == "__main__":
    unittest.main()
