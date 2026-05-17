# Provider Assumptions

Provider assumptions are intentionally narrow and cite official sources where
the MVP depends on external behavior.

| Assumption | Project use | Source | Checked |
| --- | --- | --- | --- |
| Linode Object Storage can be used as S3-compatible object storage and buckets are created before objects are uploaded. | Terraform provisions a private bucket; publisher output remains dynamic content outside Terraform. | [Akamai Cloud Object Storage guide](https://techdocs.akamai.com/cloud-computing/docs/getting-started-with-object-storage) | 2026-05-17 |
| The Linode Terraform provider supports `linode_object_storage_bucket` with `region`, `label`, and private ACL configuration. | `infra/terraform` provisions only storage infrastructure. | [Linode Terraform provider resource docs](https://registry.terraform.io/providers/linode/linode/latest/docs/resources/object_storage_bucket) | 2026-05-17 |
| The Linode Terraform provider can be configured with `LINODE_TOKEN`, `LINODE_OBJ_ACCESS_KEY`, and `LINODE_OBJ_SECRET_KEY`. | Docs recommend environment variables over committed credentials. | [Linode Terraform provider docs](https://registry.terraform.io/providers/linode/linode/latest/docs) | 2026-05-17 |
| Terraform can store sensitive variable values in state. | Security docs warn that state must remain private. | [Terraform variables docs](https://developer.hashicorp.com/terraform/language/values/variables), [Terraform sensitive data docs](https://developer.hashicorp.com/terraform/language/manage-sensitive-data) | 2026-05-17 |
| The Meraki Dashboard API exposes organization uplink statuses with generic uplink interfaces and a `publicIp` string field. | MVP Meraki code is limited to sanitized fixture parsing shaped like documented uplink data. It parses `publicIp` with `ipaddress`, renders IPv4 hosts as `/32`, and renders IPv6 hosts as `/128` if IPv6 values are present. | [Cisco Meraki Dashboard API: uplink statuses](https://developer.cisco.com/meraki/api-v1/get-organization-uplinks-statuses/), [Cisco Meraki Dashboard API getting started](https://developer.cisco.com/meraki/api-v1/getting-started/) | 2026-05-17 |

This repository is independent and personal. Provider names are used only to
describe integration surfaces; they do not imply affiliation, endorsement, or
support.
