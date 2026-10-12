from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from trusted_network_registry.cli import main
from trusted_network_registry.object_storage import ObjectStorageUploadError


ROOT = Path(__file__).resolve().parents[2]


class CliTests(unittest.TestCase):
    def test_validate_registry_reports_schema_error_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            invalid_registry = Path(tmp) / "registry.json"
            invalid_registry.write_text('{"schema_version": 2}\n', encoding="utf-8")

            result = _run_cli(["validate-registry", str(invalid_registry)])

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout, "")
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "error")
        self.assertIn("registry document missing required keys", payload["error"])

    def test_validate_config_reports_schema_error_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            invalid_config = Path(tmp) / "publisher-config.toml"
            invalid_config.write_text(
                """
[[static_entries]]
id = "admin-static-example"
cidr = "0.0.0.0/0"
source_ref = "static-admin"

[publish]
local_path = "registry.json"
""".lstrip(),
                encoding="utf-8",
            )

            result = _run_cli(["validate-config", str(invalid_config)])

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout, "")
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "error")
        self.assertIn("universal allow CIDR", payload["error"])

    def test_validate_config_does_not_echo_malformed_cidr(self) -> None:
        private_cidr = "10.23.45.67/not-a-prefix"
        with tempfile.TemporaryDirectory() as tmp:
            invalid_config = Path(tmp) / "publisher-config.toml"
            invalid_config.write_text(
                f'# malformed fixture\n\n[[static_entries]]\n'
                f'id = "admin-static-example"\ncidr = "{private_cidr}"\n'
                'source_ref = "static-admin"\n',
                encoding="utf-8",
            )

            result = _run_cli(["validate-config", str(invalid_config)])

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.stderr)
        self.assertEqual(
            payload["error"],
            "static_entries[0].cidr must be a valid CIDR",
        )
        self.assertNotIn(private_cidr, result.stderr)

    def test_publish_invalid_generated_at_reports_json_error_without_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "registry.json"
            tfvars = Path(tmp) / "trusted-registry.auto.tfvars.json"

            result = _run_cli(
                [
                    "publish",
                    "--once",
                    "--config",
                    str(ROOT / "examples/publisher-config.example.toml"),
                    "--output",
                    str(output),
                    "--tfvars-output",
                    str(tfvars),
                    "--generated-at",
                    "2026-05-17T00:00:00+00:00",
                ]
            )

            self.assertFalse(output.exists())
            self.assertFalse(tfvars.exists())

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout, "")
        payload = json.loads(result.stderr)
        self.assertEqual(payload, {"status": "error", "error": "timestamp must end in Z"})

    def test_publish_requires_once_before_rendering_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "registry.json"

            result = _run_cli(
                [
                    "publish",
                    "--config",
                    str(ROOT / "examples/publisher-config.example.toml"),
                    "--output",
                    str(output),
                ]
            )

            self.assertFalse(output.exists())

        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("publish requires --once", result.stderr)

    def test_local_file_publish_keeps_original_status_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "registry.json"
            result = _run_cli(
                [
                    "publish",
                    "--once",
                    "--config",
                    str(ROOT / "examples/publisher-config.example.toml"),
                    "--output",
                    str(output),
                    "--generated-at",
                    "2026-05-17T00:00:00Z",
                ]
            )

            self.assertTrue(output.is_file())
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {"status": "published", "entries": 4})

    def test_object_storage_publish_reports_only_receipt_metadata(self) -> None:
        class CapturingClient:
            def __init__(self, version_id: str | None) -> None:
                self.version_id = version_id
                self.body: bytes | None = None

            def put_object(self, **kwargs: object) -> dict[str, object]:
                body = kwargs["Body"]
                assert isinstance(body, bytes)
                self.body = body
                return {"VersionId": self.version_id} if self.version_id else {}

        with tempfile.TemporaryDirectory() as tmp:
            config = _object_storage_config(Path(tmp))
            for version_id in ("version-example", None):
                with self.subTest(version_id=version_id):
                    client = CapturingClient(version_id)
                    with (
                        patch(
                            "trusted_network_registry.object_storage.create_s3_client",
                            return_value=client,
                        ) as factory,
                        patch.dict(
                            os.environ,
                            {
                                "LINODE_OBJ_ACCESS_KEY": "placeholder-access-credential",
                                "LINODE_OBJ_SECRET_KEY": "placeholder-private-credential",
                            },
                        ),
                    ):
                        result = _run_cli(
                            ["publish", "--once", "--config", str(config)]
                        )

                    self.assertEqual(result.exit_code, 0)
                    self.assertEqual(result.stderr, "")
                    factory.assert_called_once()
                    self.assertIsNotNone(client.body)
                    self.assertEqual(
                        json.loads(result.stdout),
                        {
                            "status": "published",
                            "entries": 1,
                            "upload_receipt": {
                                "sha256": hashlib.sha256(client.body).hexdigest(),
                                "size_bytes": len(client.body),
                                "version_id": version_id,
                            },
                        },
                    )
                    self.assertNotIn("private-object", result.stdout)
                    self.assertNotIn("bucket-label-placeholder", result.stdout)
                    self.assertNotIn("198.51.100", result.stdout)

    def test_upload_timeout_reports_error_without_success_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _object_storage_config(Path(tmp))
            with patch(
                "trusted_network_registry.publish._upload_to_object_storage",
                side_effect=ObjectStorageUploadError(
                    "object storage upload failed (TimeoutError)"
                ),
            ):
                result = _run_cli(["publish", "--once", "--config", str(config)])

        self.assertEqual(result.exit_code, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            json.loads(result.stderr),
            {
                "status": "error",
                "error": "object storage upload failed (TimeoutError)",
            },
        )


class CliResult:
    def __init__(self, exit_code: int, stdout: str, stderr: str) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


def _object_storage_config(directory: Path) -> Path:
    config = directory / "publisher-config.toml"
    config.write_text(
        """[registry]
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
local_path = "registry.json"
bucket = "bucket-label-placeholder"
endpoint_url = "https://example.com"
region = "us-example-1"
object_key = "registry/private-object.json"
""",
        encoding="utf-8",
    )
    return config


def _run_cli(argv: list[str]) -> CliResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            exit_code = main(argv)
        except SystemExit as exc:
            exit_code = int(exc.code)
    return CliResult(
        exit_code=exit_code,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


if __name__ == "__main__":
    unittest.main()
