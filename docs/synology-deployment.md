# Synology Deployment

The recommended Synology execution model is a one-shot scheduled container
run.

This repository does not currently publish official container images.
Operators can build and load the local image manually for first Synology use,
or publish their own private image. GHCR or other official image publication is
a follow-up, not part of the current repo contract.

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

## First-Pass Manual Transfer

Build the local image from the repository root:

```sh
docker build -t trusted-network-registry:local .
```

Load that image onto the NAS:

```sh
docker save trusted-network-registry:local | ssh <nas-host> docker load
```

Copy `deploy/synology/docker-compose.example.yml` to `docker-compose.yml` in a
private project directory on the NAS, place private `config.toml` and
`publisher.env` files beside it, create the private output directory, then run:

```sh
ssh <nas-host> 'cd <project-dir> && docker compose run --rm publisher'
```

The checked-in Compose example uses the local image name
`trusted-network-registry:local`. It mounts `config.toml` read-only at
`/config/config.toml`, injects `publisher.env`, writes generated output under
`/out`, and runs:

```sh
trusted-network-registry publish --once --config /config/config.toml
```

Do not commit edited operator config, env files, generated registry JSON, or
generated tfvars JSON.

## Synology Task Scheduler

Schedule the same one-shot Compose command from the private NAS project
directory:

```sh
docker compose run --rm publisher
```

The publisher is not a long-running daemon. Let logs go to stdout/stderr for
the Synology task log. Keep generated output in the private mounted output
directory and keep secrets env-only through `publisher.env` or a
Synology-supported secret mechanism.

Run and verify the first publish locally before moving the same private
operator config and env pattern to Synology. See
[`first-real-operator-run.md`](first-real-operator-run.md).

See [`../deploy/synology`](../deploy/synology) for example files.
