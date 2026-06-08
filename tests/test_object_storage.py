from __future__ import annotations

import sys
from io import BytesIO
from hashlib import sha256

import pytest

from draftcheck_core.config import Settings
from draftcheck_core.object_storage import (
    LocalObjectStorage,
    S3ObjectStorage,
    check_object_storage_ready,
    check_s3_object_storage_ready,
    get_export_storage,
    get_object_storage,
    get_parsed_source_storage,
    get_raw_source_storage,
    get_upload_storage,
)


def test_object_storage_factory_uses_local_storage_without_s3(tmp_path):
    settings = Settings(object_storage_root=str(tmp_path), s3_endpoint_url="")

    storage = get_object_storage(settings)
    stored = storage.put_bytes("uploads/example.txt", b"hello")

    assert isinstance(storage, LocalObjectStorage)
    assert storage.get_bytes(stored.object_key) == b"hello"
    assert storage.exists(stored.object_key)


def test_local_object_storage_content_sha256_hashes_raw_bytes(tmp_path):
    content = b"\xff\x00binary\x80"
    storage = LocalObjectStorage(str(tmp_path))

    stored = storage.put_bytes("uploads/binary.bin", content)

    assert stored.content_sha256 == sha256(content).hexdigest()


def test_local_object_storage_rejects_path_traversal_keys(tmp_path):
    storage = LocalObjectStorage(str(tmp_path))

    with pytest.raises(ValueError, match="Invalid object key"):
        storage.put_bytes("../outside.txt", b"nope")

    assert not (tmp_path.parent / "outside.txt").exists()


def test_s3_object_storage_put_get_exists_and_readiness():
    settings = Settings(
        s3_endpoint_url="http://minio:9000",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="secret",
        s3_bucket_uploads="uploads",
    )
    client = FakeMinio(existing_buckets={"uploads"})
    storage = S3ObjectStorage(settings, client=client)

    stored = storage.put_bytes("projects/prj_1/documents/site-plan.txt", b"site plan")

    assert stored.object_key == "s3://uploads/projects/prj_1/documents/site-plan.txt"
    assert storage.exists(stored.object_key)
    assert storage.get_bytes(stored.object_key) == b"site plan"
    assert storage.check_ready() == {"status": "ok", "detail": "s3://uploads"}
    assert not any(object_name.startswith(".readiness/") for _bucket, object_name in client.objects)


def test_s3_object_storage_content_sha256_hashes_raw_bytes():
    content = b"\xff\x00binary\x80"
    settings = Settings(
        s3_endpoint_url="http://minio:9000",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="secret",
        s3_bucket_uploads="uploads",
    )
    storage = S3ObjectStorage(settings, client=FakeMinio(existing_buckets={"uploads"}))

    stored = storage.put_bytes("projects/prj_1/documents/binary.bin", content)

    assert stored.content_sha256 == sha256(content).hexdigest()


def test_s3_object_storage_rejects_path_traversal_keys():
    settings = Settings(
        s3_endpoint_url="http://minio:9000",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="secret",
        s3_bucket_uploads="uploads",
    )
    storage = S3ObjectStorage(settings, client=FakeMinio(existing_buckets={"uploads"}))

    with pytest.raises(ValueError, match="Invalid object key"):
        storage.put_bytes("../outside.txt", b"nope")


def test_named_s3_storage_factories_route_to_configured_buckets():
    settings = Settings(
        s3_endpoint_url="http://minio:9000",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="secret",
        s3_bucket_raw_sources="raw",
        s3_bucket_parsed_sources="parsed",
        s3_bucket_uploads="uploads",
        s3_bucket_exports="exports",
    )
    client = FakeMinio(existing_buckets={"raw", "parsed", "uploads", "exports"})

    assert get_upload_storage(settings, client=client).put_bytes("file.txt", b"1").object_key == (
        "s3://uploads/file.txt"
    )
    assert get_export_storage(settings, client=client).put_bytes("file.txt", b"2").object_key == (
        "s3://exports/file.txt"
    )
    assert get_raw_source_storage(settings, client=client).put_bytes("file.txt", b"3").object_key == (
        "s3://raw/file.txt"
    )
    assert get_parsed_source_storage(settings, client=client).put_bytes("file.txt", b"4").object_key == (
        "s3://parsed/file.txt"
    )


def test_s3_object_storage_readiness_reports_missing_bucket():
    settings = Settings(
        s3_endpoint_url="http://minio:9000",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="secret",
        s3_bucket_uploads="uploads",
    )
    storage = S3ObjectStorage(settings, client=FakeMinio(existing_buckets=set()))

    assert storage.check_ready() == {"status": "error", "detail": "S3 bucket does not exist: uploads"}


def test_s3_aggregate_readiness_requires_all_configured_buckets():
    settings = Settings(
        s3_endpoint_url="http://minio:9000",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="secret",
        s3_bucket_raw_sources="raw-sources",
        s3_bucket_parsed_sources="parsed-sources",
        s3_bucket_uploads="uploads",
        s3_bucket_exports="exports",
    )
    client = FakeMinio(existing_buckets={"raw-sources", "parsed-sources", "uploads", "exports"})

    assert check_s3_object_storage_ready(settings, client=client) == {
        "status": "ok",
        "detail": "s3 buckets ready: raw-sources, parsed-sources, uploads, exports",
    }
    assert not any(object_name.startswith(".readiness/") for _bucket, object_name in client.objects)


def test_s3_aggregate_readiness_reports_missing_non_upload_bucket():
    settings = Settings(
        s3_endpoint_url="http://minio:9000",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="secret",
        s3_bucket_raw_sources="raw-sources",
        s3_bucket_parsed_sources="parsed-sources",
        s3_bucket_uploads="uploads",
        s3_bucket_exports="exports",
    )
    client = FakeMinio(existing_buckets={"raw-sources", "parsed-sources", "uploads"})

    assert check_s3_object_storage_ready(settings, client=client) == {
        "status": "error",
        "detail": "S3 bucket does not exist: exports",
    }


def test_path_based_s3_endpoint_uses_boto3_adapter(monkeypatch):
    fake_boto3 = FakeBoto3Module(existing_buckets={"uploads"})
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    settings = Settings(
        s3_endpoint_url="https://project-ref.storage.supabase.co/storage/v1/s3",
        s3_region="ap-northeast-2",
        s3_access_key_id="access-key",
        s3_secret_access_key="secret-key",
        s3_session_token="session-token",
        s3_bucket_uploads="uploads",
    )

    storage = S3ObjectStorage(settings)
    stored = storage.put_bytes("projects/prj_1/documents/site-plan.txt", b"site plan")

    assert fake_boto3.calls == [
        {
            "service_name": "s3",
            "endpoint_url": "https://project-ref.storage.supabase.co/storage/v1/s3",
            "aws_access_key_id": "access-key",
            "aws_secret_access_key": "secret-key",
            "aws_session_token": "session-token",
            "region_name": "ap-northeast-2",
            "config": {"s3": {"addressing_style": "path"}},
        }
    ]
    assert stored.object_key == "s3://uploads/projects/prj_1/documents/site-plan.txt"
    assert storage.exists(stored.object_key)
    assert storage.get_bytes(stored.object_key) == b"site plan"
    assert storage.check_ready() == {"status": "ok", "detail": "s3://uploads"}


def test_required_durable_object_storage_without_s3_returns_readiness_error(tmp_path):
    settings = Settings(
        object_storage_root=str(tmp_path),
        require_durable_object_storage=True,
        s3_endpoint_url="",
    )

    assert check_object_storage_ready(settings=settings) == {
        "status": "error",
        "detail": (
            "REQUIRE_DURABLE_OBJECT_STORAGE=true but S3_ENDPOINT_URL is not configured; "
            "configure S3/MinIO object storage for uploads and exports."
        ),
    }
    assert not (tmp_path / ".readiness").exists()


def test_required_durable_object_storage_with_incomplete_s3_credentials_reports_error():
    settings = Settings(
        require_durable_object_storage=True,
        s3_endpoint_url="https://minio.example.test",
        s3_access_key_id="draftcheck",
        s3_secret_access_key="",
    )

    assert check_object_storage_ready(settings=settings) == {
        "status": "error",
        "detail": (
            "REQUIRE_DURABLE_OBJECT_STORAGE=true but S3 access credentials are incomplete; "
            "configure S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY."
        ),
    }


class FakeMinio:
    def __init__(self, *, existing_buckets: set[str]):
        self.existing_buckets = existing_buckets
        self.objects: dict[tuple[str, str], bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.existing_buckets

    def put_object(self, bucket: str, object_name: str, data, length: int):
        if bucket not in self.existing_buckets:
            raise RuntimeError(f"bucket does not exist: {bucket}")
        self.objects[(bucket, object_name)] = data.read(length)

    def get_object(self, bucket: str, object_name: str):
        key = (bucket, object_name)
        if key not in self.objects:
            raise RuntimeError(f"object does not exist: {bucket}/{object_name}")
        return FakeS3Response(self.objects[key])

    def stat_object(self, bucket: str, object_name: str):
        key = (bucket, object_name)
        if key not in self.objects:
            raise RuntimeError(f"object does not exist: {bucket}/{object_name}")
        return {"bucket": bucket, "object_name": object_name}

    def remove_object(self, bucket: str, object_name: str):
        self.objects.pop((bucket, object_name), None)


class FakeS3Response:
    def __init__(self, content: bytes):
        self.content = content
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self.content

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class FakeBoto3Module:
    def __init__(self, *, existing_buckets: set[str]):
        self.client_instance = FakeBoto3S3Client(existing_buckets=existing_buckets)
        self.calls: list[dict[str, str]] = []

    def client(
        self,
        service_name: str,
        *,
        endpoint_url: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_session_token: str | None,
        region_name: str,
        config,
    ):
        config_kwargs = getattr(config, "_user_provided_options", {})
        self.calls.append(
            {
                "service_name": service_name,
                "endpoint_url": endpoint_url,
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
                "aws_session_token": aws_session_token,
                "region_name": region_name,
                "config": config_kwargs,
            }
        )
        return self.client_instance


class FakeBoto3S3Client:
    def __init__(self, *, existing_buckets: set[str]):
        self.existing_buckets = existing_buckets
        self.objects: dict[tuple[str, str], bytes] = {}

    def head_bucket(self, *, Bucket: str):
        if Bucket not in self.existing_buckets:
            raise RuntimeError(f"bucket does not exist: {Bucket}")
        return {"Bucket": Bucket}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes):
        if Bucket not in self.existing_buckets:
            raise RuntimeError(f"bucket does not exist: {Bucket}")
        self.objects[(Bucket, Key)] = Body

    def get_object(self, *, Bucket: str, Key: str):
        if (Bucket, Key) not in self.objects:
            raise RuntimeError(f"object does not exist: {Bucket}/{Key}")
        return {"Body": BytesIO(self.objects[(Bucket, Key)])}

    def head_object(self, *, Bucket: str, Key: str):
        if (Bucket, Key) not in self.objects:
            raise RuntimeError(f"object does not exist: {Bucket}/{Key}")
        return {"Bucket": Bucket, "Key": Key}

    def delete_object(self, *, Bucket: str, Key: str):
        self.objects.pop((Bucket, Key), None)
