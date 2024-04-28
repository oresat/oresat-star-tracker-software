"""
test LOST attitude solver
*must use sudo for Lost program to work
"""

import os
import unittest

import lost


class TestLost(unittest.TestCase):
    """Test the LOST star tracker solving algo"""

    img_file = "./images/capture-2022-09-25-09-40-25.png"
    current_dir = os.path.dirname(__file__)
    path = os.path.join(current_dir, img_file)

    data = lost.imread(path)
    lost_args = lost.identify_args(algo="tetra")
    lost_data = lost.identify(data, lost_args)

    assert int(lost_data["attitude_ra"]) == 77.4829
    assert int(lost_data["attitude_de"]) == 83.44
    assert int(lost_data["attitude_roll"]) == 238.376
