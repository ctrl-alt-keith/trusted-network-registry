from datetime import datetime, timezone
from pathlib import Path
import unittest

from trusted_network_registry.discovery.meraki import (
    render_meraki_entries_from_fixture,
    render_meraki_uplink_entries,
)


ROOT = Path(__file__).resolve().parents[2]


class MerakiTests(unittest.TestCase):
    def test_sanitized_fixture_renders_ipv4_and_ipv6_entries(self) -> None:
        entries = render_meraki_entries_from_fixture(
            ROOT / "tests/fixtures/sanitized/meraki-uplinks.example.json",
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        by_id = {entry["id"]: entry for entry in entries}
        self.assertEqual(by_id["meraki-wan1-ipv4"]["source_ref"], "wan1")
        self.assertEqual(by_id["meraki-wan1-ipv4"]["cidr"], "203.0.113.10/32")
        self.assertEqual(by_id["meraki-wan1-ipv4"]["address_family"], "ipv4")
        self.assertEqual(by_id["meraki-wan2-ipv6"]["source_ref"], "wan2")
        self.assertEqual(by_id["meraki-wan2-ipv6"]["cidr"], "2001:db8::10/128")
        self.assertEqual(by_id["meraki-wan2-ipv6"]["address_family"], "ipv6")

    def test_ipv4_host_addresses_render_as_32(self) -> None:
        entries = render_meraki_uplink_entries(
            [{"uplinks": [{"interface": "wan1", "publicIp": "203.0.113.10"}]}],
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(entries[0]["cidr"], "203.0.113.10/32")

    def test_ipv6_host_addresses_render_as_128(self) -> None:
        entries = render_meraki_uplink_entries(
            [{"uplinks": [{"interface": "wan2", "publicIp": "2001:db8::10"}]}],
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(entries[0]["cidr"], "2001:db8::10/128")

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
