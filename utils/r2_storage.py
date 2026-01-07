"""Cloudflare R2 storage utilities for sighting images."""

import os
from typing import BinaryIO

import boto3
from botocore.client import Config


class R2Storage:
    """Cloudflare R2 storage client for image uploads."""

    def __init__(
        self,
        account_id: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        public_url_base: str | None = None,
    ):
        """
        Initialize R2 storage client.

        Args:
            account_id: Cloudflare account ID
            access_key_id: R2 access key ID
            secret_access_key: R2 secret access key
            bucket_name: R2 bucket name
            public_url_base: Public URL base for accessing images (e.g., https://pub-xyz.r2.dev)

        Environment variables (if args not provided):
            CLOUDFLARE_ACCOUNT_ID
            R2_ACCESS_KEY_ID
            R2_SECRET_ACCESS_KEY
            R2_BUCKET_NAME
            R2_PUBLIC_URL_BASE
        """
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.access_key_id = access_key_id or os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY")
        self.bucket_name = bucket_name or os.getenv("R2_BUCKET_NAME")
        self.public_url_base = public_url_base or os.getenv("R2_PUBLIC_URL_BASE")

        if not all([self.account_id, self.access_key_id, self.secret_access_key, self.bucket_name]):
            raise ValueError(
                "R2 credentials not provided. Set CLOUDFLARE_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME environment variables."
            )

        # Initialize S3-compatible client for R2
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    def upload_file(self, file_path: str, object_key: str, content_type: str = "image/jpeg") -> str:
        """
        Upload a file to R2 storage.

        Args:
            file_path: Local path to file
            object_key: Key/path in R2 bucket (e.g., "sightings/image_123.jpg")
            content_type: MIME type of the file

        Returns:
            Public URL of the uploaded file
        """
        with open(file_path, "rb") as f:
            return self.upload_fileobj(f, object_key, content_type)

    def upload_fileobj(
        self, fileobj: BinaryIO, object_key: str, content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload a file object to R2 storage.

        Args:
            fileobj: File-like object to upload
            object_key: Key/path in R2 bucket
            content_type: MIME type of the file

        Returns:
            Public URL of the uploaded file
        """
        self.s3_client.upload_fileobj(
            fileobj,
            self.bucket_name,
            object_key,
            ExtraArgs={"ContentType": content_type, "CacheControl": "public, max-age=31536000"},
        )

        # Return public URL
        if self.public_url_base:
            return f"{self.public_url_base}/{object_key}"
        return f"https://{self.bucket_name}.{self.account_id}.r2.dev/{object_key}"

    def upload_bytes(self, data: bytes, object_key: str, content_type: str = "image/jpeg") -> str:
        """
        Upload bytes to R2 storage.

        Args:
            data: Bytes to upload
            object_key: Key/path in R2 bucket
            content_type: MIME type of the data

        Returns:
            Public URL of the uploaded file
        """
        import io

        return self.upload_fileobj(io.BytesIO(data), object_key, content_type)

    def delete_file(self, object_key: str) -> None:
        """
        Delete a file from R2 storage.

        Args:
            object_key: Key/path of file to delete
        """
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)

    def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in R2 storage.

        Args:
            object_key: Key/path to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except self.s3_client.exceptions.ClientError:
            return False
