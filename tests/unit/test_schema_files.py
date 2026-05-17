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
    SOURCE_TYPES,
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

    def test_generated_example_payload_validates(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        validate_registry_document(document)


if __name__ == "__main__":
    unittest.main()
