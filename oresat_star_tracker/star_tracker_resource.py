'''Star Tracker Resource'''

from argparse import ArgumentParser
from enum import IntEnum

import cv2
from oresat_app import Resource, PRU, PRUError, logger, new_oresat_file

from .camera import Camera, CameraError
from .solver import Solver, SolverError


class StarTrackerState(IntEnum):
    BOOT = 0
    STANDBY = 1
    CAPTURE = 2
    STAR_TRACKING = 3
    HW_ERROR = 4


class StarTrackerResource(Resource):

    PRU0_FW = '/lib/firmware/pru0.bin'
    PRU1_FW = '/lib/firmware/pru1.bin'

    def __init__(self, node, fread_cache):

        super().__init__(node, 'Star Tracker', 1.0)

        self.fread_cache = fread_cache

        self.index = 0x6000
        self.subindex_ra = 0x1
        self.subindex_dec = 0x2
        self.subindex_ori = 0x3
        self.subindex_state = 0x4
        self.obj = self.node.object_dictionary[self.index]
        self._state = StarTrackerState.BOOT

    def on_start(self):

        # these will raise exception if they fail
        # let the app handle the exception
        self._prus = [PRU(0, self.PRU0_FW), PRU(1, self.PRU1_FW)]
        self._camera = Camera()
        self._solver = Solver()
        self._prus[0].start()
        self._prus[1].start()
        self._solver.startup()  # DB takes awhile to initialize

        self._state = StarTrackerState.STANDBY

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

    def _star_track(self):
        try:
            data = self._camera.capture()
            ra, dec, ori = self._solver.solve(data)

            self.obj[1] = int(ra)
            self.obj[2] = int(dec)
            self.obj[3] = int(ori)
        except CameraError as exc:
            logger.critial(exc)
            return
        except SolverError as exc:
            logger.error(exc)
            return

    def on_loop(self):

        if self._state == StarTrackerState.CAPTURE:
            self._capture()
        elif self._state == StarTrackerState.STAR_TRACKING:
            self._star_track()

    def on_end(self):

        try:
            self._prus[0].stop()
            self._prus[1].stop()
        except PRUError:
            pass

        self.obj[1] = 0
        self.obj[2] = 0
        self.obj[3] = 0

    def on_read(self, index, subindex, od):

        if index == self.index and subindex == 1:
            return self.state.value

        return

    def on_write(self, index, subindex, od, data):

        if index != self.index:
            return

        if subindex == self.subindex_state:
            new_state = self.obj[self.subindex_state].decode_raw(data)
            self.state = StarTrackerState(new_state)
