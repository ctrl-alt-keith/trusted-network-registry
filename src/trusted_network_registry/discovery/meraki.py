"""Bounded Meraki discovery scaffolding.

The MVP intentionally avoids live Dashboard API calls. It accepts sanitized
uplink-address fixtures shaped like the public API response and emits generic,
operator-controlled source references.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from ..registry import canonical_cidr, format_timestamp

ALLOWED_SOURCE_REFS = {"wan1", "wan2", "cellular"}


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


def render_meraki_uplink_entries(
    payload: list[dict[str, Any]],
    *,
    observed_at: datetime,
    valid_until: datetime,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for device in payload:
        for uplink in device.get("uplinks", []):
            raw_ref = uplink.get("interface", "")
            source_ref = _safe_source_ref(raw_ref)
            address = uplink.get("publicIp")
            if not address:
                continue
            cidr, family = canonical_cidr(f"{address}/32")
            entries.append(
                {
                    "id": f"meraki-{source_ref}-{family}",
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


def _safe_source_ref(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_SOURCE_REFS:
        raise ValueError("Meraki source_ref must be an allowed generic uplink name")
    return normalized
