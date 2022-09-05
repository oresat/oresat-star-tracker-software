'''Star Tracker Resource'''

import random
from argparse import ArgumentParser
from enum import IntEnum
from time import time
import numpy as np
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

class StateCommand(IntEnum):
    STANDBY = 0,
    STAR_TRACKING=1,
    CAPTURE=2

    def target_state(self, command):
        '''
        Translated the command received to target state.
        '''
        if command == StateCommand.STANDBY:
            return State.STANDBY
        elif command == StateCommand.STAR_TRACKING:
            return State.STAR_TRACKING
        elif command == StateCommand.CAPTURE:
            return State.CAPTURE
        else:
            raise ValueError('Unrecognized command : %d' % command)

class StarTrackerResource(Resource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.mock_hw:
            logger.debug('mocking camera')
        else:
            logger.debug('not mocking camera')

        self._state = State.BOOT
        self.state_index = 0x6000
        self.state_obj = self.od[self.state_index]

        self.data_index = 0x6001
        data_record = self.od[self.data_index]

        # 0.5s delay, so the on_loop function loops every 1s to 1.4s then,
        # solves should take between 0.5-1s
        self.delay = 0.5

        # Save references to camera
        self.right_angle_obj = data_record[DataSubindex.RIGHT_ANGLE.value]
        self.declination_obj = data_record[DataSubindex.DECLINATION.value]
        self.orientation_obj = data_record[DataSubindex.ORIENTATION.value]
        self.time_stamp_obj = data_record[DataSubindex.TIME_STAMP.value]

        self._camera = Camera(self.mock_hw)
        self._solver = Solver()

    def on_start(self):

        self._camera.power_on()
        logger.info('camera is powered on')

        self._solver.startup()  # DB takes awhile to initialize
        self._state = State.STANDBY

    def _capture(self):
        logger.info('entry: capture')
        try:
            data = self._camera.capture()
            ok, encoded = cv2.imencode('.bmp', data)
            if not ok:
                raise ValueError('bmp encode error')

            # save capture
            name = '/tmp/' + new_oresat_file('capture', ext='.bmp')
            with open(name, "wb") as f:
                f.write(encoded)
            logger.info('_capture: wrote to file:' + name)
            # add capture to fread cache
            self.fread_cache.add(name, consume=True)

        except CameraError as exc:
            logger.critial(exc)
            self._state = State.HW_ERROR
        logger.info('exit: capture')

    def _star_track(self):
        logger.info("entry: _star_track")
        try:
            data = self._camera.capture() # Take the image
            logger.info('image capture successfull')
            scet = scet_int_from_time(time()) # Record the timestamp

            # Solver takes a single shot image and returns an orientation
            logger.info('start solving')
            dec, ra, ori = self._solver.solve(data) # run the solver
            logger.info(f'finish solving: ra:{ra}, dec:{dec}, ori:{ori}')

            self.right_angle_obj.value = int(ra)
            self.declination_obj.value = int(dec)
            self.orientation_obj.value = int(ori)

            self.time_stamp_obj.value = scet

            # The tpdo will be sent out by the application
            self.send_tpdo(2)
            self.send_tpdo(3)

        except CameraError as exc:
            logger.critial(exc)
            self._state = State.HW_ERROR
        except SolverError as exc:
            logger.error(exc)
        logger.info("exit: _star_track")

    def on_loop(self):
        logger.info(f'entry: on_loop state: {self._state}')
        if self._state not in [State.STANDBY, State.CAPTURE, State.STAR_TRACKING]:
            raise ValueError(f'in invalid state for loop: {self._state.name}')
        if self._state == State.CAPTURE:
            self._capture()
        elif self._state == State.STAR_TRACKING:
            self._star_track()
        logger.info(f'exit: on_loop')

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
        logger.info('entry: on_read '+ hex(index)+str(' ') + str(subindex)+ ' ' )
        if index == self.state_index:
            logger.info('entry[startracker]: on_read '+ hex(index)+str(' ') + str(subindex)+ ' ' +' returning' + str(self._state.value))
            return self._state.value

    def on_write(self, index, subindex, od, data):
        logger.info('entry: on_write '+ hex(index)+str(' ') + str(subindex)+ ' ' + str(data))
        if index == self.state_index:
            try:
                raw_command     =  self.state_obj.decode_raw(data)
                command         =  StateCommand(raw_command)
                self._state     =  command.target_state()
                logger.info(f'start tracker now in state: {self._state.name}')
            except ValueError:
                logger.error(f'new state value of {new_state} is invalid')
        logger.info('exit: on_write')
