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

from .utils import find_cli, dict_flatten

cli = find_cli()
cli_dir = cli.parent
tmp_dir = Path(__file__).parent / 'tmp'
data_dir = Path(__file__).parent / 'data'


def lost_runner(args: dict) -> None:
    stringified_args = [str(arg) for arg in dict_flatten(args)]
    subprocess.run([str(cli), *stringified_args], cwd=cli_dir)


def database_args(overrides: dict = {}, algo: str = 'py') -> dict:
    '''
    Returns dictionary of default arguments for :func:`lost.database`.

    Applies `overrides` dict over generated/default values. For example,
    `database_args({'--max-stars': 4000})` will result in '--max-stars' mapping
    to 4000 in the returned dict.

    Sets up for pyramidal if `algo` is `'py'`, or tetra if `algo` is `'tetra'`.
    '''
    if algo == 'py':
        args = {
            'database': None,
            '--max-stars': 5000,
            '--kvector': None,
            '--kvector-min-distance': 0.2,
            '--kvector-max-distance': 15.0,
            '--kvector-distance-bins': 10_000,
            '--output': data_dir / 'py-database.dat',
        }
    elif algo == 'tetra':
        args = {
            'database': None,
            '--min-mag': 7,
            '--tetra': None,
            '--tetra-max-angle': 12,
            '--output': data_dir / 'tetra-database.dat',
        }
    else:
        raise Exception(f"Invalid database algo {algo}. Must be 'py' or 'tetra'.")
    args.update(overrides)
    return args


def database(args: dict = database_args()) -> None:
    '''
    Calls LOST's database generation command.

    Must be called before :func:`lost.identify` to initialize LOST.

    See :func:`lost.database_args` for arguments.
    '''

    lost_runner(args)


def estimate_args(overrides: dict = {}, algo: str = 'py') -> dict:
    '''
    Returns `dict` of default arguments for :func:`lost.identify`.

    Applies `overrides` dict over generated/default values. For example,
    `identify_args({'--fov': 18})` will result in
    `'--fov'` mapping to `18` in the returned dict.

    Sets up for pyramidal if `algo` is `'py'`,s or tetra if `algo` is `'tetra'`.
    '''
    if algo == 'py':
        args = {
            'pipeline': None,
            '--png': tmp_dir / 'temp_image.png',
            '--focal-length': 49,
            '--pixel-size': 22.2,
            '--centroid-algo': 'cog',  # 'cog', 'dummy', 'iwcog'
            '--centroid-mag-filter': 5,
            '--database': data_dir / 'py-database.dat',
            '--star-id-algo': 'py',  # 'dummy', 'gv', 'py', 'tetra'
            '--angular-tolerance': 0.05,
            '--false-stars': 1000,
            '--max-mismatch-prob': 0.0001,
            '--attitude-algo': 'dqm',  # 'dqm' (Davenport Q), 'triad', 'quest'
            '--print-attitude': tmp_dir / 'attitude.txt',
        }
    elif algo == 'tetra':
        args = {
            'pipeline': None,
            '--png': tmp_dir / 'temp_image.png',
            '--fov': 17,
            '--centroid-algo': 'cog',
            '--centroid-filter-brightest': 4,
            '--database': data_dir / 'tetra-database.dat',
            '--star-id-algo': 'tetra',
            '--false-stars': 0,
            '--attitude-algo': 'dqm',
            '--print-attitude': tmp_dir / 'attitude.txt',
        }
    else:
        raise Exception(f"Invalid identification algo {algo}. Must be 'py' or 'tetra'.")
    args.update(overrides)
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
    lost_runner(args)

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
