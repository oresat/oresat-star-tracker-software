from dataclasses import dataclass
from enum import Enum
from pathlib import Path

tmp_dir = Path(__file__).parent / 'tmp'
data_dir = Path(__file__).parent / 'data'


class CentroidAlgo(Enum):
    cog = 'cog'
    dummy = 'dummy'
    iwcog = 'iwcog'


class StarIdAlgo(Enum):
    py = 'py'
    dummy = 'dummy'
    gv = 'dv'
    tetra = 'tetra'


@dataclass
class PyDbConfig:
    max_stars: int = 5000
    kvector_min_distance: float = 2e-1
    kvector_max_distance: float = 15e0
    kvector_distance_bins: int = 10_000
    output: Path = data_dir / 'py-database.dat'


@dataclass
class TetraDbConfig:
    min_mag: int = 7
    tetra_max_angle: int = 12
    output: Path = data_dir / 'tetra-database.dat'


@dataclass
class PyEstimateConfig:
    focal_length: int = 49
    pixel_size: float = 22.2e0
    centroid_algo: str = CentroidAlgo('cog').name
    centroid_mag_filter: int = 5
    database: Path = data_dir / 'py-database.dat'
    star_id_algo: str = StarIdAlgo['py'].name
    angular_tolerance: float = 5e-2
    false_stars: int = 1000
    max_mismatch_prob: float = 1e-4
    attitude_algo: str = 'dqm'


@dataclass
class TetraEstimateConfig:
    fov: int = 17
    CentroidAlgo: str = CentroidAlgo['cog'].name
    centroid_filter_brightest: int = 4
    database: Path = data_dir / 'tetra-database.dat'
    star_id_algo: str = StarIdAlgo['tetra'].name
    false_stars: int = 0
    attitude_algo: str = 'dqm'
