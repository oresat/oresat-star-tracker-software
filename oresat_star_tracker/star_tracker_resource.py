'''Star Tracker Resource'''

from enum import IntEnum
from time import time

import cv2
from olaf import Resource, logger, new_oresat_file, scet_int_from_time, TimerLoop

from .camera import Camera, CameraError
from .solver import Solver, SolverError


class DataSubindex(IntEnum):
    RIGHT_ANGLE = 0x1
    DECLINATION = 0x2
    ORIENTATION = 0x3
    TIME_STAMP = 0x4


class State(IntEnum):
    OFF = 0
    BOOT = 1
    STANDBY = 2
    STAR_TRACKING = 3
    ERROR = 0xFF


STATE_TRANSISTIONS = {
    State.OFF: [State.BOOT],
    State.BOOT: [State.STANDBY],
    State.STANDBY: [State.STAR_TRACKING],
    State.STAR_TRACKING: [State.STANDBY, State.ERROR],
    State.ERROR: [],
}
'''Valid state transistions.'''


class StarTrackerResource(Resource):
    def __init__(self, mock_hw: bool = False):
        super().__init__()

        self.mock_hw = mock_hw
        self._state = State.BOOT

        if self.mock_hw:
            logger.debug('mocking camera')
        else:
            logger.debug('not mocking camera')

        self._camera = Camera(self.mock_hw)
        self._solver = Solver()

        self.timer_loop = TimerLoop('star tracker resource', self._loop, 1000)

    def on_start(self):
        self.state_index = 0x6000
        self.state_obj = self.node.od[self.state_index]

        self.data_index = 0x6001
        data_record = self.node.od['Last solve']

        self.capture_index = 0x6002
        self.test_camera_index = 0x7000

        # Save references to camera
        self.right_ascension_obj = data_record['Right Ascension']
        self.declination_obj = data_record['Declination']
        self.orientation_obj = data_record['Roll']
        self.time_stamp_obj = data_record['Timestamp']
        self.image_obj = data_record['Image']

        self.image_obj.value = b''

        self._solver.startup()  # DB takes awhile to initialize
        self._state = State.STANDBY

        self.node.add_sdo_read_callback(self.state_index, self.on_state_read)
        self.node.add_sdo_read_callback(self.test_camera_index, self.on_test_camera_read)

        self.node.add_sdo_write_callback(self.state_index, self.on_state_write)
        self.node.add_sdo_write_callback(self.capture_index, self.on_capture_write)

        self.timer_loop.start()

    def on_end(self):
        self.timer_loop.stop()
        self.right_ascension_obj.value = 0
        self.declination_obj.value = 0
        self.orientation_obj.value = 0
        self.time_stamp_obj.value = 0
        self.image_obj.value = b''
        self._state = State.OFF

    def _capture(self, ext: str = '.bmp', save: bool = False) -> bytes:
        try:
            data = self._camera.capture()
        except CameraError as exc:
            logger.critial(exc)
            self._state = State.ERROR

        ok, encoded = cv2.imencode(ext, data)
        if not ok:
            raise ValueError(f'{ext} encode error')

        if save:
            # save capture
            name = '/tmp/' + new_oresat_file('capture', ext='.bmp')
            with open(name, 'wb') as f:
                f.write(encoded)
            logger.info(f'saved new capture {name}')

            # add capture to fread cache
            self.fread_cache.add(name, consume=True)

        return bytes(encoded)

    def _star_track(self):
        try:
            data = self._camera.capture()  # Take the image
            scet = scet_int_from_time(time())  # Record the timestamp

            # Solver takes a single shot image and returns an orientation
            dec, ra, ori = self._solver.solve(data)  # run the solver
            logger.debug(f'solved: ra:{ra}, dec:{dec}, ori:{ori}')

            self.right_ascension_obj.value = int(ra)
            self.declination_obj.value = int(dec)
            self.orientation_obj.value = int(ori)

            self.time_stamp_obj.value = scet

            _, encoded = cv2.imencode('.jpg', data)
            self.image_obj.value = bytes(encoded)

            # Send the star tracker data TPDOs
            self.node.send_tpdo(2)
            self.node.send_tpdo(3)
        except CameraError as exc:
            logger.critial(exc)
            self._state = State.ERROR
        except SolverError as exc:
            logger.error(exc)

    def _loop(self) -> bool:
        if self._state == State.STAR_TRACKING:
            self._star_track()
        elif self._state == State.ERROR:
            logger.critical('camera in bad state exit star tracker loop')
            return False

        return True

    def on_state_read(self, index: int, subindex: int):
        if index == self.state_index:
            return self._state.value

    def on_test_camera_read(self, index: int, subindex: int):
        if index == self.test_camera_index and subindex == 0x1:
            return self._capture(ext='.jpg')

    def on_state_write(self, index: int, subindex: int, data):
        if index != self.state_index:
            return

        try:
            new_state = State(data)
        except ValueError:
            logger.error(f'not a valid state: {data}')
            return

        if new_state == self._state or new_state in STATE_TRANSISTIONS[self._state]:
            logger.info(f'changing state: {self._state.name} -> {new_state.name}')
            self._state = new_state
        else:
            logger.info(f'invalid state change: {self._state.name} -> {new_state.name}')

    def on_capture_write(self, index: int, subindex: int, data):
        if index == self.capture_index:
            self._capture(save=True)
