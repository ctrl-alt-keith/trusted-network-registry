variable "bucket_label" {
  type        = string
  description = "Globally unique Object Storage bucket label within the selected region."
}

variable "region" {
  type        = string
  description = "Linode Object Storage region, for example us-mia."
}

variable "object_key" {
  type        = string
  description = "Registry object key documented for publisher use. Terraform does not manage this object."
  default     = "registry.json"

  validation {
    condition     = var.object_key != "" && trimspace(var.object_key) == var.object_key
    error_message = "object_key must be a non-empty key with no surrounding whitespace."
  }
}

variable "enable_versioning" {
  type        = bool
  description = "Enable Object Storage bucket versioning."
  default     = true
}
