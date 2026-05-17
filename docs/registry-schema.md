# Registry Schema

Schema v1 lives at [`../schemas/registry.schema.json`](../schemas/registry.schema.json).

Top-level fields:

- `schema_version`: currently `1`.
- `registry`: metadata about the generated payload.
- `entries`: static and discovered CIDR entries.
- `summary`: counts derived from entries.

Each entry includes:

- `id`: stable registry-local identifier.
- `cidr`: canonical CIDR string.
- `address_family`: `ipv4` or `ipv6`.
- `kind`: `static` or `discovered`.
- `source_type`: `config` or `meraki_uplink_addresses`.
- `source_ref`: generic operator-controlled reference.
- `status`: `active` or `inactive`.

Discovered entries may also include:

- `observed_at`
- `expires_at`

Consumers should read `registry.valid_until` before using entries.
