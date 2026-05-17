# Operations

## Publisher Run

Run exactly once:

```sh
trusted-network-registry publish --once --config publisher-config.toml
```

The command validates the generated registry before writing it. If configured,
it also writes generated tfvars JSON for Terraform consumers.

## Rotation

Set `registry.ttl_seconds` to the maximum acceptable age for consumers. The
publisher writes `valid_until`; consumers should enforce their own rejection
policy when that timestamp is stale.

## Logs

The MVP prints small status messages to stdout and error messages to stderr.
It should not print registry contents, credential values, provider IDs, device
names, or bucket identifiers.

## Recovery

If a bad payload is published, publish a corrected payload with a newer
`generated_at` and shorter `valid_until`. Registry history retention and
rollback docs are deferred follow-ups.
