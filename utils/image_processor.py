"""Image processing utilities for sightings."""

import io
import os
from pathlib import Path

from PIL import Image


class ImageProcessor:
    """Process and store sighting images in multiple formats."""

    def __init__(self, volume_path: str = "/data"):
        """
        Initialize image processor.

        Args:
            volume_path: Base path for Modal volume storage
        """
        self.volume_path = volume_path
        self.originals_path = f"{volume_path}/images/originals"
        self.web_path = f"{volume_path}/images/web"

        # Ensure directories exist
        os.makedirs(self.originals_path, exist_ok=True)
        os.makedirs(self.web_path, exist_ok=True)

    def save_original(self, image_data: bytes, filename: str) -> str:
        """
        Save original full-resolution image to volume.

        Args:
            image_data: Raw image bytes
            filename: Filename to save as (e.g., "sighting_20240101_123456_1234.jpg")

        Returns:
            Path to saved original image
        """
        original_path = f"{self.originals_path}/{filename}"

        with open(original_path, "wb") as f:
            f.write(image_data)

        return original_path

    def create_web_version(
        self, original_path: str, max_width: int = 1200, max_height: int = 1200, quality: int = 85
    ) -> tuple[bytes, str]:
        """
        Create web-optimized version of image.

        Args:
            original_path: Path to original image
            max_width: Maximum width for web version
            max_height: Maximum height for web version
            quality: JPEG quality (1-100)

        Returns:
            Tuple of (image_bytes, filename)
        """
        img = Image.open(original_path)

        # Convert RGBA to RGB if necessary
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if needed
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        image_bytes = buffer.getvalue()

        # Generate web filename
        original_filename = Path(original_path).name
        web_filename = f"web_{original_filename}"

        return image_bytes, web_filename

    def save_web_version_local(self, web_bytes: bytes, filename: str) -> str:
        """
        Save web version to local volume (for backup/caching).

        Args:
            web_bytes: Processed image bytes
            filename: Filename for web version

        Returns:
            Path to saved web image
        """
        web_path = f"{self.web_path}/{filename}"

        with open(web_path, "wb") as f:
            f.write(web_bytes)

        return web_path

    def process_sighting_image(
        self,
        image_data: bytes,
        filename: str,
        upload_to_r2: bool = True,
        r2_folder: str = "sightings",
    ) -> dict[str, str]:
        """
        Full processing pipeline: save original, create web version, optionally upload to R2.

        Args:
            image_data: Raw image bytes
            filename: Base filename
            upload_to_r2: Whether to upload web version to R2
            r2_folder: Folder path in R2 bucket

        Returns:
            Dictionary with paths:
                - original_path: Local path to original
                - web_path_local: Local path to web version
                - web_url: Public R2 URL (if uploaded)
        """
        # Save original
        original_path = self.save_original(image_data, filename)

        # Create web version
        web_bytes, web_filename = self.create_web_version(original_path)

        # Save web version locally
        web_path_local = self.save_web_version_local(web_bytes, web_filename)

        result = {
            "original_path": original_path,
            "web_path_local": web_path_local,
        }

        # Upload to R2 if requested
        if upload_to_r2:
            try:
                from utils.r2_storage import R2Storage

                r2 = R2Storage()
                object_key = f"{r2_folder}/{web_filename}"
                web_url = r2.upload_bytes(web_bytes, object_key, content_type="image/jpeg")
                result["web_url"] = web_url
                print(f"✓ Uploaded to R2: {web_url}")
            except Exception as e:
                print(f"⚠ R2 upload failed: {e}")
                # Continue without R2 URL - not critical for initial save

        return result
