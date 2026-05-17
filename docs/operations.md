# Operations

## Publisher Run

Run exactly once:

```sh
trusted-network-registry publish --once --config publisher-config.toml
```

The command validates the generated registry before writing it. If configured,
it also writes generated tfvars JSON for Terraform consumers. Generated CIDR
lists may contain both IPv4 and IPv6 entries.

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

The publisher renders and validates `/out/registry.json` first, then uploads
that payload to the configured object key with a private ACL. It does not
create buckets, change bucket policies, make objects public, mutate firewalls,
or run a reconciliation loop.

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
