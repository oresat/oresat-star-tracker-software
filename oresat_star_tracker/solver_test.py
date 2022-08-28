import unittest
import sys

# Needs to be fixed
#sys.path.append('.')

from .solver import Solver, SolverError

class TestSolver(unittest.TestCase):
    def setUp(self):
        """ setUp """
        print("ENTERY::setUp")

        print("creating solver")
        self._solver = Solver()
        print("initializing solver")
        self._solver.startup()
        print("EXIT::setUp")

    def test_run(self):
        """ test_run """
        self.assertEqual(1, 1, "_solver_")

if __name__ == """__main__""":
    unittest.main()
