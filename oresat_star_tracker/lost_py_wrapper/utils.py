from pathlib import Path


def find_cli() -> Path:
    # return a path to the lost cli

    root = Path(__file__).resolve().parents[2]
    return root / "build" / "lost"


def dict_flatten(dictionary: dict) -> list:
    '''
    'flattens' a dictionary into a list, skipping None values.

    {'a': 'b', 'c': None, 'd': 3.14} -> ['a', 'b', 'c', 'd', 3.14]
    '''
    arr = []
    for key, value in dictionary.items():
        arr.append(key)
        if value is not None:
            arr.append(value)
    return arr
