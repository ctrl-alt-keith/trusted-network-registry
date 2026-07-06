from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from trusted_network_registry.cli import main


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


class CliResult:
    def __init__(self, exit_code: int, stdout: str, stderr: str) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


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
