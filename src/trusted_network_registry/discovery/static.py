"""Static CIDR entry rendering."""

from __future__ import annotations

from typing import Any

from ..config import StaticEntryConfig
from ..registry import canonical_cidr


def render_static_entries(config_entries: list[StaticEntryConfig]) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    for entry in config_entries:
        cidr, family = canonical_cidr(entry.cidr)
        rendered.append(
            {
                "id": entry.id,
                "cidr": cidr,
                "address_family": family,
                "kind": "static",
                "source_type": "config",
                "source_ref": entry.source_ref,
                "status": entry.status,
            }
        )
    return rendered
