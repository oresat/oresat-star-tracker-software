'''Star Tracker Resource'''

import random
from argparse import ArgumentParser
from enum import IntEnum
from time import time

import cv2
from olaf import Resource, logger, new_oresat_file, scet_int_from_time

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
    CAPTURE = 3
    STAR_TRACKING = 4
    SW_ERROR = 5
    HW_ERROR = 6


class StarTrackerResource(Resource):

    def __init__(self, node, fread_cache, mock_hw):

        super().__init__(node, 'Star Tracker', 1.0)

        self.fread_cache = fread_cache
        self._mock_hw = mock_hw
        logger.debug('mock_hwing camera')
        self._state = State.BOOT

        self.state_index = 0x6000
        self.state_obj = self.node.object_dictionary[self.state_index]

        self.data_index = 0x6001
        data_record = self.node.object_dictionary[self.data_index]
        self.right_angle_obj = data_record[DataSubindex.RIGHT_ANGLE.value]
        self.declination_obj = data_record[DataSubindex.DECLINATION.value]
        self.orientation_obj = data_record[DataSubindex.ORIENTATION.value]
        self.time_stamp_obj = data_record[DataSubindex.TIME_STAMP.value]

        self._camera = Camera(self._mock_hw)
        self._solver = Solver()

    def on_start(self):

        self._camera.power_on()
        logger.info('camera is powered on')

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
            scet = scet_int_from_time(time())
            ra, dec, ori = self._solver.solve(data)

            self.right_angle_obj.value = int(ra)
            self.declination_obj.value = int(dec)
            self.orientation_obj.value = int(ori)
            self.time_stamp_obj.value = scet
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

        try:
            self._camera.power_off()
        except CameraError as exc:
            logger.error(exc)
            self._state = State.HW_ERROR

        logger.info('camera is powered off')

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

