"""
Test suite for the StarTracker Camera module (camera.py).

This module uses pytest to test the public interface of the Camera class.
It focuses primarily on the mock functionality to ensure test reliability
**by avoiding the reliance on real hardware, long boot-up sequences, and
file system access, which are costly or complicated to manage in a CI/CD environment.**
"""

import pytest
import numpy as np
import time
from unittest import mock
# FIX: Changed the import path to reference the file within the main package
from oresat_star_tracker.camera import Camera, CameraState, CameraError

# Constants for checking mock results
MOCK_COLS = 1280
MOCK_ROWS = 960
EXPECTED_IMAGE_SIZE = (MOCK_COLS, MOCK_ROWS)

#-------------------------------------------------------------------------------
## Fixtures
#-------------------------------------------------------------------------------

@pytest.fixture
def mock_camera():
    """
    Initializes a Camera instance in mock mode and ensures it is in the RUNNING state.

    **Why this fixture is necessary:**
    1. **Avoids Hardware Dependency:** It initializes the camera with `mock=True`
       to ensure tests run without requiring a physical camera or its drivers.
    2. **Bypasses Lockout Time:** It calls `test_camera.unlock()` immediately
       to simulate the successful passage of the **long 90-second lock-out timer**
       defined in `Camera.__init__()`. This is crucial for **efficient, instantaneous**
       unit testing.

    The fixture yields a fully initialized and immediately ready camera instance.
    """
    # Initialize the camera in mock mode
    test_camera = Camera(mock=True)

    # In a real scenario, this is an internal Timer call. We manually call it
    # here to simulate the 90s timeout passing instantly.
    test_camera.unlock()
    
    # Ensure the camera is actually ready before yielding
    assert test_camera.state == CameraState.RUNNING
    
    # Yield the fully initialized and ready camera instance
    return test_camera

#-------------------------------------------------------------------------------
## Tests
#-------------------------------------------------------------------------------

def test_initial_state_is_lockout():
    """
    Test that the camera's initial public 'state' property is LOCKOUT before the timer runs.

    **Why the mocks?** We use `mock.patch` on `time.monotonic` and the internal 
    `Timer` class to **guarantee** that the asynchronous lockout timer thread 
    never starts or executes the `unlock()` method. This ensures we test the 
    true immediate post-initialization state.
    """
    # Use a dummy Timer mock to prevent the Timer thread from actually starting and calling unlock()
    with mock.patch.object(time, 'monotonic', return_value=0):
        with mock.patch('oresat_star_tracker.camera.Timer'): # FIX: Updated the mock target path
            cam = Camera(mock=True)
            # The Timer should not have run yet, so the state remains LOCKOUT
            assert cam.state == CameraState.LOCKOUT


def test_state_is_running(mock_camera):
    """
    Tests that the camera is in the RUNNING state after the fixture's setup
    (simulating the successful passage of the 90-second lockout).
    
    **Why is this test needed?** It verifies that the setup logic within the 
    `mock_camera` fixture successfully transitions the camera state, which is a 
    pre-requisite for all functional tests.
    """
    # The fixture mock_camera ensures unlock() has been called successfully
    assert mock_camera.state == CameraState.RUNNING


def test_read_image_size(mock_camera):
    """
    Tests the public interface 'read_image_size' returns the expected mock dimensions.
    
    **Why is this important?** It verifies that the mock implementation within 
    `camera.py` provides the expected dimensions that other parts of the system 
    (like the LOST algorithm) rely on.
    """
    # read_image_size is a public method and should be tested directly
    size = mock_camera.read_image_size()

    # The mock path in camera.py returns the internal _image_size
    assert size == EXPECTED_IMAGE_SIZE


def test_capture_returns_correct_mock_data(mock_camera):
    """
    Tests the public 'capture' method for the mock case, ensuring it returns
    a NumPy array of the correct shape and type.
    
    **Why test the mock data?** Other modules depend on `capture` returning a 
    specific, standardized `numpy.ndarray` object. This test ensures the mock 
    satisfies this contract without executing actual hardware read operations.
    """
    # Test with default color=True (mock returns a 3D array)
    img_color = mock_camera.capture(color=True)
    assert isinstance(img_color, np.ndarray)
    # Mock data is initialized as (1280, 960, 3) in mock mode (W, H, Channels)
    # Note: Camera implementation uses (MAX_COLS, MAX_ROWS, 3) for the mock data
    assert img_color.shape == (MOCK_COLS, MOCK_ROWS, 3)
    assert img_color.dtype == np.uint8

    # Test with color=False (mock returns a 3D array regardless in the current implementation,
    # but based on the code in `capture`, it should return the mock data which is (1280, 960, 3)).
    # We will assert against the mocked data's shape as currently implemented.
    img_mono = mock_camera.capture(color=False)
    assert img_mono.shape == (MOCK_COLS, MOCK_ROWS, 3)


def test_public_methods_raise_error_when_locked(mocker):
    """
    Tests that public methods raise CameraError if the camera is not RUNNING.
    This simulates an external component trying to read/capture too early.
    
    **Why the mock?** We use `mocker.patch` on `Camera.unlock` to **prevent** the camera from ever leaving the `LOCKOUT` state. This isolates the test 
    to ensure that the state guard logic functions correctly when the camera 
    is in a prohibited state.
    """
    # FIX: Patch the internal method responsible for the state transition BEFORE instantiating Camera.
    # This prevents the transition from LOCKOUT to RUNNING. We use the context manager form
    # of mocker.patch to ensure it's active for the duration of the test.

    mocker.patch('oresat_star_tracker.camera.Camera.unlock') 
    cam = Camera(mock=True)
    
    # The state is LOCKOUT immediately after init, before the timer fires
    assert cam.state == CameraState.LOCKOUT
    
    # Define a list of public methods that should fail
    methods_to_test = [
        (cam.capture, (False,)),
        (cam.read_image_size, ()),
    ]
    
    for method, args in methods_to_test:
        with pytest.raises(CameraError) as excinfo:
            method(*args)
        # Check that the error message includes the current state
        assert f"state is {CameraState.LOCKOUT}" in str(excinfo.value)
    pass

# Note on read_context_setting:
# This method inherently relies on accessing /sys files, which is not possible
# without system access. **Why omit this test?** Testing it would require deep 
# patching of the 'open' built-in, which adds complexity and is better reserved 
# for system-level integration tests, rather than unit tests focused on the 
# mock functionality and public interface flow.