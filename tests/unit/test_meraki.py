from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from trusted_network_registry.discovery.meraki import (
    API_KEY_ENV,
    DASHBOARD_API_BASE_URL,
    MerakiDiscoveryError,
    fetch_meraki_uplinks_by_device,
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
            [
                {
                    "uplinks": [
                        {
                            "interface": "wan1",
                            "addresses": [
                                {"public": {"address": "203.0.113.10"}},
                            ],
                        }
                    ]
                }
            ],
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(entries[0]["cidr"], "203.0.113.10/32")

    def test_ipv6_host_addresses_render_as_128(self) -> None:
        entries = render_meraki_uplink_entries(
            [
                {
                    "uplinks": [
                        {
                            "interface": "wan2",
                            "addresses": [
                                {"public": {"address": "2001:db8::10"}},
                            ],
                        }
                    ]
                }
            ],
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(entries[0]["cidr"], "2001:db8::10/128")

    def test_skips_stale_or_missing_uplink_public_addresses(self) -> None:
        entries = render_meraki_uplink_entries(
            [
                {},
                {"uplinks": None},
                {"uplinks": [{"interface": "wan1", "addresses": []}]},
                {
                    "uplinks": [
                        {
                            "interface": "wan2",
                            "addresses": [{"public": {"address": None}}],
                        }
                    ]
                },
            ],
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(entries, [])

    def test_enforces_generic_source_refs_only(self) -> None:
        entries = render_meraki_uplink_entries(
            [
                {
                    "uplinks": [
                        {
                            "interface": "man1",
                            "addresses": [
                                {"public": {"address": "203.0.113.11"}},
                            ],
                        },
                        {
                            "interface": "cellular",
                            "addresses": [
                                {"public": {"address": "203.0.113.12"}},
                            ],
                        },
                    ]
                }
            ],
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual([entry["source_ref"] for entry in entries], ["cellular"])

    def test_output_omits_public_unsafe_provider_metadata(self) -> None:
        entries = render_meraki_uplink_entries(
            [
                {
                    "mac": "[redacted]",
                    "name": "[redacted]",
                    "network": {"id": "[redacted]"},
                    "tags": ["example"],
                    "uplinks": [
                        {
                            "interface": "wan1",
                            "addresses": [
                                {"public": {"address": "203.0.113.10"}},
                            ],
                        }
                    ],
                }
            ],
            observed_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
            valid_until=datetime(2026, 5, 17, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(entries[0]["source_ref"], "wan1")
        self.assertNotIn("network", entries[0])
        self.assertNotIn("name", entries[0])
        self.assertNotIn("mac", entries[0])
        self.assertNotIn("tags", entries[0])

    def test_live_discovery_requires_env_credential(self) -> None:
        import os

        original = os.environ.pop(API_KEY_ENV, None)
        try:
            with self.assertRaises(MerakiDiscoveryError):
                fetch_meraki_uplinks_by_device(organization_id="example-org")
        finally:
            if original is not None:
                os.environ[API_KEY_ENV] = original

    def test_live_discovery_uses_read_only_endpoint_and_follows_next_page(self) -> None:
        first_link = (
            "</api/v1/organizations/example-org/devices/uplinks/addresses/"
            'byDevice?startingAfter=page-1>; rel="next"'
        )
        responses = [
            _FakeResponse([{"uplinks": []}], link=first_link),
            _FakeResponse([{"uplinks": [{"interface": "wan1", "addresses": []}]}]),
        ]
        requests = []

        def fake_urlopen(request, timeout):
            requests.append((request, timeout))
            return responses.pop(0)

        with patch("trusted_network_registry.discovery.meraki.urlopen", fake_urlopen):
            payload = fetch_meraki_uplinks_by_device(
                organization_id="example-org",
                api_key="example-api-key",
            )

        self.assertEqual(len(payload), 2)
        self.assertEqual(len(requests), 2)
        first_request = requests[0][0]
        self.assertEqual(first_request.get_method(), "GET")
        self.assertTrue(
            first_request.full_url.startswith(
                f"{DASHBOARD_API_BASE_URL}/organizations/example-org/"
                "devices/uplinks/addresses/byDevice?perPage=1000"
            )
        )
        self.assertEqual(first_request.get_header("Authorization"), "Bearer example-api-key")

    def test_live_discovery_accepts_same_origin_absolute_next_page(self) -> None:
        first_link = (
            f"<{DASHBOARD_API_BASE_URL}/organizations/example-org/devices/uplinks/"
            'addresses/byDevice?startingAfter=page-1>; rel="next"'
        )
        responses = [
            _FakeResponse([{"uplinks": []}], link=first_link),
            _FakeResponse([{"uplinks": []}]),
        ]
        requests = []

        def fake_urlopen(request, timeout):
            requests.append((request, timeout))
            return responses.pop(0)

        with patch("trusted_network_registry.discovery.meraki.urlopen", fake_urlopen):
            fetch_meraki_uplinks_by_device(
                organization_id="example-org",
                api_key="example-api-key",
            )

        self.assertEqual(len(requests), 2)
        self.assertTrue(requests[1][0].full_url.startswith(DASHBOARD_API_BASE_URL))

    def test_live_discovery_rejects_next_page_on_different_host(self) -> None:
        first_link = (
            '<https://example.invalid/api/v1/organizations/example-org/devices/uplinks/'
            'addresses/byDevice?startingAfter=page-1>; rel="next"'
        )

        with patch(
            "trusted_network_registry.discovery.meraki.urlopen",
            return_value=_FakeResponse([{"uplinks": []}], link=first_link),
        ):
            with self.assertRaises(MerakiDiscoveryError) as raised:
                fetch_meraki_uplinks_by_device(
                    organization_id="example-org",
                    api_key="example-api-key",
                )

        self.assertIn("pagination link", str(raised.exception))

    def test_live_discovery_rejects_next_page_with_non_https_scheme(self) -> None:
        first_link = (
            '<http://api.meraki.com/api/v1/organizations/example-org/devices/uplinks/'
            'addresses/byDevice?startingAfter=page-1>; rel="next"'
        )

        with patch(
            "trusted_network_registry.discovery.meraki.urlopen",
            return_value=_FakeResponse([{"uplinks": []}], link=first_link),
        ):
            with self.assertRaises(MerakiDiscoveryError) as raised:
                fetch_meraki_uplinks_by_device(
                    organization_id="example-org",
                    api_key="example-api-key",
                )

        self.assertIn("pagination link", str(raised.exception))


class _FakeResponse:
    def __init__(self, payload, *, link: str | None = None) -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = {}
        if link is not None:
            self.headers["Link"] = link

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._payload


if __name__ == "__main__":
    unittest.main()
