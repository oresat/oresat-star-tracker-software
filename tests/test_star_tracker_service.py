"""
Pytest suite for the StarTrackerService, focusing on the public interface
(SDO access, start, stop) and mocking time/hardware dependencies.
"""

import pytest
import numpy as np
import time
from unittest import mock
from io import BytesIO

# Import from the correct package path
from oresat_star_tracker.star_tracker_service import (
    StarTrackerService,
    State,
    CameraError,
    CameraState,
)

# Mock external dependencies used by the service
@pytest.fixture(autouse=True)
def mock_external_deps(mocker):
    """
    Mocks hardware and external library calls.

    **Why the mocks?** The service relies on interacting with the physical
    Camera object, the computationally expensive LOST star-identification
    library, the `cv2` library for image processing, and the file system.
    Mocking these dependencies allows for fast, isolated, and reliable unit
    testing without hardware, long processing times, or I/O side effects.

    Returns a dictionary of mock objects for explicit testing.
    """
    # Mock camera (needed for StarTrackerService init)
    MockCameraCls = mocker.patch("oresat_star_tracker.star_tracker_service.Camera")
    MockCameraInstance = MockCameraCls.return_value
    MockCameraInstance.state = CameraState.RUNNING  # Assume camera is ready by default

    # Mock lost library for star identification
    mocker.patch(
        "oresat_star_tracker.star_tracker_service.lost.identify_args",
        return_value={"algo": "tetra"},
    )
    # Mock specific attitude solution return values for deterministic assertions
    mocker.patch(
        "oresat_star_tracker.star_tracker_service.lost.identify",
        return_value={
            "attitude_ra": 10.5,
            "attitude_de": 20.5,
            "attitude_roll": 30.5,
        },
    )

    # Mock file-related functions and cv2 methods
    mock_imencode = mocker.patch(
        "oresat_star_tracker.star_tracker_service.cv2.imencode", 
        return_value=(True, np.array(b'mock_jpg'))
    )
    mock_cvtColor = mocker.patch(
        "oresat_star_tracker.star_tracker_service.cv2.cvtColor", 
        return_value=np.zeros((10, 10), dtype=np.uint8)
    )
    mocker.patch("oresat_star_tracker.star_tracker_service.tiff.imwrite")
    mocker.patch("oresat_star_tracker.star_tracker_service.new_oresat_file")
    # Mock builtins.open to prevent actual file creation during image saving tests
    mocker.patch("builtins.open", mock.mock_open())

    # Mock sleep functions to prevent unnecessary delay in loop execution
    mocker.patch("oresat_star_tracker.star_tracker_service.Service.sleep")
    mocker.patch("oresat_star_tracker.star_tracker_service.Service.sleep_ms")
    
    # Return a structure of important mocks for easy access in tests
    return {
        "camera": MockCameraInstance,
        "imencode": mock_imencode,
        "cvtColor": mock_cvtColor,
    }


# Fixture for a mock CANopen Node with a valid Object Dictionary structure
@pytest.fixture
def mock_node(mocker):
    """
    Creates a mock CANopen Node with all necessary Object Dictionary (OD) entries.

    **Why mock the CANopen Node?** The StarTrackerService relies heavily on the 
    OLAF framework's CANopen interface (`node.od`, `node.add_sdo_callbacks`, etc.). 
    Mocking the node is essential to test the service's SDO interaction logic in 
    isolation, without needing a running CAN bus or the full OLAF environment.
    """
    node = mock.MagicMock()
    
    # Initialize all OD entries with mock objects that have a 'value' property
    mock_od = {
        "status": mock.MagicMock(value=State.OFF.value),
        "orientation": {
            "right_ascension": mock.MagicMock(value=0),
            "declination": mock.MagicMock(value=0),
            "roll": mock.MagicMock(value=0),
            "time_since_midnight": mock.MagicMock(value=0),
        },
        "capture": {
            "delay": mock.MagicMock(value=1),
            "duration": mock.MagicMock(value=10),
            "num_of_images": mock.MagicMock(value=0),
            "last_capture_time": mock.MagicMock(value=0),
            "save_captures": mock.MagicMock(value=True),
            "last_display_image": mock.MagicMock(),
        },
        "capture_filter": {
            "enable": mock.MagicMock(value=True),
            "lower_bound": mock.MagicMock(value=0),
            "lower_percentage": mock.MagicMock(value=0),
            "upper_bound": mock.MagicMock(value=0),
            "upper_percentage": mock.MagicMock(value=0),
        },
    }
    node.od = mock_od
    node.fread_cache = mock.MagicMock() # Used for Oresat File Transfer
    
    return node


# Fixture to initialize the service and call on_start
@pytest.fixture
def star_tracker_service(mock_node):
    """
    Initializes StarTrackerService and calls the public on_start method.

    **Why a separate service fixture?** This ensures every test starts with a 
    clean, initialized service object that has already completed the necessary 
    `on_start()` setup (like assigning the mock node and registering SDO callbacks), 
    saving boilerplate code in each test function.
    """
    service = StarTrackerService(mock_hw=True)
    service.node = mock_node # Assign mock node
    service.on_start()
    return service


# Fixture to control time for the BOOT transition
@pytest.fixture
def mock_monotonic(mocker):
    """
    Mocks time.monotonic() and time.time() to control the BOOT -> STANDBY transition.

    **Why mock the time?** The BOOT state involves a **70-second wait** before 
    transitioning to STANDBY. Mocking the time functions allows us to bypass this 
    long delay instantly, ensuring tests run efficiently.
    """
    mock_mon = mocker.patch("oresat_star_tracker.star_tracker_service.monotonic", return_value=0)
    # Patch the 'time' function directly in the service module's scope
    mock_time = mocker.patch("oresat_star_tracker.star_tracker_service.time", return_value=12345.0)
    return mock_mon, mock_time

def test_service_initial_state_and_on_start(star_tracker_service, mock_node):
    """
    Tests initialization and the public on_start method's side effects.
    1. Checks the initial state is BOOT.
    2. Checks that SDO callbacks were added correctly.

    **Why test SDO callbacks?** The `on_start()` method is critical because it 
    registers the service's public access points with the CANopen node. This test 
    verifies that the correct methods (`on_read_status`, etc.) are linked.
    """
    # 1. Check initial state
    assert star_tracker_service._state == State.BOOT

    # 2. Check SDO callbacks added to the node
    mock_node.add_sdo_callbacks.assert_any_call(
        "status", None, star_tracker_service.on_read_status, star_tracker_service.on_write_status
    )
    mock_node.add_sdo_callbacks.assert_any_call(
        "capture", "last_display_image", star_tracker_service._on_read_last_display_image, None
    )


def test_on_stop_clears_data(star_tracker_service):
    """
    Tests the public on_stop method clears internal state and OD data.

    **Why is clearing state important?** The `on_stop()` method serves as the 
    shutdown handler, ensuring that volatile internal state and Object Dictionary 
    (OD) values are reset to a known, safe state before the service terminates.
    """
    # Set mock data before stopping
    star_tracker_service._right_ascension_obj.value = 100
    star_tracker_service._last_capture = np.zeros((10, 10))
    star_tracker_service._state = State.STAR_TRACK

    # Call the public method
    star_tracker_service.on_stop()

    # Assert OD values are reset
    assert star_tracker_service._right_ascension_obj.value == 0
    assert star_tracker_service._declination_obj.value == 0
    assert star_tracker_service._time_stamp_obj.value == 0
    
    # Assert service state is OFF
    assert star_tracker_service._state == State.OFF
    # Assert internal cache is cleared
    assert star_tracker_service._last_capture is None


## Tests for Public State Control (SDO Callbacks)

def test_on_read_status_returns_current_state(star_tracker_service):
    """
    Tests the public SDO read callback for status.
    
    **Why test a simple read?** This verifies the SDO read mechanism returns the 
    service's actual internal state, which is crucial for external monitoring.
    """
    star_tracker_service._state = State.STANDBY
    
    # Assert the state value is returned
    assert star_tracker_service.on_read_status() == State.STANDBY.value


def test_on_write_status_valid_transition(star_tracker_service):
    """
    Tests a successful, valid state transition via the public SDO write callback.
    
    **Why test valid transitions?** This verifies the state machine's core logic, 
    ensuring external commands can correctly move the service into functional modes.
    """
    star_tracker_service._state = State.STANDBY # Current state
    new_state = State.STAR_TRACK.value

    # Public SDO write call
    star_tracker_service.on_write_status(new_state)

    # Assert state changed
    assert star_tracker_service._state == State.STAR_TRACK


def test_on_write_status_invalid_transition(star_tracker_service):
    """
    Tests an invalid state transition via the public SDO write callback (e.g., STAR_TRACK to BOOT).
    State should remain unchanged.

    **Why test invalid transitions?** The state machine must rigorously enforce 
    allowed state changes (e.g., preventing a direct jump from STAR_TRACK to BOOT). 
    This test verifies the rejection logic.
    """
    star_tracker_service._state = State.STAR_TRACK
    invalid_new_state = State.BOOT.value

    # Public SDO write call
    star_tracker_service.on_write_status(invalid_new_state)

    # Assert state did NOT change
    assert star_tracker_service._state == State.STAR_TRACK


def test_on_write_status_rejects_transition_from_boot(star_tracker_service):
    """
    Tests that commanded transition from BOOT state is rejected.

    **Why is BOOT rejection important?** The BOOT state is internally controlled 
    by a timer. External commands must not be allowed to prematurely transition 
    the service out of BOOT.
    """
    star_tracker_service._state = State.BOOT
    new_state = State.STANDBY.value

    # Public SDO write call
    star_tracker_service.on_write_status(new_state)

    # Assert state did NOT change
    assert star_tracker_service._state == State.BOOT


def test_on_write_status_rejects_invalid_value(star_tracker_service):
    """
    Tests that providing an undefined integer value is rejected.

    **Why reject invalid values?** To ensure robustness against corrupted SDO 
    packets or malformed commands from the CAN bus.
    """
    star_tracker_service._state = State.STANDBY
    invalid_value = 9999

    # Public SDO write call
    star_tracker_service.on_write_status(invalid_value)

    # Assert state did NOT change
    assert star_tracker_service._state == State.STANDBY


## Tests for Core Logic Triggered via Public Loop/Time

def test_boot_to_standby_transition(star_tracker_service, mock_monotonic):
    """
    Tests the critical BOOT -> STANDBY transition which is controlled by internal time.
    We mock monotonic() to bypass the 70-second wait.

    **Why is this loop tested?** The `on_loop()` method is the heart of the 
    service's asynchronous behavior. This test verifies that the time-based 
    transition logic for coming out of BOOT works as expected.
    """
    mock_mon, _ = mock_monotonic
    star_tracker_service._state = State.BOOT
    
    # 1. Time is 0, should stay in BOOT
    star_tracker_service.on_loop()
    assert star_tracker_service._state == State.BOOT

    # 2. Time passes the 70s threshold (e.g., 70.1)
    mock_mon.return_value = 70.1
    star_tracker_service.on_loop()
    
    # Assert state changed
    assert star_tracker_service._state == State.STANDBY


def test_star_track_mode_and_returns_to_standby(star_tracker_service, mock_external_deps, mock_monotonic):
    """
    Tests STAR_TRACK execution when delay is 0 (track once).
    It should perform star tracking and return to STANDBY.

    **Why test STAR_TRACK?** This verifies the end-to-end execution flow of the 
    primary service function: capture image, identify stars (mocked), update OD, 
    send TPDOs, and transition back to a waiting state.
    """
    # FIX: Access the camera mock explicitly from the returned dict
    mock_camera_instance = mock_external_deps["camera"]
    mock_camera_instance.capture.return_value = np.zeros((10, 10, 3), dtype=np.uint8)

    # Set initial state and force delay=0 (track once)
    star_tracker_service._state = State.STAR_TRACK
    star_tracker_service._capture_delay_obj.value = 0
    
    # Call loop to execute _star_track()
    star_tracker_service.on_loop()

    # 1. Assert camera capture was called
    mock_camera_instance.capture.assert_called_once()
    
    # 2. Assert star tracking data was written to the OD (RA=int(10.5) = 10)
    assert star_tracker_service._right_ascension_obj.value == 10
    
    # 3. Assert TPDOs were sent (indicating data transfer to bus)
    star_tracker_service.node.send_tpdo.assert_any_call(3)
    star_tracker_service.node.send_tpdo.assert_any_call(4)
    
    # 4. Assert service returns to STANDBY because delay was 0
    assert star_tracker_service._state == State.STANDBY
    # 5. Assert no sleep occurred (as delay was 0)
    star_tracker_service.sleep.assert_not_called()


def test_capture_only_filter_enabled_and_passes(star_tracker_service, mock_external_deps):
    """
    Tests CAPTURE_ONLY mode where the filter is enabled and passes.
    Image should be captured, saved, and image count should increment.

    **Why test filter passing?** This verifies that the image capture logic, 
    file saving mechanism (via OLAF), and successful termination/transition 
    execute correctly when a captured image meets the quality criteria.
    """
    # FIX: Access the camera mock explicitly from the returned dict
    mock_camera_instance = mock_external_deps["camera"]
    # Mock camera to return a non-empty image
    mock_camera_instance.capture.return_value = np.ones((10, 10, 3), dtype=np.uint8)
    
    # Set OD parameters to ensure one image is taken
    star_tracker_service._state = State.CAPTURE_ONLY
    star_tracker_service._capture_duration_obj.value = 5  # enough time
    star_tracker_service._image_count_obj.value = 1 # Stop after 1 image
    star_tracker_service._filter_enable_obj.value = True
    
    # Force filter to pass by setting bounds to 0 (ignored)
    star_tracker_service._lower_bound_obj.value = 0
    star_tracker_service._upper_bound_obj.value = 0 
    
    # Call loop to execute _capture_only_mode()
    star_tracker_service.on_loop()

    # 1. Assert image was saved (via tiff.imwrite and builtins.open)
    star_tracker_service.node.fread_cache.add.assert_called_once()
    
    # 2. Assert state returns to STANDBY
    assert star_tracker_service._state == State.STANDBY

def test_capture_only_filter_enabled_and_fails(star_tracker_service, mock_external_deps):
    """
    Tests CAPTURE_ONLY mode where the filter is enabled and always fails.
    The service must attempt MAX_CAPTURE_RETRIES times and then return to STANDBY.

    **Why test filter failure?** This verifies the service's fault tolerance. 
    It ensures that repeated failure to meet capture criteria triggers the retry 
    mechanism and eventually results in a safe transition out of the capture mode 
    to prevent an infinite loop.
    """
    # CRITICAL: Import the service class here to access the constant
    from oresat_star_tracker.star_tracker_service import StarTrackerService 
    
    # 1. Setup initial state and mocks
    
    # Set OD parameters to ensure we stay in the mode long enough to hit retries.
    # Set image count to 1 (it will fail to get that 1 image)
    star_tracker_service._capture_duration_obj.value = 5  
    star_tracker_service._image_count_obj.value = 1 
    star_tracker_service._filter_enable_obj.value = True
    
    # Force filter to FAIL: The mocked np.zeros image has no pixels > 0.
    star_tracker_service._lower_bound_obj.value = 1  # Threshold 
    star_tracker_service._lower_percentage_obj.value = 1 # Must have >1% bright pixels
    star_tracker_service._upper_bound_obj.value = 0 # Ignore upper bound
    
    # Get the camera instance that StarTrackerService is actually using
    mock_camera_instance = mock_external_deps["camera"]
    # Mock camera to return a blank (failing) image
    mock_camera_instance.capture.return_value = np.zeros((10, 10, 3), dtype=np.uint8)

    # Set the state to the correct mode for this test
    star_tracker_service._state = State.CAPTURE_ONLY
    
    # 2. Run the test (executes _capture_only_mode and runs retries)
    star_tracker_service.on_loop() # <--- Only runs ONCE
    
    # 3. Assertions
    
    # CORRECT ASSERTION: Check the actual call count property.
    assert mock_camera_instance.capture.call_count == StarTrackerService.MAX_CAPTURE_RETRIES
    
    # Assert that no image was successfully saved
    star_tracker_service.node.fread_cache.add.assert_not_called()
    
    # Assert that the service returned to STANDBY after exhausting retries.
    assert star_tracker_service._state == State.STANDBY

    # Clean up state to prevent interference with other tests
    star_tracker_service.on_write_status('BOOT')
    pass

def test_on_read_last_display_image_success(star_tracker_service, mock_external_deps):
    """
    Tests the public SDO read callback for reading the last captured image.
    Asserts correct downscaling and encoding is attempted.

    **Why test image read?** This verifies the internal process of preparing the 
    last captured image for transfer via the CAN bus (downscaling, color conversion, 
    and JPEG encoding) is performed correctly before the data is returned.
    """
    # 1. Setup internal state
    mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
    star_tracker_service._last_capture = mock_image
    
    # 2. Call public SDO read
    encoded_bytes = star_tracker_service._on_read_last_display_image()
    
    # 3. Assert result is the mocked encoded byte array
    assert encoded_bytes == b'mock_jpg'
    
    # FIX: Assert that the cv2.imencode function was actually called
    mock_external_deps["imencode"].assert_called_once()
    # FIX: Assert that cv2.cvtColor was called for downscaling/conversion
    mock_external_deps["cvtColor"].assert_called_once()


def test_on_read_last_display_image_no_capture(star_tracker_service):
    """
    Tests the public SDO read callback when no capture has occurred.

    **Why is this test necessary?** To ensure the service returns a safe, empty 
    value (empty bytes) rather than crashing or returning stale data when the 
    internal capture buffer is empty.
    """
    star_tracker_service._last_capture = None
    
    # Call public SDO read
    encoded_bytes = star_tracker_service._on_read_last_display_image()
    
    # Assert empty bytes are returned
    assert encoded_bytes == b""
