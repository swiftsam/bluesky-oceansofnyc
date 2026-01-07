from dotenv import load_dotenv

from database import SightingsDatabase
from geolocate.boroughs import get_borough_from_coords

"""Backfill borough values for existing sightings based on GPS coordinates."""

# Load environment variables
load_dotenv()


def backfill_boroughs(dry_run: bool = True):
    """
    Backfill borough values for sightings that have GPS coordinates but no borough.

    Args:
        dry_run: If True, only print what would be updated without making changes
    """
    db = SightingsDatabase()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Find sightings with GPS coordinates but no borough
    cursor.execute(
        """
        SELECT id, license_plate, latitude, longitude
        FROM sightings
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND borough IS NULL
        ORDER BY id
        """
    )

    sightings_to_update = cursor.fetchall()
    print(f"Found {len(sightings_to_update)} sightings with GPS but no borough")

    if len(sightings_to_update) == 0:
        print("Nothing to backfill!")
        conn.close()
        return

    updated_count = 0
    not_in_nyc_count = 0

    for sighting_id, plate, latitude, longitude in sightings_to_update:
        borough = get_borough_from_coords(latitude, longitude)

        if borough:
            if dry_run:
                print(f"[DRY RUN] Would update sighting #{sighting_id} ({plate}): {borough}")
            else:
                cursor.execute(
                    "UPDATE sightings SET borough = %s WHERE id = %s", (borough, sighting_id)
                )
                print(f"✓ Updated sighting #{sighting_id} ({plate}): {borough}")
            updated_count += 1
        else:
            print(
                f"⚠️  Sighting #{sighting_id} ({plate}) at ({latitude}, {longitude}) is outside NYC boroughs"
            )
            not_in_nyc_count += 1

    if not dry_run:
        conn.commit()
        print("\n✅ Backfill complete!")
    else:
        print("\n[DRY RUN] No changes made")

    print(f"   {updated_count} sightings would be/were updated")
    print(f"   {not_in_nyc_count} sightings outside NYC boroughs")

    conn.close()


if __name__ == "__main__":
    import sys

    # Check for --apply flag
    apply = "--apply" in sys.argv

    if apply:
        print("Running backfill with APPLY mode (will update database)")
        backfill_boroughs(dry_run=False)
    else:
        print("Running backfill in DRY RUN mode (no changes will be made)")
        print("Add --apply flag to actually update the database")
        backfill_boroughs(dry_run=True)
