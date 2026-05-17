variable "trusted_registry" {
  type        = any
  description = "Generated trusted registry object."
}

variable "trusted_admin_cidrs" {
  type        = list(string)
  description = "Generated active trusted/admin CIDRs."
}

variable "trusted_registry_valid_until" {
  type        = string
  description = "Timestamp consumers should use to reject stale registry data."
}

output "trusted_admin_cidrs" {
  value       = var.trusted_admin_cidrs
  description = "Active trusted/admin CIDRs from generated tfvars JSON."
}

output "registry_valid_until" {
  value       = var.trusted_registry_valid_until
  description = "Timestamp consumers should use to reject stale registry data."
}
