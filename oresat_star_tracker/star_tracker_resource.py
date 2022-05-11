'''Star Tracker Resource'''

import random
from argparse import ArgumentParser
from enum import IntEnum

import cv2
from olaf import Resource, PRU, PRUError, logger, new_oresat_file

from .camera import Camera, CameraError
from .solver import Solver, SolverError


class DataSubindex(IntEnum):
    RIGHT_ANGLE = 0x1
    DECLINATION = 0x2
    ORIENTATION = 0x3


class State(IntEnum):
    OFF = 0
    BOOT = 1
    STANDBY = 2
    CAPTURE = 3
    STAR_TRACKING = 4
    SW_ERROR = 5
    HW_ERROR = 6


class StarTrackerResource(Resource):

    # these files are provide by the prucam-dkms debian package
    PRU0_FW = '/lib/firmware/pru0.bin'
    PRU1_FW = '/lib/firmware/pru1.bin'

    def __init__(self, node, fread_cache):

        super().__init__(node, 'Star Tracker', 1.0)

        self.fread_cache = fread_cache
        self._mock = True  # TODO args
        self._state = State.BOOT

        self.state_index = 0x6000
        self.state_obj = self.node.object_dictionary[self.state_index]

        self.data_index = 0x6001
        data_record = self.node.object_dictionary[self.data_index]
        self.right_angle_obj = data_record[DataSubindex.RIGHT_ANGLE.value]
        self.declination_obj = data_record[DataSubindex.DECLINATION.value]
        self.orientation_obj = data_record[DataSubindex.ORIENTATION.value]

    def on_start(self):

        if not self._mock:
            try:
                self._prus = [PRU(0, self.PRU0_FW), PRU(1, self.PRU1_FW)]
                self._prus[0].start()
                self._prus[1].start()
            except PRUError as exc:
                logger.error(exc)
                self._state = State.HW_ERROR
                return

        self._camera = Camera(self._mock)
        self._solver = Solver()
        self._solver.startup()  # DB takes awhile to initialize

        self._state = State.STANDBY

    def _capture(self):
        try:
            data = self._camera.capture()
            ok, encoded = cv2.imencode('.bmp', data)
            if not ok:
                raise ValueError('bmp encode error')

            # save capture
            name = '/tmp/' + new_oresat_file('capture', ext='.bmp')
            with open(name, "wb") as f:
                f.write(encoded)

            # add capture to fread cache
            self.fread_cache.add(name, consume=True)
        except CameraError as exc:
            logger.critial(exc)
            self._state = State.HW_ERROR

    def _star_track(self):
        try:
            data = self._camera.capture()
            ra, dec, ori = self._solver.solve(data)

            self.right_angle_obj.value = int(ra)
            self.declination_obj.value = int(dec)
            self.orientation_obj.value = int(ori)
        except CameraError as exc:
            logger.critial(exc)
            self._state = State.HW_ERROR
        except SolverError as exc:
            logger.error(exc)
            self._state = State.SW_ERROR

    def on_loop(self):

        if self._state not in [State.STANDBY, State.CAPTURE, State.STAR_TRACKING]:
            raise ValueError(f'in invalid state for loop: {self._state.name}')

        if self._state == State.CAPTURE:
            self._capture()
        elif self._state == State.STAR_TRACKING:
            self._star_track()

    def on_end(self):

        if not self._mock:
            try:
                self._prus[0].stop()
                self._prus[1].stop()
            except PRUError as exc:
                logger.error(exc)
                self._state = State.HW_ERROR

        self.right_angle_obj.value = 0
        self.declination_obj.value = 0
        self.orientation_obj.value = 0
        self._state = State.OFF

    def on_read(self, index, subindex, od):

        if index == self.state_index:
            return self._state.value

    def on_write(self, index, subindex, od, data):

        if index == self.state_index:
            new_state = self.state_obj.decode_raw(data)
            try:
                self._state = State(new_state)
                logger.info(f'start tracker now in state: {self._state.name}')
            except ValueError:
                logger.error(f'new state value of {new_state} is invalid')

