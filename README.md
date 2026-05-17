# Trusted Network Registry

Personal, public-safe open-source tooling for producing a private
trusted/admin CIDR registry.

This is an independent personal project. It is not affiliated with, endorsed
by, or supported by Akamai, Linode, Cisco Meraki, any employer, or their
affiliates.

## What This Repo Does

- Builds a versioned JSON registry of trusted/admin IPv4 and IPv6 CIDR entries.
- Validates and canonicalizes static CIDR entries first.
- Provides bounded Meraki uplink discovery scaffolding that renders IPv4 host
  addresses as `/32` and IPv6 host addresses as `/128` without publishing raw
  provider identifiers.
- Supports one-shot publisher execution for scheduled environments such as
  Synology.
- Provides Terraform that provisions Object Storage infrastructure only.
- Provides read-only Terraform consumer examples for already-produced registry
  JSON.

## What This Repo Does Not Do

- It does not publish registry payloads publicly by default.
- It does not manage firewall rules.
- It does not continuously reconcile external systems.
- It does not use Terraform to manage dynamic registry JSON contents.
- It does not provide a general infrastructure toolbox.
- It does not abstract NAS platforms.

## Registry Sensitivity

Registry payloads are sensitive operational access data. Treat generated JSON
as private by default, even when every value looks ordinary. Examples in this
repository use only documentation address ranges:

- `192.0.2.0/24`
- `198.51.100.0/24`
- `203.0.113.0/24`
- `2001:db8::/32`

Do not commit real home IPs, Meraki organization IDs, network IDs, serials,
bucket names, provider identifiers, internal DNS names, private URLs, or
secrets.

## Quick Start

Create a local config:

```sh
cp examples/publisher-config.example.toml publisher-config.toml
```

Run the one-shot publisher:

```sh
python -m trusted_network_registry.cli publish --once \
  --config publisher-config.toml \
  --output registry.json \
  --tfvars-output trusted-registry.auto.tfvars.json
```

Validate the example registry:

```sh
python -m trusted_network_registry.cli validate-registry \
  examples/registry.example.json
```

## Validation

`make check` is the canonical local validation entrypoint. It runs Python
compile checks, unit tests, schema/example validation, and public-safety tests.

## Documentation

- [Architecture](docs/architecture.md)
- [Security](docs/security.md)
- [Registry schema](docs/registry-schema.md)
- [Terraform integration](docs/terraform-integration.md)
- [Synology deployment](docs/synology-deployment.md)
- [Provider assumptions](docs/provider-assumptions.md)
- [Operations](docs/operations.md)
- [Follow-ups](docs/followups.md)
