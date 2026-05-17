# Synology Deployment

The recommended Synology execution model is a one-shot scheduled container
run.

## Shape

- The scheduled task runs the publisher container.
- The container executes `trusted-network-registry publish --once`.
- Logs go to stdout.
- Config is mounted read-only.
- Secrets are injected through an env file or Synology-supported secret
  mechanism.
- Generated output is written to a private mounted directory.

The MVP intentionally avoids Ansible, the Terraform Docker provider, and
long-running daemon loops. Those can be evaluated later if manual scheduling or
Compose becomes painful.

See [`../deploy/synology`](../deploy/synology) for example files.
