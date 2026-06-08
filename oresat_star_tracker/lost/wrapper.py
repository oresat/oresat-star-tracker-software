# Copyright (c) 2020 Mark Polyakov, Karen Haining, Muki Kiboigo, Edward Zhang
# (If you edit the file, add your name here!)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import subprocess
from PIL import Image
from pathlib import Path
from typing import Union
import numpy as np

from .types import PyDbConfig, TetraDbConfig, PyEstimateConfig, TetraEstimateConfig
from .utils import find_cli, dict_flatten

cli = find_cli()
cli_dir = cli.parent
tmp_dir = Path(__file__).parent / 'tmp'
data_dir = Path(__file__).parent / 'data'


def _lost_runner(args: dict) -> None:
    stringified_args = [str(arg) for arg in dict_flatten(args)]
    subprocess.run([str(cli), *stringified_args], cwd=cli_dir)


def _py_db_args(cfg: PyDbConfig) -> dict:
    return {
        'database': None,
        '--max-stars': cfg.max_stars,
        '--kvector': None,
        '--kvector-min-distance': cfg.kvector_min_distance,
        '--kvector-max-distance': cfg.kvector_max_distance,
        '--kvector-distance-bins': cfg.kvector_distance_bins,
        '--output': cfg.output,
    }


def _tetra_db_args(cfg: TetraDbConfig) -> dict:
    return {
        'database': None,
        '--min-mag': cfg.min_mag,
        '--tetra': None,
        '--tetra-max-angle': cfg.tetra_max_angle,
        '--output': cfg.output,
    }


def database_args(cfg: PyDbConfig | TetraDbConfig | None = None) -> dict:
    '''
    Returns dictionary of default arguments for :func:`lost.database`.

    Applies `overrides` dict over generated/default values. For example,
    `database_args({'--max-stars': 4000})` will result in '--max-stars' mapping
    to 4000 in the returned dict.
    '''
    cfg = cfg or PyDbConfig()
    if isinstance(cfg, PyDbConfig):
        args = _py_db_args(cfg)
    elif isinstance(cfg, TetraDbConfig):
        args = _tetra_db_args(cfg)

    return args


def database(args: dict = database_args()) -> None:
    '''
    Calls LOST's database generation command.

    Must be called before :func:`lost.estimate` to initialize LOST.

    See :func:`lost.database_args` for arguments.
    '''

    _lost_runner(args)


def _py_estimate_args(cfg: PyEstimateConfig) -> dict:
    return {
        'pipeline': None,
        '--png': tmp_dir / 'temp_image.png',
        '--focal-length': cfg.focal_length,
        '--pixel-size': cfg.pixel_size,
        '--centroid-algo': cfg.centroid_algo,
        '--centroid-mag-filter': cfg.centroid_mag_filter,
        '--database': cfg.database,
        '--star-id-algo': cfg.star_id_algo,
        '--angular-tolerance': cfg.angular_tolerance,
        '--false-stars': cfg.false_stars,
        '--max-mismatch-prob': cfg.max_mismatch_prob,
        '--attitude-algo': cfg.attitude_algo,  # 'dqm' (Davenport Q), 'triad', 'quest'
        '--print-attitude': tmp_dir / 'attitude.txt',
    }


def _tetra_estimate_args(cfg: TetraEstimateConfig) -> dict:
    return {
        'pipeline': None,
        '--png': tmp_dir / 'temp_image.png',
        '--fov': cfg.fov,
        '--centroid-algo': cfg.CentroidAlgo,
        '--centroid-filter-brightest': cfg.centroid_filter_brightest,
        '--database': cfg.database,
        '--star-id-algo': cfg.star_id_algo,
        '--false-stars': cfg.false_stars,
        '--attitude-algo': cfg.attitude_algo,
        '--print-attitude': tmp_dir / 'attitude.txt',
    }


def estimate_args(cfg: PyEstimateConfig | TetraEstimateConfig | None = None) -> dict:
    '''
    Returns `dict` of default arguments for :func:`lost.estimate`.

    Applies `overrides` dict over generated/default values. For example,
    `identify_args({'--fov': 18})` will result in
    `'--fov'` mapping to `18` in the returned dict.
    '''

    cfg = cfg or PyEstimateConfig()
    if isinstance(cfg, PyEstimateConfig):
        args = _py_estimate_args(cfg)
    elif isinstance(cfg, TetraEstimateConfig):
        args = _tetra_estimate_args(cfg)
    return args


def estimate(image: np.ndarray, args: dict = estimate_args()) -> dict:
    '''
    Identifies `image: np.ndarray`, returning attitude information as `dict`.

    Running :func:`lost.database` is a prerequisite.

    See :func:`lost.identify_args` for parameters.

    Returns dictionary of attitude information:
    ```
    {
        "attitude_known": int,   # 1 if identified successfully
        "attitude_ra": float,    # right ascension, degrees
        "attitude_de": float,    # declination, degrees
        "attitude_roll": float,  # roll, degrees
        "attitude_i": float,     # attitude quaternion i
        "attitude_j": float,     # attitude quaternion j
        "attitude_k": float,     # attitude quaternion k
        "attitude_real": float,  # attitude quaternion real part
    }
    ```
    '''
    # save the given image to disk so LOST can use it
    im = Image.fromarray(image)
    im.save(str(tmp_dir / 'temp_image.png'))

    # identify image
    _lost_runner(args)

    # parse/load attitude file
    with open(tmp_dir / 'attitude.txt') as f:
        read_data = f.read()

    result: dict[str, Union[int, float]] = {}
    rows = read_data.split('\n')
    for row in rows:
        if row == '':
            continue
        sp = row.split(' ')
        if sp[0] == 'attitude_known':
            result[sp[0]] = int(sp[1])
        else:
            result[sp[0]] = float(sp[1])

    # clean up leftover junk (image, attitude file)
    (tmp_dir / 'temp_image.png').unlink()
    (tmp_dir / 'attitude.txt').unlink()

    # return attitue information, optionally output
    return result
