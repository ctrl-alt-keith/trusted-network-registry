# Terraform Integration

Terraform has two separate roles in this project.

## Storage Infrastructure

[`../infra/terraform`](../infra/terraform) provisions a private Linode Object
Storage bucket. The bucket is infrastructure and belongs in Terraform.

Generated registry JSON is dynamic operational data and does not belong in
Terraform state for the MVP.

## Consumers

Consumers are read-only by default.

Local file example:

```hcl
locals {
  registry = jsondecode(file(var.registry_json_path))
}
```

Generated tfvars example:

```hcl
variable "trusted_admin_cidrs" {
  type = list(string)
}
```

Both examples expose `registry_valid_until` so callers can reject stale data
before using CIDRs.
