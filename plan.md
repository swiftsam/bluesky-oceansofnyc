# Implementation Plan

## Phase 1: Extract and Store Data ✅ COMPLETED

1. ✅ **Image EXIF extraction**: timestamp, latitude, longitude
   - Implemented in `exif_utils.py`
   - Extracts GPS coordinates and converts to decimal degrees
   - Extracts timestamp from EXIF data
   - Raises `ExifDataError` if GPS data is missing

2. ⏸️ **License plate confirmation** using a license plate to VIN lookup API
   - Not yet implemented
   - Currently relies on manual license plate input
   - Future enhancement

3. ✅ **Store record in database** with extracted data and image path
   - Implemented in `database.py`
   - SQLite database stores: license_plate, timestamp, latitude, longitude, image_path, created_at
   - Unique constraint on (license_plate, timestamp) prevents duplicates
   - Tracks sighting count per license plate

## Phase 2: Author Post ✅ PARTIALLY COMPLETED

1. ✅ **Lookup license plate** in sightings database to determine sighting count
   - Implemented in `database.py`: `get_sighting_count()` method
   - Returns total number of sightings for a given license plate

2. ⏸️ **Generate map image** centered on GPS coordinates with marker
   - Not yet implemented
   - Planned to use Mapbox Static Images API or similar
   - Future enhancement

3. ✅ **Compile post content**
   - Implemented in `bluesky_client.py`: `format_sighting_text()` method
   - Text format:
     - 🌊 Fisker Ocean sighting!
     - 🚗 License plate: {license_plate}
     - 🔢 This is the {ordinal} sighting of this vehicle
     - 📅 {human_readable_timestamp}
     - 📍 Spotted at {latitude}, {longitude}
   - ✅ Media attachment: original image (compressed if needed)
   - ⏸️ Media attachment: map image (future enhancement)

## Phase 3: Post to Bluesky ✅ COMPLETED

1. ✅ **Post to Bluesky** using the atproto API
   - Implemented in `bluesky_client.py`
   - Authentication using handle and app password
   - Image upload with automatic compression (max 976KB)
   - Post creation with text and images
   - Preview and confirmation before posting
   - Returns post URI on success

## Current Status

### ✅ Fully Implemented
- EXIF data extraction (GPS + timestamp)
- SQLite database storage
- Sighting counter
- Bluesky authentication
- Image compression for upload
- Post formatting with human-readable timestamps
- CLI interface with three commands (process, list-sightings, post)
- Post preview and confirmation

### ⏸️ Future Enhancements
- License plate to VIN lookup API integration
- Static map image generation and attachment
- Automated posting workflow
- Web interface