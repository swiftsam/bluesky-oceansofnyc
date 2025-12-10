"""TLC (Taxi & Limousine Commission) database operations."""

import psycopg2
import csv
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional


class TLCDatabase:
    """Database operations for NYC TLC vehicle registry."""

    # NYC Open Data API endpoint for TLC vehicle list
    TLC_CSV_URL = "https://data.cityofnewyork.us/api/views/8wbx-tsch/rows.csv?accessType=DOWNLOAD"

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not provided and not found in environment")

    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(self.db_url)

    def download_tlc_csv(self, output_dir: str = "/data/tlc") -> str:
        """
        Download the latest TLC vehicle CSV from NYC Open Data.
        Stores versioned copies and maintains a _latest symlink.

        Args:
            output_dir: Directory to store CSV files (default: /data/tlc for Modal volume)

        Returns:
            Path to the downloaded CSV file

        Raises:
            requests.RequestException: If download fails
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        versioned_file = output_path / f"tlc_vehicles_{timestamp}.csv"
        latest_file = output_path / "tlc_vehicles_latest.csv"

        # Download CSV
        print(f"Downloading TLC vehicle data from {self.TLC_CSV_URL}...")
        response = requests.get(self.TLC_CSV_URL, stream=True)
        response.raise_for_status()

        # Save versioned file
        total_bytes = 0
        with open(versioned_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                total_bytes += len(chunk)

        print(f"✓ Downloaded {total_bytes:,} bytes to {versioned_file}")

        # Update _latest symlink (or copy on systems without symlink support)
        try:
            if latest_file.is_symlink() or latest_file.exists():
                latest_file.unlink()
            latest_file.symlink_to(versioned_file.name)
            print(f"✓ Updated symlink: {latest_file} -> {versioned_file.name}")
        except (OSError, NotImplementedError):
            # Fallback to copying if symlinks not supported
            import shutil
            shutil.copy2(versioned_file, latest_file)
            print(f"✓ Copied to {latest_file}")

        return str(versioned_file)

    def import_tlc_data(self, csv_path: str, filter_fisker: bool = True) -> int:
        """
        Import TLC vehicle data from CSV file.

        Args:
            csv_path: Path to the TLC CSV file
            filter_fisker: If True, only import Fisker vehicles (VIN starts with VCF1)

        Returns:
            Number of records imported
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        import_date = datetime.now().isoformat()
        count = 0
        skipped = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Filter Fisker vehicles during import if requested
                vin = row.get('Vehicle VIN Number', '')
                if filter_fisker and not vin.startswith('VCF1'):
                    skipped += 1
                    continue

                try:
                    cursor.execute("""
                        INSERT INTO tlc_vehicles (
                            active, vehicle_license_number, name, license_type,
                            expiration_date, permit_license_number, dmv_license_plate_number,
                            vehicle_vin_number, wheelchair_accessible, certification_date,
                            hack_up_date, vehicle_year, base_number, base_name,
                            base_type, veh, base_telephone_number, website,
                            base_address, reason, order_date, last_date_updated,
                            last_time_updated, import_date
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (dmv_license_plate_number) DO UPDATE SET
                            active = EXCLUDED.active,
                            vehicle_license_number = EXCLUDED.vehicle_license_number,
                            name = EXCLUDED.name,
                            license_type = EXCLUDED.license_type,
                            expiration_date = EXCLUDED.expiration_date,
                            permit_license_number = EXCLUDED.permit_license_number,
                            vehicle_vin_number = EXCLUDED.vehicle_vin_number,
                            wheelchair_accessible = EXCLUDED.wheelchair_accessible,
                            certification_date = EXCLUDED.certification_date,
                            hack_up_date = EXCLUDED.hack_up_date,
                            vehicle_year = EXCLUDED.vehicle_year,
                            base_number = EXCLUDED.base_number,
                            base_name = EXCLUDED.base_name,
                            base_type = EXCLUDED.base_type,
                            veh = EXCLUDED.veh,
                            base_telephone_number = EXCLUDED.base_telephone_number,
                            website = EXCLUDED.website,
                            base_address = EXCLUDED.base_address,
                            reason = EXCLUDED.reason,
                            order_date = EXCLUDED.order_date,
                            last_date_updated = EXCLUDED.last_date_updated,
                            last_time_updated = EXCLUDED.last_time_updated,
                            import_date = EXCLUDED.import_date
                    """, (
                        row.get('Active', ''),
                        row.get('Vehicle License Number', ''),
                        row.get('Name', ''),
                        row.get('License Type', ''),
                        row.get('Expiration Date', ''),
                        row.get('Permit License Number', ''),
                        row.get('DMV License Plate Number', ''),
                        vin,
                        row.get('Wheelchair Accessible', ''),
                        row.get('Certification Date', ''),
                        row.get('Hack Up Date', ''),
                        row.get('Vehicle Year', ''),
                        row.get('Base Number', ''),
                        row.get('Base Name', ''),
                        row.get('Base Type', ''),
                        row.get('VEH', ''),
                        row.get('Base Telephone Number', ''),
                        row.get('Website', ''),
                        row.get('Base Address', ''),
                        row.get('Reason', ''),
                        row.get('Order Date', ''),
                        row.get('Last Date Updated', ''),
                        row.get('Last Time Updated', ''),
                        import_date
                    ))
                    count += 1
                except psycopg2.IntegrityError:
                    pass

        conn.commit()
        conn.close()

        if filter_fisker:
            print(f"  Skipped {skipped:,} non-Fisker vehicles")

        return count

    def filter_fisker_vehicles(self) -> int:
        """
        Remove all non-Fisker vehicles from the TLC database.
        Fisker VINs start with 'VCF1'.

        Returns:
            Number of Fisker vehicles remaining
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tlc_vehicles WHERE vehicle_vin_number NOT LIKE 'VCF1%'")
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM tlc_vehicles")
        count = cursor.fetchone()[0]
        conn.close()

        return count

    def get_vehicle_by_plate(self, license_plate: str) -> Optional[tuple]:
        """Get TLC vehicle information by license plate."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM tlc_vehicles WHERE dmv_license_plate_number = %s
        """, (license_plate,))

        vehicle = cursor.fetchone()
        conn.close()

        return vehicle

    def get_vehicle_count(self) -> int:
        """Get total count of TLC vehicles in database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM tlc_vehicles")
        count = cursor.fetchone()[0]
        conn.close()

        return count

    def search_plates_wildcard(self, pattern: str) -> list:
        """
        Search for license plates using wildcard pattern.
        Use * for any single character.

        Args:
            pattern: Search pattern like 'T73**580C' where * matches any character

        Returns:
            List of matching vehicle records
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Convert * to SQL wildcard _
        sql_pattern = pattern.replace('*', '_')

        cursor.execute("""
            SELECT dmv_license_plate_number, vehicle_vin_number, vehicle_year,
                   name, base_name, base_type
            FROM tlc_vehicles
            WHERE dmv_license_plate_number LIKE %s
            ORDER BY dmv_license_plate_number
        """, (sql_pattern,))

        results = cursor.fetchall()
        conn.close()

        return results

    def get_all_plates(self) -> list[str]:
        """Get all license plates in the TLC database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT dmv_license_plate_number FROM tlc_vehicles ORDER BY dmv_license_plate_number")
        plates = [row[0] for row in cursor.fetchall()]
        conn.close()

        return plates

    def update_from_nyc_open_data(self, output_dir: str = "/data/tlc") -> dict:
        """
        Download latest TLC data from NYC Open Data and update the database.
        Only imports Fisker vehicles (VIN starts with VCF1) for efficiency.

        Args:
            output_dir: Directory to store CSV files

        Returns:
            dict with statistics: {
                'csv_path': str,
                'fisker_count': int,
                'timestamp': str
            }
        """
        # Download latest CSV
        csv_path = self.download_tlc_csv(output_dir)

        # Import only Fisker vehicles (filter during import for efficiency)
        print("\nImporting Fisker Ocean vehicles (VIN starts with VCF1)...")
        fisker_count = self.import_tlc_data(csv_path, filter_fisker=True)
        print(f"✓ Imported/updated {fisker_count:,} Fisker Ocean vehicles")

        return {
            'csv_path': csv_path,
            'fisker_count': fisker_count,
            'timestamp': datetime.now().isoformat()
        }
