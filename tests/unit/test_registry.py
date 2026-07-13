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

    def test_static_ipv6_cidr_is_canonicalized(self) -> None:
        entries = render_static_entries(
            [
                StaticEntryConfig(
                    id="admin-static-ipv6-example",
                    cidr="2001:db8:100::42/64",
                    source_ref="static-admin-ipv6",
                )
            ]
        )

        self.assertEqual(entries[0]["cidr"], "2001:db8:100::/64")
        self.assertEqual(entries[0]["address_family"], "ipv6")

    def test_example_registry_validates(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        validate_registry_document(document)

    def test_registry_validation_accepts_ipv6_entries(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        ipv6_entries = [
            entry for entry in document["entries"] if entry["address_family"] == "ipv6"
        ]

        self.assertEqual(len(ipv6_entries), 2)
        validate_registry_document(document)

    def test_noncanonical_registry_fails(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        document["entries"][0]["cidr"] = "198.51.100.42/24"

        with self.assertRaises(SchemaError):
            validate_registry_document(document)

    def test_static_registry_entries_reject_universal_cidrs(self) -> None:
        for cidr in ("0.0.0.0/0", "::/0"):
            with self.subTest(cidr=cidr):
                document = json.loads((ROOT / "examples/registry.example.json").read_text())
                document["entries"][0]["cidr"] = cidr
                document["entries"][0]["address_family"] = (
                    "ipv4" if cidr == "0.0.0.0/0" else "ipv6"
                )

                with self.assertRaises(SchemaError) as raised:
                    validate_registry_document(document)

                self.assertIn("universal allow CIDR", str(raised.exception))

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

    def test_publish_once_rejects_output_path_that_matches_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "publisher-config.toml"
            config_text = _publisher_config_text(local_path="publisher-config.toml")
            config_path.write_text(config_text, encoding="utf-8")

            with self.assertRaises(ValueError) as raised:
                publish_once(
                    config_path=config_path,
                    generated_at_text="2026-05-17T00:00:00Z",
                )

            self.assertIn(
                "publisher config and registry output",
                str(raised.exception),
            )
            self.assertEqual(config_path.read_text(encoding="utf-8"), config_text)

    def test_publish_once_rejects_tfvars_path_that_matches_registry_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "publisher-config.toml"
            config_path.write_text(
                _publisher_config_text(
                    local_path="generated/registry.json",
                    tfvars_path="generated/registry.json",
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as raised:
                publish_once(
                    config_path=config_path,
                    generated_at_text="2026-05-17T00:00:00Z",
                )

            self.assertIn(
                "registry output and tfvars output",
                str(raised.exception),
            )
            self.assertFalse((Path(tmp) / "generated" / "registry.json").exists())

    def test_render_tfvars_extracts_active_cidrs(self) -> None:
        registry = json.loads((ROOT / "examples/registry.example.json").read_text())
        tfvars = render_tfvars(registry)

        self.assertEqual(
            tfvars["trusted_admin_cidrs"],
            [
                "198.51.100.0/24",
                "2001:db8:100::/64",
                "203.0.113.10/32",
                "2001:db8::10/128",
            ],
        )


def _publisher_config_text(*, local_path: str, tfvars_path: str | None = None) -> str:
    tfvars = f'tfvars_path = "{tfvars_path}"\n' if tfvars_path else ""
    return f"""
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
target = "local_file"
local_path = "{local_path}"
{tfvars}""".lstrip()


if __name__ == "__main__":
    unittest.main()
