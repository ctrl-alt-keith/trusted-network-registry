provider "linode" {}

resource "linode_object_storage_bucket" "registry" {
  region     = var.region
  label      = var.bucket_label
  acl        = "private"
  versioning = var.enable_versioning

  lifecycle_rule {
    id      = "registry-noncurrent-one-day"
    prefix  = var.object_key
    enabled = true

    noncurrent_version_expiration {
      days = 1
    }
  }
}
