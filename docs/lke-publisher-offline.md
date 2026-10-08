# LKE publisher: offline source and qualification contract

This repository supplies the publisher image source and the one-shot command.
The LKE deployment, credentials, scheduling, and eventual image promotion have
separate owners. This document does not authorize a registry upload or a NAS
cutover.

## Image source

`Dockerfile.lke` is the `linux/amd64` build input. Its Python base is pinned to
the registry-observed platform manifest digest, and
`requirements-lke.lock` pins the runtime dependencies with package hashes.
Build from the exact reviewed public Git commit so untracked local files and
private operator files never enter the build context. The Dockerfile copies
only the publisher's Python source files into the image. The existing
`Dockerfile` remains the NAS build source and retains its architecture choice.

An operator with a working container builder can build from an exact full
40-character source commit, replacing the placeholder below with the reviewed
commit. Docker's [Git context documentation](https://docs.docker.com/build/concepts/context/#git-repositories)
requires the full commit hash in this URL form:

```sh
docker build --platform linux/amd64 -f Dockerfile.lke -t trusted-network-registry:lke-local 'https://github.com/ctrl-alt-keith/trusted-network-registry.git#<reviewed-full-commit>'
```

The image entrypoint is `python -m trusted_network_registry.cli`. A successful
one-shot `publish` exits 0 and prints a JSON status and entry count, without
the registry payload. Handled runtime errors exit 1 with JSON on stderr;
argument errors exit 2 with argparse usage text. Image
publication requires a separate reviewed action: identify the exact source
commit, build platform, image tag, pushed immutable manifest digest, and the
image digest selected by the LKE deployment. A source or base-image digest is
not the resulting image digest. Pinned inputs make the build reconstructible;
this contract does not claim byte-identical images from different builders.

## Safe discovery and render qualification

Use a **separate private config** with the same `[registry]`,
`[[static_entries]]`, and `[meraki]` settings intended for production. For
live discovery, set `meraki.enabled = true` and provide the private
`meraki.organization_id`; omit `meraki.fixture_path`. Set `[publish]` to
`target = "local_file"` and use an absolute private writable `local_path`,
such as `/out/registry.json` in LKE. Relative configured output paths resolve
from the config directory and would fail under read-only `/config`. The same
rule applies to an optional `tfvars_path`. Omit
Object Storage destination fields. The Meraki API key is supplied only through
`MERAKI_DASHBOARD_API_KEY` in the runtime environment. This route reads Meraki,
validates schema v1, and writes only local JSON; it does not call the Object
Storage uploader. Keep the output private and inspect it without printing
CIDRs or config in shared logs.

Run the qualification job once with a private config mounted in the image:

```sh
trusted-network-registry publish --once --config <private-qualification-config>
```

The same arguments follow the image entrypoint. The local output path may be
overridden with `--output <private-output-path>`. **`--output` alone does not
suppress Object Storage upload** when the config has
`publish.target = "object_storage"`; never use the production upload config
for a render-only qualification. `validate-config` checks config shape but
does not perform discovery. A successful local render qualifies only that
command and config; it says nothing about upload credentials, in-cluster
network reach, object readback, scheduling, or single-writer cutover.

`make check` is the credential-free local validation path. It covers schema
validation, sanitized example rendering, public-safety checks, and regression
tests proving that a local config skips upload while `--output` with an Object
Storage config still reaches the uploader. It checks pin syntax and lock
consistency, but does not build or run the container; that requires a working
container builder before image promotion.
