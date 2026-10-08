"""Prove the qualification route never gains Object Storage write behavior."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from trusted_network_registry.publish import publish_once


class LkeLocalRenderTests(unittest.TestCase):
    def test_live_discovery_local_config_never_calls_uploader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "qualification.toml"
            output = Path(tmp) / "registry.json"
            config.write_text(
                '[meraki]\nenabled = true\norganization_id = "<organization-id>"\n\n'
                '[publish]\ntarget = "local_file"\nlocal_path = "registry.json"\n',
                encoding="utf-8",
            )
            with (
                patch(
                    "trusted_network_registry.publish.discover_meraki_uplink_entries",
                    return_value=[],
                ) as discover,
                patch(
                    "trusted_network_registry.publish._upload_to_object_storage",
                    side_effect=AssertionError("qualification attempted upload"),
                ) as upload,
            ):
                registry = publish_once(config_path=config)

            discover.assert_called_once()
            upload.assert_not_called()
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), registry)
            self.assertEqual(registry["schema_version"], 1)

    def test_output_override_does_not_make_object_storage_config_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "publisher.toml"
            output = Path(tmp) / "preview.json"
            config.write_text(
                '[publish]\ntarget = "object_storage"\n'
                'local_path = "registry.json"\n'
                'bucket = "<bucket-label>"\n'
                'endpoint_url = "https://example.com"\n'
                'region = "<region>"\n'
                'object_key = "registry.json"\n',
                encoding="utf-8",
            )
            uploads = []

            publish_once(
                config_path=config,
                output_path=output,
                object_storage_uploader=lambda *args: uploads.append(args),
            )

            self.assertTrue(output.is_file())
            self.assertEqual(len(uploads), 1)


if __name__ == "__main__":
    unittest.main()
