from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from uuid import uuid4

from draftcheck_core.config import Settings, get_settings
from draftcheck_core.json_utils import hash_bytes


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    content_sha256: str
    byte_size: int


class ObjectStorage(Protocol):
    def put_bytes(self, key: str, content: bytes) -> StoredObject:
        ...

    def get_bytes(self, key: str) -> bytes:
        ...

    def exists(self, key: str) -> bool:
        ...


class LocalObjectStorage:
    """Small S3/MinIO-shaped local storage adapter for tests and dev."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or get_settings().object_storage_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, content: bytes) -> StoredObject:
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredObject(
            object_key=str(path),
            content_sha256=hash_bytes(content),
            byte_size=len(content),
        )

    def get_bytes(self, key: str) -> bytes:
        return self._path_for_key(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path_for_key(key).exists()

    def _path_for_key(self, key: str) -> Path:
        path = Path(key)
        if not path.is_absolute():
            path = self.root / _clean_object_name(key)
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"Invalid object key: {key}") from exc
        return resolved_path


class S3ObjectStorage:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        bucket: str | None = None,
        client=None,
    ):
        self.settings = settings or get_settings()
        self.bucket = bucket or self.settings.s3_bucket_uploads
        self.client = client or _create_s3_client(self.settings)

    def put_bytes(self, key: str, content: bytes) -> StoredObject:
        object_name = _clean_object_name(key)
        self.client.put_object(self.bucket, object_name, BytesIO(content), len(content))
        return StoredObject(
            object_key=_s3_uri(self.bucket, object_name),
            content_sha256=hash_bytes(content),
            byte_size=len(content),
        )

    def get_bytes(self, key: str) -> bytes:
        bucket, object_name = _parse_s3_uri(key)
        response = self.client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            close = getattr(response, "close", None)
            if close:
                close()
            release = getattr(response, "release_conn", None)
            if release:
                release()

    def exists(self, key: str) -> bool:
        bucket, object_name = _parse_s3_uri(key)
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except Exception:
            return False

    def check_ready(self) -> dict[str, str]:
        sentinel = f".readiness/probe-{uuid4().hex}.txt"
        try:
            if not self.client.bucket_exists(self.bucket):
                return {"status": "error", "detail": f"S3 bucket does not exist: {self.bucket}"}
            self.client.put_object(
                self.bucket,
                sentinel,
                BytesIO(b"draftcheck-readiness"),
                len(b"draftcheck-readiness"),
            )
            response = self.client.get_object(self.bucket, sentinel)
            try:
                if response.read() != b"draftcheck-readiness":
                    return {"status": "error", "detail": "object storage probe read mismatch"}
            finally:
                close = getattr(response, "close", None)
                if close:
                    close()
                release = getattr(response, "release_conn", None)
                if release:
                    release()
            return {"status": "ok", "detail": f"s3://{self.bucket}"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}
        finally:
            try:
                self.client.remove_object(self.bucket, sentinel)
            except Exception:
                pass


def get_object_storage(
    settings: Settings | None = None,
    *,
    bucket: str | None = None,
    client=None,
) -> ObjectStorage:
    resolved = settings or get_settings()
    if resolved.s3_endpoint_url:
        return S3ObjectStorage(resolved, bucket=bucket, client=client)
    return LocalObjectStorage(resolved.object_storage_root)


def get_upload_storage(settings: Settings | None = None, *, client=None) -> ObjectStorage:
    resolved = settings or get_settings()
    return get_object_storage(resolved, bucket=resolved.s3_bucket_uploads, client=client)


def get_export_storage(settings: Settings | None = None, *, client=None) -> ObjectStorage:
    resolved = settings or get_settings()
    return get_object_storage(resolved, bucket=resolved.s3_bucket_exports, client=client)


def get_raw_source_storage(settings: Settings | None = None, *, client=None) -> ObjectStorage:
    resolved = settings or get_settings()
    return get_object_storage(resolved, bucket=resolved.s3_bucket_raw_sources, client=client)


def get_parsed_source_storage(settings: Settings | None = None, *, client=None) -> ObjectStorage:
    resolved = settings or get_settings()
    return get_object_storage(resolved, bucket=resolved.s3_bucket_parsed_sources, client=client)


def check_object_storage_ready(
    root: str | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, str]:
    if root is None:
        resolved = settings or get_settings()
        persistence_ready = check_object_storage_persistence_ready(resolved)
        if persistence_ready["status"] == "error":
            return persistence_ready
        if resolved.s3_endpoint_url:
            return check_s3_object_storage_ready(resolved)
        root = resolved.object_storage_root
    resolved_root = Path(root or get_settings().object_storage_root)
    sentinel = resolved_root / ".readiness" / f"probe-{uuid4().hex}.txt"
    try:
        resolved_root.mkdir(parents=True, exist_ok=True)
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_bytes(b"draftcheck-readiness")
        if sentinel.read_bytes() != b"draftcheck-readiness":
            return {"status": "error", "detail": "object storage probe read mismatch"}
        return {"status": "ok", "detail": str(resolved_root)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    finally:
        try:
            sentinel.unlink(missing_ok=True)
        except Exception:
            pass


def check_object_storage_persistence_ready(settings: Settings | None = None) -> dict[str, str]:
    resolved = settings or get_settings()
    if not resolved.require_durable_object_storage:
        return {"status": "disabled", "detail": "REQUIRE_DURABLE_OBJECT_STORAGE=false"}
    if not resolved.s3_endpoint_url:
        return {
            "status": "error",
            "detail": (
                "REQUIRE_DURABLE_OBJECT_STORAGE=true but S3_ENDPOINT_URL is not configured; "
                "configure S3/MinIO object storage for uploads and exports."
            ),
        }
    if not resolved.s3_access_key_id or not resolved.s3_secret_access_key:
        return {
            "status": "error",
            "detail": (
                "REQUIRE_DURABLE_OBJECT_STORAGE=true but S3 access credentials are incomplete; "
                "configure S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY."
            ),
        }
    return {"status": "ok", "detail": "durable object storage configured"}


def check_s3_object_storage_ready(settings: Settings | None = None, *, client=None) -> dict[str, str]:
    resolved = settings or get_settings()
    buckets = _configured_s3_buckets(resolved)
    if not buckets:
        return {"status": "error", "detail": "No S3 buckets are configured."}

    try:
        resolved_client = client or _create_s3_client(resolved)
        for bucket in buckets:
            ready = S3ObjectStorage(resolved, bucket=bucket, client=resolved_client).check_ready()
            if ready["status"] != "ok":
                return ready
        return {"status": "ok", "detail": "s3 buckets ready: " + ", ".join(buckets)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _configured_s3_buckets(settings: Settings) -> tuple[str, ...]:
    buckets = (
        settings.s3_bucket_raw_sources,
        settings.s3_bucket_parsed_sources,
        settings.s3_bucket_uploads,
        settings.s3_bucket_exports,
    )
    return tuple(dict.fromkeys(bucket for bucket in buckets if bucket))


class _Boto3S3ClientAdapter:
    def __init__(self, client):
        self.client = client

    def bucket_exists(self, bucket: str) -> bool:
        try:
            self.client.head_bucket(Bucket=bucket)
            return True
        except Exception:
            return False

    def put_object(self, bucket: str, object_name: str, data, length: int):
        self.client.put_object(Bucket=bucket, Key=object_name, Body=data.read(length))

    def get_object(self, bucket: str, object_name: str):
        response = self.client.get_object(Bucket=bucket, Key=object_name)
        return _Boto3S3Response(response["Body"])

    def stat_object(self, bucket: str, object_name: str):
        return self.client.head_object(Bucket=bucket, Key=object_name)

    def remove_object(self, bucket: str, object_name: str):
        self.client.delete_object(Bucket=bucket, Key=object_name)


class _Boto3S3Response:
    def __init__(self, body):
        self.body = body

    def read(self) -> bytes:
        return self.body.read()

    def close(self) -> None:
        close = getattr(self.body, "close", None)
        if close:
            close()


def _create_s3_client(settings: Settings):
    if not settings.s3_access_key_id or not settings.s3_secret_access_key:
        raise ValueError("S3 access key and secret key must be configured when S3_ENDPOINT_URL is set")
    endpoint = settings.s3_endpoint_url
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    path = parsed.path.rstrip("/")
    if path:
        return _create_boto3_s3_client(settings, parsed)
    return _create_minio_client(settings, parsed)


def _create_boto3_s3_client(settings: Settings, parsed):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError(
            "boto3 package is required when S3_ENDPOINT_URL includes a path, such as "
            "Supabase Storage S3 endpoints."
        ) from exc

    endpoint_url = parsed.geturl()
    return _Boto3S3ClientAdapter(
        boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            aws_session_token=settings.s3_session_token or None,
            region_name=settings.s3_region,
            config=Config(s3={"addressing_style": "path"}),
        )
    )


def _create_minio_client(settings: Settings, parsed):
    try:
        from minio import Minio
    except ImportError as exc:
        raise RuntimeError("minio package is required when S3_ENDPOINT_URL is set") from exc

    netloc = parsed.netloc or parsed.path
    if not netloc:
        raise ValueError("S3_ENDPOINT_URL must include a host")
    return Minio(
        netloc,
        access_key=settings.s3_access_key_id,
        secret_key=settings.s3_secret_access_key,
        session_token=settings.s3_session_token or None,
        secure=parsed.scheme == "https",
        region=settings.s3_region,
    )


def _clean_object_name(key: str) -> str:
    parts = [part for part in key.replace("\\", "/").lstrip("/").split("/") if part and part != "."]
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"Invalid object key: {key}")
    return "/".join(parts)


def _s3_uri(bucket: str, object_name: str) -> str:
    return f"s3://{bucket}/{object_name}"


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError(f"Invalid S3 object key: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")
