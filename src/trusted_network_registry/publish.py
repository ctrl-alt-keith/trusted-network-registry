"""One-shot registry publisher."""

from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
from typing import Any

from .config import PublisherConfig, load_publisher_config
from .discovery.meraki import render_meraki_entries_from_fixture
from .discovery.static import render_static_entries
from .registry import parse_timestamp, render_registry, utc_now
from .schema import validate_registry_document


def publish_once(
    *,
    config_path: Path,
    output_path: Path | None = None,
    tfvars_output_path: Path | None = None,
    generated_at_text: str | None = None,
) -> dict[str, Any]:
    config = load_publisher_config(config_path)
    generated_at = parse_timestamp(generated_at_text) if generated_at_text else utc_now()
    valid_until = generated_at + timedelta(seconds=config.ttl_seconds)

    entries = render_static_entries(config.static_entries)
    if config.meraki.enabled:
        assert config.meraki.fixture_path is not None
        fixture_path = _resolve_relative(config_path, config.meraki.fixture_path)
        entries.extend(
            render_meraki_entries_from_fixture(
                fixture_path,
                observed_at=generated_at,
                valid_until=valid_until,
            )
        )

    registry = render_registry(
        entries,
        name=config.registry_name,
        generated_at=generated_at,
        ttl_seconds=config.ttl_seconds,
    )
    validate_registry_document(registry)

    target_output = output_path or _default_output_path(config_path, config)
    _write_json(target_output, registry)

    target_tfvars = tfvars_output_path
    if target_tfvars is None and config.publish.tfvars_path:
        target_tfvars = _resolve_relative(config_path, config.publish.tfvars_path)
    if target_tfvars is not None:
        _write_json(target_tfvars, render_tfvars(registry))

    return registry


def render_tfvars(registry: dict[str, Any]) -> dict[str, Any]:
    active_cidrs = [
        entry["cidr"]
        for entry in registry["entries"]
        if entry.get("status") == "active"
    ]
    return {
        "trusted_registry": registry,
        "trusted_admin_cidrs": active_cidrs,
        "trusted_registry_valid_until": registry["registry"]["valid_until"],
    }


def _default_output_path(config_path: Path, config: PublisherConfig) -> Path:
    if config.publish.target == "object_storage":
        # MVP scaffold: render the object payload locally for a separate
        # credentialed upload step. Terraform does not own this dynamic file.
        return _resolve_relative(config_path, config.publish.local_path)
    return _resolve_relative(config_path, config.publish.local_path)


def _resolve_relative(config_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return config_path.parent / path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
