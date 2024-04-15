"""test LOST attitude solver"""

import unittest

import lost


class Test_lost(unittest.TestCase):

    filename = "png_samples/capture-2022-10-16-12-55-56.png"
    
    data = lost.imread(filename)
    lost_data = lost.identify(data, lost.identify_args(algo="tetra"))
    
    print(lost_data["attitude_ra"])
    print(lost_data["attitude_de"])
    print(lost_data["attitude_roll"])

if __name__ == "__main__":
    # unittest.main()
    unittest.main(verbosity=2)
