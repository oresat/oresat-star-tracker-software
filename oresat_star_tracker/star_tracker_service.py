"""Star Tracker service"""

from enum import IntEnum
from io import BytesIO
from time import monotonic, time

import canopen
import cv2
import lost
import numpy as np
import tifffile as tiff
from olaf import Service, logger, new_oresat_file

from .camera import Camera, CameraError, CameraState


class State(IntEnum):
    """All star tracker states."""

    OFF = 0x0
    BOOT = 0x1
    STANDBY = 0x2
    LOW_POWER = 0x3
    STAR_TRACK = 0x4
    CAPTURE_ONLY = 0x5
    ERROR = 0xFF


STATE_TRANSISTIONS = {
    # Why these transitions? They define the valid paths through the service's 
    # state machine, enforced by the `on_write_status` SDO callback.
    State.OFF: [State.BOOT],
    State.BOOT: [State.STANDBY],
    State.STANDBY: [State.LOW_POWER, State.STAR_TRACK, State.CAPTURE_ONLY],
    State.LOW_POWER: [State.STANDBY, State.STAR_TRACK, State.CAPTURE_ONLY],
    State.STAR_TRACK: [State.STANDBY, State.LOW_POWER, State.CAPTURE_ONLY, State.ERROR],
    State.CAPTURE_ONLY: [State.STANDBY, State.LOW_POWER, State.STAR_TRACK, State.ERROR],
    State.ERROR: [State.OFF],
}
"""Valid status transistions."""


class StarTrackerService(Service):
    """Star Tracker service."""

    # CRASH PREVENTION: Define a maximum number of times to retry a capture 
    # if the filter fails. 
    # **Why is this constant here?** It prevents the service from entering an 
    # **infinite loop (livelock)** if the camera consistently returns unusable 
    # images while in CAPTURE_ONLY mode.
    MAX_CAPTURE_RETRIES = 10 

    def __init__(self, mock_hw: bool = False):
        # **Why the mock_hw flag?** This flag allows unit tests to run the 
        # service logic without requiring the actual camera hardware or drivers, 
        # making automated testing efficient and platform-independent.
        super().__init__()

        self.mock_hw = mock_hw
        self._state = State.BOOT

        if self.mock_hw:
            logger.debug("mocking camera")
        else:
            logger.debug("not mocking camera")

        # The camera instance is created based on the mock_hw flag, abstracting 
        # the hardware interface for the rest of the service.
        self._camera = Camera(self.mock_hw)
        self._last_capture = None

        self.status_obj: canopen.objectdictionary.Variable = None
        self._right_ascension_obj: canopen.objectdictionary.Variable = None
        self._declination_obj: canopen.objectdictionary.Variable = None
        self._orientation_obj: canopen.objectdictionary.Variable = None
        self._time_stamp_obj: canopen.objectdictionary.Variable = None
        self._capture_delay_obj: canopen.objectdictionary.Variable = None
        self._capture_duration_obj: canopen.objectdictionary.Variable = None
        self._image_count_obj: canopen.objectdictionary.Variable = None
        self._last_capture_time: canopen.objectdictionary.Variable = None
        self._save_obj: canopen.objectdictionary.Variable = None
        self._filter_enable_obj: canopen.objectdictionary.Variable = None
        self._lower_bound_obj: canopen.objectdictionary.Variable = None
        self._lower_percentage_obj: canopen.objectdictionary.Variable = None
        self._upper_bound_obj: canopen.objectdictionary.Variable = None
        self._upper_percentage_obj: canopen.objectdictionary.Variable = None

    def on_start(self):
        """
        Registers SDO callbacks and caches references to OD object variables.
        
        **Why cache object references?** Accessing Object Dictionary (OD) entries 
        via dictionary lookups (`self.node.od["key"]`) is slower than direct 
        variable access. Caching these references significantly speeds up the 
        tight control loops (`on_loop`, `_star_track`, etc.) which read/write them frequently.
        """
        # ... (saving references to OD variables)
        self.status_obj = self.node.od["status"]

        orientation_rec = self.node.od["orientation"]
        self._right_ascension_obj = orientation_rec["right_ascension"]
        self._declination_obj = orientation_rec["declination"]
        self._orientation_obj = orientation_rec["roll"]
        self._time_stamp_obj = orientation_rec["time_since_midnight"]

        capture_rec = self.node.od["capture"]
        self._capture_delay_obj = capture_rec["delay"]
        self._capture_duration_obj = capture_rec["duration"]
        self._image_count_obj = capture_rec["num_of_images"]
        self._last_capture_time = capture_rec["last_capture_time"]
        self._save_obj = capture_rec["save_captures"]

        filter_rec = self.node.od["capture_filter"]
        self._filter_enable_obj = filter_rec["enable"]

        image_filter_rec = self.node.od["capture_filter"]
        self._lower_bound_obj = image_filter_rec["lower_bound"]
        self._lower_percentage_obj = image_filter_rec["lower_percentage"]
        self._upper_bound_obj = image_filter_rec["upper_bound"]
        self._upper_percentage_obj = image_filter_rec["upper_percentage"]

        # **Why add SDO callbacks here?** These are the public access points 
        # for reading/writing status and data from the CAN bus. They must be 
        # registered during `on_start` to activate bus communication.
        self.node.add_sdo_callbacks("status", None, self.on_read_status, self.on_write_status)
        self.node.add_sdo_callbacks(
            "capture", "last_display_image", self._on_read_last_display_image, None
        )

        self._state = State.BOOT

    def on_stop(self):
        """
        When service stops clear star tracking data.

        **Why clear the data?** This ensures that volatile, calculated data (like 
        attitude and last capture) are reset to a known, safe state (`0` or `None`) 
        before the service fully terminates or is restarted.
        """

        self._right_ascension_obj.value = 0
        self._declination_obj.value = 0
        self._orientation_obj.value = 0
        self._time_stamp_obj.value = 0
        self._last_capture = None
        self._last_capture_time.value = 0
        self._state = State.OFF

    def _encode(self, data: np.ndarray, ext: str = ".tiff") -> np.ndarray:
        """
        Wrap opencv's encode function to throw exception.

        **Why wrap imencode?** `cv2.imencode` returns a success boolean (`ok`) 
        and the encoded data. Wrapping it ensures a Python exception is raised 
        on failure, providing better error handling than simply checking the 
        boolean in the calling function.
        """

        ok, encoded = cv2.imencode(ext, data)
        if not ok:
            raise ValueError(f"{ext} encode error")

        return encoded

    def _encode_compress_tiff(self, data: np.ndarray, meta=None) -> np.ndarray:
        """
        Encode as an compress tiff.

        **Why use tifffile and BytesIO?** We need to generate a compressed TIFF 
        file in memory (`BytesIO`) to save bandwidth before transferring it to the 
        file cache. `tifffile` provides excellent control over compression and metadata.
        """

        buff = BytesIO()
        tiff.imwrite(
            buff,
            data,
            dtype=data.dtype,
            metadata=meta,
        )

        # Get the encoded TIFF data from the memory file
        encoded_data = buff.getvalue()

        # Convert the encoded TIFF data to a NumPy array
        return np.frombuffer(encoded_data, dtype=np.uint8)

    def _save_to_cache(self, file_keyword: str, encoded_data: np.ndarray, ext: str = ".tiff"):
        """
        Saves the encoded image data to a temporary file and registers it for 
        ORESat File Transfer (OFT) cache.

        **Why the two steps (save and cache)?** 1. Saves the file to disk (`/tmp/`) using an OLAF-formatted name (`new_oresat_file`).
        2. Registers the file path in the `fread_cache`, making it available 
           for external OFT read requests from the CAN bus.
        """
        # save capture
        name = "/tmp/" + new_oresat_file(file_keyword, ext=ext)
        with open(name, "wb") as f:
            f.write(encoded_data.tobytes())
        logger.info(f"saved new capture {name}")

        # add capture to fread cache
        self.node.fread_cache.add(name, consume=True)

    def _filter(self, img: np.ndarray) -> bool:
        """
        Checks if the image meets the configured brightness/dimness criteria 
        set in the Object Dictionary.

        **Why use a filter?** To ensure only high-quality star field images are 
        kept and saved to cache, preventing wasted storage on unusable images 
        (e.g., completely dark images, or overly saturated ones).
        """
        # If both bounds are ignored, return
        if self._lower_bound_obj.value == 0 and self._upper_bound_obj.value == 0:
            return True

        # Convert the BGR image to grayscale
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check that enough pixels are bright enough
        if self._lower_bound_obj.value != 0:
            # Threshold the grayscale image for brightness check
            bright_binary_image = np.where(gray_img > self._lower_bound_obj.value, 1, 0)
            # Calculate the mean of lit pixels in the original grayscale image
            lit_mean = np.mean(bright_binary_image) * 100

            # Check if the mean exceeds the threshold
            if lit_mean < self._lower_percentage_obj.value:
                return False

        # Check that enough pixels are dim enough
        if self._upper_bound_obj.value != 0:
            # Threshold the grayscale image for dimness check
            dim_binary_image = np.where(gray_img < self._upper_bound_obj.value, 1, 0)
            # Calculate the mean of dim pixels in the original grayscale image
            dim_mean = np.mean(dim_binary_image) * 100

            if dim_mean < self._upper_percentage_obj.value:
                return False

        return True

    def _star_track(self):
        """Star track once."""

        # Take the image
        ts = time()
        try:
            data = self._camera.capture()
        except Exception:
            self._state = State.ERROR
            logger.error("Camera capture failure")
            logger.info(f"changing status: {self._state.name} -> {State.STANDBY.name}")
            return

        # **Why call lost.identify?** This is the core logic responsible for 
        # converting the star field image into attitude data (RA, DEC, Roll).
        lost_args = lost.identify_args(algo="tetra")
        lost_data = lost.identify(data, lost_args)

        # Update the calculated attitude values in the Object Dictionary
        self._right_ascension_obj.value = int(lost_data["attitude_ra"])
        self._declination_obj.value = int(lost_data["attitude_de"])
        self._orientation_obj.value = int(lost_data["attitude_roll"])

        self._time_stamp_obj.value = int(ts)
        self._last_capture_time.value = int(ts)
        self._last_capture = data

        # **Why send TPDOs?** TPDOs (Transmit Process Data Objects) are essential 
        # for time-critical data. Sending them pushes the newly calculated attitude 
        # data onto the CAN bus immediately for other modules to use.
        self.node.send_tpdo(3)
        self.node.send_tpdo(4)

        # If the frequency is 0, star track once
        if self._capture_delay_obj.value == 0:
            logger.info(f"changing status: {self._state.name} -> {State.STANDBY.name}")
            self._state = State.STANDBY
        else:
            self.sleep(self._capture_delay_obj.value)


    def _capture_only_mode(self):
        """
        Uses the camera to take images for a specified duration or count, 
        optionally applying a filter and saving the results.
        """

        img_count = 0
        start_timestamp = time()

        # The main loop continues as long as time or image count limits aren't hit.
        while time() - start_timestamp < self._capture_duration_obj.value and (
            self._image_count_obj.value == 0 or img_count < self._image_count_obj.value
        ):
            # NEW: Implement a retry mechanism for a single capture attempt
            retries = 0
            capture_data = None

            # **Why this inner while loop?** This loop implements the retry logic 
            # to handle temporary capture failures or images that fail the filter. 
            # It attempts to capture MAX_CAPTURE_RETRIES times before giving up on 
            # the current capture cycle.
            while retries < self.MAX_CAPTURE_RETRIES:
                ts = time() # Take a new timestamp for each capture attempt
                try:
                    data = self._camera.capture()
                except Exception:
                    self._state = State.ERROR
                    logger.error("Camera capture failure")
                    logger.info(f"changing status: {self._state.name} -> {State.STANDBY.name}")
                    return # Exit the function entirely on hard camera error

                # Check if image passes filter
                if not self._filter_enable_obj.value or self._filter(data):
                    capture_data = data # Capture successful (or filter disabled/passed)
                    logger.debug(f"capture passed filter on retry {retries}")
                    break
                
                # Filter failed, increment retry count and try again immediately
                logger.debug(f"capture did not pass filter (retry {retries+1}/{self.MAX_CAPTURE_RETRIES})")
                retries += 1
                
                # CRASH PREVENTION: Add a very short sleep between retries to 
                # **prevent 100% CPU lock in a tight loop on real hardware**.
                self.sleep_ms(10) 
            
            # If capture_data is None, it means retries were exhausted and filter never passed.
            if capture_data is None:
                logger.warning(
                    f"Capture filter failed {self.MAX_CAPTURE_RETRIES} times. Aborting capture cycle."
                )
                break # Break out of the main 'while' loop.
            
            # If we reach here, we have a valid image (`capture_data`).
            self._last_capture_time.value = int(ts)
            self._last_capture = capture_data
            img_count += 1
            logger.info(f"capture {img_count}")

            if self._save_obj.value:
                # Use the successfully captured data
                self._save_to_cache("img", self._encode_compress_tiff(capture_data))  

            # Sleep for the user-defined delay *after* a successful capture
            self.sleep_ms(self._capture_delay_obj.value)

        if img_count == 0:
            logger.info("no images taken, check camera mode settings and filter")

        logger.info(f"changing status: {self._state.name} -> {State.STANDBY.name}")
        self._state = State.STANDBY

    def on_loop(self):
        """
        The main loop handler. This method controls state-based execution.
        
        **Why is this structure used?** It enforces a time-driven state machine. 
        Critical, long-running processes (`_star_track`, `_capture_only_mode`) 
        are executed based on the current state.
        """
        if self._state == State.BOOT and monotonic() > 70:
            # **Why 70 seconds?** This duration is mandated by the power-on 
            # self-test time required before the star tracker is considered operational.
            self._state = State.STANDBY
        elif self._state == State.STAR_TRACK:
            self._star_track()
        elif self._state == State.CAPTURE_ONLY:
            self._capture_only_mode()
        else:
            self.sleep(0.1)

    def on_loop_error(self, error: Exception):
        """
        Handles unhandled exceptions from the on_loop method.

        **Why handle errors here?** This provides a centralized fault handler. 
        It attempts to differentiate between recoverable errors (`ValueError`) 
        and critical errors (`CameraError`) that necessitate a transition to the 
        `ERROR` state.
        """
        if error is CameraError:
            logger.critical(error)
            self._state = State.ERROR
        elif error is ValueError:
            logger.error(error)
        else:
            logger.critical(f"Unkown error {error}")
        self._state = State.ERROR

    def on_read_status(self) -> int:
        """SDO read callback for star tracker status. Returns the current state value."""

        return self._state.value

    def on_write_status(self, value: int):
        """
        SDO write callback for star tracker status. Handles state transition commands.

        **Why the checks before transition?** A transition is only allowed if:
        1. The camera isn't locked/errored.
        2. The target state is a valid `State` enumeration member.
        3. The transition path is defined in `STATE_TRANSISTIONS` (e.g., cannot 
           jump from STANDBY to OFF).
        4. The current state is not BOOT (which is time-controlled).
        """
        new_status = self._state

        if self._camera.state == CameraState.LOCKOUT:
            logger.error("Cannot transition camera to lockout state")
        elif self._camera.state == CameraState.ERROR:
            logger.error("Camera is in error state")
            new_status = State.ERROR
        else:
            try:
                new_status = State(value)
            except ValueError:
                logger.error(f"invalid state: {value}")
                return

        if new_status == self._state:
            return  # nothing to change

        if self._state == State.BOOT:
            logger.error("cannot transfer out of BOOT state by command")
            return

        if new_status not in STATE_TRANSISTIONS[self._state]:
            logger.error(f"invalid status change: {self._state.name} -> {new_status.name}")
            return

        # When entering low power status, turn on low power mode
        # if new_status == State.LOW_POWER and self._state != State.LOW_POWER:
        #    set_cpufreq_gov('powersave')
        #    # Turn off PRUs/sensor
        # When leaving power status, turn off low power mode
        # elif self._state == State.LOW_POWER and new_status != State.LOW_POWER:
        #    set_cpufreq_gov('performance')
        #    # Turn on PRUs/sensor

        logger.info(f"changing status: {self._state.name} -> {new_status.name}")
        self._state = new_status

    def _on_read_last_display_image(self) -> bytes:
        """
        SDO read callback for the last captured image. Encodes the image to JPG 
        for efficient transfer over the CAN bus.

        **Why downscale and convert to JPG?** The raw image is too large for 
        efficient transfer. Downscaling reduces size, and JPEG encoding provides 
        lossy compression suitable for display/preview. Conversion to RGB is 
        needed because the camera/OpenCV uses BGR by default.
        """
        if self._last_capture is None:
            return b""
        
        data = np.copy(self._last_capture)
        
        # downscale image
        downscale_factor = 2
        data = data[::downscale_factor, ::downscale_factor]
        
        # FIX: Convert the image from BGR (common camera/OpenCV format) to RGB 
        # before encoding for display.
        data = cv2.cvtColor(data, cv2.COLOR_BGR2RGB)
        
        ok, encoded = cv2.imencode(".jpg", data)
        
        if not ok:
            raise ValueError("failed encode display image")
            
        return bytes(encoded)