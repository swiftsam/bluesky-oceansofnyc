#!/usr/bin/env python3
"""Generate JSON data file for static website."""

import json
import os
import sys

# Add parent directory to path to import database models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from database.models import SightingsDatabase

# Load environment variables
load_dotenv()


def generate_vehicle_data():
    """Generate JSON file with all TLC vehicles and their sighting data."""
    db = SightingsDatabase()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Get all TLC vehicles with their most recent sighting
    # Prefer web URL from R2, fall back to Modal volume path
    cursor.execute("""
        SELECT
            t.dmv_license_plate_number,
            t.vehicle_vin_number,
            COALESCE(s.image_url_web, s.image_path) as image,
            s.borough,
            s.timestamp
        FROM tlc_vehicles t
        LEFT JOIN LATERAL (
            SELECT image_url_web, image_path, borough, timestamp
            FROM sightings
            WHERE license_plate = t.dmv_license_plate_number
            ORDER BY timestamp DESC
            LIMIT 1
        ) s ON true
        ORDER BY
            t.dmv_license_plate_number
    """)

    vehicles = []
    for row in cursor.fetchall():
        plate, vin, image_path, borough, timestamp = row
        vehicles.append(
            {
                "plate": plate,
                "vin": vin,
                "image": image_path,
                "borough": borough,
                "timestamp": timestamp if timestamp else None,
            }
        )

    conn.close()

    # Write to JSON file
    output_path = os.path.join(os.path.dirname(__file__), "vehicles.json")
    with open(output_path, "w") as f:
        json.dump(
            {
                "vehicles": vehicles,
                "total": len(vehicles),
                "sighted": sum(1 for v in vehicles if v["image"]),
            },
            f,
            indent=2,
        )

    print(f"Generated {output_path}")
    print(f"Total vehicles: {len(vehicles)}")
    print(f"Vehicles with sightings: {sum(1 for v in vehicles if v['image'])}")


if __name__ == "__main__":
    generate_vehicle_data()
