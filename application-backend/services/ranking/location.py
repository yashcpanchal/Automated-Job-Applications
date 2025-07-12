from typing import Optional, Tuple
import asyncio
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import math

# Initialize the geolocator for reverse geocoding
geolocator = Nominatim(user_agent="job_search_agent")
# Cache for locations to avoid repeated geocoding
location_cache = {}

async def get_location_coordinates(location_name: str) -> Optional[Tuple[float, float]]:
    """
    Retrieves latitude and longitude for specified location

    Args:
        location_name (str): The name of the location to geocode.

    Returns:
        Optional[Tuple[float, float]]: A tuple containing latitude and longitude if found,
                                       otherwise None.
    """
    if not location_name:
        return None
    if location_name.lower() in location_cache:
        return location_cache[location_name.lower()]
    try:
        loop = asyncio.get_event_loop()
        location = await loop.run_in_executor(
            None,  # uses default executor
            lambda: geolocator.geocode(location_name)
        )
        if location:
            coords = (location.latitude, location.longitude)
            location_cache[location_name.lower()] = coords
            return coords
        return None
    except Exception as e:
        print(f"Error geocoding location '{location_name}': {e}")
        return None

def compute_proximity_score(user_coordinates, job_coordinates, decay_factor=0.2):
    """
    Computes a proximity score based on the distance between user and job coordinates.
    Args:
        user_coordinates (tuple): A tuple containing the user's latitude and longitude.
        job_coordinates (tuple): A tuple containing the job's latitude and longitude.
        decay_factor (float): The factor by which the score decays with distance.
    Returns:
        float: A proximity score between 0 and 1, where 1 means the job is at the user's location.
    """
    if not user_coordinates or not job_coordinates:
        return 0.3
    distance = geodesic(user_coordinates, job_coordinates).kilometers
    # Closer the job, higher the score; decays exponentially with distance
    score = math.exp(-decay_factor * distance)
    return max(0.0, min(score, 1.0))
