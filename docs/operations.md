# Operations

## Publisher Run

Run exactly once:

```sh
trusted-network-registry publish --once --config operator/publisher-config.toml
```

Relative `meraki.fixture_path`, `publish.local_path`, and
`publish.tfvars_path` values in the config are resolved from the config file's
directory. Relative paths passed with `--output` or `--tfvars-output` are
resolved from the process's working directory and override the corresponding
configured output path.
These overrides do not change `publish.target`; `--output` with an
`object_storage` config still uploads. For local-only discovery and render
qualification, use a separate private config with `publish.target =
"local_file"` as described in [LKE publisher offline contract](lke-publisher-offline.md).

The command validates the generated registry before writing it. If configured,
it also writes generated tfvars JSON for Terraform consumers. Generated CIDR
lists may contain both IPv4 and IPv6 entries.

Local registry and tfvars files are each staged as complete files and then
atomically replace their respective destinations. A failed replacement leaves
the prior file at that destination intact instead of exposing a partially
written payload to consumers.

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

After `PutObject` returns, the one-line stdout JSON retains `status` and
`entries` and adds `upload_receipt` for Object Storage runs:

```json
{"status":"published","entries":1,"upload_receipt":{"sha256":"<64 lowercase hex digits>","size_bytes":123,"version_id":"<returned version ID>"}}
```

`sha256` and `size_bytes` describe the exact UTF-8 JSON bytes supplied as
`PutObject.Body`, including the final newline. The receipt does not print the
payload, bucket, key, endpoint, or credentials. `version_id` is the provider's
returned `VersionId`; it is JSON `null` if absent, blank, or the literal `null`
version sentinel. A returned PUT without a usable version ID keeps the existing
exit-0 `published` behavior for unversioned-bucket callers, but it does **not**
identify a version suitable for LKE's exact-version verification gate. The
`local_file` stdout shape remains unchanged and has no `upload_receipt`.

If the SDK raises during PUT, the command exits 1 with a public-safe error on
stderr and emits no success receipt. A timeout or process failure after the PUT
may leave the write outcome unknown; absence of a receipt does not prove the
object was not written. Reconcile Object Storage state before deciding whether
to retry.
The publisher adds no application-level retry. SDK retries or duplicate Job
execution can produce additional versions, so even a receipt with a VersionId
does not prove exactly-once writes or replace private readback verification.

Validation failures identify the affected CIDR field without echoing malformed
CIDR values. This keeps operator error output from disclosing private network
configuration.

## Live Meraki Discovery

For live Meraki discovery, configure `meraki.enabled = true` and
`meraki.organization_id` in a private local config, omit `meraki.fixture_path`,
and export `MERAKI_DASHBOARD_API_KEY` before running the one-shot publisher.
The publisher calls only the read-only uplink-address endpoint and follows
documented `Link` header pagination until no next page is present. It fails
before re-requesting a repeated page URL, so a malformed pagination cycle does
not silently duplicate discovery requests.
Malformed device, uplink, address, or public-address records, and non-string or
invalid public addresses, fail discovery without echoing the provider data in
the error message.

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
