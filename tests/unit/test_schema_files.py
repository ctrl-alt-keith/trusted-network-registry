import json
from pathlib import Path
import unittest

from trusted_network_registry.config import load_publisher_config
from trusted_network_registry.schema import validate_registry_document


ROOT = Path(__file__).resolve().parents[2]


class SchemaFileTests(unittest.TestCase):
    def test_schema_files_are_valid_json(self) -> None:
        for path in ROOT.glob("schemas/*.json"):
            with self.subTest(path=path.name):
                json.loads(path.read_text())

    def test_publisher_config_example_loads(self) -> None:
        config = load_publisher_config(ROOT / "examples/publisher-config.example.toml")

        self.assertEqual(config.registry_name, "trusted-network-registry")
        self.assertEqual(config.ttl_seconds, 3600)

    def test_generated_example_payload_validates(self) -> None:
        document = json.loads((ROOT / "examples/registry.example.json").read_text())
        validate_registry_document(document)


if __name__ == "__main__":
    unittest.main()
