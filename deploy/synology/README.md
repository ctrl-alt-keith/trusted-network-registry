# Synology Deployment Example

The MVP execution model is a one-shot container run on a schedule. The
container starts, renders one registry payload, writes logs to stdout, and
exits.

This repository does not currently publish official container images. Build
and load the local image manually for first Synology use, or publish your own
private image. GHCR or other official image publication is a follow-up.

## Recommended Shape

- Schedule a Synology task to run the container periodically.
- Mount publisher config read-only.
- Inject secrets through `publisher.env` at container execution time.
- Write registry artifacts to a private output mount.
- For Object Storage publishing, use `LINODE_OBJ_ACCESS_KEY` and
  `LINODE_OBJ_SECRET_KEY` in the runtime env file.
- For live Meraki discovery, use `MERAKI_DASHBOARD_API_KEY` in the runtime env
  file.
- Do not put `LINODE_TOKEN` in `publisher.env`; it is for Terraform bucket
  provisioning, not publisher container runtime.
- Keep real bucket labels, endpoint URLs, object keys, Meraki identifiers, and
  secrets out of committed files.
- Do not run a long-lived daemon for the MVP.

## Runtime Secrets

`publisher.env` is local-only on the NAS. It must not be committed, copied
into the image, or checked into this repository.

The Compose example passes `publisher.env` as runtime environment only. Secrets
are not baked into the image, and they are not mounted as files unless the
operator chooses a different secret pattern later. The image receives these
values only when the container is executed:

```env
LINODE_OBJ_ACCESS_KEY=
LINODE_OBJ_SECRET_KEY=
MERAKI_DASHBOARD_API_KEY=
```

## Compose Example

Build the local image from the repository root:

```sh
docker build -t trusted-network-registry:local .
```

For first Synology use, load that image onto the NAS:

```sh
docker save trusted-network-registry:local | ssh <nas-host> docker load
```

Copy the example files into a private directory on the NAS:

```sh
cp docker-compose.example.yml docker-compose.yml
cp config.example.toml config.toml
cp publisher.env.example publisher.env
mkdir -p out
```

Edit the private `config.toml` and `publisher.env` on the NAS. Keep config
mounted read-only, secrets env-only, and generated output in the private `out`
directory.

Run one one-shot publish:

```sh
ssh <nas-host> 'cd <project-dir> && docker compose run --rm publisher'
```

Then schedule the same command in Synology Task Scheduler from `<project-dir>`:

```sh
docker compose run --rm publisher
```

The container logs to stdout/stderr and exits after one publish. Do not run it
as a long-lived daemon.

## First NAS Test Checklist

1. Copy `docker-compose.example.yml` to a private NAS project directory and
   edit it as needed for the local deployment.
2. Copy `config.example.toml` to private `config.toml`.
3. Copy `publisher.env.example` to private `publisher.env`.
4. Fill only `LINODE_OBJ_ACCESS_KEY`, `LINODE_OBJ_SECRET_KEY`, and
   `MERAKI_DASHBOARD_API_KEY` in `publisher.env`.
5. Build and load the image as `trusted-network-registry:local`.
6. Run the one-shot Compose command manually.
7. Verify generated local output and the remote object.
8. Only then schedule the same one-shot command in Synology Task Scheduler.

Do not commit edited `publisher.env`, generated registry JSON, or generated
tfvars JSON.

Before scheduling on Synology, complete a local one-shot publish and private
upload verification with the repository runbook:
[`../../docs/first-real-operator-run.md`](../../docs/first-real-operator-run.md).
