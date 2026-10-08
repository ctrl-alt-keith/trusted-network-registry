"""Keep the offline image build inputs narrow and immutable."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class LkeImageContractTests(unittest.TestCase):
    def test_base_and_runtime_dependencies_are_pinned(self) -> None:
        dockerfile = (ROOT / "Dockerfile.lke").read_text(encoding="utf-8")
        base = next(line for line in dockerfile.splitlines() if line.startswith("FROM "))
        self.assertRegex(
            base,
            r"^FROM --platform=linux/amd64 python:3\.11\.14-slim-bookworm@sha256:[0-9a-f]{64}$",
        )
        self.assertIn("--require-hashes -r requirements-lke.lock", dockerfile)

        lock = (ROOT / "requirements-lke.lock").read_text(encoding="utf-8")
        requirements = re.findall(r"^([a-z0-9-]+)==[^\s]+ \\\n", lock, re.MULTILINE)
        self.assertIn("boto3", requirements)
        self.assertEqual(lock.count("--hash=sha256:"), 2 * len(requirements))

    def test_build_context_cannot_include_operator_files(self) -> None:
        ignore = (ROOT / "Dockerfile.lke.dockerignore").read_text(encoding="utf-8")
        patterns = [
            line for line in ignore.splitlines() if line and not line.startswith("#")
        ]
        self.assertEqual(
            patterns,
            [
                "*",
                "!requirements-lke.lock",
                "!src/",
                "!src/trusted_network_registry/",
                "!src/trusted_network_registry/*.py",
                "!src/trusted_network_registry/discovery/",
                "!src/trusted_network_registry/discovery/*.py",
            ],
        )
        dockerfile = (ROOT / "Dockerfile.lke").read_text(encoding="utf-8")
        copies = [line for line in dockerfile.splitlines() if line.startswith("COPY ")]
        self.assertEqual(
            copies,
            ["COPY requirements-lke.lock ./", "COPY src ./src"],
        )


if __name__ == "__main__":
    unittest.main()
