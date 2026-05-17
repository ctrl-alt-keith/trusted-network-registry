"""Publisher configuration loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import tomllib

from .schema import validate_publisher_config


@dataclass(frozen=True)
class StaticEntryConfig:
    id: str
    cidr: str
    source_ref: str
    status: str = "active"


@dataclass(frozen=True)
class MerakiConfig:
    enabled: bool = False
    organization_id: str | None = None
    fixture_path: str | None = None


@dataclass(frozen=True)
class PublishConfig:
    target: str = "local_file"
    local_path: str = "registry.json"
    tfvars_path: str | None = None
    object_key: str = "registry.json"
    bucket: str | None = None
    endpoint_url: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class PublisherConfig:
    registry_name: str = "trusted-network-registry"
    ttl_seconds: int = 3600
    static_entries: list[StaticEntryConfig] = field(default_factory=list)
    meraki: MerakiConfig = field(default_factory=MerakiConfig)
    publish: PublishConfig = field(default_factory=PublishConfig)


def load_publisher_config(path: Path) -> PublisherConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    validate_publisher_config(raw)
    return publisher_config_from_dict(raw)


def publisher_config_from_dict(raw: dict[str, Any]) -> PublisherConfig:
    registry = raw.get("registry", {})
    meraki = raw.get("meraki", {})
    publish = raw.get("publish", {})
    return PublisherConfig(
        registry_name=registry.get("name", "trusted-network-registry"),
        ttl_seconds=int(registry.get("ttl_seconds", 3600)),
        static_entries=[
            StaticEntryConfig(
                id=item["id"],
                cidr=item["cidr"],
                source_ref=item["source_ref"],
                status=item.get("status", "active"),
            )
            for item in raw.get("static_entries", [])
        ],
        meraki=MerakiConfig(
            enabled=bool(meraki.get("enabled", False)),
            organization_id=meraki.get("organization_id"),
            fixture_path=meraki.get("fixture_path"),
        ),
        publish=PublishConfig(
            target=publish.get("target", "local_file"),
            local_path=publish.get("local_path", "registry.json"),
            tfvars_path=publish.get("tfvars_path"),
            object_key=publish.get("object_key", "registry.json"),
            bucket=publish.get("bucket"),
            endpoint_url=publish.get("endpoint_url"),
            region=publish.get("region"),
        ),
    )
