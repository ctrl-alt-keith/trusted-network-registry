"""S3-compatible Object Storage upload support."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping, Protocol

from .config import PublishConfig


ACCESS_KEY_ENV = "LINODE_OBJ_ACCESS_KEY"
SECRET_KEY_ENV = "LINODE_OBJ_SECRET_KEY"


class ObjectStorageError(RuntimeError):
    """Raised when an Object Storage upload cannot be completed."""


class ObjectStorageCredentialsError(ObjectStorageError):
    """Raised when required Object Storage credentials are missing."""


class ObjectStorageUploadError(ObjectStorageError):
    """Raised when the S3-compatible client rejects the upload."""


class S3Client(Protocol):
    def put_object(self, **kwargs: Any) -> Any:
        """Upload one object."""


ClientFactory = Callable[
    [str, str, str, str],
    S3Client,
]


@dataclass(frozen=True)
class ObjectStorageUploadResult:
    key: str
    size_bytes: int


def upload_registry_payload(
    *,
    registry: dict[str, Any],
    publish: PublishConfig,
    environ: Mapping[str, str],
    client_factory: ClientFactory | None = None,
) -> ObjectStorageUploadResult:
    """Upload a registry payload to S3-compatible Object Storage."""

    bucket = _required_config_value(publish.bucket, "publish.bucket")
    endpoint_url = _required_config_value(publish.endpoint_url, "publish.endpoint_url")
    region = _required_config_value(publish.region, "publish.region")
    object_key = _required_config_value(publish.object_key, "publish.object_key")

    access_key = _required_env_value(environ, ACCESS_KEY_ENV)
    secret_key = _required_env_value(environ, SECRET_KEY_ENV)
    body = json.dumps(registry, indent=2, sort_keys=True).encode("utf-8") + b"\n"

    factory = client_factory or create_s3_client
    try:
        client = factory(access_key, secret_key, endpoint_url, region)
        client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=body,
            ContentType="application/json",
            ACL="private",
        )
    except ObjectStorageError:
        raise
    except Exception as exc:  # pragma: no cover - exact SDK exceptions vary.
        raise ObjectStorageUploadError("object storage upload failed") from exc

    return ObjectStorageUploadResult(key=object_key, size_bytes=len(body))


def create_s3_client(
    access_key_id: str,
    secret_access_key: str,
    endpoint_url: str,
    region: str,
) -> S3Client:
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:  # pragma: no cover - exercised only without deps.
        raise ObjectStorageError(
            "object storage upload requires the boto3 package"
        ) from exc

    return boto3.client(
        "s3",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        endpoint_url=endpoint_url,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def _required_env_value(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name)
    if not value:
        raise ObjectStorageCredentialsError(f"missing required env var: {name}")
    return value


def _required_config_value(value: str | None, name: str) -> str:
    if not value:
        raise ObjectStorageError(f"{name} is required for object_storage publishing")
    return value
