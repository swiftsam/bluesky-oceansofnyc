import os
import io
from pathlib import Path
from typing import Optional
from datetime import datetime
from PIL import Image
from atproto import Client, models
from geocoding import Geocoder


class BlueskyClient:
    def __init__(self, handle: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Bluesky client with credentials.

        Args:
            handle: Bluesky handle (e.g., user.bsky.social). If not provided, reads from BLUESKY_HANDLE env var.
            password: Bluesky app password. If not provided, reads from BLUESKY_PASSWORD env var.
        """
        self.handle = handle or os.getenv('BLUESKY_HANDLE')
        self.password = password or os.getenv('BLUESKY_PASSWORD')

        if not self.handle or not self.password:
            raise ValueError(
                "Bluesky credentials not provided. "
                "Set BLUESKY_HANDLE and BLUESKY_PASSWORD environment variables "
                "or pass them as arguments."
            )

        self.client = Client()
        self.login()

    def login(self):
        """Authenticate with Bluesky."""
        self.client.login(self.handle, self.password)

    def compress_image(self, image_path: str, max_size_kb: int = 950) -> bytes:
        """
        Compress an image to fit within Bluesky's size limit.

        Args:
            image_path: Path to the image file
            max_size_kb: Maximum size in KB (default 950KB, under the 976KB limit)

        Returns:
            Compressed image data as bytes
        """
        img = Image.open(image_path)

        # Convert RGBA to RGB if necessary
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Start with quality 85 and reduce if needed
        quality = 85
        max_size_bytes = max_size_kb * 1024

        while quality > 20:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            size = buffer.tell()

            if size <= max_size_bytes:
                buffer.seek(0)
                return buffer.read()

            quality -= 5

        # If still too large, resize the image
        scale = 0.9
        while quality <= 85:
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            resized.save(buffer, format='JPEG', quality=quality, optimize=True)
            size = buffer.tell()

            if size <= max_size_bytes:
                buffer.seek(0)
                return buffer.read()

            scale -= 0.1
            if scale < 0.3:
                quality += 5

        # Last resort: return whatever we have
        buffer.seek(0)
        return buffer.read()

    def upload_image(self, image_path: str) -> models.AppBskyEmbedImages.Image:
        """
        Upload an image to Bluesky, compressing if necessary.

        Args:
            image_path: Path to the image file

        Returns:
            Image object that can be used in a post
        """
        image_data = self.compress_image(image_path)
        upload_response = self.client.upload_blob(image_data)
        return models.AppBskyEmbedImages.Image(alt='', image=upload_response.blob)

    def create_post(self, text: str, images: Optional[list[str]] = None) -> dict:
        """
        Create a post on Bluesky with optional images.

        Args:
            text: Post text content
            images: Optional list of image file paths (max 4)

        Returns:
            Post response from Bluesky API
        """
        embed = None

        if images:
            if len(images) > 4:
                raise ValueError("Bluesky supports a maximum of 4 images per post")

            uploaded_images = [self.upload_image(img) for img in images]
            embed = models.AppBskyEmbedImages.Main(images=uploaded_images)

        response = self.client.send_post(text=text, embed=embed)
        return response

    def format_sighting_text(
        self,
        license_plate: str,
        sighting_count: int,
        timestamp: str,
        latitude: float,
        longitude: float,
        unique_sighted: int,
        total_fiskers: int
    ) -> str:
        """
        Format the text for a sighting post.

        Args:
            license_plate: Vehicle license plate
            sighting_count: Number of times this plate has been spotted
            timestamp: When the sighting occurred (ISO format)
            latitude: GPS latitude
            longitude: GPS longitude
            unique_sighted: Number of unique Fisker plates sighted
            total_fiskers: Total number of Fisker vehicles in TLC database

        Returns:
            Formatted post text
        """
        ordinal = self._get_ordinal(sighting_count)

        # Format timestamp to human-readable format
        dt = datetime.fromisoformat(timestamp)
        formatted_time = dt.strftime("%B %d, %Y at %I:%M %p")

        # Try to get neighborhood name via reverse geocoding
        geocoder = Geocoder()
        location_text = geocoder.get_neighborhood_name(latitude, longitude)

        # Fall back to coordinates if geocoding fails
        if location_text:
            location_line = f"📍 Spotted in {location_text}"
        else:
            location_line = f"📍 Spotted at {latitude:.4f}, {longitude:.4f}"

        return (
            f"🌊 Fisker Ocean sighting!\n\n"
            f"🚗 Plate: {license_plate}\n"
            f"📈 {unique_sighted} out of {total_fiskers} Oceans collected\n"
            f"🔢 This is the {ordinal} sighting of this vehicle\n"
            f"📅 {formatted_time}\n"
            f"{location_line}"
        )

    def create_sighting_post(
        self,
        license_plate: str,
        sighting_count: int,
        timestamp: str,
        latitude: float,
        longitude: float,
        images: list[str],
        unique_sighted: int,
        total_fiskers: int
    ) -> dict:
        """
        Create a formatted sighting post for Bluesky.

        Args:
            license_plate: Vehicle license plate
            sighting_count: Number of times this plate has been spotted
            timestamp: When the sighting occurred (ISO format)
            latitude: GPS latitude
            longitude: GPS longitude
            images: List of image paths to include
            unique_sighted: Number of unique Fisker plates sighted
            total_fiskers: Total number of Fisker vehicles in TLC database

        Returns:
            Post response from Bluesky API
        """
        text = self.format_sighting_text(
            license_plate=license_plate,
            sighting_count=sighting_count,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            unique_sighted=unique_sighted,
            total_fiskers=total_fiskers
        )

        return self.create_post(text=text, images=images)

    @staticmethod
    def _get_ordinal(n: int) -> str:
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)"""
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        return f"{n}{suffix}"
