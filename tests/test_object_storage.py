from __future__ import annotations

from types import SimpleNamespace

from api.services.object_storage import S3ObjectStorage


class _FakeS3Client:
    def __init__(self) -> None:
        self.put_payload: dict[str, object] | None = None

    def put_object(self, **kwargs: object) -> None:
        self.put_payload = kwargs

    def get_object(self, **kwargs: object) -> dict[str, object]:
        raise AssertionError("get_object was not expected")

    def delete_object(self, **kwargs: object) -> None:
        raise AssertionError("delete_object was not expected")


def _settings(endpoint_url: str) -> SimpleNamespace:
    return SimpleNamespace(
        s3_bucket="agentmesh-documents",
        s3_endpoint_url=endpoint_url,
        s3_region="us-east-1",
        s3_access_key_id="agentmesh-local",
        s3_secret_access_key="agentmesh-local-secret",
    )


def test_s3_storage_uses_server_side_encryption_for_aws_s3(monkeypatch) -> None:
    fake_client = _FakeS3Client()

    import boto3

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: fake_client)

    storage = S3ObjectStorage(_settings(""))
    storage.put("documents/policy.txt", b"policy", "text/plain")

    assert fake_client.put_payload is not None
    assert fake_client.put_payload["ServerSideEncryption"] == "AES256"


def test_s3_storage_omits_server_side_encryption_for_custom_endpoint(monkeypatch) -> None:
    fake_client = _FakeS3Client()

    import boto3

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: fake_client)

    storage = S3ObjectStorage(_settings("http://minio:9000"))
    storage.put("documents/policy.txt", b"policy", "text/plain")

    assert fake_client.put_payload is not None
    assert "ServerSideEncryption" not in fake_client.put_payload
