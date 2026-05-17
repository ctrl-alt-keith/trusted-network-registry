import json
from pathlib import Path
import unittest

from trusted_network_registry.redaction import (
    PublicSafetyError,
    assert_public_safe_document,
    redact_sensitive_fields,
)


ROOT = Path(__file__).resolve().parents[2]


class PublicSafetyTests(unittest.TestCase):
    def test_checked_examples_are_public_safe(self) -> None:
        for path in [
            ROOT / "examples/registry.example.json",
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

    def test_redacts_sensitive_fields(self) -> None:
        redacted = redact_sensitive_fields(
            {
                "organizationId": "example-organization",
                "nested": {"networkId": "example-network"},
            }
        )

        self.assertEqual(redacted["organizationId"], "[redacted]")
        self.assertEqual(redacted["nested"]["networkId"], "[redacted]")


if __name__ == "__main__":
    unittest.main()
