"""
Modal app for automated Bluesky posting of Fisker Ocean sightings.

This serverless app runs scheduled batch posts to Bluesky.
Images are stored in a Modal volume for persistent access.
"""

import modal

# Create Modal app
app = modal.App("oceans-of-nyc")

# Define the container image with all dependencies and source code
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "psycopg2-binary>=2.9.11",
        "pillow>=10.0.0",
        "requests>=2.31.0",
        "atproto>=0.0.55",
        "python-dotenv>=1.0.0",
        "staticmap>=0.5.7",
        "fastapi>=0.115.0",
        "twilio>=9.0.0",
        "imagehash>=4.3.1",
        "boto3>=1.42.23",
    )
    .add_local_python_source("database")
    .add_local_python_source("validate")
    .add_local_python_source("geolocate")
    .add_local_python_source("post")
    .add_local_python_source("chat")
    .add_local_python_source("notify")
    .add_local_python_source("utils")
    .add_local_python_source("web")
)

# Define secrets
# To set these up, run:
# modal secret create bluesky-credentials BLUESKY_HANDLE=<handle> BLUESKY_PASSWORD=<password>
# modal secret create neon-db DATABASE_URL=<connection-string>
# modal secret create twilio-credentials TWILIO_ACCOUNT_SID=<sid> TWILIO_AUTH_TOKEN=<token> TWILIO_PHONE_NUMBER=<number>
# modal secret create cloudflare-r2 CLOUDFLARE_ACCOUNT_ID=<id> R2_ACCESS_KEY_ID=<key> R2_SECRET_ACCESS_KEY=<secret> R2_BUCKET_NAME=<bucket> R2_PUBLIC_URL_BASE=<url>
secrets = [
    modal.Secret.from_name("bluesky-credentials"),
    modal.Secret.from_name("neon-db"),
    modal.Secret.from_name("twilio-credentials"),
    modal.Secret.from_name("cloudflare-r2"),
]

# Create a persistent volume for images and maps
volume = modal.Volume.from_name("oceans-of-nyc", create_if_missing=True)
VOLUME_PATH = "/data"
IMAGES_PATH = f"{VOLUME_PATH}/images"
MAPS_PATH = f"{VOLUME_PATH}/maps"
TLC_PATH = f"{VOLUME_PATH}/tlc"


@app.function(image=image, secrets=secrets, volumes={VOLUME_PATH: volume})
def post_batch(batch_size: int = 4, dry_run: bool = False):
    """
    Post one or more sightings using the unified batch format.

    This is the only posting function needed - it handles 1-4 sightings
    using the same unified format with contributor statistics.

    Args:
        batch_size: Number of sightings to include (1-4, default: 4)
        dry_run: If True, only show what would be posted without actually posting
    """
    import os

    from database import SightingsDatabase
    from post.bluesky import BlueskyClient

    print(f"🚀 Starting multi-post (batch_size: {batch_size}, dry_run: {dry_run})")

    # Ensure directories exist
    os.makedirs(IMAGES_PATH, exist_ok=True)

    # Initialize database and client
    db = SightingsDatabase()

    # Get unposted sightings
    sightings = db.get_unposted_sightings()

    if not sightings:
        print("✓ No unposted sightings found")
        return {"posted": 0, "message": "No unposted sightings"}

    # Limit to batch_size
    if batch_size < 1 or batch_size > 4:
        batch_size = 4

    sightings_to_post = sightings[:batch_size]

    print(f"Found {len(sightings)} unposted sighting(s), posting {len(sightings_to_post)} in batch")

    # Get statistics
    unique_sighted = db.get_unique_sighted_count()
    total_fiskers = db.get_tlc_vehicle_count()

    # Extract info for logging
    plates = [s[1] for s in sightings_to_post]
    contributors = set(s[9] for s in sightings_to_post if s[9])

    print("\n📊 Batch Post Info:")
    print(f"   Plates: {', '.join(plates)}")
    print(f"   Contributors: {len(contributors)}")
    print(f"   Progress: {unique_sighted}/{total_fiskers}")

    if dry_run:
        print("\n🔍 DRY RUN - Not actually posting")
        return {
            "posted": 0,
            "message": f"Dry run: would post {len(sightings_to_post)} sightings",
            "plates": plates,
            "contributors": len(contributors),
        }

    try:
        # Get contributor statistics
        contributor_stats = db.get_all_contributor_sighting_counts()

        # Post to Bluesky
        client = BlueskyClient()
        response = client.create_batch_sighting_post(
            sightings=sightings_to_post,
            unique_sighted=unique_sighted,
            total_fiskers=total_fiskers,
            contributor_stats=contributor_stats,
        )

        # Mark all sightings as posted
        sighting_ids = [s[0] for s in sightings_to_post]
        post_uri = response.uri
        db.mark_batch_as_posted(sighting_ids, post_uri)

        print("\n✓ Batch posted successfully!")
        print(f"  Post URI: {post_uri}")
        print(f"  Marked {len(sighting_ids)} sighting(s) as posted")

        return {
            "posted": len(sighting_ids),
            "post_uri": post_uri,
            "plates": plates,
            "contributors": len(contributors),
            "message": f"Posted {len(sighting_ids)} sightings in batch",
        }

    except Exception as e:
        print(f"❌ Error posting batch: {e}")
        import traceback

        traceback.print_exc()
        return {"posted": 0, "error": str(e), "message": f"Failed to post batch: {e}"}


@app.function(
    image=image,
    secrets=secrets,
    volumes={VOLUME_PATH: volume},
    schedule=modal.Cron("0 22 * * *"),  # Run daily at 6 PM ET (10 PM UTC)
)
def post_sightings_queue():
    """
    Scheduled function that runs daily at 6 PM ET.

    Processes all unposted sightings using the unified batch format:
    - Posts up to 4 sightings at a time via post_batch()
    - If 5+ sightings: posts first 4, then recursively processes remainder
    - If no sightings: exits gracefully

    All posts use the same unified format showing contributor statistics.
    """
    from datetime import datetime

    from database import SightingsDatabase

    print(f"⏰ Scheduled sightings queue post triggered at {datetime.now()}")

    # Check how many unposted sightings we have
    db = SightingsDatabase()
    sightings = db.get_unposted_sightings()

    if not sightings:
        print("✓ No unposted sightings found")
        return {"posted": 0, "message": "No unposted sightings"}

    num_sightings = len(sightings)
    print(f"Found {num_sightings} unposted sighting(s)")

    # Always use batch format (unified format)
    print(f"Using unified format for {min(num_sightings, 4)} sightings")
    result = post_batch.remote(batch_size=4, dry_run=False)
    print(f"✓ Posted batch: {result}")

    # If there are more than 4 sightings, recursively process the remainder
    if num_sightings > 4:
        print(f"\n🔄 {num_sightings - 4} sightings remaining, processing next batch...")
        import time

        time.sleep(2)  # Brief pause between batches
        next_result = post_sightings_queue.remote()

        # Combine results
        total_posted = result.get("posted", 0) + next_result.get("posted", 0)
        return {
            "posted": total_posted,
            "batches": 2,
            "message": f"Posted {total_posted} sightings across multiple batches",
        }

    return result


@app.function(
    image=image,
    secrets=secrets,
)
def get_stats():
    """Get database statistics."""
    from database import SightingsDatabase

    db = SightingsDatabase()

    stats = {
        "total_sightings": len(db.get_all_sightings()),
        "unique_posted": db.get_unique_posted_count(),
        "unique_sighted": db.get_unique_sighted_count(),
        "total_vehicles": db.get_tlc_vehicle_count(),
        "unposted": len(db.get_unposted_sightings()),
    }

    print("\n📊 Database Statistics:")
    print(f"   Total sightings: {stats['total_sightings']}")
    print(f"   Unique plates sighted: {stats['unique_sighted']}")
    print(f"   Unique plates posted: {stats['unique_posted']}")
    print(f"   Total TLC vehicles: {stats['total_vehicles']}")
    print(f"   Unposted sightings: {stats['unposted']}")

    return stats


@app.function(image=image)
def get_hello():
    """Test basic connectivity without secrets."""
    import sys

    print("✓ Modal function executed successfully!")
    print(f"Python version: {sys.version}")
    print("✓ Source files mounted correctly")

    # Try importing our modules
    try:
        print("✓ database module imported successfully")
    except Exception as e:
        print(f"✗ Error importing database: {e}")

    try:
        print("✓ post.bluesky module imported successfully")
    except Exception as e:
        print(f"✗ Error importing post.bluesky: {e}")

    try:
        print("✓ geolocate module imported successfully")
    except Exception as e:
        print(f"✗ Error importing geolocate: {e}")

    try:
        print("✓ validate module imported successfully")
    except Exception as e:
        print(f"✗ Error importing validate: {e}")

    return {"status": "success"}


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
)
def upload_image(filename: str, image_data: bytes):
    """
    Upload an image to the Modal volume.

    Args:
        filename: Name for the image file
        image_data: Raw image bytes
    """
    import os

    os.makedirs(IMAGES_PATH, exist_ok=True)

    file_path = f"{IMAGES_PATH}/{filename}"
    with open(file_path, "wb") as f:
        f.write(image_data)

    volume.commit()

    size = len(image_data) / 1024
    print(f"✓ Uploaded {filename} ({size:.1f} KB)")

    return {"filename": filename, "size_kb": size, "path": file_path}


# ==================== Twilio SMS/MMS Webhook ====================


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("neon-db"),
        modal.Secret.from_name("twilio-credentials"),
    ],
    volumes={VOLUME_PATH: volume},
)
@modal.asgi_app()
def chat_sms_webhook():
    """
    Twilio SMS/MMS webhook endpoint.

    Configure this URL in your Twilio phone number settings:
    https://wallabout--oceans-of-nyc-chat-sms-webhook.modal.run

    Twilio sends POST requests with form-encoded data including:
    - From: Sender phone number
    - Body: Message text
    - NumMedia: Number of media attachments
    - MediaUrl0, MediaUrl1, etc.: URLs to media files
    - MediaContentType0, etc.: MIME types of media
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import Response

    from chat.webhook import handle_incoming_sms, parse_twilio_request

    web_app = FastAPI()

    @web_app.post("/")
    async def handle_sms(request: Request):
        print("📨 Received webhook request")

        # Get the raw body from the request
        body = await request.body()

        data = parse_twilio_request(body)

        # Extract message details
        from_number = data.get("From", "unknown")
        message_body = data.get("Body", "")
        num_media = int(data.get("NumMedia", 0))

        # Determine channel type (SMS, MMS, RCS, etc.)
        # Twilio provides this in the webhook data
        channel_type = data.get("MessagingServiceChannelType", "sms").lower()

        # Collect media URLs and types
        media_urls = []
        media_types = []
        for i in range(num_media):
            url = data.get(f"MediaUrl{i}")
            mtype = data.get(f"MediaContentType{i}")
            if url:
                media_urls.append(url)
                media_types.append(mtype or "unknown")

        # Handle the message
        twiml_response = handle_incoming_sms(
            from_number=from_number,
            body=message_body,
            num_media=num_media,
            media_urls=media_urls,
            media_types=media_types,
            volume_path=VOLUME_PATH,
            channel_type=channel_type,
        )

        # Commit volume changes if any images were saved
        volume.commit()

        # Return TwiML response
        return Response(
            content=twiml_response,
            media_type="application/xml",
        )

    @web_app.get("/")
    async def health_check():
        return {"status": "ok", "service": "fisker-ocean-sms-webhook"}

    return web_app


# ==================== TLC Data Updates ====================


@app.function(
    image=image,
    secrets=secrets,
    volumes={VOLUME_PATH: volume},
    timeout=300,
    schedule=modal.Cron("0 7 * * *"),  # Run daily at 3 AM ET (7 AM UTC)
)
def update_tlc_vehicles():
    """
    Download latest TLC vehicle data from NYC Open Data and update the database.
    Stores versioned CSVs in Modal volume and filters to Fisker vehicles only.

    Runs automatically every day at 3 AM ET.
    Can also be triggered manually via: modal run modal_app.py --command=update-tlc
    """
    import os
    from datetime import datetime

    from validate.tlc import TLCDatabase

    print(f"🚀 Starting TLC data update at {datetime.now()}")
    print(f"{'='*60}")

    # Ensure TLC directory exists
    os.makedirs(TLC_PATH, exist_ok=True)

    try:
        # Initialize TLC database
        tlc_db = TLCDatabase()

        # Download, import, and filter
        result = tlc_db.update_from_nyc_open_data(output_dir=TLC_PATH)

        # Commit volume changes to persist CSVs
        volume.commit()

        print(f"\n{'='*60}")
        print("✓ TLC data update complete!")
        print(f"  CSV: {result['csv_path']}")
        print(f"  Fisker vehicles: {result['fisker_count']:,}")
        print(f"  Timestamp: {result['timestamp']}")
        print(f"{'='*60}")

        return result

    except Exception as e:
        print(f"❌ Error updating TLC data: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@app.function(image=image, secrets=secrets, volumes={VOLUME_PATH: volume}, timeout=3600)
def backfill_image_hashes(batch_size: int = 100, dry_run: bool = False):
    """
    Backfill image hashes for existing sightings in Modal volume.

    Args:
        batch_size: Number of sightings to process in each batch
        dry_run: If True, show what would be done without updating database
    """
    import os

    from database import SightingsDatabase
    from utils.image_hashing import ImageHashError, calculate_both_hashes

    print("🔄 Starting image hash backfill on Modal...")
    print(f"   Batch size: {batch_size}")
    if dry_run:
        print("   DRY RUN MODE - no changes will be made")
    print()

    db = SightingsDatabase()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Get all sightings without hashes
    cursor.execute(
        """
        SELECT id, image_path
        FROM sightings
        WHERE image_hash_sha256 IS NULL OR image_hash_perceptual IS NULL
        ORDER BY id ASC
        """
    )

    sightings = cursor.fetchall()
    total = len(sightings)

    if total == 0:
        print("✓ All sightings already have hashes!")
        conn.close()
        return {"status": "complete", "processed": 0, "successful": 0, "skipped": 0}

    print(f"Found {total} sightings without hashes\n")

    processed = 0
    successful = 0
    skipped = 0
    failed = []

    for sighting_id, image_path in sightings:
        processed += 1

        # Check if file exists
        if not os.path.exists(image_path):
            print(f"⚠️  Sighting #{sighting_id}: Image file not found: {image_path}")
            skipped += 1
            failed.append((sighting_id, image_path, "File not found"))
            continue

        try:
            # Calculate hashes
            sha256, phash = calculate_both_hashes(image_path)

            if dry_run:
                print(
                    f"[DRY RUN] Would update sighting #{sighting_id}: "
                    f"SHA256={sha256[:16]}..., pHash={phash}"
                )
                successful += 1
            else:
                # Update database
                cursor.execute(
                    """
                    UPDATE sightings
                    SET image_hash_sha256 = %s, image_hash_perceptual = %s
                    WHERE id = %s
                    """,
                    (sha256, phash, sighting_id),
                )

                successful += 1

                # Commit in batches
                if successful % batch_size == 0:
                    conn.commit()
                    print(
                        f"✓ Committed batch of {batch_size} updates (total: {successful}/{total})"
                    )

        except ImageHashError as e:
            print(f"❌ Sighting #{sighting_id}: Failed to calculate hashes: {e}")
            failed.append((sighting_id, image_path, str(e)))
            continue

        except Exception as e:
            print(f"❌ Sighting #{sighting_id}: Unexpected error: {e}")
            failed.append((sighting_id, image_path, str(e)))
            continue

    # Final commit
    if not dry_run and successful > 0:
        conn.commit()
        print("\n✓ Final commit completed")

    # Commit volume changes
    volume.commit()

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total sightings processed: {processed}")
    print(f"Successfully updated:       {successful}")
    print(f"Skipped (file not found):  {skipped}")
    print(f"Failed:                    {len(failed)}")

    if failed and len(failed) <= 10:
        print("\nFailed sightings:")
        for sighting_id, image_path, error in failed:
            print(f"  #{sighting_id}: {error}")
            print(f"    Path: {image_path}")
    elif failed:
        print(f"\n{len(failed)} sightings failed (showing first 10):")
        for sighting_id, _image_path, error in failed[:10]:
            print(f"  #{sighting_id}: {error}")

    if dry_run:
        print("\n⚠️  DRY RUN - no changes were made to the database")
    else:
        print(f"\n✅ Backfill complete! Updated {successful}/{total} sightings")

    return {
        "status": "complete",
        "processed": processed,
        "successful": successful,
        "skipped": skipped,
        "failed": len(failed),
        "dry_run": dry_run,
    }


@app.function(image=image, secrets=secrets)
def generate_web_data():
    """
    Generate vehicles.json and upload to R2 at /web/vehicles.json.

    This function queries the database for all TLC vehicles and their most recent
    sightings, then generates a JSON file and uploads it to R2 for the static website.

    Can be triggered manually via: modal run modal_app.py --command=generate-web-data
    """
    from web.generate_data import generate_vehicle_data

    print("🔄 Generating vehicle data for web...")
    result = generate_vehicle_data(upload_to_r2=True)

    if result["status"] == "success":
        print("✓ Vehicle data generated and uploaded successfully")
        print(f"  URL: {result['url']}")
        print(f"  Total vehicles: {result['total']}")
        print(f"  Vehicles with sightings: {result['sighted']}")
    else:
        print(f"❌ Failed to generate vehicle data: {result}")

    return result


@app.function(image=image, secrets=secrets, volumes={VOLUME_PATH: volume}, timeout=3600)
def backfill_r2_images(batch_size: int = 10, dry_run: bool = False):
    """
    Backfill existing images to Cloudflare R2 and update database URLs.

    This function:
    1. Finds all sightings without image_url_web
    2. Creates web-optimized versions from originals (or from image_path if no original)
    3. Uploads to R2
    4. Updates database with R2 URLs

    Args:
        batch_size: Number of images to process before committing (default: 10)
        dry_run: If True, show what would be done without uploading or updating database
    """
    import os

    from database import SightingsDatabase
    from utils.image_processor import ImageProcessor
    from utils.r2_storage import R2Storage

    print("🔄 Starting R2 backfill on Modal...")
    print(f"   Batch size: {batch_size}")
    if dry_run:
        print("   DRY RUN MODE - no uploads or changes will be made")
    print()

    db = SightingsDatabase()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Get all sightings without R2 URLs
    cursor.execute(
        """
        SELECT id, image_path, image_path_original
        FROM sightings
        WHERE image_url_web IS NULL
        ORDER BY id ASC
        """
    )

    sightings = cursor.fetchall()
    total = len(sightings)

    if total == 0:
        print("✓ All sightings already have R2 URLs!")
        conn.close()
        return {"status": "complete", "processed": 0, "successful": 0, "skipped": 0}

    print(f"Found {total} sightings without R2 URLs\n")

    # Initialize processors
    processor = ImageProcessor(volume_path=VOLUME_PATH)
    r2: R2Storage | None
    if not dry_run:
        r2 = R2Storage()
    else:
        r2 = None

    processed = 0
    successful = 0
    skipped = 0
    failed = []

    for sighting_id, image_path, image_path_original in sightings:
        processed += 1

        # Determine source image path (prefer original, fallback to image_path)
        source_path = image_path_original if image_path_original else image_path

        if not source_path:
            print(f"⚠️  Sighting #{sighting_id}: No image path found")
            skipped += 1
            failed.append((sighting_id, None, "No image path"))
            continue

        # Check if file exists
        if not os.path.exists(source_path):
            print(f"⚠️  Sighting #{sighting_id}: Image file not found: {source_path}")
            skipped += 1
            failed.append((sighting_id, source_path, "File not found"))
            continue

        try:
            # Extract filename for R2 key
            from pathlib import Path

            filename = Path(source_path).name
            # Replace extension with .jpg for web version
            web_filename = Path(filename).stem + "_web.jpg"
            r2_key = f"sightings/{web_filename}"

            # Create web-optimized version
            web_bytes, _ = processor.create_web_version(source_path)

            if dry_run:
                print(
                    f"[DRY RUN] Would upload sighting #{sighting_id}: "
                    f"{len(web_bytes)} bytes → {r2_key}"
                )
                successful += 1
            elif r2 is not None:
                # Upload to R2
                web_url = r2.upload_bytes(web_bytes, r2_key, content_type="image/jpeg")

                # Update database
                cursor.execute(
                    """
                    UPDATE sightings
                    SET image_url_web = %s
                    WHERE id = %s
                    """,
                    (web_url, sighting_id),
                )

                print(f"✓ Sighting #{sighting_id}: Uploaded to {web_url}")
                successful += 1

                # Commit in batches
                if successful % batch_size == 0:
                    conn.commit()
                    print(
                        f"✓ Committed batch of {batch_size} updates (total: {successful}/{total})"
                    )

        except Exception as e:
            print(f"❌ Sighting #{sighting_id}: Failed: {e}")
            failed.append((sighting_id, source_path, str(e)))
            continue

    # Final commit
    if not dry_run and successful > 0:
        conn.commit()
        print("\n✓ Final commit completed")

    # Commit volume changes
    volume.commit()

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total sightings processed: {processed}")
    print(f"Successfully uploaded:      {successful}")
    print(f"Skipped (no file):         {skipped}")
    print(f"Failed:                    {len(failed)}")

    if failed and len(failed) <= 10:
        print("\nFailed sightings:")
        for sighting_id, image_path, error in failed:
            print(f"  #{sighting_id}: {error}")
            if image_path:
                print(f"    Path: {image_path}")
    elif failed:
        print(f"\n{len(failed)} sightings failed (showing first 10):")
        for sighting_id, _image_path, error in failed[:10]:
            print(f"  #{sighting_id}: {error}")

    if dry_run:
        print("\n⚠️  DRY RUN - no uploads or changes were made")
    else:
        print(f"\n✅ Backfill complete! Uploaded {successful}/{total} images to R2")

    return {
        "status": "complete",
        "processed": processed,
        "successful": successful,
        "skipped": skipped,
        "failed": len(failed),
        "dry_run": dry_run,
    }


@app.local_entrypoint()
def main(
    command: str = "stats",
    limit: int = 5,
    dry_run: bool = False,
    file: str = None,
):
    """
    Local CLI for testing Modal functions.

    Usage:
        modal run modal_app.py --command=test
        modal run modal_app.py --command=stats
        modal run modal_app.py --command=post --limit=3 --dry-run=true
        modal run modal_app.py --command=upload --file=path/to/image.jpg
        modal run modal_app.py --command=sync-images
        modal run modal_app.py --command=update-tlc
        modal run modal_app.py --command=backfill-hashes --dry-run=true
        modal run modal_app.py --command=generate-web-data
    """
    import os
    from pathlib import Path

    if command == "test":
        result = get_hello.remote()
        print(f"\nTest result: {result}")
    elif command == "stats":
        get_stats.remote()
    elif command == "post":
        # Use the unified batch posting (works for any number of sightings 1-4)
        post_batch.remote(batch_size=limit if limit <= 4 else 4, dry_run=dry_run)
    elif command == "upload":
        if not file:
            print("✗ Error: --file is required for upload command")
            return
        if not os.path.exists(file):
            print(f"✗ Error: File not found: {file}")
            return

        with open(file, "rb") as f:
            image_data = f.read()
        filename = Path(file).name
        upload_image.remote(filename, image_data)
    elif command == "sync-images":
        # Sync all images from local sightings directory
        local_images_dir = Path("sightings")
        if not local_images_dir.exists():
            print("✗ Error: Local sightings directory not found")
            return

        image_files = (
            list(local_images_dir.glob("*.jpg"))
            + list(local_images_dir.glob("*.jpeg"))
            + list(local_images_dir.glob("*.png"))
        )
        print(f"Found {len(image_files)} images to sync")

        for img_path in image_files:
            print(f"Uploading {img_path.name}...")
            with open(img_path, "rb") as f:
                image_data = f.read()
            upload_image.remote(img_path.name, image_data)

        print(f"\n✓ Synced {len(image_files)} images to Modal volume")
    elif command == "update-tlc":
        print("🔄 Updating TLC vehicle data...")
        update_tlc_vehicles.remote()
    elif command == "backfill-hashes":
        print("🔄 Backfilling image hashes...")
        result = backfill_image_hashes.remote(batch_size=100, dry_run=dry_run)
        print(f"\n✓ Backfill result: {result}")
    elif command == "backfill-r2":
        print("🔄 Backfilling images to R2...")
        result = backfill_r2_images.remote(batch_size=10, dry_run=dry_run)
        print(f"\n✓ Backfill result: {result}")
    elif command == "generate-web-data":
        print("🔄 Generating web data...")
        result = generate_web_data.remote()
        print(f"\n✓ Result: {result}")
    else:
        print(f"Unknown command: {command}")
        print(
            "Available commands: test, stats, post, upload, sync-images, update-tlc, backfill-hashes, backfill-r2, generate-web-data"
        )
