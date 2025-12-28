
import numpy as np
from geopy.distance import geodesic

def calculate_geodesic_distance(loc1, loc2):
    """
    Calculate geodesic distance between two (lat, lon) tuples in km.
    """
    return geodesic(loc1, loc2).km

def vectorized_haversine_matrix(locations, start_loc):
    """
    Vectorized Haversine to calculate distance matrix.
    locations: list of dicts with 'lat', 'lon'
    start_loc: (lat, lon) tuple
    Returns: numpy array of shape (N+1, N+1)
    """
    # 1. Prepare Coordinates
    coords = np.array([(d['lat'], d['lon']) for d in locations])
    depot = np.array([start_loc]) # shape (1, 2)
    
    # Combined: [N GVPs, 1 Depot]
    all_coords = np.vstack([coords, depot])
    
    lats = all_coords[:, 0]
    lons = all_coords[:, 1]
    
    # 2. Vectorized Haversine
    # Convert to radians
    lats_rad = np.radians(lats)
    lons_rad = np.radians(lons)
    
    # Differences (Broadcasting: (N, 1) - (1, N))
    dlat = lats_rad[:, np.newaxis] - lats_rad[np.newaxis, :]
    dlon = lons_rad[:, np.newaxis] - lons_rad[np.newaxis, :]
    
    # Formula
    a = np.sin(dlat / 2.0)**2 + np.cos(lats_rad[:, np.newaxis]) * np.cos(lats_rad[np.newaxis, :]) * np.sin(dlon / 2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    R = 6371.0 # Earth Radius km
    matrix = R * c
    
    # Apply Circuity Factor
    matrix *= 1.3
    
    return matrix
