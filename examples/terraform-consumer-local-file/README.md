# Terraform Consumer: Local Registry File

This example reads a generated private registry JSON file from disk:

```hcl
locals {
  registry = jsondecode(file(var.registry_json_path))
}
```

Consumers should reject stale registries by comparing
`local.registry.registry.valid_until` with their own policy before using the
CIDRs.
