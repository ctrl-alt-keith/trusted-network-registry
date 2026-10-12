import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from trusted_network_registry.config import PublishConfig
from trusted_network_registry.object_storage import (
    ObjectStorageCredentialsError,
    ObjectStorageError,
    ObjectStorageUploadError,
    ObjectStorageUploadResult,
    upload_registry_payload,
)
from trusted_network_registry.publish import publish_once


ROOT = Path(__file__).resolve().parents[2]


class FakeS3Client:
    def __init__(
        self,
        *,
        fail: bool = False,
        response: dict[str, object] | None = None,
    ) -> None:
        self.fail = fail
        self.response = (
            response if response is not None else {"VersionId": "version-example"}
        )
        self.calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> dict[str, object]:
        if self.fail:
            raise RuntimeError("sdk rejected upload for private object")
        self.calls.append(kwargs)
        return self.response


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
        self.assertEqual(result.size_bytes, len(call["Body"]))
        self.assertEqual(result.sha256, hashlib.sha256(call["Body"]).hexdigest())
        self.assertEqual(result.version_id, "version-example")

    def test_missing_or_null_version_id_is_not_a_versioned_receipt(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())
        publish = PublishConfig(
            target="object_storage",
            bucket="bucket-label-placeholder",
            endpoint_url="https://example.com",
            region="us-example-1",
            object_key="registry/registry.json",
        )
        environ = {
            "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
            "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
        }

        for response in ({}, {"VersionId": None}, {"VersionId": "null"}):
            with self.subTest(response=response):
                client = FakeS3Client(response=response)
                result = upload_registry_payload(
                    registry=registry,
                    publish=publish,
                    environ=environ,
                    client_factory=lambda *_args: client,
                )

                self.assertIsNone(result.version_id)
                self.assertEqual(
                    result.sha256,
                    hashlib.sha256(client.calls[0]["Body"]).hexdigest(),
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

    def test_upload_registry_payload_rejects_whitespace_config_before_client(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())
        base_values = {
            "bucket": "bucket-label-placeholder",
            "endpoint_url": "https://example.com",
            "region": "us-example-1",
            "object_key": "registry/registry.json",
        }

        for name in base_values:
            with self.subTest(name=name):
                values = base_values | {name: " \t "}
                client_factory_calls: list[tuple[object, ...]] = []

                def client_factory(*args: object) -> FakeS3Client:
                    client_factory_calls.append(args)
                    return FakeS3Client()

                with self.assertRaisesRegex(
                    ObjectStorageError,
                    f"publish.{name} is required for object_storage publishing",
                ):
                    upload_registry_payload(
                        registry=registry,
                        publish=PublishConfig(target="object_storage", **values),
                        environ={
                            "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
                            "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
                        },
                        client_factory=client_factory,
                    )

                self.assertEqual(client_factory_calls, [])

    def test_upload_registry_payload_rejects_whitespace_credentials_before_client(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())
        publish = PublishConfig(
            target="object_storage",
            bucket="bucket-label-placeholder",
            endpoint_url="https://example.com",
            region="us-example-1",
            object_key="registry/registry.json",
        )

        for name, environ in (
            (
                "LINODE_OBJ_ACCESS_KEY",
                {
                    "LINODE_OBJ_ACCESS_KEY": " \t ",
                    "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
                },
            ),
            (
                "LINODE_OBJ_SECRET_KEY",
                {
                    "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
                    "LINODE_OBJ_SECRET_KEY": "\n ",
                },
            ),
        ):
            with self.subTest(name=name):
                client_factory_calls: list[tuple[object, ...]] = []

                def client_factory(*args: object) -> FakeS3Client:
                    client_factory_calls.append(args)
                    return FakeS3Client()

                with self.assertRaisesRegex(
                    ObjectStorageCredentialsError,
                    f"missing required env var: {name}",
                ):
                    upload_registry_payload(
                        registry=registry,
                        publish=publish,
                        environ=environ,
                        client_factory=client_factory,
                    )

                self.assertEqual(client_factory_calls, [])

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
        self.assertEqual(message, "object storage upload failed (RuntimeError)")
        self.assertNotIn("bucket-label-placeholder", message)
        self.assertNotIn("placeholder-private-credential", message)
        self.assertNotIn("https://example.com", message)

    def test_upload_registry_payload_reports_safe_sdk_exception_type(self) -> None:
        class EndpointConnectionError(Exception):
            pass

        class FailingClient:
            def put_object(self, **kwargs: object) -> None:
                raise EndpointConnectionError(
                    "Could not connect to endpoint URL: https://private.example"
                )

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
                client_factory=lambda *_args: FailingClient(),
            )

        message = str(raised.exception)
        self.assertEqual(message, "object storage upload failed (EndpointConnectionError)")
        self.assertNotIn("private.example", message)
        self.assertNotIn("bucket-label-placeholder", message)
        self.assertNotIn("placeholder-private-credential", message)

    def test_timeout_after_put_call_has_no_success_receipt(self) -> None:
        class TimeoutAfterSendClient:
            def __init__(self) -> None:
                self.bodies: list[bytes] = []

            def put_object(self, **kwargs: object) -> None:
                body = kwargs["Body"]
                assert isinstance(body, bytes)
                self.bodies.append(body)
                raise TimeoutError("private endpoint and key details")

        client = TimeoutAfterSendClient()
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
                client_factory=lambda *_args: client,
            )

        self.assertEqual(len(client.bodies), 1)
        self.assertEqual(
            str(raised.exception), "object storage upload failed (TimeoutError)"
        )
        self.assertNotIn("private endpoint", str(raised.exception))

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
                    sha256="a" * 64,
                    version_id="version-example",
                )

            captured_uploads: list[ObjectStorageUploadResult] = []

            registry = publish_once(
                config_path=config_path,
                generated_at_text="2026-05-17T00:00:00Z",
                environ={
                    "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
                    "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
                },
                object_storage_uploader=uploader,
                on_upload=captured_uploads.append,
            )

            self.assertTrue(output_path.exists())
            self.assertEqual(json.loads(output_path.read_text()), registry)
            self.assertEqual(len(uploads), 1)
            self.assertEqual(uploads[0][1], "placeholder-access-credential")
            self.assertEqual(captured_uploads[0].version_id, "version-example")


if __name__ == "__main__":
    unittest.main()
