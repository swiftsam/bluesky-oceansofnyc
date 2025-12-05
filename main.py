import click
from pathlib import Path
from dotenv import load_dotenv
from database import SightingsDatabase
from exif_utils import extract_image_metadata, ExifDataError
from bluesky_client import BlueskyClient

# Load environment variables from .env file
load_dotenv()


@click.group()
def cli():
    """Fisker Ocean spotter Bluesky Bot"""
    pass


@cli.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.argument('license_plate')
def process(image_path: str, license_plate: str):
    """Process a Fisker Ocean sighting image and store it in the database."""
    try:
        click.echo(f"Processing image: {image_path}")
        click.echo(f"License plate: {license_plate}")

        metadata = extract_image_metadata(image_path)
        click.echo(f"✓ Extracted EXIF data:")
        click.echo(f"  - Timestamp: {metadata['timestamp']}")
        click.echo(f"  - Location: {metadata['latitude']}, {metadata['longitude']}")

        db = SightingsDatabase()

        previous_count = db.get_sighting_count(license_plate)

        db.add_sighting(
            license_plate=license_plate,
            timestamp=metadata['timestamp'],
            latitude=metadata['latitude'],
            longitude=metadata['longitude'],
            image_path=str(Path(image_path).absolute())
        )

        new_count = previous_count + 1
        click.echo(f"✓ Sighting saved to database")
        click.echo(f"  - This is sighting #{new_count} for {license_plate}")

    except ExifDataError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--plate', help='Filter by license plate')
def list_sightings(plate: str = None):
    """List all sightings in the database."""
    db = SightingsDatabase()
    sightings = db.get_all_sightings(plate)

    if not sightings:
        if plate:
            click.echo(f"No sightings found for license plate: {plate}")
        else:
            click.echo("No sightings in database")
        return

    click.echo(f"Found {len(sightings)} sighting(s):\n")
    for sighting in sightings:
        click.echo(f"ID: {sighting[0]}")
        click.echo(f"  License Plate: {sighting[1]}")
        click.echo(f"  Timestamp: {sighting[2]}")
        click.echo(f"  Location: {sighting[3]}, {sighting[4]}")
        click.echo(f"  Image: {sighting[5]}")
        click.echo(f"  Recorded: {sighting[6]}\n")


@cli.command()
@click.argument('csv_path', type=click.Path(exists=True))
def import_tlc(csv_path: str):
    """Import NYC TLC vehicle data from CSV file."""
    try:
        click.echo(f"Importing TLC data from: {csv_path}")
        db = SightingsDatabase()

        count = db.import_tlc_data(csv_path)

        click.echo(f"✓ Successfully imported {count:,} TLC vehicle records")
        click.echo(f"  - Total vehicles in database: {db.get_tlc_vehicle_count():,}")

    except Exception as e:
        click.echo(f"Error importing TLC data: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('license_plate')
def lookup_tlc(license_plate: str):
    """Look up NYC TLC vehicle information by license plate."""
    try:
        db = SightingsDatabase()
        vehicle = db.get_tlc_vehicle_by_plate(license_plate)

        if not vehicle:
            click.echo(f"No TLC vehicle found for license plate: {license_plate}")
            return

        click.echo(f"\nTLC Vehicle Information for {license_plate}:\n")
        click.echo(f"  Active: {vehicle[1]}")
        click.echo(f"  Vehicle License Number: {vehicle[2]}")
        click.echo(f"  Owner Name: {vehicle[3]}")
        click.echo(f"  License Type: {vehicle[4]}")
        click.echo(f"  VIN: {vehicle[8]}")
        click.echo(f"  Vehicle Year: {vehicle[12]}")
        click.echo(f"  Wheelchair Accessible: {vehicle[9]}")
        click.echo(f"  Base Name: {vehicle[14]}")
        click.echo(f"  Base Type: {vehicle[15]}")
        click.echo(f"  Base Address: {vehicle[19]}")

    except Exception as e:
        click.echo(f"Error looking up TLC data: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('sighting_id', type=int)
def post(sighting_id: int):
    """Post a sighting to Bluesky by its database ID."""
    try:
        db = SightingsDatabase()

        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sightings WHERE id = ?", (sighting_id,))
        sighting = cursor.fetchone()
        conn.close()

        if not sighting:
            click.echo(f"Error: No sighting found with ID {sighting_id}", err=True)
            raise click.Abort()

        sighting_id, license_plate, timestamp, latitude, longitude, image_path, created_at = sighting

        db = SightingsDatabase()
        sighting_count = db.get_sighting_count(license_plate)

        bluesky = BlueskyClient()
        post_text = bluesky.format_sighting_text(
            license_plate=license_plate,
            sighting_count=sighting_count,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude
        )

        click.echo("\n" + "="*60)
        click.echo("POST PREVIEW")
        click.echo("="*60)
        click.echo(post_text)
        click.echo("\nImage: " + image_path)
        click.echo("="*60 + "\n")

        if not click.confirm("Do you want to post this to Bluesky?"):
            click.echo("Post cancelled.")
            return

        click.echo("\nPosting to Bluesky...")

        response = bluesky.create_sighting_post(
            license_plate=license_plate,
            sighting_count=sighting_count,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            images=[image_path]
        )

        click.echo(f"✓ Successfully posted to Bluesky!")
        click.echo(f"  - Post URI: {response.uri}")

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("\nMake sure to set BLUESKY_HANDLE and BLUESKY_PASSWORD environment variables.", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
