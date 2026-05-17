# Architecture

Trusted Network Registry has one MVP responsibility: produce a private,
time-bounded JSON registry of trusted/admin IPv4 and IPv6 CIDRs.

## Boundaries

- Publisher owns registry production.
- Terraform owns static storage infrastructure.
- Consumers read registry data and decide their own stale-data policy.
- No component automatically mutates firewalls.
- No component continuously reconciles external systems.

## Flow

1. Load publisher config.
2. Canonicalize static IPv4 and IPv6 CIDR entries.
3. Optionally discover Meraki uplink public addresses from either a sanitized
   fixture or one live read-only Dashboard API endpoint, rendering IPv4 public
   host addresses as `/32` and IPv6 public host addresses as `/128`.
4. Render registry JSON with `generated_at` and `valid_until`.
5. Validate the registry document.
6. Write registry JSON locally and optional generated tfvars JSON.
7. If `publish.target = "object_storage"`, upload the validated registry JSON
   to the configured S3-compatible Object Storage object.

The MVP favors one-shot execution through `publish --once`. A scheduler, such
as a Synology scheduled task, owns cadence.

## Meraki Boundary

The Meraki adapter is bounded to read-only uplink address discovery. Live mode
calls only `GET /organizations/{organizationId}/devices/uplinks/addresses/byDevice`
using `MERAKI_DASHBOARD_API_KEY`; fixture mode remains available for tests and
local rendering without credentials. It does not call mutation APIs, reconcile
controllers, upload registry data, or manage firewalls.

Published entries use only generic source refs: `wan1`, `wan2`, and
`cellular`. The adapter reads `uplinks[].addresses[].public.address` and never
copies raw serials, organization IDs, network IDs, device names, ISP names,
tags, or topology labels into registry entries. Public IPv4 host addresses are
rendered as `/32`; public IPv6 host addresses are rendered as `/128`.

## Storage Boundary

Terraform provisions a private Object Storage bucket. It does not upload,
version, or replace generated registry JSON. The publisher owns dynamic object
content by rendering, validating, and then uploading the registry object during
one-shot execution.

Object Storage upload config stays intentionally narrow: bucket label, HTTPS
endpoint URL, region, and object key. Credentials are read only from
`LINODE_OBJ_ACCESS_KEY` and `LINODE_OBJ_SECRET_KEY` at runtime. The upload path
uses the S3-compatible API and requests a private ACL so generated registry
payloads remain private by default.
