import json
from pathlib import Path
import unittest

from trusted_network_registry.config import load_publisher_config
from trusted_network_registry.schema import (
    ADDRESS_FAMILIES,
    ENTRY_REQUIRED,
    ENTRY_KINDS,
    ENTRY_STATUSES,
    PUBLISH_TARGETS,
    REGISTRY_META_REQUIRED,
    REGISTRY_REQUIRED,
    SchemaError,
    SOURCE_TYPES,
    validate_publisher_config,
    validate_registry_document,
)


ROOT = Path(__file__).resolve().parents[2]


class SchemaFileTests(unittest.TestCase):
    def test_schema_files_are_valid_json(self) -> None:
        for path in ROOT.glob("schemas/*.json"):
            with self.subTest(path=path.name):
                json.loads(path.read_text())

    def test_registry_schema_enums_match_runtime_validator(self) -> None:
        schema = json.loads((ROOT / "schemas/registry.schema.json").read_text())
        entry_properties = schema["properties"]["entries"]["items"]["properties"]

        self.assertEqual(set(entry_properties["address_family"]["enum"]), ADDRESS_FAMILIES)
        self.assertEqual(set(entry_properties["kind"]["enum"]), ENTRY_KINDS)
        self.assertEqual(set(entry_properties["source_type"]["enum"]), SOURCE_TYPES)
        self.assertEqual(set(entry_properties["status"]["enum"]), ENTRY_STATUSES)

    def test_registry_schema_required_fields_match_runtime_validator(self) -> None:
        schema = json.loads((ROOT / "schemas/registry.schema.json").read_text())

        self.assertEqual(set(schema["required"]), REGISTRY_REQUIRED)
        self.assertEqual(
            set(schema["properties"]["registry"]["required"]),
            REGISTRY_META_REQUIRED,
        )
        self.assertEqual(
            set(schema["properties"]["entries"]["items"]["required"]),
            ENTRY_REQUIRED,
        )

    def test_publisher_config_schema_enums_match_runtime_validator(self) -> None:
        schema = json.loads((ROOT / "schemas/publisher-config.schema.json").read_text())
        publish_properties = schema["properties"]["publish"]["properties"]
        static_properties = schema["properties"]["static_entries"]["items"]["properties"]

        self.assertEqual(set(publish_properties["target"]["enum"]), PUBLISH_TARGETS)
        self.assertEqual(set(static_properties["status"]["enum"]), ENTRY_STATUSES)

    def test_publisher_config_example_loads(self) -> None:
        config = load_publisher_config(ROOT / "examples/publisher-config.example.toml")

        self.assertEqual(config.registry_name, "trusted-network-registry")
        self.assertEqual(config.ttl_seconds, 3600)

    def test_object_storage_config_requires_minimal_upload_fields(self) -> None:
        with self.assertRaises(SchemaError):
            validate_publisher_config({"publish": {"target": "object_storage"}})

        validate_publisher_config(
            {
                "publish": {
                    "target": "object_storage",
                    "bucket": "bucket-label-placeholder",
                    "endpoint_url": "https://example.com",
                    "region": "us-example-1",
                    "object_key": "registry/registry.json",
                }
            }
        )

    def test_live_meraki_config_requires_organization_or_fixture(self) -> None:
        validate_publisher_config(
            {
                "meraki": {"enabled": True, "organization_id": "local"},
                "publish": {"local_path": "registry.json"},
            }
        )
        validate_publisher_config(
            {
                "meraki": {"enabled": True, "fixture_path": "fixture.json"},
                "publish": {"local_path": "registry.json"},
            }
        )

        with self.assertRaises(SchemaError):
            validate_publisher_config(
                {
                    "meraki": {"enabled": True},
                    "publish": {"local_path": "registry.json"},
                }
            )

        with self.assertRaises(SchemaError):
            validate_publisher_config(
                {
                    "meraki": {
                        "enabled": True,
                        "organization_id": "local",
                        "fixture_path": "fixture.json",
                    },
                    "publish": {"local_path": "registry.json"},
                }
            )

    def test_generated_example_payload_validates(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        validate_registry_document(document)


if __name__ == "__main__":
    unittest.main()
