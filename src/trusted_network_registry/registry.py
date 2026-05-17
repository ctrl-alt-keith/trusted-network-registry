"""Registry rendering and CIDR normalization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import ipaddress
from typing import Any

from . import __version__


def canonical_cidr(value: str) -> tuple[str, str]:
    network = ipaddress.ip_network(value, strict=False)
    family = "ipv4" if network.version == 4 else "ipv6"
    return network.with_prefixlen, family


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_timestamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must end in Z")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def render_registry(
    entries: list[dict[str, Any]],
    *,
    name: str = "trusted-network-registry",
    generated_at: datetime | None = None,
    ttl_seconds: int = 3600,
) -> dict[str, Any]:
    generated = generated_at or utc_now()
    valid_until = generated + timedelta(seconds=ttl_seconds)
    normalized = sorted(entries, key=lambda entry: entry["id"])
    static_count = sum(1 for entry in normalized if entry["kind"] == "static")
    discovered_count = sum(1 for entry in normalized if entry["kind"] == "discovered")
    return {
        "schema_version": 1,
        "registry": {
            "name": name,
            "generated_at": format_timestamp(generated),
            "valid_until": format_timestamp(valid_until),
            "publisher_version": __version__,
        },
        "entries": normalized,
        "summary": {
            "entry_count": len(normalized),
            "static_count": static_count,
            "discovered_count": discovered_count,
        },
    }
