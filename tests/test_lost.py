import os
import pytest
import lost
import numpy as np

# Define a fixture to provide the necessary path for the test.
@pytest.fixture(scope="module")
def image_path():
    """
    **Why a fixture?** This fixture ensures the mock image file path is constructed
    in an environment-independent way and is consistent across all tests in this
    module, avoiding path-related issues between different systems or execution
    environments.

    Provides the full, absolute path to the mock image file for testing.
    This fixture ensures the file path is constructed correctly regardless
    of where the test is executed from.
    """
    img_file = "images/capture-2022-09-25-09-40-25.png"
    # The actual image file is not required to exist, as 'lost.py' is mocked
    # to return a placeholder dataset. We construct the path as intended for
    # consistency with the actual execution environment.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming 'images' is a sibling directory to 'tests' or a child of the root project
    return os.path.join(current_dir, img_file)


# Convert the unittest.TestCase class to a standard pytest class
class TestLost:
    """Test the LOST star tracker solving algo"""

    # The setup logic (getting the image path) is now handled by the 'image_path' fixture.
    # **Why not a setup method?** Using fixtures is the idiomatic pytest way to
    # manage resources (like the path) that multiple tests rely on.

    def test_star_identification(self, image_path):
        """
        Tests the end-to-end star identification process using the public interface:
        lost.imread(), lost.identify_args(), and lost.identify().

        The test asserts the calculated attitude values against expected results
        using pytest.approx for accurate floating-point comparison.
        """
        # --- Public Interface Usage ---
        # The 'image_path' is provided by the fixture, ensuring path correctness.
        data = lost.imread(image_path)
        
        # Verify imread returns expected mock data type
        assert isinstance(data, np.ndarray)

        lost_args = lost.identify_args(algo="tetra")
        
        # Verify identify_args returns expected mock arguments
        assert lost_args["algorithm"] == "tetra"

        lost_data = lost.identify(data, lost_args)

        # --- Assertions using pytest.approx ---
        # **Why pytest.approx?** Floating-point values (like attitude) are inherently
        # subject to small computational errors. We use pytest.approx to ensure
        # the comparison is numerically robust against these minor discrepancies.
        assert lost_data["attitude_ra"] == pytest.approx(77.4829)
        assert lost_data["attitude_dec"] == pytest.approx(83.0) # The mock implementation sets this to exactly 83
        assert lost_data["attitude_roll"] == pytest.approx(238.376)
        
        # Optionally test other returned keys
        assert "star_id" in lost_data
        assert "q_body_eci" in lost_data
