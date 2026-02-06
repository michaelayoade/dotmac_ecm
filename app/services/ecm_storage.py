import logging
import uuid

import boto3
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    @staticmethod
    def is_configured() -> bool:
        return bool(
            settings.s3_endpoint_url
            and settings.s3_access_key
            and settings.s3_secret_key
        )

    @staticmethod
    def _get_client():  # type: ignore[return]
        if not StorageService.is_configured():
            raise RuntimeError(
                "S3 storage is not configured. "
                "Set S3_ENDPOINT_URL, S3_ACCESS_KEY, and S3_SECRET_KEY."
            )
        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def generate_storage_key(document_id: str, file_name: str) -> str:
        unique = uuid.uuid4().hex[:12]
        return f"documents/{document_id}/{unique}/{file_name}"

    @staticmethod
    def generate_upload_url(storage_key: str, mime_type: str) -> str:
        client = StorageService._get_client()
        url: str = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": storage_key,
                "ContentType": mime_type,
            },
            ExpiresIn=settings.s3_presigned_url_expiry,
        )
        return url

    @staticmethod
    def generate_download_url(storage_key: str) -> str:
        client = StorageService._get_client()
        url: str = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": storage_key,
            },
            ExpiresIn=settings.s3_presigned_url_expiry,
        )
        return url


storage = StorageService()
