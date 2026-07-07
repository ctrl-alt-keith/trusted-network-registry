# Registry Schema

Schema v1 lives at [`../schemas/registry.schema.json`](../schemas/registry.schema.json).
It intentionally supports both IPv4 and IPv6 registry entries from the MVP.

## Contract Boundary

- Producer: `ctrl-alt-keith/trusted-network-registry`.
- Artifact: registry JSON emitted by `trusted-network-registry publish --once`.
- Schema/version: registry schema v1, identified by top-level
  `schema_version: 1` and described by
  [`../schemas/registry.schema.json`](../schemas/registry.schema.json).
- Public-safe fixture:
  [`../tests/fixtures/sanitized/registry.v1.example.json`](../tests/fixtures/sanitized/registry.v1.example.json).
- Intended consumer: `ctrl-alt-keith/linode-image-lab` `firewall-sync`.

Incompatible changes to the registry artifact require an explicit
schema/version change. Consumers must opt in to incompatible schema versions
instead of silently accepting them.

Top-level fields:

- `schema_version`: currently `1`.
- `registry`: metadata about the generated payload.
- `entries`: static and discovered CIDR entries.
- `summary`: counts derived from entries.

Each entry includes:

- `id`: stable registry-local identifier.
- `cidr`: canonical IPv4 or IPv6 CIDR string.
- `address_family`: `ipv4` or `ipv6`.
- `kind`: `static` or `discovered`.
- `source_type`: `config` or `meraki_uplink_addresses`.
- `source_ref`: generic operator-controlled reference.
- `status`: `active` or `inactive`.

Discovered entries may also include:

- `observed_at`
- `expires_at`

Consumers should read `registry.valid_until` before using entries.

## Runtime And Published Schemas

Runtime validation is implemented by the Python validators in
`trusted_network_registry.schema`. The checked-in JSON schemas are published
consumer contracts for downstream tooling and documentation.

The canonical local validation path parses the JSON schemas, checks that the
published enum values match the runtime validator constants, validates the
checked-in examples with the runtime validator, and checks that the public-safe
v1 fixture conforms to the published schema shape. The MVP does not add a
`jsonschema` dependency only for local validation.
