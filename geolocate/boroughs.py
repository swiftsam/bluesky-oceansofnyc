"""NYC borough detection from GPS coordinates."""

# Approximate bounding boxes for NYC boroughs
# Format: (min_lat, max_lat, min_lon, max_lon)
BOROUGH_BOUNDS = {
    "Manhattan": (40.700, 40.882, -74.019, -73.907),
    "Brooklyn": (40.570, 40.739, -74.042, -73.833),
    "Queens": (40.541, 40.800, -73.962, -73.700),
    "Bronx": (40.785, 40.917, -73.934, -73.749),
    "Staten Island": (40.477, 40.651, -74.256, -74.050),
}


def get_borough_from_coords(latitude: float, longitude: float) -> str | None:
    """
    Determine NYC borough from GPS coordinates.

    Args:
        latitude: GPS latitude
        longitude: GPS longitude

    Returns:
        Borough name ("Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island")
        or None if coordinates are outside NYC
    """
    for borough, (min_lat, max_lat, min_lon, max_lon) in BOROUGH_BOUNDS.items():
        if min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon:
            return borough

    return None


def parse_borough_input(user_input: str) -> str | None:
    """
    Parse user's borough input (single letter or full name).

    Accepts:
    - B, b, Brooklyn
    - M, m, Manhattan
    - Q, q, Queens
    - X, x, Bronx
    - S, s, Staten Island, SI

    Args:
        user_input: User's text input

    Returns:
        Canonical borough name or None if invalid
    """
    user_input = user_input.strip().upper()

    borough_map = {
        "B": "Brooklyn",
        "BROOKLYN": "Brooklyn",
        "M": "Manhattan",
        "MANHATTAN": "Manhattan",
        "Q": "Queens",
        "QUEENS": "Queens",
        "X": "Bronx",
        "BRONX": "Bronx",
        "S": "Staten Island",
        "STATEN ISLAND": "Staten Island",
        "SI": "Staten Island",
    }

    return borough_map.get(user_input)
