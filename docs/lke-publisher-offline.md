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

`.github/workflows/publish-lke-publisher.yml` is prepared to publish the
reviewed source commit `8781f32ba1b0fcb2b91d190a5a603b637cccca05` to the
existing private package. It builds that exact public Git commit rather than
the commit containing the workflow, targets `linux/amd64`, and grants only
`packages: write` to its publication job. Its destination is
`ghcr.io/ctrl-alt-keith/trusted-network-registry/lke-publisher` with tag
`sha-8781f32ba1b0fcb2b91d190a5a603b637cccca05`. The run summary
distinguishes the source commit, workflow commit, builder, and pushed manifest
digest. Publication reruns are refused.

GitHub [requires a `workflow_dispatch` file on the default branch](https://docs.github.com/actions/managing-workflow-runs/manually-running-a-workflow)
before it can be dispatched, but supports a [push trigger filtered to an exact
tag](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushbranchestagsbranches-ignoretags-ignore).
The first-package bootstrap used a different exact tag and a reviewed workflow
at commit `74dbc58d35eb859831c9aea2232815fd520a8052`. The current
`cak-364-publish-8781f32ba1b0fcb2b91d190a5a603b637cccca05` tag is an
**existing-package** publication path. After the workflow change has its own
review and exact-head checks, an annotated tag at that workflow commit can
launch it before merge. The job requires authenticated HTTP 200 package
metadata, a paginated version-tag inventory that contains the known first
publication tag, and an authenticated HTTP 200 for the first-publication
manifest. Using the same registry token, it requires an explicit HTTP 404 for
the new tag's manifest. Authentication, authorization, rate limiting,
transport, redirects, and unknown responses stop the job. It repeats these
checks after building and before pushing. An unrelated writer can still race
these checks. Branch
pushes do not publish. The `workflow_dispatch` alternative still requires the
workflow on `main` and a dispatch from `main`.

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

The published image above uses source commit `9cd00403ecae72f2757adcbc6b44b873231dc944`
and **does not contain** the upload receipt candidate in this PR. The
replacement image at source `8781f32ba1b0fcb2b91d190a5a603b637cccca05`
has not been published. A reviewed build is required before LKE can rely on
the candidate's one-line stdout `upload_receipt` (`sha256`, `size_bytes`, and returned
`version_id`). The digest and byte length cover the exact `PutObject.Body`
bytes, not a later local render. An absent or `null` version ID cannot identify
the uploaded version for readback. The integration owner must capture the
receipt after the one-shot container exits and independently verify that
version's bytes and current-version status before accepting publication. See
[Object Storage upload behavior](operations.md#object-storage-uploads) for
the candidate's failure and compatibility limits. No new image has been built
or published for this change.

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
