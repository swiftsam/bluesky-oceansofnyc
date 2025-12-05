# Fisker Ocean spotter Bluesky Bot

This bot automates the process of spotting Fisker Ocean vehicles and posting sightings to Bluesky. It extracts relevant data from images, verifies license plates, generates map images, and compiles posts for sharing on the Bluesky platform.

See the [plan.md](plan.md) file for a detailed breakdown of the steps involved in the process.

## Tech Stack
- **Python 3.13+** - Core scripting language
- **uv** - Python environment management
- **SQLite** - Local database for sightings
- **Click** - CLI framework
- **Pillow (PIL)** - Image EXIF extraction and compression
- **atproto** - Bluesky API client
- **python-dotenv** - Environment variable management

### Mapping & Geocoding
- Uses the **staticmap** Python library to generate map images from OpenStreetMap tiles
- Uses **Nominatim** (OpenStreetMap) for reverse geocoding to show neighborhood names
- No API key required
- Adds a red marker at the sighting location
- Respects Nominatim's 1 request/second rate limit

## Installation

```bash
# Install dependencies
uv sync
```

## NYC TLC Vehicle Data

This bot includes support for NYC TLC (Taxi & Limousine Commission) vehicle data, which helps identify and verify Fisker Ocean vehicles operating as for-hire vehicles in NYC.

### Data Source
The TLC vehicle data comes from NYC Open Data:
- **Dataset**: [For Hire Vehicles (FHV) - Active](https://data.cityofnewyork.us/Transportation/For-Hire-Vehicles-FHV-Active/8wbx-tsch/about_data)
- **Updates**: Nightly
- **Records**: 100,000+ active for-hire vehicles in NYC

### Importing TLC Data

Download the latest CSV from the NYC Open Data portal and import it:

```bash
uv run python main.py import-tlc data/For_Hire_Vehicles_FHV_Active_YYYYMMDD.csv
```

**Example output:**
```
✓ Successfully imported 104,821 TLC vehicle records
  - Total vehicles in database: 104,821
```

### Looking up Vehicle Information

Once imported, you can look up any TLC vehicle by license plate:

```bash
uv run python main.py lookup-tlc T731580C
```

**Example output:**
```
TLC Vehicle Information for T731580C:

  Active: YES
  Vehicle License Number: 5801620
  Owner Name: AMERICAN UNITED TRANSPORTATION INC
  License Type: FOR HIRE VEHICLE
  VIN: VCF1ZBU27PG004131
  Vehicle Year: 2023
  Base Name: UBER USA, LLC
  Base Type: BLACK-CAR
  Base Address: 1515 THIRD STREET SAN FRANCISCO CA 94158
```

This data helps verify that spotted vehicles are legitimate TLC-registered Fisker Oceans operating in NYC.

## Configuration

To post to Bluesky, create a `.env` file with your credentials:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your credentials
```

Your `.env` file should contain:
```
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password
```

To create an app password:
1. Go to [Settings > App Passwords](https://bsky.app/settings/app-passwords) in Bluesky
2. Create a new app password
3. Use that password in your `.env` file (not your account password)

## Usage

The bot provides three main commands:

### 1. Process a sighting
Extract EXIF data from an image and save to database:

```bash
uv run python main.py process <image_path> <license_plate>
```

**Example:**
```bash
uv run python main.py process images/ocean.jpg T731580C
```

**Requirements:**
- Image must contain EXIF data with GPS coordinates (latitude/longitude)
- Timestamp will be extracted from EXIF data
- License plate must be provided manually

**Output:**
```
Processing image: images/ocean.jpg
License plate: T731580C
✓ Extracted EXIF data:
  - Timestamp: 2025-11-15T11:18:06
  - Location: 40.7224, -73.9804
✓ Sighting saved to database
  - This is sighting #1 for T731580C
```

### 2. List sightings
View all sightings in the database:

```bash
# List all sightings
uv run python main.py list-sightings

# Filter by specific license plate
uv run python main.py list-sightings --plate T731580C
```

**Output:**
```
Found 2 sighting(s):

ID: 2
  License Plate: T731580C
  Timestamp: 2025-11-15T11:18:06
  Location: 40.7224, -73.9804
  Image: /path/to/images/PXL_20251115_161806313.jpg
  Recorded: 2025-12-04T23:02:08.800436
```

### 3. Post to Bluesky
Post a sighting to Bluesky with preview and confirmation:

```bash
uv run python main.py post <sighting_id>
```

**Example:**
```bash
# First, list sightings to get the ID
uv run python main.py list-sightings

# Then post using the ID
uv run python main.py post 2
```

**Features:**
- Shows a preview of the post before publishing
- Requires confirmation (y/n) before posting
- Automatically compresses images to fit Bluesky's 976KB limit
- Tracks sighting count per license plate
- Generates a map image showing the sighting location
- Posts both the vehicle photo and map image

**Post format:**
```
🌊 Fisker Ocean sighting!

🚗 Plate: T731580C
📈 2 out of 2053 Oceans collected
🔢 This is the 1st sighting of this vehicle
📅 November 15, 2025 at 11:18 AM
📍 Spotted in Alphabet City, Manhattan
```

## Features

- ✅ **EXIF Extraction** - Automatically extracts GPS coordinates and timestamp from images
- ✅ **SQLite Database** - Stores all sightings locally with full history
- ✅ **NYC TLC Data Integration** - Import and query 100,000+ NYC for-hire vehicle records
- ✅ **Vehicle Lookup** - Verify license plates against official TLC database
- ✅ **Wildcard Plate Search** - Find plates with partial matches (e.g., T73**580C)
- ✅ **Collection Progress** - Tracks how many unique Fisker Oceans have been sighted
- ✅ **Map Generation** - Creates static map images showing sighting locations using OpenStreetMap
- ✅ **Neighborhood Geocoding** - Converts GPS coordinates to human-readable NYC neighborhoods (e.g., "Fort Greene, Brooklyn")
- ✅ **Sighting Counter** - Tracks how many times each vehicle has been spotted
- ✅ **Image Compression** - Automatically compresses large images to meet Bluesky's size limits
- ✅ **Post Preview** - Shows exactly what will be posted before publishing
- ✅ **Human-readable Formatting** - Converts timestamps and coordinates to friendly formats