# This file makes the ranking directory a Python package
# Import key components to make them available when importing the package
from .location import get_location_coordinates, compute_proximity_score
from .ranker import rank_and_filter_jobs
from .filter import filter_job

__all__ = [
    'get_location_coordinates',
    'compute_proximity_score',
    'rank_and_filter_jobs',
    'filter_job'
]
