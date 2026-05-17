import json
from pathlib import Path
import tempfile
import unittest

from trusted_network_registry.config import PublishConfig
from trusted_network_registry.object_storage import (
    ObjectStorageCredentialsError,
    ObjectStorageUploadError,
    ObjectStorageUploadResult,
    upload_registry_payload,
)
from trusted_network_registry.publish import publish_once


ROOT = Path(__file__).resolve().parents[2]


class FakeS3Client:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> None:
        if self.fail:
            raise RuntimeError("sdk rejected upload for private object")
        self.calls.append(kwargs)


class ObjectStorageTests(unittest.TestCase):
    def test_upload_registry_payload_uses_private_acl_and_env_credentials(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())
        client = FakeS3Client()
        captured_factory_args: list[tuple[str, str, str, str]] = []

        def factory(
            access_key: str,
            secret_key: str,
            endpoint_url: str,
            region: str,
        ) -> FakeS3Client:
            captured_factory_args.append(
                (access_key, secret_key, endpoint_url, region)
            )
            return client

        result = upload_registry_payload(
            registry=registry,
            publish=PublishConfig(
                target="object_storage",
                bucket="bucket-label-placeholder",
                endpoint_url="https://example.com",
                region="us-example-1",
                object_key="registry/registry.json",
            ),
            environ={
                "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
                "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
            },
            client_factory=factory,
        )

        self.assertEqual(result.key, "registry/registry.json")
        self.assertEqual(
            captured_factory_args,
            [
                (
                    "placeholder-access-credential",
                    "placeholder-private-credential",
                    "https://example.com",
                    "us-example-1",
                )
            ],
        )
        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertEqual(call["Bucket"], "bucket-label-placeholder")
        self.assertEqual(call["Key"], "registry/registry.json")
        self.assertEqual(call["ACL"], "private")
        self.assertEqual(call["ContentType"], "application/json")
        self.assertEqual(
            call["Body"],
            json.dumps(registry, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        )

    def test_upload_registry_payload_requires_env_credentials(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())

        with self.assertRaises(ObjectStorageCredentialsError) as raised:
            upload_registry_payload(
                registry=registry,
                publish=PublishConfig(
                    target="object_storage",
                    bucket="bucket-label-placeholder",
                    endpoint_url="https://example.com",
                    region="us-example-1",
                    object_key="registry/registry.json",
                ),
                environ={},
                client_factory=lambda *_args: FakeS3Client(),
            )

        self.assertIn("LINODE_OBJ_ACCESS_KEY", str(raised.exception))
        self.assertNotIn("placeholder-private-credential", str(raised.exception))

    def test_upload_registry_payload_reports_public_safe_failure(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())

        with self.assertRaises(ObjectStorageUploadError) as raised:
            upload_registry_payload(
                registry=registry,
                publish=PublishConfig(
                    target="object_storage",
                    bucket="bucket-label-placeholder",
                    endpoint_url="https://example.com",
                    region="us-example-1",
                    object_key="registry/registry.json",
                ),
                environ={
                    "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
                    "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
                },
                client_factory=lambda *_args: FakeS3Client(fail=True),
            )

        message = str(raised.exception)
        self.assertEqual(message, "object storage upload failed")
        self.assertNotIn("bucket-label-placeholder", message)
        self.assertNotIn("placeholder-private-credential", message)

    def test_publish_once_renders_locally_then_uploads_object_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "publisher-config.toml"
            output_path = tmp_path / "registry.json"
            config_path.write_text(
                f"""
[registry]
name = "trusted-network-registry"
ttl_seconds = 3600

[[static_entries]]
id = "admin-static-example"
cidr = "198.51.100.42/24"
source_ref = "static-admin"

[meraki]
enabled = false

[publish]
target = "object_storage"
local_path = "{output_path}"
bucket = "bucket-label-placeholder"
endpoint_url = "https://example.com"
region = "us-example-1"
object_key = "registry/registry.json"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            uploads: list[tuple[dict[str, object], str]] = []

            def uploader(registry, config, environ):
                uploads.append((registry, environ["LINODE_OBJ_ACCESS_KEY"]))
                return ObjectStorageUploadResult(
                    key=config.publish.object_key,
                    size_bytes=0,
                )

            registry = publish_once(
                config_path=config_path,
                generated_at_text="2026-05-17T00:00:00Z",
                environ={
                    "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
                    "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
                },
                object_storage_uploader=uploader,
            )

            self.assertTrue(output_path.exists())
            self.assertEqual(json.loads(output_path.read_text()), registry)
            self.assertEqual(len(uploads), 1)
            self.assertEqual(uploads[0][1], "placeholder-access-credential")


if __name__ == "__main__":
    unittest.main()
