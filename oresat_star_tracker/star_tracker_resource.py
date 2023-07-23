'''Star Tracker Resource'''

from enum import IntEnum
from time import time

import cv2
import numpy as np

from olaf import Resource, logger, new_oresat_file, scet_int_from_time, TimerLoop

from .camera import Camera, CameraError
from .solver import Solver, SolverError


class State(IntEnum):
    OFF = 0
    BOOT = 1
    UPDATE = 2
    STANDBY = 3
    STAR_TRACKING = 4
    CAMERA = 5
    ERROR = 0xFF


STATE_TRANSISTIONS = {
    State.OFF: [State.BOOT],
    State.BOOT: [State.STANDBY],
    State.UPDATE: [],
    State.STANDBY: [State.STAR_TRACKING, State.CAMERA, State.OFF],
    State.STAR_TRACKING: [State.STANDBY, State.CAMERA, State.OFF, State.ERROR],
    State.CAMERA: [State.STANDBY, State.STAR_TRACKING, State.OFF, State.ERROR],
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

        self.timer_loop.start()

    def on_end(self):
        self.timer_loop.stop()
        self.right_ascension_obj.value = 0
        self.declination_obj.value = 0
        self.orientation_obj.value = 0
        self.time_stamp_obj.value = 0
        self.image_obj.value = b''
        self._state = State.OFF

    # Wrap opencv's encode function to throw exception
    def _encode(self, data: np.ndarray, ext: str = '.tiff') -> np.ndarray:
        ok, encoded = cv2.imencode(ext, data)
        if not ok:
            raise ValueError(f'{ext} encode error')
        
        return encoded
        
    def _save_to_cache(self, file_keyword: str, encoded_data: np.ndarray, ext: str = '.tiff'):
        # save capture
        name = '/tmp/' + new_oresat_file(file_keyword, ext='.tiff')
        with open(name, 'wb') as f:
            f.write(encoded_data)
        logger.info(f'saved new capture {name}')

        # add capture to fread cache
        self.fread_cache.add(name, consume=True)


    def _star_track(self):
        data = self._camera.capture()  # Take the image
        scet = scet_int_from_time(time())  # Record the timestamp

        # Solver takes a single shot image and returns an orientation
        dec, ra, ori = self._solver.solve(data)  # run the solver
        logger.debug(f'solved: ra:{ra}, dec:{dec}, ori:{ori}')

        self.right_ascension_obj.value = int(ra)
        self.declination_obj.value = int(dec)
        self.orientation_obj.value = int(ori)

        self.time_stamp_obj.value = scet

        _, encoded = cv2.imencode('.tiff', data)
        self.image_obj.value = bytes(encoded)

        # Send the star tracker data TPDOs
        self.node.send_tpdo(2)
        self.node.send_tpdo(3)


    def _camera(self):
        data = self._camera.capture()  # Take the image
        #scet = scet_int_from_time(time())  # Record the timestamp
        self._save_to_cache(scet_int_from_time(time()), self._encode(data)) # USe timestamp to name image

        self._state = State.STANDBY
        return True

    def _loop(self) -> bool:
        try:
            match self._state:
                case State.OFF:
                    self.node.od['Power control']['Poweroff'].value = True
                    self.node.od['Power control']['Reset'].value = 0

                case State.BOOT:
                    pass
                case State.STANDBY:
                    pass
                case State.UPDATE:
                    pass
                case State.STAR_TRACKING:
                    self._star_track()
                case State.CAMERA:
                    self._camera()
                case State.ERROR:
                    logger.critical('camera in bad state exit star tracker loop')
                    return False
                
        except CameraError as exc:
            logger.critial(exc)
            self._state = State.ERROR
        except SolverError as exc:
            logger.error(exc)
        except ValueError as exc:
            logger.error(exc)
               
        return True

    def on_state_read(self, index: int, subindex: int):
        if index == self.state_index:
            return self._state.value

    def on_test_camera_read(self, index: int, subindex: int):
        try:
            if index == self.test_camera_index and subindex == 0x1:
                data = self._camera.capture()
                return bytes(self._encode(data))
        
        except CameraError as exc:
            logger.critial(exc)
            raise
        except SolverError as exc:
            logger.error(exc)
            raise
        except ValueError as exc:
            logger.error(exc)
            raise

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