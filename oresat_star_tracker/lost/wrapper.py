# Copyright (c) 2020 Mark Polyakov, Karen Haining, Muki Kiboigo, Edward Zhang, Cullen Sharp,
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
from pathlib import Path

from .types import PyDbConfig, TetraDbConfig
from .utils import find_cli, dict_flatten

cli = find_cli()
cli_dir = cli.parent
data_dir = Path(__file__).parents[2] / "data"


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


def prepare_db_args(cfg: PyDbConfig | TetraDbConfig | None = None) -> dict:
    """
    Return a dictionary of default arguments for `lost.database`.
    """
    cfg = cfg or PyDbConfig()
    if isinstance(cfg, PyDbConfig):
        args = _py_db_args(cfg)
    elif isinstance(cfg, TetraDbConfig):
        args = _tetra_db_args(cfg)

    return args


def generate_db(args: dict = prepare_db_args()) -> None:
    """
    Call LOST's database generation command.

    See Also
    --------
    lost.PyDbConfig : Pyramid database configuration object.
    lost.TetraDbconfig : Tetra database configuration object
    """
    _lost_runner(args)
