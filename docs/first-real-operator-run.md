# First Real Operator Run

This runbook prepares the first private operator publish without moving real
operator data into Git. Keep every file under `operator/` local to the machine
or NAS that runs the publisher.

Do not commit real config, real IP addresses, Meraki organization IDs, network
IDs, serials, device names, Object Storage bucket labels, endpoint URLs,
object keys, generated registry payloads, generated tfvars, or secrets.

Bootstrap a fresh local checkout before operator work:

```sh
make venv
. .venv/bin/activate
make check
```

## Local Layout

Recommended private layout:

```text
operator/
  publisher-config.toml
  publisher.env
  storage.tfvars
  generated/
    registry.json
    trusted-registry.auto.tfvars.json
  verify/
    registry.remote.json
```

These files are intentionally ignored by Git. They may reveal administrative
source networks, private provider identifiers, bucket locations, object names,
or credentials.

## 1. Provision Private Object Storage

Prepare a local-only Terraform variable file:

```hcl
# operator/storage.tfvars
bucket_label = "<private-bucket-label>"
region       = "<object-storage-region>"
object_key   = "<private-object-key>"
```

Provision the private bucket from an operator shell, not from CI:

```sh
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform plan -var-file="../../operator/storage.tfvars"
terraform -chdir=infra/terraform apply -var-file="../../operator/storage.tfvars"
```

Review the plan before apply. It should contain private Object Storage
infrastructure only, with no firewall resources and no public object or public
bucket access resources.

Terraform owns the storage infrastructure only. It does not upload registry
JSON, manage generated `.auto.tfvars.json`, mutate firewalls, or make registry
objects public.

## 2. Create Local Publisher Config

Create `operator/publisher-config.toml` with private values:

```toml
[registry]
name = "trusted-network-registry"
ttl_seconds = 3600

[meraki]
enabled = true
organization_id = "<private-meraki-organization-id>"

[publish]
target = "object_storage"
local_path = "operator/generated/registry.json"
tfvars_path = "operator/generated/trusted-registry.auto.tfvars.json"
bucket = "<private-bucket-label>"
endpoint_url = "https://<s3-endpoint-hostname>"
region = "<object-storage-region>"
object_key = "<private-object-key>"
```

For a dry local shape check before live discovery, temporarily use sanitized
static entries or a sanitized fixture. Do not commit the edited local config.

## 3. Load Credentials

The application contract is environment variables. Secret managers are optional
wrappers that populate those variables before the process starts.

Plain shell example:

```sh
export MERAKI_DASHBOARD_API_KEY="<private-meraki-api-key>"
export LINODE_OBJ_ACCESS_KEY="<private-object-storage-access-key>"
export LINODE_OBJ_SECRET_KEY="<private-object-storage-secret-key>"
```

1Password `op` example:

```sh
cat > operator/publisher.env <<'EOF'
MERAKI_DASHBOARD_API_KEY=op://<vault>/<meraki-item>/api-key
LINODE_OBJ_ACCESS_KEY=op://<vault>/<object-storage-item>/access-key
LINODE_OBJ_SECRET_KEY=op://<vault>/<object-storage-item>/secret-key
EOF
```

Then run commands through `op run --env-file=operator/publisher.env -- ...`.
Do not add a secret-manager dependency to the Python package.

Before the first live run, verify the Meraki API key has only the scope needed
for the read-only uplink-address discovery endpoint.

## 4. Run One-Shot Publish Locally

Create private output directories:

```sh
mkdir -p operator/generated operator/verify
```

Run the publisher once:

```sh
op run --env-file=operator/publisher.env -- \
  trusted-network-registry publish --once \
  --config operator/publisher-config.toml \
  --output operator/generated/registry.json \
  --tfvars-output operator/generated/trusted-registry.auto.tfvars.json
```

If not using `op`, run the same command after exporting the required
environment variables.

This is the first live provider boundary: live Meraki discovery is read-only,
and Object Storage upload writes the generated registry object. Do not run this
step from CI.

## 5. Verify Local Payload Shape

Validate the local payload without pasting its contents into logs, PRs, or
issues:

```sh
trusted-network-registry validate-registry operator/generated/registry.json
jq 'keys' operator/generated/registry.json
```

Confirm `generated_at`, `valid_until`, schema version, and CIDR families look
right before upload. Treat the CIDR list itself as sensitive. Generated
registry artifacts contain sensitive operational access data even when they
are ignored by Git.

## 6. Verify The Private Upload

Use an S3-compatible client from the same credentialed operator environment:

```sh
aws --endpoint-url "https://<s3-endpoint-hostname>" \
  s3api head-object \
  --bucket "<private-bucket-label>" \
  --key "<private-object-key>"

aws --endpoint-url "https://<s3-endpoint-hostname>" \
  s3 cp "s3://<private-bucket-label>/<private-object-key>" \
  operator/verify/registry.remote.json

trusted-network-registry validate-registry operator/verify/registry.remote.json
```

Verify the remote object manually before wiring any consumers to it.

The object must remain private. Do not publish the registry object publicly,
grant public bucket access, or paste fetched payload contents into shared
channels.

## 7. Move To Synology Scheduling

After the local one-shot publish and private upload verification succeed, copy
the private config and env material to the Synology operator directory and use
the one-shot scheduled container model in [`synology-deployment.md`](synology-deployment.md).

Keep the scheduled task boring: one container run, one publish attempt, stdout
logs, private output mount, and no daemon loop.

## Stale Data And Rollback

Set `registry.ttl_seconds` to the maximum age consumers should trust. Consumers
should reject stale registries when `valid_until` has passed.

If a bad payload is uploaded, publish a corrected payload with a newer
`generated_at` and an appropriate `valid_until`. If bucket versioning is
enabled, you may restore a previous object version, but validate the restored
payload locally before relying on it.

If upload status is uncertain, prefer leaving consumers on their last valid
private object over making the registry public or widening firewall access as
a workaround.

## CI Boundary

CI should run public-safe validation only. It must not call live Meraki
Dashboard APIs, upload Object Storage objects, run `terraform apply`, or depend
on private operator files.
