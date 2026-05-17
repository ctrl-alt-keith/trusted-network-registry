provider "linode" {}

resource "linode_object_storage_bucket" "registry" {
  region     = var.region
  label      = var.bucket_label
  acl        = "private"
  versioning = var.enable_versioning
}
