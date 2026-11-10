"""Public-safety helpers for examples and sanitized fixtures."""

from __future__ import annotations

import ipaddress
import json
import re
from typing import Any


class PublicSafetyError(ValueError):
    """Raised when checked example material contains unsafe-looking values."""


FORBIDDEN_FIELD_NAMES = {
    "organizationId",
    "organization_id",
    "networkId",
    "network_id",
    "serial",
    "deviceName",
    "device_name",
    "isp",
}

FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"\bN_[A-Za-z0-9_-]{6,}\b"),
    re.compile(r"\bQ[A-Z0-9]{3}-[A-Z0-9]{4}-[A-Z0-9]{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"https?://(?!example\.com\b|localhost\b)[^\s\"']+"),
]
FORBIDDEN_TEXT_FIELD_RE = re.compile(
    r"^\s*[\"']?(?P<field>"
    + "|".join(re.escape(field) for field in sorted(FORBIDDEN_FIELD_NAMES))
    + r")[\"']?\s*[:=]",
    re.MULTILINE,
)
IPV4_LITERAL_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")
# RFC 5737 reserves these three IPv4 blocks for documentation.
DOCUMENTATION_IPV4_NETWORKS = tuple(
    ipaddress.IPv4Network(value)
    for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)


def _contains_non_documentation_ipv4(text: str) -> bool:
    for match in IPV4_LITERAL_RE.finditer(text):
        try:
            network = ipaddress.IPv4Network(match.group(0), strict=False)
        except ValueError:
            continue
        if not any(network.subnet_of(documentation) for documentation in DOCUMENTATION_IPV4_NETWORKS):
            return True
    return False


def assert_public_safe_document(document: Any) -> None:
    problems: list[str] = []
    _walk(document, "$", problems)
    if problems:
        raise PublicSafetyError("; ".join(problems))


def assert_public_safe_json_text(text: str) -> None:
    assert_public_safe_document(json.loads(text))


def assert_public_safe_text(text: str, *, label: str = "text") -> None:
    problems: list[str] = []
    for match in FORBIDDEN_TEXT_FIELD_RE.finditer(text):
        problems.append(f"{label} uses forbidden provider field: {match.group('field')}")
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(text):
            problems.append(f"{label} contains unsafe-looking value")
    if _contains_non_documentation_ipv4(text):
        problems.append(f"{label} contains IPv4 outside documentation ranges")
    if problems:
        raise PublicSafetyError("; ".join(problems))


def _walk(value: Any, path: str, problems: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_FIELD_NAMES:
                problems.append(f"{path}.{key} uses a forbidden provider field")
            _walk(child, f"{path}.{key}", problems)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, f"{path}[{index}]", problems)
    elif isinstance(value, str):
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(value):
                problems.append(f"{path} contains unsafe-looking value")
        if _contains_non_documentation_ipv4(value):
            problems.append(f"{path} contains IPv4 outside documentation ranges")
