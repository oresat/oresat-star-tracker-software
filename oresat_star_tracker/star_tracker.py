import logging
from io import BytesIO
from threading import Thread
from time import monotonic, sleep, time

import cv2
import numpy as np
import tifffile as tiff
from oresat_cand import NodeClient

from .ar013x import Ar013x, Ar013xState
from .gen.star_tracker_od import StarTrackerEntry, StarTrackerStatus, StarTrackerTpdo

STATE_TRANSISTIONS = {
    StarTrackerStatus.OFF: [StarTrackerStatus.BOOT],
    StarTrackerStatus.BOOT: [StarTrackerStatus.STANDBY],
    StarTrackerStatus.STANDBY: [
        StarTrackerStatus.LOW_POWER,
        StarTrackerStatus.STAR_TRACK,
        StarTrackerStatus.CAPTURE,
    ],
    StarTrackerStatus.LOW_POWER: [
        StarTrackerStatus.STANDBY,
        StarTrackerStatus.STAR_TRACK,
        StarTrackerStatus.CAPTURE,
    ],
    StarTrackerStatus.STAR_TRACK: [
        StarTrackerStatus.STANDBY,
        StarTrackerStatus.LOW_POWER,
        StarTrackerStatus.CAPTURE,
        StarTrackerStatus.ERROR,
    ],
    StarTrackerStatus.CAPTURE: [
        StarTrackerStatus.STANDBY,
        StarTrackerStatus.LOW_POWER,
        StarTrackerStatus.STAR_TRACK,
        StarTrackerStatus.ERROR,
    ],
    StarTrackerStatus.ERROR: [StarTrackerStatus.OFF],
}


class StarTracker:
    _BOOT_LOCKOUT_S = 70

    def __init__(self, node: NodeClient, camera: Ar013x):
        super().__init__()

        self.node = node
        self._state = StarTrackerStatus.BOOT
        self._camera = camera
        self.last_capture = None

        self._thread = Thread(target=self._run, daemon=True)

        self.node.add_write_callback(StarTrackerEntry.STATUS, self.on_write_status)

    def _encode_compress_tiff(self, data: np.ndarray, meta=None) -> np.ndarray:
        """Encode as an compress tiff."""

        buff = BytesIO()
        tiff.imwrite(buff, data, dtype=data.dtype, metadata=meta)

        # Get the encoded TIFF data from the memory file
        encoded_data = buff.getvalue()

        # Convert the encoded TIFF data to a NumPy array
        return np.frombuffer(encoded_data, dtype=np.uint8)

    def _filter(self, img: np.ndarray) -> bool:
        lower_bound = self.node.od_read(StarTrackerEntry.CAPTURE_FILTER_LOWER_BOUND)
        upper_bound = self.node.od_read(StarTrackerEntry.CAPTURE_FILTER_UPPER_BOUND)
        lower_percentage = self.node.od_read(StarTrackerEntry.CAPTURE_FILTER_LOWER_PERCENTAGE)
        upper_percentage = self.node.od_read(StarTrackerEntry.CAPTURE_FILTER_UPPER_PERCENTAGE)

        if lower_bound == 0 and upper_bound == 0:
            return True

        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check that enough pixels are bright enough
        if lower_bound != 0:
            bright_binary_image = np.where(gray_img > lower_bound, 1, 0)
            lit_mean = np.mean(bright_binary_image) * 100
            if lit_mean < lower_percenaget:
                return False

        # Check that enough pixels are dim enough
        if upper_bound != 0:
            dim_binary_image = np.where(gray_img < upper_bound, 1, 0)
            dim_mean = np.mean(dim_binary_image) * 100
            if dim_mean < upper_percentage:
                return False

        return True

    def _star_track(self):
        """Star track once."""

        # Take the image
        ts = time()
        try:
            data = self._camera.capture()
        except Exception:
            self._state = StarTrackerStatus.ERROR
            logging.error("Camera capture failure")
            logging.info(f"changing status: {self._state.name} -> {StarTrackerStatus.STANDBY.name}")
            return

        # NOTE: Lost currently writes the capture to disk temporarily
        import lost

        lost_args = lost.identify_args(algo="tetra")
        lost_data = lost.identify(data, lost_args)

        self.last_capture = data

        self.node_od_write_multi(
            {
                StarTrackerEntry.ORIENTATION_RIGHT_ASCENSION: int(lost_data["attitude_ra"]),
                StarTrackerEntry.ORIENTATION_DECLINATION: int(lost_data["attitude_de"]),
                StarTrackerEntry.ORIENTATION_ROLL: int(lost_data["attitude_roll"]),
                StarTrackerEntry.CAPTURE_LAST_CAPTURE: int(ts),
            }
        )
        self.node.send_tpdo([StarTrackerTpdo.TPDO_3, StarTrackerTpdo.TPDO_4])

        # If the frequency is 0, star track once
        if self.node.od_read(StarTrackerEntry.CAPTURE_DELAY) == 0:
            logging.info(f"changing status: {self._state.name} -> {StarTrackerStatus.STANDBY.name}")
            self.node.od_write(StarTrackerEntry.STATUS, StarTrackerStatus.STANDBY)
        else:
            delay_ms = self.node.od_read(StarTrackerEntry.CAPTURE_DELAY)
            sleep(delay_ms / 1000)

    def _capture_only_mode(self):
        """Use camera for some amount of time."""

        img_count = 0
        start_timestamp = time()

        def exceeded_duration() -> bool:
            return time() - start_timestamp > self.node.od_read(StarTrackerEntry.CAPTURE_DURATION)

        def exceeded_img_count() -> bool:
            return img_count > self.node.od_read(StarTrackerEntry.CAPTURE_NUM_OF_IMAGES)

        while not exceeded_duration and not exceeded_img_count:
            ts = time()
            try:
                data = self._camera.capture()
            except Exception:
                self._state = StarTrackerStatus.ERROR
                logging.error("Camera capture failure")
                logging.info(
                    f"changing status: {self._state.name} -> {StarTrackerStatus.STANDBY.name}"
                )
                return

            filter_enabled = self.node.od_read(StarTrackerEntry.CAPTURE_FILTER_ENABLE)
            if filter_enabled or not self._filter(data):
                logging.debug("capture did not pass filter")
                continue

            self.node.od_write(StarTrackerEntry.CAPTURE_LAST_CAPTURE_TIME, int(ts))
            self.last_capture = data
            img_count += 1
            logging.info(f"capture {img_count}")

            if self.node.od_read(StarTrackerEntry.CAPTURE_SAVE_CAPTURES):
                name = f"/tmp/st_capture_{int(ts) * 1000}.tiff"
                meta = {
                    "timestamp": ts,
                }
                tiff.imwrite(name, data, dtype=data.dtype, metadata=meta)
                logging.info(f"saved new capture {name}")
                self.node.add_file(name)

            delay_ms = self.node.od_read(StarTrackerEntry.CAPTURE_DELAY)
            sleep(delay_ms / 1000)

        if img_count == 0:
            logging.info("no images taken, check camera mode settings and filter")

        logging.info(f"changing status: {self._state.name} -> {StarTrackerStatus.STANDBY.name}")
        self._state = StarTrackerStatus.STANDBY

    def _run(self):
        while True:
            state = self.node.od_read(StarTrackerEntry.STATUS)
            if state == StarTrackerStatus.BOOT and monotonic() > self._BOOT_LOCKOUT_S:
                self.node.od_write(StarTrackerEntry.STATUS, StarTrackerStatus.STANDBY)
            elif state == StarTrackerStatus.STAR_TRACK:
                self._star_track()
            elif state == StarTrackerStatus.CAPTURE:
                self._capture_only_mode()
            elif state not in list(StarTrackerStatus):
                logging.error(f"state in an unknown state {state}, resetting to STANDBY")
                self.node.od_write(StarTrackerEntry.STATUS, StarTrackerStatus.STANDBY)
            else:
                sleep(0.1)

    def run(self, thread: bool):
        if thread:
            self._thread.start()
        else:
            self._run()

    def on_write_status(self, value: int):
        """SDO write callback for star tracker status."""
        new_status = self._state

        if self._camera.state == Ar013xState.LOCKOUT:
            logging.error("Cannot transition camera to lockout state")
        elif self._camera.state == Ar013xState.ERROR:
            logging.error("Camera is in error state")
            new_status = StarTrackerStatus.ERROR
        else:
            try:
                new_status = StarTrackerStatus(value)
            except ValueError:
                logging.error(f"invalid state: {value}")
                return

        if new_status == self._state:
            return  # nothing to change

        if self._state == StarTrackerStatus.BOOT:
            logging.error("cannot transfer out of BOOT state by command")
            return

        if new_status not in STATE_TRANSISTIONS[self._state]:
            logging.error(f"invalid status change: {self._state.name} -> {new_status.name}")
            return

        logging.info(f"changing status: {self._state.name} -> {new_status.name}")
        self._state = new_status
