"""Keep the offline image build inputs narrow and immutable."""

from pathlib import Path
import re
import tomllib
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

        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        boto3_range = next(
            dependency for dependency in project["project"]["dependencies"]
            if dependency.startswith("boto3")
        )
        bounds = re.fullmatch(
            r"boto3>=(\d+(?:\.\d+)+),<(\d+(?:\.\d+)+)", boto3_range
        )
        self.assertIsNotNone(bounds)
        lower, upper = bounds.groups()
        pin = re.search(r"^boto3==(\d+(?:\.\d+)+)", lock, re.MULTILINE)
        self.assertIsNotNone(pin)
        pinned = pin.group(1)

        def version(text: str) -> tuple[int, ...]:
            return tuple(int(part) for part in text.split("."))
        self.assertLessEqual(version(lower), version(pinned))
        self.assertLess(version(pinned), version(upper))

    def test_image_copies_only_runtime_source(self) -> None:
        dockerfile = (ROOT / "Dockerfile.lke").read_text(encoding="utf-8")
        copies = [line for line in dockerfile.splitlines() if line.startswith("COPY ")]
        self.assertEqual(
            copies,
            [
                "COPY requirements-lke.lock ./",
                "COPY src/trusted_network_registry/*.py ./src/trusted_network_registry/",
                "COPY src/trusted_network_registry/discovery/*.py ./src/trusted_network_registry/discovery/",
            ],
        )


if __name__ == "__main__":
    unittest.main()
