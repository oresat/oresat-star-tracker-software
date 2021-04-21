# snapper.py
# by Umair Khan, from the Portland State Aerospace Society

# Use this class to control the camera.

# Imports
import os
import time
import glob
import logging
import numpy as np
import cv2
from prucam import Camera, PRUCam

# Class definition
class Snapper:

    # Initialization
    def __init__(self, logger):

        # Set up variables
        self.logger = logger
        self.pru = PRUCam()
        self.camera = None
        self.save_snaps = "/usr/share/oresat-star-tracker/data/snaps/"
        self.save_solves = "/usr/share/oresat-star-tracker/data/solves/"
        self.running = False

        # Stop the PRUs, just in case
        try:
            self.pru.stop()
        except:
            self.logger.info("PRUs already stopped.")

    # Enable autoexposure via sysfs settings
    def enable_ae(self):
        self.camera.ae_enable = 1
        self.camera.ae_ag_en = 1
        self.camera.ae_dg_en = 1

    # Start the camera / PRU
    def start(self):
        if not self.running:
            self.pru.start()
            self.camera = Camera()
            self.enable_ae()
            self.running = True
            self.logger.info("Started camera.")
        else:
            self.logger.info("Camera already running.")

    # Stop the camera / PRU
    def stop(self):
        if self.running:
            self.camera = None
            self.pru.stop()
            self.running = False
            self.logger.info("Stopped camera.")
        else:
            self.logger.info("Camera already stopped.")

    # Restart the camera / PRU
    def restart(self):
        if self.running:
            self.stop()
            self.start()
        else:
            self.start()
        self.logger.info("Restarted camera.")

    # Capture a photo as a snap
    def capture_snap(self, curr_num):

        # Start the camera
        self.start()

        # Take the photo and rename it
        raw_path = self.camera.capture(dir_path = self.save_snaps, ext = ".png")
        date_and_time = time.strftime("%d-%m-%Y_%H-%M-%S", time.gmtime())
        new_path = self.save_snaps + f"{curr_num}_{date_and_time}.png"
        os.rename(raw_path, new_path)

        # If necessary, delete an older photo to compensate
        if curr_num >= 50:
            file_to_remove = glob.glob(self.save_snaps + f"{curr_num - 50}_*.png")[0]
            os.remove(file_to_remove)

        # Add some compression
        img = cv2.imread(new_path)
        cv2.imwrite(new_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 5])

        # Turn off the camera and return path
        self.stop()
        self.logger.info(f"Saved snap to {new_path}.")
        return new_path

    # Capture a photo to solve
    def capture_solve(self, curr_num):

        # Start the camera
        self.start()

        # Take the photo and rename it
        raw_path = self.camera.capture(dir_path = self.save_solves, ext = ".png")
        date_and_time = time.strftime("%d-%m-%Y_%H-%M-%S", time.gmtime())
        new_path = self.save_solves + f"{curr_num}_{date_and_time}.png"
        os.rename(raw_path, new_path)

        # If necessary, delete an older photo to compensate
        if curr_num >= 50:
            file_to_remove = glob.glob(self.save_solves + f"{curr_num - 50}_*.png")[0]
            os.remove(file_to_remove)

        # Resize the photo to 640x480 and add some compression
        img = cv2.imread(new_path)
        resized = cv2.resize(img, (640, 480))
        cv2.imwrite(new_path, resized, [cv2.IMWRITE_PNG_COMPRESSION, 5])

        # Turn off the camera and return path
        self.stop()
        self.logger.info(f"Saved photo to solve to {new_path}.")
        return new_path
