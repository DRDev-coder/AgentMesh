from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from api.config import Settings


class ObjectStorage(ABC):
    @abstractmethod
    def put(self, key: str, content: bytes, media_type: str) -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalObjectStorage(ObjectStorage):
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid object key")
        return path

    def put(self, key: str, content: bytes, media_type: str) -> None:
        del media_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class S3ObjectStorage(ObjectStorage):
    def __init__(self, settings: Settings):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 object storage") from exc
        self.bucket = settings.s3_bucket
        self.put_options = {}
        if not settings.s3_endpoint_url:
            self.put_options["ServerSideEncryption"] = "AES256"
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def put(self, key: str, content: bytes, media_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=media_type,
            **self.put_options,
        )

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


class AzureBlobObjectStorage(ObjectStorage):
    def __init__(self, settings: Settings):
        try:
            from azure.core.exceptions import ResourceNotFoundError
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient, ContentSettings
        except ImportError as exc:
            raise RuntimeError(
                "azure-identity and azure-storage-blob are required for Azure Blob Storage"
            ) from exc

        if settings.azure_storage_connection_string:
            service = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        elif settings.azure_storage_account_url:
            service = BlobServiceClient(
                account_url=settings.azure_storage_account_url,
                credential=DefaultAzureCredential(),
            )
        else:
            raise RuntimeError("Azure Blob Storage configuration is incomplete")
        self.container = service.get_container_client(settings.azure_storage_container)
        self.content_settings = ContentSettings
        self.resource_not_found_error = ResourceNotFoundError

    def put(self, key: str, content: bytes, media_type: str) -> None:
        self.container.upload_blob(
            name=key,
            data=content,
            overwrite=True,
            content_settings=self.content_settings(content_type=media_type),
        )

    def get(self, key: str) -> bytes:
        return self.container.download_blob(key).readall()

    def delete(self, key: str) -> None:
        try:
            self.container.delete_blob(key, delete_snapshots="include")
        except self.resource_not_found_error:
            pass


def create_object_storage(settings: Settings) -> ObjectStorage:
    if settings.object_storage_backend == "s3":
        return S3ObjectStorage(settings)
    if settings.object_storage_backend == "azure_blob":
        return AzureBlobObjectStorage(settings)
    return LocalObjectStorage(settings.object_storage_path)
