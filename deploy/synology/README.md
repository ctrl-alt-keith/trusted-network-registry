# Synology Deployment Example

The MVP execution model is a one-shot container run on a schedule. The
container starts, renders one registry payload, writes logs to stdout, and
exits.

This repository does not currently publish official container images. Build
and publish your own private image, or run the same one-shot publisher command
locally. The Compose example is a placeholder-only execution shape.

## Recommended Shape

- Schedule a Synology task to run the container periodically.
- Mount publisher config read-only.
- Inject secrets through an env file or a Synology-supported secret mechanism.
- Write registry artifacts to a private output mount.
- For Object Storage publishing, use `LINODE_OBJ_ACCESS_KEY` and
  `LINODE_OBJ_SECRET_KEY` in the runtime env file and keep real bucket labels,
  endpoint URLs, and object keys out of committed files.
- Do not run a long-lived daemon for the MVP.

## Compose Example

After replacing the placeholder image with your own private image, copy the
example files into a private directory on the NAS:

```sh
cp docker-compose.example.yml docker-compose.yml
cp config.example.toml config.toml
cp publisher.env.example publisher.env
mkdir -p out
```

Then schedule:

```sh
docker compose run --rm publisher
```

Do not commit edited `publisher.env`, generated registry JSON, or generated
tfvars JSON.

Before scheduling on Synology, complete a local one-shot publish and private
upload verification with the repository runbook:
[`../../docs/first-real-operator-run.md`](../../docs/first-real-operator-run.md).
