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
- Secrets are injected through `publisher.env` at container execution time.
- Generated output is written to a private mounted directory.
- When `publish.target = "object_storage"`, the generated output is still
  rendered locally first, then uploaded to the configured private object.
- `LINODE_TOKEN` is for Terraform bucket provisioning and is not needed by the
  publisher container at runtime.

The MVP intentionally avoids Ansible, the Terraform Docker provider, and
long-running daemon loops. Those can be evaluated later if manual scheduling or
Compose becomes painful.

## Runtime Secrets

`publisher.env` is local-only on the NAS and must not be committed. Compose
passes it as runtime environment only.

Secrets are not baked into the image. Secrets are not mounted as files unless
the operator chooses that pattern later. The image only receives these values
at container execution time:

```env
LINODE_OBJ_ACCESS_KEY=
LINODE_OBJ_SECRET_KEY=
MERAKI_DASHBOARD_API_KEY=
```

Do not add `LINODE_TOKEN` to the publisher runtime env file; Terraform uses it
for bucket provisioning outside the container publish path.

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

## First NAS Test Checklist

1. Copy and edit `docker-compose.example.yml` in a private NAS project
   directory.
2. Copy and edit `config.example.toml` as private `config.toml`.
3. Copy and edit `publisher.env.example` as private `publisher.env`.
4. Fill only `LINODE_OBJ_ACCESS_KEY`, `LINODE_OBJ_SECRET_KEY`, and
   `MERAKI_DASHBOARD_API_KEY`.
5. Build and load the image as `trusted-network-registry:local`.
6. Run the one-shot Compose command manually.
7. Verify generated local output and the remote object.
8. Only then schedule the same one-shot command with Synology Task Scheduler.

## Synology Task Scheduler

Schedule the same one-shot Compose command from the private NAS project
directory:

```sh
docker compose run --rm publisher
```

The publisher is not a long-running daemon. Let logs go to stdout/stderr for
the Synology task log. Keep generated output in the private mounted output
directory and keep secrets env-only through `publisher.env`.

Run and verify the first publish locally before moving the same private
operator config and env pattern to Synology. See
[`first-real-operator-run.md`](first-real-operator-run.md).

See [`../deploy/synology`](../deploy/synology) for example files.
