output "bucket_label" {
  description = "Object Storage bucket label."
  value       = linode_object_storage_bucket.registry.label
}

output "bucket_region" {
  description = "Object Storage bucket region."
  value       = var.region
}

output "registry_object_key" {
  description = "Registry object key reserved for publisher use. Terraform does not manage object contents."
  value       = var.object_key
}
