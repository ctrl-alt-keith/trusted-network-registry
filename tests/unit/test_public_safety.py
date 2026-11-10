import json
from pathlib import Path
import unittest

from trusted_network_registry.redaction import (
    PublicSafetyError,
    assert_public_safe_document,
    assert_public_safe_text,
)


ROOT = Path(__file__).resolve().parents[2]


class PublicSafetyTests(unittest.TestCase):
    def test_checked_examples_are_public_safe(self) -> None:
        for path in [
            ROOT / "examples/registry.example.json",
            ROOT / "tests/fixtures/sanitized/registry.v1.example.json",
            ROOT / "tests/fixtures/sanitized/meraki-uplinks.example.json",
        ]:
            assert_public_safe_document(json.loads(path.read_text()))

    def test_rejects_provider_identifiers(self) -> None:
        with self.assertRaises(PublicSafetyError):
            assert_public_safe_document(
                {
                    "organizationId": "example-organization",
                    "networkId": "example-network",
                    "serial": "example-serial",
                }
            )

    def test_rejects_non_documentation_ipv4_in_examples(self) -> None:
        for cidr in ("192.168.1.5/32", "8.8.8.8/32", "198.51.100.42/16"):
            with self.subTest(cidr=cidr):
                with self.assertRaisesRegex(PublicSafetyError, "IPv4 outside documentation ranges"):
                    assert_public_safe_document({"cidr": cidr})
                with self.assertRaisesRegex(PublicSafetyError, "IPv4 outside documentation ranges"):
                    assert_public_safe_text(f'cidr = "{cidr}"')

        assert_public_safe_document({"cidr": "198.51.100.42/32"})
        assert_public_safe_text('cidr = "203.0.113.0/24"')

    def test_operator_example_text_files_are_public_safe(self) -> None:
        for path in [
            ROOT / "examples/publisher-config.example.toml",
            ROOT / "deploy/synology/config.example.toml",
            ROOT / "deploy/synology/docker-compose.example.yml",
            ROOT / "deploy/synology/publisher.env.example",
        ]:
            with self.subTest(path=path.name):
                assert_public_safe_text(path.read_text(encoding="utf-8"), label=str(path))

    def test_text_check_rejects_provider_identifiers_and_private_urls(self) -> None:
        with self.assertRaises(PublicSafetyError):
            assert_public_safe_text(
                'organization_id = "example-organization"\n'
                'endpoint_url = "https://private.example.invalid"\n',
                label="operator config",
            )

if __name__ == "__main__":
    unittest.main()
