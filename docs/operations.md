# Operations

## Publisher Run

Run exactly once:

```sh
trusted-network-registry publish --once --config operator/publisher-config.toml
```

The command validates the generated registry before writing it. If configured,
it also writes generated tfvars JSON for Terraform consumers. Generated CIDR
lists may contain both IPv4 and IPv6 entries.

Before discovery or rendering, the publisher verifies that the config file,
registry output, and generated tfvars output point at distinct files. This
prevents a typo from overwriting the private config or making one generated
artifact clobber another.

Keep private operator files under `operator/`, including
`operator/publisher-config.toml`, `operator/publisher.env`, generated registry
JSON, and generated tfvars JSON. That directory is intentionally ignored by
Git because it may contain administrative source networks, provider
identifiers, bucket details, object names, and credentials.

For first live use, follow [`first-real-operator-run.md`](first-real-operator-run.md)
before moving the workflow to Synology scheduling.

## Object Storage Uploads

For Object Storage publishing, configure:

```toml
[publish]
target = "object_storage"
local_path = "/out/registry.json"
bucket = "<private-bucket-label>"
endpoint_url = "https://<s3-endpoint-hostname>"
region = "<region>"
object_key = "registry.json"
```

Set credentials through the runtime environment only:

```sh
LINODE_OBJ_ACCESS_KEY=...
LINODE_OBJ_SECRET_KEY=...
```

If using 1Password or another secret manager, keep the application contract the
same: the secret manager should populate environment variables before the
publisher process starts. For example, `op run --env-file=operator/publisher.env -- ...`
can wrap the one-shot publish command without adding a Python dependency.

The publisher renders and validates `/out/registry.json` first, then uploads
that payload to the configured object key with a private ACL. It does not
create buckets, change bucket policies, make objects public, mutate firewalls,
or run a reconciliation loop.

## Live Meraki Discovery

For live Meraki discovery, configure `meraki.enabled = true` and
`meraki.organization_id` in a private local config, omit `meraki.fixture_path`,
and export `MERAKI_DASHBOARD_API_KEY` before running the one-shot publisher.
The publisher calls only the read-only uplink-address endpoint and follows
documented `Link` header pagination until no next page is present.

## Rotation

Set `registry.ttl_seconds` to the maximum acceptable age for consumers. The
publisher writes `valid_until`; consumers should enforce their own rejection
policy when that timestamp is stale.

## Logs

The MVP prints small status messages to stdout and error messages to stderr.
It should not print registry contents, credential values, provider IDs, device
names, bucket identifiers, endpoint URLs, or object keys.

## Recovery

If a bad payload is published, publish a corrected payload with a newer
`generated_at` and shorter `valid_until`. Registry history retention and
rollback docs are deferred follow-ups.
