"""Bounded read-only Meraki Dashboard API discovery."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from ..registry import format_timestamp

ALLOWED_SOURCE_REFS = {"wan1", "wan2", "cellular"}
API_KEY_ENV = "MERAKI_DASHBOARD_API_KEY"
DASHBOARD_API_BASE_URL = "https://api.meraki.com/api/v1"
UPLINKS_BY_DEVICE_PATH = "/organizations/{organization_id}/devices/uplinks/addresses/byDevice"
PER_PAGE = 1000
MAX_PAGES = 100
TIMEOUT_SECONDS = 30


class MerakiDiscoveryError(RuntimeError):
    """Raised when live Meraki discovery cannot complete safely."""


def render_meraki_entries_from_fixture(
    fixture_path: Path,
    *,
    observed_at: datetime,
    valid_until: datetime,
) -> list[dict[str, Any]]:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return render_meraki_uplink_entries(
        payload,
        observed_at=observed_at,
        valid_until=valid_until,
    )


def discover_meraki_uplink_entries(
    *,
    organization_id: str,
    observed_at: datetime,
    valid_until: datetime,
) -> list[dict[str, Any]]:
    payload = fetch_meraki_uplinks_by_device(organization_id=organization_id)
    return render_meraki_uplink_entries(
        payload,
        observed_at=observed_at,
        valid_until=valid_until,
    )


def fetch_meraki_uplinks_by_device(
    *,
    organization_id: str,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    token = api_key or os.environ.get(API_KEY_ENV)
    if not token:
        raise MerakiDiscoveryError(f"{API_KEY_ENV} is required for live Meraki discovery")

    url = _uplinks_url(organization_id)
    devices: list[dict[str, Any]] = []
    for _ in range(MAX_PAGES):
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                page = json.loads(response.read().decode("utf-8"))
                if not isinstance(page, list):
                    raise MerakiDiscoveryError("Meraki uplink response must be a list")
                devices.extend(page)
                next_url = _next_link(response.headers.get("Link"), current_url=url)
        except HTTPError as exc:
            raise MerakiDiscoveryError(
                f"Meraki Dashboard API request failed with HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise MerakiDiscoveryError("Meraki Dashboard API request failed") from exc
        except json.JSONDecodeError as exc:
            raise MerakiDiscoveryError("Meraki Dashboard API response was not JSON") from exc

        if next_url is None:
            return devices
        url = next_url

    raise MerakiDiscoveryError("Meraki Dashboard API pagination exceeded the page limit")


def render_meraki_uplink_entries(
    payload: list[dict[str, Any]],
    *,
    observed_at: datetime,
    valid_until: datetime,
) -> list[dict[str, Any]]:
    discovered: set[tuple[str, str, str]] = set()
    for device in payload:
        uplinks = device.get("uplinks") or []
        if not isinstance(uplinks, list):
            continue
        for uplink in uplinks:
            if not isinstance(uplink, dict):
                continue
            source_ref = _safe_source_ref(uplink.get("interface", ""))
            if source_ref is None:
                continue
            addresses = uplink.get("addresses") or []
            if not isinstance(addresses, list):
                continue
            for address_record in addresses:
                if not isinstance(address_record, dict):
                    continue
                public = address_record.get("public", {})
                if not isinstance(public, dict):
                    continue
                address = public.get("address")
                if not isinstance(address, str) or not address.strip():
                    continue
                parsed_address = ipaddress.ip_address(address.strip())
                prefix = 32 if parsed_address.version == 4 else 128
                family = "ipv4" if parsed_address.version == 4 else "ipv6"
                cidr = f"{parsed_address}/{prefix}"
                discovered.add((source_ref, family, cidr))

    entries: list[dict[str, Any]] = []
    base_counts = Counter((source_ref, family) for source_ref, family, _cidr in discovered)
    emitted_counts: Counter[tuple[str, str]] = Counter()
    for source_ref, family, cidr in sorted(discovered):
        key = (source_ref, family)
        emitted_counts[key] += 1
        suffix = f"-{emitted_counts[key]}" if base_counts[key] > 1 else ""
        entries.append(
            {
                "id": f"meraki-{source_ref}-{family}{suffix}",
                "cidr": cidr,
                "address_family": family,
                "kind": "discovered",
                "source_type": "meraki_uplink_addresses",
                "source_ref": source_ref,
                "observed_at": format_timestamp(observed_at),
                "expires_at": format_timestamp(valid_until),
                "status": "active",
            }
        )
    return entries


def _uplinks_url(organization_id: str) -> str:
    encoded_org = quote(organization_id, safe="")
    path = UPLINKS_BY_DEVICE_PATH.format(organization_id=encoded_org)
    return f"{DASHBOARD_API_BASE_URL}{path}?perPage={PER_PAGE}"


def _next_link(link_header: str | None, *, current_url: str) -> str | None:
    if not link_header:
        return None
    expected = urlparse(DASHBOARD_API_BASE_URL)
    for part in link_header.split(","):
        pieces = [piece.strip() for piece in part.split(";")]
        if not pieces or not pieces[0].startswith("<") or not pieces[0].endswith(">"):
            continue
        rels = {
            piece.split("=", 1)[1].strip('"')
            for piece in pieces[1:]
            if piece.lower().startswith("rel=")
        }
        if "next" in rels:
            next_url = urljoin(current_url, pieces[0][1:-1])
            parsed = urlparse(next_url)
            if parsed.scheme != "https" or parsed.netloc != expected.netloc:
                raise MerakiDiscoveryError(
                    "Meraki Dashboard API pagination link must stay on the Dashboard API host"
                )
            return next_url
    return None


def _safe_source_ref(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]+", normalized):
        return None
    if normalized not in ALLOWED_SOURCE_REFS:
        return None
    return normalized
