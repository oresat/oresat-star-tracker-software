'''Star Tracker Resource'''

from enum import IntEnum
from time import time

import cv2
import numpy as np

from olaf import Resource, logger, new_oresat_file, scet_int_from_time, TimerLoop
from olaf.common.cpufreq import set_cpufreq

from .camera import Camera, CameraError
from .solver import Solver, SolverError


class State(IntEnum):
    OFF = 0
    BOOT = 1
    STANDBY = 2
    LOW_POWER = 3
    STAR_TRACKING = 4
    CAMERA = 5
    ERROR = 0xFF


STATE_TRANSISTIONS = {
    State.OFF: [State.BOOT],
    State.BOOT: [State.STANDBY],
    State.STANDBY: [State.LOW_POWER, State.STAR_TRACKING, State.CAMERA],
    State.LOW_POWER: [State.STANDBY, State.STAR_TRACKING, State.CAMERA],
    State.STAR_TRACKING: [State.STANDBY, State.LOW_POWER, State.CAMERA, State.ERROR],
    State.CAMERA: [State.STANDBY, State.LOW_POWER, State.STAR_TRACKING, State.ERROR],
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

        self.timer_loop = TimerLoop('star tracker resource', self._loop, self.node.od['Mode Settings']['Star tracking delay'])

    def on_start(self):
        # Save references to OD variables

        # State
        self.state_index = 0x6000
        self.state_obj = self.node.od[self.state_index]
        

        # Last solve record
        self.last_solve_index = 0x6001
        last_solve_record = self.node.od['Last solve']
        self.right_ascension_var = last_solve_record['Right Ascension']
        self.declination_var = last_solve_record['Declination']
        self.orientation_var = last_solve_record['Roll']
        self.time_stamp_var = last_solve_record['Timestamp']
        self.image_domain = last_solve_record['Image']
        self.image_domain.value = b''

        # Mode settings record
        self.mode_settings_index = 0x6002
        mode_settings_record = self.node.od['Mode Settings']
        self.Star_tracking_delay_var = mode_settings_record['Star tracking delay']
        self.capture_duration_var = mode_settings_record['Capture duration']
        self.image_count_var = mode_settings_record['Image count']

        # Image filter record
        self.image_filter_index = 0x6003
        image_filter_record = self.node.od['Image filter']
        self.lower_bound_var = image_filter_record['Lower bound']
        self.lower_percentage_var = image_filter_record['Lower percentage']
        self.upper_bound_var = image_filter_record['Upper bound']
        self.upper_percentage_var = image_filter_record['Upper percentage']

        self.test_camera_index = 0x7000

        self._solver.startup()  # DB takes awhile to initialize
        self._state = State.STANDBY

        self.node.add_sdo_read_callback(self.state_index, self.on_state_read)
        self.node.add_sdo_read_callback(self.test_camera_index, self.on_test_camera_read)

        self.node.add_sdo_write_callback(self.state_index, self.on_state_write)

        self.timer_loop.start()

    def on_end(self):
        self.timer_loop.stop()
        self.right_ascension_var.value = 0
        self.declination_var.value = 0
        self.orientation_var.value = 0
        self.time_stamp_var.value = 0
        self.image_domain.value = b''
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

    def _filter(self, img: np.ndarray) -> bool:
        
        # If both bounds are ignored, return
        if self.lower_bound_var.value == 0 and self.upper_bound_var.value == 0:
            return True
        
        # Convert the BGR image to grayscale
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        '''Check that enough pixels are bright enough'''
        if self.lower_bound_var.value != 0:
        
            # Threshold the grayscale image for brightness check
            bright_binary_image = np.where(gray_img > self.lower_bound_var.value, 1, 0)
            
            # Calculate the mean of lit pixels in the original grayscale image
            lit_mean = np.mean(bright_binary_image)
            
            # Check if the mean exceeds the threshold
            if lit_mean < self.lower_percentage_var.value:
                return False
        
        '''Check that enough pixels are dim enough'''
        if self.upper_bound_var.value != 0:

            # Threshold the grayscale image for dimness check
            dim_binary_image = np.where(gray_img < self.upper_bound_var.value, 1, 0)
            
            # Calculate the mean of dim pixels in the original grayscale image
            dim_mean = np.mean(dim_binary_image)

            if dim_mean < self.upper_percentage_var.value:
                return False

        return True

    # Star track once
    def _star_track(self):
        data = self._camera.capture()  # Take the image
        scet = scet_int_from_time(time())  # Record the timestamp

        # Solver takes a single shot image and returns an orientation
        dec, ra, ori = self._solver.solve(data)  # run the solver
        logger.debug(f'solved: ra:{ra}, dec:{dec}, ori:{ori}')

        self.right_ascension_var.value = int(ra)
        self.declination_var.value = int(dec)
        self.orientation_var.value = int(ori)

        self.time_stamp_var.value = scet
        self.image_domain.value = bytes(self._encode(data))

        # Send the star tracker data TPDOs
        self.node.send_tpdo(2)
        self.node.send_tpdo(3)
        
        # If the frequency is 0, star track once
        if self.Star_tracking_delay_var.value == 0:
            self._state = State.STANDBY

    # Use camera for some amount of time
    def _camera_mode(self):
        img_count = 0
        start_timestamp = time()

        # Take images until either time runs out or image count has been reached
        while time() - start_timestamp < self.capture_duration_var.value and img_count < self.image_count_var.value:
         
            # Todo - possibly add some sort of delay

            data = self._camera.capture()  # Take the image
            
            if not self._filter(data):  # Check if image passes filter
                continue

            self._save_to_cache(scet_int_from_time(time()), self._encode(data)) # Save image
            img_count += 1

        if img_count == 0:
            logger.info('No images taken, check camera mode settings and filter')

        self._state = State.STANDBY

    def _loop(self) -> bool:
        try:
            match self._state:
                case State.STAR_TRACKING:
                    self._star_track()
                case State.CAMERA:
                    self._camera_mode()
                case State.ERROR:
                    logger.critical('camera in bad state exit star tracker loop')
                    return False
                
        except CameraError as exc:
            logger.critical(exc)
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
            logger.critical(exc)
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
            
            # When entering low power state, turn on low power mode
            if new_state == State.LOW_POWER and self._state != State.LOW_POWER:
                set_cpufreq(300)
                # Todo - Turn off PRUs/sensor
            
            # When leaving power state, turn off low power mode
            elif self._state == State.LOW_POWER and new_state != State.LOW_POWER:
                set_cpufreq(1000)
                # Todo - Turn on PRUs/sensor


            logger.info(f'changing state: {self._state.name} -> {new_state.name}')
            self._state = new_state

            
        else:
            logger.info(f'invalid state change: {self._state.name} -> {new_state.name}')

        