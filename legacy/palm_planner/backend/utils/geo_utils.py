import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in meters using Haversine formula"""
    R = 6371000  # Earth radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon/2) * math.sin(delta_lon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def bounds_to_area_hectares(bounds):
    """Calculate approximate area of bounds in hectares"""
    sw = bounds['_southWest']
    ne = bounds['_northEast']
    
    # Calculate approximate distance (simplified)
    width = calculate_distance(sw['lat'], sw['lng'], sw['lat'], ne['lng'])
    height = calculate_distance(sw['lat'], sw['lng'], ne['lat'], sw['lng'])
    
    area_sq_m = width * height
    area_hectares = area_sq_m / 10000
    
    return area_hectares