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

## GHCR publication workflow

`.github/workflows/publish-lke-publisher.yml` publishes the already reviewed
source commit
`9cd00403ecae72f2757adcbc6b44b873231dc944`. It builds that exact public Git
commit rather than the commit containing the workflow, targets `linux/amd64`,
and grants only `packages: write` to its publication job. Its destination is
`ghcr.io/ctrl-alt-keith/trusted-network-registry/lke-publisher` with tag
`sha-9cd00403ecae72f2757adcbc6b44b873231dc944`. The run summary
distinguishes the source commit, workflow commit, builder, and pushed manifest
digest. Publication reruns are refused.

GitHub [requires a `workflow_dispatch` file on the default branch](https://docs.github.com/actions/managing-workflow-runs/manually-running-a-workflow)
before it can be dispatched, but supports a [push trigger filtered to an exact
tag](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushbranchestagsbranches-ignoretags-ignore).
The exact-tag event is the **first-package bootstrap**. Before creating the
tag, an organization package administrator must independently verify in the
organization's package inventory that the exact target package does not
exist. HTTP 404 from the job's package API is not proof of absence; it can
also mean lack of access. Record that operator check with the publication
decision in one issue-owned immutable evidence file with exact raw-byte
readback, size, SHA-256, provider file ID and revision. Use an annotated tag
whose message contains these exact lines with the verified values:

```text
CAK-364-Package: ghcr.io/ctrl-alt-keith/trusted-network-registry/lke-publisher
CAK-364-Absence-Decision: verified-absent
CAK-364-Absence-Evidence: id:<verified-file-id>
CAK-364-Absence-Revision: <verified-revision>
CAK-364-Absence-Bytes: <verified-byte-length>
CAK-364-Absence-SHA256: <verified-sha256>
```

The workflow checks that this is an annotated tag at the running workflow
commit and that the message carries the package and evidence identity. The
controller must compare those values with the actual verified evidence before
pushing; the workflow has no live access to the issue-owned provider. If that
evidence or comparison is unavailable, do not push the tag. After reviewing
the workflow commit, creating and pushing the unique tag
`cak-364-publish-9cd00403ecae72f2757adcbc6b44b873231dc944` at that commit
starts the bootstrap without merging the PR. The workflow refuses bootstrap
if it can read an existing package or manifest. It does not run on branch
pushes. A later manual dispatch from `main` is the **existing-package path**:
it requires readable package metadata and a complete version-tag inventory,
and refuses the target tag if present. An inaccessible package fails closed.
Every push of the bootstrap tag, including a deleted and re-created tag,
requires fresh absence evidence captured after all earlier bootstrap runs
ended. If an earlier run reached `docker push`, treat the package as existing
even if an inventory view has not refreshed yet.

The first publication completed in [run 37839591842](https://github.com/ctrl-alt-keith/trusted-network-registry/actions/runs/37839591842)
from workflow commit `74dbc58d35eb859831c9aea2232815fd520a8052`.
It recorded the pushed manifest digest
`sha256:580ec42339104bc799f2c949d45d2ebe51d0c6d76be088b99adb33cc281e8337`.
The package remains private by operator decision. A credential-free manifest
check returned `unauthorized`; no authenticated pull from the intended LKE
access context has been qualified. [GitHub's Container registry documentation](https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
describes authentication for private package pulls. Before LKE uses this image,
the integration owner must separately authorize and verify an authenticated
pull of this exact digest with the intended runtime access. This document does
not select or create those credentials.

The workflow also contains an optional public-verification path for a future,
separately authorized public package. If that decision changes, an organization
package administrator can change visibility; only then may a
`cak-364-verify-sha256-<pushed-manifest-digest-hex>` tag at the same workflow
commit launch the tokenless fresh-runner manifest and `linux/amd64` pull check.
That path is not a requirement for the current private image, and no such tag
has been pushed. Do not rerun publication against the same tag; a later source
commit needs its own reviewed publication change and unique SHA tag.

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
