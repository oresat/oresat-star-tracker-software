"""Star Tracker service"""

from enum import IntEnum
from io import BytesIO
from time import time

import canopen
import cv2
import numpy as np
import tifffile as tiff
from olaf import Service, logger, new_oresat_file  # , set_cpufreq_gov

from .camera import Camera, CameraError
from .solver import Solver, SolverError


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

    def __init__(self, mock_hw: bool = False):
        super().__init__()

        self.mock_hw = mock_hw
        self._state = State.BOOT

        if self.mock_hw:
            logger.debug("mocking camera")
        else:
            logger.debug("not mocking camera")

        self._camera = Camera(self.mock_hw)
        self._solver = Solver()
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
        """Save references to OD objiables"""

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

        self._solver.startup()  # DB takes awhile to initialize

        self.node.add_sdo_callbacks("status", None, self.on_read_status, self.on_write_status)
        self.node.add_sdo_callbacks(
            "capture", "last_display_image", self._on_read_last_display_image, None
        )

        self._state = State.STANDBY

    def on_stop(self):
        """When service stops clear star tracking data."""

        self._right_ascension_obj.value = 0
        self._declination_obj.value = 0
        self._orientation_obj.value = 0
        self._time_stamp_obj.value = 0
        self._last_capture = None
        self._last_capture_time.value = 0
        self._state = State.OFF

    def _encode(self, data: np.ndarray, ext: str = ".tiff") -> np.ndarray:
        """Wrap opencv's encode function to throw exception."""

        ok, encoded = cv2.imencode(ext, data)
        if not ok:
            raise ValueError(f"{ext} encode error")

        return encoded

    def _encode_compress_tiff(self, data: np.ndarray, meta=None) -> np.ndarray:
        """Encode as an compress tiff."""

        buff = BytesIO()
        tiff.imwrite(
            buff,
            data,
            dtype=data.dtype,
            metadata=meta,
            compression="zstd",
            compressionargs={"level": 1},
        )

        # Get the encoded TIFF data from the memory file
        encoded_data = buff.getvalue()

        # Convert the encoded TIFF data to a NumPy array
        return np.frombuffer(encoded_data, dtype=np.uint8)

    def _save_to_cache(self, file_keyword: str, encoded_data: np.ndarray, ext: str = ".tiff"):
        # save capture
        name = "/tmp/" + new_oresat_file(file_keyword, ext=ext)
        with open(name, "wb") as f:
            f.write(encoded_data.tobytes())
        logger.info(f"saved new capture {name}")

        # add capture to fread cache
        self.node.fread_cache.add(name, consume=True)

    def _filter(self, img: np.ndarray) -> bool:
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
        data = self._camera.capture()

        # Solver takes a single shot image and returns an orientation
        dec, ra, ori = self._solver.solve(data)  # run the solver
        logger.debug(f"solved: ra:{ra}, dec:{dec}, ori:{ori}")

        self._right_ascension_obj.value = int(ra)
        self._declination_obj.value = int(dec)
        self._orientation_obj.value = int(ori)

        self._time_stamp_obj.value = int(ts)
        self._last_capture_time.value = int(ts)
        self._last_capture = data

        # Send the star tracker data TPDOs
        self.node.send_tpdo(3)
        self.node.send_tpdo(4)

        # If the frequency is 0, star track once
        if self._capture_delay_obj.value == 0:
            logger.info(f"changing status: {self._state.name} -> {State.STANDBY.name}")
            self._state = State.STANDBY
        else:
            self.sleep(self._capture_delay_obj.value)

    def _capture_only_mode(self):
        """Use camera for some amount of time."""

        img_count = 0
        start_timestamp = time()

        # Take images until either time runs out or image count has been reached
        while time() - start_timestamp < self._capture_duration_obj.value and (
            self._image_count_obj.value == 0 or img_count < self._image_count_obj.value
        ):
            ts = time()
            data = self._camera.capture()  # Take the image

            # Check if image passes filter
            if not self._filter_enable_obj.value or not self._filter(data):
                logger.debug("capture did not pass filter")
                continue

            self._last_capture_time.value = int(ts)
            self._last_capture = data
            img_count += 1
            logger.info(f"capture {img_count}")

            if self._save_obj.value:
                self._save_to_cache("img", self._encode_compress_tiff(data))  # Save image

            self.sleep_ms(self._capture_delay_obj.value)

        if img_count == 0:
            logger.info("no images taken, check camera mode settings and filter")

        logger.info(f"changing status: {self._state.name} -> {State.STANDBY.name}")
        self._state = State.STANDBY

    def on_loop(self):
        if self._state == State.STAR_TRACK:
            self._star_track()
        elif self._state == State.CAPTURE_ONLY:
            self._capture_only_mode()
        else:
            self.sleep(0.1)

    def on_loop_error(self, error: Exception):
        if error is CameraError:
            logger.critical(error)
            self._state = State.ERROR
        elif error is SolverError:
            logger.error(error)
        elif error is ValueError:
            logger.error(error)
        else:
            logger.critical(f"Unkown error {error}")
            self._state = State.ERROR

    def on_read_status(self) -> int:
        """SDO read callback for star tracker status."""

        return self._state.value

    def on_write_status(self, value: int):
        """SDO write callback for star tracker status."""

        new_status = State.BOOT
        try:
            new_status = State(value)
        except ValueError:
            logger.error(f"invalid state: {value}")
            return

        if new_status == self._state:
            return  # nothing to change

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
        """SDO read callback for star tracker status."""

        if self._last_capture is None:
            return b""

        data = np.copy(self._last_capture)

        # downscale image
        downscale_factor = 2
        data = data[::downscale_factor, ::downscale_factor]

        ok, encoded = cv2.imencode(".jpg", data)
        if not ok:
            raise ValueError("failed encode display image")

        return bytes(encoded)
