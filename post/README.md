# Post Module

This module handles posting sightings to Bluesky with images and formatted text.

## Setup

Create an app password in Bluesky:
1. Go to [Settings > App Passwords](https://bsky.app/settings/app-passwords)
2. Create a new app password
3. Add credentials to your `.env` file:

```bash
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_PASSWORD=your-app-password
```

**Note:** Use the app password, not your account password.

## Features

- **Image Compression** - Automatically compresses images to meet Bluesky's 976KB limit
- **Alt Text** - Generates descriptive alt text for accessibility
- **Multi-Image Posts** - Posts both sighting photo and map image
- **Rich Text Formatting** - Creates formatted posts with emojis and data
- **Error Handling** - Robust error handling and retry logic

## Usage

### Initialize Client

```python
from post.bluesky import BlueskyClient

client = BlueskyClient()
```

### Create a Simple Post

```python
response = client.create_post("Hello from Oceans of NYC!")
print(f"Posted: {response.uri}")
```

### Create a Sighting Post

```python
from database import SightingsDatabase

db = SightingsDatabase()

# Get unposted sightings
sightings = db.get_unposted_sightings()

# Get statistics
unique_sighted = db.get_unique_sighted_count()
total_fiskers = db.get_tlc_vehicle_count()
contributor_stats = db.get_all_contributor_sighting_counts()

# Post one or more sightings (max 4)
response = client.create_batch_sighting_post(
    sightings=sightings[:4],  # Up to 4 sightings
    unique_sighted=unique_sighted,
    total_fiskers=total_fiskers,
    contributor_stats=contributor_stats,
)

print(f"Posted: {response.uri}")
```

## Post Format

All posts now use a unified batch format that shows contributor statistics:

```
🌊 +2 sightings in the last 24 hours
🚗 T744480C, T720313C
📈 3.2% ▒▒▒▒▒▒▒▒▒▒ (67 out of 2093)

* Airlineflyer.net +2 → 16
* Andy +1 → 4
* Sam +1 → 55
```

**Format Details:**
- **Header**: Number of sightings in this post
- **Plates**: Comma-separated list of license plates
- **Progress**: Percentage with progress bar showing unique vehicles spotted vs total TLC fleet
- **Contributors**: Each contributor shows:
  - `+N` = sightings in this post
  - `→ Total` = all-time total sightings by this contributor

## Module Structure

- `bluesky.py` - BlueskyClient class for API interactions
- `__init__.py` - Public API exports
