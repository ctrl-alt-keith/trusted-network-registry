#!/usr/bin/env bash
set -euo pipefail

# Copy this file to operator/run-local-publish.sh, then edit only the local copy.
# Keep operator/publisher-config.toml and operator/publisher.env private.

CONFIG_PATH="${CONFIG_PATH:-operator/publisher-config.toml}"
OUTPUT_PATH="${OUTPUT_PATH:-operator/generated/registry.json}"
TFVARS_OUTPUT_PATH="${TFVARS_OUTPUT_PATH:-operator/generated/trusted-registry.auto.tfvars.json}"

mkdir -p "$(dirname "$OUTPUT_PATH")" "$(dirname "$TFVARS_OUTPUT_PATH")"

# Optional 1Password form from the repo root after copying this helper:
# op run --env-file=operator/publisher.env -- operator/run-local-publish.sh

trusted-network-registry publish --once \
  --config "$CONFIG_PATH" \
  --output "$OUTPUT_PATH" \
  --tfvars-output "$TFVARS_OUTPUT_PATH"
