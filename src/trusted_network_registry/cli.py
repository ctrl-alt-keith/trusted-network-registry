"""Command line interface for the trusted network registry publisher."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import load_publisher_config
from .publish import publish_once
from .schema import SchemaError, validate_registry_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trusted-network-registry")
    subcommands = parser.add_subparsers(dest="command", required=True)

    publish = subcommands.add_parser("publish", help="render a registry payload")
    publish.add_argument("--once", action="store_true", help="run exactly once")
    publish.add_argument("--config", required=True, type=Path)
    publish.add_argument("--output", type=Path)
    publish.add_argument("--tfvars-output", type=Path)
    publish.add_argument("--generated-at")

    validate_registry = subcommands.add_parser(
        "validate-registry", help="validate a registry JSON file"
    )
    validate_registry.add_argument("path", type=Path)

    validate_config = subcommands.add_parser(
        "validate-config", help="validate a publisher TOML file"
    )
    validate_config.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "publish":
            if not args.once:
                parser.error("publish requires --once for the MVP execution model")
            registry = publish_once(
                config_path=args.config,
                output_path=args.output,
                tfvars_output_path=args.tfvars_output,
                generated_at_text=args.generated_at,
            )
            print(json.dumps({"status": "published", "entries": registry["summary"]["entry_count"]}))
            return 0
        if args.command == "validate-registry":
            document = json.loads(args.path.read_text(encoding="utf-8"))
            validate_registry_document(document)
            print(json.dumps({"status": "valid", "path": str(args.path)}))
            return 0
        if args.command == "validate-config":
            load_publisher_config(args.path)
            print(json.dumps({"status": "valid", "path": str(args.path)}))
            return 0
    except (OSError, SchemaError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
