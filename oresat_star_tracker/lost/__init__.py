"""LOST star identification integration."""

try:
    from oresat_star_tracker._lost_core import estimate as estimate_native
except ImportError:
    estimate_native = None  # type: ignore[misc, assignment]

__all__ = ["estimate_native"]
