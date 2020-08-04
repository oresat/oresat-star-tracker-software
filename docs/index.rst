Welcome!
========================================================

This is the documentation for the software used by OreSat's star tracker board. All of our code is hosted on `GitHub <https://github.com/oresat/oresat-star-tracker-software>`_.

Roughly speaking, this project has five parts to it:

- solver module -- solves images (based on `OpenStarTracker <http://openstartracker.org/>`_ from the University at Buffalo)
- camera module -- controls the camera
- state machine -- captures images and/or solves them, sending the results over D-Bus
- daemon manager -- creates a daemon that can be controlled with standard Linux mechanisms
- auxiliary files -- build project and package into a ``.deb``

.. automodule:: main

.. automodule:: solver.solver
   :members:

.. automodule:: camera.camera
   :members: