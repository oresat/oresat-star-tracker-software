from dataclasses import dataclass
from pathlib import Path

data_dir = Path(__file__).parents[1] / "data"

@dataclass
class PyDbConfig:
    max_stars: int = 5000
    kvector_min_distance: float = 2e-1
    kvector_max_distance: float = 15e0
    kvector_distance_bins: int = 10_000
    output: Path = data_dir / "py-database.dat"


@dataclass
class TetraDbConfig:
    min_mag: int = 7
    tetra_max_angle: int = 12
    output: Path = data_dir / "tetra-database.dat"
