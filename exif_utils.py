from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime


class ExifDataError(Exception):
    """Raised when image lacks required EXIF data."""
    pass


def get_exif_data(image_path: str) -> dict:
    """Extract EXIF data from an image."""
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()

        if not exif_data:
            raise ExifDataError(f"No EXIF data found in image: {image_path}")

        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value

        return exif
    except AttributeError:
        raise ExifDataError(f"No EXIF data found in image: {image_path}")
    except FileNotFoundError:
        raise ExifDataError(f"Image file not found: {image_path}")


def get_gps_data(exif: dict) -> dict:
    """Extract GPS data from EXIF dictionary."""
    if 'GPSInfo' not in exif:
        raise ExifDataError("No GPS data found in EXIF")

    gps_info = {}
    for key, value in exif['GPSInfo'].items():
        decode = GPSTAGS.get(key, key)
        gps_info[decode] = value

    return gps_info


def convert_to_degrees(value) -> float:
    """Convert GPS coordinates to degrees in float format."""
    d, m, s = value
    return d + (m / 60.0) + (s / 3600.0)


def get_coordinates(gps_info: dict) -> tuple[float, float]:
    """Extract latitude and longitude from GPS info."""
    if 'GPSLatitude' not in gps_info or 'GPSLongitude' not in gps_info:
        raise ExifDataError("GPS coordinates not found in EXIF data")

    lat = convert_to_degrees(gps_info['GPSLatitude'])
    lon = convert_to_degrees(gps_info['GPSLongitude'])

    if gps_info.get('GPSLatitudeRef') == 'S':
        lat = -lat
    if gps_info.get('GPSLongitudeRef') == 'W':
        lon = -lon

    return lat, lon


def get_timestamp(exif: dict) -> str:
    """Extract timestamp from EXIF data."""
    datetime_original = exif.get('DateTimeOriginal') or exif.get('DateTime')

    if not datetime_original:
        raise ExifDataError("No timestamp found in EXIF data")

    try:
        dt = datetime.strptime(datetime_original, '%Y:%m:%d %H:%M:%S')
        return dt.isoformat()
    except ValueError:
        return datetime_original


def extract_image_metadata(image_path: str) -> dict:
    """
    Extract all required metadata from an image.

    Returns:
        dict with keys: timestamp, latitude, longitude

    Raises:
        ExifDataError: If required EXIF data is missing
    """
    exif = get_exif_data(image_path)
    gps_info = get_gps_data(exif)
    lat, lon = get_coordinates(gps_info)
    timestamp = get_timestamp(exif)

    return {
        'timestamp': timestamp,
        'latitude': lat,
        'longitude': lon
    }
