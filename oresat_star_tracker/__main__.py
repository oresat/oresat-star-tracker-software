import logging
from argparse import ArgumentParser
from pathlib import Path

from oresat_cand import NodeClient

from .ar013x import Ar013x
from .gen.star_tracker_od import StarTrackerEntry
from .star_tracker import StarTracker
from .ui import Ui


def main():
    parser = ArgumentParser()
    parser.add_argument("-m", "--mock-hw", action="store_true", help="mock hardware")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    args = parser.parse_args()

    LOG_FMT = "%(levelname)s: %(filename)s:%(lineno)s - %(message)s"
    logging.basicConfig(format=LOG_FMT)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    od_config_path = Path(__file__).parent / "gen/od.csv"
    node = NodeClient(StarTrackerEntry, od_config_path=od_config_path)

    camera = Ar013x(args.mock_hw)

    star_tracker = StarTracker(node, camera)

    ui = Ui(node, star_tracker)

    star_tracker.run(thread=True)
    try:
        ui.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
