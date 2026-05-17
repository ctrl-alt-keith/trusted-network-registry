variable "registry_json_path" {
  type        = string
  description = "Path to a private generated registry JSON file."
}

locals {
  registry = jsondecode(file(var.registry_json_path))

  trusted_admin_cidrs = [
    for entry in local.registry.entries : entry.cidr
    if entry.status == "active"
  ]
}

output "trusted_admin_cidrs" {
  value       = local.trusted_admin_cidrs
  description = "Active trusted/admin CIDRs from the registry."
}

output "registry_valid_until" {
  value       = local.registry.registry.valid_until
  description = "Timestamp consumers should use to reject stale registry data."
}
