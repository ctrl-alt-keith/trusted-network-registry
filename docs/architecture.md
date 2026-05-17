# Architecture

Trusted Network Registry has one MVP responsibility: produce a private,
time-bounded JSON registry of trusted/admin CIDRs.

## Boundaries

- Publisher owns registry production.
- Terraform owns static storage infrastructure.
- Consumers read registry data and decide their own stale-data policy.
- No component automatically mutates firewalls.
- No component continuously reconciles external systems.

## Flow

1. Load publisher config.
2. Canonicalize static CIDR entries.
3. Optionally read sanitized Meraki uplink fixture data.
4. Render registry JSON with `generated_at` and `valid_until`.
5. Validate the registry document.
6. Write registry JSON and optional generated tfvars JSON.

The MVP favors one-shot execution through `publish --once`. A scheduler, such
as a Synology scheduled task, owns cadence.

## Meraki Boundary

The Meraki adapter is scaffolded around sanitized uplink-address fixture data.
It does not make live Dashboard API calls in the MVP. Published entries use
generic source refs such as `wan1` and never include raw serials, organization
IDs, network IDs, device names, ISP names, or topology labels.

## Storage Boundary

Terraform provisions a private Object Storage bucket. It does not upload,
version, or replace generated registry JSON. The publisher or a future upload
helper owns dynamic object content.
