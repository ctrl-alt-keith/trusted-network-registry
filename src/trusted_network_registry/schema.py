"""Small runtime validators for registry and publisher config documents."""

from __future__ import annotations

from datetime import datetime
import ipaddress
from urllib.parse import urlparse
from typing import Any


class SchemaError(ValueError):
    """Raised when a registry or publisher config document is invalid."""


REGISTRY_REQUIRED = {"schema_version", "registry", "entries", "summary"}
REGISTRY_META_REQUIRED = {"name", "generated_at", "valid_until", "publisher_version"}
ENTRY_REQUIRED = {
    "id",
    "cidr",
    "address_family",
    "kind",
    "source_type",
    "source_ref",
    "status",
}
ADDRESS_FAMILIES = {"ipv4", "ipv6"}
ENTRY_KINDS = {"static", "discovered"}
SOURCE_TYPES = {"config", "meraki_uplink_addresses"}
ENTRY_STATUSES = {"active", "inactive"}
PUBLISH_TARGETS = {"local_file", "object_storage"}
UNIVERSAL_CIDRS = {"0.0.0.0/0", "::/0"}


def validate_rfc3339_z(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SchemaError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchemaError(f"{field} must be a valid RFC3339 timestamp") from exc


def validate_registry_document(document: dict[str, Any]) -> None:
    if not isinstance(document, dict):
        raise SchemaError("registry document must be an object")
    _require(document, REGISTRY_REQUIRED, "registry document")
    if document["schema_version"] != 1:
        raise SchemaError("schema_version must be 1")

    meta = document["registry"]
    if not isinstance(meta, dict):
        raise SchemaError("registry must be an object")
    _require(meta, REGISTRY_META_REQUIRED, "registry")
    generated_at = validate_rfc3339_z(meta["generated_at"], "registry.generated_at")
    valid_until = validate_rfc3339_z(meta["valid_until"], "registry.valid_until")
    if valid_until <= generated_at:
        raise SchemaError("registry.valid_until must be after registry.generated_at")

    entries = document["entries"]
    if not isinstance(entries, list):
        raise SchemaError("entries must be an array")

    ids: set[str] = set()
    static_count = 0
    discovered_count = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise SchemaError(f"entries[{index}] must be an object")
        _require(entry, ENTRY_REQUIRED, f"entries[{index}]")
        entry_id = _non_empty_string(entry["id"], f"entries[{index}].id")
        if entry_id in ids:
            raise SchemaError(f"duplicate entry id: {entry_id}")
        ids.add(entry_id)

        network = ipaddress.ip_network(entry["cidr"], strict=False)
        _reject_universal_cidr(network, f"entries[{index}].cidr")
        if entry["cidr"] != network.with_prefixlen:
            raise SchemaError(
                f"entries[{index}].cidr must be canonical: {network.with_prefixlen}"
            )
        expected_family = "ipv4" if network.version == 4 else "ipv6"
        if entry["address_family"] not in ADDRESS_FAMILIES:
            raise SchemaError(f"entries[{index}].address_family is not supported")
        if entry["address_family"] != expected_family:
            raise SchemaError(f"entries[{index}].address_family does not match cidr")

        kind = entry["kind"]
        if kind not in ENTRY_KINDS:
            raise SchemaError(f"entries[{index}].kind must be static or discovered")
        if kind == "static":
            static_count += 1
        else:
            discovered_count += 1
            for field in ("observed_at", "expires_at"):
                if field in entry:
                    validate_rfc3339_z(entry[field], f"entries[{index}].{field}")

        if entry["source_type"] not in SOURCE_TYPES:
            raise SchemaError(f"entries[{index}].source_type is not supported")
        _non_empty_string(entry["source_ref"], f"entries[{index}].source_ref")
        if entry["status"] not in ENTRY_STATUSES:
            raise SchemaError(f"entries[{index}].status must be active or inactive")

    summary = document["summary"]
    if not isinstance(summary, dict):
        raise SchemaError("summary must be an object")
    expected = {
        "entry_count": len(entries),
        "static_count": static_count,
        "discovered_count": discovered_count,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise SchemaError(f"summary.{key} must be {value}")


def validate_publisher_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise SchemaError("publisher config must be an object")
    registry = config.get("registry", {})
    if not isinstance(registry, dict):
        raise SchemaError("registry config must be an object")
    if registry.get("ttl_seconds", 3600) <= 0:
        raise SchemaError("registry.ttl_seconds must be positive")

    static_entries = config.get("static_entries", [])
    if not isinstance(static_entries, list):
        raise SchemaError("static_entries must be an array")
    for index, entry in enumerate(static_entries):
        if not isinstance(entry, dict):
            raise SchemaError(f"static_entries[{index}] must be an object")
        _require(entry, {"id", "cidr", "source_ref"}, f"static_entries[{index}]")
        _non_empty_string(entry["id"], f"static_entries[{index}].id")
        network = ipaddress.ip_network(entry["cidr"], strict=False)
        _reject_universal_cidr(network, f"static_entries[{index}].cidr")
        _non_empty_string(entry["source_ref"], f"static_entries[{index}].source_ref")
        if entry.get("status", "active") not in ENTRY_STATUSES:
            raise SchemaError(f"static_entries[{index}].status must be active or inactive")

    meraki = config.get("meraki", {})
    if meraki and not isinstance(meraki, dict):
        raise SchemaError("meraki config must be an object")
    if meraki.get("enabled", False):
        has_fixture = bool(meraki.get("fixture_path"))
        has_organization = bool(meraki.get("organization_id"))
        if has_fixture == has_organization:
            raise SchemaError(
                "Meraki discovery requires exactly one of "
                "meraki.fixture_path or meraki.organization_id"
            )

    publish = config.get("publish", {})
    if publish and not isinstance(publish, dict):
        raise SchemaError("publish config must be an object")
    target = publish.get("target", "local_file")
    if target not in PUBLISH_TARGETS:
        raise SchemaError("publish.target must be local_file or object_storage")
    if target == "local_file" and not publish.get("local_path"):
        raise SchemaError("publish.local_path is required for local_file")
    if target == "object_storage":
        for field in ("bucket", "endpoint_url", "region", "object_key"):
            _non_empty_string(publish.get(field), f"publish.{field}")
        endpoint = urlparse(publish["endpoint_url"])
        if endpoint.scheme != "https" or not endpoint.netloc:
            raise SchemaError("publish.endpoint_url must be an https URL")
        if endpoint.username or endpoint.password:
            raise SchemaError("publish.endpoint_url must not include userinfo")


def _require(document: dict[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - set(document))
    if missing:
        raise SchemaError(f"{label} missing required keys: {', '.join(missing)}")


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{field} must be a non-empty string")
    return value


def _reject_universal_cidr(
    network: ipaddress.IPv4Network | ipaddress.IPv6Network,
    field: str,
) -> None:
    if network.with_prefixlen in UNIVERSAL_CIDRS:
        raise SchemaError(f"{field} must not be a universal allow CIDR")
