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
REGISTRY_SCHEMA_PATH = ROOT / "schemas/registry.schema.json"
REGISTRY_EXAMPLE_PATH = ROOT / "examples/registry.example.json"
REGISTRY_CONTRACT_FIXTURE_PATH = ROOT / "tests/fixtures/sanitized/registry.v1.example.json"


class SchemaFileTests(unittest.TestCase):
    def test_schema_files_are_valid_json(self) -> None:
        for path in ROOT.glob("schemas/*.json"):
            with self.subTest(path=path.name):
                json.loads(path.read_text())

    def test_registry_schema_enums_match_runtime_validator(self) -> None:
        schema = json.loads(REGISTRY_SCHEMA_PATH.read_text())
        entry_properties = schema["properties"]["entries"]["items"]["properties"]

        self.assertEqual(set(entry_properties["address_family"]["enum"]), ADDRESS_FAMILIES)
        self.assertEqual(set(entry_properties["kind"]["enum"]), ENTRY_KINDS)
        self.assertEqual(set(entry_properties["source_type"]["enum"]), SOURCE_TYPES)
        self.assertEqual(set(entry_properties["status"]["enum"]), ENTRY_STATUSES)

    def test_registry_schema_required_fields_match_runtime_validator(self) -> None:
        schema = json.loads(REGISTRY_SCHEMA_PATH.read_text())

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

    def test_object_storage_endpoint_url_rejects_userinfo(self) -> None:
        for endpoint_url in (
            "https://user@example.com",
            "https://user:password@example.com",
        ):
            with self.subTest(endpoint_url=endpoint_url):
                with self.assertRaises(SchemaError) as raised:
                    validate_publisher_config(
                        {
                            "publish": {
                                "target": "object_storage",
                                "bucket": "bucket-label-placeholder",
                                "endpoint_url": endpoint_url,
                                "region": "us-example-1",
                                "object_key": "registry/registry.json",
                            }
                        }
                    )

                self.assertIn("userinfo", str(raised.exception))

    def test_static_entries_reject_universal_ipv4_and_ipv6_cidrs(self) -> None:
        for cidr in ("0.0.0.0/0", "::/0"):
            with self.subTest(cidr=cidr):
                with self.assertRaises(SchemaError) as raised:
                    validate_publisher_config(
                        {
                            "static_entries": [
                                {
                                    "id": "admin-static-example",
                                    "cidr": cidr,
                                    "source_ref": "static-admin",
                                }
                            ],
                            "publish": {"local_path": "registry.json"},
                        }
                    )

                self.assertIn("universal allow CIDR", str(raised.exception))

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

    def test_registry_examples_validate(self) -> None:
        for path in (REGISTRY_EXAMPLE_PATH, REGISTRY_CONTRACT_FIXTURE_PATH):
            with self.subTest(path=path.name):
                document = json.loads(path.read_text())
                validate_registry_document(document)

    def test_registry_contract_fixture_conforms_to_published_schema(self) -> None:
        schema = json.loads(REGISTRY_SCHEMA_PATH.read_text())
        document = json.loads(REGISTRY_CONTRACT_FIXTURE_PATH.read_text())

        _assert_json_schema_subset(document, schema, "registry fixture")


def _assert_json_schema_subset(value: object, schema: dict[str, object], label: str) -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(value, dict), f"{label} must be an object"
        properties = schema.get("properties", {})
        assert isinstance(properties, dict), f"{label} schema properties must be an object"
        required = schema.get("required", [])
        assert isinstance(required, list), f"{label} schema required must be a list"
        missing = sorted(str(key) for key in required if key not in value)
        assert not missing, f"{label} missing required keys: {', '.join(missing)}"
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            assert not extra, f"{label} has extra keys: {', '.join(extra)}"
        for key, item in value.items():
            property_schema = properties.get(key)
            assert isinstance(property_schema, dict), f"{label}.{key} is not in schema"
            _assert_json_schema_subset(item, property_schema, f"{label}.{key}")
        return
    if schema_type == "array":
        assert isinstance(value, list), f"{label} must be an array"
        item_schema = schema.get("items")
        assert isinstance(item_schema, dict), f"{label} schema items must be an object"
        for index, item in enumerate(value):
            _assert_json_schema_subset(item, item_schema, f"{label}[{index}]")
        return
    if schema_type == "string":
        assert isinstance(value, str), f"{label} must be a string"
        if schema.get("minLength") == 1:
            assert value, f"{label} must be non-empty"
    elif schema_type == "integer":
        assert isinstance(value, int) and not isinstance(value, bool), f"{label} must be an integer"
        minimum = schema.get("minimum")
        if isinstance(minimum, int):
            assert value >= minimum, f"{label} must be at least {minimum}"

    if "const" in schema:
        assert value == schema["const"], f"{label} must be {schema['const']!r}"
    enum = schema.get("enum")
    if enum is not None:
        assert isinstance(enum, list), f"{label} enum must be a list"
        assert value in enum, f"{label} must be one of {enum!r}"


if __name__ == "__main__":
    unittest.main()
