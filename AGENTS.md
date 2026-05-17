# AGENTS.md

This repository uses the shared `ai-workflow-playbook` as the canonical source
for general workflow rules. This file is the thin repo-local execution layer.
Repo-local rules take precedence only for repo-specific behavior.

## Startup And Interaction Mode

- Start with `ai-workflow-playbook/docs/start-here.md` before repository or
  software work.
- Before acting, select the interaction mode from
  `ai-workflow-playbook/docs/repo-readiness.md`: implementation, review/audit,
  or orchestration/prompt-authoring.
- Implementation agents make explicit repo changes and carry them through
  validation, commit, push, and PR delivery.
- Review/audit agents inspect and report findings without mutating the repo.
- Orchestration/prompt-authoring agents produce complete, self-contained
  handoffs or prompts unless explicitly asked to implement.

## Repo Scope

- This repo contains a public-safe publisher for a private trusted/admin CIDR
  registry.
- The publisher owns registry production only.
- Terraform owns storage infrastructure only.
- Consumers are read-only by default.
- Do not add continuous reconciliation, automatic firewall mutation, Terraform
  ownership of dynamic registry JSON contents, general toolbox sprawl, or NAS
  platform abstraction in the MVP.

## Execution Model Boundary

- Prefer one-shot publisher execution with `publish --once`.
- Synology examples should use scheduled container execution or a simple
  one-shot Compose/run pattern.
- Do not add daemon loops or long-running polling behavior unless a later
  milestone explicitly asks for it.

## File Placement

- Put source code under `src/trusted_network_registry/`.
- Put discovery adapters under `src/trusted_network_registry/discovery/`.
- Put unit tests under `tests/unit/`.
- Put repo documentation under `docs/`.
- Put JSON schemas under `schemas/`.
- Put sanitized fixtures under `tests/fixtures/sanitized/`.
- Put Terraform storage infrastructure under `infra/terraform/`.
- Put Synology deployment examples under `deploy/synology/`.

## Local Execution

- Run commands from this repository working directory by default.
- Keep temporary workflow state repo-local, for example `.worktrees/`.
- Use direct command execution for ordinary repo commands such as `git ...`,
  `gh ...`, `make ...`, `python ...`, and repo-local scripts or tools.
- Before using `zsh`, `bash`, `sh`, `zsh -lc`, `bash -lc`, `sh -c`, aliases, or
  equivalent wrapper shells, check whether the command has a direct form and
  use that direct form when it does.

## Provider Assumptions

- Before changing behavior, docs, tests, or user-facing claims that depend on
  Linode Object Storage, Terraform, or Meraki provider semantics, verify the
  assumption against official provider documentation.
- Do not encode guessed provider behavior. If public docs are unclear, state
  the uncertainty and keep behavior conservative.
- When relevant, cite or summarize the verified source in PR notes or docs.

## Public-Safe Boundary

- Treat every repository file as public.
- Treat generated registry payloads as sensitive operational access data.
- Examples must use only documentation IP ranges.
- Do not commit secret values, real home IPs, Meraki serials, organization IDs,
  network IDs, device names, ISP names, topology labels, bucket names, provider
  identifiers, non-public URLs, workplace metadata, or internal DNS names.
- `MERAKI_DASHBOARD_API_KEY`, `LINODE_TOKEN`, `LINODE_OBJ_ACCESS_KEY`, and
  `LINODE_OBJ_SECRET_KEY` may appear only as environment variable names.
- Fixtures must be sanitized and live under `tests/fixtures/sanitized/`.

## Validation

- Use `make check` as the canonical validation entrypoint.
- `make check` runs Python compile checks, unit tests, schema/example
  validation, and public-safety checks.
- Live provider checks and credentialed checks are outside local blocking
  validation for the MVP.
- Keep validation implemented through the Makefile rather than direct tool
  invocation in normal workflow.

## Branches and PRs

- Branch from current `origin/main`.
- Follow the shared playbook branch naming guidance; use focused,
  purpose-based names such as `docs/<short-name>` or `feat/<short-name>`.
- Open PRs against `main`.
