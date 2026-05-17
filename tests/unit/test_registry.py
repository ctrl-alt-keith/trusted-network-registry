from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from trusted_network_registry.config import StaticEntryConfig
from trusted_network_registry.discovery.static import render_static_entries
from trusted_network_registry.publish import publish_once, render_tfvars
from trusted_network_registry.schema import SchemaError, validate_registry_document


ROOT = Path(__file__).resolve().parents[2]


class RegistryTests(unittest.TestCase):
    def test_static_cidr_is_canonicalized(self) -> None:
        entries = render_static_entries(
            [
                StaticEntryConfig(
                    id="admin-static-example",
                    cidr="198.51.100.42/24",
                    source_ref="static-admin",
                )
            ]
        )

        self.assertEqual(entries[0]["cidr"], "198.51.100.0/24")
        self.assertEqual(entries[0]["address_family"], "ipv4")

    def test_example_registry_validates(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        validate_registry_document(document)

    def test_noncanonical_registry_fails(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        document["entries"][0]["cidr"] = "198.51.100.42/24"

        with self.assertRaises(SchemaError):
            validate_registry_document(document)

    def test_publish_once_renders_registry_and_tfvars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "registry.json"
            tfvars = Path(tmp) / "trusted-registry.auto.tfvars.json"
            registry = publish_once(
                config_path=ROOT / "examples/publisher-config.example.toml",
                output_path=output,
                tfvars_output_path=tfvars,
                generated_at_text="2026-05-17T00:00:00Z",
            )

            validate_registry_document(registry)
            self.assertTrue(output.exists())
            self.assertTrue(tfvars.exists())
            rendered_tfvars = json.loads(tfvars.read_text())
            self.assertEqual(
                rendered_tfvars["trusted_registry_valid_until"],
                "2026-05-17T01:00:00Z",
            )

    def test_render_tfvars_extracts_active_cidrs(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())
        tfvars = render_tfvars(registry)

        self.assertEqual(
            tfvars["trusted_admin_cidrs"],
            ["198.51.100.0/24", "203.0.113.10/32"],
        )


if __name__ == "__main__":
    unittest.main()
