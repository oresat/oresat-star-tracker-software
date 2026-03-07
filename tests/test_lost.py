import numpy as np
from PIL import Image
import unittest

from pathlib import Path

from oresat_star_tracker.lost_py_wrapper import lost


class TestLost(unittest.TestCase):
    test_root = Path(__file__).resolve().parent
    proj_root = test_root.parent
    images_root = test_root / 'images'
    lpw_root = proj_root / 'oresat_star_tracker' / 'lost_py_wrapper'
    db_def_path = lpw_root / 'data' / 'py-database.dat'

    db_def_args = {
        'database': None,
        '--max-stars': 5000,
        '--kvector': None,
        '--kvector-min-distance': 0.2,
        '--kvector-max-distance': 15.0,
        '--kvector-distance-bins': 10000,
        '--output': db_def_path,
    }

    def assertIsFile(self, path):
        if not Path(path).resolve().is_file():
            raise AssertionError("File does not exist: %s" % str(path))

    def testDatabaseArgs(self):
        args = lost.database_args()

        self.assertEqual(args, self.db_def_args)

    def testDatabase(self):
        # generate a database for the LOST solver
        lost.database()

        self.assertIsFile(self.db_def_path)

    def testEstimation(self):

        # get path to test image
        img_path = self.images_root / 'img_7660.png'

        # convert to np.ndarry
        im = np.array(Image.open(str(img_path)))
        estimation = lost.estimate(im)

        self.assertAlmostEqual(estimation['attitude_ra'], 17.9868, places=4)
        self.assertAlmostEqual(estimation['attitude_de'], 63.4233, places=4)
        self.assertAlmostEqual(estimation['attitude_roll'], 12.238, places=4)
        self.assertAlmostEqual(estimation['attitude_i'], 0.00786371, places=4)
        self.assertAlmostEqual(estimation['attitude_j'], 0.5304, places=4)
        self.assertAlmostEqual(estimation['attitude_k'], -0.0768838, places=4)
        self.assertAlmostEqual(estimation['attitude_real'], 0.844218, places=4)

    if __name__ == '__main__':
        unittest.main()
