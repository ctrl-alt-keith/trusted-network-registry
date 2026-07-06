"""Public-safety helpers for examples and sanitized fixtures."""

from __future__ import annotations

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


def assert_public_safe_document(document: Any) -> None:
    problems: list[str] = []
    _walk(document, "$", problems)
    if problems:
        raise PublicSafetyError("; ".join(problems))


def redact_sensitive_fields(document: Any) -> Any:
    if isinstance(document, dict):
        redacted = {}
        for key, value in document.items():
            if key in FORBIDDEN_FIELD_NAMES:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_sensitive_fields(value)
        return redacted
    if isinstance(document, list):
        return [redact_sensitive_fields(item) for item in document]
    if isinstance(document, str):
        result = document
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            result = pattern.sub("[redacted]", result)
        return result
    return document


def assert_public_safe_json_text(text: str) -> None:
    assert_public_safe_document(json.loads(text))


def assert_public_safe_text(text: str, *, label: str = "text") -> None:
    problems: list[str] = []
    for match in FORBIDDEN_TEXT_FIELD_RE.finditer(text):
        problems.append(f"{label} uses forbidden provider field: {match.group('field')}")
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if pattern.search(text):
            problems.append(f"{label} contains unsafe-looking value")
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
