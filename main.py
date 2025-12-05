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
    """
    Process a Fisker Ocean sighting image and store it in the database.

    If license_plate contains wildcards (*), searches for matches and prompts for selection.
    Example: T73**580C
    """
    try:
        click.echo(f"Processing image: {image_path}")
        click.echo(f"License plate: {license_plate}")

        db = SightingsDatabase()

        # Check if license plate contains wildcards
        if '*' in license_plate:
            click.echo(f"\nSearching for plates matching pattern: {license_plate}")
            results = db.search_plates_wildcard(license_plate.upper())

            if not results:
                click.echo(f"Error: No plates found matching pattern: {license_plate}", err=True)
                raise click.Abort()

            click.echo(f"\nFound {len(results)} matching plate(s):\n")

            # Display options
            for idx, result in enumerate(results, 1):
                plate, vin, year, owner, base_name, base_type = result
                click.echo(f"{idx}. {plate} - {year} (VIN: {vin})")
                click.echo(f"   Owner: {owner}")
                click.echo(f"   Base: {base_name}")
                click.echo()

            # Prompt for selection
            if len(results) == 1:
                if click.confirm(f"Use plate {results[0][0]}?", default=True):
                    license_plate = results[0][0]
                else:
                    click.echo("Operation cancelled.")
                    raise click.Abort()
            else:
                selection = click.prompt(
                    f"Select plate number (1-{len(results)}) or 'q' to quit",
                    type=str
                )

                if selection.lower() == 'q':
                    click.echo("Operation cancelled.")
                    raise click.Abort()

                try:
                    idx = int(selection) - 1
                    if 0 <= idx < len(results):
                        license_plate = results[idx][0]
                        click.echo(f"\nSelected: {license_plate}")
                    else:
                        click.echo("Error: Invalid selection", err=True)
                        raise click.Abort()
                except ValueError:
                    click.echo("Error: Invalid input", err=True)
                    raise click.Abort()

        metadata = extract_image_metadata(image_path)
        click.echo(f"\n✓ Extracted EXIF data:")
        click.echo(f"  - Timestamp: {metadata['timestamp']}")
        click.echo(f"  - Location: {metadata['latitude']}, {metadata['longitude']}")

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
def filter_fiskers():
    """Remove all non-Fisker vehicles from TLC database (keeps only VINs starting with VCF1)."""
    try:
        db = SightingsDatabase()

        original_count = db.get_tlc_vehicle_count()
        click.echo(f"Current TLC vehicles in database: {original_count:,}")

        if not click.confirm("Remove all non-Fisker vehicles? This will keep only vehicles with VINs starting with 'VCF1'"):
            click.echo("Operation cancelled.")
            return

        fisker_count = db.filter_fisker_vehicles()
        removed = original_count - fisker_count

        click.echo(f"✓ Filtered database to Fisker vehicles only")
        click.echo(f"  - Fisker vehicles: {fisker_count:,}")
        click.echo(f"  - Removed: {removed:,}")

    except Exception as e:
        click.echo(f"Error filtering vehicles: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('pattern')
def search_plate(pattern: str):
    """
    Search for license plates using wildcard pattern.

    Use * to match any single character.
    Example: T73**580C will match T731580C, T732580C, etc.
    """
    try:
        db = SightingsDatabase()
        results = db.search_plates_wildcard(pattern.upper())

        if not results:
            click.echo(f"No plates found matching pattern: {pattern}")
            return

        click.echo(f"\nFound {len(results)} matching plate(s):\n")
        click.echo("="*80)

        for result in results:
            plate, vin, year, owner, base_name, base_type = result
            click.echo(f"Plate: {plate}")
            click.echo(f"  VIN: {vin}")
            click.echo(f"  Year: {year}")
            click.echo(f"  Owner: {owner}")
            click.echo(f"  Base: {base_name} ({base_type})")
            click.echo("="*80)

    except Exception as e:
        click.echo(f"Error searching plates: {e}", err=True)
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
        unique_sighted = db.get_unique_sighted_count()
        total_fiskers = db.get_tlc_vehicle_count()

        bluesky = BlueskyClient()
        post_text = bluesky.format_sighting_text(
            license_plate=license_plate,
            sighting_count=sighting_count,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            unique_sighted=unique_sighted,
            total_fiskers=total_fiskers
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
            images=[image_path],
            unique_sighted=unique_sighted,
            total_fiskers=total_fiskers
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
