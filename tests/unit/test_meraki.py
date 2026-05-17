from datetime import datetime, timezone
from pathlib import Path
import unittest

from trusted_network_registry.discovery.meraki import (
    render_meraki_entries_from_fixture,
    render_meraki_uplink_entries,
)


ROOT = Path(__file__).resolve().parents[2]


class MerakiTests(unittest.TestCase):
    def test_sanitized_fixture_renders_generic_entry(self) -> None:
        entries = render_meraki_entries_from_fixture(
            ROOT / "tests/fixtures/sanitized/meraki-uplinks.example.json",
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(entries[0]["id"], "meraki-wan1-ipv4")
        self.assertEqual(entries[0]["source_ref"], "wan1")
        self.assertEqual(entries[0]["cidr"], "203.0.113.10/32")

    def test_rejects_non_generic_source_ref(self) -> None:
        payload = [{"uplinks": [{"interface": "unsafe-ref", "publicIp": "203.0.113.10"}]}]

        with self.assertRaises(ValueError):
            render_meraki_uplink_entries(
                payload,
                observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
                valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
            )


if __name__ == "__main__":
    unittest.main()
