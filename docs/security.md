# Security

Registry payloads are sensitive operational access data. A CIDR registry can
expose where administrative access is expected to originate, so generated
IPv4 and IPv6 payloads should be private by default.

## Public-Safe Rules

- Examples use only documentation IP ranges, including `2001:db8::/32` for
  IPv6.
- Do not commit real home IPs, provider identifiers, private URLs, internal
  DNS names, device labels, bucket names, or secrets.
- Keep Meraki source references generic and operator-controlled.
- Keep generated registry JSON and generated tfvars JSON out of Git.

## Credential Handling

Credential names may appear in docs and examples as environment variables:

- `MERAKI_DASHBOARD_API_KEY`
- `LINODE_TOKEN`
- `LINODE_OBJ_ACCESS_KEY`
- `LINODE_OBJ_SECRET_KEY`

Do not put credential values in config files, example files, Terraform
variables committed to Git, logs, or PR notes.

## Terraform State

Terraform state can store sensitive values even when variables are marked
sensitive. Keep state private, encrypted where practical, and excluded from
Git. This repo's Terraform manages bucket infrastructure only; it intentionally
does not manage generated registry object contents.

## Expiration

Every registry includes `valid_until`. Consumers should reject stale registries
instead of continuing to trust old CIDR data silently.
