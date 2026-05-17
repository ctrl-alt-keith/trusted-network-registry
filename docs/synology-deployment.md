# Synology Deployment

The recommended Synology execution model is a one-shot scheduled container
run.

This repository does not currently publish official container images.
Operators should either build and publish their own private image or run the
publisher locally in an equivalent scheduled command. The Compose files under
`deploy/synology/` are placeholder-only examples that describe execution shape,
not an official image distribution contract.

## Shape

- The scheduled task runs the publisher container.
- The container executes `trusted-network-registry publish --once`.
- Logs go to stdout.
- Config is mounted read-only.
- Secrets are injected through an env file or Synology-supported secret
  mechanism.
- Generated output is written to a private mounted directory.
- When `publish.target = "object_storage"`, the generated output is still
  rendered locally first, then uploaded to the configured private object.

The MVP intentionally avoids Ansible, the Terraform Docker provider, and
long-running daemon loops. Those can be evaluated later if manual scheduling or
Compose becomes painful.

Run and verify the first publish locally before moving the same private
operator config and env pattern to Synology. See
[`first-real-operator-run.md`](first-real-operator-run.md).

See [`../deploy/synology`](../deploy/synology) for example files.
